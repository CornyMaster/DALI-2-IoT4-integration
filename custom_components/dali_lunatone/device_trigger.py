"""Device triggers for DALI-2 input devices (buttons, switches, occupancy).

Input devices are registered per (line, address) — registry identifier
``{entry_id}_line{line}_input_{address}`` — so identical short addresses on
different DALI lines resolve to different HA devices and never cross-trigger.
"""

from __future__ import annotations

import logging
import re

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
    INSTANCE_TYPE_OCCUPANCY,
    INSTANCE_TYPE_PUSH_BUTTON,
    INSTANCE_TYPE_SWITCH,
    OCCUPANCY_EVENT_TYPE_LIST,
)

_LOGGER = logging.getLogger(__name__)

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ALL_EVENT_TYPES),
        vol.Required(CONF_SUBTYPE): str,
    }
)

# Matches "{entry_id}_line{line}_input_{address}"
INPUT_IDENTIFIER_RE = re.compile(r"^(?P<entry_id>.+)_line(?P<line>\d+)_input_(?P<address>\d+)$")


def parse_input_identifier(identifier: str) -> tuple[str, int, int] | None:
    """Parse an input device registry identifier into (entry_id, line, address)."""
    match = INPUT_IDENTIFIER_RE.match(identifier)
    if not match:
        return None
    return (
        match.group("entry_id"),
        int(match.group("line")),
        int(match.group("address")),
    )


def _get_device_instances(
    hass: HomeAssistant, line: int, address: int
) -> dict[int, int]:
    """Map instance number -> instance type for one input device."""
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if not isinstance(entry_data, dict):
            continue
        coordinator = entry_data.get(DATA_COORDINATOR)
        if coordinator and coordinator.data:
            input_device = coordinator.data.inputs.get((line, address))
            if input_device:
                return {
                    num: instance.instance_type
                    for num, instance in input_device.instances.items()
                }
    return {}


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device triggers for one DALI-2 input device."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    if device is None:
        return []

    parsed = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            parsed = parse_input_identifier(identifier[1])
            if parsed:
                break
    if not parsed:
        return []
    _entry_id, line, address = parsed

    instances = _get_device_instances(hass, line, address)
    triggers = []
    for instance_num, instance_type in sorted(instances.items()):
        if instance_type in (INSTANCE_TYPE_PUSH_BUTTON, INSTANCE_TYPE_SWITCH):
            event_types = BUTTON_EVENT_TYPE_LIST
        elif instance_type == INSTANCE_TYPE_OCCUPANCY:
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
                    CONF_SUBTYPE: f"instance_{instance_num}",
                }
            )
    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger matching device_id, event type and instance."""
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
