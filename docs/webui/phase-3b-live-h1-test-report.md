# Phase 3B-Live-Enablement H1 — Test Report

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement H1 (Hardening) |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |
| Report ID | `HARDENING-3B-LIVE-H1-001` |

## 1. Backend hardening tests (8 files)

| File | Cases | Status |
|------|-------|--------|
| `test_dev_web_phase_3b_live_h1_approval_hardening.py` | 17 | PASS |
| `test_dev_web_phase_3b_live_h1_secret_gate_hardening.py` | 13 | PASS |
| `test_dev_web_phase_3b_live_h1_network_hardening.py` | 22 | PASS |
| `test_dev_web_phase_3b_live_h1_budget_hardening.py` | 16 | PASS |
| `test_dev_web_phase_3b_live_h1_kill_switch_hardening.py` | 11 | PASS |
| `test_dev_web_phase_3b_live_h1_roundtrip_hardening.py` | 30 | PASS |
| `test_dev_web_phase_3b_live_h1_audit_hardening.py` | 24 | PASS |
| `test_dev_web_phase_3b_live_h1_api_security.py` | 14 | PASS |

Coverage: TTL boundary, single-use idempotency, scope/mode/match tampering,
value-free approval + store, dev-only / corrupt fail-closed; secret-read gate
ordering with an env spy; scheme/private-IP/redirect/allowlist boundaries;
request/token/output/budget cap boundaries + counter fail-closed; 14 triggers +
clear-is-not-approval + corrupt-defaults-inactive; gate ordering on the
evaluate surface + single-use invalidation + no-tool-execution + forbidden
suggestion kill + secret-in-content kill; 18 event types + defensive
re-redaction + production-home fail-closed; route governance 34/34 + no
`provider_live` route + no-leak sweep.

## 2. Frontend hardening tests (5 files)

| File | Cases | Status |
|------|-------|--------|
| `phase3b-live-h1-status-ui.spec.ts` | 5 | PASS |
| `phase3b-live-h1-approval-ui.spec.ts` | 6 | PASS |
| `phase3b-live-h1-budget-ui.spec.ts` | 5 | PASS |
| `phase3b-live-h1-kill-switch-ui.spec.ts` | 8 | PASS |
| `phase3b-live-h1-no-leak-ui.spec.ts` | 3 | PASS |

## 3. Smoke / E2E

| Profile | Spec | Status |
|---------|------|--------|
| `phase3b_live_h1_hardening` | `phase-3b-live-h1-hardening-smoke.spec.ts` | PASS |
| `phase3b_live_enablement_boundary` | `phase-3b-live-enablement-boundary-smoke.spec.ts` | PASS |

The manual one-shot live profile was **not** run and is not in `all`.

## 4. Static gates

| Gate | Status |
|------|--------|
| `ruff check` (new files) | PASS |
| `python -m compileall hermes_cli` | PASS |
| `vue-tsc --noEmit` (type-check) | PASS |
| `eslint .` (lint) | PASS |
| `vite build` | PASS |
| Route governance (`test_dev_check_webui` + `test_dev_web_0c06_closure`) | PASS (34/34/5/0/1/1) |
| Preservation: Phase 3B / 3B-H1 / Live Enablement tests | PASS |
| Hardening audit script | PASS (Overall PASS, exit 0) |

## 5. Default-path safety assertions

- Default tests / smoke did **not** read any real API key.
- Default tests / smoke did **not** perform any real provider network call.
- No real live request was executed.
- Production Gateway PID `28428` unchanged; ports 5180 / 5181 free afterward.

## 6. Cross-references

- [H1 hardening overview](phase-3b-live-h1-hardening.md)
- [Security boundary](phase-3b-live-enablement-security-boundary.md)
