"""
Standard events used throughout Forza.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    """Known Forza event types."""

    SYSTEM_STARTED = "system.started"
    SYSTEM_READY = "system.ready"
    SYSTEM_STOPPING = "system.stopping"
    SYSTEM_STOPPED = "system.stopped"

    INTERNET_CONNECTED = "internet.connected"
    INTERNET_DISCONNECTED = "internet.disconnected"
    NETWORK_CHANGED = "network.changed"

    VOICE_INPUT = "voice.input"
    VOICE_OUTPUT = "voice.output"

    APP_OPENED = "app.opened"
    APP_CLOSED = "app.closed"

    FILE_CREATED = "file.created"
    FILE_MODIFIED = "file.modified"
    FILE_DELETED = "file.deleted"

    HARDWARE_CHANGED = "hardware.changed"

    VISION_DETECTED = "vision.detected"

    ERROR_OCCURRED = "error.occurred"


@dataclass(frozen=True)
class Event:
    """A message sent through the Forza event bus."""

    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    source: str = "unknown"