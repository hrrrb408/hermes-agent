# Phase 3E Planning — Real Plugin Runtime Threat Model and Sandbox Architecture

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — Threat Model, Sandbox Architecture, Process / Filesystem / Network Isolation, Supply-chain Policy, Permission / Audit / UI / Route / Production-isolation Review, GO / NO-GO |
| Status | Planning prepared — Real Plugin Runtime **not started** |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Input HEAD | `faa41010560827b9b61c332e93f6ec41831dbc73` (`docs(webui): sign off phase 3d closeout`) |
| Planning ID | `PHASE-3E-PLANNING-001` |
| Decision ID | `PHASE-3E-GO-NOGO-001` |

> This is a **docs-only planning phase.** It freezes the threat model, the
> sandbox architecture, the process / filesystem / network isolation models,
> the supply-chain policy, the permission review, the audit / redaction review,
> the UI review, the route-governance review, the production-isolation review,
> the risk register, the implementation entry criteria, the human-review brief,
> and the GO / NO-GO for a **future, separately-authorized** real Plugin Runtime.
> It does **not** implement a runtime, does **not** create a plugin loader, does
> **not** perform any dynamic loading, does **not** create a backend module, does
> **not** add a frontend component, does **not** add a test, does **not** modify
> `toolsets.py`, does **not** add a route, does **not** read any plugin directory,
> and does **not** perform any network call.

---

## 1. Goal

After Phase 3D shipped, hardened, closed, and signed off a **static, dev-only,
descriptive Plugin Descriptor Registry** (descriptor-only, disabled-by-default,
capability-bound, read-only), this planning phase answers a single question:
**is a real Plugin Runtime worth pursuing, and — if a future, separately-
authorized phase ever touches it — what isolation / sandbox / supply-chain /
permission / audit / route / production models must exist first?**

Phase 3E Planning produces, as documentation only:

- A frozen **real-runtime threat model** (30 runtime-specific threats).
- A frozen **runtime scope freeze** (currently-allowed / future-considerable /
  still-forbidden).
- A frozen **sandbox architecture** (four options compared; descriptor-only
  recommended).
- A frozen **process isolation model** (in-process high risk; out-of-process /
  containerized require their own policy).
- A frozen **filesystem boundary model** (deny-by-default dev sandbox).
- A frozen **network boundary model** (network disabled by default).
- A frozen **supply-chain policy** (no package install by default).
- A frozen **permission review** (runtime inherits most-restrictive; grants
  nothing).
- A frozen **audit / redaction review** (safe fields only, fail-closed).
- A frozen **UI review** (runtime-disabled banner; no secret leak).
- A frozen **route-governance review** (no new route).
- A frozen **production-isolation review** (no production access).
- A **risk register**, **GO / NO-GO**, **implementation entry criteria**,
  **human-review brief**, and **prompt draft**.

## 2. Core positioning

Phase 3E Planning defines the **architecture and prerequisites of a future real
plugin runtime** — it does not build one, and it does not authorize building one.

> A future real Plugin Runtime, if ever separately authorized, must remain
> **dev-only, sandboxed, process-isolated, filesystem-bounded, network-disabled-
> by-default, supply-chain-pinned, permission-inheriting, audit-fail-closed,
> kill-switched, route-governed, and production-isolated.** It must inherit —
> never bypass — the existing tool policy, provider live gate, workflow approval
> gates, dry-run / confirmation / audit chain, capability classification
> (Phase 3C), descriptor registry (Phase 3D), and route governance. None of its
> required isolation models exist or are approved today; the runtime remains
> NO-GO.

Phase 3E Planning is frozen as:

- **docs-only**
- **no implementation**
- **no real plugin runtime**
- **no plugin loader**
- **no plugin execution**
- **no dynamic loading**
- **no `importlib` / `__import__` dynamic import**
- **no local plugin directory loading**
- **no remote registry**
- **no marketplace**
- **no external plugin fetch**
- **no provider-generated plugin**
- **no LLM-generated plugin install**
- **no shell execution**
- **no database mutation**
- **no external HTTP execution**
- **no production operation**
- **no provider write**
- **no autonomous write**
- **no production rollout**
- **no new route**

## 3. Non-goals (forbidden in this planning phase)

- Implementing the plugin runtime or any plugin loader.
- Creating any backend module (`dev_web_runtime*.py`) or frontend component.
- Adding any test, smoke profile, or smoke spec.
- Modifying `toolsets.py`, runtime stores, or `state.db`.
- Adding any HTTP route, Provider route, Tool write route, plugin route, or
  runtime route.
- Any dynamic loading (`importlib` / `__import__` / path-based load / `pkgutil`
  walk), local plugin directory scan, marketplace, remote registry, remote
  manifest fetch, arbitrary-URL fetch, shell-command plugin, database plugin,
  external-HTTP plugin, provider-generated plugin, LLM-generated tool installed
  as a plugin, self-modifying plugin, auto-enable, or production plugin.
- Any sandbox process spawn, container start, IPC channel, or filesystem /
  network egress probe — even for "trying out" a future runtime.
- Reading any API key, performing any network call, or accessing `~/.hermes` /
  production `state.db`.
- Any production rollout; stopping / restarting / replacing / signaling the
  Production Gateway.

See [phase-3e-runtime-scope-freeze.md](phase-3e-runtime-scope-freeze.md).

## 4. Scope freeze

The future real Plugin Runtime scope is frozen to **descriptor-only remains the
runtime; a real runtime is not authorized.** See
[phase-3e-runtime-scope-freeze.md](phase-3e-runtime-scope-freeze.md).

The freeze separates three buckets:

1. **Currently allowed:** docs-only planning — threat model, sandbox
   architecture, isolation / boundary / supply-chain / permission / audit / UI /
   route / production-isolation review.
2. **Future implementation — considerable but NOT approved:** a runtime-disabled
   skeleton, a runtime configuration model, a runtime capability-policy check, a
   sandbox adapter interface, a kill-switch model, an audit model, a runtime
   status block, a runtime-disabled UI panel.
3. **Continuously forbidden:** actual plugin execution, dynamic import, local
   plugin directory loading, remote registry, marketplace, external plugin
   fetch, provider-generated plugin, LLM-generated plugin install, shell
   execution, database mutation, external HTTP execution, production operation,
   production rollout, new route by default.

> **Phase 3E Planning does not authorize any implementation.**

## 5. Companion documents

| Topic | Document |
|-------|----------|
| Runtime scope freeze | [phase-3e-runtime-scope-freeze.md](phase-3e-runtime-scope-freeze.md) |
| Real runtime threat model | [phase-3e-real-runtime-threat-model.md](phase-3e-real-runtime-threat-model.md) |
| Sandbox architecture | [phase-3e-sandbox-architecture.md](phase-3e-sandbox-architecture.md) |
| Process isolation model | [phase-3e-process-isolation-model.md](phase-3e-process-isolation-model.md) |
| Filesystem boundary model | [phase-3e-filesystem-boundary-model.md](phase-3e-filesystem-boundary-model.md) |
| Network boundary model | [phase-3e-network-boundary-model.md](phase-3e-network-boundary-model.md) |
| Supply-chain policy | [phase-3e-supply-chain-policy.md](phase-3e-supply-chain-policy.md) |
| Permission review | [phase-3e-permission-review.md](phase-3e-permission-review.md) |
| Audit / redaction review | [phase-3e-audit-redaction-review.md](phase-3e-audit-redaction-review.md) |
| UI review | [phase-3e-ui-review.md](phase-3e-ui-review.md) |
| Route-governance review | [phase-3e-route-governance-review.md](phase-3e-route-governance-review.md) |
| Production-isolation review | [phase-3e-production-isolation-review.md](phase-3e-production-isolation-review.md) |
| Runtime GO / NO-GO | [phase-3e-runtime-go-no-go.md](phase-3e-runtime-go-no-go.md) |
| Risk register | [phase-3e-risk-register.md](phase-3e-risk-register.md) |
| Implementation entry criteria | [phase-3e-implementation-entry-criteria.md](phase-3e-implementation-entry-criteria.md) |
| Human review brief | [phase-3e-human-review-brief.md](phase-3e-human-review-brief.md) |
| Prompt draft | [phase-3e-prompt.md](phase-3e-prompt.md) |

## 6. GO / NO-GO summary

```
GO  — completing Phase 3E Planning (this docs-only phase).
GO  — preparing the Phase 3E Planning Closeout / Human Review Readiness
       prompt ONLY after an explicit user request.
NO-GO — Phase 3E Implementation by default.
NO-GO — real plugin runtime execution.
NO-GO — plugin loader execution.
NO-GO — plugin execution.
NO-GO — dynamic loading.
NO-GO — local plugin directory loading.
NO-GO — remote registry.
NO-GO — marketplace.
NO-GO — external plugin fetch.
NO-GO — provider-generated plugin.
NO-GO — LLM-generated plugin install.
NO-GO — shell execution.
NO-GO — database mutation.
NO-GO — external HTTP execution.
NO-GO — production operation.
NO-GO — provider write.
NO-GO — autonomous write.
NO-GO — production rollout.
NO-GO — new HTTP route.
```

> **Planning does not equal authorization to implement.** Implementation requires
> a separate explicit user request **and** approved sandbox / process /
> filesystem / network / supply-chain / audit / kill-switch models.

See [phase-3e-runtime-go-no-go.md](phase-3e-runtime-go-no-go.md).

## 7. Production safety

Production Gateway PID `28428` was not stopped / restarted / replaced / signaled /
reconfigured (count 1). Dev services bind `127.0.0.1` only. No `~/.hermes` access;
no production `state.db` access. Route governance unchanged (34 / 34 / 5 / 0 / 1
/ 1). No plugin was loaded; no plugin directory was read; no dynamic import was
performed; no sandbox process was spawned; no network call was made; no API key
was read.

See [phase-3e-production-isolation-review.md](phase-3e-production-isolation-review.md).

## 8. Relationship to Phase 3C and Phase 3D

Phase 3E Planning is **additive** to the closed Phase 3C Capability Registry
and the signed-off Phase 3D Plugin Descriptor Registry.

- **Phase 3C** remains the **source of capability classification.** A future
  runtime capability-policy check must bind to existing Phase 3C `capabilityId`s
  and cannot create a new permission class. See
  [phase-3e-permission-review.md](phase-3e-permission-review.md).
- **Phase 3D** remains the **descriptor source.** A future runtime must treat
  descriptors as static, reviewed, capability-bound data; it may not execute
  them, may not load them dynamically, and may not relax any forbidden-field /
  trust / permission boundary. See
  [phase-3e-runtime-scope-freeze.md](phase-3e-runtime-scope-freeze.md).
- The runtime inherits every prior Phase 3 boundary: 3A workflow approval, 3B
  provider boundary, 3B-Live-Enablement live gate, 3C capability registry, 3D
  descriptor registry. It relaxes nothing.

## 9. Inheritance — the runtime may never bypass these

A future real runtime must inherit (never override, never bypass):

```
Tool policy (read-only / write-preview / write-confirm / rollback-confirm)
Provider live gate (human approval + budget + kill switch + allowlist)
Workflow approval gates (no auto-advance, no autonomous write)
Dry-run / confirmation / audit chain (Phase 1G / 2C / 2D)
Capability classification (Phase 3C — most-restrictive permission inheritance)
Descriptor registry (Phase 3D — descriptor-only, disabled-by-default)
Route governance (34 / 34 / 5 / 0 / 1 / 1)
Production isolation (PID 28428, no ~/.hermes, no production state.db)
```

## 10. Cross-references

- [Phase 3D human review signoff](phase-3d-human-review-signoff.md)
- [Phase 3D Phase 3E planning authorization](phase-3d-phase-3e-planning-authorization.md)
- [Phase 3D Phase 3E entry criteria](phase-3d-phase-3e-entry-criteria.md)
- [Phase 3D real runtime NO-GO](phase-3d-real-runtime-no-go.md)
- [Phase 3D final security boundary (after H1)](phase-3d-final-security-boundary-after-h1.md)
- [Phase 3D closeout](phase-3d-closeout.md)
- [Phase 3C closeout](phase-3c-closeout.md)
- [Phase 3 planning](phase-3-planning.md)
- [Phase 3 scope freeze](phase-3-scope-freeze.md)
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)
