# CLI, Testing, Dependencies, Development

## CLI

Installed entry point `asis` (`pyproject.toml [project.scripts]`).
There is **no `python -m asis`** (`__main__.py` does not exist) — use
the `asis` command (or `entry()` programmatically).

`asis` flags (verified from `--help`): `--version`, `--identify`
(prints configured identity system prompt), `--provider
{mock,ollama}`, `--model MODEL`, `--memory-db PATH`, `--list-tools`,
`--message TEXT` (single shot, else stdin REPL until the shutdown
phrase, default `asis shutdown`). All default from settings; all work
offline with `--provider mock`.

`asis voice` flags: `--stt-engine`, `--stt-model`, `--tts-engine`,
`--tts-voice`, `--speaker-engine`, `--wake-word`, `--no-wake-word`,
`--provider`, `--model`, `--memory-db PATH`, `--max-turns N`
(`0` = infinite), `--debug`. Mock engines by default; voice startup
failures exit `2` unless `--debug` re-raises.

## Testing

```bash
python3 -m pytest -q        # full suite: 128 tests, ~1s
```

| File | Tests | Covers |
|---|---|---|
| `test_configuration.py` | 49 | defaults/overrides/precedence/validation/paths/voice |
| `test_voice.py` | 28 | models/buffer/engines/pipeline/CLI, mock-only |
| `test_ai/memory/tools/cli/…` | 51 | providers, lifecycle, registry, parsers, events |

Mock providers everywhere: **no Ollama, microphone, speakers, GPU,
models, internet, CORE, or RESCS required**. No coverage gate is
configured (`pytest-cov` is installed but no threshold set) — do not
claim 100% coverage.

## Dependencies (`pyproject.toml`, `requires-python = >=3.11`)

- **Core (mandatory):** `platformdirs`, `psutil`, `python-dotenv`.
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
