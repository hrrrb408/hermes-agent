# Phase 3B-Live-Enablement — Budget / Rate-limit Implementation

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Implementation) |
| Module | `hermes_cli/dev_web_provider_live_budget.py` |
| Tests | `tests/test_dev_web_phase_3b_live_budget_policy.py` |
| Date | 2026-06-17 |

Implements the frozen [budget / rate-limit policy](phase-3b-live-enablement-budget-policy.md).

## 1. Frozen first-live caps (`LiveBudgetCaps`)

| Cap | Value |
|-----|-------|
| `maxRequests` | 1 |
| `maxTotalTokens` | 1000 |
| `maxInputTokens` | 800 |
| `maxOutputTokens` | 200 |
| `maxBudgetCents` | 5 |
| `maxRuntimeSeconds` | 60 |
| `maxRetries` | 0 |
| `rateLimitWindow` | 60s |
| `failClosedOnCounterError` | true |

## 2. `evaluate_live_budget(...)`

Pre-call evaluation (no network call). Fail-closed order:

1. caps missing                         → `blocked_live_provider_budget_not_configured`
2. `maxRetries != 0`                     → `blocked_live_provider_retry_not_allowed`
3. counters unreadable / corrupt         → `blocked_live_provider_counter_unavailable`
4. requests ≥ `maxRequests`             → `blocked_live_provider_request_cap_exceeded`
5. est_total > `maxTotalTokens`          → `blocked_live_provider_token_cap_exceeded`
6. est_output > `maxOutputTokens`        → `blocked_live_provider_token_cap_exceeded`
7. counters.tokens + est_total > cap     → `blocked_live_provider_token_cap_exceeded`
8. counters.cents + estimate > cap       → `blocked_live_provider_budget_exceeded`

`estimate_live_cost_cents` is conservative (rounded up) and derived from token
counts only — never from a key-bearing payload.

## 3. Atomic fail-closed counters

Counters live under `$HERMES_HOME/gateway/dev/provider-live-budget/counters.json`
(atomic temp+rename, per-minute window reset). On corruption / outside home /
production home, reads return `None` and the request is blocked. `record_live_attempt`
counts an attempt pre-call; `meter_live_usage` meters a completed call;
`reset_live_counters` supports the disable / rollback procedure.

## 4. Dev-only

The store rejects the production home, a missing home, a path escaping the
home, and any `state.db` path. Counters never carry a key and are never committed.

## 5. Cross-references

- [Live enablement implementation](phase-3b-live-enablement-implementation.md)
- [Audit implementation](phase-3b-live-enablement-audit-implementation.md)
