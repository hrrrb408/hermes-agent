# Phase 3D — Known Limitations / Deferred Work

| Field | Value |
|-------|-------|
| Phase | 3D (Closeout) |
| Title | Static Plugin Descriptor Registry — Known Limitations / Deferred Work |
| Status | Recorded |
| Date | 2026-06-19 |
| Summary ID | `PHASE-3D-KNOWN-LIMITATIONS-001` |

> The intentionally deferred / out-of-scope items for the Phase 3D Static Plugin
> Descriptor Registry. **These are intentional deferrals, not unfinished
> defects.** Each governs a possible future runtime and is NO-GO until that
> runtime is separately authorized.

## 1. Deferred items

1. No real plugin runtime.
2. No plugin loader execution.
3. No plugin execution.
4. No dynamic loading.
5. No `importlib` / `__import__` dynamic import.
6. No local plugin directory loading.
7. No remote registry.
8. No marketplace.
9. No external plugin fetch.
10. No provider-generated plugin.
11. No LLM-generated plugin install.
12. No production rollout.
13. No executable plugin sandbox.
14. No plugin process isolation.
15. No plugin filesystem-boundary implementation.
16. No plugin network-boundary implementation.
17. No plugin package / supply-chain policy.
18. No plugin version migration.
19. No multi-user plugin ownership.
20. Generated frontend descriptor mirror may remain deferred if not implemented
    (a hand-maintained mirror is in place today; drift is bounded by a
    consistency test).

## 2. Why these are deferred

The first version is deliberately **descriptor-only**. There is nothing to
execute, nothing to sandbox, nothing to isolate, and nothing to fetch. Adding any
of the above without a separate planning phase, threat model, and isolation /
supply-chain policy would create an execution surface that the Phase 3D
architecture explicitly forbids. Each deferred item is recorded in the risk
register as a P2 (intentional, non-blocking) or a P0 stop condition (if it were
ever introduced without authorization).

## 3. Hand-maintained mirror (P2 drift control)

The frontend `constants/pluginDescriptorRegistryManifest.ts` mirrors the backend
12-descriptor manifest by hand. A generator that derives this mirror from the
backend is deferred (PLUG-P2-01). Drift is bounded by a manifest-consistency test
(Phase 3D + H1 manifest-consistency tests, PASS).

## 4. Cross-references

- [Closeout](phase-3d-closeout.md)
- [Risk closure after H1](phase-3d-risk-closure-after-h1.md)
- [Real runtime NO-GO](phase-3d-real-runtime-no-go.md)
- [Final security boundary after H1](phase-3d-final-security-boundary-after-h1.md)
- [Phase 3E entry criteria](phase-3d-phase-3e-entry-criteria.md)
