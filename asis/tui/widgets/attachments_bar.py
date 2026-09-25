"""Attachments Bar - Right column strip.

One line: Attachments: followed by chips with icons and × close buttons.
"""

from __future__ import annotations

from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static, Button

from asis.tui.state import AppState


class AttachmentsBar(Widget):
    """Right column attachments strip."""

    DEFAULT_CSS = """
    AttachmentsBar {
        width: 100%;
        height: 100%;
        border: solid $panel-border;
        background: $background;
        padding: 0 1;
    }

    AttachmentsBar > Horizontal {
        width: 100%;
        height: 100%;
    }

    AttachmentsBar .label {
        color: $text-dim;
        text-style: dim;
        width: auto;
    }

    AttachmentsBar .chip {
        background: $surface;
        border: solid $panel-border;
        padding: 0 1;
        margin-right: 1;
        min-width: 0;
    }

    AttachmentsBar .chip-label {
        color: $text;
    }

    AttachmentsBar .chip-close {
        color: $text-dim;
        margin-left: 1;
    }

    AttachmentsBar .chip-close:hover {
        color: $error;
    }

    AttachmentsBar .no-attachments {
        color: $text-dim;
        text-style: dim;
    }
    """

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state

    def compose(self) -> Widget:
        with Horizontal(id="chips-container"):
            yield Static("Attachments:", classes="label")
            yield Static("(none)", classes="no-attachments", id="none-msg")

    def on_mount(self) -> None:
        self._update()

    def watch_state(self) -> None:
        self._update()

    def _update(self) -> None:
        container = self.query_one("#chips-container", Horizontal)
        none_msg = self.query_one("#none-msg", Static)

        # Remove existing chip buttons
        for child in list(container.children):
            if hasattr(child, "classes") and "chip" in child.classes:
                child.remove()

        if not self.state.attachments:
            none_msg.display = True
            return

        none_msg.display = False

        for att in self.state.attachments:
            chip = Button(f"{att.icon} {att.name} ×", classes="chip", id=f"attach-{att.name}")
            chip.tooltip = f"Click to remove {att.name}"
            container.mount(chip)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("attach-"):
            name = event.button.id[7:]  # Remove "attach-"
            self.state.remove_attachment(name)
            self._update()