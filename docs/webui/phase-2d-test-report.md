# Phase 2D — Test Report

## Backend tests (Phase 2D)

10 new test files, all passing:

| File | Focus |
|------|-------|
| `test_dev_web_phase_2d_audit_schema.py` | canonical schema, `audit_schema_v2`, required fields, enumerations, validation |
| `test_dev_web_phase_2d_audit_sanitizer.py` | unified redaction, `str()` fallback closed, PEM/bearer/sk-*/hash redaction, callable scrub |
| `test_dev_web_phase_2d_audit_store.py` | append durability, monotonic sequence, unique eventId, concurrent writes, path containment |
| `test_dev_web_phase_2d_audit_index.py` | build / update / rebuild-when-missing / repair-when-stale / equality query |
| `test_dev_web_phase_2d_audit_query.py` | cursor pagination, offset compat, filters, safe search, cursor tamper / mismatch / limit rejection |
| `test_dev_web_phase_2d_audit_rotation.py` | rotation by size + count, monotonic segments, query across segments, non-overwrite |
| `test_dev_web_phase_2d_audit_recovery.py` | corruption detection (all classes), quarantine non-destructive, query skips corrupt |
| `test_dev_web_phase_2d_audit_api.py` | store-mode response shape, filters, cursor, legacy compat, route governance, no-leak |
| `test_dev_web_phase_2d_audit_integration.py` | dual-write bridge for all 7 audit kinds + query readback |
| `test_dev_web_phase_2d_audit_security.py` | P0 security: no secret/token/hash/raw-args/callable on disk or in output, confinement, gitignore |

**Result: 196 tests, 0 failed.**

## Preservation tests (Phase 1G / 2A / 2B / 2C / 2C-H1)

The dual-write bridge + API enhancement must not regress prior phases.

**Result: 1120 tests across 34 files, 0 failed.** Existing audit/writer/route
tests continue to pass unchanged.

## Route governance (unchanged)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 34 |
| Runtime routes | 34 |
| Tool GET | 5 |
| Tool write HTTP route | 0 |
| Tool dry-run route | 1 |
| Tool execution route | 1 |

No new HTTP route, no Tool write HTTP route. The audit-events route remains
GET-only.

## Frontend gates

| Gate | Result |
|------|--------|
| `vue-tsc --noEmit` | pass |
| ESLint | pass |
| Vitest (incl. new `tool-audit-store-v2.spec.ts`) | 737 tests pass |
| `vite build` | pass |

New frontend coverage: store-mode toggle, cursor pagination, filters, safe
search, store/index status badges, redactionApplied visibility, corruption
warning, no raw secret / callable / raw-args in store state.

## Smoke / E2E

New profile `phase2d_audit_store_indexing` added to
`scripts/run-dev-webui-execute-audit-smoke.sh`; included in the `all` profile.
Spec: `tests/smoke/phase-2d-audit-store-indexing-smoke.spec.ts`. The Production
Gateway PID baseline (28428) is unchanged by the smoke harness.

## Boundary searches

- No runtime artifacts (audit-store / token / rollback / JSONL) staged.
- Secret terms appear only in security docs, sanitizer rules, negative assertions, and test names.
- No shell command execution / database mutation / external service write introduced.
- No production `~/.hermes` or `state.db` access.
- `.claude/` not committed.
