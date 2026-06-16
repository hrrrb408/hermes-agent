# Phase 3B Execution Brief — Real Provider Read-only Controlled Integration

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B |
| Title | Real Provider Read-only Controlled Integration (Execution Brief) |
| Status | Brief prepared — Phase 3B implementation **not started** |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Brief ID | `PHASE-3B-EXECUTION-BRIEF-001` |

> This brief is the one-page contract for a future, separately-authorized
> Phase 3B. **Phase 3B is not started by this planning phase.** The full
> copy-paste prompt is [phase-3b-prompt.md](phase-3b-prompt.md).

---

## 1. Name

Real Provider Read-only Controlled Integration.

## 2. Goal

Wire the **one blocked thing** left by Phase 2B-H1 — the concrete real-vendor
HTTPS round-trip inside `RealProviderAdapter` — as a disabled-by-default,
operator-enabled, single-round-trip, non-streaming, read-only path behind the
existing provider boundary. Every request / response / tool call / failure is
audited and redacted. No provider write, no auto-write, no autonomous execution,
no streaming, no multi-provider routing.

## 3. Scope (allowed)

- Provider config model (env-driven, disabled by default).
- Generic provider adapter interface; first impl = OpenAI-compatible.
- OpenAI-compatible read-only request / response schema (non-streaming).
- Real-provider disabled-by-default boundary + explicit enable flag.
- API-key env strategy (env only; never UI; never stored / logged).
- Secret redaction (reuse + extend the Phase 2B-H1 sanitizer).
- Read-only tool-call allowlist (reuse the Phase 2A `STATIC_ALLOWLIST`).
- Provider request preview (redacted) + response normalization (safe summary).
- Timeout / retry / rate-limit / cost policies (bounded, capped, audited).
- `provider_real_*` audit events (reuse the Phase 2D durable store).
- UI real-provider blocked / disabled / preview states (no API-key input).
- Tests + an additive smoke profile (fake + blocked-real; no real spend).

## 4. Non-goals (forbidden)

Provider write; provider auto-write; provider rollback execute; autonomous agent;
shell command; database mutation; external service write beyond the single
provider HTTPS call; production rollout; `~/.hermes` access; production
`state.db` access; dynamic plugin loading; streaming; multi-provider routing;
background tasks / schedule / cron; storing / logging an API key; exposing a raw
secret-bearing prompt or response; arbitrary-URL fetch; a Provider route (default
no new HTTP route).

## 5. Inputs

- Baseline: `d435b54ad9237dc3b1fca6521e8477710a4e2c60` (Phase 3A-H1).
- HERMES_HOME: `/Users/huangruibang/Code/hermes-home-dev`.
- Reused capabilities: Phase 2B provider boundary (schema / request / fake
  adapter / blocked real adapter / audit / sanitizer), Phase 2A read-only
  allowlist, Phase 2C-H1 confirmation model, Phase 2D durable audit store,
  Phase 2E/2E-H1 console shell + no-leak closure, Phase 3A workflow container.

## 6. Outputs

- A read-only real-provider round-trip path (backend) behind a generic adapter
  boundary + extended real-provider states in the provider panel (frontend).
- `provider_real_*` audit events dual-written to the Phase 2D durable store +
  dev-only provider audit JSONL.
- Cost / rate-limit counters under the dev `HERMES_HOME`.
- New tests + a new additive smoke profile (fake + blocked-real).
- Phase 3B closeout docs (scope, security boundary, test report).

## 7. Architecture notes

- The real round-trip reuses the existing `mode`-branched `/tools/dry-run` +
  `/tools/execute` surface — **no new route** (default).
- The generic adapter interface selects the concrete impl by
  `HERMES_PROVIDER_NAME`; the first impl is OpenAI-compatible (non-streaming
  `POST /v1/chat/completions`).
- The request envelope is built redacted; the response is normalized to a bounded
  summary; tool calls are validated against the read-only allowlist and flow
  through the **existing** controlled chain.
- Real mode is gated by the Phase 2B-H1 eligibility gate plus the new base-URL
  allowlist, timeout, retry, rate-limit, and cost checks.

## 8. State model

- Cost / rate-limit counters: append-only / atomic JSON under the dev
  `HERMES_HOME`; fail-closed on corruption.
- No new persisted workflow state; a provider round-trip may bind to an existing
  Phase 3A workflow step via `workflowId` (optional).

## 9. UI model

- The provider panel gains blocked / disabled / preview states for real mode,
  a redacted request preview, a safe response summary, a budget badge (safe
  metadata), and blocked-reason panels. **No API-key input control.**
- Inherits the Phase 2E-H1 accessibility + no-leak closure.
- `/#/` and the Workflow section unchanged.

## 10. Audit model

- `provider_real_*` events (request previewed / blocked / started / completed /
  failed / response redacted / tool-call requested / blocked / completed / budget
  blocked / rate-limit blocked) dual-written to the Phase 2D durable store +
  dev-only JSONL. No new audit kind beyond `provider` is assumed.

## 11. Risk gates

P0 stop conditions and P1 push-gates from
[phase-3b-security-risk-register.md](phase-3b-security-risk-register.md). In
particular: real provider disabled by default, no API-key leak, no secret in
audit/log/UI, no prompt-injection-driven disallowed call, no arbitrary URL
fetch, no provider write / auto-write / autonomous execution, no shell / db /
external write, no route drift, PID `28428` unchanged.

## 12. Test gates

- Backend unit / contract: config gating, adapter interface, request / response
  schema, redaction, read-only tool-call validation, timeout / retry / rate-limit
  / cost enforcement, audit coverage, route-governance no-new-route, no-leak.
- Frontend unit: provider panel real-states, budget badge, blocked-reason panels,
  no-leak.
- Smoke: new additive profile (fake + blocked-real; no real spend) + zero
  regression.

## 13. Commit message

```
docs(webui): plan phase 3b provider integration
```

(this planning phase). The future Phase 3B execution uses its own conventional
commit, e.g. `feat(webui): add read-only real provider round-trip`.

## 14. Final report format

A Phase 3B closeout report mirroring the Phase 3A-H1 structure: scope, what
changed, what did not change, route governance, production safety, gates,
residual risks (P2), conclusion.

---

## 15. Phase 3B Must Not Start Here

This brief is the contract for a future, separately-authorized phase. It does
not start Phase 3B. The copy-paste prompt lives at
[phase-3b-prompt.md](phase-3b-prompt.md).

---

## 16. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B scope freeze](phase-3b-provider-readonly-scope-freeze.md)
- [Phase 3B provider selection matrix](phase-3b-provider-selection-matrix.md)
- [Phase 3B API-key & secret strategy](phase-3b-api-key-and-secret-strategy.md)
- [Phase 3B network boundary](phase-3b-network-boundary.md)
- [Phase 3B request / response schema](phase-3b-provider-request-response-schema.md)
- [Phase 3B audit model](phase-3b-provider-audit-model.md)
- [Phase 3B failure / timeout / retry policy](phase-3b-failure-timeout-retry-policy.md)
- [Phase 3B cost / rate-limit policy](phase-3b-cost-and-rate-limit-policy.md)
- [Phase 3B security risk register](phase-3b-security-risk-register.md)
- [Phase 3B GO / NO-GO](phase-3b-go-no-go.md)
- [Phase 3B prompt draft](phase-3b-prompt.md)
