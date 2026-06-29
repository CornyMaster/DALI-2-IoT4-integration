# Release Notes — v0.2.0-beta-13

**Fix: Switch Manager blueprint deployment.**

## Fixed

- Auto-deploy now detects Switch Manager by its installed component and copies
  the bundled DALI-2 MC blueprint into `custom_components/switch_manager/blueprints/`.
  Previously it looked for a folder that does not exist on a fresh install, so
  nothing was deployed. Use the "Deploy Switch Manager Blueprints" button (or
  reload the integration), then `switch_manager.reload`.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
