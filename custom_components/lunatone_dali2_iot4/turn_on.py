"""Per-light "turn-on behavior" preference (no explicit brightness given).

When a lamp/group/broadcast is switched on in HA without a brightness, the
gateway needs to be told *what* level to go to. The DALI bus offers three
useful answers, all natively supported by the gateway's ``ControlData`` schema:

* ``gotoLastActive`` -> GO TO LAST ACTIVE LEVEL (the level the lamp had before
  it was switched off; identical to the "GOTO LAST ACTIVE LEVEL" button action
  on a DALI-2 MC), and
* ``dimmable: 100`` -> recall the maximum level, or
* ``dimmable: <pct>`` (optionally ``dimmableWithFade``) -> a fixed level.

The gateway does not persist *which* of these HA should use, so the choice is
held here per (line, address) / (line, group) / (line) target and restored
across restarts by the select/number entities that expose it. The store itself
lives on the coordinator so light/select/number entities reach it via
``self.coordinator.turn_on_store``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Select option strings (also the stored state of the select entity).
OPTION_LAST_ACTIVE = "Last active level"
OPTION_MAXIMUM = "Maximum"
OPTION_FIXED = "Fixed value"

TURN_ON_OPTIONS = [OPTION_LAST_ACTIVE, OPTION_MAXIMUM, OPTION_FIXED]

# Default: go to the last active level (matches "switch on to whatever it was").
DEFAULT_MODE = OPTION_LAST_ACTIVE
DEFAULT_FIXED_PCT = 100.0
DEFAULT_FIXED_FADE = 0.0


@dataclass
class TurnOnPreference:
    """How one target should switch on when no brightness is supplied."""

    mode: str = DEFAULT_MODE
    fixed_pct: float = DEFAULT_FIXED_PCT
    fixed_fade: float = DEFAULT_FIXED_FADE


class TurnOnPreferenceStore:
    """In-memory map of target key -> TurnOnPreference (one per config entry)."""

    def __init__(self) -> None:
        self._prefs: dict[str, TurnOnPreference] = {}

    def get(self, key: str) -> TurnOnPreference:
        """Return the preference for ``key``, creating a default on first use."""
        return self._prefs.setdefault(key, TurnOnPreference())

    def set_mode(self, key: str, mode: str) -> None:
        self.get(key).mode = mode

    def set_fixed(self, key: str, percent: float) -> None:
        self.get(key).fixed_pct = percent

    def set_fixed_fade(self, key: str, fade: float) -> None:
        self.get(key).fixed_fade = fade


def build_turn_on_control(pref: TurnOnPreference) -> dict[str, Any]:
    """Translate a preference into a gateway ControlData payload."""
    if pref.mode == OPTION_MAXIMUM:
        return {"dimmable": 100}
    if pref.mode == OPTION_FIXED:
        if pref.fixed_fade > 0:
            return {
                "dimmableWithFade": {
                    "fadeTime": pref.fixed_fade,
                    "dimValue": pref.fixed_pct,
                }
            }
        return {"dimmable": pref.fixed_pct}
    # Default / OPTION_LAST_ACTIVE
    return {"gotoLastActive": True}


# Stable target keys, mirroring the light entities' unique-id scheme. Kept
# bus-based (line/address/group) so they survive gateway re-scans that renumber
# gateway ids.
def turn_on_key_device(line: int, address: int) -> str:
    return f"device:{line}:{address}"


def turn_on_key_group(line: int, group: int) -> str:
    return f"group:{line}:{group}"


def turn_on_key_broadcast(line: int | None) -> str:
    return f"broadcast:{line if line is not None else 'all'}"
