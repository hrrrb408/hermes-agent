# Phase 2D-H1 — Audit Stress Test Report

## Identification

- Stress ID: `AUDIT-STRESS-2D-H1-001`
- Hardening ID: `HARDENING-2D-H1-001`
- Evidence: `tests/test_dev_web_phase_2d_h1_audit_store_hardening.py` (Lens 3,
  6, 7 stress); hardening script repeated-run lens.

## 1. Repeated runs

- `for i in 1..5; run_tests.sh tests/test_dev_web_phase_2d_h1_audit_store_hardening.py
  tests/test_dev_web_phase_2d_h1_audit_consistency.py tests/test_dev_web_phase_2d_h1_audit_security.py`
  → **5 passed / 0 failed**.
- The hardening script's "Repeated Hardening Stability" lens records 5/5 PASS.

## 2. Concurrent append stress

- 32 threads × 40 events per thread = 1280 events appended concurrently.
- Result: 1280 written, sequences `1..1280` contiguous, zero duplicates, zero
  lost events. Every `eventId` is durable on disk.
- 16 concurrent batches × 10 events = 160 events; sequences contiguous `1..160`.

## 3. Rotation stress

- Rotation by event count (policy `max_events_per_segment=4` against a 5-line
  segment) and by size (policy `max_segment_bytes=1024` against a 2048-byte
  segment) both report `should_rotate_audit_segment == True`.
- Repeated `rotate_audit_segment` produces strictly monotonic zero-padded
  segment names; original segment content is preserved across rotations.
- Query + index rebuild across multiple segments returns the full event set in
  the correct order.
- An interrupted rotation (rotation-state pointing at a not-yet-existing high
  segment number) is reconciled on the next append; old segments are retained.

## 4. Corruption recovery stress

- Every corruption class is detected in isolation: invalid JSON, not-an-object,
  missing required field, schema-version mismatch, partial write (no trailing
  newline), duplicate sequence, duplicate eventId, unsafe secret value.
- Quarantine copies the corrupt line to a dev-local dir without deleting the
  source segment.
- The query path skips the corrupt line and reports `skippedMalformed`; the API
  returns 200 (never crashes).
- `repair_audit_store` rebuilds the index and keeps every valid event
  queryable.

## 5. Cursor pagination stress

- 5-event store paged `limit=2` desc: pages `[5,4]`, `[3,2]` — correct boundary.
- 5-event store paged `limit=2` asc: pages `[1,2]`, `[3,4]` — correct boundary.
- Tampered cursor → blocked; query-mismatch cursor → blocked; direction-
  mismatch cursor → blocked.
- 6-event store paged via legacy offset cursors `"0"` and `"2"`: disjoint pages,
  no overlap.

## 6. Smoke stress

- `./scripts/run-dev-webui-execute-audit-smoke.sh all` → all profiles PASS,
  including `phase2d_audit_store_indexing` (9 Playwright tests).
- Production Gateway PID 28428 unchanged; ports 5180 / 5181 free at start and
  end.

## Result summary

| Stress | Result |
|--------|--------|
| Repeated runs (5/5) | PASS |
| Concurrent append (32 threads, 1280 events) | PASS — 0 lost, 0 duplicate |
| Rotation (size + count, multi-segment) | PASS |
| Corruption recovery (all classes) | PASS |
| Cursor pagination (asc/desc/tamper/offset) | PASS |
| Smoke (all profiles) | PASS |

**Overall: PASS.** The durable audit store is deterministic and stable under
concurrency, rotation, corruption, pagination, and repeated invocation.
