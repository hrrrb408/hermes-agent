# Phase 3B-Live-Enablement — Audit Implementation

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Implementation) |
| Module | `hermes_cli/dev_web_provider_live_audit.py` |
| Tests | `tests/test_dev_web_phase_3b_live_audit_policy.py` |
| Date | 2026-06-17 |

Implements the frozen [audit policy](phase-3b-live-enablement-audit-policy.md).

## 1. Event types (18)

```
provider_live_enablement_requested       provider_live_enablement_approved
provider_live_enablement_denied          provider_live_enablement_expired
provider_live_enablement_started         provider_live_enablement_completed
provider_live_enablement_failed          provider_live_enablement_kill_switch_triggered
provider_live_secret_state_checked       provider_live_network_request_started
provider_live_network_request_completed  provider_live_network_request_blocked
provider_live_budget_checked             provider_live_budget_blocked
provider_live_tool_call_requested        provider_live_tool_call_blocked
provider_live_tool_call_completed        provider_live_disable_completed
```

## 2. Safe fields (only these may appear)

```
providerName, providerMode, approvalId, requestId, responseId, workflowId,
model, baseUrlHost, toolId, toolCallId, status, blockedReason, redactionApplied,
budget, usageSummary, costEstimate, secretState, safeMetadata
```

## 3. Forbidden fields (never present)

API key, Authorization header, bearer token, raw prompt/response secret, raw
tool args, full tokenHash, file content, callable repr, production path.

## 4. Redaction + dual-write + fail-closed

Every event carries `redactionApplied = true` and is defensively re-redacted
via the Phase 2B-H1 / Phase 3B `redact_real_payload` sanitizer **before** the
writer sees it. Events are dual-written through the Phase 2B
`write_provider_audit_event` (containment guard under the dev `HERMES_HOME`,
rotation cap, Phase 2D durable-store dual-write with `auditKind=provider`),
distinguished by `phase = "3B-Live-Enablement"`. An audit write failure on a
live request fails closed (the orchestrator aborts).

## 5. Typed writers

One convenience writer per frozen event (e.g. `write_live_enablement_started`,
`write_live_kill_switch_triggered`, `write_live_secret_state_checked`,
`write_live_budget_blocked`). Each builds a value-free event and writes it
through the shared redacting path.

## 6. Cross-references

- [Live enablement implementation](phase-3b-live-enablement-implementation.md)
- [Phase 3B provider audit model](phase-3b-provider-audit-model.md)
