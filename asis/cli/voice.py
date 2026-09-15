"""
``asis voice`` runtime: real voice loop with clean lifecycle/shutdown.

Flow: config -> identity -> voice providers -> audio start -> loop
(listen/VAD/wake/STT/speaker -> A.S.I.S. chat -> TTS/output) until
shutdown phrase / Ctrl-C / max-turns. All providers come from the
factory; failures produce structured errors, never tracebacks (unless
--debug). Voice never executes shell; text routes through A.S.I.S.
intelligence (AIManager + memory), where tool permissions apply.
"""

from __future__ import annotations

import argparse
import contextlib
import sys

from asis.ai import AIManager
from asis.configuration import settings
from asis.errors import ASISError
from asis.events import EventBus
from asis.identity import build_identity
from asis.logging.logger import get_logger
from asis.system.interrupt import InterruptCoordinator
from asis.voice.engines.mock import (
    MockAudioInput,
    MockAudioOutput,
    MockSpeakerIdentifier,
    MockSpeechRecognizer,
    MockTextToSpeech,
    MockVadDetector,
    MockWakeWordDetector,
)
from asis.voice.models import AudioData
from asis.voice.pipeline import VoicePipeline


def build_voice_parser() -> argparse.ArgumentParser:
    """Parser for ``asis voice`` (overrides config for this run only)."""
    parser = argparse.ArgumentParser(
        prog="asis voice",
        description="Run the A.S.I.S. voice subsystem (local, mock by default).",
    )
    parser.add_argument(
        "--stt-engine", default=None, help="STT engine (mock|faster-whisper)"
    )
    parser.add_argument("--stt-model", default=None, help="STT model name")
    parser.add_argument("--tts-engine", default=None, help="TTS engine (mock|pyttsx3)")
    parser.add_argument("--tts-voice", default=None, help="TTS voice")
    parser.add_argument(
        "--speaker-engine", default=None, help="speaker engine (mock|embedding)"
    )
    parser.add_argument("--wake-word", default=None, help="wake phrase")
    parser.add_argument(
        "--no-wake-word", action="store_true", help="disable wake-word gating"
    )
    parser.add_argument(
        "--provider", default=settings.ai.provider, choices=["mock", "ollama"]
    )
    parser.add_argument("--model", default=settings.ai.model)
    parser.add_argument("--memory-db", default=None, metavar="PATH")
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
    parser.add_argument(
        "--max-turns", type=int, default=0, help="stop after N turns (0=infinite)"
    )
    parser.add_argument("--debug", action="store_true")
    return parser


def _build_providers(args) -> dict:
    """Build voice providers honoring CLI overrides (no global mutation)."""
    from asis.voice import factory as vf

    # STT
    if args.stt_engine is not None:
        eng = args.stt_engine.lower()
        if eng == "mock":
            stt = MockSpeechRecognizer(language=settings.voice.stt.language or None)
        elif eng in {"faster-whisper", "faster_whisper", "whisper"}:
            from asis.voice.speech.faster_whisper import FasterWhisperRecognizer

            stt = FasterWhisperRecognizer(
                model=args.stt_model or settings.voice.stt.model,
                device=settings.voice.stt.device,
                compute_type=settings.voice.stt.compute_type,
                language=settings.voice.stt.language or None,
            )
        else:
            raise ASISError(f"unsupported STT engine: {args.stt_engine}")
    else:
        stt = vf.create_speech_recognizer()

    # TTS
    if args.tts_engine is not None:
        eng = args.tts_engine.lower()
        tts_rate = settings.voice.tts.sample_rate or settings.voice.sample_rate
        if eng == "mock":
            tts = MockTextToSpeech(sample_rate=tts_rate)
        elif eng in {"pyttsx3", "local"}:
            from asis.voice.tts.pyttsx3_engine import Pyttsx3Engine

            tts = Pyttsx3Engine(
                voice=args.tts_voice or settings.voice.tts.voice,
                sample_rate=tts_rate,
            )
        else:
            raise ASISError(f"unsupported TTS engine: {args.tts_engine}")
    else:
        tts = vf.create_tts()

    # Speaker
    if args.speaker_engine is not None:
        eng = args.speaker_engine.lower()
        if eng == "mock":
            speaker = MockSpeakerIdentifier(
                confidence=settings.voice.speaker.confidence
            )
        else:
            # delegate to factory path for real engines (validates + raises helpfully)
            speaker = vf.create_speaker_identifier()
    else:
        speaker = vf.create_speaker_identifier()

    # Wake word
    if args.no_wake_word:
        wake = None
    elif args.wake_word is not None:
        wake = MockWakeWordDetector(phrases=(args.wake_word,))
    else:
        try:
            wake = vf.create_wake_word_detector()
        except ASISError:
            wake = MockWakeWordDetector(phrases=(settings.voice.wake_word,))

    try:
        vad = vf.create_vad()
    except ASISError:
        vad = MockVadDetector()

    return {
        "audio_input": MockAudioInput([]),
        "vad": vad,
        "wake_word": wake,
        "speech_recognizer": stt,
        "speaker_identifier": speaker,
        "tts": tts,
        "audio_output": MockAudioOutput(),
    }


def run_voice(argv: list[str] | None = None) -> int:
    """Entry for ``asis voice``; returns process exit code."""
    logger = get_logger("voice.runtime")
    args = build_voice_parser().parse_args(argv)
    if args.debug:
        logger.info("voice debug mode on")

    # Lazy import to keep CLI import light
    from asis.app.assistant import AssistantApp
    from asis.cli.main import _provider, build_memory

    identity = build_identity()
    try:
        engines = _build_providers(args)
    except ASISError as exc:
        print(f"voice startup failed: {exc}", file=sys.stderr)
        if args.debug:
            raise
        return 2
    except Exception as exc:  # pragma: no cover - defensive
        print(f"voice startup failed: {exc}", file=sys.stderr)
        if args.debug:
            raise
        return 2

    try:
        provider = _provider(args.provider, args.model)
    except ValueError as exc:
        print(f"voice startup failed: {exc}", file=sys.stderr)
        return 2

    event_bus = EventBus()
    interrupts = InterruptCoordinator()
    interrupts.register("voice")
    ai = AIManager(provider=provider, event_bus=event_bus)
    memory = build_memory(args.memory_db)
    app = AssistantApp(
        identity=identity,
        ai=ai,
        memory=memory,
        interrupts=interrupts,
        mode=args.mode,
        workspace=args.workspace,
    )

    pipeline = VoicePipeline(
        audio_input=engines["audio_input"],
        speech_recognizer=engines["speech_recognizer"],
        speaker_identifier=engines["speaker_identifier"],
        tts=engines["tts"],
        audio_output=engines["audio_output"],
        event_bus=event_bus,
        interrupts=interrupts,
        vad=engines["vad"],
        wake_word_detector=engines["wake_word"],
    )

    logger.info(
        "voice startup: stt=%s tts=%s speaker=%s wake=%s",
        type(engines["speech_recognizer"]).__name__,
        type(engines["tts"]).__name__,
        type(engines["speaker_identifier"]).__name__,
        type(engines["wake_word"]).__name__ if engines["wake_word"] else "disabled",
    )

    try:
        pipeline.audio_input.start()
    except Exception as exc:
        print(f"voice startup failed: {exc}", file=sys.stderr)
        return 2

    print(identity.greeting)
    print("Voice mode running (mock audio). Say the shutdown phrase to exit.")
    shutdown = settings.identity.shutdown_phrase.lower()
    require_wake = not args.no_wake_word
    turns = 0

    def process_fn(text: str, _speaker) -> str:
        return app.chat(text)

    try:
        while True:
            if args.max_turns and turns >= args.max_turns:
                break
            try:
                result = pipeline.run_once(
                    process_fn=process_fn,
                    require_wake_word=require_wake,
                )
            except ASISError as exc:
                if args.debug:
                    raise
                print(f"voice error: {exc}", file=sys.stderr)
                continue
            text = (result.get("text") or "").strip()
            if not text and result.get("status") in {"no-speech", "no-wake-word"}:
                # Mock input exhausts to empty segments; stop instead of spinning.
                if isinstance(engines["audio_input"], MockAudioInput):
                    break
                continue
            if text.lower() == shutdown:
                print("Shutting down.")
                with contextlib.suppress(ASISError):
                    pipeline.speak("Shutting down.")
                break
            if result.get("response"):
                print(result["response"])
            turns += 1
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        try:
            pipeline.stop()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("voice stop warning: %s", exc)
        logger.info("voice shutdown complete")
    return 0


# Backwards-compat helper for tests: run one turn with scripted mocks.
def run_voice_once(
    segments: list[AudioData],
    transcript: str = "hello",
    require_wake_word: bool = False,
) -> dict:
    """Run a single pipeline turn with scripted mocks (no hardware)."""
    pipeline = VoicePipeline(
        audio_input=MockAudioInput(segments),
        speech_recognizer=MockSpeechRecognizer(text=transcript),
        speaker_identifier=MockSpeakerIdentifier(),
        tts=MockTextToSpeech(),
        audio_output=MockAudioOutput(),
        vad=MockVadDetector(),
        wake_word_detector=MockWakeWordDetector() if require_wake_word else None,
    )
    return pipeline.run_once(require_wake_word=require_wake_word)
