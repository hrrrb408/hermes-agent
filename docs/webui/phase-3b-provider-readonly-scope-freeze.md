# Phase 3B Provider Read-only Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Scope Freeze |
| Title | Phase 3B — Real Provider Read-only Controlled Integration (Scope Freeze) |
| Status | Frozen — Phase 3B implementation **not started** (scope frozen for a future, separately-authorized phase) |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Scope-Freeze ID | `PHASE-3B-SCOPE-FREEZE-001` |
| Selected Phase 3B | Real Provider Read-only Controlled Integration |

> This document freezes the Phase 3B scope. **Phase 3B must not start in this
> planning phase.** It may start only after the user explicitly asks for the
> Phase 3B execution prompt / implementation and separately authorizes it. This
> freeze governs the **future** Phase 3B implementation; nothing here is coded.

---

## 1. Selected Phase 3B

**Real Provider Read-only Controlled Integration.**

A disabled-by-default, operator-enabled, single-round-trip, non-streaming,
read-only real-provider path that wires the **one blocked thing** left by Phase
2B-H1 — the concrete real-vendor HTTPS call inside `RealProviderAdapter` — behind
the existing provider boundary (schema projection, request envelope, tool-call
validation, controlled execution chain, audit, sanitization). Every request,
response, tool call, and failure is audited and redacted. No provider write, no
auto-write, no rollback, no autonomous execution, no shell / db / external-write,
no production rollout, no streaming, no multi-provider routing.

---

## 2. Allowed Changes (future implementation)

| Area | Allowed |
|------|---------|
| Provider config model | New dev-only config (env-driven, **disabled by default**) |
| Provider adapter interface | A generic adapter boundary; first concrete impl = OpenAI-compatible |
| OpenAI-compatible request / response schema | New schema for the first real round-trip (non-streaming) |
| Real-provider disabled-by-default boundary | Explicit `HERMES_PROVIDER_API_ENABLED=1` + `HERMES_PROVIDER_MODE=real` required |
| API-key env strategy | Env-var only; never UI; never stored / logged / committed |
| Secret redaction | Reuse + extend the Phase 2B-H1 sanitizer; redact request / response / audit / UI |
| Read-only tool-call allowlist | Reuse the Phase 2A `STATIC_ALLOWLIST` unchanged |
| Provider request preview | Operator sees a redacted preview before the call is made |
| Provider response normalization | Safe summary; bounded size; no raw secret |
| Provider timeout / retry / rate-limit / cost policy | Bounded, capped, audited (see dedicated docs) |
| Provider request / response / tool-call / failure audit | New `provider_real_*` events (see audit model) |
| UI real-provider states | Blocked / disabled / preview states; **no API-key input control** |
| Smoke profile | New additive profile using the **fake** provider + **blocked-real** mode |
| Offline contract tests | Optional schema contract tests (no real network) |

---

## 3. Forbidden Changes (future implementation)

| Area | Forbidden |
|------|-----------|
| Provider write | No provider-driven write execution |
| Provider auto-write | No auto-execution of a write |
| Provider rollback execute | No provider-driven rollback |
| Autonomous agent | No autonomous real-provider loop; single round-trip only |
| Shell / process | No shell command execution, no process spawn |
| Database | No database mutation (no new DB, no `state.db` write) |
| External service write | No external-service write beyond the single allowed provider HTTPS call |
| Production | No production rollout, no `~/.hermes` access, no production `state.db` access |
| Routes | Default: **no new HTTP route**, no Tool write HTTP route, no Provider route — the real round-trip reuses the existing `mode`-branched `/tools/dry-run` + `/tools/execute` surface. A Provider route is forbidden unless separately approved. |
| Dynamic loading | No dynamic plugin / code loading |
| Streaming | No streaming in the first implementation |
| Multi-provider routing | No multi-provider routing in the first implementation |
| Background tasks | No background tasks / schedule / cron |
| Secret storage | No storing / logging / committing an API key or raw token |
| Raw secret exposure | No exposing a raw provider prompt or response containing secrets |
| Arbitrary URL | No arbitrary-URL fetch; base-URL allowlist only |

---

## 4. APIs Allowed

- **Reuse only** (default). No new route. The real round-trip is a new `mode`
  branch (or an extension of the existing `provider_roundtrip` mode with
  `providerMode=real`) on the **existing** surface:
  - `POST /api/dev/v1/tools/dry-run` (read-only / provider / write_preview /
    rollback_preview modes — unchanged).
  - `POST /api/dev/v1/tools/execute` (read-only / provider / write / rollback
    modes — unchanged).
  - `GET /api/dev/v1/tools/policy`, `GET /api/dev/v1/tools/audit-events`
    (read-only — unchanged).
- A **Provider route** is **not** assumed by this freeze. If one is genuinely
  required, it must be **explicitly approved and separately authorized** before
  being added — and the route-governance contract test must be updated with that
  authorization recorded.

---

## 5. Routes Allowed

**None new (default).** Route governance must remain **OpenAPI 34 / runtime 34 /
Tool GET 5 / Tool write HTTP route 0 / dry-run 1 / execution 1** unless an
explicit, separately-authorized change is approved and recorded. The default
assumption is: the real round-trip reuses the existing `mode`-branched routes.

---

## 6. Storage Allowed

| Store | Location | Notes |
|-------|----------|-------|
| Provider real-request / real-response audit | dev `HERMES_HOME` only (e.g. `$HERMES_HOME/gateway/dev/audit/`) | Dev-only, gitignored, never committed |
| Provider audit (durable) | existing Phase 2D durable store | Reused read-only / linked; `auditKind=provider` |
| Workflow state | existing dev-only store (if reached via a workflow step) | Reused |
| Confirmation tokens | existing Phase 2C-H1 file-backed store | Reused |
| Cost / rate-limit counters | dev `HERMES_HOME` only (append-only / atomic) | Dev-only, gitignored, never committed |

No API key, provider audit JSONL, cost counter, token store, rollback manifest,
or runtime audit JSONL may be committed. No `.claude/` may be committed.

---

## 7. UI Allowed

- The existing provider panel gains **blocked / disabled / preview** states for
  real mode — mirroring the Phase 2B "real mode surfaces a blocked message"
  behaviour, extended with a redacted request preview and a safe response
  summary when a real round-trip is authorized and completed.
- **The UI never accepts an API key.** No password / key / bearer input control
  and no key `v-model` binding may be added (inherit the Phase 2B-H1 Lens 8
  closure).
- The section inherits the Phase 2E-H1 accessibility baseline and the no-leak
  closure (no API key / raw token / full hash / raw args / callable repr /
  production path).
- A budget / rate-limit badge may be shown (safe metadata only).
- `/#/` (the 3-column chat workbench) and the Workflow section stay unchanged.

---

## 8. Tests Required

- Backend unit / contract tests for: config gating (disabled / fake / real),
  adapter interface, request / response schema, redaction, read-only tool-call
  validation, timeout / retry / rate-limit / cost enforcement, and audit.
- An **offline** test asserting the real adapter returns a blocked reason when
  enablement is missing (`blocked_real_provider_not_wired_in_phase_3b` or the
  eligibility-gated equivalent), with `externalNetworkCalled=false`.
- A no-leak test asserting no secret / token / hash / raw arg / callable repr /
  production path / API key crosses the provider real surface.
- A route-governance contract test asserting no new route was added (34 / 34 /
  5 / 0 / 1 / 1).
- A **smoke that does not consume real budget** — the smoke profile must use the
  fake provider + blocked-real mode only.

---

## 9. Smoke Required

- A new additive smoke profile + spec (e.g. `phase3b_provider_real_readonly`)
  wired into the `all` smoke target. It must exercise the **blocked-real** path
  (real provider disabled / not enabled → blocked reason, `externalNetworkCalled=false`)
  and the **fake** path — **never** a real network call and **never** real spend.
- Existing smoke profiles must keep passing (zero regression).

---

## 10. Production Boundary

- No production rollout.
- No `~/.hermes` access.
- No production `state.db` access.
- Production Gateway PID `28428` never stopped / restarted / replaced /
  signaled / reconfigured.
- WebUI binds to `127.0.0.1` only.

---

## 11. Provider Boundary

- Real provider is **disabled by default**. It becomes reachable only when
  `HERMES_PROVIDER_API_ENABLED=1` **and** `HERMES_PROVIDER_MODE=real` are set
  **and** every Phase 2B-H1 eligibility condition holds (API key present, dev
  home, production gate).
- Provider write stays **blocked** (`blocked_provider_write_not_allowed`); no
  auto-write; no auto-rollback.
- The base URL must be on an **allowlist** (`blocked_provider_base_url_not_allowed`
  otherwise); no arbitrary URL; no provider-requested URL fetch.

---

## 12. Network Boundary

- The **only** allowed external network in a future implementation is the single
  provider HTTPS endpoint.
- It must be timeout-bounded, response-size-bounded, retry-capped, rate-limited,
  and cost-capped.
- Any failure must **safe-degrade** to a blocked reason with no side effect.

Full detail: [phase-3b-network-boundary.md](phase-3b-network-boundary.md).

---

## 13. Audit Boundary

- Every real request / response / tool call / failure writes a `provider_real_*`
  audit event into the Phase 2D durable store (and the dev-only provider audit
  JSONL).
- No new audit kind beyond `provider` is assumed; if one is needed it must be
  explicitly approved.
- No secret / token / hash / raw arg / callable repr / API key / Authorization
  header may leak via the provider real surface (inherit the Phase 2B-H1 closure).

Full detail: [phase-3b-provider-audit-model.md](phase-3b-provider-audit-model.md).

---

## 14. Success Criteria (for a future Phase 3B implementation)

1. Provider config model implemented (env-driven, disabled by default).
2. Generic adapter interface + OpenAI-compatible read-only round-trip implemented.
3. Real-mode gating enforces **all** eligibility conditions; missing any → blocked.
4. Request preview, response normalization, redaction all work.
5. Timeout / retry / rate-limit / cost caps all enforced and audited.
6. `provider_real_*` audit events written; no secret leak.
7. UI shows blocked / disabled / preview states; no API-key input.
8. No provider write / auto-write / rollback / autonomous execution / shell / db /
   external-write / streaming / multi-provider routing / production rollout.
9. Route governance unchanged (or explicitly approved + recorded).
10. All tests pass; smoke pass (no real budget); memory-check / dev-check PASS.
11. Production untouched (PID `28428`; no `~/.hermes` / `state.db` access).

---

## 15. Phase 3B Must Not Start in This Planning Phase

This document freezes the scope. The actual Phase 3B work is deferred to a
separately authorized phase that begins only when the user explicitly asks for
the Phase 3B execution prompt / implementation. The execution brief is
[phase-3b-execution-brief.md](phase-3b-execution-brief.md); the prompt draft is
[phase-3b-prompt.md](phase-3b-prompt.md).

---

## 16. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B provider selection matrix](phase-3b-provider-selection-matrix.md)
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
