"""AssistantApp: shared text path (local inference + CORE intents)."""

from __future__ import annotations

from asis.ai import (
    AIManager,
    ContextAssembler,
    ConversationSession,
    InferenceEngine,
)
from asis.ai.providers import MockAIProvider
from asis.app import AssistantApp, parse_core_intent
from asis.identity import build_identity
from asis.integrations.core.connection import CoreConnectionManager
from asis.integrations.core.mock import MockCoreAdapter
from asis.system.context import RuntimeContext
from asis.tools.executor import ToolExecutor
from asis.tools.provided import register_core_tools
from asis.tools.registry import ToolRegistry
from asis.tools.router import ToolRouter


def _app(responses=("hello local",), core=None, router=None):
    session = ConversationSession()
    engine = InferenceEngine(
        AIManager(provider=MockAIProvider(responses=list(responses))),
        ContextAssembler(build_identity()),
    )
    return AssistantApp(session=session, engine=engine, router=router, core=core)


def _online_stack():
    mock = MockCoreAdapter()
    manager = CoreConnectionManager(
        mock, enabled=True, credential_provider=lambda: "cred",
        reconnect_enabled=False,
    )
    registry = ToolRegistry()
    register_core_tools(registry, manager)
    router = ToolRouter(registry, ToolExecutor(authorizer=lambda tool: True))
    return manager, router


def test_local_reply_and_history():
    app = _app()
    result = app.handle_text("hi there")
    assert result.assistant_text == "hello local"
    assert result.stopped is False
    assert len(app.session) == 2  # user + assistant


def test_empty_and_shutdown():
    app = _app()
    assert app.handle_text("   ").assistant_text == ""
    stopped = app.handle_text("asis shutdown")
    assert stopped.stopped is True


def test_inference_failure_is_safe():
    session = ConversationSession()
    engine = InferenceEngine(
        AIManager(provider=MockAIProvider(fail=True)),
        ContextAssembler(build_identity()),
    )
    app = AssistantApp(session=session, engine=engine)
    result = app.handle_text("hello")
    assert result.assistant_text == ""
    assert any("Local inference failed" in m for m in result.system_messages)


def test_core_intent_offline_reports_unavailable():
    manager, router = _online_stack()  # never started -> offline
    app = _app(core=manager, router=router)
    result = app.handle_text("core:devices")
    assert result.assistant_text == "hello local"  # local LLM still answered
    assert any("CORE_UNAVAILABLE" in m for m in result.system_messages)


def test_core_intent_online_runs_tool():
    manager, router = _online_stack()
    ctx = RuntimeContext()
    manager.start(ctx)
    try:
        app = _app(core=manager, router=router)
        result = app.handle_text("core:devices")
        assert any("core_discover_devices: ok" in m for m in result.system_messages)
        info = app.handle_text("core:device mac-01")
        assert any("core_device_info" in m for m in info.system_messages)
    finally:
        manager.stop(ctx)


def test_parse_core_intent_matrix():
    assert parse_core_intent("hello") is None
    assert parse_core_intent("core:") is None
    assert parse_core_intent("core:bogus") is None
    assert parse_core_intent("core:device") is None  # missing id
    assert parse_core_intent("core:devices").tool_name == "core_discover_devices"
    assert parse_core_intent("core:status").tool_name == "core_status"
    assert parse_core_intent("core:device mac-01").kwargs == {"device_id": "mac-01"}
    svc = parse_core_intent("core:service health status")
    assert svc.tool_name == "core_service_request"
    assert parse_core_intent("core:agent status").tool_name == "core_agent_request"
    data = parse_core_intent("core:data record_list")
    assert data.tool_name == "core_data_request"
    send = parse_core_intent("core:send mac-02 APP_PING hello")
    assert send.tool_name == "core_send_to_device"
    assert send.kwargs["device_id"] == "mac-02"


def test_core_status_text_offline_and_disabled():
    assert "disabled" in _app().core_status_text()
    manager, _ = _online_stack()
    app = _app(core=manager)
    assert "disconnected" in app.core_status_text()


def test_memory_failure_does_not_break_reply(memory_manager):
    app = _app()
    app.memory = None
    assert app.handle_text("my name is Ada").assistant_text == "hello local"
