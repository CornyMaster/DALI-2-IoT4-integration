"""Unit tests for the turn-on preference store and control builder."""

from custom_components.lunatone_dali2_iot4.turn_on import (
    DEFAULT_MODE,
    OPTION_FIXED,
    OPTION_LAST_ACTIVE,
    OPTION_MAXIMUM,
    TurnOnPreferenceStore,
    build_turn_on_control,
    turn_on_key_broadcast,
    turn_on_key_device,
    turn_on_key_group,
)


def test_default_is_go_to_last_active():
    store = TurnOnPreferenceStore()
    pref = store.get("device:0:5")
    assert pref.mode == DEFAULT_MODE == OPTION_LAST_ACTIVE
    assert build_turn_on_control(pref) == {"gotoLastActive": True}


def test_maximum_builds_dimmable_100():
    store = TurnOnPreferenceStore()
    store.set_mode("g", OPTION_MAXIMUM)
    assert build_turn_on_control(store.get("g")) == {"dimmable": 100}


def test_fixed_without_fade_builds_dimmable():
    store = TurnOnPreferenceStore()
    store.set_mode("g", OPTION_FIXED)
    store.set_fixed("g", 42.0)
    assert build_turn_on_control(store.get("g")) == {"dimmable": 42.0}


def test_fixed_with_fade_builds_dimmable_with_fade():
    store = TurnOnPreferenceStore()
    store.set_mode("g", OPTION_FIXED)
    store.set_fixed("g", 30.0)
    store.set_fixed_fade("g", 2.5)
    assert build_turn_on_control(store.get("g")) == {
        "dimmableWithFade": {"fadeTime": 2.5, "dimValue": 30.0}
    }


def test_fade_only_applies_to_fixed_mode():
    """A fade value set while in last-active mode must not leak into control."""
    store = TurnOnPreferenceStore()
    store.set_fixed_fade("g", 5.0)  # mode still default (last active)
    assert build_turn_on_control(store.get("g")) == {"gotoLastActive": True}


def test_key_builders_are_distinct_and_stable():
    assert turn_on_key_device(0, 5) == "device:0:5"
    assert turn_on_key_group(2, 3) == "group:2:3"
    assert turn_on_key_broadcast(1) == "broadcast:1"
    assert turn_on_key_broadcast(None) == "broadcast:all"
    keys = {
        turn_on_key_device(0, 5),
        turn_on_key_group(0, 5),
        turn_on_key_broadcast(0),
    }
    assert len(keys) == 3
