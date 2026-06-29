"""Passive websocket listener for the Lunatone DALI-2 IoT(4) gateway.

The gateway pushes JSON messages over ``ws://<host>``. This listener never
sends anything; all control and inventory runs over the REST API (api.py).
We only consume:

- ``daliMonitor``: raw bus traffic. 24-bit frames are DALI-2 input device
  events (buttons, occupancy/light sensors). The payload carries the ``line``
  the frame was seen on — essential on multi-line IoT4 gateways, where the
  same short address exists on several lines. Older single-line gateways may
  omit the field; we default to line 0.
- ``devices``: status push for gateway-known devices (merged by the
  coordinator between REST polls).
- ``info``: gateway information, sent once after connect.

Pure aiohttp + stdlib so the decoding logic is unit-testable without Home
Assistant.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

import aiohttp

from .const import BUTTON_EVENT_TYPES

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10
DEFAULT_RECONNECT_DELAY = 5.0
MAX_RECONNECT_DELAY = 300.0
# The gateway repeats monitor frames for reliability; drop exact repeats
# seen within this window (per line!).
DEDUPE_WINDOW = 0.5
DEDUPE_MAX_AGE = 2.0


@dataclass(frozen=True)
class InputEvent:
    """A decoded DALI-2 input instance event."""

    line: int
    address: int
    instance: int
    event_data: int


def decode_dali2_frame(line: int, dali_data: list[int]) -> InputEvent | None:
    """Decode a 24-bit DALI-2 frame into an instance event, if it is one.

    Per IEC 62386-103 the bus monitor shows events AND command frames; they
    are told apart by the LSB of the address byte (0 = event message,
    1 = command frame, e.g. the gateway's own device queries). We only decode
    short-address + instance-number scheme events: address byte ``0AAAAAA0``,
    instance byte ``1NNNNNEE`` (N = instance number, E = event info bits 9:8).
    """
    if len(dali_data) != 3:
        return None
    address_byte, instance_byte, opcode = dali_data
    if address_byte & 0x01:
        return None  # command frame (e.g. gateway query), not an event
    if address_byte & 0x80:
        return None  # device-group / instance-scheme event, no short address
    if instance_byte < 128:
        return None  # device/instance-type scheme, no instance number
    return InputEvent(
        line=line,
        address=(address_byte >> 1) & 0x3F,
        instance=(instance_byte - 128) >> 2,
        event_data=((instance_byte & 0x03) << 8) | opcode,
    )


def decode_button_event(event_data: int) -> str:
    """Decode push-button event info per IEC 62386-301."""
    return BUTTON_EVENT_TYPES.get(event_data, f"unknown_event_{event_data}")


def decode_occupancy_event(event_data: int) -> str:
    """Decode occupancy sensor event info per IEC 62386-303.

    Bit 0: movement (1=detected). Bits 2:1: occupancy state
    (00=vacant, 01=occupied, 10=unknown, 11=still occupied).
    """
    movement = (event_data & 0x01) == 1
    occupancy_bits = (event_data >> 1) & 0x03
    if occupancy_bits == 0b01:
        return "occupied"
    if occupancy_bits == 0b11:
        return "still_occupied"
    if occupancy_bits == 0b00 and not movement:
        return "vacant"
    if movement:
        return "movement_detected"
    return "no_movement"


class LunatoneWsListener:
    """Read-only websocket client with automatic reconnect."""

    def __init__(
        self,
        session: aiohttp.ClientSession | None,
        host: str,
        port: int = 80,
        on_input_event: Callable[[InputEvent], None] | None = None,
        on_devices_update: Callable[[list[dict[str, Any]]], None] | None = None,
        on_info: Callable[[dict[str, Any]], None] | None = None,
        reconnect_delay: float = DEFAULT_RECONNECT_DELAY,
    ) -> None:
        self._session = session
        self.url = f"ws://{host}:{port}"
        self._on_input_event = on_input_event
        self._on_devices_update = on_devices_update
        self._on_info = on_info
        self._reconnect_delay = reconnect_delay
        self._task: asyncio.Task | None = None
        self._stopped = False
        self.connected = False
        self._recent_frames: dict[str, float] = {}

    async def async_start(self) -> None:
        self._stopped = False
        self._task = asyncio.get_running_loop().create_task(self._run())

    async def async_stop(self) -> None:
        self._stopped = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self.connected = False

    async def _run(self) -> None:
        delay = self._reconnect_delay
        while not self._stopped:
            try:
                async with self._session.ws_connect(
                    self.url,
                    timeout=aiohttp.ClientWSTimeout(ws_close=CONNECT_TIMEOUT),
                    heartbeat=30,
                ) as ws:
                    _LOGGER.debug("Websocket connected to %s", self.url)
                    self.connected = True
                    delay = self._reconnect_delay
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                            except ValueError:
                                continue
                            await self._handle_message(data)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            break
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, OSError, asyncio.TimeoutError) as err:
                _LOGGER.debug("Websocket connection failed: %s", err)
            finally:
                self.connected = False
            if self._stopped:
                break
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_RECONNECT_DELAY)

    async def _handle_message(self, data: dict[str, Any]) -> None:
        message_type = data.get("type")
        payload = data.get("data") or {}

        if message_type == "info":
            if self._on_info:
                self._on_info(payload)
            return

        if message_type == "devices":
            if self._on_devices_update:
                devices = payload.get("devices")
                if isinstance(devices, list):
                    self._on_devices_update(devices)
            return

        if message_type == "daliMonitor":
            num_bits = payload.get("bits", payload.get("numberOfBits", 16))
            dali_data = payload.get("data", payload.get("daliData", []))
            if num_bits != 24:
                return
            line = payload.get("line", 0)
            timestamp = payload.get("timestamp")
            if not isinstance(timestamp, (int, float)):
                timestamp = time.monotonic()
            if self._is_duplicate(line, dali_data, timestamp):
                return
            event = decode_dali2_frame(line, dali_data)
            if event and self._on_input_event:
                self._on_input_event(event)
            return

        _LOGGER.debug("Ignoring websocket message type %s", message_type)

    def _is_duplicate(
        self, line: int, dali_data: list[int], timestamp: float
    ) -> bool:
        key = f"{line}:{','.join(map(str, dali_data))}"
        last = self._recent_frames.get(key)
        if last is not None and timestamp - last < DEDUPE_WINDOW:
            return True
        self._recent_frames[key] = timestamp
        for old_key in [
            k for k, t in self._recent_frames.items() if timestamp - t > DEDUPE_MAX_AGE
        ]:
            del self._recent_frames[old_key]
        return False
