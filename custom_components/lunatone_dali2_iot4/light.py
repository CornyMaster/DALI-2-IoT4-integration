"""Light platform for the Lunatone DALI-2 IoT(4) integration.

Every entity is line-aware: device lights are identified by their stable bus
identity (line, address), group lights exist once per (line, group), and
broadcast lights exist once per line (plus an optional all-lines entity).
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ENABLE_GLOBAL_BROADCAST,
    DATA_COORDINATOR,
    DOMAIN,
    MAX_COLOR_TEMP_KELVIN,
    MIN_COLOR_TEMP_KELVIN,
)
from .coordinator import (
    LunatoneCoordinator,
    broadcast_device_identifier,
    gear_device_identifier,
    group_device_identifier,
    input_device_identifier,
    scene_control,
)
from .brightness import (
    dimmable_pct_to_ha_brightness,
    ha_brightness_to_dimmable_pct,
)
from .models import LunatoneDevice
from .turn_on import (
    build_turn_on_control,
    turn_on_key_broadcast,
    turn_on_key_device,
    turn_on_key_group,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up line-aware DALI light entities."""
    coordinator: LunatoneCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    known_devices: set[tuple[int, int]] = set()
    known_groups: set[tuple[int, int]] = set()
    known_broadcast_lines: set[int] = set()
    known_leds: set[tuple[int, int, int]] = set()
    global_broadcast_added = False

    @callback
    def _async_sync_entities() -> None:
        """Create entities for anything new in coordinator data."""
        nonlocal global_broadcast_added
        data = coordinator.data
        if not data:
            return
        new_entities: list[LightEntity] = []

        for device in data.devices.values():
            key = (device.line, device.address)
            if key not in known_devices:
                known_devices.add(key)
                new_entities.append(
                    LunatoneDeviceLight(coordinator, entry, device.line, device.address)
                )

        for line, group in sorted(data.groups_with_members()):
            if group <= 15 and (line, group) not in known_groups:
                known_groups.add((line, group))
                new_entities.append(
                    LunatoneGroupLight(coordinator, entry, line, group)
                )

        for line in data.lines_with_devices():
            if line not in known_broadcast_lines:
                known_broadcast_lines.add(line)
                new_entities.append(
                    LunatoneBroadcastLight(coordinator, entry, line)
                )

        if not global_broadcast_added and entry.options.get(
            CONF_ENABLE_GLOBAL_BROADCAST, False
        ):
            global_broadcast_added = True
            new_entities.append(LunatoneBroadcastLight(coordinator, entry, None))

        for (line, address), input_device in sorted(data.inputs.items()):
            for instance_num, instance in sorted(input_device.instances.items()):
                led_key = (line, address, instance_num)
                if instance.has_feedback_led and led_key not in known_leds:
                    known_leds.add(led_key)
                    new_entities.append(
                        FeedbackLedLight(coordinator, entry, line, address, instance_num)
                    )

        if new_entities:
            _LOGGER.debug("Adding %d new light entities", len(new_entities))
            async_add_entities(new_entities)

    _async_sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_sync_entities))

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service("step_up", {}, "async_step_up")
    platform.async_register_entity_service("step_down", {}, "async_step_down")
    platform.async_register_entity_service("recall_max", {}, "async_recall_max")
    scene_number = vol.All(vol.Coerce(int), vol.Range(min=0, max=15))
    platform.async_register_entity_service(
        "recall_scene",
        {
            vol.Required("scene"): scene_number,
            vol.Optional("fade_time"): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=600)
            ),
        },
        "async_recall_scene",
    )
    platform.async_register_entity_service(
        "store_scene", {vol.Required("scene"): scene_number}, "async_store_scene"
    )
    platform.async_register_entity_service(
        "set_scene_level",
        {
            vol.Required("scene"): scene_number,
            vol.Optional("level"): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=100)
            ),
        },
        "async_set_scene_level",
    )


def _aggregate_is_on(members: list[LunatoneDevice]) -> bool | None:
    """On if any member is on; unknown (None) if all members are unknown."""
    if not members:
        return None
    if any(device.is_on is True for device in members):
        return True
    if all(device.is_on is None for device in members):
        return None
    return False


def _color_modes_for(devices: list[LunatoneDevice]) -> tuple[set[ColorMode], ColorMode]:
    """Derive HA color mode from device features (never from DALI type)."""
    if any(device.supports_color_temp for device in devices):
        return {ColorMode.COLOR_TEMP}, ColorMode.COLOR_TEMP
    if any(device.supports_dimming for device in devices):
        return {ColorMode.BRIGHTNESS}, ColorMode.BRIGHTNESS
    return {ColorMode.ONOFF}, ColorMode.ONOFF


class LunatoneDeviceLight(CoordinatorEntity[LunatoneCoordinator], LightEntity):
    """One DALI control-gear device, addressed via its gateway id."""

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        entry: ConfigEntry,
        line: int,
        address: int,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._line = line
        self._address = address
        # Stable bus identity: survives gateway re-scans that renumber ids
        self._attr_unique_id = f"{entry.entry_id}_line{line}_dali_{address}"
        device = self._device
        self._attr_name = device.name if device else f"Line {line} DALI {address}"
        self._update_capabilities()

    @property
    def _device(self) -> LunatoneDevice | None:
        data = self.coordinator.data
        return data.device_by_line_addr(self._line, self._address) if data else None

    def _update_capabilities(self) -> None:
        device = self._device
        modes, mode = _color_modes_for([device] if device else [])
        self._attr_supported_color_modes = modes
        self._attr_color_mode = mode
        if mode is ColorMode.COLOR_TEMP:
            self._attr_min_color_temp_kelvin = MIN_COLOR_TEMP_KELVIN
            self._attr_max_color_temp_kelvin = MAX_COLOR_TEMP_KELVIN

    def _handle_coordinator_update(self) -> None:
        self._update_capabilities()
        super()._handle_coordinator_update()

    @property
    def device_info(self) -> DeviceInfo:
        device = self._device
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    gear_device_identifier(
                        self._entry.entry_id, self._line, self._address
                    ),
                )
            },
            name=device.name if device else f"Line {self._line} DALI {self._address}",
            model=f"DALI line {self._line} address {self._address}",
            manufacturer="Lunatone",
            via_device=(DOMAIN, self._entry.entry_id),
        )

    @property
    def available(self) -> bool:
        device = self._device
        return (
            self.coordinator.last_update_success
            and device is not None
            and device.available
        )

    @property
    def is_on(self) -> bool | None:
        device = self._device
        return device.is_on if device else None

    @property
    def brightness(self) -> int | None:
        device = self._device
        if device is None:
            return None
        return dimmable_pct_to_ha_brightness(
            device.brightness_pct, device.physical_min_level
        )

    @property
    def color_temp_kelvin(self) -> int | None:
        device = self._device
        return device.color_temp_kelvin if device else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        device = self._device
        attrs: dict[str, Any] = {"line": self._line, "address": self._address}
        if device:
            attrs.update(
                {
                    "gateway_device_id": device.gw_id,
                    "groups": device.groups,
                    "dali_types": device.dali_types,
                    "lamp_failure": device.lamp_failure,
                    "control_gear_failure": device.control_gear_failure,
                }
            )
            if device.scenes:
                attrs["scenes"] = {
                    scene: values.get("dimmable", values)
                    for scene, values in sorted(device.scenes.items())
                }
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        device = self._device
        if device is None:
            _LOGGER.error(
                "Device line %d address %d not in gateway inventory",
                self._line,
                self._address,
            )
            return
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        if color_temp_kelvin is not None and device.supports_color_temp:
            kelvin = max(
                MIN_COLOR_TEMP_KELVIN, min(MAX_COLOR_TEMP_KELVIN, color_temp_kelvin)
            )
            await self.coordinator.async_set_color_temp(device.gw_id, kelvin)

        if brightness is not None and device.supports_dimming:
            await self.coordinator.async_set_brightness(
                device.gw_id,
                ha_brightness_to_dimmable_pct(brightness, device.physical_min_level),
            )
        elif color_temp_kelvin is None:
            control = build_turn_on_control(
                self.coordinator.turn_on_store.get(
                    turn_on_key_device(self._line, self._address)
                )
            )
            await self.coordinator.async_apply_turn_on(device.gw_id, control)

    async def async_turn_off(self, **kwargs: Any) -> None:
        device = self._device
        if device:
            await self.coordinator.async_turn_off(device.gw_id)

    async def async_step_up(self) -> None:
        device = self._device
        if device:
            await self.coordinator.async_step_up(device.gw_id)

    async def async_step_down(self) -> None:
        device = self._device
        if device:
            await self.coordinator.async_step_down(device.gw_id)

    async def async_recall_max(self) -> None:
        device = self._device
        if device:
            await self.coordinator.async_recall_max(device.gw_id)

    async def async_recall_scene(
        self, scene: int, fade_time: float | None = None
    ) -> None:
        device = self._device
        if device:
            await self.coordinator.async_recall_scene(device.gw_id, scene, fade_time)

    async def async_store_scene(self, scene: int) -> None:
        device = self._device
        if device:
            await self.coordinator.async_store_scene(device.gw_id, scene)

    async def async_set_scene_level(
        self, scene: int, level: float | None = None
    ) -> None:
        device = self._device
        if device:
            await self.coordinator.async_set_scene_level(device.gw_id, scene, level)


class LunatoneGroupLight(CoordinatorEntity[LunatoneCoordinator], LightEntity):
    """One DALI group on ONE line; state aggregated from member devices."""

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        entry: ConfigEntry,
        line: int,
        group: int,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._line = line
        self._group = group
        self._attr_unique_id = f"{entry.entry_id}_line{line}_group{group}"
        self._attr_name = f"Line {line} Group {group}"
        self._update_capabilities()
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, group_device_identifier(entry.entry_id, line, group))
            },
            name=f"DALI Line {line} Group {group}",
            model="DALI Group",
            manufacturer="Lunatone",
            via_device=(DOMAIN, entry.entry_id),
        )

    def _members(self) -> list[LunatoneDevice]:
        data = self.coordinator.data
        if not data:
            return []
        return [
            device
            for device in data.devices.values()
            if device.line == self._line and self._group in device.groups
        ]

    def _update_capabilities(self) -> None:
        modes, mode = _color_modes_for(self._members())
        self._attr_supported_color_modes = modes
        self._attr_color_mode = mode
        if mode is ColorMode.COLOR_TEMP:
            self._attr_min_color_temp_kelvin = MIN_COLOR_TEMP_KELVIN
            self._attr_max_color_temp_kelvin = MAX_COLOR_TEMP_KELVIN

    def _handle_coordinator_update(self) -> None:
        self._update_capabilities()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and bool(self._members())

    @property
    def is_on(self) -> bool | None:
        return _aggregate_is_on(self._members())

    def _phys_min(self) -> int:
        """Group floor = the most restrictive member physical minimum."""
        return max(
            (device.physical_min_level for device in self._members()), default=1
        )

    @property
    def brightness(self) -> int | None:
        levels = [
            device.brightness_pct
            for device in self._members()
            if device.brightness_pct is not None
        ]
        if not levels:
            return None
        return dimmable_pct_to_ha_brightness(max(levels), self._phys_min())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        members = self._members()
        return {
            "line": self._line,
            "group": self._group,
            "devices": [
                {"address": device.address, "name": device.name} for device in members
            ],
            "device_count": len(members),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        if (
            color_temp_kelvin is not None
            and ColorMode.COLOR_TEMP in self._attr_supported_color_modes
        ):
            kelvin = max(
                MIN_COLOR_TEMP_KELVIN, min(MAX_COLOR_TEMP_KELVIN, color_temp_kelvin)
            )
            await self.coordinator.async_control_group(
                self._line, self._group, {"colorKelvin": kelvin}
            )

        if brightness is not None:
            await self.coordinator.async_control_group(
                self._line,
                self._group,
                {"dimmable": ha_brightness_to_dimmable_pct(brightness, self._phys_min())},
            )
        elif color_temp_kelvin is None:
            control = build_turn_on_control(
                self.coordinator.turn_on_store.get(
                    turn_on_key_group(self._line, self._group)
                )
            )
            await self.coordinator.async_control_group(
                self._line, self._group, control
            )
            if "gotoLastActive" in control:
                await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_control_group(
            self._line, self._group, {"switchable": False}
        )

    async def async_recall_scene(
        self, scene: int, fade_time: float | None = None
    ) -> None:
        await self.coordinator.async_control_group(
            self._line, self._group, scene_control(scene, fade_time)
        )
        await self.coordinator.async_request_refresh()

    async def async_set_scene_level(
        self, scene: int, level: float | None = None
    ) -> None:
        _LOGGER.warning(
            "set_scene_level targets individual device lights; call it on the "
            "member devices of group %d (line %d) instead",
            self._group,
            self._line,
        )

    async def async_store_scene(self, scene: int) -> None:
        await self.coordinator.async_control_group(
            self._line, self._group, {"saveToScene": scene}
        )
        await self.coordinator.async_refresh_line_scenes(self._line)


class LunatoneBroadcastLight(CoordinatorEntity[LunatoneCoordinator], LightEntity):
    """Broadcast to one line, or to all lines when line is None."""

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        entry: ConfigEntry,
        line: int | None,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._line = line
        if line is None:
            self._attr_unique_id = f"{entry.entry_id}_broadcast_all"
            self._attr_name = "DALI Broadcast (All Lines)"
            self._attr_entity_registry_enabled_default = False
        else:
            self._attr_unique_id = f"{entry.entry_id}_line{line}_broadcast"
            self._attr_name = f"Line {line} Broadcast"
        self._update_capabilities()
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, broadcast_device_identifier(entry.entry_id, line))
            },
            name="DALI Broadcast" if line is None else f"Line {line} Broadcast",
            model="DALI Broadcast Controller",
            manufacturer="Lunatone",
            via_device=(DOMAIN, entry.entry_id),
        )

    def _members(self) -> list[LunatoneDevice]:
        data = self.coordinator.data
        if not data:
            return []
        return [
            device
            for device in data.devices.values()
            if self._line is None or device.line == self._line
        ]

    def _update_capabilities(self) -> None:
        modes, mode = _color_modes_for(self._members())
        self._attr_supported_color_modes = modes
        self._attr_color_mode = mode
        if mode is ColorMode.COLOR_TEMP:
            self._attr_min_color_temp_kelvin = MIN_COLOR_TEMP_KELVIN
            self._attr_max_color_temp_kelvin = MAX_COLOR_TEMP_KELVIN

    def _handle_coordinator_update(self) -> None:
        self._update_capabilities()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool | None:
        return _aggregate_is_on(self._members())

    def _phys_min(self) -> int:
        return max(
            (device.physical_min_level for device in self._members()), default=1
        )

    @property
    def brightness(self) -> int | None:
        levels = [
            device.brightness_pct
            for device in self._members()
            if device.brightness_pct is not None
        ]
        if not levels:
            return None
        return dimmable_pct_to_ha_brightness(max(levels), self._phys_min())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "line": self._line if self._line is not None else "all",
            "device_count": len(self._members()),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        if (
            color_temp_kelvin is not None
            and ColorMode.COLOR_TEMP in self._attr_supported_color_modes
        ):
            kelvin = max(
                MIN_COLOR_TEMP_KELVIN, min(MAX_COLOR_TEMP_KELVIN, color_temp_kelvin)
            )
            await self.coordinator.async_control_broadcast(
                {"colorKelvin": kelvin}, line=self._line
            )

        if brightness is not None:
            await self.coordinator.async_control_broadcast(
                {"dimmable": ha_brightness_to_dimmable_pct(brightness, self._phys_min())},
                line=self._line,
            )
        elif color_temp_kelvin is None:
            control = build_turn_on_control(
                self.coordinator.turn_on_store.get(
                    turn_on_key_broadcast(self._line)
                )
            )
            await self.coordinator.async_control_broadcast(control, line=self._line)
            if "gotoLastActive" in control:
                await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_control_broadcast(
            {"switchable": False}, line=self._line
        )

    async def async_recall_scene(
        self, scene: int, fade_time: float | None = None
    ) -> None:
        await self.coordinator.async_control_broadcast(
            scene_control(scene, fade_time), line=self._line
        )
        await self.coordinator.async_request_refresh()

    async def async_set_scene_level(
        self, scene: int, level: float | None = None
    ) -> None:
        _LOGGER.warning(
            "set_scene_level targets individual device lights, not broadcast"
        )

    async def async_store_scene(self, scene: int) -> None:
        await self.coordinator.async_control_broadcast(
            {"saveToScene": scene}, line=self._line
        )
        await self.coordinator.async_refresh_line_scenes(self._line)


class FeedbackLedLight(CoordinatorEntity[LunatoneCoordinator], LightEntity):
    """Feedback LED of a DALI-2 input instance (line-aware 24-bit frames)."""

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        entry: ConfigEntry,
        line: int,
        address: int,
        instance_num: int,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._line = line
        self._address = address
        self._instance_num = instance_num
        self._attr_unique_id = (
            f"{entry.entry_id}_line{line}_input_{address}_led_{instance_num}"
        )
        self._attr_name = f"LED {instance_num}"

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data
        input_device = data.inputs.get((self._line, self._address)) if data else None
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    input_device_identifier(
                        self._entry.entry_id, self._line, self._address
                    ),
                )
            },
            name=input_device.name
            if input_device
            else f"Line {self._line} Input {self._address}",
            model="DALI-2 Input Device",
            manufacturer="Lunatone",
            via_device=(DOMAIN, self._entry.entry_id),
        )

    @property
    def icon(self) -> str | None:
        if self.is_on is None:
            return "mdi:lightning-bolt"
        return None

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.get_led_state(
            self._line, self._address, self._instance_num
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "line": self._line,
            "address": self._address,
            "instance": self._instance_num,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_feedback_led(
            self._line, self._address, self._instance_num, True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_feedback_led(
            self._line, self._address, self._instance_num, False
        )
