# Phase 1C-00: Review Queue Approve/Reject Dev-Only Execute Scope & Safety Boundary Freeze

**Date:** 2026-06-09
**Status:** Completed ✅
**Depends on:** Phase 1B (commit `1cc4148db`)
**Governance scope:** `docs/webui/phase-1-00-planning-and-scope.md`
**Predecessor:** `docs/webui/phase-1b-00-review-queue-dry-run-scope.md`

---

## 1. Status

Phase 1C-00 is a **planning and safety boundary freeze** task. It does not implement any execute API, modify any business code, or change any runtime behavior. It audits the real approve/reject write effects, defines the execute scope, and freezes safety boundaries that Phase 1C implementation must satisfy.

---

## 2. Background

Phase 1A delivered a read-only Review Queue panel with 3 GET endpoints. Phase 1B added dry-run preview of approve/reject with 2 POST endpoints. Phase 1C is the next step: enabling **real** approve/reject execution in the dev-only environment.

This is the first phase with real write operations. It requires strict safety boundaries documented in this scope freeze.

---

## 3. Current Phase 1B Baseline

### 3.1 Implemented Routes (16 paths)

| Method | Path | Phase |
|--------|------|-------|
| GET | `/api/dev/v1/status` | 0E |
| GET | `/api/dev/v1/files/status` | 0E |
| GET | `/api/dev/v1/sessions` | 0E |
| GET | `/api/dev/v1/sessions/{sessionId}` | 0E |
| GET | `/api/dev/v1/sessions/{sessionId}/messages` | 0E |
| GET | `/api/dev/v1/memory/status` | 0E |
| GET | `/api/dev/v1/memory/categories` | 0E |
| GET | `/api/dev/v1/memory/items` | 0E |
| GET | `/api/dev/v1/memory/items/{memoryId}` | 0E |
| POST | `/api/dev/v1/context/preview` | 0E |
| GET | `/api/dev/v1/agent/status` | 0E |
| GET | `/api/dev/v1/reviews/status` | 1A |
| GET | `/api/dev/v1/reviews` | 1A |
| GET | `/api/dev/v1/reviews/{reviewId}` | 1A |
| POST | `/api/dev/v1/reviews/{reviewId}/approve/dry-run` | 1B |
| POST | `/api/dev/v1/reviews/{reviewId}/reject/dry-run` | 1B |

### 3.2 Current Capabilities

- **Read-only:** All 16 routes are read-only or dry-run only
- **Dry-run available:** Approve and reject preview available
- **Execute available:** None
- **Write capability:** None
- **Kill switch:** Not needed (no execute routes exist)

### 3.3 Current Safety Flags (from `get_status()` response)

```
readOnly: true
queueEnabled: false
writeEnabled: false
approveEnabled: false
rejectEnabled: false
enqueueEnabled: false
dryRunEnabled: true
```

---

## 4. Approve/Reject Write-Effect Audit

### 4.1 Source Files Audited

| File | Purpose |
|------|---------|
| `agent/memory_review_queue.py` | Review queue storage, approve/reject/enqueue logic |
| `agent/runtime_memory_writer.py` | Memory evaluation and auto-write |
| `hermes_cli/memory_router.py` | Memory CRUD (create, update, archive, index, events) |
| `hermes_cli/dev_web_review_service.py` | Dev WebUI review query service (read-only + dry-run) |
| `hermes_cli/dev_web_api.py` | Dev WebUI API routes |
| `hermes_cli/dev_web_schemas.py` | Dev WebUI DTOs |
| `hermes_cli/dev_web_errors.py` | Dev WebUI error codes |

### 4.2 Approve Write Effects (WRITE action)

When `approve_review_item(review_id, action="WRITE", dry_run=False)` is called:

**Step 1: Acquire lock** (`review_queue_lock`)
- Acquires `_THREAD_LOCK` (`threading.RLock`) — intra-process
- Acquires `fcntl.LOCK_EX` on `.queue.lock` file — inter-process (Unix only)

**Step 2: Load & validate**
- Reads `memory/reviews/items/{reviewId}.json`
- Checks status is PENDING
- Calls `revalidate_review_approval()` — read-only validation

**Step 3: Execute memory write** (inside lock)
- Calls `allocate_memory_id()` — reads all indexes to find next ID
- Calls `create_memory_item()` which writes:

| # | File Written | Description |
|---|-------------|-------------|
| 1 | `memory/snapshots/INDEX-{category}-{timestamp}.md` | Index backup before modification |
| 2 | `memory/indexes/{category}.md` | Category index with new memory entry |
| 3 | `memory/records/{category}/{id}.md` | New memory record file |
| 4 | `memory/events.jsonl` | `memory_create` event appended |

**Step 4: Update review status** (inside lock, after memory write)
- Writes to:

| # | File Written | Description |
|---|-------------|-------------|
| 5 | `memory/reviews/items/{reviewId}.json` | Status→APPROVED, approval object, last_error cleared |
| 6 | `memory/reviews/events.jsonl` | `review_approved` event appended |

**Total files written: 6**

**If memory write fails (step 3):**
- Writes `last_error` to review item JSON (file #5)
- Appends `review_approval_failed` event (file #6)
- Re-raises the exception
- Review stays PENDING but has error info

### 4.3 Approve Write Effects (UPDATE action)

Same as WRITE, but `update_memory_item()` is called instead of `create_memory_item()`:

| # | File Written | Description |
|---|-------------|-------------|
| 1 | `memory/snapshots/INDEX-{category}-{timestamp}.md` | Index backup |
| 2 | `memory/snapshots/RECORD-{memoryId}-{timestamp}.md` | Record backup |
| 3 | `memory/indexes/{category}.md` | Updated category index |
| 4 | `memory/records/{category}/{id}.md` | Updated memory record |
| 5 | `memory/events.jsonl` | `memory_update` event appended |
| 6 | `memory/reviews/items/{reviewId}.json` | Status→APPROVED, approval object |
| 7 | `memory/reviews/events.jsonl` | `review_approved` event appended |

**Total files written: 7**

### 4.4 Reject Write Effects

When `reject_review_item(review_id, reason)` is called:

**Step 1: Acquire lock** (`review_queue_lock`)

**Step 2: Load & validate**
- Reads review JSON
- Checks status is PENDING (cannot reject APPROVED items)

**Step 3: Update review status** (inside lock)

| # | File Written | Description |
|---|-------------|-------------|
| 1 | `memory/reviews/items/{reviewId}.json` | Status→REJECTED, rejection object with timestamp and reason |
| 2 | `memory/reviews/events.jsonl` | `review_rejected` event appended |

**Total files written: 2**

**Reject never writes memory files.**

### 4.5 Indirect Write Effects (via memory_router)

The following functions from `hermes_cli/memory_router.py` are called during approve:

| Function | Called by | Writes |
|----------|-----------|--------|
| `ensure_memory_scaffold()` | `create_memory_item`, `update_memory_item` | Creates directories, empty index files |
| `allocate_memory_id()` | `approve_review_item` | None (read-only) |
| `create_memory_item()` | `approve_review_item` (WRITE) | Index backup, index file, record file, event |
| `update_memory_item()` | `approve_review_item` (UPDATE) | Index backup, record backup, index file, record file, event |
| `backup_file()` | `create_memory_item`, `update_memory_item` | Snapshot file |
| `write_index_items()` | `create_memory_item`, `update_memory_item` | Index MD file |
| `append_event()` | `create_memory_item`, `update_memory_item` | events.jsonl |

### 4.6 `_hermes_home_scope()` Mechanism

`approve_review_item()` uses `_hermes_home_scope(home)` (line 571) to set the HERMES_HOME override before calling memory write functions. This ensures `create_memory_item()` and `update_memory_item()` write to the correct (dev) home directory.

This mechanism is critical for dev-only execution. Phase 1C must verify it works correctly with the dev home path.

---

## 5. Failure Modes & Half-Completion Audit

### 5.1 Failure Scenarios

| Scenario | Files Written | Recovery |
|----------|--------------|----------|
| Memory record write succeeds, review JSON write fails | 4 memory files, 1 backup | Orphaned memory record exists but review still PENDING |
| Review JSON write succeeds, event append fails | 4 memory files, review APPROVED | Review shows approved but audit trail incomplete |
| Event append succeeds, review JSON write fails | 4 memory files, event logged | Review still PENDING, retry creates duplicate memory |
| Process killed mid-write | Partial files | Inconsistent state, may need manual cleanup |
| Category archived between dry-run and execute | Memory write fails validation | Error written to review, stays PENDING |
| Duplicate created between dry-run and execute | Validation catches duplicate | May auto-reject or error, stays PENDING |

### 5.2 Atomicity Analysis

**No atomic transaction boundary exists.** The approve operation writes to 6–7 files sequentially with no rollback mechanism.

**Partial ordering:**
1. Memory write first (create/update)
2. Review status update second
3. Review event append third

If step 1 succeeds but step 2 fails:
- Memory record exists but review still shows PENDING
- Retrying the approve will attempt to create a **new** memory record (duplicate)
- The original memory record is orphaned

If step 2 succeeds but step 3 fails:
- Review shows APPROVED
- Audit trail in events.jsonl is incomplete
- Less critical but creates a gap in audit history

**No compare-and-set or version check** on the review item between dry-run and execute.

### 5.3 Lock & Concurrency Analysis

**Lock mechanism:**
- `_THREAD_LOCK = threading.RLock()` — intra-process thread safety
- `fcntl.flock(LOCK_EX)` on `memory/reviews/.queue.lock` — inter-process file lock (Unix only)

**Lock scope in `approve_review_item()`:**
```
with review_queue_lock(paths):    # Acquires both locks
    item = load_review_item(...)   # Read
    if item.status != PENDING:     # Check
        raise ValueError(...)
    validation = revalidate(...)   # Read-only
    create_memory_item(...)        # Write (inside lock)
    item.status = APPROVED
    atomic_write_review_json(...)  # Write (inside lock)
    append_review_event(...)       # Write (inside lock)
                                    # Releases both locks
```

**Lock scope in `reject_review_item()`:**
```
with review_queue_lock(paths):    # Acquires both locks
    item = load_review_item(...)   # Read
    if item.status != PENDING:     # Check
        raise ValueError(...)
    item.status = REJECTED
    atomic_write_review_json(...)  # Write (inside lock)
    append_review_event(...)       # Write (inside lock)
                                    # Releases both locks
```

**Lock observations:**
- ✅ Both approve and reject are fully enclosed in the lock
- ✅ Status check happens inside the lock (no TOCTOU between check and write)
- ✅ Double-approve returns early with `already_approved: True` (line 578-579)
- ✅ Approved items cannot be rejected (line 443-444)
- ⚠️ No precondition on `updatedAt` or `fingerprint` — dry-run preview cannot guarantee item unchanged at execute time
- ⚠️ Lock is only effective within a single host (no distributed locking)
- ⚠️ `fcntl` is Unix-only — Windows has no inter-process lock

### 5.4 Race Condition Scenarios

| Scenario | Protection | Risk |
|----------|-----------|------|
| Concurrent approve of same review | Lock + status check | ✅ Safe — second approve sees APPROVED |
| Approve after reject | Lock + status check | ✅ Safe — sees REJECTED, raises error |
| Concurrent approve + CLI approve | `fcntl` file lock | ⚠️ Safe on Unix, no protection on Windows |
| Dry-run preview, item changes, then execute | No precondition | ❌ TOCTOU — execute may act on stale data |
| Process killed during approve | No rollback | ❌ Partial state possible |

---

## 6. Phase 1C Execute Scope

### 6.1 Proposed Execute Routes

Phase 1C adds 2 execute POST routes:

```http
POST /api/dev/v1/reviews/{reviewId}/approve/execute
POST /api/dev/v1/reviews/{reviewId}/reject/execute
```

**Route naming rationale:**
- Must explicitly distinguish from dry-run (`/execute` suffix)
- Must never use bare `/approve` or `/reject` — avoids accidental execution
- Follows the Phase 1B pattern (`/approve/dry-run` → `/approve/execute`)

### 6.2 Non-Goals

Phase 1C does NOT implement:
- Real enqueue operations
- Batch approve/reject
- Auto-approve
- Memory write/update/archive API
- Agent run or tool execution
- SSE streaming
- WebSocket
- File browsing/upload/delete
- Gateway control
- Production execution

### 6.3 Forbidden Routes (Permanently)

```http
POST /api/dev/v1/reviews/{reviewId}/approve         (bare, no /execute suffix)
POST /api/dev/v1/reviews/{reviewId}/reject           (bare, no /execute suffix)
POST /api/dev/v1/reviews/enqueue
POST /api/dev/v1/reviews
PATCH /api/dev/v1/reviews/*
DELETE /api/dev/v1/reviews/*
```

### 6.4 Write Capability

| Action | Writes Memory | Writes Review | Writes Event |
|--------|--------------|---------------|--------------|
| Approve execute (WRITE) | ✅ Creates memory record | ✅ Status→APPROVED | ✅ Two events |
| Approve execute (UPDATE) | ✅ Updates memory record | ✅ Status→APPROVED | ✅ Two events |
| Reject execute | ❌ No memory write | ✅ Status→REJECTED | ✅ One event |

### 6.5 Allowed Side Effects (dev-home only)

- Write to `memory/reviews/items/` — review JSON status update
- Write to `memory/reviews/events.jsonl` — audit event append
- Write to `memory/indexes/` — category index update (approve only)
- Write to `memory/records/` — memory record create/update (approve only)
- Write to `memory/events.jsonl` — memory event append (approve only)
- Write to `memory/snapshots/` — backup before modification (approve only)

### 6.6 Forbidden Side Effects

- Write to production home (`~/.hermes/`)
- Modify production state.db
- Modify production Gateway
- Execute shell commands
- Run Agent
- Call LLM
- Access network
- Modify source code files

---

## 7. Proposed Execute API Contracts

### 7.1 Approve Execute Request

```http
POST /api/dev/v1/reviews/{reviewId}/approve/execute
Content-Type: application/json
```

```json
{
  "confirmationText": "APPROVE",
  "expectedAction": "APPROVE",
  "reviewUpdatedAt": "2026-06-09T14:30:00+08:00",
  "dryRunPreviewed": true,
  "acknowledgedEffects": [
    "WRITE_MEMORY",
    "UPDATE_REVIEW",
    "APPEND_REVIEW_EVENT"
  ]
}
```

**Required fields:**

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `confirmationText` | string | Must equal `"APPROVE"` exactly | Explicit confirmation |
| `expectedAction` | string | Must equal `"APPROVE"` | Prevents action confusion |
| `reviewUpdatedAt` | string | ISO 8601, must match current `updated_at` | TOCTOU protection |
| `dryRunPreviewed` | boolean | Must be `true` | Proves dry-run was performed first |
| `acknowledgedEffects` | string[] | Must include all applicable effects | User awareness of consequences |

### 7.2 Reject Execute Request

```http
POST /api/dev/v1/reviews/{reviewId}/reject/execute
Content-Type: application/json
```

```json
{
  "confirmationText": "REJECT",
  "expectedAction": "REJECT",
  "reason": "Duplicate of existing memory",
  "reviewUpdatedAt": "2026-06-09T14:30:00+08:00",
  "dryRunPreviewed": true,
  "acknowledgedEffects": [
    "UPDATE_REVIEW",
    "APPEND_REVIEW_EVENT"
  ]
}
```

**Required fields:**

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `confirmationText` | string | Must equal `"REJECT"` exactly | Explicit confirmation |
| `expectedAction` | string | Must equal `"REJECT"` | Prevents action confusion |
| `reason` | string | Optional, max 500 chars, path-redacted | Rejection reason |
| `reviewUpdatedAt` | string | ISO 8601, must match current `updated_at` | TOCTOU protection |
| `dryRunPreviewed` | boolean | Must be `true` | Proves dry-run was performed first |
| `acknowledgedEffects` | string[] | Must include all applicable effects | User awareness |

### 7.3 Execute Response (Success)

```json
{
  "data": {
    "reviewId": "MR-20260609T143000-abc12345",
    "executed": true,
    "action": "APPROVE",
    "statusBefore": "PENDING",
    "statusAfter": "APPROVED",
    "memoryChanged": true,
    "reviewChanged": true,
    "eventAppended": true,
    "target": {
      "memoryId": "MEM-HERMES-004",
      "category": "hermes",
      "operation": "WRITE"
    },
    "audit": {
      "actor": "dev-webui",
      "timestamp": "2026-06-09T14:31:00+08:00",
      "devOnly": true
    },
    "warnings": []
  },
  "meta": {
    "requestId": "...",
    "timestamp": "..."
  }
}
```

### 7.4 Execute Response (Rejected due to precondition failure)

```json
{
  "error": {
    "code": "REVIEW_PRECONDITION_FAILED",
    "message": "Review item was modified since dry-run preview. Please re-run dry-run.",
    "details": "updated_at mismatch"
  },
  "requestId": "...",
  "timestamp": "..."
}
```

### 7.5 Forbidden Response Fields

The execute response must NEVER include:
- Raw candidate content
- Full memory record text
- Full prompt or system message
- Fingerprint hash
- Absolute file paths
- Secrets, tokens, API keys
- Python traceback
- Source objects
- Evaluation raw data

---

## 8. Confirmation Model

### 8.1 Mandatory Confirmation Steps

Phase 1C execute requires ALL of the following:

1. **Explicit text confirmation** — `confirmationText` must exactly match `APPROVE` or `REJECT`
2. **Action match** — `expectedAction` must match the route being called
3. **Dry-run first** — `dryRunPreviewed` must be `true`
4. **Effects acknowledgment** — `acknowledgedEffects` must list all applicable effects
5. **Precondition check** — `reviewUpdatedAt` must match the current item's `updated_at`
6. **Status check** — Review must be PENDING
7. **Revalidation** — Full `revalidate_review_approval()` must pass (approve only)

### 8.2 Server-Side Revalidation (on execute)

Before executing, the server must re-run all validation:

1. Review item exists
2. Review status is PENDING
3. `reviewUpdatedAt` matches current `updated_at`
4. Category exists and is active
5. No duplicate memory found (approve only)
6. Target memory still valid (UPDATE action only)
7. Target not P0 protected
8. Target not permanent protected
9. Kill switch is enabled

### 8.3 Confirmation Flow Diagram

```
User clicks "Approve execute" button
  → Frontend shows confirmation dialog
    → User types "APPROVE" in input
    → User checks acknowledged effects checkboxes
    → Frontend calls POST /approve/execute with all required fields
      → Backend validates confirmationText
      → Backend validates kill switch enabled
      → Backend validates dev-only environment
      → Backend loads review item
      → Backend checks reviewUpdatedAt precondition
      → Backend checks status is PENDING
      → Backend runs revalidate_review_approval
      → If any check fails → 409 or 422 error
      → If all pass → execute approve_review_item()
      → Return execute result
```

---

## 9. Dry-Run-First Requirement

### 9.1 Requirement

Phase 1C execute routes must require that a dry-run was performed before allowing execution.

### 9.2 Implementation Options

**Option A: `dryRunPreviewed` boolean flag (Recommended)**
- Simplest to implement
- Client asserts they viewed dry-run results
- Server can optionally verify by checking dry-run result existence

**Option B: `dryRunToken` cryptographic token**
- Dry-run response includes a one-time token
- Execute request must include this token
- Server validates token freshness
- More secure but more complex

**Frozen decision: Option A for Phase 1C initial implementation.**
Option B may be considered in a future refinement.

---

## 10. Kill Switch Strategy

### 10.1 Default State

Execute routes must be **disabled by default**. The kill switch must fail closed.

### 10.2 Proposed Mechanism

Configuration-based kill switch in Dev WebUI config:

```python
# In hermes_cli/dev_web_config.py or equivalent
REVIEW_EXECUTE_ENABLED = False  # Default: disabled

# Or via environment variable
HERMES_DEV_REVIEW_EXECUTE = "false"  # Default: disabled
```

### 10.3 Kill Switch Behavior

| Kill Switch State | Execute Route Behavior |
|-------------------|----------------------|
| Disabled (default) | Returns 403 with `REVIEW_EXECUTE_DISABLED` |
| Enabled | Proceeds with full validation chain |

### 10.4 Kill Switch Verification

`dev-check` must verify:
- Kill switch exists
- Kill switch is disabled by default
- Kill switch can be toggled
- Kill switch state is reported in `/reviews/status`

### 10.5 Kill Switch Response

When disabled:

```json
{
  "error": {
    "code": "REVIEW_EXECUTE_DISABLED",
    "message": "Review execute is disabled. Enable with HERMES_DEV_REVIEW_EXECUTE=true.",
    "details": "kill_switch_disabled"
  },
  "requestId": "...",
  "timestamp": "..."
}
```

---

## 11. Dev-Only Environment Guard

### 11.1 Requirement

Execute routes must only operate in the development environment. Production execution is permanently prohibited.

### 11.2 Guards

| Guard | Check | Failure Behavior |
|-------|-------|-----------------|
| `enforce_dev_environment()` | Source root == dev source root | RuntimeError — refuse to start |
| `HERMES_HOME` check | == `/Users/huangruibang/Code/hermes-home-dev` | RuntimeError — refuse request |
| Production path check | `!= /Users/huangruibang/.hermes` | 403 error |
| `state.db` check | Not production state.db | 403 error |

### 11.3 Status Reporting

`/reviews/status` must report execute capability:

```json
{
  "executeEnabled": false,
  "killSwitchActive": true,
  "devOnly": true,
  "productionBlocked": true
}
```

---

## 12. Audit Trail

### 12.1 Required Audit Fields

Each execute operation must record:

| Field | Value | Notes |
|-------|-------|-------|
| `actor` | `"dev-webui"` | Fixed |
| `action` | `"APPROVE_EXECUTE"` or `"REJECT_EXECUTE"` | Distinguishes from dry-run |
| `reviewId` | `MR-...` | Target review |
| `targetCategory` | Category name | Memory category affected |
| `targetMemoryId` | `MEM-...` or null | Memory record affected |
| `timestamp` | ISO 8601 | When executed |
| `requestId` | UUID | Correlates with API request |
| `result` | `"success"` or `"failed"` | Outcome |
| `devOnly` | `true` | Always true |

### 12.2 Forbidden Audit Fields

Audit records must NEVER include:
- Full candidate content
- Full user message
- Full assistant reply
- Secrets, tokens, API keys
- Absolute file paths
- Raw source objects
- Python traceback

### 12.3 Audit Storage

Audit events are appended to `memory/reviews/events.jsonl` via the existing `append_review_event()` mechanism. No separate audit table or database is needed for Phase 1C.

---

## 13. Revalidation Strategy

### 13.1 Pre-Execute Revalidation

Before executing, the server must re-run all validation that was performed during dry-run:

| Check | Function | Scope |
|-------|----------|-------|
| Review exists | `load_review_item()` | Read |
| Status is PENDING | Status check | Read |
| `reviewUpdatedAt` matches | Precondition check | Read |
| Category valid | `parse_root()` | Read |
| No duplicate | `find_best_memory_match()` | Read |
| Not protected | `is_protected_memory()` | Read |
| Kill switch enabled | Config check | Read |
| Dev-only environment | `enforce_dev_environment()` | Read |

### 13.2 Revalidation Failure

If revalidation fails:
- Do NOT execute
- Return 409 with specific error code
- Optionally update review item's `last_error` field
- Append `review_approval_failed` or `review_rejection_failed` event

---

## 14. Concurrency Strategy

### 14.1 Precondition-Based Protection

Phase 1C requires `reviewUpdatedAt` in the execute request. The server compares this with the current item's `updated_at`. If they differ, the execute is rejected with `REVIEW_PRECONDITION_FAILED`.

This prevents:
- TOCTOU between dry-run preview and execute
- Concurrent modification from CLI or other clients
- Stale dry-run results being used for execution

### 14.2 Lock-Based Protection

The existing `review_queue_lock` provides:
- Thread safety within a single process (`threading.RLock`)
- Process safety across processes (`fcntl.LOCK_EX`)

Phase 1C execute routes must use the same lock mechanism by calling `approve_review_item()` or `reject_review_item()` from `agent/memory_review_queue.py`.

### 14.3 Idempotency

- Double-approve returns the existing approved item with `already_approved: true`
- Double-reject returns the existing rejected item with `changed: false`
- These are handled by the existing functions

### 14.4 Single-Generation Constraint

At most one execute operation may run per review item at any time. The `review_queue_lock` already enforces this.

---

## 15. Rollback / Recovery Strategy

### 15.1 Known Failure Scenarios

| Scenario | Impact | Recovery |
|----------|--------|----------|
| Memory write succeeds, review JSON write fails | Orphaned memory record, review still PENDING | Manual: delete orphaned record, or retry approve (creates new record) |
| Review JSON write succeeds, event append fails | Review APPROVED, incomplete audit | Low impact — audit trail gap only |
| Process killed during approve | Partial files | Manual: check file state, clean up |
| `reviewUpdatedAt` mismatch | Execute rejected | User re-runs dry-run and retries |

### 15.2 Phase 1C Strategy

For Phase 1C initial implementation:

1. **Use existing lock** — `review_queue_lock` covers the entire operation
2. **No automatic rollback** — Memory records once written are not automatically rolled back
3. **Error recording** — Failed operations write `last_error` to review item
4. **Event logging** — All outcomes (success and failure) append events
5. **Pre-execute backup** — `create_memory_item()` and `update_memory_item()` already create backups in `memory/snapshots/`
6. **Dev-only safety net** — Failures only affect dev-home, not production

### 15.3 Recommendations for Phase 1C Implementation

1. Execute the review status update BEFORE the memory write (reverse of current order) — if status update fails, no memory was written; if memory write fails, review can be marked with error
2. Consider adding a `pre-execute snapshot` of the review item before modification
3. For initial release, accept that partial failures require manual intervention in dev-home

---

## 16. Frontend Information Architecture

### 16.1 Execute Capability Area

The Review Panel detail view must display:

```
┌─────────────────────────────────────────────┐
│ Execute Controls                             │
│ ────────────────────                         │
│ ✅ Dry-run completed                         │
│ ⚠️ Execute: disabled (kill switch active)    │
│ 📋 Dev-only execution                        │
│ 🔒 Production permanently blocked            │
│                                              │
│ Effects preview:                             │
│ • Would create memory record (WRITE)         │
│ • Would mark review as approved              │
│ • Would append review event                  │
│                                              │
│ [Approve Execute]  [Reject Execute]          │
│                                              │
│ ⚠️ These buttons will modify dev memory      │
│    files. This cannot be undone.             │
└─────────────────────────────────────────────┘
```

### 16.2 Execute Button Requirements

- **Default state:** Disabled
- **Enable condition:** Dry-run completed + kill switch enabled + review is PENDING
- **Label:** Must include "execute" explicitly (e.g., "Approve execute", "Reject execute")
- **Click action:** Shows confirmation dialog (see 16.3)
- **Disabled tooltip:** Shows reason (kill switch, not PENDING, dry-run not done)

### 16.3 Confirmation Dialog

```
┌─────────────────────────────────────────────┐
│ ⚠️ Confirm Approve Execute                  │
│                                              │
│ This will:                                   │
│ • Write a new memory record to dev-home      │
│ • Mark review MR-xxx as APPROVED             │
│ • Append an audit event                      │
│                                              │
│ Type APPROVE to confirm:                     │
│ [________________________________]           │
│                                              │
│ Acknowledged effects:                        │
│ ☑ WRITE_MEMORY — Creates memory record       │
│ ☑ UPDATE_REVIEW — Changes review status      │
│ ☑ APPEND_REVIEW_EVENT — Logs audit event     │
│                                              │
│ This operation cannot be undone.             │
│                                              │
│              [Cancel]  [Execute Approve]     │
└─────────────────────────────────────────────┘
```

### 16.4 Prohibited UI Elements

The frontend must NEVER show:
- "Approve now" / "Reject now" (implies instant action)
- One-click approve/reject
- Auto-approve / Auto-reject
- Batch approve / Batch reject
- "Skip dry-run" / "Skip confirmation"

### 16.5 Post-Execute Success State

After successful execution, the UI must:
- Refresh review list (status changed from PENDING to APPROVED/REJECTED)
- Refresh review detail (show new status and approval/rejection info)
- Display execute result (memoryChanged, reviewChanged, eventAppended)
- Disable execute buttons (item no longer PENDING)
- Show success message with audit info

### 16.6 Accessibility

- Confirmation dialog must trap focus
- Keyboard navigation must be supported
- Screen reader must announce action, effects, and result
- `prefers-reduced-motion` must be respected for success/error animations

---

## 17. Error Model

### 17.1 Execute-Specific Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `REVIEW_EXECUTE_DISABLED` | 403 | Kill switch is active, execute not allowed |
| `REVIEW_PRECONDITION_FAILED` | 409 | `reviewUpdatedAt` mismatch — item was modified |
| `REVIEW_NOT_PENDING` | 409 | Review is not PENDING (already approved/rejected/failed) |
| `REVIEW_APPROVAL_BLOCKED` | 409 | Approval revalidation failed (duplicate, protected, etc.) |
| `REVIEW_REJECTION_BLOCKED` | 409 | Rejection blocked (already approved) |
| `INVALID_CONFIRMATION` | 422 | `confirmationText` does not match expected value |
| `MISSING_DRY_RUN` | 422 | `dryRunPreviewed` is false or missing |
| `INVALID_ACKNOWLEDGED_EFFECTS` | 422 | Missing required acknowledged effects |
| `REVIEW_EXECUTE_ERROR` | 500 | Unexpected error during execution |

### 17.2 Existing Error Codes (Carried Forward)

All Phase 1A and 1B error codes remain valid:
- `REVIEW_QUEUE_UNAVAILABLE`, `REVIEW_NOT_FOUND`, `INVALID_REVIEW_ID`
- `INVALID_REVIEW_QUERY`, `REVIEW_STORE_ERROR`
- `REVIEW_DRY_RUN_UNAVAILABLE`

### 17.3 Error Response Format

Follows the existing unified error envelope:

```json
{
  "error": {
    "code": "REVIEW_PRECONDITION_FAILED",
    "message": "Review item was modified since dry-run preview.",
    "details": "updated_at: expected 2026-..., got 2026-..."
  },
  "requestId": "...",
  "timestamp": "..."
}
```

### 17.4 Forbidden Error Message Content

Error messages must never include:
- Absolute file paths
- Python traceback
- Source code snippets
- Raw candidate content
- Memory record content
- Secrets, tokens, API keys
- Internal function names
- Database queries

---

## 18. OpenAPI Strategy

### 18.1 Current State (Phase 1B)

- **16 paths** in OpenAPI spec
- Execute routes do not exist
- Forbidden routes do not exist

### 18.2 Phase 1C-00 (This Document)

- **No changes** to OpenAPI spec
- 16 paths remain unchanged

### 18.3 Phase 1C Implementation Target

- **18 paths** after Phase 1C
- 2 new execute routes added
- Forbidden routes still absent

### 18.4 New Routes (Phase 1C Implementation Only)

| Method | Path | Status Codes |
|--------|------|-------------|
| POST | `/api/dev/v1/reviews/{reviewId}/approve/execute` | 200, 400, 403, 404, 409, 422, 500, 503 |
| POST | `/api/dev/v1/reviews/{reviewId}/reject/execute` | 200, 400, 403, 404, 409, 422, 500, 503 |

---

## 19. dev-check Strategy

### 19.1 Phase 1C-00 (This Document)

No changes to dev-check. 16-path validation remains.

### 19.2 Phase 1C Implementation Target

dev-check must verify:

| Check | Expected |
|-------|----------|
| OpenAPI path count | 18 |
| Execute routes present | `/approve/execute`, `/reject/execute` |
| Bare routes absent | `/approve` (no suffix), `/reject` (no suffix) |
| Enqueue route absent | `/enqueue` not present |
| Kill switch exists | Configuration key present |
| Kill switch default | Disabled |
| Dev-only guard | `enforce_dev_environment()` called |
| Production path guard | Production home rejected |

### 19.3 New dev-check Output

```
PASS Execute routes:        present (2)
PASS Kill switch:           exists, disabled
PASS Dev-only guard:        present
PASS Production guard:      present
PASS Forbidden routes:      absent
```

---

## 20. Playwright Smoke Strategy

### 20.1 Phase 1C-00 (This Document)

No changes to Playwright tests.

### 20.2 Phase 1C Implementation Target

Playwright smoke tests must verify:

| Check | Method |
|-------|--------|
| Execute routes return 403 when kill switch disabled | POST to execute routes, expect 403 |
| Execute routes not accessible without confirmation | POST without body, expect 422 |
| Dry-run routes still work | Existing dry-run tests unchanged |
| Bare approve/reject routes still absent | 404/405 for bare routes |
| Enqueue route still absent | 404/405 for enqueue |
| Kill switch status visible in /reviews/status | GET status, check `executeEnabled: false` |

### 20.3 FORBIDDEN_PATTERNS Update

Allow `/approve/execute` and `/reject/execute` while continuing to forbid bare `/approve` and `/reject`.

---

## 21. Side-Effect Validation Strategy

### 21.1 Disabled Mode (Default)

When kill switch is disabled (default):

| File/Directory | Expected State |
|---------------|----------------|
| `state.db` | UNCHANGED |
| `MEMORY.md` | UNCHANGED |
| `memory/indexes/` | UNCHANGED |
| `memory/records/` | UNCHANGED |
| `memory/events.jsonl` | UNCHANGED |
| `memory/snapshots/` | UNCHANGED |
| `memory/reviews/` | UNCHANGED |

### 21.2 Enabled Mode (Temporary Test Fixture)

When kill switch is enabled for testing:

- Must use temporary `HERMES_HOME` fixture
- Must NOT use `/Users/huangruibang/Code/hermes-home-dev` for real execute tests
- Must verify:
  - Review status changed correctly (PENDING → APPROVED/REJECTED)
  - Memory files created/updated (approve only)
  - Events appended to both review and memory event logs
  - No forbidden files modified
  - Production home untouched
  - Backups created in snapshots

### 21.3 Dev-Home Pollution Prevention

**Critical rule:** Phase 1C implementation must NOT execute real approve/reject against the permanent dev-home memory store during tests. All execute tests must use temporary `HERMES_HOME` fixtures.

---

## 22. Risks

### 22.1 P0 Risks

None identified. Phase 1C-00 is documentation-only with no runtime impact.

### 22.2 P1 Risks (Phase 1C Implementation)

| Risk | Impact | Mitigation |
|------|--------|------------|
| Non-atomic multi-file write | Partial state after crash | Dev-only scope; backups in snapshots; manual recovery acceptable |
| TOCTOU between dry-run and execute | Stale preview used for execution | `reviewUpdatedAt` precondition check |
| Kill switch bypass | Execute in production | `enforce_dev_environment()` + HERMES_HOME check + source root check |
| Memory record orphaned after failure | Duplicate memory on retry | Error handler writes `last_error`; manual cleanup in dev-home acceptable |

### 22.3 P2 Risks (Phase 1C Implementation)

| Risk | Impact | Mitigation |
|------|--------|------------|
| Frontend confirmation UX confusing | User confusion about execute vs dry-run | Clear labeling, forced dry-run, explicit confirmation text |
| Audit trail incomplete | Missing event in events.jsonl | Low impact — review JSON has timestamps |
| `fcntl` unavailable on non-Unix | No inter-process lock | Dev-only environment assumed Unix |

---

## 23. Acceptance Criteria

Phase 1C-00 completion requires:

1. ✅ Approve/reject real write effects audited and documented (Section 4)
2. ✅ Failure modes audited and documented (Section 5)
3. ✅ Concurrency / lock / race conditions audited (Section 5.3–5.4)
4. ✅ Dev-only execute scope frozen (Section 6)
5. ✅ Execute routes草案 frozen (Section 6.1)
6. ✅ Dry-run-first requirement frozen (Section 9)
7. ✅ Explicit confirmation model frozen (Section 8)
8. ✅ Kill switch strategy frozen (Section 10)
9. ✅ Dev-only guard strategy frozen (Section 11)
10. ✅ Audit trail strategy frozen (Section 12)
11. ✅ Rollback/recovery strategy frozen (Section 15)
12. ✅ OpenAPI strategy: no change to current 16-path contract (Section 18.2)
13. ✅ dev-check strategy defined (Section 19)
14. ✅ Playwright smoke strategy defined (Section 20)
15. ✅ Side-effect validation strategy defined (Section 21)
16. ✅ No execute API implemented
17. ✅ No business code modified
18. ✅ No memory files modified
19. ✅ No review queue files modified
20. ✅ memory-check PASS
21. ✅ dev-check PASS
22. ✅ compileall PASS
23. ✅ Document complete
24. ✅ Local commit created
25. ✅ Not pushed
26. ✅ Working tree clean after commit
27. ✅ Production environment unaffected
28. ✅ Phase 1C implementation not started

---

## 24. Acceptance Conclusion

Phase 1C-00 completed. Review Queue dev-only execute scope and safety boundary are frozen.

---

## 25. Next Task

**Phase 1C: Review Queue Dev-Only Execute Implementation**

This task must not begin until Phase 1C-00 is committed and the user explicitly requests it.
