"""Scene platform: DALI scenes as native Home Assistant scenes.

Each (line, scene) becomes a HA ``scene.*`` entity on its own device
"DALI Line X Scene Y". Activating it (scene.turn_on, dashboard, automation)
recalls the DALI scene on the whole line via a single broadcast. A scene
appears as soon as at least one lamp on that line has a stored value for it;
the member lamps and their levels are exposed as attributes.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    """Set up DALI scene entities, including scenes configured later."""
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
            new_entities.append(LunatoneScene(coordinator, entry, line, scene))
        if new_entities:
            _LOGGER.debug("Adding %d DALI scene entities", len(new_entities))
            async_add_entities(new_entities)

    _async_sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_sync_entities))


class LunatoneScene(Scene):
    """One DALI scene on one line, recalled via a line broadcast."""

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
        self._coordinator = coordinator
        self._line = line
        self._scene = scene
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
        members = self._coordinator.scene_members(self._line, self._scene)
        return {
            "line": self._line,
            "scene": self._scene,
            "members": members,
            "member_count": len(members),
        }

    async def async_activate(self, **kwargs: Any) -> None:
        """Recall the DALI scene on the whole line (broadcast)."""
        await self._coordinator.async_control_broadcast(
            scene_control(self._scene), line=self._line
        )
