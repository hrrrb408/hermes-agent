# Phase 0C-04: Session Message Read-only Integration

**Date:** 2026-06-08
**Status:** Completed
**Depends on:** Phase 0C-03 (Session List and Detail Read-only Integration)

---

## Overview

Phase 0C-04 implements the **read-only session messages API** and connects it to the Dev WebUI workspace. Users can now select a session from the sidebar and view its complete message history in the central workspace area.

---

## Scope

### Implemented

- **Backend:** `GET /api/dev/v1/sessions/{sessionId}/messages`
- **Backend:** Message query service with DTO whitelist
- **Backend:** Pagination (offset/limit + before/after anchors)
- **Backend:** Role normalization, content safety, tool call display
- **Backend:** Sensitive field exclusion (reasoning, codex_*, etc.)
- **Backend:** Read-only guarantee (no database writes)
- **Frontend:** Message API client
- **Frontend:** Message TypeScript types
- **Frontend:** Session store message state and actions
- **Frontend:** Workspace message rendering (user, assistant, tool, system, unknown)
- **Frontend:** Loading, empty, error, retry, load-more states
- **Frontend:** Safe text rendering (no v-html, HTML escaped)
- **Tests:** 65 backend tests, 56 frontend tests

### Not Included (Phase 0C-05+)

- Message sending
- SSE / streaming
- WebSocket
- Tool execution
- Memory / Context / Agent panels
- Composer unlock
- Agent runtime integration

---

## Architecture

### Backend

```
FastAPI Route (dev_web_api.py)
    ↓
DevMessageQueryService (dev_web_message_service.py)
    ↓
SessionDB(read_only=True)
    ↓
Message DTO Transformer (_transform_message)
    ↓
Response Schema (dev_web_schemas.py)
```

### Message DTO Whitelist

Only these fields are returned in the API response:

| Field | Type | Source Column |
|-------|------|--------------|
| `id` | integer | `messages.id` |
| `role` | string | `messages.role` (normalized) |
| `content` | object | `messages.content` (decoded, sanitized) |
| `timestamp` | string | `messages.timestamp` (ISO 8601) |
| `tokenCount` | integer? | `messages.token_count` |
| `finishReason` | string? | `messages.finish_reason` |
| `toolCalls` | array? | `messages.tool_calls` (parsed, args truncated) |
| `toolCallId` | string? | `messages.tool_call_id` |
| `toolName` | string? | `messages.tool_name` |

### Excluded Fields (never returned)

- `reasoning`
- `reasoning_content`
- `reasoning_details`
- `codex_reasoning_items`
- `codex_message_items`
- `observed`
- `active`
- `platform_message_id`

### Content Safety

- **Plain text**: Returned as `{"type": "text", "text": "..."}`
- **Empty/None**: Returned as `{"type": "empty"}`
- **Structured (\x00json:)**: Text parts extracted; non-text → `{"type": "unsupported"}`
- **Control characters**: Stripped (except newline, tab, CR)
- **Truncation**: Text > 50,000 chars truncated with `truncated: true`
- **Tool call args**: Truncated at 200 characters

### Role Normalization

```python
SAFE_ROLES = {"user", "assistant", "tool", "system"}
# null → "unknown"
# unrecognized → "unknown"
# case-insensitive matching
```

### Pagination

- Default: `limit=50, offset=0`
- Maximum: `limit=100`
- Order: always `id ASC`
- Anchors: `before` (messages with id < N), `after` (messages with id > N)
- Response includes `messagesBefore` and `messagesAfter` when anchors used

---

## Frontend

### New Files

| File | Purpose |
|------|---------|
| `src/types/api/message.ts` | Message TypeScript types |
| `src/api/messages.ts` | Message API client |
| `src/tests/message-api.spec.ts` | 11 API tests |
| `src/tests/message-store.spec.ts` | 18 store tests |
| `src/tests/message-workspace.spec.ts` | 27 workspace tests |

### Modified Files

| File | Change |
|------|--------|
| `src/stores/session.ts` | Added message state, loadMessages, loadMoreMessages |
| `src/components/layout/ChatWorkspaceShell.vue` | Replaced placeholder with real message rendering |

### Message Rendering Safety

- Vue default text escaping (no `v-html`)
- `white-space: pre-wrap` for multiline preservation
- `overflow-wrap: break-word` for long words
- Tool calls shown as name-only cards (no arguments displayed)
- Unsupported content shown as placeholder text

---

## Runtime Routes

After Phase 0C-04, the Dev Web API has 5 business routes:

```http
GET /api/dev/v1/status
GET /api/dev/v1/files/status
GET /api/dev/v1/sessions
GET /api/dev/v1/sessions/{sessionId}
GET /api/dev/v1/sessions/{sessionId}/messages
```

---

## Test Results

### Backend (270 total)

- `test_dev_web_api.py`: 203 passed
- `test_dev_web_sessions.py`: Updated 3 tests for 5 business routes
- `test_dev_web_messages.py`: 65 new tests

### Frontend (228 total)

- 172 existing tests: all passing
- 56 new message tests: all passing

---

## Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `SESSION_NOT_FOUND` | 404 | Session does not exist |
| `SESSION_STORE_UNAVAILABLE` | 503 | Database unavailable |
| `INVALID_PARAMETER` | 400 | Invalid sessionId or parameter |

---

## Next Steps (Phase 0C-05)

Phase 0C-05 should implement:

- Memory status and category listing
- Context preview panel
- Agent status display
- Workspace panel tabs with real data
