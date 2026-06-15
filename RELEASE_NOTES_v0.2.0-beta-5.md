# Release Notes — v0.2.0-beta-5

**Individual group devices and reliable input-device names.**

## Changed

- **Each DALI group is now a separate Home Assistant device.** Until now all
  groups of a line were bundled under one "DALI Line X Groups" device. Every
  group now appears as its own device — "DALI Line X Group Y" — so you can
  rename it and assign it to an area independently.
- Entity unique_ids are unchanged (`…_line{L}_group{G}`), so existing history,
  dashboards and automations keep working. After the upgrade the old bundling
  device is empty and can be removed via the Home Assistant UI ("Delete
  device").

## Fixed

- **Garbled or truncated switch names** (for example "Schalter_Wohnzimme"
  instead of "Schalter_Wohnzimmer_O", or random characters): reading the
  on-device description from memory bank 2 is now robust against the DALI bus.
  - Raw 24-bit traffic is serialized per line. Setting the transfer registers
    (DTR0/DTR1) uses the broadcast address, so two reads on the same line used
    to reset each other's read pointer and corrupt the result.
  - A missing per-byte answer (a DALI NAK, returned as `null`) is no longer
    taken as the end of the name; the read is retried instead of being cut
    short, and bytes that are not valid UTF-8 are rejected.
  - Each request re-seeks the read pointer instead of relying on
    auto-increment surviving between separate HTTP requests.

## Added

- New service **`lunatone_dali2_iot4.refresh_input_names`** re-reads the names
  of all DALI-2 input devices from the bus. Run it once after upgrading to
  repair switch names that an earlier release stored garbled or truncated.
  Names you renamed by hand are never overwritten.

## Upgrade notes

- Reload the integration (or restart Home Assistant) so the per-group devices
  are created.
- Call `lunatone_dali2_iot4.refresh_input_names` once (Developer Tools →
  Actions) to fix any previously corrupted switch names.
- Group devices have generic names ("DALI Line X Group Y") — the descriptive
  group names from DALI Cockpit are stored only in the local Cockpit project
  and are not available from the gateway, so rename the group devices in Home
  Assistant as you like.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
