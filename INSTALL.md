# Lunatone DALI-2 IoT4 Gateway - Installation Guide

## Installation Methods

### Method 1: HACS (Recommended)

HACS (Home Assistant Community Store) provides the easiest installation and automatic updates.

#### Prerequisites
- [HACS](https://hacs.xyz/) installed in Home Assistant

#### Steps

1. **Add Custom Repository:**
   - Open HACS in Home Assistant
   - Click the three dots menu (⋮) in the top right
   - Select "Custom repositories"
   - Add repository URL: `https://github.com/CornyMaster/DALI-2-IoT4-integration`
   - Category: "Integration"
   - Click "Add"

2. **Install Integration:**
   - In HACS, search for "Lunatone DALI-2 IoT4"
   - Click on the integration
   - Click "Download"
   - Restart Home Assistant

3. **Configure Integration:**
   - Go to **Settings → Devices & Services**
   - Click **+ Add Integration**
   - Search for "Lunatone DALI-2 IoT4"
   - Enter connection details:
     - **Host**: IP address of your Lunatone DALI-2 IoT4 Gateway (e.g., `192.168.1.100`)
     - **Port**: `80` (default WebSocket port)
     - **Coordinator Update Interval**: 900 seconds (default, optional)
     - **Scan on Setup**: Enabled (recommended for first setup)
   - Click **Submit**

### Method 2: Manual Installation from GitHub Release

1. **Download Latest Release:**
   - Go to [Releases](https://github.com/CornyMaster/DALI-2-IoT4-integration/releases)
   - Download the latest `lunatone_dali2_iot4.zip` file

2. **Extract to Custom Components:**
   ```bash
   # From your Home Assistant config directory
   cd /path/to/homeassistant/config
   mkdir -p custom_components
   unzip lunatone_dali2_iot4.zip -d custom_components/
   ```

3. **Restart Home Assistant:**
   - Via UI: **Settings → System → Restart**
   - Via CLI: `ha core restart`

4. **Configure Integration:**
   - Follow step 3 from Method 1 above

### Method 3: Manual Installation from Source

For development or testing unreleased versions:

```bash
# From your Home Assistant config directory
cd /path/to/homeassistant/config
mkdir -p custom_components
cp -r /path/to/DALI-2-IoT4-integration/custom_components/lunatone_dali2_iot4 custom_components/
```

Or create a symbolic link for development:

```bash
cd /path/to/homeassistant/config/custom_components
ln -s /path/to/DALI-2-IoT4-integration/custom_components/lunatone_dali2_iot4 lunatone_dali2_iot4
```

Then restart Home Assistant and configure as described above.

## Verification

### Check Integration Loaded

## Verification

### Check Integration Loaded

After setup, verify the integration is working:

1. **Check Entities:**
   - Go to **Settings → Devices & Services**
   - Find "Lunatone DALI-2 IoT4"
   - Click on it to see all entities

2. **Expected Entities:**
   - **DALI light entities** for all detected devices (addresses 0-63)
     - Device Type 6: LED modules
     - Device Type 7: Switching function
     - Device Type 8: Color control with color temperature (2000K - 6500K)
   - **Binary sensors** for DALI2 input devices:
     - iT1: Push buttons with event detection
     - iT2: Switches with state tracking
     - iT3: Occupancy sensors (motion detection)
   - **Light sensors** (iT4) showing illuminance in lux
   - **Group entities** if configured (groups 0-15)
   - **Broadcast entity** for controlling all devices

3. **Test Basic Control:**
  - iT1: Push buttons with event detection
  - iT2: Switches with state tracking
  - iT3: Occupancy sensors (motion detection)
- **Light sensors** (iT4) showing illuminance in lux
- **Group entities** if configured (groups 0-63)
- **Broadcast entity** for controlling all devices

## Available Services

### Integration Services

**`lunatone_dali2_iot4.rescan_devices`**
- Rescans the DALI bus for new/changed devices
- Use when adding or removing devices from the bus

### Light Services

**`lunatone_dali2_iot4.step_up`**
- Increase brightness by one step
- Target: Individual light entities

**`lunatone_dali2_iot4.step_down`**
- Decrease brightness by one step
- Target: Individual light entities

**`lunatone_dali2_iot4.recall_max`**
- Turn light on to maximum brightness (100%)
- Target: Individual light entities

## Testing

### Test Light Control

```yaml
# In Developer Tools → Services

# Turn on light
service: light.turn_on
target:
  entity_id: light.dali_device_22  # Replace with your entity ID
data:
  brightness: 128

# Set color temperature (DT8 devices only)
service: light.turn_on
target:
  entity_id: light.dali_device_22  # Replace with DT8 device
data:
  color_temp: 370  # 2700K (mirek value)

# Step up brightness
service: lunatone_dali2_iot4.step_up
target:
  entity_id: light.dali_device_22

# Recall maximum
service: lunatone_dali2_iot4.recall_max
target:
  entity_id: light.dali_device_22

# Control group
service: light.turn_on
target:
  entity_id: light.dali_group_0  # Replace with your group number
data:
  brightness: 200

# Control all devices via broadcast
service: light.turn_on
target:
  entity_id: light.dali_broadcast
data:
  brightness: 255
```

### Test Device Rescan

```yaml
# Rescan for devices
service: lunatone_dali2_iot4.rescan_devices
```

## Troubleshooting

### No Devices Found

1. Check connection to gateway:
   ```bash
   # Replace 192.168.1.100 with your Lunatone DALI-2 IoT4 Gateway IP
   curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: test" \
     http://192.168.1.100:80
   ```

2. Check Home Assistant logs:
   ```bash
   ha core logs | grep lunatone_dali2_iot4
   ```

### Lights Not Responding

1. Enable debug logging in `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.lunatone_dali2_iot4: debug
   ```

2. Restart Home Assistant

3. Check logs for errors

### Integration Won't Load

1. Validate Python syntax:
   ```bash
   cd /path/to/DALI-2-IoT4-integration
   python3 -m py_compile custom_components/lunatone_dali2_iot4/*.py
   ```

2. Check manifest.json is valid:
   ```bash
   cat custom_components/lunatone_dali2_iot4/manifest.json | python3 -m json.tool
   ```

## Features Implemented

✅ **Device Discovery**
  - Automatic DALI bus scanning (addresses 0-63)
  - DALI2 instance detection (iT0-iT6)
  - Device type identification (DT6, DT7, DT8)
  - Device persistence in storage

✅ **Light Control**
  - Individual light entities for all DALI devices
  - Brightness control (0-100%)
  - On/Off control
  - Color temperature (2000K-6500K on DT8 devices)
  - Step up/down brightness
  - Recall maximum level
  - Group entities (groups 0-15)
  - Broadcast entity (control all devices)

✅ **DALI2 Binary Sensors**
  - iT1: Push buttons with event detection
  - iT2: Switches with state tracking
  - iT3: Occupancy sensors (motion detection)
  - Event types: released, pressed, short, double, long press (start/repeat/stop), stuck/free

✅ **DALI2 Sensors**
  - iT4: Light level sensors (illuminance in lux)
  - iT5: Colour sensors
  - iT6: General purpose sensors

✅ **Real-time Monitoring**
  - Bus command monitoring
  - External command detection (wall switches)
  - Group command synchronization
  - Broadcast command handling
  - Event-based updates

✅ **Advanced Features**
  - Configurable polling interval
  - Automatic reconnection
  - Config flow UI
  - Options flow for settings
  - Device registry integration
  - Service definitions
  - Repair flow for issues  

## Development

### Project Structure

```
custom_components/lunatone_dali2_iot4/
├── __init__.py           # Integration setup, services
├── manifest.json         # Integration metadata
├── strings.json          # Translation strings
├── config_flow.py        # Configuration UI
├── const.py              # Constants and DALI commands
├── coordinator.py        # Update coordinator
├── light.py              # Light platform (individual, group, broadcast)
├── binary_sensor.py      # Binary sensor platform (buttons, occupancy)
├── sensor.py             # Sensor platform (light level, etc.)
├── lunatone_api.py       # WebSocket API client
├── storage.py            # Device persistence
├── repairs.py            # Repair flow
└── services.yaml         # Service definitions
```

## Support

For issues or questions:
1. Enable debug logging in Home Assistant:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.lunatone_dali2_iot4: debug
   ```
2. Check logs: `ha core logs | grep lunatone_dali2_iot4`
3. Check CHANGELOG.md for version history
4. Report issues on GitHub
