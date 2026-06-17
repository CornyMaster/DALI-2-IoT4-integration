"""Unit tests for physical-minimum-aware brightness remapping."""

import pytest

from custom_components.lunatone_dali2_iot4.brightness import (
    dimmable_pct_to_ha_brightness as to_ha,
    ha_brightness_to_dimmable_pct as to_pct,
)

L = 254  # DALI max level


def lvl(pct):
    return pct / 100 * L


def test_identity_when_no_floor():
    # phys_min 1 (or unknown) -> plain linear mapping, unchanged behavior
    assert to_pct(128, 1) == 50
    assert to_ha(50.0, 1) == 128
    assert to_ha(100.0, 1) == 255
    assert to_ha(0.0, 1) == 0


def test_endpoints_with_floor_85():
    # level 85 -> HA 1 (lowest on), level 254 -> HA 255 (100%)
    assert to_pct(1, 85) == pytest.approx(85 / L * 100)      # HA 1 -> level 85
    assert to_pct(255, 85) == pytest.approx(100.0)            # HA 255 -> level 254
    assert to_ha(85 / L * 100, 85) == 1                       # level 85 -> HA 1
    assert to_ha(100.0, 85) == 255                            # level 254 -> HA 255


def test_below_floor_reads_as_one():
    # a (transient) reported level below the physical minimum clamps to HA 1
    assert to_ha(lvl(50) / L * 100 * 0 + 0.787, 85) == 1     # ~level 2 -> 1
    assert to_ha(10.0, 85) == 1                               # level ~25 < 85 -> 1


def test_off_stays_off():
    assert to_ha(0.0, 85) == 0
    assert to_ha(None, 85) is None


def test_midpoint_is_within_usable_range():
    # HA 128 with floor 85 must land between level 85 and 254 (not below floor)
    pct = to_pct(128, 85)
    assert 85 / L * 100 < pct < 100.0
    # round-trips back to ~128 (allow off-by-one from integer level rounding)
    assert abs(to_ha(pct, 85) - 128) <= 1
