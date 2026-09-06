"""
Environment configuration for Forza.

Environment variables override built-in defaults.
No secrets or machine-specific values should be hardcoded here.
"""

from __future__ import annotations

import os
from typing import Optional

from . import defaults


def _get(name: str) -> Optional[str]:
    """Return an environment variable, treating empty values as unset."""
    value = os.getenv(name)
    if value is None:
        return None

    value = value.strip()
    return value if value else None


def get_string(name: str, default: str) -> str:
    """Get a string environment variable with a fallback."""
    return _get(name) or default


def get_bool(name: str, default: bool) -> bool:
    """Get a boolean environment variable with a fallback."""
    value = _get(name)

    if value is None:
        return default

    return value.lower() in {
        "1",
        "true",
        "yes",
        "on",
        "enabled",
    }


def get_int(name: str, default: int) -> int:
    """Get an integer environment variable with a fallback."""
    value = _get(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def get_float(name: str, default: float) -> float:
    """Get a floating-point environment variable with a fallback."""
    value = _get(name)

    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Forza configuration
# ---------------------------------------------------------------------------

APP_NAME = get_string("FORZA_APP_NAME", defaults.APP_NAME)
APP_VERSION = get_string("FORZA_APP_VERSION", defaults.APP_VERSION)

DEBUG = get_bool("FORZA_DEBUG", defaults.DEBUG)
LOG_LEVEL = get_string("FORZA_LOG_LEVEL", defaults.LOG_LEVEL)

# AI
AI_PROVIDER = get_string("FORZA_AI_PROVIDER", defaults.AI_PROVIDER)
AI_MODEL = get_string("FORZA_AI_MODEL", defaults.AI_MODEL)
AI_ENDPOINT = get_string("FORZA_AI_ENDPOINT", defaults.AI_ENDPOINT)

AI_REQUEST_TIMEOUT = get_int(
    "FORZA_AI_REQUEST_TIMEOUT",
    defaults.AI_REQUEST_TIMEOUT,
)

AI_TEMPERATURE = get_float(
    "FORZA_AI_TEMPERATURE",
    defaults.AI_TEMPERATURE,
)

AI_MAX_CONTEXT_MESSAGES = get_int(
    "FORZA_AI_MAX_CONTEXT_MESSAGES",
    defaults.AI_MAX_CONTEXT_MESSAGES,
)

# Network
NETWORK_TIMEOUT = get_int(
    "FORZA_NETWORK_TIMEOUT",
    defaults.NETWORK_TIMEOUT,
)

NETWORK_RETRIES = get_int(
    "FORZA_NETWORK_RETRIES",
    defaults.NETWORK_RETRIES,
)

# Tools
TOOL_TIMEOUT = get_int(
    "FORZA_TOOL_TIMEOUT",
    defaults.TOOL_TIMEOUT,
)

# Security
REQUIRE_CONFIRMATION_FOR_DANGEROUS_TOOLS = get_bool(
    "FORZA_CONFIRM_DANGEROUS_TOOLS",
    defaults.REQUIRE_CONFIRMATION_FOR_DANGEROUS_TOOLS,
)

# Runtime
SHUTDOWN_TIMEOUT = get_int(
    "FORZA_SHUTDOWN_TIMEOUT",
    defaults.SHUTDOWN_TIMEOUT,
)