# Phase 3B Security Boundary

| Field | Value |
|-------|-------|
| Phase | 3B |
| Status | Implemented + verified |
| Date | 2026-06-16 |

## 1. Core invariants

1. **Real provider disabled by default.** Reachable only when every gate holds;
   any failure fails closed (`externalNetworkCalled=false`, no network call).
2. **No real network in tests/smoke.** The HTTP client is a required injected
   dependency (`ProviderHttpClient` Protocol); tests inject `MockHttpClient`.
   There is no default real-network client in the live request path.
3. **API key is env-only.** Read once into a local, attached to a single
   outbound header, dropped after the call. Never persisted, never logged,
   never audited, never rendered, never committed.
4. **Read-only tool calls only.** The provider may request only the Phase 2A
   `STATIC_ALLOWLIST`; write / rollback / shell / db / external / production /
   plugin names are each blocked with a precise reason.
5. **No provider write / auto-write / autonomous execution / rollback / shell /
   db / external-write / streaming / multi-provider routing / production
   rollout.**
6. **No new route.** Reuses the existing `mode`-branched `/tools/dry-run` +
   `/tools/execute`; boundary metadata rides `/status`. Governance stays
   34 / 34 / 5 / 0 / 1 / 1.

## 2. What never leaks

API-key value; Authorization / API-key header; raw bearer token; full
tokenHash; raw confirmation token; raw arguments containing a secret; callable /
function / bound-method repr; production path (`~/.hermes`, `state.db`); raw
request body with a secret; raw response body; full secret-bearing URL; partial
key prefix. Token COUNTS (`maxTokens`, `promptTokens`, `totalTokens`) are safe
and preserved.

## 3. Network boundary

The only allowed egress (future, when a real client is wired) is a single
outbound HTTPS POST to the allowlisted provider endpoint: timeout-bounded,
response-size-bounded (64 KiB), retry-capped (safe-transient only), rate-limited,
cost-capped. Failures safe-degrade (audited blocked reason, no side effect).

## 4. Failure / retry

No retry on auth failure (401/403), policy-block, budget exceeded, rate-limit,
response-too-large, secret-detected, malformed, or schema-mismatch. Safe-transient
(5xx / 429 / transport) retries up to the cap with bounded backoff.

## 5. Audit

Every real request / response / tool call / failure writes a `provider_real_*`
event (phase=3B, redactionApplied=true) into the Phase 2B JSONL + the Phase 2D
durable store (`auditKind=provider`). `safeMetadata` carries only value-free
markers.

## 6. Production safety

Production Gateway PID `28428` not stopped/restarted/replaced/signaled.
Dev services bind `127.0.0.1` only. No `~/.hermes` access; no production
`state.db` access. No runtime artifacts committed; no `.claude/` committed.

## 7. Residual risks (P2 — deferred)

Streaming; multi-provider routing; provider write; token encryption at rest;
multi-user namespace; live real-provider enablement (the scope is now **frozen**
under `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` — Strict Manual Real Provider
Read-only Enablement — but remains **not started**; see
[phase-3b-live-enablement-planning.md](phase-3b-live-enablement-planning.md)).

---

## Phase 3B-H1 update (completed)

The Phase 3B-H1 hardening pass (`HARDENING-3B-H1-001`) verified all 10 lenses of
this boundary: **10 / 10 PASS, P0 = 0, P1 = 0.** No live real-provider enablement,
no real API key read, no real network call. Provider write / auto-write /
autonomous write and production rollout remain blocked. The concrete real HTTP
client remains deferred. See [phase-3b-h1-provider-boundary-hardening](phase-3b-h1-provider-boundary-hardening.md).

---

## Phase 3B-Live-Enablement update (implemented — default disabled)

The live layer (`PHASE-3B-LIVE-ENABLEMENT-IMPL-001`) adds a strict manual
one-shot live gate on top of this boundary without relaxing any lens: a fresh,
single-use, 5-minute human approval; an env-only value-free secret read; an
HTTPS single-host allowlist (`api.openai.com`); frozen first-live caps
(1 request / 1000 / 200 / 5c / 0 retry / 60s); a 14-trigger kill switch; and
18 redacted dual-write `provider_live_*` audit events. The real provider stays
**disabled by default**; default tests / smoke read no real key and make no real
network call. No new route (governance unchanged 34 / 34 / 5 / 0 / 1 / 1). See
[phase-3b-live-enablement-implementation](phase-3b-live-enablement-implementation.md)
and [phase-3b-live-enablement-security-boundary](phase-3b-live-enablement-security-boundary.md).

---

## Phase 3C Planning update (scope frozen — not implemented)

The next slice — **Phase 3C — Plugin / Capability Registry** — has had its scope
**frozen** in a separate docs-only planning phase
(`PHASE-3C-PLANNING-001`) without being implemented. The Phase 3C freeze is a
**descriptive read-only layer** that references this boundary: it classifies the
existing provider capabilities (`provider.fake_roundtrip` = READ_ONLY,
`provider.real_gated_roundtrip` / `provider.live_manual_one_shot` =
LIVE_PROVIDER_GATED, `provider.write` / `provider.auto_write` /
`provider.autonomous_action` / `provider.tool_execution` = blocked) **without
relaxing any lens here**. The registry grants no permission, loads no code, adds
no route by default, and is dev-only / `productionAllowed=false`. No dynamic
plugin runtime, marketplace, or remote registry. See
[phase-3c-planning](phase-3c-planning.md),
[phase-3c-provider-capability-mapping](phase-3c-provider-capability-mapping.md),
and [phase-3c-go-no-go](phase-3c-go-no-go.md).
