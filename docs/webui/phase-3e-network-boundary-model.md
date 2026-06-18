# Phase 3E — Network Boundary Model

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — Network Boundary Model (Frozen, Design-only) |
| Status | Frozen (docs-only planning; Real Plugin Runtime **not started**) |
| Date | 2026-06-19 |
| Planning ID | `PHASE-3E-PLANNING-001` |
| Network-Boundary ID | `PHASE-3E-NETWORK-BOUNDARY-001` |

> This document designs — but does **not** implement — the network boundary a
> future real plugin runtime would require. No implementation is authorized.

## 1. Position (disabled by default)

```
Network disabled by default.
External HTTP disabled by default.
Remote registry disabled.
Marketplace disabled.
External plugin fetch disabled.
Provider-generated plugin disabled.
No plugin network egress unless separately planned.
```

## 2. Kill switch

- A dedicated network kill switch is checked **before** any socket / HTTP call.
- When the kill switch is thrown, no egress is possible and pending egress is
  cancelled.
- Kill state is audited; the runtime fails closed when killed.

## 3. Allowlist model (deny-by-default)

- Default posture: **deny all egress**.
- If egress is ever separately approved, it is via an explicit, reviewed
  allowlist of (host, port, scheme) tuples — never a wildcard.
- `http://`, `localhost`, link-local, and private-IP ranges are denied unless
  explicitly allowlisted and justified.
- Redirect chains are validated against the allowlist at every hop (no SSRF via
  redirect).

## 4. DNS policy

- DNS resolution is bounded; resolved IPs are checked against the allowlist and
  the private-IP / link-local denylist.
- DNS rebinding is mitigated by re-checking the resolved IP at connect time.

## 5. Egress audit

- Every egress attempt is audited (`runtime_network_access_*`; safe fields:
  pluginId, capabilityId, permissionClass, decision, blockedReason, devOnly,
  productionAllowed, redactionApplied).
- No URL / host / path is written to audit beyond an allowlisted host label —
  never a full URL with credentials, query, or fragment.
- Audit failure is fail-closed.

## 6. Timeout + budget

```
timeout — per-request wall-clock cap
budget  — per-plugin request / byte cap
rate    — per-plugin request-rate cap
```

Exceeding any cap kills the egress and audits `runtime_network_access_denied`.

## 7. Redaction / no-leak

- No secret headers (`Authorization`, `Bearer`, `X-Api-Key`, cookies) are sent on
  plugin egress by default.
- No API key / token is ever placed on a plugin network request.
- Egress responses are redacted before any audit / log / UI surface.
- No `Authorization` / `Bearer` leak in any runtime surface.

## 8. Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E sandbox architecture](phase-3e-sandbox-architecture.md)
- [Phase 3E process isolation model](phase-3e-process-isolation-model.md)
- [Phase 3E filesystem boundary model](phase-3e-filesystem-boundary-model.md)
- [Phase 3E supply-chain policy](phase-3e-supply-chain-policy.md)
- [Phase 3B network boundary](phase-3b-network-boundary.md)
- [Phase 3B-Live-Enablement network allowlist](phase-3b-live-enablement-network-allowlist.md)
