# Phase 3B-Live-Enablement — Budget / Rate-limit Policy

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Planning) |
| Title | Strict Manual Real Provider Enablement — Budget / Rate-limit Policy |
| Status | Frozen (docs-only planning; live enablement **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |

## 1. Principle

Every live request is cost-bounded, rate-bounded, token-bounded, and
time-bounded. Counters are atomic and fail-closed: if a counter cannot be read or
written, the request is blocked.

## 2. First live test caps (recommended)

| Cap | Value |
|-----|-------|
| `maxRequests` | 1 |
| `maxTotalTokens` | 1000 |
| `maxInputTokens` | 800 |
| `maxOutputTokens` | 200 |
| `maxBudgetCents` | 5 |
| `maxRuntimeSeconds` | 60 |
| `maxRetries` | 0 (no retry for the first live test) |

## 3. Expansion requires fresh approval

| Change | Requirement |
|--------|-------------|
| `maxRequests > 1` | new approval |
| `maxBudgetCents > 5` | new approval |
| `maxRetries > 0` | new approval |
| streaming | later phase |
| multi-provider | later phase |

## 4. Required counter / limit fields

```
budgetCap
requestCap
tokenCap
retryCap
timeoutCap
rateLimitWindow
spentEstimate
remainingEstimate
failClosedOnCounterError
```

`spentEstimate` / `remainingEstimate` are computed from usage summaries
(`promptTokens`, `totalTokens`) — **never** from any key-bearing payload.

## 5. Counter semantics

- Counters live under the dev `HERMES_HOME` only (never `~/.hermes`).
- Counters are append-only / atomic JSON.
- On corruption / unreadable counter → `blocked_live_provider_counter_unavailable`
  and fail closed (`failClosedOnCounterError=true`).

## 6. Blocked reasons (budget layer)

```
blocked_live_provider_budget_not_configured
blocked_live_provider_budget_exceeded
blocked_live_provider_request_cap_exceeded
blocked_live_provider_token_cap_exceeded
blocked_live_provider_retry_not_allowed
blocked_live_provider_counter_unavailable
```

## 7. Reuse of Phase 3B cost / rate-limit enforcement

The future implementation reuses the Phase 3B budget + rate-limit modules, adding
the live approval gate, the kill-switch check, and the stricter first-test caps.
The existing `blocked_provider_rate_limit_exceeded` /
`blocked_provider_budget_exceeded` reasons remain valid for the real-gated mode.

## 8. Cost estimate safety

`costEstimate` and `usageSummary` are safe audit fields. They are derived from
token counts and the model's published pricing; they never carry key material.

## 9. Cross-references

- [Phase 3B cost / rate-limit policy](phase-3b-cost-and-rate-limit-policy.md)
- [Phase 3B-H1 policy hardening](phase-3b-h1-provider-policy-hardening.md)
- [Phase 3B-Live-Enablement audit policy](phase-3b-live-enablement-audit-policy.md)
