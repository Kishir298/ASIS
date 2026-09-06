"""
Forza AI Voice System
Voice Activity Detection.

Uses Silero VAD for cross-platform speech detection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import torch
from silero_vad import load_silero_vad


class VoiceActivityDetector:
    """Detect human speech using Silero VAD."""

    SUPPORTED_SAMPLE_RATES = {8_000, 16_000}

    FRAME_SIZES = {
        8_000: 256,
        16_000: 512,
    }

    def __init__(
        self,
        sample_rate: int = 16_000,
        threshold: float = 0.5,
        model_path: Optional[str | Path] = None,
    ) -> None:
        if sample_rate not in self.SUPPORTED_SAMPLE_RATES:
            raise ValueError(
                f"Unsupported sample rate: {sample_rate}. "
                "Use 8000 or 16000 Hz."
            )

        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0.")

        self.sample_rate = sample_rate
        self.threshold = threshold
        self.frame_size = self.FRAME_SIZES[sample_rate]

        self.device = torch.device("cpu")

        if model_path is not None:
            self.model = load_silero_vad(
                model_path=str(model_path)
            )
        else:
            self.model = load_silero_vad()

        self.model.to(self.device)
        self.model.eval()

    def speech_probability(self, audio: np.ndarray) -> float:
        """
        Return the highest speech probability found in the audio.

        The input can contain any number of samples. Audio is
        automatically split into Silero-compatible frames.

        Args:
            audio:
                Mono float32 audio in the range [-1.0, 1.0].

        Returns:
            Highest speech probability from 0.0 to 1.0.
        """

        samples = self._prepare_audio(audio)

        if samples.size == 0:
            return 0.0

        probabilities: list[float] = []

        for start in range(0, samples.size, self.frame_size):
            frame = samples[start:start + self.frame_size]

            if frame.size < self.frame_size:
                break

            tensor = torch.from_numpy(frame).to(self.device)

            with torch.no_grad():
                probability = self.model(
                    tensor,
                    self.sample_rate,
                ).item()

            probabilities.append(float(probability))

        if not probabilities:
            return 0.0

        return max(probabilities)

    def is_speech(self, audio: np.ndarray) -> bool:
        """
        Determine whether speech exists in the supplied audio.

        Args:
            audio:
                Mono float32 audio.

        Returns:
            True if any valid frame reaches the configured threshold.
        """

        return self.speech_probability(audio) >= self.threshold

    def reset(self) -> None:
        """Reset the VAD model's internal state."""

        if hasattr(self.model, "reset_states"):
            self.model.reset_states()

    @staticmethod
    def _prepare_audio(audio: np.ndarray) -> np.ndarray:
        """Normalize incoming audio."""

        samples = np.asarray(
            audio,
            dtype=np.float32,
        ).flatten()

        if samples.size == 0:
            return samples

        return np.clip(samples, -1.0, 1.0)