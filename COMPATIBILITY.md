# ASIS Compatibility

Machine-readable source of truth: [`compatibility.json`](compatibility.json).

## Platforms

| OS | Architectures | Minimum | Status |
| --- | --- | --- | --- |
| Windows | x86_64, arm64 | 10 22H2 | CI smoke on windows-latest; Win10 needs hardware validation |
| macOS | x86_64, arm64 | 12.0 | CI smoke on macos-latest |
| Linux | x86_64, arm64 | glibc 2.28 | CI tests on ubuntu-latest |

## Runtime

- Python 3.11+ (`asis`, `asis-tui` console scripts).
- pip, pipx and standalone executables are supported installation methods.

## CORE integration

Optional. When enabled, ASIS verifies the device through CORE-CLIENT,
authenticates with a runtime credential, validates the server and honours CORE
permissions. Protocol versions `0.3.0` and `0.4.0` are accepted. ASIS remains
fully operational when CORE is disabled or unreachable.

## Validation levels

1. Source compilation and unit tests: verified.
2. Package generation: performed by the release workflow.
3. Installer: not tested on physical Windows hardware here.
4. Runtime: macOS local tests plus CI on Linux/Windows/macOS.
5. Physical hardware (Windows 10, ARM64, macOS Intel): **not verified**.
