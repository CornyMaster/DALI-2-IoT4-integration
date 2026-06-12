# Release Notes — v0.2.0-beta-1

**Project renamed to DALI-2 IoT4 integration: full multi-line support.**

This release is a rewrite of the integration around the gateway's REST API.
The previous architecture was built for the single-line DALI-2 IoT gateway —
`line=0` was hardcoded in every command, device keys and unique_ids carried
no line, and the integration-side bus scan only covered line 0. On a 4-line
IoT4 gateway this meant colliding entities and commands that always went to
line 0.

## Highlights

- **Multi-line support**: devices, groups, broadcast, button events and
  device triggers are separated per DALI line. The same short address or
  group number on different lines maps to different entities.
- **Line selection in the UI**: the line count is auto-detected from the
  gateway (`GET /info` → `descriptor.lines`) and the managed lines are
  selectable during setup and later in the options.
- **REST-based inventory**: `GET /devices` is the source of truth, including
  live state — entities now show real on/brightness state instead of an
  assumed one. The fragile integration-side bus scan is gone; the scan
  button triggers the gateway's own non-destructive scan.
- **Line-aware control**: devices via `POST /device/{id}/control`, groups via
  `POST /group/{g}/control?_line=N`, broadcast per line (plus an optional
  all-lines broadcast entity).
- **Realtime**: a passive websocket listener merges status pushes between
  polls and decodes DALI-2 input events including their line.
- **Group state aggregation**: group lights derive on/brightness from their
  member devices.

## Breaking changes

- All unique_ids changed (now line-aware: `…_line{L}_dali_{A}` etc.).
  Entities created by 0.1.x appear as new entities; remove the old ones.
- `set_feedback_led` now takes `line`, `address`, `instance`, `state`.
- Options `background_status_polling` and `scan_new_devices_on_startup` were
  removed; inventory polling is always on (default 30 s, configurable).
- The `websockets` Python dependency was dropped (aiohttp only).

## Upgrade notes

Remove the old integration entry, install this version, and re-add the
gateway. The config flow will detect the lines automatically.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
