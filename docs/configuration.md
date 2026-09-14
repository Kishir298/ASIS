# A.S.I.S. Configuration

Single validated layer: `asis/configuration` → typed `settings` →
components. Application code must not call `os.getenv` (the only
exception is the generic `permissions/secrets.py:get_secret()` helper).

## Flow and precedence

```text
Built-in defaults            asis/configuration/defaults.py
        ↓
.env files                   project root + user config dir
        ↓
Process environment          ASIS_* variables
        ↓
Explicit overrides           load_settings(env={...})
        ↓
Environment parsing          strict, lazy, per call
        ↓
Typed Settings               frozen dataclasses
        ↓
Validation                   validate_settings() → ConfigurationError
        ↓
A.S.I.S. Components
```

`.env` files load with `override=False`: existing process variables
always win. Explicit `load_settings(env=...)` wins over everything.

## API

```python
from asis.configuration import load_settings, settings

settings.ai.model            # global singleton (frozen)
fresh = load_settings()      # independent reload, reads live env
custom = load_settings({"ASIS_AI_MODEL": "x"})
```

Settings dataclasses are frozen — mutation raises
`FrozenInstanceError`. Tests use `monkeypatch.setenv` + `load_settings()`
and never touch the global.

## Parsing rules

- Empty/whitespace-only values count as **unset** (default applies).
- Present-but-invalid values raise **`ConfigurationError`** naming
  variable, received value, and expectation — never silent fallback.
- Booleans accept `1/true/yes/on/enabled` and
  `0/false/no/off/disabled` (case-insensitive); anything else raises.

## Categories

| Section | Key fields |
|---|---|
| Identity | `name`, `title`, `shutdown_phrase`, `app_version` |
| Runtime | `debug`, `log_level` (`DEBUG…CRITICAL`), `shutdown_timeout` (>0) |
| AI | `provider`, `model`, `endpoint` (http(s) URL), `request_timeout` (>0), `temperature` (0–2), `max_context_messages`, `context_char_limit` (>0) |
| Conversation | `max_history` (>0) |
| Memory | `provider` (`local` only), `database_name` (safe filename) |
| Voice | audio (`sample_rate`, `channels`, `block_size` >0; `input/output_engine`), STT (`engine/model/device/compute_type`, optional `language`), TTS (`engine`, optional `voice`, `sample_rate`), speaker (`engine/model/device/metric`, `confidence/threshold` 0–1), wake (`engine`, `threshold` 0–1, `model` optional; `wake_word` required unless engine is mock/none/off), VAD (`engine`, `threshold` 0–1) |
| Network | `timeout` (>0), `retries` (≥0) |
| Tools | `timeout` (>0, per-run bound) |
| Security | `require_confirmation_for_dangerous` (strict bool) |
| Paths | `data/config/cache/logs/memory/runtime` (platformdirs, overridable) |

## Paths

`platformdirs` on macOS/Windows/Linux; nothing persistent lives in the
repo. `runtime/` uses the OS temp dir; the rest live under the
platform's user data/config/cache roots. Any directory is overridable:

```text
ASIS_DATA_DIRECTORY, ASIS_CONFIG_DIRECTORY, ASIS_CACHE_DIRECTORY,
ASIS_LOG_DIRECTORY, ASIS_MEMORY_DIRECTORY, ASIS_RUNTIME_DIRECTORY
```

Overrides accept `~`, resolve to absolute paths, and fall back to
platform defaults when unset.

## Reference

`.env.example` documents all 52 variables with type, range, and default
(46 set explicitly; the 6 `ASIS_*_DIRECTORY` path overrides appear
commented-out since platform defaults apply). It is cross-checked
against `settings.py` — if they ever disagree, the code wins and the
file must be fixed.
