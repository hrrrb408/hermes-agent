# Phase 2D — Advanced Audit Storage / Indexing (Durable Dev Audit Store MVP)

## Status

**Phase 2D — completed.** Implements a dev-only durable audit store with
canonical `audit_schema_v2` events, unified audit sanitization, append-only
durable storage, indexing, cursor pagination, filtering, safe search,
rotation, corruption detection, and recovery / quarantine.

## Goal

Upgrade the Dev WebUI audit system from "viewable events" (legacy per-kind
JSONL files) to a long-lived dev-only audit query and storage infrastructure.

## What Phase 2D delivers

- **Canonical audit schema** (`audit_schema_v2`) — every audit event shares one
  JSON-native shape regardless of origin.
- **Unified audit sanitizer** — single redaction surface; closes the Phase 2A
  `str(object)` defense-in-depth gap.
- **Durable audit store** — append-only JSONL segments under the dev
  `HERMES_HOME`, with monotonic sequence, unique `eventId`, file locking.
- **Audit index** — per-field indexes with build / update / rebuild / repair.
- **Cursor pagination** — opaque, tamper-resistant cursors; legacy offset
  pagination retained for backward compatibility.
- **Filters + safe search** — eventType / toolId / status / auditKind / source /
  providerMode / readOnly / writeRequired / time range / substring search.
- **Rotation policy** — segment rollover by size or event count.
- **Corruption detection + quarantine** — corrupt lines are detected, copied to
  a dev-local quarantine dir, and skipped safely by the query path.
- **Dual-write bridge** — every existing audit writer (dry-run, pre/post
  execution, provider, write, rollback, confirmation) flows events into the
  durable store, best-effort and never blocking the legacy write.
- **Enhanced Audit Viewer** — store-mode toggle, filters, search, store/index
  status badges, segment count, redactionApplied badge, corruption warning.

## Hard boundaries (unchanged)

- Audit store lives **only** under the dev `HERMES_HOME`
  (`$HERMES_HOME/gateway/dev/audit-store`).
- Audit store is **not** under the repository, **not** under `~/.hermes`, and
  **not** any production state location.
- No audit store / token / rollback manifest / audit JSONL files are committed.
- Route governance unchanged: **OpenAPI paths 34, runtime routes 34, Tool GET
  5, Tool write HTTP route 0, Tool dry-run route 1, Tool execution route 1**.
- No new HTTP route, no Tool write HTTP route.
- No production rollout, no `~/.hermes` access, no production `state.db` access.
- No shell command execution, no database mutation, no external service write.

See companion docs:
- [Audit Store Design](phase-2d-audit-store-design.md)
- [Audit Schema v2](phase-2d-audit-schema-v2.md)
- [Audit Query + Indexing](phase-2d-audit-query-and-indexing.md)
- [Audit Rotation + Recovery](phase-2d-audit-rotation-and-recovery.md)
- [Audit Security Boundary](phase-2d-audit-security-boundary.md)
- [Test Report](phase-2d-test-report.md)
