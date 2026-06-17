# Phase 3B-Live-Enablement H1 — Network Allowlist Hardening

| Field | Value |
|-------|-------|
| Lens | 3 — Network Allowlist / No-default-network Boundary |
| Hardening ID | `LIVE-NETWORK-3B-H1-001` |
| Status | PASS |

## Scope

The only permitted live egress is a single outbound HTTPS POST to
`api.openai.com`. http / file / localhost / loopback / private IP ranges
(10 / 127 / 192.168 / 169.254 / 172.16–31), off-allowlist hosts, host mismatch
with the approval, and any redirect fail closed.

## Evidence

- Test file: `tests/test_dev_web_phase_3b_live_h1_network_hardening.py`
- Implementation: `hermes_cli/dev_web_provider_live_network.py`

## Findings & Fixes

- Allowlist is exactly `{api.openai.com}`.
- Non-https schemes (`http`, `ftp`, `file`) → `blocked_live_provider_scheme_not_https`.
- Private / loopback hosts → `blocked_live_provider_private_network_not_allowed`.
- `172.15` / `172.32` are NOT private (correctly fall through to
  `blocked_live_provider_host_not_approved`, not in allowlist).
- Off-allowlist host and host/approval mismatch → `blocked_live_provider_host_not_approved`.
- Redirects (empty / off-allowlist / private) → blocked.
- Provider external-HTTP tool denylist (`external_http`, `web_search`,
  `web_extract`, `browser_*`, `send_message`) verified.

No implementation change was required.

## Residual risk

None. No default path performs a network call.
