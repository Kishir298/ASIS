"""
Event handler definitions.
"""

from __future__ import annotations

from collections.abc import Callable

from .events import Event

EventHandler = Callable[[Event], None]