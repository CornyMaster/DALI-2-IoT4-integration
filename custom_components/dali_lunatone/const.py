"""Constants for the Lunatone DALI-2 IoT integration."""
from typing import Final

DOMAIN: Final = "dali_lunatone"
PLATFORMS: Final = ["light", "binary_sensor", "sensor", "button"]

# Configuration
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_BACKGROUND_STATUS_POLLING: Final = "background_status_polling"
CONF_POLLING_INTERVAL: Final = "polling_interval"
CONF_SCAN_NEW_DEVICES_ON_STARTUP: Final = "scan_new_devices_on_startup"
DEFAULT_PORT: Final = 80
DEFAULT_NAME: Final = "Lunatone DALI"
DEFAULT_POLLING_INTERVAL: Final = 1800  # 30 minutes in seconds
MIN_POLLING_INTERVAL: Final = 300  # 5 minutes in seconds
MAX_POLLING_INTERVAL: Final = 86400  # 24 hours in seconds

# Device types
DALI_DEVICE_TYPES: Final = {
    0: "Fluorescent lamps",
    1: "Self-contained emergency lighting",
    2: "Discharge lamps",
    3: "Low-voltage halogen lamps",
    4: "Supply voltage incandescent lamps",
    5: "Low-voltage incandescent lamps",
    6: "LED modules",
    7: "Switching function",
    8: "Colour control",  # DT8 - supports color temperature
    9: "Sequencer",
    10: "Optical control",
}

# GTIN prefix to manufacturer mapping
# GTIN (Global Trade Item Number) prefix identifies the manufacturer
GTIN_MANUFACTURERS: Final = {
    "4062172": "Osram",
    "4052899": "Osram",
    "6971379110529": "LTECH",  # Full GTIN for LTECH
    "6971542121802": "Sunricher",  # Full GTIN for Sunricher
    "6971542": "Sunricher",  # Prefix for Sunricher
    "8718696": "Signify",
    "9010342": "Lunatone",
    "9006210": "Tridonic",
}

# DALI commands (standard)
CMD_OFF: Final = 0
CMD_UP: Final = 1
CMD_DOWN: Final = 2
CMD_STEP_UP: Final = 3
CMD_STEP_DOWN: Final = 4
CMD_RECALL_MAX: Final = 5
CMD_RECALL_MIN: Final = 6
CMD_GO_TO_LAST: Final = 10
CMD_QUERY_STATUS: Final = 144
CMD_QUERY_DEVICE_TYPE: Final = 153
CMD_QUERY_ACTUAL_LEVEL: Final = 160
CMD_QUERY_MAX_LEVEL: Final = 161
CMD_QUERY_MIN_LEVEL: Final = 162
CMD_STORE_ACTUAL_LEVEL_IN_DTR: Final = 33
CMD_QUERY_CONTENT_DTR: Final = 152
CMD_RECALL_MAX_LEVEL: Final = 254  # Special direct command
CMD_QUERY_GROUPS_0_7: Final = 192
CMD_QUERY_GROUPS_8_15: Final = 193

# DT8 Color temperature commands
CMD_ENABLE_DT8: Final = 193  # Enable Device Type 8
CMD_SET_TEMP_COLOR_TEMP: Final = 231  # Set temporary color temperature
CMD_ACTIVATE: Final = 226  # Activate command

# DALI2 commands
CMD_QUERY_DEVICE_CAPABILITIES: Final = 0x46  # Query DALI2 capabilities
CMD_QUERY_NUMBER_OF_INSTANCES: Final = 0x35
CMD_QUERY_INSTANCE_TYPE: Final = 0x80
CMD_QUERY_INSTANCE_ENABLED: Final = 0x86
CMD_QUERY_FEATURE_TYPE: Final = 0x8E  # Query instance feature type
CMD_QUERY_NEXT_FEATURE_TYPE: Final = 0x8F  # Query next feature type
CMD_QUERY_DEVICE_STATUS: Final = 0x30  # Query device status
CMD_QUERY_VERSION_NUMBER: Final = 0x34  # Query version number
CMD_READ_MEMORY_LOCATION: Final = 0x3C  # Read memory bank
CMD_SET_DTR0: Final = 0x30  # Set DTR0 (used with 0xC1)
CMD_SET_DTR1: Final = 0x31  # Set DTR1 (used with 0xC1)

# DALI2 Instance Types
INSTANCE_TYPES: Final = {
    0: "iT0: Generic",
    1: "iT1: Push Button",
    2: "iT2: Absolute Input Device/Switch",
    3: "iT3: Occupancy Sensor",
    4: "iT4: Light Sensor",
    5: "iT5: Colour Sensor",
    6: "iT6: General Purpose Sensor",
}

# DALI2 Instance Feature Types (IEC 62386-303 Part 303)
FEATURE_TYPES: Final = {
    0: "No feature",
    32: "Light output",  # Feedback indicator LEDs!
    33: "Temperature sensor",
    34: "Occupancy sensor",
    35: "Light sensor",
    36: "Proximity sensor",
}

# Feedback LED commands (24-bit frames)
FEEDBACK_LED_ON: Final = 0x10
FEEDBACK_LED_OFF: Final = 0x11

# DALI2 Button Event Types (for iT1 Push Buttons)
# Based on event filter bits specification
BUTTON_EVENT_TYPES: Final = {
    0: "button_released",       # Bit 0: Button released
    1: "button_pressed",        # Bit 1: Button pressed
    2: "short_press",           # Bit 2: Short press
    3: "double_press",          # Bit 3: Double press
    4: "long_press_start",      # Bit 4: Long press start
    5: "long_press_repeat",     # Bit 5: Long press repeat
    6: "long_press_stop",       # Bit 6: Long press stop
    7: "button_stuck_free",     # Bit 7: Button stuck/free
}

# Color temperature range (in Kelvin)
MIN_COLOR_TEMP_KELVIN: Final = 2700
MAX_COLOR_TEMP_KELVIN: Final = 6500
# Color temperature range (in mireds)
MIN_MIREDS: Final = 153  # ~6500K
MAX_MIREDS: Final = 370  # ~2700K

# Update intervals
DEVICE_SCAN_INTERVAL: Final = 300  # Device discovery interval (5 minutes)

# Connection settings
CONNECTION_TIMEOUT: Final = 10
RECONNECT_DELAY: Final = 5
MAX_RECONNECT_ATTEMPTS: Final = 3

# Data keys
DATA_COORDINATOR: Final = "coordinator"
DATA_CLIENT: Final = "client"
DATA_DEVICES: Final = "devices"

# Device attributes
ATTR_DEVICE_TYPE: Final = "device_type"
ATTR_DEVICE_NAME: Final = "device_name"
ATTR_PROTOCOL: Final = "protocol"
ATTR_ADDRESS: Final = "address"
ATTR_FIRMWARE_VERSION: Final = "firmware_version"
