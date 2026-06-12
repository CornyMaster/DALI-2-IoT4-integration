"""Fixtures for tests that need a running Home Assistant test instance.

These tests require pytest-homeassistant-custom-component, which only runs
on Linux (HA imports fcntl). On Windows the whole directory is skipped.
"""

import pytest

pytest.importorskip("homeassistant")

from aioresponses import aioresponses  # noqa: E402
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # noqa: E402
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.lunatone_dali2_iot4.api import LunatoneRestClient  # noqa: E402
from custom_components.lunatone_dali2_iot4.const import (  # noqa: E402
    CONF_HOST,
    CONF_PORT,
    DOMAIN,
)
from custom_components.lunatone_dali2_iot4.coordinator import LunatoneCoordinator  # noqa: E402

HOST = "gw.example"
BASE = f"http://{HOST}"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading the integration from custom_components/."""
    yield


@pytest.fixture(scope="session", autouse=True)
def _start_pycares_shutdown_thread():
    """Start pycares' process-wide helper thread before any test runs.

    aiohttp's AsyncResolver spawns a daemon thread on first use that lives for
    the rest of the process; starting it here keeps it out of the per-test
    lingering-thread check.
    """
    try:
        import pycares

        pycares.Channel()
    except ImportError:
        pass
    yield


@pytest.fixture
def config_entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PORT: 80},
        options={},
        title="Lunatone DALI-2 IoT4",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_gateway(gw_info, gw_devices):
    """Mock the gateway REST endpoints with the real fixture data."""
    with aioresponses() as mock:
        mock.get(f"{BASE}/info", payload=gw_info, repeat=True)
        mock.get(f"{BASE}/devices", payload=gw_devices, repeat=True)
        mock.get(f"{BASE}/sensors", payload={"sensors": []}, repeat=True)
        yield mock


@pytest.fixture
async def coordinator(hass, config_entry, mock_gateway):
    """A coordinator that has completed its first refresh against the mock."""
    client = LunatoneRestClient(async_get_clientsession(hass), HOST)
    coordinator = LunatoneCoordinator(hass, config_entry, client)
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    return coordinator
