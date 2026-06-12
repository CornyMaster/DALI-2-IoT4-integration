# Release Notes — v0.2.0-beta-2

**Phantom-input fix, input tracking option, basic scene support.**

## Fixed

- **Phantom input devices** ("Line X Input N" with a single "Button 31"
  entity and `unknown_event_53`): the 24-bit frame decoder treated the
  gateway's own DALI command frames (e.g. QUERY NUMBER OF INSTANCES to the
  instance broadcast) as button events. Events and command frames are now
  told apart per IEC 62386-103 (address byte LSB); only short-address +
  instance-number scheme events are decoded, using the full 10-bit event
  info.
- Input registry storage bumped to v2: v1 data (which may contain phantom
  devices) is discarded; inputs are rediscovered from real events.
- Stale devices can now be deleted from the Home Assistant UI.

## Added

- Option **"Track DALI-2 input devices"**: input tracking (entity creation
  and events from websocket bus traffic) can be disabled entirely.
- DALI scene support: entity services `recall_scene` and `store_scene`
  (scene 0-15) on device, group and broadcast lights — line-aware like all
  other commands.

## Upgrade from beta-1

Update via HACS, restart Home Assistant, then delete the phantom
"Line X Input N" devices on the integration's device page (now possible via
the UI). They will not come back.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
