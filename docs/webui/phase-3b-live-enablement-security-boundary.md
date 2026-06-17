# Phase 3B-Live-Enablement — Security Boundary

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Implementation) |
| Date | 2026-06-17 |
| Branch | `dev-huangruibang` |

The live-enablement boundary is **additive** to Phase 3B / Phase 3B-H1. It
introduces the live layer in front of the real-gated path's concrete network
call, without relaxing any existing gate.

## 1. Invariants

1. Real provider is **disabled by default.**
2. A live request requires a **fresh, single-use, 5-minute, in-scope human
   approval** (scope `provider_live_enablement`).
3. The approval is **value-free** (no key / header / token / raw prompt /
   raw response / production path).
4. The API key is read **only** from `OPENAI_API_KEY`, **only** past every
   gate, and **only** its presence is reported (value never persisted / logged /
   audited / rendered).
5. The only egress is a **single** outbound HTTPS POST to an **allowlisted**
   host (`api.openai.com`); http / localhost / private IP / off-allowlist
   redirect / response-driven fetch are blocked.
6. The first live request is **one-shot**: 1 request, ≤ 1000 tokens (≤ 200
   output), ≤ 5 cents, 0 retries, ≤ 60s, non-streaming.
7. No tool execution for the first live request (returned `tool_calls` are
   classified + audited + blocked; a write/autonomous suggestion fires the
   kill switch).
8. Every lifecycle event is **redacted, dual-written, fail-closed** audit.
9. The kill switch (14 triggers) blocks before the secret read and before any
   network call; clearing it is **not** an approval.
10. After the call the single-use approval is **invalidated immediately.**

## 2. Permanently blocked (live layer does not relax these)

Provider write, provider auto-write, provider rollback execute, autonomous
write, shell / database / external-HTTP / production operations, plugin dynamic
load, streaming, multi-provider routing, background / cron, production rollout,
`~/.hermes` access, production `state.db` access, arbitrary-URL fetch.

## 3. Route governance (unchanged)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 34 |
| Runtime routes | 34 |
| Tool GET | 5 |
| Tool write HTTP route | 0 |
| Tool dry-run route | 1 |
| Tool execution route | 1 |

No new route was added. The live gate is surfaced **only** under the existing
`GET /status` `data.providerBoundary.providerLive` block.

## 4. Frozen blocked-reason catalogue (live layer)

```
blocked_live_provider_not_human_approved
blocked_live_provider_approval_expired
blocked_live_provider_approval_scope_invalid
blocked_live_provider_approval_used
blocked_live_provider_approval_mismatch
blocked_live_provider_dev_only_violation
blocked_live_provider_kill_switch_active
blocked_live_provider_host_not_approved
blocked_live_provider_scheme_not_https
blocked_live_provider_redirect_not_allowed
blocked_live_provider_private_network_not_allowed
blocked_live_provider_response_fetch_not_allowed
blocked_live_provider_network_timeout
blocked_live_provider_response_too_large
blocked_live_provider_budget_not_configured
blocked_live_provider_budget_exceeded
blocked_live_provider_request_cap_exceeded
blocked_live_provider_token_cap_exceeded
blocked_live_provider_retry_not_allowed
blocked_live_provider_counter_unavailable
```

## 5. No-leak guarantees

No API-key value, Authorization header, bearer token, raw token, full
tokenHash, raw prompt/response secret, raw tool args, callable repr, or
production path appears in any audit event, log, exception, HTTP response,
rendered UI, test snapshot, or git commit. Default tests / smoke do not read a
real key and do not call a real network.

## 6. Cross-references

- [Live enablement implementation](phase-3b-live-enablement-implementation.md)
- [Phase 3B security boundary](phase-3b-security-boundary.md)
- [Phase 3B-H1 provider boundary hardening](phase-3b-h1-provider-boundary-hardening.md)
- [Test report](phase-3b-live-enablement-test-report.md)
