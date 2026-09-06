"""
Data models for the Forza AI subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AIMessage:
    """A message sent to or returned by an AI model."""

    role: str
    content: str


@dataclass(frozen=True)
class AIResponse:
    """Standard response returned by an AI provider."""

    content: str
    model: str
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict)