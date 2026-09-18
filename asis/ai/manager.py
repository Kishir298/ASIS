"""
High-level AI manager for A.S.I.S.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from asis.configuration.settings import settings
from asis.errors import InferenceError
from asis.events.bus import EventBus
from asis.events.events import Event, EventType
from asis.logging.logger import get_logger

from .models import AIMessage, AIResponse
from .providers import AIProvider, MockAIProvider


def create_provider(provider_name: str | None = None) -> AIProvider:
    """Build the configured AI provider."""
    name = (provider_name or settings.ai.provider).lower()

    if name == "mock":
        return MockAIProvider(
            model=settings.ai.model,
        )

    if name == "ollama":
        from .providers import OllamaProvider

        return OllamaProvider(
            model=settings.ai.model,
            host=settings.ai.endpoint,
            timeout=settings.ai.request_timeout,
            temperature=settings.ai.temperature,
            retries=settings.network.retries,
        )

    raise InferenceError(f"Unknown AI provider: {name}")


class AIManager:
    """High-level interface to the configured AI provider."""

    def __init__(
        self,
        provider: AIProvider | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.provider = provider or create_provider()
        self.event_bus = event_bus
        self.logger = get_logger("ai")

    def available(self) -> bool:
        """Return whether the AI backend is available."""
        return self.provider.available()

    def _publish(
        self,
        event_type: EventType,
        **data,
    ) -> None:
        if self.event_bus is None:
            return

        self.event_bus.publish(
            Event(
                type=event_type,
                data={
                    "provider": self.provider.name,
                    "model": self.provider.model,
                    **data,
                },
                source="ai",
            )
        )

    def chat(
        self,
        messages: Sequence[AIMessage],
    ) -> AIResponse:
        """Generate an AI response."""
        if not messages:
            raise ValueError("At least one message is required.")

        self.logger.info(
            "Sending request to %s/%s",
            self.provider.name,
            self.provider.model,
        )
        self._publish(EventType.AI_INFERENCE_STARTED)

        try:
            response = self.provider.chat(messages)

        except Exception as exc:
            self._publish(EventType.AI_INFERENCE_FAILED, error=str(exc))
            raise

        self._publish(EventType.AI_INFERENCE_FINISHED)
        return response

    def chat_with_tools(
        self,
        messages: Sequence[AIMessage],
        tools: Sequence[Any],
    ) -> AIResponse:
        """Generate a response with native tool definitions available."""
        if not messages:
            raise ValueError("At least one message is required.")

        self.logger.info(
            "Sending tool-enabled request to %s/%s (%d tools)",
            self.provider.name,
            self.provider.model,
            len(list(tools)),
        )
        self._publish(EventType.AI_INFERENCE_STARTED)

        try:
            response = self.provider.chat_with_tools(messages, tools)

        except Exception as exc:
            self._publish(EventType.AI_INFERENCE_FAILED, error=str(exc))
            raise

        self._publish(EventType.AI_INFERENCE_FINISHED)
        return response

    def stream_chat(
        self,
        messages: Sequence[AIMessage],
    ) -> Iterable[str]:
        """Stream an AI response as text chunks."""
        if not messages:
            raise ValueError("At least one message is required.")

        self.logger.info(
            "Streaming request to %s/%s",
            self.provider.name,
            self.provider.model,
        )
        self._publish(EventType.AI_INFERENCE_STARTED)

        try:
            yield from self.provider.stream_chat(messages)

        except Exception as exc:
            self._publish(EventType.AI_INFERENCE_FAILED, error=str(exc))
            raise

        else:
            self._publish(EventType.AI_INFERENCE_FINISHED)
