# Phase 3B-Live-Enablement Implementation — Strict Manual One-shot Real Provider Enablement

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Implementation) |
| Title | Strict Manual One-shot Real Provider Enablement |
| Status | Implemented — live provider **disabled by default**; a live request requires explicit human approval |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |
| Input HEAD | `45e762d1b786dd705165cf6cf9355bf24f022527` (`docs(webui): plan provider live enablement`) |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |
| Implementation ID | `PHASE-3B-LIVE-ENABLEMENT-IMPL-001` |

> This phase implements the **live layer** frozen by the Phase 3B-Live-Enablement
> planning docs. It adds a strict manual one-shot live gate on top of the
> already-shipped Phase 3B / Phase 3B-H1 read-only boundary. The real provider
> remains **disabled by default**. Default tests and smoke do **not** read a real
> API key and do **not** perform any real provider network call. The manual
> one-shot live profile is opt-in and is **not** included in the default `all`
> smoke target.

## 1. Goal

Wire a **live gate** in front of the Phase 3B real-gated path: a fresh, single-use,
short-window, revocable human approval; an env-only secret-read policy; an
HTTPS single-host network allowlist; a strict budget / rate-limit cap; a kill
switch; and redacted dual-write audit. The first live request is one-shot,
non-streaming, no tool execution, ≤ 5 cents, ≤ 1000 tokens (≤ 200 output), 0
retries, with immediate approval invalidation afterward.

## 2. What shipped

### Backend modules (7 new, under `hermes_cli/`)

| Module | Responsibility |
|--------|----------------|
| `dev_web_provider_live_approval.py` | Human-approval model + dev-only atomic store (issue / validate / match / mark-used / revoke) |
| `dev_web_provider_live_secret.py` | Value-free secret-read policy — reads `OPENAI_API_KEY` presence **only** past every live gate |
| `dev_web_provider_live_network.py` | HTTPS single-host allowlist (`api.openai.com`); http / localhost / private IP / off-allowlist redirect blocked |
| `dev_web_provider_live_budget.py` | Frozen first-live caps (1 request / 1000 / 200 / 5c / 0 retry / 60s) + atomic fail-closed counters |
| `dev_web_provider_live_audit.py` | 18 `provider_live_*` audit event writers (redacted, dual-written via Phase 2B writer) |
| `dev_web_provider_live_kill_switch.py` | Kill switch store + 14 frozen trigger reasons; inactive by default |
| `dev_web_provider_live_roundtrip.py` | One-shot live round-trip orchestrator — ordered gate evaluation, mock-only HTTP client, approval invalidation |

### API integration (no new route)

The live status is surfaced under the existing `GET /api/dev/v1/status`
`data.providerBoundary.providerLive` block (value-free). No `provider_live`
route, no live-approval route, no live-roundtrip route. Route governance is
unchanged: **OpenAPI 34 / runtime 34 / Tool GET 5 / Tool write HTTP route 0 /
Tool dry-run 1 / Tool execution 1.**

### Frontend (additive)

- `ProviderLiveStatus` / `ProviderLiveBudgetBadge` types in
  `src/types/api/toolProvider.ts`
- `liveStatus` + `liveEnabled` computeds in `src/stores/toolProvider.ts`
- A "Live Provider Enablement" section extended onto the existing
  `ProviderBoundaryStatus.vue` (no API-key input, no secret rendering)

### Smoke

- New profile `phase3b_live_enablement_boundary` (fake provider, no real key,
  no real network) + spec `phase-3b-live-enablement-boundary-smoke.spec.ts`.
  Added to the default `all` target.
- The manual profile `phase3b_live_enablement_manual_one_shot` is documented
  but **not** implemented in the default smoke runner and is **not** in `all`.

## 3. What did NOT ship (forbidden / deferred)

- A real live request was **not** executed (no real network call, no real key
  read). Default tests / smoke use injected mocks and value-free state only.
- Provider write / auto-write / rollback / autonomous write remain permanently
  blocked. Shell / DB / external-HTTP / production operations remain blocked.
- Streaming, multi-provider routing, background / cron, production rollout,
  plugin dynamic loading, arbitrary-URL fetch — all blocked.
- No `~/.hermes` access; no production `state.db` access.
- The manual one-shot live profile was not run.

## 4. Backend tests (8 new files, 115 cases)

| File | Coverage |
|------|----------|
| `test_dev_web_phase_3b_live_approval.py` | default-missing blocked, value-free record, 5-min TTL, single-use, expiry, scope/match mismatch, dev-only store |
| `test_dev_web_phase_3b_live_secret_policy.py` | blocked-before-secret-read on every gate, value-free state, no env read when disabled |
| `test_dev_web_phase_3b_live_network_allowlist.py` | openai-only allowlist, http/file/localhost/private-IP blocked, redirect policy, external-HTTP tool detection |
| `test_dev_web_phase_3b_live_budget_policy.py` | frozen caps, request/token/budget caps, retry-zero, counter corruption fail-closed, dev-only store |
| `test_dev_web_phase_3b_live_audit_policy.py` | 18 event types, redaction-before-write, safe-fields-only, no-leak in persisted JSONL |
| `test_dev_web_phase_3b_live_kill_switch.py` | inactive default, trigger/clear, clear-is-not-approval, 14 triggers, dev-only, value-free |
| `test_dev_web_phase_3b_live_roundtrip.py` | default/kill-switch/no-approval/off-allowlist/budget blocks; completed one-shot + invalidation; no tool execution; write-tool kill; no-leak |
| `test_dev_web_phase_3b_live_api_security.py` | route governance unchanged (34), providerLive block value-free + default disabled, no live route |

Default tests inject `MockHttpClient` and never read a real key or call a real
network. See [phase-3b-live-enablement-test-report.md](phase-3b-live-enablement-test-report.md).

## 5. Frontend tests (5 new files, 22 cases)

`phase3b-live-enablement-status` / `-approval` / `-no-leak` / `-kill-switch` /
`-budget`. Render the live gate across states; assert no API-key input, no
Authorization / Bearer / raw token / callable repr / production path.

## 6. Live approval model

See [phase-3b-live-enablement-approval-implementation.md](phase-3b-live-enablement-approval-implementation.md).
Scope `provider_live_enablement`; 5-minute TTL; single-use; matched against
provider / model / host / tool-allowlist; invalidated immediately after use;
dev-only store under `$HERMES_HOME/gateway/dev/provider-live-approvals`.

## 7. Secret / network / budget / audit / kill switch

- [Secret-read implementation](phase-3b-live-enablement-secret-implementation.md) — env-only; value-free state; read only past every gate.
- [Network allowlist implementation](phase-3b-live-enablement-network-implementation.md) — HTTPS `api.openai.com`; no redirect / fetch / private network.
- [Budget implementation](phase-3b-live-enablement-budget-implementation.md) — 1/1000/200/5c/0/60s; atomic fail-closed counters.
- [Audit implementation](phase-3b-live-enablement-audit-implementation.md) — 18 redacted dual-write events; fail-closed.
- [Kill switch implementation](phase-3b-live-enablement-kill-switch-implementation.md) — 14 triggers; inactive default; fresh approval to re-enable.

## 8. Production safety

Production Gateway PID `28428` was not stopped / restarted / replaced / signaled /
reconfigured. Dev services bind `127.0.0.1` only. No `~/.hermes` access; no
production `state.db` access. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1).

## 9. Cross-references

- [Phase 3B-Live-Enablement planning](phase-3b-live-enablement-planning.md)
- [Security boundary](phase-3b-live-enablement-security-boundary.md)
- [GO / NO-GO](phase-3b-live-enablement-go-no-go.md)
- [Phase 3B real-provider read-only integration](phase-3b-real-provider-readonly-integration.md)
- [Phase 3B-H1 provider boundary hardening](phase-3b-h1-provider-boundary-hardening.md)

## 10. H1 hardening (2026-06-17)

This implementation was hardened in place under `HARDENING-3B-LIVE-H1-001`
(Phase 3B-Live-Enablement H1). The deterministic 11-lens hardening pass added
edge-case backend + frontend tests, the `phase3b_live_h1_hardening` smoke
profile (included in `all`), a hardening audit script
(`scripts/run-dev-webui-phase3b-live-hardening-audit.sh`), and hardening docs.
11/11 lenses PASS, P0 = 0, P1 = 0. No live request was executed, no real
`OPENAI_API_KEY` was read, no real provider network call was made, and no
implementation defect was found — so no production-boundary code changed. The
manual one-shot live profile remains excluded from the default `all` smoke
target. See [phase-3b-live-h1-hardening](phase-3b-live-h1-hardening.md) and
[phase-3b-live-h1-test-report](phase-3b-live-h1-test-report.md).
