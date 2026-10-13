"""Pairing with the My Magic Home MCP gateway.

The config flow (and the options flow, to reconnect) calls :func:`async_pair`
with a one-time code generated in the gateway's admin panel. This module creates
a dedicated Home Assistant user and long-lived token for the gateway, sends them
to the gateway's ``/enroll`` endpoint, and returns what to store in the config
entry. The gateway tests the connection before accepting, so a successful pair
means the gateway can already reach this Home Assistant.
"""

from __future__ import annotations

import datetime as _dt
import logging
import secrets
from typing import Any
from urllib.parse import urlparse

import aiohttp
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.auth.models import TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import (
    CONF_GATEWAY_URL,
    CONF_HA_URL,
    CONF_REFRESH_TOKEN_ID,
    CONF_SITE_NAME,
    CONF_SITE_SLUG,
    CONF_USER_ID,
    GATEWAY_USER_NAME,
    MMH_DOMAIN_SUFFIX,
    SERVER_VERSION,
)

_LOGGER = logging.getLogger(__name__)

TOKEN_LIFETIME = _dt.timedelta(days=3650)
ENROLL_TIMEOUT = aiohttp.ClientTimeout(total=45)


class PairingError(Exception):
    """Pairing failed; the message is shown to the person in the flow."""


def suggest_site(hass: HomeAssistant) -> dict[str, str]:
    """Defaults for the pairing form, from the HA's own configuration."""
    external = hass.config.external_url or ""
    host = urlparse(external).hostname or ""
    slug = ""
    if host.endswith(MMH_DOMAIN_SUFFIX):
        slug = host[: -len(MMH_DOMAIN_SUFFIX)].rstrip(".")
    if not slug:
        slug = slugify(hass.config.location_name or "", separator="-")
    ha_url = external.rstrip("/") if external.startswith("https://") else ""
    if not ha_url and slug:
        ha_url = f"https://{slug}.{MMH_DOMAIN_SUFFIX.lstrip('.')}"
    return {"slug": slug, "name": hass.config.location_name or slug, "ha_url": ha_url}


async def _async_gateway_user(hass: HomeAssistant, user_id: str | None) -> tuple[Any, bool]:
    """The HA user the gateway acts as: reused when known, otherwise created."""
    if user_id:
        user = await hass.auth.async_get_user(user_id)
        if user is not None and user.is_active:
            return user, False
    # No credentials: this user can't log in to the UI, only use its tokens.
    user = await hass.auth.async_create_user(
        GATEWAY_USER_NAME, group_ids=[GROUP_ID_ADMIN], local_only=False
    )
    return user, True


async def async_pair(
    hass: HomeAssistant,
    *,
    gateway_url: str,
    code: str,
    slug: str,
    name: str,
    ha_url: str,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Enroll this HA in the gateway. Returns the config-entry data to store."""
    previous = previous or {}
    gateway_url = gateway_url.strip().rstrip("/")
    parsed = urlparse(gateway_url)
    local_dev = parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1")
    if parsed.scheme != "https" and not local_dev:
        raise PairingError("o endereço do gateway precisa começar com https://")

    user, created = await _async_gateway_user(hass, previous.get(CONF_USER_ID))
    refresh_token = await hass.auth.async_create_refresh_token(
        user,
        # LLAT client names must be unique per user; the suffix keeps quick
        # successive reconnections from colliding.
        client_name=f"MMH Gateway {dt_util.now().strftime('%Y-%m-%d %H:%M')} ({secrets.token_hex(3)})",
        token_type=TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
        access_token_expiration=TOKEN_LIFETIME,
    )
    access_token = hass.auth.async_create_access_token(refresh_token)

    payload = {
        "code": code.strip(),
        "slug": slug.strip().lower(),
        "name": name.strip(),
        "ha_url": ha_url.strip().rstrip("/"),
        "ha_token": access_token,
        "integration_version": SERVER_VERSION,
    }

    async def _rollback() -> None:
        hass.auth.async_remove_refresh_token(refresh_token)
        if created:
            await hass.auth.async_remove_user(user)

    try:
        session = async_get_clientsession(hass)
        async with session.post(
            f"{gateway_url}/enroll", json=payload, timeout=ENROLL_TIMEOUT
        ) as resp:
            try:
                body = await resp.json(content_type=None)
            except ValueError:
                body = {}
            if resp.status != 200 or not body.get("ok"):
                raise PairingError(body.get("error") or f"o gateway respondeu HTTP {resp.status}")
    except PairingError:
        await _rollback()
        raise
    except (aiohttp.ClientError, TimeoutError) as err:
        await _rollback()
        raise PairingError(f"não foi possível contatar o gateway em {gateway_url}") from err
    except Exception:
        await _rollback()
        raise

    # Rotate: the token from a previous pairing is no longer needed.
    old_id = previous.get(CONF_REFRESH_TOKEN_ID)
    if old_id and old_id != refresh_token.id:
        old = hass.auth.async_get_refresh_token(old_id)
        if old is not None:
            hass.auth.async_remove_refresh_token(old)

    site = body.get("site") or {}
    _LOGGER.info("mmh_mcp: paired with %s as site '%s'", gateway_url, site.get("slug", slug))
    return {
        CONF_GATEWAY_URL: gateway_url,
        CONF_SITE_SLUG: site.get("slug", payload["slug"]),
        CONF_SITE_NAME: site.get("name", payload["name"]),
        CONF_HA_URL: site.get("ha_url", payload["ha_url"]),
        CONF_USER_ID: user.id,
        CONF_REFRESH_TOKEN_ID: refresh_token.id,
    }


async def async_unpair(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Remove the gateway's HA user (and with it every token it had)."""
    user_id = data.get(CONF_USER_ID)
    if not user_id:
        return
    user = await hass.auth.async_get_user(user_id)
    if user is not None and user.name == GATEWAY_USER_NAME and not user.credentials:
        await hass.auth.async_remove_user(user)
        _LOGGER.info("mmh_mcp: removed the gateway user")
