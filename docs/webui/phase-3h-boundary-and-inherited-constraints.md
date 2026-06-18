# Phase 3H Boundary and Inherited Constraints

| Field | Value |
|-------|-------|
| Phase | 3H (Sandbox Proof Planning Boundary) |
| Title | Real Plugin Runtime — Phase 3H Boundary and Inherited Constraints |
| Boundary ID | `PHASE-3H-BOUNDARY-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Status | Docs-only boundary record — does **not** start Phase 3H Sandbox Proof Planning |

> This document is docs-only.
> This document records inherited constraints for future Phase 3H Sandbox Proof Planning.
> This document does not start Phase 3H Sandbox Proof Planning.
> This document does not authorize implementation.
> This document does not authorize sandbox proof implementation.
> This document does not authorize real plugin runtime.
> This document does not authorize production rollout.
> This document does not authorize new routes.

## A. Inherited phase state

```
Phase 3E = CLOSED / ARCHIVED
Phase 3F = CLOSED / ARCHIVED
Phase 3G = CLOSED / ARCHIVED
Implementation Authorization = NO-GO
Phase 3H Sandbox Proof Planning Authorization = GO
Phase 3H Sandbox Proof Planning = NOT STARTED
Phase 3H Implementation = NO-GO
Real plugin runtime = NO-GO
New route = NO-GO
Production rollout = NO-GO
```

- Phase 3G Archive / Index is COMPLETE, so Phase 3G is treated as CLOSED / ARCHIVED.
- Phase 3H Sandbox Proof Planning may begin only after an explicit user request.
- This document does not itself start Phase 3H Sandbox Proof Planning.
- Phase 3H Implementation remains NO-GO.

## B. Inherited NO-GO list

The following remain NO-GO / not authorized:

```
Phase 3H Implementation
Phase 3G Implementation
Phase 3F Implementation
Phase 3E Implementation
sandbox proof implementation
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

```
Each item above remains NO-GO / not approved.
This list is non-authorizing by construction.
```

## C. Inherited P0 gates

- 24 P0 gates remain unresolved.
- Phase 3H planning authorization does not resolve them.
- Future Phase 3H planning may define proof plans for them.
- Future Phase 3H planning may not implement proof artifacts.

```
Total P0 gates:    24
Resolved P0 gates: 0
Unresolved P0:     24
Any unresolved P0 means STOP.
```

See [phase-3g-p0-gate-resolution-review](phase-3g-p0-gate-resolution-review.md)
and [phase-3f-p0-gate-consolidation](phase-3f-p0-gate-consolidation.md).

## D. Sandbox proof planning boundary

A future Phase 3H Sandbox Proof Planning task may discuss, as documentation only:

- proof goals;
- proof assumptions;
- proof non-goals;
- sandbox candidate models;
- process-boundary planning;
- filesystem-boundary planning;
- network-boundary planning;
- capability-boundary planning;
- audit / redaction planning;
- kill-switch planning;
- failure-mode planning;
- rollback planning;
- human-review planning.

The future planning must not:

```
create a worker;
create a runtime;
create a loader;
execute plugins;
load plugins dynamically;
mutate files;
mutate the DB;
call external HTTP;
read secrets;
add routes;
start production rollout.
```

## E. Route and production boundary

Route baseline (unchanged):

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

Production safety baseline (unchanged):

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

- No route definition may be modified.
- No production process may be affected.

## F. Future task boundary

```
Phase 3H Sandbox Proof Planning requires a separate explicit user request.
Even when executed, Phase 3H Sandbox Proof Planning must remain docs-only.
Phase 3H Implementation remains NO-GO.
```

## Cross-references

- [Phase 3H sandbox proof planning](phase-3h-sandbox-proof-planning.md) — the Phase 3H Sandbox Proof Planning task (docs-only). It respects every boundary recorded here and changes none.
- [Phase 3H sandbox proof planning authorization](phase-3h-sandbox-proof-planning-authorization.md) — the authorization that permits a future docs-only Phase 3H Sandbox Proof Planning task.
- [Phase 3H GO / NO-GO](phase-3h-go-no-go.md)
- [Phase 3G archive index](phase-3g-archive-index.md)
- [Phase 3F boundary and inherited constraints](phase-3f-boundary-and-inherited-constraints.md)
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)
