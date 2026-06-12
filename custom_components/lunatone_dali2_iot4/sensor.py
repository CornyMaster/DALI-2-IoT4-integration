"""Sensors for DALI-2 light sensors, keyed by (line, address, instance)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LIGHT_LUX
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN, INSTANCE_TYPE_LIGHT_SENSOR
from .coordinator import LunatoneCoordinator, input_device_identifier
from .models import InputInstance

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DALI-2 light sensors, added dynamically on discovery."""
    coordinator: LunatoneCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    known: set[tuple[int, int, int]] = set()

    @callback
    def _async_sync_entities() -> None:
        data = coordinator.data
        if not data:
            return
        new_entities = []
        for (line, address), input_device in data.inputs.items():
            for instance_num, instance in input_device.instances.items():
                key = (line, address, instance_num)
                if (
                    key in known
                    or instance.instance_type != INSTANCE_TYPE_LIGHT_SENSOR
                ):
                    continue
                known.add(key)
                new_entities.append(
                    DaliLightSensor(coordinator, entry, line, address, instance_num)
                )
        if new_entities:
            _LOGGER.debug("Adding %d DALI-2 light sensors", len(new_entities))
            async_add_entities(new_entities)

    _async_sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_sync_entities))


class DaliLightSensor(CoordinatorEntity[LunatoneCoordinator], SensorEntity):
    """A DALI-2 light (lux) sensor instance on one line."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = LIGHT_LUX

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
            f"{entry.entry_id}_line{line}_input_{address}_inst{instance_num}"
        )
        self._attr_name = f"Light Level {instance_num}"

    @property
    def _instance(self) -> InputInstance | None:
        data = self.coordinator.data
        if not data:
            return None
        input_device = data.inputs.get((self._line, self._address))
        return input_device.instances.get(self._instance_num) if input_device else None

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
    def native_value(self) -> float | None:
        instance = self._instance
        return instance.value if instance else None

    @property
    def available(self) -> bool:
        return self._instance is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "line": self._line,
            "address": self._address,
            "instance": self._instance_num,
        }
