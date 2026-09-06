"""
Cross-platform filesystem paths for Forza.

No paths are hardcoded to a specific user's home directory.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

from . import defaults


def get_home_directory() -> Path:
    """Return the current user's home directory."""
    return Path.home()


def get_data_directory() -> Path:
    """
    Return Forza's persistent application-data directory.

    Windows:
        %LOCALAPPDATA%/Forza

    macOS:
        ~/Library/Application Support/Forza

    Linux:
        $XDG_DATA_HOME/Forza
        or ~/.local/share/Forza
    """
    system = platform.system()

    if system == "Windows":
        base = os.getenv("LOCALAPPDATA")

        if base:
            return Path(base) / defaults.APP_NAME

        return get_home_directory() / "AppData" / "Local" / defaults.APP_NAME

    if system == "Darwin":
        return (
            get_home_directory()
            / "Library"
            / "Application Support"
            / defaults.APP_NAME
        )

    # Linux and other Unix-like systems
    xdg_data_home = os.getenv("XDG_DATA_HOME")

    if xdg_data_home:
        return Path(xdg_data_home) / defaults.APP_NAME

    return (
        get_home_directory()
        / ".local"
        / "share"
        / defaults.APP_NAME
    )


def get_config_directory() -> Path:
    """Return Forza's user configuration directory."""
    system = platform.system()

    if system == "Windows":
        base = os.getenv("APPDATA")

        if base:
            return Path(base) / defaults.APP_NAME

        return get_home_directory() / "AppData" / "Roaming" / defaults.APP_NAME

    if system == "Darwin":
        return (
            get_home_directory()
            / "Library"
            / "Application Support"
            / defaults.APP_NAME
        )

    xdg_config_home = os.getenv("XDG_CONFIG_HOME")

    if xdg_config_home:
        return Path(xdg_config_home) / defaults.APP_NAME

    return (
        get_home_directory()
        / ".config"
        / defaults.APP_NAME
    )


def get_cache_directory() -> Path:
    """Return Forza's cache directory."""
    system = platform.system()

    if system == "Windows":
        base = os.getenv("LOCALAPPDATA")

        if base:
            return Path(base) / defaults.APP_NAME / "cache"

        return (
            get_home_directory()
            / "AppData"
            / "Local"
            / defaults.APP_NAME
            / "cache"
        )

    if system == "Darwin":
        return (
            get_home_directory()
            / "Library"
            / "Caches"
            / defaults.APP_NAME
        )

    xdg_cache_home = os.getenv("XDG_CACHE_HOME")

    if xdg_cache_home:
        return Path(xdg_cache_home) / defaults.APP_NAME

    return (
        get_home_directory()
        / ".cache"
        / defaults.APP_NAME
    )


def get_log_directory() -> Path:
    """Return Forza's log directory."""
    return get_data_directory() / defaults.LOG_DIRECTORY_NAME


def get_memory_directory() -> Path:
    """Return Forza's persistent memory directory."""
    return get_data_directory() / defaults.MEMORY_DIRECTORY_NAME


def get_runtime_directory() -> Path:
    """
    Return a temporary/runtime directory for the current user.

    This location is not intended for permanent application data.
    """
    import tempfile

    return Path(tempfile.gettempdir()) / defaults.APP_NAME


def ensure_directories() -> dict[str, Path]:
    """
    Create required Forza directories if they don't exist.

    Returns:
        A dictionary containing the created/verified paths.
    """
    directories = {
        "data": get_data_directory(),
        "config": get_config_directory(),
        "cache": get_cache_directory(),
        "logs": get_log_directory(),
        "memory": get_memory_directory(),
        "runtime": get_runtime_directory(),
    }

    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)

    return directories