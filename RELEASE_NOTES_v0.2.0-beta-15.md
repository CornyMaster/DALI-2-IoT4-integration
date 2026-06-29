# Release Notes — v0.2.0-beta-15

**Precise switch identity for Switch Manager.**

## Added

- Every `lunatone_dali2_iot4_event` now includes a stable `switch_uid`
  (unique per line + address). The bundled DALI-2 MC blueprint identifies
  couplers by `switch_uid` instead of the ambiguous DALI address, so two
  couplers with the same address on different lines no longer collide.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
