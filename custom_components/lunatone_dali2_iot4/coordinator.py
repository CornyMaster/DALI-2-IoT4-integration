"""DataUpdateCoordinator for the Lunatone DALI-2 IoT(4) integration.

The gateway's REST inventory (GET /devices) is the source of truth: it is
line-aware and already contains live state for every device. The coordinator
polls it and merges websocket push events (device status changes and DALI-2
input events) in between polls.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LunatoneApiError, LunatoneRestClient
from .const import (
    BUTTON_ACTIVE_EVENTS,
    CONF_TRACK_INPUTS,
    CONF_LINES,
    CONF_POLLING_INTERVAL,
    DALI_EVENT,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    FEEDBACK_LED_OFF,
    FEEDBACK_LED_ON,
    INSTANCE_TYPE_LIGHT_SENSOR,
    INSTANCE_TYPE_OCCUPANCY,
    INSTANCE_TYPE_PUSH_BUTTON,
    INSTANCE_TYPE_SWITCH,
    MOMENTARY_EVENTS,
    MOMENTARY_RESET_DELAY,
)
from .models import GatewayInfo, InputDevice, InputInstance, LunatoneData, LunatoneDevice
from .storage import InputDeviceStore
from .turn_on import TurnOnPreferenceStore
from .websocket import InputEvent, decode_button_event, decode_occupancy_event

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPE_TO_INSTANCE_TYPE = {
    "occupancy": INSTANCE_TYPE_OCCUPANCY,
    "light": INSTANCE_TYPE_LIGHT_SENSOR,
}


def scene_control(scene: int, fade_time: float | None = None) -> dict[str, Any]:
    """Build the ControlData payload for a scene recall."""
    if fade_time is not None:
        return {"sceneWithFade": {"scene": scene, "fadeTime": fade_time}}
    return {"scene": scene}


def _turn_on_optimistic_updates(control: dict[str, Any]) -> dict[str, Any]:
    """Derive optimistic device-attribute updates from a turn-on control."""
    updates: dict[str, Any] = {}
    if control.get("gotoLastActive") or control.get("switchable"):
        updates["is_on"] = True
    if "dimmable" in control:
        updates["is_on"] = control["dimmable"] > 0
        updates["brightness_pct"] = float(control["dimmable"])
    if "dimmableWithFade" in control:
        dim_value = control["dimmableWithFade"].get("dimValue")
        if dim_value is not None:
            updates["is_on"] = dim_value > 0
            updates["brightness_pct"] = float(dim_value)
    return updates


def gear_device_identifier(entry_id: str, line: int, address: int) -> str:
    """Registry identifier for a control-gear device (stable bus identity)."""
    return f"{entry_id}_line{line}_addr{address}"


def input_device_identifier(entry_id: str, line: int, address: int) -> str:
    """Registry identifier for a DALI-2 input device."""
    return f"{entry_id}_line{line}_input_{address}"


def group_device_identifier(entry_id: str, line: int, group: int) -> str:
    """Registry identifier for a single DALI group on one line."""
    return f"{entry_id}_line{line}_group{group}"


def scene_device_identifier(entry_id: str, line: int, scene: int) -> str:
    """Registry identifier for a single DALI scene on one line."""
    return f"{entry_id}_line{line}_scene{scene}"


def broadcast_device_identifier(entry_id: str, line: int | None) -> str:
    """Registry identifier for a broadcast target (one line, or all lines)."""
    if line is None:
        return f"{entry_id}_broadcast_all"
    return f"{entry_id}_line{line}_broadcast"


class LunatoneCoordinator(DataUpdateCoordinator[LunatoneData]):
    """Polls the REST inventory and merges websocket push events."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: LunatoneRestClient,
    ) -> None:
        polling_interval = entry.options.get(
            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=polling_interval),
            config_entry=entry,
        )
        self.entry = entry
        self.client = client
        self.track_inputs: bool = entry.options.get(CONF_TRACK_INPUTS, True)
        lines = entry.options.get(CONF_LINES)
        self.lines: set[int] | None = {int(line) for line in lines} if lines else None
        self.info: GatewayInfo | None = None
        self._inputs: dict[tuple[int, int], InputDevice] = {}
        self._inputs_loaded = False
        self._store = InputDeviceStore(hass, entry.entry_id)
        self._led_states: dict[tuple[int, int, int], bool] = {}
        self._scenes: dict[int, dict[int, Any]] = {}
        self._scenes_loaded = False
        # Cached per-device physical minimum DALI level (QUERY PHYSICAL MINIMUM),
        # keyed by (line, address). Static hardware property; queried once and
        # re-applied to the rebuilt device objects on every poll.
        self._phys_min: dict[tuple[int, int], int] = {}
        # Per-target "switch on without brightness" behavior; populated by the
        # select/number entities (restored across restarts) and read by the
        # light entities. Defaults to "go to last active level".
        self.turn_on_store = TurnOnPreferenceStore()

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> LunatoneData:
        try:
            if self.info is None:
                self.info = GatewayInfo.from_api(await self.client.async_get_info())
            devices = await self.client.async_get_devices()
            sensors = await self.client.async_get_sensors()
        except LunatoneApiError as err:
            raise UpdateFailed(str(err)) from err

        if not self._inputs_loaded:
            stored = await self._store.async_load()
            for key, device in stored.items():
                self._inputs.setdefault(key, device)
            self._inputs_loaded = True

        self._merge_sensors(sensors)
        data = LunatoneData.from_api(
            self.info, devices, lines=self.lines, inputs=self._inputs
        )
        if not self._scenes_loaded:
            await self._async_fetch_all_scenes(data)
            self._scenes_loaded = True
        for gw_id, device in data.devices.items():
            device.scenes = self._scenes.get(gw_id, {})
            device.physical_min_level = self._phys_min.get(
                (device.line, device.address), 1
            )
        return data

    async def async_refresh_physical_minimums(self) -> None:
        """Query each device's physical minimum dim level once and cache it.

        Read-only DALI queries (no light changes). Lets the light entities map
        the HA slider onto the lamp's usable range instead of its unreachable
        lower part. Runs in the background after setup and after a rescan.
        """
        data = self.data
        if not data:
            return
        changed = False
        for device in list(data.devices.values()):
            key = (device.line, device.address)
            if key in self._phys_min:
                device.physical_min_level = self._phys_min[key]
                continue
            try:
                level = await self.client.async_query_physical_minimum(
                    device.line, device.address
                )
            except LunatoneApiError as err:
                _LOGGER.debug("Physical-min query failed for %s: %s", key, err)
                continue
            if level is not None and 1 <= level <= 254:
                self._phys_min[key] = level
                device.physical_min_level = level
                changed = True
        if changed:
            self.async_set_updated_data(data)

    async def _async_fetch_all_scenes(self, data: LunatoneData) -> None:
        """Load the stored scene values of every device (once at startup)."""

        async def fetch(gw_id: int) -> None:
            try:
                raw = await self.client.async_get_device_scenes(gw_id)
            except LunatoneApiError as err:
                _LOGGER.debug("Reading scenes of device %d failed: %s", gw_id, err)
                return
            self._scenes[gw_id] = self._parse_scenes(raw)

        await asyncio.gather(*(fetch(gw_id) for gw_id in data.devices))

    @staticmethod
    def _parse_scenes(raw: dict[str, Any]) -> dict[int, Any]:
        """Keep only scenes that actually store a value."""
        scenes: dict[int, Any] = {}
        for key, value in (raw or {}).items():
            try:
                scene = int(key)
            except ValueError:
                continue
            if isinstance(value, dict) and any(
                v is not None for v in value.values()
            ):
                scenes[scene] = value
        return scenes

    async def async_refresh_device_scenes(self, gw_id: int) -> None:
        """Re-read one device's stored scenes (after a scene write)."""
        try:
            raw = await self.client.async_get_device_scenes(gw_id)
        except LunatoneApiError as err:
            _LOGGER.debug("Reading scenes of device %d failed: %s", gw_id, err)
            return
        self._scenes[gw_id] = self._parse_scenes(raw)
        if self.data and gw_id in self.data.devices:
            self.data.devices[gw_id].scenes = self._scenes[gw_id]
            self.async_set_updated_data(self.data)

    async def async_refresh_all_scenes(self) -> None:
        """Re-read the stored scenes of every device (e.g. after a rescan).

        Stored scenes are otherwise only read once at startup; this picks up
        scenes that were configured later (in DALI Cockpit or via store_scene)
        so they appear as scene entities.
        """
        data = self.data
        if not data:
            return
        await self._async_fetch_all_scenes(data)
        for gw_id, device in data.devices.items():
            device.scenes = self._scenes.get(gw_id, {})
        self.async_set_updated_data(data)

    async def async_refresh_line_scenes(self, line: int | None) -> None:
        """Re-read stored scenes of one line's devices (all lines if None).

        Used after a broadcast/group store_scene so the affected scene entity
        and its member list update immediately, without a manual rescan.
        """
        data = self.data
        if not data:
            return
        changed = False
        for gw_id, device in data.devices.items():
            if line is not None and device.line != line:
                continue
            try:
                raw = await self.client.async_get_device_scenes(gw_id)
            except LunatoneApiError as err:
                _LOGGER.debug("Reading scenes of device %d failed: %s", gw_id, err)
                continue
            self._scenes[gw_id] = self._parse_scenes(raw)
            device.scenes = self._scenes[gw_id]
            changed = True
        if changed:
            self.async_set_updated_data(data)

    def configured_scenes(self) -> set[tuple[int, int]]:
        """(line, scene) pairs with a stored value on at least one device."""
        result: set[tuple[int, int]] = set()
        data = self.data
        if not data:
            return result
        for gw_id, scenes in self._scenes.items():
            device = data.devices.get(gw_id)
            if device is None:
                continue
            for scene in scenes:
                result.add((device.line, scene))
        return result

    def scene_members(self, line: int, scene: int) -> list[dict[str, Any]]:
        """Lamps on `line` that store a value for `scene`, with that value.

        Lets the UI show which lamps (and at which level) belong to a scene.
        """
        members: list[dict[str, Any]] = []
        data = self.data
        if not data:
            return members
        for gw_id, scenes in self._scenes.items():
            device = data.devices.get(gw_id)
            if device is None or device.line != line or scene not in scenes:
                continue
            value = scenes[scene]
            members.append(
                {
                    "address": device.address,
                    "name": device.name,
                    "level": value.get("dimmable") if isinstance(value, dict) else None,
                }
            )
        return sorted(members, key=lambda m: m["address"])

    def _merge_sensors(self, sensors: list[dict[str, Any]]) -> None:
        """Type and update input instances from GET /sensors."""
        for sensor in sensors:
            address_info = sensor.get("daliSensorAddress") or {}
            if not address_info:
                continue
            line = address_info.get("line", 0)
            address = address_info.get("address")
            instance_num = address_info.get("instanceNumber", 0)
            instance_type = SENSOR_TYPE_TO_INSTANCE_TYPE.get(sensor.get("type"))
            if address is None or instance_type is None:
                continue
            if self.lines is not None and line not in self.lines:
                continue
            device = self._inputs.setdefault(
                (line, address),
                InputDevice(line=line, address=address, name=sensor.get("name", "")),
            )
            instance = device.instances.setdefault(
                instance_num, InputInstance(instance_type=instance_type)
            )
            instance.instance_type = instance_type
            if instance_type == INSTANCE_TYPE_LIGHT_SENSOR:
                instance.value = sensor.get("value")
            elif instance_type == INSTANCE_TYPE_OCCUPANCY:
                instance.state = bool(sensor.get("value"))

    # ------------------------------------------------------------------
    # Device control (optimistic updates, REST control by gateway id)
    # ------------------------------------------------------------------

    async def _async_control_device(
        self, gw_id: int, control: dict[str, Any], **updates: Any
    ) -> bool:
        try:
            await self.client.async_control_device(gw_id, control)
        except LunatoneApiError as err:
            _LOGGER.error("Control of device %d failed: %s", gw_id, err)
            return False
        device = self.data.devices.get(gw_id) if self.data else None
        if device and updates:
            for attr, value in updates.items():
                setattr(device, attr, value)
            self.async_set_updated_data(self.data)
        return True

    async def async_turn_on(self, gw_id: int) -> bool:
        return await self._async_control_device(
            gw_id, {"switchable": True}, is_on=True
        )

    async def async_apply_turn_on(
        self, gw_id: int, control: dict[str, Any]
    ) -> bool:
        """Switch a device on with a caller-built control (turn-on behavior).

        Used by the light entity to honor the per-lamp turn-on preference
        (last active level / maximum / fixed value). For "last active level"
        the resulting brightness is unknown up front, so a refresh is requested
        to pull the real level from the gateway.
        """
        result = await self._async_control_device(
            gw_id, control, **_turn_on_optimistic_updates(control)
        )
        if "gotoLastActive" in control:
            await self.async_request_refresh()
        return result

    async def async_turn_off(self, gw_id: int) -> bool:
        return await self._async_control_device(
            gw_id, {"switchable": False}, is_on=False, brightness_pct=0.0
        )

    async def async_set_brightness(self, gw_id: int, percent: float) -> bool:
        return await self._async_control_device(
            gw_id,
            {"dimmable": percent},
            is_on=percent > 0,
            brightness_pct=percent,
        )

    async def async_set_color_temp(self, gw_id: int, kelvin: int) -> bool:
        return await self._async_control_device(
            gw_id, {"colorKelvin": kelvin}, color_temp_kelvin=kelvin
        )

    async def async_step_up(self, gw_id: int) -> bool:
        result = await self._async_control_device(gw_id, {"dimUp": 1})
        await self.async_request_refresh()
        return result

    async def async_step_down(self, gw_id: int) -> bool:
        result = await self._async_control_device(gw_id, {"dimDown": 1})
        await self.async_request_refresh()
        return result

    async def async_recall_scene(
        self, gw_id: int, scene: int, fade_time: float | None = None
    ) -> bool:
        """Recall a DALI scene (0-15) on one device, optionally with fade."""
        result = await self._async_control_device(
            gw_id, scene_control(scene, fade_time)
        )
        await self.async_request_refresh()
        return result

    async def async_store_scene(self, gw_id: int, scene: int) -> bool:
        """Store the device's current level into a DALI scene (0-15)."""
        result = await self._async_control_device(gw_id, {"saveToScene": scene})
        await self.async_refresh_device_scenes(gw_id)
        return result

    async def async_set_scene_level(
        self, gw_id: int, scene: int, level: float | None
    ) -> bool:
        """Write a device's stored scene value directly (None clears it)."""
        try:
            await self.client.async_set_device_scenes(
                gw_id, {str(scene): {"dimmable": level}}
            )
        except LunatoneApiError as err:
            _LOGGER.error(
                "Setting scene %d of device %d failed: %s", scene, gw_id, err
            )
            return False
        await self.async_refresh_device_scenes(gw_id)
        return True

    async def async_recall_max(self, gw_id: int) -> bool:
        return await self._async_control_device(
            gw_id, {"dimmable": 100}, is_on=True, brightness_pct=100.0
        )

    # ------------------------------------------------------------------
    # Group / broadcast control (line-aware!)
    # ------------------------------------------------------------------

    async def async_control_group(
        self, line: int, group: int, control: dict[str, Any]
    ) -> bool:
        """Control DALI group `group` on one specific line."""
        try:
            await self.client.async_control_group(group, control, line=line)
        except LunatoneApiError as err:
            _LOGGER.error(
                "Control of group %d on line %d failed: %s", group, line, err
            )
            return False
        self._apply_optimistic_to_members(
            control,
            [
                device
                for device in (self.data.devices.values() if self.data else [])
                if device.line == line and group in device.groups
            ],
        )
        return True

    async def async_control_broadcast(
        self, control: dict[str, Any], line: int | None = None
    ) -> bool:
        """Broadcast to one line, or to all lines when line is None."""
        try:
            await self.client.async_control_broadcast(control, line=line)
        except LunatoneApiError as err:
            _LOGGER.error("Broadcast on line %s failed: %s", line, err)
            return False
        self._apply_optimistic_to_members(
            control,
            [
                device
                for device in (self.data.devices.values() if self.data else [])
                if line is None or device.line == line
            ],
        )
        return True

    def _apply_optimistic_to_members(
        self, control: dict[str, Any], devices: list[LunatoneDevice]
    ) -> None:
        if not devices:
            return
        for device in devices:
            if "switchable" in control:
                device.is_on = bool(control["switchable"])
                if not device.is_on:
                    device.brightness_pct = 0.0
            if "dimmable" in control:
                device.brightness_pct = float(control["dimmable"])
                device.is_on = control["dimmable"] > 0
            if "gotoLastActive" in control:
                # Target level unknown up front; a poll/ws update fills it in.
                device.is_on = True
            if "dimmableWithFade" in control:
                dim_value = control["dimmableWithFade"].get("dimValue")
                if dim_value is not None:
                    device.brightness_pct = float(dim_value)
                    device.is_on = dim_value > 0
            if "colorKelvin" in control and device.supports_color_temp:
                device.color_temp_kelvin = round(control["colorKelvin"])
        self.async_set_updated_data(self.data)

    # ------------------------------------------------------------------
    # Websocket push handlers
    # ------------------------------------------------------------------

    def handle_ws_devices_update(self, devices: list[dict[str, Any]]) -> None:
        """Merge a `devices` push into current data (status changes)."""
        if not self.data:
            return
        changed = False
        needs_refresh = False
        for raw in devices:
            gw_id = raw.get("id")
            if gw_id is None:
                continue
            device = self.data.devices.get(gw_id)
            if device is None:
                # unknown device (e.g. created by a gateway scan) -> full poll
                if self.lines is None or raw.get("line") in self.lines:
                    needs_refresh = True
                continue
            features = raw.get("features") or {}
            if "switchable" in features:
                status = features["switchable"].get("status")
                if status is not None:
                    device.is_on = bool(status)
                    changed = True
            if "dimmable" in features:
                status = features["dimmable"].get("status")
                if status is not None:
                    device.brightness_pct = float(status)
                    device.is_on = status > 0
                    changed = True
            if "colorKelvin" in features:
                status = features["colorKelvin"].get("status")
                if status is not None:
                    device.color_temp_kelvin = round(status)
                    changed = True
            if "available" in raw:
                device.available = bool(raw["available"])
                changed = True
        if changed:
            self.async_set_updated_data(self.data)
        if needs_refresh:
            self.hass.async_create_task(self.async_request_refresh())

    def handle_ws_input_event(self, event: InputEvent) -> None:
        """Handle a DALI-2 input event (button press, occupancy, ...)."""
        if not self.track_inputs:
            return
        if self.lines is not None and event.line not in self.lines:
            return

        key = (event.line, event.address)
        device = self._inputs.get(key)
        if device is None:
            device = InputDevice(line=event.line, address=event.address)
            self._inputs[key] = device
            _LOGGER.info(
                "Discovered new DALI-2 input device on line %d address %d",
                event.line,
                event.address,
            )
            # name it from the description stored in the device (Cockpit's
            # "Device Description", memory bank 2), if there is one
            self.hass.async_create_task(self._async_fetch_input_device_name(device))
        instance = device.instances.get(event.instance)
        if instance is None:
            # Type is not queryable via REST: /sensors marks occupancy and
            # light sensors, everything else that sends events is treated as
            # a push button.
            instance = InputInstance(instance_type=INSTANCE_TYPE_PUSH_BUTTON)
            device.instances[event.instance] = instance
            self.hass.async_create_task(self._store.async_save(self._inputs))

        event_type = self._apply_input_event(instance, event)

        if event_type:
            device_registry = dr.async_get(self.hass)
            ha_device = device_registry.async_get_device(
                identifiers={
                    (
                        DOMAIN,
                        input_device_identifier(
                            self.entry.entry_id, event.line, event.address
                        ),
                    )
                }
            )
            self.hass.bus.async_fire(
                DALI_EVENT,
                {
                    "device_id": ha_device.id if ha_device else None,
                    "type": event_type,
                    "line": event.line,
                    "device_address": event.address,
                    "instance": event.instance,
                    "instance_type": instance.instance_type,
                    "event_type": event_type,
                    "event_data": event.event_data,
                },
            )

        if self.data:
            self.async_set_updated_data(self.data)

        if event_type in MOMENTARY_EVENTS:
            self.hass.async_create_task(
                self._async_reset_momentary_state(instance, event)
            )

    def _apply_input_event(
        self, instance: InputInstance, event: InputEvent
    ) -> str | None:
        """Update instance state from the event; return the event type name."""
        if instance.instance_type in (
            INSTANCE_TYPE_PUSH_BUTTON,
            INSTANCE_TYPE_SWITCH,
        ):
            event_type = decode_button_event(event.event_data)
            instance.state = event.event_data in BUTTON_ACTIVE_EVENTS
            instance.event_type = event_type
            return event_type
        if instance.instance_type == INSTANCE_TYPE_OCCUPANCY:
            event_type = decode_occupancy_event(event.event_data)
            instance.state = event_type in ("occupied", "still_occupied")
            instance.event_type = event_type
            return event_type
        if instance.instance_type == INSTANCE_TYPE_LIGHT_SENSOR:
            instance.value = float(event.event_data)
            return None
        return None

    async def _async_fetch_input_device_name(self, device: InputDevice) -> None:
        """Use the device's stored description as its name, if available."""
        try:
            description = await self.client.async_read_input_device_description(
                device.line, device.address
            )
        except LunatoneApiError as err:
            _LOGGER.debug(
                "Reading description of input line %d address %d failed: %s",
                device.line,
                device.address,
                err,
            )
            description = None
        if description:
            device.name = description
            _LOGGER.info(
                "Input device line %d address %d is named '%s'",
                device.line,
                device.address,
                description,
            )
            # entities may already exist with the default name; update the
            # registry unless the user renamed the device manually
            registry = dr.async_get(self.hass)
            entry = registry.async_get_device(
                identifiers={
                    (
                        DOMAIN,
                        input_device_identifier(
                            self.entry.entry_id, device.line, device.address
                        ),
                    )
                }
            )
            if entry and not entry.name_by_user:
                registry.async_update_device(entry.id, name=description)
        await self._store.async_save(self._inputs)
        if self.data:
            self.async_set_updated_data(self.data)

    async def async_refresh_input_names(self) -> None:
        """Re-read the description (name) of every known input device.

        Repairs names that were persisted from an earlier unreliable read
        (garbled or truncated). Reads are serialized by the line lock in the
        REST client; names the user renamed by hand are left untouched.
        """
        devices = list(self._inputs.values())
        _LOGGER.info("Refreshing names of %d input device(s)", len(devices))
        for device in devices:
            await self._async_fetch_input_device_name(device)

    async def _async_reset_momentary_state(
        self, instance: InputInstance, event: InputEvent
    ) -> None:
        """Reset a binary sensor shortly after a momentary button event.

        A newer press on the same instance starts its own reset; only the
        latest one is allowed to clear the state, so rapid repeats are not cut
        short by an earlier timer.
        """
        if not hasattr(self, "_momentary_seq"):
            self._momentary_seq = {}
        key = (event.line, event.address, event.instance)
        token = self._momentary_seq.get(key, 0) + 1
        self._momentary_seq[key] = token
        await asyncio.sleep(MOMENTARY_RESET_DELAY)
        if self._momentary_seq.get(key) != token:
            return  # a newer event arrived; let its timer handle the reset
        if instance.event_type in MOMENTARY_EVENTS:
            instance.state = False
            if self.data:
                self.async_set_updated_data(self.data)

    # ------------------------------------------------------------------
    # Feedback LEDs (24-bit frames on the device's line)
    # ------------------------------------------------------------------

    def get_led_state(self, line: int, address: int, instance: int) -> bool | None:
        return self._led_states.get((line, address, instance))

    async def async_set_feedback_led(
        self, line: int, address: int, instance: int, state: bool
    ) -> bool:
        try:
            await self.client.async_send_dali24(
                line,
                address=(address << 1) + 1,
                instance=0x20 + instance,
                command=FEEDBACK_LED_ON if state else FEEDBACK_LED_OFF,
            )
        except LunatoneApiError as err:
            _LOGGER.error(
                "Setting feedback LED line %d address %d instance %d failed: %s",
                line,
                address,
                instance,
                err,
            )
            return False
        self._led_states[(line, address, instance)] = state
        if self.data:
            self.async_set_updated_data(self.data)
        return True
