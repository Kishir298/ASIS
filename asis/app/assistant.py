"""
Stateful A.S.I.S. application runtime.

Owns one conversation session for its lifetime and wires together the
already-built subsystems:

    user input -> ConversationSession -> memory retrieval ->
    ContextAssembler -> InferenceEngine -> AIManager -> action decision ->
    ToolRouter/Permission/Executor -> final response -> ConversationSession

Shared by the text CLI and the voice loop so both use the same
intelligence path. Memory failures are fail-open (log + continue);
inference failures preserve conversation state and propagate typed errors.
"""

from __future__ import annotations

from asis.ai.context import ContextAssembler
from asis.ai.conversation import ConversationSession
from asis.ai.inference import InferenceEngine
from asis.ai.manager import AIManager
from asis.configuration.settings import settings
from asis.events.bus import EventBus
from asis.identity.identity import Identity
from asis.logging.logger import get_logger
from asis.system.interrupt import InterruptCoordinator
from asis.tools.executor import ToolExecutor
from asis.tools.provided import CurrentTimeTool, EchoTool
from asis.tools.registry import ToolRegistry
from asis.tools.result import ToolResult
from asis.tools.router import ToolRouter, build_executor

from .actions import ToolRequest, format_tool_result_for_context, parse_tool_request
from .memories import store_auto_memories


def build_default_tool_router(
    executor: ToolExecutor | None = None,
) -> ToolRouter:
    """Build the default safe router with the audited built-in tools."""
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(CurrentTimeTool())
    return ToolRouter(registry=registry, executor=build_executor(executor))


class AssistantApp:
    """Stateful chat application owning conversation, memory and tools."""

    def __init__(
        self,
        identity: Identity,
        ai: AIManager,
        memory,
        tools_router: ToolRouter | None = None,
        interrupts: InterruptCoordinator | None = None,
        event_bus: EventBus | None = None,
        max_memory_items: int = 5,
    ) -> None:
        self.identity = identity
        self.ai = ai
        self.memory = memory
        self.event_bus = event_bus
        self.interrupts = interrupts
        self.logger = get_logger("app.assistant")
        self.session = ConversationSession()
        self._pending_memory_query = ""
        self._max_memory_items = max(1, max_memory_items)
        self.assembler = ContextAssembler(
            identity=identity,
            memory_context_provider=self._memory_context,
            max_context_messages=settings.ai.max_context_messages,
            context_char_limit=settings.ai.context_char_limit,
        )
        self.engine = InferenceEngine(
            manager=ai, assembler=self.assembler, interrupts=interrupts
        )
        self.tools_router = tools_router or build_default_tool_router()

    def _memory_context(self) -> str:
        query = self._pending_memory_query
        if not query or not query.strip():
            return ""
        try:
            search = getattr(self.memory, "search_context", None)
            if callable(search):
                return search(query, limit=self._max_memory_items) or ""
            return ""
        except Exception as exc:
            self.logger.warning("Memory retrieval failed, continuing: %s", exc)
            return ""

    def _execute_tool(self, request: ToolRequest) -> ToolResult:
        try:
            return self.tools_router.execute(request.tool_name, **request.arguments)
        except Exception as exc:
            self.logger.exception("Tool dispatch failed: %s", request.tool_name)
            return ToolResult.failure(error=str(exc), tool_name=request.tool_name)

    def chat(self, message: str) -> str:
        """Process one user message through the full wired pipeline."""
        text = (message or "").strip()
        if not text:
            return ""
        store_auto_memories(text, self.memory)
        self.session.add_user(text)
        self._pending_memory_query = text
        try:
            response = self.engine.generate(self.session.messages)
        finally:
            self._pending_memory_query = ""

        request = parse_tool_request(response.content, user_text=text)
        if request is None:
            self.session.add_assistant(response.content)
            return response.content

        result = self._execute_tool(request)
        # Record the intermediate model action + explicit tool result so the
        # history stays auditable; tool output is never user-authored.
        self.session.add_assistant(response.content)
        self.session.add_assistant(format_tool_result_for_context(result))

        self._pending_memory_query = ""
        try:
            final = self.engine.generate(self.session.messages)
        finally:
            self._pending_memory_query = ""
        self.session.add_assistant(final.content)
        return final.content

    def history_roles(self) -> list[str]:
        """Return session roles (test helper)."""
        return [m.role.value for m in self.session.messages]

    @property
    def conversation(self) -> ConversationSession:
        """Expose the owned conversation session."""
        return self.session
