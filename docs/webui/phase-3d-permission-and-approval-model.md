# Phase 3D — Permission & Approval Model

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime — Permission & Approval Model (Frozen) |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Model ID | `PHASE-3D-PERMISSION-MODEL-001` |

> Phase 3D Planning **does not change the permission model.** A plugin descriptor
> grants no permission. The existing Phase 2 / 3 permission classes and approval
> gates remain the sole authority.

## 1. Permission classes (inherited, unchanged)

The frozen Phase 3C permission classes remain authoritative:

| Class | Effect for a descriptor |
|-------|-------------------------|
| `READ_ONLY` | read-only; may be displayed; no state change |
| `WRITE_PREVIEW` | may generate a write preview only; no real write |
| `WRITE_CONFIRM` | requires dry-run + digest + explicit confirmation token + audit |
| `ROLLBACK_CONFIRM` | requires rollback manifest + explicit confirmation + audit |
| `LIVE_PROVIDER_GATED` | requires the Phase 3B-Live-Enablement live gate (approval + budget + kill switch + audit) |
| `ADMIN_FORBIDDEN` | forbidden; blocked |
| `EXTERNAL_FORBIDDEN` | forbidden; blocked |
| `PRODUCTION_FORBIDDEN` | forbidden; blocked |

- `READ_ONLY` remains read-only.
- `WRITE_CONFIRM` still requires dry-run + digest + confirmation + audit.
- `ROLLBACK_CONFIRM` still requires rollback manifest + confirmation + audit.
- `LIVE_PROVIDER_GATED` still requires the Phase 3B live approval + budget + kill
  switch + audit.
- `ADMIN_FORBIDDEN` remains blocked.
- `EXTERNAL_FORBIDDEN` remains blocked.
- `PRODUCTION_FORBIDDEN` remains blocked.

## 2. What a descriptor does NOT do

A plugin descriptor **does not grant permission**. Specifically:

- No plugin can create an approval.
- No plugin can create a confirmation token.
- No plugin can create a rollback manifest.
- No plugin can bypass audit.
- No plugin can elevate its permission class above its bound capability.
- No plugin can create a new permission class.

## 3. Approval / confirmation inheritance

A descriptor's `requiresApproval` / `requiresDryRun` / `requiresConfirmation` /
`requiresAudit` / `requiresBudget` / `requiresKillSwitch` flags are inherited from
its bound capability; they cannot be relaxed by the descriptor. If a bound
capability requires a confirmation token, the descriptor's bound execution path
requires it too — the descriptor cannot waive it.

## 4. Frozen non-grant invariants

```
Plugin planning does not change permission model.
Plugin descriptor does not grant permission.
No plugin can create approval.
No plugin can create confirmation token.
No plugin can create rollback manifest.
No plugin can bypass audit.
```

## 5. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D capability registry integration](phase-3d-capability-registry-integration.md)
- [Phase 3D provider / workflow boundary](phase-3d-provider-and-workflow-boundary.md)
- [Phase 3C capability permission classes](phase-3c-capability-permission-classes.md)
