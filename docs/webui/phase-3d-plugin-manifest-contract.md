# Phase 3D — Plugin Manifest Contract

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Descriptor Manifest Contract (Allowed / Forbidden Fields) |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Schema ID | `PHASE-3D-MANIFEST-CONTRACT-001` |

> This document designs the **future** plugin descriptor manifest contract. It is
> a **descriptor, not executable code.** No manifest file is created here; no
> Python module is created here. The contract extends the Phase 3C static manifest
> schema with plugin-binding fields while keeping every forbidden field rejected.

## 1. What the manifest is

The plugin manifest is a **descriptor** for a static, reviewed plugin descriptor.
It is:

- **static** — a tracked data structure, not a runtime artifact.
- **tracked** — committed to the repo, reviewable in a diff.
- **reviewable** — every declaration is human-readable.
- **deterministic** — same input → same output; no `Date.now()` / `Math.random()`.
- **no code pointer** — it never points at code to load or run.

```
Manifest is a descriptor, not executable code.
Manifest does not grant permission.
Manifest does not create an execution path.
Manifest does not create a route.
Manifest does not create an approval.
```

## 2. Allowed descriptor fields

A future manifest entry may carry only these fields (the Phase 3C capability
fields plus plugin-binding fields):

```
pluginId
displayName
description
version
owner
source
trustLevel
status
capabilityBindings
permissionClass
executionMode
requiresApproval
requiresDryRun
requiresConfirmation
requiresAudit
requiresBudget
requiresKillSwitch
devOnly
productionAllowed
disabledByDefault
blockedReason
metadataSchema
createdAt
updatedAt
```

`capabilityBindings` is the binding to one or more **existing** Phase 3C
capability IDs. A descriptor cannot declare a capability that does not already
exist in the Phase 3C registry.

## 3. Forbidden descriptor fields

A manifest entry **must not** carry any of these. Validation rejects the entire
manifest (fail-closed, recursive + scalar type guard) if any forbidden field is
present at any depth:

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
localPath
remoteUrl
installCommand
postInstallHook
preExecutionHook
arbitraryArgs
```

Rationale: each forbidden field would convert a descriptive descriptor into an
**execution surface** (dynamic code load, shell, SQL mutation, network fetch,
local file load, install hook, or secret carriage). A descriptor describes; it
never invokes.

## 4. Manifest invariants

1. The manifest is **descriptive** — it grants no permission; it labels, binds,
   classifies, exposes, audits, and blocks.
2. The manifest is **static + tracked + deterministic** — no code pointer, no
   callable, no import path, no shell command, no external URL, no install hook,
   no SQL, no secret, no local path, no remote URL.
3. **No dynamic loading** — no `importlib`, no path load, no marketplace, no
   remote registry, no remote manifest, no arbitrary-URL fetch.
4. **dev-only** — every descriptor is `devOnly=true`, `productionAllowed=false`.
5. **Capability-bound** — `capabilityBindings` references existing Phase 3C IDs
   only; the descriptor inherits each bound capability's permission class (it may
   not declare a higher class).
6. **Disabled by default** — `disabledByDefault=true`; no auto-enable, no trust
   auto-upgrade.
7. **No leak** — manifest / read model / audit / UI never carry a secret,
   callable repr, shell command, SQL, production path, local plugin path, dynamic
   import path, install command, or external URL.
8. **No new route by default** — status rides the existing `/status` block; route
   governance stays 34 / 34 / 5 / 0 / 1 / 1.

## 5. Validation rules (future)

The future validator must:

1. Reject any entry containing a forbidden field (recursive + scalar type guard)
   → `plugin_descriptor_rejected`.
2. Reject any entry missing a required field (`pluginId`, `capabilityBindings`,
   `permissionClass`, `trustLevel`, `status`).
3. Reject any entry whose `permissionClass` / `trustLevel` is not in the frozen
   Phase 3C taxonomies.
4. Reject any entry whose `capabilityBindings` references a capability not in the
   Phase 3C registry.
5. Reject any entry whose declared `permissionClass` is **higher** than its bound
   capability's class (no escalation).
6. Reject any entry with a duplicate `pluginId`.
7. Reject any entry with `productionAllowed = true` in the first version.
8. Reject any entry whose `source` is not a reviewed static source.
9. Force forbidden trust levels to a non-executable `status`.
10. Emit `plugin_descriptor_validated` on success or
    `plugin_descriptor_validation_failed` on failure.

## 6. Determinism

The manifest must be deterministic: descriptor ordering, field set, and derived
status are reproducible from source. No runtime sampling, no wall-clock-derived
timestamps inside the manifest module. `createdAt` / `updatedAt` are passed in,
not generated at descriptor-load time.

## 7. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D scope freeze](phase-3d-plugin-runtime-scope-freeze.md)
- [Phase 3D lifecycle model](phase-3d-plugin-lifecycle-model.md)
- [Phase 3D capability registry integration](phase-3d-capability-registry-integration.md)
- [Phase 3C static manifest schema](phase-3c-static-manifest-schema.md)
- [Phase 3C capability model](phase-3c-capability-model.md)
