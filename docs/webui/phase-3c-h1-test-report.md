# Phase 3C-H1 — Test Report

| Field | Value |
|-------|-------|
| Phase | 3C-H1 (Hardening) |
| Title | Static Capability Registry Hardening Test Report |
| Status | Passing |
| Date | 2026-06-18 |

## 1. Backend hardening tests (8 files)

| File | Coverage |
|------|----------|
| `test_dev_web_phase_3c_h1_manifest_consistency.py` | Backend determinism, 46-entry count, pinned IDs/version, frontend-mirror drift detection (IDs/permission/trust/status/category/forbidden-fields/version), drift-detector self-tests |
| `test_dev_web_phase_3c_h1_forbidden_fields.py` | Top-level + alias + **nested** forbidden-field rejection (dict/list/deep), read-model blocks nested forbidden no-leak, fail-closed summary |
| `test_dev_web_phase_3c_h1_permission_non_grant.py` | No grant/execute symbol, no execution-surface imports, side-effect-free read API, descriptive-only permission, forbidden capabilities blocked |
| `test_dev_web_phase_3c_h1_permission_trust_coherence.py` | Enabled-requires-verified-trust, forbidden-class non-executable, gate coherence (WRITE_CONFIRM/ROLLBACK_CONFIRM/LIVE_PROVIDER_GATED), blocked-requires-reason, first-version invariants |
| `test_dev_web_phase_3c_h1_tool_provider_workflow_mapping.py` | Exact tool/sandbox/rollback + provider (incl. live listed-not-executed) + workflow mapping; registry never satisfies external gates |
| `test_dev_web_phase_3c_h1_no_dynamic_loading.py` | AST no-forbidden-import + no dynamic-exec call + no shell=True + no path-loader; frozen flags; manual one-shot listed-not-executed; forbidden capabilities described-blocked |
| `test_dev_web_phase_3c_h1_audit_no_leak.py` | 10 event types; safe-field set frozen; redaction drops forbidden/bytes/callables/nested; every event-type redacted+no-leak; audit failure never enables registry; production home refused |
| `test_dev_web_phase_3c_h1_status_api_security.py` | `/status` block present (count 46), frozen flags, no-leak, OpenAPI path count 34, no capability/registry route |

## 2. Frontend hardening tests (6 files)

| File | Coverage |
|------|----------|
| `phase3c-h1-registry-mirror.spec.ts` | Mirror count 46, pinned IDs, unique IDs, version, dev-only/not-production, safe field names, forbidden-field set, drift detector |
| `phase3c-h1-registry-panel.spec.ts` | Section/summary/table render, describes-only messaging, five frozen flags, route-governance baseline, validation passed, table select, read-only filters |
| `phase3c-h1-registry-detail.spec.ts` | Drawer renders notice + runtime gates, blocked reason, read-only, no-leak across all 46, close emit |
| `phase3c-h1-registry-badges-a11y.spec.ts` | Every permission/trust/status badge: text label + title attribute + forbidden/not-executable marker (non-color) |
| `phase3c-h1-registry-no-leak.spec.ts` | Section HTML + store + manifest JSON no forbidden token; no API-key input; no production path; safe across filters |
| `phase3c-h1-registry-validation-states.spec.ts` | validation_failed + null summary safe; empty filtered state graceful; blocked reasons visible |

## 3. Smoke (Profile Q)

`tests/smoke/phase-3c-h1-capability-registry-hardening-smoke.spec.ts`
(included in `all`) asserts the 23-point H1 boundary across API + UI.

## 4. Gates

- Hardening audit script `scripts/run-dev-webui-phase3c-hardening-audit.sh`
  → Overall PASS (exit 0).
- Route governance: `test_dev_check_webui.py` + `test_dev_web_0c06_closure.py`
  → 34 / 34 / 5 / 0 / 1 / 1.
- Phase 3C backend tests (160) + H1 backend tests still pass.
- `ruff check` clean on capability modules + H1 tests.
- Frontend `type-check`, `lint`, `test`, `build` pass.
- `memory-check` + `dev-check` PASS (only `.claude/` untracked WARN).

## 5. Production safety

Production Gateway PID 28428 unchanged; dev services 127.0.0.1 only; ports
5180/5181 free before and after; no `~/.hermes` / production `state.db` access.
