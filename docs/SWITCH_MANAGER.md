# Switch Manager — DALI-2 push-button couplers

This integration fires a `lunatone_dali2_iot4_event` for every DALI-2 input
event, so physical DALI push buttons (e.g. the Lunatone **DALI-2 MC**) can be
mapped centrally with the HACS add-on
[Switch Manager](https://github.com/Sian-Lee-SA/Home-Assistant-Switch-Manager)
instead of cluttering your automations. A ready-made blueprint is bundled in
[`switch_manager/`](../switch_manager/).

## Install Switch Manager

1. HACS → custom repository `Sian-Lee-SA/Home-Assistant-Switch-Manager` (type
   *Integration*) → install → restart HA.
2. Settings → Devices & Services → **Add integration** → *Switch Manager*.
3. A blueprint folder is created at `config/blueprints/switch_manager/`.

## Add the bundled blueprint

The blueprint + image ship with the integration
(`custom_components/lunatone_dali2_iot4/blueprints/`). When Switch Manager is
installed, the integration **auto-deploys** them to
`config/blueprints/switch_manager/` on setup/update (it never overwrites files
you changed). To re-copy the originals manually, press the **Deploy Switch
Manager Blueprints** button on the gateway device, then `switch_manager.reload`.
Updates are safe: only missing files and known previous bundled versions are
refreshed (tracked via `known_hashes.json`), so edited copies are left alone.
Use **Deploy Switch Manager Blueprints (Force)** to overwrite unconditionally.
The blueprint appears under **Add Switch** as *Lunatone DALI-2 → DALI-2 MC*.

## Bind a coupler

- **Add Switch** → pick *DALI-2 MC* → open the identifier dialog → auto-discover
  → press any button → it fills `device_address` (the coupler's DALI address).
- T1–T4 map to `instance` 0–3; COM is common only (no button).
- Save, then test. Each button supports: press, press 2x, hold, hold repeat,
  hold (released), stuck.

| Field | Event key | Notes |
|-------|-----------|-------|
| Switch identifier | `device_address` | coupler DALI address |
| Button T1–T4 | `instance` 0–3 | one button each |
| Type filter | `instance_type` = 1 | push button |
| Action | `event_type` | short_press / double_press / long_press_start / long_press_repeat / long_press_stop / button_stuck |

## Multiple couplers / lines

Add the switch once per coupler; the identifier (`device_address`) keeps them
apart. If the same address exists on different lines, add a switch variable
`line` and a root condition `key: line` so events are scoped to that line.

## Notes

- Enable **Double press** on the coupler (DALI config) if you want `press 2x`;
  it is off by default.
- Couplers are discovered after the first button press; ensure *Track inputs*
  stays enabled in the integration options.
