"""
High-level AI manager for Forza.
"""

from __future__ import annotations

from collections.abc import Sequence

from core.logging.logger import get_logger

from .models import AIMessage, AIResponse
from .provider import AIProvider


class AIManager:
    """High-level interface to the configured AI provider."""

    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider
        self.logger = get_logger("ai")

    def available(self) -> bool:
        """Return whether the AI backend is available."""
        return self.provider.available()

    def chat(
        self,
        messages: Sequence[AIMessage],
    ) -> AIResponse:
        """Generate an AI response."""

        if not messages:
            raise ValueError(
                "At least one message is required."
            )

        self.logger.info(
            "Sending request to %s/%s",
            self.provider.name,
            self.provider.model,
        )

        return self.provider.chat(messages)