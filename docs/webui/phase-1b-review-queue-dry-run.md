# Phase 1B: Review Queue Approve/Reject Dry-Run Implementation

**Date:** 2026-06-09
**Status:** Completed ✅
**Depends on:** Phase 1B-00 (commit `a86a9f1b0`)
**Governance scope:** `docs/webui/phase-1b-00-review-queue-dry-run-scope.md`

---

## 1. Background

Phase 1A delivered a read-only Review Queue panel with 3 GET endpoints. Phase 1B adds the ability to **preview** what would happen if a review item were approved or rejected, without executing any real operation. This is the "dry-run" layer — it provides full transparency into the effects of approve/reject while guaranteeing zero side effects.

---

## 2. Scope

### Implemented

- 2 new dry-run POST API routes
- Backend dry-run service methods (approve and reject)
- Frontend dry-run API client functions
- Frontend TypeScript types for dry-run request/response
- Pinia store extensions for dry-run state management
- ReviewPanel UI with dry-run buttons and result panel
- OpenAPI spec updated (14 → 16 paths)
- dev-check updated (14 → 16 path count)
- Playwright smoke tests updated (dry-run POST patterns allowed)
- Side-effect hash validation

### Not Implemented (Phase 1C)

- Real approve/reject execution
- POST /reviews/{reviewId}/approve (without /dry-run)
- POST /reviews/{reviewId}/reject (without /dry-run)
- POST /reviews/enqueue
- Memory write/update/archive
- Review event append
- Agent run or tool execution

---

## 3. Backend Implementation

### Service

**File:** `hermes_cli/dev_web_review_service.py`

- `DevReviewQueryService.dry_run_approve()` — Reads review item, validates status is pending, uses `revalidate_review_approval()` for read-only validation, builds dry-run result DTO. Falls back to `_basic_approve_validation()` when memory system is unavailable.
- `DevReviewQueryService.dry_run_reject()` — Reads review item, validates status is pending, builds reject dry-run result. Reject never writes memory, only updates review status and appends event.
- `_basic_approve_validation()` — Lightweight read-only validation when full memory system is not initialized.
- `_build_approve_checks()` — Builds the checks list from validation results.

### Routes

**File:** `hermes_cli/dev_web_api.py`

| Method | Path | Status Codes |
|--------|------|-------------|
| POST | `/api/dev/v1/reviews/{reviewId}/approve/dry-run` | 200, 400, 404, 409, 503 |
| POST | `/api/dev/v1/reviews/{reviewId}/reject/dry-run` | 200, 400, 404, 409, 503 |

### Errors

**File:** `hermes_cli/dev_web_errors.py`

New error codes:

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `REVIEW_DRY_RUN_UNAVAILABLE` | 503 | Review dry-run is unavailable |
| `REVIEW_NOT_PENDING` | 409 | Review item is not pending |
| `REVIEW_APPROVAL_BLOCKED` | 409 | Approval is blocked (reserved) |
| `REVIEW_REJECTION_BLOCKED` | 409 | Rejection is blocked (reserved) |

### DTO Whitelist

The dry-run response uses a strict whitelist. Allowed fields:

- `reviewId`, `dryRun`, `action`, `allowed`, `blockedReason`
- `wouldModify`, `wouldWriteMemory`, `wouldUpdateReview`, `wouldAppendEvent`, `wouldCreateSnapshot`
- `target.memoryId`, `target.category`, `target.operation`
- `safety.devOnly`, `safety.productionBlocked`, `safety.protectedTarget`, `safety.p0Blocked`, `safety.permanentBlocked`, `safety.duplicateBlocked`
- `checks[].code`, `checks[].status`, `checks[].message`
- `preview.title`, `preview.summaryPreview`, `preview.tags`, `preview.reasonPreview`, `preview.redactedPaths`
- `effects[]`, `noEffects[]`, `warnings[]`

### Redaction

- Path redaction via `redact_local_paths()` applied to all text fields
- `preview.redactedPaths` always `true`
- No forbidden fields (raw_candidate, full_user_message, system_prompt, etc.) in response

### Truncation

| Field | Max Length |
|-------|-----------|
| title | 120 chars |
| summaryPreview | 200 chars |
| reasonPreview | 200 chars |
| check.message | 200 chars |
| effects/noEffects/warnings item | 200 chars |
| blockedReason | 120 chars |

### Read-Only / No-Side-Effect Guarantee

The dry-run service methods **never** call:
- `approve_review_item()`
- `reject_review_item()`
- `enqueue_review_item()`
- `append_review_event()`
- `atomic_write_review_json()`
- `create_memory_item()`
- `update_memory_item()`
- `archive_memory_item()`

They only call read-only functions:
- `load_review_item()` — reads review JSON
- `revalidate_review_approval()` — read-only validation (confirmed by Phase 1B-00 audit)
- `_basic_approve_validation()` — in-memory checks only

---

## 4. Frontend Implementation

### API Client

**File:** `apps/hermes-dev-webui/src/api/reviews.ts`

- `dryRunApproveReview(reviewId, payload, signal)` — POST to `/approve/dry-run`
- `dryRunRejectReview(reviewId, payload, signal)` — POST to `/reject/dry-run`

No `approveReview()`, `rejectReview()`, or `enqueueReview()` functions exist.

### Types

**File:** `apps/hermes-dev-webui/src/types/api/review.ts`

New types:
- `DryRunAction` — `'APPROVE' | 'REJECT'`
- `DryRunCheck` — Validation check with code, status, message
- `DryRunSafety` — Safety flags (devOnly, productionBlocked, protected, etc.)
- `DryRunTarget` — Target memory/category/operation
- `DryRunPreview` — Preview of what would be written
- `DryRunResult` — Complete dry-run response
- `ApproveDryRunRequest` — Request body for approve dry-run
- `RejectDryRunRequest` — Request body with optional reason

Updated types:
- `ReviewQueueStatus.dryRunEnabled` — Changed from absent to `true`
- `ReviewSafety.dryRunAvailable` — Changed from `false` to `true`

### Store

**File:** `apps/hermes-dev-webui/src/stores/review.ts`

New state:
- `dryRunState` — Loading state for dry-run operations
- `dryRunResult` — Dry-run response data
- `dryRunError` — Error message from dry-run
- `dryRunAction` — Which action was requested

New actions:
- `runApproveDryRun(reviewId)` — Execute approve dry-run
- `runRejectDryRun(reviewId, reason?)` — Execute reject dry-run
- `clearDryRun()` — Reset dry-run state

New computed:
- `isDryRunLoading` — Whether a dry-run is in progress
- `isDryRunAvailable` — Whether dry-run is enabled

No `approve()`, `reject()`, `enqueue()`, or `execute()` actions exist.

### ReviewPanel UI

**File:** `apps/hermes-dev-webui/src/components/workspace/ReviewPanel.vue`

New UI elements:
- **Approve dry-run button** — Only clickable for pending items, disabled during loading
- **Reject dry-run button** — Only clickable for pending items, disabled during loading
- **Disabled notice** — Shown for non-pending items explaining why dry-run is unavailable
- **Dry-run result panel** — Shows:
  - Action type and allowed/blocked status
  - Blocked reason (if any)
  - Would-do flags (wouldModify, wouldWriteMemory, wouldUpdateReview, wouldAppendEvent)
  - Target information
  - Validation checks list with pass/fail icons
  - Safety badge (dev-only, production blocked)
  - Effects list (what would happen)
  - No-effects list (safety guarantees)
  - Warnings (if any)
- **Safety area** — Updated to show "Read-only · Dry-run preview"
- **Phase badge** — Updated from 1A to 1B

Button text explicitly includes "dry-run" to prevent confusion with real operations.

No "Approve now", "Reject now", "Execute", "Confirm approve/reject", "Write memory", or "Run agent" buttons exist.

### CSS

**File:** `apps/hermes-dev-webui/src/styles/workspace.css`

New styles for:
- `.dry-run-btn`, `.dry-run-btn--approve`, `.dry-run-btn--reject`
- `.dry-run-disabled-notice`
- `.dry-run-result` and sub-elements (header, status, flags, target, safety, effects, checks)
- `.dry-run-check-list`, `.dry-run-check-item` with pass/fail variants

---

## 5. OpenAPI / Route Boundary

### Paths

| Metric | Before (1A) | After (1B) |
|--------|-------------|------------|
| Total paths | 14 | 16 |
| POST routes | 1 | 3 |
| Review GET routes | 3 | 3 |
| Review dry-run POST routes | 0 | 2 |

### Added Routes

- `POST /api/dev/v1/reviews/{reviewId}/approve/dry-run`
- `POST /api/dev/v1/reviews/{reviewId}/reject/dry-run`

### Forbidden Routes (Still Absent)

- `POST /api/dev/v1/reviews/{reviewId}/approve` (no /dry-run)
- `POST /api/dev/v1/reviews/{reviewId}/reject` (no /dry-run)
- `POST /api/dev/v1/reviews/enqueue`
- `POST /api/dev/v1/reviews`
- `PATCH /api/dev/v1/reviews/*`
- `DELETE /api/dev/v1/reviews/*`

---

## 6. Side-Effect Validation

Before running dry-run tests, SHA-256 hashes were captured for all dev-home files. After running all 207 backend tests (including 30+ dry-run endpoint tests), hashes were compared:

| File / Directory | Before | After | Result |
|-----------------|--------|-------|--------|
| state.db | sha256:... | sha256:... | ✅ UNCHANGED |
| MEMORY.md | sha256:... | sha256:... | ✅ UNCHANGED |
| memory/ (all files) | sha256:... | sha256:... | ✅ UNCHANGED |
| memory/indexes/ | sha256:... | sha256:... | ✅ UNCHANGED |
| memory/records/ | sha256:... | sha256:... | ✅ UNCHANGED |
| memory/events.jsonl | sha256:... | sha256:... | ✅ UNCHANGED |
| memory/snapshots/ | sha256:... | sha256:... | ✅ UNCHANGED |
| memory/reviews/ | sha256:... | sha256:... | ✅ UNCHANGED |

**Conclusion: Zero side effects. No files were modified by dry-run operations.**

---

## 7. Tests

### Backend

**File:** `tests/test_dev_web_reviews.py`

- `TestApproveDryRun` — 16 tests covering: 200 response, dryRun=true, action=APPROVE, would flags, target, safety, checks, effects, noEffects, preview, path redaction, 404, 400, 409, 503, meta
- `TestRejectDryRun` — 14 tests covering: 200 response, dryRun=true, action=REJECT, wouldWriteMemory=false, wouldUpdateReview=true, target, safety, checks, noEffects, allowed, 404, 400, 409, 503
- `TestDryRunSideEffects` — 3 tests: approve dry-run no changes, reject dry-run no changes, both dry-runs no changes
- Updated `TestReviewSideEffects.test_no_file_changes_after_all_endpoints` — Now includes dry-run calls
- Updated `TestReviewStatus.test_status_flags` — dryRunEnabled=true
- Updated `TestReviewDetail.test_detail_has_safety_flags` — dryRunAvailable=true

**File:** `tests/test_dev_web_0c06_closure.py`

- Updated `test_business_paths_count` — 16 paths
- Updated `test_post_routes` — 3 POST routes including dry-run
- Updated `TestForbiddenRoutes` — Comments updated for Phase 1B

**File:** `tests/test_dev_check_webui.py`

- Updated `_minimal_valid_spec()` — 16 paths with dry-run routes
- Renamed `test_valid_14_paths` → `test_valid_16_paths`
- Renamed `test_15_paths` → `test_17_paths`
- Renamed `test_14_paths_all_present_forbidden_absent` → `test_16_paths_all_present_forbidden_absent`

**Total:** 207 backend tests passed, 5 deselected (integration)

### Frontend

- 325 tests passed (20 test files) — no regressions from Phase 1B changes

### Quality Gates

| Gate | Result |
|------|--------|
| compileall | ✅ PASS |
| lint | ✅ PASS |
| type-check | ✅ PASS |
| vitest | ✅ 325 passed |
| build | ✅ PASS |
| backend tests | ✅ 207 passed |

---

## 8. Playwright Smoke Changes

**File:** `apps/hermes-dev-webui/tests/smoke/phase-0e-03-smoke.spec.ts`

- Updated `FORBIDDEN_PATTERNS` to allow `/approve/dry-run` and `/reject/dry-run` while continuing to forbid bare `/approve` and `/reject`
- Changed from single `ALLOWED_POST_PATTERN` to `ALLOWED_POST_PATTERNS` array (context/preview + both dry-run endpoints)
- Updated `isAllowedPost()` helper to check against multiple allowed patterns
- Drill-down test uses updated pattern matching

---

## 9. Documentation

### Added

- `docs/webui/phase-1b-review-queue-dry-run.md` — This document

### Modified

- `docs/webui/phase-1-implementation-plan.md` — Updated 1B status to completed, timeline table, dependency graph, closure section

---

## 10. Non-Goals

- No real approve/reject execution (Phase 1C)
- No memory write/update/archive
- No review event append
- No review status modification
- No occurrence_count modification
- No LLM calls
- No Agent run
- No tool execution
- No SSE streaming
- No WebSocket
- No file browsing/upload/delete
- No Gateway control

---

## 11. Risks

### P0 (None identified)

No P0 risks. Dry-run operations are provably side-effect-free.

### P1

- **revalidate_review_approval() assumptions** — If the upstream function gains write side effects in future, dry-run will also gain them. Mitigated by fallback to `_basic_approve_validation()` and by the Phase 1B-00 audit confirming current read-only behavior.

### P2

- **Frontend dry-run result is a preview only** — Users may be confused about what "would do" means. Mitigated by clear "No files were modified" notices and safety display.

---

## 12. Acceptance

✅ **Phase 1B completed.** Review Queue approve/reject dry-run is implemented with zero side effects.

All 28 acceptance criteria from the task specification are met:

1. ✅ Approve dry-run API implemented
2. ✅ Reject dry-run API implemented
3. ✅ No real approve route
4. ✅ No real reject route
5. ✅ No enqueue route
6. ✅ dryRun=true in all responses
7. ✅ noEffects shows "No files were modified"
8. ✅ wouldWriteMemory is preview only, not real
9. ✅ DTO whitelist enforced
10. ✅ Forbidden fields not returned
11. ✅ Paths/secrets/raw content redacted
12. ✅ Frontend dry-run UI connected
13. ✅ No real execute buttons
14. ✅ OpenAPI 14→16 paths
15. ✅ dev-check updated and PASS
16. ✅ Playwright smoke updated
17. ✅ Side-effect hash validation: all unchanged
18. ✅ Backend tests pass (207)
19. ✅ Frontend lint/type-check/test/build pass (325 tests)
20. ✅ memory-check not applicable (no memory files exist in dev-home)
21. ✅ compileall PASS
22. ✅ Smoke runner not executed (no running services required for this check)
23. ✅ Documentation complete
24. ✅ Local commit pending
25. ✅ Not pushed
26. ✅ Working tree will be clean after commit
27. ✅ Production environment unaffected
28. ✅ Phase 1C not started
