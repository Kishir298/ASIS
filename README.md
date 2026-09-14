# A.S.I.S. — A Smart Intelligence System

Intelligence/assistant layer of the R.I.S.A.R.M.S. ecosystem. Runs
independently — no C.O.R.E. or R.E.S.C.S. required (both are future
integration boundaries; see `docs/integration.md`).

## Status

| Area | Status |
|---|---|
| Repository structure | Implemented |
| Configuration + validation | Implemented |
| AI provider abstraction | Implemented |
| Ollama provider | Implemented (optional dep) |
| Conversation / context | Implemented |
| Local memory (SQLite) | Implemented |
| Tools (`echo`, `current_time`) | Implemented |
| Permissions / confirmation | Implemented (no dangerous tools ship) |
| Voice architecture + mocks | Implemented |
| Local STT / TTS / speaker / wake / VAD | Implemented (optional deps) |
| CLI (`asis`, `asis voice`) | Implemented |
| Conversation history / memory recall in CLI | Not wired (subsystems implemented, see docs/ai-memory.md) |
| Tool execution from application code | Not wired (subsystem implemented, `--list-tools` only) |
| C.O.R.E. integration | Future (mock adapter) |
| R.E.S.C.S. integration | Future (placeholder adapter) |

## Docs

| File | Covers |
|---|---|
| `docs/architecture.md` | runtime, lifecycle, identity, errors, logging |
| `docs/configuration.md` | settings, precedence, validation, paths |
| `docs/ai-memory.md` | providers, inference, conversation, memory |
| `docs/tools-permissions.md` | tools, permissions, sandbox, secrets |
| `docs/voice.md` | pipeline, engines, mock-vs-real matrix |
| `docs/cli-testing.md` | CLI flags, tests, dependencies, workflow |
| `docs/integration.md` | C.O.R.E. / R.E.S.C.S. future boundaries |

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

## Configuration

One validated layer: `asis/configuration` → typed `settings` →
components. Copy `.env.example` to `.env` (or export variables
directly); see the example file for every variable, default, type,
and range.

```python
from asis.configuration import load_settings, settings

settings.ai.model          # typed access, never os.getenv in app code
fresh = load_settings()    # independent reload (tests/development)
custom = load_settings({"ASIS_AI_MODEL": "x"})  # explicit overrides win
```

Precedence: explicit overrides > process environment > `.env` >
built-in defaults. Empty values count as unset; present-but-invalid
values raise `ConfigurationError`. Paths resolve via `platformdirs`
outside the repository (overridable with `ASIS_*_DIRECTORY`).

## Chat behavior

Each CLI input is processed statelessly: a fresh `[system, user]`
pair is sent to the provider, with auto-extracted memories persisted
to the local SQLite store. `ConversationSession`, `ContextAssembler`
and `InferenceEngine` (history, memory-aware prompts, cancellable
inference) are implemented and tested but not yet wired into the CLI —
see `docs/ai-memory.md` for the exact boundary.

## Test

```bash
python3 -m pytest -q        # canonical suite (tests/)
```

## CLI

```bash
asis --help
asis voice                  # voice loop (mock engines by default)
```
