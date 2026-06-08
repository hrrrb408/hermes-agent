# Phase 1A-00: Review Queue Read-Only Panel Scope & Contract Freeze

**Status:** Completed
**Date:** 2026-06-08
**Branch:** dev-huangruibang
**Base commit:** 794a78140 (Phase 1-00: Phase 1 planning scope)
**Depends on:** Phase 1-00 Completed
**Governance scope:** `docs/webui/phase-1-00-planning-and-scope.md`

---

## 1. Background

Phase 1-00 completed the Phase 1 planning and scope freeze. The Phase 1 subphase roadmap is frozen:

```
1A → 1B → 1C (Review Queue track)
1D (Memory Writer track)
1E → 1F → 1G (Agent + Tools track)
```

Phase 1A-00 is a **scope and contract freeze** task for Phase 1A (Review Queue Read-Only Panel). It audits the Review Queue data source, defines the read-only API proposal, freezes DTOs, error models, pagination strategies, and frontend information architecture — without implementing any functionality.

---

## 2. Current Baseline

### 2.1 Repository State

| Item | Value |
|------|-------|
| Branch | `dev-huangruibang` |
| HEAD | `794a78140` |
| origin/dev-huangruibang | `cc64aa690` (Phase 1-00 is local only, expected) |
| Working tree | Clean |

### 2.2 Environment State

| Item | Value |
|------|-------|
| HERMES_HOME | `/Users/huangruibang/Code/hermes-home-dev` |
| Production Gateway PID | 1717 (running, untouched) |
| Dev Gateway | stopped |
| Port 5180 | free |
| Port 5181 | free |
| memory-check | PASS |
| dev-check | PASS |

### 2.3 Current Route Inventory

11 implemented business routes (documented in `docs/webui/openapi/dev-web-api-v1.yaml`):

| Method | Path |
|--------|------|
| GET | `/api/dev/v1/status` |
| GET | `/api/dev/v1/files/status` |
| GET | `/api/dev/v1/sessions` |
| GET | `/api/dev/v1/sessions/{sessionId}` |
| GET | `/api/dev/v1/sessions/{sessionId}/messages` |
| GET | `/api/dev/v1/memory/status` |
| GET | `/api/dev/v1/memory/categories` |
| GET | `/api/dev/v1/memory/items` |
| GET | `/api/dev/v1/memory/items/{memoryId}` |
| POST | `/api/dev/v1/context/preview` |
| GET | `/api/dev/v1/agent/status` |

**OpenAPI paths: 11. All read-only / side-effect-free.**

### 2.4 Current Frontend State

- No Review Queue Panel exists
- Workspace panel has: Files, Memory, Context, Agent tabs
- No review-related API types or stores
- Smoke tests enforce review endpoint absence (`/reviews` is forbidden)

---

## 3. Review Queue Data Source Audit

### 3.1 Source Files

| File | Role |
|------|------|
| `agent/memory_review_queue.py` | Core Review Queue module: storage, validation, CRUD operations |
| `agent/runtime_memory_writer.py` | Decision engine: evaluates WRITE/UPDATE/REVIEW/SKIP, creates candidates |

### 3.2 Storage Paths

| Item | Path (relative to HERMES_HOME) | Description |
|------|-------------------------------|-------------|
| Root | `memory/reviews/` | Review queue root directory |
| Items | `memory/reviews/items/` | Individual review item JSON files |
| Events | `memory/reviews/events.jsonl` | Append-only event log |
| Lock | `memory/reviews/.queue.lock` | File lock for concurrent access |

**Resolved dev path:** `/Users/huangruibang/Code/hermes-home-dev/memory/reviews/`
**Current state:** Directory exists, 0 pending reviews.

### 3.3 Review Item JSON Structure

The `MemoryReviewItem` dataclass (line 68 of `memory_review_queue.py`) defines:

```python
@dataclass
class MemoryReviewItem:
    review_id: str           # Format: MR-YYYYMMDDTHHMMSS-<fingerprint8>
    status: str              # "pending" | "approved" | "rejected" | "failed"
    created_at: str          # ISO 8601 local timestamp
    updated_at: str          # ISO 8601 local timestamp
    last_seen_at: str        # ISO 8601 local timestamp
    occurrence_count: int    # How many times this fingerprint was seen
    fingerprint: str         # SHA-256 of normalized candidate fields
    source: dict             # {kind, channel, session_id_hash, message_id}
    original_decision: str   # WRITE | UPDATE | REVIEW | SKIP | SKIP_DUPLICATE
    proposed_action: str     # WRITE | UPDATE | UNDECIDED
    candidate: dict          # {summary, category, tags, title, type, importance, ttl, source_confidence}
    evaluation: dict         # {score, score_breakdown, reason_codes, reasons, title_similarity, ...}
    matched_memory: dict|None # {memory_id, title, category}
    approval: dict|None      # {approved_at, action, memory_id}
    rejection: dict|None     # {rejected_at, reason}
    last_error: str|None     # Error message from failed operations
    version: int = 1         # Schema version
```

### 3.4 Event Structure

Events are appended to `memory/reviews/events.jsonl`:

```json
{"time": "...", "event": "review_created", "review_id": "...", "decision": "...", ...}
{"time": "...", "event": "review_duplicate_seen", "review_id": "...", "occurrence_count": 2}
{"time": "...", "event": "review_approved", "review_id": "...", "action": "...", "memory_id": "..."}
{"time": "...", "event": "review_rejected", "review_id": "...", "reason": "..."}
{"time": "...", "event": "review_approval_failed", "review_id": "...", "error": "..."}
```

### 3.5 Review Status Enum

```python
class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
```

### 3.6 Proposed Action Enum

```python
class ProposedAction(str, Enum):
    WRITE = "WRITE"
    UPDATE = "UPDATE"
    UNDECIDED = "UNDECIDED"
```

### 3.7 Evaluation Fields

The `evaluation` dict in a review item contains:

| Field | Type | Description |
|-------|------|-------------|
| `score` | int | Memory candidate score (0–100) |
| `score_breakdown` | list[{rule, value}] | Individual rule contributions |
| `reason_codes` | list[str] | Machine-readable reason identifiers |
| `reasons` | list[str] | Human-readable reason descriptions |
| `title_similarity` | float | Title similarity to best match (0.0–1.0) |
| `summary_similarity` | float | Summary similarity to best match |
| `combined_similarity` | float | Combined text similarity |
| `similarity` | float | Overall best similarity |
| `tag_overlap` | list[str] | All overlapping tags |
| `core_tag_overlap` | list[str] | Non-generic overlapping tags |
| `protected_target` | bool | Whether matched memory is P0/permanent |

### 3.8 Candidate Fields

The `candidate` dict contains:

| Field | Type | Description |
|-------|------|-------------|
| `summary` | str | Memory summary (may contain user message excerpt) |
| `category` | str | Target memory category |
| `tags` | list[str] | Memory tags |
| `title` | str | Memory title (may be similar to summary) |
| `type` | str | Memory type (default: "project_status") |
| `importance` | str | Memory importance (P0/P1/P2) |
| `ttl` | str | Memory TTL |
| `source_confidence` | str | "user_confirmed" or "assistant_inferred" |

### 3.9 Function Classification

**Read-only functions (safe for Phase 1A):**

| Function | Description | Side Effects |
|----------|-------------|-------------|
| `get_review_queue_config()` | Parse review queue config | None |
| `get_review_queue_paths()` | Resolve storage paths | None |
| `list_review_items()` | List items with filtering | None |
| `validate_review_item()` | Validate item structure | None |
| `load_review_item()` | Load single item by ID | None |
| `get_review_queue_summary()` | Queue statistics | None |
| `format_review_item()` | Format item for CLI display | None |
| `proposed_action_for()` | Map decision to action | None |
| `fingerprint_memory_candidate()` | Compute candidate fingerprint | None |

**Write functions (prohibited in Phase 1A):**

| Function | Description | Side Effects |
|----------|-------------|-------------|
| `enqueue_review_item()` | Create/update review item | Writes JSON, appends event |
| `approve_review_item()` | Approve review and execute write | Writes JSON, appends event, creates/updates memory |
| `reject_review_item()` | Reject review item | Writes JSON, appends event |
| `append_review_event()` | Append event to events.jsonl | Appends to events file |
| `atomic_write_review_json()` | Write review item JSON | Writes file |
| `_ensure_paths()` | Create directories if missing | May create directories |
| `revalidate_review_approval()` | Re-validate approval conditions | Reads memory system (no writes, but imports write-capable modules) |

### 3.10 Sensitive Fields Analysis

**Fields that may contain sensitive content:**

| Field | Risk | Reason |
|-------|------|--------|
| `candidate.summary` | HIGH | May contain excerpt from user message |
| `candidate.title` | MEDIUM | Usually same as summary |
| `evaluation.reasons` | MEDIUM | Human-readable strings, generally safe |
| `source.session_id_hash` | LOW | Hashed, not raw session ID |
| `source.message_id` | LOW | UUID, no content |
| `rejection.reason` | MEDIUM | User/admin-provided text |
| `last_error` | MEDIUM | May contain internal paths or error details |
| `fingerprint` | LOW | SHA-256 hash, no content |

**Fields that must NOT be exposed:**

The Review Queue item does NOT store raw user messages, raw assistant replies, system prompts, or API keys directly. However:

- `candidate.summary` is derived from user message text (truncated to 100 chars by `extract_memory_candidate`)
- `candidate.title` is typically set to the same as summary
- `evaluation.reasons` contains human-readable descriptions that are rule-generated (safe)
- `last_error` may contain internal Python exception strings or file paths

**Conclusion:** The Review Queue stores structured memory *candidates*, not raw conversation text. The `summary` and `title` fields are the most sensitive, as they are derived from user messages but are already truncated/normalized by the memory writer. Phase 1A must still apply truncation and path redaction to these fields.

### 3.11 Current Queue Data

Dev environment has **0 pending reviews**. The Review Queue is disabled by default (`enabled: false` in config). Data exists only when the queue is explicitly enabled and candidates are evaluated.

---

## 4. Phase 1A Read-Only API Proposal (Draft)

### 4.1 Proposed Routes

3 new GET routes:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dev/v1/reviews/status` | Review queue availability, configuration, and counts |
| GET | `/api/dev/v1/reviews` | Paginated review item list with filtering |
| GET | `/api/dev/v1/reviews/{reviewId}` | Single review item detail |

### 4.2 GET /reviews/status

**Purpose:** Display Review Queue system status, configuration state, and item counts.

**Request:** No parameters.

**Response:**

```json
{
  "data": {
    "available": true,
    "readOnly": true,
    "queueEnabled": false,
    "writeEnabled": false,
    "approveEnabled": false,
    "rejectEnabled": false,
    "enqueueEnabled": false,
    "counts": {
      "pending": 0,
      "approved": 0,
      "rejected": 0,
      "failed": 0,
      "total": 0
    },
    "storage": {
      "available": true,
      "redactedPath": "[dev-home]/memory/reviews"
    }
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

**Notes:**
- `readOnly` is always `true` in Phase 1A
- All write flags (`writeEnabled`, `approveEnabled`, `rejectEnabled`, `enqueueEnabled`) are always `false` in Phase 1A
- `redactedPath` uses the same pattern as existing memory status (`[dev-home]/...`)
- `storage.available` indicates whether the items directory exists
- No real absolute paths, no secrets

### 4.3 GET /reviews

**Purpose:** Paginated listing of review items with filtering.

**Query Parameters:**

| Parameter | Type | Default | Validation |
|-----------|------|---------|------------|
| `status` | string | `"pending"` | `pending\|approved\|rejected\|failed\|all` |
| `decision` | string | `"all"` | `WRITE\|UPDATE\|REVIEW\|SKIP\|SKIP_DUPLICATE\|all` |
| `category` | string | (none) | Alphanumeric + hyphens, max 64 chars |
| `query` | string | (none) | Max 200 chars, no control characters |
| `limit` | int | `30` | 1–100 |
| `offset` | int | `0` | ≥ 0 |
| `order` | string | `"updated_desc"` | `created_desc\|updated_desc` |

**Response:**

```json
{
  "data": {
    "items": [
      {
        "reviewId": "MR-20260608T143000-a1b2c3d4",
        "status": "pending",
        "decision": "WRITE",
        "proposedAction": "WRITE",
        "category": "hermes",
        "title": "...",
        "summaryPreview": "...",
        "tags": ["hermes", "gateway"],
        "score": 90,
        "reasonCodes": ["WRITE_CANDIDATE", "hermes_project_terms"],
        "targetMemoryId": null,
        "protectedTarget": false,
        "occurrenceCount": 1,
        "createdAt": "2026-06-08T14:30:00+08:00",
        "updatedAt": "2026-06-08T14:30:00+08:00",
        "reviewedAt": null
      }
    ],
    "page": {
      "offset": 0,
      "limit": 30,
      "total": 1,
      "hasMore": false
    }
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

**Notes:**
- `summaryPreview` is truncated to max 120 characters
- `title` is the candidate title (already truncated by memory writer to ~100 chars)
- `targetMemoryId` comes from `matched_memory.memory_id` (null if no match)
- `protectedTarget` comes from `evaluation.protected_target`
- `reviewedAt` is `null` for pending items; for approved/rejected, comes from approval/rejection timestamp

### 4.4 GET /reviews/{reviewId}

**Purpose:** Detailed view of a single review item.

**Path Parameters:**

| Parameter | Type | Validation |
|-----------|------|------------|
| `reviewId` | string | Must match `^MR-\d{8}T\d{6}-[0-9a-f]{8}$` |

**Response:**

```json
{
  "data": {
    "reviewId": "MR-20260608T143000-a1b2c3d4",
    "status": "pending",
    "decision": "WRITE",
    "proposedAction": "WRITE",
    "category": "hermes",
    "title": "...",
    "summary": "...",
    "tags": ["hermes", "gateway"],
    "score": 90,
    "scoreBreakdown": [
      {"rule": "progress_keyword", "value": 20},
      {"rule": "git_hash", "value": 20}
    ],
    "reasonCodes": ["WRITE_CANDIDATE", "hermes_project_terms"],
    "similarity": {
      "title": 0.45,
      "summary": 0.32,
      "combined": 0.38,
      "targetMemoryId": null
    },
    "target": {
      "memoryId": null,
      "protected": false,
      "protectionReason": null
    },
    "safety": {
      "readOnly": true,
      "approveAvailable": false,
      "rejectAvailable": false,
      "writeAvailable": false,
      "dryRunAvailable": false
    },
    "timestamps": {
      "createdAt": "2026-06-08T14:30:00+08:00",
      "updatedAt": "2026-06-08T14:30:00+08:00",
      "reviewedAt": null,
      "lastSeenAt": "2026-06-08T14:30:00+08:00"
    },
    "occurrenceCount": 1,
    "errors": {
      "lastError": null
    }
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

**Notes:**
- `summary` is truncated to max 300 characters with path redaction applied
- `scoreBreakdown` contains rule/value pairs from evaluation
- `similarity` object contains similarity scores and target memory reference
- `target` describes the matched memory and protection status
- `safety` object always has write flags set to `false` in Phase 1A
- `errors.lastError` is redacted (path removal, truncated to 200 chars)
- `decision` maps from `original_decision` field
- For approved items, `reviewedAt` = `approval.approved_at`
- For rejected items, `reviewedAt` = `rejection.rejected_at`

---

## 5. DTO Whitelist

### 5.1 List Item Fields (GET /reviews)

| API Field | Source Field | Transformation |
|-----------|-------------|----------------|
| `reviewId` | `review_id` | Direct |
| `status` | `status` | Direct, validated enum |
| `decision` | `original_decision` | Direct |
| `proposedAction` | `proposed_action` | Direct |
| `category` | `candidate.category` | Direct |
| `title` | `candidate.title` | Truncated to 120 chars, path redaction |
| `summaryPreview` | `candidate.summary` | Truncated to 120 chars, path redaction |
| `tags` | `candidate.tags` | Direct (list of strings) |
| `score` | `evaluation.score` | Direct (int) |
| `reasonCodes` | `evaluation.reason_codes` | Direct (list of strings) |
| `targetMemoryId` | `matched_memory.memory_id` | Direct (nullable) |
| `protectedTarget` | `evaluation.protected_target` | Direct (bool) |
| `occurrenceCount` | `occurrence_count` | Direct (int) |
| `createdAt` | `created_at` | Direct (ISO 8601) |
| `updatedAt` | `updated_at` | Direct (ISO 8601) |
| `reviewedAt` | `approval.approved_at` or `rejection.rejected_at` | Nullable, derived |

### 5.2 Detail Fields (GET /reviews/{reviewId})

All list item fields, plus:

| API Field | Source Field | Transformation |
|-----------|-------------|----------------|
| `summary` | `candidate.summary` | Truncated to 300 chars, path redaction |
| `scoreBreakdown` | `evaluation.score_breakdown` | Direct (list of {rule, value}) |
| `similarity.title` | `evaluation.title_similarity` | Direct (float) |
| `similarity.summary` | `evaluation.summary_similarity` | Direct (float) |
| `similarity.combined` | `evaluation.combined_similarity` | Direct (float) |
| `similarity.targetMemoryId` | `matched_memory.memory_id` | Direct (nullable) |
| `target.memoryId` | `matched_memory.memory_id` | Direct (nullable) |
| `target.protected` | `evaluation.protected_target` | Direct (bool) |
| `target.protectionReason` | Derived from reason_codes | Nullable string |
| `safety.readOnly` | Constant `true` | Phase 1A always true |
| `safety.approveAvailable` | Constant `false` | Phase 1A always false |
| `safety.rejectAvailable` | Constant `false` | Phase 1A always false |
| `safety.writeAvailable` | Constant `false` | Phase 1A always false |
| `safety.dryRunAvailable` | Constant `false` | Phase 1A always false |
| `timestamps.lastSeenAt` | `last_seen_at` | Direct (ISO 8601) |
| `errors.lastError` | `last_error` | Path redaction, truncated to 200 chars |

### 5.3 Forbidden Fields (Must NOT Appear in Any Response)

| Category | Examples |
|----------|---------|
| Raw conversation content | Full user message, full assistant reply |
| Raw candidate text | Untruncated `candidate.summary`, `candidate.title` beyond limit |
| Internal paths | Absolute paths (`/Users/...`, `/home/...`), file:// URIs |
| Fingerprint | `fingerprint` (internal dedup mechanism) |
| Source metadata | `source.session_id_hash`, `source.message_id`, `source.channel` |
| Evaluation details | `evaluation.reasons` (human-readable, but internal) |
| Full evaluation | `evaluation.similarity` (redundant with breakdown) |
| Full tag overlap | `evaluation.tag_overlap`, `evaluation.core_tag_overlap` |
| Internal metadata | `version` |
| Matched memory detail | `matched_memory.title`, `matched_memory.category` (expose only ID) |
| Approval/rejection detail | `approval`, `rejection` objects (expose only `reviewedAt` timestamp) |
| Error stack traces | Full Python exceptions |
| Configuration | Internal config values, thresholds |
| Secrets | API keys, tokens, cookies, credentials |
| Production paths | Any path containing `~/.hermes` or production paths |

### 5.4 Redaction Rules

Apply existing `redact_local_paths()` from `dev_web_memory_service.py`:

| Pattern | Replacement |
|---------|-------------|
| `/Users/<segment>/...` | `[local-path]` |
| `/home/<segment>/...` | `[local-path]` |
| `C:\<segment>\...` | `[local-path]` |
| `file://...` | `[file-uri-redacted]` |
| `memory://...` | Preserved (not redacted) |
| `https://...` | Preserved (not redacted) |
| `http://...` | Preserved (not redacted) |

Additionally for Review Queue:

| Context | Rule |
|---------|------|
| Status `storage.redactedPath` | Use `[dev-home]/memory/reviews` pattern (matching existing memory status) |
| `title` in list response | Truncate to 120 chars, apply `redact_local_paths()` |
| `summaryPreview` in list response | Truncate to 120 chars, apply `redact_local_paths()` |
| `summary` in detail response | Truncate to 300 chars, apply `redact_local_paths()` |
| `errors.lastError` | Truncate to 200 chars, apply `redact_local_paths()` |

---

## 6. Error Model

### 6.1 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `REVIEW_QUEUE_UNAVAILABLE` | 503 | Review queue storage is not accessible or items directory missing |
| `REVIEW_NOT_FOUND` | 404 | Review item with given ID does not exist |
| `INVALID_REVIEW_ID` | 400 | Review ID format is invalid (must match `MR-\d{8}T\d{6}-[0-9a-f]{8}`) |
| `INVALID_REVIEW_QUERY` | 400 | Query parameter validation failed (invalid status, decision, limit, offset, etc.) |
| `REVIEW_STORE_ERROR` | 500 | Unexpected error reading review item JSON |
| `UNSAFE_ENVIRONMENT` | 500 | Environment check failed (wrong HERMES_HOME, wrong source root) |
| `INTERNAL_ERROR` | 500 | Unexpected internal error |

### 6.2 Error Response Envelope

Follows existing Dev API error envelope from `dev_web_errors.py`:

```json
{
  "error": {
    "code": "REVIEW_NOT_FOUND",
    "message": "Review item was not found.",
    "details": null
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

### 6.3 Error Message Redaction

Error messages must NOT contain:

- Real file system paths
- Python tracebacks
- Exception class names or repr
- SQL queries
- Internal variable names
- API keys, tokens, secrets
- Raw review item content

All error messages must use the same forbidden-string check as existing `dev_web_errors.py`:
- "traceback", file paths, usernames, ".hermes", "state.db", "api_key", "token", "secret", "cookie", "sql", "exception"

### 6.4 Validation Rules

| Input | Validation |
|-------|------------|
| `reviewId` path param | Must match regex `^MR-\d{8}T\d{6}-[0-9a-f]{8}$` |
| `status` query param | Must be one of: `pending`, `approved`, `rejected`, `failed`, `all` |
| `decision` query param | Must be one of: `WRITE`, `UPDATE`, `REVIEW`, `SKIP`, `SKIP_DUPLICATE`, `all` |
| `category` query param | Alphanumeric + hyphens, max 64 chars |
| `query` query param | Max 200 chars, no ASCII control characters |
| `limit` query param | Integer, 1–100 |
| `offset` query param | Integer, ≥ 0 |
| `order` query param | Must be one of: `created_desc`, `updated_desc` |

---

## 7. Pagination / Filter / Sort Strategy

### 7.1 Pagination

Follows existing Dev API pagination pattern:

- **Method:** Offset-based (matching sessions and memory items APIs)
- **Default limit:** 30
- **Max limit:** 100
- **Response includes:** `page.offset`, `page.limit`, `page.total`, `page.hasMore`

### 7.2 Filtering

| Filter | Behavior |
|--------|----------|
| `status` | Filter by review item status. Default: `pending`. `all` returns all statuses. |
| `decision` | Filter by `original_decision` field. Default: `all`. |
| `category` | Filter by `candidate.category`. Default: no filter. |
| `query` | Case-insensitive text search against `candidate.title` and `candidate.summary`. Default: no search. |

### 7.3 Sorting

| Order | Sort Key | Direction |
|-------|----------|-----------|
| `updated_desc` (default) | `updated_at` | Descending (most recently updated first) |
| `created_desc` | `created_at` | Descending (newest first) |

**Implementation note:** The existing `list_review_items()` function sorts by `updated_at` descending. Phase 1A implementation should use this function with `include_all=True` and apply server-side filtering/pagination on the result, since the Review Queue stores items as individual JSON files (no database query engine). For queues with > 500 items, this may need optimization in later phases.

---

## 8. Frontend Panel Information Architecture

### 8.1 Component Proposal

| Component | Location (future) |
|-----------|-------------------|
| `ReviewPanel.vue` | `apps/hermes-dev-webui/src/components/workspace/ReviewPanel.vue` |
| Review store | `apps/hermes-dev-webui/src/stores/review.ts` |
| Review API types | `apps/hermes-dev-webui/src/types/api/review.ts` |

**This document does NOT create these files.** They are defined in Phase 1A implementation.

### 8.2 Panel Layout

```
┌─────────────────────────────────────────┐
│ Review Queue                    [Read-Only] │
│                                         │
│ Pending: 0  Approved: 2  Rejected: 1   │
│ Queue: disabled                        │
├─────────────────────────────────────────┤
│ Status: [All ▾] Decision: [All ▾]      │
│ Category: [All ▾]  [Search...] [↻]     │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ MR-20260608T143000-a1b2c3d4        │ │
│ │ WRITE · pending · hermes · score 90│ │
│ │ "Add gateway config support..."     │ │
│ │ Tags: hermes, gateway              │ │
│ │ Occurrences: 1 · 2026-06-08 14:30  │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ MR-20260607T090000-e5f6a7b8        │ │
│ │ UPDATE · approved · hermes         │ │
│ │ ...                                │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Showing 1-2 of 2  [← 1 →]             │
├─────────────────────────────────────────┤
│ Detail: MR-20260608T143000-a1b2c3d4    │
│                                         │
│ Title: "Add gateway config support..." │
│ Summary: [truncated/redacted text]     │
│ Score: 90                               │
│   +20 progress_keyword                  │
│   +20 git_hash                          │
│ Decision: WRITE                         │
│ Similarity: title 0.45 · summary 0.32  │
│ Target: none                            │
│ Protected: no                           │
│                                         │
│ ┌─ Safety ────────────────────────────┐ │
│ │ ● Read-only mode (Phase 1A)        │ │
│ │ ○ Approve: disabled                │ │
│ │ ○ Reject: disabled                 │ │
│ │ ○ Enqueue: disabled                │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Created: 2026-06-08 14:30              │
│ Updated: 2026-06-08 14:30              │
│ Occurrences: 1                          │
└─────────────────────────────────────────┘
```

### 8.3 Status Header

- Queue available indicator (green/gray)
- Read-only badge (always visible in Phase 1A)
- Counts: pending, approved, rejected, failed
- Queue enabled/disabled status
- Write actions disabled indicator

### 8.4 Filter Bar

- Status dropdown: All, Pending, Approved, Rejected, Failed
- Decision dropdown: All, WRITE, UPDATE, REVIEW, SKIP
- Category dropdown: populated from available categories
- Search input: text search against title/summary
- Refresh button: re-fetch list

### 8.5 Review List

Each item shows:

- Review ID (truncated)
- Status badge (color-coded)
- Decision badge
- Proposed action
- Category
- Title (truncated, redacted)
- Score
- Reason codes (collapsed)
- Tags
- Occurrence count
- Created date

### 8.6 Detail Panel

When an item is selected:

- Full title (redacted)
- Summary (truncated to 300 chars, redacted)
- Score with breakdown
- Decision and proposed action
- Similarity scores
- Target memory ID and protection status
- Safety status (all disabled in Phase 1A)
- Timestamps (created, updated, last seen, reviewed)
- Occurrence count
- Last error (redacted, if any)

### 8.7 Safety Area

Always visible in detail view:

- Read-only mode indicator
- Approve: disabled (grayed out)
- Reject: disabled (grayed out)
- Enqueue: disabled (grayed out)
- Text: "Read-only in Phase 1A"

### 8.8 Disabled Actions

The following UI elements must be visibly disabled:

- Approve button (grayed out, tooltip: "Not available in read-only mode")
- Reject button (grayed out, tooltip: "Not available in read-only mode")
- Enqueue button (not present or grayed out)
- Write Memory button (not present)
- Run Agent button (not present)
- Raw prompt viewer (not present)
- Raw conversation viewer (not present)

---

## 9. OpenAPI Strategy

### 9.1 Current State

- Current implemented OpenAPI: **11 paths** in `docs/webui/openapi/dev-web-api-v1.yaml`
- dev-check validates: `OpenAPI paths: 11`

### 9.2 Phase 1A-00 Rule

This task does **NOT** modify `docs/webui/openapi/dev-web-api-v1.yaml`. The proposed 3 review routes exist only in this draft document.

### 9.3 Phase 1A Implementation Rule

When Phase 1A is implemented:

1. Update `docs/webui/openapi/dev-web-api-v1.yaml` to include 3 new paths:
   - `GET /api/dev/v1/reviews/status`
   - `GET /api/dev/v1/reviews`
   - `GET /api/dev/v1/reviews/{reviewId}`
2. Path count increases from 11 to **14**
3. Update dev-check `ALLOWED_ROUTES` and expected path count
4. Add schemas for `ReviewStatusResponse`, `ReviewListResponse`, `ReviewDetailResponse`, `ReviewListItem`, `ReviewDetail`

---

## 10. Dev-Check Update Strategy

### 10.1 Current State

dev-check expects:
- OpenAPI paths: 11
- All 11 routes present
- Forbidden routes absent

### 10.2 Phase 1A Implementation Updates

When Phase 1A is implemented:

| Check | Current | After 1A |
|-------|---------|----------|
| OpenAPI path count | 11 | 14 |
| ALLOWED_ROUTES | (11 existing) | + `GET /reviews/status`, `GET /reviews`, `GET /reviews/{reviewId}` |
| Forbidden POST routes | (existing list) | + `POST /reviews/*`, `POST /reviews/{reviewId}/approve`, `POST /reviews/{reviewId}/reject`, `POST /reviews/enqueue` |

**Key rule:** Phase 1A allows new `GET /reviews*` routes. `POST /reviews*` remains forbidden until Phase 1B/1C.

### 10.3 New Checks (Optional)

- Review Queue read-only feature flag check
- Review Panel component file existence check (optional, not blocking)

---

## 11. Playwright Smoke Update Strategy

### 11.1 Current State

Smoke tests at `apps/hermes-dev-webui/tests/smoke/phase-0e-03-smoke.spec.ts`:
- 4 viewports × 5 themes = 20 combinations
- Forbidden patterns include `/reviews` endpoints

### 11.2 Phase 1A Implementation Updates

When Phase 1A is implemented, add smoke checks:

1. **Review tab visible** — Workspace panel has Review tab
2. **GET /reviews/status intercepted** — Status API called on tab open
3. **GET /reviews intercepted** — List API called with default filters
4. **GET /reviews/{id} intercepted** — Detail API called on item selection
5. **No approve/reject/enqueue requests** — Forbidden pattern enforcement
6. **No raw prompt/path/secret in response** — Content safety check
7. **Read-only badge visible** — Status indicator present
8. **Disabled approve/reject UI** — Action buttons grayed out with correct text
9. **Five themes render** — Review Panel displays correctly in all themes
10. **Four viewports** — No overflow at mobile/tablet/desktop/wide breakpoints

### 11.3 Forbidden Pattern Update

Update smoke spec forbidden patterns:

- Remove: `/reviews\b` from forbidden list (GET is now allowed)
- Keep: `POST.*\/reviews` in forbidden list
- Keep: `/reviews\/.*\/(approve|reject)/` in forbidden list

---

## 12. Side-Effect Hash Validation Strategy

### 12.1 Phase 1A Read-Only Guarantee

Phase 1A is read-only. The following must remain **completely unchanged** after any Review Queue API operation:

| Path | What to verify |
|------|----------------|
| `state.db` | SHA-256 unchanged |
| `MEMORY.md` | SHA-256 unchanged |
| `memory/indexes/` | All files SHA-256 unchanged |
| `memory/records/` | All files SHA-256 unchanged |
| `memory/events.jsonl` | SHA-256 unchanged |
| `memory/snapshots/` | All files SHA-256 unchanged |
| `memory/reviews/` | All files SHA-256 unchanged (items + events.jsonl + .queue.lock) |

### 12.2 Validation Method

```bash
# Before Phase 1A implementation testing
find /Users/huangruibang/Code/hermes-home-dev/memory -type f | sort | xargs shasum > /tmp/pre-review-hash.txt

# After testing
find /Users/huangruibang/Code/hermes-home-dev/memory -type f | sort | xargs shasum > /tmp/post-review-hash.txt

# Compare
diff /tmp/pre-review-hash.txt /tmp/post-review-hash.txt
# Expected: no differences
```

### 12.3 Blocking Condition

If reading Review Queue items via `list_review_items()` or `load_review_item()` causes any of:
- File mtime changes on review item JSON files
- Event append to `events.jsonl`
- New file creation in `memory/reviews/`
- Directory creation

This is a **blocking issue**. The implementation must not call any write-capable function.

**Verified:** `list_review_items()` (line 271) and `load_review_item()` (line 317) are confirmed read-only. They use `json.loads(path.read_text())` and do not call `_ensure_paths()`, `append_review_event()`, or `atomic_write_review_json()`. The only function called that touches the filesystem is `paths.items.exists()` (existence check, read-only).

---

## 13. Non-Goals

This task does NOT:

1. Implement any API route
2. Modify `hermes_cli/dev_web_api.py`
3. Modify `docs/webui/openapi/dev-web-api-v1.yaml`
4. Create frontend components
5. Approve, reject, or enqueue review items
6. Modify review queue files
7. Modify memory files
8. Start any services
9. Access or modify production environment
10. Begin Phase 1A implementation

---

## 14. Risks

### 14.1 P0 — Blockers

None identified.

### 14.2 P1 — Must Resolve Before Phase 1A Implementation

| ID | Risk | Mitigation |
|----|------|-----------|
| P1-R1 | `list_review_items()` loads all items into memory before filtering | For Phase 1A, this is acceptable (queue is typically small, max_pending=500). Document as known limitation. Optimize in later phase if needed. |
| P1-R2 | `candidate.summary` may contain user message excerpts | Apply truncation (120 chars for list, 300 chars for detail) and path redaction. Review actual data when queue has items. |

### 14.3 P2 — Should Monitor

| ID | Risk | Mitigation |
|----|------|-----------|
| P2-R1 | Queue directory doesn't exist on fresh install | `list_review_items()` handles missing directory gracefully (returns empty list). Status API should report `storage.available: false`. |
| P2-R2 | `evaluation.reasons` list may be large | Only expose `reason_codes` in list, keep `reasons` internal. |
| P2-R3 | `score_breakdown` may reveal scoring rules | Considered acceptable — scoring rules are part of the system design, not secrets. |

---

## 15. Acceptance Criteria

Phase 1A-00 completes when:

1. ✅ Review Queue data source audited (structure, functions, storage, sensitive fields)
2. ✅ Read-only API proposal frozen (3 routes with request/response schemas)
3. ✅ DTO whitelist frozen (list fields, detail fields, transformations)
4. ✅ Forbidden fields documented (raw content, paths, secrets, internal metadata)
5. ✅ Path/secret/raw content redaction rules defined (reusing existing `redact_local_paths()`)
6. ✅ Error model frozen (7 error codes, envelope, redaction, validation rules)
7. ✅ Pagination/filter/sort strategy frozen (offset-based, 4 filters, 2 sort orders)
8. ✅ Frontend information architecture frozen (panel layout, status, filters, list, detail, safety area)
9. ✅ OpenAPI strategy documented (no change to 11-path contract in this task)
10. ✅ dev-check update strategy documented (11 → 14 paths in Phase 1A)
11. ✅ Playwright smoke update strategy documented (10 new checks)
12. ✅ Side-effect hash validation strategy documented (SHA-256 verification)
13. ✅ No API implemented
14. ✅ No business code modified
15. ✅ No memory/review files modified
16. ✅ memory-check PASS
17. ✅ dev-check PASS
18. ✅ compileall PASS
19. ✅ Document produced
20. ✅ Local commit created
21. ✅ Not pushed
22. ✅ Final worktree clean
23. ✅ Production environment unaffected

---

## 16. Next Task

**Phase 1A: Review Queue Read-Only Panel Implementation**

This task does NOT automatically start Phase 1A.
