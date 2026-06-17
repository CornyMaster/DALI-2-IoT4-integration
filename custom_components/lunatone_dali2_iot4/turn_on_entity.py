"""Shared discovery + base entity for the per-light turn-on config entities.

The select ("turn-on behavior") and the two numbers ("turn-on brightness" /
"turn-on fade time") all attach to the same HA devices as the lights and target
the same set of dimmable lamps / groups / broadcast lines. This module keeps
that discovery and device wiring in one place so the platforms stay thin.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import (
    LunatoneCoordinator,
    gear_device_identifier,
    group_device_identifier,
)
from .turn_on import (
    TurnOnPreference,
    turn_on_key_broadcast,
    turn_on_key_device,
    turn_on_key_group,
)

KIND_DEVICE = "device"
KIND_GROUP = "group"
KIND_BROADCAST = "broadcast"


@dataclass(frozen=True)
class TurnOnTarget:
    """A lamp / group / broadcast line that owns a turn-on preference."""

    kind: str
    line: int
    index: int  # device address or group number; 0 for broadcast

    @property
    def key(self) -> str:
        if self.kind == KIND_DEVICE:
            return turn_on_key_device(self.line, self.index)
        if self.kind == KIND_GROUP:
            return turn_on_key_group(self.line, self.index)
        return turn_on_key_broadcast(self.line)

    @property
    def unique_suffix(self) -> str:
        if self.kind == KIND_DEVICE:
            return f"line{self.line}_dali_{self.index}"
        if self.kind == KIND_GROUP:
            return f"line{self.line}_group{self.index}"
        return f"line{self.line}_broadcast"


def discover_targets(coordinator: LunatoneCoordinator) -> list[TurnOnTarget]:
    """Every dimmable lamp, every group, and every broadcast line."""
    data = coordinator.data
    targets: list[TurnOnTarget] = []
    if not data:
        return targets
    for device in data.devices.values():
        if device.supports_dimming:
            targets.append(TurnOnTarget(KIND_DEVICE, device.line, device.address))
    for line, group in sorted(data.groups_with_members()):
        if group <= 15:
            targets.append(TurnOnTarget(KIND_GROUP, line, group))
    for line in data.lines_with_devices():
        targets.append(TurnOnTarget(KIND_BROADCAST, line, 0))
    return targets


def _device_info_for(
    entry: ConfigEntry, target: TurnOnTarget, coordinator: LunatoneCoordinator
) -> DeviceInfo:
    """DeviceInfo matching the corresponding light entity (so they merge)."""
    if target.kind == KIND_DEVICE:
        data = coordinator.data
        device = (
            data.device_by_line_addr(target.line, target.index) if data else None
        )
        return DeviceInfo(
            identifiers={
                (DOMAIN, gear_device_identifier(entry.entry_id, target.line, target.index))
            },
            name=device.name
            if device
            else f"Line {target.line} DALI {target.index}",
            model=f"DALI line {target.line} address {target.index}",
            manufacturer="Lunatone",
            via_device=(DOMAIN, entry.entry_id),
        )
    if target.kind == KIND_GROUP:
        return DeviceInfo(
            identifiers={
                (DOMAIN, group_device_identifier(entry.entry_id, target.line, target.index))
            },
            name=f"DALI Line {target.line} Group {target.index}",
            model="DALI Group",
            manufacturer="Lunatone",
            via_device=(DOMAIN, entry.entry_id),
        )
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_broadcast")},
        name="DALI Broadcast",
        model="DALI Broadcast Controller",
        manufacturer="Lunatone",
        via_device=(DOMAIN, entry.entry_id),
    )


class TurnOnConfigEntity(CoordinatorEntity[LunatoneCoordinator]):
    """Base for the turn-on select/number entities (CONFIG, device-grouped)."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        entry: ConfigEntry,
        target: TurnOnTarget,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._target = target
        self._store = coordinator.turn_on_store

    @property
    def _pref(self) -> TurnOnPreference:
        return self._store.get(self._target.key)

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info_for(self._entry, self._target, self.coordinator)
