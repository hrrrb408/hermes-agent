# Phase 3B Network Boundary

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Planning |
| Title | Real Provider Network Boundary (Frozen) |
| Status | Frozen |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Boundary ID | `PHASE-3B-NETWORK-BOUNDARY-001` |

> Companion to [phase-3b-planning.md](phase-3b-planning.md). This document freezes
> the single allowed egress path and every guard around it for a future Phase 3B
> implementation. **No network call is made in this planning phase.** The real
> provider stays blocked by default.

---

## 1. The Single Allowed Egress

In a future Phase 3B implementation, the **only** allowed external network
operation is a single outbound HTTPS `POST` to the configured, allowlisted
provider endpoint. Everything else — any other host, any other method, any
provider-requested URL fetch, any tool-driven HTTP — remains **blocked**.

```
[ operator enablement: HERMES_PROVIDER_API_ENABLED=1 + HERMES_PROVIDER_MODE=real ]
   → eligibility gate (Phase 2B-H1): key present + dev home + production gate
      → base-URL allowlist check
         → timeout / size / retry / rate-limit / cost checks
            → single HTTPS POST to the allowlisted provider endpoint
               → redacted response normalization
                  → audited result (or audited blocked reason)
```

---

## 2. Default State

- The real-provider path is **disabled by default**. It is reachable only when
  **all** of the following hold:
  - `HERMES_PROVIDER_API_ENABLED=1`
  - `HERMES_PROVIDER_MODE=real`
  - a provider API key is present in the environment (read-only, never logged)
  - `HERMES_HOME` is the dev home (not `~/.hermes`)
  - the production-gateway PID gate passes (read-only observation)
  - the base URL is on the allowlist
- If any condition fails, the request is blocked with a precise
  `blocked_provider_*` reason and **no network call is made**
  (`externalNetworkCalled=false`).

---

## 3. URL Policy (frozen)

| # | Rule |
|---|------|
| 1 | The outbound URL must be on an explicit **base-URL allowlist**. |
| 2 | Arbitrary URLs are **blocked** (`blocked_provider_base_url_not_allowed`). |
| 3 | A provider-requested URL fetch is **blocked** (`blocked_provider_external_url_not_allowed`). |
| 4 | A tool performing external HTTP is **blocked**. |
| 5 | `shell` / `curl` / `httpx` / `urllib` / `aiohttp` arbitrary calls are **blocked**. |
| 6 | Only `https://` schemes are permitted; plaintext `http://` is blocked. |
| 7 | Redirects off the allowlist are blocked (do not follow redirects to non-allowlisted hosts). |

The allowlist is config-driven and **audited** (`safeMetadata.allowlistedBaseUrl`
carries the host, not the full URL with any path query secret). The full URL
(redacted of headers) may appear only in the dev-only audit JSONL, never in a
response or the UI.

---

## 4. Transport Guards (frozen)

| Guard | Requirement |
|-------|-------------|
| Connect timeout | bounded (from `HERMES_PROVIDER_TIMEOUT_SECONDS`, clamped) |
| Read timeout | bounded (separate from connect timeout) |
| Total request timeout | bounded (hard ceiling per request) |
| Max response size | bounded (reject oversize → `blocked_provider_response_too_large`) |
| Max retries | capped (from `HERMES_PROVIDER_MAX_RETRIES`, clamped) |
| Retry scope | safe-transient only (see failure policy) |
| Rate limit | per-minute + daily caps (see cost / rate-limit policy) |
| Cost cap | daily budget cap (see cost / rate-limit policy) |
| TLS | required (`https://`); certificate verification on |

Full failure / timeout / retry semantics:
[phase-3b-failure-timeout-retry-policy.md](phase-3b-failure-timeout-retry-policy.md).

---

## 5. Blocked-Reason Catalogue (frozen)

| Reason | When |
|--------|------|
| `blocked_provider_real_not_enabled` | mode is not `real` |
| `blocked_provider_api_disabled` | `HERMES_PROVIDER_API_ENABLED` is not `1` |
| `blocked_provider_base_url_not_allowed` | base URL not on allowlist |
| `blocked_provider_api_key_missing` | no API key in env |
| `blocked_provider_timeout_invalid` | timeout config out of bounds |
| `blocked_provider_rate_limit_exceeded` | per-minute / daily cap exceeded |
| `blocked_provider_budget_exceeded` | daily budget cap exceeded |
| `blocked_provider_response_too_large` | response exceeds max size |
| `blocked_provider_tool_call_not_allowed` | provider requested a non-allowlisted / write tool |
| `blocked_provider_write_not_allowed` | provider attempted a write |
| `blocked_provider_external_url_not_allowed` | provider / tool requested an arbitrary URL |
| `blocked_provider_secret_detected` | sanitizer detected a secret in request / response / args |

Every block is audited and sets `externalNetworkCalled=false` (no call was made)
or the appropriate flag when the call started and then failed.

---

## 6. Safe-Degrade Contract

Any failure (timeout, oversize, malformed JSON, schema mismatch, provider
unavailable, rate-limit, budget) must **safe-degrade**:

- The system returns a blocked / error result to the operator.
- **No side effect** is committed (no write, no state mutation, no partial
  result committed as if complete).
- The failure is **audited** (`provider_real_request_failed` or the specific
  block event).
- The UI shows a **safe** blocked / error state — **no raw stack trace**, no
  raw provider body, no secret.

---

## 7. What Is NOT on the Network Boundary

- No streaming socket in the first implementation (non-streaming single POST
  only).
- No webhooks / inbound HTTP from the provider.
- No long-lived connections / connection pools that survive the request beyond a
  bounded idle window.
- No DNS pinning tricks or custom resolvers.
- No proxy configuration beyond the dev machine's defaults (and only to the
  allowlisted host).

---

## 8. Audit Footprint (frozen)

The network boundary emits the audit events in
[phase-3b-provider-audit-model.md](phase-3b-provider-audit-model.md). Every event
records the **allowlisted host** (not a secret-bearing URL), the
`blockedReason` (if any), `externalNetworkCalled`, and the bounded usage / cost
summary — never an API key, header, or raw body.

---

## 9. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B scope freeze](phase-3b-provider-readonly-scope-freeze.md)
- [Phase 3B API-key & secret strategy](phase-3b-api-key-and-secret-strategy.md)
- [Phase 3B failure / timeout / retry policy](phase-3b-failure-timeout-retry-policy.md)
- [Phase 3B cost / rate-limit policy](phase-3b-cost-and-rate-limit-policy.md)
- [Phase 3B audit model](phase-3b-provider-audit-model.md)
- [Phase 3B request / response schema](phase-3b-provider-request-response-schema.md)
- [Phase 3B redaction & no-leak policy](phase-3b-provider-redaction-and-no-leak-policy.md)
- [Phase 2B provider security boundary](phase-2b-provider-security-boundary.md)
