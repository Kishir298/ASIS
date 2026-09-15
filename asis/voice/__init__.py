"""
A.S.I.S. voice subsystem.

Engines are pluggable; the default configuration uses mock engines so
A.S.I.S. runs without audio hardware or heavy AI dependencies.
"""

from .engines import (
    KeyphraseWakeWordDetector,
    MockAudioInput,
    MockAudioOutput,
    MockSpeakerIdentifier,
    MockSpeechRecognizer,
    MockTextToSpeech,
)
from .factory import (
    create_audio_input,
    create_audio_output,
    create_speaker_identifier,
    create_speech_recognizer,
    create_tts,
    create_voice_engines,
)
from .models import AudioData, SpeakerResult, TranscriptionResult
from .pipeline import VoicePipeline
from .runner import VoiceRunner
from .providers import (
    AudioInputProvider,
    AudioOutputProvider,
    SpeakerIdentifier,
    SpeechRecognizer,
    TextToSpeechProvider,
)

__all__ = [
    "AudioData",
    "AudioInputProvider",
    "AudioOutputProvider",
    "KeyphraseWakeWordDetector",
    "MockAudioInput",
    "MockAudioOutput",
    "MockSpeakerIdentifier",
    "MockSpeechRecognizer",
    "MockTextToSpeech",
    "SpeakerIdentifier",
    "SpeakerResult",
    "SpeechRecognizer",
    "TextToSpeechProvider",
    "TranscriptionResult",
    "VoicePipeline",
    "VoiceRunner",
    "create_audio_input",
    "create_audio_output",
    "create_speaker_identifier",
    "create_speech_recognizer",
    "create_tts",
    "create_voice_engines",
]
