"""Tests for the REST client (mocked HTTP; live gateway tests are marked)."""

import asyncio
import os

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.lunatone_dali2_iot4.api import (
    IncompleteDescriptionError,
    LunatoneApiError,
    LunatoneReadOnlyError,
    LunatoneRestClient,
    parse_device_description,
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


def test_parse_device_description_real_bytes():
    """Bytes as captured from a real Lunatone DALI-2 MC (memory bank 2)."""
    header = [24, None, 2]
    text = list("Schalter_Küche_L".encode())
    padding = [255] * (33 - len(header) - len(text))
    assert parse_device_description(header + text + padding) == "Schalter_Küche_L"


def test_parse_device_description_empty_bank():
    assert parse_device_description([24, None] + [255] * 31) is None


def test_parse_device_description_missing_answer_raises():
    """An all-NAK read is unreliable, not an empty description."""
    with pytest.raises(IncompleteDescriptionError):
        parse_device_description([None, None, None, None])


def test_parse_device_description_nak_mid_string_raises():
    """A None inside the text must not silently truncate the name."""
    text = list("Schalter_Wohnzimmer_O".encode())
    text[-1] = None  # final byte NAK'd, as seen on a busy bus
    with pytest.raises(IncompleteDescriptionError):
        parse_device_description([24, None, 2] + text + [0])


def test_parse_device_description_invalid_utf8_raises():
    """Misaligned/garbage bytes that are not valid UTF-8 are rejected."""
    with pytest.raises(IncompleteDescriptionError):
        parse_device_description([24, None, 2, 0xC3, 0x28, 0])  # bad 2-byte seq


def _bank(text_bytes):
    """Full 33-byte bank-2 image (3-byte header + text + 0x00 padding)."""
    return [24, None, 2] + list(text_bytes) + [0] * (33 - 3 - len(text_bytes))


async def test_read_input_device_description_batches(client):
    """3 re-seeking requests (14 + 14 + 5 reads) reassemble the 33-byte bank."""
    bank = _bank("Schalter_Küche_L".encode())
    with aioresponses() as mock:
        mock.post(f"{BASE}/dali/sendDali24/0", payload=[None, None] + bank[0:14])
        mock.post(f"{BASE}/dali/sendDali24/0", payload=[None, None] + bank[14:28])
        mock.post(f"{BASE}/dali/sendDali24/0", payload=[None, None] + bank[28:33])
        result = await client.async_read_input_device_description(0, 0)
    assert result == "Schalter_Küche_L"
    key = list(mock.requests.keys())[0]
    reqs = mock.requests[key]
    first = reqs[0].kwargs["json"]
    assert first[0] == {"address": 0xC1, "instance": 0x31, "command": 2}  # DTR1=bank2
    assert first[1] == {"address": 0xC1, "instance": 0x30, "command": 0}  # DTR0=0
    assert first[2] == {"address": 1, "instance": 0xFE, "command": 0x3C}  # READ
    assert len(first) == 16  # gateway limit per request
    # each follow-up request RE-SEEKS DTR0 instead of relying on auto-increment
    assert reqs[1].kwargs["json"][1] == {"address": 0xC1, "instance": 0x30, "command": 14}
    assert reqs[2].kwargs["json"][1] == {"address": 0xC1, "instance": 0x30, "command": 28}


async def test_read_input_device_description_retries_on_nak(client):
    """A first read with a NAK'd byte is retried, not persisted truncated."""
    bad = _bank("Schalter_Küche_L".encode())
    bad[8] = None  # NAK in the text region -> parse raises -> retry
    good = _bank("Schalter_Küche_L".encode())
    with aioresponses() as mock:
        for chunk in ((0, 14), (14, 28), (28, 33)):
            mock.post(f"{BASE}/dali/sendDali24/0", payload=[None, None] + bad[chunk[0]:chunk[1]])
        for chunk in ((0, 14), (14, 28), (28, 33)):
            mock.post(f"{BASE}/dali/sendDali24/0", payload=[None, None] + good[chunk[0]:chunk[1]])
        result = await client.async_read_input_device_description(0, 0)
    assert result == "Schalter_Küche_L"


async def test_dali24_traffic_serialized_per_line(client):
    """Same-line raw traffic is serialized; different lines run concurrently."""
    active = {"n": 0, "max": 0}

    async def fake_request(method, path, json=None, params=None):
        active["n"] += 1
        active["max"] = max(active["max"], active["n"])
        await asyncio.sleep(0.01)
        active["n"] -= 1
        return [None]

    client._request = fake_request
    await asyncio.gather(
        client.async_send_dali24_frames(0, [{"x": 1}]),
        client.async_send_dali24_frames(0, [{"x": 2}]),
    )
    assert active["max"] == 1  # same line never overlaps

    active.update(n=0, max=0)
    await asyncio.gather(
        client.async_send_dali24_frames(0, [{"x": 1}]),
        client.async_send_dali24_frames(1, [{"x": 2}]),
    )
    assert active["max"] == 2  # different lines are independent


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
