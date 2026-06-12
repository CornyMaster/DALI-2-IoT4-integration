"""Tests for the websocket listener and DALI-2 event decoding."""

import asyncio

import aiohttp
import pytest
from aiohttp import web

from custom_components.dali_lunatone.websocket import (
    InputEvent,
    LunatoneWsListener,
    decode_button_event,
    decode_dali2_frame,
    decode_occupancy_event,
)


def make_frame(address: int, instance: int, event_data: int) -> list[int]:
    """Build a 24-bit DALI-2 instance event frame as the gateway reports it."""
    return [(address << 1) | 1, 128 + (instance << 2), event_data]


# ---------------------------------------------------------------------------
# Frame decoding
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("line", [0, 1, 2, 3])
@pytest.mark.parametrize(
    "event_data,expected",
    [
        (0, "button_released"),
        (1, "button_pressed"),
        (2, "short_press"),
        (5, "double_press"),
        (9, "long_press_start"),
        (11, "long_press_repeat"),
        (12, "long_press_stop"),
        (14, "button_free"),
        (15, "button_stuck"),
    ],
)
def test_decode_button_frames_on_all_lines(line, event_data, expected):
    event = decode_dali2_frame(line, make_frame(5, 2, event_data))
    assert event == InputEvent(line=line, address=5, instance=2, event_data=event_data)
    assert decode_button_event(event.event_data) == expected


@pytest.mark.parametrize(
    "event_data,expected",
    [
        (0b010, "occupied"),
        (0b011, "occupied"),
        (0b110, "still_occupied"),
        (0b000, "vacant"),
        (0b001, "movement_detected"),
    ],
)
def test_decode_occupancy_events(event_data, expected):
    assert decode_occupancy_event(event_data) == expected


def test_non_instance_frame_is_ignored():
    # second byte < 128 -> not an instance event
    assert decode_dali2_frame(0, [10, 0x42, 1]) is None


def test_malformed_frames_are_ignored():
    assert decode_dali2_frame(0, []) is None
    assert decode_dali2_frame(0, [1, 2]) is None
    assert decode_dali2_frame(0, [1, 2, 3, 4]) is None


def test_same_address_on_different_lines_yields_distinct_events():
    frame = make_frame(5, 0, 1)
    e0 = decode_dali2_frame(0, frame)
    e1 = decode_dali2_frame(1, frame)
    assert (e0.line, e0.address) != (e1.line, e1.address)
    assert e0.address == e1.address == 5


# ---------------------------------------------------------------------------
# Message dispatch (no network)
# ---------------------------------------------------------------------------


@pytest.fixture
def events():
    return []


@pytest.fixture
def listener(events):
    return LunatoneWsListener(
        session=None,
        host="gw.example",
        on_input_event=lambda event: events.append(event),
    )


async def test_dali_monitor_message_dispatches_input_event(listener, events):
    await listener._handle_message(
        {
            "type": "daliMonitor",
            "data": {
                "line": 2,
                "bits": 24,
                "data": make_frame(7, 1, 2),
                "timestamp": 100.0,
            },
        }
    )
    assert events == [InputEvent(line=2, address=7, instance=1, event_data=2)]


async def test_dali_monitor_missing_line_defaults_to_zero(listener, events):
    """Single-line DALI-2 IoT gateways may not include a line field."""
    await listener._handle_message(
        {
            "type": "daliMonitor",
            "data": {"bits": 24, "data": make_frame(7, 1, 2), "timestamp": 1.0},
        }
    )
    assert events[0].line == 0


async def test_duplicate_frames_are_deduplicated_per_line(listener, events):
    msg = {
        "type": "daliMonitor",
        "data": {"line": 1, "bits": 24, "data": make_frame(3, 0, 1), "timestamp": 10.0},
    }
    await listener._handle_message(msg)
    # exact repeat within 0.5s -> dropped
    msg["data"]["timestamp"] = 10.2
    await listener._handle_message(msg)
    # same frame on ANOTHER line -> must NOT be dropped
    other = {
        "type": "daliMonitor",
        "data": {"line": 2, "bits": 24, "data": make_frame(3, 0, 1), "timestamp": 10.3},
    }
    await listener._handle_message(other)
    assert [e.line for e in events] == [1, 2]


async def test_devices_push_dispatches_update():
    updates = []
    listener = LunatoneWsListener(
        session=None,
        host="gw.example",
        on_devices_update=lambda devices: updates.append(devices),
    )
    await listener._handle_message(
        {"type": "devices", "data": {"devices": [{"id": 1, "features": {}}]}}
    )
    assert updates == [[{"id": 1, "features": {}}]]


async def test_info_push_dispatches_info():
    infos = []
    listener = LunatoneWsListener(
        session=None,
        host="gw.example",
        on_info=lambda info: infos.append(info),
    )
    await listener._handle_message({"type": "info", "data": {"name": "gw"}})
    assert infos == [{"name": "gw"}]


async def test_unknown_message_types_are_ignored(listener, events):
    await listener._handle_message({"type": "somethingNew", "data": {}})
    await listener._handle_message({"no_type": True})
    assert events == []


# ---------------------------------------------------------------------------
# Connection / reconnect against a local fake gateway
# ---------------------------------------------------------------------------


async def test_listener_receives_and_reconnects(unused_tcp_port_factory=None):
    """Listener connects, receives a message, survives a server-side close."""
    connections = 0

    async def ws_handler(request):
        nonlocal connections
        connections += 1
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_json(
            {
                "type": "daliMonitor",
                "data": {
                    "line": 3,
                    "bits": 24,
                    "data": make_frame(9, 0, 1),
                    "timestamp": float(connections),
                },
            }
        )
        await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/", ws_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]

    received = []
    async with aiohttp.ClientSession() as session:
        listener = LunatoneWsListener(
            session=session,
            host="127.0.0.1",
            port=port,
            on_input_event=lambda event: received.append(event),
            reconnect_delay=0.05,
        )
        await listener.async_start()
        for _ in range(100):
            if len(received) >= 2:
                break
            await asyncio.sleep(0.05)
        await listener.async_stop()
    await runner.cleanup()

    assert len(received) >= 2  # reconnected after server close
    assert connections >= 2
    assert received[0].line == 3 and received[0].address == 9
