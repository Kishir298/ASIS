"""
Filesystem sandbox helpers for Forza.
"""

from __future__ import annotations

from pathlib import Path


class SandboxViolation(PermissionError):
    """Raised when an operation escapes its permitted directory."""


def resolve_sandbox_path(
    base_directory: Path,
    requested_path: Path,
) -> Path:
    """
    Resolve a requested path and ensure it remains inside the sandbox.
    """
    base = base_directory.expanduser().resolve()
    target = requested_path.expanduser()

    if not target.is_absolute():
        target = base / target

    target = target.resolve()

    try:
        target.relative_to(base)
    except ValueError as exc:
        raise SandboxViolation(
            f"Path escapes sandbox: {target}"
        ) from exc

    return target