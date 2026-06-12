"""Tests for the line-aware data models, using real gateway fixtures."""

from custom_components.lunatone_dali2_iot4.models import (
    GatewayInfo,
    LunatoneData,
    LunatoneDevice,
)


def test_device_from_api_maps_line_and_address(gw_devices):
    dev = LunatoneDevice.from_api(gw_devices["devices"][0])
    assert dev.gw_id == 1
    assert dev.line == 0
    assert dev.address == 20
    assert dev.name == "Line 0 - DALI#20"
    assert dev.available is True
    assert dev.groups == [0, 1, 4]
    assert dev.is_on is False
    assert dev.brightness_pct == 0.0
    assert dev.supports_dimming is True
    assert dev.supports_color_temp is False
    assert dev.color_temp_kelvin is None
    assert dev.lamp_failure is False


def test_device_color_temp_feature_detection():
    """Color temp must be detected from features, not DALI device type."""
    data = {
        "id": 99,
        "name": "DT8 lamp",
        "type": "default",
        "available": True,
        "status": {"lampOn": True, "lampFailure": False},
        "features": {
            "switchable": {"status": True},
            "dimmable": {"status": 80.0},
            "colorKelvin": {"status": 3500.0},
        },
        "groups": [],
        "address": 5,
        "line": 3,
        "daliTypes": [6, 8],
    }
    dev = LunatoneDevice.from_api(data)
    assert dev.supports_color_temp is True
    assert dev.color_temp_kelvin == 3500
    assert dev.is_on is True
    assert dev.brightness_pct == 80.0
    assert dev.line == 3


def test_device_switch_only():
    data = {
        "id": 7,
        "name": "relay",
        "available": True,
        "status": {},
        "features": {"switchable": {"status": True}},
        "groups": [],
        "address": 1,
        "line": 2,
    }
    dev = LunatoneDevice.from_api(data)
    assert dev.supports_dimming is False
    assert dev.is_on is True
    assert dev.brightness_pct is None


def test_gateway_info_from_api(gw_info):
    info = GatewayInfo.from_api(gw_info)
    assert info.name == "lunatone-gw"
    assert info.version == "v1.18.1/3.8.7"
    assert info.lines == 4
    assert info.serial == 249108113225
    assert info.uid == "67329271-edda-4bc1-9213-7416fbe99120"
    assert info.line_status[0] == "ok"


def test_gateway_info_defaults_single_line():
    """Old single-line DALI-2 IoT gateways may not report descriptor.lines."""
    info = GatewayInfo.from_api({"name": "gw", "version": "v1.14.1", "device": {}})
    assert info.lines == 1


def test_data_indexes_all_51_devices(gw_info, gw_devices):
    data = LunatoneData.from_api(gw_info, gw_devices["devices"])
    assert len(data.devices) == 51
    # address collisions across lines must stay separate
    per_line = {}
    for dev in data.devices.values():
        per_line.setdefault(dev.line, 0)
        per_line[dev.line] += 1
    assert per_line == {0: 19, 1: 18, 2: 14}
    # same DALI address on different lines resolves to different devices
    d0 = data.device_by_line_addr(0, 20)
    d2 = data.device_by_line_addr(2, 20)
    assert d0 is not None and d2 is not None
    assert d0.gw_id != d2.gw_id
    assert d0.gw_id == 1 and d2.gw_id == 24


def test_groups_are_split_per_line(gw_info, gw_devices):
    data = LunatoneData.from_api(gw_info, gw_devices["devices"])
    groups = data.groups_with_members()
    assert set(g for (line, g) in groups if line == 0) == {0, 1, 2, 3, 4}
    assert set(g for (line, g) in groups if line == 1) == {0, 1, 2, 3, 4, 5, 6}
    assert set(g for (line, g) in groups if line == 2) == {0}
    # group 0 on line 0 and group 0 on line 2 contain different devices
    assert groups[(0, 0)] != groups[(2, 0)]
    # 5 + 7 + 1 distinct (line, group) entities
    assert len(groups) == 13


def test_line_filter(gw_info, gw_devices):
    data = LunatoneData.from_api(gw_info, gw_devices["devices"], lines={0, 2})
    lines_present = {dev.line for dev in data.devices.values()}
    assert lines_present == {0, 2}
    assert len(data.devices) == 33
    assert all(line in (0, 2) for (line, _g) in data.groups_with_members())


def test_lines_with_devices(gw_info, gw_devices):
    data = LunatoneData.from_api(gw_info, gw_devices["devices"])
    assert data.lines_with_devices() == [0, 1, 2]
