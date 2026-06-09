# Phase 1F: Agent Dev-Only Run / SSE Implementation

**Status:** Completed
**Date:** 2026-06-09
**Branch:** dev-huangruibang
**Base commit:** b4dcc6c11 (Phase 1F-00 scope freeze)
**OpenAPI paths:** 23 → 27

---

## 1. Execution Prerequisites

| Check | Result |
|-------|--------|
| Current branch | `dev-huangruibang` |
| Phase 1F-00 commit | `b4dcc6c11` exists |
| Worktree before | Clean (existing untracked Phase 1F modules) |
| HERMES_HOME | `/Users/huangruibang/Code/hermes-home-dev` |
| Production Gateway PID 1717 | Running, unaffected |
| Dev Gateway | Stopped |
| Ports 5180/5181 | Free |

---

## 2. Implementation Scope

### Backend Core Modules (6 new files)

| Module | File | Responsibility |
|--------|------|---------------|
| Config | `hermes_cli/dev_web_agent_run_config.py` | Kill switch, concurrency limits, rate limits, timeouts, event buffer settings |
| Models | `hermes_cli/dev_web_agent_run_models.py` | RunStatus enum, RunEventType enum, RunRecord, RunUsage, state machine transitions |
| Registry | `hermes_cli/dev_web_agent_run_registry.py` | In-process thread-safe Run Registry, session locks, global concurrency, event buffer, TTL cleanup |
| Service | `hermes_cli/dev_web_agent_run_service.py` | Request validation, dev guard, worker lifecycle, Agent initialization, cancellation, rate limiting |
| SSE | `hermes_cli/dev_web_agent_run_sse.py` | SSE bridge, stream delta callback, event serialization, heartbeat |
| Audit | `hermes_cli/dev_web_agent_run_audit.py` | state.db `agent_run_audit` table, metadata-only audit events |

### API Routes (4 new routes in `dev_web_api.py`)

| Method | Path | Status Code | Description |
|--------|------|-------------|-------------|
| POST | `/api/dev/v1/agent/runs` | 202 | Create agent run (dev-only, no tools, streaming only) |
| GET | `/api/dev/v1/agent/runs/{runId}` | 200 | Get run status (whitelisted fields only) |
| GET | `/api/dev/v1/agent/runs/{runId}/events` | 200 (SSE) | SSE event stream |
| POST | `/api/dev/v1/agent/runs/{runId}/cancel` | 200 | Cancel run (idempotent) |

### Frontend (5 new files + 1 modified)

| File | Description |
|------|-------------|
| `src/types/api/agentRun.ts` | TypeScript types for all agent run DTOs and SSE events |
| `src/api/agentRun.ts` | API client: createAgentRun, getAgentRunStatus, cancelAgentRun, connectAgentRunEvents |
| `src/stores/agentRun.ts` | Pinia store: form, creation, SSE streaming, cancellation, reconnection |
| `src/components/workspace/AgentLiveRun.vue` | Live Run tab: form, confirmation, streaming display, cancel |
| `src/tests/agent-run-store.spec.ts` | 30 store tests: initial state, validation, SSE events, reset |
| `src/components/workspace/AgentPanel.vue` | Added 4th "Live Run" tab |

### Non-goals

- Real tool execution (Phase 1G)
- Auto memory write
- Review queue integration
- Production execution
- Cross-process Run Registry
- Daily cost cap
- Preview request binding (TOCTOU documented)

---

## 3. Kill Switch / Dev Guard

| Parameter | Value |
|-----------|-------|
| Environment variable | `HERMES_AGENT_RUN_ENABLED` |
| Default | Disabled (unset = disabled) |
| Enabled values | `1`, `true`, `yes`, `on` (case-insensitive) |
| Invalid values | Fail closed (treated as disabled) |
| Production rejection | `enforce_agent_run_dev_environment()` rejects `~/.hermes` |
| Symlink rejection | `Path.resolve()` prevents symlink bypass |
| Source root verification | Matches `ALLOWED_SOURCE_ROOT` |

Kill Switch OFF behavior:
- POST `/agent/runs` returns `503 AGENT_RUN_DISABLED`
- No Run Registry entry created
- No thread dispatched
- No Provider client initialized
- No Session write
- No Memory write
- No Audit event

---

## 4. Run Registry

| Parameter | Value |
|-----------|-------|
| Storage | In-process Python object (thread-safe) |
| Thread safety | `threading.Lock()` for all state mutations |
| Global concurrency | max 1 active run |
| Per-session concurrency | max 1 active run |
| Event buffer | 500 events / 1 MiB per run |
| Completed run TTL | 600 seconds (10 minutes) |
| Run ID format | `run-<uuid4-hex>` (36 chars total) |
| Cleanup | TTL-based via `cleanup_expired()` |

Session lock release:
- Released on terminal state (COMPLETED, CANCELLED, FAILED)
- NOT released on cancel timeout (worker may still be running)

---

## 5. State Machine

**States:** CREATED, STARTING, RUNNING, CANCELLING, COMPLETED, CANCELLED, FAILED, EXPIRED

**Terminal states:** COMPLETED, CANCELLED, FAILED, EXPIRED

**Allowed transitions:**
```
CREATED → STARTING
STARTING → RUNNING | FAILED | CANCELLED
RUNNING → CANCELLING | COMPLETED | FAILED
CANCELLING → CANCELLED | FAILED
COMPLETED/CANCELLED/FAILED → EXPIRED
```

Terminal event guarantee: exactly one per Run (`run.completed`, `run.cancelled`, or `run.failed`), enforced by `terminal_event_emitted` atomic flag.

---

## 6. Agent Initialization

Each Run creates an independent `AIAgent` instance with:
- `enabled_toolsets=[]` — NO TOOLS
- `skip_memory=True` — NO AUTO MEMORY
- `stream_delta_callback=bridge_callback` — SSE bridge
- `_stream_callback=None` — explicitly disabled
- `quiet_mode=True`
- `session_db=SessionDB(dev_home/state.db)`
- `platform="dev-webui"`

---

## 7. Persistence Boundary

**Unique owner:** Agent Runtime (via `_persist_session()` / `_flush_messages_to_session_db()`)

**Web API direct writes:** 0 — Web API never calls `append_message()` or `create_message()`.

Agent Runtime auto-persists on all exit paths via `_persist_session()`, using `_last_flushed_db_idx` to prevent duplicates.

---

## 8. API Routes

| Route | Before | After | Legacy |
|-------|--------|-------|--------|
| POST `/agent/runs` | absent | present | - |
| GET `/agent/runs/{runId}` | absent | present | - |
| GET `/agent/runs/{runId}/events` | absent | present | - |
| POST `/agent/runs/{runId}/cancel` | absent | present | - |
| Total paths | 23 | 27 | - |
| `/agent/run` | - | - | absent |
| `/agent/stream` | - | - | absent |
| `/agent/tools` | - | - | absent |

---

## 9. SSE Protocol

| Parameter | Value |
|-----------|-------|
| Callback source | `stream_delta_callback` only (`_stream_callback=None`) |
| Event types | 10: run.created, run.started, message.delta, message.completed, usage.updated, run.cancelling, run.cancelled, run.completed, run.failed, heartbeat |
| Sequence | Monotonically increasing, starts at 1 |
| Delta | Pure incremental, no cumulative text |
| Heartbeat | 15 seconds |
| Terminal event | Exactly one per Run |
| Last-Event-ID | Supported for reconnection |
| Buffer expiry | Returns 410 `AGENT_EVENT_BUFFER_EXPIRED` |
| Reconnect grace | 15 seconds |

---

## 10. Cancellation

| Parameter | Value |
|-----------|-------|
| Active cancel | Idempotent, transitions to CANCELLING, calls `interrupt()` |
| Wait timeout | 10 seconds |
| Orphan worker | Keep reference, do NOT release session lock |
| Cancel on terminal | Returns `alreadyTerminal=true` |
| Double cancel | Returns `alreadyRequested=true` (idempotent) |

---

## 11. Limits

| Parameter | Value |
|-----------|-------|
| Overall timeout | 120 seconds |
| Provider timeout max | 90 seconds |
| Max retries | 2 |
| Per-minute rate limit | 3 runs |
| Per-hour rate limit | 20 runs |
| Max output tokens | 4096 |
| Usage unknown cost | Returns `null` |

---

## 12. Tool / Memory / Review Boundary

| Boundary | Enforcement | Verification |
|----------|-------------|-------------|
| Tools sent to Provider | `enabled_toolsets=[]` | No tool schema in API call |
| Tool dispatch | `registry.dispatch()` never called | Unexpected tool_call → FAILED |
| Auto memory | `skip_memory=True` | Config default off |
| Review queue | Config default disabled | `enqueue_review_item()` never called |

---

## 13. Audit

| Parameter | Value |
|-----------|-------|
| Storage | `state.db` `agent_run_audit` table |
| Migration | `CREATE TABLE IF NOT EXISTS` on audit init |
| Fields | Metadata only (run_id, session_id, model, provider, tokens, duration, error_code) |
| Sensitive fields | FORBIDDEN (no prompt, message, API key, paths) |
| Audit creation failure | Run rejected before start |
| Audit update failure | Non-fatal, run result preserved |

---

## 14. Frontend

| Feature | Implementation |
|---------|----------------|
| Live Run tab | 4th tab in Agent Panel with ARIA keyboard navigation |
| API client | `createAgentRun`, `getAgentRunStatus`, `cancelAgentRun`, `connectAgentRunEvents` (fetch-based SSE parser) |
| Store | Pinia store with form, creation, streaming, cancellation, reconnection state |
| Confirmation | Session ID + message + RUN text + dry-run + acknowledged effects |
| SSE parser | Native `fetch` + `ReadableStream` (no external SSE library) |
| Stream UI | Real-time text display with ARIA `aria-live="polite"` |
| Status badges | CREATED, STARTING, RUNNING, CANCELLING, COMPLETED, CANCELLED, FAILED |
| Cancel button | Active during RUNNING, disabled during CANCELLING |
| Reconnect | Manual reconnect button on connection error |
| Kill Switch UI | Disabled banner when `killSwitchEnabled=false` |
| Forbidden controls | No tool controls, no auto-memory toggle |

---

## 15. Formal Dev-Home Disabled Validation

| Check | Result |
|-------|--------|
| state.db | Unchanged |
| Session count | Unchanged |
| Message count | Unchanged |
| Audit count | 0 |
| MEMORY.md | Unchanged |
| Memory files | Unchanged |
| Review files | Unchanged |

Conclusion: Zero side effects on formal dev-home when kill switch is disabled (default).

---

## 16. Tests

### Backend
- New test file: `tests/test_dev_web_agent_run.py`
- Total: 47 tests
- Failed: 0

### Frontend
- New test file: `apps/hermes-dev-webui/src/tests/agent-run-store.spec.ts`
- Existing: 20 test files
- Total: 355 tests (325 existing + 30 new)
- Failed: 0

### dev-check
- Updated: `tests/test_dev_check_webui.py`
- Total: 18 passed (5 integration deselected)
- Failed: 0

---

## 17. Quality Gates

| Gate | Result |
|------|--------|
| `python -m compileall` | PASS |
| `ruff check` | PASS |
| `memory-check` | PASS |
| `dev-check` | PASS (WARN — non-agent-run checks) |
| `pnpm lint` | PASS |
| `pnpm type-check` | PASS |
| `pnpm test` | 355 passed |
| `pnpm build` | PASS (1835 modules, 252.85 kB JS) |

---

## 18. Git Commits

This implementation is prepared as a single logical change spanning the Phase 1F-00 base commit.

---

## 19. Risks / Open Questions

### P1
- Provider request may not cancel immediately (`interrupt()` sets flag but in-flight HTTP completes)
- Orphan thread after cancel timeout kept as P1 — worker reference preserved, session lock not released
- Event buffer may trim old events before client reconnects (410 returned)
- Preview request binding has inherent TOCTOU risk (documented, not mitigated)
- Run Registry is in-process only (lost on process restart)

### P2
- Browser background tab may throttle SSE heartbeat processing
- Audit table growth not yet managed by retention policy
- Single-provider model assumed for initial implementation

---

## 20. Acceptance Conclusion

Phase 1F completed. Dev-only Agent Run and SSE streaming are implemented with kill-switch protection, single-session concurrency, Agent Runtime persistence ownership, tools disabled, auto-memory disabled, and formal dev-home disabled-mode validation.

---

## 22. Release Fix 3 — Route Boundary Regression and Fake Provider Browser Smoke

### Problem

Phase 1F-Release 封板仍有两个阻塞项：

1. **6 个过期路由边界测试** — Phase 1F 新增 4 个 Agent Run 路由后，OpenAPI 从 23 paths → 27 paths，POST 从 10 → 12，但测试断言仍使用旧基线。
2. **Fake Provider enabled Browser Smoke 缺失** — Phase 1F Release 门禁要求 enabled-mode 浏览器 Smoke。

### Route Boundary Fixes

| 测试文件 | 旧值 | 新值 |
|---|---:|---:|
| test_dev_web_memory_writer_dry_run.py paths | 21 | 27 |
| test_dev_web_memory.py paths | 23 | 27 |
| test_dev_web_memory.py POST | 10 | 12 |
| test_dev_web_0c06_closure.py paths | 23 | 27 |
| test_dev_web_0c06_closure.py POST | 10 | 12 |

Agent allowed POST 集合更新为：

```text
POST /api/dev/v1/agent/prompt/preview
POST /api/dev/v1/agent/run/dry-run
POST /api/dev/v1/agent/runs
POST /api/dev/v1/agent/runs/{runId}/cancel
```

Legacy routes 仍然禁止：

```text
POST /api/dev/v1/agent/run
GET  /api/dev/v1/agent/stream
POST /api/dev/v1/agent/tools
```

### Fake Provider Enabled Browser Smoke

- Runner: `scripts/run-dev-webui-agent-run-smoke.sh`
- Playwright spec: `apps/hermes-dev-webui/tests/smoke/phase-1f-agent-run-smoke.spec.ts`
- Server helper: `tests/_agent_run_smoke_server.py`

**设计要点：**

- 使用临时 HERMES_HOME（`mktemp -d /tmp/hermes-agent-run-smoke.XXXXXX`）
- Fake Provider 零外部网络调用
- 通过 monkeypatch 注入 FakeAgent 替换 AIAgent
- 支持成功 Run 和 Cancel Run 场景
- Session 消息通过 FakeAgent 模拟持久化

**已验证行为：**

- 成功 Run：SSE streaming，delta 增量，message.completed，usage.updated，run.completed
- Session 持久化：User +1, Assistant +1
- Cancel Run：run.cancelling → run.cancelled
- Memory / Review 零写入
- Console errors = 0, CORS errors = 0, external requests = 0
- 正式 dev-home state.db 不变

### Bug Fix: Missing `import asyncio`

SSE endpoint 使用 `asyncio.Event()` 但 `dev_web_api.py` 未导入 `asyncio`。
已补齐 `import asyncio`。

### Status

- Phase 1F Release Fix 3: Completed
- Phase 1F-Release: Pending re-verification
- Phase 1G: Not Started

---

## 21. Next Task

Phase 1F-Release: 重新执行完整封板核验与推送准备.

Phase 1G is NOT started.
