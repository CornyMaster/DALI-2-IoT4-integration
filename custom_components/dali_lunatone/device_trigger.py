"""Provides device triggers for DALI-2 input devices (push buttons, switches, occupancy sensors).

Each DALI-2 device can have multiple instances (e.g. 4 push buttons). Triggers use
CONF_SUBTYPE to let the user select which instance to trigger on, shown in the
automation UI as a second dropdown after the event type.
"""
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
    CONF_SUBTYPE,
    DALI_EVENT,
    DATA_COORDINATOR,
    DOMAIN,
    INSTANCE_TYPE_NAMES,
    OCCUPANCY_EVENT_TYPE_LIST,
)

_LOGGER = logging.getLogger(__name__)

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ALL_EVENT_TYPES),
        vol.Required(CONF_SUBTYPE): str,
    }
)


def _get_device_instances(
    hass: HomeAssistant, protocol: str, address: int
) -> dict[int, int]:
    """Get instance number -> instance type mapping for a DALI device.

    Returns e.g. {0: 1, 1: 1, 2: 1, 3: 1} for a 4-button device (four iT1 instances).
    """
    instances: dict[int, int] = {}
    for _entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
        if not isinstance(entry_data, dict):
            continue
        coordinator = entry_data.get(DATA_COORDINATOR)
        if coordinator and coordinator.data:
            device_key = (protocol, address)
            if device_key in coordinator.data:
                dali_device = coordinator.data[device_key]
                if hasattr(dali_device, "instances") and dali_device.instances:
                    for inst_num, inst_data in dali_device.instances.items():
                        instances[inst_num] = inst_data.get("type", 0)
    return instances


def _make_subtype_key(instance_num: int, instance_type: int) -> str:
    """Create a subtype key like 'instance_0' for internal matching."""
    return f"instance_{instance_num}"


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device triggers for DALI-2 input devices.

    Returns triggers for devices that have push button (iT1),
    switch (iT2), or occupancy sensor (iT3) instances.
    Each instance generates its own set of triggers so the user
    can select which specific button/sensor to respond to.
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

    # Get instances on this device: {instance_num: instance_type}
    instances = _get_device_instances(hass, protocol, address)

    if not instances:
        return []

    triggers = []

    for inst_num, inst_type in sorted(instances.items()):
        subtype_key = _make_subtype_key(inst_num, inst_type)

        # Select event types based on instance type
        if inst_type in (1, 2):
            # iT1 Push Button or iT2 Switch -> button event triggers
            event_types = BUTTON_EVENT_TYPE_LIST
        elif inst_type == 3:
            # iT3 Occupancy Sensor -> presence event triggers
            event_types = OCCUPANCY_EVENT_TYPE_LIST
        else:
            continue

        for event_type in event_types:
            triggers.append(
                {
                    CONF_PLATFORM: "device",
                    CONF_DEVICE_ID: device_id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_TYPE: event_type,
                    CONF_SUBTYPE: subtype_key,
                }
            )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger to listen for DALI-2 device events.

    Matches on device_id, event type, AND instance (subtype).
    """
    # Extract instance number from subtype key "instance_N"
    subtype = config[CONF_SUBTYPE]
    try:
        instance_num = int(subtype.split("_", 1)[1])
    except (IndexError, ValueError):
        instance_num = None

    event_data: dict = {
        CONF_DEVICE_ID: config[CONF_DEVICE_ID],
        CONF_TYPE: config[CONF_TYPE],
    }
    if instance_num is not None:
        event_data["instance"] = instance_num

    event_config = {
        event_trigger.CONF_PLATFORM: "event",
        event_trigger.CONF_EVENT_TYPE: DALI_EVENT,
        event_trigger.CONF_EVENT_DATA: event_data,
    }
    event_config = event_trigger.TRIGGER_SCHEMA(event_config)
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
