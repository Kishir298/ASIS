"""
Forza AI Voice System
Audio buffering.

Provides a thread-safe buffer for microphone audio.
"""

from __future__ import annotations

from collections import deque
from threading import Lock

import numpy as np


class AudioBuffer:
    """Thread-safe audio sample buffer."""

    def __init__(
        self,
        max_seconds: float = 30.0,
        sample_rate: int = 16_000,
    ) -> None:
        if max_seconds <= 0:
            raise ValueError("max_seconds must be greater than zero.")

        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than zero.")

        self.sample_rate = sample_rate
        self.max_samples = int(max_seconds * sample_rate)

        self._buffer: deque[np.ndarray] = deque()
        self._sample_count = 0
        self._lock = Lock()

    @property
    def sample_count(self) -> int:
        """Return the number of samples currently buffered."""

        with self._lock:
            return self._sample_count

    @property
    def duration_seconds(self) -> float:
        """Return the buffered audio duration in seconds."""

        return self.sample_count / self.sample_rate

    def write(self, audio: np.ndarray) -> None:
        """
        Add audio samples to the buffer.

        Args:
            audio: Audio samples as a NumPy array.
        """

        samples = np.asarray(audio, dtype=np.float32).flatten()

        if samples.size == 0:
            return

        with self._lock:
            self._buffer.append(samples)
            self._sample_count += samples.size

            while self._sample_count > self.max_samples:
                oldest = self._buffer.popleft()
                self._sample_count -= oldest.size

    def read(self, seconds: float | None = None) -> np.ndarray:
        """
        Read buffered audio without removing it.

        Args:
            seconds: Optional amount of audio to return.
                     If omitted, returns everything.

        Returns:
            Copy of the requested audio samples.
        """

        with self._lock:
            if not self._buffer:
                return np.empty(0, dtype=np.float32)

            audio = np.concatenate(tuple(self._buffer))

        if seconds is None:
            return audio

        if seconds <= 0:
            raise ValueError("seconds must be greater than zero.")

        sample_count = min(
            int(seconds * self.sample_rate),
            audio.size,
        )

        return audio[-sample_count:].copy()

    def consume(self, seconds: float | None = None) -> np.ndarray:
        """
        Read and remove audio from the buffer.

        Args:
            seconds: Optional amount of audio to consume.
                     If omitted, consumes everything.

        Returns:
            Consumed audio samples.
        """

        with self._lock:
            if not self._buffer:
                return np.empty(0, dtype=np.float32)

            audio = np.concatenate(tuple(self._buffer))

            if seconds is None:
                self.clear()
                return audio

            if seconds <= 0:
                raise ValueError("seconds must be greater than zero.")

            sample_count = min(
                int(seconds * self.sample_rate),
                audio.size,
            )

            result = audio[-sample_count:].copy()

            remaining = audio[:-sample_count]

            self.clear()

            if remaining.size:
                self._buffer.append(remaining)
                self._sample_count = remaining.size

            return result

    def clear(self) -> None:
        """Remove all buffered audio."""

        with self._lock:
            self._buffer.clear()
            self._sample_count = 0