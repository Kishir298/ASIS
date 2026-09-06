"""
Forza AI Voice System
Microphone input interface.

Cross-platform microphone discovery and audio capture.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd


@dataclass(frozen=True)
class MicrophoneConfig:
    """Configuration for microphone capture."""

    sample_rate: int = 16_000
    channels: int = 1
    block_size: int = 1_024
    dtype: str = "float32"
    device: Optional[int] = None


class Microphone:
    """Cross-platform microphone interface."""

    def __init__(
        self,
        config: Optional[MicrophoneConfig] = None,
    ) -> None:
        self.config = config or MicrophoneConfig()
        self._stream: Optional[sd.InputStream] = None

    @staticmethod
    def list_devices() -> list[dict]:
        """
        Return available input devices.

        Returns:
            List of dictionaries containing device information.
        """

        devices = sd.query_devices()

        return [
            {
                "index": index,
                "name": device["name"],
                "input_channels": device["max_input_channels"],
                "sample_rate": device["default_samplerate"],
            }
            for index, device in enumerate(devices)
            if device["max_input_channels"] > 0
        ]

    @property
    def is_running(self) -> bool:
        """Return whether the microphone stream is active."""

        return self._stream is not None and self._stream.active

    def start(self) -> None:
        """Start microphone capture."""

        if self.is_running:
            return

        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            blocksize=self.config.block_size,
            dtype=self.config.dtype,
            device=self.config.device,
        )

        self._stream.start()

    def read(self, frames: Optional[int] = None) -> np.ndarray:
        """
        Read audio frames.

        Args:
            frames: Number of frames to read.

        Returns:
            NumPy array containing audio samples.

        Raises:
            RuntimeError: If the microphone is not running.
        """

        if not self.is_running:
            raise RuntimeError("Microphone is not running.")

        frame_count = frames or self.config.block_size

        audio, _overflowed = self._stream.read(frame_count)

        return np.asarray(audio, dtype=np.float32)

    def stop(self) -> None:
        """Stop microphone capture and release resources."""

        if self._stream is None:
            return

        try:
            self._stream.stop()
        finally:
            self._stream.close()
            self._stream = None

    def __enter__(self) -> "Microphone":
        self.start()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.stop()