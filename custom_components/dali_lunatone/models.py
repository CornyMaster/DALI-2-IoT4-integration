"""Line-aware data models for the Lunatone DALI-2 IoT(4) gateway REST API.

Pure Python (no Home Assistant imports) so the mapping logic is unit-testable
standalone. The gateway is the source of truth: ``GET /devices`` returns every
device on every DALI line with a globally unique ``id`` plus its ``line`` and
short ``address``. DALI short addresses and group numbers repeat per line, so
all lookups in here are keyed by ``(line, address)`` or ``(line, group)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# DALI-2 input instance types (IEC 62386-3xx)
INSTANCE_TYPE_PUSH_BUTTON = 1
INSTANCE_TYPE_ABSOLUTE_INPUT = 2
INSTANCE_TYPE_OCCUPANCY = 3
INSTANCE_TYPE_LIGHT_SENSOR = 4


def _feature_status(features: dict[str, Any], key: str) -> Any:
    """Return features[key]["status"] if present, else None."""
    value = features.get(key)
    if isinstance(value, dict):
        return value.get("status")
    return None


@dataclass
class LunatoneDevice:
    """One control-gear device as reported by GET /devices."""

    gw_id: int
    line: int
    address: int
    name: str
    available: bool
    groups: list[int]
    dali_types: list[int]
    features: dict[str, Any]
    is_on: bool
    brightness_pct: float | None
    color_temp_kelvin: int | None
    lamp_failure: bool
    control_gear_failure: bool
    status_raw: dict[str, Any]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> LunatoneDevice:
        features = data.get("features") or {}
        status = data.get("status") or {}

        switch_status = _feature_status(features, "switchable")
        dim_status = _feature_status(features, "dimmable")
        kelvin_status = _feature_status(features, "colorKelvin")

        return cls(
            gw_id=data["id"],
            line=data.get("line", 0),
            address=data.get("address", 0),
            name=data.get("name") or f"Line {data.get('line', 0)} DALI {data.get('address', 0)}",
            available=data.get("available", True),
            groups=list(data.get("groups") or []),
            dali_types=list(data.get("daliTypes") or []),
            features=features,
            is_on=bool(switch_status),
            brightness_pct=float(dim_status) if dim_status is not None else None,
            color_temp_kelvin=round(kelvin_status) if kelvin_status is not None else None,
            lamp_failure=bool(status.get("lampFailure", False)),
            control_gear_failure=bool(status.get("controlGearFailure", False)),
            status_raw=status,
        )

    @property
    def supports_switch(self) -> bool:
        return "switchable" in self.features

    @property
    def supports_dimming(self) -> bool:
        return "dimmable" in self.features

    @property
    def supports_color_temp(self) -> bool:
        return "colorKelvin" in self.features or "dimmableKelvin" in self.features


@dataclass
class InputInstance:
    """State of one DALI-2 input instance (button, occupancy, light sensor)."""

    instance_type: int
    state: bool = False
    event_type: str | None = None
    value: float | None = None
    has_feedback_led: bool = False


@dataclass
class InputDevice:
    """A DALI-2 input device (push button coupler, sensor) on one line."""

    line: int
    address: int
    name: str = ""
    instances: dict[int, InputInstance] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            self.name = f"Line {self.line} Input {self.address}"


@dataclass
class GatewayInfo:
    """Subset of GET /info we care about."""

    name: str
    version: str
    serial: int | None
    uid: str | None
    lines: int
    line_status: dict[int, str]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> GatewayInfo:
        descriptor = data.get("descriptor") or {}
        line_status: dict[int, str] = {}
        for key, value in (data.get("lines") or {}).items():
            try:
                line_status[int(key)] = value.get("lineStatus", "unknown")
            except (ValueError, AttributeError):
                continue
        return cls(
            name=data.get("name", "Lunatone DALI"),
            version=data.get("version", "unknown"),
            serial=(data.get("device") or {}).get("serial"),
            uid=data.get("uid"),
            lines=descriptor.get("lines", 1),
            line_status=line_status,
        )


@dataclass
class LunatoneData:
    """Coordinator data: full line-aware inventory of the gateway."""

    info: GatewayInfo
    devices: dict[int, LunatoneDevice] = field(default_factory=dict)
    by_line_addr: dict[tuple[int, int], int] = field(default_factory=dict)
    inputs: dict[tuple[int, int], InputDevice] = field(default_factory=dict)

    @classmethod
    def from_api(
        cls,
        info_data: dict[str, Any] | GatewayInfo,
        devices_data: list[dict[str, Any]],
        lines: set[int] | None = None,
        inputs: dict[tuple[int, int], InputDevice] | None = None,
    ) -> LunatoneData:
        info = (
            info_data
            if isinstance(info_data, GatewayInfo)
            else GatewayInfo.from_api(info_data)
        )
        data = cls(info=info, inputs=inputs or {})
        for raw in devices_data:
            device = LunatoneDevice.from_api(raw)
            if lines is not None and device.line not in lines:
                continue
            data.devices[device.gw_id] = device
            data.by_line_addr[(device.line, device.address)] = device.gw_id
        return data

    def device_by_line_addr(self, line: int, address: int) -> LunatoneDevice | None:
        gw_id = self.by_line_addr.get((line, address))
        return self.devices.get(gw_id) if gw_id is not None else None

    def groups_with_members(self) -> dict[tuple[int, int], set[int]]:
        """Map (line, group) -> set of gateway device ids that are members."""
        groups: dict[tuple[int, int], set[int]] = {}
        for device in self.devices.values():
            for group in device.groups:
                groups.setdefault((device.line, group), set()).add(device.gw_id)
        return groups

    def lines_with_devices(self) -> list[int]:
        return sorted({device.line for device in self.devices.values()})
