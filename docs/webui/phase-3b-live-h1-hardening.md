# Phase 3B-Live-Enablement H1 — Live Gate Hardening

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement H1 (Hardening) |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |
| Hardening ID | `HARDENING-3B-LIVE-H1-001` |
| Input HEAD | `5da7e09559611709d293d7cc1258454f3f44ca82` |
| Output HEAD | _(set on commit)_ |
| Phase 3C | not started |

## 1. Goal

A deterministic **hardening pass** over the strict manual one-shot real-provider
live enablement gate introduced in Phase 3B-Live-Enablement. This phase does
**not** execute a live request, does **not** read a real `OPENAI_API_KEY`, and
does **not** make a real provider network call.

It adds edge-case hardening tests (backend + frontend), a hardening smoke
profile, a hardening audit script, and hardening documentation. Implementation
code is changed only if a real defect is found — none was found.

## 2. Scope

- Harden the live **approval** model (5-min TTL, single-use, in-scope, mismatch).
- Harden the **secret read gate** (env inspected ONLY past every gate).
- Harden the **network allowlist** (single HTTPS POST to `api.openai.com`).
- Harden the **budget / counter** policy (1 / 1000 / 200 / 5c / 0 retry, fail-closed).
- Harden the **kill switch** (14 triggers, clear-is-not-approval).
- Harden the **live round-trip** (gate ordering, no tool execution).
- Harden `provider_live_*` **audit** (18 events, defensive re-redaction, fail-closed).
- Harden the **frontend** live-enablement UI (no-leak in every state).
- Add the `phase3b_live_h1_hardening` smoke profile (included in `all`).
- Preserve route governance (34/34/5/0/1/1) and production isolation.

## 3. Hardening IDs

| Lens | ID |
|------|----|
| Overall | `HARDENING-3B-LIVE-H1-001` |
| Live Approval / TTL / Single-use | `LIVE-APPROVAL-3B-H1-001` |
| Secret Read Gate | `LIVE-SECRET-3B-H1-001` |
| Network Allowlist | `LIVE-NETWORK-3B-H1-001` |
| Budget / Counter / Fail-closed | `LIVE-BUDGET-3B-H1-001` |
| Kill Switch / Disable / Re-enable | `LIVE-KILL-3B-H1-001` |
| Live Round-trip / No-tool-execution | `LIVE-ROUNDTRIP-3B-H1-001` |
| provider_live_* Audit / Redaction | `LIVE-AUDIT-3B-H1-001` |
| Frontend Live UI No-leak | `LIVE-UI-3B-H1-001` |

## 4. 11-Lens summary

| # | Lens | Status |
|---|------|--------|
| 1 | Live Approval / TTL / Single-use | PASS |
| 2 | Secret Read Gate / OPENAI_API_KEY Non-read | PASS |
| 3 | Network Allowlist / No-default-network | PASS |
| 4 | Budget / Counter / Fail-closed | PASS |
| 5 | Kill Switch / Disable / Re-enable | PASS |
| 6 | Live Round-trip / No-tool-execution | PASS |
| 7 | provider_live_* Audit / Redaction | PASS |
| 8 | Frontend Live Enablement UI No-leak | PASS |
| 9 | Smoke Profile / Manual Profile Exclusion | PASS |
| 10 | Route Governance / Preservation | PASS |
| 11 | Production Isolation / Runtime Artifact | PASS |

11 / 11 PASS. P0 = 0, P1 = 0.

## 5. Deliverables

- Backend hardening tests (8 files):
  `tests/test_dev_web_phase_3b_live_h1_{approval,secret_gate,network,budget,kill_switch,roundtrip,audit,api_security}_hardening.py`
- Frontend hardening tests (5 files):
  `src/tests/phase3b-live-h1-{status,approval,budget,kill-switch,no-leak}-ui.spec.ts`
- Smoke profile + spec:
  `phase3b_live_h1_hardening` / `tests/smoke/phase-3b-live-h1-hardening-smoke.spec.ts`
- Hardening audit script:
  `scripts/run-dev-webui-phase3b-live-hardening-audit.sh`
- Hardening docs (this file + 8 lens docs).
- Code fixes: none (no real defect found).

## 6. What this phase does NOT do

No live request executed. No real API key read. No real provider network call.
The manual one-shot live profile remains **excluded** from the default `all`
smoke target. Provider write, provider auto-write, provider rollback, autonomous
write, shell / DB / external-HTTP / production operations, streaming,
multi-provider routing, production rollout, `~/.hermes` access, and production
`state.db` access remain blocked. Phase 3C was not started.

## 7. Cross-references

- [Live enablement implementation](phase-3b-live-enablement-implementation.md)
- [Live enablement security boundary](phase-3b-live-enablement-security-boundary.md)
- [H1 test report](phase-3b-live-h1-test-report.md)

---

## Phase 3C Planning update (scope frozen — not implemented)

After this H1 hardening pass, the next slice — **Phase 3C — Plugin / Capability
Registry** — had its scope **frozen** in a separate docs-only planning phase
(`PHASE-3C-PLANNING-001`) without being implemented. The Phase 3C registry is a
**descriptive read-only layer** that classifies the existing tool / provider /
workflow capabilities (including this hardening's `provider.live_manual_one_shot`
= LIVE_PROVIDER_GATED) **without relaxing any H1 lens**. It grants no permission,
loads no code, adds no route by default, and is dev-only /
`productionAllowed=false`. No dynamic plugin runtime, marketplace, or remote
registry. The manual one-shot live execution remains NO-GO until separately
authorized. See [phase-3c-planning](phase-3c-planning.md) and
[phase-3c-go-no-go](phase-3c-go-no-go.md).
