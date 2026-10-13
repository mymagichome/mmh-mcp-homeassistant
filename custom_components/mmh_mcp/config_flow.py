"""Config flow for mmh_mcp (single-instance).

Step 1 (user): integration options. Step 2 (gateway): optional pairing with the
My Magic Home MCP gateway using a one-time code from its admin panel. The
options flow offers the same pairing again, to connect or reconnect later.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_ALLOW_DESTRUCTIVE,
    CONF_ALLOW_FIRE_EVENT,
    CONF_ALLOW_WRITE,
    CONF_GATEWAY_URL,
    CONF_HA_URL,
    CONF_PAIR_CODE,
    CONF_RATE_LIMIT_PER_MINUTE,
    CONF_SITE_NAME,
    CONF_SITE_SLUG,
    DEFAULT_ALLOW_DESTRUCTIVE,
    DEFAULT_ALLOW_FIRE_EVENT,
    DEFAULT_ALLOW_WRITE,
    DEFAULT_GATEWAY_URL,
    DEFAULT_RATE_LIMIT_PER_MINUTE,
    DOMAIN,
    TITLE,
)
from .gateway_link import PairingError, async_pair, suggest_site


def _options_schema(opts: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_ALLOW_WRITE, default=opts.get(CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE)
            ): bool,
            vol.Required(
                CONF_ALLOW_DESTRUCTIVE,
                default=opts.get(CONF_ALLOW_DESTRUCTIVE, DEFAULT_ALLOW_DESTRUCTIVE),
            ): bool,
            vol.Required(
                CONF_ALLOW_FIRE_EVENT,
                default=opts.get(CONF_ALLOW_FIRE_EVENT, DEFAULT_ALLOW_FIRE_EVENT),
            ): bool,
            vol.Required(
                CONF_RATE_LIMIT_PER_MINUTE,
                default=opts.get(CONF_RATE_LIMIT_PER_MINUTE, DEFAULT_RATE_LIMIT_PER_MINUTE),
            ): vol.All(int, vol.Range(min=0)),
        }
    )


def _gateway_schema(defaults: dict[str, Any], *, code_required: bool) -> vol.Schema:
    code_key = vol.Required(CONF_PAIR_CODE) if code_required else vol.Optional(CONF_PAIR_CODE)
    return vol.Schema(
        {
            code_key: str,
            vol.Required(CONF_SITE_SLUG, default=defaults.get(CONF_SITE_SLUG, "")): str,
            vol.Required(CONF_SITE_NAME, default=defaults.get(CONF_SITE_NAME, "")): str,
            vol.Required(CONF_HA_URL, default=defaults.get(CONF_HA_URL, "")): str,
            vol.Required(
                CONF_GATEWAY_URL, default=defaults.get(CONF_GATEWAY_URL, DEFAULT_GATEWAY_URL)
            ): str,
        }
    )


def _defaults_from(hass, data: dict[str, Any] | None = None) -> dict[str, Any]:
    suggested = suggest_site(hass)
    data = data or {}
    return {
        CONF_SITE_SLUG: data.get(CONF_SITE_SLUG) or suggested["slug"],
        CONF_SITE_NAME: data.get(CONF_SITE_NAME) or suggested["name"],
        CONF_HA_URL: data.get(CONF_HA_URL) or suggested["ha_url"],
        CONF_GATEWAY_URL: data.get(CONF_GATEWAY_URL) or DEFAULT_GATEWAY_URL,
    }


async def _try_pair(
    hass, user_input: dict[str, Any], previous: dict[str, Any] | None
) -> tuple[dict[str, Any] | None, dict[str, str], dict[str, str]]:
    """Returns (entry data, errors, description placeholders)."""
    try:
        data = await async_pair(
            hass,
            gateway_url=user_input[CONF_GATEWAY_URL],
            code=user_input[CONF_PAIR_CODE],
            slug=user_input[CONF_SITE_SLUG],
            name=user_input[CONF_SITE_NAME],
            ha_url=user_input[CONF_HA_URL],
            previous=previous,
        )
    except PairingError as err:
        return None, {"base": "pairing_failed"}, {"error": str(err)}
    return data, {}, {}


class HaMcpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._options: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            self._options = dict(user_input)
            return await self.async_step_gateway()
        return self.async_show_form(step_id="user", data_schema=_options_schema({}))

    async def async_step_gateway(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"error": ""}
        defaults = _defaults_from(self.hass)
        if user_input is not None:
            defaults = {**defaults, **user_input}
            if not (user_input.get(CONF_PAIR_CODE) or "").strip():
                # Pairing skipped: endpoint only, connect later in the options.
                return self.async_create_entry(title=TITLE, data={}, options=self._options)
            # The gateway tests /api/mmh_mcp before accepting, so expose it now
            # with the options chosen in step 1; closed again if pairing fails.
            from . import async_register_endpoint, options_from

            async_register_endpoint(self.hass, options_from(self._options), None)
            data, errors, placeholders = await _try_pair(self.hass, user_input, None)
            if data is None:
                self.hass.data.pop(DOMAIN, None)
            else:
                return self.async_create_entry(
                    title=f"{TITLE} · {data[CONF_SITE_SLUG]}", data=data, options=self._options
                )
        return self.async_show_form(
            step_id="gateway",
            data_schema=_gateway_schema(defaults, code_required=False),
            errors=errors,
            description_placeholders=placeholders,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return HaMcpOptionsFlow(config_entry)


class HaMcpOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        return self.async_show_menu(step_id="init", menu_options=["settings", "gateway"])

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="settings", data_schema=_options_schema(self._entry.options)
        )

    async def async_step_gateway(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"error": ""}
        defaults = _defaults_from(self.hass, dict(self._entry.data))
        if user_input is not None:
            defaults = {**defaults, **user_input}
            data, errors, placeholders = await _try_pair(
                self.hass, user_input, dict(self._entry.data)
            )
            if data is not None:
                self.hass.config_entries.async_update_entry(
                    self._entry, data=data, title=f"{TITLE} · {data[CONF_SITE_SLUG]}"
                )
                # Keep the current settings; only the pairing changed.
                return self.async_create_entry(title="", data=dict(self._entry.options))
        return self.async_show_form(
            step_id="gateway",
            data_schema=_gateway_schema(defaults, code_required=True),
            errors=errors,
            description_placeholders=placeholders,
        )
