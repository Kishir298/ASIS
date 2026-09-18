"""Intelligence orchestration regression tests (deterministic, offline).

Covers: orchestrator intent taxonomy, personality runtime integration,
context assembly bounds, mode differences, tool/permission representation,
thinking separation, streaming visibility, ESC recovery, CLI end-to-end,
qwen3:14b default, and multi-turn memory recall.
"""

from __future__ import annotations

import io

from asis.ai import AIManager
from asis.ai.context import ContextAssembler
from asis.ai.conversation import ConversationSession
from asis.ai.inference import InferenceEngine
from asis.ai.models import AIResponse
from asis.ai.orchestrator import Intent, build_plan, classify_intent
from asis.ai.providers import MockAIProvider
from asis.app.assistant import AssistantApp
from asis.configuration import defaults
from asis.errors import CancellationError
from asis.identity import build_identity
from asis.identity.personality import load_personality_file
from asis.memory import MemoryCategory
from asis.system.interrupt import InterruptCoordinator


def _app(memory_manager, responses=("ok",), **kwargs):
    return AssistantApp(
        identity=build_identity(),
        ai=AIManager(provider=MockAIProvider(responses=responses)),
        memory=memory_manager,
        **kwargs,
    )


# -- orchestrator taxonomy -------------------------------------------------


def test_intent_taxonomy_deterministic():
    assert classify_intent("hi") is Intent.GENERAL_CHAT
    assert classify_intent("What is the time?") is Intent.TOOL_REQUEST
    assert classify_intent("what is my name?") is Intent.MEMORY_QUERY
    assert classify_intent("core:devices") is Intent.CORE_OPERATION
    assert classify_intent("2+2") is Intent.CALCULATION
    assert classify_intent("calculate 6*7") is Intent.CALCULATION
    assert classify_intent("read the file foo.py", mode="coding") is Intent.CODING
    assert classify_intent("summarize the document", has_docs=True) in (
        Intent.DOCUMENT_QUERY,
        Intent.TASK,
    )
    assert classify_intent("What is Python?") is Intent.QUESTION
    assert classify_intent("Write a function") is Intent.TASK
    assert classify_intent("", mode="general") is Intent.UNKNOWN
    assert classify_intent("hello", is_voice=True) is Intent.VOICE_INTERACTION
    assert classify_intent("anything", mode="translation") is Intent.TRANSLATION
    # Deterministic: same input -> same output, no model involved.
    assert classify_intent("hi") == classify_intent("hi")


def test_plan_memory_bounded_and_selective():
    plan = build_plan("what is my name?", memory_limit=5)
    assert plan.memory_needed is True
    assert plan.memory_limit == 5
    chat = build_plan("hi")
    assert chat.memory_needed is False


# -- personality runtime ---------------------------------------------------


def test_identity_in_runtime_context(memory_manager):
    app = _app(memory_manager, responses=("ok",))
    prompt = app.assembler.system_prompt()
    assert "SYSTEM:" in prompt
    assert app.identity.name in prompt
    assert "MODE:" in prompt  # general profile now always present
    assert "CAPABILITIES:" in prompt


def test_personality_file_missing_graceful(tmp_path):
    assert load_personality_file(str(tmp_path / "nope.txt")) is None
    identity = build_identity(personality_file=str(tmp_path / "nope.txt"))
    assert identity.personality  # falls back to default


def test_personality_file_empty_graceful(tmp_path):
    target = tmp_path / "empty.txt"
    target.write_text("   \n", encoding="utf-8")
    assert load_personality_file(target) is None


def test_personality_file_loaded(tmp_path):
    target = tmp_path / "p.txt"
    target.write_text("Serve as {name}, test persona.", encoding="utf-8")
    identity = build_identity(personality_file=str(target))
    assert "test persona" in identity.personality


def test_empty_personality_still_functions(memory_manager):
    from asis.identity import Identity

    app = AssistantApp(
        identity=Identity(name="A", title="T", personality=""),
        ai=AIManager(provider=MockAIProvider(responses=("ok",))),
        memory=memory_manager,
    )
    assert app.chat("hello") == "ok"


# -- context assembly ------------------------------------------------------


def test_mode_contexts_differ(memory_manager):
    general = _app(memory_manager, responses=("ok",), mode="general")
    coding = _app(memory_manager, responses=("ok",), mode="coding")
    translation = _app(memory_manager, responses=("ok",), mode="translation")
    g, c, t = (
        general.assembler.system_prompt(),
        coding.assembler.system_prompt(),
        translation.assembler.system_prompt(),
    )
    assert g != c
    assert g != t
    assert "coding" in c.lower() or "A.S.C.S" in c or "repository" in c.lower()


def test_context_bounded():
    identity = build_identity()
    big = "x" * 100_000
    assembler = ContextAssembler(
        identity=identity,
        memory_context_provider=lambda: big,
        context_char_limit=1000,
    )
    prompt = assembler.system_prompt()
    assert len(prompt) <= 1000 + len("\n\n[context truncated]")


def test_conversation_reaches_model(memory_manager):
    seen: dict = {}

    class Capturing(MockAIProvider):
        def chat(self, messages):
            seen["messages"] = list(messages)
            return AIResponse(content="ok", model="m", provider="mock")

    app = AssistantApp(
        identity=build_identity(),
        ai=AIManager(provider=Capturing()),
        memory=memory_manager,
    )
    app.chat("first turn")
    app.chat("second turn")
    contents = [m.content for m in seen["messages"]]
    assert any("first turn" in c for c in contents)
    assert any("second turn" in c for c in contents)


def test_only_relevant_memory_included(memory_manager):
    memory_manager.remember("User plays chess.", category=MemoryCategory.USER)
    app = _app(memory_manager, responses=("ok",))
    app.chat("hi")  # general chat: no memory query -> no memory section
    prompt = app.assembler.system_prompt()
    # No pending query outside a turn, so unrelated memory stays out.
    assert "chess" not in prompt


# -- tools / permissions ---------------------------------------------------


def test_tools_represented_in_capabilities(memory_manager):
    app = _app(memory_manager, responses=("ok",))
    caps = app._capabilities_section()
    assert "echo" in caps
    assert "current_time" in caps


def test_model_cannot_bypass_permissions(memory_manager):
    from asis.tools.executor import ToolExecutor
    from asis.tools.provided import EchoTool
    from asis.tools.registry import ToolRegistry
    from asis.tools.router import ToolRouter

    registry = ToolRegistry()
    registry.register(EchoTool())
    router = ToolRouter(
        registry=registry, executor=ToolExecutor(authorizer=lambda t: False)
    )
    app = _app(
        memory_manager,
        responses=('{"tool": "echo", "arguments": {"text": "x"}}', "denied-ok"),
        tools_router=router,
    )
    assert app.chat("echo x") == "denied-ok"


# -- thinking separation ---------------------------------------------------


def test_thinking_stripped_from_chat():
    from asis.ai.providers.ollama import strip_thinking

    visible, thinking = strip_thinking("<think>private plan</think>Hello")
    assert visible == "Hello"
    assert "private" in thinking
    visible2, _ = strip_thinking("plain answer")
    assert visible2 == "plain answer"


def test_thinking_stream_filter_hides_reasoning():
    from asis.ai.providers.ollama import _ThinkingStreamFilter

    filt = _ThinkingStreamFilter()
    assert filt.feed("<think>hid") == ""
    assert filt.feed("den</think>Hi") == "Hi"


# -- streaming / cancellation / CLI ----------------------------------------


def test_stream_chunks_visible_to_caller(memory_manager):
    app = _app(memory_manager, responses=("hello world",))
    chunks: list[str] = []
    out = app.chat_streamed("hi", on_chunk=chunks.append)
    assert out.strip() == "hello world"
    assert "".join(chunks).strip() == "hello world"


def test_engine_cancel_then_next_turn_recovers():
    coordinator = InterruptCoordinator()
    coordinator.register("inference")
    engine = InferenceEngine(
        manager=AIManager(provider=MockAIProvider(responses=("a", "b"))),
        assembler=ContextAssembler(identity=build_identity()),
        interrupts=coordinator,
    )
    coordinator.cancel("inference")
    try:
        engine.generate(ConversationSession().messages)
        raise AssertionError("must raise")
    except CancellationError:
        pass
    engine.reset_turn()  # loop turn boundary
    response = engine.generate(ConversationSession().messages)
    assert response.content == "a"


def test_cli_user_to_visible_response(memory_manager):
    from asis.cli.interactive.loop import run_interactive
    from asis.cli.interactive.renderer import TypingRenderer

    app = _app(memory_manager, responses=("Hi",))
    stream = io.StringIO()
    it = iter(['say exactly "Hi" back to me', "/exit"])
    code = run_interactive(
        app,
        input_fn=lambda p: next(it),
        renderer=TypingRenderer(stream=stream, char_delay=0),
        stream=stream,
    )
    assert code == 0
    assert "Hi" in stream.getvalue()


def test_multi_turn_memory_recall(memory_manager):
    app = _app(memory_manager, responses=("noted", "recall-check"))
    app.chat("My name is TestUser.")
    assert "TestUser" in memory_manager.search_context("what is my name?")
    # New turn with memory query pulls the fact into context.
    seen: dict = {}

    class Capturing(MockAIProvider):
        def chat(self, messages):
            seen["system"] = messages[0].content
            return AIResponse(
                content="Your name is TestUser.", model="m", provider="mock"
            )

    app2 = AssistantApp(
        identity=build_identity(),
        ai=AIManager(provider=Capturing()),
        memory=memory_manager,
    )
    out = app2.chat("What did I just tell you?")
    assert "TestUser" in seen["system"]
    assert "TestUser" in out


def test_default_model_is_qwen3_14b():
    assert defaults.AI_MODEL == "qwen3:14b"
