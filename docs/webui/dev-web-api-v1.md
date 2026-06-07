# Dev WebUI API Contract v1

**Version:** 1.0.0-draft
**Date:** 2026-06-07
**Status:** Proposed (Phase 0C-01)
**Base URL:** `http://127.0.0.1:5181/api/dev/v1`
**Transport:** HTTP/1.1 over localhost only

---

## 1. Overview

A read-only REST API that provides the Hermes Dev WebUI with session, memory, context preview, and agent status data from the development Hermes instance.

### 1.1 Design Principles

- **Read-only.** No data mutation through any endpoint.
- **Local-only.** Binds to `127.0.0.1` exclusively.
- **Dev-only.** Rejects non-development HERMES_HOME at startup.
- **DTO-enforced.** All responses pass through a whitelist DTO transformer.
- **No LLM.** No model API calls for any endpoint.
- **No side effects.** Every request leaves zero persistent state changes.

### 1.2 Content-Type

- Request: `application/json` (for POST body)
- Response: `application/json; charset=utf-8`

### 1.3 CORS

- **Allowed Origins:** `http://127.0.0.1:5180`
- **Allowed Methods:** `GET`, `POST`, `OPTIONS`
- **Allowed Headers:** `Content-Type`, `X-Request-ID`
- **Credentials:** `false`
- **Max Age:** `86400`

Wildcard `*` is prohibited. `http://localhost:*` is prohibited.

### 1.4 Request ID

Every response includes a `requestId` field:

- If `X-Request-ID` header is present in request, use it (max 64 chars, truncated if longer).
- Otherwise, generate a random 16-char hex string.
- Returned in response body and as `X-Request-ID` response header.

### 1.5 Timestamp Format

All timestamps use **ISO 8601 UTC** format: `2026-06-07T10:30:00Z`

Source timestamps from SessionDB are Unix floats (REAL), converted at the DTO layer.

### 1.6 ID Types

| Entity | ID Type | Example |
|--------|---------|---------|
| Session | `string` (TEXT) | `"2024-01-15T10-30-00-abc123"` |
| Message | `integer` (AUTOINCREMENT) | `42` |
| Memory Item | `string` (MEM-{CAT}-{NUM}) | `"MEM-HERMES-002"` |
| Category | `string` (name) | `"hermes"` |
| Review Item | `string` (MR-...) | `"MR-20260607T103000-abcd1234"` |

### 1.7 Null Handling

- Empty lists return `[]`, not `null`.
- Nullable fields are explicitly marked in schemas.
- Missing optional fields are omitted from responses (not set to `null`).

---

## 2. Response Format

### 2.1 Success Response

```json
{
  "data": { ... },
  "meta": {
    "requestId": "a1b2c3d4e5f6a7b8",
    "timestamp": "2026-06-07T10:30:00Z"
  }
}
```

For list endpoints, `data` contains `items` and `page`:

```json
{
  "data": {
    "items": [ ... ],
    "page": {
      "nextCursor": "...",
      "hasMore": true,
      "total": 150,
      "limit": 30
    }
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

### 2.2 Error Response

```json
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "Session was not found.",
    "details": null
  },
  "meta": {
    "requestId": "a1b2c3d4e5f6a7b8",
    "timestamp": "2026-06-07T10:30:00Z"
  }
}
```

**`details`** is nullable. When present, it contains a plain string with additional context, never a traceback, path, or secret.

---

## 3. Error Codes

### 3.1 HTTP Status Codes

| Status | Meaning |
|--------|---------|
| `200` | Success |
| `400` | Bad request (invalid parameter) |
| `404` | Resource not found |
| `422` | Unprocessable entity (valid params but semantically invalid combination) |
| `429` | Rate limited (if implemented for context preview) |
| `500` | Internal server error |
| `503` | Service unavailable (backend store unreachable) |

### 3.2 Business Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `INVALID_LIMIT` | 400 | `limit` out of allowed range |
| `INVALID_CURSOR` | 400 | Cursor format invalid or expired |
| `INVALID_PARAMETER` | 400 | General parameter validation failure |
| `QUERY_TOO_LONG` | 400 | Search query exceeds max length (500 chars) |
| `SESSION_NOT_FOUND` | 404 | Session ID does not exist |
| `MEMORY_NOT_FOUND` | 404 | Memory item ID does not exist |
| `CATEGORY_NOT_FOUND` | 404 | Category key does not exist |
| `REVIEW_NOT_FOUND` | 404 | Review item ID does not exist |
| `PREVIEW_VALIDATION_FAILED` | 422 | Context preview request semantically invalid |
| `RATE_LIMITED` | 429 | Too many requests |
| `SESSION_STORE_UNAVAILABLE` | 503 | Cannot open state.db |
| `MEMORY_STORE_UNAVAILABLE` | 503 | Cannot read memory files |
| `AGENT_STATUS_UNAVAILABLE` | 503 | Cannot read agent config |
| `CONTEXT_UNAVAILABLE` | 503 | Context loader failed |
| `UNSAFE_ENVIRONMENT` | 500 | Dev environment isolation check failed |
| `INTERNAL_ERROR` | 500 | Unhandled exception |

---

## 4. Pagination

### 4.1 Strategy: Offset-based pagination

**Rationale:** `SessionDB.list_sessions_rich()` natively uses `limit` + `offset`. Cursor-based pagination would require an additional abstraction layer over the existing offset-based storage, with no performance benefit for a local-only dev tool with modest data volumes.

### 4.2 Parameters

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `limit` | integer | 30 (sessions), 50 (messages) | 100 | Items per page |
| `offset` | integer | 0 | None | Number of items to skip |

### 4.3 Response

```json
{
  "page": {
    "offset": 30,
    "limit": 30,
    "total": 150,
    "hasMore": true
  }
}
```

### 4.4 Sorting

| Endpoint | Default Sort | Direction | Stable |
|----------|-------------|-----------|--------|
| Session list | `last_active` | DESC | Yes (by started_at as tiebreaker) |
| Messages | `id` (AUTOINCREMENT) | ASC | Yes (true insertion order) |
| Memory items | `updated_at` | DESC | Yes |

---

## 5. Endpoints

### 5.1 System Status

```
GET /api/dev/v1/status
```

**Purpose:** Health check and environment verification.

**Parameters:** None.

**Response:**

```json
{
  "data": {
    "environment": "development",
    "apiVersion": "v1",
    "status": "ok",
    "isolation": {
      "passed": true,
      "usesDevelopmentHome": true,
      "productionHomeUntouched": true,
      "bindHost": "127.0.0.1"
    },
    "services": {
      "sessions": {
        "available": true,
        "readOnly": true
      },
      "memory": {
        "available": true,
        "readOnly": true
      },
      "agent": {
        "available": true,
        "readOnly": true
      },
      "gateway": {
        "status": "stopped"
      }
    }
  },
  "meta": {
    "requestId": "...",
    "timestamp": "2026-06-07T10:30:00Z"
  }
}
```

**Gateway status source:** Read from dev gateway state file (`gateway-dev-state.json`). Does not connect to gateway process.

---

### 5.2 Session List

```
GET /api/dev/v1/sessions
```

**Purpose:** List sessions with pagination.

**Parameters:**

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `limit` | integer | 30 | No | Items per page (1–100) |
| `offset` | integer | 0 | No | Offset for pagination |
| `query` | string | — | No | FTS5 search in message content |
| `source` | string | — | No | Filter by source (e.g., "cli", "wechat") |
| `order` | string | "recent" | No | "recent" (last_active DESC) or "created" (started_at DESC) |
| `archived` | string | "exclude" | No | "exclude", "include", or "only" |

**Response:**

```json
{
  "data": {
    "items": [
      {
        "id": "2024-01-15T10-30-00-abc123",
        "title": "Hermes 记忆系统讨论",
        "source": "cli",
        "model": "gpt-4o",
        "messageCount": 12,
        "toolCallCount": 3,
        "archived": false,
        "startedAt": "2024-01-15T10:30:00Z",
        "endedAt": null,
        "lastActiveAt": "2024-01-15T11:45:00Z",
        "preview": "讨论 Hermes 的记忆系统架构和实现方案..."
      }
    ],
    "page": {
      "offset": 0,
      "limit": 30,
      "total": 150,
      "hasMore": true
    }
  },
  "meta": { "requestId": "...", "timestamp": "..." }
}
```

**Field mapping from SessionDB:**

| DTO field | Source column | Transform |
|-----------|--------------|-----------|
| `id` | `sessions.id` | As-is |
| `title` | `sessions.title` | As-is; `null` → omit |
| `source` | `sessions.source` | As-is |
| `model` | `sessions.model` | As-is |
| `messageCount` | `sessions.message_count` | As-is |
| `toolCallCount` | `sessions.tool_call_count` | As-is |
| `archived` | `sessions.archived` | 0/1 → boolean |
| `startedAt` | `sessions.started_at` | Unix float → ISO 8601 UTC |
| `endedAt` | `sessions.ended_at` | Unix float → ISO 8601 UTC; `null` → omit |
| `lastActiveAt` | Computed (max messages.timestamp) | Unix float → ISO 8601 UTC |
| `preview` | Computed (first user message, 60 chars) | As-is |

**Excluded columns:** system_prompt, model_config, user_id, cwd, billing_*, cost_*, handoff_*, rewind_count, parent_session_id, reasoning_tokens, cache_*, api_call_count

---

### 5.3 Session Detail

```
GET /api/dev/v1/sessions/{sessionId}
```

**Purpose:** Get detailed information about a single session.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sessionId` | path | Yes | Session ID |

**Response:**

```json
{
  "data": {
    "id": "2024-01-15T10-30-00-abc123",
    "title": "Hermes 记忆系统讨论",
    "source": "cli",
    "model": "gpt-4o",
    "messageCount": 12,
    "toolCallCount": 3,
    "inputTokens": 5000,
    "outputTokens": 3000,
    "archived": false,
    "startedAt": "2024-01-15T10:30:00Z",
    "endedAt": null,
    "lastActiveAt": "2024-01-15T11:45:00Z",
    "endReason": null
  },
  "meta": { "requestId": "...", "timestamp": "..." }
}
```

**Error codes:** `SESSION_NOT_FOUND`

---

### 5.4 Session Messages

```
GET /api/dev/v1/sessions/{sessionId}/messages
```

**Purpose:** Get messages for a session with pagination.

**Parameters:**

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `sessionId` | path | — | Yes | Session ID |
| `limit` | integer | 50 | No | Messages per page (1–100) |
| `offset` | integer | 0 | No | Offset for pagination |
| `before` | integer | — | No | Message ID anchor — return messages before this ID |
| `after` | integer | — | No | Message ID anchor — return messages after this ID |

**Anchor-based pagination:** When `before` or `after` is provided, uses `get_messages_around()` for efficient windowed access. The `offset` parameter is ignored when anchors are used.

**Response:**

```json
{
  "data": {
    "items": [
      {
        "id": 1,
        "role": "user",
        "content": {
          "type": "text",
          "text": "Hello Hermes"
        },
        "timestamp": "2024-01-15T10:30:00Z",
        "tokenCount": null
      },
      {
        "id": 2,
        "role": "assistant",
        "content": {
          "type": "text",
          "text": "Hello! How can I help you?"
        },
        "timestamp": "2024-01-15T10:30:05Z",
        "tokenCount": 15,
        "finishReason": "stop"
      },
      {
        "id": 3,
        "role": "assistant",
        "content": {
          "type": "text",
          "text": "Let me search for that."
        },
        "timestamp": "2024-01-15T10:30:10Z",
        "tokenCount": null,
        "toolCalls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "search_files",
              "arguments": "{\"pattern\": \"memory\"}"
            }
          }
        ]
      },
      {
        "id": 4,
        "role": "tool",
        "content": {
          "type": "text",
          "text": "Found 5 files matching 'memory'"
        },
        "timestamp": "2024-01-15T10:30:12Z",
        "toolCallId": "call_abc123",
        "toolName": "search_files"
      }
    ],
    "page": {
      "offset": 0,
      "limit": 50,
      "total": 12,
      "hasMore": false,
      "messagesBefore": 0,
      "messagesAfter": 8
    }
  },
  "meta": { "requestId": "...", "timestamp": "..." }
}
```

**Message content format (discriminated union):**

| Content type | Condition | Shape |
|-------------|-----------|-------|
| `text` | Default | `{ "type": "text", "text": "..." }` |
| `structured` | Multimodal (images, etc.) | `{ "type": "structured", "parts": [...] }` |
| `tool_calls` | Assistant with tool calls | Included in assistant message as `toolCalls` array |
| `empty` | No content (null/empty) | `{ "type": "empty" }` |

**Excluded columns:** reasoning, reasoning_content, reasoning_details, codex_reasoning_items, codex_message_items, platform_message_id, observed, active

**Tool call argument sanitization:** Arguments that may contain sensitive data (file contents, API responses) are truncated to 200 chars in the DTO.

**Error codes:** `SESSION_NOT_FOUND`, `SESSION_STORE_UNAVAILABLE`

---

### 5.5 Memory Status

```
GET /api/dev/v1/memory/status
```

**Purpose:** Memory system availability and summary.

**Parameters:** None.

**Response:**

```json
{
  "data": {
    "enabled": true,
    "categories": {
      "total": 6,
      "active": 5,
      "archived": 1
    },
    "memories": {
      "total": 12,
      "active": 10,
      "archived": 2
    },
    "capabilities": {
      "contextLoader": true,
      "reviewQueue": true
    },
    "exposedCapabilities": {
      "read": true,
      "write": false,
      "review": false,
      "approve": false,
      "reject": false
    }
  },
  "meta": { "requestId": "...", "timestamp": "..." }
}
```

---

### 5.6 Memory Categories

```
GET /api/dev/v1/memory/categories
```

**Parameters:**

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `includeArchived` | boolean | false | No | Include archived categories |

**Response:**

```json
{
  "data": {
    "items": [
      {
        "key": "hermes",
        "scope": "project",
        "priority": "P0",
        "status": "active",
        "keywords": ["hermes", "agent", "development"],
        "description": "Hermes 项目状态和开发笔记",
        "memoryCount": 3
      }
    ]
  },
  "meta": { "requestId": "...", "timestamp": "..." }
}
```

**Field mapping from RootCategory:**

| DTO field | Source | Transform |
|-----------|--------|-----------|
| `key` | `RootCategory.name` | As-is |
| `scope` | `fields["scope"]` | As-is |
| `priority` | `fields["priority"]` | As-is |
| `status` | `fields["status"]` | As-is |
| `keywords` | `fields["keywords"]` | Comma-separated → string array |
| `description` | `fields["description"]` | As-is |
| `memoryCount` | Count from `parse_index()` | Integer |

**Excluded:** `index` (file URI), `storage` paths

---

### 5.7 Memory Items

```
GET /api/dev/v1/memory/items
```

**Parameters:**

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `category` | string | — | No | Filter by category |
| `includeArchived` | boolean | false | No | Include archived items |
| `limit` | integer | 30 | No | Items per page (1–100) |
| `offset` | integer | 0 | No | Offset |

**Response:**

```json
{
  "data": {
    "items": [
      {
        "id": "MEM-HERMES-002",
        "title": "Hermes Memory System Architecture",
        "category": "hermes",
        "summary": "Hierarchical memory system with categories, indexes, and records...",
        "tags": ["memory", "architecture"],
        "importance": "P1",
        "ttl": "permanent",
        "status": "active",
        "updatedAt": "2026-06-01"
      }
    ],
    "page": {
      "offset": 0,
      "limit": 30,
      "total": 12,
      "hasMore": false
    }
  },
  "meta": { "requestId": "...", "timestamp": "..." }
}
```

**Excluded:** `storage` (file path URI), full record text (use detail endpoint)

---

### 5.8 Memory Item Detail

```
GET /api/dev/v1/memory/items/{memoryId}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `memoryId` | path | Yes | Memory item ID (e.g., "MEM-HERMES-002") |

**Response:**

```json
{
  "data": {
    "id": "MEM-HERMES-002",
    "title": "Hermes Memory System Architecture",
    "category": "hermes",
    "summary": "Hierarchical memory system with categories...",
    "tags": ["memory", "architecture"],
    "importance": "P1",
    "ttl": "permanent",
    "status": "active",
    "type": "project_status",
    "createdAt": "2026-05-15",
    "updatedAt": "2026-06-01",
    "record": "Full record text content up to maxRecordChars..."
  },
  "meta": { "requestId": "...", "timestamp": "..." }
}
```

**`record` field:** Full record text, truncated to `maxRecordChars` (default 3000). Includes `truncated: true` flag if truncated.

**Error codes:** `MEMORY_NOT_FOUND`

---

### 5.9 Context Preview

```
POST /api/dev/v1/context/preview
```

**Purpose:** Preview what runtime memory context would be loaded for a given query, without calling any LLM.

**Safety guarantees:**
- No LLM call
- No persistence
- No session write
- No memory write
- No review queue trigger
- No file modification of any kind

**Request body:**

```json
{
  "query": "Hermes 记忆系统现在做到哪了",
  "options": {
    "maxCategories": 3,
    "maxMemories": 5,
    "maxRecordChars": 2000,
    "includeArchived": false
  }
}
```

| Field | Type | Default | Max | Required | Description |
|-------|------|---------|-----|----------|-------------|
| `query` | string | — | 500 chars | Yes | The user message to preview context for |
| `options.maxCategories` | integer | 3 | 10 | No | Max categories to load |
| `options.maxMemories` | integer | 5 | 20 | No | Max memories per category |
| `options.maxRecordChars` | integer | 2000 | 5000 | No | Max chars per record in preview |
| `options.includeArchived` | boolean | false | — | No | Include archived memories |

**Response:**

```json
{
  "data": {
    "query": "Hermes 记忆系统现在做到哪了",
    "matchedCategories": [
      {
        "key": "hermes",
        "score": 3,
        "scope": "project"
      }
    ],
    "memories": [
      {
        "id": "MEM-HERMES-002",
        "category": "hermes",
        "title": "Hermes Memory System Architecture",
        "summary": "Hierarchical memory system with categories...",
        "score": 5,
        "truncated": false,
        "recordPreview": "First 200 chars of record text..."
      }
    ],
    "skipped": [
      "MEM-USER-001(status=archived)"
    ],
    "limits": {
      "maxCategories": 3,
      "maxMemories": 5,
      "maxRecordChars": 2000
    },
    "sideEffects": false
  },
  "meta": { "requestId": "...", "timestamp": "..." }
}
```

**Error codes:** `QUERY_TOO_LONG`, `PREVIEW_VALIDATION_FAILED`, `CONTEXT_UNAVAILABLE`

---

### 5.10 Agent Status

```
GET /api/dev/v1/agent/status
```

**Purpose:** Agent configuration and runtime status (static, read from config).

**Parameters:** None.

**Response:**

```json
{
  "data": {
    "available": true,
    "model": {
      "provider": "openai",
      "name": "gpt-4o",
      "configured": true
    },
    "memory": {
      "enabled": true,
      "contextLoaderEnabled": true
    },
    "execution": {
      "readOnly": true,
      "messageSendEnabled": false,
      "toolExecutionEnabled": false,
      "streamingEnabled": false
    }
  },
  "meta": { "requestId": "...", "timestamp": "..." }
}
```

**Field sources:**

| DTO field | Source |
|-----------|--------|
| `model.provider` | `config.yaml` → model config (sanitized) |
| `model.name` | `config.yaml` → model field |
| `model.configured` | Whether model and provider are set |
| `memory.enabled` | `config.yaml` → memory.enabled |
| `memory.contextLoaderEnabled` | `config.yaml` → memory.context_loader.enabled |

**Excluded:** api_key, base_url, billing_*, system_prompt, full config object

---

### 5.11 Files Status

```
GET /api/dev/v1/files/status
```

**Purpose:** Indicate whether file browsing is available (always false in Phase 0C).

**Response:**

```json
{
  "data": {
    "available": false,
    "reason": "File browsing is not available in Phase 0C"
  },
  "meta": { "requestId": "...", "timestamp": "..." }
}
```

---

## 6. Endpoints Summary Table

| Method | Path | Purpose | Side Effects | Status |
|--------|------|---------|-------------|--------|
| GET | `/api/dev/v1/status` | System health & isolation check | None | Phase 0C-02 |
| GET | `/api/dev/v1/sessions` | Session list with pagination | None | Phase 0C-03 |
| GET | `/api/dev/v1/sessions/{id}` | Session detail | None | Phase 0C-03 |
| GET | `/api/dev/v1/sessions/{id}/messages` | Session messages with pagination | None | Phase 0C-04 |
| POST | `/api/dev/v1/context/preview` | Memory context preview | None (guaranteed) | Phase 0C-05 |
| GET | `/api/dev/v1/memory/status` | Memory system status | None | Phase 0C-05 |
| GET | `/api/dev/v1/memory/categories` | Memory categories list | None | Phase 0C-05 |
| GET | `/api/dev/v1/memory/items` | Memory items list | None | Phase 0C-05 |
| GET | `/api/dev/v1/memory/items/{id}` | Memory item detail | None | Phase 0C-05 |
| GET | `/api/dev/v1/agent/status` | Agent configuration status | None | Phase 0C-05 |
| GET | `/api/dev/v1/files/status` | Files availability (always false) | None | Phase 0C-02 |

---

## 7. Non-Goals

This API explicitly does NOT provide:

- Message sending or conversation initiation
- Session creation, deletion, renaming, or archiving
- Memory writing, updating, or archiving
- Review queue access (data source audited but not exposed in Phase 0C)
- Tool execution
- LLM streaming (SSE)
- File browsing or upload
- Gateway start, stop, or restart
- Configuration modification
- Environment variable modification
- WebSocket connections
- Authentication or authorization (localhost-only)
- Real-time updates or push notifications

---

## 8. Compatibility Strategy

- API version is embedded in URL prefix (`/api/dev/v1/`).
- Breaking changes require a new version prefix (`v2`).
- Additive changes (new fields, new endpoints) are backwards-compatible within a version.
- Deprecated fields are marked in documentation but not removed within a version.
- `UNKNOWN` fallback: Enum fields that encounter unrecognized values return `"UNKNOWN"` instead of causing errors.
