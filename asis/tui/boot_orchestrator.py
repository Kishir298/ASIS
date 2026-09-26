"""
Boot Orchestrator - Decoupled boot sequence with dependency injection.

This module provides a clean separation of concerns for the ASIS boot process,
allowing for easier testing and configuration of individual components.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

from asis.ai.manager import AIManager
from asis.ai.providers import AIProvider, MockAIProvider, OllamaProvider
from asis.app.assistant import AssistantApp
from asis.app.boot import BootError
from asis.app.modes import AssistantMode as AppAssistantMode
from asis.app.routers import build_default_tool_router
from asis.configuration import settings
from asis.events import EventBus
from asis.identity import build_identity
from asis.logging.logger import configure_logging
from asis.memory import MemoryManager, MemoryStorage, MemoryDatabase
from asis.voice.pipeline import VoicePipeline
from asis.voice.engines.mock import (
    MockAudioInput,
    MockAudioOutput,
    MockSpeakerIdentifier,
    MockSpeechRecognizer,
    MockTextToSpeech,
    MockVadDetector,
)

from asis.tui.state import AppState
from asis.tui.widgets import BootLogPanel


logger = logging.getLogger("asis.boot.orchestrator")


class IdentityProvider(Protocol):
    """Protocol for identity providers."""

    def build(self) -> Any:
        ...


class MemoryProvider(Protocol):
    """Protocol for memory providers."""

    def __init__(self, manager: MemoryManager) -> None:
        ...


class ToolRouterProvider(Protocol):
    """Protocol for tool router providers."""

    def build(self) -> Any:
        ...


class AIProviderFactory(Protocol):
    """Protocol for AI provider factories."""

    def create(self, settings_obj: Any) -> AIProvider:
        ...


class VoicePipelineFactory(Protocol):
    """Protocol for voice pipeline factories."""

    def create(self, event_bus: EventBus) -> VoicePipeline:
        ...


@dataclass
class BootComponents:
    """Container for all boot components."""

    identity: Any = None
    memory: MemoryManager | None = None
    tool_router: Any = None
    ai_provider: AIProvider | None = None
    ai_manager: AIManager | None = None
    assistant_app: AssistantApp | None = None
    voice_pipeline: VoicePipeline | None = None
    event_bus: EventBus | None = None


class BootOrchestrator:
    """
    Orchestrates the ASIS boot sequence with dependency injection.

    This class decouples the boot process from the TUI app, allowing
    for easier testing and configuration of individual components.
    """

    def __init__(
        self,
        state: AppState,
        event_bus: EventBus,
        boot_log_panel: BootLogPanel | None = None,
        # Dependency injection hooks
        identity_provider: IdentityProvider | None = None,
        memory_provider_factory: Callable[[], MemoryManager] | None = None,
        tool_router_provider: ToolRouterProvider | None = None,
        ai_provider_factory: AIProviderFactory | None = None,
        voice_pipeline_factory: VoicePipelineFactory | None = None,
    ) -> None:
        self.state = state
        self.event_bus = event_bus
        self.boot_log_panel = boot_log_panel
        self._components = BootComponents()

        # DI hooks (use defaults if not provided)
        self._identity_provider = identity_provider or DefaultIdentityProvider()
        self._memory_provider_factory = memory_provider_factory or self._default_memory_factory
        self._tool_router_provider = tool_router_provider or DefaultToolRouterProvider()
        self._ai_provider_factory = ai_provider_factory or DefaultAIProviderFactory()
        self._voice_pipeline_factory = voice_pipeline_factory or DefaultVoicePipelineFactory()

    def _add_boot_log(self, status: str, message: str) -> None:
        """Add a boot log entry."""
        self.state.add_boot_log(status, message)
        if self.boot_log_panel:
            self.boot_log_panel.refresh()
        logger.info("Boot: %s - %s", status, message)

    def _default_memory_factory(self) -> MemoryManager:
        """Default memory factory using SQLite."""
        db_path = settings.paths.memory / settings.memory.database_name
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return MemoryManager(MemoryStorage(MemoryDatabase(db_path)))

    async def run(self) -> BootComponents:
        """Run the complete boot sequence."""
        self._add_boot_log("BOOT", "Starting ASIS boot sequence...")

        # Step 1: Identity
        await self._boot_identity()

        # Step 2: Memory
        await self._boot_memory()

        # Step 3: Tool Router
        await self._boot_tool_router()

        # Step 4: AI Provider
        await self._boot_ai_provider()

        # Step 5: Model Verification
        await self._verify_model()

        # Step 6: AI Manager
        await self._boot_ai_manager()

        # Step 7: Assistant App
        await self._boot_assistant_app()

        # Step 8: Voice Pipeline
        await self._boot_voice_pipeline()

        self._add_boot_log("OK", "A.S.I.S. ready.")
        return self._components

    async def _boot_identity(self) -> None:
        """Boot identity system."""
        try:
            identity = self._identity_provider.build()
            self._components.identity = identity
            self._add_boot_log("OK", "Identity loaded")
        except Exception as exc:
            self._add_boot_log("FAIL", f"Identity failed: {exc}")
            raise BootError(f"Identity boot failed: {exc}") from exc

    async def _boot_memory(self) -> None:
        """Boot memory system."""
        try:
            memory = self._memory_provider_factory()
            self._components.memory = memory
            self.state.memory_ready = True
            self._add_boot_log("OK", "Memory initialized")
        except Exception as exc:
            self._add_boot_log("FAIL", f"Memory failed: {exc}")
            raise BootError(f"Memory boot failed: {exc}") from exc

    async def _boot_tool_router(self) -> None:
        """Boot tool router."""
        try:
            tool_router = self._tool_router_provider.build()
            ensure_all_tools = __import__("asis.app.routers", fromlist=["ensure_all_tools"]).ensure_all_tools
            ensure_all_tools(tool_router, None)
            self._components.tool_router = tool_router
            self.state.tools_ready = True
            self._add_boot_log("OK", "Tools initialized")
        except Exception as exc:
            self._add_boot_log("FAIL", f"Tools failed: {exc}")
            raise BootError(f"Tool router boot failed: {exc}") from exc

    async def _boot_ai_provider(self) -> None:
        """Boot AI provider."""
        try:
            provider_name = settings.ai.provider
            if provider_name == "ollama":
                provider = OllamaProvider(
                    model=settings.ai.model,
                    host=settings.ai.endpoint,
                    timeout=settings.ai.request_timeout,
                    temperature=settings.ai.temperature,
                    retries=settings.network.retries,
                )
                self._add_boot_log("BOOT", "Connecting to Ollama...")

                # Check availability
                available = False
                try:
                    avail_fn = getattr(provider, "available", None)
                    if callable(avail_fn):
                        try:
                            available = avail_fn(timeout=5.0)
                        except TypeError:
                            available = avail_fn()
                except Exception:
                    available = False

                if available:
                    self.state.ollama_online = True
                    self._add_boot_log("OK", "Ollama ready")
                else:
                    self._add_boot_log("FAIL", "Ollama server not reachable")
                    provider = MockAIProvider(model=settings.ai.model)

                self.state.model_name = settings.ai.model
            else:
                provider = MockAIProvider(model=settings.ai.model)
                self.state.model_name = settings.ai.model

            self._components.ai_provider = provider
        except Exception as exc:
            self._add_boot_log("FAIL", f"AI provider failed: {exc}")
            raise BootError(f"AI provider boot failed: {exc}") from exc

    async def _verify_model(self) -> None:
        """Verify model readiness."""
        self._add_boot_log("BOOT", "Verifying model...")
        try:
            from asis.ai.models import AIMessage, MessageRole
            provider = self._components.ai_provider
            if not provider:
                raise BootError("AI provider not initialized")

            messages = [AIMessage(role=MessageRole.USER, content="hello")]
            response = provider.chat(messages)
            content = getattr(response, "content", "")
            text = content if isinstance(content, str) else str(content or "")

            if text.strip():
                self.state.model_ready = True
                self._add_boot_log("OK", "Model ready")
            else:
                raise BootError("Model readiness probe returned empty response")
        except Exception as exc:
            self._add_boot_log("FAIL", f"Model readiness check failed: {exc}")
            # Use mock as fallback
            self._components.ai_provider = MockAIProvider(model=settings.ai.model)
            self.state.model_ready = True
            self._add_boot_log("OK", "Model ready (mock fallback)")

    async def _boot_ai_manager(self) -> None:
        """Boot AI manager."""
        try:
            provider = self._components.ai_provider
            if not provider:
                raise BootError("AI provider not initialized")

            ai = AIManager(provider=provider, event_bus=self.event_bus)
            self._components.ai_manager = ai
            self._add_boot_log("OK", "AI Manager initialized")
        except Exception as exc:
            self._add_boot_log("FAIL", f"AI Manager failed: {exc}")
            raise BootError(f"AI Manager boot failed: {exc}") from exc

    async def _boot_assistant_app(self) -> None:
        """Boot assistant app."""
        try:
            identity = self._components.identity
            ai = self._components.ai_manager
            memory = self._components.memory
            tool_router = self._components.tool_router

            if not all([identity, ai, memory, tool_router]):
                raise BootError("Missing required components for AssistantApp")

            assistant_app = AssistantApp(
                identity=identity,
                ai=ai,
                memory=memory,
                tools_router=tool_router,
                event_bus=self.event_bus,
                mode=AppAssistantMode.GENERAL,
            )

            self._components.assistant_app = assistant_app
            self._add_boot_log("OK", "Assistant App initialized")
        except Exception as exc:
            self._add_boot_log("FAIL", f"Assistant App failed: {exc}")
            raise BootError(f"Assistant App boot failed: {exc}") from exc

    async def _boot_voice_pipeline(self) -> None:
        """Boot voice pipeline (mock for now)."""
        try:
            voice_pipeline = self._voice_pipeline_factory.create(self.event_bus)
            self._components.voice_pipeline = voice_pipeline
            self.state.voice_state = "READY"
            self._add_boot_log("OK", "Voice pipeline initialized")
        except Exception as exc:
            self.state.voice_state = "ERROR"
            self._add_boot_log("WARN", f"Voice pipeline unavailable: {exc}")


# Default implementations for DI hooks

class DefaultIdentityProvider:
    """Default identity provider using the built-in build_identity."""

    def build(self) -> Any:
        return build_identity()


class DefaultToolRouterProvider:
    """Default tool router provider."""

    def build(self) -> Any:
        return build_default_tool_router()


class DefaultAIProviderFactory:
    """Default AI provider factory."""

    def create(self, settings_obj: Any) -> AIProvider:
        provider_name = settings.ai.provider
        if provider_name == "ollama":
            return OllamaProvider(
                model=settings.ai.model,
                host=settings.ai.endpoint,
                timeout=settings.ai.request_timeout,
                temperature=settings.ai.temperature,
                retries=settings.network.retries,
            )
        return MockAIProvider(model=settings.ai.model)


class DefaultVoicePipelineFactory:
    """Default voice pipeline factory (mock)."""

    def create(self, event_bus: EventBus) -> VoicePipeline:
        return VoicePipeline(
            audio_input=MockAudioInput([]),
            speech_recognizer=MockSpeechRecognizer(),
            speaker_identifier=MockSpeakerIdentifier(),
            tts=MockTextToSpeech(),
            audio_output=MockAudioOutput(),
            event_bus=event_bus,
            vad=MockVadDetector(),
        )


# Backward compatibility function
async def run_boot_sequence_legacy(
    state: AppState,
    event_bus: EventBus,
    boot_log_panel: BootLogPanel | None = None,
) -> dict[str, Any]:
    """
    Legacy compatibility wrapper for the old boot sequence.

    This function maintains backward compatibility with the existing
    TUI app code while using the new BootOrchestrator internally.
    """
    orchestrator = BootOrchestrator(
        state=state,
        event_bus=event_bus,
        boot_log_panel=boot_log_panel,
    )
    components = await orchestrator.run()
    return {
        "identity": components.identity,
        "memory": components.memory,
        "tool_router": components.tool_router,
        "ai_provider": components.ai_provider,
        "ai_manager": components.ai_manager,
        "assistant_app": components.assistant_app,
        "voice_pipeline": components.voice_pipeline,
        "event_bus": components.event_bus,
    }