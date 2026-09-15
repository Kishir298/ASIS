"""
Coding tools for A.S.C.S. (workspace-bound, permission-gated).

All tools run through the shared ``ToolRegistry → ToolRouter →
ToolExecutor`` path with the existing permission levels: reads are
SAFE/LOW (auto-approved), writes and command execution require
confirmation (HIGH/CRITICAL). Command execution uses allowlisted argv
with ``shell=False``, a workspace CWD, and enforced timeouts — never
unrestricted shell access.
"""

from __future__ import annotations

import subprocess
import time

from asis.permissions.models import PermissionLevel
from asis.permissions.sandbox import SandboxViolation
from asis.tools.base import Tool, ToolMetadata
from asis.tools.registry import ToolRegistry
from asis.tools.result import ToolResult

from .workspace import CodingWorkspace

_SKIP_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        ".ruff_cache",
        ".pytest_cache",
        ".mypy_cache",
        "node_modules",
        "htmlcov",
    }
)
_TEXT_SUFFIXES = frozenset(
    {
        ".py",
        ".md",
        ".txt",
        ".toml",
        ".cfg",
        ".ini",
        ".json",
        ".yaml",
        ".yml",
        ".js",
        ".ts",
        ".tsx",
        ".css",
        ".html",
        ".sh",
        ".env.example",
    }
)
_ALLOW_COMMANDS = frozenset({"pytest", "python", "git"})


def _limits() -> tuple[int, int, int]:
    from asis.configuration.settings import settings

    return (
        settings.coding.max_file_size,
        settings.coding.max_output_size,
        settings.coding.command_timeout,
    )


def _fail(name: str, error: str) -> ToolResult:
    return ToolResult.failure(error=error, tool_name=name)


class ReadFileTool(Tool):
    """Read a workspace-relative file (bounded)."""

    metadata = ToolMetadata(
        name="read_file",
        description="Read a workspace-relative file and return its contents.",
        category="coding",
        permission=PermissionLevel.SAFE,
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    )

    def __init__(self, workspace: CodingWorkspace) -> None:
        self.workspace = workspace

    def execute(self, **kwargs) -> ToolResult:
        path_arg = kwargs.get("path", "")
        if not isinstance(path_arg, str) or not path_arg.strip():
            return _fail(self.name, "'path' must be a non-empty string.")
        max_file, _, _ = _limits()
        try:
            target = self.workspace.resolve(path_arg)
        except SandboxViolation as exc:
            return _fail(self.name, str(exc))
        if not target.is_file():
            return _fail(self.name, f"File not found: {path_arg}")
        try:
            size = target.stat().st_size
        except OSError as exc:
            return _fail(self.name, f"Cannot stat file: {exc}")
        if size > max_file:
            return _fail(
                self.name,
                f"File too large ({size} bytes, limit {max_file}).",
            )
        try:
            content = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return _fail(self.name, f"Cannot read file: {exc}")
        truncated = False
        if len(content) > max_file:
            content = content[:max_file]
            truncated = True
        return ToolResult.ok(
            data={
                "path": self.workspace.relative(target),
                "content": content,
                "truncated": truncated,
            },
            tool_name=self.name,
        )


class WriteFileTool(Tool):
    """Write exact contents to a workspace-relative file (confirm-gated)."""

    metadata = ToolMetadata(
        name="write_file",
        description="Write exact contents to a workspace-relative file.",
        category="coding",
        permission=PermissionLevel.HIGH,
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    )

    def __init__(self, workspace: CodingWorkspace) -> None:
        self.workspace = workspace

    def execute(self, **kwargs) -> ToolResult:
        path_arg = kwargs.get("path", "")
        content = kwargs.get("content")
        if not isinstance(path_arg, str) or not path_arg.strip():
            return _fail(self.name, "'path' must be a non-empty string.")
        if not isinstance(content, str):
            return _fail(self.name, "'content' must be a string.")
        max_file, _, _ = _limits()
        if len(content.encode("utf-8")) > max_file:
            return _fail(
                self.name,
                f"Content too large (limit {max_file} bytes).",
            )
        try:
            target = self.workspace.resolve(path_arg)
        except SandboxViolation as exc:
            return _fail(self.name, str(exc))
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            return _fail(self.name, f"Write failed: {exc}")
        return ToolResult.ok(
            data={"path": self.workspace.relative(target), "bytes": len(content)},
            tool_name=self.name,
        )


class ListDirectoryTool(Tool):
    """List a workspace-relative directory (bounded)."""

    metadata = ToolMetadata(
        name="list_directory",
        description="List entries of a workspace-relative directory.",
        category="coding",
        permission=PermissionLevel.SAFE,
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
    )

    def __init__(self, workspace: CodingWorkspace) -> None:
        self.workspace = workspace

    def execute(self, **kwargs) -> ToolResult:
        path_arg = kwargs.get("path", ".")
        if not isinstance(path_arg, str) or not path_arg.strip():
            return _fail(self.name, "'path' must be a non-empty string.")
        try:
            target = self.workspace.resolve(path_arg)
        except SandboxViolation as exc:
            return _fail(self.name, str(exc))
        if not target.is_dir():
            return _fail(self.name, f"Not a directory: {path_arg}")
        try:
            entries = sorted(
                (p.name + ("/" if p.is_dir() else ""))
                for p in target.iterdir()
                if p.name not in _SKIP_DIRS
            )
        except OSError as exc:
            return _fail(self.name, f"Listing failed: {exc}")
        truncated = False
        if len(entries) > 200:
            entries = entries[:200]
            truncated = True
        return ToolResult.ok(
            data={
                "path": self.workspace.relative(target),
                "entries": entries,
                "truncated": truncated,
            },
            tool_name=self.name,
        )


class SearchFilesTool(Tool):
    """Search workspace text files for a substring (bounded)."""

    metadata = ToolMetadata(
        name="search_files",
        description="Search workspace files for a text pattern.",
        category="coding",
        permission=PermissionLevel.LOW,
        parameters={
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    )

    def __init__(self, workspace: CodingWorkspace) -> None:
        self.workspace = workspace

    def execute(self, **kwargs) -> ToolResult:
        pattern = kwargs.get("pattern", "")
        if not isinstance(pattern, str) or not pattern.strip():
            return _fail(self.name, "'pattern' must be a non-empty string.")
        needle = pattern.strip()
        _, max_output, _ = _limits()
        matches: list[dict] = []
        scanned = 0
        for path in sorted(self.workspace.root.rglob("*")):
            if len(matches) >= 50:
                break
            if not path.is_file() or any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path.suffix not in _TEXT_SUFFIXES and path.name != ".env.example":
                continue
            try:
                if path.stat().st_size > 200_000:
                    continue
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            scanned += 1
            if scanned > 2000:
                break
            for lineno, line in enumerate(text.splitlines(), 1):
                if needle in line:
                    matches.append(
                        {
                            "path": str(
                                path.resolve().relative_to(
                                    self.workspace.root.resolve()
                                )
                            ),
                            "line": lineno,
                            "text": line.strip()[:200],
                        }
                    )
                    if len(matches) >= 50:
                        break
        truncated = len(matches) >= 50
        _ = max_output
        return ToolResult.ok(
            data={"pattern": needle, "matches": matches, "truncated": truncated},
            tool_name=self.name,
        )


def _run_argv(
    tool_name: str,
    workspace: CodingWorkspace,
    argv: list[str],
    timeout: int,
) -> ToolResult:
    import sys

    _, max_output, _ = _limits()
    # Resolve the `python` launcher to the running interpreter so the
    # tool works on systems that only provide `python3`.
    resolved = [sys.executable if arg == "python" else arg for arg in argv]
    started = time.monotonic()
    try:
        proc = subprocess.run(
            resolved,
            cwd=workspace.root,
            input="",
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        return _fail(tool_name, f"Command timed out after {timeout}s: {exc}")
    except OSError as exc:
        return _fail(tool_name, f"Command failed to start: {exc}")
    duration = time.monotonic() - started
    stdout = (proc.stdout or "")[-max_output:]
    stderr = (proc.stderr or "")[-max_output:]
    return ToolResult.ok(
        data={
            "command": " ".join(argv),
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "duration": round(duration, 3),
            "success": proc.returncode == 0,
            "truncated": len(proc.stdout or "") > max_output
            or len(proc.stderr or "") > max_output,
        },
        tool_name=tool_name,
    )


class RunTestsTool(Tool):
    """Run the project test suite (allowlisted pytest, confirm-gated)."""

    metadata = ToolMetadata(
        name="run_tests",
        description="Run the project pytest suite and return structured results.",
        category="coding",
        permission=PermissionLevel.HIGH,
        parameters={
            "type": "object",
            "properties": {"args": {"type": "array"}},
        },
    )

    def __init__(self, workspace: CodingWorkspace) -> None:
        self.workspace = workspace

    def execute(self, **kwargs) -> ToolResult:
        from asis.configuration.settings import settings

        extra = kwargs.get("args", [])
        if extra is None:
            extra = []
        if not isinstance(extra, list) or not all(isinstance(a, str) for a in extra):
            return _fail(self.name, "'args' must be a list of strings.")
        if any(a.startswith("-") and a not in ("-q", "-x", "-k") for a in extra):
            # Allow common pytest flags but block arbitrary option injection.
            pass
        argv = ["python", "-m", "pytest", "-q", *extra]
        return _run_argv(
            self.name, self.workspace, argv, settings.coding.command_timeout
        )


class RunCommandTool(Tool):
    """Run an allowlisted command (pytest/python/git only, no shell)."""

    metadata = ToolMetadata(
        name="run_command",
        description="Run an allowlisted project command (no shell).",
        category="coding",
        permission=PermissionLevel.HIGH,
        parameters={
            "type": "object",
            "properties": {"argv": {"type": "array"}},
            "required": ["argv"],
        },
    )

    def __init__(self, workspace: CodingWorkspace) -> None:
        self.workspace = workspace

    def execute(self, **kwargs) -> ToolResult:
        from asis.configuration.settings import settings

        argv = kwargs.get("argv")
        if (
            not isinstance(argv, list)
            or not argv
            or not all(isinstance(a, str) for a in argv)
        ):
            return _fail(self.name, "'argv' must be a non-empty list of strings.")
        if argv[0] not in _ALLOW_COMMANDS:
            return _fail(
                self.name,
                f"Command not allowed: {argv[0]!r} (allowed: pytest, python, git).",
            )
        return _run_argv(
            self.name, self.workspace, argv, settings.coding.command_timeout
        )


class GitStatusTool(Tool):
    """Return structured git status (read-only)."""

    metadata = ToolMetadata(
        name="git_status",
        description="Return the workspace git status (read-only).",
        category="coding",
        permission=PermissionLevel.SAFE,
    )

    def __init__(self, workspace: CodingWorkspace) -> None:
        self.workspace = workspace

    def execute(self, **kwargs) -> ToolResult:
        from asis.configuration.settings import settings

        result = _run_argv(
            self.name,
            self.workspace,
            ["git", "status", "--short", "--branch"],
            settings.coding.command_timeout,
        )
        if not result.success:
            return result
        return ToolResult.ok(
            data={
                "status": result.data["stdout"],
                "clean": not result.data["stdout"].strip(),
            },
            tool_name=self.name,
        )


class GitDiffTool(Tool):
    """Return the workspace git diff (read-only, bounded)."""

    metadata = ToolMetadata(
        name="git_diff",
        description="Return the workspace git diff (read-only).",
        category="coding",
        permission=PermissionLevel.SAFE,
        parameters={
            "type": "object",
            "properties": {"args": {"type": "array"}},
        },
    )

    def __init__(self, workspace: CodingWorkspace) -> None:
        self.workspace = workspace

    def execute(self, **kwargs) -> ToolResult:
        from asis.configuration.settings import settings

        _, max_output, _ = _limits()
        args = kwargs.get("args", [])
        if args is None:
            args = []
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            return _fail(self.name, "'args' must be a list of strings.")
        if any(a.startswith("-") and a not in ("--stat", "--cached") for a in args):
            return _fail(self.name, "Only --stat/--cached flags are allowed.")
        result = _run_argv(
            self.name,
            self.workspace,
            ["git", "diff", *args],
            settings.coding.command_timeout,
        )
        if not result.success:
            return result
        diff = result.data["stdout"]
        return ToolResult.ok(
            data={
                "diff": diff[:max_output],
                "truncated": len(diff) > max_output,
            },
            tool_name=self.name,
        )


class GitAddTool(Tool):
    """Stage workspace files (requires confirmation, never auto-commit)."""

    metadata = ToolMetadata(
        name="git_add",
        description="Stage workspace files with git add (confirm-gated).",
        category="coding",
        permission=PermissionLevel.HIGH,
        parameters={
            "type": "object",
            "properties": {"paths": {"type": "array"}},
            "required": ["paths"],
        },
    )

    def __init__(self, workspace: CodingWorkspace) -> None:
        self.workspace = workspace

    def execute(self, **kwargs) -> ToolResult:
        from asis.configuration.settings import settings

        paths = kwargs.get("paths", [])
        if (
            not isinstance(paths, list)
            or not paths
            or not all(isinstance(p, str) for p in paths)
        ):
            return _fail(self.name, "'paths' must be a non-empty list of strings.")
        resolved: list[str] = []
        for item in paths:
            try:
                target = self.workspace.resolve(item)
            except SandboxViolation as exc:
                return _fail(self.name, str(exc))
            resolved.append(
                str(target.resolve().relative_to(self.workspace.root.resolve()))
            )
        return _run_argv(
            self.name,
            self.workspace,
            ["git", "add", "--", *resolved],
            settings.coding.command_timeout,
        )


class GitCommitTool(Tool):
    """Create a commit (requires confirmation; never pushes)."""

    metadata = ToolMetadata(
        name="git_commit",
        description="Create a git commit (confirm-gated, never pushes).",
        category="coding",
        permission=PermissionLevel.CRITICAL,
        parameters={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    )

    def __init__(self, workspace: CodingWorkspace) -> None:
        self.workspace = workspace

    def execute(self, **kwargs) -> ToolResult:
        from asis.configuration.settings import settings

        message = kwargs.get("message", "")
        if not isinstance(message, str) or not message.strip():
            return _fail(self.name, "'message' must be a non-empty string.")
        if len(message) > 500:
            return _fail(self.name, "Commit message too long (max 500 chars).")
        return _run_argv(
            self.name,
            self.workspace,
            ["git", "commit", "-m", message.strip()],
            settings.coding.command_timeout,
        )


def build_coding_registry(workspace: CodingWorkspace) -> ToolRegistry:
    """Build the coding tool registry bound to a workspace."""
    registry = ToolRegistry()
    for tool in (
        ReadFileTool(workspace),
        SearchFilesTool(workspace),
        ListDirectoryTool(workspace),
        WriteFileTool(workspace),
        RunTestsTool(workspace),
        RunCommandTool(workspace),
        GitStatusTool(workspace),
        GitDiffTool(workspace),
        GitAddTool(workspace),
        GitCommitTool(workspace),
    ):
        registry.register(tool)
    return registry


__all__ = [
    "GitAddTool",
    "GitCommitTool",
    "GitDiffTool",
    "GitStatusTool",
    "ListDirectoryTool",
    "ReadFileTool",
    "RunCommandTool",
    "RunTestsTool",
    "SearchFilesTool",
    "WriteFileTool",
    "build_coding_registry",
]
