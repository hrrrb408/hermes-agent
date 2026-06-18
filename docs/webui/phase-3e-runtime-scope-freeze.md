# Phase 3E — Runtime Scope Freeze

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — Scope Freeze (Frozen) |
| Status | Frozen (docs-only planning; Real Plugin Runtime **not started**) |
| Date | 2026-06-19 |
| Planning ID | `PHASE-3E-PLANNING-001` |
| Scope-Freeze ID | `PHASE-3E-SCOPE-FREEZE-001` |

> This document freezes the scope of a **future, separately-authorized** real
> Plugin Runtime into three buckets — currently allowed, future-considerable but
> not approved, and continuously forbidden. It implements nothing. **Phase 3E
> Planning does not authorize any implementation.**

## 1. Frozen direction

```
A real plugin runtime is NOT authorized.
Phase 3E Planning produces the prerequisites a future runtime would need,
   as documentation only.
If a runtime is ever separately considered, it must start from a sandboxed,
   process-isolated, filesystem-bounded, network-disabled, supply-chain-pinned,
   permission-inheriting, audit-fail-closed, kill-switched model — and even that
   is a future, separately-authorized phase, not this one.
```

## 2. Currently allowed (this phase)

```
docs-only planning
real runtime threat model
sandbox architecture design
process isolation design
filesystem boundary design
network boundary design
supply-chain policy design
permission review
audit review
UI review
route governance review
production isolation review
GO / NO-GO
```

No code, no route, no execution, no production access.

## 3. Future implementation — considerable, but NOT approved

These are the building blocks a future runtime *might* need. They are recorded so
the prerequisites are explicit; **none is authorized by this phase.** Each would
require a separate explicit approval after planning closeout and human review.

```
runtime-disabled skeleton (no dispatch, no loader)
runtime configuration model
runtime capability-policy check (binds to existing Phase 3C capabilityIds)
runtime sandbox adapter interface (interface only; no concrete adapter)
runtime kill-switch model
runtime audit model
runtime status block (rides existing /status if no new route)
runtime-disabled UI panel
```

> Even these "considerable" items are gated behind approved sandbox / process /
> filesystem / network / supply-chain / audit / kill-switch models. They are
> **not** a commitment and **not** an authorization.

## 4. Continuously forbidden (this phase and any default future phase)

```
actual plugin execution
dynamic import (importlib / __import__ / path load / pkgutil walk)
local plugin directory loading
remote registry
marketplace
external plugin fetch
provider-generated plugin
LLM-generated plugin install
shell execution
database mutation
external HTTP execution
production operation
production rollout
new route by default
```

Each remains NO-GO unless and until a separate, explicitly-approved phase lifts
it — and only after the matching threat model + isolation model + audit + kill
switch exist.

## 5. What the future runtime is NOT

- It is **not** in-process code execution (high risk; see process-isolation
  model).
- It is **not** a permission grantor (inherits most-restrictive; grants nothing).
- It is **not** external (no marketplace, no remote registry, no remote fetch).
- It is **not** production-facing (`devOnly = true`, `productionAllowed = false`).
- It is **not** a write surface (never writes tool / provider / workflow /
  sandbox / runtime / production state without the existing gates).
- It is **not** a route surface (no new route by default).

## 6. Relationship to existing boundaries

This scope freeze is **additive** to the Phase 3C Capability Registry and the
Phase 3D Plugin Descriptor Registry, and to every prior Phase 3 boundary (3A
workflow approval, 3B provider boundary, 3B-Live-Enablement live gate). A future
runtime is a **sandboxed dispatch layer** that *references* existing capabilities
and descriptors. It does not relax any gate; it only formalizes what an
executable layer would require. None of those requirements is approved today.

## 7. Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E threat model](phase-3e-real-runtime-threat-model.md)
- [Phase 3E sandbox architecture](phase-3e-sandbox-architecture.md)
- [Phase 3E runtime GO / NO-GO](phase-3e-runtime-go-no-go.md)
- [Phase 3E implementation entry criteria](phase-3e-implementation-entry-criteria.md)
- [Phase 3D plugin runtime scope freeze](phase-3d-plugin-runtime-scope-freeze.md)
- [Phase 3D real runtime NO-GO](phase-3d-real-runtime-no-go.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
