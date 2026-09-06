"""
Forza AI Voice System
Speech-to-Text transcription.

Uses Faster-Whisper with automatic language detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel


@dataclass(frozen=True)
class TranscriptionResult:
    """Result returned by the speech-to-text engine."""

    text: str
    language: Optional[str]
    language_probability: Optional[float]
    duration: float


class SpeechTranscriber:
    """Speech-to-text engine powered by Faster-Whisper."""

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        language: Optional[str] = None,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16_000,
    ) -> TranscriptionResult:
        """
        Transcribe a speech segment.

        If language is None, Faster-Whisper automatically detects
        the spoken language.
        """

        samples = np.asarray(
            audio,
            dtype=np.float32,
        ).flatten()

        if samples.size == 0:
            return TranscriptionResult(
                text="",
                language=None,
                language_probability=None,
                duration=0.0,
            )

        duration = samples.size / sample_rate

        segments, info = self.model.transcribe(
            samples,
            language=self.language,
            task="transcribe",
            beam_size=5,
            vad_filter=False,
        )

        text_parts: list[str] = []

        for segment in segments:
            text = segment.text.strip()

            if text:
                text_parts.append(text)

        text = " ".join(text_parts).strip()

        language = getattr(info, "language", None)
        language_probability = getattr(
            info,
            "language_probability",
            None,
        )

        return TranscriptionResult(
            text=text,
            language=language,
            language_probability=(
                float(language_probability)
                if language_probability is not None
                else None
            ),
            duration=duration,
        )