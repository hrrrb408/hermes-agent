# Phase 0C: Data Flow Design

**Date:** 2026-06-07
**Status:** Proposed
**Depends on:** Phase 0C-01 Audit Report

---

## 1. Overview

This document defines all data flows between the Dev WebUI frontend, the Dev API server, and the Hermes backend services. Every flow is read-only and local-only.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser (http://127.0.0.1:5180)              │
│                     Vue 3 Dev WebUI Frontend                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP GET / POST (read-only)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                Dev API Server (http://127.0.0.1:5181)           │
│                  FastAPI, /api/dev/v1/*                         │
│                                                                 │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ Session     │ │ Memory       │ │ Context      │            │
│  │ Query Svc   │ │ Query Svc    │ │ Preview Svc  │            │
│  └──────┬──────┘ └──────┬───────┘ └──────┬───────┘            │
│         │               │                │                      │
│         ▼               ▼                ▼                      │
│  ┌─────────────────────────────────────────────────┐           │
│  │              DTO / Redaction Layer               │           │
│  └─────────────────────────────────────────────────┘           │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Python function calls (in-process)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              Hermes Backend Services (read-only)                 │
│                                                                 │
│  ┌──────────────┐ ┌───────────────┐ ┌────────────────────┐    │
│  │ SessionDB    │ │ memory_router │ │ runtime_memory     │    │
│  │ (read_only)  │ │ (parse/list)  │ │ (context preview)  │    │
│  └──────┬───────┘ └──────┬────────┘ └──────┬─────────────┘    │
│         │                │                  │                    │
│         ▼                ▼                  ▼                    │
│  ┌──────────────┐ ┌───────────────┐ ┌────────────────────┐    │
│  │ state.db     │ │ MEMORY.md +   │ │ (delegates to      │    │
│  │ (SQLite RO)  │ │ memory/ files │ │  memory_router)    │    │
│  └──────────────┘ └───────────────┘ └────────────────────┘    │
│                                                                 │
│  HERMES_HOME = /Users/huangruibang/Code/hermes-home-dev        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Session List Data Flow

```
WebUI SessionSidebar
  │
  │ GET /api/dev/v1/sessions?limit=30&cursor=...
  │
  ▼
Dev API: routes/sessions.py
  │
  │ session_query_service.list_sessions(limit, cursor, query, ...)
  │
  ▼
SessionQueryService
  │
  │ SessionDB(db_path=dev_state_db, read_only=True)
  │ db.list_sessions_rich(limit=N, offset=M, ...)
  │
  ▼
SessionDB.list_sessions_rich()
  │
  │ SELECT ... FROM sessions ...
  │ Returns List[Dict] with raw columns
  │
  ▼
SessionDTOTransformer.to_session_list_item()
  │
  │ Whitelist: id, title, source, started_at, ended_at,
  │            message_count, preview, last_active, archived
  │ Strip: system_prompt, model_config, billing_*, cwd, user_id
  │
  ▼
JSON Response → WebUI
```

**Trust boundary:** DTO transformation is the trust boundary. Raw DB objects never cross it.

---

## 3. Session Messages Data Flow

```
WebUI ChatArea
  │
  │ GET /api/dev/v1/sessions/{id}/messages?cursor=...&limit=50
  │
  ▼
Dev API: routes/sessions.py
  │
  │ session_query_service.get_messages(session_id, cursor, limit)
  │
  ▼
SessionQueryService
  │
  │ db.get_messages_around(session_id, around_message_id, window)
  │ OR db.get_messages(session_id)
  │
  ▼
SessionDB.get_messages() / get_messages_around()
  │
  │ SELECT * FROM messages WHERE session_id = ? ORDER BY id
  │ Decodes content (JSON prefix handling)
  │ Parses tool_calls JSON
  │
  ▼
MessageDTOTransformer.to_message_item()
  │
  │ Whitelist: id, role, content, tool_call_id, tool_calls,
  │            tool_name, timestamp, finish_reason
  │ Strip: reasoning, reasoning_content, codex_* fields
  │ Sanitize: tool_calls params that may contain secrets
  │
  ▼
JSON Response → WebUI
```

---

## 4. Memory Data Flow

```
WebUI MemoryPanel
  │
  │ GET /api/dev/v1/memory/categories
  │ GET /api/dev/v1/memory/items?category=hermes
  │ GET /api/dev/v1/memory/items/{id}
  │
  ▼
Dev API: routes/memory.py
  │
  │ memory_query_service.*
  │
  ▼
MemoryQueryService
  │
  │ memory_router.parse_root(home=dev_home)
  │ memory_router.active_root_categories(home=dev_home)
  │ memory_router.parse_index(category, home=dev_home)
  │ memory_router.list_items(home=dev_home)
  │ memory_router.find_item_location(memory_id, home=dev_home)
  │
  ▼
memory_router (read-only functions only)
  │
  │ Reads MEMORY.md, indexes/*.md, records/**/*.md
  │ Returns RootCategory, MemoryItem dataclass objects
  │
  ▼
MemoryDTOTransformer
  │
  │ CategoryDTO: name, scope, priority, status, keywords,
  │              description, memory_count
  │ MemoryItemDTO: memory_id, title, category, summary, tags,
  │                importance, ttl, status, updated_at
  │ Strip: storage (file path URI)
  │
  ▼
JSON Response → WebUI
```

---

## 5. Context Preview Data Flow

```
WebUI ContextPanel
  │
  │ POST /api/dev/v1/context/preview
  │ Body: { "query": "...", "options": { ... } }
  │
  ▼
Dev API: routes/context.py
  │
  │ context_preview_service.preview(query, options)
  │
  ▼
ContextPreviewService
  │
  │ runtime_memory.load_runtime_memory_context(query, config)
  │   └─> memory_router.load_memory_context(query, ...)
  │        └─> Scoring + file reads (NO LLM, NO writes)
  │
  │ Returns RuntimeMemoryContext
  │
  ▼
ContextDTOTransformer
  │
  │ ContextPreviewDTO: query, matched_categories, memories,
  │                    skipped, limits, side_effects=false
  │ Strip: context (full formatted text for LLM injection)
  │ Return: structured summary only, not raw injection text
  │
  ▼
JSON Response → WebUI
```

**Critical safety properties:**
- No LLM call
- No persistence
- No session write
- No memory write
- No review queue trigger
- Full injection text is NOT returned — only structured summary

---

## 6. Agent Status Data Flow

```
WebUI AgentPanel
  │
  │ GET /api/dev/v1/agent/status
  │
  ▼
Dev API: routes/agent.py
  │
  │ agent_status_service.get_status()
  │
  ▼
AgentStatusService
  │
  │ Reads config.yaml (via load_config_readonly())
  │ Extracts: model name, provider, memory flags
  │ Does NOT instantiate AIAgent
  │ Does NOT read credentials
  │
  ▼
AgentDTOTransformer
  │
  │ AgentStatusDTO: available, model.name, model.provider,
  │                 model.configured, memory.enabled,
  │                 memory.contextLoaderEnabled,
  │                 execution.readOnly=true
  │ Strip: api_key, base_url, billing_*, system_prompt
  │
  ▼
JSON Response → WebUI
```

---

## 7. Prohibited Data Flows

The following flows are explicitly **prohibited** in Phase 0C:

```
✕ WebUI → Direct file read from HERMES_HOME
✕ WebUI → Direct SQLite access to state.db
✕ WebUI → Direct call to AIAgent or run_conversation()
✕ WebUI → Direct call to Memory Writer functions
✕ WebUI → Direct call to Review Queue write functions
✕ WebUI → subprocess execution of CLI commands
✕ WebUI → Direct connection to production Gateway (port 9119 or other)
✕ API → LLM API calls
✕ API → Session write operations (create, update, delete, archive)
✕ API → Memory write operations (add, update, archive)
✕ API → Review approve/reject operations
✕ API → Tool execution
✕ API → Message sending
✕ API → File system write operations
✕ API → Environment variable modification
```

---

## 8. Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│ UNTRUSTED ZONE                                                  │
│ Browser / Frontend JavaScript                                   │
│ - Cannot access HERMES_HOME                                     │
│ - Cannot access state.db                                        │
│ - Cannot execute Python                                         │
│ - Only sees JSON responses from API                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP (CORS-restricted to 127.0.0.1:5180)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ SEMI-TRUSTED ZONE                                               │
│ Dev API Server (FastAPI)                                        │
│ - Receives HTTP requests                                        │
│ - Validates parameters                                          │
│ - Calls service functions                                       │
│ - Applies DTO transformations (trust boundary)                  │
│ - Strips sensitive fields                                       │
│ - Returns safe JSON                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ Python function calls (in-process)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ TRUSTED ZONE                                                    │
│ Hermes Backend Services                                         │
│ - SessionDB (read_only=True)                                    │
│ - memory_router (read-only functions)                           │
│ - runtime_memory (context preview only)                         │
│ - Config reader (readonly mode)                                 │
│ - All accesses HERMES_HOME_DEV only                             │
└─────────────────────────────────────────────────────────────────┘
```

**Key principle:** Every response crosses exactly one trust boundary — the DTO layer. Raw internal objects are never serialized to JSON.

---

## 9. Error Propagation

```
Backend Exception
  │
  ▼
Service Layer (catches, converts to domain error)
  │
  ▼
API Route (catches domain error, converts to HTTP error)
  │
  ▼
ErrorDTO (sanitized: code, message, requestId, timestamp)
  │
  ▼
JSON Error Response → WebUI
```

**Error information that is NEVER propagated:**
- Python traceback
- Absolute filesystem paths
- SQL statements
- API keys, tokens, secrets
- Environment variable names or values
- Internal exception types
- Source code references

---

## 10. Development Environment Isolation

```
Production Environment                    Development Environment
─────────────────────                    ──────────────────────
~/.hermes/                               /Users/huangruibang/Code/hermes-home-dev/
├── state.db                             ├── state.db
├── config.yaml                          ├── config.yaml
├── gateway.pid                          ├── gateway-dev.pid
├── gateway_state.json                   ├── gateway-dev-state.json
├── gateway.lock                         ├── gateway.lock
├── memory/                              ├── memory/
├── logs/gateway.log                     ├── logs/gateway-dev.log
└── ...                                  └── ...

Production Gateway (PID 1717)            Dev API Server (PID TBD)
Port: dynamic                            Port: 5181
Process: Running                         Process: On-demand

Production Dashboard                     Dev WebUI Frontend
Port: 9119                               Port: 5180
```

**Isolation guarantees:**
- Dev API only reads from `hermes-home-dev`
- Startup validation rejects wrong HERMES_HOME
- PID files are separate
- Port numbers are separate
- No shared state between production and development
