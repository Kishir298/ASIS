# Future Integrations (C.O.R.E. / R.E.S.C.S.)

Both are **future boundaries** — A.S.I.S. runs fully without them.
Nothing in `asis/` imports C.O.R.E. or R.E.S.C.S. code.

## C.O.R.E. (future)

Intended relationship:

```text
A.S.I.S.
   ↓
CoreClient / CoreInterface   asis/integrations/core/client.py (ABC today)
   ↓
C.O.R.E.                     (separate project; adapter not yet provided)
```

`CoreClient` defines the contract (`send_message`, `request_service`,
`publish_event`, `get_resource`, `register_component`, `get_health`).
`MockCoreAdapter` is the runtime stand-in (in-memory messages, events,
resources; `request_service` always reports no handler). Do not invent
protocol details beyond this contract.

## R.E.S.C.S. (future)

Intended relationship:

```text
A.S.I.S.
   ↓
MemoryProvider / StorageProvider   (local SQLite today)
   ↓
Future RESCS Adapter               asis/integrations/rescs/adapter.py (placeholder)
   ↓
C.O.R.E.
   ↓
R.E.S.C.S.
```

`StorageClient` defines the contract (`store/retrieve/search/delete`).
The shipped adapter reports unavailable and raises `MemoryError`
directing callers to local memory. Rules: no direct cloud-DB coupling
in A.S.I.S., no fake cloud integration, integration arrives through
these abstractions.
