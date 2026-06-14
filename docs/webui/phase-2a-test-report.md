# Phase 2A — Test Report

## 1. Summary

Phase 2A is covered by six new backend test files plus updates to the existing
Phase 1G suite (count/allowlist pins), and two new frontend test files plus a
Playwright smoke profile.

| Gate | Result |
|------|--------|
| Backend regression (existing + Phase 2A) | PASS — 2149 tests, 0 failed |
| Route governance (34/34/5/0/1/1) | PASS |
| ruff (modified + new files) | PASS — clean |
| Frontend type-check (`vue-tsc --noEmit`) | PASS |
| Frontend lint (`eslint`) | PASS — clean |
| Frontend unit tests (`vitest`) | PASS — 692 tests, 0 failed |
| Frontend build (`vite build`) | PASS |
| Playwright smoke `phase2a` profile | added (servers required to run live) |

## 2. New Backend Test Files

| File | Coverage |
|------|----------|
| `test_dev_web_phase_2a_read_only_registry.py` | registry lists exactly 5 tools; single-source STATIC_ALLOWLIST; all tools readOnly/provider=False/write=False/externalSideEffects=False/requiresConfirmation=True; strict-whitelist argument validation (forbidden/path/shell/secret rejected). |
| `test_dev_web_phase_2a_read_only_dry_run.py` | each tool dry-run `would_allow` + correct risk tier; flags all False; static allowlist unmutated; unknown/write/provider tools blocked. |
| `test_dev_web_phase_2a_read_only_execute.py` | each tool completes end-to-end; provider/side-effect flags False; per-tool decision + preview type; full audit-chain IDs; block reasons (allowlist/missing-token/digest-mismatch). Exports `run_read_only_tool_to_completion` helper. |
| `test_dev_web_phase_2a_read_only_audit.py` | dry-run/pre/post audits written per tool; toolId filter isolates one tool; no raw-argument/secret leak; read-only result summary recorded. |
| `test_dev_web_phase_2a_read_only_frontend_contract.py` | selectable-tool list matches STATIC_ALLOWLIST; execute envelope fields; `executionCompleted` boolean completed-signal; toolResult structure; clarify contract unchanged. |
| `test_dev_web_phase_2a_security_boundaries.py` | safety profile per tool; unsupported/write/provider tools not in allowlist; no `~/.hermes`/`state.db` access in source; production PID baseline 1962; no signal/kill/terminate; no secret/callable-repr leak; route governance 34/34/5/0/1/1. |

## 3. New Frontend Test Files

| File | Coverage |
|------|----------|
| `tool-execute-phase-2a.spec.ts` | 6 selectable tools (clarify first); `setCanonicalName` switches + resets; per-tool argument building; each read-only `<toolId>_execution_completed` recognized; blocked on `executionCompleted=false`; raw token never exposed. |
| `tool-execute-panel-phase-2a.spec.ts` | selector renders 6 options; default clarify; read-only tool shows args + hides clarify fields; safety badges render; structured result renders; side-effect flags false; clarify legacy preserved. |

## 4. Updated Existing Tests

The legitimate inventory change (71→76 tools, candidate 6→11, allowlist 1→6,
R0 1→3, R1 5→8) required updating count/allowlist pins across the Phase 1G
suite. These were `STATIC_ALLOWLIST == frozenset({"clarify"})` assertions and
inventory-count assertions in ~20 test files. All updated assertions now pin
the Phase 2A reality; the underlying invariants (static ⊆ candidate, static ∩
denylist = ∅, candidate risks ⊆ {R0,R1}) are unchanged and still asserted.

Note: `test_dev_web_tool_policy_service.py` and `test_dev_web_tool_schema_preview_service.py`
held latent failures at the Phase 1G seal (the seal gate did not include them);
Phase 2A fixed them to assert the correct derived values.

## 5. Smoke Profile

`scripts/run-dev-webui-execute-audit-smoke.sh` gained a `phase2a` profile
(Profile C) and a `tests/smoke/phase-2a-read-only-tools-smoke.spec.ts` spec.
The `all` profile now runs A (blocked) → B (completed) → C (phase2a). The
Production Gateway PID baseline (1962) is unchanged; the harness remains
fail-closed on drift.

## 6. Clarify Preservation

`test_dev_web_phase_2a_read_only_frontend_contract.py::TestClarifyContractUnchanged`
and the end-to-end verification confirm clarify keeps its Phase 1G behavior
exactly: decision `clarify_execution_completed`, previewType `clarify`,
toolResult `{type, message, questions}`.
