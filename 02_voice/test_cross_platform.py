from __future__ import annotations

import platform
import sys
from pathlib import Path

import numpy as np

# Make 02_voice importable regardless of where this script is launched from.
VOICE_ROOT = Path(__file__).resolve().parent

if str(VOICE_ROOT) not in sys.path:
    sys.path.insert(0, str(VOICE_ROOT))

from config.platform import get_platform, is_supported_platform  # noqa: E402
from input.microphone import Microphone, MicrophoneConfig  # noqa: E402
from recognition.speech_to_text import SpeechTranscriber  # noqa: E402


def print_section(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def test_platform() -> None:
    print_section("PLATFORM")

    print("OS:", platform.system())
    print("Platform:", get_platform())
    print("Supported:", is_supported_platform())

    if not is_supported_platform():
        raise RuntimeError("Unsupported platform.")


def test_microphones() -> None:
    print_section("MICROPHONES")

    devices = Microphone.list_devices()

    if not devices:
        raise RuntimeError("No microphone input devices detected.")

    for device in devices:
        print(
            f"[{device['index']}] "
            f"{device['name']} | "
            f"inputs={device['input_channels']} | "
            f"default_rate={device['sample_rate']}"
        )

    return devices


def test_microphone_capture() -> np.ndarray:
    print_section("MICROPHONE CAPTURE")

    config = MicrophoneConfig(
        sample_rate=16_000,
        channels=1,
        block_size=1024,
    )

    microphone = Microphone(config)

    print("Starting microphone...")
    microphone.start()

    try:
        print("Speak normally for a few seconds.")
        print("Capturing audio...")

        chunks = []

        for _ in range(50):
            audio = microphone.read()
            chunks.append(audio)

        samples = np.concatenate(chunks, axis=0)

    finally:
        microphone.stop()

    print("Captured samples:", len(samples))
    print("Shape:", samples.shape)
    print("Sample rate:", config.sample_rate)
    print("Channels:", config.channels)

    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(samples**2)))

    print("Peak volume:", round(peak, 5))
    print("RMS volume:", round(rms, 5))

    if peak == 0:
        raise RuntimeError("Microphone captured only silence.")

    print("Microphone capture: OK")

    return samples


def test_transcription(samples: np.ndarray) -> None:
    print_section("SPEECH-TO-TEXT")

    print("Loading speech-to-text model...")
    transcriber = SpeechTranscriber()

    print("Transcribing...")
    result = transcriber.transcribe(
        samples,
        sample_rate=16_000,
    )

    print("Text:", result.text)
    print("Language:", result.language)
    print("Language probability:", result.language_probability)
    print("Duration:", result.duration)

    if not result.text.strip():
        raise RuntimeError("Speech-to-text returned empty text.")

    print("Speech-to-text: OK")


def main() -> None:
    print("Forza AI Voice Cross-Platform Test")
    print("Python:", sys.version.split()[0])
    print("Executable:", sys.executable)

    test_platform()
    test_microphones()
    samples = test_microphone_capture()
    test_transcription(samples)

    print()
    print("=" * 60)
    print("ALL CROSS-PLATFORM VOICE TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
