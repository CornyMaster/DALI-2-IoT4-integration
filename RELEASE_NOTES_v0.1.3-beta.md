# Release Notes - v0.1.3-beta

## 🐛 Bug Fixes

### Fixed DALI-2 Push Button Event Decoding
- **Fixed critical bug in push button event type decoding** that caused incorrect event identification
- The event info byte was incorrectly parsed by masking with `& 0x07` (extracting only lower 3 bits), but per IEC 62386-301, the full byte value uniquely identifies the event type — there is no separate counter/timing field for push buttons
- **Impact**: Several button events were decoded incorrectly:
  | Actual Event | Raw Value | Was Decoded As | Now Decoded As |
  |---|---|---|---|
  | Double press | 5 | "long_press_repeat" | "double_press" ✓ |
  | Long press start | 9 | "button_pressed" | "long_press_start" ✓ |
  | Long press repeat | 11 | "button_hold" | "long_press_repeat" ✓ |
  | Long press stop | 12 | "long_press_start" | "long_press_stop" ✓ |
  | Button free | 14 | "long_press_stop" | "button_free" ✓ |
- **Most notably**: `long_press_stop` was never detected — it was incorrectly decoded as `long_press_start`, making it impossible to detect when a long-pressed button was released

### Updated Event Type Map
- Corrected `BUTTON_EVENT_TYPES` dictionary to use proper IEC 62386-301 event info values:
  - `0` = button_released
  - `1` = button_pressed
  - `2` = short_press
  - `5` = double_press
  - `9` = long_press_start
  - `11` = long_press_repeat
  - `12` = long_press_stop
  - `14` = button_free (was stuck, now released)
  - `15` = button_stuck

### Fixed Button State Logic
- Button `state` (on/off) now correctly reflects active press states only: `button_pressed` (1), `long_press_start` (9), `long_press_repeat` (11)
- Removed incorrect `event_counter` field that was based on the wrong assumption of bit splitting

## 📝 Technical Details
- Reference: IEC 62386-301 specification and [python-dali](https://github.com/sde1000/python-dali) library (`dali/device/pushbutton.py`)
- Fix applies to both iT1 (Push Button) and iT2 (Absolute Input Device/Switch) instance types

## ⬆️ Upgrade Instructions

1. **Update via HACS** or manually replace integration files
2. **Restart Home Assistant**
3. No configuration changes needed — button events will now decode correctly

## 🔗 Links
- [GitHub Repository](https://github.com/Martsola/dali-lunatone-integration)
- [Issue Tracker](https://github.com/Martsola/dali-lunatone-integration/issues)
- [Installation Guide](https://github.com/Martsola/dali-lunatone-integration/blob/main/INSTALL.md)

---

**Full Changelog**: https://github.com/Martsola/dali-lunatone-integration/compare/v0.1.2-beta...v0.1.3-beta
