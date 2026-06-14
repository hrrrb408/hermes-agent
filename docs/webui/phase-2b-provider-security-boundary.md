# Phase 2B — Provider Security Boundary

Status: **frozen**
Related: [phase-2b-provider-schema-api-integration.md](phase-2b-provider-schema-api-integration.md),
[phase-2b-provider-audit-model.md](phase-2b-provider-audit-model.md)

## 1. Boundary contract

The Provider is untrusted input. Every value it returns is validated before
it can influence execution. The boundary is enforced at four layers:

1. **Schema boundary** — the provider schema is a pure projection of
   `STATIC_ALLOWLIST`. It can never advertise a write tool, a
   provider-recursive tool, a secret, a callable/function repr, or a
   filesystem/shell/database parameter. `validate_provider_schema_bundle`
   and `validate_provider_schema_boundary` enforce this.

2. **Request boundary** — the provider request envelope is gated by mode.
   `disabled` sends nothing. `fake` sends the schema but never the network.
   `real` is blocked unless every enablement condition holds. The request
   never carries an API key.

3. **Tool-call boundary** — every provider tool call is parsed and validated
   by `validate_provider_tool_call` against `STATIC_ALLOWLIST`. Unknown,
   write-like, provider-recursive, malformed, oversized, or secret-bearing
   calls are blocked with a specific reason and never reach execution.

4. **Execution boundary** — a validated tool call flows through the
   **existing** controlled execution chain unchanged: dry-run → digest →
   confirmation token → pre-execution audit → handler lookup → dispatch →
   handler call → post-execution audit. The Provider cannot bypass any gate.

## 2. Real-mode gating

Real mode is blocked unless ALL hold:

| Condition | Check |
|-----------|-------|
| `HERMES_PROVIDER_API_ENABLED=1` | env exact match |
| `HERMES_PROVIDER_MODE=real` | env exact match |
| provider API key present | any of the accepted env keys non-empty (read only, never logged) |
| `HERMES_HOME` is dev home | not `~/.hermes` |
| production gateway PID gate | read-only `pgrep`, exactly one process at PID 1962 |
| explicit `providerMode=real` | request flag |

Even when all hold, the concrete vendor network call is **not wired** in
Phase 2B (`blocked_real_provider_not_wired_in_phase_2b`). This is a P2
deferral, recorded honestly.

## 3. Prohibited (never in Phase 2B)

- API key in any response, log, audit, or UI input.
- Raw token, full tokenHash, raw arguments, secret, or callable/function repr.
- Tool write route or write tool execution.
- Provider-requested call bypassing the controlled chain.
- `~/.hermes` access; production `state.db` access.
- Production gateway stop/restart/replace/signal.
- Production rollout.

## 4. Enforcement points

| Invariant | Enforced by |
|-----------|-------------|
| allowlist membership | `STATIC_ALLOWLIST` (single source of truth) + per-call validation |
| read-only only | registry consistency check + per-tool schema flags |
| no external network in fake | `FakeProviderAdapter` (offline) + request boundary test |
| real blocked by default | `_evaluate_real_mode_eligibility` + `RealProviderAdapter` |
| no API key leak | audit sanitizer + redaction patterns + UI has no key input |
| no new route | route governance test pins 34/34/5/0/1/1 |

## 5. Audit

See [phase-2b-provider-audit-model.md](phase-2b-provider-audit-model.md).
Every lifecycle event is written with `redactionApplied=true`; the audit
file lives under the dev `HERMES_HOME` and is never committed.

## Phase 2C Update — Controlled Tool Write Execution

Phase 2C adds a **separate** write boundary that reuses this provider
boundary's disciplines (no new route, `mode` branching, full redaction, dev
`HERMES_HOME`-only audit files). A provider may *suggest* a Phase 2C write
tool; the system generates a write **preview only** and blocks auto-execution
(`blocked_write_provider_auto_execute_denied`), with
`externalNetworkCalled=false`. The provider security boundary itself is
unchanged. See
[phase-2c-write-sandbox-security](phase-2c-write-sandbox-security.md) and
[phase-2c-write-audit-model](phase-2c-write-audit-model.md).
