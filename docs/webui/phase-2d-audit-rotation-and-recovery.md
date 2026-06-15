# Phase 2D — Audit Rotation + Recovery

## Rotation policy

`dev_web_audit_rotation.py` rolls the active segment to a new monotonically
numbered file when either threshold is crossed:

- maximum segment size (default 1 MiB)
- maximum events per segment (default 1000)

```
audit-000001.jsonl  →  audit-000002.jsonl  →  audit-000003.jsonl
```

Guarantees:

- rotation **never overwrites or deletes** an existing segment.
- segment filenames are monotonically increasing and zero-padded.
- rotation state is persisted (`meta/rotation-state.json`); survives restarts.
- a partial / interrupted rotation is recoverable — the next append picks the
  highest existing segment or creates the next one.
- queries and indexes transparently span all segments.

Old segments are **never deleted** in Phase 2D. Retention deletion is deferred
to a future retention phase.

## Corruption detection

`dev_web_audit_recovery.py` scans every segment and detects:

- invalid JSON line
- valid JSON but not an object
- missing required canonical field
- `schemaVersion` mismatch
- non-JSON-native value present
- unsafe secret-like value present
- duplicate `sequence`
- duplicate `eventId`
- partial write line (no trailing newline — possible truncated write)

## Quarantine

`quarantine_corrupt_records()` copies corrupt lines verbatim into
`quarantine/corrupt-<token>-<segment>.jsonl` (dev-local only). It is
**non-destructive**: the original segment is left intact. The report never
prints or persists secrets beyond the dev-local quarantine copy.

## Repair

`repair_audit_store()`:

1. Scans for corrupt records.
2. Quarantines them (copy only).
3. Rebuilds the index so queries skip corrupt lines via the scan path.

Phase 2D repair is non-destructive by default. An opt-in `create_clean_segment`
writes a fresh segment of only the valid records (old segments are still kept).

## Query safety

The query engine scans with `include_corrupt=True` and **counts** corrupt lines
it skips (`skippedMalformed`), then continues — a corrupt line never crashes the
API. The Audit Viewer surfaces a corruption warning when `skippedMalformed > 0`.
