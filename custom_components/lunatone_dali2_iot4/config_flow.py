"""Config flow for the Lunatone DALI-2 IoT(4) integration.

The number of DALI lines is detected automatically from GET /info
(``descriptor.lines``: 4 on an IoT4, 1 on the classic DALI-2 IoT). The user
can then choose which lines the integration should manage — both during
setup and later via the options flow.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LunatoneApiError, LunatoneRestClient
from .const import (
    CONF_ENABLE_GLOBAL_BROADCAST,
    CONF_TRACK_INPUTS,
    CONF_HOST,
    CONF_LINES,
    CONF_POLLING_INTERVAL,
    CONF_PORT,
    DEFAULT_NAME,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_PORT,
    DOMAIN,
    MAX_POLLING_INTERVAL,
    MIN_POLLING_INTERVAL,
)
from .models import GatewayInfo

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


def _line_options(line_count: int) -> dict[str, str]:
    return {str(line): f"Line {line}" for line in range(line_count)}


async def _fetch_gateway_info(
    hass: HomeAssistant, host: str, port: int
) -> GatewayInfo:
    client = LunatoneRestClient(async_get_clientsession(hass), host, port)
    try:
        return GatewayInfo.from_api(await client.async_get_info())
    except LunatoneApiError as err:
        raise CannotConnect(str(err)) from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lunatone DALI-2 IoT."""

    VERSION = 3

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._info: GatewayInfo | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for the gateway address and verify it via GET /info."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _fetch_gateway_info(
                    self.hass, user_input[CONF_HOST], user_input[CONF_PORT]
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    info.uid or str(info.serial or user_input[CONF_HOST])
                )
                self._abort_if_unique_id_configured()
                self._host = user_input[CONF_HOST]
                self._port = user_input[CONF_PORT]
                self._info = info
                return await self.async_step_lines()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_lines(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick which auto-detected DALI lines to manage."""
        assert self._info is not None
        line_count = self._info.lines

        if user_input is not None:
            selected = [int(line) for line in user_input[CONF_LINES]]
            return self.async_create_entry(
                title=f"{self._info.name or DEFAULT_NAME} ({self._host})",
                data={CONF_HOST: self._host, CONF_PORT: self._port},
                options={
                    CONF_LINES: selected,
                    CONF_POLLING_INTERVAL: DEFAULT_POLLING_INTERVAL,
                    CONF_ENABLE_GLOBAL_BROADCAST: False,
                },
            )

        options = _line_options(line_count)
        return self.async_show_form(
            step_id="lines",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LINES, default=list(options)
                    ): cv.multi_select(options),
                }
            ),
            description_placeholders={
                "line_count": str(line_count),
                "gateway": self._info.name,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options: managed lines, polling interval, global broadcast entity."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            user_input[CONF_LINES] = [int(line) for line in user_input[CONF_LINES]]
            return self.async_create_entry(title="", data=user_input)

        line_count = await self._async_line_count()
        options = _line_options(line_count)
        current_lines = [
            str(line)
            for line in self.config_entry.options.get(CONF_LINES, list(range(line_count)))
            if int(line) < line_count
        ] or list(options)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LINES, default=current_lines): cv.multi_select(
                        options
                    ),
                    vol.Optional(
                        CONF_POLLING_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_POLLING_INTERVAL, max=MAX_POLLING_INTERVAL),
                    ),
                    vol.Optional(
                        CONF_ENABLE_GLOBAL_BROADCAST,
                        default=self.config_entry.options.get(
                            CONF_ENABLE_GLOBAL_BROADCAST, False
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_TRACK_INPUTS,
                        default=self.config_entry.options.get(
                            CONF_TRACK_INPUTS, True
                        ),
                    ): bool,
                }
            ),
        )

    async def _async_line_count(self) -> int:
        """Line count from the running coordinator, or freshly from the API."""
        entry_data = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if entry_data:
            coordinator = entry_data.get("coordinator")
            if coordinator and coordinator.info:
                return coordinator.info.lines
        try:
            info = await _fetch_gateway_info(
                self.hass,
                self.config_entry.data[CONF_HOST],
                self.config_entry.data[CONF_PORT],
            )
            return info.lines
        except CannotConnect:
            # offline: offer at least the currently configured lines
            configured = self.config_entry.options.get(CONF_LINES) or [0]
            return max(int(line) for line in configured) + 1


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
