"""
Command-line interface and console entry point for A.S.I.S.

Wires the identity, local memory, event bus and an AI provider together and
exposes a small set of subcommands: version, identity, tool listing, single
message processing, and a stdin REPL.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from asis.ai import AIManager
from asis.ai.providers import MockAIProvider, OllamaProvider
from asis.app.assistant import AssistantApp
from asis.app.modes import AssistantMode, parse_mode
from asis.configuration import settings
from asis.events import EventBus
from asis.identity import Identity, build_identity
from asis.memory import MemoryDatabase, MemoryManager, MemoryStorage
from asis.tools.provided import CurrentTimeTool, EchoTool, build_core_tools


def build_memory(db_path: str | Path | None = None) -> MemoryManager:
    """Build the local memory manager backed by a SQL file database."""
    from asis.errors import ConfigurationError

    if settings.memory.provider.strip().lower() != "local":
        raise ConfigurationError(
            "Invalid configuration memory.provider: only 'local' is "
            f"supported, received {settings.memory.provider!r}."
        )
    path = (
        Path(db_path)
        if db_path
        else (settings.paths.memory / settings.memory.database_name)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    return MemoryManager(MemoryStorage(MemoryDatabase(path)))


def _provider(provider_name: str, model: str):
    """Construct the requested provider, honouring the model override."""
    if provider_name == "mock":
        return MockAIProvider(model=model)
    if provider_name == "ollama":
        return OllamaProvider(
            model=model,
            host=settings.ai.endpoint,
            timeout=settings.ai.request_timeout,
            temperature=settings.ai.temperature,
            retries=settings.network.retries,
        )
    raise ValueError(f"Unsupported AI provider: {provider_name}")


def build_assistant(
    identity: Identity,
    ai: AIManager,
    memory: MemoryManager,
    mode: AssistantMode | str | None = None,
    workspace: str | Path | None = None,
) -> AssistantApp:
    """Build the stateful assistant owning one conversation session."""
    return AssistantApp(
        identity=identity, ai=ai, memory=memory, mode=mode, workspace=workspace
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the ``asis`` command-line parser."""
    parser = argparse.ArgumentParser(
        prog="asis",
        description="A.S.I.S. - A Smart Intelligence System. "
        "Speak to an always-on personal assistant that remembers you.",
    )
    parser.add_argument(
        "--version", action="store_true", help="print the version and exit"
    )
    parser.add_argument(
        "--identify",
        action="store_true",
        help="print the configured identity (system prompt) and exit",
    )
    parser.add_argument(
        "--provider",
        default=settings.ai.provider,
        choices=["mock", "ollama"],
        help="AI provider to use (default: %(default)s)",
    )
    parser.add_argument(
        "--model",
        default=settings.ai.model,
        help="model to use (default: %(default)s)",
    )
    parser.add_argument(
        "--memory-db",
        default=None,
        metavar="PATH",
        help="file for the local memory database (default: configured path)",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="list the built-in tools and exit",
    )
    parser.add_argument(
        "--core-status",
        action="store_true",
        help="print the C.O.R.E. connection status and exit",
    )
    parser.add_argument(
        "--message",
        default=None,
        metavar="TEXT",
        help="process a single message and exit",
    )
    parser.add_argument(
        "--mode",
        default=settings.coding.default_mode,
        choices=["general", "coding"],
        help="assistant mode to use (default: %(default)s)",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        metavar="PATH",
        help="coding workspace root (default: configured workspace or CWD)",
    )
    return parser


def core_status_line() -> str:
    """Describe the configured C.O.R.E. uplink without connecting.

    Never prompts for the provisioning credential and never opens a
    socket: with no credential available the manager reports DISABLED
    (CORE off) or DISCONNECTED (CORE on, no session) — both secret-free.
    """
    from asis.integrations.core.adapter import RealCoreAdapter
    from asis.integrations.core.connection import (
        build_connection_manager_from_settings,
    )
    from asis.system.context import RuntimeContext

    core = settings.core
    adapter = RealCoreAdapter(
        host=core.host,
        port=core.port,
        device_file=core.device_file,
        ca_file=core.ca_file,
        insecure=core.insecure,
        connect_timeout=core.connect_timeout,
        request_timeout=core.request_timeout,
    )
    manager = build_connection_manager_from_settings(
        settings, adapter, credential_provider=None
    )
    context = RuntimeContext()
    manager.start(context)
    try:
        status = manager.status()
    finally:
        manager.stop(context)
    state = getattr(status.state, "value", str(status.state)).lower()
    if state == "disabled":
        return "CORE: disabled (standalone)."
    return f"CORE: {state} (host={core.host}:{core.port})."


def handle_mode_command(app: AssistantApp, message: str) -> str | None:
    """Handle /mode and /ascs REPL commands; None when not a mode command."""
    text = message.strip()
    lowered = text.lower()
    if lowered == "/ascs":
        app.set_mode(AssistantMode.CODING)
        return f"A.S.C.S. coding mode enabled.\nWorkspace: {app.workspace.root}"
    if lowered == "/mode":
        return f"Current mode: {app.mode.value}"
    if lowered.startswith("/mode "):
        try:
            app.set_mode(parse_mode(text.split(None, 1)[1]))
        except ValueError as exc:
            return str(exc)
        if app.mode is AssistantMode.CODING:
            return f"A.S.C.S. coding mode enabled.\nWorkspace: {app.workspace.root}"
        return "A.S.I.S. general mode enabled."
    return None


def handle_message(
    identity: Identity,
    ai: AIManager,
    memory: MemoryManager,
    message: str,
    assistant: AssistantApp | None = None,
) -> str:
    """Process one user message through the stateful assistant pipeline.

    When ``assistant`` is provided the call joins its owned conversation
    session; otherwise a single-turn assistant is used (backwards
    compatible for direct callers and tests).
    """
    app = assistant or AssistantApp(identity=identity, ai=ai, memory=memory)
    return app.chat(message)


def entry(argv: Sequence[str] | None = None) -> int:
    """Console entry point for A.S.I.S."""
    raw = list(argv) if argv is not None else sys.argv[1:]
    if raw and raw[0] == "voice":
        from asis.cli.voice import run_voice

        return run_voice(raw[1:])

    args = build_parser().parse_args(argv)

    if args.version:
        print(f"{settings.app_name} {settings.app_version}")
        return 0

    if args.identify:
        print(build_identity().system_prompt())
        return 0

    if args.list_tools:
        for tool in (EchoTool(), CurrentTimeTool(), *build_core_tools(None)):
            print(f"{tool.name}: {tool.description}")
        return 0

    if args.core_status:
        print(core_status_line())
        return 0

    identity = build_identity()
    provider = _provider(args.provider, args.model)
    event_bus = EventBus()
    ai = AIManager(provider=provider, event_bus=event_bus)
    memory = build_memory(args.memory_db)
    app = build_assistant(
        identity, ai, memory, mode=args.mode, workspace=args.workspace
    )

    if args.message is not None:
        print(handle_message(identity, ai, memory, args.message, assistant=app))
        return 0

    print(identity.greeting)
    shutdown = settings.identity.shutdown_phrase.lower()
    for raw in sys.stdin:
        message = raw.strip()
        if not message:
            continue
        if message.lower() == shutdown:
            print("Shutting down.")
            break
        mode_reply = handle_mode_command(app, message)
        if mode_reply is not None:
            print(mode_reply)
            continue
        print(handle_message(identity, ai, memory, message, assistant=app))
    return 0


if __name__ == "__main__":
    raise SystemExit(entry())
