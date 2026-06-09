# Phase 1E-00: Agent Prompt Preview / Dry-Run Scope, Contract & Safety Boundary Freeze

**Status:** Completed
**Date:** 2026-06-09
**Branch:** dev-huangruibang
**Base commit:** e5d0163f1c91f3e6c4d99462d7df203e29d4da60
**Scope:** Documentation-only audit and contract freeze
**OpenAPI paths:** 21 (unchanged)

---

## 1. Status

Phase 1E-00 is a **documentation-only scope freeze**. No code was modified, no APIs were registered, no LLM calls were made, no sessions were written, and no memory was modified.

Phase 1E implementation remains **Not Started**.

---

## 2. Background

Phase 1E introduces two preview routes that allow the Dev WebUI to inspect what the Agent *would* do when processing a message — without actually calling any LLM, executing any tool, or writing any data. This requires a deep audit of the Agent's internal call chain to identify:

- Which functions are safe to call in a read-only preview context
- Which functions must be strictly forbidden
- How prompts are assembled and what sensitive data they contain
- Who owns message persistence (to prevent double-writes in Phase 1F)
- Which streaming callback to use for future SSE

---

## 3. Current Baseline

| Metric | Value |
|--------|-------|
| OpenAPI paths | 21 |
| Agent capability | Read-only status endpoint |
| Prompt Preview capability | None |
| Agent Run capability | None |
| LLM capability | None |
| Tool execution capability | None |
| Session write capability | None |
| Memory write capability | Memory Writer dry-run (3 routes) |
| Review Queue | Read-only + Dry-run + Dev-only Execute |

---

## 4. Audit Sources

### Source Code Files Audited

| File | Purpose |
|------|---------|
| `run_agent.py` | AIAgent class, persistence, streaming, interrupt (~12k LOC) |
| `cli.py` | HermesCLI, session management (~11k LOC) |
| `agent/agent_init.py` | Agent initialization, callback wiring |
| `agent/conversation_loop.py` | Main conversation turn loop |
| `agent/system_prompt.py` | System prompt assembly (stable/context/volatile tiers) |
| `agent/prompt_builder.py` | Environment hints, skills prompt |
| `agent/runtime_memory_writer.py` | Auto memory evaluation and writing |
| `agent/memory_review_queue.py` | Review queue persistence and lifecycle |
| `agent/context_engine.py` | Context engine |
| `agent/context_compressor.py` | Context compression |
| `agent/memory_provider.py` | MemoryProvider ABC |
| `hermes_state.py` | SessionDB, append_message, message persistence |
| `model_tools.py` | Tool discovery, dispatch, handle_function_call |
| `tools/registry.py` | Tool registration and execution dispatch |
| `toolsets.py` | Toolset definitions |
| `gateway/run.py` | Gateway agent invocation and transcript management |
| `gateway/session.py` | Gateway session persistence, append_to_transcript |
| `hermes_cli/config.py` | Config loading, provider config, API keys |
| `hermes_cli/dev_web_api.py` | Dev Web API router |
| `hermes_cli/dev_web_schemas.py` | Dev Web DTOs |
| `hermes_cli/dev_web_errors.py` | Error codes and handling |
| `hermes_cli/dev_web_agent_service.py` | Agent service layer |

### Planning Documents Reviewed

- `docs/webui/phase-1-00-planning-and-scope.md`
- `docs/webui/phase-1-implementation-plan.md`
- `docs/webui/phase-0e-06-phase-1-safety-boundary.md`
- `docs/webui/phase-1d-00-memory-writer-dry-run-scope.md`
- `docs/webui/phase-1d-memory-writer-dry-run.md`
- `docs/webui/phase-1c-review-queue-execute.md`
- `docs/webui/phase-1c-post-approve-execute-test-closure.md`
- `docs/webui/dev-web-api-v1.md`

---

## 5. Agent Call Graph

### Entry Points

```
CLI         → cli.py HermesCLI._ensure_session() → AIAgent(session_db=SessionDB())
                                                        → run_agent.py AIAgent.__init__()
                                                          → agent/agent_init.py init_agent()

Gateway     → gateway/run.py → AIAgent(session_db=SessionDB())
                             → agent.run_conversation(message, conversation_history)

Web (future)→ dev_web_api → service layer → AIAgent(session_db=...)
                                              → agent.run_conversation(message, ...)
```

### Complete Call Chain

```
Entry Point
  → Config Loading (hermes_cli/config.py)
    → load_config() / load_config_readonly()       [read-only, file read]
    → Provider config, model, API key, base URL     [file read, contains secrets]
  → Session Load (hermes_state.py)
    → SessionDB.get_messages()                      [read-only, DB read]
    → SessionDB.get_session()                       [read-only, DB read]
  → Memory Context (agent/system_prompt.py)
    → agent._memory_store.format_for_system_prompt() [read-only, memory read]
    → External memory provider prefetch              [may be network]
  → Prompt Assembly (agent/system_prompt.py)
    → build_system_prompt_parts()                   [pure computation]
    → build_system_prompt()                         [pure computation]
  → User Message Injection (agent/conversation_loop.py)
    → _sanitize_surrogates()                        [pure computation]
    → Append to messages list                       [in-memory]
  → LLM Call (run_agent.py → chat_completion)
    → OpenAI-compatible API                         [NETWORK SIDE EFFECT]
  → Streaming Callbacks (run_agent.py)
    → stream_delta_callback / _stream_callback      [callback invocation]
  → Tool Calls (model_tools.py → tools/registry.py)
    → registry.dispatch()                           [TOOL SIDE EFFECT]
  → Session Persistence (run_agent.py)
    → _persist_session()                            [DB + FILE SIDE EFFECT]
    → _flush_messages_to_session_db()               [DB SIDE EFFECT]
    → SessionDB.append_message()                    [DB SIDE EFFECT]
  → Runtime Memory Writer (agent/runtime_memory_writer.py)
    → maybe_auto_write_memory()                     [FILE SIDE EFFECT]
    → enqueue_review_item()                         [FILE SIDE EFFECT]
  → Gateway Transcript (gateway/session.py)
    → append_to_transcript(skip_db=agent_persisted) [DB SIDE EFFECT, guarded]
```

### Side-Effect Classification

| Segment | Classification |
|---------|---------------|
| Config Loading | Read-only (file read) |
| Session Load | Read-only (DB read) |
| Memory Context | Read-only (memory/file read) |
| Prompt Assembly | Pure computation |
| User Message Injection | In-memory only |
| LLM Call | **Network side effect** |
| Streaming Callbacks | Callback invocation |
| Tool Execution | **Tool side effect** |
| Session Persistence | **DB + File side effect** |
| Runtime Memory Writer | **File side effect** |
| Review Queue Enqueue | **File side effect** |
| Gateway Transcript | **DB side effect** (guarded by skip_db) |

---

## 6. Prompt Assembly Pipeline

### Assembly Order

The system prompt is assembled in three tiers by `build_system_prompt_parts()` (agent/system_prompt.py:61):

#### Tier 1: Stable (cached for agent lifetime)

1. **SOUL.md identity** — from `HERMES_HOME/SOUL.md` or `DEFAULT_AGENT_IDENTITY`
2. **HERMES_AGENT_HELP_GUIDANCE** — pointer to docs
3. **TASK_COMPLETION_GUIDANCE** — no-fabrication instructions
4. **Tool-aware behavioral guidance** — memory, session_search, skills, kanban blocks
5. **Computer-use guidance** (if enabled)
6. **Nous subscription prompt** (if applicable)
7. **Tool-use enforcement guidance** — model-specific
8. **Model-specific operational guidance** — Google/OpenAI/xAI
9. **Skills system prompt** — built from `build_skills_system_prompt()`
10. **Alibaba model identity** (if provider=alibaba)
11. **Environment hints** — WSL, Termux, OS info via `build_environment_hints()`
12. **Environment probe** — Python/pip/uv state
13. **Active profile hint** — profile name and paths
14. **Platform hints** — messaging platform guidance

#### Tier 2: Context (session-stable, changes between sessions)

1. **Caller system_message** (optional override)
2. **Context files** — AGENTS.md, .cursorrules, CLAUDE.md via `build_context_files_prompt()`

#### Tier 3: Volatile (changes per turn)

1. **Memory context** — `agent._memory_store.format_for_system_prompt("memory")`
2. **User profile** — `agent._memory_store.format_for_system_prompt("user")`
3. **External memory provider block** — `agent._memory_manager.build_system_prompt()`
4. **Timestamp** — conversation start date, session ID, model name, provider

### Final Assembly

`build_system_prompt()` (agent/system_prompt.py:347) joins the three tiers:
```
stable + "\n\n" + context + "\n\n" + volatile
```

Cached on `agent._cached_system_prompt` for the session lifetime.

### Sensitive Content Analysis

| Content | Contains Paths | Contains Secrets | Risk Level |
|---------|---------------|-----------------|------------|
| SOUL.md | Possible | No | Low |
| Tool guidance | No | No | None |
| Skills prompt | Skill file paths | No | Low |
| Environment hints | Yes (OS paths) | No | Medium |
| Profile hint | Yes (~/.hermes) | No | Medium |
| Context files | Yes (project paths) | No | Medium |
| Memory context | Memory paths in records | No | Low-Medium |
| Timestamp block | No | No | None |
| Model/provider | No | No | None |

**Critical finding:** The system prompt does NOT contain API keys, base URLs, or authorization headers. It DOES contain local file paths (profile paths, skill paths, project paths).

---

## 7. System Prompt Sources

### Source Files

| Part | Source | File |
|------|--------|------|
| SOUL.md | `HERMES_HOME/SOUL.md` | Read from filesystem |
| Default identity | `DEFAULT_AGENT_IDENTITY` constant | agent/system_prompt.py |
| Tool guidance | Compiled constants | agent/system_prompt.py |
| Skills prompt | `build_skills_system_prompt()` | agent/prompt_builder.py:1053 |
| Environment hints | `build_environment_hints()` | agent/prompt_builder.py:773 |
| Context files | `build_context_files_prompt()` | agent/prompt_builder.py:1482 |
| Memory context | `format_for_system_prompt()` | Memory store/provider |
| Model/provider | `agent.model`, `agent.provider` | Runtime attributes |

### Assembly Priority

1. Stable tier (highest priority, never changes)
2. Context tier (changes per session)
3. Volatile tier (changes per turn, lowest priority)

All tiers are concatenated; there is no override mechanism between tiers.

---

## 8. User Message and History

### User Message Processing

1. User message is received as `user_message` parameter to `run_conversation()` (agent/conversation_loop.py:351)
2. Sanitized via `_sanitize_surrogates()` (removes invalid Unicode)
3. Optional `persist_user_message` override for synthetic prefixes
4. Appended to `messages` list as `{"role": "user", "content": ...}`
5. Memory nudge prefix may be prepended (controlled by `_memory_nudge_interval`)

### Conversation History Loading

1. `conversation_history` parameter passed to `run_conversation()` (list of dicts)
2. In CLI mode: loaded from `SessionDB.get_messages()` via `_load_conversation_history()`
3. In Gateway mode: loaded from `session_store.load_transcript()`
4. History is copied to avoid mutating caller's list: `messages = list(conversation_history)`
5. Todo store hydrated from history
6. Nudge counters reconstructed from history

### Message Format

```python
{"role": "user"|"assistant"|"tool"|"system", "content": "...", "tool_calls": [...], ...}
```

---

## 9. Memory Context Injection

### Source Functions

| Function | File | Side Effects |
|----------|------|-------------|
| `agent._memory_store.format_for_system_prompt("memory")` | Memory store | None (read-only) |
| `agent._memory_store.format_for_system_prompt("user")` | Memory store | None (read-only) |
| `agent._memory_manager.build_system_prompt()` | Memory provider | May be network |
| `agent._memory_manager.prefetch()` | Memory provider | May be network |

### Memory Context Content

- Memory IDs (e.g., `MEM-HERMES-001`)
- Memory titles
- Categories
- Importance scores
- TTL information
- Status (active/archived)
- Updated timestamps
- Summaries

### What Memory Context Does NOT Include

- Storage URIs or file paths (at the format level)
- Full record content (summaries only)
- API keys or secrets
- Internal state variables

### Memory Context Injection Safety

- **Explicit home:** Memory store is initialized with `hermes_home` from agent config
- **Read-only:** `format_for_system_prompt()` only reads; never writes
- **No Memory writes:** No events appended, no records modified
- **No Review enqueue:** No queue items created
- **Character limits:** Configurable via `memory.context.max_categories`, `memory.context.max_memories`, `memory.context.max_chars`

**For Phase 1E Prompt Preview:** Safe to call `format_for_system_prompt()` directly. Must use dev HERMES_HOME. Must NOT call `prefetch()` on external providers (network risk).

---

## 10. Model and Provider Config

### Config Loading Chain

```
hermes_cli/config.py
  → load_config()        — full config with defaults
  → load_config_readonly() — read-only variant

Config fields relevant to Agent:
  - model: str            (model name, e.g., "glm-5-turbo")
  - provider: str         (provider name, e.g., "zai")
  - base_url: str         (API endpoint URL — MAY contain tokens)
  - api_key: str          (API key — SECRET)
  - api_mode: str         (API compatibility mode)
  - temperature: float    (sampling temperature)
  - max_tokens: int       (max output tokens)
  - timeout: int          (request timeout)
  - enabled_toolsets: list (toolset names)
  - disabled_toolsets: list
  - providers: dict       (provider-specific configs — MAY contain secrets)
  - providers_order: list (provider priority)
  - proxy: dict           (proxy config — MAY contain credentials)
  - custom_headers: dict  (additional headers — MAY contain secrets)
```

### Sensitive Config Fields

| Field | Secret Level | Storage |
|-------|-------------|---------|
| `api_key` | **Critical** | `.env` file, env vars |
| `base_url` | **Medium** | config.yaml (may contain tokens) |
| `proxy` credentials | **Critical** | config.yaml |
| `custom_headers` | **Medium** | config.yaml (may contain auth) |
| `model` | Safe | config.yaml |
| `provider` | Safe | config.yaml |
| `temperature` | Safe | config.yaml |
| `max_tokens` | Safe | config.yaml |

### Provider Config Audit

- API keys are loaded from `.env` files via `load_hermes_dotenv()`
- Base URLs may contain embedded tokens (e.g., OpenRouter URLs)
- Provider configs are in `config.yaml` under `providers` key
- All sensitive values must be redacted in preview responses

**For Phase 1E:** Only expose `model` name, `provider` label, `temperature`, `max_tokens`, `timeout`. NEVER expose `api_key`, `base_url`, `proxy`, or `custom_headers`.

---

## 11. LLM Call Boundary

### Where LLM Calls Happen

1. **`_interruptible_api_call()`** in `agent/chat_completion_helpers.py` — main API call
2. **`_interruptible_streaming_api_call()`** — streaming variant
3. Both called from within `_run_agent_loop()` via `_run()` method

### LLM Call Side Effects

- **Network request** to provider endpoint
- **Token consumption** (cost)
- **Rate limiting** impact
- **Response generation** (creates assistant message)

### Phase 1E Guarantee

**No LLM calls will be made.** Prompt Preview and Agent Run Dry-Run only inspect what *would* be sent, never actually send it.

---

## 12. Tool Execution Boundary

### Tool Registration

- Tools register via `registry.register()` in `tools/*.py` files (auto-discovered)
- Each tool declares: `name`, `toolset`, `schema`, `handler`, `check_fn`
- Toolsets defined in `toolsets.py` with hierarchical includes

### Tool Schema in Prompt

- Tool schemas are included in the API request as `tools=[...]` parameter
- NOT embedded in the system prompt text itself
- `format_tools_for_system_message()` (agent/system_prompt.py:377) generates a text summary for the system prompt

### Phase 1E Tool Metadata Exposure

| Field | Safe to Expose | Reason |
|-------|---------------|--------|
| Tool names | Yes | Non-sensitive |
| Tool count | Yes | Non-sensitive |
| Tool descriptions | Conditional | May reveal internal behavior |
| Tool schemas | **No** | May contain parameter templates |
| Tool implementations | **No** | May contain shell commands |
| Tool execution results | **No** | Side effects |

**For Phase 1E:** Return `toolsEnabled=false`, `availableToolCount`, and optionally safe tool name list. Never return full schemas or implementations.

---

## 13. Runtime Memory Writer Boundary

### Trigger Point

`maybe_auto_write_memory()` is called in `agent/conversation_loop.py:4741`:

```python
if final_response and not interrupted:
    maybe_auto_write_memory(
        original_user_message,
        final_response,
        config=load_config_readonly(),
    )
```

### Conditions for Auto-Write

1. `final_response` exists (LLM returned a response)
2. `not interrupted` (turn was not cancelled)
3. Config `memory.auto_write.enabled` is true
4. Evaluation score exceeds thresholds

### Side Effects of Auto-Write

| Decision | Side Effect |
|----------|------------|
| WRITE | Creates new memory record, appends event |
| UPDATE | Modifies existing memory record, appends event |
| REVIEW | Enqueues review queue item |
| SKIP | None |

### Runtime Behavior

- Runs **synchronously** in the conversation loop thread
- Called **after** the final response is generated
- Never called during streaming
- Can be disabled via config or environment variable

**For Phase 1E:** `autoMemoryEnabled=false`, `memoryWriteAvailable=false`, `reviewEnqueueAvailable=false`. Must NEVER call `maybe_auto_write_memory()`.

---

## 14. Review Queue Boundary

### Enqueue Trigger

`enqueue_review_item()` is called from within `maybe_auto_write_memory()` when:
1. Review queue is enabled
2. Evaluation qualifies for review
3. Not a duplicate of existing pending item

### Phase 1E Guarantee

Review queue will never be enqueued during Phase 1E preview operations.

---

## 15. Session / Message Persistence Audit

### Key Finding: AIAgent Auto-Persists All Messages

The `conversation_loop.py` calls `_persist_session()` at **16+ different exit points**, ensuring every code path persists messages:

- Normal completion (line 1216, 1573)
- Tool call completion (line 1735, 1796, 1856, 1877, 1891)
- Error paths (line 2066, 2730, 2944, 2978, 3031, 3100, 3134)
- Context overflow (line 2730)

### Persistence Flow

```
_persist_session(messages, conversation_history)
  → _drop_trailing_empty_response_scaffolding(messages)   [in-memory cleanup]
  → _apply_persist_user_message_override(messages)         [in-memory mutation]
  → _save_session_log(messages)                            [JSON file write]
  → _flush_messages_to_session_db(messages, conversation_history)
      → for msg in messages[flush_from:]:
          → SessionDB.append_message(session_id, role, content, ...)
```

### What Gets Persisted

| Message Type | Persisted By | Storage Function | Timing | Duplicate Risk |
|-------------|-------------|-----------------|--------|---------------|
| User message | Agent Runtime | `_flush_messages_to_session_db()` → `SessionDB.append_message()` | End of turn | See Gateway below |
| Assistant final message | Agent Runtime | Same as above | End of turn | See Gateway below |
| Tool calls | Agent Runtime | Same as above (tool_calls JSON field) | During tool loop | Low |
| Tool results | Agent Runtime | Same as above (role="tool") | During tool loop | Low |
| Reasoning metadata | Agent Runtime | Same as above (reasoning fields) | End of turn | Low |
| Cancelled response | Agent Runtime | Same as above (partial) | On interrupt | Low |
| Failed response | Agent Runtime | Same as above (scaffolding removed) | On error | Low |

### Gateway Double-Persist Prevention

The Gateway (`gateway/run.py:9798-9823`) has explicit double-persist prevention:

```python
# The agent already persisted these messages to SQLite via
# _flush_messages_to_session_db(), so skip the DB write here
# to prevent the duplicate-write bug (#860).
agent_persisted = self._session_db is not None
...
self.session_store.append_to_transcript(
    session_entry.session_id, entry,
    skip_db=agent_persisted,
)
```

The Gateway always writes to JSONL (for backup) but skips SQLite when the agent already persisted.

---

## 16. Double-Persist Decision

### Evidence

1. **AIAgent auto-persists** via `_flush_messages_to_session_db()` at every exit point
2. **Gateway skips DB write** when agent already persisted (`skip_db=agent_persisted`)
3. **CLI mode** has no double-write — agent is the sole persistence owner
4. **Gateway mode** uses `skip_db=True` to prevent double-write

### Decision: Agent Runtime is the Single Persistence Owner

**Selected approach: Option A — Agent Runtime is the sole persistence owner.**

| Context | Persistence Owner | Web API Role |
|---------|------------------|-------------|
| CLI | Agent Runtime | N/A |
| Gateway | Agent Runtime (Gateway uses skip_db) | N/A |
| **Web (Phase 1F)** | **Agent Runtime** | **No direct session/message writes** |

### Rationale

1. The Agent Runtime already has robust persistence at every exit path
2. The Gateway has already solved this problem with `skip_db=True`
3. Adding a second persistence layer in the Web API would reintroduce double-write risk
4. The Web API should follow the same pattern: let the agent persist, skip DB in the web layer

### Required Before Phase 1F

- [ ] Verify that `run_conversation()` can be called from the Web API thread pool
- [ ] Verify that `_session_db` is properly initialized for Web API agent instances
- [ ] Verify that `session_db_created` flag works correctly in Web API context
- [ ] Add test: single `run_conversation()` call → message count increases by exactly expected amount (not doubled)

**Blocker status:** No P1 blocker. The existing code architecture supports Option A. Phase 1F implementation must verify the above items but no architectural change is needed.

---

## 17. Streaming Callback Audit

### Callback Inventory

| Callback | Attribute | Set Where | Receives |
|----------|----------|-----------|----------|
| `stream_delta_callback` | `agent.stream_delta_callback` | `init_agent()` (constructor) | Incremental text deltas (str) |
| `_stream_callback` | `agent._stream_callback` | `run_conversation()` (per-turn) | Text deltas + thinking content |
| `thinking_callback` | `agent.thinking_callback` | `init_agent()` | Thinking/reasoning content |
| `reasoning_callback` | `agent.reasoning_callback` | `init_agent()` | Reasoning content |
| `interim_assistant_callback` | `agent.interim_assistant_callback` | `init_agent()` | Mid-turn assistant messages |
| `tool_gen_callback` | `agent.tool_gen_callback` | `init_agent()` | Tool name when args generating |
| `status_callback` | `agent.status_callback` | `init_agent()` | Status updates |

### Overlap Analysis: stream_delta_callback vs _stream_callback

**Both callbacks are invoked with the same data:**

```python
callbacks = [cb for cb in (self.stream_delta_callback, self._stream_callback) if cb is not None]
for cb in callbacks:
    try:
        cb(text)
    except Exception:
        pass
```

This pattern appears at:
- `run_agent.py:3780` — thinking block tail flush
- `run_agent.py:3794` — context scrubber tail flush
- `run_agent.py:3884` — normal text delta delivery

**Both receive identical text deltas.** If both are registered, the same text is delivered to both — causing double output.

**`_stream_callback`** is set per-turn in `run_conversation()` and was originally designed for the TTS pipeline.

**`stream_delta_callback`** is set at construction time and is the "public" streaming interface.

### Payload Shape

Both callbacks receive a single `str` argument — the incremental text delta.

**Neither is cumulative.** Both receive deltas. The agent tracks cumulative text internally via `_current_streamed_assistant_text`.

### Tool Call Flow

Tool calls do NOT flow through text streaming callbacks. Tool calls are:
1. Received in the API response as structured `tool_calls` data
2. Dispatched to tool handlers
3. Tool results added to messages list
4. Persisted via `_persist_session()`

### Reasoning Flow

Reasoning content flows through:
- `thinking_callback` — dedicated reasoning callback
- `_stream_callback` — also receives thinking content (via scrubber)
- `reasoning_callback` — another reasoning path

### Cancellation Behavior

On cancellation:
1. `_interrupt_requested` flag is set
2. Tool workers receive interrupt signal
3. Any pending streaming text is flushed to callbacks
4. Current turn is persisted (partial)

### Phase 1E Guarantee

No streaming callbacks will be registered during Phase 1E preview operations.

---

## 18. SSE Callback Decision

### Decision: Use `stream_delta_callback` for Phase 1F SSE

**Selected mechanism:** `stream_delta_callback` (constructor-time callback)

### Rationale

1. **True delta interface:** Receives incremental text chunks, ideal for SSE event payloads
2. **Set at construction:** Persistent across turns, no need to re-register per-turn
3. **Public API:** Intentionally exposed for external consumers (TUI uses this)
4. **`_stream_callback` is internal:** Set per-turn, designed for TTS pipeline
5. **Never both:** Must NOT register both simultaneously

### Rules for Phase 1F

1. **Only register `stream_delta_callback`** — never `_stream_callback`
2. **Register at AIAgent construction** — not in `run_conversation()`
3. **Wrap in asyncio bridge:** `loop.call_soon_threadsafe(queue.put_nowait, event)`
4. **Done event:** Triggered by background Future completing, NOT by text delta
5. **Single-generation constraint:** At most one generation per session (HTTP 409 for concurrent)
6. **Client disconnect:** Call `agent.interrupt()` to stop generation

### Double-Emission Prevention

Phase 1F implementation MUST verify:
- `_stream_callback` is NOT set (left as None)
- Only `stream_delta_callback` is registered
- Test: no text is delivered twice for the same chunk

**Blocker status:** No P1 blocker. The choice is clear and well-supported.

---

## 19. Agent Cancellation and Concurrency

### Interrupt Mechanism

`AIAgent.interrupt()` (run_agent.py:2237):
1. Sets `_interrupt_requested = True`
2. Sets `_interrupt_message` (optional new message)
3. Propagates interrupt to tool worker threads
4. Thread-safe via `_execution_thread_id` scoping

### Concurrent Agent Run Risk

- **Same session, concurrent runs:** NOT guarded at the Agent level
- **Gateway:** Has per-session locking (only one message processed at a time)
- **CLI:** Single-threaded, no concurrent risk
- **Web API (Phase 1F):** MUST implement session-level lock (HTTP 409 for concurrent requests to same session)

### Orphaned Thread Risk

When a client disconnects during generation:
1. The agent thread continues running in the background
2. Tool calls may continue executing
3. Memory writer may fire
4. Session persistence may occur

**Mitigation for Phase 1F:**
- Monitor `Request.is_disconnected()` in SSE loop
- Call `agent.interrupt()` on disconnect
- Wait for background Future to complete (with timeout)
- Log orphaned thread warnings

---

## 20. Safe Read-Only Functions

The following functions are safe for Phase 1E Prompt Preview / Dry-Run:

| Function | File | Purpose | Reads Files | Reads DB | Network | Writes | Preview | Dry-Run |
|----------|------|---------|------------|---------|---------|--------|---------|---------|
| `load_config_readonly()` | hermes_cli/config.py | Read config | Yes | No | No | No | ✅ | ✅ |
| `SessionDB(path)` | hermes_state.py | Session DB | Yes | Yes | No | No | ✅ | ✅ |
| `SessionDB.get_session()` | hermes_state.py | Get session | No | Yes | No | No | ✅ | ✅ |
| `SessionDB.get_messages()` | hermes_state.py | Get messages | No | Yes | No | No | ✅ | ✅ |
| `SessionDB.get_messages_around()` | hermes_state.py | Get messages window | No | Yes | No | No | ✅ | ✅ |
| `build_system_prompt_parts()` | agent/system_prompt.py | Build prompt parts | Yes | No | No | No | ✅ | ✅ |
| `build_system_prompt()` | agent/system_prompt.py | Build full prompt | Yes | No | No | No | ✅ | ✅ |
| `format_tools_for_system_message()` | agent/system_prompt.py | Tool summary | No | No | No | No | ✅ | ✅ |
| `build_environment_hints()` | agent/prompt_builder.py | Env hints | Yes | No | No | No | ✅ | ✅ |
| `build_skills_system_prompt()` | agent/prompt_builder.py | Skills prompt | Yes | No | No | No | ✅ | ✅ |
| `build_context_files_prompt()` | agent/prompt_builder.py | Context files | Yes | No | No | No | ✅ | ✅ |
| `format_for_system_prompt()` | Memory store | Memory context | Yes | No | No | No | ✅ | ✅ |
| `redact_local_paths()` | hermes_cli/dev_web_api.py | Path redaction | No | No | No | No | ✅ | ✅ |
| `_sanitize_surrogates()` | agent/conversation_loop.py | Text sanitization | No | No | No | No | ✅ | ✅ |
| `get_hermes_home()` | hermes_constants.py | Home path | No | No | No | No | ✅ | ✅ |
| `evaluate_memory_auto_write(write=False)` | runtime_memory_writer.py | Score evaluation | Yes | No | No | No | ❌ | ✅ |
| `parse_root()` | Memory module | Parse MEMORY.md | Yes | No | No | No | ✅ | ✅ |
| `parse_index()` | Memory module | Parse index | Yes | No | No | No | ✅ | ✅ |
| `list_items()` | Memory module | List memory items | Yes | No | No | No | ✅ | ✅ |

**Note:** `evaluate_memory_auto_write(write=False)` is safe for dry-run but requires careful parameter control.

---

## 21. Forbidden Execution Functions

The following functions MUST NOT be called during Phase 1E:

| Function | File | Side Effects |
|----------|------|-------------|
| `AIAgent.chat()` | run_agent.py:4872 | LLM call + full agent loop + persistence |
| `AIAgent.run_conversation()` | run_agent.py:4859 | LLM call + full agent loop + persistence |
| `run_conversation()` (module) | agent/conversation_loop.py:351 | Full conversation loop |
| `_interruptible_api_call()` | agent/chat_completion_helpers.py | Network request to LLM |
| `_interruptible_streaming_api_call()` | agent/chat_completion_helpers.py | Network request to LLM |
| `registry.dispatch()` | tools/registry.py | Tool execution |
| `handle_function_call()` | model_tools.py | Tool dispatch |
| `maybe_auto_write_memory()` | agent/runtime_memory_writer.py:809 | Memory file writes + review enqueue |
| `enqueue_review_item()` | agent/memory_review_queue.py | Review queue file writes |
| `approve_review_item()` | agent/memory_review_queue.py | Memory file modification |
| `reject_review_item()` | agent/memory_review_queue.py | Review file modification |
| `SessionDB.append_message()` | hermes_state.py:1931 | DB write |
| `SessionDB.create_session()` | hermes_state.py:973 | DB write |
| `SessionDB.replace_messages()` | hermes_state.py | DB write |
| `_persist_session()` | run_agent.py:1438 | JSON file + DB writes |
| `_flush_messages_to_session_db()` | run_agent.py:1507 | DB writes |
| `_save_session_log()` | run_agent.py:2151 | File writes |
| `append_to_transcript()` | gateway/session.py:1251 | DB + JSONL writes |
| `rewrite_transcript()` | gateway/session.py:1285 | DB writes |
| `append_event()` | Memory module | Event log append |
| `ensure_memory_scaffold()` | Memory module | Creates memory directories/files |
| `write_memory_item()` | Memory module | Memory record creation |
| `update_memory_item()` | Memory module | Memory record modification |

### Monkeypatch Verification Strategy

Phase 1E implementation tests should monkeypatch all forbidden functions to fail loudly:

```python
def _forbidden_call(*args, **kwargs):
    raise RuntimeError("Forbidden function called during preview")

monkeypatch.setattr("agent.conversation_loop.run_conversation", _forbidden_call)
monkeypatch.setattr("agent.runtime_memory_writer.maybe_auto_write_memory", _forbidden_call)
# ... etc
```

---

## 22. Proposed Routes

### Prompt Preview

```http
POST /api/dev/v1/agent/prompt/preview
```

### Agent Run Dry-Run

```http
POST /api/dev/v1/agent/run/dry-run
```

### Route Properties

| Property | Value |
|----------|-------|
| Current OpenAPI paths | 21 |
| After Phase 1E | 23 |
| New routes | 2 |
| Real Agent Run route | Absent |
| SSE route | Absent |
| Tool Execute route | Absent |

---

## 23. Prompt Preview Request DTO

```json
{
  "sessionId": "optional-session-id",
  "message": "用户准备发送的消息",
  "options": {
    "includeHistory": true,
    "historyLimit": 20,
    "includeMemoryContext": true,
    "memoryQuery": "optional memory query",
    "maxCategories": 5,
    "maxMemories": 10,
    "includeSystemPreview": false,
    "includeToolMetadata": true
  },
  "overrides": {
    "model": null,
    "temperature": null,
    "maxOutputTokens": null
  }
}
```

### Field Validation

| Field | Required | Type | Limits | Validation |
|-------|----------|------|--------|-----------|
| `message` | **Yes** | string | Max 10000 chars | Non-empty after trim |
| `sessionId` | No | string | Max 256 chars | Safe chars only, no control chars |
| `options.includeHistory` | No | boolean | Default true | — |
| `options.historyLimit` | No | integer | 1–100, default 20 | Bounded |
| `options.includeMemoryContext` | No | boolean | Default true | — |
| `options.memoryQuery` | No | string | Max 500 chars | Sanitized |
| `options.maxCategories` | No | integer | 1–10, default 5 | Bounded |
| `options.maxMemories` | No | integer | 1–20, default 10 | Bounded |
| `options.includeSystemPreview` | No | boolean | Default false | — |
| `options.includeToolMetadata` | No | boolean | Default true | — |
| `overrides.model` | No | string | Max 100 chars | Must match allowlist |
| `overrides.temperature` | No | float | 0.0–2.0 | Range check |
| `overrides.maxOutputTokens` | No | integer | 1–128000 | Range check |

### Forbidden Client Fields

- `apiKey` — NEVER accepted
- `baseUrl` — NEVER accepted
- `systemPrompt` — NEVER accepted
- `toolImplementation` — NEVER accepted
- `execute` — NEVER accepted (always false)

---

## 24. Agent Run Dry-Run Request DTO

```json
{
  "sessionId": "optional-session-id",
  "message": "用户准备发送的消息",
  "options": {
    "includeHistory": true,
    "includeMemoryContext": true,
    "toolsRequested": false,
    "streamRequested": false,
    "autoMemoryRequested": false
  },
  "overrides": {
    "model": null,
    "temperature": null,
    "maxOutputTokens": null
  }
}
```

### Forced-Disabled Capabilities

| Capability | Value | Reason |
|-----------|-------|--------|
| `llmCallRequested` | **false** | No LLM calls in Phase 1E |
| `streamingRequested` | **false** | No SSE in Phase 1E |
| `toolsRequested` | **false** | No tool execution |
| `autoMemoryRequested` | **false** | No memory writes |
| `sessionWriteAvailable` | **false** | No message persistence |

All requested-capability flags are advisory. The server enforces all as false regardless of client input.

---

## 25. Unified Response DTO

### Structure

```json
{
  "data": {
    "dryRun": true,
    "operation": "PROMPT_PREVIEW",
    "allowed": true,
    "blockedReason": null,
    "session": {
      "sessionId": "safe-id",
      "exists": true,
      "historyIncluded": true,
      "historyMessageCount": 12
    },
    "model": {
      "name": "glm-5-turbo",
      "provider": "zai",
      "temperature": 0.7,
      "maxOutputTokens": 2048
    },
    "prompt": {
      "sectionCount": 5,
      "characterCount": 8200,
      "truncated": false,
      "sections": [
        {
          "type": "SYSTEM",
          "included": true,
          "characterCount": 4200,
          "preview": null,
          "redacted": true
        },
        {
          "type": "HISTORY",
          "included": true,
          "messageCount": 12,
          "characterCount": 2100
        },
        {
          "type": "MEMORY_CONTEXT",
          "included": true,
          "memoryCount": 3,
          "characterCount": 1200
        },
        {
          "type": "USER_MESSAGE",
          "included": true,
          "characterCount": 700,
          "preview": "..."
        }
      ]
    },
    "memoryContext": {
      "enabled": true,
      "categoryCount": 2,
      "memoryCount": 3,
      "items": [
        {
          "memoryId": "MEM-HERMES-001",
          "title": "Hermes development",
          "category": "hermes",
          "score": 31,
          "summaryPreview": "..."
        }
      ],
      "truncated": false
    },
    "capabilities": {
      "llmCallRequested": false,
      "llmCallAvailable": false,
      "streamingRequested": false,
      "streamingAvailable": false,
      "toolsRequested": false,
      "toolExecutionAvailable": false,
      "autoMemoryRequested": false,
      "memoryWriteAvailable": false,
      "sessionWriteAvailable": false
    },
    "checks": [
      {
        "code": "NO_LLM_CALL",
        "passed": true,
        "message": "No language model call was made."
      }
    ],
    "noEffects": [
      "No LLM request was sent.",
      "No session message was written.",
      "No memory file was modified.",
      "No tool was executed.",
      "No review item was created."
    ],
    "safety": {
      "readOnly": true,
      "sideEffects": false,
      "llmCalled": false,
      "toolsExecuted": false,
      "sessionWritten": false,
      "memoryWritten": false,
      "reviewQueued": false
    },
    "warnings": []
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

---

## 26. Field Whitelist

### Allowed Response Fields

```
data.dryRun
data.operation
data.allowed
data.blockedReason

data.session.sessionId
data.session.exists
data.session.historyIncluded
data.session.historyMessageCount

data.model.name
data.model.provider
data.model.temperature
data.model.maxOutputTokens

data.prompt.sectionCount
data.prompt.characterCount
data.prompt.truncated
data.prompt.sections[].type
data.prompt.sections[].included
data.prompt.sections[].characterCount
data.prompt.sections[].messageCount
data.prompt.sections[].preview
data.prompt.sections[].redacted

data.memoryContext.enabled
data.memoryContext.categoryCount
data.memoryContext.memoryCount
data.memoryContext.items[].memoryId
data.memoryContext.items[].title
data.memoryContext.items[].category
data.memoryContext.items[].score
data.memoryContext.items[].summaryPreview
data.memoryContext.truncated

data.capabilities.llmCallRequested
data.capabilities.llmCallAvailable
data.capabilities.streamingRequested
data.capabilities.streamingAvailable
data.capabilities.toolsRequested
data.capabilities.toolExecutionAvailable
data.capabilities.autoMemoryRequested
data.capabilities.memoryWriteAvailable
data.capabilities.sessionWriteAvailable

data.checks[].code
data.checks[].passed
data.checks[].message

data.noEffects[]
data.warnings[]

data.safety.readOnly
data.safety.sideEffects
data.safety.llmCalled
data.safety.toolsExecuted
data.safety.sessionWritten
data.safety.memoryWritten
data.safety.reviewQueued

meta.requestId
meta.timestamp
```

---

## 27. Forbidden Response Fields

The following fields MUST NEVER appear in any response:

- `apiKey`, `api_key`, `Authorization`, `Bearer`, `Token`
- `secret`, `cookie`, `credential`
- Raw provider config object
- Private base URL (if it contains tokens)
- Proxy credentials
- Full System Prompt text
- Full Developer Prompt text
- Raw MEMORY.md content
- Raw Memory record content
- Storage URI, record path, index path
- Absolute local file paths
- Full conversation history content
- Reasoning/thinking content
- Codex reasoning items
- Tool implementation code
- Shell command templates
- Traceback/stack trace
- Exception repr
- Exception message with internal details

---

## 28. Redaction and Truncation

### Path Redaction

Reuse existing `redact_local_paths()` function:

```
/Users/... → [local-path]
/home/... → [local-path]
C:\... → [local-path]
file://... → [file-uri-redacted]
```

Preserve: `memory://`, `https://`, `http://`

### Truncation Limits

| Field | Max Length | Strategy |
|-------|-----------|----------|
| User message preview | 500 chars | Truncate with `...` |
| History message preview | 300 chars | Truncate with `...` |
| Memory summary preview | 300 chars | Truncate with `...` |
| System prompt preview | 500 chars | Truncate, only when `includeSystemPreview=true` |
| Check message | 200 chars | Truncate |
| Warning | 200 chars | Truncate |
| Blocked reason | 200 chars | Truncate |
| Model name | 100 chars | Hard limit |
| Provider label | 50 chars | Hard limit |

### System Prompt Exposure Decision

**Selected strategy: B (Structured metadata + optional strictly-redacted preview)**

- Default: Return metadata only (character count, section count, included flag)
- Optional (`includeSystemPreview=true`): Return redacted, truncated preview (max 500 chars)
- **Never** return the full internal System Prompt

Rationale:
- Full System Prompt (Strategy A) would expose internal instructions, tool rules, safety rules, and system architecture
- Metadata-only (Strategy C) is too restrictive — developers need some visibility for debugging
- Strategy B balances observability with security

---

## 29. Error Model

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AGENT_PREVIEW_UNAVAILABLE` | 503 | Agent preview service unavailable |
| `INVALID_AGENT_PREVIEW_REQUEST` | 400 | Request validation failed |
| `INVALID_SESSION_ID` | 400 | Session ID format invalid |
| `SESSION_NOT_FOUND` | 404 | Session does not exist (when required) |
| `INVALID_MODEL_OVERRIDE` | 400 | Model override not in allowlist |
| `INVALID_TEMPERATURE` | 400 | Temperature out of range |
| `INVALID_MAX_OUTPUT_TOKENS` | 400 | Max tokens out of range |
| `AGENT_HISTORY_UNAVAILABLE` | 503 | Cannot read session history |
| `AGENT_MEMORY_CONTEXT_UNAVAILABLE` | 503 | Cannot read memory context |
| `AGENT_CONFIG_UNAVAILABLE` | 503 | Cannot read agent config |
| `AGENT_PROMPT_ASSEMBLY_ERROR` | 500 | Prompt assembly failed |
| `UNSAFE_ENVIRONMENT` | 503 | Environment safety check failed |
| `INTERNAL_ERROR` | 500 | Unexpected internal error |

### Error Envelope

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message (redacted)",
    "details": {}
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

### Error Message Redaction

All error messages must:
- Redact local paths via `redact_local_paths()`
- Never include API keys, tokens, or secrets
- Never include full system prompt content
- Never include stack traces or exception repr
- Use generic descriptions for internal errors

### Semantic Decisions

- `sessionId` not provided but optional → HTTP 200 with `session.exists=false`
- `sessionId` provided but not found → HTTP 404 `SESSION_NOT_FOUND`
- `model` override not in allowlist → HTTP 400 `INVALID_MODEL_OVERRIDE`
- Config read fails → HTTP 503 `AGENT_CONFIG_UNAVAILABLE`

---

## 30. Frontend Information Architecture

### Panel Placement

Within the existing Agent Panel, add three sub-tabs:

1. **Status** (existing — agent status)
2. **Prompt Preview** (new)
3. **Run Dry-Run** (new)

### Prompt Preview Form

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| Session ID | text input | empty | Optional |
| Message | textarea | empty | Required to preview |
| Include History | toggle | true | — |
| History Limit | number | 20 | 1–100 |
| Include Memory Context | toggle | true | — |
| Memory Query | text input | empty | Optional |
| Max Categories | number | 5 | 1–10 |
| Max Memories | number | 10 | 1–20 |
| Include System Metadata | toggle | false | — |
| Include Tool Metadata | toggle | true | — |
| Model Override | select | default | From allowlist |
| Temperature | number | null | 0.0–2.0 |
| Max Output Tokens | number | null | 1–128000 |

**Button:** `Preview Prompt` (NOT "Send", "Run", "Execute", "Call Model")

### Run Dry-Run Form

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| Session ID | text input | empty | Optional |
| Message | textarea | empty | Required |
| Include History | toggle | true | — |
| Include Memory Context | toggle | true | — |
| Requested Streaming | toggle | false | Disabled in Phase 1E |
| Requested Tools | toggle | false | Disabled in Phase 1E |
| Requested Auto-Memory | toggle | false | Disabled in Phase 1E |

**Button:** `Preview Agent Run` (NOT "Run Agent", "Execute")

### Result Panel

Must display:

- **Header:** "Dry-run only" badge
- **No-effects list:** All five "No ..." statements
- **Model section:** Name, provider, temperature, max tokens
- **Prompt section:** Section count, character count, per-section breakdown
- **Memory context:** Category count, memory count, items with scores
- **Capabilities:** All flags with Requested/Available/Forced Disabled status
- **Checks:** All check results
- **Warnings:** Any warnings

### Forbidden UI Elements

- "Run Agent" button
- "Send to Model" button
- "Execute" button
- "Stream" toggle (functional)
- "Commit Message" action
- "Save Session" action
- "Auto Memory" toggle (functional)
- Any element that implies real execution

---

## 31. Accessibility

| Requirement | Implementation |
|------------|----------------|
| Tab navigation | `tablist` / `tab` / `tabpanel` ARIA pattern |
| Form labels | All inputs have associated `<label>` elements |
| Loading state | `aria-busy="true"` on result container |
| Error display | `role="alert"` on error messages |
| Result updates | `aria-live="polite"` on result container |
| Button keyboard | All buttons keyboard-reachable, `focus-visible` styles |
| Disabled state | Semantic `disabled` attribute, `aria-disabled` |
| Motion | Respect `prefers-reduced-motion` |

---

## 32. OpenAPI Strategy

### Current State

- OpenAPI paths: **21** (unchanged by Phase 1E-00)

### After Phase 1E Implementation

- OpenAPI paths: **23** (+2)
- New routes:
  - `POST /api/dev/v1/agent/prompt/preview`
  - `POST /api/dev/v1/agent/run/dry-run`

### Forbidden Routes (Absent)

- `POST /api/dev/v1/agent/run` — Real agent run
- `POST /api/dev/v1/agent/stream` — SSE streaming
- `POST /api/dev/v1/agent/tools/*` — Tool execution
- `POST /api/dev/v1/sessions/{id}/messages` — Direct message writing

---

## 33. dev-check Strategy

### Current State

dev-check unchanged in Phase 1E-00.

### After Phase 1E Implementation

dev-check must verify:

| Check | Expected |
|-------|----------|
| OpenAPI paths | 23 |
| Agent preview routes | 2 |
| Real Agent Run route | Absent |
| SSE route | Absent |
| Tool Execute route | Absent |
| Agent Preview side-effect flags | All `false` |
| `safety.readOnly` | `true` |
| `safety.sideEffects` | `false` |
| `safety.llmCalled` | `false` |

---

## 34. Playwright Smoke Strategy

Phase 1E implementation Smoke must cover:

| Check | Expected |
|-------|----------|
| Agent Panel visible | ✅ |
| Prompt Preview tab visible | ✅ |
| Run Dry-Run tab visible | ✅ |
| No "Run Agent" button | ✅ |
| No "Send to Model" button | ✅ |
| No "Tool Execute" button | ✅ |
| Prompt Preview returns result | ✅ |
| Run Dry-Run returns result | ✅ |
| "No LLM request was sent" displayed | ✅ |
| "No session message was written" displayed | ✅ |
| "No memory file was modified" displayed | ✅ |
| "No tool was executed" displayed | ✅ |
| `safety.sideEffects=false` | ✅ |
| `llmCalled=false` | ✅ |
| `toolsExecuted=false` | ✅ |
| `sessionWritten=false` | ✅ |
| `memoryWritten=false` | ✅ |
| `reviewQueued=false` | ✅ |
| No `/agent/run` request | ✅ |
| No SSE connection | ✅ |
| No provider external request | ✅ |
| Port 5182 not used | ✅ |
| No `localhost` external request | ✅ |
| All 5 themes pass | ✅ |
| 4 viewports no horizontal overflow | ✅ |
| Console errors = 0 | ✅ |
| CORS errors = 0 | ✅ |
| Asset 404 = 0 | ✅ |

---

## 35. Side-Effect Validation Strategy

### Hash Validation

Before and after calling each preview route, verify:

| Resource | Method | Expected |
|----------|--------|----------|
| `state.db` | SHA-256 hash | Unchanged |
| `MEMORY.md` | SHA-256 hash | Unchanged |
| `memory/indexes/` | Directory listing + hashes | Unchanged |
| `memory/records/` | Directory listing + hashes | Unchanged |
| `memory/events.jsonl` | Line count + SHA-256 | Unchanged |
| `memory/snapshots/` | Directory listing | Unchanged |
| `memory/reviews/` | Directory listing | Unchanged |

### Count Validation

| Metric | Method | Expected |
|--------|--------|----------|
| Session message count | `SessionDB.get_messages()` count | Unchanged |
| Review item count | Review directory listing | Unchanged |
| Memory event count | `events.jsonl` line count | Unchanged |

### Filesystem Validation

| Check | Expected |
|-------|----------|
| No new WAL/SHM/journal files | ✅ |
| No new files in `memory/` | ✅ |
| No new files in `memory/reviews/` | ✅ |

### Network Monitoring

| Endpoint | Expected |
|----------|----------|
| LLM provider endpoint | No requests |
| Base URL endpoint | No requests |
| Tool endpoint | No requests |
| Gateway endpoint | No requests |

### Test Fixture Strategy

All tests use `pytest tmp_path`:
- Temporary `state.db`
- Temporary `HERMES_HOME`
- Fabricated sessions and messages
- Fabricated memory context
- Fabricated config

Never copy production config. Never use real API keys.

---

## 36. Test Fixture Design

### Required Test Cases

| Test | Category |
|------|----------|
| Prompt preview without session | Basic |
| Prompt preview with session history | Session |
| Prompt preview with memory context | Memory |
| Prompt preview with both history and memory | Combined |
| Session not found (optional session) | Error — 200 + exists=false |
| Session not found (required session) | Error — 404 |
| Invalid session ID | Error — 400 |
| Memory unavailable | Error — 503 |
| Config unavailable | Error — 503 |
| Model override allowed (in allowlist) | Override |
| Model override blocked (not in allowlist) | Error — 400 |
| Temperature out of range | Error — 400 |
| Max tokens out of range | Error — 400 |
| System Prompt metadata only (default) | Metadata |
| System Prompt with preview (includeSystemPreview=true) | Preview |
| Path redaction verified | Security |
| Secret redaction verified | Security |
| No local paths in response | Security |
| No API keys in response | Security |
| Run dry-run capabilities forced disabled | Capability |
| No LLM call made (monkeypatch verify) | Side-effect |
| No Tool call made (monkeypatch verify) | Side-effect |
| No Session write (hash verify) | Side-effect |
| No Memory write (hash verify) | Side-effect |
| No Review enqueue (count verify) | Side-effect |
| Double-persist protection test | Persistence |
| Streaming callback not registered | Streaming |
| Forbidden functions not called (monkeypatch) | Forbidden |
| Empty message rejected | Validation |
| Message too long rejected | Validation |
| No-effects list present | Response |
| Safety flags all false | Response |
| Agent config points to dev home | Environment |
| Production home rejected | Environment |

---

## 37. Risks

### P0

None identified. No blockers for Phase 1E implementation.

### P1

| Risk | Status | Mitigation |
|------|--------|-----------|
| Prompt Builder coupled to agent instance | **Open** | Phase 1E must either instantiate a minimal agent or extract prompt-building logic into standalone functions |
| Memory context may depend on initialized memory store | **Open** | Phase 1E must verify memory store can be safely initialized in read-only mode |
| `build_system_prompt_parts()` requires a live agent object | **Open** | May need to create a lightweight agent stub with read-only attributes |
| System Prompt may contain profile paths | **Mitigated** | `redact_local_paths()` applied to all preview output |
| Provider config contains API keys | **Mitigated** | Only safe fields (model, provider, temperature) returned |
| Agent Run disconnect may leave orphaned thread | **Phase 1F** | Not relevant for Phase 1E (no agent runs) |
| Same session concurrent runs | **Phase 1F** | Not relevant for Phase 1E (no agent runs) |
| Runtime Memory Writer auto-triggers after agent run | **Phase 1F** | Phase 1E never calls agent run, so writer never triggers |

### P2

| Risk | Notes |
|------|-------|
| Prompt character count vs token count estimation | Approximate, may differ from actual token count |
| Long session history performance | History limit mitigates |
| Memory context scan performance | Category/memory limits mitigate |
| Model override allowlist maintenance | Must be updated when new models added |
| Provider name normalization | Must standardize display names |
| History truncation strategy | Currently simple tail truncation |

---

## 38. Non-Goals

Phase 1E-00 explicitly does NOT:

- Implement the Prompt Preview API
- Implement the Agent Run Dry-Run API
- Call any LLM
- Execute any Agent Run
- Execute any Tool
- Implement SSE
- Register any streaming callback
- Write any Session or Message
- Write any Memory
- Enqueue any Review
- Modify any Provider configuration
- Expose any API Key
- Expose the full System Prompt
- Modify the current OpenAPI (21 paths)
- Modify `dev-check`
- Modify any frontend code
- Modify any backend business code
- Access the production environment (`~/.hermes`)
- Begin Phase 1E implementation

---

## 39. Acceptance Criteria

Phase 1E-00 is complete when all of the following are true:

1. ✅ Current branch is `dev-huangruibang`
2. ✅ Local HEAD matches remote HEAD (`e5d0163f1`)
3. ✅ Worktree is clean before and after
4. ✅ Agent main call chain has been audited with source evidence
5. ✅ Prompt assembly pipeline has been audited (3 tiers documented)
6. ✅ System Prompt sources have been audited
7. ✅ History loading flow has been audited
8. ✅ Memory Context injection has been audited
9. ✅ Model/Provider config has been audited
10. ✅ LLM call entry point has been audited
11. ✅ Tool execution entry point has been audited
12. ✅ Runtime Memory Writer trigger point has been audited
13. ✅ Review Queue trigger point has been audited
14. ✅ Session/Message write points have been audited
15. ✅ `AIAgent.chat()` persistence behavior confirmed (auto-persists via `_persist_session`)
16. ✅ `conversation_loop` persistence behavior confirmed (16+ exit paths)
17. ✅ Double-persist risk has explicit conclusion (Agent Runtime is sole owner)
18. ✅ Phase 1F single persistence owner frozen (Option A: Agent Runtime)
19. ✅ `stream_callback` audited (per-turn, TTS pipeline)
20. ✅ `stream_delta_callback` audited (constructor-time, public API)
21. ✅ Callback overlap confirmed (both receive same deltas)
22. ✅ Phase 1F SSE mechanism frozen (`stream_delta_callback`)
23. ✅ Agent interrupt mechanism audited
24. ✅ Concurrent run risk audited
25. ✅ Orphaned thread risk audited
26. ✅ Safe read-only functions listed (20+ functions)
27. ✅ Forbidden execution functions listed (22+ functions)
28. ✅ Prompt Preview route草案 frozen
29. ✅ Agent Run Dry-Run route草案 frozen
30. ✅ Prompt Preview request DTO frozen
31. ✅ Run Dry-Run request DTO frozen
32. ✅ Unified response DTO frozen
33. ✅ DTO field whitelist frozen
34. ✅ System Prompt exposure strategy frozen (metadata + optional redacted preview)
35. ✅ Redaction and truncation rules frozen
36. ✅ Error model frozen (13 error codes)
37. ✅ Frontend IA frozen (3 sub-tabs, forms, result panel)
38. ✅ OpenAPI strategy clear: current 21 paths, future 23 paths
39. ✅ dev-check strategy defined
40. ✅ Playwright Smoke strategy defined (30+ checks)
41. ✅ Side-effect hash strategy defined
42. ✅ Test fixture strategy defined (35+ test cases)
43. ✅ No LLM calls made
44. ✅ No Agent Runs executed
45. ✅ No Tool Execution
46. ✅ No Session writes
47. ✅ No Message writes
48. ✅ No Memory writes
49. ✅ No Review enqueue
50. ✅ No APIs implemented
51. ✅ No business code modified
52. ✅ No frontend modified
53. ✅ No OpenAPI modified
54. ✅ `memory-check` PASS
55. ✅ `dev-check` PASS
56. ✅ `compileall` PASS
57. ✅ Documentation complete
58. ✅ Local commit created
59. ✅ Not pushed
60. ✅ Final worktree clean
61. ✅ Production Gateway PID 1717 unaffected
62. ✅ Dev Gateway stopped
63. ✅ Ports 5180/5181 free
64. ✅ Phase 1E implementation not started

---

## 40. Next Phase

**Phase 1E: Agent Prompt Preview / Dry-Run Implementation**

Must NOT begin automatically. Requires explicit user initiation.

---

## 41. Document Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-06-09 | Claude | Initial scope freeze document |
