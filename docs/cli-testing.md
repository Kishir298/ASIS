# CLI, Testing, Dependencies, Development

## CLI

Installed entry point `asis` (`pyproject.toml [project.scripts]`).
There is **no `python -m asis`** (`__main__.py` does not exist) — use
the `asis` command (or `entry()` programmatically).

`asis` flags (verified from `--help`): `--version`, `--identify`
(prints configured identity system prompt), `--provider
{mock,ollama}`, `--model MODEL`, `--memory-db PATH`, `--list-tools`,
`--message TEXT` (single shot, else stdin REPL until the shutdown
phrase, default `asis shutdown`), `--mode {general,coding}`,
`--workspace PATH`. REPL commands: `/mode [general|coding]`, `/ascs`
(coding shortcut), `/mode` (print current). All default from settings;
all work offline with `--provider mock`.

`asis voice` flags: `--stt-engine`, `--stt-model`, `--tts-engine`,
`--tts-voice`, `--speaker-engine`, `--wake-word`, `--no-wake-word`,
`--provider`, `--model`, `--memory-db PATH`, `--mode`, `--workspace`,
`--max-turns N`
(`0` = infinite), `--debug`. Mock engines by default; voice startup
failures exit `2` unless `--debug` re-raises.

## Testing

```bash
python3 -m pytest -q        # full suite: 197 tests, ~11s
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
- **AI (optional):** `requests`, `ollama`.
- **Voice (optional):** `numpy`, `scipy`, `sounddevice`, `soundfile`,
  `silero-vad`, `faster-whisper`, `torch`, `torchaudio`, `speechbrain`,
  `openwakeword`, `pyttsx3` (+ `pycaw/comtypes/pywin32` on Windows).
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
