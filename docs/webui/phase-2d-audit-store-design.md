# Phase 2D — Audit Store Design

## Location

```
$HERMES_HOME/gateway/dev/audit-store/
  events/
    audit-000001.jsonl   # monotonically numbered, append-only segments
    audit-000002.jsonl
  indexes/
    by-event-type.json   # per-field equality indexes
    by-tool-id.json
    by-status.json
    by-audit-kind.json
    by-source.json
    by-provider-mode.json
    by-read-only.json
    by-write-required.json
    by-created-date.json
    sequence.json        # high-water-mark consistency marker
  quarantine/
    corrupt-<token>-<segment>.jsonl
  meta/
    store-meta.json      # authoritative sequence counter + store status
    rotation-state.json  # active segment + rotation bookkeeping
    store.lock           # cross-process advisory lock (fcntl.flock)
```

## Path containment

The store root is resolved and validated by `get_audit_store_root()` /
`validate_audit_store_root()` in `dev_web_audit_store.py`. Validation rejects:

- the production home `/Users/huangruibang/.hermes` (exact + subtree)
- the repository root `/Users/huangruibang/Code/hermes-agent-dev`
- any path ending in `state.db`

Containment uses `Path.relative_to()`, never string prefix matching.

## Write semantics

`append_audit_event()` / `append_audit_events()`:

1. Sanitize the event through the unified sanitizer.
2. Validate the canonical schema.
3. Acquire the in-process `RLock` + cross-process `fcntl.flock`.
4. Floor the next sequence against the **on-disk maximum** (not just the meta
   counter) so a stale meta can never cause a colliding or gapped sequence.
5. Reject duplicate `eventId`s.
6. Append one JSONL line per event with `flush` + best-effort `fsync`.
7. Update `meta/store-meta.json` atomically (unique tmp name + `replace`).

A batch is all-or-nothing: if any event fails validation, the whole batch is
rejected (no partial append).

## Concurrency

- In-process: `threading.RLock` serializes appends within the process.
- Cross-process: `fcntl.flock(LOCK_EX)` on `meta/store.lock` (stdlib only;
  falls back to the in-process lock if `fcntl` is unavailable).
- The on-disk sequence floor makes the store self-healing: even if a meta
  write fails after an event line is durable, the next append recovers the
  correct sequence from disk.

## Legacy compatibility

The legacy per-kind JSONL files (`tool-dry-run-audit.jsonl`, etc.) remain the
source of truth for the legacy offset-based read path. The durable store is an
**additional** canonical sink populated by the best-effort dual-write bridge.
Both remain readable; the query engine reads the durable store, the legacy
reader reads the legacy files.

## Never committed

All files under `audit-store/` are runtime artifacts. `.gitignore` asserts
`audit-store/` plus every legacy audit JSONL / token / rollback store pattern
as defense-in-depth (they live under the dev `HERMES_HOME`, outside the repo).
