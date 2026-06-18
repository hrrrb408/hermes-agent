# Phase 3D — Capability Registry Integration

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime ↔ Phase 3C Capability Registry Integration (Frozen) |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Integration ID | `PHASE-3D-CAPABILITY-INTEGRATION-001` |

> This document freezes how a future Phase 3D Plugin Runtime relates to the closed
> Phase 3C Capability Registry. Phase 3C remains the source of visible capability
> classification; a plugin descriptor **binds to** existing capability IDs and
> cannot create or upgrade capability classification.

## 1. Phase 3C remains authoritative

- The Phase 3C Capability Registry remains the **source of visible capability
  classification** (capability IDs, categories, permission classes, trust levels,
  statuses).
- A future plugin descriptor does **not** duplicate or replace that
  classification; it references it.

## 2. Binding model

A descriptor binds to one or more **existing** Phase 3C capability IDs via
`capabilityBindings`:

```
plugin descriptor
  → capability binding (must reference an existing Phase 3C capability ID)
    → permission classification (inherited from the bound capability)
      → trust classification (must not contradict the descriptor's trust level)
        → audit (every step, safe fields, fail-closed)
          → UI display (read-only; disabled by default)
```

## 3. What a descriptor cannot do

A future plugin descriptor:

- **cannot create a new permission class** — it inherits the bound capability's
  class.
- **cannot self-authorize** — declaring `permissionClass = WRITE_CONFIRM` while
  bound to a `READ_ONLY` capability is rejected (no escalation).
- **cannot bypass capability-registry validation** — its `capabilityBindings`
  must resolve against the live Phase 3C registry.
- **cannot bypass forbidden-field checks** — the same recursive + scalar-type
  guard from Phase 3C-H1 applies to descriptor fields.
- **cannot expose executable fields** — `pythonImportPath` / `callable` /
  `shellCommand` / `externalUrl` / `downloadUrl` / `installCommand` etc. are
  forbidden.

## 4. Permission-class inheritance (frozen)

| Descriptor declares | Bound capability class | Result |
|---------------------|------------------------|--------|
| same or lower class | READ_ONLY | accepted (descriptor inherits READ_ONLY) |
| higher class | READ_ONLY | **rejected** (escalation) |
| any | ADMIN_FORBIDDEN / EXTERNAL_FORBIDDEN / PRODUCTION_FORBIDDEN | **rejected** (terminal class) |

The descriptor's effective permission class is `min(descriptor declared, bound
capability class)` under the Phase 3C ordering, and the descriptor may never
exceed the bound capability.

## 5. Consistency with Phase 3C trust

A descriptor's `trustLevel` must be consistent with its trust zone (see
[phase-3d-trust-boundary.md](phase-3d-trust-boundary.md)). A descriptor bound to
a capability whose trust level is `EXTERNAL_FORBIDDEN` / `UNKNOWN_FORBIDDEN` is
itself `external_forbidden` / `unknown_forbidden` and never executable.

## 6. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D manifest contract](phase-3d-plugin-manifest-contract.md)
- [Phase 3D permission / approval model](phase-3d-permission-and-approval-model.md)
- [Phase 3C capability model](phase-3c-capability-model.md)
- [Phase 3C capability permission classes](phase-3c-capability-permission-classes.md)
- [Phase 3C static manifest schema](phase-3c-static-manifest-schema.md)
