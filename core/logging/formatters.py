"""
Logging formatters for Forza.
"""

from __future__ import annotations

import logging


class ForzaFormatter(logging.Formatter):
    """Consistent human-readable formatter for Forza logs."""

    def __init__(self) -> None:
        super().__init__(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )