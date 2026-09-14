# A.S.I.S. — A Smart Intelligence System

Intelligence layer of the R.I.S.A.R.M.S. ecosystem.

## Layout

```text
ASIS/
├── asis/                  # sole production package
│   ├── ai/                # inference, conversation, context engines
│   ├── app/               # application orchestration
│   ├── cli/               # `asis` entry point + voice loop
│   ├── configuration/     # centralized settings
│   ├── memory/            # local memory provider
│   ├── tools/             # tool system + permissions
│   ├── voice/             # sole production voice implementation
│   └── ...
├── tests/                 # canonical test suite
├── requirements/          # base / ai / voice dependency sets
├── pyproject.toml
└── requirements.txt
```

## Voice (`asis/voice`)

Pluggable voice pipeline: audio input (microphone/sounddevice), VAD
(Silero, optional), wake-word detection (keyphrase/openwakeword),
speech recognition (faster-whisper, optional), speaker identification
+ embeddings, TTS (pyttsx3), audio output. Heavy audio/ML
dependencies are optional and lazily imported — base installs and
tests run without them. Scriptable mocks live in
`asis/voice/engines/mock.py`.

## Install

```bash
pip install -e .            # base
pip install -e ".[voice]"   # voice extras (microphone, STT, TTS, VAD)
```

## Test

```bash
python3 -m pytest -q        # canonical suite (tests/)
```

## CLI

```bash
asis --help
asis voice                  # voice loop (mock engines by default)
```
