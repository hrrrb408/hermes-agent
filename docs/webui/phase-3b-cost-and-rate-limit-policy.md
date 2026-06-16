# Phase 3B Cost & Rate-limit Policy

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Planning |
| Title | Real Provider Cost / Rate-limit / Budget Policy (Frozen) |
| Status | Frozen |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Policy ID | `PHASE-3B-COST-POLICY-001` |

> Companion to [phase-3b-planning.md](phase-3b-planning.md). This document freezes
> the caps and accounting a future Phase 3B implementation must enforce on real
> provider spend and request volume. **No real spend is incurred in this planning
> phase.** Smoke must never consume real budget.

---

## 1. Principle

A real round-trip has a real cost. Phase 3B treats that cost as a **first-class
safety boundary**, not an afterthought. Every request is counted, every response
is metered, a cost estimate is computed **before** the call, and a hard daily
budget cap blocks further spend once reached. The caps are config-driven, bounded,
and audited.

---

## 2. Caps (frozen)

| Cap | Rule |
|-----|------|
| Per-minute request cap | bounded; exceeded → `blocked_provider_rate_limit_blocked` |
| Daily request cap | bounded; exceeded → `blocked_provider_rate_limit_blocked` |
| Daily token cap | bounded (prompt + completion); exceeded → `blocked_provider_budget_blocked` |
| Daily budget cap | bounded, in cents (`HERMES_PROVIDER_DAILY_BUDGET_CENTS`, clamped); exceeded → `blocked_provider_budget_exceeded` |
| Per-request max tokens | bounded `maxTokens` from config (clamped) |
| Model allowlist | only allowlisted models may be used; unknown model → blocked |

Caps are **defensive**: when a counter cannot be read or written safely, the
request is blocked (fail-closed), never allowed.

---

## 3. Accounting (frozen)

- A **cost estimate** is computed **before** the call from the request token
  count and the model's price table (bounded, conservative estimate).
- If the estimate plus the running daily total exceeds the daily budget cap, the
  request is blocked with `blocked_provider_budget_exceeded` **before** any
  network call.
- A **usage summary** is metered **after** the call from the provider's reported
  usage block (prompt / completion / total tokens), and the running counters are
  updated.
- Counters are stored in the dev `HERMES_HOME` only (append-only / atomic),
  never committed, never sent to the UI beyond a safe badge value.

---

## 4. Audit (frozen)

Every cost / rate-limit decision is audited:

| Event | When |
|------|------|
| `provider_real_budget_blocked` | a budget / token cap blocks the request |
| `provider_real_rate_limit_blocked` | a per-minute / daily request cap blocks the request |
| `provider_real_request_completed` | carries the bounded `usageSummary` and `costEstimate` |
| `provider_real_request_failed` | carries the bounded `usageSummary` if any tokens were billed |

The audit record carries `usageSummary` and `costEstimate` only — never a
secret, never an API key, never a raw response body.

---

## 5. UI Representation (frozen)

- A **budget badge** may show safe, value-free metadata: daily budget cap,
  remaining requests / tokens / cents (rounded, conservative), and the active
  model name.
- The badge **never** shows an API key, a header, a raw response, or a precise
  spend that could leak usage patterns of a secret session.
- When a cap is reached, the UI shows the `blocked_provider_budget_exceeded` /
  `blocked_provider_rate_limit_blocked` reason and disables the real-round-trip
  control until the window resets.

---

## 6. Smoke Must Not Consume Real Budget (frozen)

- The smoke profile for Phase 3B uses the **fake** provider + **blocked-real**
  mode only. It must **never** make a real network call and must **never** incur
  real spend.
- The blocked-real assertions verify that, with the real path not fully enabled,
  the request is blocked with the correct `blocked_provider_*` reason and
  `externalNetworkCalled=false`.

---

## 7. Reset & Recovery (frozen)

- Per-minute and daily counters reset on their natural window boundaries (the
  implementation must not back-date or pre-date counters).
- A corrupted counter file fails **closed** (the request is blocked) until the
  operator resets it through an explicit, dev-only action — never automatically
  and never silently.

---

## 8. Acceptance (for a future Phase 3B implementation)

1. A cost estimate is computed before the call; estimate-over-budget → blocked.
2. Usage is metered after the call; counters updated atomically.
3. Per-minute / daily / token / budget caps are all enforced and audited.
4. Unknown models are blocked (model allowlist).
5. Corrupted counters fail closed.
6. Smoke never consumes real budget.
7. The UI budget badge shows only safe metadata.

---

## 9. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B network boundary](phase-3b-network-boundary.md)
- [Phase 3B failure / timeout / retry policy](phase-3b-failure-timeout-retry-policy.md)
- [Phase 3B audit model](phase-3b-provider-audit-model.md)
- [Phase 3B request / response schema](phase-3b-provider-request-response-schema.md)
