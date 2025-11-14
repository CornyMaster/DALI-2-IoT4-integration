"""Button platform for Lunatone DALI-2 IoT integration."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import LunatoneCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lunatone button entities."""
    coordinator: LunatoneCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    async_add_entities([ManualScanButton(coordinator, config_entry)])


class ManualScanButton(ButtonEntity):
    """Button entity for manual device scanning."""

    def __init__(
        self,
        coordinator: LunatoneCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._attr_name = "Manual Scan"
        self._attr_unique_id = f"{config_entry.entry_id}_manual_scan"
        self._attr_icon = "mdi:magnify-scan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Manual scan button pressed")
        await self._coordinator.async_rescan_devices()
