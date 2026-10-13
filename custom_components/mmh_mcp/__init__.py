"""mmh_mcp — Home Assistant MCP server (generic tools)."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_ALLOW_DESTRUCTIVE,
    CONF_ALLOW_FIRE_EVENT,
    CONF_ALLOW_WRITE,
    CONF_RATE_LIMIT_PER_MINUTE,
    DEFAULT_ALLOW_DESTRUCTIVE,
    DEFAULT_ALLOW_FIRE_EVENT,
    DEFAULT_ALLOW_WRITE,
    DEFAULT_RATE_LIMIT_PER_MINUTE,
    DOMAIN,
    VIEW_URL,
)
from .http import MCPView

_LOGGER = logging.getLogger(__name__)

VIEW_REGISTERED_KEY = f"{DOMAIN}_view_registered"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    return True


def async_register_endpoint(hass: HomeAssistant, options: dict, entry_id: str | None) -> None:
    """Activate /api/mmh_mcp with ``options``.

    Called by the entry setup and also by the config flow, which must expose the
    endpoint before the entry exists so the gateway can test it while pairing.
    The aiohttp view can't be unregistered, so it is registered once per run;
    without options in hass.data it refuses requests (see http.py).
    """
    # Import tool modules so they register into the TOOLS registry.
    from . import tools  # noqa: F401  (import side-effects)

    hass.data[DOMAIN] = {"entry_id": entry_id, "options": options}
    if not hass.data.get(VIEW_REGISTERED_KEY):
        hass.http.register_view(MCPView(hass))
        hass.data[VIEW_REGISTERED_KEY] = True
        _LOGGER.info("mmh_mcp: MCP endpoint registered at %s", VIEW_URL)


def options_from(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        CONF_ALLOW_WRITE: raw.get(CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE),
        CONF_ALLOW_DESTRUCTIVE: raw.get(CONF_ALLOW_DESTRUCTIVE, DEFAULT_ALLOW_DESTRUCTIVE),
        CONF_ALLOW_FIRE_EVENT: raw.get(CONF_ALLOW_FIRE_EVENT, DEFAULT_ALLOW_FIRE_EVENT),
        CONF_RATE_LIMIT_PER_MINUTE: raw.get(
            CONF_RATE_LIMIT_PER_MINUTE, DEFAULT_RATE_LIMIT_PER_MINUTE
        ),
    }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    async_register_endpoint(hass, options_from(entry.options), entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # HA does not provide a public API to unregister a view; the route stays
    # but will reject calls because hass.data[DOMAIN] no longer carries options.
    hass.data.pop(DOMAIN, None)
    _LOGGER.warning("mmh_mcp: entry unloaded; the /api/mmh_mcp route remains until HA restart")
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    hass.data[DOMAIN]["options"] = options_from(entry.options)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Integration deleted: remove the gateway's HA user and its tokens."""
    from .gateway_link import async_unpair

    await async_unpair(hass, dict(entry.data))
