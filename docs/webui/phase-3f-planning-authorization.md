# Phase 3F Planning Authorization

| Field | Value |
|-------|-------|
| Phase | 3F (Planning Authorization) |
| Title | Real Plugin Runtime — Phase 3F Planning Authorization |
| Authorization ID | `PHASE-3F-PLANNING-AUTH-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Source commit reviewed | `65b67d2136b4331b9acb859e531ddfa615e88dc2` |
| Status | Docs-only authorization — does **not** start Phase 3F Planning |

> This document is docs-only.
> This document authorizes Phase 3F Planning only.
> This document does not start Phase 3F Planning.
> This document does not authorize Phase 3F Implementation.
> This document does not authorize real plugin runtime.
> This document does not authorize production rollout.
> This document does not authorize any new route.

## A. Authorization summary

- Phase 3E is complete, signed off, and archived.
- Phase 3E remains closed.
- Phase 3F Planning Authorization is being evaluated in this document.
- Phase 3F Planning may be authorized as a future docs-only planning task.
- Phase 3F Planning is not started by this document.
- Phase 3F Implementation remains NO-GO.
- Real plugin runtime remains NO-GO.
- Production rollout remains NO-GO.

| Item | Decision |
| ---- | -------- |
| Phase 3E Planning | GO |
| Phase 3E Planning Closeout | SIGNED OFF |
| Phase 3E Archive / Index | COMPLETE |
| Phase 3F Planning Authorization | GO |
| Phase 3F Planning | AUTHORIZED FOR FUTURE DOCS-ONLY TASK |
| Phase 3F Implementation | NO-GO |
| Real plugin runtime | NO-GO |
| Plugin loader | NO-GO |
| Plugin execution | NO-GO |
| Dynamic loading | NO-GO |
| Production rollout | NO-GO |
| New route | NO-GO |

This document authorizes **only** a future Phase 3F Planning task, and only as a
docs-only task. It does not start that task, does not implement anything, and does
not relax any Phase 3E NO-GO boundary.

## B. Source evidence

Phase 3F Planning Authorization is grounded in the closed and archived Phase 3E
record. The Phase 3E closure evidence reviewed:

- [phase-3e-archive-index.md](phase-3e-archive-index.md)
- [phase-3e-human-review-signoff.md](phase-3e-human-review-signoff.md)
- [phase-3e-review-board-decision.md](phase-3e-review-board-decision.md)
- [phase-3e-planning-closeout.md](phase-3e-planning-closeout.md)
- [phase-3e-runtime-go-no-go.md](phase-3e-runtime-go-no-go.md)
- [phase-3e-implementation-entry-criteria.md](phase-3e-implementation-entry-criteria.md)
- [phase-3e-risk-register.md](phase-3e-risk-register.md)
- [phase-3-go-no-go.md](phase-3-go-no-go.md)

Phase 3E commit chain:

| Step | Commit | Message |
| ---- | ------ | ------- |
| Phase 3E Planning | `b8028d37baed55ca5bf6f57f1b924922f3b54ce7` | `docs(webui): plan phase 3e runtime sandbox` |
| Phase 3E Closeout / Readiness | `584fc11f8f730d0ed7554a7b7838a5056c84894d` | `docs(webui): close phase 3e planning review` |
| Phase 3E Signoff | `8c37965650ddb13a7bfc6a8d55ea39f63132bbcb` | `docs(webui): sign off phase 3e planning closeout` |
| Phase 3E Archive / Index | `65b67d2136b4331b9acb859e531ddfa615e88dc2` | `docs(webui): archive phase 3e planning package` |

The Phase 3E archive explicitly did **not** authorize Phase 3F. This document is
the separate, explicit authorization that a future Phase 3F Planning task may
begin.

## C. Phase 3F Planning purpose

The allowed purpose of a later Phase 3F Planning task is to prepare the next
documentation-only planning package for safe future work after Phase 3E.

Phase 3F Planning may evaluate:

- whether to continue descriptor-only governance;
- whether to create an implementation readiness roadmap;
- whether to split real runtime work into later subphases;
- whether additional sandbox proofs, test plans, or governance docs are required;
- whether future implementation should remain blocked until more review;
- whether developer-facing UI, review flows, or policy docs need planning;
- whether future route governance or capability governance needs more planning;
- whether a stronger production isolation policy is required before any
  implementation.

Phase 3F Planning must not implement anything.

## D. Phase 3F allowed scope

Allowed Phase 3F Planning work (all docs-only):

- docs-only planning;
- inherited-constraints review;
- gap analysis;
- readiness roadmap;
- future-phase decomposition;
- risk review;
- P0 gate consolidation;
- implementation-entry review;
- human-review checklist update;
- route governance planning;
- production-isolation planning;
- audit / redaction planning;
- UI warning and review-flow planning;
- test strategy planning;
- no code changes.

## E. Phase 3F forbidden scope

The following remain explicitly forbidden in Phase 3F Planning unless separately
and explicitly authorized by the project owner:

```
Phase 3F Implementation
real plugin runtime
plugin loader
plugin execution
dynamic loading
importlib runtime loading
__import__ runtime loading
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
provider write
autonomous write
live provider execution
real API key reading
external network
new route
production rollout
```

## F. Inherited Phase 3E constraints

Phase 3F Planning inherits all Phase 3E constraints. None is relaxed by this
authorization.

- **Option A — descriptor-only / no runtime** remains the approved current
  architecture.
- **Option B — in-process execution** remains rejected for real runtime execution.
- **Option C — out-of-process worker** remains the minimum future execution
  baseline, but is **not** authorized for implementation.
- **Option D — containerized isolation** remains deferred and preferred for
  production-grade isolation, but is **not** authorized for implementation.
- All Phase 3E P0 stop conditions remain active.
- All real runtime work remains blocked.
- Route governance counts must remain unchanged.
- Production isolation must remain intact.
- No secrets may be read.
- No external network may be used.
- No provider live request may be issued.
- No route may be added.
- No production rollout may occur.

## G. P0 gate inheritance

Every Phase 3E P0 stop condition remains active and must be inherited by
Phase 3F. A Phase 3F Planning task must not relax any of them:

```
No approved sandbox model means STOP.
No approved process isolation model means STOP.
No approved filesystem boundary model means STOP.
No approved network boundary model means STOP.
No approved supply-chain policy means STOP.
No approved permission model means STOP.
No approved audit/redaction model means STOP.
No approved kill switch means STOP.
No approved production isolation model means STOP.
Any ambiguity in secret handling means STOP.
Any ambiguity in filesystem or network access means STOP.
Any unapproved execution path means STOP.
Any production impact means STOP.
Any new route without route governance approval means STOP.
```

## H. Route governance boundary

Expected route counts (unchanged):

```
OpenAPI paths:        34
Runtime routes:       34
Tool GET:             5
Tool write HTTP route: 0
Tool dry-run route:    1
Tool execution route:  1
New HTTP route:        0
New Tool write route:  0
New Provider route:    0
New plugin route:      0
New runtime route:     0
```

- Phase 3F Planning Authorization does not modify routes.
- Phase 3F Planning must not modify routes unless separately and explicitly
  authorized.
- Phase 3F Implementation remains NO-GO.

## I. Production safety boundary

```
Production Gateway PID 28428 must remain unaffected.
Production Gateway count must remain 1.
Production Gateway must not be stopped, restarted, replaced, signaled, or killed.
Dev Gateway must remain stopped.
Dashboard must remain not started.
Ports 5180/5181 must remain free.
~/.hermes must not be accessed.
production state.db must not be accessed.
```

## J. Authorization decision

```
Decision:
Authorize a later Phase 3F Planning task only.
```

Approval scope:

```
Phase 3F Planning Authorization
future Phase 3F Planning task
docs-only planning
inherited constraints review
no implementation
```

Not approved:

```
Phase 3F Implementation
real plugin runtime
plugin loader
plugin execution
dynamic loading
production rollout
new routes
provider writes
autonomous writes
live provider execution
secret/API-key read
external network execution
```

## K. Next allowed task

The next allowed task is Phase 3F Planning, but only by explicit user request.

The next Phase 3F Planning task must remain docs-only unless the project owner
explicitly overrides this in writing.

Implementation must not start.

## L. Authorization metadata

| Field | Value |
|-------|-------|
| Review type | Phase 3F Planning Authorization |
| Branch | `dev-huangruibang` |
| Source commit reviewed | `65b67d2136b4331b9acb859e531ddfa615e88dc2` |
| Authorization commit | To be filled after commit (see final report) |
| Reviewer | Project owner / human reviewer |
| Decision date | 2026-06-19 |
| Decision | Phase 3F Planning authorized as future docs-only task |
| Implementation authorized | No |
| Production authorized | No |
| Real runtime authorized | No |
| New route authorized | No |

## Cross-references

- [Phase 3F boundary and inherited constraints](phase-3f-boundary-and-inherited-constraints.md) — companion boundary document for a future Phase 3F Planning task.
- [Phase 3E archive index](phase-3e-archive-index.md) — closed and archived Phase 3E record; does not authorize Phase 3F.
- [Phase 3E human review signoff](phase-3e-human-review-signoff.md)
- [Phase 3E review board decision](phase-3e-review-board-decision.md)
- [Phase 3E planning closeout](phase-3e-planning-closeout.md)
- [Phase 3E runtime GO / NO-GO](phase-3e-runtime-go-no-go.md)
- [Phase 3E risk register](phase-3e-risk-register.md)
- [Phase 3E implementation entry criteria](phase-3e-implementation-entry-criteria.md)
- [Phase 3D Phase 3E planning authorization](phase-3d-phase-3e-planning-authorization.md) — prior planning-authorization precedent (docs-only).
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)
