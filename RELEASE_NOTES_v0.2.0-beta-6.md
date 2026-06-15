# Release Notes — v0.2.0-beta-6

**Device deletion, a button-name refresh button, and sorted switch buttons.**

## Changed

- **Any device of this integration can now be deleted from the Home Assistant
  UI** — lamp, group, switch or the gateway itself — not just stale/phantom
  devices. Note: a device that is still present on the bus reappears on the
  next gateway poll (or, for switches, on the next button press). To remove it
  permanently, deselect its line in the options, disable its entities, or
  remove the integration.

## Added

- **"Refresh input names" button** on the gateway device (shown when input
  tracking is enabled). It re-reads the names of all DALI-2 input devices from
  the bus — the same as the `refresh_input_names` service — to repair switch
  names that were stored garbled or truncated.

## Fixed

- A switch's **buttons are now listed in instance order** (Button 0, 1, 2, 3)
  instead of the order they happened to be pressed during discovery.

## Notes

- **Discovering switches:** DALI-2 input devices are *not* found by the "Scan
  for devices" button — that scan finds control gear (lamps) only. Switches are
  discovered automatically and continuously whenever you physically press them
  (the integration listens to bus events over the websocket); there is no scan
  window. Press each button once to make it appear.
- **Existing unsorted buttons:** entities already in the registry keep their
  order. To re-sort an existing switch, delete the input device (now possible)
  and restart Home Assistant — its buttons are recreated in order from the
  stored data.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
