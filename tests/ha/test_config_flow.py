"""Config flow tests: auto-detected line count, line selection in the GUI."""

from unittest.mock import patch

import aiohttp
import pytest

pytest.importorskip("homeassistant")

from aioresponses import aioresponses  # noqa: E402
from homeassistant import config_entries  # noqa: E402
from homeassistant.data_entry_flow import FlowResultType  # noqa: E402

from custom_components.lunatone_dali2_iot4.const import (  # noqa: E402
    CONF_ENABLE_GLOBAL_BROADCAST,
    CONF_HOST,
    CONF_LINES,
    CONF_POLLING_INTERVAL,
    CONF_PORT,
    DOMAIN,
)

from .conftest import HOST  # noqa: E402


async def test_full_flow_detects_4_lines(hass, mock_gateway):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: 80}
    )
    # line selection step with the 4 auto-detected lines
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "lines"
    schema_key = next(iter(result["data_schema"].schema))
    assert result["data_schema"].schema[schema_key].options == {
        "0": "Line 0",
        "1": "Line 1",
        "2": "Line 2",
        "3": "Line 3",
    }

    with patch(
        "custom_components.lunatone_dali2_iot4.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_LINES: ["0", "1", "3"]}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: HOST, CONF_PORT: 80}
    assert result["options"][CONF_LINES] == [0, 1, 3]
    assert result["options"][CONF_POLLING_INTERVAL] == 30
    assert result["options"][CONF_ENABLE_GLOBAL_BROADCAST] is False
    entry = result["result"]
    assert entry.unique_id == "67329271-edda-4bc1-9213-7416fbe99120"


async def test_flow_cannot_connect(hass):
    """A connection error is surfaced as cannot_connect."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with aioresponses() as mock:
        mock.get(
            "http://unreachable.example/info",
            exception=aiohttp.ClientConnectionError("connection refused"),
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "unreachable.example", CONF_PORT: 80}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
