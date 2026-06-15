# Release Notes — v0.2.0-beta-7

**DALI scenes as native Home Assistant scenes.**

## Added

- Each configured DALI scene is now a native **`scene.*` entity** on its own
  device "DALI Line X Scene Y". Activate it from anywhere Home Assistant
  handles scenes — `scene.turn_on`, the Scenes list, dashboard cards,
  automations and scripts. Activation recalls the scene on the **whole line**
  via a single broadcast (fast, runs on the gateway).
- A scene appears **automatically** as soon as at least one lamp on the line
  has a stored value for it, so empty scenes don't clutter the UI.
- Each scene shows **which lamps belong to it and at which level** via the
  `members` / `member_count` attributes.
- Scenes are kept up to date: the "Scan for devices" button / `rescan_devices`
  service re-reads stored scenes, and a broadcast/group `store_scene` refreshes
  that line's scenes immediately — newly created or edited scenes show up
  without extra steps.

## How to create / edit a scene

1. Set the line's lamps as you want them (normal HA light controls).
2. Call `lunatone_dali2_iot4.store_scene` on the **per-line broadcast light**
   with `scene: N` (gateway `saveToScene`); use `set_scene_level` for an
   explicit per-device value.
3. The scene entity and its member list update immediately.

Only lamps of a line can belong to that line's scene.

## Notes

- These scenes are **not** editable in the Home Assistant scene editor (the
  pencil is greyed out — "only scenes defined in scenes.yaml are editable").
  That is normal for integration-provided scenes (Hue, deCONZ, …); edit the
  DALI scene content via `store_scene` / `set_scene_level` instead.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
