# Phase 3B Provider Audit (Implementation)

| Field | Value |
|-------|-------|
| Phase | 3B |
| Status | Implemented |
| Module | `hermes_cli/dev_web_provider_real_audit.py` |

Emits the `provider_real_*` audit events. The writer, sanitizer, containment
rules, and Phase 2D durable-store dual-write are **reused unchanged** from
Phase 2B (`write_provider_audit_event`), so the events flow into the same
dev-only JSONL (`provider-roundtrip-audit.jsonl`) and the durable store
(`auditKind=provider`).

## Events (frozen)

`provider_real_request_previewed`, `provider_real_request_blocked`,
`provider_real_request_started`, `provider_real_request_completed`,
`provider_real_request_failed`, `provider_real_response_redacted`,
`provider_real_tool_call_requested`, `provider_real_tool_call_blocked`,
`provider_real_tool_call_completed`, `provider_real_budget_blocked`,
`provider_real_rate_limit_blocked`.

Every event is written with `phase="3B"`, `redactionApplied=true`, and a
bounded payload, and is defensively re-redacted before serialization.

## Common envelope

`eventId`, `eventType`, `phase`, `schemaVersion`, `timestamp`, `providerName`,
`providerMode`, `requestId`, `responseId`, `workflowId`, `toolCallId`,
`toolId`, `status`, `blockedReason`, `redactionApplied`,
`externalNetworkCalled`, `usageSummary`, `costEstimate`, `safeMetadata`,
`payload`.

## `safeMetadata` (the only place provider context appears)

`apiKeySource: "env"`, `apiKeyPresent: bool`, `apiKeySourceDetail:
"env_present" | "env_missing"`, `allowlistedBaseUrl` (host only), `modelName`,
`adapterName`. **Never** the key value, the env value, an Authorization
header, a raw token, a full tokenHash, or a callable repr.

## Containment (reused)

The audit path resolver rejects a missing `HERMES_HOME`, `~/.hermes`
(production), any path outside the dev `HERMES_HOME`, and any path ending in
`state.db`. Write failure never enables execution and never leaks.
