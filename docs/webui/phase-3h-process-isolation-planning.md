# Phase 3H Process Isolation Planning

| Field | Value |
|-------|-------|
| Phase | 3H (Sandbox Proof Planning — Process Isolation) |
| Title | Real Plugin Runtime — Phase 3H Process Isolation Planning |
| Planning ID | `PHASE-3H-PLANNING-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Status | Docs-only planning — does **not** create a worker |

> This document is docs-only.
> This document plans process isolation proof requirements only.
> This document does not create a worker process.
> This document does not implement sandbox proof.
> This document does not authorize runtime execution.
> This document does not authorize production rollout.
> This document does not authorize new routes.

## A. Process isolation planning summary

This document plans the process isolation requirements that a future sandbox proof would
need to satisfy. It does not create a worker, does not spawn a process, and does not authorize
implementation. Process isolation implementation remains NO-GO.

## B. Process boundary questions

A future proof would need to answer, as documentation first and then as reproducible
dev-only evidence:

- how a future worker would be isolated from the main process and the gateway;
- how a future worker lifecycle (start, run, stop) would be controlled;
- how a future worker failure would be prevented from affecting the gateway or the main
  process;
- how a future timeout / cancellation would be demonstrated;
- how a future stdout / stderr / log redaction would be planned;
- how a future environment-variable exposure would be prevented (no secret leakage to the
  worker);
- how a future resource limits (CPU, memory, wall-clock, file descriptors) would be planned;
- how a future kill-switch would be linked to the worker lifecycle.

```
These are questions, not answers and not implementation.
```

## C. Required future evidence

A future separately-authorized proof would need to produce, none of which is produced here:

- reproducible process-boundary demonstration (dev-only);
- worker lifecycle control demonstration;
- timeout / cancellation demonstration;
- redacted stdout / stderr demonstration;
- environment-variable no-leak demonstration;
- resource-limit demonstration;
- kill-switch linkage demonstration.

```
This document produces no evidence.
This document only lists what a future proof would need.
```

## D. Stop conditions

```
Worker lifecycle unclear means STOP.
Process boundary unclear means STOP.
Environment-variable leakage unclear means STOP.
Timeout / cancellation unclear means STOP.
Main process / gateway impact unclear means STOP.
```

Any unresolved P0 means STOP toward implementation.

## E. Planning verdict

```
Process isolation implementation remains NO-GO.
This document authorizes no worker, no runtime, no execution, no route, no production change.
```

## Cross-references

- [Phase 3H sandbox proof planning](phase-3h-sandbox-proof-planning.md)
- [Phase 3H sandbox model options](phase-3h-sandbox-model-options.md)
- [Phase 3H kill-switch planning](phase-3h-kill-switch-planning.md)
- [Phase 3H GO / NO-GO](phase-3h-go-no-go.md)
