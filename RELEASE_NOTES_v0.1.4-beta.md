# Release Notes - v0.1.4-beta

## 🐛 Bug Fixes

### Fixed DALI Device Type Iterator Invalidation (Critical)
- **Root cause**: Per IEC 62386-102, `QUERY NEXT DEVICE TYPE` (cmd 167) must be sent immediately after `QUERY DEVICE TYPE` with **no intervening DALI commands**. Any other command — including `QUERY STATUS` — resets the device type iterator inside the gear firmware.
- **Previous behaviour**: The scan code sent a `QUERY STATUS` command between `QUERY DEVICE TYPE` and the first `QUERY NEXT DEVICE TYPE`, which silently reset the iterator. Devices at addresses 25–27 were consequently detected as DT6 only, losing CCT colour control entirely.
- **Fix**: Removed the intermediate `QUERY STATUS` step. The MASK (0xFF) response to `QUERY DEVICE TYPE` is itself proof of device presence; no additional confirmation query is needed.
- Verified via Lunatone DALI Cockpit TCP capture — the Cockpit sends `QUERY NEXT DEVICE TYPE` with only DALI-bus RTT (~50 ms) between calls, zero extra sleep.

### Corrected `CMD_QUERY_NEXT_DEVICE_TYPE` Constant
- The constant was `154` (0x9A) — **completely wrong command number**.
- Correct value is **`167` (0xA7)**, confirmed via Wireshark capture of Lunatone DALI Cockpit.
- This caused devices 40–49 to previously appear as DT85 instead of DT8 (Colour control).

### Reduced Iterator Loop Sleep
- Loop sleep between `QUERY NEXT DEVICE TYPE` calls reduced from **100 ms → 20 ms**.
- Some device firmware has an iterator timeout of ~80 ms; the previous 100 ms sleep caused the iterator to expire before the next call arrived.

### Dynamic Light Entity Creation After Scan
- Light entities are now created dynamically when a Manual Scan detects DT6/DT7/DT8 devices that didn't exist in coordinator data at startup.
- Previously, devices stored with old/wrong types (e.g. DT1) at startup would never appear as lights even after a corrective rescan.

### CCT Color Mode Refresh
- `LunatoneDaliLight` now calls `_update_color_mode()` on every coordinator data update.
- An entity initially created as brightness-only (DT6) will automatically gain CCT controls after being rescanned as DT8 — no restart required.

### Fixed `KeyError` in Background State Update
- `update_device_states()` used an unguarded `self._devices[(protocol, address)]` dict access. If the device list changed mid-iteration (e.g. during a concurrent scan) this raised a `KeyError`, logged as `"Error during background state update: ('DALI', 40)"`.
- Fixed with a safe `.get()` + `continue` guard.

### Fixed `KeyError` in `LunatoneDaliLight.__init__`
- The entity constructor used `coordinator.data[self._device_key]` which could raise `KeyError` if the device was not yet present.
- Replaced with the safe `_update_color_mode()` helper that uses `.get()`.

### Improved Error Logging
- Background state update errors now log with `_LOGGER.exception()` instead of `_LOGGER.error("...: %s", e)`, so the full stack trace is visible in the log.

---

## 📊 Device Detection — Before & After

| Addresses | Before v0.1.4 | After v0.1.4 |
|---|---|---|
| 25–27 | DT6 (brightness only) ❌ | DT6,8,50,51,52 — CCT ✓ |
| 40–49 | DT85 (wrong type) ❌ | DT6,8 — CCT ✓ |

---

## ⬆️ Upgrade Instructions

1. **Update via HACS** or manually replace integration files
2. **Restart Home Assistant**
3. Run **Manual Scan** from the integration options — new CCT entities will appear automatically for addresses 25–27 and 40–49
4. No configuration changes needed

---

## 🔗 Links
- [GitHub Repository](https://github.com/Martsola/dali-lunatone-integration)
- [Issue Tracker](https://github.com/Martsola/dali-lunatone-integration/issues)
- [Installation Guide](https://github.com/Martsola/dali-lunatone-integration/blob/main/INSTALL.md)

---

**Full Changelog**: https://github.com/Martsola/dali-lunatone-integration/compare/v0.1.3-beta...v0.1.4-beta
