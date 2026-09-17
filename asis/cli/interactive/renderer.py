"""Terminal typing renderer (presentation layer only).

The LLM response is fully generated before rendering begins; this class
only animates already-final text.  The provider/engine never knows about
the terminal.
"""

from __future__ import annotations

import sys
import threading
import time


class TypingRenderer:
    """Renders ``A.S.I.S. > <text>`` progressively on one terminal line."""

    def __init__(
        self,
        prefix: str = "A.S.I.S. > ",
        char_delay: float = 0.012,
        stream=None,
    ) -> None:
        self.prefix = prefix
        self.char_delay = max(0.0, float(char_delay))
        self.stream = stream if stream is not None else sys.stdout

    def _tty(self) -> bool:
        try:
            return bool(self.stream.isatty())
        except Exception:
            return False

    def render(
        self,
        text: str,
        stop_event: threading.Event | None = None,
    ) -> str:
        """Render text with a typing animation; return what was shown.

        A set ``stop_event`` (ESC) stops mid-render and restores the line.
        Never raises on render errors; always ends with a newline.
        """
        final = text if isinstance(text, str) else str(text)
        try:
            self.stream.write(self.prefix)
            self.stream.flush()
        except Exception:
            return ""
        if not final:
            try:
                self.stream.write("\n")
                self.stream.flush()
            except Exception:
                pass
            return ""
        # Non-TTY (pipes/tests) or zero delay: single write, no animation.
        if not self._tty() or self.char_delay <= 0:
            try:
                self.stream.write(final + "\n")
                self.stream.flush()
            except Exception:
                pass
            return final
        shown: list[str] = []
        try:
            for ch in final:
                if stop_event is not None and stop_event.is_set():
                    self.stream.write("  [interrupted]\n")
                    self.stream.flush()
                    return "".join(shown)
                self.stream.write(ch)
                self.stream.flush()
                shown.append(ch)
                if ch != "\n":
                    time.sleep(self.char_delay)
            self.stream.write("\n")
            self.stream.flush()
        except Exception:
            try:
                self.stream.write("\n")
                self.stream.flush()
            except Exception:
                pass
        return "".join(shown) if shown else final
