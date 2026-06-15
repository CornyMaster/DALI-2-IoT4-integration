"""Coordinator tests against a mocked gateway in a real HA test instance."""

import pytest

pytest.importorskip("homeassistant")

from homeassistant.helpers.aiohttp_client import async_get_clientsession  # noqa: E402
from pytest_homeassistant_custom_component.common import (  # noqa: E402
    MockConfigEntry,
    async_capture_events,
)

from custom_components.lunatone_dali2_iot4.api import LunatoneRestClient  # noqa: E402
from custom_components.lunatone_dali2_iot4.const import (  # noqa: E402
    CONF_HOST,
    CONF_LINES,
    CONF_TRACK_INPUTS,
    CONF_PORT,
    DALI_EVENT,
    DOMAIN,
)
from custom_components.lunatone_dali2_iot4.coordinator import LunatoneCoordinator  # noqa: E402
from custom_components.lunatone_dali2_iot4.websocket import InputEvent  # noqa: E402

from .conftest import BASE, HOST  # noqa: E402


async def test_first_refresh_builds_line_aware_inventory(coordinator):
    data = coordinator.data
    assert len(data.devices) == 51
    assert data.info.lines == 4
    # colliding addresses stay separate per line
    assert data.device_by_line_addr(0, 20).gw_id == 1
    assert data.device_by_line_addr(2, 20).gw_id == 24
    assert len(data.groups_with_members()) == 13


async def test_line_filter_from_options(hass, gw_info, gw_devices, mock_gateway):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PORT: 80},
        options={CONF_LINES: [0, 2]},
    )
    entry.add_to_hass(hass)
    client = LunatoneRestClient(async_get_clientsession(hass), HOST)
    coordinator = LunatoneCoordinator(hass, entry, client)
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert {device.line for device in coordinator.data.devices.values()} == {0, 2}
    assert len(coordinator.data.devices) == 33


async def test_ws_devices_push_merges_status(coordinator):
    device = coordinator.data.devices[1]
    assert device.is_on is False
    coordinator.handle_ws_devices_update(
        [{"id": 1, "features": {"dimmable": {"status": 75.0}}}]
    )
    assert device.brightness_pct == 75.0
    assert device.is_on is True


async def test_input_event_fires_line_aware_event(hass, coordinator):
    events = async_capture_events(hass, DALI_EVENT)
    coordinator.handle_ws_input_event(
        InputEvent(line=2, address=5, instance=1, event_data=2)  # short_press
    )

    assert len(events) == 1
    payload = events[0].data
    assert payload["line"] == 2
    assert payload["device_address"] == 5
    assert payload["instance"] == 1
    assert payload["type"] == "short_press"

    # input device was registered under its line-aware key; short_press is an
    # active event until the momentary auto-reset task has run
    input_device = coordinator.data.inputs[(2, 5)]
    instance = input_device.instances[1]
    assert instance.state is True

    # block_till_done waits out the 0.5s momentary reset task
    await hass.async_block_till_done()
    assert instance.state is False


async def test_new_input_device_is_named_from_description(hass, coordinator):
    from unittest.mock import AsyncMock

    coordinator.client.async_read_input_device_description = AsyncMock(
        return_value="Schalter_Küche_L"
    )
    coordinator.handle_ws_input_event(InputEvent(0, 0, 1, 2))
    await hass.async_block_till_done()

    device = coordinator.data.inputs[(0, 0)]
    assert device.name == "Schalter_Küche_L"
    coordinator.client.async_read_input_device_description.assert_awaited_once_with(0, 0)


async def test_input_device_keeps_default_name_without_description(hass, coordinator):
    from unittest.mock import AsyncMock

    coordinator.client.async_read_input_device_description = AsyncMock(
        return_value=None
    )
    coordinator.handle_ws_input_event(InputEvent(3, 7, 0, 1))
    await hass.async_block_till_done()
    assert coordinator.data.inputs[(3, 7)].name == "Line 3 Input 7"


async def test_refresh_input_names_repairs_persisted_name(hass, coordinator):
    """A previously corrupt/truncated name is re-read and overwritten."""
    from unittest.mock import AsyncMock

    coordinator.client.async_read_input_device_description = AsyncMock(
        return_value="Schalter_Wohnzimme"  # earlier truncated read, now persisted
    )
    coordinator.handle_ws_input_event(InputEvent(2, 0, 1, 2))
    await hass.async_block_till_done()
    assert coordinator.data.inputs[(2, 0)].name == "Schalter_Wohnzimme"

    coordinator.client.async_read_input_device_description = AsyncMock(
        return_value="Schalter_Wohnzimmer_O"  # bus quiet now, reads correctly
    )
    await coordinator.async_refresh_input_names()
    assert coordinator.data.inputs[(2, 0)].name == "Schalter_Wohnzimmer_O"
    coordinator.client.async_read_input_device_description.assert_awaited_with(2, 0)


async def test_refresh_all_scenes_picks_up_new_scene(coordinator):
    """A scene configured after startup is detected on a rescan refresh."""
    from unittest.mock import AsyncMock

    async def fake_scenes(gw_id):
        base = {str(s): {"dimmable": None} for s in range(16)}
        if gw_id == 24:  # device 24 is on line 2
            base["5"] = {"dimmable": 50.0}
        return base

    assert (2, 5) not in coordinator.configured_scenes()
    coordinator.client.async_get_device_scenes = AsyncMock(side_effect=fake_scenes)
    await coordinator.async_refresh_all_scenes()
    assert (2, 5) in coordinator.configured_scenes()


async def test_same_address_on_two_lines_are_distinct_inputs(hass, coordinator):
    coordinator.handle_ws_input_event(InputEvent(0, 5, 0, 1))
    coordinator.handle_ws_input_event(InputEvent(3, 5, 0, 1))
    await hass.async_block_till_done()
    assert (0, 5) in coordinator.data.inputs
    assert (3, 5) in coordinator.data.inputs


async def test_input_event_outside_line_filter_is_ignored(hass, gw_devices, mock_gateway):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PORT: 80},
        options={CONF_LINES: [0]},
    )
    entry.add_to_hass(hass)
    client = LunatoneRestClient(async_get_clientsession(hass), HOST)
    coordinator = LunatoneCoordinator(hass, entry, client)
    await coordinator.async_refresh()
    assert coordinator.last_update_success

    coordinator.handle_ws_input_event(InputEvent(1, 5, 0, 1))
    await hass.async_block_till_done()
    assert (1, 5) not in coordinator.data.inputs


async def test_input_tracking_can_be_disabled(hass, gw_devices, mock_gateway):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PORT: 80},
        options={CONF_TRACK_INPUTS: False},
    )
    entry.add_to_hass(hass)
    client = LunatoneRestClient(async_get_clientsession(hass), HOST)
    coordinator = LunatoneCoordinator(hass, entry, client)
    await coordinator.async_refresh()
    assert coordinator.last_update_success

    coordinator.handle_ws_input_event(InputEvent(0, 5, 0, 1))
    await hass.async_block_till_done()
    assert coordinator.data.inputs == {}


async def test_scene_values_are_loaded_and_refreshed(coordinator, mock_gateway):
    from unittest.mock import AsyncMock

    # initial fetch found no stored scenes (all dimmable null)
    assert coordinator.data.devices[1].scenes == {}
    # after a write, the device's scenes are re-read
    mock_gateway.post(f"{BASE}/device/1/scenes", payload={})
    coordinator.client.async_get_device_scenes = AsyncMock(
        return_value={"0": {"dimmable": 80.0}, "1": {"dimmable": None}}
    )
    assert await coordinator.async_set_scene_level(1, 0, 80.0) is True
    assert coordinator.data.devices[1].scenes == {0: {"dimmable": 80.0}}
    # the write went to POST /device/1/scenes with a partial update
    key = ("POST", _url(f"{BASE}/device/1/scenes"))
    assert mock_gateway.requests[key][0].kwargs["json"] == {
        "0": {"dimmable": 80.0}
    }


async def test_device_control_uses_gateway_id(coordinator, mock_gateway):
    mock_gateway.post(f"{BASE}/device/24/control", payload={})
    # device 24 == line 2, address 20
    assert await coordinator.async_set_brightness(24, 50) is True
    assert coordinator.data.devices[24].brightness_pct == 50
    assert coordinator.data.devices[24].is_on is True
    request = mock_gateway.requests[("POST", _url(f"{BASE}/device/24/control"))][0]
    assert request.kwargs["json"] == {"dimmable": 50}


async def test_group_control_targets_single_line(coordinator, mock_gateway):
    mock_gateway.post(f"{BASE}/group/0/control?_line=2", payload={})
    assert await coordinator.async_control_group(2, 0, {"switchable": True}) is True
    # only line-2 members of group 0 got the optimistic update
    line2_members = [
        device
        for device in coordinator.data.devices.values()
        if device.line == 2 and 0 in device.groups
    ]
    line0_members = [
        device
        for device in coordinator.data.devices.values()
        if device.line == 0 and 0 in device.groups
    ]
    assert line2_members and all(device.is_on for device in line2_members)
    assert line0_members and not any(device.is_on for device in line0_members)


def _url(url: str):
    from yarl import URL

    return URL(url)
