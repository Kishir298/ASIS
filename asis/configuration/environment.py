"""
Environment configuration for A.S.I.S.

Environment variables override built-in defaults. A ``.env`` file in the
project root or user configuration directory is loaded when present.
Secrets must never be hardcoded here.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from . import defaults

_PROJECT_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def _load_env_files() -> None:
    """Load .env files (project root and user config directory)."""
    candidates: list[Path] = [_PROJECT_ROOT_ENV_FILE]

    try:
        from .paths import get_config_directory

        candidates.append(get_config_directory() / ".env")
    except Exception:  # pragma: no cover - defensive during bootstrap
        pass

    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate, override=False)


def _get(name: str) -> str | None:
    """Return an environment variable, treating empty values as unset."""
    value = os.getenv(name)

    if value is None:
        return None

    value = value.strip()
    return value if value else None


def get_string(name: str, default: str) -> str:
    return _get(name) or default


def get_bool(name: str, default: bool) -> bool:
    value = _get(name)

    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on", "enabled"}


def get_int(name: str, default: int) -> int:
    value = _get(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def get_float(name: str, default: float) -> float:
    value = _get(name)

    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default


_load_env_files()

# Identity
IDENTITY_NAME = get_string("ASIS_IDENTITY_NAME", defaults.APP_NAME)
IDENTITY_TITLE = get_string("ASIS_IDENTITY_TITLE", defaults.IDENTITY_TITLE)
APP_VERSION = get_string("ASIS_APP_VERSION", defaults.APP_VERSION)
SHUTDOWN_PHRASE = get_string("ASIS_SHUTDOWN_PHRASE", defaults.SHUTDOWN_PHRASE)

# Runtime
DEBUG = get_bool("ASIS_DEBUG", defaults.DEBUG)
LOG_LEVEL = get_string("ASIS_LOG_LEVEL", defaults.LOG_LEVEL)

# AI
AI_PROVIDER = get_string("ASIS_AI_PROVIDER", defaults.AI_PROVIDER)
AI_MODEL = get_string("ASIS_AI_MODEL", defaults.AI_MODEL)
AI_ENDPOINT = get_string("ASIS_AI_ENDPOINT", defaults.AI_ENDPOINT)

AI_REQUEST_TIMEOUT = get_int("ASIS_AI_REQUEST_TIMEOUT", defaults.AI_REQUEST_TIMEOUT)
AI_TEMPERATURE = get_float("ASIS_AI_TEMPERATURE", defaults.AI_TEMPERATURE)
AI_MAX_CONTEXT_MESSAGES = get_int(
    "ASIS_AI_MAX_CONTEXT_MESSAGES", defaults.AI_MAX_CONTEXT_MESSAGES
)
AI_CONTEXT_CHAR_LIMIT = get_int(
    "ASIS_AI_CONTEXT_CHAR_LIMIT", defaults.AI_CONTEXT_CHAR_LIMIT
)

# Conversation
CONVERSATION_MAX_HISTORY = get_int(
    "ASIS_CONVERSATION_MAX_HISTORY", defaults.CONVERSATION_MAX_HISTORY
)

# Memory
MEMORY_PROVIDER = get_string("ASIS_MEMORY_PROVIDER", defaults.MEMORY_PROVIDER)
MEMORY_DATABASE_NAME = get_string(
    "ASIS_MEMORY_DATABASE_NAME", defaults.MEMORY_DATABASE_NAME
)

# Voice
VOICE_SAMPLE_RATE = get_int("ASIS_VOICE_SAMPLE_RATE", defaults.VOICE_SAMPLE_RATE)
VOICE_CHANNELS = get_int("ASIS_VOICE_CHANNELS", defaults.VOICE_CHANNELS)
VOICE_BLOCK_SIZE = get_int("ASIS_VOICE_BLOCK_SIZE", defaults.VOICE_BLOCK_SIZE)
VOICE_STT_ENGINE = get_string("ASIS_VOICE_STT_ENGINE", defaults.VOICE_STT_ENGINE)
VOICE_STT_MODEL = get_string("ASIS_VOICE_STT_MODEL", defaults.VOICE_STT_MODEL)
VOICE_STT_DEVICE = get_string("ASIS_VOICE_STT_DEVICE", defaults.VOICE_STT_DEVICE)
VOICE_STT_COMPUTE_TYPE = get_string(
    "ASIS_VOICE_STT_COMPUTE_TYPE", defaults.VOICE_STT_COMPUTE_TYPE
)
VOICE_STT_LANGUAGE = get_string("ASIS_VOICE_STT_LANGUAGE", defaults.VOICE_STT_LANGUAGE)
VOICE_TTS_ENGINE = get_string("ASIS_VOICE_TTS_ENGINE", defaults.VOICE_TTS_ENGINE)
VOICE_TTS_VOICE = get_string("ASIS_VOICE_TTS_VOICE", defaults.VOICE_TTS_VOICE)
VOICE_SPEAKER_ENGINE = get_string(
    "ASIS_VOICE_SPEAKER_ENGINE", defaults.VOICE_SPEAKER_ENGINE
)
VOICE_SPEAKER_CONFIDENCE = get_float(
    "ASIS_VOICE_SPEAKER_CONFIDENCE", defaults.VOICE_SPEAKER_CONFIDENCE
)
VOICE_WAKE_WORD = get_string("ASIS_VOICE_WAKE_WORD", defaults.VOICE_WAKE_WORD)

# Network
NETWORK_TIMEOUT = get_int("ASIS_NETWORK_TIMEOUT", defaults.NETWORK_TIMEOUT)
NETWORK_RETRIES = get_int("ASIS_NETWORK_RETRIES", defaults.NETWORK_RETRIES)

# Tools
TOOL_TIMEOUT = get_int("ASIS_TOOL_TIMEOUT", defaults.TOOL_TIMEOUT)

# Security / permissions
REQUIRE_CONFIRMATION_FOR_DANGEROUS = get_bool(
    "ASIS_CONFIRM_DANGEROUS_TOOLS", defaults.REQUIRE_CONFIRMATION_FOR_DANGEROUS
)

# Runtime
SHUTDOWN_TIMEOUT = get_int("ASIS_SHUTDOWN_TIMEOUT", defaults.SHUTDOWN_TIMEOUT)

# C.O.R.E. integration (optional external infrastructure; never secrets here)
CORE_ENABLED = get_bool("ASIS_CORE_ENABLED", defaults.CORE_ENABLED)
CORE_HOST = get_string("ASIS_CORE_HOST", defaults.CORE_HOST)
CORE_PORT = get_int("ASIS_CORE_PORT", defaults.CORE_PORT)
CORE_DEVICE_FILE = get_string("ASIS_CORE_DEVICE_FILE", defaults.CORE_DEVICE_FILE)
CORE_CA_FILE = get_string("ASIS_CORE_CA_FILE", defaults.CORE_CA_FILE)
CORE_INSECURE = get_bool("ASIS_CORE_INSECURE", defaults.CORE_INSECURE)
CORE_CONNECT_TIMEOUT = get_int(
    "ASIS_CORE_CONNECT_TIMEOUT", defaults.CORE_CONNECT_TIMEOUT
)
CORE_REQUEST_TIMEOUT = get_int(
    "ASIS_CORE_REQUEST_TIMEOUT", defaults.CORE_REQUEST_TIMEOUT
)
CORE_RECONNECT_ENABLED = get_bool(
    "ASIS_CORE_RECONNECT_ENABLED", defaults.CORE_RECONNECT_ENABLED
)
CORE_RECONNECT_DELAY = get_int(
    "ASIS_CORE_RECONNECT_DELAY", defaults.CORE_RECONNECT_DELAY
)
