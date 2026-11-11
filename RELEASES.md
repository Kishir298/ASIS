# ASIS Releases

A.S.I.S. versions independently (`pyproject.toml` / `compatibility.json`).
Current: `0.1.0`.

## Channels

| Channel | Trigger | Result |
| --- | --- | --- |
| Stable | tag `vX.Y.Z` | GitHub Release |
| Beta | tag `vX.Y.Z-beta.N` | prerelease |
| Development | `workflow_dispatch` | artifacts only |

## Artifacts

`ASIS-<version>-<os>-<arch>-<format>`:

- `ASIS-<v>-windows-x64.zip` (`asis.exe`)
- `ASIS-<v>-windows-arm64.zip` (experimental)
- `ASIS-<v>-macos-x86_64.tar.gz`, `ASIS-<v>-macos-arm64.tar.gz`
- `ASIS-<v>-linux-x64.tar.gz`, `ASIS-<v>-linux-arm64.tar.gz`
- `ASIS-<v>-python-wheel.whl`, `ASIS-<v>-python-sdist.tar.gz`
- `SHA256SUMS`, `sbom.cdx.json`

## Process

1. Bump the version in `pyproject.toml`, `package.json`, `compatibility.json`
   and `CHANGELOG.md`.
2. Run `pytest` and `ruff check --select F asis tests`.
3. Commit, then tag: `git tag -a vX.Y.Z -m "ASIS X.Y.Z"`.
4. Push the tag; the workflow validates, builds, checksums and publishes.
5. Publish is skipped when any required build job fails.

## Known limitations

- macOS artifacts are unsigned/notarized only when signing secrets are
  configured.
- Voice/Torch dependencies are not embedded in standalone binaries.
- Windows ARM64 is marked experimental pending dependency verification.
