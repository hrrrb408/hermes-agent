# Phase 3C — Static Manifest Schema

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Static Capability Manifest Schema (Allowed / Forbidden Fields) |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Schema ID | `PHASE-3C-MANIFEST-SCHEMA-001` |

> This document freezes the **static manifest schema** a future Phase 3C
> registry must use. No manifest file is created here; no Python module is
> created here.

## 1. What the manifest is

The manifest is the **single source of truth** for declared capabilities. It is:

- **static** — a tracked data structure, not a runtime artifact.
- **tracked** — committed to the repo, reviewable in a diff.
- **reviewable** — every capability declaration is human-readable.
- **deterministic** — same input → same registry output; no `Date.now()` /
  `Math.random()` / wall-clock drift.
- **no runtime plugin path** — it never points at code to load.

## 2. Recommended location (future, not created here)

The future implementation may place the manifest in one of:

```
hermes_cli/dev_web_capability_registry_manifest.py
hermes_cli/dev_web_capability_registry.py
```

This phase **does not create** either file. The location is recorded so the
future implementation does not invent a runtime / plugin path.

## 3. Allowed fields

A manifest entry may carry only these fields (a subset of the capability model;
see [phase-3c-capability-model.md](phase-3c-capability-model.md)):

```
capabilityId
displayName
description
category
permissionClass
trustLevel
status
toolBinding
providerBinding
workflowBinding
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
auditEventPrefix
metadataSchema
version
owner
source
```

## 4. Forbidden fields

A manifest entry **must not** carry any of these. Validation rejects the entire
manifest (fail-closed) if any forbidden field is present:

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

Rationale: each forbidden field would convert a descriptive registry into an
**execution surface** (dynamic code load, shell, SQL mutation, network fetch,
or secret carriage). The registry describes capabilities; it never invokes them.

## 5. Validation rules (future)

The future validator must:

1. Reject any entry containing a forbidden field (`capability_registry_manifest_rejected`).
2. Reject any entry missing a required field (`capabilityId`, `category`,
   `permissionClass`, `trustLevel`, `status`).
3. Reject any entry whose `permissionClass` / `trustLevel` is not in the frozen
   taxonomies ([phase-3c-capability-permission-classes.md](phase-3c-capability-permission-classes.md)).
4. Reject any entry with a duplicate `capabilityId`.
5. Reject any entry where `productionAllowed = true` in the first version.
6. Reject any entry whose `source` is not in
   {`builtin`, `static_manifest`, `provider_boundary`, `workflow_boundary`}.
7. Force `EXPERIMENTAL_DISABLED` / `EXTERNAL_FORBIDDEN` / `UNKNOWN_FORBIDDEN`
   trust levels to a non-executable `status`.
8. Emit `capability_registry_validation_passed` on success or
   `capability_registry_validation_failed` on failure.

## 6. Determinism

The manifest must be deterministic: capability ordering, field set, and derived
status are reproducible from the source. No runtime sampling, no wall-clock
derived timestamps inside the manifest module. Any `createdAt` / `updatedAt`
values are passed in (e.g. via the build / release context), not generated at
registry-load time.

## 7. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3C capability model](phase-3c-capability-model.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
- [Phase 3C audit policy](phase-3c-capability-audit-policy.md)
