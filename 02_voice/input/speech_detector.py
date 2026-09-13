"""
Forza AI Voice System
Real-time speech segment detection.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from input.microphone import Microphone
from input.vad import VoiceActivityDetector


@dataclass
class SpeechSegment:
    """A completed segment of detected speech."""

    audio: np.ndarray
    sample_rate: int
    duration: float


class SpeechDetector:
    """
    Detect complete speech segments from a live microphone.

    The detector waits for speech to begin, records it, and
    finishes the segment after enough consecutive silence.
    """

    def __init__(
        self,
        microphone: Microphone,
        vad: VoiceActivityDetector,
        silence_duration: float = 0.8,
        minimum_duration: float = 0.15,
        maximum_duration: float = 30.0,
    ) -> None:
        if silence_duration <= 0:
            raise ValueError("silence_duration must be greater than zero.")

        if minimum_duration <= 0:
            raise ValueError("minimum_duration must be greater than zero.")

        if maximum_duration <= minimum_duration:
            raise ValueError("maximum_duration must be greater than minimum_duration.")

        self.microphone = microphone
        self.vad = vad

        self.silence_duration = silence_duration
        self.minimum_duration = minimum_duration
        self.maximum_duration = maximum_duration

        self.sample_rate = microphone.config.sample_rate
        self.frame_size = vad.frame_size

    def listen(
        self,
        on_speech: Callable[[SpeechSegment], None] | None = None,
        stop_event=None,
    ) -> None:
        """
        Continuously listen for speech.

        Args:
            on_speech:
                Optional callback called whenever a complete speech
                segment is detected.

            stop_event:
                Optional threading.Event used to stop listening.
        """

        if not self.microphone.is_running:
            self.microphone.start()

        speech_audio: list[np.ndarray] = []

        speaking = False
        speech_start_time: float | None = None
        last_speech_time: float | None = None

        try:
            while True:
                if stop_event is not None and stop_event.is_set():
                    break

                frame = self.microphone.read(self.frame_size)

                if frame.size != self.frame_size:
                    continue

                is_speech = self.vad.is_speech(frame)

                now = time.monotonic()

                if is_speech:
                    if not speaking:
                        speaking = True
                        speech_start_time = now
                        speech_audio = []

                    last_speech_time = now
                    speech_audio.append(frame.copy())

                    if (
                        speech_start_time is not None
                        and now - speech_start_time >= self.maximum_duration
                    ):
                        segment = self._create_segment(speech_audio)

                        self._emit(segment, on_speech)

                        speech_audio = []
                        speaking = False
                        speech_start_time = None
                        last_speech_time = None

                elif speaking:
                    speech_audio.append(frame.copy())

                    if (
                        last_speech_time is not None
                        and now - last_speech_time >= self.silence_duration
                    ):
                        segment = self._create_segment(speech_audio)

                        if segment.duration >= self.minimum_duration:
                            self._emit(segment, on_speech)

                        speech_audio = []
                        speaking = False
                        speech_start_time = None
                        last_speech_time = None

        finally:
            self.microphone.stop()

    def _create_segment(
        self,
        frames: list[np.ndarray],
    ) -> SpeechSegment:
        """Combine audio frames into a speech segment."""

        if not frames:
            audio = np.empty(0, dtype=np.float32)
        else:
            audio = np.concatenate(frames).astype(
                np.float32,
                copy=False,
            )

        duration = audio.size / self.sample_rate

        return SpeechSegment(
            audio=audio,
            sample_rate=self.sample_rate,
            duration=duration,
        )

    @staticmethod
    def _emit(
        segment: SpeechSegment,
        callback: Callable[[SpeechSegment], None] | None,
    ) -> None:
        """Send a completed segment to the callback."""

        if callback is not None:
            callback(segment)
