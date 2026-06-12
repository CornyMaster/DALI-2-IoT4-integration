# Release Notes — v0.2.0-beta-4

**Automatic input device naming from the on-device description.**

## Added

- When a DALI-2 input device (push button coupler, sensor) is discovered,
  the integration now reads the **device description stored in the device
  itself** — the "Device Description" field in DALI Cockpit (memory bank 2)
  — and uses it as the Home Assistant device name. Your switch shows up as
  "Schalter_Küche_L" instead of "Line 0 Input 0".
- The read uses plain DALI queries via `POST /dali/sendDali24/{line}`
  (DTR1/DTR0 + READ MEMORY LOCATION); nothing is written to the bus devices.
- Fallback to the generic "Line X Input Y" name when no description is
  stored. Devices renamed manually in HA are never overwritten.

## Notes

To use this, write a description into each input device once via DALI
Cockpit (General tab → Device Description → save to device). Already
discovered devices keep their stored name; delete the HA device and press a
button to re-discover it with the new name.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
