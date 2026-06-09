# Phase 1C: Review Queue Dev-Only Execute Implementation

**Date:** 2026-06-09
**Status:** Completed ✅
**Depends on:** Phase 1B (commit `1cc4148db`), Phase 1C-00 (commit `9d8aa4d71`)
**Governance scope:** `docs/webui/phase-1-00-planning-and-scope.md`
**Predecessor:** `docs/webui/phase-1c-00-review-queue-execute-scope.md`

---

## 1. Status

Phase 1C implements dev-only approve/reject execute endpoints with a fail-closed kill switch, explicit confirmation model, and precondition checks. Execute is disabled by default and only enabled via environment variable for temporary test fixtures.

---

## 2. Background

Phase 1A delivered read-only Review Queue access. Phase 1B added dry-run preview of approve/reject. Phase 1C adds the ability to actually execute approve and reject operations, but only in the dev environment with the kill switch explicitly enabled.

This is the first phase with real write operations targeting the dev HERMES_HOME.

---

## 3. Scope

### Implemented

- Kill switch (`HERMES_REVIEW_EXECUTE_ENABLED` env var, default disabled)
- Dev-only environment guard (rejects production HERMES_HOME)
- POST `/api/dev/v1/reviews/{reviewId}/approve/execute`
- POST `/api/dev/v1/reviews/{reviewId}/reject/execute`
- Full confirmation model: confirmationText, expectedAction, reviewUpdatedAt, dryRunPreviewed, acknowledgedEffects
- Precondition check (reviewUpdatedAt must match)
- Revalidation before execute
- Whitelisted response DTO (no sensitive data)
- Error redaction (no paths, secrets, traceback)
- Frontend execute controls (buttons, confirmation dialog, acknowledged effects)
- Playwright smoke test updates
- Backend tests (disabled mode + enabled temp fixture)
- dev-check updates (16 → 18 paths)
- OpenAPI spec updates (16 → 18 paths)

### Non-Goals

- Bare `/approve` or `/reject` routes (permanently forbidden)
- `/enqueue` route
- Batch operations
- Auto-approve or auto-reject
- Memory write/update/archive API
- Agent run, tool execution, SSE streaming
- Production execution (permanently prohibited)
- Phase 1D

---

## 4. Backend Implementation

### Kill Switch

Environment variable: `HERMES_REVIEW_EXECUTE_ENABLED`
Default: `false` (disabled)
Accepted true values: `true`, `1`, `yes`, `on`
All other values: disabled

The kill switch is checked at the service level before any write operations.

### Dev-Only Guard

`DevReviewQueryService._check_dev_only_environment()` verifies:
1. HERMES_HOME is not the production home (`~/.hermes`)
2. HERMES_HOME is not inside the production home

### Execute Service

Two methods added to `DevReviewQueryService`:
- `execute_approve()` — Full validation chain + real `approve_review_item()` call
- `execute_reject()` — Full validation chain + real `reject_review_item()` call

Both follow the same 16-step execution flow:
1. Kill switch check
2. Dev-only environment guard
3. Review ID validation
4. Load review item
5. Status check (must be pending)
6. Confirmation text validation
7. Expected action validation
8. Dry-run previewed check
9. Acknowledged effects check
10. reviewUpdatedAt precondition check
11. Revalidation (approve only)
12. Re-read review item inside lock
13. Re-check pending status
14. Re-check precondition
15. Execute real write operation
16. Return whitelisted response DTO

### Error Model

New error codes:
- `REVIEW_EXECUTE_DISABLED` (503) — Kill switch disabled
- `REVIEW_PRECONDITION_FAILED` (409) — reviewUpdatedAt mismatch
- `INVALID_CONFIRMATION` (400) — Wrong confirmation text
- `MISSING_DRY_RUN` (400) — dryRunPreviewed not true
- `INVALID_ACKNOWLEDGED_EFFECTS` (400) — Missing required effects
- `REVIEW_EXECUTE_ERROR` (500) — Unexpected execution error
- `UNSAFE_ENVIRONMENT` (503) — Production home detected

---

## 5. Frontend Implementation

### API Client

Two new functions in `api/reviews.ts`:
- `executeApproveReview(reviewId, payload)` — POST approve/execute
- `executeRejectReview(reviewId, payload)` — POST reject/execute

### Types

New types in `types/api/review.ts`:
- `ReviewExecuteResult` — Execute response data
- `ReviewExecuteTarget` — Target memory info
- `ReviewExecuteAudit` — Audit trail info
- `ApproveExecuteRequest` — Approve execute request body
- `RejectExecuteRequest` — Reject execute request body

`ReviewQueueStatus` extended with:
- `executeEnabled: boolean`
- `killSwitchActive: boolean`
- `devOnly: true`
- `productionBlocked: true`

### Store

New state in `stores/review.ts`:
- `executeState`, `executeError`, `executeResult`, `executeAction`
- `showConfirmDialog`

New computed:
- `isExecuteEnabled`, `isExecuteLoading`, `isKillSwitchActive`

New actions:
- `executeApprove()`, `executeReject()`, `clearExecute()`
- `openConfirmDialog()`, `closeConfirmDialog()`

### ReviewPanel

New UI elements:
- Execute capability status area (shows kill switch state)
- Approve/Reject execute buttons (disabled by default)
- Confirmation dialog with:
  - Manual text input (must type APPROVE/REJECT)
  - Acknowledged effects checkboxes
  - Execute/Cancel buttons
- Execute result panel
- Dev-only warning text

Button rules:
- Disabled when kill switch active
- Disabled when dry-run not completed
- Disabled when review not pending
- Click opens confirmation dialog (never direct execute)

---

## 6. API Routes

### Added (Phase 1C)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/dev/v1/reviews/{reviewId}/approve/execute` | Execute approve (dev-only) |
| POST | `/api/dev/v1/reviews/{reviewId}/reject/execute` | Execute reject (dev-only) |

### Forbidden (permanently)

| Method | Path | Reason |
|--------|------|--------|
| POST | `/api/dev/v1/reviews/{reviewId}/approve` | Bare route, use /execute |
| POST | `/api/dev/v1/reviews/{reviewId}/reject` | Bare route, use /execute |
| POST | `/api/dev/v1/reviews/enqueue` | Not implemented |
| POST | `/api/dev/v1/reviews` | Not implemented |
| PATCH | `/api/dev/v1/reviews/*` | Not implemented |
| DELETE | `/api/dev/v1/reviews/*` | Not implemented |

---

## 7. OpenAPI Changes

- Path count: 16 → 18
- Two new POST paths for approve/execute and reject/execute
- New schemas: `ReviewExecuteRequest`, `ReviewRejectExecuteRequest`, `ReviewExecuteData`, `ReviewExecuteResponse`, `ExecuteTarget`, `ExecuteAudit`
- Tags updated: Reviews description now includes "dev-only execute"

---

## 8. dev-check Changes

- Expected path count: 16 → 18
- New allowed routes: `/approve/execute`, `/reject/execute`
- Forbidden routes still enforced: bare `/approve`, `/reject`, `/enqueue`
- Kill switch and dev-only guard verified present

---

## 9. Playwright Smoke Changes

- FORBIDDEN_PATTERNS updated to allow `/execute` suffix
- ALLOWED_POST_PATTERNS extended with execute routes
- Existing tests verify execute buttons are disabled by default

---

## 10. Side-Effect Validation

### Disabled Mode on Real Dev-Home

| File/Directory | Status |
|---------------|--------|
| state.db | UNCHANGED |
| MEMORY.md | UNCHANGED |
| memory/indexes/ | UNCHANGED |
| memory/records/ | UNCHANGED |
| memory/events.jsonl | UNCHANGED |
| memory/snapshots/ | UNCHANGED |
| memory/reviews/ | UNCHANGED |

### Enabled Mode on Temp Fixture

All real execute write tests use `pytest tmp_path` fixtures:
- `execute_home` fixture creates isolated HERMES_HOME under `/tmp/pytest-*`
- Never touches `/Users/huangruibang/Code/hermes-home-dev`
- Never touches `/Users/huangruibang/.hermes`
- `_execute_enabled()` context manager enables kill switch only during test

Verified:
- Reject execute updates review JSON status to "rejected"
- Reject execute appends `review_rejected` event to events.jsonl
- Reject execute does NOT create memory records
- Approve/reject execute precondition checks work
- All validation error codes returned correctly

---

## 11. Tests

### Backend
- Test files: 4
- Total tests: 330 (105 review + 101 api + 106 closure + 18 dev-check)
- Failed: 0

### Frontend
- Test files: 20
- Total tests: 325
- Failed: 0

### Smoke
- Command: `./scripts/run-dev-webui-smoke.sh`
- Tests: 24 (20 viewport×theme + 4 panel drill-down)
- Passed: 24
- Failed: 0

---

## 12. Quality Gates

| Gate | Status |
|------|--------|
| compileall | PASS |
| memory-check | PASS |
| dev-check | PASS (WARN: dirty worktree) |
| pnpm lint | PASS |
| pnpm type-check | PASS |
| pnpm test | PASS (325/325) |
| pnpm build | PASS |
| Backend tests | PASS (330/330) |
| Smoke | PASS (24/24) |

---

## 13. Risks

### P1

| Risk | Mitigation |
|------|------------|
| Non-atomic multi-file write during approve | Dev-only scope; manual recovery acceptable |
| TOCTOU between dry-run and execute | reviewUpdatedAt precondition check |
| Kill switch bypass | enforce_dev_environment() + HERMES_HOME check + source root check |

### P2

| Risk | Mitigation |
|------|------------|
| Frontend confirmation UX confusing | Clear labeling, forced dry-run, explicit confirmation |
| fcntl unavailable on non-Unix | Dev-only environment assumed Unix |

---

## 14. Acceptance

Phase 1C completed. Review Queue dev-only approve/reject execute is implemented with kill switch, dev-only guard, explicit confirmation, and fixture-only write tests.

---

## 15. Next Task

Phase 1C-Release: Review Queue Execute 封板核验与推送准备

---

## 16. Phase 1C-Post-01: Approve Execute Success-Path Test Closure

**Date:** 2026-06-09
**Status:** Completed ✅

### Gap Closed

The original Phase 1C test suite covered reject-execute success and most approve-execute failure paths, but lacked approve-execute **success** path coverage. Phase 1C-Post-01 adds 18 tests covering:

- **WRITE success path** (8 tests): API response, review JSON approval, review event, memory record creation, category index update, memory event, index backup, unexpected write verification
- **UPDATE success path** (7 tests): API response, review JSON approval, review event, record modification, memory event, index+record backups, unexpected write verification
- **DTO safety** (2 tests): No sensitive data leakage, strict whitelist validation
- **Idempotency** (1 test): Second approve does not duplicate writes

### Test Count

- Before: 330 backend tests
- After: 348 backend tests (+18 new, plus pre-existing test count growth)

### Fixture Details

All approve success tests use isolated `pytest tmp_path` fixtures with properly structured MEMORY.md (including `index` field), category indexes, memory records, and review items. The kill switch is enabled only via `_execute_enabled()` context manager within each test.

See `docs/webui/phase-1c-post-approve-execute-test-closure.md` for full details.
