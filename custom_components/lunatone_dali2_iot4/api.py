"""Async REST client for the Lunatone DALI-2 IoT(4) gateway.

Pure aiohttp (no Home Assistant imports) so it is testable standalone. The
caller provides the ClientSession (in HA: ``async_get_clientsession(hass)``).

Line handling: device control uses the gateway-unique device id (the gateway
resolves the line itself); group and broadcast control accept an optional
``line`` which is sent as the ``_line`` query parameter — without it the
gateway addresses ALL lines.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10

# Raw 24-bit DALI frames (IEC 62386-103)
DALI24_MAX_FRAMES_PER_REQUEST = 16  # gateway limit per sendDali24 request
SPECIAL_DEVICE_ADDRESS = 0xC1  # special device commands (DTR0/DTR1)
CMD_SET_DTR0 = 0x30
CMD_SET_DTR1 = 0x31
CMD_READ_MEMORY_LOCATION = 0x3C
DEVICE_INSTANCE = 0xFE  # instance byte addressing the device itself
# Lunatone stores the user-editable device description ("Device Description"
# in DALI Cockpit, written to the device) in memory bank 2, after a 3-byte
# header; up to 30 characters, UTF-8.
DESCRIPTION_MEMORY_BANK = 2
DESCRIPTION_OFFSET = 3
DESCRIPTION_MAX_LENGTH = 30
DESCRIPTION_READ_RETRIES = 3  # whole-read retries on an unreliable (NAK'd) read


class IncompleteDescriptionError(Exception):
    """A memory-bank-2 read was unreliable and must be retried.

    Raised when a per-byte answer is missing (``None`` from a DALI NAK) before
    a proper string terminator, or when the collected bytes are not valid
    UTF-8. Treating such a read as a finished string is exactly what produced
    truncated ("Schalter_Wohnzimme") and garbled names; the caller retries
    instead of persisting a corrupt name.
    """


def parse_device_description(data: list[Any]) -> str | None:
    """Extract the description text from memory bank 2 read answers.

    ``0x00`` and ``0xFF`` are end-of-string markers (a UTF-8 name never
    contains ``0xFF``). A missing answer (``None``/non-int) *before* a
    terminator means the read failed mid-string -> raise so it can be retried
    rather than silently truncated. Returns ``None`` for an empty description.
    """
    raw = bytearray()
    for value in data[DESCRIPTION_OFFSET:]:
        if value in (0x00, 0xFF):
            break
        if not isinstance(value, int) or not 0 <= value <= 0xFF:
            raise IncompleteDescriptionError(
                f"missing/invalid byte in description read: {value!r}"
            )
        raw.append(value)
    try:
        text = raw.decode("utf-8").strip()
    except UnicodeDecodeError as err:
        raise IncompleteDescriptionError(f"description not valid UTF-8: {err}") from err
    return text or None


class LunatoneApiError(Exception):
    """Communication with the gateway failed."""


class LunatoneReadOnlyError(LunatoneApiError):
    """A write was attempted on a client constructed with read_only=True."""


class LunatoneRestClient:
    """Thin typed wrapper around the gateway REST endpoints."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int = 80,
        read_only: bool = False,
    ) -> None:
        self._session = session
        self._read_only = read_only
        self.host = host
        self.port = port
        self.base_url = f"http://{host}" if port == 80 else f"http://{host}:{port}"
        # Raw DALI-24 traffic on one line must be serialized: setting DTR0/DTR1
        # uses the broadcast special address, so concurrent reads/writes on the
        # same line clobber each other's transfer registers.
        self._line_locks: dict[int, asyncio.Lock] = {}

    def _line_lock(self, line: int) -> asyncio.Lock:
        lock = self._line_locks.get(line)
        if lock is None:
            lock = asyncio.Lock()
            self._line_locks[line] = lock
        return lock

    async def _request(
        self,
        method: str,
        path: str,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        if method != "GET" and self._read_only:
            raise LunatoneReadOnlyError(
                f"read-only client: refusing {method} {path}"
            )
        url = f"{self.base_url}{path}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.request(
                    method, url, json=json, params=params
                ) as response:
                    if response.status >= 400:
                        body = await response.text()
                        raise LunatoneApiError(
                            f"{method} {url} failed: HTTP {response.status}: {body[:200]}"
                        )
                    if response.content_type == "application/json":
                        return await response.json()
                    return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
            raise LunatoneApiError(f"{method} {url} failed: {err}") from err

    # -- read endpoints ----------------------------------------------------

    async def async_get_info(self) -> dict[str, Any]:
        return await self._request("GET", "/info")

    async def async_get_devices(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/devices")
        return data.get("devices", [])

    async def async_get_sensors(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/sensors")
        return data.get("sensors", [])

    async def async_get_scan_status(self) -> dict[str, Any]:
        return await self._request("GET", "/dali/scan")

    async def async_get_device_scenes(self, gw_id: int) -> dict[str, Any]:
        """Stored scene values of one device: {"0": {"dimmable": pct|null}, ...}."""
        return await self._request("GET", f"/device/{gw_id}/scenes")

    async def async_set_device_scenes(
        self, gw_id: int, scenes: dict[str, Any]
    ) -> dict[str, Any]:
        """Write stored scene values of one device (partial updates allowed)."""
        return await self._request("POST", f"/device/{gw_id}/scenes", json=scenes)

    # -- control endpoints (ControlData bodies) -----------------------------

    async def async_control_device(
        self, gw_id: int, control: dict[str, Any]
    ) -> Any:
        """Control one device via its gateway-unique id (line-safe)."""
        return await self._request("POST", f"/device/{gw_id}/control", json=control)

    async def async_control_group(
        self, group: int, control: dict[str, Any], line: int | None = None
    ) -> Any:
        """Control a DALI group (0-15); line=None addresses all lines."""
        params = {"_line": line} if line is not None else None
        return await self._request(
            "POST", f"/group/{group}/control", json=control, params=params
        )

    async def async_control_broadcast(
        self, control: dict[str, Any], line: int | None = None
    ) -> Any:
        """Broadcast to one line, or to all lines if line is None."""
        params = {"_line": line} if line is not None else None
        return await self._request(
            "POST", "/broadcast/control", json=control, params=params
        )

    # -- misc write endpoints ------------------------------------------------

    async def async_send_dali24(
        self, line: int, address: int, instance: int, command: int
    ) -> Any:
        """Send a raw 24-bit DALI frame on one line (used for feedback LEDs)."""
        frame = {"address": address, "instance": instance, "command": command}
        return await self.async_send_dali24_frames(line, [frame])

    async def async_send_dali24_frames(
        self, line: int, frames: list[dict[str, int]]
    ) -> list[Any]:
        """Send a batch of raw 24-bit frames; returns one answer per frame."""
        async with self._line_lock(line):
            return await self._send_dali24_frames(line, frames)

    async def _send_dali24_frames(
        self, line: int, frames: list[dict[str, int]]
    ) -> list[Any]:
        """Unlocked variant; caller must already hold the line lock."""
        return await self._request("POST", f"/dali/sendDali24/{line}", json=frames)

    async def async_read_input_device_description(
        self, line: int, address: int
    ) -> str | None:
        """Read the device description of a DALI-2 input device.

        Reads memory bank 2 via DTR1/DTR0 + READ MEMORY LOCATION (queries
        only, no configuration change). The whole sequence runs under the line
        lock so a concurrent read/write cannot reset the shared transfer
        registers mid-read. An unreliable read (a NAK'd byte) is retried rather
        than accepted as a truncated name. Returns None when no description is
        stored or the read keeps failing.
        """
        async with self._line_lock(line):
            for _attempt in range(DESCRIPTION_READ_RETRIES):
                data = await self._read_description_bank(line, address)
                try:
                    return parse_device_description(data)
                except IncompleteDescriptionError as err:
                    _LOGGER.debug(
                        "Unreliable description read on line %d address %d: %s",
                        line,
                        address,
                        err,
                    )
            return None

    async def _read_description_bank(self, line: int, address: int) -> list[Any]:
        """Read memory bank 2 (header + description) into a flat byte list.

        Each HTTP request re-seeks DTR0 to the next location instead of relying
        on the device's auto-increment surviving between separate requests, so
        the read is deterministic even if other line traffic intervenes.
        """
        read = {
            "address": (address << 1) | 1,
            "instance": DEVICE_INSTANCE,
            "command": CMD_READ_MEMORY_LOCATION,
        }
        total = DESCRIPTION_OFFSET + DESCRIPTION_MAX_LENGTH
        data: list[Any] = []
        while len(data) < total:
            setup = [
                {
                    "address": SPECIAL_DEVICE_ADDRESS,
                    "instance": CMD_SET_DTR1,
                    "command": DESCRIPTION_MEMORY_BANK,
                },
                {
                    "address": SPECIAL_DEVICE_ADDRESS,
                    "instance": CMD_SET_DTR0,
                    "command": len(data),
                },
            ]
            reads = min(
                DALI24_MAX_FRAMES_PER_REQUEST - len(setup), total - len(data)
            )
            answers = await self._send_dali24_frames(line, setup + [read] * reads)
            data.extend(answers[len(setup):])
        return data

    async def async_start_scan(self) -> Any:
        """Trigger the gateway's own device scan, without re-addressing."""
        return await self._request(
            "POST",
            "/dali/scan",
            json={"newInstallation": False, "noAddressing": True},
        )
