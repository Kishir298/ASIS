# A.S.I.S. — A Smart Intelligence System

Local-first assistant: local LLM (Ollama) + conversation/memory + tool
system + voice pipeline. C.O.R.E. is an **optional** infrastructure
uplink — A.S.I.S. runs fully standalone without it.

## Standalone vs +C.O.R.E.

```text
Standalone:  user -> CLI/voice -> ToolRouter -> local tools -> Ollama (localhost)
+C.O.R.E.:   user -> CLI/voice -> ToolRouter -> CORE tools -> adapter
             -> CORE-CLIENT -> TCP+TLS -> CORE-HOST -> response -> local LLM
```

Intelligence stays local. CORE provides infrastructure (transport,
routing, services, device registry) — never AI inference. Normal prompts
and history are never sent to the host.

## Quick start (standalone)

```bash
cd ASIS
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements/base.txt -r requirements/ai.txt
.venv/Scripts/python -m pytest -q            # 91 passed
.venv/Scripts/python -m asis --message "hello" --provider mock
```

## Optional C.O.R.E. uplink

1. Install CORE-CLIENT so `client.core_device_client` is importable
   (sibling repo or `PYTHONPATH`), keeping the repos unmerged.
2. Provision the device on CORE-HOST (`provision-device`), copy only the
   public cert (`core.crt`) to the Mac — never `core.key`/`.pfx`.
3. Configure (see `.env.example`; credential is runtime-only, never filed):

```bash
ASIS_CORE_ENABLED=true
ASIS_CORE_HOST=192.168.1.67
ASIS_CORE_PORT=5000
ASIS_CORE_CA_FILE=C:\path\to\core.crt
```

4. Start A.S.I.S.; it connects (`CORE_HANDSHAKE` -> auth ->
   `DEVICE_REGISTER` -> online) via `CoreConnectionManager`
   (`asis/integrations/core/connection.py`), a plain `RuntimeComponent`
   of the existing `ASISRuntime`. When disabled/unreachable, everything
   local keeps working and CORE tools fail cleanly with
   `CORE_UNAVAILABLE`.

## Architecture (boundary)

```text
A.S.I.S. -> integrations/core/ (models, protocol, client ABC,
adapter.RealCoreAdapter, connection.CoreConnectionManager, errors)
-> CORE-CLIENT (CoreDeviceClient.request/device_info/service_request/...)
-> TCP+TLS -> CORE-HOST
```

Rules: no `from core.communication import ...` inside `asis/` (tested);
device identity is CORE-authoritative (`device_id/identity_id/join_name`
+ ephemeral `session_token/connection_id`, never persisted/logged);
TLS 1.2+, no plaintext LAN fallback; session expiry follows the
host-authoritative lease — reconnect reuses the in-memory credential for
a fresh session, never manufactures one.

## CORE tools (existing tool system only)

Registered via `register_core_tools(registry, manager)` onto the shared
`ToolRegistry`: `core_discover_devices`, `core_device_info`,
`core_status` (SAFE), `core_service_request`, `core_agent_request`
(all network tools HIGH — confirmation-gated). Flow:
`LLM -> ToolRouter -> PermissionManager(authorizer) -> ToolExecutor ->
adapter -> CORE-CLIENT -> HOST`. Results are redacted (`session_token`,
`credential`, `connection_id`, ...) and truncated to 8 000 chars before
the model. Voice transcripts and any future coding mode use this same
Router path — there is no separate voice→CORE client.

## Offline / failure behavior

Connection loss, expiry, or auth failure marks the session
`DISCONNECTED`, destroys ephemeral state, preserves local
conversation/memory/tools/voice/shutdown, and retries with bounded
backoff (`ASIS_CORE_RECONNECT_DELAY` x attempt, max 3 retries,
stop-aware). Shutdown stays bounded (`ASIS_SHUTDOWN_TIMEOUT`).

## Tests

```bash
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m pytest tests/test_core_config.py tests/test_core_adapter.py \
  tests/test_core_tools.py tests/test_core_lifecycle.py tests/test_core_integration.py -q
```

## Manual LAN validation (NOT YET PERFORMED)

Windows: start CORE-HOST (TLS listener). Mac: provision device,
configure CORE-CLIENT, authenticate, register, confirm online; start
A.S.I.S., hold a local-LLM conversation, invoke a CORE tool, confirm the
host sees the request and the response returns; kill the host, confirm
local operation survives; restore host, confirm bounded reconnect;
shutdown and confirm credentials are destroyed. Do not mark PASS until
physically performed.
