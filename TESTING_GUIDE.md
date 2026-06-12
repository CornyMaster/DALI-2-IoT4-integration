# Testing Guide

All tests against a real gateway are **strictly read-only**: GET requests and
passive websocket listening only. Control paths are tested against mocks; the
REST client used in live tests is constructed with `read_only=True`, which
makes any write raise an exception.

## Unit tests (no gateway, any OS)

```bash
python -m venv .venv
pip install pytest pytest-asyncio aioresponses "aiohttp<3.13"
pytest
```

Covers the line-aware models (using captured fixtures of a real 4-line IoT4
gateway with 51 devices), the REST client (URL/`_line`-query/body assertions),
and the websocket event decoder (all button/occupancy event types on lines
0-3, dedupe, reconnect).

## Home Assistant integration tests (Linux/WSL)

Home Assistant does not run on native Windows, so these tests skip there.

```bash
pip install pytest-homeassistant-custom-component
pytest tests/ha
```

Covers the coordinator (inventory, line filter, websocket merge, line-aware
`dali_lunatone_event`), light entities (unique ids, group aggregation,
line-targeted control) and the config flow (auto-detected line count,
line selection).

## Read-only tests against a real gateway (opt-in)

```bash
LUNATONE_GW_HOST=<gateway-ip> pytest -m gateway --override-ini addopts=
```

## Manual helpers

```bash
# Show every entity the integration would create, verify no unique_id
# collisions, then listen passively on the websocket for 15s:
python tests/manual/dry_run.py <gateway-ip>

# Capture raw websocket traffic (e.g. while pressing wall switches):
python tests/manual/ws_listen.py <gateway-ip> 90 capture.jsonl
```
