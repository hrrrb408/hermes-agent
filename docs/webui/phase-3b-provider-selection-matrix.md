# Phase 3B Provider Selection Matrix

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Planning |
| Title | Real Provider Class Selection Matrix |
| Status | Evaluated |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Evaluation ID | `PHASE-3B-PROVIDER-SELECT-001` |

> Companion to [phase-3b-planning.md](phase-3b-planning.md). This document scores
> the candidate provider classes for the first real round-trip and records the
> recommended first slice. **No real API is called here.** This is analysis only.

---

## 1. Scoring Dimensions

Each provider class is evaluated across 14 dimensions (qualitative Low / Medium /
High, summarized in the matrix):

| Dimension | What it measures |
|-----------|------------------|
| API compatibility | How standard / portable the protocol is |
| Tool-call support | Whether the protocol carries structured tool calls the boundary can validate |
| Streaming support | Whether first-implementation streaming is needed (deferred either way) |
| Timeout control | How well the client supports bounded connect / read timeouts |
| Retry control | How safely transient errors can be retried |
| Rate-limit control | Visibility into per-minute / daily limits |
| Cost visibility | Whether usage / cost is reported back deterministically |
| Secret handling | Risk profile of the API-key / bearer model |
| Request / response auditability | How well the payload maps to a redacted, bounded audit record |
| Schema determinism | How predictable the response / tool-call schema is |
| Failure predictability | How classifiable failures are (auth / transient / policy / oversize) |
| Dev setup complexity | How much new code / config a first impl needs |
| Security risk | Risk to the frozen safety boundary |
| Implementation complexity | Engineering effort for a read-only first slice |

---

## 2. Selection Matrix

| Provider Class | Compatibility | Tool-call | Auditability | Secret Risk | Network Risk | Cost Risk | Complexity | Decision |
|---|---|---|---|---|---|---|---|---|
| A — OpenAI-compatible | Broad (de-facto standard) | Yes | High | Medium | Medium | Medium | Medium | **First** |
| B — Anthropic-compatible | Narrow (proprietary) | Yes (different schema) | High | Medium | Medium | Medium | Medium-High | Later |
| C — Z.ai / GLM-compatible | OpenAI-ish | Yes | High | Medium | Medium | Medium | Medium | Later |
| D — OpenRouter-compatible | Broad (aggregator) | Yes | Medium | Medium-High | Medium-High | Medium-High | Medium | Later |
| E — Local mock / fake | n/a (offline) | Deterministic | High | None | None | None | Low | Baseline (keep) |

Legend: Secret / Network / Cost risk — Higher = riskier. Complexity — Higher =
harder. "First" = recommended first slice; "Later" = behind the same boundary;
"Baseline" = the existing offline fake adapter, kept as the test / smoke default.

---

## 3. Per-Class Detail

### Class A — OpenAI-compatible provider

The generic OpenAI-compatible Chat Completions protocol (`POST /v1/chat/completions`
with `messages`, `tools`, `tool_choice`, bounded `max_tokens`, `temperature`).

- **Strengths:** de-facto standard; many vendors speak it; deterministic JSON
  schema; structured tool-call array the boundary can validate against the
  allowlist; usage block reports prompt / completion tokens (cost visibility);
  mature client timeout / retry primitives; lowest-complexity first slice.
- **Risks:** standard bearer-key model (secret risk = Medium, handled by the
  Phase 2B-H1 env-only / redaction closure); network + cost are Medium and
  bounded by the timeout / retry / rate-limit / cost policy; prompt-injection
  risk is handled by read-only tool-call validation.
- **Why first:** highest compatibility, highest auditability, lowest complexity,
  most deterministic schema. Wiring it as a **generic adapter boundary** (not a
  hard-coded vendor) means classes C (Z.ai / GLM) and D (OpenRouter) reuse the
  same code path.

### Class B — Anthropic-compatible provider

The Anthropic Messages API (`POST /v1/messages` with a different message / tool
schema, a separate `x-api-key` header model, and a distinct tool-use block).

- **Strengths:** strong tool-call support; good auditability.
- **Risks:** a **different** request / response schema and a different header
  model → a separate normalization layer; secret risk is Medium.
- **Why later:** the schema divergence means it is a **second** adapter behind
  the boundary, not the first. It is explicitly in scope for a later Phase 3B
  slice using the same boundary.

### Class C — Z.ai / GLM-compatible provider

A provider that exposes an OpenAI-compatible surface (the GLM family). It reuses
the Class A protocol almost verbatim.

- **Strengths:** reuses the Class A adapter boundary; good tool-call support.
- **Risks:** endpoint-specific quirks; secret / network / cost risk Medium.
- **Why later:** because it is OpenAI-compatible, it is naturally the **second
  configuration** of the Class A adapter, not a separate first slice. It is in
  scope for a later Phase 3B slice.

### Class D — OpenRouter-compatible provider

An aggregator that speaks OpenAI-compatible but routes to many upstream models.

- **Strengths:** broad model coverage through one endpoint.
- **Risks:** an aggregator is a **second hop** — the request reaches an
  intermediary before the upstream model. That raises secret / network / cost
  risk slightly (Medium-High) and reduces auditability of the true upstream.
  Cost routing can be less deterministic.
- **Why later:** the extra hop and reduced determinism make it a poor **first**
  real round-trip. It fits cleanly behind the same boundary in a later slice.

### Class E — Local mock / fake provider baseline

The existing `FakeProviderAdapter` from Phase 2B — deterministic, offline,
sha256-derived ids, no network imports, `external_network_called=false`.

- **Strengths:** zero secret / network / cost risk; deterministic; already
  hardened.
- **Risks:** none (it is the test / smoke baseline).
- **Decision:** **keep as baseline.** The fake adapter remains the default for
  tests, smoke, and local verification throughout Phase 3B. The real adapter is
  an additional path, never a replacement.

---

## 4. Decision Rationale

Phase 3B's first slice must maximize **(compatibility × auditability × schema
determinism) ÷ (secret risk × complexity)** while staying read-only and
disabled-by-default. Class A dominates that ratio:

- It is the de-facto standard, so a **generic adapter boundary** serves classes
  A, C, and (largely) D from one code path.
- Its JSON tool-call array maps cleanly onto the existing
  `validate_provider_tool_call` boundary (allowlist, read-only, no secrets).
- Its usage block gives deterministic cost visibility (needed by the cost /
  rate-limit policy).
- Its secret / network / cost risks are all **Medium** and fully covered by the
  frozen API-key strategy, network boundary, and cost policy.

Class B is explicitly in scope but is a second adapter (different schema). Class
D's extra hop makes it a later choice. Class E stays as the offline baseline.

---

## 5. Recommended First Slice

```
Phase 3B-1 — OpenAI-compatible read-only controlled round-trip (non-streaming)
             behind a generic provider adapter boundary, disabled by default.
Phase 3B-2 — Add Anthropic-compatible + Z.ai/GLM + OpenRouter adapters behind
             the same boundary.
Phase 3B-3 — Streaming (deferred — separately authorized).
Phase 3B-4 — Multi-provider routing (deferred — separately authorized).
Phase 3B-5 — Provider write (deferred — separately authorized; not in 3B).
```

The order is **risk-ascending**: a single read-only, non-streaming round-trip
behind a generic boundary first; more adapters reuse it; streaming and routing
come later; provider write stays out of Phase 3B entirely.

---

## 6. Non-Goals of the Selection

This selection does **not** authorize:

- Calling any real provider now (this is a planning phase).
- Reading any API key now.
- Any network call now.
- Binding the system to one vendor (the boundary is generic).
- Streaming, multi-provider routing, or provider write in the first slice.
- Any production rollout.

---

## 7. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B scope freeze](phase-3b-provider-readonly-scope-freeze.md)
- [Phase 3B API-key & secret strategy](phase-3b-api-key-and-secret-strategy.md)
- [Phase 3B network boundary](phase-3b-network-boundary.md)
- [Phase 3B request / response schema](phase-3b-provider-request-response-schema.md)
- [Phase 2B provider schema / API integration](phase-2b-provider-schema-api-integration.md)
- [Phase 2B-H1 provider round-trip hardening](phase-2b-h1-provider-roundtrip-hardening.md)
