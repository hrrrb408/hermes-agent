# Phase 1C-Post-01: Approve Execute Success-Path Test Closure

**Date:** 2026-06-09
**Status:** Completed ✅
**Depends on:** Phase 1C (commit `498b6d86d`)
**Governance scope:** `docs/webui/phase-1-00-planning-and-scope.md`

---

## 1. Summary

Phase 1C shipped with reject-execute success-path tests and most approve-execute failure-path tests, but the approve-execute **success** path (WRITE and UPDATE) lacked automated coverage. This task closes that gap.

---

## 2. Gap Identified

| Path | Before 1C-Post-01 |
|------|-------------------|
| Reject execute success | ✅ Covered |
| Approve execute disabled | ✅ Covered |
| Approve execute failure paths | ✅ Covered (invalid confirmation, missing dry-run, precondition, etc.) |
| **Approve WRITE success** | ❌ Not covered |
| **Approve UPDATE success** | ❌ Not covered |
| **Approve DTO whitelist** | ❌ Not covered for approve (only reject) |
| **Approve idempotency** | ❌ Not covered |

---

## 3. Test Implementation

### 3.1 Fixture Design

Two new pytest fixtures with isolated `tmp_path` HERMES_HOME:

**`approve_execute_home`** — for WRITE tests:
- `MEMORY.md` with proper `index` field (required by `parse_root()`)
- Empty category index (no duplicates)
- One pending WRITE review item
- Full memory directory structure (indexes, records, snapshots, events)
- Review queue structure (items, events, lock)

**`approve_update_home`** — for UPDATE tests:
- Same MEMORY.md with `index` field
- Category index with one existing memory item (`MEM-HERMES-001`)
- Record file at `memory/records/hermes/mem-hermes-001.md`
- One pending UPDATE review item with `matched_memory` pointing to target
- Candidate title/summary designed for high similarity (≥0.85 title / ≥0.90 summary)
- Non-P0, non-permanent importance (`P2`) to avoid protected-target blocking
- Non-generic tags (`alpha`, `beta`) for core tag overlap

Both fixtures:
- Use `tmp_path` only (not `hermes-home-dev` or `~/.hermes`)
- Are cleaned up by pytest automatically
- Never appear in Git

### 3.2 Kill Switch

All tests use the existing `_execute_enabled()` context manager to temporarily set `HERMES_REVIEW_EXECUTE_ENABLED=true`. The environment variable is restored after each test.

---

## 4. Tests Added

### TestApproveExecuteWriteSuccess (8 tests)

| Test | Assertion |
|------|-----------|
| `test_approve_execute_write_success_response` | HTTP 200, correct DTO fields (executed, action, statusBefore/After, memoryChanged, reviewChanged, eventAppended, audit) |
| `test_approve_execute_write_review_json_approved` | Review JSON status → approved, approval object exists with approved_at, memory_id, action=WRITE |
| `test_approve_execute_write_review_event_appended` | `review_approved` event appended with correct review_id and memory_id |
| `test_approve_execute_write_creates_memory_record` | New .md record file created with MEM-HERMES- prefix |
| `test_approve_execute_write_updates_category_index` | Category index updated with new item |
| `test_approve_execute_write_appends_memory_event` | `memory_create` event appended to memory events.jsonl |
| `test_approve_execute_write_creates_index_backup` | Snapshot file created with INDEX- prefix |
| `test_approve_execute_write_no_unexpected_file_changes` | All file changes limited to expected paths |

### TestApproveExecuteUpdateSuccess (7 tests)

| Test | Assertion |
|------|-----------|
| `test_approve_execute_update_success_response` | HTTP 200, operation=UPDATE, target.memoryId=MEM-HERMES-001 |
| `test_approve_execute_update_review_json_approved` | Review JSON → approved, action=UPDATE, memory_id matches target |
| `test_approve_execute_update_review_event` | `review_approved` event with action=UPDATE |
| `test_approve_execute_update_modifies_record` | Target record file content changed |
| `test_approve_execute_update_appends_memory_event` | `memory_update` event appended |
| `test_approve_execute_update_creates_backups` | Both INDEX- and RECORD- snapshot files created |
| `test_approve_execute_update_no_unexpected_file_changes` | All changes limited to expected paths |

### TestApproveExecuteDtoSafety (2 tests)

| Test | Assertion |
|------|-----------|
| `test_approve_execute_response_no_sensitive_data` | No /Users/, /home/, traceback, secret, token, cookie in response |
| `test_approve_execute_response_dto_whitelist` | Only whitelisted top-level keys, no rawCandidate/source/fingerprint |

### TestApproveExecuteIdempotency (1 test)

| Test | Assertion |
|------|-----------|
| `test_second_approve_does_not_duplicate_memory_write` | Second approve does not create additional records or duplicate memory_create events |

**Total: 18 new tests**

---

## 5. Key Implementation Details Discovered

1. **Record path for "hermes" category**: `_record_uri_for("hermes", ...)` returns `memory://records/projects/hermes/...`, not `memory://records/hermes/...`. Tests must check the correct location.

2. **MEMORY.md requires `index` field**: `category_index_path()` calls `resolve_memory_uri()` which requires a `memory://` URI. The existing `execute_home` fixture's MEMORY.md lacked this field, making it unsuitable for approve success tests. New fixtures include `- index: memory://indexes/hermes.md`.

3. **UPDATE similarity requirements**: Candidate title and summary must be very similar to the target to pass `revalidate_review_approval` thresholds (combined ≥0.90, title ≥0.85 OR summary ≥0.90). Target importance must not be P0, TTL must not be permanent. Non-generic tags needed for core tag overlap.

4. **Idempotency**: `approve_review_item()` returns `{already_approved: True}` for already-approved items without performing additional writes. The service handles this gracefully.

---

## 6. Side-Effect Validation

### Formal dev-home (`hermes-home-dev`)

| Artifact | Before SHA | After SHA | Status |
|----------|-----------|-----------|--------|
| state.db | (recorded) | (identical) | ✅ No change |
| MEMORY.md | (recorded) | (identical) | ✅ No change |
| memory/* | (recorded) | (identical) | ✅ No change |

### Production (`~/.hermes`)

Not accessed during any test run. Gateway PID 1717 untouched.

---

## 7. Quality Gates

| Gate | Result |
|------|--------|
| Approve execute tests | 20 passed (including 2 pre-existing) |
| Phase 1C backend test set | 348 passed, 5 deselected |
| compileall | PASS |
| memory-check | PASS |
| dev-check | PASS (WARN: dirty worktree — expected) |
| OpenAPI paths | 18 (unchanged) |
| Frontend gates | Not re-run (no frontend changes) |

---

## 8. Files Changed

| File | Change |
|------|--------|
| `tests/test_dev_web_reviews.py` | Added 4 test classes, 3 fixtures, 1 helper (18 new tests) |
| `docs/webui/phase-1c-post-approve-execute-test-closure.md` | Created (this file) |
| `docs/webui/phase-1c-review-queue-execute.md` | Updated test coverage section |
| `docs/webui/phase-1-implementation-plan.md` | Added Phase 1C-Post-01 status |

No business code modified. No API routes added or removed. No frontend changes.

---

## 9. Acceptance

Phase 1C-Post-01 completed. Approve execute WRITE/UPDATE success paths are covered using isolated temporary fixtures, with formal dev-home and production environments untouched.

---

## 10. Next Task

Phase 1C-Post-Release: 测试补强封板核验与推送准备.
