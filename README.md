# Lunatone DALI-2 IoT Gateway - Home Assistant Integration

[![GitHub Release](https://img.shields.io/github/release/Martsola/dali-lunatone-integration.svg?style=flat-square)](https://github.com/Martsola/dali-lunatone-integration/releases)
[![License](https://img.shields.io/github/license/Martsola/dali-lunatone-integration.svg?style=flat-square)](https://github.com/Martsola/dali-lunatone-integration/blob/main/LICENSE)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
[![Validate](https://github.com/Martsola/dali-lunatone-integration/actions/workflows/validate.yml/badge.svg)](https://github.com/Martsola/dali-lunatone-integration/actions/workflows/validate.yml)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Martsola&repository=dali-lunatone-integration&category=integration)

A custom Home Assistant integration for controlling the Lunatone DALI-2 IoT Gateway via WebSocket.

**Compatible Gateway:** Lunatone DALI-2 IoT Gateway (all firmware versions)

---

## Features

✅ **Fully Async** - Non-blocking WebSocket communication

✅ **Auto-Discovery** - Automatically scans and discovers DALI devices (addresses 0-63)

✅ **Light Control** - On/Off, brightness (0-100%), color temperature (DT8 devices)

✅ **Real-time Updates** - Monitors DALI bus for external changes (wall switches, groups)

✅ **Group Commands** - Supports DALI group addressing (groups 0-15)

✅ **Binary Sensors** - DALI2 pushbuttons and occupancy sensors

✅ **Light Sensors** - DALI2 illuminance sensors

✅ **Device Triggers** - DALI2 button and occupancy events as automation triggers (selectable from dropdown)

✅ **Reconnection** - Automatic reconnection on connection loss

✅ **DataUpdateCoordinator** - Efficient state polling with configurable intervals

✅ **Config Flow** - Easy setup through Home Assistant UI

✅ **Multiple Gateways** - Support for multiple gateway instances, each managing its own DALI bus

✅ **Bus Monitoring** - Real-time monitoring of DALI bus for instant updates from external commands

✅ **Group Support** - DALI addresses 0-63 can belong to groups 0-15, with automatic entity updates when group commands are received

## Supported Devices

### DALI Devices
- **Device Type 6**: LED modules
- **Device Type 7**: Switching function
- **Device Type 8**: Color control (with color temperature support)

### DALI2 Devices
- **Instance Type 0 (iT0)**: Generic devices
- **Instance Type 1 (iT1)**: Push Buttons - Binary sensors for button events
- **Instance Type 2 (iT2)**: Absolute Input Devices/Switches - Binary sensors for switch states
- **Instance Type 3 (iT3)**: Occupancy Sensors - Motion detection
- **Instance Type 4 (iT4)**: Light Sensors - Illuminance measurement (lux)
- **Instance Type 5 (iT5)**: Colour Sensors - Color measurement
- **Instance Type 6 (iT6)**: General Purpose Sensors - Generic sensor data

### Group Commands
- Supports DALI group addressing (groups 0-15)
- External group commands automatically update all devices in the group
- Physical wall switches can control multiple lights via groups

### Button Event Types

For iT1 (Push Buttons) and iT2 (Switches), the following event types are detected:
- **button_released** (bit 0): Button released
- **button_pressed** (bit 1): Button pressed
- **short_press** (bit 2): Short press detected
- **double_press** (bit 3): Double press detected
- **long_press_start** (bit 4): Long press started
- **long_press_repeat** (bit 5): Long press repeating
- **long_press_stop** (bit 6): Long press stopped
- **button_stuck_free** (bit 7): Button stuck or freed

## Installation

### Option 1: HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=YOUR_GITHUB_USERNAME&repository=dali-lunatone-integration&category=integration)

1. **Add Custom Repository:**
   - Open HACS in Home Assistant
   - Click the three dots menu → Custom repositories
   - Add: `https://github.com/martsola/dali-lunatone-integration`
   - Category: Integration

2. **Install:**
   - Search for "Lunatone DALI-2 IoT" in HACS
   - Click Install
   - Restart Home Assistant

3. **Configure:**
   - Go to **Settings → Devices & Services → Add Integration**
   - Search for "Lunatone DALI-2 IoT"
   - Enter your Lunatone DALI-2 IoT Gateway IP address and port (default: 80)

### Option 2: Manual Installation

1. Download the [latest release](https://github.com/martsola/dali-lunatone-integration/releases) from GitHub
2. Extract the `custom_components/dali_lunatone` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration**
5. Search for "Lunatone DALI-2 IoT"
6. Enter your Lunatone DALI-2 IoT Gateway IP address and port (default: 80)

## Configuration

### Initial Setup

1. Navigate to **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for **Lunatone DALI-2 IoT**
4. Enter:
   - **IP Address**: Your Lunatone device IP address
   - **Port**: WebSocket port (default: `80`)
5. Click **Submit**

The integration will:
- Connect to the Lunatone device via WebSocket
- Load previously discovered devices from storage
- Start real-time monitoring of the DALI bus
- Create entities for all devices

### Configuration Options

After initial setup, configure the integration behavior:

1. Navigate to **Settings → Devices & Services**
2. Find **Lunatone DALI-2 IoT** and click **Configure** (or **Options**)
3. Available options:

#### Background Status Polling
- **Type**: Toggle (on/off)
- **Default**: Off (disabled)
- **Description**: When enabled, the integration periodically polls all device states at the configured interval. When disabled, device states are only updated through real-time WebSocket events (button presses, manual commands) and the Manual Scan button.
- **Recommendation**: Keep disabled unless you need scheduled state verification. Real-time WebSocket monitoring handles most updates automatically.

#### Polling Interval
- **Type**: Number (seconds)
- **Range**: 300-86400 (5 minutes to 24 hours)
- **Default**: 1800 (30 minutes)
- **Description**: How often to poll device states when background polling is enabled. Only applies if "Background status polling" is turned on.
- **Note**: This does not affect real-time event monitoring, which always operates immediately via WebSocket.

#### Scan New Devices on Startup
- **Type**: Toggle (on/off)
- **Default**: Off (disabled)
- **Description**: When enabled, the integration automatically scans the DALI bus for new, changed, or removed devices every time Home Assistant starts. When disabled, the integration loads devices from storage and you can manually trigger scans using the Manual Scan button.
- **Recommendation**: Enable if you frequently add/remove devices. Otherwise, keep disabled and use Manual Scan when needed.

#### Activate New Device Scanning Now
- **Type**: Toggle (on/off)
- **Default**: Off (disabled)
- **Description**: Enable this option and click Submit to immediately scan the DALI bus for devices. The scan will run once and this option automatically resets to off after completion.
- **Alternative**: You can also use the **Manual Scan** button entity for the same functionality.

### Manual Scan Button

A button entity is created for each gateway: `button.lunatone_dali_[ip]_manual_scan`

- **Purpose**: Manually trigger a full device scan
- **Use Case**: Discovery of new devices, verification of removed devices
- **Location**: Available in the device page or entities list

### System Options

In addition to the integration-specific options above, Home Assistant provides standard system options (accessed via **... → System Options**):

- **Enable newly added entities**: Automatically enable entities for newly discovered devices
- **Enable polling for changes**: Use Home Assistant's standard polling mechanism (note: this integration uses WebSocket for real-time updates, so HA polling is typically not needed)

**Note**: The integration's "Background status polling" option is separate from Home Assistant's system-level polling option.

## Usage

### Light Entities

Each discovered DALI light appears as a light entity:
- **Name**: `DALI [Device Type] [Address]`
- **Entity ID**: `light.dali_[device_type]_[address]`

### Group and Broadcast Entities

DALI group control entities are created for groups with assigned devices:
- **Group Entities**: `light.dali_group_[0-15]`
- **Broadcast Entity**: `light.dali_broadcast_all_devices`

### Binary Sensor Entities

DALI2 pushbuttons, switches, and occupancy sensors appear as binary sensors:
- **Pushbuttons (iT1)**: `binary_sensor.dali2_[address]_button_[number]`
- **Switches (iT2)**: `binary_sensor.dali2_[address]_switch_[number]`
- **Occupancy (iT3)**: `binary_sensor.dali2_[address]_occupancy`

#### Binary Sensor Behavior

**Momentary Events**: `short_press` and `double_press` events briefly set the binary sensor state to **on** (True), then automatically reset to **off** (False) after 0.5 seconds. This allows automations to trigger on state changes without the sensor staying stuck on.

**Sustained Events**: `button_pressed`, `long_press_start`, and `long_press_repeat` keep the binary sensor **on** until a corresponding release or stop event is received.

#### Binary Sensor Attributes

**Push Buttons and Switches (iT1, iT2)**
- `last_event_type`: The type of the last button/switch event
  - `button_released` (bit 0)
  - `button_pressed` (bit 1)
  - `short_press` (bit 2) — momentary, auto-resets
  - `double_press` (bit 3) — momentary, auto-resets
  - `long_press_start` (bit 4)
  - `long_press_repeat` (bit 5)
  - `long_press_stop` (bit 6)
  - `button_stuck_free` (bit 7)
- `last_event_data`: Raw event data value (0-7)

**Occupancy Sensors (iT3)**
- `movement_detected`: Boolean indicating if movement was detected

### Event Bus Events

The integration fires `dali_lunatone_event` events on the Home Assistant event bus for all button, switch, and occupancy interactions (instance types iT1, iT2, and iT3). These events can be used directly in automations.

**Event data:**
- `device_id`: Home Assistant device ID (for device trigger matching)
- `type`: Event type string (same as `event_type`, used by device triggers)
- `device_address`: DALI bus address of the device
- `instance`: Instance number on the device
- `instance_type`: Instance type (1 = push button, 2 = switch, 3 = occupancy)
- `event_type`: Event type string (e.g., `short_press`, `double_press`, `occupied`, `vacant`)
- `event_data`: Raw event data value

### Device Triggers (Automation UI)

DALI-2 input devices are registered as device triggers in Home Assistant, allowing you to select events directly from the automation UI dropdown — no YAML needed.

To use:
1. Go to **Settings → Automations → Create Automation**
2. Click **Add Trigger → Device**
3. Select your DALI-2 device
4. Choose the event type from the dropdown

#### Push Button / Switch Triggers (iT1, iT2)

| Trigger | Description |
|---------|-------------|
| Button released | Button was released |
| Button pressed | Button was pressed down |
| Short press | Short press completed |
| Double press | Double press detected |
| Long press started | Long press threshold reached |
| Long press repeat | Long press ongoing (periodic) |
| Long press stopped | Button released after long press |
| Button free (unstuck) | Button was stuck and is now released |
| Button stuck | Button stuck detection |

#### Occupancy Sensor Triggers (iT3)

| Trigger | Description |
|---------|-------------|
| Movement detected | Motion sensor detected movement |
| No movement | No movement detected |
| Occupied | Area is occupied |
| Vacant | Area is vacant |
| Still occupied | Area is still occupied (periodic) |

### Sensor Entities

DALI2 light sensors and other sensors appear as sensor entities:
- **Illuminance (iT4)**: `sensor.dali2_[address]_illuminance` (in lux)
- **Colour Sensors (iT5)**: `sensor.dali2_[address]_colour`
- **General Purpose (iT6)**: `sensor.dali2_[address]_sensor`

#### Sensor Attributes

Sensors provide their measured values as the main state:
- **iT4 (Light Sensors)**: Illuminance in lux (float value)
- **iT5 (Colour Sensors)**: Color measurement data
- **iT6 (General Purpose)**: Generic sensor value

### Supported Features

#### All DALI Devices
- **Turn On/Off**: Standard light controls
- **Brightness**: 0-100% dimming control
- **Group Support**: Responds to DALI group commands from wall switches

#### DT8 Color Control Devices
- **Color Temperature**: 2700K-6500K (warm to cool white)

### Example Automations

#### Turn on light at sunset
```yaml
automation:
  - alias: "DALI Light On at Sunset"
    trigger:
      - platform: sun
        event: sunset
    action:
      - service: light.turn_on
        target:
          entity_id: light.dali_led_modules_0  # Replace with your entity ID
        data:
          brightness_pct: 80
```

#### Set color temperature based on time
```yaml
automation:
  - alias: "DALI Adaptive Lighting"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: light.turn_on
        target:
          entity_id: light.dali_colour_control_0  # Replace with your entity ID
        data:
          brightness_pct: 100
          color_temp_kelvin: 6500  # Cool white
  
  - alias: "DALI Evening Lighting"
    trigger:
      - platform: time
        at: "19:00:00"
    action:
      - service: light.turn_on
        target:
          entity_id: light.dali_colour_control_0  # Replace with your entity ID
        data:
          brightness_pct: 60
          color_temp_kelvin: 2700  # Warm white
```

#### Toggle light on DALI button short press (using event bus)
```yaml
automation:
  - alias: "DALI Button Toggle Light"
    trigger:
      - platform: event
        event_type: dali_lunatone_event
        event_data:
          device_address: 10  # Replace with your button address
          event_type: short_press
    action:
      - service: light.toggle
        target:
          entity_id: light.dali_led_modules_0  # Replace with your entity ID
```

#### Toggle light on button press (using device trigger - recommended)
```yaml
automation:
  - alias: "DALI Button Toggle Light"
    trigger:
      - platform: device
        domain: dali_lunatone
        device_id: <your_device_id>  # From UI or device registry
        type: short_press
    action:
      - service: light.toggle
        target:
          entity_id: light.dali_led_modules_0
```

#### Turn on lights when occupancy detected (using device trigger)
```yaml
automation:
  - alias: "DALI Occupancy Light On"
    trigger:
      - platform: device
        domain: dali_lunatone
        device_id: <your_device_id>
        type: occupied
    action:
      - service: light.turn_on
        target:
          entity_id: light.dali_led_modules_0
        data:
          brightness_pct: 100
```

#### Turn off lights when area vacant
```yaml
automation:
  - alias: "DALI Vacancy Light Off"
    trigger:
      - platform: device
        domain: dali_lunatone
        device_id: <your_device_id>
        type: vacant
    action:
      - service: light.turn_off
        target:
          entity_id: light.dali_led_modules_0
```

#### Dim light on DALI button double press (using event bus)
```yaml
automation:
  - alias: "DALI Button Dim Light"
    trigger:
      - platform: event
        event_type: dali_lunatone_event
        event_data:
          device_address: 10  # Replace with your button address
          event_type: double_press
    action:
      - service: light.turn_on
        target:
          entity_id: light.dali_led_modules_0  # Replace with your entity ID
        data:
          brightness_pct: 30
```

## Architecture

### Components

1. **`lunatone_api.py`** - WebSocket client handling JSON-RPC 2.0 protocol
   - Connection management & reconnection
   - Device discovery & scanning
   - DALI command execution
   - Bus event monitoring

2. **`coordinator.py`** - DataUpdateCoordinator for state management
   - Periodic brightness polling (configurable)
   - Efficient batch updates
   - Device state caching

3. **`light.py`** - Light platform implementation
   - LightEntity with brightness & color temperature
   - Proper state reporting
   - Device info integration

5. **`device_trigger.py`** - Device automation triggers
   - Push button event triggers (short press, long press, etc.)
   - Occupancy sensor triggers (occupied, vacant, movement)
   - Selectable from Home Assistant automation UI dropdown

6. **`config_flow.py`** - UI configuration flow
   - Connection validation
   - Duplicate prevention
   - User-friendly setup

## Technical Details

### Communication Protocol

- **Transport**: WebSocket (JSON-RPC 2.0)
- **Default Port**: 80
- **Message Format**: JSON
- **DALI Protocol**: DALI-1 and DALI-2

### DALI Commands Used

This integration communicates with the Lunatone DALI-2 IoT Gateway using the following DALI commands:

#### Standard DALI Commands (IEC 62386-102)

**Query Commands**
- **QUERY_STATUS (144)**: Check device status and failure conditions
- **QUERY_DEVICE_TYPE (153)**: Identify device type (DT6, DT7, DT8, etc.)
- **QUERY_ACTUAL_LEVEL (160)**: Read current brightness level (0-254)
- **QUERY_MIN_LEVEL (161)**: Read minimum configured brightness
- **QUERY_MAX_LEVEL (162)**: Read maximum configured brightness
- **QUERY_GROUPS_0_7 (192)**: Read group membership for groups 0-7
- **QUERY_GROUPS_8_15 (193)**: Read group membership for groups 8-15

**Control Commands**
- **OFF (0)**: Turn light off
- **STEP_UP (3)**: Increase brightness by one step
- **STEP_DOWN (4)**: Decrease brightness by one step
- **Direct Arc Power**: Set brightness directly (address<<1, level)

**Group Addressing**
- Group command format: `0x80 | (group_number << 1)`
- Supports groups 0-15
- External group commands automatically update all devices in the group

**Broadcast Commands**
- **0xFE**: Unaddressed/broadcast command prefix
- **0xFF**: Broadcast command indicator

#### DALI2 Commands (IEC 62386-103)

**Device Capabilities**
- **QUERY_DEVICE_CAPABILITIES (0x46)**: Read device feature support
- **QUERY_NUMBER_OF_INSTANCES (0x35)**: Count available input devices

**Instance Queries**
- **QUERY_INSTANCE_TYPE (0x80)**: Identify instance type (iT0-iT6)
- **QUERY_INSTANCE_STATUS (0x82)**: Read current instance state
- **QUERY_INSTANCE_ENABLED (0x83)**: Check if instance is enabled

**Event Monitoring**
- Push button events (iT1): All 8 event filter bits
- Switch state changes (iT2): State and event detection
- Occupancy detection (iT3): Motion sensor state
- Light level measurements (iT4): Sensor readings (lux)
- Colour sensor data (iT5): Color measurements
- General purpose sensor data (iT6): Generic values

#### DT8 Color Temperature Commands (IEC 62386-209)

For color temperature control, the integration uses a 6-command sequence:

1. **SET_DTR (195)**: Set Data Transfer Register with lower byte
2. **SET_DTR1 (163)**: Set Data Transfer Register 1 with upper byte
3. **ENABLE_DT8 (193)**: Enable Device Type 8 color control mode
4. **SET_TEMP_COLOR_TEMP (231)**: Set temporary color temperature from DTR/DTR1
5. **ACTIVATE (226)**: Activate the new color temperature
6. **Direct Arc Power**: Set brightness level to complete the transition

Color temperature is calculated as: `mirek = 1000000 / kelvin`

#### Bus Monitoring

The integration maintains real-time synchronization by monitoring:
- All DALI traffic from external sources (wall switches, other controllers)
- Group commands that update multiple devices
- Broadcast commands affecting all devices
- Device responses to validate command execution

This ensures Home Assistant state matches physical device state even when controlled externally.

### State Updates

1. **Polling**: Configurable interval (60-3600 seconds, default: 900 seconds)
2. **Bus Monitoring**: Real-time updates from external commands and group commands
3. **Immediate Updates**: After local commands from Home Assistant
4. **Coordinator**: Regular updates for UI responsiveness

## Development

### Debug Logging

Enable detailed logging by adding to `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    custom_components.dali_lunatone: debug
    custom_components.dali_lunatone.lunatone_api: debug
```

## API Reference

### Lunatone Device Info

After connecting, the integration stores device information:
- **Name**: Device name
- **Version**: Firmware version
- **Serial**: Device serial number

### Device Attributes

Each DALI light entity includes attributes:
- `address`: DALI bus address (0-63)
- `protocol`: "DALI" or "DALI2"
- `device_type`: DALI device type number
- `device_name`: Human-readable device type name

Each DALI group entity includes attributes:
- `group_number`: DALI group number (0-15)
- `devices`: List of devices in the group
- `device_count`: Number of devices in the group

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Ways to contribute:
- Report bugs and suggest features via [GitHub Issues](https://github.com/martsola/dali-lunatone-integration/issues)
- Submit pull requests for bug fixes or enhancements
- Improve documentation
- Test with different DALI device types
- Share your automation examples

## Support

- **Documentation**: [Installation Guide](INSTALL.md)
- **Issues**: [GitHub Issues](https://github.com/martsola/dali-lunatone-integration/issues)
- **Discussions**: [GitHub Discussions](https://github.com/martsola/dali-lunatone-integration/discussions)

## License

MIT License - Copyright (c) 2025 Mikko Martsola

See [LICENSE](LICENSE) file for details.

---

**Made with ❤️ for the Home Assistant community**

**Version**: 0.1.3-beta  
**Author**: Mikko Martsola 
**Last Updated**: February 12, 2026
