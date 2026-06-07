# Phase 0C-03: Session List and Detail Read-only Integration

**Status:** Completed
**Date:** 2026-06-07
**Branch:** dev-huangruibang

## Scope

Connect the Dev Web API backend to the real Hermes development session database (`state.db`) via read-only queries, and switch the Dev WebUI Session Sidebar from local mock data to live API data.

## Architecture

### Backend

```
FastAPI Route (sync def)
    ↓
DevSessionQueryService
    ↓
SessionDB(db_path, read_only=True)
    ↓
DTO Transformer (explicit whitelist)
    ↓
Response Schema
```

### SessionDB Access

- **Path:** Derived from `DevWebApiConfig.hermes_home / "state.db"`
- **Mode:** `SessionDB(read_only=True)` — SQLite `mode=ro` URI
- **Lifecycle:** Short-lived per request, closed in `finally` block
- **No context manager:** SessionDB doesn't implement `__enter__`/`__exit__`; explicit `close()` required

### Query Design

- **List:** Custom SQL with correlated subqueries for `preview` (first user message, 63 chars max) and `last_active` (MAX of message timestamps, falls back to `started_at`)
- **Detail:** Uses `SessionDB.get_session()` (public API) for base row, plus separate lightweight query for `last_active`
- **Count:** Separate `SELECT COUNT(*)` query with same WHERE clause (no pagination)
- **Sort:** Whitelisted ORDER BY clauses — `recent` (last_active DESC) or `created` (started_at DESC), both with stable secondary sort by `id DESC`
- **Search:** Parameterized `LIKE` on `title` and `id` columns — no message content search in P0C-03

## API Endpoints

### GET /api/dev/v1/sessions

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| limit | int | 30 | 1–100 |
| offset | int | 0 | ≥ 0 |
| query | string | null | max 500 chars, title+ID search |
| source | string | null | filter by source platform |
| order | enum | recent | `recent`, `created` |
| archived | enum | exclude | `exclude`, `include`, `only` |

**Response fields (SessionListItem):** id, title, source, model, messageCount, toolCallCount, archived, startedAt, endedAt, lastActiveAt, preview

### GET /api/dev/v1/sessions/{sessionId}

**Response fields (SessionDetail):** id, title, source, model, messageCount, toolCallCount, inputTokens, outputTokens, archived, startedAt, endedAt, lastActiveAt, endReason

### Status Update

`GET /api/dev/v1/status` now reports real session availability:
```json
"sessions": { "available": true, "readOnly": true }
```

## DTO Whitelist

Only explicitly approved fields are returned. The following are **never** included:

- `system_prompt`, `model_config`, `user_id`, `cwd`
- `billing_provider`, `billing_base_url`, `billing_mode`
- `estimated_cost_usd`, `actual_cost_usd`, `cost_status`
- `pricing_version`, `api_call_count`
- `handoff_state`, `handoff_platform`, `handoff_error`
- `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens`
- `parent_session_id`, `rewind_count`

Time fields are converted from Unix timestamp (seconds, REAL) to ISO 8601 UTC strings.

## Error Handling

| Condition | HTTP | Code |
|-----------|------|------|
| Session not found | 404 | `SESSION_NOT_FOUND` |
| Database missing/corrupt | 503 | `SESSION_STORE_UNAVAILABLE` |
| Invalid session ID | 400 | `INVALID_PARAMETER` |
| Invalid limit/offset | 422 | `VALIDATION_ERROR` |

Error messages never include file paths, SQL, traceback, or internal details.

## Frontend

### API Client (`src/api/client.ts`)

- Unified fetch wrapper with timeout (8s), abort, X-Request-ID
- Typed error parsing with `DevApiError` interface
- No Axios — uses native `fetch`

### Session Store (`src/stores/session.ts`)

- Pinia store with `loadSessions`, `reloadSessions`, `loadMoreSessions`
- Debounced search (300ms) via `setSearchQuery`
- Session selection with detail loading and cancellation
- Request sequencing to prevent stale responses from overwriting new ones
- `localStorage` persistence for `selectedSessionId`, `sortOrder`, `archivedFilter`

### Sidebar Integration

- `SessionSidebar.vue` now uses the store instead of mock `shellSessions`
- States: Loading (spinner), Empty, Error (with Retry), Success (session list)
- Load More button when `hasMore` is true
- Search triggers debounced server-side search

### Workspace Behavior

- No session selected → "Select a session from the sidebar" prompt
- Session selected → Detail summary (safe fields only)
- Message history → Placeholder: "Message history integration will be available in Phase 0C-04"
- Composer → Still disabled, marked "Read only"

### Mock Data

- `src/mocks/workspace-shell.ts` preserved for existing test fixtures
- Runtime code does NOT import or use mock session data
- `workspaceCapabilities` array still used in ChatWorkspaceShell placeholder

## Tests

### Backend (92 new tests in `tests/test_dev_web_sessions.py`)

- List basics (9 tests): 200, empty, single, multi, pagination, null title, unicode
- Sorting (3 tests): recent, created, stable with offset
- Search (10 tests): title, ID, case-insensitive, trim, empty, no results, Chinese, SQL injection, no system_prompt match
- Filter (5 tests): source, archived exclude/include/only
- Pagination validation (7 tests): min/max/zero/exceeds limit, negative/large offset, no duplicates
- Detail (10 tests): 200, 404, fields, no messages, null fields, special chars, URL encoding, too long, control chars, SQL injection
- Sensitive field exclusion (4 tests): values and field names excluded from both list and detail
- Read-only guarantee (4 tests): hash unchanged, no WAL/journal, read_only=True verified
- Database unavailability (5 tests): missing, corrupted, directory, error message safety
- Request ID (6 tests): present in all response types
- Status (3 tests): available with DB, unavailable without, no crash without home
- Preview (3 tests): from first user message, null when no messages, max length
- Time conversion (3 tests): null, valid, negative
- Service helpers (13 tests): escape_like, build_preview, validate_session_id, transform whitelist
- OpenAPI routes (5 tests): session paths present, no messages/memory/agent

### Frontend (43 new + 12 updated tests)

- API client (13 tests): URL, headers, success, 400, 404, 503, network error, abort, non-JSON, helpers
- Session store (24 tests): initial state, load, empty, error, retry, search, clear search, load more, dedup, select, 404, 503, skip reload, clear, concurrent list, concurrent detail, persistence, reset, no mock
- Session sidebar (12 tests): titles, collapsed, controls, selection, empty, active, new session disabled, loading, error, load more, search

## Security Verification

- ✅ Only development `state.db` accessed
- ✅ `SessionDB(read_only=True)` enforced
- ✅ Database hash unchanged after requests
- ✅ No sensitive fields in API responses
- ✅ Parameterized queries (no SQL injection)
- ✅ Error messages sanitized (no paths, SQL, traceback)
- ✅ CORS: `http://127.0.0.1:5180` only
- ✅ Host: `127.0.0.1` only
- ✅ No LLM, Tool, Memory, or Agent calls
- ✅ Production Gateway (PID 1717) unaffected
- ✅ No production `~/.hermes` access

## Files Changed

### New Files

| Path | Purpose |
|------|---------|
| `hermes_cli/dev_web_session_service.py` | Session query service with DTO whitelist |
| `tests/test_dev_web_sessions.py` | 92 session API tests |
| `apps/hermes-dev-webui/src/api/client.ts` | Unified Dev API fetch client |
| `apps/hermes-dev-webui/src/api/sessions.ts` | Session API functions |
| `apps/hermes-dev-webui/src/types/api/session.ts` | Session TypeScript types |
| `apps/hermes-dev-webui/src/stores/session.ts` | Session Pinia store |
| `apps/hermes-dev-webui/src/tests/api-client.spec.ts` | API client tests |
| `apps/hermes-dev-webui/src/tests/session-store.spec.ts` | Session store tests |

### Modified Files

| Path | Change |
|------|--------|
| `hermes_cli/dev_web_api.py` | Added session routes, updated status, added Sessions tag |
| `hermes_cli/dev_web_schemas.py` | Added session Pydantic models |
| `hermes_cli/dev_web_errors.py` | Added SESSION_NOT_FOUND, SESSION_STORE_UNAVAILABLE codes |
| `tests/test_dev_web_api.py` | Updated route boundary tests for new endpoints |
| `apps/hermes-dev-webui/src/components/layout/SessionSidebar.vue` | Uses session store instead of mock |
| `apps/hermes-dev-webui/src/components/layout/AppLayout.vue` | Uses session store |
| `apps/hermes-dev-webui/src/components/layout/ChatWorkspaceShell.vue` | Shows session detail or placeholder |
| `apps/hermes-dev-webui/src/tests/session-sidebar.spec.ts` | Updated for store-based sidebar |
| `apps/hermes-dev-webui/src/tests/workspace-view.spec.ts` | Updated for new workspace text |

## Non-goals

- Message reading (Phase 0C-04)
- Session write operations
- SSE/WebSocket real-time updates
- Agent/LLM integration
- Memory/Context endpoints
- Message content search
- Compression chain projection

## Phase 0C-04 Inputs

Phase 0C-04 (Session Message Read-only Integration) will need:

1. Session ID from the sidebar selection (already available in store)
2. Message list endpoint: `GET /api/dev/v1/sessions/{sessionId}/messages`
3. Message content rendering in ChatWorkspaceShell
4. Streaming message preview design decisions

---

## Phase 0C-03A: Closure Validation

### SessionDB Read-only Close Fix

**Problem:** `SessionDB.close()` unconditionally attempted `PRAGMA wal_checkpoint(TRUNCATE)` even for read-only connections. Read-only connections cannot checkpoint, so the attempt would fail and be silently caught, but the attempt itself was incorrect.

**Fix:** Added `if not self.read_only:` guard before the checkpoint block in `hermes_state.py` line 656.

**Verification:**
- Read-only connection: WAL/SHM mtime unchanged after close (no checkpoint attempted)
- Writable connection: checkpoint behavior preserved
- `state.db` hash unchanged: `6bccb704e3...` (pre and post test)
- WAL stays 0 bytes

### Search Contract Alignment

**Decision:** Phase 0C-03 `query` parameter searches **session title and session ID only**. Message-content full-text search is deferred to Phase 0C-04 or a separately approved task.

**Changes:**
- `docs/webui/openapi/dev-web-api-v1.yaml`: Updated query description from "FTS5 search in message content" to "Search session titles and session identifiers. Message contents are not searched in Phase 0C-03."
- `docs/webui/dev-web-api-v1.md`: Updated query description
- `hermes_cli/dev_web_api.py`: Added `description` to FastAPI `Query()` parameter for runtime OpenAPI
- `apps/hermes-dev-webui/src/components/layout/SessionSidebar.vue`: Placeholder changed from "Search sessions" to "Search title or ID"

### Browser Integration Validation

**Environment:** Chrome, WebUI `http://127.0.0.1:5180`, API `http://127.0.0.1:5181`

**Verified via systematic integration test (40/42 checks passed):**
- ✅ Session list loads with 417 sessions
- ✅ Pagination works (no duplicate IDs across pages)
- ✅ Search by title works (e.g. "Review" → 1 result)
- ✅ Search does not match message content or sensitive fields
- ✅ Session detail loads with safe DTO fields only
- ✅ No sensitive fields (systemPrompt, modelConfig, cwd, userId, billing) in any response
- ✅ 404 returns SESSION_NOT_FOUND with requestId
- ✅ CORS allows `http://127.0.0.1:5180` origin
- ✅ Runtime OpenAPI has 4 business paths, no messages/memory/agent
- ✅ Query parameter description mentions title/session, no FTS5
- ✅ state.db hash unchanged after all requests
- ✅ WAL unchanged (0 bytes, mtime unchanged after close fix)

### Additional Tests Added

- 4 tests: `TestSessionDBCloseReadOnly` — read-only skips checkpoint, closes connection, WAL/SHM unchanged, writable still checkpoints
- 7 tests: `TestSearchScopeContract` — title/ID hit, message/system_prompt/cwd/user_id/billing don't hit
- 2 tests: `TestOpenAPISearchDescription` — description mentions title/session, no FTS5 claim
5. Tool call card rendering
6. Reasoning/reasoning_content display strategy
