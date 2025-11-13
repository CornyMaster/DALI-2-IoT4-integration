"""DataUpdateCoordinator for Lunatone DALI-2 IoT integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_ENABLE_BACKGROUND_SCAN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, SCAN_INTERVAL_SECONDS
from .lunatone_api import DaliDevice, LunatoneClient
from .storage import DeviceStorage

_LOGGER = logging.getLogger(__name__)


class LunatoneCoordinator(DataUpdateCoordinator[dict[tuple[str, int], DaliDevice]]):
    """Class to manage fetching Lunatone DALI data."""

    def __init__(self, hass: HomeAssistant, client: LunatoneClient, entry_id: str, config_entry: Any) -> None:
        """Initialize coordinator."""
        # Get scan interval from options or use default
        scan_interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        enable_background_scan = config_entry.options.get(CONF_ENABLE_BACKGROUND_SCAN, True)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS) if enable_background_scan else None,
        )
        self.client = client
        self.storage = DeviceStorage(hass, entry_id)
        self._devices_loaded = False
        self._background_scan_task = None
        self._scan_interval = scan_interval
        self._enable_background_scan = enable_background_scan
        self._last_full_scan = 0.0  # Timestamp of last full state scan
        self._led_states: dict[tuple[int, int], bool] = {}  # (address, instance) -> is_on
        
        # Register callback for real-time events
        self.client.add_callback(self._handle_device_event)

    async def _async_update_data(self) -> dict[tuple[str, int], DaliDevice]:
        """Fetch data from Lunatone."""
        try:
            if not self.client.connected:
                raise UpdateFailed("Not connected to Lunatone device")

            # Load devices from storage on first run
            if not self._devices_loaded:
                _LOGGER.info("Loading devices from storage")
                stored_devices = await self.storage.async_load()
                
                if stored_devices:
                    # Restore devices from storage
                    restored_devices = self.storage.deserialize_devices(stored_devices)
                    self.client.devices.update(restored_devices)
                    _LOGGER.info("Restored %d devices from storage", len(restored_devices))
                else:
                    _LOGGER.info("No stored devices found, use rescan_devices service to discover devices")
                
                self._devices_loaded = True

            # Check if we should do a full state scan based on configured interval
            import time
            current_time = time.time()
            if current_time - self._last_full_scan >= self._scan_interval:
                if self.client.devices:
                    _LOGGER.debug("Performing periodic state scan (interval: %ds)", self._scan_interval)
                    await self.client.update_device_states()
                    self._last_full_scan = current_time

            return self.client.devices

        except Exception as err:
            raise UpdateFailed(f"Error communicating with Lunatone: {err}") from err

    async def async_set_brightness(
        self, address: int, brightness: int
    ) -> bool:
        """Set device brightness."""
        success = await self.client.set_brightness(address, brightness)
        if success:
            # Update device state immediately for DALI device without scanning
            key = ("DALI", address)
            if key in self.client.devices:
                self.client.devices[key].brightness = brightness
                self.client.devices[key].is_on = brightness > 0
                # Notify coordinator of state change without triggering a scan
                self.async_set_updated_data(self.client.devices)
        return success

    async def async_turn_on(self, address: int) -> bool:
        """Turn on device."""
        success = await self.client.turn_on(address)
        if success:
            key = ("DALI", address)
            if key in self.client.devices:
                self.client.devices[key].is_on = True
                # Notify coordinator of state change without triggering a scan
                self.async_set_updated_data(self.client.devices)
        return success

    async def async_turn_off(self, address: int) -> bool:
        """Turn off device."""
        success = await self.client.turn_off(address)
        if success:
            key = ("DALI", address)
            if key in self.client.devices:
                self.client.devices[key].is_on = False
                self.client.devices[key].brightness = 0
                # Notify coordinator of state change without triggering a scan
                self.async_set_updated_data(self.client.devices)
        return success

    async def async_set_color_temp(
        self, address: int, kelvin: int
    ) -> bool:
        """Set device color temperature."""
        success = await self.client.set_color_temp(address, kelvin)
        if success:
            key = ("DALI", address)
            if key in self.client.devices:
                self.client.devices[key].color_temp = kelvin
                # Notify coordinator of state change without triggering a scan
                self.async_set_updated_data(self.client.devices)
        return success

    async def async_rescan_devices(self) -> dict[tuple[str, int], DaliDevice]:
        """Rescan for devices on the bus."""
        _LOGGER.info("Rescanning for DALI devices")
        
        # Get old devices for comparison
        old_devices = set(self.client.devices.keys())
        
        try:
            # Perform scan
            devices = await self.client.scan_devices()
        except ConnectionError as e:
            _LOGGER.error("Cannot rescan: %s", e)
            persistent_notification.async_create(
                self.hass,
                f"Rescan failed: {e}. Please check that the gateway is online and try again.",
                title="DALI Rescan Failed",
                notification_id=f"{DOMAIN}_rescan_failed",
            )
            return self.client.devices
        except Exception as e:
            _LOGGER.error("Error during rescan: %s", e)
            persistent_notification.async_create(
                self.hass,
                f"Rescan error: {e}",
                title="DALI Rescan Error",
                notification_id=f"{DOMAIN}_rescan_error",
            )
            return self.client.devices
        
        # Get new devices after scan
        new_devices = set(self.client.devices.keys())
        
        # Find newly discovered and missing devices
        added_devices = new_devices - old_devices
        missing_devices = old_devices - new_devices
        
        # Save to storage
        serialized_devices = {}
        for key, device in self.client.devices.items():
            serialized_devices[key] = self.storage.serialize_device(device)
        
        await self.storage.async_save(serialized_devices, datetime.now().isoformat())
        _LOGGER.info("Saved %d devices to storage", len(serialized_devices))
        
        # Report changes
        if added_devices:
            await self._report_new_devices(added_devices)
        
        if missing_devices:
            await self._report_missing_devices(missing_devices)
        
        await self.async_request_refresh()
        return devices
    
    async def _report_new_devices(self, device_keys: set[tuple[str, int]]) -> None:
        """Create notifications for newly discovered devices."""
        for key in device_keys:
            device = self.client.devices.get(key)
            if device:
                persistent_notification.async_create(
                    self.hass,
                    f"New {device.protocol} device found:\n"
                    f"Type: {device.device_type}\n"
                    f"Address: {device.address}\n"
                    f"Name: {device.device_name}",
                    "DALI Device Discovered",
                    f"dali_new_device_{device.protocol}_{device.address}",
                )
                _LOGGER.info(
                    "New device discovered: %s %s at address %d",
                    device.protocol,
                    device.device_type,
                    device.address,
                )
    
    async def _report_missing_devices(self, device_keys: set[tuple[str, int]]) -> None:
        """Create repair issues for missing devices."""
        from homeassistant.helpers import issue_registry as ir
        
        for key in device_keys:
            protocol, address = key
            
            # Get device info from old data if available
            device_name = "Unknown"
            device_type = "Unknown"
            if key in self.client.devices:
                device = self.client.devices[key]
                device_name = device.device_name
                device_type = device.device_type
            
            # Create repair issue
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"missing_device_{protocol}_{address}",
                is_fixable=True,
                severity=ir.IssueSeverity.WARNING,
                translation_key="missing_device",
                translation_placeholders={
                    "protocol": protocol,
                    "address": str(address),
                    "device_name": device_name,
                    "device_type": device_type,
                },
            )
            
            _LOGGER.warning(
                "Device missing from bus: %s %s at address %d - created repair issue",
                protocol,
                device_type,
                address,
            )
    
    async def async_remove_device(self, protocol: str, address: int) -> bool:
        """Remove a device from storage after user confirmation."""
        from homeassistant.helpers import issue_registry as ir
        
        key = (protocol, address)
        if key in self.client.devices:
            device = self.client.devices.pop(key)
            
            # Save updated devices to storage
            serialized_devices = {}
            for k, dev in self.client.devices.items():
                serialized_devices[k] = self.storage.serialize_device(dev)
            
            await self.storage.async_save(serialized_devices)
            
            # Remove the repair issue
            ir.async_delete_issue(
                self.hass,
                DOMAIN,
                f"missing_device_{protocol}_{address}",
            )
            
            _LOGGER.info(
                "Removed device: %s %s at address %d",
                protocol,
                device.device_type,
                address,
            )
            
            await self.async_request_refresh()
            return True
        
        return False

    async def async_step_up(self, address: int) -> bool:
        """Step up brightness."""
        success = await self.client.step_up(address)
        if success:
            # For step commands, we need to query the actual brightness
            # Schedule a refresh on next update cycle
            await self.async_request_refresh()
        return success

    async def async_step_down(self, address: int) -> bool:
        """Step down brightness."""
        success = await self.client.step_down(address)
        if success:
            # For step commands, we need to query the actual brightness
            # Schedule a refresh on next update cycle
            await self.async_request_refresh()
        return success

    async def async_recall_max(self, address: int) -> bool:
        """Recall maximum level."""
        success = await self.client.recall_max_level(address)
        if success:
            key = ("DALI", address)
            if key in self.client.devices:
                self.client.devices[key].is_on = True
                self.client.devices[key].brightness = 100
                # Notify coordinator of state change without triggering a scan
                self.async_set_updated_data(self.client.devices)
        return success

    def _handle_device_event(self, event_type: str, *args: Any) -> None:
        """Handle device events from the WebSocket connection."""
        if event_type == "state_update":
            # DALI device state changed (external command from wall switch, etc.)
            device = args[0] if args else None
            if device:
                _LOGGER.debug(
                    "External state update: %s address %d, brightness=%d%%, on=%s",
                    device.protocol,
                    device.address,
                    device.brightness,
                    device.is_on,
                )
                # Trigger coordinator update to notify all entities
                self.async_set_updated_data(self.client.devices)
        
        elif event_type == "dali2_event":
            # DALI2 instance event (pushbutton, sensor, etc.)
            device = args[0] if len(args) > 0 else None
            instance = args[1] if len(args) > 1 else None
            instance_info = args[2] if len(args) > 2 else None
            
            if device and instance is not None and instance_info:
                instance_type = instance_info.get("type", 0)
                _LOGGER.debug(
                    "DALI2 event: address %d, instance %d, type %d, data=%s",
                    device.address,
                    instance,
                    instance_type,
                    instance_info,
                )
                # Trigger coordinator update to notify binary_sensor and sensor entities
                self.async_set_updated_data(self.client.devices)

    def get_led_state(self, address: int, instance: int) -> bool | None:
        """Get the current state of a feedback LED."""
        return self._led_states.get((address, instance))

    def set_led_state(self, address: int, instance: int, is_on: bool) -> None:
        """Set the state of a feedback LED and notify listeners."""
        self._led_states[(address, instance)] = is_on
        # Trigger coordinator update to notify LED entities
        self.async_set_updated_data(self.client.devices)
