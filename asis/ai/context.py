"""
Prompt context assembly for A.S.I.S.

Assembles the system prompt from the active identity, long-term memory
context and correctness rules, then builds the final message list sent
to the AI model with history trimmed to the configured limit.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from asis.configuration.settings import settings
from asis.identity.identity import Identity

from .models import AIMessage, MessageRole

MemoryContextProvider = Callable[[], str]

_MEMORY_RULES = (
    "MEMORY RULES:\n"
    "- Use these memories when relevant.\n"
    "- Never invent memories.\n"
    "- Never claim to remember something that is not shown.\n"
    "- Do not mention the memory system unless asked."
)


class ContextAssembler:
    """Builds the context sent alongside user history."""

    def __init__(
        self,
        identity: Identity,
        memory_context_provider: MemoryContextProvider | None = None,
        max_context_messages: int | None = None,
        context_char_limit: int | None = None,
    ) -> None:
        self.identity = identity
        self.memory_context_provider = memory_context_provider
        self.max_context_messages = (
            max_context_messages or settings.ai.max_context_messages
        )
        self.context_char_limit = context_char_limit or settings.ai.context_char_limit

    def system_prompt(self) -> str:
        """Build the full system prompt for this identity."""
        sections = [self.identity.system_prompt()]

        if self.memory_context_provider is not None:
            memory_context = self.memory_context_provider()

            if memory_context.strip():
                text = memory_context.strip()
                if len(text) > self.context_char_limit:
                    text = text[: self.context_char_limit]
                sections.append(text)

        sections.append(_MEMORY_RULES)

        return "\n\n".join(sections)

    def build_messages(
        self,
        history: Sequence[AIMessage],
    ) -> list[AIMessage]:
        """Build the final message list for the AI model."""
        limit = max(1, self.max_context_messages)
        recent = list(history)[-limit:]

        return [
            AIMessage(
                role=MessageRole.SYSTEM,
                content=self.system_prompt(),
            ),
            *recent,
        ]
