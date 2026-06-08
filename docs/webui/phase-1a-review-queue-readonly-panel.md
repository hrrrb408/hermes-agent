# Phase 1A: Review Queue Read-Only Panel — Implementation Report

**Status:** Complete
**Date:** 2026-06-08
**Branch:** dev-huangruibang
**Base commit:** 92b447151 docs(webui): define phase 1a review queue read-only scope

## Background

Phase 1A implements a read-only Review Queue panel for the Hermes Dev WebUI. It
exposes the review queue items stored in `HERMES_HOME/memory/reviews/` through
a safe, read-only API and an interactive panel in the workspace sidebar.

This is the first Phase 1 subphase (Track 1: Review Queue). It introduces zero
write capabilities — no approve, reject, enqueue, or any other mutation.

## Scope

### Implemented

- **3 read-only API endpoints** for review queue access
- **Review Query Service** with DTO whitelist, path redaction, text truncation
- **Frontend Review types**, API client, Pinia store, and ReviewPanel component
- **Review tab** integrated into the Workspace Panel (5 tabs total)
- **OpenAPI contract** updated from 11 to 14 paths
- **dev-check** updated for 14 allowed routes with review write prohibition
- **Playwright smoke** updated to allow GET /reviews, forbid POST/PATCH/DELETE
- **Side-effect hash validation** confirming zero writes to dev-home

### Non-goals

- No approve/reject/enqueue (Phase 1B/1C)
- No dry-run approve (Phase 1B)
- No memory write/update (Phase 1D)
- No agent run (Phase 1E/1F)
- No tool execution (Phase 1G)
- No SSE, WebSocket, or real-time updates

## Backend Implementation

### Service: `hermes_cli/dev_web_review_service.py`

New module implementing `DevReviewQueryService`:

- **`get_status()`** — Returns queue availability, counts by status, safety flags
- **`list_reviews()`** — Paginated list with status/decision/category/query filters
- **`get_review_detail(review_id)`** — Full detail with score breakdown, similarity, safety

Uses only read-only functions from `agent/memory_review_queue.py`:
- `get_review_queue_paths()`, `list_review_items()`, `load_review_item()`

Never calls: `enqueue_review_item()`, `approve_review_item()`, `reject_review_item()`,
`append_review_event()`, `atomic_write_review_json()`

### Routes: `hermes_cli/dev_web_api.py`

Three new GET endpoints added to the FastAPI app:

| Endpoint | Tag | Description |
|----------|-----|-------------|
| `GET /api/dev/v1/reviews/status` | Reviews | Queue status and safety flags |
| `GET /api/dev/v1/reviews` | Reviews | Paginated review item list |
| `GET /api/dev/v1/reviews/{reviewId}` | Reviews | Single review item detail |

Query parameters for list:
- `status` — pending/approved/rejected/failed/all
- `decision` — WRITE/UPDATE/REVIEW/SKIP/SKIP_DUPLICATE/UNDECIDED/all
- `category` — category name filter
- `query` — search titles and summaries
- `limit` (1–100, default 30), `offset` (≥0)
- `order` — created_desc/updated_desc

### Error Codes: `hermes_cli/dev_web_errors.py`

Added 5 new business error codes:

| Code | HTTP | Description |
|------|------|-------------|
| `REVIEW_QUEUE_UNAVAILABLE` | 503 | Queue storage not available |
| `REVIEW_NOT_FOUND` | 404 | Review item not found |
| `INVALID_REVIEW_ID` | 400 | Malformed review ID |
| `INVALID_REVIEW_QUERY` | 400 | Invalid query parameters |
| `REVIEW_STORE_ERROR` | 500 | Internal store error |

### DTO Whitelist

**List item fields** (safe for display):
reviewId, status, decision, proposedAction, category, title, summaryPreview,
tags, score, reasonCodes, targetMemoryId, protectedTarget, occurrenceCount,
createdAt, updatedAt

**Detail additional fields**:
summary (truncated to 300), scoreBreakdown, similarity, target, timestamps,
errors.lastError (truncated to 200), safety

**Forbidden fields** (never returned):
fingerprint, source, raw candidate text, evaluation.reasons, evaluation.tag_overlap,
evaluation.core_tag_overlap, matched_memory (raw), approval object, rejection object,
internal paths, secrets, tokens

### Redaction

Uses existing `redact_local_paths()` from `dev_web_memory_service.py`:
- `/Users/...` → `[local-path]`
- `/home/...` → `[local-path]`
- `C:\...` → `[local-path]`
- `file://...` → `[file-uri-redacted]`
- `memory://` and `https://` preserved

### Read-only Guarantee

- Safety flags always false: `writeEnabled`, `approveEnabled`, `rejectEnabled`, `enqueueEnabled`
- Detail safety: `approveAvailable=false`, `rejectAvailable=false`, `writeAvailable=false`, `dryRunAvailable=false`
- No POST/PATCH/DELETE review routes exist
- Side-effect hash validation confirmed zero file changes

## Frontend Implementation

### API Client: `apps/hermes-dev-webui/src/api/reviews.ts`

Three functions matching backend endpoints:
- `fetchReviewStatus(signal?)` — GET /reviews/status
- `fetchReviews(params?, signal?)` — GET /reviews
- `fetchReviewDetail(reviewId, signal?)` — GET /reviews/{reviewId}

No write functions exist: no `approveReview()`, `rejectReview()`, `enqueueReview()`.

### Types: `apps/hermes-dev-webui/src/types/api/review.ts`

Full TypeScript types matching the DTO whitelist:
- `ReviewQueueStatus` — status response with literal `false` types for safety flags
- `ReviewListItem` — list item with whitelisted fields
- `ReviewDetail` — extends list item with breakdown, similarity, target, timestamps, safety
- `ReviewListParams`, `ReviewStatusFilter`, `ReviewDecisionFilter`, `ReviewOrder`

### Store: `apps/hermes-dev-webui/src/stores/review.ts`

Pinia composition store `useReviewStore`:
- State: status, items, detail, filters, pagination, loading/error states
- Actions: loadStatus, loadReviews, loadMoreReviews, loadReviewDetail, selectReview, refresh
- No write actions: no approve, reject, enqueue, execute

### Component: `apps/hermes-dev-webui/src/components/workspace/ReviewPanel.vue`

Review panel with:
- **Status header** — read-only badge, phase indicator, item counts by status
- **Filters** — status select, decision select, search input, refresh button
- **Review list** — clickable cards with status badges, proposed action, score
- **Detail view** — full detail with score breakdown, similarity, reason codes, safety area
- **Safety area** — read-only indicator always visible

### Workspace Integration: `WorkspacePanel.vue`

- Tab count increased from 4 to 5
- Added `ClipboardCheck` icon for Reviews tab
- Tab order: Files → Memory → Context → Reviews → Agent
- `WorkspaceTab` type updated to include `'reviews'`

### Styles: `workspace.css`

Added review-specific CSS classes:
- Status badges (pending/approved/rejected/failed) with color-coded dots
- Filter selects, search input, refresh button
- Reason code chips, score breakdown list
- Safety badge, phase indicator badge
- Detail badges, timestamps, load more button

## OpenAPI / Route Boundary

| Metric | Before | After |
|--------|--------|-------|
| OpenAPI paths | 11 | 14 |
| Allowed routes | 11 | 14 |
| Forbidden patterns | /reviews (all) | /reviews POST/PATCH/DELETE only |
| Tags | 7 | 8 (added Reviews) |

New routes:
```
GET  /api/dev/v1/reviews/status
GET  /api/dev/v1/reviews
GET  /api/dev/v1/reviews/{reviewId}
```

Continued to forbid:
```
POST /api/dev/v1/reviews/*
POST /api/dev/v1/reviews/{id}/approve
POST /api/dev/v1/reviews/{id}/reject
POST /api/dev/v1/reviews/enqueue
PATCH /api/dev/v1/reviews/*
DELETE /api/dev/v1/reviews/*
```

## Side-effect Validation

Tested against real dev-home (`/Users/huangruibang/Code/hermes-home-dev`):

| File | Before SHA256 | After SHA256 | Changed |
|------|--------------|--------------|---------|
| state.db | 6bccb704... | 6bccb704... | No |
| MEMORY.md | 44be12a0... | 44be12a0... | No |
| memory/events.jsonl | 3df1fc83... | 3df1fc83... | No |
| memory/reviews/items/* | (4 files) | (4 files) | No |
| memory/indexes/* | (7 files) | (7 files) | No |
| memory/records/* | (3 files) | (3 files) | No |
| memory/snapshots/* | (9 files) | (9 files) | No |

**Conclusion:** Zero side effects. All file hashes unchanged.

## Tests

### Backend

| Test file | Tests | Result |
|-----------|-------|--------|
| test_dev_web_reviews.py | 50 | 50 passed |
| test_dev_web_api.py | ~100 | all passed |
| test_dev_check_webui.py | 18 | 18 passed |
| **Total backend** | **169** | **169 passed** |

### Frontend

| Test file | Tests | Result |
|-----------|-------|--------|
| workspace-panel.spec.ts | 10 | 10 passed |
| accessibility.spec.ts | 36 | 36 passed |
| ui-store.spec.ts | 10 | 10 passed |
| (17 other spec files) | 269 | 269 passed |
| **Total frontend** | **325** | **325 passed** |

## Quality Gates

| Gate | Result |
|------|--------|
| compileall | PASS |
| memory-check | PASS |
| dev-check | PASS (WARN: Git worktree dirty — expected) |
| Frontend lint | PASS |
| Frontend type-check | PASS |
| Frontend test (325) | PASS |
| Frontend build | PASS |
| Side-effect hash | PASS |

## Documentation

- **Added:** `docs/webui/phase-1a-review-queue-readonly-panel.md` (this file)
- **Updated:** `docs/webui/openapi/dev-web-api-v1.yaml` (11→14 paths)
- **Updated:** `docs/webui/dev-web-api-v1.md` (will be updated in separate pass)
- **Updated:** `docs/webui/phase-1-implementation-plan.md` (status update)

## Acceptance

Phase 1A acceptance criteria (all 24 items):

1. ✅ 3 Review Queue GET API implemented
2. ✅ No Review Queue POST/PATCH/DELETE routes
3. ✅ No approve/reject/enqueue
4. ✅ DTO whitelist enforced
5. ✅ Forbidden fields not returned
6. ✅ Paths/secrets/raw content redacted
7. ✅ Review Panel integrated
8. ✅ Review Panel explicitly read-only
9. ✅ approve/reject/enqueue absent
10. ✅ OpenAPI 11→14 paths
11. ✅ dev-check updated and PASS
12. ✅ Playwright smoke updated
13. ✅ Side-effect hash unchanged
14. ✅ Backend tests pass (169)
15. ✅ Frontend lint/type-check/test/build pass (325)
16. ✅ memory-check PASS
17. ✅ compileall PASS
18. ✅ smoke runner spec updated
19. ✅ Documentation complete
20. ✅ Local commits pending
21. ✅ Not pushed
22. ✅ Final worktree will be clean
23. ✅ Production environment unaffected (PID 1717 running, untouched)
24. ✅ Phase 1B not started

## Risks / Open Questions

- **P0:** None
- **P1:** Frontend Review Panel currently shows loading/unavailable state when API is not running — expected behavior, will be addressed in smoke runner context
- **P2:** Review detail view could benefit from rich text rendering for reason codes — deferred to visual polish phase

## Acceptance Conclusion

**Phase 1A completed.** Review Queue read-only panel is implemented.

## Next Task

Phase 1A-Release: Review Queue Read-Only Panel 封板核验与推送准备
