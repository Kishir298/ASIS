# ASIS Installation

A.S.I.S. installs as the `asis` command (plus `asis-tui`). It is fully
standalone: CORE, RESCS and a Raspberry Pi are not required. Python 3.11+.

## pip / pipx

```bash
python -m pip install .            # or: pipx install .
python -m pip install ".[ai,tui,docs]"
```

`pipx` is recommended for a globally available command that does not pollute
project environments.

## Windows

- Windows 10 22H2 and Windows 11, x64 (ARM64 where wheels exist).
- PowerShell 5.1 is supported. WSL/Bash are not required.
- If `asis` is not found, add
  `%LOCALAPPDATA%\Programs\Python\Python3xx\Scripts` (or your environment's
  `Scripts`) to the user `PATH`, then open a new terminal.
- Voice extras use `pycaw`, `comtypes` and `pywin32`, which are installed only
  on Windows.

## macOS

- Intel and Apple Silicon; Python 3.11+.
- Add `~/Library/Python/3.x/bin` or the pipx bin directory to `PATH` in
  `~/.zshrc` if the command is not found:

  ```zsh
  export PATH="$HOME/.local/bin:$PATH"
  ```

- Microphone access must be granted to the terminal application for voice
  features.

## Linux

- x86_64 and ARM64 where binary wheels exist.
- Add `~/.local/bin` to `PATH` if needed.
- Voice requires PortAudio and the distribution's audio tooling; install the
  `.[voice]` extra only when those native libraries are present.

## Setup and diagnostics

```bash
asis setup                      # writes a private config; no downloads
asis doctor                     # offline report
asis doctor --check-model       # bounded local Ollama probe
asis                            # interactive interface
```

`asis setup` never downloads a model and never contacts the network. Existing
configuration is preserved. Configuration lives under the per-user
application-data directory; see `asis doctor` for exact paths.

## CORE integration (optional)

```bash
export ASIS_CORE_ENABLED=true
export ASIS_CORE_CREDENTIAL=...   # runtime-only, never persisted
asis doctor
asis core-status
```

A.S.I.S. continues to work with CORE disabled or unreachable.

## Updating

Reinstall the package. Configuration, memory databases and documents are
preserved. Updates never overwrite an existing `.env`.

## Uninstall

```bash
python -m pip uninstall asis     # or: pipx uninstall asis
```

Uninstalling does not delete memory, documents, configuration or identities.

## Standalone executables

Release builds provide `asis.exe` (Windows) and `asis` binaries for macOS and
Linux. They are self-contained; no Python installation is required.
