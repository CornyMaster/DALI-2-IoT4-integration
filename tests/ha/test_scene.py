"""Scene entity tests: DALI scenes as native HA scenes."""

import pytest

pytest.importorskip("homeassistant")

from yarl import URL  # noqa: E402

from custom_components.lunatone_dali2_iot4.scene import LunatoneScene  # noqa: E402

from .conftest import BASE  # noqa: E402


def _configure_scene(coordinator, gw_id, scene, pct=33.0):
    """Pretend a device has a stored value for a scene."""
    coordinator._scenes[gw_id] = {scene: {"dimmable": pct}}


async def test_no_scenes_when_unconfigured(coordinator):
    assert coordinator.configured_scenes() == set()


async def test_configured_scene_detected_on_its_line(coordinator):
    # gw_id 1 is on line 0, gw_id 24 is on line 2
    _configure_scene(coordinator, 1, 0)
    _configure_scene(coordinator, 24, 5)
    configured = coordinator.configured_scenes()
    assert (0, 0) in configured
    assert (2, 5) in configured
    assert (0, 5) not in configured


async def test_scene_identity(coordinator, config_entry):
    sc = LunatoneScene(coordinator, config_entry, 0, 3)
    assert sc.unique_id == f"{config_entry.entry_id}_line0_scene3"
    assert sc.device_info["identifiers"] == {
        ("lunatone_dali2_iot4", f"{config_entry.entry_id}_line0_scene3")
    }
    assert sc.device_info["name"] == "DALI Line 0 Scene 3"


async def test_scene_activate_broadcasts_scene(
    coordinator, config_entry, mock_gateway
):
    mock_gateway.post(f"{BASE}/broadcast/control?_line=0", payload={})
    sc = LunatoneScene(coordinator, config_entry, 0, 3)
    await sc.async_activate()

    key = ("POST", URL(f"{BASE}/broadcast/control?_line=0"))
    assert key in mock_gateway.requests
    assert mock_gateway.requests[key][0].kwargs["json"] == {"scene": 3}


async def test_scene_lists_members_and_levels(coordinator, config_entry):
    # device gw_id 1 is on line 0, address 20
    _configure_scene(coordinator, 1, 0, pct=33.0)
    sc = LunatoneScene(coordinator, config_entry, 0, 0)
    attrs = sc.extra_state_attributes
    assert attrs["member_count"] == 1
    member = attrs["members"][0]
    assert member["address"] == 20
    assert member["level"] == 33.0
