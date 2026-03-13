"""Storage helper for Lunatone DALI-2 IoT integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "dali_lunatone_devices"


class DeviceStorage:
    """Handle device configuration storage."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize device storage."""
        self.hass = hass
        self.entry_id = entry_id
        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_{entry_id}",
        )
        self._data: dict[str, Any] = {}

    async def async_load(self) -> dict[tuple[str, int], dict[str, Any]]:
        """Load devices from storage."""
        try:
            stored_data = await self._store.async_load()
            if stored_data is None:
                _LOGGER.info("No stored device configuration found")
                return {}

            self._data = stored_data
            devices = {}
            
            # Convert stored format to runtime format
            for device_key, device_data in stored_data.get("devices", {}).items():
                # Parse key: "DALI_4" -> ("DALI", 4)
                protocol, address_str = device_key.rsplit("_", 1)
                address = int(address_str)
                devices[(protocol, address)] = device_data

            last_scan = stored_data.get("last_scan")
            _LOGGER.info(
                "Loaded %d devices from storage (last scan: %s)",
                len(devices),
                last_scan or "never",
            )
            return devices

        except Exception as e:
            _LOGGER.error("Error loading device storage: %s", e)
            return {}

    async def async_save(
        self,
        devices: dict[tuple[str, int], dict[str, Any]],
        scan_timestamp: str | None = None,
    ) -> None:
        """Save devices to storage."""
        try:
            # Convert runtime format to storage format
            storage_devices = {}
            for (protocol, address), device_data in devices.items():
                # Create key: ("DALI", 4) -> "DALI_4"
                device_key = f"{protocol}_{address}"
                storage_devices[device_key] = device_data

            data = {
                "devices": storage_devices,
                "last_scan": scan_timestamp or datetime.now().isoformat(),
                "version": STORAGE_VERSION,
            }

            await self._store.async_save(data)
            self._data = data
            _LOGGER.info("Saved %d devices to storage", len(storage_devices))

        except Exception as e:
            _LOGGER.error("Error saving device storage: %s", e)

    async def async_remove(self) -> None:
        """Remove storage file."""
        try:
            await self._store.async_remove()
            self._data = {}
            _LOGGER.info("Removed device storage")
        except Exception as e:
            _LOGGER.error("Error removing device storage: %s", e)

    def get_last_scan_time(self) -> str | None:
        """Get timestamp of last device scan."""
        return self._data.get("last_scan")

    def serialize_device(self, device: Any) -> dict[str, Any]:
        """Serialize a DaliDevice to dict for storage."""
        return {
            "address": device.address,
            "protocol": device.protocol,
            "device_type": device.device_type,
            "device_name": device.device_name,
            "capabilities": device.capabilities,
            "groups": device.groups,
            "num_instances": device.num_instances,
            "instances": device.instances,
            "device_types": device.device_types if hasattr(device, "device_types") else [],
            "gtin": device.gtin if hasattr(device, "gtin") else None,
            "firmware_version": device.firmware_version if hasattr(device, "firmware_version") else None,
            "hardware_version": device.hardware_version if hasattr(device, "hardware_version") else None,
            "identification_number": device.identification_number if hasattr(device, "identification_number") else None,
        }

    def deserialize_devices(
        self, stored_devices: dict[tuple[str, int], dict[str, Any]]
    ) -> dict[tuple[str, int], Any]:
        """Deserialize stored device data to DaliDevice objects."""
        from .lunatone_api import DaliDevice

        devices = {}
        for key, data in stored_devices.items():
            device = DaliDevice(
                address=data["address"],
                protocol=data["protocol"],
                device_type=data["device_type"],
                device_name=data["device_name"],
                capabilities=data.get("capabilities"),
            )
            device.groups = data.get("groups", [])
            device.num_instances = data.get("num_instances", 0)
            # Convert instance keys from strings to integers (JSON stores them as strings)
            instances_data = data.get("instances", {})
            device.instances = {int(k): v for k, v in instances_data.items()} if instances_data else {}
            device.device_types = data.get("device_types", [])
            device.gtin = data.get("gtin")
            device.firmware_version = data.get("firmware_version")
            device.hardware_version = data.get("hardware_version")
            device.identification_number = data.get("identification_number")
            devices[key] = device

        return devices
