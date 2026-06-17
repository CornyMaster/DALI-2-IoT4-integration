"""Turn-on behavior select: discovery, device merge and read path."""

import pytest

pytest.importorskip("homeassistant")

from homeassistant.helpers.entity import EntityCategory  # noqa: E402

from custom_components.lunatone_dali2_iot4.light import (  # noqa: E402
    LunatoneDeviceLight,
)
from custom_components.lunatone_dali2_iot4.select import (  # noqa: E402
    LunatoneTurnOnModeSelect,
)
from custom_components.lunatone_dali2_iot4.turn_on import (  # noqa: E402
    OPTION_LAST_ACTIVE,
    OPTION_MAXIMUM,
    TURN_ON_OPTIONS,
    turn_on_key_device,
)
from custom_components.lunatone_dali2_iot4.turn_on_entity import (  # noqa: E402
    KIND_BROADCAST,
    KIND_DEVICE,
    KIND_GROUP,
    TurnOnTarget,
    discover_targets,
)


def test_discovery_covers_devices_groups_and_broadcast(coordinator):
    targets = discover_targets(coordinator)
    keys = [t.key for t in targets]
    assert len(keys) == len(set(keys))  # all unique

    dimmable = [d for d in coordinator.data.devices.values() if d.supports_dimming]
    device_targets = [t for t in targets if t.kind == KIND_DEVICE]
    assert len(device_targets) == len(dimmable)

    assert any(t.kind == KIND_GROUP for t in targets)
    # one broadcast target per line that has devices
    broadcast_lines = {t.line for t in targets if t.kind == KIND_BROADCAST}
    assert broadcast_lines == set(coordinator.data.lines_with_devices())


def test_select_defaults_and_options(coordinator, config_entry):
    target = TurnOnTarget(KIND_DEVICE, 2, 20)
    select = LunatoneTurnOnModeSelect(coordinator, config_entry, target)
    assert select.options == TURN_ON_OPTIONS
    assert select.current_option == OPTION_LAST_ACTIVE
    assert select.entity_category == EntityCategory.CONFIG
    assert select.unique_id == f"{config_entry.entry_id}_line2_dali_20_turn_on_mode"


def test_select_reads_store(coordinator, config_entry):
    target = TurnOnTarget(KIND_DEVICE, 2, 20)
    select = LunatoneTurnOnModeSelect(coordinator, config_entry, target)
    coordinator.turn_on_store.set_mode(turn_on_key_device(2, 20), OPTION_MAXIMUM)
    assert select.current_option == OPTION_MAXIMUM


def test_select_shares_device_with_its_light(coordinator, config_entry):
    target = TurnOnTarget(KIND_DEVICE, 2, 20)
    select = LunatoneTurnOnModeSelect(coordinator, config_entry, target)
    light = LunatoneDeviceLight(coordinator, config_entry, 2, 20)
    assert select.device_info["identifiers"] == light.device_info["identifiers"]
