# Release Notes - v0.1.2-beta

## 🎉 New Features

### Manual Scan Button
- Added dedicated **Manual Scan** button entity for on-demand device discovery
- Button appears under the gateway device for easy access
- Replaces the previous checkbox-based manual scan trigger in options

### Gateway Device
- Created proper gateway device entity: **"Lunatone DALI-2 IoT Gateway"**
- Shows manufacturer (Lunatone), model, and firmware information
- Includes configuration URL for quick access to the gateway web interface
- All integration controls (Manual Scan button, etc.) now grouped under gateway device

### Improved Configuration Options
All configuration options are now accessible via **Configure** button:

1. **Background Status Polling** (default: OFF)
   - Enable periodic polling of device states
   - Real-time WebSocket updates work independently of this setting
   - When disabled, relies entirely on WebSocket for state updates

2. **Polling Interval** (default: 1800 seconds / 30 minutes)
   - Configurable range: 5 minutes (300s) to 24 hours (86400s)
   - Only applies when background polling is enabled
   - Allows customization based on your needs

3. **Scan for New Devices on Startup** (default: OFF)
   - Automatically discover devices when Home Assistant starts
   - Now opt-in instead of automatic
   - Prevents startup delays by default

## 🔄 Changes

### Configuration Improvements
- Scan on startup is now **disabled by default** (was enabled in v0.1.1)
- Removed confusing "Activate device scanning now" option (use Manual Scan button instead)
- Background scanning removed - replaced with configurable polling interval
- All settings now clearly documented with descriptions

### Better UX
- Manual scanning is now a button press instead of checkbox toggle
- Gateway device properly named (no more "Unnamed device")
- Configuration options better organized and easier to understand

## 📝 Breaking Changes
- **Configuration options reset required**: Old options (scan_on_setup, enable_background_scan, scan_interval) are replaced with new options (scan_new_devices_on_startup, background_status_polling, polling_interval)
- After upgrading, reconfigure your preferences via **Configure** button

## 🐛 Bug Fixes
- Fixed gateway device showing as "Unnamed device"
- Fixed button entity not properly attached to gateway device

## 📚 Documentation
- Updated README with configuration options documentation
- Added clear descriptions for all settings in the UI

## ⬆️ Upgrade Instructions

1. **Update via HACS** or manually replace integration files
2. **Restart Home Assistant**
3. Go to **Settings → Devices & Services → Lunatone DALI-2 IoT Gateway**
4. Click **"Configure"** to review and update options:
   - Set **Background Status Polling** (recommend: OFF unless needed)
   - Set **Polling Interval** if you enabled polling
   - Set **Scan for New Devices on Startup** (recommend: OFF for faster startup)
5. Use the **Manual Scan** button to discover devices on demand

## 🔗 Links
- [GitHub Repository](https://github.com/Martsola/dali-lunatone-integration)
- [Issue Tracker](https://github.com/Martsola/dali-lunatone-integration/issues)
- [Installation Guide](https://github.com/Martsola/dali-lunatone-integration/blob/main/INSTALL.md)

---

**Full Changelog**: https://github.com/Martsola/dali-lunatone-integration/compare/v0.1.1-beta...v0.1.2-beta
