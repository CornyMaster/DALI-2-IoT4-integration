# Release Notes — v0.2.0-beta-11

**A round of correctness fixes: clean broadcast devices, accurate group state,
and multi-gateway-safe services.**

## Fixed

- **Each broadcast now has its own device.** The per-line broadcasts (and the
  optional all-lines broadcast) previously shared a single "DALI Broadcast"
  device, so every line landed on the same card. They are now split into one
  device per line (plus a separate all-lines device). Existing setups are
  migrated automatically: the entities keep their IDs and history, and the old
  shared device is removed on update — nothing to clean up by hand.
- **Groups and broadcasts no longer show "off" while their state is unknown.**
  At startup, before the first poll, a group/broadcast with no known member
  state reported *off*; it now reports *unknown* and switches to on/off only
  once a member is known.
- **Services work with more than one gateway.** `rescan_devices`,
  `set_feedback_led` and `refresh_input_names` now reach every configured
  gateway instead of only the first, and are removed cleanly when the last
  gateway is unloaded (no leftover services pointing at a gone setup).
- **Rapid button taps no longer cut each other short.** A momentary button
  reset is now tied to the latest press, so quick repeats don't get reset early.
- **More robust event de-duplication.** Monitor frames that arrive without a
  timestamp use a monotonic clock for the dedupe window instead of falling back
  to zero.

## Notes

- Config entry version bumped to 3 (broadcast device migration). No
  re-configuration needed; behavior for lamps without a physical-minimum floor
  is unchanged.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
