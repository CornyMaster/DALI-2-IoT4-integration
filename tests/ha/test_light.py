"""Light entity tests: unique ids, aggregation and line-aware control."""

import pytest

pytest.importorskip("homeassistant")

from yarl import URL  # noqa: E402

from custom_components.lunatone_dali2_iot4.light import (  # noqa: E402
    LunatoneBroadcastLight,
    LunatoneDeviceLight,
    LunatoneGroupLight,
)

from .conftest import BASE  # noqa: E402


async def test_device_lights_have_line_aware_unique_ids(coordinator, config_entry):
    light_l0 = LunatoneDeviceLight(coordinator, config_entry, 0, 20)
    light_l2 = LunatoneDeviceLight(coordinator, config_entry, 2, 20)
    assert light_l0.unique_id == f"{config_entry.entry_id}_line0_dali_20"
    assert light_l2.unique_id == f"{config_entry.entry_id}_line2_dali_20"
    assert light_l0.unique_id != light_l2.unique_id
    # names come from the gateway
    assert light_l0.name == "Line 0 - DALI#20"
    assert light_l2.name == "Line 2 - DALI#20"
    # both resolve to different gateway ids
    assert light_l0.extra_state_attributes["gateway_device_id"] == 1
    assert light_l2.extra_state_attributes["gateway_device_id"] == 24


async def test_all_51_devices_have_unique_entity_ids(coordinator, config_entry):
    unique_ids = {
        LunatoneDeviceLight(coordinator, config_entry, d.line, d.address).unique_id
        for d in coordinator.data.devices.values()
    }
    assert len(unique_ids) == 51


async def test_device_turn_on_posts_to_gateway_id(coordinator, config_entry, mock_gateway):
    mock_gateway.post(f"{BASE}/device/24/control", payload={})
    light = LunatoneDeviceLight(coordinator, config_entry, 2, 20)
    await light.async_turn_on()
    request = mock_gateway.requests[("POST", URL(f"{BASE}/device/24/control"))][0]
    assert request.kwargs["json"] == {"switchable": True}


async def test_device_brightness_conversion(coordinator, config_entry, mock_gateway):
    mock_gateway.post(f"{BASE}/device/1/control", payload={})
    light = LunatoneDeviceLight(coordinator, config_entry, 0, 20)
    await light.async_turn_on(brightness=128)
    request = mock_gateway.requests[("POST", URL(f"{BASE}/device/1/control"))][0]
    assert request.kwargs["json"] == {"dimmable": 50}
    assert light.brightness == round(50 / 100 * 255)


async def test_group_light_per_line(coordinator, config_entry, mock_gateway):
    group_l0 = LunatoneGroupLight(coordinator, config_entry, 0, 0)
    group_l2 = LunatoneGroupLight(coordinator, config_entry, 2, 0)
    assert group_l0.unique_id == f"{config_entry.entry_id}_line0_group0"
    assert group_l2.unique_id == f"{config_entry.entry_id}_line2_group0"
    assert group_l0.name == "Line 0 Group 0"
    # member sets differ between lines (addresses 20-25 on line 0; all 14 on line 2)
    assert group_l0.extra_state_attributes["device_count"] == 6
    assert group_l2.extra_state_attributes["device_count"] == 14

    mock_gateway.post(f"{BASE}/group/0/control?_line=2", payload={})
    await group_l2.async_turn_on()
    key = ("POST", URL(f"{BASE}/group/0/control?_line=2"))
    assert key in mock_gateway.requests
    assert mock_gateway.requests[key][0].kwargs["json"] == {"switchable": True}


async def test_group_state_aggregates_members(coordinator, config_entry):
    group = LunatoneGroupLight(coordinator, config_entry, 0, 0)
    assert group.is_on is False
    coordinator.data.device_by_line_addr(0, 20).is_on = True
    coordinator.data.device_by_line_addr(0, 20).brightness_pct = 40.0
    assert group.is_on is True
    assert group.brightness == round(40 / 100 * 255)


async def test_broadcast_per_line_and_global(coordinator, config_entry, mock_gateway):
    line_broadcast = LunatoneBroadcastLight(coordinator, config_entry, 1)
    global_broadcast = LunatoneBroadcastLight(coordinator, config_entry, None)
    assert line_broadcast.unique_id == f"{config_entry.entry_id}_line1_broadcast"
    assert global_broadcast.unique_id == f"{config_entry.entry_id}_broadcast_all"

    mock_gateway.post(f"{BASE}/broadcast/control?_line=1", payload={})
    await line_broadcast.async_turn_off()
    assert ("POST", URL(f"{BASE}/broadcast/control?_line=1")) in mock_gateway.requests

    mock_gateway.post(f"{BASE}/broadcast/control", payload={})
    await global_broadcast.async_turn_off()
    assert ("POST", URL(f"{BASE}/broadcast/control")) in mock_gateway.requests
