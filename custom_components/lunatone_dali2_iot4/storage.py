"""Persistence for DALI-2 input devices discovered via websocket events.

The gateway's REST API lists control gear (GET /devices) but not input
devices (push buttons). Those are discovered from websocket events, so we
persist them per config entry to recreate their entities and device triggers
right after a Home Assistant restart instead of waiting for the next press.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .models import InputDevice, InputInstance

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 2


class _InputStore(Store):
    """Store with migration support for the input registry."""

    async def _async_migrate_func(self, old_major_version, old_minor_version, old_data):
        # v1 data may contain phantom devices created by misdecoded 24-bit
        # command frames (gateway queries); discard it and rediscover inputs
        # from real events.
        return {"inputs": []}


class InputDeviceStore:
    """Stores known input devices keyed by (line, address)."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store = _InputStore(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.inputs"
        )

    async def async_load(self) -> dict[tuple[int, int], InputDevice]:
        data = await self._store.async_load()
        inputs: dict[tuple[int, int], InputDevice] = {}
        for entry in (data or {}).get("inputs", []):
            device = InputDevice(
                line=entry["line"],
                address=entry["address"],
                name=entry.get("name", ""),
            )
            for instance_key, instance_data in entry.get("instances", {}).items():
                device.instances[int(instance_key)] = InputInstance(
                    instance_type=instance_data.get("type", 1),
                    has_feedback_led=instance_data.get("has_feedback_led", False),
                )
            inputs[(device.line, device.address)] = device
        if inputs:
            _LOGGER.debug("Restored %d input devices from storage", len(inputs))
        return inputs

    async def async_save(self, inputs: dict[tuple[int, int], InputDevice]) -> None:
        await self._store.async_save(
            {
                "inputs": [
                    {
                        "line": device.line,
                        "address": device.address,
                        "name": device.name,
                        "instances": {
                            str(num): {
                                "type": instance.instance_type,
                                "has_feedback_led": instance.has_feedback_led,
                            }
                            for num, instance in device.instances.items()
                        },
                    }
                    for device in inputs.values()
                ]
            }
        )
