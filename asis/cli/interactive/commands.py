"""Slash-command parsing for the interactive terminal.

Commands are handled by the CLI and never forwarded to the LLM.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    name: str
    arg: str = ""
    is_command: bool = True


COMMANDS = (
    "/help",
    "/mode",
    "/upload",
    "/attach",
    "/docs",
    "/clear-docs",
    "/clear",
    "/exit",
    "/quit",
    "/identities",
    "/identity",
)


def _split_arg(text: str) -> tuple[str, str]:
    """Split ``/cmd arg`` honoring Windows + quoted paths."""
    try:
        parts = shlex.split(text, posix=False)
    except ValueError:
        parts = text.split(None, 1)
    if not parts:
        return "", ""
    name = parts[0].lower()
    arg = ""
    if len(parts) > 1:
        arg = parts[1] if len(parts) == 2 else " ".join(parts[1:])
    arg = arg.strip().strip("\"'")
    # shlex with posix=False keeps quotes; strip once more.
    arg = arg.strip().strip("\"'")
    return name, arg


def parse_command(text: str) -> CommandResult | None:
    """Return a CommandResult for slash commands, else None."""
    stripped = (text or "").strip()
    if not stripped.startswith("/"):
        return None
    name, arg = _split_arg(stripped)
    if name in ("/upload", "/attach") and not arg:
        return CommandResult(name=name, arg="")
    if name not in COMMANDS and not name.startswith("/mode"):
        # Unknown slash input: treat as command so it is not sent to the LLM.
        return CommandResult(name=name, arg=arg)
    return CommandResult(name=name, arg=arg)


HELP_TEXT = (
    "Commands:\n"
    "  /help              show this help\n"
    "  /mode [text|voice] switch or toggle input mode\n"
    "  /upload <path>     attach a document (.txt .md .pdf .docx .csv .json)\n"
    "  /attach <path>     same as /upload\n"
    "  /docs              list attached documents\n"
    "  /clear-docs        remove attached documents\n"
    "  /clear             clear the screen (keeps conversation)\n"
    "  /identities        list reconstructed identities\n"
    "  /identity <sub>    analyze|show|questions|simulate|forget|export <name>\n"
    "  /exit, /quit       leave A.S.I.S. (also CTRL+C)\n"
    "Keys: ENTER submit, ESC interrupt response, CTRL+C exit."
)
