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
        return await self._request("POST", f"/dali/sendDali24/{line}", json=[frame])

    async def async_start_scan(self) -> Any:
        """Trigger the gateway's own device scan, without re-addressing."""
        return await self._request(
            "POST",
            "/dali/scan",
            json={"newInstallation": False, "noAddressing": True},
        )
