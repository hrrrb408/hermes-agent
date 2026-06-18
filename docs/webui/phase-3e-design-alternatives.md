# Phase 3E Design Alternatives — Real Plugin Runtime

| Field | Value |
|-------|-------|
| Phase | 3E (Planning Closeout) |
| Title | Real Plugin Runtime — Design Alternatives |
| Status | Planning-only — does **not** authorize implementation |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Doc ID | `PHASE-3E-DESIGN-ALTERNATIVES-001` |

> **This document is planning-only and does not authorize implementation.**
> It restates the four real-plugin-runtime architecture alternatives in a
> standalone, human-review-friendly form. The approved current state is
> descriptor-only (Option A). Real plugin runtime execution remains NO-GO.

## Option A — Descriptor-only / no runtime

- **Status:** **current approved architecture** (Phase 3D, signed off).
- **Description:** the registry holds static, reviewed, capability-bound plugin
  descriptors only. There is no runtime, no loader, no execution.
- **Properties:**
  - No plugin execution.
  - No loader.
  - No dynamic loading.
  - No external fetch.
  - No runtime secrets.
  - No production execution.
- **Decision:** **recommended current decision.** This is the only option that
  carries zero runtime risk, and it is what exists today.

## Option B — In-process execution

- **Status:** **rejected for real execution.**
- **Description:** plugin code would run inside the dev server process.
- **Risks (why it is rejected for real execution):**
  - **Process escape risk:** a plugin shares the host interpreter / address
    space; one mis-wire compromises the whole process.
  - **Memory sharing risk:** shared mutable state, namespace collision,
    reflection reach host memory.
  - **Secret exposure risk:** the in-process plugin can read `os.environ`,
    process memory, and any reachable secret.
  - **Dependency collision risk:** shared import graph; a plugin's dependency
    can shadow or break host dependencies.
  - **Audit ambiguity:** in-process actions are hard to attribute and bound.
  - **Kill-switch weakness:** an in-process path is hard to stop cleanly and
    atomically.
  - **Production blast radius:** one bug reaches every secret and path the host
    can reach.
- **Residual allowance:** it may only exist as a **disabled skeleton** in the
  future, if separately authorized, and it **cannot execute anything**.

## Option C — Out-of-process worker

- **Status:** **minimum acceptable architecture for any future real execution.**
- **Description:** plugin code runs in a separate OS process with a narrow IPC
  channel.
- **Must remain disabled until all P0 gates are approved.**
- **Required controls:**
  - Process boundary (separate process; no shared memory).
  - Least privilege (non-root; no new privileges; minimal capability surface).
  - Deny-by-default filesystem (explicit read / write allowlist; symlink /
    traversal rejection).
  - Deny-by-default network (egress allowlist only; no secret headers).
  - No secret inheritance (scrubbed / allowlisted env; no inherited secrets /
    filesystem / network).
  - Structured capability manifest (binds to existing Phase 3C capabilityIds;
    most-restrictive permission inheritance).
  - Runtime kill switch (checked before secret read / network / dispatch;
    fail-closed).
  - Fail-closed audit (safe fields only; an audit failure blocks the action).
  - Safe redaction (no secret / callable / path / command in any surface).
  - Reviewed source (static, reviewed, pinned; no fetched / installed code).
  - Deterministic startup contract (versioned IPC schema; bounded message size).
  - Explicit lifecycle and timeout model (spawn / dispatch / kill / cleanup;
    per-dispatch CPU / memory / time caps).

## Option D — Containerized / stronger isolation

- **Status:** **deferred.**
- **Description:** plugin code runs inside a hardened container.
- **When required:** before production consideration or any high-risk plugin
  category.
- **Must include:**
  - Image provenance (signed / reviewed image; tracked source).
  - Pinned dependencies (no floating versions; hash verification).
  - Non-root user.
  - Read-only root filesystem where feasible.
  - Mount allowlist (explicit mounts only; no host filesystem by default).
  - Egress policy (network disabled by default; explicit allowlist).
  - Resource limits (CPU / memory / time / fd caps).
  - Logs redaction (no secret / path / command in container logs).
  - No host socket.
  - No host credential mount.

## Comparison table

| Option | Status | Execution allowed? | Isolation strength | Implementation complexity | Production suitability | Decision |
|--------|--------|--------------------|--------------------|---------------------------|-------------------------|----------|
| A — Descriptor-only / no runtime | current approved | no | total (nothing to isolate) | lowest (already shipped) | none required | **approved current state** |
| B — In-process execution | rejected for execution | no (disabled skeleton only) | low (shares host process) | low–medium | unsuitable | **rejected for execution** |
| C — Out-of-process worker | future minimum | no, until all P0 gates approved | high (separate process) | high | dev-only first | **minimum future execution baseline** |
| D — Containerized | deferred | no | highest (process + namespace + capability + syscall) | highest | dev-only, production-grade later | **deferred, preferred for production-grade isolation** |

## Final decision

```
Option A remains the approved current state.
Option C is the minimum future execution baseline.
Option D is deferred but preferred for production-grade isolation.
Option B is rejected for execution (a disabled skeleton is the only allowed in-process form).
```

## Explicit GO / NO-GO

```
Phase 3E Planning Closeout = GO
Phase 3E Implementation   = NO-GO
Real runtime               = NO-GO
Production rollout         = NO-GO
```

## Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E sandbox architecture](phase-3e-sandbox-architecture.md)
- [Phase 3E runtime GO / NO-GO](phase-3e-runtime-go-no-go.md)
- [Phase 3E runtime scope freeze](phase-3e-runtime-scope-freeze.md)
- [Phase 3E human approver checklist](phase-3e-human-approver-checklist.md)
- [Phase 3E review board decision template](phase-3e-review-board-decision-template.md)
- [Phase 3E planning closeout](phase-3e-planning-closeout.md)
