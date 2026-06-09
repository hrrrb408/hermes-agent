# Phase 1D: Memory Writer Dry-Run Panel — Implementation

**Date:** 2026-06-09
**Status:** Completed
**Depends on:** Phase 1C-Post (commit `79b92142b`), Phase 1D-00 (commit `06549bb9c`)
**Governance scope:** `docs/webui/phase-1-00-planning-and-scope.md`

---

## 1. Status

Phase 1D is **completed**. Three dry-run API endpoints and a frontend Writer Preview panel have been implemented. Zero side effects verified on formal dev-home.

---

## 2. Scope

Three read-only dry-run POST routes:
- `POST /api/dev/v1/memory/write/dry-run`
- `POST /api/dev/v1/memory/items/{memoryId}/update/dry-run`
- `POST /api/dev/v1/memory/items/{memoryId}/archive/dry-run`

Frontend Writer Preview sub-panel within the Memory panel.

---

## 3. Non-Goals

- Real Memory WRITE, UPDATE, or ARCHIVE execution
- Memory Writer Execute capability
- Auto Memory, Review Queue Enqueue
- Agent Run, LLM Call, Tool Execution
- SSE, WebSocket, File Upload/Delete
- Gateway or Dashboard control
- Phase 1E work

---

## 4. Backend Architecture

### Service

`DevMemoryWriterDryRunService` in `hermes_cli/dev_web_memory_writer_service.py`.

Uses only safe read-only functions with explicit `home` parameter:
- `list_items(home=self._home, include_all=True)` — read all memory items
- `find_item(memory_id, home=self._home)` — read single item
- `parse_root(home=self._home)` — read root categories
- `calculate_score()` — pure computation
- `calculate_similarity_breakdown()` — pure computation
- `is_protected_memory()` — pure computation
- `AutoWriteConfig()` — defaults only, no file I/O

### Decision Logic

Reimplemented locally in the service (not via `resolve_memory_decision()`) because:
- `resolve_memory_decision()` calls `find_best_memory_match()` which uses default `get_hermes_home()`
- `find_best_memory_match()` calls `list_items()` without `home` parameter
- `_category_status()` calls `parse_root()` without `home` parameter

Local `_find_best_match_local()` reads items with explicit `home` and iterates with `calculate_similarity_breakdown()`.

### Route Registration

Routes registered via `_register_writer_routes()` helper function called from `_register_routes()`. Keeps Phase 1D routes separate from existing routes.

---

## 5. Safety Guarantees

All responses enforce:
- `dryRun: true`
- `safety.readOnly: true`
- `safety.writeEnabled: false`
- `safety.executeAvailable: false`
- `safety.sideEffects: false`

### Forbidden Function Protection

Tests monkeypatch all write functions to fail if called:
- `create_memory_item`, `update_memory_item`, `append_event`
- `write_root_categories`, `write_index_items`, `backup_file`
- `ensure_memory_scaffold`, `_ensure_auto_category`
- `perform_safe_memory_action`, `maybe_auto_write_memory`
- `enqueue_review_item`, `atomic_write_review_json`

All 3 dry-run routes pass under monkeypatch protection.

---

## 6. Protection Model

### WRITE
- Not blocked by P0/permanent (new items can have any importance)
- Blocked by: score below threshold, duplicate detection, category issues

### UPDATE
- Blocked by: P0 importance, permanent TTL, archived status
- Protection checked independently in the service

### ARCHIVE
- Blocked by: P0 importance, permanent TTL, already archived
- **Independently enforced** — core archive path does NOT check P0/permanent
- This is a P1 risk documented in Phase 1D-00

---

## 7. OpenAPI Changes

- Paths: 18 → 21
- Added 3 dry-run POST routes
- Added `MemoryDryRunResponse`, `MemoryDryRunData`, and related schemas
- No real write routes exist

---

## 8. dev-check Changes

- Expected path count: 21
- 3 memory dry-run routes in ALLOWED_ROUTES
- Real write routes remain forbidden
- Tests updated for 21 paths

---

## 9. Frontend Architecture

### Panel Placement

Memory panel → two sub-tabs: **Browse** (existing) and **Writer Preview** (new).

### API Client

Three functions in `src/api/memory.ts`:
- `previewMemoryWrite(payload, signal?)`
- `previewMemoryUpdate(memoryId, payload, signal?)`
- `previewMemoryArchive(memoryId, payload, signal?)`

### Store

`useMemoryWriterStore` in `src/stores/memoryWriter.ts`:
- Form state for WRITE, UPDATE, ARCHIVE
- Loading/error/success state
- AbortController for request cancellation
- No execute action

### Components

- `MemoryWriterPreview.vue` — operation tabs, forms, result display
- `MemoryPanel.vue` — Browse + Writer Preview sub-tab navigation

---

## 10. Testing

### Backend (51 new tests)
- WRITE: 15 tests (allowed, category not found, invalid inputs, unavailable)
- UPDATE: 10 tests (allowed, not found, P0/permanent/archived blocked, diff)
- ARCHIVE: 10 tests (allowed, not found, P0/permanent blocked, reason redaction)
- Side Effects: 5 tests (hash validation, no new dirs, no events)
- Forbidden Functions: 3 tests (monkeypatch write functions)
- DTO Safety: 3 tests (no paths, no secrets, no dangerous fields)
- Route Boundary: 4 tests (21 paths, no real writes, dry-run POST only)

### Existing tests updated (7)
- Path count: 18 → 21
- POST routes: 1/5 → 8
- Route boundary checks updated

### Frontend (325 tests, all pass)
- Type-check: PASS
- ESLint: PASS
- Build: PASS

---

## 11. Side-Effect Validation

### Automated fixture validation

- WRITE dry-run: hash identical before/after
- UPDATE dry-run: hash identical before/after
- ARCHIVE dry-run: hash identical before/after
- No new directories, lock files, events, snapshots, or review items

### Formal dev-home validation

Before and after calling all 3 dry-run routes:
- `state.db`: IDENTICAL
- `MEMORY.md`: IDENTICAL
- All 26 memory files: IDENTICAL
- All 8 memory directories: IDENTICAL

**Conclusion: Zero side effects confirmed.**

---

## 12. Quality Gates

| Gate | Result |
|------|--------|
| compileall | PASS |
| memory-check | PASS |
| dev-check | PASS (21 paths) |
| Backend tests | 353 passed |
| Frontend lint | PASS |
| Frontend type-check | PASS |
| Frontend tests | 325 passed |
| Frontend build | PASS |

---

## 13. Acceptance

Phase 1D completed. Memory Writer WRITE/UPDATE/ARCHIVE dry-run APIs and preview panel are implemented with zero side effects.

---

## 14. Next Task

Phase 1D-Release:封板核验与推送准备。

Phase 1E must NOT be started.
