"""ANSI panel layout: header / conversation / composer / status bar.

Pure display helpers (return strings, no I/O, no model calls) so
visual tests stay deterministic on a low-capability machine.
"""

from __future__ import annotations

import shutil

MIN_WIDTH = 40
DEFAULT_WIDTH = 80


def terminal_width(default: int = DEFAULT_WIDTH) -> int:
    try:
        return max(MIN_WIDTH, shutil.get_terminal_size().columns)
    except Exception:
        return default


def _rule(width: int) -> str:
    width = max(MIN_WIDTH, int(width))
    return "─" * (width - 2)


def header(title: str = "A.S.I.S.", online: bool = True, width: int = DEFAULT_WIDTH) -> str:
    state = "● ONLINE" if online else "○ OFFLINE"
    bar = _rule(width)
    return f"┌{bar}┐\n│ {title:<{width - 14}} {state} │\n├{bar}┤"


def footer(width: int = DEFAULT_WIDTH) -> str:
    bar = _rule(width)
    return f"├{bar}┤\n│ ENTER Send   ESC Stop   TAB Mode   CTRL+C Exit{' ' * max(0, width - 52)}│\n└{bar}┘"


def user_bubble(text: str, width: int = DEFAULT_WIDTH) -> str:
    return f"You\n┌{_rule(width)}┐\n│ {(text or '').strip()} │\n└{_rule(width)}┘"


def assistant_bubble(text: str, streaming: bool = False, width: int = DEFAULT_WIDTH) -> str:
    cursor = " ▌" if streaming else ""
    return f"A.S.I.S.\n┌{_rule(width)}┐\n│ {(text or '').strip()}{cursor} │\n└{_rule(width)}┘"


def tool_badge(name: str, done: bool = False) -> str:
    state = "[DONE]" if done else "[TOOL]"
    return f"{state} {name}"


def attachments_bar(names: list[str]) -> str:
    if not names:
        return "Attachments: (none)"
    return "Attachments: " + "  ".join(f"📄 {n}" for n in names)


def composer(mode: str = "TEXT", attachments: list[str] | None = None, generating: bool = False) -> str:
    atts = attachments_bar(attachments or [])
    status = "▌ Generating..." if generating else "> Type a message..."
    return f"[{mode}]  [+ ] Attach\n{atts}\n{status}"
