# Lunatone DALI-2 IoT4 — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=CornyMaster&repository=DALI-2-IoT4-integration&category=integration)

Home Assistant custom integration for the **Lunatone DALI-2 IoT4 gateway**
(multi-line) and the classic single-line DALI-2 IoT gateway.

This is a fork of [Martsola/dali-lunatone-integration](https://github.com/Martsola/dali-lunatone-integration),
rewritten around the gateway's REST API to properly support **multiple DALI
lines**. The original integration was built for the single-line gateway:
DALI short addresses (0–63) and groups (0–15) repeat on every line, so on an
IoT4 the original entities collided and all commands went to line 0 only.

## How it works

- **Inventory & state via REST.** `GET /devices` is the source of truth: the
  gateway reports every device on every line with a unique id, its line,
  short address, groups and live state. No bus scanning from the integration;
  the optional "Scan for devices" button triggers the *gateway's own* scan
  (without re-addressing).
- **Control via REST.** Devices are controlled through their gateway id
  (`POST /device/{id}/control`), groups and broadcast per line
  (`POST /group/{g}/control?_line=N`, `POST /broadcast/control?_line=N`).
- **Realtime via websocket.** A passive listener merges status pushes between
  polls and decodes DALI-2 input events (push buttons, occupancy and light
  sensors) — including the line they happened on.

## Entities

| Entity | Per | unique_id pattern |
|---|---|---|
| Light (device) | line + address | `…_line{L}_dali_{A}` |
| Light (group) | line + group | `…_line{L}_group{G}` |
| Light (broadcast) | line (+ optional all-lines) | `…_line{L}_broadcast` |
| Binary sensor (button/switch/occupancy) | line + address + instance | `…_line{L}_input_{A}_inst{I}` |
| Sensor (light level) | line + address + instance | `…_line{L}_input_{A}_inst{I}` |
| Light (feedback LED) | line + address + instance | `…_line{L}_input_{A}_led_{I}` |
| Scene (DALI scene) | line + scene | `…_line{L}_scene{S}` |
| Button (gateway scan) | gateway | `…_manual_scan` |
| Button (refresh input names) | gateway | `…_refresh_input_names` |

unique_ids are based on the stable bus identity (line + address), so they
survive gateway re-scans that renumber internal device ids.

Each DALI group is its own Home Assistant device ("DALI Line X Group Y"), so
groups can be named and assigned to an area individually. The descriptive
group names from DALI Cockpit live only in the local Cockpit project and are
not exposed by the gateway, so rename group devices in HA as needed.

Device triggers for buttons/sensors are available per instance, and the
`lunatone_dali2_iot4_event` payload includes the `line`. Input devices are
named from the description stored in the device (DALI Cockpit "Device
Description"), read automatically on first discovery. The read is serialized
per line and retried on bus NAKs, so names are not truncated or garbled; use
the `refresh_input_names` service (or the "Refresh input names" button) to
re-read them on demand.

> **Discovering switches:** DALI-2 input devices (buttons/switches) are **not**
> found by the "Scan for devices" button — the gateway scan only enumerates
> control gear (lamps). Input devices are discovered **automatically when you
> physically press them** (the integration listens to bus events over the
> websocket). So to add a switch, press it once and it appears in HA. This also
> requires the DALI-2 MC to be configured to send events (see the wiki / DALI
> Cockpit setup), not just act as a direct application controller.

## Scenes

DALI scenes (0–15) are exposed as native Home Assistant **`scene.*` entities**,
one per `(line, scene)`, each on its own device "DALI Line X Scene Y". A scene
appears once at least one lamp on that line has a stored value for it; the scene
exposes its **member lamps and their stored levels** as attributes.

- **Activate:** `scene.turn_on`, the Scenes UI, a dashboard card or an
  automation. Activation recalls the DALI scene on the whole line via a single
  broadcast (fast, runs on the gateway).
- **Create / edit:** set the line's lamps as you want, then store the current
  state into the scene with the `store_scene` service on the **per-line
  broadcast light** (gateway `saveToScene`); use `set_scene_level` for an
  explicit per-device value. The scene entity updates immediately. Only lamps of
  a line can belong to that line's scene.
- These scenes are **not** editable in the HA scene editor (the pencil is
  greyed out) — that editor only edits scenes defined in `scenes.yaml`/storage.
  This is normal for integration-provided scenes (Hue, deCONZ, …).

## Configuration

1. Add the integration and enter the gateway host (and port).
2. The number of DALI lines is **detected automatically** from the gateway
   (`GET /info` → `descriptor.lines`: 4 on an IoT4, 1 on a DALI-2 IoT).
3. Select which lines the integration should manage (default: all).

Options (changeable later in the UI): managed lines, polling interval
(default 30 s; status changes also arrive in realtime via websocket), an
optional all-lines broadcast entity, and a switch to enable/disable
tracking of DALI-2 input devices (buttons/sensors).

## Services

- `lunatone_dali2_iot4.rescan_devices` — start the gateway's device scan
- `lunatone_dali2_iot4.refresh_input_names` — re-read all input-device names
  from the bus (repairs garbled/truncated names; manual renames are kept)
- `lunatone_dali2_iot4.step_up` / `step_down` / `recall_max` — entity services on lights
- `lunatone_dali2_iot4.recall_scene` / `store_scene` — recall (optionally with
  `fade_time`) or store a DALI scene (0-15) on a device, group or broadcast
  light (line-aware)
- `lunatone_dali2_iot4.set_scene_level` — write a device's stored scene value
  directly; stored values are shown in the `scenes` attribute of device lights
- `lunatone_dali2_iot4.set_feedback_led` — control a button's indicator LED by
  line / address / instance

## Requirements

- Lunatone DALI-2 IoT or IoT4 gateway, firmware 1.14.1+ (tested on 1.18.1)
- Home Assistant 2024.8 or newer

## Installation

**HACS (recommended):** click the badge above, or add
`https://github.com/CornyMaster/DALI-2-IoT4-integration` manually as a custom
repository (category "Integration") and install "Lunatone DALI-2 IoT4".

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=CornyMaster&repository=DALI-2-IoT4-integration&category=integration)

**Manual:** copy `custom_components/lunatone_dali2_iot4` into your Home Assistant
`config/custom_components/` directory and restart.

## Breaking changes vs. upstream (v0.2.0)

- All unique_ids changed (now line-aware). Existing entities from the
  upstream integration will appear as new entities; old ones can be removed.
- The integration-side bus scan (and its device storage) was removed entirely.
- `set_feedback_led` now takes `line`, `address`, `instance`, `state` instead
  of an entity id.
- Options `background_status_polling` and `scan_new_devices_on_startup` were
  removed; inventory polling is always on (default every 30 s).

## Development

```bash
python -m venv .venv
pip install pytest pytest-asyncio aioresponses "aiohttp<3.13"
pytest                      # unit tests (no gateway needed)

# optional: read-only tests against a real gateway
LUNATONE_GW_HOST=<gateway-ip> pytest -m gateway --override-ini addopts=

# Home Assistant integration tests (Linux/WSL only)
pip install pytest-homeassistant-custom-component
pytest tests/ha
```

Tests against a real gateway are strictly read-only (GET + passive websocket
listening); control paths are tested against mocks.
