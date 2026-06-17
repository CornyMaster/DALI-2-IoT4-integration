"""Constants for the Lunatone DALI-2 IoT integration."""
from typing import Final

DOMAIN: Final = "lunatone_dali2_iot4"
PLATFORMS: Final = [
    "light",
    "binary_sensor",
    "sensor",
    "button",
    "scene",
    "select",
    "number",
]

# Configuration
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_LINES: Final = "lines"
CONF_POLLING_INTERVAL: Final = "polling_interval"
CONF_ENABLE_GLOBAL_BROADCAST: Final = "enable_global_broadcast"
CONF_TRACK_INPUTS: Final = "track_inputs"
DEFAULT_PORT: Final = 80
DEFAULT_NAME: Final = "Lunatone DALI"
DEFAULT_POLLING_INTERVAL: Final = 30  # seconds; one GET /devices per poll
MIN_POLLING_INTERVAL: Final = 5
MAX_POLLING_INTERVAL: Final = 3600

# hass.data keys
DATA_CLIENT: Final = "client"
DATA_COORDINATOR: Final = "coordinator"
DATA_WS_LISTENER: Final = "ws_listener"

# DALI2 instance types (IEC 62386-3xx)
INSTANCE_TYPE_PUSH_BUTTON: Final = 1
INSTANCE_TYPE_SWITCH: Final = 2
INSTANCE_TYPE_OCCUPANCY: Final = 3
INSTANCE_TYPE_LIGHT_SENSOR: Final = 4

INSTANCE_TYPE_NAMES: Final = {
    INSTANCE_TYPE_PUSH_BUTTON: "Push Button",
    INSTANCE_TYPE_SWITCH: "Switch",
    INSTANCE_TYPE_OCCUPANCY: "Occupancy Sensor",
    INSTANCE_TYPE_LIGHT_SENSOR: "Light Sensor",
}

# Feedback LED opcodes (24-bit frames, instance byte 0x20 + instance)
FEEDBACK_LED_ON: Final = 0x10
FEEDBACK_LED_OFF: Final = 0x11

# DALI2 Button Event Types (for iT1 Push Buttons)
# Per IEC 62386-301: the event information uniquely defines the event.
BUTTON_EVENT_TYPES: Final = {
    0: "button_released",
    1: "button_pressed",
    2: "short_press",
    5: "double_press",
    9: "long_press_start",
    11: "long_press_repeat",
    12: "long_press_stop",
    14: "button_free",
    15: "button_stuck",
}

# Button events that represent an active press (binary sensor ON)
BUTTON_ACTIVE_EVENTS: Final = (1, 2, 5, 9, 11)

# DALI2 Occupancy Sensor Event Types (for iT3 Occupancy Sensors)
OCCUPANCY_EVENT_TYPES: Final = {
    "movement_detected": "Movement detected",
    "no_movement": "No movement",
    "occupied": "Occupied",
    "vacant": "Vacant",
    "still_occupied": "Still occupied",
}

# Event bus event name for device triggers
DALI_EVENT: Final = f"{DOMAIN}_event"

# Subtype key for device automation (instance selection)
CONF_SUBTYPE: Final = "subtype"

# All supported event types for device automation triggers
BUTTON_EVENT_TYPE_LIST: Final = list(BUTTON_EVENT_TYPES.values())
OCCUPANCY_EVENT_TYPE_LIST: Final = list(OCCUPANCY_EVENT_TYPES.keys())
ALL_EVENT_TYPES: Final = BUTTON_EVENT_TYPE_LIST + OCCUPANCY_EVENT_TYPE_LIST

# Color temperature fallback range in Kelvin (used when the gateway does not
# report device-specific limits)
MIN_COLOR_TEMP_KELVIN: Final = 2700
MAX_COLOR_TEMP_KELVIN: Final = 6500

# Momentary event types that should auto-reset the binary sensor state
MOMENTARY_EVENTS: Final = ("short_press", "double_press")
MOMENTARY_RESET_DELAY: Final = 0.5  # seconds
