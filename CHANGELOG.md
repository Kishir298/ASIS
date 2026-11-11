# Changelog

## [0.1.0] — 2026-11-11

### Added

- Cross-platform release pipeline (Windows x64/ARM64, macOS Intel/ARM64,
  Linux x64/ARM64) with checksums, CycloneDX SBOM and release channels.
- Standalone `asis` executable entry point for PyInstaller builds.
- Machine-readable `compatibility.json`.
- Platform smoke CI job verifying `asis --help`, `asis setup` and
  `asis doctor` from an unrelated directory.
- Documentation: installation, building, releases, security, compatibility.

### Verified

- `asis setup`, `asis doctor` and the manifest are covered by regression
  tests; existing suite passes unchanged.

### Known limitations

- Voice/Torch extras are not embedded in standalone binaries.
- macOS signing/notarization depends on configured secrets.
- Windows 10/ARM64 and macOS Intel are not physically validated here.
