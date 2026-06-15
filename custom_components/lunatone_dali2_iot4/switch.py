"""Switch platform: DALI scenes as per-line recall switches.

One switch per (line, scene), each on its own device "DALI Line X Scene Y".
A scene switch appears as soon as at least one device on that line has a
stored value for the scene (so empty scenes do not clutter the UI). Turning
it on recalls the scene on the whole line via a broadcast; the state is purely
optimistic because the DALI bus has no "active scene" feedback.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import (
    LunatoneCoordinator,
    scene_control,
    scene_device_identifier,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DALI scene switches, including scenes configured later."""
    coordinator: LunatoneCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    known: set[tuple[int, int]] = set()

    @callback
    def _async_sync_entities() -> None:
        if not coordinator.data:
            return
        new_entities = []
        for line, scene in sorted(coordinator.configured_scenes()):
            if (line, scene) in known:
                continue
            known.add((line, scene))
            new_entities.append(LunatoneSceneSwitch(coordinator, entry, line, scene))
        if new_entities:
            _LOGGER.debug("Adding %d DALI scene switches", len(new_entities))
            async_add_entities(new_entities)

    _async_sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_sync_entities))


class LunatoneSceneSwitch(CoordinatorEntity[LunatoneCoordinator], SwitchEntity):
    """Recall one DALI scene on one line (optimistic, independent trigger)."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:palette"

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        entry: ConfigEntry,
        line: int,
        scene: int,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._line = line
        self._scene = scene
        self._attr_is_on = False
        self._attr_unique_id = f"{entry.entry_id}_line{line}_scene{scene}"
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, scene_device_identifier(entry.entry_id, line, scene))
            },
            name=f"DALI Line {line} Scene {scene}",
            model="DALI Scene",
            manufacturer="Lunatone",
            via_device=(DOMAIN, entry.entry_id),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"line": self._line, "scene": self._scene}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Recall the scene on the whole line (broadcast)."""
        await self.coordinator.async_control_broadcast(
            scene_control(self._scene), line=self._line
        )
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Clear the optimistic state; the bus has no scene deactivation."""
        self._attr_is_on = False
        self.async_write_ha_state()
