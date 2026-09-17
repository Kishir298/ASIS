"""Persistent interactive loop (thin orchestration over AssistantApp)."""

from __future__ import annotations

import contextlib
import os
import sys
import threading
from collections.abc import Callable

from .commands import HELP_TEXT, parse_command
from .keys import KeyWatcher
from .renderer import TypingRenderer
from .session import InteractiveSession

EXIT_PHRASES = frozenset({"asis shutdown"})


def _clear_screen(stream=None) -> None:
    out = stream if stream is not None else sys.stdout
    try:
        if os.name == "nt":
            os.system("cls")
        else:
            out.write("\033[2J\033[H")
            out.flush()
    except Exception:
        pass


def _default_voice_poll() -> str | None:
    """Non-blocking check for a typed line while in voice mode.

    Lets the user type ``/mode text`` (or any command) without restarting.
    Returns None when nothing was typed.  Never raises, never blocks.
    """
    try:
        if not sys.stdin.isatty():
            return None
        if os.name == "nt":
            import msvcrt

            if not msvcrt.kbhit():
                return None
            line = sys.stdin.readline()
        else:
            import select

            ready, _, _ = select.select([sys.stdin], [], [], 0)
            if not ready:
                return None
            line = sys.stdin.readline()
        text = (line or "").strip()
        return text or None
    except Exception:
        return None


def run_interactive(
    app,
    pipeline=None,
    doc_store=None,
    prompt: str = "You > ",
    input_fn: Callable[[str], str] | None = None,
    renderer: TypingRenderer | None = None,
    stream=None,
    cleanup: Callable[[], None] | None = None,
    max_turns: int = 0,
    voice_poll: Callable[[], str | None] | None = None,
) -> int:
    """Run the persistent terminal until /exit, /quit, shutdown phrase or CTRL+C.

    Returns a process exit code (0 normally).  ``max_turns`` bounds the loop
    for deterministic tests (0 = infinite).
    """
    out = stream if stream is not None else sys.stdout
    ask = input_fn if input_fn is not None else (lambda p: input(p))
    render = renderer if renderer is not None else TypingRenderer(stream=out)
    session = InteractiveSession(app, pipeline=pipeline, doc_store=doc_store)
    stop_event = threading.Event()
    poll_typed = voice_poll if voice_poll is not None else _default_voice_poll

    def _on_esc() -> None:
        stop_event.set()
        interrupts = getattr(app, "interrupts", None)
        if interrupts is not None:
            for scope in ("inference", "voice", "tools"):
                with contextlib.suppress(Exception):
                    interrupts.cancel(scope)
        if pipeline is not None:
            with contextlib.suppress(Exception):
                tts = getattr(pipeline, "tts", None)
                if tts is not None and hasattr(tts, "stop"):
                    tts.stop()
            with contextlib.suppress(Exception):
                pipeline.audio_output.stop()

    def _say_goodbye() -> None:
        try:
            out.write("Shutting down.\n")
            out.flush()
        except Exception:
            pass

    watcher = KeyWatcher(on_esc=_on_esc)

    def _cleanup() -> None:
        with contextlib.suppress(Exception):
            watcher.stop()
        if cleanup is not None:
            with contextlib.suppress(Exception):
                cleanup()

    try:
        out.write("A.S.I.S. ready.\n")
        out.flush()
    except Exception:
        pass
    watcher.start()
    turns = 0
    try:
        while True:
            if max_turns and turns >= max_turns:
                return 0
            stop_event.clear()
            try:
                if session.interaction_mode == "voice":
                    try:
                        out.write(
                            "VOICE MODE\n"
                            "Listening... (type /mode text + Enter to switch)\n"
                        )
                        out.flush()
                    except Exception:
                        pass
                    # Typed escape first: never trap the user in mic capture.
                    try:
                        typed = poll_typed()
                    except Exception:
                        typed = None
                    if not typed and voice_poll is None:
                        # Piped/scripted stdin (not a TTY): poll can't see it
                        # (msvcrt.kbhit/select only work on consoles), so
                        # consume the next scripted line instead of spinning
                        # on empty mock-audio turns forever.
                        try:
                            if not sys.stdin.isatty():
                                line = sys.stdin.readline()
                                if line == "":
                                    _say_goodbye()
                                    return 0
                                typed = (line or "").strip() or None
                        except Exception:
                            typed = None
                    if typed:
                        if typed.lower() in EXIT_PHRASES or typed.lower() in (
                            "/exit",
                            "/quit",
                        ):
                            _say_goodbye()
                            return 0
                        tcmd = parse_command(typed)
                        if tcmd is not None:
                            code = _handle_command(tcmd.name, tcmd.arg, session, out)
                            if code == "exit":
                                _say_goodbye()
                                return 0
                            turns += 1
                            continue
                        try:
                            response = session.chat_text(typed)
                        except Exception as exc:
                            response = f"Sorry, that failed: {exc}"
                        render.render(response or "", stop_event=stop_event)
                        turns += 1
                        continue
                    try:
                        turn = session.voice_turn()
                    except RuntimeError as exc:
                        try:
                            out.write(f"A.S.I.S. > {exc}\n")
                            out.flush()
                        except Exception:
                            pass
                        turns += 1
                        continue
                    transcript = (turn.get("transcript") or "").strip()
                    response = turn.get("response") or ""
                    if transcript:
                        try:
                            out.write(f"You > {transcript}\n")
                            out.flush()
                        except Exception:
                            pass
                    else:
                        turns += 1
                        continue
                    # run_once() already spoke via the existing pipeline using
                    # the same final text; render the identical transcript.
                    render.render(response, stop_event=stop_event)
                    turns += 1
                    continue
                try:
                    raw = ask(prompt)
                except EOFError:
                    _say_goodbye()
                    return 0
                message = (raw or "").strip()
                if not message:
                    continue
                if message.lower() in EXIT_PHRASES or message.lower() in (
                    "/exit",
                    "/quit",
                ):
                    _say_goodbye()
                    return 0
                cmd = parse_command(message)
                if cmd is not None:
                    code = _handle_command(cmd.name, cmd.arg, session, out)
                    if code == "exit":
                        _say_goodbye()
                        return 0
                    turns += 1
                    continue
                try:
                    response = session.chat_text(message)
                except Exception as exc:
                    try:
                        out.write(f"A.S.I.S. > Sorry, that failed: {exc}\n")
                        out.flush()
                    except Exception:
                        pass
                    turns += 1
                    continue
                render.render(response or "", stop_event=stop_event)
                turns += 1
            except KeyboardInterrupt:
                _say_goodbye()
                return 0
    finally:
        _cleanup()
    return 0


def _handle_command(
    name: str, arg: str, session: InteractiveSession, out
) -> str | None:
    lname = (name or "").lower()
    if lname == "/help":
        out.write(HELP_TEXT + "\n")
        out.flush()
        return None
    if lname == "/mode":
        if not arg:
            mode = session.toggle_mode()
        elif arg.strip().lower() in ("text", "voice"):
            mode = session.set_interaction_mode(arg.strip().lower())
        else:
            out.write("Usage: /mode [text|voice]\n")
            out.flush()
            return None
        out.write("VOICE MODE\n" if mode == "voice" else "TEXT MODE\n")
        out.flush()
        return None
    if lname in ("/upload", "/attach"):
        if not arg:
            out.write("Usage: /upload <path>\n")
            out.flush()
            return None
        try:
            doc = session.docs.attach(arg)
        except FileNotFoundError:
            out.write("A.S.I.S. > I couldn't find that file.\n")
            out.flush()
            return None
        except ValueError as exc:
            text = str(exc)
            if "unsupported" in text.lower():
                out.write("A.S.I.S. > I can't read that file type yet.\n")
            else:
                out.write(f"A.S.I.S. > {text}\n")
            out.flush()
            return None
        except Exception as exc:
            out.write(f"A.S.I.S. > Couldn't attach that file: {exc}\n")
            out.flush()
            return None
        out.write(f"Attached: {doc.name}\n")
        out.flush()
        return None
    if lname == "/docs":
        names = session.docs.list_names()
        if not names:
            out.write("No attached documents.\n")
        else:
            out.write("Attached documents:\n")
            for doc_name in names:
                out.write(f"- {doc_name}\n")
        out.flush()
        return None
    if lname == "/clear-docs":
        session.docs.clear()
        out.write("Cleared attached documents.\n")
        out.flush()
        return None
    if lname == "/clear":
        _clear_screen(out)
        return None
    if lname in ("/exit", "/quit"):
        return "exit"
    out.write(f"Unknown command: {lname} (try /help)\n")
    out.flush()
    return None
