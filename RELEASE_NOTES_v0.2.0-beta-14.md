# Release Notes — v0.2.0-beta-14

**Fix: input devices never stay nameless.**

## Fixed

- When a DALI-2 input device has no stored description, or its memory-bank-2
  read fails, it now falls back to a stable "Line L Input A" name instead of an
  empty label. A successful description read still wins, and any manual rename
  is preserved. Use "Refresh input names" to re-read after fixing a coupler.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
