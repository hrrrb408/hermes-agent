# Phase 3B-Live-Enablement — Audit Policy

| Field | Value |
|-------|-------|
| Phase | 3B-Live-Enablement (Planning) |
| Title | Strict Manual Real Provider Enablement — Audit Policy |
| Status | Frozen (docs-only planning; live enablement **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3B-LIVE-ENABLEMENT-PLANNING-001` |

## 1. Principle

Every live-enablement lifecycle event is audited, redacted, dual-written, and
fail-closed. An audit write failure on a live request blocks the request.

## 2. New audit event types (live layer)

```
provider_live_enablement_requested
provider_live_enablement_approved
provider_live_enablement_denied
provider_live_enablement_expired
provider_live_enablement_started
provider_live_enablement_completed
provider_live_enablement_failed
provider_live_enablement_kill_switch_triggered
provider_live_secret_state_checked
provider_live_network_request_started
provider_live_network_request_completed
provider_live_network_request_blocked
provider_live_budget_checked
provider_live_budget_blocked
provider_live_tool_call_requested
provider_live_tool_call_blocked
provider_live_tool_call_completed
provider_live_disable_completed
```

## 3. Safe fields

```
providerName
providerMode
approvalId
requestId
responseId
workflowId
model
baseUrlHost
toolId
toolCallId
status
blockedReason
redactionApplied
budgetCap
requestCap
tokenCap
usageSummary
costEstimate
safeMetadata
```

## 4. Forbidden fields

```
API key
Authorization header
Bearer token
raw provider prompt containing secrets
raw provider response containing secrets
raw tool args containing secrets
full tokenHash
file content
callable repr
production path
```

## 5. Hard requirements

- `redactionApplied = true` on every live event.
- Defensive re-redaction before write (the same payload is passed through the
  Phase 2B-H1 / Phase 3B sanitizer a second time before persistence).
- Audit write failure on a live request → **fail closed**: the live request is
  aborted and `provider_live_enablement_failed` (best-effort) is emitted.

## 6. Dual-write target

Live events are dual-written into:

- the Phase 2B provider JSONL (`provider_real_*` namespace), and
- the Phase 2D durable audit store (`auditKind=provider`).

No new audit kind is assumed. `phase=3B-Live-Enablement` (or the agreed phase
tag) distinguishes live events without changing the store schema.

## 7. Counter / no-leak cross-check

Before any live event is persisted:

1. The payload is checked for secret patterns (key prefix, bearer token, raw
   args).
2. Any hit fires `blocked_provider_secret_detected` + the kill switch.
3. Token counts are preserved; token values are redacted.

## 8. Cross-references

- [Phase 3B audit](phase-3b-provider-audit.md)
- [Phase 3B provider audit model](phase-3b-provider-audit-model.md)
- [Phase 3B-H1 audit security](phase-3b-h1-provider-audit-security.md)
- [Phase 3B-Live-Enablement kill switch](phase-3b-live-enablement-kill-switch-and-rollback.md)
