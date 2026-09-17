# A.S.I.S. — A Smart Intelligence System

Intelligence/assistant layer of the R.I.S.A.R.M.S. ecosystem. Runs
independently — no C.O.R.E. or R.E.S.C.S. required (C.O.R.E. is a real
but optional uplink; R.E.S.C.S. remains a future boundary; see
`docs/integration.md`).

## Status

| Area | Status |
|---|---|
| Repository structure | Implemented |
| Configuration + validation | Implemented |
| AI provider abstraction | Implemented |
| Ollama provider | Implemented (optional dep) |
| Conversation / context | Implemented + wired (`AssistantApp` owns session) |
| Local memory (SQLite) | Implemented + wired (query-scoped recall, fail-open) |
| Tools (`echo`, `current_time`) | Implemented + application-wired (native function calling primary, heuristic fallback, permission-mandatory) |
| Web access (`web_search`, `web_fetch`) | Implemented + application-wired (shared registry for GENERAL/A.S.C.S./voice, SSRF-guarded bounded provider, optional via `ASIS_WEB_ENABLED`) |
| A.S.C.S. coding mode | Implemented + wired (shared provider/model, workspace-bound tools) |
| Permissions / confirmation | Implemented (no dangerous tools ship) |
| Voice architecture + mocks | Implemented |
| Local STT / TTS / speaker / wake / VAD | Implemented (optional deps) |
| CLI (`asis`, `asis voice`) | Implemented (stateful multi-turn) |
| Shutdown timeout | Implemented (bounded stop, FAILED + log on expiry) |
| C.O.R.E. integration | Implemented (optional uplink; standalone by default) |
| R.E.S.C.S. integration | Future (placeholder adapter) |

## Docs

| File | Covers |
|---|---|
| `docs/architecture.md` | runtime, lifecycle, identity, errors, logging |
| `docs/configuration.md` | settings, precedence, validation, paths |
| `docs/ai-memory.md` | providers, inference, conversation, memory |
| `docs/coding.md` | A.S.C.S. modes, workspace, coding tools, permissions |
| `docs/tools-permissions.md` | tools, permissions, sandbox, secrets |
| `docs/voice.md` | pipeline, engines, mock-vs-real matrix |
| `docs/cli-testing.md` | CLI flags, tests, dependencies, workflow |
| `docs/integration.md` | C.O.R.E. (real adapter) / R.E.S.C.S. future boundary |

## Layout

```text
ASIS/
├── asis/                  # sole production package
│   ├── ai/                # inference, conversation, context engines
│   ├── app/               # application orchestration
│   ├── cli/               # `asis` entry point + voice loop
│   ├── configuration/     # centralized settings
│   ├── integrations/      # C.O.R.E. adapter (real) / R.E.S.C.S. (future)
│   ├── memory/            # local memory provider
│   ├── tools/             # tool system + permissions
│   ├── web/              # web provider (search + fetch, SSRF guard)
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

Each REPL/voice run owns one `ConversationSession` (`AssistantApp`):
turns persist user + assistant messages within configured history /
context limits, relevant memories are retrieved query-scoped into the
system prompt (stored memory is data, never instructions). Tool use is
native-first: the local model receives tool definitions derived from
the active registry and may return structured calls (validated against
parameter schemas, at most `ASIS_TOOL_MAX_CALLS_PER_TURN` per turn),
falling back to the heuristic/explicit intent path when native calling
is unavailable — both converge on the same Router/permission path.
Failed inference preserves state; memory failure logs and continues.
Explicit `core:` user commands (`core:devices`, `core:device <id>`,
`core:status`, `core:service <svc> <op>`, `core:agent <op>`,
`core:data <type>`, `core:send <device> <type>`) execute one CORE tool
deterministically through the same Router/permission path.

## C.O.R.E. uplink (optional)

```text
A.S.I.S. -> integrations/core/ (RealCoreAdapter, CoreConnectionManager)
-> CORE-CLIENT (CoreDeviceClient) -> TCP+TLS -> CORE-HOST
```

1. Make `client.core_device_client` importable (sibling CORE-CLIENT repo
   or `PYTHONPATH`); repos stay unmerged, and A.S.I.S. never imports
   CORE-HOST modules (tested).
2. Provision the device on CORE-HOST (`provision-device`); copy only the
   public cert to the device — never `core.key`/`.pfx`.
3. Set `ASIS_CORE_ENABLED=true` (+ host/port/cert in `.env`; the
   provisioning credential is runtime-only, never filed).
4. `CoreConnectionManager` (a plain `RuntimeComponent`) connects
   (`CORE_HANDSHAKE` → auth → `DEVICE_REGISTER` → online). When
   disabled/unreachable everything local keeps working; CORE tools fail
   cleanly with `CORE_UNAVAILABLE`; reconnect is bounded and stop-aware.

CORE tools (`core_discover_devices`, `core_device_info`, `core_status`,
`core_data_request`, `core_service_request`, `core_agent_request`,
`core_send_to_device`) are registered on the shared `ToolRegistry` in
both GENERAL and CODING modes — one adapter, one connection.
Network tools are HIGH (confirmation-gated); results are redacted and
truncated to 8 000 chars before the model. Host device-to-device
routing is one-way, so `core_send_to_device` yields a timeout-shaped
result rather than a reply envelope. Intelligence stays local:
normal prompts/history never leave the device; Ollama remains the only
inference provider.

## Manual LAN validation (NOT PERFORMED)

Windows CORE-HOST (TLS listener) + Mac CORE-CLIENT/A.S.I.S./Ollama:
provision → configure → authenticate → register → online; start
A.S.I.S., confirm CORE status (`--core-status`), hold a local
conversation, invoke a CORE tool, confirm host receipt + response;
stop the host, confirm local operation survives; restore host, confirm
bounded reconnect; shut down, confirm session secrets destroyed.
Do not mark PASS until physically performed.

## Test

```bash
python3 -m pytest -q        # canonical suite (tests/)
```

## CLI

```bash
asis --help
asis voice                  # voice loop (mock engines by default)
```
