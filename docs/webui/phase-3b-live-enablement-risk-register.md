# Phase 3B-Live-Enablement — Risk Register

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Planning) |
| Title | Strict Manual Real Provider Enablement — Risk Register |
| Status | Frozen (docs-only planning; live enablement **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |

## 1. Risk model

- **P0** = stop conditions. Any materialization halts work, blocks push, and
  triggers the kill switch.
- **P1** = implementation push-gates. Must pass before a future live
  implementation can be enabled.
- **P2** = deferred sequencing risks. Non-blocking; tracked for later phases.

## 2. P0 risks (stop conditions)

| ID | Risk | Mitigation |
|----|------|-----------|
| LIV-P0-01 | Real API key leaks to audit / log / UI / exception / response / commit | Env-only read; defensive re-redaction before write; secret detection in prompt/response/args; `keyValue=never` enforced; kill switch on detection |
| LIV-P0-02 | Live provider enabled without explicit human approval | Default disabled; live layer requires a fresh, in-scope, unexpired approval; any mismatch → `blocked_live_provider_not_human_approved` / `..._approval_scope_invalid` |
| LIV-P0-03 | Provider executes a write / rollback / autonomous / shell / db / external tool | Read-only allowlist only; each forbidden name blocked with a precise reason; tool execution remains on the existing controlled chain |
| LIV-P0-04 | Arbitrary-URL fetch / off-allowlist redirect / response-driven fetch | Empty default allowlist; HTTPS-only; redirect-to-allowlist-only; no response fetch; blocked reasons |
| LIV-P0-05 | Production rollout / `~/.hermes` access / production `state.db` access | Dev-only `HERMES_HOME` gate; production path detection; PID `28428` gate |
| LIV-P0-06 | New HTTP route / Provider route / Tool write HTTP route | Route governance pinned at 34/34/5/0/1/1; re-asserted pre/post |
| LIV-P0-07 | Live request exceeds budget / runs unbounded retries / streams | First-test caps (1 request, 1000 tokens, 5 cents, 0 retries, non-streaming); atomic fail-closed counters |
| LIV-P0-08 | Production Gateway affected | PID `28428` / count `1` re-asserted; never stop/restart/replace/signal |

## 3. P1 risks (push-gates for the future implementation)

| ID | Risk | Gate |
|----|------|------|
| LIV-P1-01 | Approval record accidentally stores a secret | Approval schema frozen with forbidden-fields list; test asserts no forbidden field is present |
| LIV-P1-02 | Counter corruption allows over-spend | `failClosedOnCounterError=true`; unreadable counter → `blocked_live_provider_counter_unavailable` |
| LIV-P1-03 | Kill switch does not abort in-flight call | In-flight abort path + smoke that triggers kill switch mid-request |
| LIV-P1-04 | Audit write failure silently drops an event | Audit write failure on live request → fail closed + best-effort `provider_live_enablement_failed` |
| LIV-P1-05 | Live smoke escapes into the default `all` target | Layer 6 is opt-in / operator-witnessed only; never in default smoke |
| LIV-P1-06 | Token / cost estimate carries key material | Estimates derived from counts only; sanitizer applied before audit |

## 4. P2 risks (deferred)

| ID | Risk | Disposition |
|----|------|-------------|
| LIV-P2-01 | Streaming live responses | Deferred to a later phase; first live test is non-streaming |
| LIV-P2-02 | Multi-provider live routing | Deferred to a later phase |
| LIV-P2-03 | Token encryption at rest | Reuses Phase 3B residual P2; not introduced here |
| LIV-P2-04 | Live tool-call execution chain | Provider tool calls are classified/blocked, not executed, in the first live test; execution is a separately-authorized future step |
| LIV-P2-05 | Long-window / recurring approvals | Out of scope; first live test is single-use, 5 minutes |

## 5. Relationship to existing registers

This register is additive to
[phase-3b-security-risk-register.md](phase-3b-security-risk-register.md) and
[phase-1g-05-risk-register.md](phase-1g-05-risk-register.md). It does not relax
any P0/P1 there; it adds the live-layer risks.

## 6. Cross-references

- [Phase 3B-Live-Enablement GO / NO-GO](phase-3b-live-enablement-go-no-go.md)
- [Phase 3B-Live-Enablement scope freeze](phase-3b-live-enablement-scope-freeze.md)
- [Phase 3B security risk register](phase-3b-security-risk-register.md)
