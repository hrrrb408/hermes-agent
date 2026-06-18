# Phase 3H Sandbox Model Options

| Field | Value |
|-------|-------|
| Phase | 3H (Sandbox Proof Planning — Model Options) |
| Title | Real Plugin Runtime — Phase 3H Sandbox Model Options |
| Planning ID | `PHASE-3H-PLANNING-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Status | Docs-only planning — evaluates options only |

> This document is docs-only.
> This document evaluates sandbox model options for future planning only.
> This document does not select an implementation.
> This document does not implement a sandbox.
> This document does not authorize runtime execution.
> This document does not authorize production rollout.
> This document does not authorize new routes.

## A. Model review summary

This document compares candidate sandbox models for a future sandbox proof. It does not select
a buildable implementation, does not authorize implementation, and does not relax any
inherited NO-GO boundary. The comparison is planning material only.

The inherited architecture baseline (from Phase 3D / Phase 3E / Phase 3G) is:

- Option A — descriptor-only / no runtime remains the **only** approved current architecture.
- Option B — in-process execution remains **rejected** for real runtime execution.
- Option C — out-of-process worker remains a minimum future execution baseline only, not
  authorized for implementation.
- Option D — containerized isolation remains deferred and preferred for production-grade
  isolation, not authorized for implementation.
- Real runtime remains NO-GO.

## B. Candidate models

### Option A — Descriptor-only / no runtime baseline

- Current approved state: this is the only approved architecture. It is descriptor-only,
  disabled-by-default, capability-bound, read-only, dev-only.
- Pros: zero runtime risk; zero loader; zero execution; zero dynamic loading; route-stable;
  production-safe; auditable by inspection.
- Cons: cannot demonstrate any runtime isolation property because there is no runtime.
- Proof need: none required for runtime (there is no runtime). May serve as the safety
  baseline against which any future proof is compared.
- Whether it can serve as the current baseline: **yes** — it is the current baseline and the
  safest reference point.

### Option B — In-process simulated sandbox

- Description: a simulated boundary that lives inside the existing process, with no real
  worker, no real isolation, and no real capability enforcement.
- Risks: provides no real isolation; cannot bound the main process or gateway; cannot enforce
  a real filesystem or network boundary; cannot prove process isolation.
- Why it cannot serve as real runtime execution: there is no process boundary, so any failure
  mode, secret exposure, or capability escalation inside the process is indistinguishable from
  the main process. Presenting it as real isolation is unacceptable evidence.
- Permitted role: documentation discussion object only. It must not be implemented as a real
  runtime.

### Option C — Out-of-process worker proof candidate

- Description: a separate worker process that a future proof could use to demonstrate
  isolation, controlled lifecycle, bounded resources, and a killable boundary.
- Boundaries a future proof would need to demonstrate: process isolation, worker lifecycle
  control, timeout / cancellation, redacted stdout / stderr, environment-variable exposure
  prevention, resource limits, kill-switch linkage.
- Failure modes a future proof would need to demonstrate: worker timeout, worker crash,
  denied filesystem write, denied network call, denied secret read, malformed descriptor,
  oversized input, audit write failure, redaction failure, kill-switch active.
- Implementation authorization: **still NO-GO**. This option is a proof candidate only.

### Option D — Containerized proof candidate

- Description: a containerized boundary that a future proof could use to demonstrate stronger
  filesystem and network isolation.
- Isolation advantages: clearer filesystem boundary; clearer network boundary; clearer
  capability surface.
- Complexity / portability risks: higher operational complexity; portability across developer
  machines; dependency on container tooling; larger attack / supply-chain surface to review.
- Production-grade status: still requires future review; production-grade isolation is not
  approved by this document.
- Implementation authorization: **still NO-GO**.

### Option E — External managed sandbox service

- Description: a remote managed sandbox service that would host the proof execution.
- Network / third-party / data-exfiltration risks: requires external network; introduces a
  third-party trust boundary; creates data-exfiltration surface; requires secrets or tokens to
  authenticate; conflicts with the no-external-network and no-secret-read non-goals.
- Availability this phase: **not available** — it is incompatible with the inherited network
  and secret boundaries.
- Implementation authorization: **still NO-GO**.

```
No option above is selected for implementation.
No option above is authorized to be built.
```

## C. Comparison matrix

| Model | Isolation strength | Filesystem boundary clarity | Network boundary clarity | Secret exposure risk | Auditability | Testability | Operational complexity | Production risk | Current verdict |
| ----- | ------------------ | --------------------------- | ------------------------ | -------------------- | ------------ | ----------- | ---------------------- | --------------- | --------------- |
| A — Descriptor-only / no runtime | Highest (no runtime) | N/A (no runtime) | N/A (no runtime) | Lowest | Highest | Highest | Lowest | Lowest | Approved current baseline |
| B — In-process simulated | None | Low | Low | High | Low | Medium | Low | High | Rejected for real runtime |
| C — Out-of-process worker | Medium (if proven) | Medium (if proven) | Medium (if proven) | Medium (if proven) | Medium (if proven) | Medium (if proven) | Medium | Medium | Future proof candidate only; implementation NO-GO |
| D — Containerized | High (if proven) | High (if proven) | High (if proven) | Low (if proven) | Medium (if proven) | Medium (if proven) | High | Low (if proven) | Deferred; implementation NO-GO |
| E — External managed service | High (external) | Unknown (third-party) | Violates boundary | High | Low | Low | High | High | Not available this phase; NO-GO |

```
"if proven" means a future separately-authorized proof would be required.
No "if proven" condition is satisfied by this planning document.
```

## D. Planning conclusion

Future Phase 3H planning may continue to research the proof requirements for Option C and
Option D. It may **not** implement them.

```
Option A remains the only approved architecture.
Option B remains rejected for real runtime execution.
Option C and Option D remain future proof candidates only; implementation NO-GO.
Option E remains incompatible with inherited boundaries; implementation NO-GO.
```

```
This document selects no buildable implementation.
This document authorizes no runtime, loader, execution, route, or production change.
```

## Cross-references

- [Phase 3H sandbox proof planning](phase-3h-sandbox-proof-planning.md)
- [Phase 3H process isolation planning](phase-3h-process-isolation-planning.md)
- [Phase 3H filesystem boundary planning](phase-3h-filesystem-boundary-planning.md)
- [Phase 3H network boundary planning](phase-3h-network-boundary-planning.md)
- [Phase 3H GO / NO-GO](phase-3h-go-no-go.md)
- [Phase 3G archive index](phase-3g-archive-index.md)
