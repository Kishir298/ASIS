# A.S.I.S. Architecture

A.S.I.S. (**A Smart Intelligence System**) is the intelligence/assistant
layer of the R.I.S.A.R.M.S. ecosystem. It runs independently: AI
interaction, conversation, memory, tools, permissions, voice, and
identity all work with no C.O.R.E. or R.E.S.C.S. process present (see
`docs/integration.md` for the future boundaries).

## Runtime shape

```text
User
 │
 ▼
CLI / Voice Interface          asis/cli/main.py, asis/cli/voice.py
 │
 ▼
Conversation Engine            asis/ai/conversation.py (bounded session)
 │
 ├── Context Manager           asis/ai/context.py (system prompt + limits)
 │
 ├── Memory                    asis/memory/ (local SQLite, see docs/ai-memory.md)
 │
 ├── Model Provider            asis/ai/ (mock default, Ollama optional)
 │
 └── Tool System               asis/tools/ (registry → router → executor)
       │
       ▼
   Permission Manager          asis/permissions/ (levels + confirmation)
       │
       ▼
    Tool Execution             bounded by tools.timeout
```

There is **no agentic loop**: inference is a single
context → model → response pass per turn (`asis/ai/inference.py`).
The model never invokes tools by itself; tools run only when
application code calls the router.

## Voice pipeline

```text
Microphone
    ↓
Audio Input                    asis/voice/input/ (mock default, sounddevice real)
    ↓
Wake Word / VAD                engines + input/vad.py (mock default)
    ↓
Speech Recognition             speech/ (mock default, faster-whisper real)
    ↓
Speaker Identification         speaker/ (mock default, embedding real)
    ↓
A.S.I.S. Processing            process_fn supplied by caller (CLI wires AI chat)
    ↓
Response
    ↓
Text-to-Speech                 tts/ (mock default, pyttsx3 real)
    ↓
Audio Output                   output/ (mock default, sounddevice real)
```

Every stage is mock-by-default and independently testable; real
engines are explicit opt-ins via `ASIS_VOICE_*_ENGINE`. Details in
`docs/voice.md`.

## Lifecycle / shutdown

`asis/system/lifecycle.py` starts components in registration order and
stops them in reverse; per-component stop failures are logged, not
re-raised. `ASISRuntime` (`asis/system/runtime.py`) tracks
`CREATED → STARTING → RUNNING → STOPPING → STOPPED/FAILED` and cancels
all interrupt scopes on stop. Shutdown is triggered by the configured
phrase (default `asis shutdown`) in the CLI/voice REPLs, by
`--max-turns`, or by `Ctrl+C`; the voice loop always runs
`pipeline.stop()` in `finally`.

Known limitation: `runtime.shutdown_timeout` is validated but no
component currently enforces a timed join — shutdown is cooperative.

`InterruptCoordinator` (`asis/system/interrupt.py`, scopes
`inference` and `voice`) lets one subsystem cancel another's blocking
work via `CancellationError`.

## Identity

`asis/identity/`: frozen `Identity(name, title, personality,
preferences, greeting)` rendered from `settings.identity`
(`build_identity()`), so renaming A.S.I.S. is configuration, not code.
Default personality template supports `{name}`/`{title}`.

## Package map

```text
asis/
├── ai/               inference, conversation, context, providers
├── app/              auto-memory extraction, process result
├── cli/              entry point, chat REPL, voice loop
├── configuration/    defaults → env → validated Settings
├── errors/           ASISError hierarchy (see below)
├── events/           EventBus (AI, tools, memory, voice events)
├── identity/         config-driven identity + personality
├── integrations/     future CORE/RESCS contracts + mock adapters
├── logging/          console + rotating-file handlers
├── memory/           local SQLite memory
├── permissions/      levels, confirmation, sandbox, secrets helper
├── system/           lifecycle, runtime, interrupts
├── tools/            registry, router, executor, provided tools
└── voice/            canonical voice subsystem
```

## Error hierarchy

`asis/errors/`: `ASISError` → `ConfigurationError`, `ModelError` →
`InferenceError`, `ConversationError`, `ToolError` →
`ToolValidationError`/`ToolNotFoundError`, `PermissionError`
(intentionally shadows the builtin), `VoiceError` →
`SpeechRecognitionError`/`SpeakerRecognitionError`/`TTSError`,
`MemoryError`, `CancellationError`. Failures surface as typed
exceptions; the CLI prints them (exit `2` for voice startup failures
unless `--debug` re-raises).

## Logging

`asis/logging/`: level from `settings.runtime.log_level` (unknown →
`INFO`), `get_logger(name)` returns `asis` children with
`propagate=False`; console `StreamHandler` + `RotatingFileHandler`
(`logs/asis.log`, 5 MB × 5, UTF-8), format
`[asctime] [level] [name] message`. No redaction mechanism exists —
**never log secrets** (policy; see `docs/cli-testing.md` security
notes and `.env.example`).
