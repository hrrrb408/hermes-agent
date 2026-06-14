# Phase 2C — Write Test Report

## Backend tests

Eight new Phase 2C test files, all run via the hermetic wrapper
(`scripts/run_tests.sh`, per-file subprocess isolation, clean env):

| File | Coverage |
|------|----------|
| `test_dev_web_phase_2c_write_registry.py` | allowlist exact (4), read-only frozen (6), unified (10), disjointness, safety profile, argument validation (binary / forbidden / unknown / missing) |
| `test_dev_web_phase_2c_write_sandbox.py` | sandbox root, production-home block, traversal / absolute / symlink escape / forbidden / file-type / depth / length, size + binary, write/append/patch/readback IO, sha256, diff |
| `test_dev_web_phase_2c_write_plan.py` | before/after hashes, diff + rollback preview, digest stability, precise blocked reasons, preview-issues-token, preview-does-not-write, redaction |
| `test_dev_web_phase_2c_write_execute.py` | enablement gate, confirmation (missing / wrong / replay), digest mismatch, 4 handlers, rollback manifest, audit ids, side-effect flags, no raw args, sandbox-only |
| `test_dev_web_phase_2c_write_audit.py` | lifecycle events (pre/post/rollback/blocked), redaction (secrets + callables), no raw args, `auditKind=write` queryable via the audit route |
| `test_dev_web_phase_2c_write_rollback.py` | delete vs restore modes, restore preview, validation, redaction, hash carry-through |
| `test_dev_web_phase_2c_provider_write_preview.py` | preview-not-executed, no file written, plan+token present, API branch blocked, real-provider-write blocked |
| `test_dev_web_phase_2c_write_security.py` | write-outside-sandbox sweep, forbidden targets, oversized/binary, source inspection (no shell/db/external/prod-access), route governance 34/34/5/0/1/1, provider-write boundary, audit redaction, Phase 1G/2A/2B preservation |

**Result: 185 tests, 0 failed.**

## Frontend tests

- `src/tests/tool-write-panel.spec.ts` — panel render, 4-tool selector, safety
  flags, target-path validation (absolute / traversal / `.env`), content input,
  execute-disabled-before-confirmation, execute-enabled-after-confirm, diff +
  rollback preview, result/rollback/audit-id surface, blocked reason, no API
  key / shell input.
- `workspace-panel.spec.ts` / `accessibility.spec.ts` / `ui-store.spec.ts`
  updated for the new `write` tab (8 tabs).

**Result: 721 vitest tests pass; `vue-tsc -b` build + eslint clean.**

## Smoke / E2E

New profile `phase2c_write_sandbox` in
`scripts/run-dev-webui-execute-audit-smoke.sh` (exports
`HERMES_TOOL_WRITE_EXECUTION_ENABLED=true` only for that profile; cleaned on
script exit). New spec
`tests/smoke/phase-2c-write-sandbox-smoke.spec.ts` covers preview → execute →
audit → readback → provider-write-not-auto-executed, plus a UI check. The
`all` profile runs blocked / completed / phase2a / phase2b /
phase2c_write_sandbox.

## Preservation gates

- Route governance: **OpenAPI 34 / runtime 34 / Tool GET 5 / Tool write route
  0 / Tool dry-run route 1 / Tool execution route 1** (unchanged).
- Phase 1G / 2A / 2B suites: 0 failed.
- Full related backend regression: 0 failed.

## PID baseline refresh

An external gateway restart during the session moved the live PID
`1962 → 28428`. Under user authorization, the PID baseline constant was
refreshed `1962 → 28428` (code, smoke harness, tests). The pre-existing
`test_real_adapter_blocked_even_when_enabled` test (which gates on the live
PID matching the baseline) now passes.
