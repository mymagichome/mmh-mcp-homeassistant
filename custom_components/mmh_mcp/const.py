"""Constants for the mmh_mcp integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "mmh_mcp"
TITLE: Final = "MMH MCP"

VIEW_URL: Final = "/api/mmh_mcp"

CONF_ALLOW_WRITE: Final = "allow_write"
CONF_ALLOW_DESTRUCTIVE: Final = "allow_destructive"
CONF_ALLOW_FIRE_EVENT: Final = "allow_fire_event"
CONF_RATE_LIMIT_PER_MINUTE: Final = "rate_limit_per_minute"

DEFAULT_ALLOW_WRITE: Final = True
DEFAULT_ALLOW_DESTRUCTIVE: Final = False
DEFAULT_ALLOW_FIRE_EVENT: Final = False
DEFAULT_RATE_LIMIT_PER_MINUTE: Final = 600

PROTOCOL_VERSION: Final = "2025-06-18"
SERVER_NAME: Final = "mmh_mcp"
SERVER_VERSION: Final = "1.1.1"
# Upstream czechbol/hass-mcp version this fork is based on.
UPSTREAM_VERSION: Final = "2.2.2"

# Key under each tool's ``_meta`` carrying its permission classes, read by the
# MMH gateway to enforce the same read/write/destructive split per user.
META_PERMISSIONS_KEY: Final = "br.com.mymagichome/permissions"

# Pairing with the My Magic Home MCP gateway (config entry data keys).
CONF_PAIR_CODE: Final = "code"
CONF_GATEWAY_URL: Final = "gateway_url"
CONF_SITE_SLUG: Final = "site_slug"
CONF_SITE_NAME: Final = "site_name"
CONF_HA_URL: Final = "ha_url"
CONF_USER_ID: Final = "gateway_user_id"
CONF_REFRESH_TOKEN_ID: Final = "gateway_refresh_token_id"

DEFAULT_GATEWAY_URL: Final = "https://mcp.mymagichome.com.br"
GATEWAY_USER_NAME: Final = "MMH Gateway"
MMH_DOMAIN_SUFFIX: Final = ".mymagichome.com.br"
