# Phase 3B-Live-Enablement — Secret Read Policy Implementation

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Implementation) |
| Module | `hermes_cli/dev_web_provider_live_secret.py` |
| Tests | `tests/test_dev_web_phase_3b_live_secret_policy.py` |
| Date | 2026-06-17 |

Implements the frozen [secret-read policy](phase-3b-live-enablement-secret-read-policy.md).

## 1. Principle

A real API key is read **only** from `OPENAI_API_KEY`, and **only** after every
live gate has passed. Its value never persists, never traverses a store, and
never appears in audit / logs / exceptions / responses / UI / tests. This module
returns a **value-free** `SecretState` only.

## 2. `read_provider_api_key_if_live_approved(...)`

Evaluation order (first gate wins; all short-circuit to
`blocked_before_secret_read` — the env is **never** inspected):

1. mode == real            else `not_checked`
2. api_enabled             else `blocked_before_secret_read`
3. kill switch inactive    else `blocked_before_secret_read`
4. approval valid          else `blocked_before_secret_read`
5. budget valid            else `blocked_before_secret_read`
6. host allowlisted        else `blocked_before_secret_read`
7. only now: read `OPENAI_API_KEY` presence → `env_present` / `env_missing`

Default tests / smoke never reach step 7 (no approval ⇒ blocked at step 4),
so no real key is read.

## 3. Value-free state

`SecretCheckResult` carries only:

```
keySource = environment
keyState  = env_present | env_missing | not_checked | blocked_before_secret_read
keyValue  = never
```

Forbidden: the key value, a fingerprint, a prefix, a suffix, a length, a hash,
the Authorization header, a bearer token.

## 4. Audit

The secret state is recorded via `provider_live_secret_state_checked`
(value-free `secretState` projection only). See
[audit implementation](phase-3b-live-enablement-audit-implementation.md).

## 5. Cross-references

- [Live enablement implementation](phase-3b-live-enablement-implementation.md)
- [Phase 3B-H1 secret redaction](phase-3b-h1-provider-secret-redaction.md)
