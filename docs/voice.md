# Voice (`asis/voice/`)

Canonical and only voice implementation (the old `02_voice` tree was
removed). Status labels: **Implemented** = works today, **Mock** =
scripted test double, **Optional** = needs an extra + hardware/model.

## Pipeline order (`VoicePipeline.run_once`)

`listen → check_voice_activity → transcribe → normalize_text →
detect_wake_text (if required) → identify_speaker → process_fn →
speak`, returning `{text, speaker, response, status}` with status
`spoken | no-speech | no-wake-word`. Each stage is independently
callable and interrupt-checked; `VoiceEvent`s never carry raw audio.

## Engines

| Stage | Mock (default) | Real (opt-in) | Engine names |
|---|---|---|---|
| Audio input | `MockAudioInput` | `SoundDeviceInputProvider` (Optional) | `mock`, `sounddevice`, `microphone`, `real` |
| Audio output | `MockAudioOutput` | `SoundDeviceOutputProvider` (Optional) | `mock`, `sounddevice`, `real` |
| VAD | `MockVadDetector` | `SileroVadDetector` (Optional, torch+silero) | `mock`, `silero*` |
| Wake word | `MockWakeWordDetector`, `KeyphraseWakeWordDetector` | `OpenWakeWordDetector` (Optional) | `mock`, `keyphrase`, `openwakeword`, … |
| STT | `MockSpeechRecognizer` | `FasterWhisperRecognizer` (Optional) | `mock`, `faster-whisper`, … |
| Speaker ID | `MockSpeakerIdentifier` | `EmbeddingSpeakerIdentifier` (Optional, speechbrain) | `mock`, `embedding`, … |
| TTS | `MockTextToSpeech` | `Pyttsx3Engine` (Optional, offline wav) | `mock`, `pyttsx3`, `local` |

Unknown engine names raise `VoiceError` pointing at the corresponding
`ASIS_VOICE_*_ENGINE` variable. All `*_ENGINE` defaults are `mock`.

## Details

- **Audio input** (`input/`): `Microphone` (lazy sounddevice,
  discovery/capture), `AudioBuffer` (thread-safe deque, numpy-optional),
  `VoiceActivityDetector` (256/512 frames) + `SileroVadDetector` adapter.
- **STT** (`speech/`): `SpeechTranscriber` (lazy WhisperModel,
  auto-language) + `FasterWhisperRecognizer` adapter
  (`model/device/compute_type/language` from settings) +
  `TranscriptionNormalizer`.
- **Speaker** (`speaker/`): JSON-file/memory `SpeakerStore` (never
  stores audio), `register_speaker()` merge, `EmbeddingSpeakerIdentifier`
  (`threshold`, `cosine` metric, `unknown` fallback), pure-python
  embedding math + lazy SpeechBrain provider.
- **TTS** (`tts/`): `Pyttsx3Engine` renders offline to wav and returns
  `AudioData`; empty `voice` allowed (provider auto-selects).
- **Output** (`output/`): `SoundDeviceOutputProvider.play/stop` with
  validation and channel-mismatch warning.
- **Wake** (`engines/`): text keyphrase detector, scriptable mocks,
  `OpenWakeWordDetector` (threshold + optional model path).

## Current limitations

- The voice CLI hardcodes mock audio input/output regardless of
  `VOICE_INPUT/OUTPUT_ENGINE` (engines apply via the factory API).
- `--wake-word` forces a mock keyphrase detector, bypassing wake
  engine/threshold/model settings.
- `VAD`/`wake`/`speaker` thresholds and `tts.sample_rate` have no CLI
  flags (configuration only).
- Standard tests are mock-only: no microphone, speakers, GPU, models,
  or network required.

Voice uses the same `AssistantApp` intelligence as the text CLI
(stateful session + memory recall + single tool cycle via
`process_fn`), not a second AI implementation.
