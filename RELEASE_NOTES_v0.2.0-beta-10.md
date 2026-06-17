# Release Notes — v0.2.0-beta-10

**Floored lamps now read 1% at the bottom of the slider, not 0%.**

## Fixed

- After v0.2.0-beta-9, a lamp sitting at its physical minimum (e.g. the EVN
  spots) showed **0%** in Home Assistant, even though the slider only let you
  set down to **1%** — display and lowest settable value disagreed.
- Cause: the physical minimum was mapped to HA brightness 1, which the frontend
  renders as "0%". It now maps to HA's own brightness for 1%, so the bottom of
  the slider reads **1%** and matches the lowest value you can set.

This is a small display/scaling correction on top of beta-9; no behavior change
for lamps without a physical-minimum floor.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
