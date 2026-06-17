# Release Notes — v0.2.0-beta-9

**The brightness slider now matches what your lamps can actually do.**

## Added

- Many LED drivers can't physically dim below a hardware **minimum level** —
  for example the EVN spots on this gateway bottom out at ~33%, so the lower
  third of the Home Assistant slider did nothing and the minimum showed as 33%.
- The integration now reads each lamp's **physical minimum** straight from the
  driver (DALI `QUERY PHYSICAL MINIMUM` — a read-only query, no light changes)
  and **remaps the brightness slider onto the usable range**:
  - the lamp's physical minimum becomes HA **"1%"** (lowest on-value),
  - full output stays **100%**,
  - everything in between is scaled accordingly.
- Result: the bottom of the slider equals the lamp's real minimum, the range
  feels linear, and HA no longer offers settings the driver would just clamp.
- Lamps **without** a meaningful floor (physical minimum = level 1, e.g. the
  Lunatone 24 V power supply) behave exactly as before.
- **Groups** use the most restrictive member as the floor. Detection runs in
  the **background** after startup and after a "Scan for devices".

## Notes

- This is a display/scaling improvement; it does not (and cannot) make a driver
  dim below its hardware minimum. To dim lower you would need a driver/luminaire
  with a lower physical minimum.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
