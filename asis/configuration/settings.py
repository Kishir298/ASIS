"""
Centralized A.S.I.S. configuration.

Combines built-in defaults, environment overrides and cross-platform
paths. Other A.S.I.S. modules should resolve configuration through
`settings` rather than reading the environment directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import environment
from .paths import (
    get_cache_directory,
    get_config_directory,
    get_data_directory,
    get_log_directory,
    get_memory_directory,
    get_runtime_directory,
)


@dataclass(frozen=True)
class AISettings:
    provider: str
    model: str
    endpoint: str
    request_timeout: int
    temperature: float
    max_context_messages: int
    context_char_limit: int


@dataclass(frozen=True)
class ConversationSettings:
    max_history: int


@dataclass(frozen=True)
class NetworkSettings:
    timeout: int
    retries: int


@dataclass(frozen=True)
class ToolSettings:
    timeout: int


@dataclass(frozen=True)
class SecuritySettings:
    require_confirmation_for_dangerous: bool


@dataclass(frozen=True)
class MemorySettings:
    provider: str
    database_name: str


@dataclass(frozen=True)
class SpeechToTextSettings:
    engine: str
    model: str
    device: str
    compute_type: str
    language: str


@dataclass(frozen=True)
class TTSSettings:
    engine: str
    voice: str


@dataclass(frozen=True)
class SpeakerSettings:
    engine: str
    confidence: float


@dataclass(frozen=True)
class VoiceSettings:
    sample_rate: int
    channels: int
    block_size: int
    wake_word: str
    stt: SpeechToTextSettings = field(default_factory=SpeechToTextSettings)
    tts: TTSSettings = field(default_factory=TTSSettings)
    speaker: SpeakerSettings = field(default_factory=SpeakerSettings)


@dataclass(frozen=True)
class RuntimeSettings:
    shutdown_timeout: int
    debug: bool
    log_level: str


@dataclass(frozen=True)
class CoreSettings:
    """Optional C.O.R.E. infrastructure connection (standalone by default)."""

    enabled: bool
    host: str
    port: int
    device_file: str
    ca_file: str
    insecure: bool
    connect_timeout: int
    request_timeout: int
    reconnect_enabled: bool
    reconnect_delay: int


@dataclass(frozen=True)
class IdentitySettings:
    name: str
    title: str
    shutdown_phrase: str


@dataclass(frozen=True)
class PathSettings:
    data: Path
    config: Path
    cache: Path
    logs: Path
    memory: Path
    runtime: Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str

    identity: IdentitySettings
    ai: AISettings
    conversation: ConversationSettings
    network: NetworkSettings
    tools: ToolSettings
    security: SecuritySettings
    memory: MemorySettings
    voice: VoiceSettings
    runtime: RuntimeSettings
    core: CoreSettings
    paths: PathSettings


def load_settings() -> Settings:
    """Build and return the current A.S.I.S. configuration."""
    return Settings(
        app_name=environment.IDENTITY_NAME,
        app_version=environment.APP_VERSION,
        identity=IdentitySettings(
            name=environment.IDENTITY_NAME,
            title=environment.IDENTITY_TITLE,
            shutdown_phrase=environment.SHUTDOWN_PHRASE,
        ),
        ai=AISettings(
            provider=environment.AI_PROVIDER,
            model=environment.AI_MODEL,
            endpoint=environment.AI_ENDPOINT,
            request_timeout=environment.AI_REQUEST_TIMEOUT,
            temperature=environment.AI_TEMPERATURE,
            max_context_messages=environment.AI_MAX_CONTEXT_MESSAGES,
            context_char_limit=environment.AI_CONTEXT_CHAR_LIMIT,
        ),
        conversation=ConversationSettings(
            max_history=environment.CONVERSATION_MAX_HISTORY,
        ),
        network=NetworkSettings(
            timeout=environment.NETWORK_TIMEOUT,
            retries=environment.NETWORK_RETRIES,
        ),
        tools=ToolSettings(timeout=environment.TOOL_TIMEOUT),
        security=SecuritySettings(
            require_confirmation_for_dangerous=(
                environment.REQUIRE_CONFIRMATION_FOR_DANGEROUS
            )
        ),
        memory=MemorySettings(
            provider=environment.MEMORY_PROVIDER,
            database_name=environment.MEMORY_DATABASE_NAME,
        ),
        voice=VoiceSettings(
            sample_rate=environment.VOICE_SAMPLE_RATE,
            channels=environment.VOICE_CHANNELS,
            block_size=environment.VOICE_BLOCK_SIZE,
            wake_word=environment.VOICE_WAKE_WORD,
            stt=SpeechToTextSettings(
                engine=environment.VOICE_STT_ENGINE,
                model=environment.VOICE_STT_MODEL,
                device=environment.VOICE_STT_DEVICE,
                compute_type=environment.VOICE_STT_COMPUTE_TYPE,
                language=environment.VOICE_STT_LANGUAGE,
            ),
            tts=TTSSettings(
                engine=environment.VOICE_TTS_ENGINE,
                voice=environment.VOICE_TTS_VOICE,
            ),
            speaker=SpeakerSettings(
                engine=environment.VOICE_SPEAKER_ENGINE,
                confidence=environment.VOICE_SPEAKER_CONFIDENCE,
            ),
        ),
        runtime=RuntimeSettings(
            shutdown_timeout=environment.SHUTDOWN_TIMEOUT,
            debug=environment.DEBUG,
            log_level=environment.LOG_LEVEL,
        ),
        core=CoreSettings(
            enabled=environment.CORE_ENABLED,
            host=environment.CORE_HOST,
            port=environment.CORE_PORT,
            device_file=environment.CORE_DEVICE_FILE,
            ca_file=environment.CORE_CA_FILE,
            insecure=environment.CORE_INSECURE,
            connect_timeout=environment.CORE_CONNECT_TIMEOUT,
            request_timeout=environment.CORE_REQUEST_TIMEOUT,
            reconnect_enabled=environment.CORE_RECONNECT_ENABLED,
            reconnect_delay=environment.CORE_RECONNECT_DELAY,
        ),
        paths=PathSettings(
            data=get_data_directory(),
            config=get_config_directory(),
            cache=get_cache_directory(),
            logs=get_log_directory(),
            memory=get_memory_directory(),
            runtime=get_runtime_directory(),
        ),
    )


# Global read-only configuration instance.
settings = load_settings()
