# Phase 3E — Sandbox Architecture

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — Sandbox Architecture (Frozen, Design-only) |
| Status | Frozen (docs-only planning; Real Plugin Runtime **not started**) |
| Date | 2026-06-19 |
| Planning ID | `PHASE-3E-PLANNING-001` |
| Sandbox ID | `PHASE-3E-SANDBOX-ARCH-001` |

> This document designs — but does **not** implement — the sandbox architecture a
> future real plugin runtime would require. Four options are compared. The
> recommendation is to **not** implement actual plugin execution; if a runtime is
> ever considered, an out-of-process or containerized sandbox must be separately
> planned and reviewed.

## 1. Comparison axes

Each option is scored on: Description · Allowed operations · Forbidden operations
· Isolation strength · Complexity · Failure modes · Audit requirements · Kill
switch requirements · Route governance impact · Production risk · Recommendation.

---

## Option A — No runtime; descriptor-only remains

- **Description:** keep the Phase 3D descriptor-only registry; never execute.
- **Allowed operations:** describe, classify, bind, expose (read-only), audit.
- **Forbidden operations:** any execution, loading, dispatch.
- **Isolation strength:** total (nothing to isolate).
- **Complexity:** lowest (already shipped).
- **Failure modes:** none runtime-related.
- **Audit requirements:** existing `plugin_descriptor_*` audit.
- **Kill switch requirements:** none (nothing to kill).
- **Route governance impact:** none (34 / 34 / 5 / 0 / 1 / 1).
- **Production risk:** none.
- **Recommendation:** **recommended** — the only option with zero runtime risk.

## Option B — In-process disabled runtime skeleton only

- **Description:** an in-process skeleton that holds a runtime-disabled dispatch
  interface; no plugin code is ever loaded or executed; every call returns
  `runtime_disabled`.
- **Allowed operations:** declare a disabled interface, classify intended
  capabilities, expose a runtime-disabled status block.
- **Forbidden operations:** in-process plugin execution; dynamic import; reaching
  secrets / paths / network inside the host process.
- **Isolation strength:** low (shares the host interpreter/address space; the
  *only* thing keeping it safe is "never executes").
- **Complexity:** low–medium.
- **Failure modes:** if a future change accidentally wires the dispatch, the host
  process is directly compromised (every RUNTIME-THREAT-01..06 fires in-process).
- **Audit requirements:** `runtime_*` events (requested / denied) with safe
  fields; fail-closed.
- **Kill switch requirements:** a runtime kill switch checked before any dispatch
  (even disabled).
- **Route governance impact:** none if status rides `/status`; a route would
  require separate approval.
- **Production risk:** medium (in-process; one mis-wire away from execution).
- **Recommendation:** **acceptable only as a never-executing skeleton**; if
  execution is ever contemplated, Option B is rejected in favor of C / D.

## Option C — Out-of-process sandboxed worker

- **Description:** plugin code runs in a separate OS process (or set of
  processes) with a restricted IPC channel, dropped privileges, resource limits,
  and no inherited secrets / filesystem / network by default.
- **Allowed operations:** dispatch over a narrow IPC; per-plugin CPU / memory /
  time limits; explicit allowlist of filesystem reads / writes; explicit network
  allowlist.
- **Forbidden operations:** reaching the host process memory; reading inherited
  env / secrets; arbitrary filesystem / network access.
- **Isolation strength:** high (separate process; OS-enforced boundary).
- **Complexity:** high (IPC protocol, lifecycle, resource accounting, restart,
  cleanup).
- **Failure modes:** IPC protocol bugs; resource accounting drift; zombie
  workers; partial-output crashes.
- **Audit requirements:** lifecycle + dispatch + boundary-access events (safe
  fields; fail-closed).
- **Kill switch requirements:** hard kill of the worker process; checked before
  secret read / network / dispatch.
- **Route governance impact:** none unless a dispatch route is added (separate
  approval).
- **Production risk:** low–medium (process-isolated; still dev-only).
- **Recommendation:** the **minimum acceptable** isolation for any real
  execution; requires the process-isolation, filesystem-boundary,
  network-boundary, supply-chain, and kill-switch models all approved.

## Option D — Containerized sandbox

- **Description:** plugin code runs inside a hardened container (read-only
  rootfs, dropped capabilities, seccomp / AppArmor, non-root, no-new-privileges,
  no network by default).
- **Allowed operations:** as Option C, plus container-enforced filesystem /
  network / capability boundaries.
- **Forbidden operations:** container breakout primitives; host mount; privileged
  capabilities.
- **Isolation strength:** highest (defense-in-depth: OS process + namespace +
  capability + syscall filter).
- **Complexity:** highest (image build / pinning, lifecycle, image supply chain,
  runtime dependency).
- **Failure modes:** container-runtime bugs; image supply-chain; resource /
  startup latency.
- **Audit requirements:** as Option C plus image-integrity provenance.
- **Kill switch requirements:** hard container kill; image denylist.
- **Route governance impact:** none unless a dispatch route is added.
- **Production risk:** low (most isolated; still dev-only).
- **Recommendation:** **strongest isolation**, but the most complex; deferred
  (RUNTIME-P2-02). Only if Option C proves insufficient and the container image
  supply chain is separately approved.

---

## 2. Recommendation

```
Phase 3E Implementation should not implement actual plugin execution.
If a future runtime is ever considered, out-of-process sandbox (Option C)
   or containerized sandbox (Option D) must be separately planned and
   reviewed — never in-process execution (Option B beyond a disabled skeleton),
   and never descriptor-bypass execution.
```

- **Now:** Option A (descriptor-only). No execution. No sandbox to build.
- **If ever:** Option C as the minimum, Option D if stronger isolation is
  required. Both require their full model set (process / filesystem / network /
  supply-chain / audit / kill switch) approved first.

## 3. What every option must inherit (non-negotiable)

Regardless of option, a future runtime must:

```
inherit the tool policy (no new execution path outside the controlled chain)
inherit the provider live gate (no provider path bypass)
inherit the workflow approval gates (no auto-advance / autonomous write)
bind to existing Phase 3C capability IDs (most-restrictive permission)
treat descriptors as static reviewed data (Phase 3D; no dynamic load)
keep route governance at 34 / 34 / 5 / 0 / 1 / 1 (no new route by default)
stay dev-only (devOnly = true; productionAllowed = false)
have a dedicated kill switch checked before secret read / network / dispatch
audit fail-closed with safe fields only
keep no inherited secrets / environment / filesystem by default
```

## 4. Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E process isolation model](phase-3e-process-isolation-model.md)
- [Phase 3E filesystem boundary model](phase-3e-filesystem-boundary-model.md)
- [Phase 3E network boundary model](phase-3e-network-boundary-model.md)
- [Phase 3E supply-chain policy](phase-3e-supply-chain-policy.md)
- [Phase 3E threat model](phase-3e-real-runtime-threat-model.md)
- [Phase 3D execution isolation model](phase-3d-execution-isolation-model.md)
