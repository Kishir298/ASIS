# Building ASIS

## Prerequisites

- Python 3.11+
- `python -m pip install build pyinstaller`
- Voice builds need the platform audio libraries listed in
  `requirements/voice.txt`.

## Wheel and sdist

```bash
python -m build --wheel --sdist
```

## Standalone executable

```bash
python -m pip install ".[ai,tui,docs]" pyinstaller
python -m PyInstaller --onefile --name asis \
  --collect-submodules asis --collect-data asis \
  --distpath dist scripts/standalone_entry.py
```

Build on each target OS/architecture. PyInstaller cannot cross-compile.

## Tests and lint

```bash
python -m pytest -q
ruff check --select F asis tests
```

## Release automation

`.github/workflows/release.yml` builds wheels/sdists and standalone binaries
for Windows x64/ARM64, macOS Intel/ARM64 and Linux x64/ARM64. It verifies that
the tag, `pyproject.toml` and `compatibility.json` versions agree, then emits
SHA-256 checksums and a CycloneDX SBOM.

Voice/Torch extras are intentionally **not** bundled into the standalone
binary; the release binary covers the text/TUI application. Install the
`[voice]` extra for voice features.
