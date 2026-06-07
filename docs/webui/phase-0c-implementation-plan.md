# Phase 0C Implementation Plan

**Date:** 2026-06-07
**Status:** In Progress
**Depends on:** Phase 0C-01 API Contract (accepted)

---

## Overview

Phase 0C replaces static mock data with real data from the Hermes development instance, connected through a read-only Dev API server.

---

## Phase 0C-02: Dev API Server Skeleton — Completed

**Implementation commit:** `ccf8320c1`

### Goal

Create the FastAPI application skeleton with environment validation, CORS, error handling, and the status endpoint. No real data access yet.

### Input

- ADR-WEBUI-001 (accepted)
- API Contract v1
- Data Flow Design

### Output

- `hermes_cli/dev_web_api.py` — FastAPI application
- `hermes_cli/dev_web_schemas.py` — Shared response/error models
- `hermes_cli/dev_web_config.py` — Configuration and environment validation
- CLI entry point: `hermes dev-webui-api`
- Tests for environment validation, CORS, error format

### Dependencies

- None (can start immediately)

### Modification Scope

| File | Action |
|------|--------|
| `hermes_cli/dev_web_api.py` | **New** — FastAPI app with CORS, middleware, error handler |
| `hermes_cli/dev_web_schemas.py` | **New** — Pydantic models for response envelope |
| `hermes_cli/dev_web_config.py` | **New** — Environment validation, constants |
| `hermes_cli/main.py` | **Modify** — Add `dev-webui-api` command registration |
| `hermes_cli/commands.py` | **Modify** — Add command definition |
| `tests/test_dev_web_api.py` | **New** — Skeleton tests |

### Test Requirements

- Environment validation rejects non-dev HERMES_HOME
- CORS only allows `http://127.0.0.1:5180`
- Error response matches contract (code, message, requestId, timestamp)
- GET /api/dev/v1/status returns 200 with correct structure
- Server binds to 127.0.0.1 only
- Server rejects startup if bind host is not 127.0.0.1

### Acceptance Criteria

- `python -m hermes_cli.main dev-webui-api` starts on `127.0.0.1:5181`
- Status endpoint returns valid JSON
- Non-dev HERMES_HOME causes immediate exit with error
- All tests pass
- No modification to production files

### Risks

- **Low:** Port 5181 may be in use — handle gracefully with error message

### Not Included

- Real session/memory/agent data access
- Frontend changes
- SSE or streaming

---

## Phase 0C-03: Session List and Detail Read-only Integration — Completed

**Implementation commits:** backend + frontend + docs (3 commits)

### Goal

Wire the session list and session detail endpoints to real SessionDB read-only queries. Connect the frontend Session Sidebar to the live API.

### Input

- Phase 0C-02 skeleton (running)
- SessionDB audit results from Phase 0C-01

### Output

- `hermes_cli/dev_web_session_service.py` — Session query service with DTO whitelist
- Routes: `GET /api/dev/v1/sessions`, `GET /api/dev/v1/sessions/{sessionId}`
- Frontend API client, session store, updated sidebar
- 92 backend tests, 43 new frontend tests

### Dependencies

- Phase 0C-02

### Modification Scope

| File | Action |
|------|--------|
| `hermes_cli/dev_web_session_service.py` | **New** — Session query service, DTO transformers, validation |
| `hermes_cli/dev_web_api.py` | **Modify** — Add session routes, update status |
| `hermes_cli/dev_web_schemas.py` | **Modify** — Add session Pydantic models |
| `hermes_cli/dev_web_errors.py` | **Modify** — Add SESSION_NOT_FOUND, SESSION_STORE_UNAVAILABLE codes |
| `apps/hermes-dev-webui/src/api/client.ts` | **New** — Unified fetch client |
| `apps/hermes-dev-webui/src/api/sessions.ts` | **New** — Session API functions |
| `apps/hermes-dev-webui/src/types/api/session.ts` | **New** — TypeScript types |
| `apps/hermes-dev-webui/src/stores/session.ts` | **New** — Pinia session store |
| `apps/hermes-dev-webui/src/components/layout/SessionSidebar.vue` | **Modify** — Uses store |
| `apps/hermes-dev-webui/src/components/layout/AppLayout.vue` | **Modify** — Uses store |
| `apps/hermes-dev-webui/src/components/layout/ChatWorkspaceShell.vue` | **Modify** — Session detail/placeholder |
| `tests/test_dev_web_sessions.py` | **New** — 92 session API tests |

### Acceptance Criteria

- ✅ Session sidebar shows real sessions from development instance
- ✅ Clicking a session shows session detail
- ✅ Search/filter works
- ✅ All sensitive fields absent from API responses
- ✅ SessionDB opened in read_only mode, database hash unchanged after requests
- ✅ All 192 backend tests pass (100 existing + 92 new)
- ✅ All 172 frontend tests pass (129 existing + 43 new)
- ✅ Production Gateway PID 1717 unaffected

### Goal

Wire the session list and session detail endpoints to real SessionDB read-only queries.

### Input

- Phase 0C-02 skeleton (running)
- SessionDB audit results from Phase 0C-01

### Output

- `hermes_cli/dev_web_services/session_query_service.py` — Session query logic
- `hermes_cli/dev_web_services/session_dto.py` — Session DTO transformer
- Routes: `GET /api/dev/v1/sessions`, `GET /api/dev/v1/sessions/{id}`
- Updated frontend API client for sessions
- Updated SessionSidebar to use real data

### Dependencies

- Phase 0C-02

### Modification Scope

| File | Action |
|------|--------|
| `hermes_cli/dev_web_services/session_query_service.py` | **New** |
| `hermes_cli/dev_web_services/session_dto.py` | **New** |
| `hermes_cli/dev_web_api.py` | **Modify** — Add session routes |
| `apps/hermes-dev-webui/src/api/sessions.ts` | **New** — API client |
| `apps/hermes-dev-webui/src/types/api/session.ts` | **New** — TypeScript types |
| `apps/hermes-dev-webui/src/stores/sessionStore.ts` | **New** — Pinia store |
| `apps/hermes-dev-webui/src/components/sidebar/SessionList.vue` | **Modify** — Real data |
| `tests/test_dev_web_api_sessions.py` | **New** |

### Test Requirements

- Session list returns real sessions from dev state.db
- Pagination works correctly (offset, limit, total, hasMore)
- Sensitive fields (system_prompt, model_config, billing_*) are absent from response
- Session not found returns 404 with correct error code
- SessionDB opened in read_only mode
- Timestamps are ISO 8601 UTC format
- archived field is boolean (not 0/1)

### Acceptance Criteria

- Session sidebar shows real sessions from development instance
- Clicking a session shows session detail
- Search/filter works
- All sensitive fields absent from API responses
- All tests pass

### Risks

- **Medium:** dev state.db may be empty — need graceful empty state handling

### Not Included

- Message display within sessions (Phase 0C-04)
- Session creation or mutation

---

## Phase 0C-04: Session Messages Read-Only Display

### Goal

Wire the messages endpoint to real SessionDB and display messages in the chat area.

### Input

- Phase 0C-03 (session list working)
- Message schema audit from Phase 0C-01

### Output

- Message DTO transformer
- Route: `GET /api/dev/v1/sessions/{id}/messages`
- Message rendering components (text, tool calls, tool results)
- Pagination for messages (anchor-based scrolling)

### Dependencies

- Phase 0C-03

### Modification Scope

| File | Action |
|------|--------|
| `hermes_cli/dev_web_services/session_query_service.py` | **Modify** — Add message queries |
| `hermes_cli/dev_web_services/message_dto.py` | **New** — Message DTO |
| `hermes_cli/dev_web_api.py` | **Modify** — Add message route |
| `apps/hermes-dev-webui/src/components/chat/` | **New/Modify** — Message components |
| `apps/hermes-dev-webui/src/api/messages.ts` | **New** |
| `apps/hermes-dev-webui/src/types/api/message.ts` | **New** |
| `tests/test_dev_web_api_messages.py` | **New** |

### Test Requirements

- Messages returned in correct order (ASC by id)
- Message content decoded correctly (plain text, multimodal)
- Tool calls parsed and structured
- Tool call arguments truncated at 200 chars
- Pagination works with before/after anchors
- Sensitive columns (reasoning, codex_*) absent
- Empty session returns empty items array
- Deleted messages excluded by default

### Acceptance Criteria

- Chat area displays real messages from selected session
- Different message types rendered appropriately (user, assistant, tool)
- Tool calls shown as collapsible cards
- Pagination/scrolling works for long sessions
- All tests pass

### Risks

- **Medium:** Message content may contain HTML or sensitive data — need sanitization
- **Low:** Very long sessions may cause performance issues — mitigated by pagination

### Not Included

- Message sending
- Streaming (SSE)
- Real-time updates

---

## Phase 0C-05: Memory / Context / Agent Panel Integration

### Goal

Wire the memory, context preview, and agent status endpoints to real backend services.

### Input

- Phase 0C-04 (messages working)
- Memory/Context/Agent audit from Phase 0C-01

### Output

- Memory query service and DTO
- Context preview service and DTO
- Agent status service and DTO
- Routes: Memory, Context Preview, Agent Status
- Updated frontend panels (Memory, Context, Agent tabs)

### Dependencies

- Phase 0C-04

### Modification Scope

| File | Action |
|------|--------|
| `hermes_cli/dev_web_services/memory_query_service.py` | **New** |
| `hermes_cli/dev_web_services/memory_dto.py` | **New** |
| `hermes_cli/dev_web_services/context_preview_service.py` | **New** |
| `hermes_cli/dev_web_services/agent_status_service.py` | **New** |
| `hermes_cli/dev_web_api.py` | **Modify** — Add all new routes |
| `apps/hermes-dev-webui/src/api/` | **New** — API clients |
| `apps/hermes-dev-webui/src/types/api/` | **New** — TypeScript types |
| `apps/hermes-dev-webui/src/stores/` | **New** — Pinia stores |
| `apps/hermes-dev-webui/src/components/workspace/` | **Modify** — Real data |
| `tests/test_dev_web_api_memory.py` | **New** |
| `tests/test_dev_web_api_context.py` | **New** |
| `tests/test_dev_web_api_agent.py` | **New** |

### Test Requirements

**Memory:**
- Categories returned with correct fields
- Memory items filtered by category
- Memory detail includes record text (truncated)
- Storage paths (file URIs) absent from responses
- Archived items excluded by default

**Context Preview:**
- POST request accepted
- Returns matched categories with scores
- Returns loaded memories with scores and previews
- No file modification during preview (verify with file timestamps)
- No LLM call (mock config without API key)
- Query too long returns 400

**Agent Status:**
- Model name and provider returned (sanitized)
- api_key absent from response
- base_url absent from response
- Memory flags correct

### Acceptance Criteria

- Memory panel shows real categories and items from dev instance
- Context preview returns relevant memories for a test query
- Agent panel shows current model configuration
- All tests pass

### Risks

- **Low:** Memory system may not be initialized — graceful empty state
- **Low:** Config parsing may fail — catch and return partial status

### Not Included

- Memory writing
- Review approve/reject
- Context persistence

---

## Phase 0C-06: Quality, Testing, and Freeze

### Goal

Comprehensive testing, error handling polish, visual regression across all five themes, and Phase 0C freeze.

### Input

- All Phase 0C-02 through 0C-05 deliverables

### Output

- Complete test suite
- Error handling audit
- Visual regression verification
- Updated documentation
- Phase 0C frozen baseline

### Dependencies

- Phase 0C-05

### Modification Scope

| Area | Action |
|------|--------|
| Test suite | Expand to full coverage |
| Error handling | Audit and fix edge cases |
| Themes | Verify all five themes with real data |
| Documentation | Update with final state |
| OpenAPI | Validate and finalize |

### Test Requirements

**Comprehensive backend tests:**
- All endpoints return correct status codes
- DTO whitelist enforcement (no sensitive fields leak)
- Environment isolation (reject wrong HERMES_HOME)
- CORS (reject non-allowed origins)
- Error format consistency
- Request ID generation and propagation
- Timestamp format validation
- Pagination edge cases (offset beyond total, limit=0, limit=101)
- Empty data handling (empty sessions, empty messages, empty memory)
- Concurrent request handling

**Frontend tests:**
- API client error handling
- Store state management
- Component rendering with real data shapes
- All five themes render correctly with real data

**Integration tests:**
- End-to-end: start API, request data, verify response
- Session list → session detail → messages flow
- Memory categories → items → detail flow
- Context preview query flow

### Acceptance Criteria

- `vue-tsc --noEmit` passes
- `eslint` passes
- `vitest run` passes
- `vite build` succeeds
- `ruff check .` passes
- All five themes verified visually with real data
- No sensitive data in any API response
- All documentation updated and accurate
- Git history clean

### Risks

- **Medium:** Visual regression across five themes with real data may reveal layout issues
- **Low:** Performance with large session datasets

### Not Included

- SSE/streaming
- Message sending
- Production deployment
- Public access

---

## Summary Timeline

| Phase | Goal | Estimated Effort | Dependencies |
|-------|------|-----------------|-------------|
| 0C-01 | Audit & API Contract | ✅ Complete | None |
| 0C-02 | API Server Skeleton | Medium | 0C-01 |
| 0C-03 | Session List Integration | Medium | 0C-02 |
| 0C-04 | Session Messages Display | Medium-High | 0C-03 |
| 0C-05 | Memory/Context/Agent Panels | High | 0C-04 |
| 0C-06 | Quality & Freeze | Medium | 0C-05 |
