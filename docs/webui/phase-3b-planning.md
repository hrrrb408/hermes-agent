# Phase 3B Planning — Real Provider Read-only Controlled Integration Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Planning |
| Title | Real Provider Read-only Controlled Integration — Scope Freeze, Risk Gate & Prompt Preparation |
| Status | Planning complete; Phase 3B implementation **not started** |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Planning type | docs-only — no product code, no frontend, no backend, no script |
| Input HEAD | `d435b54ad9237dc3b1fca6521e8477710a4e2c60` |
| Input HEAD message | `chore(webui): harden agent workflow mvp` |
| Predecessor | Phase 3A-H1 (Workflow Hardening) — completed and pushed |

> **This is a planning phase.** It freezes the Phase 3B scope (Real Provider
> Read-only Controlled Integration), records the provider selection matrix, the
> API-key / secret strategy, the network boundary, the request / response schema,
> the audit model, the failure / timeout / retry policy, the cost / rate-limit
> policy, the security risk register, the GO / NO-GO decision, the execution
> brief, and the Phase 3B execution prompt — **and prepares nothing executable.**
> **Phase 3B is not implemented here.** No real provider is enabled, no real
> network call is made, no API key is read, no production rollout is performed,
> no shell / database / external-service write is introduced, and no new HTTP
> route is added. The real provider remains **blocked by default** exactly as it
> was after Phase 2B-H1 and Phase 3A-H1.

---

## 1. Phase 3B Planning ID

`PHASE-3B-PLANNING-001`

---

## 2. Current Baseline

| Item | Value |
|------|-------|
| Branch | `dev-huangruibang` |
| Local HEAD | `d435b54ad9237dc3b1fca6521e8477710a4e2c60` |
| Remote HEAD | `d435b54ad9237dc3b1fca6521e8477710a4e2c60` |
| Merge base | `d435b54ad9237dc3b1fca6521e8477710a4e2c60` |
| Ahead / behind | 0 / 0 |
| Tracked worktree | clean |
| Only untracked | `.claude/` |
| HERMES_HOME | `/Users/huangruibang/Code/hermes-home-dev` |
| Production Gateway expected PID | `28428` |
| Production Gateway observed PID | `28428` |
| Production Gateway process count | `1` |
| Dev Gateway | stopped |
| Dashboard | not started |
| 5180 / 5181 | free / free |
| `~/.hermes` access | none |
| Production `state.db` access | none |

### Route governance baseline (frozen)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 34 |
| Runtime routes | 34 |
| Tool GET | 5 |
| Tool write HTTP route | 0 |
| Tool dry-run route | 1 |
| Tool execution route | 1 |

### Completed capability chain

```
Read-only Tools (2A)
  → Provider Fake Round-trip (2B)
    → Sandbox Write (2C)
      → Rollback (2C-H1)
        → Durable Audit Store / Indexing (2D)
          → Audit Store Hardening (2D-H1)
            → Unified Dev Console (2E)
              → Frontend UX Hardening (2E-H1)
                → Dev-only Agent Workflow MVP (3A)
                  → Workflow Hardening (3A-H1)
                    → Phase 3B Planning (this phase — docs only)
```

Phase 1G = SEALED. Phase 2 = functionally complete for dev-only controlled tool
execution and auditability. Phase 3A / 3A-H1 = the dev-only workflow container
is implemented and hardened. **The real provider vendor call is still NOT wired**
— Phase 2B-H1 left it as a deliberately blocked framework
(`blocked_real_provider_not_wired_in_phase_2b`).

---

## 3. What Already Exists (the Phase 2B provider boundary — inherited)

Phase 3B does **not** invent the provider boundary from nothing. Phase 2B / 2B-H1
already built the controlled framework that Phase 3B will extend:

| Already built (Phase 2B / 2B-H1) | State entering Phase 3B |
|----------------------------------|--------------------------|
| Provider schema projection from `STATIC_ALLOWLIST` (6 read-only tools) | Exists, hardened |
| Provider request envelope (never carries an API key) | Exists, hardened |
| `FakeProviderAdapter` (deterministic, offline) | Exists |
| `RealProviderAdapter` (blocked framework) | Exists but **not wired** — returns `blocked_real_provider_not_wired_in_phase_2b` |
| Real-mode eligibility gate (`_evaluate_real_mode_eligibility`) | Exists — requires enablement env, mode env, API key present, dev home, production gate |
| Provider audit writer + Phase 2D durable-store dual-write | Exists, hardened (PEM / suffixed-secret closure applied) |
| Sanitizer (`sk-…`, `Bearer …`, `Authorization: …`, PEM, forbidden field stems, `<non_json_value>`) | Exists, hardened |
| Route discipline (mode branching on existing `/tools/dry-run` + `/tools/execute`) | Exists — 34 / 34 / 5 / 0 / 1 / 1 |

Phase 3B's job is to take the **one blocked thing** — the concrete real-vendor
HTTPS round-trip inside `RealProviderAdapter` — and turn it into a **read-only,
disabled-by-default, audited, redacted, time / retry / rate / cost-bounded**
controlled path. Everything else (schema, request envelope, tool-call validation,
controlled execution chain, audit, sanitization) is **reused unchanged**.

---

## 4. Phase 3B Objective

Phase 3B grows the Dev WebUI from **"a real provider is wired as a blocked
framework"** into **"a real provider can make a single read-only HTTPS
round-trip under explicit operator enablement, with full audit and redaction"** —
while preserving every Phase 1G / Phase 2 / Phase 3A safety invariant.

The objective of this **planning** phase is:

1. Freeze the Phase 3B scope (what a future implementation may and may not do).
2. Decide which provider class to wire first (selection matrix).
3. Freeze the API-key / secret strategy, network boundary, request / response
   schema, audit model, failure / timeout / retry policy, cost / rate-limit
   policy, and security risk register.
4. Record the GO / NO-GO decision.
5. Prepare the Phase 3B execution prompt — **without executing it.**

Phase 3B is **not** a single deliverable and **not** a green light to call a real
provider. It is a separately authorized slice whose implementation may begin only
when the user explicitly asks for the Phase 3B execution prompt.

---

## 5. Provider Candidate Options

Five provider classes were evaluated for the first real round-trip. Full matrix
in [phase-3b-provider-selection-matrix.md](phase-3b-provider-selection-matrix.md).

| Class | Direction |
|-------|-----------|
| A | OpenAI-compatible provider (generic adapter boundary) |
| B | Anthropic-compatible provider |
| C | Z.ai / GLM-compatible provider |
| D | OpenRouter-compatible provider |
| E | Local mock / fake provider baseline (already exists) |

---

## 6. Evaluation Matrix (summary)

| Class | Compatibility | Tool-call | Auditability | Secret Risk | Network Risk | Cost Risk | Complexity | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---|
| A — OpenAI-compatible | Broad (de-facto standard) | Yes | High | Medium | Medium | Medium | Medium | **First** |
| B — Anthropic-compatible | Narrow (proprietary) | Yes (different schema) | High | Medium | Medium | Medium | Medium-High | Later |
| C — Z.ai / GLM-compatible | OpenAI-ish | Yes | High | Medium | Medium | Medium | Medium | Later |
| D — OpenRouter-compatible | Broad (aggregator) | Yes | Medium | Medium-High | Medium-High | Medium-High | Medium | Later |
| E — Local mock / fake | n/a (offline) | Deterministic | High | None | None | None | Low | Baseline (keep) |

Scoring detail and rationale: [phase-3b-provider-selection-matrix.md](phase-3b-provider-selection-matrix.md).

---

## 7. Recommended Path

```
Phase 3B-1 — OpenAI-compatible read-only controlled round-trip (non-streaming)   ← first slice
Phase 3B-2 — Additional provider classes (Anthropic / Z.ai / OpenRouter) behind the same boundary
Phase 3B-3 — Streaming (deferred)
Phase 3B-4 — Multi-provider routing (deferred)
Phase 3B-5 — Provider write (deferred — separately authorized, not in 3B)
```

**Rationale:** Phase 3B does **not** bind to a single vendor. The first slice
implements a **generic OpenAI-compatible adapter boundary** because that protocol
is the de-facto standard and is the lowest-complexity, most-auditable, most-
deterministic first real round-trip. Real provider stays **disabled by default**.
The first implementation is **non-streaming** and **read-only**. Streaming,
multi-provider routing, and provider write are all deferred to later, separately
authorized slices.

---

## 8. Phase 3B Proposed Scope (allowed, frozen for a future implementation)

| # | Allowed (future implementation) |
|---|----------------------------------|
| 1 | Provider config model (env-driven, disabled by default) |
| 2 | Generic provider adapter interface |
| 3 | OpenAI-compatible request / response schema |
| 4 | Real-provider disabled-by-default boundary + explicit enable flag |
| 5 | API-key environment-variable strategy (env only, never UI) |
| 6 | Secret redaction strategy (request / response / audit / UI) |
| 7 | Read-only tool-call allowlist (the Phase 2A `STATIC_ALLOWLIST`) |
| 8 | Provider request preview (operator sees what will be sent, redacted) |
| 9 | Provider response normalization (safe summary, no raw secret) |
| 10 | Provider timeout policy (connect / read / request caps) |
| 11 | Provider retry policy (safe-transient only, capped) |
| 12 | Provider rate-limit policy (per-minute / daily caps) |
| 13 | Provider cost-estimate / daily-budget-cap policy |
| 14 | Provider request / response / tool-call / failure audit |
| 15 | UI real-provider blocked / disabled / preview states |
| 16 | Smoke profile using the **fake** provider + blocked-real mode |
| 17 | Optional offline contract tests for the provider schema |

Full freeze: [phase-3b-provider-readonly-scope-freeze.md](phase-3b-provider-readonly-scope-freeze.md).

---

## 9. Phase 3B Non-Goals (forbidden, frozen)

| # | Forbidden |
|---|-----------|
| 1 | Provider write (no provider-driven write execution) |
| 2 | Provider auto-write (no auto-execution of a write) |
| 3 | Provider rollback execute |
| 4 | Autonomous agent (no autonomous real-provider loop) |
| 5 | Shell command |
| 6 | Database mutation |
| 7 | External service write beyond the single allowed provider HTTPS call |
| 8 | Production rollout |
| 9 | `~/.hermes` access |
| 10 | Production `state.db` access |
| 11 | Dynamic plugin loading |
| 12 | Streaming in the first implementation |
| 13 | Multi-provider routing in the first implementation |
| 14 | Background tasks / schedule / cron |
| 15 | Storing / logging / committing an API key |
| 16 | Exposing a raw provider prompt containing secrets |
| 17 | Exposing a raw provider response containing secrets |
| 18 | Arbitrary-URL fetch (base-URL allowlist only) |
| 19 | A Provider route (default: no new HTTP route) |

---

## 10. API Key / Secret Strategy (frozen)

| Field | Value |
|-------|-------|
| API-key source | **environment variable only** |
| UI API-key input | **no** |
| Stored in workflow store | **no** |
| Stored in audit store | **no** |
| Stored in provider request audit | **no** |
| Stored in provider response audit | **no** |
| Stored in frontend state / localStorage / sessionStorage | **no** |
| Real key in docs examples | **no** (placeholders only) |
| Logged value | **no** (only `env_present` / `env_missing`) |
| Authorization header printed / stored | **no** |
| Raw bearer token stored | **no** |

Full strategy: [phase-3b-api-key-and-secret-strategy.md](phase-3b-api-key-and-secret-strategy.md).

Suggested env-var surface (read **only** in a future implementation, not here):

```
HERMES_PROVIDER_MODE=disabled|fake|real
HERMES_PROVIDER_API_ENABLED=0|1
HERMES_PROVIDER_NAME=openai_compatible|anthropic_compatible|zai_compatible|openrouter_compatible
HERMES_PROVIDER_BASE_URL=<allowlisted; redacted in audit>
HERMES_PROVIDER_MODEL=<safe string>
HERMES_PROVIDER_TIMEOUT_SECONDS=<bounded number>
HERMES_PROVIDER_MAX_RETRIES=<bounded number>
HERMES_PROVIDER_DAILY_BUDGET_CENTS=<bounded number>
```

The provider API-key env vars (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `ZAI_API_KEY`,
`OPENROUTER_API_KEY`) are **only** referenced as future-implementation suggestions
in this planning phase. **They are never read here.**

---

## 11. Network Boundary (frozen)

| Field | Value |
|-------|-------|
| Allowed external network (future implementation) | the single provider HTTPS endpoint only |
| Default state | **disabled** |
| Enablement | requires `HERMES_PROVIDER_API_ENABLED=1` **and** `HERMES_PROVIDER_MODE=real` |
| URL policy | base-URL allowlist only — no arbitrary URL |
| Provider-requested URL fetch | **blocked** |
| Tool external HTTP | **blocked** |
| shell / curl / httpx arbitrary call | **blocked** |
| Timeout / max-response-size / retry-cap / rate-limit / cost-cap | **all required** |
| Network failure | **safe degrade** (blocked reason, no side effect) |

Full boundary: [phase-3b-network-boundary.md](phase-3b-network-boundary.md).

Frozen `blocked_provider_*` reason catalogue:
`blocked_provider_real_not_enabled`, `blocked_provider_api_disabled`,
`blocked_provider_base_url_not_allowed`, `blocked_provider_api_key_missing`,
`blocked_provider_timeout_invalid`, `blocked_provider_rate_limit_exceeded`,
`blocked_provider_budget_exceeded`, `blocked_provider_response_too_large`,
`blocked_provider_tool_call_not_allowed`, `blocked_provider_write_not_allowed`,
`blocked_provider_external_url_not_allowed`, `blocked_provider_secret_detected`.

---

## 12. Request / Response Schema (frozen)

Full schema: [phase-3b-provider-request-response-schema.md](phase-3b-provider-request-response-schema.md).

The provider request envelope **includes** `providerMode`, `providerName`,
`model`, `requestId`, `conversationId`, `workflowId`, `toolAllowlist`, `messages`,
`maxTokens`, `temperature`, `timeoutSeconds`, `redactionPolicy`, `auditRequired`
— and **never includes** `apiKey`, an Authorization header, a raw secret / token,
a full tokenHash, a production path, raw file content, or a callable repr.

The provider response envelope **includes** `requestId`, `responseId`,
`providerName`, `model`, `status`, `contentSummary`, `toolCalls`, `usageSummary`,
`finishReason`, `blockedReason`, `auditLinks`, `redactionApplied` — and **never
includes** a raw secret, an API key, an Authorization header, a raw token, a full
tokenHash, a callable repr, or an unbounded raw response.

---

## 13. Read-only Tool-call Allowlist (frozen)

Phase 3B's first implementation allows the provider to request **only** these
read-only tools (the Phase 2A `STATIC_ALLOWLIST`):

```
clarify, tool_policy_read, route_governance_read, audit_events_read,
dev_environment_read, release_status_read
```

Forbidden (each maps to a precise blocked reason): `dev_sandbox_file_write`,
`dev_sandbox_file_append`, `dev_sandbox_file_patch`, `dev_sandbox_file_readback`,
`dev_sandbox_rollback_execute`, `shell`, `database`, `external_http`,
`production_operation`, `plugin_dynamic_load`.

A provider tool call must: validate tool id → validate args → dry-run → manual
approval if required → execute read-only → write provider tool-call audit → write
tool-result audit → return a safe summary (never raw args / secrets / tokens).

---

## 14. Audit Model (frozen)

Full model: [phase-3b-provider-audit-model.md](phase-3b-provider-audit-model.md).

Frozen audit events:

```
provider_real_request_previewed
provider_real_request_blocked
provider_real_request_started
provider_real_request_completed
provider_real_request_failed
provider_real_response_redacted
provider_real_tool_call_requested
provider_real_tool_call_blocked
provider_real_tool_call_completed
provider_real_budget_blocked
provider_real_rate_limit_blocked
```

Every audit record carries `providerName`, `providerMode`, `requestId`,
`responseId`, `workflowId`, `toolCallId`, `toolId`, `status`, `blockedReason`,
`redactionApplied`, `usageSummary`, `costEstimate`, `safeMetadata` — and **never**
an API key, an Authorization header, a raw prompt / response containing secrets,
a raw token, a full tokenHash, file content, a callable repr, or a production
path.

---

## 15. Failure / Timeout / Retry Policy (frozen)

Full policy: [phase-3b-failure-timeout-retry-policy.md](phase-3b-failure-timeout-retry-policy.md).

Frozen invariants: bounded connect / read / request timeouts; capped retries on
**safe transient** errors only; **no retry** on auth failure, budget exceeded, or
policy-blocked; response-size limit; malformed-JSON fallback; tool-call
schema-mismatch fallback; provider-unavailable fallback; every failure audited; UI
shows a safe blocked / error state; **no raw stack trace in the UI**.

---

## 16. Cost / Rate-limit Policy (frozen)

Full policy: [phase-3b-cost-and-rate-limit-policy.md](phase-3b-cost-and-rate-limit-policy.md).

Frozen invariants: daily request cap, per-minute request cap, daily token cap,
daily budget cap, per-request max-token, model allowlist, cost estimate **before**
request, usage summary **after** request, budget-exceeded blocked reason, audited
budget decisions, UI budget badge, **smoke must not consume real budget**.

---

## 17. Phase 3B Risk Model

| Tier | Count | Examples |
|------|-------|----------|
| P0 | see register | real provider enabled without authorization, API-key leak, secret in audit/log/UI, prompt-injection-driven tool call, external-URL fetch, route drift, autonomous write, production rollout, `~/.hermes` access |
| P1 | see register | timeout / retry storm, rate-limit bypass, budget-cap bypass, response-size DoS, audit gap, redaction regression, response normalization drift, smoke real-budget leak |
| P2 | see register | streaming deferred, multi-provider routing deferred, provider write deferred, token encryption at rest deferred, multi-user namespace deferred |

Full register: [phase-3b-security-risk-register.md](phase-3b-security-risk-register.md).

---

## 18. GO / NO-GO Recommendation

| Field | Value |
|-------|-------|
| Decision | **GO** for Phase 3B Implementation prompt preparation only |
| Selected Phase 3B scope | Real Provider Read-only Controlled Integration |
| Real provider allowed in future implementation | yes, but **disabled by default** |
| Provider write allowed | **no** |
| Provider auto-write allowed | **no** |
| Autonomous write allowed | **no** |
| Production rollout allowed | **no** |
| Shell / DB / external write allowed | **no** |
| New HTTP route allowed (default) | **no** |
| API-key source | env only |
| UI API-key input | **no** |
| Audit required | **yes** |
| Human approval required before implementation | **yes** |
| Phase 3B implementation may start | only after the user explicitly asks for the execution prompt |

Full decision: [phase-3b-go-no-go.md](phase-3b-go-no-go.md).

**Phase 3B Implementation must not start until the user explicitly asks for the
execution prompt.** This planning phase only freezes scope and prepares the draft.

---

## 19. Safety Boundaries Preserved by This Planning Phase

No production rollout. No `~/.hermes` access. No production `state.db` access.
No shell command execution. No database mutation. No external service write.
No real provider vendor network call (real provider stays blocked by default —
`blocked_real_provider_not_wired_in_phase_2b`). No API key is read, logged,
printed, or committed. No Provider auto-write / auto-rollback. No new HTTP route.
No Tool write HTTP route. No Provider route. No audit / token / rollback-manifest
/ runtime-JSONL artifact committed. No `.claude/` committed. No API key / raw
token / full tokenHash / raw arguments / callable repr exposed. Route governance
stays 34 / 34 / 5 / 0 / 1 / 1. Production Gateway PID `28428` untouched.

---

## 20. Deliverables of This Planning Phase

| Deliverable | Path |
|-------------|------|
| Phase 3B planning (this doc) | `phase-3b-planning.md` |
| Provider read-only scope freeze | `phase-3b-provider-readonly-scope-freeze.md` |
| Provider selection matrix | `phase-3b-provider-selection-matrix.md` |
| API-key & secret strategy | `phase-3b-api-key-and-secret-strategy.md` |
| Network boundary | `phase-3b-network-boundary.md` |
| Request / response schema | `phase-3b-provider-request-response-schema.md` |
| Audit model | `phase-3b-provider-audit-model.md` |
| Failure / timeout / retry policy | `phase-3b-failure-timeout-retry-policy.md` |
| Cost / rate-limit policy | `phase-3b-cost-and-rate-limit-policy.md` |
| Security risk register | `phase-3b-security-risk-register.md` |
| GO / NO-GO | `phase-3b-go-no-go.md` |
| Execution brief | `phase-3b-execution-brief.md` |
| Prompt draft | `phase-3b-prompt.md` |
| Read-only provider threat model (optional) | `phase-3b-readonly-provider-threat-model.md` |
| Redaction & no-leak policy (optional) | `phase-3b-provider-redaction-and-no-leak-policy.md` |

Updated: `phase-1-implementation-plan.md`, `phase-1g-05-risk-register.md`,
`phase-3-scope-freeze.md`, `phase-3-go-no-go.md`,
`phase-3a-h1-workflow-hardening.md`.

---

## 21. Cross-References

- [Phase 3 planning](phase-3-planning.md)
- [Phase 3 options evaluation](phase-3-options-evaluation.md)
- [Phase 3 scope freeze](phase-3-scope-freeze.md)
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)
- [Phase 3 risk register](phase-3-risk-register.md)
- [Phase 3A dev-only agent workflow MVP](phase-3a-dev-only-agent-workflow-mvp.md)
- [Phase 3A-H1 workflow hardening](phase-3a-h1-workflow-hardening.md)
- [Phase 2B-H1 provider round-trip hardening](phase-2b-h1-provider-roundtrip-hardening.md)
- [Phase 2B provider security boundary](phase-2b-provider-security-boundary.md)
- [Phase 2B provider audit model](phase-2b-provider-audit-model.md)
- [Phase 2B provider schema / API integration](phase-2b-provider-schema-api-integration.md)
- [Phase 2D-H1 audit storage hardening](phase-2d-h1-audit-storage-hardening.md)
- [Phase 3B scope freeze](phase-3b-provider-readonly-scope-freeze.md)
- [Phase 3B selection matrix](phase-3b-provider-selection-matrix.md)
- [Phase 3B API-key & secret strategy](phase-3b-api-key-and-secret-strategy.md)
- [Phase 3B network boundary](phase-3b-network-boundary.md)
- [Phase 3B request / response schema](phase-3b-provider-request-response-schema.md)
- [Phase 3B audit model](phase-3b-provider-audit-model.md)
- [Phase 3B failure / timeout / retry policy](phase-3b-failure-timeout-retry-policy.md)
- [Phase 3B cost / rate-limit policy](phase-3b-cost-and-rate-limit-policy.md)
- [Phase 3B security risk register](phase-3b-security-risk-register.md)
- [Phase 3B GO / NO-GO](phase-3b-go-no-go.md)
- [Phase 3B execution brief](phase-3b-execution-brief.md)
- [Phase 3B prompt draft](phase-3b-prompt.md)

---

## 22. Conclusion

Phase 3B Planning is complete. The **Real Provider Read-only Controlled
Integration** scope has been frozen: a generic OpenAI-compatible adapter boundary
is recommended as the first slice, real provider stays **disabled by default** and
**read-only**, provider write / auto-write / rollback / autonomous execution /
shell / db / external-write / production-rollout / streaming / multi-provider
routing are all **forbidden**, every request / response / tool-call / failure is
audited and redacted, and the API key is env-only with no UI input. This was a
**docs-only** planning phase — no product code, frontend, backend, or script was
modified; no real provider call was made; no API key was read; no external network
call was made. Phase 3B **implementation was not started**. Route governance stays
34 / 34 / 5 / 0 / 1 / 1 and the Production Gateway PID `28428` is untouched.
