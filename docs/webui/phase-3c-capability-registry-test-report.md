# Phase 3C — Capability Registry Test Report

| Field | Value |
|-------|-------|
| Phase | 3C (Implementation) |
| Title | Static Capability Registry Test Report |
| Status | Passing |
| Date | 2026-06-17 |

## 1. Backend tests (160)

| File | Coverage |
|------|----------|
| `test_dev_web_phase_3c_capability_schema.py` | Frozen taxonomies, predicates, field sets, capabilityId format |
| `test_dev_web_phase_3c_capability_manifest.py` | Determinism, no forbidden field, devOnly/productionAllowed, required capabilities, provider/workflow/forbidden mapping, no execution surface |
| `test_dev_web_phase_3c_capability_validation.py` | Required/enum/unique/unknown-field rejection, every forbidden field rejected, first-version invariants, determinism |
| `test_dev_web_phase_3c_capability_policy.py` | Composition rules, gate coherence, forbidden-class non-executability, READ_ONLY no-write-gate |
| `test_dev_web_phase_3c_capability_status_api.py` | `/status` block present, frozen flags, route governance 34, no leak, GET-only |
| `test_dev_web_phase_3c_capability_audit.py` | Event types, payload redaction, dev-home write, forbidden-field never persisted, fail-safe, no production home |
| `test_dev_web_phase_3c_capability_no_dynamic_loading.py` | Frozen flags, AST-based no-importlib/subprocess/network scan, static-manifest-only |
| `test_dev_web_phase_3c_capability_security.py` | Read-model no-leak, no network/production access, fail-closed summary, blocked detail |

## 2. Frontend tests

`phase3c-capability-registry-{panel,summary,table,detail,no-leak,badges}.spec.ts`
cover rendering, frozen flags, badges (non-color), blocked reasons, the
describes-only notice, and the full no-leak scan (every capability detail).

The two Phase 2E accessibility specs that count nav tabs were updated 8 → 9
(the new "Capability Registry" section).

## 3. Smoke (Profile P)

`tests/smoke/phase-3c-capability-registry-smoke.spec.ts` (included in `all`)
asserts: `/status` block present, frozen flags false, route governance
unchanged, validation passed, no-leak, no capability route, and the UI panel
renders with no leak.

## 4. Gates

- Route governance: `tests/test_dev_check_webui.py` + `tests/test_dev_web_0c06_closure.py` → OpenAPI 34 / runtime 34 / 5/0/1/1.
- `ruff check` clean on all new modules + tests.
- Frontend `type-check`, `lint`, `test` (1058), `build` all pass.
- `memory-check` + `dev-check` PASS (only `.claude/` untracked WARN).

## 5. Production safety

Production Gateway PID 28428 unchanged; dev services 127.0.0.1 only; ports
5180/5181 free before and after; no `~/.hermes` / production `state.db` access.

---

## 6. Phase 3C-H1 Hardening Update (2026-06-18)

`HARDENING-3C-H1-001` added 8 backend hardening test files + 6 frontend
hardening test files + a new smoke profile (Profile Q,
`phase3c_h1_capability_registry_hardening`) + the hardening audit script
`scripts/run-dev-webui-phase3c-hardening-audit.sh`. One real defect was fixed
(recursive forbidden-field scan + scalar type guard). All Phase 3C tests (160)
still pass. See [Phase 3C-H1 test report](phase-3c-h1-test-report.md).
