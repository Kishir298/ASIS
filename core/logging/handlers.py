"""
Logging handlers for Forza.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .formatters import ForzaFormatter


def create_console_handler(level: int) -> logging.Handler:
    """Create a console logging handler."""
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(ForzaFormatter())

    return handler


def create_file_handler(
    log_directory: Path,
    level: int,
    filename: str = "forza.log",
) -> logging.Handler:
    """
    Create a rotating file handler.

    Log files are limited in size so Forza cannot eventually
    consume the entire disk because apparently logs reproduce.
    """
    log_directory.mkdir(parents=True, exist_ok=True)

    log_file = log_directory / filename

    handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )

    handler.setLevel(level)
    handler.setFormatter(ForzaFormatter())

    return handler