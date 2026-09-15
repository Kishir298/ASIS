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
| `core_status` | Local CORE connection snapshot | SAFE | Implemented (needs CORE manager) |
| `core_discover_devices` / `core_device_info` / `core_data_request` / `core_service_request` / `core_agent_request` / `core_send_to_device` | C.O.R.E. infrastructure operations | HIGH | Implemented, confirm-gated (needs CORE session) |

No dangerous tools ship today. `ToolResult(success, data, error,
tool_name)` is frozen; non-`ToolResult` returns are wrapped.

**Wiring status:** the tool subsystem is application-wired via
`AssistantApp` + `asis/app/actions.py` + `asis/app/native_tools.py`.
Preferred path is native function calling: the model receives tool
definitions derived from the active registry and returns structured
calls, each normalized to a validated `ToolRequest` (unknown tools,
malformed arguments, missing/wrong-typed/unknown parameters rejected)
and dispatched through `ToolRouter` → mandatory permission check →
`ToolExecutor`, bounded to `ASIS_TOOL_MAX_CALLS_PER_TURN` calls per
turn with a final plain generation. Fallback is the heuristic/explicit
path (structured JSON action in model output, or conservative
heuristics such as time questions → `current_time`) through the same
single-cycle `ToolRequest` dispatch. Results return explicitly to the
conversation and feed inference. Unknown tools, invalid arguments,
denials, timeouts and exceptions all become controlled failures, never
crashes. Model-generated `"confirmed"`/`"yes"` arguments are not
authorization and are rejected as unknown parameters before the
permission layer is reached. Direct `tool.execute()` (which bypasses
permissions/timeout) is never used by application code, and no
shell/subprocess path exists.

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
`TOOL_DENIED` before anything runs. Coding writes, command execution,
git mutations and all networked CORE tools sit at `HIGH`/`CRITICAL`,
so confirmation is exercised in coding mode (see `docs/coding.md`).

`PermissionManager` (`asis/permissions/manager.py`) is the named
object facade over these primitives (`allows` / `require` /
`needs_confirmation` / `level`); its `.authorizer` plugs directly into
`ToolExecutor`, so manager-gated and callable-gated execution behave
identically. The model can never bypass it: every CORE tool result is
redacted and size-bounded before reaching model context.

Helpers: `resolve_sandbox_path()` jails relative paths
(`SandboxViolation` on escape); `get_secret()`/`require_secret()`
read process secrets without hardcoding names (missing required
secret → `ConfigurationError`); generic `require_*` validators.
