# Phase 3B-Live-Enablement — Network Allowlist Implementation

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Implementation) |
| Module | `hermes_cli/dev_web_provider_live_network.py` |
| Tests | `tests/test_dev_web_phase_3b_live_network_allowlist.py` |
| Date | 2026-06-17 |

Implements the frozen [network allowlist policy](phase-3b-live-enablement-network-allowlist.md).

## 1. Static allowlist

The default allowlist is **empty**; an operator-approved host must additionally
be inside the frozen static allowlist for the first live slice:

```
LIVE_ALLOWED_HOSTS = { api.openai.com }
```

## 2. `evaluate_live_network(base_url, approval_host)`

1. scheme must be `https`            else `blocked_live_provider_scheme_not_https`
2. host present                       else `blocked_live_provider_host_not_approved`
3. host private / loopback            else `blocked_live_provider_private_network_not_allowed`
4. host == approval host              else `blocked_live_provider_host_not_approved`
5. host in static allowlist           else `blocked_live_provider_host_not_approved`

Private / loopback detection covers `localhost`, `::1`, `127.0.0.0/8`,
`10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`, `169.254.0.0/16`, `0.0.0.0/8`.

## 3. Redirect / fetch policy

`validate_live_redirect(current_host, location)` blocks any redirect to a host
other than the approved allowlisted host (and any http / private redirect). The
first live slice forbids redirects in practice. A provider response triggering
an extra fetch is blocked (`blocked_live_provider_response_fetch_not_allowed`)
via `is_tool_external_http(tool_id)` (covers `external_http`, `web_search`,
`web_extract`, `browser_*`, `send_message`).

## 4. No default network call

This module is a pure decision surface. The concrete HTTP client (an injected
mock in tests) is wired only by the round-trip orchestrator, and only after
every network check passes. Default tests / smoke make **no** real network call.

## 5. Cross-references

- [Live enablement implementation](phase-3b-live-enablement-implementation.md)
- [Phase 3B network boundary](phase-3b-network-boundary.md)
