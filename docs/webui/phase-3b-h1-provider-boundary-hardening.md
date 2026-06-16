# Phase 3B-H1 — Provider Boundary Hardening

- **Hardening ID:** HARDENING-3B-H1-001
- **Phase:** 3B-H1 (a hardening pass over the Phase 3B real-provider read-only boundary)
- **Status:** completed
- **Input HEAD:** b2ee4fdb7521612e210a15499c35b92f73c6d8c9
- **Live real-provider:** NOT enabled
- **Real API key read:** NO
- **Real network call:** NO
- **Provider write / auto-write / autonomous write:** blocked
- **Production rollout:** NOT performed

## Goal

Phase 3B-H1 hardens the Phase 3B real-provider read-only boundary. It is a
deterministic, test-and-document hardening pass — no live real-provider enablement,
no real API key read, no real network call, no provider write, no autonomous write,
no production rollout. Real client wiring remains deferred to a future phase.

This document is the umbrella hardening summary. The focused boundary areas are
documented separately:

- Secret / Authorization redaction — [phase-3b-h1-provider-secret-redaction.md](phase-3b-h1-provider-secret-redaction.md) (`PROVIDER-SECRET-3B-H1-001`)
- Network isolation / mock-only — [phase-3b-h1-provider-network-isolation.md](phase-3b-h1-provider-network-isolation.md) (`PROVIDER-NETWORK-3B-H1-001`)
- Policy hardening (base URL / timeout / retry / budget / rate-limit / size) — [phase-3b-h1-provider-policy-hardening.md](phase-3b-h1-provider-policy-hardening.md) (`PROVIDER-POLICY-3B-H1-001`)
- Audit no-leak — [phase-3b-h1-provider-audit-security.md](phase-3b-h1-provider-audit-security.md) (`PROVIDER-AUDIT-3B-H1-001`)
- Frontend UI no-leak — [phase-3b-h1-provider-ui-security.md](phase-3b-h1-provider-ui-security.md) (`PROVIDER-UI-3B-H1-001`)
- Test report — [phase-3b-h1-test-report.md](phase-3b-h1-test-report.md)

## 10-Lens Review

| Lens | Name | Status |
|------|------|--------|
| 1 | Provider Config / Mode Gate Boundary | PASS |
| 2 | API Key / Secret / Authorization Redaction Boundary | PASS |
| 3 | Network Isolation / Mock-only Boundary | PASS |
| 4 | Base URL / Timeout / Retry Boundary | PASS |
| 5 | Budget / Rate-limit / Response-size Boundary | PASS |
| 6 | Request / Response Schema Normalization Boundary | PASS |
| 7 | Read-only Tool-call Allowlist Boundary | PASS |
| 8 | provider_real_* Audit No-leak Boundary | PASS |
| 9 | Frontend Provider Boundary UI No-leak Boundary | PASS |
| 10 | Smoke / Route Governance / Production Isolation Boundary | PASS |

Result: **10 / 10 PASS, P0 = 0, P1 = 0.**

## Provider Boundary (unchanged in capability, hardened in verification)

- **Modes:** `disabled` (default), `fake` (deterministic offline), `real` (gated).
- **Default:** disabled.
- **Real-gated:** reachable only when EVERY gate passes (mode=real, API_ENABLED=1,
  implemented name, key present, dev home, production PID gate, allowlisted base
  URL, allowlisted model, bounded timeout). No default code path wires a real
  HTTP client, so no real provider call happens in tests, smoke, or default operation.
- **Fake:** deterministic, offline, unchanged.
- **API key source:** environment only — read for presence, never the value,
  never persisted, never rendered in the UI, never written to audit.
- **Network:** mock-only in tests/smoke; the HTTP client is an injected Protocol.
- **Read-only tool allowlist:** `clarify`, `tool_policy_read`,
  `route_governance_read`, `audit_events_read`, `dev_environment_read`,
  `release_status_read`.

## Deliverables

- **Hardening audit script:** `scripts/run-dev-webui-phase3b-hardening-audit.sh`
- **Backend hardening tests:** 8 files (329 tests) under `tests/`.
- **Frontend hardening tests:** 5 files (30 tests) under `apps/hermes-dev-webui/src/tests/`.
- **Smoke:** `phase3b_h1_provider_boundary_hardening` profile +
  `tests/smoke/phase-3b-h1-provider-boundary-hardening-smoke.spec.ts`.
- **Docs:** this file + 5 focused hardening docs + the test report.

## Deferred / Not Implemented

- Live real-provider enablement (scope now frozen under
  `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001`; implementation not started).
- Real HTTP client wiring (urllib concrete client) into the live request path.
- Real API key reading in tests/smoke.
- Streaming, multi-provider routing, provider write, provider auto-write,
  autonomous write, production rollout, plugin registry.
- Phase 3C (not started).

## Phase 3B-Live-Enablement Planning note (2026-06-17)

A docs-only planning pass froze the Strict Manual Real Provider Read-only
Enablement scope (human approval, env-only secret read, empty-default HTTPS
allowlist, strict budget / rate-limit caps, read-only tool allowlist, redacted
dual-write audit, kill switch / rollback, layered smoke). It adds the live
layer on top of this hardened boundary without relaxing any lens here. No live
enablement; no real HTTP client wiring; no real API key read; no real network
call. See [phase-3b-live-enablement-planning](phase-3b-live-enablement-planning.md)
and [phase-3b-live-enablement-risk-register](phase-3b-live-enablement-risk-register.md).

## Residual Risk

- P0: none.
- P1: none.
- P2: the `blocked_provider_retry_exhausted` reason is produced only by the
  adapter's defensive post-loop code; under the current bounded retry logic the
  terminal transient failure surfaces as `blocked_provider_network_unavailable`.
  Both are non-retryable-terminal and fail closed, so the retry-storm invariant
  holds; the hardening tests pin the actual capped behavior.
