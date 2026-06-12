"""Shared fixtures for dali_lunatone tests."""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Make `custom_components.dali_lunatone.<module>` importable without a Home
# Assistant install: register the package namespaces manually so importing a
# submodule does not execute the package __init__.py (which needs HA).
import types  # noqa: E402

for pkg_name, pkg_path in (
    ("custom_components", REPO_ROOT / "custom_components"),
    ("custom_components.dali_lunatone", REPO_ROOT / "custom_components" / "dali_lunatone"),
):
    if pkg_name not in sys.modules:
        module = types.ModuleType(pkg_name)
        module.__path__ = [str(pkg_path)]
        sys.modules[pkg_name] = module


def load_fixture(name: str) -> dict:
    """Load a JSON fixture captured from the real gateway."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def gw_devices() -> dict:
    """Real /devices response: 51 devices on lines 0/1/2."""
    return load_fixture("gw_devices.json")


@pytest.fixture
def gw_info() -> dict:
    """Real /info response: IoT4 gateway with descriptor.lines == 4."""
    return load_fixture("gw_info.json")


@pytest.fixture
def gw_zones() -> dict:
    """Real /zones response."""
    return load_fixture("gw_zones.json")
