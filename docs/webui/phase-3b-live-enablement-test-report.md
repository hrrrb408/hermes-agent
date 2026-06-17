# Phase 3B-Live-Enablement — Test Report

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Implementation) |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |
| Report ID | `PHASE-3B-LIVE-ENABLEMENT-TEST-001` |

## 1. Backend unit tests (8 files, 115 cases)

| File | Cases | Status |
|------|-------|--------|
| `test_dev_web_phase_3b_live_approval.py` | 18 | PASS |
| `test_dev_web_phase_3b_live_secret_policy.py` | 10 | PASS |
| `test_dev_web_phase_3b_live_network_allowlist.py` | 22 | PASS |
| `test_dev_web_phase_3b_live_budget_policy.py` | 16 | PASS |
| `test_dev_web_phase_3b_live_audit_policy.py` | 28 | PASS |
| `test_dev_web_phase_3b_live_kill_switch.py` | 10 | PASS |
| `test_dev_web_phase_3b_live_roundtrip.py` | 8 | PASS |
| `test_dev_web_phase_3b_live_api_security.py` | 13 | PASS |

Coverage: default-missing blocked, value-free approval, 5-min TTL, single-use +
invalidation, scope/match mismatch, dev-only store, blocked-before-secret-read
on every gate, value-free secret state, openai-only allowlist, http/file/
localhost/private-IP/redirect blocking, frozen caps, request/token/budget caps,
retry-zero, counter corruption fail-closed, 18 audit event types, redaction-
before-write, 14 kill-switch triggers, kill-switch-blocks-before-network,
completed one-shot, no tool execution for first live, write-tool kill, route
governance unchanged, no-leak in persisted JSONL + rendered UI.

## 2. Frontend unit tests (5 files, 22 cases)

| File | Cases | Status |
|------|-------|--------|
| `phase3b-live-enablement-status.spec.ts` | 5 | PASS |
| `phase3b-live-enablement-approval.spec.ts` | 5 | PASS |
| `phase3b-live-enablement-no-leak.spec.ts` | 4 | PASS |
| `phase3b-live-enablement-kill-switch.spec.ts` | 4 | PASS |
| `phase3b-live-enablement-budget.spec.ts` | 4 | PASS |

Coverage: disabled-by-default rendering, approval-required/single-use/TTL,
frozen caps, tool-execution-disabled, kill-switch banner, no API-key input, no
Authorization/Bearer/raw-token/callable-repr/production-path leak in any state.

## 3. Smoke / E2E

| Profile | Spec | Status |
|---------|------|--------|
| `phase3b_live_enablement_boundary` | `phase-3b-live-enablement-boundary-smoke.spec.ts` | PASS (6/6) |

Verified: live status surfaced + disabled by default + approval-required,
frozen caps render, real-mode round-trip blocked without approval
(`externalNetworkCalled=false`), value-free boundary, route governance unchanged
(34 paths, no `provider_live` route), Provider panel renders live status with no
API-key input. The manual one-shot profile was **not** run and is not in `all`.

## 4. Static gates

| Gate | Status |
|------|--------|
| `ruff check` (new files) | PASS |
| `python -m compileall hermes_cli` | PASS |
| `vue-tsc --noEmit` (type-check) | PASS |
| `eslint .` (lint) | PASS |
| `vite build` | PASS |
| Route governance (`test_dev_check_webui` + `test_dev_web_0c06_closure`) | PASS (124) |
| Preservation: Phase 3B / 3B-H1 provider tests | PASS (129) |

## 5. Default-path safety assertions

- Default tests / smoke did **not** read any real API key.
- Default tests / smoke did **not** perform any real provider network call.
- No real live request was executed.
- Production Gateway PID `28428` unchanged; ports 5180 / 5181 free afterward.

## 6. Cross-references

- [Live enablement implementation](phase-3b-live-enablement-implementation.md)
- [Security boundary](phase-3b-live-enablement-security-boundary.md)

## 7. H1 hardening (2026-06-17)

The live gate was hardened in place under `HARDENING-3B-LIVE-H1-001`. The H1
pass added 8 backend hardening test files + 5 frontend hardening test files +
the `phase3b_live_h1_hardening` smoke profile (in `all`) + a hardening audit
script. 11/11 lenses PASS, P0 = 0, P1 = 0. No live request executed, no real
`OPENAI_API_KEY` read, no real network call, no implementation defect found.
See [phase-3b-live-h1-test-report](phase-3b-live-h1-test-report.md) and
[phase-3b-live-h1-hardening](phase-3b-live-h1-hardening.md).
