"""Button platform for the Lunatone DALI-2 IoT integration."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import LunatoneApiError
from .blueprints_deploy import async_deploy_switch_manager_blueprints
from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import LunatoneCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lunatone button entities."""
    coordinator: LunatoneCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        DATA_COORDINATOR
    ]
    buttons: list[ButtonEntity] = [GatewayScanButton(coordinator, config_entry)]
    if coordinator.track_inputs:
        buttons.append(RefreshInputNamesButton(coordinator, config_entry))
    buttons.append(DeployBlueprintsButton(config_entry))
    buttons.append(DeployBlueprintsButton(config_entry, force=True))
    async_add_entities(buttons)


class GatewayScanButton(ButtonEntity):
    """Triggers the gateway's own (non-destructive) device scan."""

    _attr_name = "Scan for devices"
    _attr_icon = "mdi:magnify-scan"

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{config_entry.entry_id}_manual_scan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
        )

    async def async_press(self) -> None:
        _LOGGER.info("Starting gateway device scan (no re-addressing)")
        try:
            await self._coordinator.client.async_start_scan()
        except LunatoneApiError as err:
            _LOGGER.error("Gateway scan failed to start: %s", err)
            return
        await self._coordinator.async_request_refresh()
        # Pick up scenes configured since startup -> new scene entities.
        await self._coordinator.async_refresh_all_scenes()


class RefreshInputNamesButton(ButtonEntity):
    """Re-reads the names of all known DALI-2 input devices from the bus.

    Note: this does not discover new switches — DALI-2 input devices are only
    found when physically pressed (the gateway scan finds control gear only).
    It repairs names that were stored garbled or truncated.
    """

    _attr_name = "Refresh input names"
    _attr_icon = "mdi:rename-box"

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{config_entry.entry_id}_refresh_input_names"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
        )

    async def async_press(self) -> None:
        await self._coordinator.async_refresh_input_names()


class DeployBlueprintsButton(ButtonEntity):
    """Deploy bundled Switch Manager blueprints.

    Default keeps user-edited files (only updates missing or known-old bundled
    copies); the force variant overwrites the deployed copies unconditionally.
    """

    _attr_icon = "mdi:file-export"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, config_entry: ConfigEntry, force: bool = False) -> None:
        self._force = force
        suffix = "deploy_blueprints_force" if force else "deploy_blueprints"
        self._attr_name = (
            "Deploy Switch Manager Blueprints (Force)"
            if force
            else "Deploy Switch Manager Blueprints"
        )
        self._attr_unique_id = f"{config_entry.entry_id}_{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
        )

    async def async_press(self) -> None:
        n = await async_deploy_switch_manager_blueprints(self.hass, force=self._force)
        if n < 0:
            _LOGGER.warning("Switch Manager not installed; nothing deployed")
        else:
            _LOGGER.info("Deployed %d Switch Manager blueprint file(s)", n)
