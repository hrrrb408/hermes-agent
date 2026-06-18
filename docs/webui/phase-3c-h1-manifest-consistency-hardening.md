# Phase 3C-H1 — Manifest Consistency Hardening

| Field | Value |
|-------|-------|
| Lens | 1 — Static Manifest Determinism / Mirror Consistency |
| Hardening ID | `CAP-MANIFEST-3C-H1-001` |
| Status | PASS |

## Scope

The backend static manifest must be deterministic, and the tracked frontend TS
mirror must not drift from it. The mirror is a hand-maintained copy (a
generator is P2-deferred), so drift must be bounded by a test.

## Evidence

- Backend: 46 entries, `MANIFEST_VERSION = "phase3c-static-v1"`, pinned
  timestamps, tuple-of-dicts, deterministic across calls.
- Frontend mirror: 46 entries, same version, same forbidden-field set.

## Commands

```bash
./scripts/run_tests.sh tests/test_dev_web_phase_3c_h1_manifest_consistency.py
```

## Findings

No drift existed, but no test bounded it. Added a drift detector that parses
the TS mirror and asserts capability IDs (ordered), permission-class /
trust-level / status / category sets, the forbidden-field set, and the
registry version all match the backend exactly.

## Fixes

Test-only (`test_dev_web_phase_3c_h1_manifest_consistency.py`). No
implementation change. The generator remains P2-deferred — drift is now
bounded.

## Residual risk

P2: the mirror is still a tracked copy. A generator would remove the manual
sync step entirely; until then, the consistency test fails closed on any
drift.
