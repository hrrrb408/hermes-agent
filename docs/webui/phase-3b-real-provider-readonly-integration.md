# Phase 3B Implementation — Real Provider Read-only Controlled Integration

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B |
| Title | Real Provider Read-only Controlled Integration (Implementation) |
| Status | Implemented — real provider **disabled by default**; no real network in tests/smoke |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Commit | `feat(webui): add real provider read-only boundary` |

> This is the Phase 3B **implementation** closeout. It implements the
> real-provider read-only boundary planned in [phase-3b-planning.md](phase-3b-planning.md).
> Real provider remains **disabled by default**; no real network call is
> exercised by tests or smoke; no API key is read, persisted, or rendered.

---

## 1. What Phase 3B Implements

A disabled-by-default, operator-enabled, single-round-trip, non-streaming,
**read-only** real-provider path behind the existing provider boundary. It wires
the one blocked thing left by Phase 2B-H1 — the concrete real-vendor HTTPS call —
as a **gated, audited, redacted, time/retry/rate/cost-bounded** controlled path.

The boundary is a parallel, **injectable** module set: the HTTP client is a
required injected dependency (a `ProviderHttpClient` Protocol). Tests inject a
`MockHttpClient`; there is **no default real-network client wired into the live
request path**, so no real provider call ever happens in tests, smoke, or
default operation. The existing Phase 2B live `mode=real` path stays blocked
exactly as before (it does not wire a real client).

### Modes

| Mode | State |
|------|-------|
| `disabled` | default — no provider at all |
| `fake` | Phase 2B deterministic offline adapter (unchanged) |
| `real` | the gated boundary — reachable only when EVERY eligibility gate passes |

### Gating (real mode)

Real mode is eligible only when **all** hold (any failure fails closed with a
precise `blocked_provider_*` reason and `externalNetworkCalled=false`):

1. `HERMES_PROVIDER_MODE == real`
2. `HERMES_PROVIDER_API_ENABLED == 1`
3. provider name has a concrete adapter (Phase 3B ships `openai_compatible`)
4. an API key is present in the environment (read-only, never logged)
5. `HERMES_HOME` is the dev home (not `~/.hermes`)
6. the production-gateway PID gate passes (read-only observation)
7. the base URL is on the allowlist (`https://` hosts only)
8. the model is on the model allowlist
9. the timeout config is in bounds

Plus, before any network call: secret-detection, rate-limit, and budget caps.

---

## 2. Backend Deliverables

| Module | Responsibility |
|--------|----------------|
| `hermes_cli/dev_web_provider_config.py` | bounded env-driven config (clamped, allowlisted, value-free key markers) |
| `hermes_cli/dev_web_provider_real_schema.py` | frozen request / response envelopes (no key, bounded sizes) |
| `hermes_cli/dev_web_provider_real_redaction.py` | redaction + secret detection (reuses Phase 2B-H1 patterns; preserves token counts) |
| `hermes_cli/dev_web_provider_real_audit.py` | `provider_real_*` audit writers (reuse Phase 2B writer + Phase 2D dual-write) |
| `hermes_cli/dev_web_provider_real_budget.py` | cost estimate + per-minute/daily/token/budget caps (atomic, fail-closed) |
| `hermes_cli/dev_web_provider_real_policy.py` | gating → frozen-catalogue reasons; read-only allowlist; retry classification |
| `hermes_cli/dev_web_provider_openai_compatible.py` | OpenAI-compatible adapter with injectable mock HTTP client |
| `hermes_cli/dev_web_provider_openai_compatible_schema.py` | wire request/response mapping (bounded normalization) |
| `hermes_cli/dev_web_provider_real_roundtrip.py` | gated orchestrator (config → policy → adapter → audit), requires injected client |

Plus a safe, value-free `providerBoundary` block added to the existing
`GET /api/dev/v1/status` response (no new route).

### Blocked-reason catalogue (frozen)

`blocked_provider_real_not_enabled`, `blocked_provider_api_disabled`,
`blocked_provider_base_url_not_allowed`, `blocked_provider_api_key_missing`,
`blocked_provider_name_not_supported`, `blocked_provider_model_not_allowed`,
`blocked_provider_timeout_invalid`, `blocked_provider_rate_limit_exceeded`,
`blocked_provider_budget_exceeded`, `blocked_provider_response_too_large`,
`blocked_provider_tool_call_not_allowed`, `blocked_provider_write_not_allowed`,
`blocked_provider_external_url_not_allowed`, `blocked_provider_secret_detected`,
`blocked_provider_auth_failed`, `blocked_provider_malformed_response`,
`blocked_provider_schema_mismatch`, `blocked_provider_network_unavailable`,
`blocked_provider_retry_exhausted`.

### Read-only tool allowlist (reused unchanged from Phase 2A)

`clarify`, `tool_policy_read`, `route_governance_read`, `audit_events_read`,
`dev_environment_read`, `release_status_read`. Write / rollback / shell / db /
external / production / plugin-load names are each blocked with a precise reason.

---

## 3. Frontend Deliverables

- `ProviderBoundaryStatus.vue` — renders the value-free boundary metadata:
  mode label (disabled / fake / real blocked / real gated), API enabled
  (no/yes, redacted), key `env_present`/`env_missing` marker, base URL host
  (allowlisted/blocked), model, adapter, budget/rate-limit caps, the
  permanently-blocked flags (write / auto-write / autonomous / production
  rollout), the current gating reason, and the read-only tool allowlist.
- `toolProvider` store: `boundary` state + `boundaryLabel` computed +
  `loadBoundary()` (fetches `/status` providerBoundary).
- `types/api/toolProvider.ts`: `ProviderBoundaryStatus` type.
- `api/toolProvider.ts`: `fetchProviderBoundary()`.
- Wired into `ProviderRoundtripPanel.vue` (loads boundary on mount).

**The UI never renders an API-key input control, an API-key value, an
Authorization/Bearer header, a raw token, a full tokenHash, raw arguments, a
callable repr, or a production path.**

---

## 4. What Phase 3B Does NOT Do (forbidden / deferred)

Provider write; provider auto-write; provider rollback execute; autonomous
agent; streaming; multi-provider routing; background tasks / cron; production
rollout; `~/.hermes` access; production `state.db` access; dynamic plugin
loading; arbitrary-URL fetch; storing/logging/committing an API key; a new HTTP
route; reading a real API key in tests/smoke; a real network call in tests/smoke.

The Phase 3B boundary does **not** execute provider tool calls (it classifies
them); controlled-chain execution of real-provider tool calls is a future,
separately-authorized step.

---

## 5. Tests

- 9 backend test files (`tests/test_dev_web_phase_3b_provider_*.py`) — 188 cases.
- 5 frontend test files (`apps/hermes-dev-webui/src/tests/phase3b-provider-*.spec.ts`).
- 1 Playwright smoke profile + spec (`phase3b_provider_readonly_boundary`) wired
  into the `all` smoke target (fake + blocked-real; no real spend).

See [phase-3b-test-report.md](phase-3b-test-report.md).

---

## 6. Route Governance (unchanged)

OpenAPI paths **34** / runtime **34** / Tool GET **5** / Tool write HTTP route
**0** / dry-run **1** / execution **1**. **No new route.** The real round-trip
reuses the existing `mode`-branched `/tools/dry-run` + `/tools/execute` surface;
the boundary metadata rides on the existing `/status` response.

---

## 7. Production Safety

Production Gateway PID `28428` was **not** stopped / restarted / replaced /
signaled / reconfigured. Dev services bind to `127.0.0.1` only. No `~/.hermes`
access; no production `state.db` access.

---

## 8. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B config](phase-3b-provider-config.md)
- [Phase 3B schema](phase-3b-provider-schema.md)
- [Phase 3B redaction](phase-3b-provider-redaction.md)
- [Phase 3B audit](phase-3b-provider-audit.md)
- [Phase 3B UI](phase-3b-provider-ui.md)
- [Phase 3B test report](phase-3b-test-report.md)
- [Phase 3B security boundary](phase-3b-security-boundary.md)

---

## Phase 3B-H1 — Provider Boundary Hardening (completed)

Phase 3B-H1 is a deterministic hardening pass over this read-only boundary.
Result: **10 / 10 lenses PASS, P0 = 0, P1 = 0.**

- No live real-provider enablement; no real API key read; no real network call.
- Provider write / auto-write / autonomous write, production rollout remain blocked.
- Real client wiring remains deferred.
- New: 8 backend hardening tests + 5 frontend hardening tests + the
  `phase3b_h1_provider_boundary_hardening` smoke profile + the
  `run-dev-webui-phase3b-hardening-audit.sh` gate.

See [phase-3b-h1-provider-boundary-hardening](phase-3b-h1-provider-boundary-hardening.md)
and [phase-3b-h1-test-report](phase-3b-h1-test-report.md). Route governance
unchanged (34/34/5/0/1/1). Production Gateway PID `28428` untouched.
