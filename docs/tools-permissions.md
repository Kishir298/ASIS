# Tools & Permissions

A.S.I.S. tools are controlled capabilities — the model never executes
shell commands or calls tools by itself. Application code routes
explicit tool requests through registry → router → executor.

## Tools

| Tool | Purpose | Permission | Status |
|---|---|---|---|
| `echo` | Repeat text back (empty input fails) | SAFE | Implemented |
| `current_time` | Current UTC date/time (`iso`, `timestamp`) | SAFE | Implemented |

No dangerous tools ship today. `ToolResult(success, data, error,
tool_name)` is frozen; non-`ToolResult` returns are wrapped.

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
`TOOL_DENIED` before anything runs. The confirmation mechanism is
real but currently unexercised — no shipped tool exceeds SAFE.

Helpers: `resolve_sandbox_path()` jails relative paths
(`SandboxViolation` on escape); `get_secret()`/`require_secret()`
read process secrets without hardcoding names (missing required
secret → `ConfigurationError`); generic `require_*` validators.
