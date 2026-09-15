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
from asis.configuration import settings
from asis.events import EventBus
from asis.identity import Identity, build_identity
from asis.memory import MemoryDatabase, MemoryManager, MemoryStorage
from asis.tools.provided import CurrentTimeTool, EchoTool


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
) -> AssistantApp:
    """Build the stateful assistant owning one conversation session."""
    return AssistantApp(identity=identity, ai=ai, memory=memory)


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
        "--message",
        default=None,
        metavar="TEXT",
        help="process a single message and exit",
    )
    return parser


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
        for tool in (EchoTool(), CurrentTimeTool()):
            print(f"{tool.name}: {tool.description}")
        return 0

    identity = build_identity()
    provider = _provider(args.provider, args.model)
    event_bus = EventBus()
    ai = AIManager(provider=provider, event_bus=event_bus)
    memory = build_memory(args.memory_db)
    app = build_assistant(identity, ai, memory)

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
        print(handle_message(identity, ai, memory, message, assistant=app))
    return 0


if __name__ == "__main__":
    raise SystemExit(entry())
