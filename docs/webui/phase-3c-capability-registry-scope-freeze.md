# Phase 3C — Capability Registry Scope Freeze

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Static Dev-only Capability Registry Scope Freeze |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Scope-Freeze ID | `PHASE-3C-SCOPE-FREEZE-001` |

## 1. Frozen direction

Future Phase 3C **may only** be:

> **Static Dev-only Capability Registry**

A static, tracked, deterministic, dev-only registry that **describes**
built-in tool / provider / workflow / sandbox / audit / system capabilities,
classifies each by permission class and trust level, and exposes a read-only
view + audit. It is **not** a plugin runtime.

The frozen invariants:

1. The registry is **static.** Capabilities are declared in a tracked manifest;
   no runtime plugin path, no arbitrary import, no callable, no shell command,
   no external URL.
2. The registry is **dev-only.** `devOnly = true`; `productionAllowed = false`
   for the first version.
3. The registry **does not grant permission.** It describes, exposes, audits,
   and blocks. Execution stays governed by the existing tool policy, approval /
   confirmation model, route governance, provider live gate, and workflow
   approval gates.
4. **No dynamic loading.** No `importlib`, no path loading, no marketplace, no
   remote registry, no remote manifest, no arbitrary-URL fetch, no npm / remote
   JS plugin, no provider-generated plugin, no LLM-generated tool installed as a
   plugin, no self-modifying capability.
5. **No auto-enable.** A capability never self-enables; a manifest upload never
   auto-promotes to `enabled`; trust levels never auto-upgrade.
6. **No new route by default.** Capability status rides the existing `/status`
   response only if no new route is required; otherwise it is read from a static
   module / store. Default route governance stays 34 / 34 / 5 / 0 / 1 / 1.
7. **No production rollout.** No `~/.hermes` access; no production `state.db`
   access; no production plugin.
8. **No secret leak.** No API key, Authorization header, bearer token, raw token
   hash, callable repr, production path, local plugin path, dynamic import path,
   shell command, or SQL mutation may appear in the registry or its UI.
9. **Audit is mandatory.** Registry load / validation / view / block / route
   governance / no-dynamic-loading checks are audited with safe fields only.
10. **A GO / NO-GO gate is mandatory.**

## 2. What the Capability Registry is NOT

- It is **not** a plugin runtime. Plugin runtime, if ever needed, is a separate
  future phase (Phase 3D / 3E).
- It is **not** a permission grantor. It does not authorize execution.
- It is **not** dynamic. It does not load code.
- It is **not** external. No marketplace, no remote registry, no remote fetch.
- It is **not** production-facing. Dev-only for the first version.
- It is **not** a write surface. The registry never writes tool / provider /
  workflow / sandbox state.

## 3. Allowed Changes (future implementation, separately authorized)

| Area | Allowed |
|------|---------|
| Static capability registry module | A single tracked Python module (e.g. `hermes_cli/dev_web_capability_registry.py`) holding the manifest data |
| Manifest validation | Schema validation with an explicit forbidden-fields list |
| Capability classification | Each capability tagged with permissionClass + trustLevel + status |
| Status exposure | Capability status surfaced inside the **existing** `/status` response only if no new route is required |
| Frontend read-only panel | A read-only Capability Registry panel + detail drawer (additive, like Phase 2E / 3A) |
| Audit | `capability_registry_*` events (safe fields only, dual-write) |
| Tests | Backend + frontend unit / contract tests |
| Smoke | New additive smoke profile + spec |

## 4. Forbidden Changes

| Area | Forbidden |
|------|-----------|
| Dynamic loading | No `importlib` / path / marketplace / remote registry / remote manifest / arbitrary-URL fetch / npm plugin / remote JS plugin |
| Plugin runtime | No plugin execution, no provider-generated plugin, no LLM-generated tool as plugin |
| Permission grant | No capability grants execution permission |
| Routes | No new HTTP route, no Tool write route, no Provider route (unless separately approved + recorded) |
| Production | No production rollout, no `~/.hermes` access, no production `state.db` access |
| Secrets | No API key / Authorization / bearer token / callable repr / path / shell command / SQL in registry or UI |
| Auto-enable | No capability self-enable, no manifest-upload auto-promote, no trust auto-upgrade |
| Write | No registry writes to tool / provider / workflow / sandbox / runtime state |
| Storage | No production capability store; the registry manifest is tracked source, not runtime data |

## 5. Relationship to existing boundaries

This scope freeze is **additive** to the Phase 3B / Phase 3B-H1 / Phase
3B-Live-Enablement / Phase 3B-Live-H1 boundaries. The Capability Registry is a
**descriptive read-only layer** that references the existing tool policy,
provider boundary, workflow approval gates, and route governance. It does not
relax any existing gate; it only formalizes a description of what the system can
do and why each capability is permitted, gated, or blocked.

## 6. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3C capability model](phase-3c-capability-model.md)
- [Phase 3C permission classes + trust levels](phase-3c-capability-permission-classes.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
- [Phase 3C GO / NO-GO](phase-3c-go-no-go.md)
