# Phase 3C — Risk Closure

| Field | Value |
|-------|-------|
| Phase | 3C (Closeout) |
| Title | Static Capability Registry — Risk Closure |
| Status | Closed |
| Date | 2026-06-18 |

## 1. Summary

| Severity | Count open | Blocking? |
|----------|------------|-----------|
| **P0** | **0** | n/a |
| **P1** | **0** | n/a |
| **P2** (deferred) | 1 — frontend TS manifest mirror generator | No (drift bounded by the H1 consistency test) |

**No P0. No P1.** Every Phase 3C P0 stop condition remains closed.

## 2. P0 stop conditions (all CLOSED)

| ID | Condition | Status |
|----|-----------|--------|
| `CAP-P0-01` | Dynamic plugin loading introduced | CLOSED — none |
| `CAP-P0-02` | External marketplace or remote registry introduced | CLOSED — none |
| `CAP-P0-03` | Capability grants permission instead of describing permission | CLOSED — descriptive only |
| `CAP-P0-04` | Write capability bypasses dry-run / confirmation | CLOSED — registry never executes; gates still required |
| `CAP-P0-05` | Provider live gate bypassed | CLOSED — registry never invokes the live path |
| `CAP-P0-06` | Shell / database / external HTTP capability exposed | CLOSED — described as blocked only |
| `CAP-P0-07` | Production operation exposed | CLOSED — described as blocked only |
| `CAP-P0-08` | `~/.hermes` or production `state.db` accessed | CLOSED — never accessed |
| `CAP-P0-09` | Route governance drift | CLOSED — 34 / 34 / 5 / 0 / 1 / 1 |
| `CAP-P0-10` | Secret / callable / path leak in registry or UI | CLOSED — no-leak; reinforced by recursive scan |
| `CAP-P0-11` | Runtime artifact committed | CLOSED — none committed |
| `CAP-P0-12` | `.claude/` committed | CLOSED — never staged |

## 3. Real defect found and closed

**Nested forbidden field leaked through the read model.** The Phase 3C
forbidden-field scanner was shallow, so a forbidden field nested inside an
allowed field's value (e.g.
`{"metadataSchema": {"shellCommand": "rm -rf", "secret": "leak",
"Authorization": "Bearer x"}}`) could pass validation and be exposed verbatim
by the read model.

**Fixed in Phase 3C-H1** by:
1. a **recursive forbidden-field scan** (top-level keys + any nested dict /
   list / tuple), and
2. a **scalar-string type guard** (scalar fields must be string scalars).

**Status: CLOSED.** All 160 Phase 3C backend tests still pass; 8 H1 backend
test files + 6 H1 frontend test files pin the fix. CAP-P0-10 is reinforced:
three independent layers now enforce the forbidden-field boundary.

## 4. P2 deferred

**Frontend TS manifest mirror generator.** The frontend mirror
(`constants/capabilityRegistryManifest.ts`) is a tracked, hand-maintained copy
of the backend manifest. A generator that derives it from the backend would
remove the manual sync step. Drift is **bounded** by the H1 manifest-
consistency test, which fails closed if the two diverge. This is a
non-blocking P2, not a defect.

## 5. Phase 3D risk posture

Phase 3D (Plugin Runtime) is **not started**. Any future Phase 3D carries its
own P0/P1 risk register, threat model, and GO/NO-GO. The dynamic-loading,
remote-registry, and marketplace risks are explicitly **NO-GO** until a
separately authorized security model exists.

## 6. Cross-references

- [Final acceptance](phase-3c-final-acceptance.md)
- [Final security boundary](phase-3c-security-boundary-final.md)
- [Known limitations / deferred work](phase-3c-known-limitations-and-deferred-work.md)
- [Phase 3C risk register](phase-3c-security-risk-register.md)
- [Post-sealing risk inventory](phase-1g-05-risk-register.md)
