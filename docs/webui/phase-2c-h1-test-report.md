# Phase 2C-H1 — Test Report

## Backend tests

Seven new Phase 2C-H1 test files, run via the hermetic wrapper:

| File | Coverage |
|------|----------|
| `test_dev_web_phase_2c_h1_confirmation_store.py` | file-backed create/load, plain secret not stored, full tokenHash not exposed, scope/digest/TTL enforced, single-use persists across reload, cleanup safe (no symlink / no non-token / no production) |
| `test_dev_web_phase_2c_h1_confirmation_ttl.py` | expired blocked, default TTLs (10/10/5), max cap, scope isolation (write↔rollback↔provider), digest binding, replay-after-reload |
| `test_dev_web_phase_2c_h1_rollback_store.py` | save/load/list/mark_executed, rollbackId traversal blocked, tamper rejected, beforeContent stored internally + redacted, production home rejected |
| `test_dev_web_phase_2c_h1_rollback_execute.py` | delete_created_file + restore_previous_content work; current-hash mismatch, already-executed, write-disabled, missing-confirmation, digest-mismatch, symlink-escape, outside-sandbox all blocked |
| `test_dev_web_phase_2c_h1_rollback_audit.py` | rollback lifecycle events (pre/handler/post/marked), ids carried, no token secret / no beforeContent leak, blocked event |
| `test_dev_web_phase_2c_h1_provider_write_boundary.py` | provider write preview no auto-execute, API branch blocked, real provider blocked, rollback token cannot write |
| `test_dev_web_phase_2c_h1_write_hardening.py` | write token file-backed + scope-isolated from rollback, route governance 34/34/5/0/1/1, source inspection (no shell/db/external/prod-IO), Phase 1G/2A/2B preservation |

**Result: 79 tests, 0 failed.**

Two Phase 2C assertions were updated to reflect the hardening: the unified
allowlist now includes the rollback tool (11 members), and write-token replay
now reports the granular `blocked_write_confirmation_already_used` reason.

## Frontend tests

- `src/tests/tool-write-panel.spec.ts` extended: rollback id input, preview
  button gating, replay-blocked + expired-token messages, execute-disabled
  before confirmation. **726 vitest tests pass; `vue-tsc -b` build + eslint
  clean.**

## Smoke / E2E

New profile `phase2c_h1_rollback_and_token_ttl` (same gates as the write
profile + write enablement) and new spec
`tests/smoke/phase-2c-h1-rollback-and-token-ttl-smoke.spec.ts`: write →
rollback preview (token TTL visible) → rollback execute (delete + restore) →
token replay blocked → audit viewer surfaces rollback events → provider write
preview still no auto-execute → UI rollback section visible. The `all` profile
runs all six profiles.

## Preservation gates

- Route governance: **OpenAPI 34 / runtime 34 / Tool GET 5 / Tool write route
  0 / Tool dry-run route 1 / Tool execution route 1** (unchanged).
- Phase 1G/2A/2B/2C suites: 0 failed.
- Production Gateway PID baseline: **28428** (carried from Phase 2C; unchanged
  by this work).
