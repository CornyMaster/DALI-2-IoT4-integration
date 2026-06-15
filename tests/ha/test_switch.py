"""Scene switch tests: per-line scene recall switches."""

import pytest

pytest.importorskip("homeassistant")

from yarl import URL  # noqa: E402

from custom_components.lunatone_dali2_iot4.switch import (  # noqa: E402
    LunatoneSceneSwitch,
)

from .conftest import BASE  # noqa: E402


def _configure_scene(coordinator, gw_id, scene, pct=33.0):
    """Pretend a device has a stored value for a scene."""
    coordinator._scenes[gw_id] = {scene: {"dimmable": pct}}


async def test_no_scene_switches_when_unconfigured(coordinator):
    # the mock gateway stores no scenes (all null)
    assert coordinator.configured_scenes() == set()


async def test_configured_scene_detected_on_its_line(coordinator):
    # gw_id 1 is on line 0, gw_id 24 is on line 2
    _configure_scene(coordinator, 1, 0)
    _configure_scene(coordinator, 24, 5)
    configured = coordinator.configured_scenes()
    assert (0, 0) in configured
    assert (2, 5) in configured
    assert (0, 5) not in configured


async def test_scene_switch_identity(coordinator, config_entry):
    sw = LunatoneSceneSwitch(coordinator, config_entry, 0, 3)
    assert sw.unique_id == f"{config_entry.entry_id}_line0_scene3"
    assert sw.device_info["identifiers"] == {
        ("lunatone_dali2_iot4", f"{config_entry.entry_id}_line0_scene3")
    }
    assert sw.device_info["name"] == "DALI Line 0 Scene 3"
    assert sw.is_on is False


async def test_scene_switch_turn_on_broadcasts_scene(
    hass, coordinator, config_entry, mock_gateway
):
    mock_gateway.post(f"{BASE}/broadcast/control?_line=0", payload={})
    sw = LunatoneSceneSwitch(coordinator, config_entry, 0, 3)
    sw.hass = hass
    sw.entity_id = "switch.dali_line0_scene3"
    await sw.async_turn_on()

    key = ("POST", URL(f"{BASE}/broadcast/control?_line=0"))
    assert key in mock_gateway.requests
    assert mock_gateway.requests[key][0].kwargs["json"] == {"scene": 3}
    assert sw.is_on is True

    await sw.async_turn_off()
    assert sw.is_on is False  # optimistic only, no bus action
