# Tools & Permissions

A.S.I.S. tools are controlled capabilities — the model never executes
shell commands or calls tools by itself. Application code routes
explicit tool requests through registry → router → executor.

## Tools

| Tool | Purpose | Permission | Status |
|---|---|---|---|
| `echo` | Repeat text back (empty input fails) | SAFE | Implemented |
| `current_time` | Current UTC date/time (`iso`, `timestamp`) | SAFE | Implemented |
| `read_file` / `search_files` / `list_directory` | Workspace inspection (bounded) | SAFE–LOW | Implemented (coding mode) |
| `git_status` / `git_diff` | Read-only repo state (`--stat`/`--cached` only) | SAFE | Implemented (coding mode) |
| `write_file` | Exact workspace write | HIGH | Implemented, confirm-gated (coding mode) |
| `run_tests` / `run_command` | Allowlisted `pytest`/`python`/`git`, `shell=False` | HIGH | Implemented, confirm-gated (coding mode) |
| `git_add` | Stage workspace paths | HIGH | Implemented, confirm-gated (coding mode) |
| `git_commit` | Commit (never pushes) | CRITICAL | Implemented, confirm-gated (coding mode) |

No dangerous tools ship today. `ToolResult(success, data, error,
tool_name)` is frozen; non-`ToolResult` returns are wrapped.

**Wiring status:** the tool subsystem is application-wired via
`AssistantApp` + `asis/app/actions.py` (single inference/action cycle):
a structured JSON action in model output — or a conservative heuristic
(time questions → `current_time`) — becomes a validated `ToolRequest`
dispatched through `ToolRouter` → mandatory permission check →
`ToolExecutor`. Results return explicitly to the conversation and feed
one final inference pass. Unknown tools, invalid arguments, denials,
timeouts and exceptions all become controlled failures, never crashes.
Direct `tool.execute()` (which bypasses permissions/timeout) is never
used by application code, and no shell/subprocess path exists.

Mechanics (`asis/tools/`): `ToolRegistry` (thread-safe, rejects
duplicates with `ToolValidationError`), `ToolRouter` (unknown names
→ `failure("Tool not found")`, executor defaults to
`settings.tools.timeout`), `ToolExecutor` (authorization gate, then
run in a daemon thread joined on the timeout → `failure("Tool timed
out…")` on expiry; exceptions become failures; start/finish/deny
events published).

## Permissions (`asis/permissions/`)

Levels: `SAFE(0) < LOW < MODERATE < HIGH < CRITICAL`; confirmation
required at `HIGH+` via `request_confirmation()`, which auto-approves
when `settings.security.require_confirmation_for_dangerous` is false
and otherwise uses the console handler (literal `yes`; EOF/Ctrl+C
denies). Enforcement path: `Tool.authorizer` → executor denies with
`TOOL_DENIED` before anything runs. Coding writes, command execution
and git mutations all sit at `HIGH`/`CRITICAL`, so confirmation is
exercised in coding mode (see `docs/coding.md`).

Helpers: `resolve_sandbox_path()` jails relative paths
(`SandboxViolation` on escape); `get_secret()`/`require_secret()`
read process secrets without hardcoding names (missing required
secret → `ConfigurationError`); generic `require_*` validators.
