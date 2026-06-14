# Phase 2B — Provider Schema / API Controlled Integration

Status: **implemented (fake provider round-trip); real provider blocked by default**
Branch: `dev-huangruibang`
Predecessor: Phase 2A-H1 (deterministic 7-lens hardening + adversarial review closure)

## 1. Goal

Upgrade the Hermes Dev WebUI from "the user manually selects a read-only tool
to execute" to "a Provider can, under controlled conditions, select a
read-only tool and complete a tool-call round-trip."

The Provider may only select tools projected from the Phase 2A read-only
allowlist. Every Provider-requested tool call flows through the existing
controlled execution chain (dry-run → digest → confirmation token →
pre-execution audit → handler lookup → dispatch → handler call →
post-execution audit). Nothing about the chain is bypassed.

## 2. Provider Modes

| Mode | Schema sent | Provider API called | External network | Default |
|------|-------------|---------------------|------------------|---------|
| `disabled` | false | false | false | **yes** |
| `fake` | true | true (deterministic fake adapter) | false | — |
| `real` | true (only when fully enabled) | true (only when fully enabled) | true (only when fully enabled) | blocked |

`disabled` is the default. `fake` is deterministic and offline and is the
mode used by tests, smoke, and local verification. `real` is the controlled
framework for a real external Provider API and is **blocked by default**;
even when fully enabled it does not perform a real network call in Phase 2B
(the concrete vendor call is deferred — see Phase 2B P2 backlog).

Real mode requires ALL of:
- `HERMES_PROVIDER_API_ENABLED=1`
- `HERMES_PROVIDER_MODE=real`
- a provider API key present in the environment (read only, never logged)
- `HERMES_HOME` is the dev home (not `~/.hermes`)
- the production gateway PID gate passes (read-only observation)

If any condition fails, the request is blocked with `blocked_provider_*`.

## 3. Backend Deliverables

| Module | Role |
|--------|------|
| `hermes_cli/dev_web_provider_schema.py` | Builds the provider tool schema purely from `STATIC_ALLOWLIST` (clarify + the five read-only tools). Validates the boundary; redacts for audit. |
| `hermes_cli/dev_web_provider_request.py` | Builds the controlled provider request envelope; enforces disabled/fake/real gating; redacts for audit. |
| `hermes_cli/dev_web_provider_adapter.py` | `FakeProviderAdapter` (deterministic, offline) + `RealProviderAdapter` (blocked framework) + `get_provider_adapter`. |
| `hermes_cli/dev_web_provider_roundtrip.py` | Orchestrates schema → request → adapter → validated tool calls → existing controlled chain → finalize. |
| `hermes_cli/dev_web_provider_audit.py` | Dev-only JSONL audit writer for the full provider round-trip lifecycle. |

### Provider Schema

Generated only from `STATIC_ALLOWLIST`:

```
clarify, tool_policy_read, route_governance_read,
audit_events_read, dev_environment_read, release_status_read
```

Each tool entry carries `readOnly=true`, `providerRequired=false`,
`writeRequired=false`, `externalSideEffects=false`, `safetyTier=read_only_safe`.
No write tool, no provider-recursive tool, no secret, no callable/function
repr, and no filesystem path / shell command / database mutation parameter
ever appears.

### Provider Round-trip Flow

```
build schema (allowlist projection)
  → build request (mode gating)
  → audit schema + request
  → if request blocked (e.g. real mode) → return blocked
  → invoke adapter (fake by default)
  → audit response
  → parse + validate every tool call against the allowlist
       (unknown / write-like / provider-recursive / malformed → blocked)
  → for each valid call: run the EXISTING controlled execution chain
       (dry-run → digest → confirmation token → pre-audit → handler lookup
        → dispatch → handler call → post-audit)
  → audit each tool call + tool result
  → feed tool results to the fake provider for a final answer
  → audit the final response
  → return unified result envelope
```

Fake-provider round-trips use internal confirmation (read-only only); each
tool call's digest is still verified and the audit records
`internalConfirmation=true`. Real-provider round-trips would stop at
preview/confirmation — but real mode is blocked in Phase 2B regardless.

## 4. API Integration (no new route)

The round-trip reuses the existing `POST /api/dev/v1/tools/execute` path via
a `mode` field in the request body:

```json
{
  "mode": "provider_roundtrip",
  "providerMode": "fake",
  "message": "check route governance",
  "allowedToolIds": ["route_governance_read"]
}
```

Response data includes: `status`, `mode`, `providerMode`, `providerRequestId`,
`providerResponseId`, `providerSchemaSent`, `providerApiCalled`,
`externalNetworkCalled`, `readOnlyOnly`, `toolWriteDisabled`, `toolCalls`,
`toolResults`, `finalAnswer`, `providerAuditIds`, `blockedReason`,
`schemaSummary`.

**No new route is added.** Route governance remains 34/34/5/0/1/1.

## 5. Frontend Deliverables

| File | Role |
|------|------|
| `src/types/api/toolProvider.ts` | Typed response/request models. |
| `src/api/toolProvider.ts` | API client (reuses the execute route). |
| `src/stores/toolProvider.ts` | Pinia store (mode, message, selection, result). |
| `src/components/workspace/ProviderRoundtripPanel.vue` | Provider panel. |
| `src/components/layout/WorkspacePanel.vue` | Adds the `provider` workspace tab. |
| `src/stores/ui.ts` | Adds `provider` to the `WorkspaceTab` union. |

The panel offers: mode selector (disabled/fake/real), user message input,
allowed-tools selector, schema preview, run-fake-round-trip button, tool
calls panel, tool results panel, final answer panel, provider audit IDs, and
safety badges. **The UI never accepts an API key.** Real mode surfaces a
blocked message.

## 6. What Phase 2B does NOT do

- No Tool write route (Tool write = 0).
- No write tools executed.
- No real Provider API call without explicit enablement.
- No API key exposure (never printed, logged, audited, or accepted by the UI).
- No production rollout, no `~/.hermes` access, no production `state.db` access.
- No Phase 2C (tool write controlled execution).

## 7. Tests

Backend (1798 pass across the related regression; 74 new Phase 2B tests):
- `test_dev_web_phase_2b_provider_schema.py`
- `test_dev_web_phase_2b_provider_request.py`
- `test_dev_web_phase_2b_fake_provider_adapter.py`
- `test_dev_web_phase_2b_provider_roundtrip.py`
- `test_dev_web_phase_2b_provider_audit.py`
- `test_dev_web_phase_2b_provider_security.py`

Frontend (708 pass; new: `tool-provider-store.spec.ts`, `tool-provider-panel.spec.ts`).

Smoke/E2E: `phase2b_provider_fake_roundtrip` profile (6/6 pass) covering API
round-trip, tool-write-disabled invariant, real-mode blocked, audit query,
and the UI panel.

## 8. Next

- Phase 2B-H1: deterministic hardening audit of the provider round-trip
  (recommended before Phase 2C).
- Phase 2C: Tool Write Controlled Execution (deferred).
