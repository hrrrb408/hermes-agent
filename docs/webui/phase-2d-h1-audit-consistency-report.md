# Phase 2D-H1 — Audit Consistency Report

## Identification

- Consistency ID: `AUDIT-CONSISTENCY-2D-H1-001`
- Hardening ID: `HARDENING-2D-H1-001`
- Evidence: `tests/test_dev_web_phase_2d_h1_audit_consistency.py`,
  `tests/test_dev_web_phase_2d_h1_audit_store_hardening.py`,
  `tests/test_dev_web_phase_2d_audit_store.py`,
  `tests/test_dev_web_phase_2d_audit_index.py`,
  `tests/test_dev_web_phase_2d_audit_integration.py`

## 1. Append consistency

- Single append is durable; the event is a valid JSONL line carrying
  `schemaVersion=audit_schema_v2`.
- Batch append is all-or-nothing: an invalid event in a batch rejects the whole
  batch with no partial write.
- `append_audit_event` / `append_audit_events` never raise; failures are
  reported via `AuditStoreWriteResult.error_code`.

## 2. Sequence consistency

- `sequence` is monotonic, non-negative, and unique.
- The on-disk sequence floor (`_scan_existing`) recovers from a stale / deleted
  / stale-low `store-meta.json`: the next sequence is floored against the real
  on-disk maximum so it can never collide.
- After deleting `store-meta.json` mid-stream, subsequent appends continue the
  contiguous sequence (verified across 30 sequential appends).

## 3. eventId uniqueness

- A duplicate `eventId` is rejected (`ERROR_DUPLICATE_EVENT_ID`); it is never
  silently dropped or duplicated.
- Across separate appends and across batches, every `eventId` appears exactly
  once on disk.

## 4. Concurrent write checks

- 32 threads × 40 events = 1280 events: all durable, sequences are the
  contiguous set `1..1280`, no duplicates, no lost events.
- 16 concurrent batches of 10 = 160 events: sequences contiguous
  `1..160`, no collision.

## 5. Index vs segment scan

- For every indexed field (`eventType`, `toolId`, `status`, `auditKind`,
  `source`, `providerMode`, `readOnly`, `writeRequired`, `createdDate`) the
  index bucket-id set equals the full segment-scan bucket-id set.
- Index build from an empty store and from multiple segments both yield a
  consistent index.
- A stale index (event appended without rebuild) is detected and repaired; a
  corrupt sequence marker is rebuilt.

## 6. Query consistency

- Cursor pagination (asc / desc) windows correctly across pages with no overlap.
- The query hash is stable across `limit` / `cursor` changes and distinct across
  filter changes.
- Every equality filter (eventType / toolId / status / auditKind / source /
  providerMode / readOnly / writeRequired) and time-range filter behaves as
  specified; substring search matches summary / metadata text.
- Validation rejects oversized / negative / non-integer limits, invalid dates,
  unsafe / oversized search, and invalid enumerations with explicit codes.
- Legacy bare-integer offset cursor remains backward compatible.

## 7. Dual-write consistency

- All 7 audit kinds (dry-run, pre-execution, post-execution, provider, write,
  rollback, confirmation) bridge into the canonical store exactly once.
- Re-bridging the same `eventId` is rejected — no duplicate display.
- The bridge never raises on bad input (`None`, unknown kind, empty mapping).

## Result summary

| Check | Result |
|-------|--------|
| Append durability (single + batch) | PASS |
| Sequence monotonic + unique | PASS |
| eventId unique | PASS |
| Concurrent append (32 threads) | PASS — 0 lost, 0 duplicate |
| Index == segment scan (all fields) | PASS |
| Query / cursor / filter / search | PASS |
| Dual-write (7 kinds, once each) | PASS |

**Overall: PASS.** No event loss, no duplicate sequence, no duplicate eventId,
index equals scan, dual-write is consistent.
