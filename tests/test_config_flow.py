"""Config flow and gateway pairing, against a real (test) Home Assistant."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.mmh_mcp.const import (
    CONF_GATEWAY_URL,
    CONF_REFRESH_TOKEN_ID,
    CONF_SITE_SLUG,
    CONF_USER_ID,
    DOMAIN,
    GATEWAY_USER_NAME,
)

GATEWAY = "https://mcp.example.com"
OPTIONS = {
    "allow_write": True,
    "allow_destructive": False,
    "allow_fire_event": False,
    "rate_limit_per_minute": 600,
}


@pytest.fixture(autouse=True)
def _custom_integrations(enable_custom_integrations: None) -> None:
    """Make custom_components/ loadable in these tests only."""


@pytest.fixture
async def site_config(hass: HomeAssistant) -> None:
    await hass.config.async_update(
        location_name="Casa Business", external_url="https://business.mymagichome.com.br"
    )


def _pair_input(**overrides: Any) -> dict[str, Any]:
    return {
        "code": "MMH-ABCDE-FGHJK",
        "site_slug": "business",
        "site_name": "MMH Business",
        "ha_url": "https://business.mymagichome.com.br",
        "gateway_url": GATEWAY,
        **overrides,
    }


async def _start(hass: HomeAssistant) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], OPTIONS)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "gateway"
    return result


async def _gateway_users(hass: HomeAssistant):
    return [u for u in await hass.auth.async_get_users() if u.name == GATEWAY_USER_NAME]


async def test_suggests_site_from_external_url(hass: HomeAssistant, site_config: None) -> None:
    result = await _start(hass)
    defaults = {
        str(k): k.default()
        for k in result["data_schema"].schema
        if hasattr(k, "default") and callable(k.default)
    }
    assert defaults["site_slug"] == "business"
    assert defaults["site_name"] == "Casa Business"
    assert defaults["ha_url"] == "https://business.mymagichome.com.br"
    assert defaults["gateway_url"] == "https://mcp.mymagichome.com.br"


async def test_pairing_success_creates_user_token_and_entry(
    hass: HomeAssistant, site_config: None, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(
        f"{GATEWAY}/enroll",
        json={
            "ok": True,
            "site": {
                "slug": "business",
                "name": "MMH Business",
                "ha_url": "https://business.mymagichome.com.br",
            },
        },
    )
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], _pair_input())

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "MMH MCP · business"
    assert result["options"] == OPTIONS
    data = result["data"]
    assert data[CONF_SITE_SLUG] == "business"
    assert data[CONF_GATEWAY_URL] == GATEWAY

    # What the gateway received: the code and a working token for an admin user.
    sent = aioclient_mock.mock_calls[0][2]
    assert sent["code"] == "MMH-ABCDE-FGHJK"
    refresh = hass.auth.async_validate_access_token(sent["ha_token"])
    assert refresh is not None and refresh.id == data[CONF_REFRESH_TOKEN_ID]
    user = refresh.user
    assert user.id == data[CONF_USER_ID]
    assert user.name == GATEWAY_USER_NAME and user.is_admin and not user.credentials
    assert user.local_only is False


async def test_pairing_error_is_shown_and_rolled_back(
    hass: HomeAssistant, site_config: None, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(
        f"{GATEWAY}/enroll",
        status=403,
        json={"ok": False, "error": "código de pareamento inválido"},
    )
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], _pair_input())

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "pairing_failed"}
    assert result["description_placeholders"]["error"] == "código de pareamento inválido"
    # Nothing left behind: no gateway user, no token.
    assert await _gateway_users(hass) == []


async def test_gateway_unreachable(
    hass: HomeAssistant, site_config: None, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(f"{GATEWAY}/enroll", exc=TimeoutError())
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], _pair_input())
    assert result["errors"] == {"base": "pairing_failed"}
    assert "não foi possível contatar o gateway" in result["description_placeholders"]["error"]
    assert await _gateway_users(hass) == []


async def test_rejects_plain_http_gateway(hass: HomeAssistant, site_config: None) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _pair_input(gateway_url="http://mcp.example.com")
    )
    assert result["errors"] == {"base": "pairing_failed"}
    assert await _gateway_users(hass) == []


async def test_skipping_pairing_creates_plain_entry(hass: HomeAssistant, site_config: None) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], _pair_input(code=""))
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {}
    assert await _gateway_users(hass) == []


async def test_reconnect_rotates_token_and_reuses_user(
    hass: HomeAssistant, site_config: None, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(f"{GATEWAY}/enroll", json={"ok": True, "site": {"slug": "business"}})
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], _pair_input())
    entry = result["result"]
    first = dict(entry.data)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "gateway"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _pair_input(code="MMH-ZZZZZ-YYYYY")
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == OPTIONS  # settings untouched

    assert entry.data[CONF_USER_ID] == first[CONF_USER_ID]
    assert entry.data[CONF_REFRESH_TOKEN_ID] != first[CONF_REFRESH_TOKEN_ID]
    assert hass.auth.async_get_refresh_token(first[CONF_REFRESH_TOKEN_ID]) is None
    assert len(await _gateway_users(hass)) == 1


async def test_removing_entry_removes_gateway_user(
    hass: HomeAssistant, site_config: None, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(f"{GATEWAY}/enroll", json={"ok": True, "site": {"slug": "business"}})
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], _pair_input())
    entry = result["result"]
    await hass.async_block_till_done()
    assert len(await _gateway_users(hass)) == 1

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert await _gateway_users(hass) == []


async def test_single_instance(hass: HomeAssistant) -> None:
    MockConfigEntry(domain=DOMAIN, data={}, options=OPTIONS).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_endpoint_is_live_while_gateway_tests_it(
    hass: HomeAssistant, site_config: None, aioclient_mock: AiohttpClientMocker
) -> None:
    from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse

    seen: dict[str, Any] = {}

    async def gateway(method, url, data):
        # What the gateway would hit in its connection test.
        seen["options"] = hass.data.get(DOMAIN, {}).get("options")
        return AiohttpClientMockResponse(
            method, url, status=502, json={"ok": False, "error": "teste"}
        )

    aioclient_mock.post(f"{GATEWAY}/enroll", side_effect=gateway)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], _pair_input())

    assert seen["options"] == OPTIONS  # endpoint enabled with the step-1 options
    assert result["errors"] == {"base": "pairing_failed"}
    assert DOMAIN not in hass.data  # closed again after the failure


async def test_slug_is_normalized_before_sending(
    hass: HomeAssistant, site_config: None, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(f"{GATEWAY}/enroll", json={"ok": True, "site": {"slug": "diego-pasa"}})
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _pair_input(site_slug="Diego Pasã")
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert aioclient_mock.mock_calls[0][2]["slug"] == "diego-pasa"


async def test_empty_slug_is_rejected_without_creating_anything(
    hass: HomeAssistant, site_config: None
) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _pair_input(site_slug="!!")
    )
    assert result["errors"] == {"base": "pairing_failed"}
    assert "identificador" in result["description_placeholders"]["error"]
    assert await _gateway_users(hass) == []
