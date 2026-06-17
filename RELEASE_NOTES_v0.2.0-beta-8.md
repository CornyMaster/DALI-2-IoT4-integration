# Release Notes — v0.2.0-beta-8

**Choose how each lamp/group switches on — last active level, maximum, or a fixed value.**

## Added

- Switching a light, group or broadcast line on in Home Assistant **without an
  explicit brightness** now goes to its **last active level** by default
  (DALI `gotoLastActive` — the "GOTO LAST ACTIVE LEVEL" action) instead of
  jumping to maximum.
- Each dimmable lamp, group and broadcast line gains three **config entities**
  under its existing device:
  - a **select "Turn-on behavior"** — *Last active level* / *Maximum* /
    *Fixed value*,
  - a **number "Turn-on brightness"** (%) used when the behavior is
    *Fixed value*, and
  - a **number "Turn-on fade time"** (s) applied to that fixed value
    (`0` = no fade; uses DALI `dimmableWithFade`).
- The choice is remembered **per lamp/group/broadcast** and restored across
  restarts. Existing lamps/groups/broadcasts pick the new entities up
  **automatically** on the next start — no re-import or reconfiguration needed.

## How to use

1. Open a lamp's (or group's) device page in Home Assistant.
2. In its **Configuration** section set **"Turn-on behavior"**:
   - *Last active level* (default) — restores the brightness it had before,
   - *Maximum* — full brightness,
   - *Fixed value* — use **"Turn-on brightness"** (and optionally
     **"Turn-on fade time"**).
3. From then on, toggling that light on without a brightness follows the choice.

## Notes

- The fade time only applies to the *Fixed value* behavior; *Last active level*
  and *Maximum* switch on without a fade.

**Full Changelog**: https://github.com/CornyMaster/DALI-2-IoT4-integration/blob/main/CHANGELOG.md
