"""Select platform: per-lamp/group "turn-on behavior".

One ``select.*`` per dimmable lamp, group and broadcast line lets the user pick
what happens when the light is switched on in HA without an explicit brightness:
go to the last active level, the maximum, or a fixed value (see
``number`` platform for the fixed value/fade). The choice is held on the
coordinator and restored across restarts via ``RestoreEntity``.
"""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import LunatoneCoordinator
from .turn_on import TURN_ON_OPTIONS
from .turn_on_entity import TurnOnConfigEntity, TurnOnTarget, discover_targets

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up turn-on behavior selects, including targets discovered later."""
    coordinator: LunatoneCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    known: set[str] = set()

    @callback
    def _async_sync_entities() -> None:
        new_entities = []
        for target in discover_targets(coordinator):
            if target.key in known:
                continue
            known.add(target.key)
            new_entities.append(
                LunatoneTurnOnModeSelect(coordinator, entry, target)
            )
        if new_entities:
            _LOGGER.debug("Adding %d turn-on selects", len(new_entities))
            async_add_entities(new_entities)

    _async_sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_sync_entities))


class LunatoneTurnOnModeSelect(TurnOnConfigEntity, SelectEntity, RestoreEntity):
    """Dropdown choosing how a target switches on without a brightness."""

    _attr_translation_key = "turn_on_mode"
    _attr_icon = "mdi:lightbulb-on-outline"
    _attr_options = TURN_ON_OPTIONS

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        entry: ConfigEntry,
        target: TurnOnTarget,
    ) -> None:
        super().__init__(coordinator, entry, target)
        self._attr_unique_id = (
            f"{entry.entry_id}_{target.unique_suffix}_turn_on_mode"
        )
        self._attr_name = "Turn-on behavior"

    @property
    def current_option(self) -> str:
        return self._pref.mode

    async def async_select_option(self, option: str) -> None:
        self._store.set_mode(self._target.key, option)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state in TURN_ON_OPTIONS:
            self._store.set_mode(self._target.key, last_state.state)
