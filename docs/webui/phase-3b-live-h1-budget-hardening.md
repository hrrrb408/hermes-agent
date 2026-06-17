# Phase 3B-Live-Enablement H1 — Budget / Counter / Fail-closed Hardening

| Field | Value |
|-------|-------|
| Lens | 4 — Budget / Counter / Fail-closed Boundary |
| Hardening ID | `LIVE-BUDGET-3B-H1-001` |
| Status | PASS |

## Scope

The frozen first-live caps (1 request, ≤ 1000 total tokens, ≤ 200 output,
≤ 5 cents, 0 retries, ≤ 60 s) and the atomic, fail-closed dev-only counter store.

## Evidence

- Test file: `tests/test_dev_web_phase_3b_live_h1_budget_hardening.py`
- Implementation: `hermes_cli/dev_web_provider_live_budget.py`

## Findings & Fixes

- Fresh counters allowed; one `record_live_attempt` tips the request cap →
  `blocked_live_provider_request_cap_exceeded`.
- Total-token-over-cap, output-token-over-cap, and accumulated-token overflow →
  `blocked_live_provider_token_cap_exceeded`.
- In-window cents overflow → `blocked_live_provider_budget_exceeded`.
- Non-zero retry cap and missing caps → `blocked_live_provider_retry_not_allowed`
  / `blocked_live_provider_budget_not_configured`.
- Corrupt counter file → `read_live_counters` returns `None` →
  `blocked_live_provider_counter_unavailable` (fail closed).
- Production home → fail closed. Store lives under the dev `HERMES_HOME` only.
- `reset_live_counters` zeroes the window; cost estimate is rounded-up cents.

No implementation change was required.

## Residual risk

None. Counters are atomic, dev-only, and fail-closed.
