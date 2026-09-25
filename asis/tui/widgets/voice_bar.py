"""Voice Bar - Right column bottom.

Left: VOICE ● READY chip
Middle: LISTENING PROCESSING SPEAKING segments (only active lit)
Right: mic/speaker glyphs
"""

from __future__ import annotations

from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static, Button

from asis.tui.state import AppState, VoiceState


class VoiceBar(Widget):
    """Right column voice bar."""

    DEFAULT_CSS = """
    VoiceBar {
        width: 100%;
        height: 100%;
        border: solid $panel-border;
        background: $background;
        padding: 0 1;
    }

    VoiceBar > Horizontal {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    VoiceBar .voice-chip {
        background: $surface;
        border: solid $panel-border;
        padding: 0 1;
        margin-right: 2;
    }

    VoiceBar .voice-chip-ready {
        color: $success;
    }

    VoiceBar .voice-chip-error {
        color: $error;
    }

    VoiceBar .voice-chip-off {
        color: $text-dim;
    }

    VoiceBar .segment {
        padding: 0 1;
        margin: 0 1;
        border: solid $panel-border;
        color: $text-dim;
        text-style: dim;
        min-width: 12;
        content-align: center middle;
    }

    VoiceBar .segment-active {
        background: $accent;
        color: $background;
        text-style: bold;
        border: solid $accent;
    }

    VoiceBar .glyph {
        color: $text;
        margin-left: 2;
    }

    VoiceBar .glyph-active {
        color: $success;
    }
    """

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state

    def compose(self) -> Widget:
        with Horizontal():
            yield Button("", classes="voice-chip", id="voice-chip", disabled=True)
            with Horizontal(id="segments"):
                yield Static("LISTENING", classes="segment", id="seg-listening")
                yield Static("PROCESSING", classes="segment", id="seg-processing")
                yield Static("SPEAKING", classes="segment", id="seg-speaking")
            yield Static("🎤 🔊", classes="glyph", id="glyphs")

    def on_mount(self) -> None:
        self._update()

    def watch_state(self) -> None:
        self._update()

    def _update(self) -> None:
        chip = self.query_one("#voice-chip", Button)
        seg_listening = self.query_one("#seg-listening", Static)
        seg_processing = self.query_one("#seg-processing", Static)
        seg_speaking = self.query_one("#seg-speaking", Static)
        glyphs = self.query_one("#glyphs", Static)

        # Voice chip
        vs = self.state.voice_state
        if vs == VoiceState.READY:
            chip.label = "VOICE ● READY"
            chip.remove_class("voice-chip-error")
            chip.remove_class("voice-chip-off")
            chip.add_class("voice-chip-ready")
        elif vs == VoiceState.ERROR:
            chip.label = "VOICE ● ERROR"
            chip.remove_class("voice-chip-ready")
            chip.remove_class("voice-chip-off")
            chip.add_class("voice-chip-error")
        elif vs == VoiceState.OFF:
            chip.label = "VOICE ○ OFF"
            chip.remove_class("voice-chip-ready")
            chip.remove_class("voice-chip-error")
            chip.add_class("voice-chip-off")
        else:
            chip.label = f"VOICE ● {vs.value}"
            chip.remove_class("voice-chip-off")
            chip.remove_class("voice-chip-error")
            chip.add_class("voice-chip-ready")

        # Segments - only active one lit
        for seg in [seg_listening, seg_processing, seg_speaking]:
            seg.remove_class("segment-active")

        if vs == VoiceState.LISTENING:
            seg_listening.add_class("segment-active")
            glyphs.update("[span.glyph-active]🎤[/span] 🔊")
        elif vs == VoiceState.PROCESSING:
            seg_processing.add_class("segment-active")
            glyphs.update("🎤 🔊")
        elif vs == VoiceState.SPEAKING:
            seg_speaking.add_class("segment-active")
            glyphs.update("🎤 [span.glyph-active]🔊[/span]")
        else:
            glyphs.update("🎤 🔊")