# Phase 3E — Production Isolation Review

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — Production Isolation Review (Frozen) |
| Status | Frozen (docs-only planning; Real Plugin Runtime **not started**) |
| Date | 2026-06-19 |
| Planning ID | `PHASE-3E-PLANNING-001` |
| Production-Isolation ID | `PHASE-3E-PRODUCTION-ISOLATION-001` |

> This document reviews — but does **not** change — production isolation for the
> real plugin runtime surface. No implementation is authorized.

## 1. Position

```
No production access.
No ~/.hermes access.
No production state.db access.
No production rollout.
No production process signal.
No production Gateway restart.
No production config read.
No production secret read.
```

## 2. Baseline recorded

```
Production Gateway PID baseline = 28428
Production Gateway count baseline = 1
Dev Gateway final must remain stopped
Dashboard final must remain not started
5180 / 5181 must remain free
```

These were verified unchanged at planning start (Production Gateway PID `28428`,
count `1`; Dev Gateway `stopped`; ports `5180` / `5181` free). This phase is
docs-only; it cannot affect any of them.

## 3. Runtime production-isolation rules (future)

A future runtime would be constrained to:

```
devOnly = true
productionAllowed = false
dev HERMES_HOME sandbox only (enforce_dev_environment() allowlist inherited)
fail-closed in production HERMES_HOME
no ~/.hermes access
no production state.db access
no production config / secret read
kill switch enforced before any production-capable path
```

If a future runtime were ever reachable from a production `HERMES_HOME`, that is
a hard stop (RUNTIME-P0-21 / RUNTIME-P0-22 / RUNTIME-THREAT-24).

## 4. Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E route governance review](phase-3e-route-governance-review.md)
- [Phase 3D production isolation summary](phase-3d-production-isolation-summary.md)
- [Phase 3C production isolation summary](phase-3c-production-isolation-summary.md)
