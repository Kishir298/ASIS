# CLI, Testing, Dependencies, Development

## CLI

Installed entry point `asis` (`pyproject.toml [project.scripts]`).
`python -m asis` is supported as an alias (`asis/__main__.py`).

Bare `asis` launches the persistent interactive terminal (TEXT/VOICE,
documents, typing effect) on top of the existing `AssistantApp` runtime:

```text
A.S.I.S. ready.

You > hello

A.S.I.S. > Hello! How can I help?

You >
```

`asis` flags: `--version`, `--identify`, `--provider {mock,ollama}`,
`--model MODEL` (default `qwen3:14b`), `--memory-db PATH`,
`--list-tools`, `--core-status`, `--message TEXT` (single shot),
`--mode {general,coding,translation}`, `--workspace PATH`, `--debug`,
`--log-level LEVEL`. Normal interactive use defaults to a quiet console
(WARNING); `--debug` restores verbose logs. File logging is preserved.

Interactive slash commands (handled by the CLI, never sent to the LLM):
`/help`, `/mode [text|voice]` (bare `/mode` toggles), `/upload <path>` /
`/attach <path>` (`.txt .md .pdf .docx .csv .json`), `/docs`,
`/clear-docs`, `/clear`, `/exit`, `/quit`. Keys: ENTER submit, ESC
interrupt response/speech (app stays alive), CTRL+C exit cleanly with
terminal restore. Documents persist across text/voice switches and are
injected as bounded offline context (4k chars/doc, 12k total).

Interrupt semantics (implemented, deterministically tested):
ESC sets a stop flag, cancels all `InterruptCoordinator` scopes
(`inference`/`voice`/`tools`), stops TTS + audio output, and returns
the prompt immediately. Cancellation is cooperative: chunk boundaries,
VAD/STT stages, and the typing renderer observe it. Blocking Ollama
HTTP (`requests.post`) cannot be safely killed mid-socket, so it stays
bounded by the configured request timeout; the UI does not wait for
it — the orphaned worker is a daemon thread whose late result is
discarded and never touches conversation/tool/terminal state.
CTRL+C is delivered to the main loop through a thread-safe
`shutdown_event` (a background watcher thread cannot raise
`KeyboardInterrupt` in the main thread); shutdown stops TTS/audio,
stops the watcher (joining it), restores POSIX `termios` state in a
`finally`, runs runtime cleanup, and exits `0`.
Physical TTY ESC/CTRL+C timing is unit-tested with mocks only;
manual TTY validation is recorded as NOT PERFORMED unless physically
exercised (see validation status below).

Document resource bounds (implemented, deterministically tested):
files over 10 MB are rejected before reading (`stat` gate); text/JSON
reads are capped at 2 MB; PDF extraction stops after 2 MB of text;
DOCX archives with more than 64 entries or a `document.xml` over
2 MB are treated as empty rather than extracted. All parsing is
offline (stdlib-first, optional `pypdf`/`python-docx`).

Validation status (this environment):
`python -m asis --version/--help` live-tested; persistent mock-provider
session live-tested (multi-turn, `/mode voice|text`, `/docs`,
`/clear-docs`, `/upload`, `/exit`, exit `0`); installed `asis` console
script verified equivalent via the `entry()` argv path (no binary on
PATH in this container — run `pip install -e .` to install it).
REAL OLLAMA VALIDATION: NOT PERFORMED (`qwen3:14b` not installed;
server reachable but only `qwen2.5:3b` cached and CPU inference
exceeded the validation window). REAL VOICE HARDWARE VALIDATION:
NOT PERFORMED (no audio hardware/deps; mock pipeline tests cover
the path).

`asis translate` subcommand (offline translation REPL/single-shot):
`--to LANG`, `--from LANG|auto`, `--message TEXT`, `--provider`,
`--model`, `--memory-db PATH`. REPL supports `/tr-to`, `/tr-from`,
`/mode` (see `docs/translation.md`).

`asis calculate` subcommand (offline deterministic math): positional or
`--expression TEXT`, `--operation OP` (30 engine operations),
`--equation/--equations/--variables/--variable/--function/--arguments/`
`--value/--from/--to/--data/--angle-mode`, repeatable `--param KEY=VALUE`.
Exit `2` with a `CALCULATION_*` code on failure
(see `docs/calculator.md`).

`asis voice` flags: `--stt-engine`, `--stt-model`, `--tts-engine`,
`--tts-voice`, `--speaker-engine`, `--wake-word`, `--no-wake-word`,
`--provider`, `--model`, `--memory-db PATH`, `--mode`, `--workspace`,
`--max-turns N`
(`0` = infinite), `--debug`. Mock engines by default; voice startup
failures exit `2` unless `--debug` re-raises.

## Testing

```bash
python -m pytest -q        # full deterministic suite (no HW/net/GPU)
python -m pytest tests/test_cli.py tests/test_interactive.py tests/test_cli_hardening.py -q
python -m pytest tests/test_voice.py tests/test_voice_runner.py tests/test_ollama_model_default.py -q
```

| File | Collected tests | Covers |
|---|---|---|
| `test_configuration.py` | 49 | defaults/overrides/precedence/validation/paths/voice/coding |
| `test_voice.py` | 28 | models/buffer/engines/pipeline/CLI, mock-only |
| `test_assistant.py` | 20 | session/memory/tools wiring, fail-open, permissions |
| `test_modes.py` | 13 | mode parse/switch/persistence, shared provider, CLI commands |
| `test_coding_tools.py` | 11 | read/search/list/write/tests/git through shared runtime |
| `test_coding_security.py` | 10 | traversal/symlink/allowlist/timeout/denied git safety |
| `test_ai.py` | 9 | providers, manager, conversation, context, inference |
| `test_app.py` | 6 | auto-memory extraction and result handling |
| `test_cli.py` | 7 | entry point, flags, REPL shutdown, memory building |
| `test_cli_interrupt.py` | 14 | launcher basename hardening, model override, shutdown-event contract, cooperative cancel/recovery, mode+doc persistence, doc→context proof, oversized/zip-bomb bounds, quoted paths, renderer edges, logging dedup |
| `test_base_install.py` | 4 | mock/offline CLI imports without `requests`; ollama without `requests` fails with install hint; lazy `OllamaProvider` identity |
| `test_runtime_integration.py` | 5 | multi-turn CLI, memory/tool paths, voice app path |
| `test_coding_integration.py` | 5 | integrated coding path, multi-turn fix flow, memory separation |
| `test_shutdown.py` | 5 | bounded shutdown, timeout FAILED, reverse order |
| `test_events.py` | 5 | event bus and event types |
| `test_identity.py` | 5 | identity rendering, personality template |
| `test_memory.py` | 10 | manager, storage, search, models |
| `test_tools.py` | 9 | registry, router, executor, permissions, provided tools |

Mock providers everywhere: **no Ollama, microphone, speakers, GPU,
models, internet, CORE, or RESCS required**. No coverage gate is
configured (`pytest-cov` is installed but no threshold set) — do not
claim 100% coverage.

## Dependencies (`pyproject.toml`, `requires-python = >=3.11`)

- **Core (mandatory):** `platformdirs`, `psutil` (declared in
  `pyproject.toml`/`requirements/base.txt` but not yet imported by any
  `asis/` module — reserved for future system/resource features),
  `python-dotenv`.
- **AI (optional):** `requests` (the Ollama provider uses HTTP via
  `requests`; the `ollama` client package is not used). A base install
  without extras still runs the mock/offline CLI: `OllamaProvider` is
  imported lazily and only actual Ollama or web-tool execution needs
  `requests` (proven by `tests/test_base_install.py`).
- **Voice (optional):** `numpy`, `scipy`, `sounddevice`, `soundfile`,
  `silero-vad`, `faster-whisper`, `torch`, `torchaudio`, `speechbrain`,
  `openwakeword`, `pyttsx3` (+ `pycaw/comtypes/pywin32` on Windows).
- **Docs (optional):** `pypdf`, `python-docx` (`requirements/docs.txt`,
  `pip install -e ".[docs]"`). Parsers fall back to stdlib-only
  extraction when these are absent.
- **Dev:** `pytest`, `pytest-cov`, `ruff`, `black` (line-length 88;
  ruff rules `E,F,W,I,UP,B,SIM`).

Heavy packages stay optional via lazy imports — base install and
tests never touch them.

## Development workflow

```bash
pip install -e ".[dev]"     # pytest, ruff, black
python3 -m pytest -q        # test
ruff check asis tests       # lint (must pass)
ruff format --check asis tests  # format
```

`setup_venv.py` bootstraps a local venv. `ASIS.code-workspace`
points VS Code at `.venv` with `pytestArgs=["tests"]`.
