"""Turn-on brightness/fade numbers: defaults, ranges and read path."""

import pytest

pytest.importorskip("homeassistant")

from custom_components.lunatone_dali2_iot4.number import (  # noqa: E402
    LunatoneTurnOnFadeNumber,
    LunatoneTurnOnLevelNumber,
)
from custom_components.lunatone_dali2_iot4.turn_on import (  # noqa: E402
    turn_on_key_group,
)
from custom_components.lunatone_dali2_iot4.turn_on_entity import (  # noqa: E402
    KIND_GROUP,
    TurnOnTarget,
)


def test_level_number_defaults_and_range(coordinator, config_entry):
    target = TurnOnTarget(KIND_GROUP, 2, 0)
    number = LunatoneTurnOnLevelNumber(coordinator, config_entry, target)
    assert number.native_value == 100.0  # default fixed value
    assert number.native_min_value == 0
    assert number.native_max_value == 100
    assert number.unique_id == f"{config_entry.entry_id}_line2_group0_turn_on_level"


def test_fade_number_defaults_and_range(coordinator, config_entry):
    target = TurnOnTarget(KIND_GROUP, 2, 0)
    number = LunatoneTurnOnFadeNumber(coordinator, config_entry, target)
    assert number.native_value == 0.0  # default: no fade
    assert number.native_min_value == 0
    assert number.native_max_value == 600
    assert number.unique_id == f"{config_entry.entry_id}_line2_group0_turn_on_fade"


def test_numbers_read_store(coordinator, config_entry):
    target = TurnOnTarget(KIND_GROUP, 2, 0)
    level = LunatoneTurnOnLevelNumber(coordinator, config_entry, target)
    fade = LunatoneTurnOnFadeNumber(coordinator, config_entry, target)
    coordinator.turn_on_store.set_fixed(turn_on_key_group(2, 0), 45.0)
    coordinator.turn_on_store.set_fixed_fade(turn_on_key_group(2, 0), 1.5)
    assert level.native_value == 45.0
    assert fade.native_value == 1.5
