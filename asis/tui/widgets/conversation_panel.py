"""Conversation Panel - Right column main area.

Scrollable message history with streaming support.
Formats: You >, A.S.I.S. >, [TOOL], [RUN ], [....], [DONE], [FAIL]
"""

from __future__ import annotations

from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import RichLog

from asis.tui.state import AppState, ConversationMessage


class ConversationPanel(Widget):
    """Right column main area: conversation history."""

    DEFAULT_CSS = """
    ConversationPanel {
        width: 100%;
        height: 100%;
        border: solid $panel-border;
        background: $background;
    }

    ConversationPanel > VerticalScroll {
        width: 100%;
        height: 1fr;
        padding: 0 1;
    }

    ConversationPanel RichLog {
        width: 100%;
        height: 1fr;
    }

    ConversationPanel .user-msg {
        color: $prompt-cyan;
    }

    ConversationPanel .assistant-msg {
        color: $prompt-amber;
    }

    ConversationPanel .tool-msg {
        color: $tool-tag;
    }

    ConversationPanel .system-msg {
        color: $text-dim;
        text-style: dim;
    }

    ConversationPanel .streaming-caret {
        color: $prompt-amber;
        text-style: blink;
    }

    ConversationPanel .tool-started {
        color: $tool-tag;
    }

    ConversationPanel .tool-running {
        color: $warning;
    }

    ConversationPanel .tool-done {
        color: $success;
    }

    ConversationPanel .tool-fail {
        color: $error;
    }
    """

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self._last_msg_count = 0

    def compose(self) -> Widget:
        with VerticalScroll(id="scroll"):
            yield RichLog(id="log", markup=True, highlight=False, wrap=True)

    def on_mount(self) -> None:
        self._update()

    def watch_state(self) -> None:
        self._update()

    def _update(self) -> None:
        log = self.query_one("#log", RichLog)

        if len(self.state.conversation) == self._last_msg_count:
            # Check if last message is streaming (might need caret update)
            if self.state.conversation and self.state.conversation[-1].streaming:
                self._render_streaming_update(log)
            return

        # Full re-render for new messages
        log.clear()
        for msg in self.state.conversation:
            self._render_message(log, msg)

        self._last_msg_count = len(self.state.conversation)
        log.scroll_end(animate=False)

    def _render_streaming_update(self, log: RichLog) -> None:
        """Update only the last streaming message."""
        # For simplicity, re-render last message
        if not self.state.conversation:
            return
        msg = self.state.conversation[-1]
        # Remove last line and re-add
        # RichLog doesn't support easy line replacement, so we'll just scroll
        pass

    def _render_message(self, log: RichLog, msg: ConversationMessage) -> None:
        """Render a single message."""
        if msg.role == "user":
            content = f"[span.user-msg]You >[/span] {msg.content}"
        elif msg.role == "assistant":
            caret = " [span.streaming-caret]▌[/span]" if msg.streaming else ""
            content = f"[span.assistant-msg]A.S.I.S. >[/span] {msg.content}{caret}"
        elif msg.role == "tool":
            if msg.tool_status == "STARTED":
                prefix = "[span.tool-started][TOOL][/span]"
            elif msg.tool_status == "RUNNING":
                prefix = "[span.tool-running][RUN ][/span]"
            elif msg.tool_status == "DONE":
                prefix = "[span.tool-done][DONE][/span]"
            elif msg.tool_status == "FAIL":
                prefix = "[span.tool-fail][FAIL][/span]"
            else:
                prefix = "[span.tool-msg][TOOL][/span]"
            content = f"{prefix} {msg.content}"
        elif msg.role == "system":
            content = f"[span.system-msg]{msg.content}[/span]"
        else:
            content = msg.content

        log.write(content)

    async def append_user_message(self, content: str) -> None:
        """Append a user message (called from input handler)."""
        log = self.query_one("#log", RichLog)
        log.write(f"[span.user-msg]You >[/span] {content}")
        log.scroll_end(animate=False)

    async def start_assistant_stream(self) -> None:
        """Start streaming assistant response."""
        log = self.query_one("#log", RichLog)
        log.write("[span.assistant-msg]A.S.I.S. >[/span] ")
        log.scroll_end(animate=False)

    async def append_assistant_chunk(self, chunk: str) -> None:
        """Append a streaming chunk to the last assistant message."""
        log = self.query_one("#log", RichLog)
        # RichLog doesn't support in-place update easily
        # We'll write the chunk directly - the caret is handled by CSS
        log.write(chunk)
        log.scroll_end(animate=False)

    async def end_assistant_stream(self, final_content: str = "") -> None:
        """End streaming and optionally replace with final content."""
        log = self.query_one("#log", RichLog)
        # The streaming is done via direct writes, so just ensure scroll
        log.scroll_end(animate=False)

    async def add_tool_message(self, tool_name: str, status: str, detail: str = "") -> None:
        """Add a tool status message."""
        log = self.query_one("#log", RichLog)

        if status == "STARTED":
            prefix = "[span.tool-started][TOOL][/span]"
            content = f"{prefix} {tool_name}"
        elif status == "RUNNING":
            prefix = "[span.tool-running][RUN ][/span]"
            content = f"{prefix} {detail or tool_name}"
        elif status == "DONE":
            prefix = "[span.tool-done][DONE][/span]"
            content = f"{prefix} {detail or tool_name}"
        elif status == "FAIL":
            prefix = "[span.tool-fail][FAIL][/span]"
            content = f"{prefix} {detail or tool_name}"
        else:
            prefix = "[span.tool-msg][TOOL][/span]"
            content = f"{prefix} {tool_name}: {detail}"

        log.write(content)
        log.scroll_end(animate=False)

    async def add_system_message(self, content: str) -> None:
        """Add a system message (memory, etc.)."""
        log = self.query_one("#log", RichLog)
        log.write(f"[span.system-msg]{content}[/span]")
        log.scroll_end(animate=False)