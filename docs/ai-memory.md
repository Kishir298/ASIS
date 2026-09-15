# AI, Conversation, Memory

## Providers (`asis/ai/providers/`)

Abstract contract `AIProvider`: `name`, `model`, `chat(messages)`,
`stream_chat(messages)`, `available()`. Two implementations exist:

| Provider | Status | Details |
|---|---|---|
| `mock` | Implemented (tests/dev) | `MockAIProvider`: scripted responses, `fail`/`delay` knobs, offline; optional scripted `tool_sequences` enable native-call tests |
| `ollama` | Implemented (optional dep) | Local server: model/host/timeout/**temperature**/**retries** from settings; `temperature` sent as chat `options` only when set; `available()` probes `/api/tags`; native function calling via `/api/chat` `tools` (`supports_native_tools=True`, model-dependent) |

No Hugging Face or cloud providers exist — anything else is future.

`create_provider()` (`asis/ai/manager.py`) selects by
`settings.ai.provider`; unknown names raise `InferenceError`.
`AIManager` wraps chat/streaming with `AI_INFERENCE_STARTED/FINISHED/
FAILED` events. The CLI provider helper passes model/host/timeout/
temperature/retries from settings, matching the manager path.

## Inference (`asis/ai/inference.py`)

```text
Input → Context Construction → Prompt Construction → Model Inference
→ Response Parsing → Final Response
```

`InferenceEngine.generate()` = interrupt-check → assemble messages →
single `manager.chat()` → interrupt-check. No retries at this layer
(retries live in `OllamaProvider.chat`), no tool invocation, no
agentic loop. Streaming variant yields per-chunk with per-chunk
cancellation. All failures surface as `InferenceError`.

## Native function calling (`asis/ai/tool_schemas.py`, `asis/app/native_tools.py`)

The model may request tools through the provider-native protocol
instead of text heuristics. Tool definitions are derived
deterministically from the active-mode `ToolRegistry`
(`ToolDefinition`: name, description, JSON-Schema parameters; sorted,
secret-vocabulary rejected). `OllamaProvider.chat_with_tools()` renders
them into `/api/chat` `tools` and parses `message.tool_calls` into
`NativeToolCall` records (malformed entries dropped, never raised);
`AIProvider.supports_native_tools` advertises the capability (default
`False`, so incapable providers use the heuristic fallback).

`AssistantApp.chat()` order per turn: explicit `core:` command →
native loop (definitions → validate each call against its schema →
`ToolRouter` → `PermissionManager` → `ToolExecutor`, at most
`ASIS_TOOL_MAX_CALLS_PER_TURN` validated calls, then a final plain
generation) → heuristic fallback (`parse_tool_request`, unchanged
single cycle). Both paths converge on the same `ToolRequest` and the
same permission boundary; the model only requests, A.S.I.S. authorizes.
`ASIS_AI_NATIVE_TOOLS` (`auto`/`true`/`false`, default `auto`) controls
the attempt; small local models that ignore `tools` simply fall back.
Limitations: multi-step depth is bounded by configuration, and native
support varies by Ollama model — fallback coverage is intentional, not
a gap.

## Conversation vs memory

```text
Conversation Context  ≠  Permanent Memory
   (per-session, bounded)      (SQLite, persistent)
```

- `ConversationSession`: in-memory turn list, tail-trimmed to
  `max_history` (no token counting).
- `ContextAssembler`: system prompt = identity + memory text truncated
  to `context_char_limit` + fixed rules; history tail-sliced to
  `max_context_messages`. History itself is never char-truncated.

**Wiring status:** `ConversationSession` + `ContextAssembler` +
`InferenceEngine` are wired into the normal CLI and voice paths via
`AssistantApp` (`asis/app/assistant.py`), which owns one session per
REPL/voice run. Each turn persists user + assistant messages (bounded
by `max_history` / `max_context_messages`); failed inference preserves
state without inserting a phantom assistant turn; the `inference`
interrupt scope stays cancellable.

## Memory (`asis/memory/`)

| Piece | Status |
|---|---|
| `MemoryManager` (remember/recall/search/forget) | Implemented |
| SQLite file storage (`memories` table, category/importance index) | Implemented |
| LIKE search (`importance DESC, created_at DESC`) | Implemented (no embeddings/vector search) |
| Auto-extraction (`my name is…`, `I like…`, `I'm building…`) | Implemented (`asis/app/memories.py`, invoked by chat CLI) |
| Recall into prompts | Implemented + wired — `search_context()` keyword retrieval injected via `ContextAssembler`; empty → normal inference; failure → log + continue |
| Cloud sync | Future — R.E.S.C.S. responsibility, not A.S.I.S. |

Database lives at `settings.paths.memory / settings.memory.database_name`
(default `memory.db`); only the `local` provider exists
(`build_memory()` rejects anything else with `ConfigurationError`).
Tests use a temp-DB fixture; no cloud, no internet.
