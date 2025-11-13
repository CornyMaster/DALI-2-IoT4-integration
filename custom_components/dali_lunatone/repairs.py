"""Repairs platform for Lunatone DALI-2 IoT integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DATA_COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Create flow for fixing missing device issues."""
    if issue_id.startswith("missing_device_"):
        return MissingDeviceRepairFlow(issue_id)
    
    return ConfirmRepairFlow()


class MissingDeviceRepairFlow(RepairsFlow):
    """Handler for missing device repair flow."""

    def __init__(self, issue_id: str) -> None:
        """Initialize repair flow."""
        super().__init__()
        self.issue_id = issue_id
        
        # Parse issue_id: "missing_device_DALI_4" -> protocol="DALI", address=4
        parts = issue_id.replace("missing_device_", "").rsplit("_", 1)
        self.protocol = parts[0]
        self.address = int(parts[1])

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the first step of the repair flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the confirm step of the repair flow."""
        if user_input is not None:
            # User confirmed, remove the device
            for entry_id, entry_data in self.hass.data[DOMAIN].items():
                coordinator = entry_data[DATA_COORDINATOR]
                success = await coordinator.async_remove_device(self.protocol, self.address)
                if success:
                    return self.async_create_entry(title="", data={})
            
            # Device not found
            _LOGGER.error(
                "Could not find device to remove: %s address %d",
                self.protocol,
                self.address,
            )
            return self.async_abort(reason="device_not_found")

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "protocol": self.protocol,
                "address": str(self.address),
            },
        )
