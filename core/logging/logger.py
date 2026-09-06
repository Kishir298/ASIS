"""
Centralized logging system for Forza.
"""

from __future__ import annotations

import logging
from pathlib import Path

from core.config.settings import settings

from .handlers import create_console_handler, create_file_handler


_ROOT_LOGGER_NAME = "forza"


def _resolve_log_level(level_name: str) -> int:
    """Convert a textual log level into a logging constant."""
    level = getattr(logging, level_name.upper(), None)

    if isinstance(level, int):
        return level

    return logging.INFO


def configure_logging() -> logging.Logger:
    """
    Configure the global Forza logger.

    Calling this multiple times is safe and will not duplicate handlers.
    """
    logger = logging.getLogger(_ROOT_LOGGER_NAME)

    level = _resolve_log_level(settings.runtime.log_level)

    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        return logger

    logger.addHandler(
        create_console_handler(level)
    )

    logger.addHandler(
        create_file_handler(
            settings.paths.logs,
            level,
        )
    )

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a logger belonging to the Forza logging hierarchy.

    Examples:
        get_logger()
        get_logger("internet")
        get_logger("voice.stt")
    """
    root = configure_logging()

    if not name:
        return root

    return root.getChild(name)