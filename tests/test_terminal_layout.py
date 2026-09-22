"""Display-only tests for terminal layout + status bar (no model/mic)."""

from __future__ import annotations

from asis.cli.terminal import layout
from asis.cli.terminal import status as statusmod


def test_header_footer_panels():
    h = layout.header()
    assert "A.S.I.S." in h and "ONLINE" in h
    assert "OFFLINE" in layout.header(online=False)
    f = layout.footer()
    assert "ENTER Send" in f and "CTRL+C Exit" in f


def test_bubbles_badges_composer():
    assert "You" in layout.user_bubble("hello")
    assert "Hello" in layout.assistant_bubble("Hello")
    assert "▌" in layout.assistant_bubble("Hi", streaming=True)
    assert "[TOOL]" in layout.tool_badge("calc")
    assert "[DONE]" in layout.tool_badge("calc", done=True)
    assert "(none)" in layout.attachments_bar([])
    assert "physics_notes.pdf" in layout.attachments_bar(["physics_notes.pdf"])
    c = layout.composer(mode="VOICE", attachments=["a.pdf"], generating=True)
    assert "VOICE" in c and "Generating" in c


def test_status_voice_error_text():
    bar = statusmod.status_bar()
    assert "MODEL:" in bar and "MODE:" in bar and "OLLAMA:" in bar
    assert "LISTENING" in statusmod.voice_strip("listening")
    assert "IDLE" in statusmod.voice_strip("bogus")
    err = statusmod.clean_error("Unable to reach Ollama.", "connection failed", "check Ollama")
    assert "⚠" in err and "Traceback" not in err


def test_narrow_width_no_overflow():
    h = layout.header(width=40)
    assert len(h.splitlines()[0]) <= 42
