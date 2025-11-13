# Release Notes - Lunatone DALI-2 IoT Integration v0.1.1-beta

**Release Date:** November 13, 2025

## Overview

Version 0.1.1-beta introduces comprehensive device information support for both DALI1 and DALI2 devices, including manufacturer detection, proper serial number decoding, and enhanced device metadata display in Home Assistant.

## 🎉 Major Features

### 1. **DALI1 Memory Bank 0 Support**
- Extended device information reading now works for **both DALI1 and DALI2** devices
- Correctly implements IEC 62386-102 Memory Bank 0 reading for DALI1 devices
- Handles special checksum byte behavior (address 0x01)

### 2. **Enhanced Device Information**
All device information now displayed in Home Assistant device pages:
- **GTIN** (Global Trade Item Number) - shown in decimal format
- **Manufacturer** - automatically detected from GTIN prefix
- **Firmware Version** - smart formatting (e.g., "3.12" instead of "3.12.0.0")
- **Hardware Version**
- **Serial Number** - correctly decoded from 64-bit ID field

### 3. **Manufacturer Detection**
Automatic manufacturer identification for:
- **Osram** (GTIN: 4062172*, 4052899*)
- **Sunricher** (GTIN: 6971542*)
- **Signify** (GTIN: 8718696*)
- **LTECH** (GTIN: 6971379110529)
- **Lunatone** (GTIN: 9010342*)
- **Tridonic** (GTIN: 9006210*)

### 4. **Improved Device Naming**
- Devices now use simplified naming: **"[Protocol] Address [N]"**
- Examples: "DALI Address 0", "DALI2 Address 1"
- Cleaner and more consistent across all entity types

### 5. **Feedback LED Support** (from v0.1.0-beta)
- Automatic detection of feedback indicator LED support on DALI2 devices
- New service `dali_lunatone.set_feedback_led` for LED control
- Binary sensors expose LED capabilities via attributes

## 🔧 Technical Improvements

### DALI1 Memory Bank Implementation
- **DTR0 (0xA3)**: Sets memory address
- **DTR1 (0xC3)**: Sets memory bank
- **READ (0xC5)**: Reads current location with auto-increment
- Proper handling of checksum byte (continues reading despite no response)

### Data Format Enhancements
- **GTIN**: Converted from hex to decimal (13-digit numbers)
- **Serial Number**: Extracted from bytes 2-5 of 64-bit ID as big-endian 32-bit integer
- **Empty Values**: All-zero GTINs (000000000000) are hidden
- **Firmware/Hardware**: Smart version formatting

### New API Methods
- `read_dali1_device_info()` - Memory Bank 0 reading for DALI1
- `gtin_hex_to_decimal()` - GTIN format conversion
- `get_manufacturer_from_gtin()` - Manufacturer lookup
- `format_serial_number()` - Serial number decoding
- `format_firmware_version()` - Version string formatting
- `format_hardware_version()` - Hardware version formatting

### Device Properties
- `device.gtin_decimal` - GTIN as decimal string
- `device.manufacturer` - Manufacturer name from GTIN
- `device.serial_number` - Serial number as decimal string

## 📊 What's Changed

### Device Information Display
**Before:**
- Limited device info only for DALI2
- GTIN in hex format (e.g., "03AFA3A8F650")
- Serial number shown as full 64-bit hex
- No manufacturer information

**After:**
- Device info for both DALI1 and DALI2
- GTIN in decimal format (e.g., "4052899919440")
- Serial number correctly decoded (e.g., "118961")
- Manufacturer name displayed (e.g., "Osram")
- Empty values hidden

### Example Device Info
```
DALI Address 10
  Manufacturer: Osram
  Model: DALI DT6 (GTIN: 4052899919440)
  Software Version: 2.11.53.20
  Serial Number: 4247640312
```

## 🐛 Bug Fixes

- Fixed DALI1 Memory Bank 0 reading (was failing for all DALI1 devices)
- Fixed serial number decoding (now extracts correct bytes)
- Fixed GTIN display format (now decimal instead of hex)
- Fixed empty device info handling (zeros no longer shown)

## 📦 Installation

### Requirements
- Home Assistant 2023.8.0 or newer
- Lunatone DALI-2 IoT Gateway (firmware version tested: varies)
- Python 3.11 or newer

### Installation Methods

#### Method 1: Manual Installation
```bash
# Copy the release package to your Home Assistant device
scp dali_lunatone_v0.1.1-beta.tar.gz user@homeassistant:/config/

# SSH into Home Assistant and extract
cd /config/custom_components/
tar -xzf ../dali_lunatone_v0.1.1-beta.tar.gz

# Restart Home Assistant
```

#### Method 2: HACS (Coming Soon)
This integration will be available through HACS in a future release.

### Upgrading from v0.1.0-beta

**Important:** Device registries will be recreated with new naming format.

1. Backup your Home Assistant configuration
2. Remove old integration files
3. Install v0.1.1-beta package
4. Clear device and entity registries (optional, for clean names):
   ```bash
   rm /config/.storage/core.device_registry
   rm /config/.storage/core.entity_registry
   ```
5. Restart Home Assistant
6. Integration will reload with new device names and information

## 🧪 Testing

The integration has been tested with:
- **DALI1 Devices**: DT6 (LED modules), DT7 (Switching), DT8 (Color control)
- **DALI2 Devices**: Instance Controllers, Application Controllers
- **Manufacturers**: Osram, Sunricher, Lunatone devices confirmed working
- **Memory Bank Reading**: Tested on 38 devices (mix of DALI1 and DALI2)

## 📝 Known Issues

- Some DALI1 devices may not implement Memory Bank 0 (optional feature)
- Manufacturer detection requires valid GTIN - devices with all-zero GTIN won't show manufacturer
- Hardware version not widely reported by devices

## 🔮 Future Enhancements

Planned for future releases:
- Additional manufacturer GTIN prefixes
- Device model name detection
- Extended memory bank support
- Device capability detection enhancements

## 📚 Documentation

- [README.md](README.md) - Main documentation
- [INSTALL.md](INSTALL.md) - Installation guide
- [CHANGELOG.md](CHANGELOG.md) - Full change history
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines

## 🙏 Acknowledgments

Special thanks to the users who helped test and identify the serial number decoding issue!

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/martsola/dali-lunatone-integration/issues)
- **Discussions**: [GitHub Discussions](https://github.com/martsola/dali-lunatone-integration/discussions)

---

**Note:** This is a beta release. Please report any issues on GitHub.
