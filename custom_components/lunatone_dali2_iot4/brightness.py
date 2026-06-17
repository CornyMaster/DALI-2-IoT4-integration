"""HA <-> DALI brightness mapping that honors each driver's physical minimum.

The gateway's ``dimmable`` percent is linear in the DALI arc level
(``level = pct / 100 * 254``). A control-gear driver cannot dim below its
*physical minimum* level (DALI ``QUERY PHYSICAL MINIMUM``); for many LED drivers
that is well above 1 — e.g. the user's EVN spots floor at level 85 (~33%).

So that the Home Assistant slider spans the lamp's *usable* range instead of
wasting its lower third on unreachable levels, the usable level range
``[phys_min, 254]`` is mapped onto HA brightness ``[MIN_ON_BRIGHTNESS, 255]``:

* level ``phys_min`` -> HA brightness ``MIN_ON_BRIGHTNESS`` (3, renders as "1%")
* level ``254``      -> HA brightness 255 (100%)

HA's frontend renders brightness 1 as "0%", so the floor maps to 3 (HA's own
brightness for 1%) — the slider bottom then reads 1% and matches the lowest
value the user can actually set. When ``phys_min`` is 1 (or unknown) the mapping
is the plain linear default, so nothing changes for drivers without a floor.
"""

from __future__ import annotations

DALI_MAX_LEVEL = 254
# Lowest HA brightness for a lamp sitting at its physical minimum. HA's frontend
# renders brightness 1 as "0%"; using 3 (HA's own brightness for 1%) makes the
# bottom of the slider read 1% and match the lowest value the user can set.
MIN_ON_BRIGHTNESS = 3


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
        return MIN_ON_BRIGHTNESS
    span = DALI_MAX_LEVEL - phys_min_level
    return max(
        MIN_ON_BRIGHTNESS,
        min(
            255,
            round(
                MIN_ON_BRIGHTNESS
                + (level - phys_min_level) / span * (255 - MIN_ON_BRIGHTNESS)
            ),
        ),
    )


def ha_brightness_to_dimmable_pct(
    ha_brightness: int, phys_min_level: int
) -> float:
    """Map an HA brightness (1-255) to a gateway ``dimmable`` percent (0-100)."""
    if phys_min_level <= 1 or phys_min_level >= DALI_MAX_LEVEL:
        return round(ha_brightness / 255 * 100)
    if ha_brightness <= MIN_ON_BRIGHTNESS:
        return phys_min_level / DALI_MAX_LEVEL * 100
    span = DALI_MAX_LEVEL - phys_min_level
    level = phys_min_level + (ha_brightness - MIN_ON_BRIGHTNESS) / (
        255 - MIN_ON_BRIGHTNESS
    ) * span
    level = max(phys_min_level, min(DALI_MAX_LEVEL, round(level)))
    return level / DALI_MAX_LEVEL * 100
