# Phase 1F-00: Agent Dev-Only Run / SSE Scope, Contract & Safety Boundary Freeze

**Status:** Completed
**Date:** 2026-06-09
**Branch:** dev-huangruibang
**Base commit:** 6cb05c8dadfa70236f1b7affb2622b928dfa4288
**Scope:** Documentation-only audit and contract freeze
**OpenAPI paths:** 23 (unchanged)

---

## 1. Status

Phase 1F-00 is a **documentation-only scope freeze**. No code was modified, no APIs were registered, no LLM calls were made, no sessions were written, no memory was modified, no SSE was implemented, no tools were executed.

Phase 1F implementation remains **Not Started**.

---

## 2. Background

Phase 1F introduces the first real Agent Run capability in the Dev WebUI — enabling LLM calls, SSE streaming, and session persistence in a strictly dev-only environment with tools disabled and auto-memory disabled. This requires comprehensive audits of:

- The complete Agent Run call chain from entry to persistence
- Streaming callback mechanisms and thread safety
- Cancellation propagation and orphan thread handling
- Session/message persistence ownership (no double-writes)
- Concurrency model and same-session run isolation
- Run lifecycle, state machine, and registry design
- SSE protocol, event sequencing, and reconnection strategy
- Kill switch, environment isolation, and confirmation model
- Rate limits, cost controls, and audit trail
- Tool boundary enforcement and memory writer disable verification

---

## 3. Current Baseline

| Metric | Value |
|--------|-------|
| OpenAPI paths | 23 |
| Agent capability | Status + Prompt Preview + Run Dry-Run (no real run) |
| Prompt Preview routes | 2 (`/agent/status`, `/agent/prompt/preview`, `/agent/run/dry-run`) |
| Agent Run capability | None |
| SSE capability | None |
| Tool execution capability | None |
| Session write capability | None (Agent Runtime writes in CLI/gateway only) |
| Memory write capability | Memory Writer dry-run (3 routes) + Dev-only execute |
| Review Queue | Read-only + Dry-run + Dev-only Execute |
| Kill switch for Agent Run | None (not yet implemented) |

---

## 4. Audit Sources

### Source Code Files Audited

| File | Purpose |
|------|---------|
| `run_agent.py` | AIAgent class, constructor, persistence, streaming, interrupt, chat (~12k LOC) |
| `agent/agent_init.py` | Agent initialization, provider wiring, callback setup (~84k LOC) |
| `agent/conversation_loop.py` | Main `run_conversation()` turn loop (~271k LOC) |
| `agent/chat_completion_helpers.py` | `interruptible_api_call()`, completion handling |
| `agent/runtime_memory_writer.py` | Auto memory evaluation and writing (~37k LOC) |
| `agent/memory_review_queue.py` | Review queue persistence and lifecycle (~33k LOC) |
| `hermes_state.py` | SessionDB, append_message, message persistence |
| `model_tools.py` | Tool discovery, dispatch, handle_function_call |
| `tools/registry.py` | Tool registration and execution dispatch |
| `toolsets.py` | Toolset definitions, `_HERMES_CORE_TOOLS` |
| `gateway/run.py` | Gateway agent invocation |
| `hermes_cli/dev_web_api.py` | Dev Web API router |
| `hermes_cli/dev_web_agent_service.py` | Agent status service (read-only) |
| `hermes_cli/dev_web_agent_preview_service.py` | Agent prompt preview service |
| `hermes_cli/dev_web_schemas.py` | Dev Web DTOs |
| `hermes_cli/dev_web_errors.py` | Error codes |
| `hermes_cli/dev_web_config.py` | Dev Web config |

### Planning Documents Reviewed

- `docs/webui/phase-1-00-planning-and-scope.md`
- `docs/webui/phase-1-implementation-plan.md`
- `docs/webui/phase-0e-06-phase-1-safety-boundary.md`
- `docs/webui/phase-1e-00-agent-prompt-preview-scope.md`
- `docs/webui/phase-1e-agent-prompt-preview.md`
- `docs/webui/phase-1c-review-queue-execute.md`
- `docs/webui/phase-1c-post-approve-execute-test-closure.md`
- `docs/webui/dev-web-api-v1.md`
- `docs/webui/openapi/dev-web-api-v1.yaml`
- `CLAUDE.md` — SSE Constraints, Session Persistence Constraints, P0 Access Control

---

## 5. Agent Run Call Graph

### Complete Call Chain (source-audited)

```
Web API POST /agent/runs
  → Run Service (new, Phase 1F)
    → Kill Switch Check                                    [Pure computation]
    → Dev-only Environment Guard                           [Pure computation]
    → Run Registry Create                                  [In-memory write]
    → Run Registry Session Lock                            [In-memory write]
    → Thread Pool Dispatch                                 [Thread side effect]
      → Agent Initialization
        → config = load_config_readonly()                  [Read-only file]
        → AIAgent(...)                                     [Object creation]
          → init_agent()                                   [Object creation]
            → Provider client creation                     [Read config, create SDK client]
            → API Key loading from .env                    [Read env var]
            → Tool registry (empty toolset)                [Object creation]
            → session_db = SessionDB(hermes_home)          [Read/Write DB]
            → stream_delta_callback = bridge_callback      [Callback assignment]
            → _stream_callback = None                       [Explicit None]
          → run_conversation(user_message)
            → _ensure_db_session()                         [DB write: create_session row]
            → Set _execution_thread_id                     [Thread state]
            → Memory context loading                       [Read-only file]
            → Prompt assembly                              [Pure computation]
            → _interruptible_api_call()                    [Network: LLM Provider Request]
              → stream=True                                [Network side effect]
              → For each chunk: _fire_stream_delta(text)   [Callback: bridge → Queue]
                → stream_delta_callback(text)              [Callback fires]
                → _stream_callback(text)                   [Only if not None]
              → On interrupt: check _interrupt_requested   [Thread-safe flag]
            → Tool loop (Phase 1F: DISABLED)
              → tools=[] in API kwargs                     [No tool schema sent]
              → If provider returns tool_call: ERROR       [Blocked by design]
            → Final response assembly                      [Pure computation]
            → _persist_session(messages)                   [DB write]
              → _flush_messages_to_session_db(messages)    [DB write: append_message per msg]
            → maybe_auto_write_memory()                    [Phase 1F: DISABLED by config]
            → enqueue_review_item()                        [Phase 1F: DISABLED by config]
            → Clear _stream_callback = None                [Cleanup]
            → clear_interrupt()                            [Cleanup]
            → Return result dict                           [Pure computation]
      → Bridge: Queue → SSE events                         [Thread → Async bridge]
      → Run Registry Update: status → COMPLETED            [In-memory write]
    → SSE terminal event emitted                           [Network: SSE]
    → Run Registry TTL timer starts                        [In-memory timer]
```

### Side Effect Classification

| Step | Side Effect Type | Phase 1F Behavior |
|------|-----------------|-------------------|
| Provider request | Network (LLM API) | **Enabled** — sole purpose of Phase 1F |
| stream_delta_callback | Thread → Queue bridge | **Enabled** — via SSE bridge |
| _stream_callback | None | **Disabled** — explicitly set to None |
| _ensure_db_session | DB write (create_session) | **Enabled** — Agent Runtime owns this |
| _flush_messages_to_session_db | DB write (append_message) | **Enabled** — Agent Runtime owns this |
| maybe_auto_write_memory | File/DB write | **Disabled** — config default is off |
| enqueue_review_item | File/DB write | **Disabled** — config default is off |
| Tool dispatch | Various side effects | **Disabled** — tools=[] in API call |
| _save_session_log | File write (JSON log) | **Enabled** — part of Agent Runtime persistence |

---

## 6. Agent Initialization Audit

### AIAgent Constructor (source: `run_agent.py:342` → `agent/agent_init.py`)

| Parameter | Phase 1F Value | Notes |
|-----------|---------------|-------|
| `base_url` | From config | Dev config only |
| `api_key` | From .env | Dev API key only |
| `provider` | From config | e.g., "zai" |
| `model` | From config or override | From allowlist |
| `session_id` | Explicit existing session | Must pre-exist in dev-home |
| `session_db` | `SessionDB(hermes_home=dev_home)` | Dev-home only |
| `stream_delta_callback` | Bridge callback (Queue) | SSE bridge function |
| `_stream_callback` | `None` | **Must remain None** |
| `enabled_toolsets` | Empty or None | **No tools** |
| `disabled_toolsets` | All | **Extra safety** |
| `skip_memory` | `True` or config-level disable | No memory injection |
| `max_tokens` | From config or override | Capped by safety limit |
| `hermes_home` | `/Users/huangruibang/Code/hermes-home-dev` | Dev-only |
| `quiet_mode` | `True` | Suppress CLI output |
| `tools` | `[]` or `None` | **No tool schemas** |

### Provider Client Creation (source: `agent/agent_init.py:800+`)

- Provider client created via `resolve_provider_client()` from `agent/agent_runtime_helpers.py`
- API key read from environment variable (provider-specific, e.g., `ZAI_API_KEY`)
- Client created as `openai.OpenAI(api_key=..., base_url=..., timeout=...)`
- Timeout defaults from config or `_provider_timeout` setting
- **Thread safety:** OpenAI SDK client is thread-safe for concurrent read operations

### SessionDB Initialization (source: `run_agent.py:481+`)

- `SessionDB()` created with default `hermes_home` from `get_hermes_home()`
- For Phase 1F: must pass explicit `session_db=SessionDB(hermes_home=dev_home)`
- `_ensure_db_session()` creates the session row on first use per turn
- `_session_db_created` flag prevents double creation

### Callback Wiring (source: `agent/agent_init.py`, `run_agent.py:378+`)

- `stream_delta_callback` set in AIAgent constructor — persists across turns
- `_stream_callback` set per-call in `run_conversation()` (line 428) — cleared after each call (line 4814)
- Both callbacks fire from `_fire_stream_delta()` (line 3884) if not None
- **Phase 1F decision:** Only `stream_delta_callback` is used. `_stream_callback` must be `None`.

---

## 7. Persistence Ownership (Re-confirmed from Phase 1E-00)

### Frozen Decision: Agent Runtime Is Sole Persistence Owner

**Option A (confirmed):** Agent Runtime auto-persists via `_persist_session()` → `_flush_messages_to_session_db()`. Web API must NOT write sessions/messages directly.

### Persistence Points in run_conversation() (source-audited)

| Exit Path | Persistence Call | Location |
|-----------|-----------------|----------|
| Normal completion (final_response) | `_persist_session(messages)` | conversation_loop.py |
| Interrupt detected | `_persist_session(messages)` | conversation_loop.py |
| Max iterations reached | `_persist_session(messages)` | conversation_loop.py |
| Error during API call | `_persist_session(messages)` | conversation_loop.py |
| Context compression | `_persist_session(messages)` | conversation_loop.py |
| Tool guardrail halt | `_persist_session(messages)` | conversation_loop.py |
| All other exits | `_persist_session(messages)` | conversation_loop.py |

### Duplicate-Write Prevention (source: `run_agent.py:1507-1564`)

- `_last_flushed_db_idx` tracks which messages have been flushed
- Repeated calls to `_flush_messages_to_session_db()` only write new messages
- This prevents duplicate writes even if `_persist_session()` is called multiple times

### Message Type Persistence Matrix

| Message Type | Written by | Function | Timing | Failure Behavior | Duplicate Risk |
|-------------|-----------|----------|--------|-----------------|---------------|
| User Message | Agent Runtime | `_flush_messages_to_session_db()` | During `_persist_session()` | Warning logged, session continues | Low: idx tracking |
| Assistant Final | Agent Runtime | `_flush_messages_to_session_db()` | During `_persist_session()` | Warning logged, session continues | Low: idx tracking |
| Partial Assistant | Agent Runtime | `_flush_messages_to_session_db()` | Only if turn ends mid-stream | Warning logged | Low: idx tracking |
| Tool Call | Agent Runtime | `_flush_messages_to_session_db()` | N/A (Phase 1F: tools disabled) | N/A | N/A |
| Tool Result | Agent Runtime | `_flush_messages_to_session_db()` | N/A (Phase 1F: tools disabled) | N/A | N/A |
| Reasoning Metadata | Agent Runtime | `_flush_messages_to_session_db()` | With assistant message | Warning logged | Low: idx tracking |
| Cancelled Response | Agent Runtime | `_flush_messages_to_session_db()` | During `_persist_session()` on interrupt | Warning logged | Low: idx tracking |
| Failed Response | Agent Runtime | `_flush_messages_to_session_db()` | During `_persist_session()` on error | Warning logged | Low: idx tracking |

### Frozen Constraint

```text
Web API MUST NOT call:
  - session_db.create_session()
  - session_db.append_message()
  - session_db.update_message()
  - session_db.delete_session()
  - Any SessionDB write method

Web API ONLY:
  - Starts the Run (creates thread)
  - Forwards SSE events from stream_delta_callback bridge
  - Tracks Run state in Run Registry
```

---

## 8. Streaming Callback Audit (Re-confirmed from Phase 1E-00)

### Callback Architecture (source: `run_agent.py:3842-3891`)

```python
# _fire_stream_delta fires BOTH callbacks if not None:
callbacks = [cb for cb in (self.stream_delta_callback, self._stream_callback) if cb is not None]
for cb in callbacks:
    cb(text)
```

### Phase 1F Streaming Decision

| Callback | Registration Time | Scope | Phase 1F |
|----------|------------------|-------|----------|
| `stream_delta_callback` | Constructor (`AIAgent.__init__`) | Instance-level, persistent | **USED** — SSE bridge |
| `_stream_callback` | Per-call (`run_conversation()` line 428) | Per-invocation, cleared after | **MUST BE None** |

### Delta Semantics

- `stream_delta_callback(text)` receives **incremental deltas** (not cumulative text)
- `stream_delta_callback(None)` signals end-of-stream for display purposes
- Text passes through think-scrubber and context-scrubber before delivery
- `_stream_needs_break` flag prepends `\n\n` before first post-tool text

### SSE Bridge Pattern (CLAUDE.md Section: SSE Constraints)

```text
Synchronous Agent Thread:
  stream_delta_callback(text) → loop.call_soon_threadsafe(queue.put_nowait, event)

Async SSE Response:
  async for event in queue: yield SSE formatted event
```

Key rules (from CLAUDE.md):
1. `run_conversation()` runs in thread pool via `asyncio.get_running_loop().run_in_executor(None, ...)`
2. Bridge: synchronous callback writes to `asyncio.Queue` via `loop.call_soon_threadsafe(queue.put_nowait, event)`
3. **Single streaming entry:** Only `stream_delta_callback` registered, `_stream_callback = None`
4. Done event emitted when background Future completes
5. Error propagation: exception caught → `error` SSE event
6. Client disconnect: `AIAgent.interrupt()` called
7. Single-generation constraint: at most one generation per session

---

## 9. Concurrency Audit

### Same-Session Concurrent Run Risk (source-audited)

If two Runs target the same `session_id` simultaneously:

| Risk | Severity | Explanation |
|------|----------|-------------|
| History read race | **HIGH** | Both load same conversation_history, then both append conflicting messages |
| Message order corruption | **HIGH** | `_flush_messages_to_session_db()` writes interleave |
| Duplicate persistence | **HIGH** | `_last_flushed_db_idx` tracking breaks under concurrent access |
| Provider response cross-contamination | **MEDIUM** | Same session, different responses persisted |
| Cancel target ambiguity | **HIGH** | `interrupt()` would cancel both runs |

### Different-Session Concurrent Run Risk

| Component | Thread-Safe? | Evidence |
|-----------|-------------|----------|
| OpenAI SDK client | Yes | Official SDK is thread-safe |
| SessionDB (SQLite) | Partial | SQLite supports concurrent reads; writes serialized by GIL + WAL |
| `stream_delta_callback` | Yes (per agent) | Each AIAgent instance has its own callback |
| `_execution_thread_id` | Instance-level | Each AIAgent has its own thread ID |
| Config (read-only) | Yes | `load_config_readonly()` returns new dict each call |
| Provider state | No concern | Each agent creates own client kwargs |

### Frozen Concurrency Policy

```text
Same-session concurrency: PROHIBITED
  → Second Run request returns HTTP 409 AGENT_SESSION_BUSY
  → No queuing in Phase 1F (explicitly rejected)

Global concurrent runs: MAX 1 (initial Phase 1F)
  → Simpler reasoning, easier safety verification
  → Can increase to 2+ in future phases after safety audit

Cross-process: NOT SUPPORTED
  → Run Registry is in-process only
  → Dev API is single-process, single-worker
  → No horizontal scaling support in Phase 1F
```

### Cross-Process Limitations

- Run Registry state (active runs, event buffers) lives in Python process memory
- If Dev API process restarts, all Run state is lost
- SSE connections cannot be resumed across process boundaries
- Must document as Phase 1F limitation

---

## 10. Run Registry Design (Frozen)

### Storage: In-Process Python Object

```python
@dataclass
class AgentRun:
    run_id: str
    session_id: str
    status: str  # CREATED, STARTING, RUNNING, CANCELLING, COMPLETED, CANCELLED, FAILED, EXPIRED
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    failed_at: Optional[datetime]
    request_id: str
    model: str
    provider: str
    thread_id: Optional[int]
    cancel_requested: bool
    client_connected: bool
    last_event_id: int
    event_buffer: list  # Bounded deque of SSE events
    error_code: Optional[str]
    error_message: Optional[str]
    usage: Optional[dict]  # Token counts from provider
    future: Optional[concurrent.futures.Future]  # Background thread handle
    agent: Optional[AIAgent]  # Agent instance for interrupt
```

### Forbidden Fields (must NOT be stored in Run Registry)

```text
API Key
Authorization Header
Complete System Prompt
Complete Provider Config
Complete User Message Content
Complete Assistant Response Content
```

### Thread Safety

- Run Registry protected by `threading.Lock()`
- All status transitions atomic under lock
- Event buffer append is lock-protected
- Session lock map is lock-protected

### Limits

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Max active runs | 1 | Safety-first for Phase 1F |
| Completed run retention | 10 minutes | Debug window without memory leak |
| Event buffer max events | 500 | ~500 deltas for a typical response |
| Event buffer max bytes | 1 MiB per run | Prevent unbounded memory growth |
| Run ID format | `run-<uuid4>` | Globally unique, no guessable sequence |

### Cleanup

- Completed/CANCELLED/FAILED runs expire after retention period
- EXPIRED runs removed from registry
- Event buffer cleared on expiry
- Session lock released on terminal state (or cancel timeout)

---

## 11. Run State Machine (Frozen)

### States

```text
CREATED      — Run record created, not yet started
STARTING     — Thread dispatched, agent initializing
RUNNING      — Agent executing, SSE streaming
CANCELLING   — Cancel requested, waiting for thread
COMPLETED    — Normal completion
CANCELLED    — Cancelled by user or disconnect
FAILED       — Error occurred
EXPIRED      — Terminal state cleaned up
```

### Allowed Transitions

```text
CREATED   → STARTING
STARTING  → RUNNING
STARTING  → FAILED          (initialization error)
STARTING  → CANCELLED       (cancel before agent starts)

RUNNING   → CANCELLING
RUNNING   → COMPLETED
RUNNING   → FAILED

CANCELLING → CANCELLED
CANCELLING → FAILED         (cancel timeout)

COMPLETED  → EXPIRED        (retention TTL)
CANCELLED  → EXPIRED
FAILED     → EXPIRED
```

### Terminal States

```text
COMPLETED, CANCELLED, FAILED, EXPIRED
```

Terminal states are immutable — no further transitions allowed (except EXPIRED cleanup).

---

## 12. Kill Switch (Frozen)

### Environment Variable

```text
HERMES_AGENT_RUN_ENABLED
```

### Default State

```text
unset = DISABLED
```

### Enable Values

```text
1, true, yes, on (case-insensitive)
```

### Disable Values

```text
0, false, no, off, "" (case-insensitive)
```

### Invalid Values

```text
Any other value → FAIL CLOSED (treated as disabled)
```

### Backend Enforcement

Kill switch checked **independently** at:

1. Run creation route — reject with `503 AGENT_RUN_DISABLED`
2. SSE connection route — reject with `503 AGENT_RUN_DISABLED`
3. Run status route — return disabled status

### Kill Switch OFF Behavior

```text
- POST /agent/runs returns 503 AGENT_RUN_DISABLED
- SSE endpoint rejects connections
- No Run Registry entry created
- No thread dispatched
- No Provider client initialized
- No Session write
- No Memory write
- No Audit event
- Frontend displays "Agent execution disabled"
```

---

## 13. Dev-Only Environment Guard (Frozen)

### Mandatory Checks (at Run creation)

```python
def enforce_run_environment():
    # 1. Source root
    source_root = Path(__file__).resolve().parents[1]
    assert source_root == ALLOWED_SOURCE_ROOT

    # 2. HERMES_HOME
    hermes_home = Path(os.environ.get("HERMES_HOME", "")).resolve()
    assert hermes_home == ALLOWED_HERMES_HOME

    # 3. Not symlinked to production
    assert not hermes_home.is_symlink() or hermes_home.resolve() != PRODUCTION_HOME

    # 4. Bind host
    assert BIND_HOST == "127.0.0.1"
```

### Production Fail-Closed

Any mismatch → **refuse immediately**. No warning, no confirmation, no proceed.

---

## 14. Confirmation Model (Frozen)

### Real Agent Run is HIGH-RISK

Requires explicit confirmation before execution.

### Request Fields

```json
{
  "sessionId": "existing-session-id",
  "message": "User message text",
  "confirmationText": "RUN",
  "dryRunPreviewed": true,
  "previewRequestId": "optional-phase-1e-preview-id",
  "acknowledgedEffects": ["CALL_LLM", "WRITE_SESSION"],
  "options": {
    "stream": true,
    "tools": false,
    "autoMemory": false
  },
  "overrides": {
    "model": null,
    "temperature": null,
    "maxOutputTokens": null
  }
}
```

### Mandatory Requirements

| Field | Constraint |
|-------|-----------|
| `sessionId` | Required, must exist in dev-home SessionDB |
| `message` | Required, 1–4000 characters |
| `confirmationText` | Must exactly equal `"RUN"` |
| `dryRunPreviewed` | Must be `true` |
| `acknowledgedEffects` | Must contain exactly `["CALL_LLM", "WRITE_SESSION"]` |
| `stream` | Must be `true` (Phase 1F only supports streaming) |
| `tools` | Must be `false` |
| `autoMemory` | Must be `false` |
| `model` | If provided, must be from model allowlist |
| `temperature` | If provided, 0.0–2.0 |
| `maxOutputTokens` | If provided, 1–4096 |

### Forbidden Client Fields

```text
apiKey, baseUrl, authorization, headers, proxy,
systemPrompt, developerPrompt, toolSchema, executeTool,
writeMemory, persistMode, workerCount, threadId
```

### Preview Binding (TOCTOU Risk)

- `previewRequestId` is optional but recommended
- Preview TTL: 5 minutes (recommended)
- If preview binding cannot be safely implemented, accept `dryRunPreviewed=true` alone
- TOCTOU risk acknowledged and documented: config may change between preview and run

---

## 15. Proposed Routes (Frozen, Not Implemented)

### REST-Style Run Routes

```http
POST   /api/dev/v1/agent/runs                    Create Run
GET    /api/dev/v1/agent/runs/{runId}            Run Status
GET    /api/dev/v1/agent/runs/{runId}/events     SSE Stream
POST   /api/dev/v1/agent/runs/{runId}/cancel     Cancel Run
```

### Route Count Change

```text
Before Phase 1F: 23 paths
After Phase 1F:  27 paths (+4)
```

### Why REST-Style Over Single Execute

- Run is an independent resource with lifecycle
- Status queryable independently of SSE
- SSE reconnectable via Run ID
- Cancel has clear target
- Extensible for future features (multiple models, parallel runs)

### Forbidden Legacy Routes

```http
POST /api/dev/v1/agent/run          ← CONFUSING with /agent/run/dry-run
GET  /api/dev/v1/agent/stream       ← No independent streaming endpoint
POST /api/dev/v1/agent/tools/*      ← Tool execution not supported
```

---

## 16. Create Run Request DTO (Frozen)

```typescript
interface CreateRunRequest {
  sessionId: string;              // Required, must exist
  message: string;                // Required, 1-4000 chars
  confirmationText: "RUN";        // Must be exactly "RUN"
  dryRunPreviewed: true;          // Must be true
  previewRequestId?: string;      // Optional, Phase 1E preview request ID
  acknowledgedEffects: ["CALL_LLM", "WRITE_SESSION"];  // Exact match
  options: {
    stream: true;                 // Must be true
    tools: false;                 // Must be false
    autoMemory: false;            // Must be false
  };
  overrides?: {
    model?: string | null;        // From allowlist
    temperature?: number | null;  // 0.0-2.0
    maxOutputTokens?: number | null;  // 1-4096
  };
}
```

---

## 17. Create Run Response DTO (Frozen)

### HTTP 202 Accepted

```typescript
interface CreateRunResponse {
  data: {
    runId: string;
    sessionId: string;
    status: "CREATED";
    streamUrl: string;            // "/api/dev/v1/agent/runs/{runId}/events"
    statusUrl: string;            // "/api/dev/v1/agent/runs/{runId}"
    cancelUrl: string;            // "/api/dev/v1/agent/runs/{runId}/cancel"
    model: {
      name: string;               // Safe model name (no path)
      provider: string;           // Safe provider name
    };
    capabilities: {
      llmCall: true;
      streaming: true;
      tools: false;
      autoMemory: false;
      sessionWrite: true;
      memoryWrite: false;
      reviewQueue: false;
    };
    safety: {
      devOnly: true;
      killSwitchEnabled: boolean;
      toolsDisabled: true;
      autoMemoryDisabled: true;
    };
  };
  meta: {
    requestId: string;
    timestamp: string;            // ISO 8601
  };
}
```

### Forbidden Response Fields

```text
API Key, Base URL, Full Prompt, Full History, Full Memory Context,
Thread Object, File Paths, Traceback
```

---

## 18. Run Status Response DTO (Frozen)

```typescript
interface RunStatusResponse {
  data: {
    runId: string;
    sessionId: string;
    status: string;               // State machine value
    createdAt: string;
    startedAt: string | null;
    completedAt: string | null;
    cancelRequested: boolean;
    clientConnected: boolean;
    model: {
      name: string;
      provider: string;
    };
    usage: {
      inputTokens: number | null;
      outputTokens: number | null;
      totalTokens: number | null;
      cost: number | null;        // null if not estimable
      costEstimated: boolean;     // false if cost is null
    } | null;
    capabilities: {
      streaming: true;
      tools: false;
      autoMemory: false;
      sessionWrite: true;
    };
    safety: {
      devOnly: true;
      killSwitchEnabled: boolean;
    };
  };
  meta: {
    requestId: string;
    timestamp: string;
  };
}
```

### Note: Full Response Content

Full assistant response is NOT returned in status query. Available only via:
- SSE terminal event (`run.completed`)
- Session Message API (read from SessionDB after run completes)

---

## 19. Cancel Response DTO (Frozen)

### HTTP 200 OK (Idempotent)

```typescript
interface CancelRunResponse {
  data: {
    runId: string;
    cancelRequested: boolean;
    statusBefore: string;         // e.g., "RUNNING"
    statusAfter: string;          // e.g., "CANCELLING"
    alreadyTerminal: boolean;     // true if was already COMPLETED/CANCELLED/FAILED
  };
  meta: {
    requestId: string;
    timestamp: string;
  };
}
```

### Idempotent Behavior

- First cancel: `alreadyTerminal=false`, status transitions to CANCELLING
- Repeated cancel on active run: `alreadyTerminal=false`, no-op (already CANCELLING)
- Cancel on terminal run: `alreadyTerminal=true`, no status change

---

## 20. SSE Protocol (Frozen)

### SSE Route

```http
GET /api/dev/v1/agent/runs/{runId}/events
```

### Headers

```text
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

### Callback Source

```text
stream_delta_callback ONLY
_stream_callback MUST BE None
```

### Event Types

| Event Type | Phase 1F | Description |
|-----------|----------|-------------|
| `run.created` | Yes | Run record created |
| `run.started` | Yes | Agent started executing |
| `message.delta` | Yes | Incremental text delta |
| `message.completed` | Yes | Full message complete |
| `usage.updated` | Yes | Token usage update |
| `run.cancelling` | Yes | Cancel requested |
| `run.cancelled` | Yes | Run cancelled |
| `run.completed` | Yes | Run completed successfully |
| `run.failed` | Yes | Run failed with error |
| `heartbeat` | Yes | Keep-alive ping |
| `tool.call` | **No** | Tools disabled |
| `tool.result` | **No** | Tools disabled |
| `memory.write` | **No** | Auto-memory disabled |
| `review.created` | **No** | Review queue disabled |

### Event Format

```text
id: 12
event: message.delta
data: {"runId":"run-abc","sequence":12,"delta":"hello","timestamp":"..."}

```

### Event JSON Envelope

```typescript
interface SSEEvent {
  runId: string;
  sequence: number;        // Monotonically increasing per run
  timestamp: string;       // ISO 8601
  type: string;            // Event type
  data: Record<string, any>;  // Event-specific payload
}
```

### Delta Rules

```text
- delta is PURE INCREMENTAL (not cumulative)
- Never re-send previously sent deltas
- sequence is monotonically increasing (never repeats, never gaps)
- Only one callback source (stream_delta_callback)
- _stream_callback must be None to prevent dual emission
```

### Terminal Event

Each Run sends exactly **one** terminal event:

```text
run.completed  — normal finish
run.cancelled  — user cancelled
run.failed     — error occurred
```

No Run may emit two terminal events.

### Heartbeat

```text
Interval: 15 seconds
Content: {"runId":"...","sequence":N,"type":"heartbeat"}
Purpose: Keep connection alive, detect client disconnect
```

### Event Buffer

```text
Max events: 500 per run
Max bytes: 1 MiB per run
Used for: Last-Event-ID reconnection
```

---

## 21. Reconnection Strategy (Frozen)

### Last-Event-ID Support

Phase 1F supports **limited reconnection** via event buffer:

1. Client sends `Last-Event-ID: <last_sequence>` header
2. Server replays buffered events from `last_sequence + 1`
3. If buffer has been trimmed (sequence gap), return `410 AGENT_EVENT_BUFFER_EXPIRED`
4. Client must treat 410 as "cannot resume" — show terminal status via status API

### Disconnect Grace Period

```text
Grace period: 15 seconds
```

Behavior:
1. SSE disconnect detected
2. Enter grace period (run continues executing)
3. If client reconnects within grace period: resume from buffered events
4. If grace period expires without reconnect: request Run cancellation

### API Process Exit

```text
If Dev API process exits:
  - All Run state is lost (in-process only)
  - Agent thread may continue briefly (daemon thread)
  - Session persistence already handled by Agent Runtime
  - Client sees connection close with no terminal event
  - Document as Phase 1F limitation
```

---

## 22. Cancellation Propagation (Frozen)

### Cancel Flow

```text
POST /agent/runs/{runId}/cancel
  → Registry: status = CANCELLING
  → AIAgent.interrupt()
    → _interrupt_requested = True
    → _set_interrupt(True, _execution_thread_id)
    → Fan out to tool worker threads (N/A in Phase 1F — no tools)
  → Wait for Worker thread (join with timeout)
    → Success: status = CANCELLED, emit run.cancelled
    → Timeout: status = FAILED, errorCode = AGENT_CANCEL_TIMEOUT
```

### interrupt() Mechanism (source: `run_agent.py:2237-2303`)

- Sets `self._interrupt_requested = True` (thread-safe flag)
- Calls `_set_interrupt(True, _execution_thread_id)` (per-thread signal)
- Propagates to child agents (subagent delegation — N/A in Phase 1F)
- **Cannot abort in-flight HTTP request** — Provider SDK manages socket
- `_interruptible_api_call()` checks `_interrupt_requested` between retries
- Agent checks interrupt flag at loop boundaries

### Provider Request Cancellation

- OpenAI SDK does NOT support mid-request cancellation
- `interrupt()` sets flag, but in-flight HTTP response completes
- For streaming: `stream_delta_callback` may receive remaining chunks
- **P1 Risk:** Provider request may complete even after cancel requested
- **Mitigation:** Agent checks interrupt flag after each API call and before persisting

---

## 23. Orphan Thread Handling (Frozen)

### Thread Properties

- Worker threads are **daemon threads** (set via `ThreadPoolExecutor`)
- Daemon threads are killed when main process exits
- Cannot leave zombie processes

### Cancel Timeout

```text
cancel_wait_timeout = 10 seconds
```

### Timeout Behavior

1. Cancel requested → `AIAgent.interrupt()` called
2. `worker_future.result(timeout=10)` awaited
3. If timeout:
   - `status = FAILED`
   - `errorCode = AGENT_CANCEL_TIMEOUT`
   - Log audit event
   - **Keep worker reference** — do not release session lock
   - **Reject new Runs** for same session until worker actually exits
4. Worker eventually completes (Provider request finishes) or process exits

### Prohibited Behavior

```text
- Never mark a still-running thread as CANCELLED and release session lock
- Never allow new Run on same session while previous Run thread is alive
- Never forcefully terminate thread (no Thread.terminate() in Python)
```

---

## 24. Timeout and Retry (Frozen)

### Overall Run Timeout

```text
overall_run_timeout = 120 seconds
```

Enforced by Run Service — cancels Run if exceeded.

### Provider Timeout

```text
provider_timeout = use existing config, max 90 seconds
```

Configured via `_provider_timeout` in agent config.

### Retry

```text
retry_count = use existing safe config, max 2
```

Existing retry logic in `conversation_loop.py` handles retryable errors.

### Retry Constraints

```text
- No infinite retries
- No retry after disconnect
- No retry after cancel
- Cancel priority > retry priority
```

---

## 25. Rate Limits (Frozen)

### Limits

| Dimension | Value |
|-----------|-------|
| Global concurrent active runs | 1 |
| Per-session active runs | 1 |
| Run starts per minute | 3 |
| Run starts per hour | 20 |

### Rate Limit Error

```text
429 AGENT_RATE_LIMITED
```

Response includes `retryAfter` hint.

---

## 26. Token and Cost Limits (Frozen)

### Usage Tracking

Provider returns in API response (source: `conversation_loop.py:4782-4793`):

```python
result["input_tokens"] = agent.session_input_tokens
result["output_tokens"] = agent.session_output_tokens
result["total_tokens"] = agent.session_total_tokens
result["estimated_cost_usd"] = agent.session_estimated_cost_usd
result["cost_status"] = agent.session_cost_status
result["cost_source"] = agent.session_cost_source
```

### Safety Limits

| Parameter | Value |
|-----------|-------|
| `maxOutputTokens` request cap | 4096 |
| Per-run cost tracking | Yes (from provider response) |
| Daily cost cap | Deferred to Phase 1F implementation |

### Cost DTO Rule

```text
If cost cannot be precisely calculated:
  cost = null
  costEstimated = false

NEVER fabricate cost values.
```

---

## 27. Tool Boundary (Frozen)

### Enforcement Strategy

1. **Tool schema not sent to Provider:** `tools=[]` or `tools=None` in API kwargs
2. **Tool Choice disabled:** No `tool_choice` parameter
3. **Tool dispatch blocked:** Agent Run uses empty toolset

### Unexpected Tool Call Handling

If Provider returns a tool_call despite no tools being sent:

```text
1. Run terminates immediately
2. Status = FAILED
3. errorCode = AGENT_TOOL_CALL_FORBIDDEN
4. No tool executed
5. Audit event recorded
6. SSE run.failed event emitted
```

This must have an automated test.

---

## 28. Runtime Memory Writer Boundary (Frozen)

### Disable Verification

`maybe_auto_write_memory()` (source: `agent/runtime_memory_writer.py:809`) checks `auto_write_enabled` from config:

```python
def auto_write_enabled(config=None) -> bool:
    return _auto_write_config(config).enabled  # Default: False
```

### Phase 1F Enforcement

```text
auto_write config = disabled (default)
auto_update config = disabled (default)
auto_create_categories = disabled (default)
```

After Run completion:
- `maybe_auto_write_memory()` returns SKIP decision (enabled=False)
- `enqueue_review_item()` not called (queue_cfg.enabled=False)
- No WRITE, UPDATE, or REVIEW events
- No Memory files modified
- No Review Queue items created

### Verification Test Required

```text
After Phase 1F Run:
  - maybe_auto_write_memory call count = 1 (but decision = SKIP)
  - enqueue_review_item call count = 0
  - Memory hashes unchanged
  - Review hashes unchanged
```

---

## 29. Review Queue Boundary (Frozen)

### Disable Verification

`get_review_queue_config()` (source: `agent/memory_review_queue.py:112+`):

```python
enabled: bool = False  # Default
```

Also gated by environment variable:

```python
cfg.enabled = _as_bool(os.getenv("HERMES_MEMORY_REVIEW_QUEUE"), False)
```

Phase 1F: Neither config nor env var enables review queue.

---

## 30. Audit Trail (Frozen)

### Storage Decision

**Option B: `state.db` independent `agent_run_audit` table**

Rationale:
- Transactional consistency with session data
- Queryable via SQL
- No separate file to manage
- No separate rotation logic needed
- Reuses existing SQLite infrastructure

### Schema

```sql
CREATE TABLE agent_run_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'dev-webui',
    action TEXT NOT NULL,            -- 'run.created', 'run.completed', etc.
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    status TEXT NOT NULL,
    cancel_requested INTEGER DEFAULT 0,
    tools_enabled INTEGER DEFAULT 0,
    auto_memory_enabled INTEGER DEFAULT 0,
    input_token_count INTEGER,
    output_token_count INTEGER,
    total_token_count INTEGER,
    duration_ms INTEGER,
    error_code TEXT,
    dev_only INTEGER DEFAULT 1
);
```

### Forbidden Fields (must NOT appear in audit)

```text
Complete user message, complete assistant response, complete system prompt,
API key, authorization, local absolute paths
```

### Audit Events

| Event | When |
|-------|------|
| `run.created` | Run record created |
| `run.started` | Agent thread begins execution |
| `run.completed` | Normal completion |
| `run.cancelled` | User cancelled |
| `run.failed` | Error occurred |

---

## 31. Error Model (Frozen)

### Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `AGENT_RUN_DISABLED` | 503 | Kill switch is OFF |
| `UNSAFE_ENVIRONMENT` | 503 | Environment guard failed |
| `INVALID_AGENT_RUN_REQUEST` | 400 | Request validation failed |
| `INVALID_CONFIRMATION` | 400 | confirmationText != "RUN" |
| `MISSING_DRY_RUN` | 400 | dryRunPreviewed != true |
| `INVALID_ACKNOWLEDGED_EFFECTS` | 400 | Wrong acknowledged effects |
| `INVALID_SESSION_ID` | 400 | Session ID format invalid |
| `SESSION_NOT_FOUND` | 404 | Session does not exist |
| `AGENT_SESSION_BUSY` | 409 | Session already has active Run |
| `AGENT_RUN_NOT_FOUND` | 404 | Run ID does not exist |
| `AGENT_RUN_ALREADY_TERMINAL` | 409 | Run is already in terminal state |
| `AGENT_CANCEL_TIMEOUT` | 500 | Cancel wait exceeded timeout |
| `AGENT_RATE_LIMITED` | 429 | Rate limit exceeded |
| `AGENT_MODEL_NOT_ALLOWED` | 400 | Model not in allowlist |
| `AGENT_PROVIDER_UNAVAILABLE` | 503 | Provider client init failed |
| `AGENT_PROVIDER_TIMEOUT` | 504 | Provider request timed out |
| `AGENT_TOOL_CALL_FORBIDDEN` | 409 | Provider returned unexpected tool call |
| `AGENT_EVENT_BUFFER_EXPIRED` | 410 | SSE event buffer trimmed |
| `AGENT_RUN_FAILED` | 500 | Agent execution error |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

### Client Disconnect (Internal Only)

```text
AGENT_STREAM_DISCONNECTED — internal status only, not returned as HTTP response
```

Client disconnect triggers cancel flow. No HTTP response possible on SSE stream.

---

## 32. Frontend Information Architecture (Frozen)

### Agent Panel Tabs (Extended)

| Tab | Phase | Description |
|-----|-------|-------------|
| Status | 1E | Agent config status (read-only) |
| Prompt Preview | 1E | Prompt construction preview |
| Run Dry-Run | 1E | Simulated run without LLM |
| **Live Run** | **1F** | **Real Agent Run with SSE** |

### Live Run Tab — Default State (Kill Switch OFF)

```text
- "Agent execution disabled" banner
- Kill switch status: OFF
- "Dev-only" badge
- "Tools: Disabled" badge
- "Auto Memory: Disabled" badge
- Run button: DISABLED
```

### Live Run Form

| Field | Type | Constraints |
|-------|------|-------------|
| Session ID | Select/Text | Required, must exist |
| Message | Textarea | Required, 1-4000 chars |
| Model Override | Select | Optional, from allowlist |
| Temperature | Slider/Input | Optional, 0.0-2.0 |
| Max Output Tokens | Input | Optional, 1-4096 |

### Fixed Display (not editable)

```text
Streaming: On
Tools: Off
Auto Memory: Off
Session persistence: Agent Runtime
```

### Pre-Execution Confirmation Flow

1. User fills form
2. Clicks "Preview" → calls Phase 1E Dry-Run endpoint
3. Dry-run result displayed (prompt structure, token estimate, etc.)
4. User must:
   - Type "RUN" in confirmation input
   - Check "I understand this will call LLM (costs tokens)"
   - Check "I understand this will write to session database"
5. Clicks "Execute" → POST /agent/runs

### Live Run UI Elements

| Element | Display |
|---------|---------|
| Run ID | Static text |
| Status | Badge (CREATED/RUNNING/COMPLETED/etc.) |
| Connection | Status indicator (connected/disconnected/reconnecting) |
| Model | Name + provider |
| Streaming text | Real-time SSE text display |
| Token usage | Live counter (input/output/total) |
| Duration | Running timer |
| Cancel button | Active during RUNNING, confirmation optional |
| Terminal result | Full response text after completion |
| Error | Error code + message if failed |

### Prohibited UI Elements

```text
- Tool execution controls
- Auto Memory toggle
- Review Queue controls
- Parallel Run button
- Batch Run
- Auto-retry toggle
```

### Cancel UX

```text
- Explicit "Cancel" button visible during RUNNING
- Optional second confirmation (not required)
- Immediate visual transition to "Cancelling..."
- Disable button during CANCELLING
- Show "Waiting for agent to stop..." text
- Terminal state displays final status
```

### Page Refresh Behavior

```text
1. After refresh, attempt to reconnect via runId
2. GET /agent/runs/{runId} to check status
3. If RUNNING: reconnect to SSE (with Last-Event-ID if available)
4. If terminal: display final status and result
5. If not found: display "Run information lost (page was refreshed during execution)"
```

---

## 33. Accessibility (Frozen)

| Requirement | Implementation |
|-------------|---------------|
| Tab navigation | `tablist` / `tab` / `tabpanel` ARIA pattern |
| Stream text | `aria-live="polite"` for streaming area |
| Running state | `aria-busy="true"` during execution |
| Connection status | `role="status"` |
| Errors | `role="alert"` |
| Cancel button | Keyboard accessible (Tab + Enter) |
| Focus stability | Focus does NOT jump per-token |
| Screen reader | Batch updates every ~500ms or sentence boundary |
| Reduced motion | `prefers-reduced-motion` respected |

---

## 34. OpenAPI Strategy (Frozen)

### Current State

```text
23 paths
```

### Phase 1F Implementation Will Add

```http
POST /api/dev/v1/agent/runs
GET  /api/dev/v1/agent/runs/{runId}
GET  /api/dev/v1/agent/runs/{runId}/events
POST /api/dev/v1/agent/runs/{runId}/cancel
```

### Expected After Phase 1F

```text
27 paths
```

### Must NOT Appear

```http
POST /api/dev/v1/agent/run              ← Confusing with /agent/run/dry-run
GET  /api/dev/v1/agent/stream           ← No standalone streaming
POST /api/dev/v1/agent/tools/*          ← Tool execution not supported
```

### Phase 1F-00 Does NOT Modify OpenAPI

OpenAPI changes only happen in Phase 1F implementation.

---

## 35. dev-check Strategy (Frozen)

### After Phase 1F Implementation, dev-check Should Verify

| Check | Expected Value |
|-------|---------------|
| OpenAPI paths | 27 |
| Agent Preview routes | 2 |
| Agent Run routes | 4 |
| Kill Switch default | disabled |
| Tools for Agent Run | disabled |
| Auto Memory for Agent Run | disabled |
| Legacy /agent/run | absent |
| Legacy /agent/stream | absent |
| Agent Tool routes | absent |

### Phase 1F-00 Does NOT Modify dev-check

---

## 36. Playwright Smoke Strategy (Frozen)

### Two Test Modes

#### Mode 1: Kill Switch Disabled (Default)

Test against real dev-home with `HERMES_AGENT_RUN_ENABLED` unset:

```text
- Live Run Tab visible
- Run button disabled
- "Agent execution disabled" visible
- No Provider request
- No Run created
- No Session write
- No Memory write
```

#### Mode 2: Temporary Fixture (Agent Run Enabled)

Test with temporary HERMES_HOME, temporary state.db, Fake Provider:

```text
- Create Run → 202 Accepted
- SSE connected
- Delta sequence correct
- Only sent once (no dual emission)
- Single terminal event
- Cancel works
- Session persisted once
- Tools not executed
- Auto Memory not executed
- Review Queue not entered
```

**Fake Provider MUST NOT call real LLM.**

---

## 37. Backend Test Strategy (Frozen)

### Test Groups

| Group | Count | Description |
|-------|-------|-------------|
| Kill Switch | 4 | unset/false/invalid/true |
| Dev-only Guard | 4 | dev home OK, production rejected, symlink rejected, wrong root rejected |
| Run Creation | 6 | valid, missing confirmation, missing dry-run, invalid effects, session not found, model not allowed |
| Concurrency | 4 | same-session 409, global limit enforced, terminal releases lock, cancel-timeout no premature release |
| Streaming | 7 | callback only, _stream None, delta sequence, no duplicate delta, single terminal, heartbeat, buffer limit |
| Cancellation | 6 | cancel active, cancel starting, cancel terminal, double cancel, cancel timeout, disconnect grace |
| Persistence | 5 | user message once, assistant once, cancelled partial once, failed no duplicate, Web API append count = 0 |
| Tool Boundary | 4 | tool schema not sent, dispatch count = 0, provider tool call blocked, unexpected tool_call error |
| Memory Boundary | 3 | maybe_auto_write_memory called but SKIP, enqueue_review_item count = 0, memory hashes unchanged |
| Audit | 4 | started event, completed event, cancelled event, failed event; no prompt/secret content |
| SSE Protocol | 5 | event format, sequence monotonic, terminal uniqueness, heartbeat interval, Last-Event-ID resume |

### Fixture Strategy

```text
All Agent Run tests use:
  - pytest tmp_path for temporary HERMES_HOME
  - Temporary state.db (SessionDB)
  - Temporary session (pre-created)
  - Fake Provider (mock OpenAI client returning canned streaming response)
  - Fake usage data
  - Fake timeout / cancellation
  - Fake stream_delta_callback

MUST NOT:
  - Call real LLM
  - Use real API Key
  - Write to hermes-home-dev
  - Write to ~/.hermes
```

### Formal Dev-Home Validation

Kill Switch OFF mode only:

```text
1. Snapshot dev-home state (state.db hash, memory hashes)
2. Call real Run route → expect 503 AGENT_RUN_DISABLED
3. Verify:
   - No Run Registry entry
   - No thread created
   - No Provider initialized
   - No Session write
   - No Message write
   - No Memory write
   - No Review Queue entry
   - No Audit file created
4. Snapshot dev-home state again
5. Verify all hashes unchanged
```

---

## 38. Non-Goals

Phase 1F-00 explicitly does NOT:

```text
- Implement real Agent Run
- Implement SSE endpoint
- Call any LLM
- Execute any Tool
- Write any Session
- Write any Message
- Write any Memory
- Enqueue any Review
- Create Audit data
- Add new routes
- Modify OpenAPI
- Modify dev-check
- Modify frontend code
- Modify backend business code
- Access production environment
- Start Phase 1F implementation
```

---

## 39. Risks

### P0 Risks (Phase 1F Blockers)

No P0 blockers identified.

The following would be blockers if found during Phase 1F implementation:

| Risk | Status |
|------|--------|
| `AIAgent.interrupt()` cannot safely stop a running Provider request | **Mitigated** — interrupt sets flag, Provider request completes naturally, Agent checks flag after call |
| Cannot guarantee single persistence responsibility | **Resolved** — `_last_flushed_db_idx` tracking prevents duplicates |
| Cannot prevent same-session concurrent Runs | **Resolved** — Run Registry session lock |
| `stream_delta_callback` is not the sole delta source | **Resolved** — `_stream_callback` explicitly set to None |
| Agent executes Tool even with tools=None | **Mitigated** — no tool schema sent; unexpected tool_call → Run FAILED |
| Cannot disable Runtime Memory Writer | **Resolved** — config default is disabled |
| Cannot isolate Provider calls in dev-only environment | **Resolved** — environment guard enforces dev-home |

### P1 Risks

| Risk | Status | Mitigation |
|------|--------|-----------|
| Provider request may not cancel immediately | **Mitigated** | `interrupt()` sets flag; request completes; Agent checks flag post-call |
| Orphan thread after cancel timeout | **Open** | Keep worker reference; block new Runs; daemon thread dies on process exit |
| SSE reconnection buffer may grow large | **Mitigated** | Buffer capped at 500 events / 1 MiB |
| Event buffer trimmed before reconnect | **Open** | Return 410; client falls back to status API |
| Token cost estimation imprecise | **Open** | Return `cost=null, costEstimated=false` when uncertain |
| Provider usage fields vary by provider | **Open** | Normalize to common schema; unknown fields = null |
| Real Prompt drift from Phase 1E Preview | **Open** | Acknowledged TOCTOU risk; Preview is advisory, not contractual |
| Audit log lacks transaction guarantees (if JSONL) | **Resolved** | Using state.db table for transactional consistency |

### P2 Risks

| Risk | Notes |
|------|-------|
| Browser background tab throttling | May delay SSE heartbeat processing |
| Long response memory usage | Event buffer capped; streaming text not accumulated in registry |
| Audit table growth | Add retention/cleanup in future phase |
| Multi-provider model compatibility | Phase 1F starts with single configured provider |
| Run history query | Not in Phase 1F scope; future enhancement |

---

## 40. Acceptance Criteria

Phase 1F-00 completion requires:

1. ✅ Current branch is `dev-huangruibang`
2. ✅ Local/remote HEAD match (`6cb05c8da`)
3. ✅ Worktree was clean before execution
4. ✅ Agent Run complete call chain audited (source-evidenced)
5. ✅ Agent initialization audited (constructor, provider, callbacks)
6. ✅ Provider initialization audited (API key, client creation, timeout)
7. ✅ SessionDB initialization audited
8. ✅ Prompt Assembly pipeline confirmed
9. ✅ All persistence exit paths audited (`_persist_session` called on all exits)
10. ✅ Agent Runtime confirmed as sole persistence owner
11. ✅ Web API forbidden from direct message writes (frozen)
12. ✅ Same-session concurrent run policy frozen (409 reject)
13. ✅ Global concurrent run limit frozen (max 1)
14. ✅ Cross-process limitations documented
15. ✅ Single-worker requirement documented
16. ✅ Run Registry designed (in-process, thread-safe, bounded, TTL)
17. ✅ Run State Machine designed (8 states, 12 transitions, 4 terminal)
18. ✅ Run ID strategy defined (`run-<uuid4>`)
19. ✅ Kill Switch defined (`HERMES_AGENT_RUN_ENABLED`, default OFF)
20. ✅ Kill Switch default is disabled
21. ✅ Dev-only guard defined (fail-closed)
22. ✅ Production fail-closed confirmed
23. ✅ Confirmation model defined (RUN + dryRunPreviewed + acknowledgedEffects)
24. ✅ Dry-run-first enforced
25. ✅ Run creation route frozen (`POST /agent/runs`)
26. ✅ Run status route frozen (`GET /agent/runs/{runId}`)
27. ✅ SSE route frozen (`GET /agent/runs/{runId}/events`)
28. ✅ Cancel route frozen (`POST /agent/runs/{runId}/cancel`)
29. ✅ Future path count confirmed (23 → 27)
30. ✅ Legacy `/agent/run` still forbidden
31. ✅ Legacy `/agent/stream` still forbidden
32. ✅ SSE uses only `stream_delta_callback`
33. ✅ `_stream_callback` must remain `None`
34. ✅ SSE delta semantics frozen (pure incremental)
35. ✅ SSE event types frozen (10 types, 4 disabled)
36. ✅ Sequence numbering frozen (monotonically increasing)
37. ✅ Terminal event uniqueness frozen (exactly one per Run)
38. ✅ Heartbeat frozen (15 seconds)
39. ✅ Event buffer frozen (500 events / 1 MiB)
40. ✅ Reconnection strategy frozen (Last-Event-ID + 15s grace)
41. ✅ Last-Event-ID strategy frozen (buffer replay or 410)
42. ✅ Disconnect strategy frozen (grace period → cancel)
43. ✅ Cancel propagation frozen (interrupt → join → timeout)
44. ✅ Cancel timeout frozen (10 seconds)
45. ✅ Orphan thread strategy frozen (keep reference, block new runs)
46. ✅ Session lock release frozen (on terminal, never on cancel-timeout)
47. ✅ Overall timeout frozen (120 seconds)
48. ✅ Retry limit frozen (max 2)
49. ✅ Rate limits frozen (1 concurrent, 3/min, 20/hour)
50. ✅ Token limit frozen (maxOutputTokens ≤ 4096)
51. ✅ Cost model frozen (null if uncertain, never fabricate)
52. ✅ Tools forcibly disabled (empty schema, unexpected call = error)
53. ✅ Unexpected Tool Call handling frozen (terminate Run, error code)
54. ✅ Runtime Memory Writer forcibly disabled (config default = off)
55. ✅ Review Queue forcibly disabled (config default = off)
56. ✅ Allowed persistent effects: Session/Message + Audit only
57. ✅ Audit storage selected (state.db `agent_run_audit` table)
58. ✅ Audit fields frozen (metadata only, no content)
59. ✅ Sensitive field exclusion frozen
60. ✅ Error model frozen (20 error codes)
61. ✅ Frontend IA frozen (4-tab Agent panel, Live Run tab)
62. ✅ Accessibility frozen (ARIA, reduced motion, screen reader)
63. ✅ OpenAPI strategy frozen (23 → 27 paths)
64. ✅ dev-check strategy frozen (27 paths, kill switch, tool disable checks)
65. ✅ Smoke strategy frozen (2 modes: disabled + fixture)
66. ✅ Backend test strategy frozen (10 groups, 48+ tests)
67. ✅ Fake Provider fixture frozen
68. ✅ Formal dev-home disabled-mode validation frozen
69. ✅ No LLM called
70. ✅ No Agent run
71. ✅ No Tool executed
72. ✅ No SSE started
73. ✅ No Session written
74. ✅ No Message written
75. ✅ No Memory written
76. ✅ No Review Queue entry
77. ✅ No new API routes added
78. ✅ No business code modified
79. ✅ No frontend code modified
80. ✅ No OpenAPI modified
81. ✅ memory-check PASS
82. ✅ dev-check PASS
83. ✅ compileall PASS
84. ✅ Documentation complete
85. ✅ Local commit created
86. ✅ Not pushed
87. ✅ Final worktree clean
88. ✅ Production Gateway PID 1717 unaffected
89. ✅ Dev Gateway stopped
90. ✅ Ports 5180/5181 free
91. ✅ Phase 1F implementation not started

---

## 41. Next Phase

Phase 1F: Agent Dev-Only Run / SSE Implementation

Must NOT start automatically. Requires explicit user request.
