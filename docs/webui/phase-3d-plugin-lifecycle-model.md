# Phase 3D — Plugin Lifecycle Model

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Descriptor Lifecycle Model (Frozen) |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Lifecycle ID | `PHASE-3D-LIFECYCLE-001` |

> This document designs the **future** plugin descriptor lifecycle. It does not
> implement it. The lifecycle is **audit-only-dry-run**: descriptors are declared,
> validated, classified, and rendered read-only; **execution remains disabled by
> default**.

## 1. Lifecycle states (first version)

| State | Meaning |
|-------|---------|
| `planned` | Declared for a future phase; not yet validated; not executable |
| `declared` | A static descriptor exists in tracked source |
| `validated` | The descriptor passed schema + forbidden-field + capability-binding + permission-class validation |
| `visible` | Rendered in the read-only descriptor list / drawer |
| `disabled` | Registered but turned off; not executable until explicitly enabled (default) |
| `blocked` | Registered but execution blocked (see `blockedReason`) |
| `deprecated` | Registered but slated for removal; not executable |
| `removed` | No longer present in tracked source |

## 2. Prohibited lifecycle states (first version)

The following states are **forbidden** in the first version. Any one of them is a
P0 stop condition:

```
installed
loaded
executing
hot_reloaded
remote_synced
marketplace_installed
provider_generated
```

Rationale: each implies code was loaded, executed, hot-swapped, fetched remotely,
marketplace-installed, or provider-generated — all of which Phase 3D forbids.

## 3. Safe lifecycle (first version)

The only permitted lifecycle transitions are:

```
descriptor declared
  → descriptor validated (schema + forbidden fields + capability binding + permission class)
    → capability binding checked (binds an existing Phase 3C capability ID)
      → permission class checked (descriptor class ≤ bound capability class)
        → trust level checked (not external / unknown / production-forbidden)
          → audit policy checked (every transition audited, fail-closed)
            → UI displays read-only (visible / disabled / blocked)
              → execution remains disabled by default
```

No lifecycle step loads code, calls the network, writes state, or grants
permission. A descriptor that fails any check moves to `blocked` (or is rejected
before `declared`).

## 4. Lifecycle transitions (frozen)

| From | To | Allowed? | Condition |
|------|----|-----------|-----------|
| `(none)` | `planned` | yes | declared for a future phase |
| `planned` | `declared` | yes | static descriptor in tracked source |
| `declared` | `validated` | yes | passes all validation rules |
| `declared` / `validated` | `blocked` | yes | validation / check failure |
| `validated` | `visible` | yes | rendered read-only |
| `validated` | `disabled` | yes | default for the first version |
| `disabled` | `enabled` | **NO** (first version) | requires separately authorized phase + tests + approval |
| any | `deprecated` | yes | slated for removal |
| `deprecated` | `removed` | yes | no longer in tracked source |
| any | `installed` / `loaded` / `executing` / `hot_reloaded` / `remote_synced` / `marketplace_installed` / `provider_generated` | **NO** | forbidden |

## 5. Disabled-by-default activation model

- Every descriptor enters the first version as `disabled` (or `blocked`).
- **No descriptor auto-activates.** A declaration never promotes to `enabled`.
- Enabling a descriptor (if ever allowed) is a **separately authorized** change
  with code review, tests, and explicit user approval — and even then it only
  makes the descriptor *visible as enabled*; it still executes nothing by itself
  (execution rides the existing capability's gates).

## 6. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D manifest contract](phase-3d-plugin-manifest-contract.md)
- [Phase 3D execution isolation model](phase-3d-execution-isolation-model.md)
- [Phase 3D permission / approval model](phase-3d-permission-and-approval-model.md)
- [Phase 3C capability model](phase-3c-capability-model.md)
