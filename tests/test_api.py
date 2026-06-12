"""Tests for the REST client (mocked HTTP; live gateway tests are marked)."""

import os

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.lunatone_dali2_iot4.api import (
    LunatoneApiError,
    LunatoneReadOnlyError,
    LunatoneRestClient,
)

HOST = "gw.example"
BASE = f"http://{HOST}"  # aiohttp normalizes the default port 80 away


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as sess:
        yield sess


@pytest.fixture
def client(session):
    return LunatoneRestClient(session, HOST)


async def test_get_info(client, gw_info):
    with aioresponses() as mock:
        mock.get(f"{BASE}/info", payload=gw_info)
        info = await client.async_get_info()
    assert info["descriptor"]["lines"] == 4


async def test_get_devices(client, gw_devices):
    with aioresponses() as mock:
        mock.get(f"{BASE}/devices", payload=gw_devices)
        devices = await client.async_get_devices()
    assert len(devices) == 51


async def test_get_sensors_empty(client):
    with aioresponses() as mock:
        mock.get(f"{BASE}/sensors", payload={"sensors": []})
        assert await client.async_get_sensors() == []


async def test_control_device_posts_to_unique_id(client):
    with aioresponses() as mock:
        mock.post(f"{BASE}/device/24/control", payload={})
        await client.async_control_device(24, {"dimmable": 50.0})
    key = list(mock.requests.keys())[0]
    assert str(key[1]) == f"{BASE}/device/24/control"
    request = mock.requests[key][0]
    assert request.kwargs["json"] == {"dimmable": 50.0}


async def test_control_group_includes_line_query(client):
    with aioresponses() as mock:
        mock.post(f"{BASE}/group/4/control?_line=1", payload={})
        await client.async_control_group(4, {"switchable": True}, line=1)
    key = list(mock.requests.keys())[0]
    assert str(key[1]) == f"{BASE}/group/4/control?_line=1"


async def test_control_group_without_line_hits_all_lines(client):
    with aioresponses() as mock:
        mock.post(f"{BASE}/group/0/control", payload={})
        await client.async_control_group(0, {"switchable": False})
    key = list(mock.requests.keys())[0]
    assert str(key[1]) == f"{BASE}/group/0/control"


async def test_control_broadcast_with_line(client):
    with aioresponses() as mock:
        mock.post(f"{BASE}/broadcast/control?_line=2", payload={})
        await client.async_control_broadcast({"dimmable": 0}, line=2)
    key = list(mock.requests.keys())[0]
    assert str(key[1]) == f"{BASE}/broadcast/control?_line=2"


async def test_send_dali24_uses_line_path(client):
    with aioresponses() as mock:
        mock.post(f"{BASE}/dali/sendDali24/3", payload={})
        await client.async_send_dali24(3, address=10, instance=0x82, command=0x01)
    key = list(mock.requests.keys())[0]
    assert str(key[1]) == f"{BASE}/dali/sendDali24/3"
    request = mock.requests[key][0]
    assert request.kwargs["json"] == [
        {"address": 10, "instance": 0x82, "command": 0x01}
    ]


async def test_start_scan_is_non_destructive(client):
    with aioresponses() as mock:
        mock.post(f"{BASE}/dali/scan", payload={"id": "1", "status": "scanning"})
        await client.async_start_scan()
    key = list(mock.requests.keys())[0]
    request = mock.requests[key][0]
    assert request.kwargs["json"] == {"newInstallation": False, "noAddressing": True}


async def test_read_only_guard_blocks_all_writes(session):
    client = LunatoneRestClient(session, HOST, read_only=True)
    with pytest.raises(LunatoneReadOnlyError):
        await client.async_control_device(1, {"switchable": True})
    with pytest.raises(LunatoneReadOnlyError):
        await client.async_control_group(0, {}, line=0)
    with pytest.raises(LunatoneReadOnlyError):
        await client.async_control_broadcast({})
    with pytest.raises(LunatoneReadOnlyError):
        await client.async_send_dali24(0, 1, 2, 3)
    with pytest.raises(LunatoneReadOnlyError):
        await client.async_start_scan()


async def test_http_error_raises_api_error(client):
    with aioresponses() as mock:
        mock.get(f"{BASE}/devices", status=500)
        with pytest.raises(LunatoneApiError):
            await client.async_get_devices()


# ---------------------------------------------------------------------------
# Live read-only tests against the real gateway (opt-in via env + marker)
# ---------------------------------------------------------------------------

requires_gateway = pytest.mark.skipif(
    not os.environ.get("LUNATONE_GW_HOST"),
    reason="LUNATONE_GW_HOST not set",
)


@pytest.mark.gateway
@requires_gateway
async def test_live_inventory_is_line_aware(session):
    from custom_components.lunatone_dali2_iot4.models import LunatoneData

    client = LunatoneRestClient(
        session, os.environ["LUNATONE_GW_HOST"], read_only=True
    )
    info = await client.async_get_info()
    devices = await client.async_get_devices()
    data = LunatoneData.from_api(info, devices)

    assert data.info.lines >= 1
    # every device must map to a unique (line, address) slot
    assert len(data.by_line_addr) == len(data.devices)
    # group split sanity: every (line, group) only references devices on that line
    for (line, _group), members in data.groups_with_members().items():
        assert all(data.devices[gw_id].line == line for gw_id in members)
