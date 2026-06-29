# Release Notes — v0.2.0-beta-17

**Notify instead of overwrite when a deployed blueprint was changed.**

## Added

- If the deployed Switch Manager blueprint has an unknown hash (edited by you
  or rewritten by Switch Manager), the integration keeps it and shows a
  **dismissible notification** pointing to the *Deploy Switch Manager
  Blueprints (Force)* button. The notification is gated by the shipped
  blueprint's hash, so once dismissed it only returns after a new blueprint
  version is released. Force deploy clears it.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
