"""HA <-> DALI brightness mapping that honors each driver's physical minimum.

The gateway's ``dimmable`` percent is linear in the DALI arc level
(``level = pct / 100 * 254``). A control-gear driver cannot dim below its
*physical minimum* level (DALI ``QUERY PHYSICAL MINIMUM``); for many LED drivers
that is well above 1 — e.g. the user's EVN spots floor at level 85 (~33%).

So that the Home Assistant slider spans the lamp's *usable* range instead of
wasting its lower third on unreachable levels, the usable level range
``[phys_min, 254]`` is mapped onto HA brightness ``[1, 255]``:

* level ``phys_min`` -> HA brightness 1   (the lowest on-value, "1%")
* level ``254``      -> HA brightness 255 (100%)

When ``phys_min`` is 1 (or unknown) the mapping is the plain linear default, so
nothing changes for drivers without a meaningful floor.
"""

from __future__ import annotations

DALI_MAX_LEVEL = 254


def dimmable_pct_to_ha_brightness(
    brightness_pct: float | None, phys_min_level: int
) -> int | None:
    """Map a gateway ``dimmable`` percent to an HA brightness (0-255)."""
    if brightness_pct is None:
        return None
    if brightness_pct <= 0:
        return 0
    if phys_min_level <= 1 or phys_min_level >= DALI_MAX_LEVEL:
        return max(1, min(255, round(brightness_pct / 100 * 255)))
    level = brightness_pct / 100 * DALI_MAX_LEVEL
    if level <= phys_min_level:
        return 1
    span = DALI_MAX_LEVEL - phys_min_level
    return max(1, min(255, round(1 + (level - phys_min_level) / span * 254)))


def ha_brightness_to_dimmable_pct(
    ha_brightness: int, phys_min_level: int
) -> float:
    """Map an HA brightness (1-255) to a gateway ``dimmable`` percent (0-100)."""
    if phys_min_level <= 1 or phys_min_level >= DALI_MAX_LEVEL:
        return round(ha_brightness / 255 * 100)
    span = DALI_MAX_LEVEL - phys_min_level
    level = phys_min_level + (ha_brightness - 1) / 254 * span
    level = max(phys_min_level, min(DALI_MAX_LEVEL, round(level)))
    return level / DALI_MAX_LEVEL * 100
