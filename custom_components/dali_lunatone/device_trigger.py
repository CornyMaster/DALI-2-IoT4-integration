"""Provides device triggers for DALI-2 input devices (push buttons, switches, occupancy sensors)."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import (
    ALL_EVENT_TYPES,
    BUTTON_EVENT_TYPE_LIST,
    DALI_EVENT,
    DATA_COORDINATOR,
    DOMAIN,
    OCCUPANCY_EVENT_TYPE_LIST,
)

_LOGGER = logging.getLogger(__name__)

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ALL_EVENT_TYPES),
    }
)


def _get_device_instance_types(
    hass: HomeAssistant, protocol: str, address: int
) -> set[int]:
    """Get the set of instance types for a DALI device."""
    instance_types: set[int] = set()
    for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
        if not isinstance(entry_data, dict):
            continue
        coordinator = entry_data.get(DATA_COORDINATOR)
        if coordinator and coordinator.data:
            device_key = (protocol, address)
            if device_key in coordinator.data:
                dali_device = coordinator.data[device_key]
                if hasattr(dali_device, "instances") and dali_device.instances:
                    for _inst_num, inst_data in dali_device.instances.items():
                        instance_types.add(inst_data.get("type", 0))
    return instance_types


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device triggers for DALI-2 input devices.

    Returns triggers for devices that have push button (iT1),
    switch (iT2), or occupancy sensor (iT3) instances.
    Button/switch devices get button event triggers.
    Occupancy devices get presence event triggers.
    """
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if device is None:
        return []

    # Find our integration's identifier (format: "DALI2_<address>")
    dali_identifier = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            dali_identifier = identifier[1]
            break

    if not dali_identifier:
        return []

    # Parse protocol and address from identifier
    parts = dali_identifier.split("_")
    if len(parts) != 2:
        return []  # Not a device-level entry (could be the gateway)

    protocol = parts[0]
    if protocol != "DALI2":
        return []  # Only DALI2 devices have input instances

    try:
        address = int(parts[1])
    except ValueError:
        return []

    # Get the instance types present on this device
    instance_types = _get_device_instance_types(hass, protocol, address)

    if not instance_types:
        return []

    # Build trigger list based on what instance types the device has
    event_types: list[str] = []

    # iT1 Push Button or iT2 Switch -> button event triggers
    if instance_types & {1, 2}:
        event_types.extend(BUTTON_EVENT_TYPE_LIST)

    # iT3 Occupancy Sensor -> presence event triggers
    if 3 in instance_types:
        event_types.extend(OCCUPANCY_EVENT_TYPE_LIST)

    if not event_types:
        return []

    triggers = []
    for event_type in event_types:
        triggers.append(
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: event_type,
            }
        )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger to listen for DALI-2 device events."""
    event_config = {
        event_trigger.CONF_PLATFORM: "event",
        event_trigger.CONF_EVENT_TYPE: DALI_EVENT,
        event_trigger.CONF_EVENT_DATA: {
            CONF_DEVICE_ID: config[CONF_DEVICE_ID],
            CONF_TYPE: config[CONF_TYPE],
        },
    }
    event_config = event_trigger.TRIGGER_SCHEMA(event_config)
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
