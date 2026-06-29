# Release Notes — v0.2.0-beta-16

**Fix: Switch Manager blueprint deploy path + auto reload.**

## Fixed

- Blueprints are deployed to `config/blueprints/switch_manager/`, the folder
  Switch Manager actually loads from, so the bundled DALI-2 MC blueprint
  (keyed on `switch_uid`) is the one in use. The deploy buttons now also call
  `switch_manager.reload` so changes apply without a restart.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
