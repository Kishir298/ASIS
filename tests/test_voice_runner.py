"""VoiceRunner: STT -> AssistantApp -> TTS, same Router path as text."""

from __future__ import annotations

from asis.ai import (
    AIManager,
    ContextAssembler,
    ConversationSession,
    InferenceEngine,
)
from asis.ai.providers import MockAIProvider
from asis.app import AssistantApp
from asis.identity import build_identity
from asis.integrations.core.connection import CoreConnectionManager
from asis.integrations.core.mock import MockCoreAdapter
from asis.system.context import RuntimeContext
from asis.tools.executor import ToolExecutor
from asis.tools.provided import register_core_tools
from asis.tools.registry import ToolRegistry
from asis.tools.router import ToolRouter
from asis.voice import (
    MockAudioInput,
    MockAudioOutput,
    MockSpeakerIdentifier,
    MockSpeechRecognizer,
    MockTextToSpeech,
    VoicePipeline,
    VoiceRunner,
)
from asis.voice.models import AudioData


def _pipeline(transcript="hello voice"):
    return VoicePipeline(
        MockAudioInput([AudioData(samples=[0], sample_rate=16000)]),
        MockSpeechRecognizer(text=transcript),
        MockSpeakerIdentifier(),
        MockTextToSpeech(),
        MockAudioOutput(),
    )


def _app(responses=("hi via voice",), core=None, router=None):
    return AssistantApp(
        session=ConversationSession(),
        engine=InferenceEngine(
            AIManager(provider=MockAIProvider(responses=list(responses))),
            ContextAssembler(build_identity()),
        ),
        router=router,
        core=core,
    )


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


def test_voice_roundtrip_speaks_local_reply():
    pipe = _pipeline()
    result = VoiceRunner(pipe, _app()).run_once()
    assert result.assistant_text == "hi via voice"
    assert pipe.tts.synthesized == ["hi via voice"]


def test_voice_core_intent_reaches_same_tool():
    manager, router = _online_stack()
    ctx = RuntimeContext()
    manager.start(ctx)
    try:
        pipe = _pipeline("core:devices")
        result = VoiceRunner(pipe, _app(core=manager, router=router)).run_once()
        assert any("core_discover_devices: ok" in m for m in result.system_messages)
        assert "core_discover_devices: ok" in pipe.tts.synthesized[0]
    finally:
        manager.stop(ctx)


def test_voice_core_failure_is_spoken_safe():
    manager, router = _online_stack()  # offline
    pipe = _pipeline("core:devices")
    result = VoiceRunner(pipe, _app(core=manager, router=router)).run_once()
    assert any("CORE_UNAVAILABLE" in m for m in result.system_messages)
    assert "CORE_UNAVAILABLE" in pipe.tts.synthesized[0]


def test_voice_empty_transcript_says_nothing():
    pipe = _pipeline("")
    result = VoiceRunner(pipe, _app()).run_once()
    assert result.assistant_text == ""
    assert pipe.tts.synthesized == []


def test_voice_has_no_core_imports():
    import pathlib

    text = (pathlib.Path(__file__).resolve().parents[1] / "asis" / "voice" / "runner.py").read_text()
    assert "core_device_client" not in text
    assert "from core." not in text
    assert "socket" not in text
