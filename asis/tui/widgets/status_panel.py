"""Status Panel - Left column box 2.

Shows MODEL, OLLAMA, MEMORY, TOOLS, VOICE with colored status dots.
"""

from __future__ import annotations

from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static

from asis.tui.state import AppState


class StatusPanel(Widget):
    """Left column second box: subsystem status."""

    DEFAULT_CSS = """
    StatusPanel {
        width: 100%;
        height: 100%;
        border: solid $panel-border;
        background: $background;
        padding: 0 1;
    }

    StatusPanel > Static {
        width: 100%;
        height: 1;
    }

    StatusPanel .label {
        color: $text-dim;
    }

    StatusPanel .value {
        color: $text;
    }

    StatusPanel .dot-online {
        color: $success;
    }

    StatusPanel .dot-offline {
        color: $error;
    }

    StatusPanel .model-name {
        color: $text;
        text-style: bold;
    }
    """

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state

    def compose(self) -> Widget:
        with Vertical():
            yield Static("", id="model")
            yield Static("", id="ollama")
            yield Static("", id="memory")
            yield Static("", id="tools")
            yield Static("", id="voice")

    def on_mount(self) -> None:
        self._update()

    def watch_state(self) -> None:
        self._update()

    def _update(self) -> None:
        model = self.query_one("#model", Static)
        ollama = self.query_one("#ollama", Static)
        memory = self.query_one("#memory", Static)
        tools = self.query_one("#tools", Static)
        voice = self.query_one("#voice", Static)

        # MODEL
        model.update(f"[span.label]MODEL:[/span] [span.model-name]{self.state.model_name}[/span]")

        # OLLAMA
        ollama_dot = "●" if self.state.ollama_online else "○"
        ollama_class = "dot-online" if self.state.ollama_online else "dot-offline"
        ollama_text = "ONLINE" if self.state.ollama_online else "OFFLINE"
        ollama.update(f"[span.label]OLLAMA:[/span] [span.{ollama_class}]{ollama_dot}[/span] [span.value]{ollama_text}[/span]")

        # MEMORY
        mem_dot = "●" if self.state.memory_ready else "○"
        mem_class = "dot-online" if self.state.memory_ready else "dot-offline"
        mem_text = "READY" if self.state.memory_ready else "OFFLINE"
        memory.update(f"[span.label]MEMORY:[/span] [span.{mem_class}]{mem_dot}[/span] [span.value]{mem_text}[/span]")

        # TOOLS
        tools_dot = "●" if self.state.tools_ready else "○"
        tools_class = "dot-online" if self.state.tools_ready else "dot-offline"
        tools_text = "READY" if self.state.tools_ready else "OFFLINE"
        tools.update(f"[span.label]TOOLS:[/span] [span.{tools_class}]{tools_dot}[/span] [span.value]{tools_text}[/span]")

        # VOICE
        voice_dot = "●" if self.state.voice_state.value in ("READY", "LISTENING", "PROCESSING", "SPEAKING") else "○"
        voice_class = "dot-online" if voice_dot == "●" else "dot-offline"
        voice_text = self.state.voice_state.value
        voice.update(f"[span.label]VOICE:[/span] [span.{voice_class}]{voice_dot}[/span] [span.value]{voice_text}[/span]")