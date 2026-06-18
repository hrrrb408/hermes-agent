# Phase 3H Production Isolation Constraints

| Field | Value |
|-------|-------|
| Phase | 3H (Sandbox Proof Planning — Production Isolation Constraints) |
| Title | Real Plugin Runtime — Phase 3H Production Isolation Constraints |
| Planning ID | `PHASE-3H-PLANNING-001` |
| Date | 2026-06-19 |
| Branch | `dev-huangruibang` |
| Status | Docs-only planning — does **not** touch production |

> This document is docs-only.
> This document records production-isolation constraints on sandbox proof only.
> This document does not access production.
> This document does not implement sandbox proof.
> This document does not authorize runtime execution.
> This document does not authorize production rollout.
> This document does not authorize new routes.

## A. Production isolation summary

This document records the production-isolation constraints that apply to any future sandbox
proof. It does not touch any production process, file, or database. Production rollout remains
NO-GO.

## B. Current production safety baseline

```
Production Gateway expected PID: 28428
Production Gateway count:        1
Dev Gateway:                     stopped
Dashboard:                       not started
Ports 5180 / 5181:               free
~/.hermes:                       not accessed
production state.db:             not accessed
```

```
This baseline is unchanged by this planning.
```

## C. Future proof constraints

Any future sandbox proof planning or proof must be:

- dev-only;
- no production process impact;
- no production state access;
- no `~/.hermes`;
- no production secrets;
- no route changes;
- no dashboard start;
- no gateway restart.

```
None of these constraints is relaxed by this planning.
```

## D. Stop conditions

```
Production PID changes means STOP.
Production state access means STOP.
~/.hermes access means STOP.
Gateway restart means STOP.
Dashboard start means STOP.
```

Any unresolved P0 means STOP toward implementation.

## E. Planning verdict

```
Production rollout remains NO-GO.
This document authorizes no production access, no production change, no runtime, no route.
```

## Cross-references

- [Phase 3H sandbox proof planning](phase-3h-sandbox-proof-planning.md)
- [Phase 3H filesystem boundary planning](phase-3h-filesystem-boundary-planning.md)
- [Phase 3H GO / NO-GO](phase-3h-go-no-go.md)
- [Phase 3F production isolation planning](phase-3f-production-isolation-planning.md)
