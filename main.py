"""
Forza AI
--------

Main interactive runtime for Forza.

Boot order:
    1. Display banner
    2. Load long-term memory
    3. Start runtime
    4. Initialize AI
    5. Check Ollama
    6. Greet the user
    7. Start chat

Memory is stored outside the Git repository using
Forza's cross-platform persistent data directory.
"""

from __future__ import annotations

import json
import re
import signal
from collections.abc import Sequence
from pathlib import Path
from types import FrameType

from core.ai.models import AIMessage
from core.ai.ollama import OllamaProvider
from core.ai.manager import AIManager
from core.config.settings import settings
from core.runtime import ForzaRuntime


# ============================================================================
# TERMINAL COLORS
# ============================================================================

RESET = "\033[0m"
BOLD = "\033[1m"

GREEN = "\033[92m"
CYAN = "\033[96m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
GRAY = "\033[90m"


# ============================================================================
# GLOBAL STATE
# ============================================================================

runtime = ForzaRuntime()

provider: OllamaProvider | None = None
ai: AIManager | None = None

conversation: list[AIMessage] = []

_shutdown_requested = False
_generating = False


# ============================================================================
# MEMORY
# ============================================================================

MEMORY_FILE_NAME = "memories.json"

memory: dict[str, list[dict[str, object]]] = {
    "user": [],
    "assistant": [],
    "general": [],
}


def get_memory_file() -> Path:
    """
    Return Forza's persistent memory file.

    IMPORTANT:
    This uses Forza's platform-specific application-data directory,
    NOT the Git repository.
    """

    memory_directory = Path(
        settings.paths.memory
    )

    memory_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return memory_directory / MEMORY_FILE_NAME


def default_memory() -> dict[str, list[dict[str, object]]]:
    """Return Forza's permanent identity memories."""

    return {
        "user": [],
        "assistant": [
            {
                "fact": (
                    "I am Forza, the AI assistant "
                    "inside the Forza AI project."
                ),
                "importance": 10,
            },
            {
                "fact": (
                    "The user is developing and "
                    "improving Forza AI."
                ),
                "importance": 10,
            },
        ],
        "general": [],
    }


def normalize_memory(
    data: object,
) -> dict[str, list[dict[str, object]]]:
    """Normalize memory data without deleting valid memories."""

    normalized = {
        "user": [],
        "assistant": [],
        "general": [],
    }

    if isinstance(data, list):

        for item in data:

            if isinstance(item, str) and item.strip():

                normalized["general"].append(
                    {
                        "fact": item.strip()[:500],
                        "importance": 5,
                    }
                )

    elif isinstance(data, dict):

        for category in (
            "user",
            "assistant",
            "general",
        ):

            values = data.get(
                category,
                [],
            )

            if not isinstance(values, list):
                continue

            for item in values:

                if isinstance(item, str):

                    fact = item.strip()
                    importance = 5

                elif isinstance(item, dict):

                    fact = str(
                        item.get(
                            "fact",
                            "",
                        )
                    ).strip()

                    try:
                        importance = int(
                            item.get(
                                "importance",
                                5,
                            )
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        importance = 5

                else:
                    continue

                if not fact:
                    continue

                normalized[category].append(
                    {
                        "fact": fact[:500],
                        "importance": max(
                            1,
                            min(
                                importance,
                                10,
                            ),
                        ),
                    }
                )

    # Remove duplicates.
    for category in normalized:

        unique: list[dict[str, object]] = []
        seen: set[str] = set()

        for item in normalized[category]:

            fact = str(
                item["fact"]
            ).strip()

            key = fact.casefold()

            if not fact or key in seen:
                continue

            seen.add(key)
            unique.append(item)

        normalized[category] = unique

    return normalized


def load_memory() -> None:
    """
    Load memory from disk.

    IMPORTANT:
    Loading NEVER writes to the memory file.
    """

    global memory

    memory_file = get_memory_file()

    if not memory_file.exists():

        memory = default_memory()

        save_memory()

        return

    try:

        with memory_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        memory = normalize_memory(data)

        # Add missing built-in identity memories.
        defaults = default_memory()

        existing = {
            str(item["fact"]).casefold()
            for item in memory["assistant"]
        }

        changed = False

        for item in defaults["assistant"]:

            fact = str(
                item["fact"]
            )

            if fact.casefold() not in existing:

                memory["assistant"].append(
                    item
                )

                changed = True

        # Only write if something genuinely needed adding.
        if changed:
            save_memory()

    except json.JSONDecodeError:

        print_warning(
            "Memory file is invalid. "
            "Existing file was NOT overwritten."
        )

        memory = default_memory()

    except OSError as exc:

        print_warning(
            f"Could not read memory: {exc}"
        )

        memory = default_memory()


def save_memory() -> None:
    """Atomically save persistent memory."""

    memory_file = get_memory_file()

    temporary_file = memory_file.with_suffix(
        ".tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            memory,
            file,
            indent=2,
            ensure_ascii=False,
        )

    temporary_file.replace(
        memory_file
    )


def add_memory(
    fact: str,
    category: str = "general",
    importance: int = 5,
) -> bool:
    """Add a permanent memory."""

    if category not in memory:
        category = "general"

    fact = fact.strip()[:500]

    if not fact:
        return False

    try:
        importance = int(
            importance
        )

    except (
        TypeError,
        ValueError,
    ):
        importance = 5

    importance = max(
        1,
        min(
            importance,
            10,
        ),
    )

    existing = {
        str(item["fact"]).casefold()
        for item in memory[category]
    }

    if fact.casefold() in existing:
        return False

    memory[category].append(
        {
            "fact": fact,
            "importance": importance,
        }
    )

    save_memory()

    return True


def remove_memory(
    query: str,
) -> int:
    """Remove memories matching a search term."""

    query = query.strip().casefold()

    if not query:
        return 0

    removed = 0

    for category in memory:

        original_count = len(
            memory[category]
        )

        memory[category] = [
            item
            for item in memory[category]
            if query
            not in str(
                item["fact"]
            ).casefold()
        ]

        removed += (
            original_count
            - len(memory[category])
        )

    if removed:
        save_memory()

    return removed


def clear_memory() -> int:
    """Clear user/general memory while preserving Forza identity."""

    count = (
        len(memory["user"])
        + len(memory["general"])
    )

    memory["user"].clear()
    memory["general"].clear()

    save_memory()

    return count


def get_user_name() -> str | None:
    """Return the user's remembered name."""

    for item in memory["user"]:

        fact = str(
            item["fact"]
        )

        match = re.search(
            r"user'?s name is\s+([^.!?,]+)",
            fact,
            flags=re.IGNORECASE,
        )

        if match:

            name = match.group(1).strip()

            if name:
                return name

    return None


def get_all_memories() -> list[dict[str, object]]:
    """Return every stored memory."""

    result = []

    for category in (
        "user",
        "assistant",
        "general",
    ):

        for item in memory[category]:

            result.append(
                {
                    "category": category,
                    "fact": item["fact"],
                    "importance": item["importance"],
                }
            )

    return result


def get_memory_context() -> str:
    """
    Build the memory context sent to Forza.

    User memories are always included.

    This is intentional. With a small personal memory store,
    keyword matching is unnecessary and can cause Forza to
    forget relevant information simply because the user said
    'what are my interests?' instead of 'what do I like?'
    """

    lines = [
        "LONG-TERM MEMORY:",
        "",
        "USER MEMORIES:",
    ]

    if memory["user"]:

        for item in memory["user"]:

            lines.append(
                f"- {item['fact']}"
            )

    else:

        lines.append(
            "- No user memories stored."
        )

    lines.extend(
        [
            "",
            "FORZA IDENTITY:",
        ]
    )

    for item in memory["assistant"]:

        lines.append(
            f"- {item['fact']}"
        )

    if memory["general"]:

        lines.extend(
            [
                "",
                "GENERAL MEMORIES:",
            ]
        )

        for item in memory["general"]:

            lines.append(
                f"- {item['fact']}"
            )

    lines.extend(
        [
            "",
            "MEMORY RULES:",
            "- Use these memories when relevant.",
            "- Never invent memories.",
            "- Never claim to remember something that is not here.",
            "- User memories describe the user.",
            "- Forza identity memories describe Forza.",
            "- Do not mention the memory system unless asked.",
        ]
    )

    return "\n".join(lines)


def automatically_store_memory(
    message: str,
) -> None:
    """
    Detect explicit personal facts from the user's message.

    This intentionally handles several facts in one sentence.
    """

    text = message.strip()

    # ------------------------------------------------------------------------
    # NAME
    # ------------------------------------------------------------------------

    name_match = re.search(
        r"\bmy name is\s+([^,.!?]+)",
        text,
        flags=re.IGNORECASE,
    )

    if name_match:

        name = name_match.group(1).strip()

        if name:

            add_memory(
                f"User's name is {name}.",
                category="user",
                importance=10,
            )

    # ------------------------------------------------------------------------
    # LIKE / LOVE
    # ------------------------------------------------------------------------

    like_match = re.search(
        r"\bi (?:like|love)\s+(.+?)(?:(?:\.\s)|(?:!\s)|(?:\?\s)|$)",
        text,
        flags=re.IGNORECASE,
    )

    if like_match:

        interests = like_match.group(1).strip()

        if interests:

            verb = (
                "loves"
                if re.search(
                    r"\bi love\b",
                    text,
                    flags=re.IGNORECASE,
                )
                else "likes"
            )

            add_memory(
                f"User {verb} {interests}.",
                category="user",
                importance=8,
            )

    # ------------------------------------------------------------------------
    # PLAY
    # ------------------------------------------------------------------------

    play_match = re.search(
        r"\bi play\s+(.+?)(?:(?:\.\s)|(?:!\s)|(?:\?\s)|$)",
        text,
        flags=re.IGNORECASE,
    )

    if play_match:

        games_or_sports = (
            play_match.group(1).strip()
        )

        if games_or_sports:

            add_memory(
                f"User plays {games_or_sports}.",
                category="user",
                importance=7,
            )

    # ------------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------------

    read_match = re.search(
        r"\bi read\s+(.+?)(?:(?:\.\s)|(?:!\s)|(?:\?\s)|$)",
        text,
        flags=re.IGNORECASE,
    )

    if read_match:

        books = read_match.group(1).strip()

        if books:

            add_memory(
                f"User reads {books}.",
                category="user",
                importance=7,
            )

    # ------------------------------------------------------------------------
    # BUILDING / WORKING ON
    # ------------------------------------------------------------------------

    project_match = re.search(
        r"\bi(?:'m| am)\s+(?:building|working on)\s+(.+?)(?:(?:\.\s)|(?:!\s)|(?:\?\s)|$)",
        text,
        flags=re.IGNORECASE,
    )

    if project_match:

        project = project_match.group(1).strip()

        if project:

            add_memory(
                f"User is working on {project}.",
                category="user",
                importance=9,
            )

    # ------------------------------------------------------------------------
    # FORZA IDENTITY
    # ------------------------------------------------------------------------

    identity_patterns = [
        (
            r"\byou(?:'re| are)\s+the ai\b",
            "I am the AI assistant being developed as Forza.",
        ),
        (
            r"\byou(?:'re| are)\s+forza\b",
            "I am Forza.",
        ),
        (
            r"\byou(?:'re| are)\s+the assistant\b",
            "I am the AI assistant in the Forza AI project.",
        ),
        (
            r"\bi(?:'m| am)\s+improving you\b",
            "The user is actively improving Forza AI.",
        ),
        (
            r"\bi(?:'m| am)\s+building you\b",
            "The user is building Forza AI.",
        ),
    ]

    for pattern, fact in identity_patterns:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):

            add_memory(
                fact,
                category="assistant",
                importance=10,
            )


# ============================================================================
# SYSTEM PROMPT
# ============================================================================

FORZA_SYSTEM_PROMPT = """
You are Forza.

You are the AI assistant inside the Forza AI project.

The user is actively developing and improving you.

IDENTITY:
- You are Forza.
- You are the AI being developed by the user.
- The user may call you Forza, the AI, or you.
- Understand that these refer to you.
- Do not behave like a generic customer-service chatbot.

PERSONALITY:
- Casual
- Funny when appropriate
- Slightly sarcastic
- Confident
- Playful
- Smart
- Direct
- Human-sounding

Speak naturally.

Do not constantly ask follow-up questions.

Do not repeatedly say:
"How can I help you today?"
"What can I get you today?"
"Certainly!"
"Great question!"
"I'd be happy to assist."

If the user says they are improving or building you,
understand that they are developing Forza AI.

MEMORY:
Long-term memory is supplied below.

Use it naturally.

If the user asks about their name, interests,
preferences, projects, hobbies, or other stored facts,
answer directly using the memory.

Never invent personal information.

Never say the user is "the user" when their name
or relevant personal information is available.

You are Forza.
"""


# ============================================================================
# OUTPUT
# ============================================================================

def print_system(
    message: str,
) -> None:

    print(
        f"{CYAN}{BOLD}[SYSTEM]{RESET} "
        f"{CYAN}{message}{RESET}",
        flush=True,
    )


def print_error(
    message: str,
) -> None:

    print(
        f"{RED}{BOLD}[ERROR]{RESET} "
        f"{RED}{message}{RESET}",
        flush=True,
    )


def print_warning(
    message: str,
) -> None:

    print(
        f"{YELLOW}{BOLD}[WARNING]{RESET} "
        f"{YELLOW}{message}{RESET}",
        flush=True,
    )


def print_forza_prefix() -> None:

    print(
        f"{GREEN}{BOLD}Forza-AI:{RESET} "
        f"{GREEN}",
        end="",
        flush=True,
    )


def print_user_prefix() -> None:

    print(
        f"{BLUE}{BOLD}User:{RESET} ",
        end="",
        flush=True,
    )


# ============================================================================
# BANNER
# ============================================================================

def print_banner() -> None:

    print()

    print(
        f"{GREEN}{BOLD}"
        "███████╗ ██████╗ ██████╗ ███████╗ █████╗ ██╗\n"
        "██╔════╝██╔═══██╗██╔══██╗╚══███╔╝██╔══██╗██║\n"
        "█████╗  ██║   ██║██████╔╝  ███╔╝ ███████║██║\n"
        "██╔══╝  ██║   ██║██╔══██╗ ███╔╝  ██╔══██║██║\n"
        "██║     ╚██████╔╝██║  ██║███████╗██║  ██║██║\n"
        "╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝"
        f"{RESET}"
    )

    print(
        f"{GRAY}Cross-platform AI assistant{RESET}"
    )

    print()


# ============================================================================
# BOOT GREETING
# ============================================================================

def get_boot_greeting() -> str:

    name = get_user_name()

    if name:
        return f"Yo {name}, wassup? 💀"

    return "Yo, wassup? 💀"


def print_boot_greeting() -> None:

    print_forza_prefix()

    print(
        get_boot_greeting()
        + RESET,
        flush=True,
    )


# ============================================================================
# AI
# ============================================================================

def create_ai() -> AIManager:

    if settings.ai.provider.lower() != "ollama":

        raise RuntimeError(
            f"Unsupported AI provider: "
            f"{settings.ai.provider}"
        )

    ollama = OllamaProvider(
        model=settings.ai.model,
        host=settings.ai.endpoint,
        timeout=float(
            settings.ai.request_timeout
        ),
    )

    return AIManager(
        ollama
    )


def build_messages(
    messages: Sequence[AIMessage],
) -> list[AIMessage]:

    context_limit = max(
        1,
        int(
            settings.ai.max_context_messages
        ),
    )

    system_content = (
        FORZA_SYSTEM_PROMPT.strip()
        + "\n\n"
        + get_memory_context()
    )

    return [
        AIMessage(
            role="system",
            content=system_content,
        ),
        *list(
            messages[
                -context_limit:
            ]
        ),
    ]


# ============================================================================
# STREAMING
# ============================================================================

def stream_response(
    manager: AIManager,
    messages: Sequence[AIMessage],
) -> tuple[str, bool]:

    global _generating

    provider_instance = manager.provider

    if not isinstance(
        provider_instance,
        OllamaProvider,
    ):

        raise RuntimeError(
            "The configured provider "
            "does not support streaming."
        )

    parts: list[str] = []
    interrupted = False

    _generating = True

    print_forza_prefix()

    try:

        for chunk in provider_instance.stream_chat(
            build_messages(messages)
        ):

            parts.append(chunk)

            print(
                chunk,
                end="",
                flush=True,
            )

    except KeyboardInterrupt:

        interrupted = True

    finally:

        _generating = False

        print(
            RESET,
            flush=True,
        )

    return (
        "".join(parts),
        interrupted,
    )


# ============================================================================
# STATUS
# ============================================================================

def show_status() -> None:

    print_system(
        f"Runtime: {runtime.state}"
    )

    if provider is not None:

        print_system(
            f"AI provider: {provider.name}"
        )

        print_system(
            f"AI model: {provider.model}"
        )

        try:
            available = provider.available()

        except Exception:
            available = False

        print_system(
            "Ollama: "
            + (
                f"{GREEN}ready{RESET}"
                if available
                else f"{RED}offline{RESET}"
            )
        )

    print_system(
        f"Memory file: {get_memory_file()}"
    )

    print_system(
        f"Total memories: "
        f"{len(get_all_memories())}"
    )

    print_system(
        f"User memories: "
        f"{len(memory['user'])}"
    )

    print_system(
        f"Forza memories: "
        f"{len(memory['assistant'])}"
    )

    print_system(
        f"General memories: "
        f"{len(memory['general'])}"
    )


# ============================================================================
# MEMORY DISPLAY
# ============================================================================

def show_memory() -> None:

    memories = get_all_memories()

    if not memories:

        print_system(
            "No memories stored."
        )

        return

    print_system(
        f"Stored memories: {len(memories)}"
    )

    print()

    for index, item in enumerate(
        memories,
        start=1,
    ):

        print(
            f"{MAGENTA}{index:>3}.{RESET} "
            f"[{item['category']}] "
            f"{item['fact']} "
            f"{GRAY}"
            f"(importance "
            f"{item['importance']}/10)"
            f"{RESET}"
        )


# ============================================================================
# COMMANDS
# ============================================================================

def handle_command(
    message: str,
) -> bool | None:

    original = message.strip()
    command = original.casefold()

    if command in {
        "shutdown",
        "/shutdown",
        "exit",
        "/exit",
        "quit",
        "/quit",
    }:

        shutdown()

        return False

    if command in {
        "status",
        "/status",
    }:

        show_status()

        return True

    if command in {
        "clear",
        "/clear",
    }:

        conversation.clear()

        print_system(
            "Conversation cleared."
        )

        return True

    if command in {
        "memory",
        "/memory",
        "memories",
        "/memories",
    }:

        show_memory()

        return True

    if command.startswith(
        (
            "remember ",
            "/remember ",
        )
    ):

        fact = original.split(
            " ",
            1,
        )[1].strip()

        if add_memory(
            fact,
            category="general",
            importance=7,
        ):

            print_system(
                "Memory saved permanently."
            )

        else:

            print_system(
                "That memory already exists."
            )

        return True

    if command.startswith(
        (
            "forget ",
            "/forget ",
        )
    ):

        query = original.split(
            " ",
            1,
        )[1].strip()

        removed = remove_memory(
            query
        )

        if removed:

            print_system(
                f"Removed {removed} "
                f"matching "
                f"{'memory' if removed == 1 else 'memories'}."
            )

        else:

            print_system(
                "No matching memories found."
            )

        return True

    if command in {
        "clear_memory",
        "/clear_memory",
    }:

        count = clear_memory()

        print_system(
            f"Cleared {count} user/general memories."
        )

        return True

    if command in {
        "help",
        "/help",
    }:

        print_system(
            "Commands: status, clear, memory, "
            "remember <fact>, forget <fact>, "
            "clear_memory, help, shutdown"
        )

        print_system(
            "Ctrl+C interrupts the current response."
        )

        return True

    return None


# ============================================================================
# MESSAGE HANDLING
# ============================================================================

def handle_message(
    message: str,
) -> bool:

    if not message.strip():
        return True

    command_result = handle_command(
        message
    )

    if command_result is not None:
        return command_result

    if ai is None:

        print_error(
            "AI manager is not initialized."
        )

        return True

    cleaned = message.strip()

    # Store facts BEFORE generating the response.
    automatically_store_memory(
        cleaned
    )

    conversation.append(
        AIMessage(
            role="user",
            content=cleaned,
        )
    )

    try:

        response, interrupted = (
            stream_response(
                ai,
                conversation,
            )
        )

    except Exception as exc:

        print_error(
            f"AI response failed: {exc}"
        )

        conversation.pop()

        return True

    if interrupted:

        print(
            f"{YELLOW}"
            "[Response interrupted]"
            f"{RESET}",
            flush=True,
        )

        return True

    if response.strip():

        conversation.append(
            AIMessage(
                role="assistant",
                content=response,
            )
        )

    print()

    return True


# ============================================================================
# CHAT LOOP
# ============================================================================

def chat_loop() -> None:

    print_system(
        "Type a message to talk to Forza."
    )

    print_system(
        "Ctrl+C interrupts the current response."
    )

    print_system(
        "Use 'shutdown' to turn Forza off."
    )

    print_system(
        "Commands: status, clear, memory, "
        "remember <fact>, forget <fact>, "
        "clear_memory, help, shutdown"
    )

    print()

    while (
        runtime.is_running
        and not _shutdown_requested
    ):

        try:

            print_user_prefix()

            user_message = input()

        except KeyboardInterrupt:

            print()

            print_system(
                "Input cancelled."
            )

            print()

            continue

        except EOFError:

            print()

            shutdown()

            return

        if not handle_message(
            user_message
        ):

            return


# ============================================================================
# SHUTDOWN
# ============================================================================

def shutdown() -> None:

    global _shutdown_requested

    if _shutdown_requested:
        return

    _shutdown_requested = True

    print()

    print_system(
        "Shutdown requested."
    )

    try:

        if runtime.is_running:
            runtime.stop()

    except Exception as exc:

        print_error(
            f"Runtime shutdown failed: {exc}"
        )

    else:

        print_system(
            "Runtime stopped."
        )

        print_forza_prefix()

        print(
            "Goodbye."
            f"{RESET}",
            flush=True,
        )


# ============================================================================
# SIGNAL HANDLING
# ============================================================================

def handle_signal(
    signum: int,
    frame: FrameType | None,
) -> None:

    if _generating:

        raise KeyboardInterrupt

    print()

    print_system(
        "Ctrl+C does not shut down Forza."
    )

    print_system(
        "Use 'shutdown' to stop Forza."
    )

    print()


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:

    global provider
    global ai

    # ------------------------------------------------------------------------
    # 1. BANNER
    # ------------------------------------------------------------------------

    print_banner()

    # ------------------------------------------------------------------------
    # 2. MEMORY
    # ------------------------------------------------------------------------

    print_system(
        "Loading long-term memory..."
    )

    load_memory()

    print_system(
        f"Loaded "
        f"{len(get_all_memories())} "
        f"memories."
    )

    # ------------------------------------------------------------------------
    # 3. RUNTIME
    # ------------------------------------------------------------------------

    print()

    print_system(
        "Starting runtime..."
    )

    try:

        runtime.start()

        print_system(
            "Runtime started."
        )

        # --------------------------------------------------------------------
        # 4. AI
        # --------------------------------------------------------------------

        ai = create_ai()

        provider = ai.provider

        print_system(
            f"AI provider: "
            f"{provider.name}"
        )

        print_system(
            f"AI model: "
            f"{provider.model}"
        )

        # --------------------------------------------------------------------
        # 5. OLLAMA
        # --------------------------------------------------------------------

        if provider.available():

            print_system(
                "Ollama connection: "
                f"{GREEN}ready{RESET}"
            )

        else:

            print_error(
                "Ollama is not reachable."
            )

            print_system(
                "Start Ollama before sending messages."
            )

        # --------------------------------------------------------------------
        # 6. GREETING
        # --------------------------------------------------------------------

        print()

        print_boot_greeting()

        print()

        # --------------------------------------------------------------------
        # 7. CHAT
        # --------------------------------------------------------------------

        chat_loop()

    except Exception as exc:

        if not _shutdown_requested:

            print_error(
                f"Forza failed to start: {exc}"
            )

            try:

                if runtime.is_running:
                    runtime.stop()

            except Exception:
                pass

            return 1

    return 0


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":

    signal.signal(
        signal.SIGINT,
        handle_signal,
    )

    if hasattr(
        signal,
        "SIGTERM",
    ):

        signal.signal(
            signal.SIGTERM,
            handle_signal,
        )

    raise SystemExit(
        main()
    )