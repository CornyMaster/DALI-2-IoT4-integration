"""The Lunatone DALI-2 IoT(4) integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LunatoneApiError, LunatoneRestClient
from .const import (
    CONF_HOST,
    CONF_PORT,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DATA_WS_LISTENER,
    DEFAULT_PORT,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import LunatoneCoordinator
from .websocket import LunatoneWsListener

_LOGGER = logging.getLogger(__name__)

SERVICE_RESCAN = "rescan_devices"
SERVICE_SET_FEEDBACK_LED = "set_feedback_led"

SET_FEEDBACK_LED_SCHEMA = vol.Schema(
    {
        vol.Required("line"): vol.All(vol.Coerce(int), vol.Range(min=0, max=15)),
        vol.Required("address"): vol.All(vol.Coerce(int), vol.Range(min=0, max=63)),
        vol.Required("instance"): vol.All(vol.Coerce(int), vol.Range(min=0, max=31)),
        vol.Required("state"): cv.boolean,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lunatone DALI-2 IoT from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)

    session = async_get_clientsession(hass)
    client = LunatoneRestClient(session, host, port)

    try:
        await client.async_get_info()
    except LunatoneApiError as err:
        raise ConfigEntryNotReady(
            f"Unable to reach Lunatone gateway at {host}:{port}: {err}"
        ) from err

    coordinator = LunatoneCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    # Websocket is push-only icing; polling still works if it never connects.
    ws_listener = LunatoneWsListener(
        session,
        host,
        port,
        on_input_event=coordinator.handle_ws_input_event,
        on_devices_update=coordinator.handle_ws_devices_update,
    )
    await ws_listener.async_start()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_CLIENT: client,
        DATA_COORDINATOR: coordinator,
        DATA_WS_LISTENER: ws_listener,
    }

    info = coordinator.info
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Lunatone",
        model=f"DALI-2 IoT Gateway ({info.lines} lines)" if info else "DALI-2 IoT Gateway",
        sw_version=info.version if info else None,
        serial_number=str(info.serial) if info and info.serial else None,
        configuration_url=client.base_url,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    async def handle_rescan_devices(call: ServiceCall) -> None:
        """Trigger the gateway's own scan (never re-addresses the bus)."""
        _LOGGER.info("Starting gateway device scan")
        await client.async_start_scan()
        await coordinator.async_request_refresh()

    async def handle_set_feedback_led(call: ServiceCall) -> None:
        await coordinator.async_set_feedback_led(
            call.data["line"],
            call.data["address"],
            call.data["instance"],
            call.data["state"],
        )

    if not hass.services.has_service(DOMAIN, SERVICE_RESCAN):
        hass.services.async_register(DOMAIN, SERVICE_RESCAN, handle_rescan_devices)
    if not hass.services.has_service(DOMAIN, SERVICE_SET_FEEDBACK_LED):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_FEEDBACK_LED,
            handle_set_feedback_led,
            schema=SET_FEEDBACK_LED_SCHEMA,
        )

    _LOGGER.info(
        "Lunatone setup complete for %s: %d devices on lines %s",
        host,
        len(coordinator.data.devices),
        coordinator.data.lines_with_devices(),
    )
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries to version 2 (REST-based, line-aware)."""
    if entry.version > 2:
        return False
    if entry.version < 2:
        # v1 options (background polling / scan-on-startup) are obsolete;
        # line selection and the new defaults come from the options flow.
        hass.config_entries.async_update_entry(entry, options={}, version=2)
        _LOGGER.info("Migrated config entry %s to version 2", entry.entry_id)
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        ws_listener: LunatoneWsListener = data[DATA_WS_LISTENER]
        await ws_listener.async_stop()
    return unload_ok
