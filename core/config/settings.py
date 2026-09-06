"""
Centralized Forza configuration.

This module combines:
    - built-in defaults
    - environment overrides
    - cross-platform filesystem paths

Other Forza modules should generally import `settings`
instead of reading environment variables directly.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
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
    """AI provider and model configuration."""

    provider: str
    model: str
    endpoint: str
    request_timeout: int
    temperature: float
    max_context_messages: int


@dataclass(frozen=True)
class NetworkSettings:
    """Network-related configuration."""

    timeout: int
    retries: int


@dataclass(frozen=True)
class ToolSettings:
    """Tool execution configuration."""

    timeout: int


@dataclass(frozen=True)
class SecuritySettings:
    """Security and permission configuration."""

    require_confirmation_for_dangerous_tools: bool


@dataclass(frozen=True)
class RuntimeSettings:
    """Runtime behavior configuration."""

    shutdown_timeout: int
    debug: bool
    log_level: str


@dataclass(frozen=True)
class SystemSettings:
    """Information about the current runtime platform."""

    platform: str
    architecture: str
    python_version: str


@dataclass(frozen=True)
class PathSettings:
    """Cross-platform Forza filesystem locations."""

    data: Path
    config: Path
    cache: Path
    logs: Path
    memory: Path
    runtime: Path


@dataclass(frozen=True)
class Settings:
    """Complete Forza configuration."""

    app_name: str
    app_version: str

    ai: AISettings
    network: NetworkSettings
    tools: ToolSettings
    security: SecuritySettings
    runtime: RuntimeSettings
    system: SystemSettings
    paths: PathSettings


def load_settings() -> Settings:
    """Build and return the current Forza configuration."""

    return Settings(
        app_name=environment.APP_NAME,
        app_version=environment.APP_VERSION,

        ai=AISettings(
            provider=environment.AI_PROVIDER,
            model=environment.AI_MODEL,
            endpoint=environment.AI_ENDPOINT,
            request_timeout=environment.AI_REQUEST_TIMEOUT,
            temperature=environment.AI_TEMPERATURE,
            max_context_messages=environment.AI_MAX_CONTEXT_MESSAGES,
        ),

        network=NetworkSettings(
            timeout=environment.NETWORK_TIMEOUT,
            retries=environment.NETWORK_RETRIES,
        ),

        tools=ToolSettings(
            timeout=environment.TOOL_TIMEOUT,
        ),

        security=SecuritySettings(
            require_confirmation_for_dangerous_tools=(
                environment.REQUIRE_CONFIRMATION_FOR_DANGEROUS_TOOLS
            ),
        ),

        runtime=RuntimeSettings(
            shutdown_timeout=environment.SHUTDOWN_TIMEOUT,
            debug=environment.DEBUG,
            log_level=environment.LOG_LEVEL,
        ),

        system=SystemSettings(
            platform=platform.system(),
            architecture=platform.machine(),
            python_version=sys.version.split()[0],
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