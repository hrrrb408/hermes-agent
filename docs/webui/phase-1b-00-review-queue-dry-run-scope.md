# Phase 1B-00: Review Queue Approve/Reject Dry-Run Scope & Contract Freeze

**Status:** Completed
**Date:** 2026-06-08
**Branch:** dev-huangruibang
**Base commit:** 97ec7c32c (Phase 1A-Release: Review Queue closure tests)
**Depends on:** Phase 1A Completed & Pushed
**Governance scope:** `docs/webui/phase-1-00-planning-and-scope.md`

---

## 1. Background

Phase 1A completed the Review Queue Read-Only Panel and was pushed to `origin/dev-huangruibang` at commit `97ec7c32c`. The Dev WebUI now has 14 read-only business routes, including 3 review queue GET endpoints. No write capability exists.

Phase 1B-00 is a **scope and contract freeze** task for Phase 1B (Review Queue Approve/Reject Dry-Run). It audits the real approve/reject side effects, defines the dry-run boundary, freezes API contracts, DTOs, error models, and UI information architecture — without implementing any functionality.

---

## 2. Current Baseline

### 2.1 Repository State

| Item | Value |
|------|-------|
| Branch | `dev-huangruibang` |
| HEAD | `97ec7c32cda4347e4c3f363b0b98d1fa5fd07469` |
| origin/dev-huangruibang | `97ec7c32cda4347e4c3f363b0b98d1fa5fd07469` |
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

14 implemented business routes (documented in `docs/webui/openapi/dev-web-api-v1.yaml`):

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
| GET | `/api/dev/v1/reviews/status` |
| GET | `/api/dev/v1/reviews` |
| GET | `/api/dev/v1/reviews/{reviewId}` |

**OpenAPI paths: 14. All read-only / side-effect-free.**

### 2.4 Current Review Queue Capability

| Capability | Status |
|-----------|--------|
| Read review items | ✅ Available (Phase 1A) |
| List review items | ✅ Available (Phase 1A) |
| View review detail | ✅ Available (Phase 1A) |
| Approve (dry-run) | ❌ Not available |
| Reject (dry-run) | ❌ Not available |
| Approve (execute) | ❌ Not available |
| Reject (execute) | ❌ Not available |
| Enqueue | ❌ Not available |

### 2.5 Current Write Capability

**None.** The Dev WebUI has zero write operations across all 14 routes.

---

## 3. Review Approve/Reject Audit Summary

### 3.1 Source Files

| File | Role |
|------|------|
| `agent/memory_review_queue.py` | Core Review Queue module: storage, validation, CRUD, approve, reject |
| `agent/runtime_memory_writer.py` | Decision engine, similarity, protection checks |
| `hermes_cli/memory_router.py` | Memory CRUD (create/update items) — called during approve |

### 3.2 Approve Real Side Effects

`approve_review_item()` (line 560–679) performs the following when `dry_run=False`:

| Step | Function Called | Side Effect |
|------|----------------|-------------|
| 1 | `load_review_item()` | Read-only |
| 2 | `revalidate_review_approval()` | Read-only (validates category, duplicate, protection) |
| 3 | `allocate_memory_id()` | Reads next ID counter |
| 4 | `create_memory_item()` or `update_memory_item()` | **WRITES** memory/indexes/{category}.md, memory/records/{category}/{id}.md, memory/events.jsonl |
| 5 | `atomic_write_review_json()` | **WRITES** memory/reviews/items/{reviewId}.json |
| 6 | `append_review_event()` | **APPENDS** to memory/reviews/events.jsonl |
| 7 | Status change: `"pending"` → `"approved"` | In-memory + persisted via step 5 |
| 8 | Adds `approval` dict to review item | In-memory + persisted via step 5 |

**Files modified by real approve:**

| File | Change |
|------|--------|
| `memory/reviews/items/{reviewId}.json` | Status → approved, approval metadata added |
| `memory/reviews/events.jsonl` | `review_approved` event appended |
| `memory/indexes/{category}.md` | New/updated index entry (via memory_router) |
| `memory/records/{category}/{id}.md` | New/updated memory record (via memory_router) |
| `memory/events.jsonl` | `memory_create` or `memory_update` event appended |

### 3.3 Approve Dry-Run Path

When `dry_run=True` (line 572–574):

```python
if dry_run:
    item = load_review_item(review_id, home=home, config=config)
    return item, revalidate_review_approval(item, action=action, target=target)
```

**No side effects.** Only calls `load_review_item()` (read) and `revalidate_review_approval()` (read-only validation).

The `revalidate_review_approval()` function (line 477–557):
- Reads category list via `parse_root()` — read-only
- Reads existing memories via `find_best_memory_match()` → `list_items()` — read-only
- Computes similarity via `calculate_similarity_breakdown()` — pure computation
- Checks protection via `is_protected_memory()` — pure check
- Checks target existence via `find_item()` — read-only
- Returns validation result dict — no writes

### 3.4 Reject Real Side Effects

`reject_review_item()` (line 429–458):

| Step | Function Called | Side Effect |
|------|----------------|-------------|
| 1 | `load_review_item()` | Read-only |
| 2 | `atomic_write_review_json()` | **WRITES** memory/reviews/items/{reviewId}.json |
| 3 | `append_review_event()` | **APPENDS** to memory/reviews/events.jsonl |
| 4 | Status change: `"pending"` → `"rejected"` | In-memory + persisted via step 2 |
| 5 | Adds `rejection` dict to review item | In-memory + persisted via step 2 |

**Reject does NOT call memory_router.** It only modifies the review item file and appends a rejection event. No memory data is created or updated.

**Files modified by real reject:**

| File | Change |
|------|--------|
| `memory/reviews/items/{reviewId}.json` | Status → rejected, rejection metadata added |
| `memory/reviews/events.jsonl` | `review_rejected` event appended |

### 3.5 Reject Dry-Run — No Native Support

`reject_review_item()` has **no** `dry_run` parameter. Phase 1B dry-run for reject must be implemented entirely in the Dev Web API service layer by:

1. Loading the review item (read-only)
2. Validating the item status is `"pending"`
3. Computing what would change (status, rejection metadata)
4. Returning the dry-run response without calling `reject_review_item()`

### 3.6 Revalidation Checks Available for Dry-Run

The following checks from `revalidate_review_approval()` can be reused:

| Check Code | Description | Action |
|-----------|-------------|--------|
| `CATEGORY_NOT_ACTIVE_OR_MISSING` | Target category doesn't exist or is archived | WRITE, UPDATE |
| `BECAME_DUPLICATE` | Candidate became duplicate since enqueue | WRITE |
| `UPDATE_TARGET_REQUIRED` | No target specified for UPDATE | UPDATE |
| `UPDATE_TARGET_NOT_FOUND` | Target memory doesn't exist | UPDATE |
| `TARGET_P0_PROTECTED` | Target memory is P0 importance | UPDATE |
| `TARGET_PERMANENT_PROTECTED` | Target memory has permanent TTL | UPDATE |
| `CATEGORY_MISMATCH` | Target memory is in different category | UPDATE |
| `TARGET_NOT_ACTIVE` | Target memory is not active status | UPDATE |
| `NO_CORE_TAG_OVERLAP` | No meaningful tag overlap with target | UPDATE |
| `SIMILARITY_BELOW_UPDATE_THRESHOLD` | Overall similarity too low | UPDATE |
| `TITLE_SUMMARY_SIMILARITY_TOO_LOW` | Both title and summary similarity low | UPDATE |
| `INVALID_APPROVAL_ACTION` | Action is not WRITE or UPDATE | ANY |

### 3.7 Functions Forbidden in Dry-Run

Phase 1B dry-run **MUST NOT** call:

| Function | Reason |
|----------|--------|
| `approve_review_item(dry_run=False)` | Writes review JSON, events, memory data |
| `reject_review_item()` | Writes review JSON, events (no dry_run param) |
| `append_review_event()` | Writes to events.jsonl |
| `atomic_write_review_json()` | Writes review item JSON |
| `create_memory_item()` | Writes memory index, record, events |
| `update_memory_item()` | Writes memory index, record, events |
| `allocate_memory_id()` | Reads ID counter (safe but unnecessary for dry-run) |
| `enqueue_review_item()` | Creates new review items |

### 3.8 Functions Safe for Dry-Run

Phase 1B dry-run **MAY** call:

| Function | Reason |
|----------|--------|
| `load_review_item()` | Read-only |
| `list_review_items()` | Read-only |
| `get_review_queue_paths()` | Read-only |
| `get_review_queue_config()` | Read-only |
| `get_review_queue_summary()` | Read-only |
| `revalidate_review_approval()` | Read-only validation |
| `validate_review_item()` | Read-only validation |
| `format_review_item()` | Read-only formatting |
| `proposed_action_for()` | Pure computation |
| `fingerprint_memory_candidate()` | Pure computation |

### 3.9 Risks Identified

| ID | Risk | Severity | Mitigation |
|----|------|----------|-----------|
| R1 | `revalidate_review_approval()` imports `memory_router` and `runtime_memory_writer` — these modules contain write-capable functions | P2 | Only import and call the specific read-only functions (`parse_root`, `find_item`, `find_best_memory_match`, `calculate_similarity_breakdown`, `is_protected_memory`). Never call `create_memory_item()` or `update_memory_item()`. |
| R2 | Reject has no native `dry_run` parameter — Web API service must simulate | P1 | Implement reject dry-run entirely in `dev_web_review_service.py` without calling `reject_review_item()`. Perform read-only checks only. |
| R3 | Approve dry-run via `approve_review_item(dry_run=True)` returns raw item dict that may contain sensitive fields | P1 | Apply same DTO whitelisting and path redaction as Phase 1A read-only endpoints. Never expose raw item fields. |
| R4 | Concurrent real approval between dry-run preview and user review could change state | P2 | Dry-run is advisory only. Display warning that state may have changed. Re-validate at execute time (Phase 1C). |
| R5 | `revalidate_review_approval()` calls `parse_root()` which reads MEMORY.md — may be slow for large files | P3 | Acceptable for dev-only local tool. Set reasonable timeout. |

---

## 4. Phase 1B Dry-Run Scope

### 4.1 Scope

1. **2 new side-effect-free POST routes** for dry-run preview
2. **Dry-run service** in `dev_web_review_service.py` that uses only read-only functions
3. **Frontend dry-run controls** in Review Panel (buttons + result display)
4. **OpenAPI update** from 14 to 16 paths
5. **dev-check update** for 16 allowed routes with dry-run route verification
6. **Playwright smoke update** for dry-run controls and forbidden execute routes

### 4.2 Non-Goals

1. No real approve/reject execution (Phase 1C)
2. No memory write/update/archive
3. No event append to `events.jsonl`
4. No review item file modification
5. No snapshot generation
6. No review item status change
7. No `state.db` modification
8. No `MEMORY.md` modification
9. No memory index/record file modification
10. No Agent Run
11. No LLM call
12. No tool execution
13. No SSE / WebSocket
14. No batch operations
15. No enqueue capability
16. No audit event production (dry-run only)

### 4.3 Write Capability

**None.** All Phase 1B operations are dry-run preview only. No real execution is possible.

### 4.4 Allowed Side Effects

**None.** Phase 1B dry-run must produce zero side effects:

- No file writes
- No file creates
- No file appends
- No status changes
- No event append
- No Memory data modification
- No state.db changes

### 4.5 Forbidden Side Effects

| Operation | Forbidden |
|-----------|-----------|
| Write review item JSON | ✅ Forbidden |
| Append review event | ✅ Forbidden |
| Create/update memory record | ✅ Forbidden |
| Create/update memory index | ✅ Forbidden |
| Append memory event | ✅ Forbidden |
| Change review item status | ✅ Forbidden |
| Modify `MEMORY.md` | ✅ Forbidden |
| Modify `state.db` | ✅ Forbidden |
| Create snapshot | ✅ Forbidden |
| Call `approve_review_item()` | ✅ Forbidden |
| Call `reject_review_item()` | ✅ Forbidden |
| Call `enqueue_review_item()` | ✅ Forbidden |
| Call `create_memory_item()` | ✅ Forbidden |
| Call `update_memory_item()` | ✅ Forbidden |

---

## 5. Proposed API Routes

Phase 1B-00 defines 2 draft routes. **Neither is implemented in this task.**

### 5.1 POST /reviews/{reviewId}/approve/dry-run

| Attribute | Value |
|-----------|-------|
| Method | POST |
| Path | `/api/dev/v1/reviews/{reviewId}/approve/dry-run` |
| Side Effects | **None** |
| Classification | Dry-run preview |
| Phase Available | 1B |

**Purpose:** Preview what would happen if a review item were approved, without executing any real operation.

**Path Parameters:**

| Parameter | Type | Validation |
|-----------|------|------------|
| `reviewId` | string | Must match `^MR-\d{8}T\d{6}-[0-9a-f]{8}$` |

**Request Body:**

```json
{
  "confirmText": null,
  "includeDiff": true
}
```

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `confirmText` | string\|null | `null` | No | Reserved for Phase 1C execute confirmation. Ignored in dry-run. |
| `includeDiff` | boolean | `true` | No | Whether to include preview details in response. |

**Response (Success — Allowed):**

```json
{
  "data": {
    "reviewId": "MR-20260608T143000-a1b2c3d4",
    "dryRun": true,
    "action": "APPROVE",
    "allowed": true,
    "wouldModify": true,
    "wouldWriteMemory": true,
    "wouldUpdateReview": true,
    "wouldAppendEvent": true,
    "wouldCreateSnapshot": false,
    "target": {
      "memoryId": "MEM-HERMES-001",
      "category": "hermes",
      "operation": "WRITE"
    },
    "safety": {
      "devOnly": true,
      "productionBlocked": true,
      "protectedTarget": false,
      "p0Blocked": false,
      "permanentBlocked": false,
      "duplicateBlocked": false
    },
    "checks": [
      {
        "code": "CATEGORY_EXISTS",
        "status": "pass",
        "message": "Category exists and is active."
      }
    ],
    "preview": {
      "title": "...",
      "summaryPreview": "...",
      "tags": ["..."],
      "redactedPaths": true
    },
    "effects": [
      "Would create memory record.",
      "Would mark review as approved.",
      "Would append review_approved event."
    ],
    "noEffects": [
      "No file was modified.",
      "No event was appended.",
      "No memory was written."
    ]
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

**Response (Blocked — Not Allowed):**

```json
{
  "data": {
    "reviewId": "MR-20260608T143000-a1b2c3d4",
    "dryRun": true,
    "action": "APPROVE",
    "allowed": false,
    "blockedReason": "BECAME_DUPLICATE",
    "wouldModify": false,
    "wouldWriteMemory": false,
    "wouldUpdateReview": false,
    "wouldAppendEvent": false,
    "wouldCreateSnapshot": false,
    "target": {
      "memoryId": null,
      "category": "hermes",
      "operation": "WRITE"
    },
    "safety": {
      "devOnly": true,
      "productionBlocked": true,
      "protectedTarget": false,
      "p0Blocked": false,
      "permanentBlocked": false,
      "duplicateBlocked": true
    },
    "checks": [
      {
        "code": "BECAME_DUPLICATE",
        "status": "fail",
        "message": "Candidate became a duplicate since enqueue."
      }
    ],
    "preview": {
      "title": "...",
      "summaryPreview": "...",
      "tags": ["..."],
      "redactedPaths": true
    },
    "effects": [],
    "noEffects": [
      "No file was modified.",
      "No event was appended.",
      "No memory was written.",
      "Approval would be blocked."
    ]
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

**Implementation Notes:**

- The approve dry-run **MUST** call `revalidate_review_approval()` to get real validation results
- It **MUST NOT** call `approve_review_item()` — not even with `dry_run=True` — to maintain an absolute isolation boundary between Web API and agent write functions
- All validation is done by reading review item data + reading memory system state
- The `wouldWriteMemory` field indicates what **would** happen in real execute (Phase 1C), not what the dry-run does

### 5.2 POST /reviews/{reviewId}/reject/dry-run

| Attribute | Value |
|-----------|-------|
| Method | POST |
| Path | `/api/dev/v1/reviews/{reviewId}/reject/dry-run` |
| Side Effects | **None** |
| Classification | Dry-run preview |
| Phase Available | 1B |

**Purpose:** Preview what would happen if a review item were rejected, without executing any real operation.

**Path Parameters:**

| Parameter | Type | Validation |
|-----------|------|------------|
| `reviewId` | string | Must match `^MR-\d{8}T\d{6}-[0-9a-f]{8}$` |

**Request Body:**

```json
{
  "reason": "Optional reason text",
  "includeDiff": true
}
```

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `reason` | string\|null | `null` | No | Preview reason. Truncated to 200 chars. Redacted. |
| `includeDiff` | boolean | `true` | No | Whether to include preview details. |

**Response (Success — Allowed):**

```json
{
  "data": {
    "reviewId": "MR-20260608T143000-a1b2c3d4",
    "dryRun": true,
    "action": "REJECT",
    "allowed": true,
    "wouldModify": true,
    "wouldWriteMemory": false,
    "wouldUpdateReview": true,
    "wouldAppendEvent": true,
    "wouldCreateSnapshot": false,
    "target": {
      "memoryId": null,
      "category": "hermes",
      "operation": "REJECT"
    },
    "safety": {
      "devOnly": true,
      "productionBlocked": true
    },
    "checks": [
      {
        "code": "REVIEW_IS_PENDING",
        "status": "pass",
        "message": "Review item is pending and can be rejected."
      }
    ],
    "preview": {
      "reasonPreview": "Optional reason...",
      "redactedPaths": true
    },
    "effects": [
      "Would mark review as rejected.",
      "Would append review_rejected event."
    ],
    "noEffects": [
      "No file was modified.",
      "No event was appended.",
      "No memory was written."
    ]
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

**Response (Blocked — Not Allowed):**

```json
{
  "data": {
    "reviewId": "MR-20260608T143000-a1b2c3d4",
    "dryRun": true,
    "action": "REJECT",
    "allowed": false,
    "blockedReason": "REVIEW_NOT_PENDING",
    "wouldModify": false,
    "wouldUpdateReview": false,
    "wouldAppendEvent": false,
    "wouldCreateSnapshot": false,
    "target": {
      "memoryId": null,
      "category": "hermes",
      "operation": "REJECT"
    },
    "safety": {
      "devOnly": true,
      "productionBlocked": true
    },
    "checks": [
      {
        "code": "REVIEW_IS_PENDING",
        "status": "fail",
        "message": "Review item is not pending (current: approved)."
      }
    ],
    "preview": {
      "reasonPreview": "Optional reason...",
      "redactedPaths": true
    },
    "effects": [],
    "noEffects": [
      "No file was modified.",
      "No event was appended.",
      "No memory was written.",
      "Rejection would be blocked."
    ]
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

**Implementation Notes:**

- The reject dry-run **MUST NOT** call `reject_review_item()` — it has no dry_run parameter
- Validation is: load item → check status is "pending" → return result
- No memory data is affected by reject (only review item metadata changes)

### 5.3 Routes That Remain Forbidden

```http
POST /api/dev/v1/reviews/{reviewId}/approve        ← Forbidden until Phase 1C
POST /api/dev/v1/reviews/{reviewId}/reject          ← Forbidden until Phase 1C
POST /api/dev/v1/reviews/enqueue                    ← Forbidden indefinitely
PATCH /api/dev/v1/reviews/*                         ← Forbidden indefinitely
DELETE /api/dev/v1/reviews/*                        ← Forbidden indefinitely
```

---

## 6. DTO Whitelist

### 6.1 Approve Dry-Run Response Fields

| Field | Type | Source | Transformation |
|-------|------|--------|----------------|
| `reviewId` | string | `review_id` | Direct |
| `dryRun` | boolean | Constant `true` | Always true |
| `action` | string | Request action | `"APPROVE"` |
| `allowed` | boolean | `revalidation.valid` | Direct |
| `blockedReason` | string\|null | First error code | Nullable, truncated 120 chars |
| `wouldModify` | boolean | Derived | True if allowed |
| `wouldWriteMemory` | boolean | Derived | True if action is WRITE and allowed |
| `wouldUpdateReview` | boolean | Derived | True if allowed |
| `wouldAppendEvent` | boolean | Derived | True if allowed |
| `wouldCreateSnapshot` | boolean | Constant `false` | Always false for review |
| `target.memoryId` | string\|null | `matched_memory.memory_id` or computed | Nullable |
| `target.category` | string | `candidate.category` | Direct |
| `target.operation` | string | `proposed_action` | `"WRITE"` or `"UPDATE"` |
| `safety.devOnly` | boolean | Constant `true` | Always true |
| `safety.productionBlocked` | boolean | Constant `true` | Always true |
| `safety.protectedTarget` | boolean | `revalidation.protected_target` | Direct |
| `safety.p0Blocked` | boolean | Derived from revalidation errors | True if `TARGET_P0_PROTECTED` |
| `safety.permanentBlocked` | boolean | Derived from revalidation errors | True if `TARGET_PERMANENT_PROTECTED` |
| `safety.duplicateBlocked` | boolean | Derived from revalidation errors | True if `BECAME_DUPLICATE` |
| `checks[]` | array | `revalidation.errors` | Transformed to check objects |
| `checks[].code` | string | Error code | Direct |
| `checks[].status` | string | Derived | `"pass"` or `"fail"` |
| `checks[].message` | string | Human-readable | Truncated 200 chars, path redaction |
| `preview.title` | string | `candidate.title` | Truncated 120 chars, path redaction |
| `preview.summaryPreview` | string | `candidate.summary` | Truncated 200 chars, path redaction |
| `preview.tags` | string[] | `candidate.tags` | Direct |
| `preview.redactedPaths` | boolean | Constant `true` | Always true |
| `effects[]` | string[] | Derived | Human-readable effect descriptions |
| `noEffects[]` | string[] | Constant | Always includes "No file was modified." |
| `warnings[]` | string[] | Derived | Truncated 200 chars each |

### 6.2 Reject Dry-Run Response Fields

| Field | Type | Source | Transformation |
|-------|------|--------|----------------|
| `reviewId` | string | `review_id` | Direct |
| `dryRun` | boolean | Constant `true` | Always true |
| `action` | string | Constant `"REJECT"` | Always REJECT |
| `allowed` | boolean | Status check | True if pending |
| `blockedReason` | string\|null | Error code | Nullable, truncated 120 chars |
| `wouldModify` | boolean | Derived | True if allowed |
| `wouldWriteMemory` | boolean | Constant `false` | Reject never writes memory |
| `wouldUpdateReview` | boolean | Derived | True if allowed |
| `wouldAppendEvent` | boolean | Derived | True if allowed |
| `wouldCreateSnapshot` | boolean | Constant `false` | Always false |
| `target.memoryId` | string\|null | Constant `null` | Reject has no memory target |
| `target.category` | string | `candidate.category` | Direct |
| `target.operation` | string | Constant `"REJECT"` | Always REJECT |
| `safety.devOnly` | boolean | Constant `true` | Always true |
| `safety.productionBlocked` | boolean | Constant `true` | Always true |
| `checks[]` | array | Status validation | Transformed |
| `checks[].code` | string | Check code | `"REVIEW_IS_PENDING"` etc. |
| `checks[].status` | string | Derived | `"pass"` or `"fail"` |
| `checks[].message` | string | Human-readable | Truncated 200 chars |
| `preview.reasonPreview` | string\|null | Request `reason` | Truncated 200 chars, path redaction |
| `preview.redactedPaths` | boolean | Constant `true` | Always true |
| `effects[]` | string[] | Derived | Human-readable |
| `noEffects[]` | string[] | Constant | Always includes safety text |
| `warnings[]` | string[] | Derived | Truncated 200 chars each |

### 6.3 Forbidden Fields (Must NOT Appear in Any Response)

| Category | Examples |
|----------|---------|
| Raw candidate text | Untruncated `candidate.summary`, `candidate.title` |
| Raw message content | `raw_candidate`, `raw_message`, `full_user_message`, `full_assistant_reply` |
| Internal paths | Absolute paths (`/Users/...`, `/home/...`), `file://` URIs |
| Source metadata | `source` object (session_id_hash, message_id, channel) |
| Fingerprint | `fingerprint` (internal dedup mechanism) |
| Evaluation internals | `evaluation.reasons`, `evaluation.tag_overlap`, `evaluation.core_tag_overlap` |
| Approval/rejection objects | `approval` object, `rejection` object (raw, with timestamps) |
| Full matched memory | `matched_memory.title`, `matched_memory.category` |
| Internal metadata | `version` |
| Configuration | Internal config values, thresholds, scoring rules |
| Secrets | API keys, tokens, cookies, credentials |
| Stack traces | `traceback`, `stackTrace`, Python exceptions |
| Production paths | Any path containing `~/.hermes` |
| Full memory record | `full memory record text`, `record` field |
| System prompt | `system_prompt`, `full_prompt` |
| Model config | `model_config`, `provider_config` |

### 6.4 Truncation Rules

| Field | Max Length | Overflow |
|-------|-----------|----------|
| `preview.title` | 120 chars | Truncate with `...` |
| `preview.summaryPreview` | 200 chars | Truncate with `...` |
| `preview.reasonPreview` | 200 chars | Truncate with `...` |
| `checks[].message` | 200 chars | Truncate with `...` |
| `effects[]` item | 200 chars | Truncate with `...` |
| `noEffects[]` item | 200 chars | Truncate with `...` |
| `warnings[]` item | 200 chars | Truncate with `...` |
| `blockedReason` | 120 chars | Truncate with `...` |
| Request `reason` | 200 chars | Truncate at input validation |

### 6.5 Path Redaction Rules

Reuse existing `redact_local_paths()` from `dev_web_memory_service.py`:

| Pattern | Replacement |
|---------|-------------|
| `/Users/<segment>/...` | `[local-path]` |
| `/home/<segment>/...` | `[local-path]` |
| `C:\<segment>\...` | `[local-path]` |
| `file://...` | `[file-uri-redacted]` |
| `memory://...` | Preserved |
| `https://...` | Preserved |
| `http://...` | Preserved |

Apply to: `preview.title`, `preview.summaryPreview`, `preview.reasonPreview`, `checks[].message`, `blockedReason`.

---

## 7. Error Model

### 7.1 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `REVIEW_DRY_RUN_UNAVAILABLE` | 503 | Dry-run service unavailable (storage not accessible) |
| `REVIEW_NOT_FOUND` | 404 | Review item with given ID does not exist |
| `INVALID_REVIEW_ID` | 400 | Review ID format invalid (must match `MR-\d{8}T\d{6}-[0-9a-f]{8}`) |
| `INVALID_REVIEW_ACTION` | 400 | Action is not `approve` or `reject` |
| `INVALID_REVIEW_DRY_RUN_REQUEST` | 400 / 422 | Request body validation failed |
| `REVIEW_NOT_PENDING` | 409 | Review item status is not `pending` (dry-run blocked) |
| `REVIEW_APPROVAL_BLOCKED` | 409 | Approval would be blocked (duplicate, protected, etc.) |
| `REVIEW_REJECTION_BLOCKED` | 409 | Rejection would be blocked (already approved, etc.) |
| `REVIEW_PROTECTED_TARGET` | 409 | Target memory is P0 or permanent (approve blocked) |
| `REVIEW_DUPLICATE_BLOCKED` | 409 | Candidate became duplicate (approve blocked) |
| `UNSAFE_ENVIRONMENT` | 500 / 503 | Environment check failed |
| `INTERNAL_ERROR` | 500 | Unexpected internal error |

### 7.2 Error Response Envelope

Reuse existing Dev API error envelope from `dev_web_errors.py`:

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

### 7.3 Error Message Redaction

Error messages must NOT contain:

| Prohibited Content | Examples |
|-------------------|---------|
| Real file paths | `/Users/...`, `/home/...`, any absolute path |
| Tracebacks | Python traceback text |
| Raw review content | Full candidate summary, full evaluation |
| Secrets | API keys, tokens, cookies |
| Internal variable names | Python identifiers, module paths |
| Production paths | Any path containing `~/.hermes` |
| SQL queries | Any SQL statement |
| Exception repr | Full Python exception text |

### 7.4 Validation Rules

| Input | Validation |
|-------|------------|
| `reviewId` path param | Must match `^MR-\d{8}T\d{6}-[0-9a-f]{8}$` |
| `confirmText` body field | Max 200 chars, no control characters (reserved for 1C) |
| `reason` body field | Max 200 chars, no control characters |
| `includeDiff` body field | Boolean |

---

## 8. UI Information Architecture

### 8.1 Status / Capability Area

Existing Phase 1A status header updates:

| Element | Phase 1A | Phase 1B |
|---------|----------|----------|
| Read-only badge | Visible | Replaced with "Dry-run available" badge |
| Approve status | Disabled | "Dry-run available" |
| Reject status | Disabled | "Dry-run available" |
| Execute status | Not shown | "Disabled until Phase 1C" |

New display elements:

```
┌─────────────────────────────────────────┐
│ Review Queue                [Dry-run ●] │
│                                         │
│ Pending: 3  Approved: 2  Rejected: 1   │
│ Dry-run: available                     │
│ Execute: disabled until Phase 1C       │
└─────────────────────────────────────────┘
```

### 8.2 Detail Action Area

For each pending review item detail view:

```
┌─────────────────────────────────────────┐
│ [Approve dry-run ▾]  [Reject dry-run ▾] │
│                                         │
│ ⚠ Dry-run only. No files will be       │
│   modified.                             │
└─────────────────────────────────────────┘
```

**Button text requirements:**
- Must include "dry-run" in the label
- Must NOT include "Execute", "Confirm approve", "Confirm reject"
- Must NOT include "Approve now", "Reject now"

**Button states:**
- Pending item: enabled
- Non-pending item: disabled with tooltip explaining why
- Queue unavailable: disabled

### 8.3 Dry-Run Result Panel

When a dry-run completes:

```
┌─────────────────────────────────────────┐
│ Dry-run result: APPROVE                 │
│                                         │
│ Status: ✅ Allowed                      │
│ Would modify: Yes                       │
│ Would write memory: Yes (WRITE)         │
│ Would update review: Yes                │
│ Would append event: Yes                 │
│                                         │
│ Target: MEM-HERMES-001 (hermes, WRITE)  │
│                                         │
│ Checks:                                │
│   ✅ CATEGORY_EXISTS    — pass          │
│   ✅ DUPLICATE_CHECK    — pass          │
│   ✅ PROTECTION_CHECK   — pass          │
│                                         │
│ Preview:                                │
│   Title: "..."                         │
│   Tags: hermes, gateway                │
│                                         │
│ Effects:                                │
│   • Would create memory record          │
│   • Would mark review as approved       │
│   • Would append review_approved event  │
│                                         │
│ ┌─ Safety ────────────────────────────┐ │
│ │ ✅ No files were modified.          │ │
│ │ ✅ No events were appended.         │ │
│ │ ✅ No memory was written.           │ │
│ │ ℹ This is a dry-run preview only.  │ │
│ │ ℹ Real approve/reject is disabled  │ │
│ │   until Phase 1C.                   │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

When dry-run is blocked:

```
┌─────────────────────────────────────────┐
│ Dry-run result: APPROVE                 │
│                                         │
│ Status: ❌ Blocked                      │
│ Reason: BECAME_DUPLICATE               │
│                                         │
│ Checks:                                │
│   ✅ CATEGORY_EXISTS    — pass          │
│   ❌ BECAME_DUPLICATE   — fail          │
│                                         │
│ ┌─ Safety ────────────────────────────┐ │
│ │ ✅ No files were modified.          │ │
│ │ ℹ Approval would be blocked.        │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 8.4 Mandatory Safety Display

The dry-run result panel must always show:

1. **"No files were modified."** — Prominently displayed
2. **"This is a dry-run preview only."** — Always visible
3. **"Real approve/reject is disabled in Phase 1B."** — Phase indicator

### 8.5 Prohibited UI Elements

The following must NOT appear in Phase 1B:

| Prohibited Element | Reason |
|-------------------|--------|
| "Approve now" button | No real execution |
| "Reject now" button | No real execution |
| "Execute" button | No real execution |
| "Confirm approve" button | No real execution |
| "Confirm reject" button | No real execution |
| "Write memory" button | No memory write |
| "Run agent" button | No agent run |
| Batch approve/reject | Not supported |
| Auto-approve toggle | Not supported |

---

## 9. OpenAPI Strategy

### 9.1 Current State

- Current implemented OpenAPI: **14 paths** in `docs/webui/openapi/dev-web-api-v1.yaml`
- dev-check validates: `OpenAPI paths: 14`

### 9.2 Phase 1B-00 Rule

This task does **NOT** modify `docs/webui/openapi/dev-web-api-v1.yaml`. The proposed 2 dry-run routes exist only in this draft document.

### 9.3 Phase 1B Implementation Rule

When Phase 1B is implemented:

1. Update `docs/webui/openapi/dev-web-api-v1.yaml` to include 2 new paths:
   - `POST /api/dev/v1/reviews/{reviewId}/approve/dry-run`
   - `POST /api/dev/v1/reviews/{reviewId}/reject/dry-run`
2. Path count increases from 14 to **16**
3. Add schemas for `ApproveDryRunRequest`, `RejectDryRunRequest`, `DryRunResponse`
4. Tag: `Reviews`

### 9.4 Forbidden Route Documentation

These routes remain documented as forbidden:

```http
POST /api/dev/v1/reviews/{reviewId}/approve        ← Forbidden until Phase 1C
POST /api/dev/v1/reviews/{reviewId}/reject          ← Forbidden until Phase 1C
POST /api/dev/v1/reviews/enqueue                    ← Forbidden
PATCH /api/dev/v1/reviews/*                         ← Forbidden
DELETE /api/dev/v1/reviews/*                        ← Forbidden
```

---

## 10. Dev-Check Update Strategy

### 10.1 Current State

dev-check expects:
- OpenAPI paths: 14
- 14 allowed routes
- Forbidden routes: POST/PATCH/DELETE to /reviews/*

### 10.2 Phase 1B Implementation Updates

When Phase 1B is implemented:

| Check | Current (1A) | After 1B |
|-------|-------------|----------|
| OpenAPI path count | 14 | 16 |
| ALLOWED_ROUTES | + 3 review GET routes | + 2 dry-run POST routes |
| Forbidden POST routes | All POST /reviews/* | POST /reviews/{id}/approve (without /dry-run), POST /reviews/{id}/reject (without /dry-run), POST /reviews/enqueue |

### 10.3 New Check Requirements

dev-check must distinguish:

| Route Pattern | Allowed in 1B | Forbidden |
|--------------|---------------|-----------|
| `POST /reviews/{id}/approve/dry-run` | ✅ Allowed | — |
| `POST /reviews/{id}/reject/dry-run` | ✅ Allowed | — |
| `POST /reviews/{id}/approve` | — | ❌ Forbidden (Phase 1C) |
| `POST /reviews/{id}/reject` | — | ❌ Forbidden (Phase 1C) |
| `POST /reviews/enqueue` | — | ❌ Forbidden |
| `PATCH /reviews/*` | — | ❌ Forbidden |
| `DELETE /reviews/*` | — | ❌ Forbidden |

dev-check output must clearly state:
- "Dry-run routes: 2 (approve/dry-run, reject/dry-run)"
- "Execute routes: 0 (approve, reject remain forbidden until Phase 1C)"
- "WebUI governance: no execute routes registered"

---

## 11. Playwright Smoke Update Strategy

### 11.1 Current State

Smoke tests at `apps/hermes-dev-webui/tests/smoke/phase-0e-03-smoke.spec.ts`:
- 4 viewports × 5 themes = 20 combinations
- Forbidden patterns allow GET /reviews but forbid POST/PATCH/DELETE

### 11.2 Phase 1B Implementation Updates

When Phase 1B is implemented, add smoke checks:

1. **Dry-run buttons visible** — "Approve dry-run" and "Reject dry-run" buttons present for pending items
2. **Dry-run button click** — Triggers POST /approve/dry-run or POST /reject/dry-run
3. **No execute requests** — Verify no POST /approve or POST /reject (without /dry-run) is sent
4. **No enqueue requests** — Verify no POST /reviews/enqueue is sent
5. **Dry-run result panel** — Shows "No files were modified" text
6. **No memory file changes** — Verify no memory/indexes, memory/records changes
7. **No review file changes** — Verify no memory/reviews/items changes
8. **Safety badge** — "Dry-run available" visible
9. **Execute disabled** — No "Approve now" / "Reject now" / "Execute" buttons
10. **Five themes render** — Dry-run controls render correctly in all themes
11. **Four viewports** — No overflow at mobile/tablet/desktop/wide breakpoints

### 11.3 Forbidden Pattern Update

Update smoke spec forbidden patterns:

- **Allow:** `POST.*\/reviews\/.*\/approve\/dry-run` (new)
- **Allow:** `POST.*\/reviews\/.*\/reject\/dry-run` (new)
- **Keep forbidden:** `POST.*\/reviews\/(?!.*\/dry-run)` (POST to reviews without dry-run)
- **Keep forbidden:** `POST.*\/reviews\/enqueue`
- **Keep forbidden:** `PATCH.*\/reviews`
- **Keep forbidden:** `DELETE.*\/reviews`

---

## 12. Side-Effect Hash Validation Strategy

### 12.1 Phase 1B Dry-Run Guarantee

Phase 1B dry-run must leave **zero side effects**. The following must remain **completely unchanged** after any dry-run operation:

| Path | What to Verify |
|------|----------------|
| `state.db` | SHA-256 unchanged |
| `MEMORY.md` | SHA-256 unchanged |
| `memory/indexes/` | All files SHA-256 unchanged |
| `memory/records/` | All files SHA-256 unchanged |
| `memory/events.jsonl` | SHA-256 unchanged |
| `memory/snapshots/` | All files SHA-256 unchanged |
| `memory/reviews/items/*.json` | All files SHA-256 unchanged |
| `memory/reviews/events.jsonl` | SHA-256 unchanged |

### 12.2 Specific Assertions

Dry-run calls must NOT:

- Change `occurrence_count` on any review item
- Change `status` on any review item
- Write `last_error` on any review item
- Write `approval` or `rejection` fields on any review item
- Create new files in `memory/reviews/items/`
- Append to `memory/reviews/events.jsonl`
- Modify `memory/indexes/` or `memory/records/`
- Modify `memory/events.jsonl`

### 12.3 Validation Method

```bash
# Before Phase 1B testing
find /Users/huangruibang/Code/hermes-home-dev/memory -type f | sort | xargs shasum > /tmp/pre-dryrun-hash.txt

# After dry-run operations
find /Users/huangruibang/Code/hermes-home-dev/memory -type f | sort | xargs shasum > /tmp/post-dryrun-hash.txt

# Compare
diff /tmp/pre-dryrun-hash.txt /tmp/post-dryrun-hash.txt
# Expected: no differences
```

### 12.4 Blocking Condition

If any hash changes after a dry-run call:

- **Phase 1B implementation has failed.**
- The dry-run is not truly side-effect-free.
- Root cause must be identified and fixed before proceeding.

---

## 13. Acceptance Criteria

Phase 1B-00 completes when:

1. ✅ Review approve real side effects audited (5 files modified, memory write triggered)
2. ✅ Review reject real side effects audited (2 files modified, no memory write)
3. ✅ Dry-run vs execute boundary clearly defined
4. ✅ Phase 1B dry-run API draft frozen (2 routes with request/response schemas)
5. ✅ Approve dry-run DTO whitelist defined (28+ fields)
6. ✅ Reject dry-run DTO whitelist defined (20+ fields)
7. ✅ Forbidden fields documented (raw content, paths, secrets, internals)
8. ✅ Path/secret/raw content redaction rules defined
9. ✅ Truncation rules defined
10. ✅ Error model frozen (12 error codes, envelope, redaction)
11. ✅ Frontend information architecture frozen (dry-run controls, result panel, safety display)
12. ✅ OpenAPI strategy documented: no change to 14-path contract in this task
13. ✅ dev-check update strategy documented (14 → 16 paths, dry-run vs execute distinction)
14. ✅ Playwright smoke update strategy documented (11 new checks)
15. ✅ Side-effect hash validation strategy documented (SHA-256 before/after)
16. ✅ No API implemented
17. ✅ No business code modified
18. ✅ No memory files modified
19. ✅ No review queue files modified
20. ✅ memory-check PASS
21. ✅ dev-check PASS
22. ✅ compileall PASS
23. ✅ Document produced
24. ✅ Implementation plan updated
25. ✅ Local commit created
26. ✅ Not pushed
27. ✅ Final worktree clean
28. ✅ Production environment unaffected

---

## 14. Next Task

**Phase 1B: Review Queue Approve/Reject Dry-Run Implementation**

This task does NOT automatically start Phase 1B.
