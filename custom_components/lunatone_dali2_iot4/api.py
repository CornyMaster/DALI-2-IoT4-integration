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


def parse_device_description(data: list[Any]) -> str | None:
    """Extract the description text from memory bank 2 read answers."""
    raw = bytearray()
    for value in data[DESCRIPTION_OFFSET:]:
        if not isinstance(value, int) or value in (0x00, 0xFF):
            break
        raw.append(value)
    text = raw.decode("utf-8", errors="replace").strip()
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
        return await self._request("POST", f"/dali/sendDali24/{line}", json=frames)

    async def async_read_input_device_description(
        self, line: int, address: int
    ) -> str | None:
        """Read the device description of a DALI-2 input device.

        Reads memory bank 2 via DTR1/DTR0 + READ MEMORY LOCATION (queries
        only, no configuration change). Returns None when no description is
        stored.
        """
        read = {
            "address": (address << 1) | 1,
            "instance": DEVICE_INSTANCE,
            "command": CMD_READ_MEMORY_LOCATION,
        }
        setup = [
            {
                "address": SPECIAL_DEVICE_ADDRESS,
                "instance": CMD_SET_DTR1,
                "command": DESCRIPTION_MEMORY_BANK,
            },
            {
                "address": SPECIAL_DEVICE_ADDRESS,
                "instance": CMD_SET_DTR0,
                "command": 0,
            },
        ]
        total = DESCRIPTION_OFFSET + DESCRIPTION_MAX_LENGTH
        first_reads = DALI24_MAX_FRAMES_PER_REQUEST - len(setup)
        answers = await self.async_send_dali24_frames(
            line, setup + [read] * first_reads
        )
        data: list[Any] = list(answers[len(setup):])
        while len(data) < total:
            chunk = min(DALI24_MAX_FRAMES_PER_REQUEST, total - len(data))
            data.extend(await self.async_send_dali24_frames(line, [read] * chunk))
        return parse_device_description(data)

    async def async_start_scan(self) -> Any:
        """Trigger the gateway's own device scan, without re-addressing."""
        return await self._request(
            "POST",
            "/dali/scan",
            json={"newInstallation": False, "noAddressing": True},
        )
