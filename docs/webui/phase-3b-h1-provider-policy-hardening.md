# Phase 3B-H1 — Provider Policy Hardening

- **Provider Policy Hardening ID:** PROVIDER-POLICY-3B-H1-001
- **Lenses:** 4 (Base URL / Timeout / Retry) + 5 (Budget / Rate-limit / Response-size)
- **Status:** PASS

## Scope

The enablement gate (`evaluate_real_provider_gating`), the retry classifier, the
HTTP-failure classifier, and the cost / rate-limit / budget policy
(`hermes_cli/dev_web_provider_real_policy.py`, `dev_web_provider_real_budget.py`).
Phase 3B-H1 hardens every fail-closed path.

## Lens 4 — Base URL / Timeout / Retry

- **First failure wins, all fail closed:** the gate evaluates in a fixed order
  and returns a precise `blocked_provider_*` reason on the FIRST missing
  condition, with NO network call. Verified for every gate independently:
  `real_not_enabled`, `api_disabled`, `name_not_supported`, `api_key_missing`,
  `not_dev_home`, `production_gate_drift`, `base_url_not_allowed`,
  `model_not_allowed`.
- **Timeout floor is structurally guaranteed:** the loader HARD-clamps timeout
  to `[1, 60]`, so the `timeout_invalid` gate's precondition is defense-in-depth.
- **Retry is safe-transient ONLY:** `408/425/500/502/503/504` retry; auth
  (`401/403`), policy-block, budget, rate-limit, response-too-large, secret-
  detected NEVER retry. A retry storm is structurally impossible.
- **HTTP classification is deterministic:** `401/403`→auth, `429`→rate-limit,
  `4xx`→schema-mismatch, `5xx`/None→network-unavailable.

## Lens 5 — Budget / Rate-limit / Response-size

- **Caps enforced BEFORE any network call:** per-minute request cap, daily
  request cap, daily token cap, daily budget cap. A breach returns a precise
  reason (`rate_limit_exceeded` / `budget_exceeded`).
- **Cost is estimated before the call:** conservative, rounded UP, bounded price
  table; unknown models are blocked by the model allowlist first.
- **Fail-closed counters:** a corrupt / out-of-home counter file, or production
  `HERMES_HOME`, returns `None` and the request is blocked.
- **Smoke consumes no real budget** (the real path is never reached).

## Evidence

- `tests/test_dev_web_phase_3b_h1_provider_policy_hardening.py`

## Residual Risk

- P0: none. P1: none.
