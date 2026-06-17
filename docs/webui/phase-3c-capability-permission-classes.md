# Phase 3C — Capability Permission Classes & Trust Levels

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Permission Classes + Trust Levels (Taxonomy Freeze) |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Taxonomy ID | `PHASE-3C-PERMISSION-TRUST-001` |

> This document freezes the **permission-class** and **trust-level** taxonomies.
> They are descriptive labels on capability records, **not** runtime grants.
> Real execution stays governed by the existing tool policy, the approval /
> confirmation model, route governance, the provider live gate, and the workflow
> approval gates.

## 1. Permission classes

First-version permission classes:

| Class | Meaning |
|-------|---------|
| `READ_ONLY` | Read-only capability. May be displayed or executed in an authorized UI / API without changing state. |
| `WRITE_PREVIEW` | May generate a write **preview** only. No real write. |
| `WRITE_CONFIRM` | Requires dry-run + digest + explicit confirmation token + audit before execution. |
| `ROLLBACK_CONFIRM` | Requires a rollback manifest + explicit confirmation + audit before execution. |
| `LIVE_PROVIDER_GATED` | Requires the Phase 3B-Live-Enablement live gate: human approval + budget + kill switch + audit. |
| `ADMIN_FORBIDDEN` | Administrative or destructive capability. Currently forbidden. |
| `EXTERNAL_FORBIDDEN` | External execution, external HTTP, remote plugin, arbitrary URL, marketplace. Currently forbidden. |
| `PRODUCTION_FORBIDDEN` | Production operation, `~/.hermes`, production `state.db`, production rollout. Currently forbidden. |

### Ordering (least → most privileged)

```
READ_ONLY
WRITE_PREVIEW
WRITE_CONFIRM
ROLLBACK_CONFIRM
LIVE_PROVIDER_GATED
ADMIN_FORBIDDEN     (forbidden)
EXTERNAL_FORBIDDEN  (forbidden)
PRODUCTION_FORBIDDEN (forbidden)
```

The three `*_FORBIDDEN` classes are terminal: a capability classified under one
of them is **not executable** in the first version.

### What permission classes are NOT

- They are **not** permission grants. Classifying a capability `WRITE_CONFIRM`
  does not let it write; the existing dry-run + confirmation + audit chain still
  gates it.
- They are **not** runtime bypass tokens. A `LIVE_PROVIDER_GATED` capability
  still needs a fresh, in-scope, unexpired live approval.
- They are **not** mutable at runtime. The first version ships a frozen static
  classification.

## 2. Trust levels

First-version trust levels:

| Trust level | Meaning |
|-------------|---------|
| `BUILTIN_VERIFIED` | Built into the current code, has test coverage, has an audited boundary. |
| `DEV_STATIC_MANIFEST` | Declared in a dev-only static manifest; loads no code. |
| `EXPERIMENTAL_DISABLED` | A planned capability; default `disabled`; not executable. |
| `EXTERNAL_FORBIDDEN` | External source, remote plugin, marketplace, dynamic download. Forbidden. |
| `UNKNOWN_FORBIDDEN` | Unknown source. Forbidden. |

### What trust levels are NOT

- No trust level **auto-upgrades.** `DEV_STATIC_MANIFEST` never becomes
  `BUILTIN_VERIFIED` automatically.
- A manifest upload never auto-promotes a capability to `enabled`.
- No remote / marketplace source may earn `BUILTIN_VERIFIED` or
  `DEV_STATIC_MANIFEST`; remote / marketplace sources are `EXTERNAL_FORBIDDEN`.
- Unknown sources are `UNKNOWN_FORBIDDEN` and never executable.

## 3. Frozen composition rules

For the first version, the following combinations are the only valid ones:

- A capability is `enabled` only if `trustLevel ∈ {BUILTIN_VERIFIED,
  DEV_STATIC_MANIFEST}` **and** `permissionClass ∈ {READ_ONLY, WRITE_PREVIEW,
  WRITE_CONFIRM, ROLLBACK_CONFIRM, LIVE_PROVIDER_GATED}` **and** every runtime
  gate it declares (`requiresApproval`, `requiresDryRun`, `requiresConfirmation`,
  `requiresAudit`, `requiresBudget`, `requiresKillSwitch`) holds.
- A capability with `trustLevel ∈ {EXTERNAL_FORBIDDEN, UNKNOWN_FORBIDDEN}` or
  `permissionClass ∈ {ADMIN_FORBIDDEN, EXTERNAL_FORBIDDEN,
  PRODUCTION_FORBIDDEN}` is always `disabled` or `blocked`.
- `EXPERIMENTAL_DISABLED` capabilities are always `disabled` or `planned`.
- No capability in the first version has `productionAllowed = true`.

## 4. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3C capability model](phase-3c-capability-model.md)
- [Phase 3C static manifest schema](phase-3c-static-manifest-schema.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
