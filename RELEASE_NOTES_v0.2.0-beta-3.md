# Release Notes — v0.2.0-beta-3

**Full DALI scene support.**

## Added

- `recall_scene` accepts an optional `fade_time` for smooth scene
  transitions (`sceneWithFade`), on device, group and broadcast lights.
- New entity service `set_scene_level`: write the stored value of a DALI
  scene (0-15) on a device light directly via `POST /device/{id}/scenes` —
  without changing the current light state. Omit the level to clear the
  scene from the device.
- Stored scene values are read from the gateway at startup and after scene
  writes, and exposed in the `scenes` attribute of every device light.

## Scene services overview

| Service | Targets | Effect |
|---|---|---|
| `recall_scene` (scene, fade_time?) | device / group / broadcast lights | activates the scene on the DALI bus, line-aware |
| `store_scene` (scene) | device / group / broadcast lights | stores the *current* level into the scene |
| `set_scene_level` (scene, level?) | device lights | writes the stored scene value directly |

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
