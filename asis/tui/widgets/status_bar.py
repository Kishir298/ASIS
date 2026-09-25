"""Bottom Status Bar - Full width, 1 line.

Left: mode, model, three colored dots
Right: shortcuts
"""

from __future__ import annotations

from textual.widget import Widget
from textual.widgets import Static

from asis.tui.state import AppState


class StatusBar(Widget):
    """Full-width bottom status bar."""

    DEFAULT_CSS = """
    StatusBar {
        width: 100%;
        height: 1;
        background: $surface;
        border: solid $panel-border;
        border-top: solid $panel-border;
        padding: 0 1;
    }

    StatusBar > Static {
        width: 100%;
        height: 1;
    }

    StatusBar .left-section {
        color: $text;
    }

    StatusBar .right-section {
        color: $text-dim;
        text-style: dim;
        content-align: right middle;
    }

    StatusBar .mode-label {
        color: $accent;
        text-style: bold;
    }

    StatusBar .model-name {
        color: $text;
    }

    StatusBar .dot-online {
        color: $success;
    }

    StatusBar .dot-offline {
        color: $error;
    }

    StatusBar .shortcut-key {
        color: $text;
        text-style: bold;
    }
    """

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state

    def compose(self) -> Widget:
        yield Static("", id="status-content")

    def on_mount(self) -> None:
        self._update()

    def watch_state(self) -> None:
        self._update()

    def _update(self) -> None:
        status = self.query_one("#status-content", Static)

        # Left section
        mode_text = self.state.interaction_mode.value
        ollama_dot = "●" if self.state.ollama_online else "○"
        ollama_class = "dot-online" if self.state.ollama_online else "dot-offline"
        mem_dot = "●" if self.state.memory_ready else "○"
        mem_class = "dot-online" if self.state.memory_ready else "dot-offline"
        tools_dot = "●" if self.state.tools_ready else "○"
        tools_class = "dot-online" if self.state.tools_ready else "dot-offline"

        left = (
            f"[span.mode-label]{mode_text} MODE[/span]  "
            f"[span.model-name]{self.state.model_name}[/span]  "
            f"OLLAMA [span.{ollama_class}]{ollama_dot}[/span]  "
            f"MEMORY [span.{mem_class}]{mem_dot}[/span]  "
            f"TOOLS [span.{tools_class}]{tools_dot}[/span]"
        )

        # Right section
        right = (
            f"[span.shortcut-key]Ctrl+C[/span] Exit  "
            f"[span.shortcut-key]Esc[/span] Cancel"
        )

        # Combine with spacing
        status.update(f"{left}  {right}")