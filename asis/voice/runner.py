"""
Voice runner for A.S.I.S.

Thin loop over the existing VoicePipeline and AssistantApp — the ONLY
voice→assistant path. There is deliberately no voice-specific CORE
networking: transcripts flow through ``AssistantApp.handle_text``, so
voice inherits the same ToolRouter/CORE-tool/local-LLM behavior as text.
"""

from __future__ import annotations

from asis.app.result import ProcessResult
from asis.logging.logger import get_logger

from .pipeline import VoicePipeline


class VoiceRunner:
    """Drive one listen → think → speak cycle at a time."""

    name = "voice-runner"

    def __init__(self, pipeline: VoicePipeline, app) -> None:
        self._logger = get_logger("voice.runner")
        self.pipeline = pipeline
        self.app = app

    def run_once(self) -> ProcessResult:
        """Capture, transcribe, handle via AssistantApp, and speak.

        Never raises: STT/app/TTS failures become system messages, and a
        CORE failure surfaces as a spoken-safe notice inside the result.
        """
        try:
            transcript = self.pipeline.listen_and_transcribe().text.strip()
        except Exception as exc:
            self._logger.exception("Voice capture/transcription failed.")
            return ProcessResult(
                assistant_text="",
                system_messages=[f"Voice input failed: {exc}"],
            )
        if not transcript:
            return ProcessResult(assistant_text="")

        try:
            result = self.app.handle_text(transcript)
        except Exception as exc:  # defensive: app contract is never-raise
            self._logger.exception("AssistantApp failed on voice transcript.")
            result = ProcessResult(
                assistant_text="",
                system_messages=[f"Assistant failed: {exc}"],
            )

        spoken_parts = [result.assistant_text, *result.system_messages]
        spoken = " ".join(part for part in spoken_parts if part).strip()
        if spoken:
            try:
                self.pipeline.speak(spoken)
            except Exception as exc:
                self._logger.exception("Voice output failed.")
                result.system_messages.append(f"Voice output failed: {exc}")
        return result
