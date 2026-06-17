# Phase 3C — Capability Model

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Capability Model — Fields, Categories, Statuses |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Model ID | `PHASE-3C-CAPABILITY-MODEL-001` |

> This document freezes the **capability model** that a future Phase 3C
> Capability Registry must implement. No code is written here.

## 1. Core fields

A capability record is frozen to these fields. The `capabilityId` is the stable
key. The field set is the **maximum** the registry may carry; the static
manifest (see [phase-3c-static-manifest-schema.md](phase-3c-static-manifest-schema.md))
further restricts which of these a manifest source may supply.

| Field | Meaning |
|-------|---------|
| `capabilityId` | Stable ID, e.g. `tool.read.route_governance_read` |
| `displayName` | Human-facing UI name |
| `description` | Short prose description (no secrets, no paths) |
| `category` | `tool` / `provider` / `workflow` / `sandbox` / `audit` / `registry` / `system` |
| `version` | Capability manifest version (string) |
| `owner` | Owning subsystem / phase (e.g. `phase-2a`, `phase-3b`) |
| `source` | `builtin` / `static_manifest` / `provider_boundary` / `workflow_boundary` |
| `status` | `enabled` / `disabled` / `blocked` / `planned` / `deprecated` |
| `permissionClass` | See [permission classes](phase-3c-capability-permission-classes.md) |
| `trustLevel` | See [trust levels](phase-3c-capability-permission-classes.md) |
| `executionMode` | `none` / `read_only` / `dry_run` / `confirmed_execute` / `manual_live` |
| `routeExposure` | `existing_route_only` / `no_route` / `forbidden_new_route` |
| `toolBinding` | Bound tool name, if a tool capability (may be empty) |
| `providerBinding` | Bound provider mode, if a provider capability (may be empty) |
| `workflowBinding` | Bound workflow step type, if a workflow capability (may be empty) |
| `requiresApproval` | Whether a human approval / confirmation is required at runtime |
| `requiresDryRun` | Whether a dry-run preview is required before execution |
| `requiresConfirmation` | Whether an explicit confirmation token + digest is required |
| `requiresAudit` | Whether an audit event is mandatory for this capability |
| `requiresBudget` | Whether a budget cap governs this capability |
| `requiresKillSwitch` | Whether a kill switch governs this capability |
| `devOnly` | `true` for the Phase 3C first version |
| `productionAllowed` | `false` for the Phase 3C first version |
| `disabledByDefault` | Whether the capability is disabled until explicitly enabled |
| `blockedReason` | Stable blocked-reason code when `status=blocked` (may be empty) |
| `auditEventPrefix` | Prefix for this capability's audit events (e.g. `provider_real_`) |
| `metadataSchema` | Reference to the safe-metadata schema (value-free markers only) |
| `createdAt` | Creation timestamp (passed in, not `Date.now()` at runtime) |
| `updatedAt` | Last-update timestamp (passed in, not `Date.now()` at runtime) |

## 2. Categories

| Category | Covers |
|----------|-------|
| `tool` | Built-in agent tools (read-only allowlist, sandbox write, rollback) |
| `provider` | Provider boundary capabilities (fake, real boundary, live gated) |
| `workflow` | Workflow step types and approval gates |
| `sandbox` | Sandbox write / rollback capabilities |
| `audit` | Audit read / query capabilities |
| `registry` | The capability registry itself (load / validate / view) |
| `system` | Dev environment / release status / route governance read |

## 3. Statuses

| Status | Meaning |
|--------|---------|
| `enabled` | Registered and usable inside its existing gates |
| `disabled` | Registered but turned off; not executable until explicitly enabled |
| `blocked` | Registered but execution blocked (see `blockedReason`) |
| `planned` | Declared for a future phase; not executable |
| `deprecated` | Registered but slated for removal; not executable |

## 4. executionMode

| executionMode | Meaning |
|---------------|---------|
| `none` | No execution (descriptive / planned / blocked) |
| `read_only` | Read-only execution; no state change |
| `dry_run` | Generates a preview; performs no real write |
| `confirmed_execute` | Requires dry-run + confirmation token + digest + audit |
| `manual_live` | Requires the Phase 3B-Live-Enablement live gate (human approval + budget + kill switch + audit) |

## 5. routeExposure

| routeExposure | Meaning |
|---------------|---------|
| `existing_route_only` | Rides an existing `mode`-branched route (no new route) |
| `no_route` | No HTTP route (static module / in-memory read) |
| `forbidden_new_route` | A new route is **not** permitted for this capability |

## 6. Forbidden fields

A capability record (and any manifest that produces one) **must not** carry:

```
pythonImportPath
callable
shellCommand
externalUrl
downloadUrl
pluginPackage
dynamicModule
evalCode
execCode
sqlStatement
productionPath
apiKey
Authorization
secret
```

These are forbidden because they would turn a descriptive registry into an
execution surface. See
[phase-3c-static-manifest-schema.md](phase-3c-static-manifest-schema.md) and
[phase-3c-no-dynamic-loading-policy.md](phase-3c-no-dynamic-loading-policy.md).

## 7. Key invariants

1. The registry **describes**; it does **not authorize.** A capability's
   `permissionClass` is a label, not a runtime grant.
2. `devOnly = true` and `productionAllowed = false` for every capability in the
   first version.
3. No capability may auto-promote from `disabled` / `planned` / `blocked` to
   `enabled` without a separately authorized change.
4. No capability record may carry a forbidden field.

## 8. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3C scope freeze](phase-3c-capability-registry-scope-freeze.md)
- [Phase 3C permission classes + trust levels](phase-3c-capability-permission-classes.md)
- [Phase 3C static manifest schema](phase-3c-static-manifest-schema.md)
