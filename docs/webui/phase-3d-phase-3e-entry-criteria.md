# Phase 3D — Phase 3E Entry Criteria

| Field | Value |
|-------|-------|
| Phase | 3D (Closeout) |
| Title | Phase 3E Entry Criteria (from Phase 3D Closeout) |
| Status | Recorded |
| Date | 2026-06-19 |
| Criteria ID | `PHASE-3D-PHASE-3E-ENTRY-CRITERIA-001` |

> Defines the entry conditions for any next phase (Phase 3E) after the Phase 3D
> closeout. Phase 3D closeout does **not** authorize Phase 3E; it only states
> what must hold before Phase 3E may be considered.

## 1. Default readiness

```
Phase 3E Planning readiness:      CONDITIONAL GO
Phase 3E Implementation readiness: NO-GO
Real plugin runtime execution:    NO-GO
```

## 2. Phase 3E Planning (docs-only) — CONDITIONAL GO

Phase 3E **Planning** (docs-only) may be considered **only after explicit user
approval**, and only while **all** of the following hold:

```
Phase 3D closeout completed
P0 = 0
P1 = 0
Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1)
Production Gateway PID 28428 unchanged (count 1)
No ~/.hermes access
No production state.db access
Explicit user approval
Scope limited to planning unless separately authorized
```

## 3. Phase 3E Implementation — NO-GO

Phase 3E **Implementation** is NO-GO by default. It requires separate explicit
user approval **and** a reviewed implementation scope. If Phase 3E would touch a
real runtime, the additional requirements in §4 apply first.

## 4. If Phase 3E concerns a real plugin runtime — additional mandatory prerequisites

Before any real-runtime implementation, **all** of the following must be
completed and approved:

```
new runtime threat model
sandbox model
process isolation model
filesystem boundary model
network boundary model
supply-chain policy
permission review
audit review
UI review
route review
production isolation review
explicit user approval
```

Until these exist, real plugin runtime, plugin loader execution, dynamic
loading, local plugin directory loading, remote registry, marketplace, and
external plugin fetch all remain NO-GO.

## 5. Invariants that must hold at Phase 3E entry

- The descriptor registry remains descriptor-only, disabled-by-default,
  capability-bound, read-only, and dev-only.
- Descriptors bind only to existing Phase 3C capabilityIds.
- No descriptor grants a permission, creates an approval / confirmation /
  dry-run / route, or creates an execution path.
- Route governance stays 34 / 34 / 5 / 0 / 1 / 1.
- Production Gateway PID `28428` (count 1) is unchanged.
- No `~/.hermes` access; no production `state.db` access.

## 6. Cross-references

- [Closeout](phase-3d-closeout.md)
- [Release readiness](phase-3d-release-readiness.md)
- [Real runtime NO-GO](phase-3d-real-runtime-no-go.md)
- [Final security boundary after H1](phase-3d-final-security-boundary-after-h1.md)
- [Phase 3D implementation entry criteria](phase-3d-implementation-entry-criteria.md)
- [Phase 3C → 3D entry criteria](phase-3c-phase-3d-entry-criteria.md)
