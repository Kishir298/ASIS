"""
Centralized validation for A.S.I.S. configuration.

Runs after parsing and before settings become active: any invalid value
raises ``ConfigurationError`` naming the field and constraint. Invalid
configuration never silently becomes a default. Provider-specific value
checks belong to the provider/factory layer, not here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from asis.errors import ConfigurationError

if TYPE_CHECKING:  # avoid a runtime cycle with settings.py
    from .settings import Settings

LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
_TEMPERATURE_MAX = 2.0


def _require_non_empty(section: str, field: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(
            f"Invalid configuration {section}.{field}: must be a non-empty string."
        )


def _require_positive_int(section: str, field: str, value: int) -> None:
    if not isinstance(value, bool) and isinstance(value, int) and value > 0:
        return
    raise ConfigurationError(
        f"Invalid configuration {section}.{field}: expected a positive "
        f"integer, received {value!r}."
    )


def _require_non_negative_int(section: str, field: str, value: int) -> None:
    if not isinstance(value, bool) and isinstance(value, int) and value >= 0:
        return
    raise ConfigurationError(
        f"Invalid configuration {section}.{field}: expected an integer >= 0, "
        f"received {value!r}."
    )


def _require_unit_interval(section: str, field: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(
            f"Invalid configuration {section}.{field}: expected a number "
            f"between 0 and 1, received {value!r}."
        )
    if not 0.0 <= float(value) <= 1.0:
        raise ConfigurationError(
            f"Invalid configuration {section}.{field}: expected a number "
            f"between 0 and 1, received {value!r}."
        )


def _validate_endpoint(endpoint: str) -> None:
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ConfigurationError(
            "Invalid configuration ai.endpoint: must be a non-empty endpoint URL."
        )
    parsed = urlparse(endpoint.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ConfigurationError(
            f"Invalid configuration ai.endpoint: expected an http(s) URL, "
            f"received {endpoint!r}."
        )


def _validate_database_name(name: str) -> None:
    _require_non_empty("memory", "database_name", name)
    if "/" in name or "\\" in name or ".." in name or "\x00" in name:
        raise ConfigurationError(
            f"Invalid configuration memory.database_name: unsafe database "
            f"name {name!r}."
        )
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    if any(c not in allowed for c in name):
        raise ConfigurationError(
            f"Invalid configuration memory.database_name: unsupported "
            f"characters in {name!r}."
        )


def validate_settings(settings: Settings) -> Settings:
    """Validate a fully built ``Settings`` object, returning it unchanged."""
    # AI
    _require_non_empty("ai", "provider", settings.ai.provider)
    _require_non_empty("ai", "model", settings.ai.model)
    _validate_endpoint(settings.ai.endpoint)
    _require_positive_int("ai", "request_timeout", settings.ai.request_timeout)
    temp = settings.ai.temperature
    if (
        isinstance(temp, bool)
        or not isinstance(temp, (int, float))
        or not 0.0 <= float(temp) <= _TEMPERATURE_MAX
    ):
        raise ConfigurationError(
            f"Invalid configuration ai.temperature: expected a number "
            f"between 0 and {_TEMPERATURE_MAX}, received {temp!r}."
        )
    _require_positive_int(
        "ai", "max_context_messages", settings.ai.max_context_messages
    )
    _require_positive_int("ai", "context_char_limit", settings.ai.context_char_limit)

    # Conversation
    _require_positive_int(
        "conversation", "max_history", settings.conversation.max_history
    )

    # Network
    _require_positive_int("network", "timeout", settings.network.timeout)
    _require_non_negative_int("network", "retries", settings.network.retries)

    # Tools
    _require_positive_int("tools", "timeout", settings.tools.timeout)

    # Security
    if not isinstance(settings.security.require_confirmation_for_dangerous, bool):
        raise ConfigurationError(
            "Invalid configuration "
            "security.require_confirmation_for_dangerous: expected a boolean."
        )

    # Memory
    _require_non_empty("memory", "provider", settings.memory.provider)
    _validate_database_name(settings.memory.database_name)

    # Voice: audio
    _require_non_empty("voice", "input_engine", settings.voice.input_engine)
    _require_non_empty("voice", "output_engine", settings.voice.output_engine)
    _require_positive_int("voice", "sample_rate", settings.voice.sample_rate)
    _require_positive_int("voice", "channels", settings.voice.channels)
    _require_positive_int("voice", "block_size", settings.voice.block_size)

    # Voice: STT (language may be empty meaning automatic detection)
    _require_non_empty("voice.stt", "engine", settings.voice.stt.engine)
    _require_non_empty("voice.stt", "model", settings.voice.stt.model)
    _require_non_empty("voice.stt", "device", settings.voice.stt.device)
    _require_non_empty("voice.stt", "compute_type", settings.voice.stt.compute_type)

    # Voice: TTS (voice may be empty when the provider auto-selects)
    _require_non_empty("voice.tts", "engine", settings.voice.tts.engine)
    _require_positive_int("voice.tts", "sample_rate", settings.voice.tts.sample_rate)

    # Voice: speaker
    _require_non_empty("voice.speaker", "engine", settings.voice.speaker.engine)
    _require_non_empty("voice.speaker", "model", settings.voice.speaker.model)
    _require_non_empty("voice.speaker", "device", settings.voice.speaker.device)
    _require_unit_interval(
        "voice.speaker", "confidence", settings.voice.speaker.confidence
    )
    _require_unit_interval(
        "voice.speaker", "threshold", settings.voice.speaker.threshold
    )
    _require_non_empty("voice.speaker", "metric", settings.voice.speaker.metric)

    # Voice: wake word required whenever wake-word mode is enabled
    _require_non_empty("voice.wake", "engine", settings.voice.wake.engine)
    _require_unit_interval("voice.wake", "threshold", settings.voice.wake.threshold)
    if settings.voice.wake.engine.strip().lower() not in ("mock", "none", "off", ""):
        _require_non_empty("voice", "wake_word", settings.voice.wake_word)

    # Voice: VAD
    _require_non_empty("voice.vad", "engine", settings.voice.vad.engine)
    _require_unit_interval("voice.vad", "threshold", settings.voice.vad.threshold)

    # Voice: utterance bounds (must stay positive to avoid infinite capture)
    for field_name in ("max_utterance_s", "silence_s"):
        value = getattr(settings.voice, field_name)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not float(value) > 0
        ):
            raise ConfigurationError(
                f"Invalid configuration voice.{field_name}: expected a "
                f"positive number, received {value!r}."
            )

    # Runtime
    _require_positive_int(
        "runtime", "shutdown_timeout", settings.runtime.shutdown_timeout
    )
    if (
        not isinstance(settings.runtime.log_level, str)
        or settings.runtime.log_level.strip().upper() not in LOG_LEVELS
    ):
        raise ConfigurationError(
            f"Invalid configuration runtime.log_level: expected one of "
            f"{sorted(LOG_LEVELS)}, received "
            f"{settings.runtime.log_level!r}."
        )

    # Coding (A.S.C.S. capability)
    _require_non_empty("coding", "default_mode", settings.coding.default_mode)
    if settings.coding.default_mode.strip().lower() not in ("general", "coding"):
        raise ConfigurationError(
            "Invalid configuration coding.default_mode: expected 'general' "
            f"or 'coding', received {settings.coding.default_mode!r}."
        )
    _require_positive_int("coding", "command_timeout", settings.coding.command_timeout)
    _require_positive_int("coding", "max_file_size", settings.coding.max_file_size)
    _require_positive_int("coding", "max_output_size", settings.coding.max_output_size)

    # C.O.R.E. uplink (optional infrastructure; standalone by default)
    _require_non_empty("core", "host", settings.core.host)
    if "\x00" in settings.core.host:
        raise ConfigurationError(
            "Invalid configuration core.host: must not contain NUL bytes."
        )
    port = settings.core.port
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ConfigurationError(
            f"Invalid configuration core.port: expected an integer "
            f"between 1 and 65535, received {port!r}."
        )
    for field_name in ("connect_timeout", "request_timeout"):
        value = getattr(settings.core, field_name)
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 600:
            raise ConfigurationError(
                f"Invalid configuration core.{field_name}: expected an "
                f"integer between 1 and 600, received {value!r}."
            )
    delay = settings.core.reconnect_delay
    if isinstance(delay, bool) or not isinstance(delay, int) or not 0 <= delay <= 300:
        raise ConfigurationError(
            f"Invalid configuration core.reconnect_delay: expected an "
            f"integer between 0 and 300, received {delay!r}."
        )
    for field_name in ("enabled", "insecure", "reconnect_enabled"):
        if not isinstance(getattr(settings.core, field_name), bool):
            raise ConfigurationError(
                f"Invalid configuration core.{field_name}: expected a boolean."
            )
    for field_name in ("device_file", "ca_file"):
        value = getattr(settings.core, field_name)
        if not isinstance(value, str):
            raise ConfigurationError(
                f"Invalid configuration core.{field_name}: expected a string."
            )
        if "\x00" in value:
            raise ConfigurationError(
                f"Invalid configuration core.{field_name}: "
                "must not contain NUL bytes."
            )

    # Paths
    for field_name in ("data", "config", "cache", "logs", "memory", "runtime"):
        value = getattr(settings.paths, field_name)
        if value is None or str(value) == "":
            raise ConfigurationError(
                f"Invalid configuration paths.{field_name}: must be a valid path."
            )

    return settings
