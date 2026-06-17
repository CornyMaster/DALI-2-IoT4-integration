"""Number platform: the fixed value + fade time for the turn-on behavior.

Per dimmable lamp/group/broadcast line two ``number.*`` entities accompany the
``select`` ("turn-on behavior"):

* "Turn-on brightness" (%) – the level used when the select is on "Fixed value".
* "Turn-on fade time" (s) – the fade applied to that fixed value (0 = none).

Both are CONFIG entities, grouped under the light's device, and restored across
restarts via ``RestoreEntity``. They are always kept; they only take effect when
the select is set to "Fixed value".
"""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import LunatoneCoordinator
from .turn_on_entity import TurnOnConfigEntity, TurnOnTarget, discover_targets

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up turn-on brightness/fade numbers, including later targets."""
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
                LunatoneTurnOnLevelNumber(coordinator, entry, target)
            )
            new_entities.append(
                LunatoneTurnOnFadeNumber(coordinator, entry, target)
            )
        if new_entities:
            _LOGGER.debug("Adding %d turn-on numbers", len(new_entities))
            async_add_entities(new_entities)

    _async_sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_sync_entities))


class LunatoneTurnOnLevelNumber(TurnOnConfigEntity, NumberEntity, RestoreEntity):
    """Fixed brightness (%) used when the turn-on behavior is "Fixed value"."""

    _attr_translation_key = "turn_on_level"
    _attr_icon = "mdi:brightness-percent"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        entry: ConfigEntry,
        target: TurnOnTarget,
    ) -> None:
        super().__init__(coordinator, entry, target)
        self._attr_unique_id = (
            f"{entry.entry_id}_{target.unique_suffix}_turn_on_level"
        )
        self._attr_name = "Turn-on brightness"

    @property
    def native_value(self) -> float:
        return self._pref.fixed_pct

    async def async_set_native_value(self, value: float) -> None:
        self._store.set_fixed(self._target.key, value)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            try:
                self._store.set_fixed(self._target.key, float(last_state.state))
            except (TypeError, ValueError):
                pass


class LunatoneTurnOnFadeNumber(TurnOnConfigEntity, NumberEntity, RestoreEntity):
    """Fade time (s) applied to the fixed turn-on value (0 = no fade)."""

    _attr_translation_key = "turn_on_fade"
    _attr_icon = "mdi:transition"
    _attr_native_min_value = 0
    _attr_native_max_value = 600
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        entry: ConfigEntry,
        target: TurnOnTarget,
    ) -> None:
        super().__init__(coordinator, entry, target)
        self._attr_unique_id = (
            f"{entry.entry_id}_{target.unique_suffix}_turn_on_fade"
        )
        self._attr_name = "Turn-on fade time"

    @property
    def native_value(self) -> float:
        return self._pref.fixed_fade

    async def async_set_native_value(self, value: float) -> None:
        self._store.set_fixed_fade(self._target.key, value)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            try:
                self._store.set_fixed_fade(self._target.key, float(last_state.state))
            except (TypeError, ValueError):
                pass
