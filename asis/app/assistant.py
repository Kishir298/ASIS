"""
A.S.I.S. application orchestrator.

Single shared application path for text, voice, and (future) coding
consumers: conversation → local inference → explicit CORE tool intents →
response. Intelligence stays local (Ollama); CORE tools ride the existing
ToolRouter/permission system and fail cleanly when offline.

Explicit tool intents use a deterministic ``core:`` command prefix (same
idea as the legacy ``handle_command`` verbs) — no model parsing, no
second inference step:

```text
core:devices                  -> core_discover_devices
core:device <id>              -> core_device_info
core:status                   -> core_status
core:service <svc> <op>       -> core_service_request
core:agent <op>               -> core_agent_request
core:data <request-type>      -> core_data_request
core:send <device> <type> ... -> core_send_to_device
```
"""

from __future__ import annotations

from dataclasses import dataclass

from asis.ai.conversation import ConversationSession
from asis.ai.inference import InferenceEngine
from asis.logging.logger import get_logger

from .memories import store_auto_memories
from .result import ProcessResult


@dataclass(frozen=True)
class CoreIntent:
    """A parsed explicit CORE tool request."""

    tool_name: str
    kwargs: dict


def parse_core_intent(text: str) -> CoreIntent | None:
    """Parse a ``core:`` command prefix into a tool call, if present."""
    stripped = (text or "").strip()
    if not stripped.lower().startswith("core:"):
        return None
    parts = stripped[5:].strip().split()
    if not parts:
        return None
    verb = parts[0].lower()
    args = parts[1:]
    if verb in ("devices", "discover"):
        return CoreIntent("core_discover_devices", {})
    if verb == "device" and args:
        return CoreIntent("core_device_info", {"device_id": args[0]})
    if verb == "status":
        return CoreIntent("core_status", {})
    if verb == "service" and len(args) >= 2:
        return CoreIntent(
            "core_service_request",
            {"service": args[0], "operation": args[1], "params": {}},
        )
    if verb == "agent" and args:
        return CoreIntent("core_agent_request", {"operation": args[0], "params": {}})
    if verb == "data" and args:
        return CoreIntent(
            "core_data_request", {"request_type": args[0], "params": {}}
        )
    if verb == "send" and len(args) >= 2:
        return CoreIntent(
            "core_send_to_device",
            {
                "device_id": args[0],
                "message_type": args[1],
                "payload": {"text": " ".join(args[2:])} if len(args) > 2 else {},
            },
        )
    return None


class AssistantApp:
    """Owns one conversation: memory, local inference, CORE tool intents."""

    def __init__(
        self,
        *,
        session: ConversationSession,
        engine: InferenceEngine,
        router=None,
        memory=None,
        core=None,
        shutdown_phrase: str = "asis shutdown",
    ) -> None:
        self._logger = get_logger("app.assistant")
        self.session = session
        self.engine = engine
        self.router = router
        self.memory = memory
        self.core = core
        self.shutdown_phrase = (shutdown_phrase or "").strip().lower()

    @property
    def core_available(self) -> bool:
        """Return whether the optional CORE session is currently usable."""
        if self.core is None:
            return False
        try:
            return bool(self.core.is_available())
        except Exception:
            return False

    def handle_text(self, message: str) -> ProcessResult:
        """Process one user message into a ProcessResult (never raises)."""
        text = (message or "").strip()
        if not text:
            return ProcessResult(assistant_text="")
        if self.shutdown_phrase and text.lower() == self.shutdown_phrase:
            return ProcessResult(stopped=True, assistant_text="Shutting down.")

        if self.memory is not None:
            try:
                store_auto_memories(text, self.memory)
            except Exception:
                self._logger.exception("Memory store failed; continuing.")

        self.session.add_user(text)

        try:
            reply = self.engine.generate(self.session.messages).content
        except Exception as exc:
            self._logger.exception("Local inference failed.")
            return ProcessResult(
                assistant_text="",
                system_messages=[f"Local inference failed: {exc}"],
            )
        self.session.add_assistant(reply)

        system_messages: list[str] = []
        intent = parse_core_intent(text)
        if intent is not None:
            system_messages.append(self._run_core_tool(intent))

        return ProcessResult(assistant_text=reply, system_messages=system_messages)

    # -- internals --
    def _run_core_tool(self, intent: CoreIntent) -> str:
        if self.router is None:
            return "CORE tool unavailable: no tool router configured."
        if not self.core_available:
            return "CORE_UNAVAILABLE: C.O.R.E. is not connected."
        try:
            result = self.router.execute(intent.tool_name, **intent.kwargs)
        except Exception as exc:
            return f"CORE tool failed: {exc}"
        if result.success:
            return f"{intent.tool_name}: ok."
        return f"{intent.tool_name} failed: {result.error or 'unknown error'}"

    def core_status_text(self) -> str:
        """Short human-readable CORE status line (no secrets)."""
        if self.core is None:
            return "CORE: disabled."
        try:
            status = self.core.status()
        except Exception as exc:
            return f"CORE: unknown ({exc})"
        state = getattr(status.state, "value", str(status.state))
        return f"CORE: {state.lower()} (connected={status.connected})."
