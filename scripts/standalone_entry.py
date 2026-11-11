"""Frozen-executable entry point for A.S.I.S. (used only by PyInstaller)."""

from asis.cli.main import entry

if __name__ == "__main__":
    raise SystemExit(entry())
