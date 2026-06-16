# Phase 3B-Live-Enablement — Network Allowlist Policy

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Planning) |
| Title | Strict Manual Real Provider Enablement — Network Allowlist |
| Status | Frozen (docs-only planning; live enablement **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |

## 1. Principle

The only egress a live provider may ever make is a **single** outbound HTTPS POST
to an **explicitly allowlisted** host. The default allowlist is **empty.** Any
deviation fails closed with a precise blocked reason and no network call.

> **This planning phase performs no network call.** This policy describes the
> constraints the future implementation must satisfy.

## 2. Network rules

1. Only HTTPS (`https://`) is allowed.
2. Only an explicitly allowlisted host is allowed.
3. The default allowlist is empty.
4. The operator must explicitly approve a host at approval time.
5. Arbitrary URLs are forbidden.
6. `http://` is forbidden.
7. `localhost` providers require separate approval.
8. Private-IP providers require separate approval.
9. Redirects to an off-allowlist host are forbidden.
10. A provider response triggering an extra fetch is forbidden.
11. Tool-call external HTTP is forbidden.
12. `curl` / shell network is forbidden.
13. Database network is forbidden.
14. Production endpoints are forbidden.
15. Every network call has a timeout.
16. Every network call has a response-size limit.
17. Every network call is audited.

## 3. Recommended initial allowlist

```
api.openai.com
```

This planning phase **does not call** this host. It only freezes it as the
recommended initial candidate, subject to operator approval.

## 4. Allowed outbound envelope (future)

A single `POST` to `https://<allowlisted host>/<approved path>`, with:

- a bounded timeout,
- a bounded response size (recommended ≤ 64 KiB, matching Phase 3B),
- a single `Authorization` header carrying the env-only key,
- no retries beyond the approved cap (zero retries for the first live test).

## 5. Redirect / fetch policy

- Off-allowlist redirect → `blocked_live_provider_redirect_not_allowed`.
- Response-driven extra fetch → `blocked_live_provider_response_fetch_not_allowed`.
- Private / localhost network → `blocked_live_provider_private_network_not_allowed`.

## 6. Blocked reasons (network layer)

```
blocked_live_provider_host_not_approved
blocked_live_provider_scheme_not_https
blocked_live_provider_redirect_not_allowed
blocked_live_provider_private_network_not_allowed
blocked_live_provider_response_fetch_not_allowed
blocked_live_provider_network_timeout
blocked_live_provider_response_too_large
```

## 7. Reuse of Phase 3B network boundary

The future implementation reuses the Phase 3B base-URL allowlist, timeout, and
response-size enforcement, layering the live approval + kill switch on top. It
does **not** relax the existing `blocked_provider_external_url_not_allowed` /
`blocked_provider_base_url_not_allowed` gates.

## 8. Cross-references

- [Phase 3B network boundary](phase-3b-network-boundary.md)
- [Phase 3B-H1 network isolation](phase-3b-h1-provider-network-isolation.md)
- [Phase 3B-Live-Enablement budget policy](phase-3b-live-enablement-budget-policy.md)
