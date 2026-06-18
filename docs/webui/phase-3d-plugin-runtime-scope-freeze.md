# Phase 3D — Plugin Runtime Scope Freeze

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Static Dev-only Plugin Descriptor Runtime Skeleton — Scope Freeze |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Scope-Freeze ID | `PHASE-3D-SCOPE-FREEZE-001` |

> This document freezes the scope of a **future, separately-authorized** Phase 3D
> Plugin Runtime. It does not implement anything. The future first implementation
> must start from **static reviewed descriptors**, not executable external
> plugins.

## 1. Frozen direction

Future Phase 3D **may only** be:

> **Static Dev-only Plugin Descriptor Runtime Skeleton**

A future dev-only skeleton that holds **static, reviewed plugin descriptors**,
binds each to an existing Phase 3C capability ID, classifies each by the frozen
permission class and trust level, exposes a **read-only** view, and runs an
**audit-only dry-run** lifecycle. It is **disabled by default**. It is **not** an
executable plugin runtime.

The frozen invariants:

1. The runtime is **descriptor-based.** Plugin descriptors are static, tracked,
   reviewable data structures; they carry no code pointer, no callable, no import
   path, no shell command, no external URL, no SQL, no secret.
2. The runtime is **dev-only.** `devOnly = true`; `productionAllowed = false`
   for the first version.
3. The runtime **does not grant permission.** It describes, classifies, binds,
   exposes, audits, and blocks. Execution stays governed by the existing tool
   policy, approval / confirmation model, route governance, provider live gate,
   and workflow approval gates.
4. **No dynamic loading.** No `importlib`, no `__import__`, no path loading, no
   `pkgutil` walk, no marketplace, no remote registry, no remote manifest, no
   arbitrary-URL fetch, no npm / remote JS plugin, no provider-generated plugin,
   no LLM-generated tool installed as a plugin, no self-modifying plugin.
5. **No auto-enable.** A descriptor never self-enables; a descriptor declaration
   never auto-promotes to `enabled`; trust levels never auto-upgrade.
6. **No new route by default.** Descriptor status rides the existing `/status`
   response only if no new route is required. Default route governance stays
   34 / 34 / 5 / 0 / 1 / 1.
7. **No production rollout.** No `~/.hermes` access; no production `state.db`
   access; no production plugin.
8. **No secret leak.** No API key, Authorization header, bearer token, raw token
   hash, callable repr, production path, local plugin path, dynamic import path,
   shell command, or SQL mutation may appear in any descriptor, read model, audit
   event, or UI.
9. **Audit is mandatory.** Descriptor declaration / validation / binding /
   classification / view / block / route-governance / no-dynamic-loading checks
   are audited with safe fields only (fail-closed).
10. **A GO / NO-GO gate is mandatory.**

## 2. What the future Plugin Runtime is NOT

- It is **not** a dynamic plugin runtime. Dynamic loading, if ever considered, is
  a separate, later, even more tightly-gated phase.
- It is **not** a permission grantor. A descriptor does not authorize execution.
- It is **not** external. No marketplace, no remote registry, no remote fetch.
- It is **not** production-facing. Dev-only for the first version.
- It is **not** a write surface. Descriptors never write tool / provider /
  workflow / sandbox / runtime state.
- It is **not** an execution surface. Descriptors carry no executable code.

## 3. Allowed Changes (future implementation, separately authorized)

| Area | Allowed |
|------|---------|
| Static plugin descriptor module | A single tracked Python module holding static, reviewed descriptor data |
| Descriptor validation | Schema validation with an explicit forbidden-fields list (recursive + scalar type guard) |
| Capability binding | Each descriptor binds to an **existing** Phase 3C capability ID (`capabilityBindings`) |
| Descriptor classification | Each descriptor tagged with permissionClass + trustLevel + status |
| Read-only view | Descriptor status surfaced inside the **existing** `/status` response only if no new route is required |
| Frontend read-only panel | A read-only descriptor list + detail drawer + runtime-disabled banner (additive) |
| Audit-only dry-run lifecycle | A lifecycle that declares, validates, binds, classifies, and renders — never loads or executes |
| Audit | `plugin_*` events (safe fields only, dual-write, fail-closed) |
| Tests | Backend + frontend unit / contract tests |

> **Future implementation must start from static reviewed descriptors, not
> executable external plugins.**

## 4. Forbidden Changes

| Area | Forbidden |
|------|-----------|
| Dynamic loading | No `importlib` / `__import__` / path load / `pkgutil` walk / marketplace / remote registry / remote manifest / arbitrary-URL fetch / npm plugin / remote JS plugin |
| Plugin execution | No plugin code execution, no provider-generated plugin, no LLM-generated tool as plugin |
| External plugins | No external plugin files, no user plugin directory, no remote plugin registry |
| Permission grant | No descriptor grants execution permission |
| Routes | No new HTTP route, no Tool write route, no Provider route (unless separately approved + recorded) |
| Production | No production rollout, no `~/.hermes` access, no production `state.db` access |
| Secrets | No API key / Authorization / bearer token / callable repr / path / shell command / SQL in any descriptor, read model, audit, or UI |
| Auto-enable | No descriptor self-enable, no declaration auto-promote, no trust auto-upgrade |
| Write | No descriptor writes to tool / provider / workflow / sandbox / runtime state |
| Storage | No production plugin store; descriptors are tracked source, not runtime data |

## 5. Relationship to existing boundaries

This scope freeze is **additive** to the Phase 3C Capability Registry and every
prior Phase 3 boundary (3A workflow approval, 3B provider boundary, 3B-Live-Enablement
live gate). A future plugin descriptor is a **descriptive binding layer** on top
of the Phase 3C capability classification. It does not relax any existing gate;
it only formalizes a descriptor structure that *references* existing capabilities.

## 6. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D non-goals / forbidden scope](phase-3d-non-goals-and-forbidden-scope.md)
- [Phase 3D manifest contract](phase-3d-plugin-manifest-contract.md)
- [Phase 3D lifecycle model](phase-3d-plugin-lifecycle-model.md)
- [Phase 3D capability registry integration](phase-3d-capability-registry-integration.md)
- [Phase 3D GO / NO-GO](phase-3d-go-no-go.md)
- [Phase 3C capability registry scope freeze](phase-3c-capability-registry-scope-freeze.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
