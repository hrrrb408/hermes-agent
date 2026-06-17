# Phase 3C — Capability Registry Audit Policy

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Capability Registry Audit Policy (Events + Safe / Forbidden Fields) |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Policy ID | `PHASE-3C-AUDIT-POLICY-001` |

> This document freezes the audit policy for the future Capability Registry.
> Audit events use **safe fields only**; defensive re-redaction is applied
> before write; audit write failure fails closed. No audit event may carry a
> secret, callable, path, shell command, or SQL.

## 1. Audit events (future)

| Event | When |
|-------|------|
| `capability_registry_loaded` | The registry loaded its static manifest successfully |
| `capability_registry_validation_passed` | Manifest validation passed |
| `capability_registry_validation_failed` | Manifest validation rejected an entry |
| `capability_registry_capability_viewed` | A capability detail was viewed (UI / status read) |
| `capability_registry_capability_blocked` | A capability was reported blocked (with `blockedReason`) |
| `capability_registry_permission_classified` | A capability was classified by `permissionClass` |
| `capability_registry_trust_classified` | A capability was classified by `trustLevel` |
| `capability_registry_manifest_rejected` | A manifest entry was rejected (forbidden field / invalid) |
| `capability_registry_route_governance_checked` | Route governance re-asserted at registry load |
| `capability_registry_no_dynamic_loading_checked` | No-dynamic-loading invariants confirmed at registry load |

## 2. Audit safe fields

Only these fields may appear in a `capability_registry_*` event:

```
capabilityId
category
permissionClass
trustLevel
status
blockedReason
requiresApproval
requiresAudit
devOnly
productionAllowed
routeExposure
safeMetadata          (value-free markers only)
redactionApplied      (true)
```

`safeMetadata` carries only value-free markers (e.g. counts, booleans, stable
enum labels). Every event records `redactionApplied=true`.

## 3. Audit forbidden fields

A `capability_registry_*` event **must never** carry:

```
API key
Authorization
Bearer token
raw secret
raw prompt
raw response
full tokenHash
callable repr
shell command
SQL statement
production path
local plugin path
dynamic import path
```

Defensive re-redaction runs before the write, regardless of input, so a
defective caller cannot leak a forbidden field into the audit store.

## 4. Storage & fail-closed

- `capability_registry_*` events are written to the existing Phase 2D durable
  audit store (`auditKind=registry`) + the dev JSONL.
- Audit write failure on a registry event **fails closed** (the registry load /
  view reports failure; no silent drop).
- No audit store, JSONL, or runtime artifact is committed. No `.claude/` is
  committed.

## 5. Dual-write + determinism

- Events are dual-written (durable store + dev JSONL).
- The audit payload is deterministic given the manifest; no wall-clock sampling
  inside the writer. Timestamps are taken from the caller / event context, not
  `Date.now()` at write time.

## 6. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3C capability model](phase-3c-capability-model.md)
- [Phase 3C static manifest schema](phase-3c-static-manifest-schema.md)
- [Phase 2D audit store design](phase-2d-audit-store-design.md)
