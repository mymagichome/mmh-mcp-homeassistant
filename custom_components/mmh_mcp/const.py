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
SERVER_VERSION: Final = "1.0.0"
# Upstream czechbol/hass-mcp version this fork is based on.
UPSTREAM_VERSION: Final = "2.2.2"

# Key under each tool's ``_meta`` carrying its permission classes, read by the
# MMH gateway to enforce the same read/write/destructive split per user.
META_PERMISSIONS_KEY: Final = "br.com.mymagichome/permissions"
