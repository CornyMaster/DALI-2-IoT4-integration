"""Button platform for the Lunatone DALI-2 IoT integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import LunatoneApiError
from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import (
    LunatoneCoordinator,
    scene_control,
    scene_device_identifier,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lunatone button entities (incl. scene buttons added later)."""
    coordinator: LunatoneCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        DATA_COORDINATOR
    ]
    buttons: list[ButtonEntity] = [GatewayScanButton(coordinator, config_entry)]
    if coordinator.track_inputs:
        buttons.append(RefreshInputNamesButton(coordinator, config_entry))
    async_add_entities(buttons)

    known_scenes: set[tuple[int, int]] = set()

    @callback
    def _async_sync_scene_buttons() -> None:
        if not coordinator.data:
            return
        new_buttons: list[ButtonEntity] = []
        for line, scene in sorted(coordinator.configured_scenes()):
            if (line, scene) in known_scenes:
                continue
            known_scenes.add((line, scene))
            new_buttons.append(
                LunatoneSceneButton(coordinator, config_entry, line, scene)
            )
        if new_buttons:
            _LOGGER.debug("Adding %d DALI scene buttons", len(new_buttons))
            async_add_entities(new_buttons)

    _async_sync_scene_buttons()
    config_entry.async_on_unload(
        coordinator.async_add_listener(_async_sync_scene_buttons)
    )


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
        # Pick up scenes configured since startup -> new scene switches.
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


class LunatoneSceneButton(ButtonEntity):
    """Recall one DALI scene on one line (single click), on its own device.

    Exposes the lamps that belong to the scene and their stored level as
    attributes, so it is visible what the scene does.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:palette"

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        config_entry: ConfigEntry,
        line: int,
        scene: int,
    ) -> None:
        self._coordinator = coordinator
        self._line = line
        self._scene = scene
        self._attr_unique_id = f"{config_entry.entry_id}_line{line}_scene{scene}"
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, scene_device_identifier(config_entry.entry_id, line, scene))
            },
            name=f"DALI Line {line} Scene {scene}",
            model="DALI Scene",
            manufacturer="Lunatone",
            via_device=(DOMAIN, config_entry.entry_id),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        members = self._coordinator.scene_members(self._line, self._scene)
        return {
            "line": self._line,
            "scene": self._scene,
            "members": members,
            "member_count": len(members),
        }

    async def async_press(self) -> None:
        await self._coordinator.async_control_broadcast(
            scene_control(self._scene), line=self._line
        )
