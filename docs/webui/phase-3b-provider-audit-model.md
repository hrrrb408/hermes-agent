# Phase 3B Provider Audit Model

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3B Planning |
| Title | Real Provider Audit Event Model (Frozen) |
| Status | Frozen |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3B-PLANNING-001` |
| Audit ID | `PHASE-3B-PROVIDER-AUDIT-001` |

> Companion to [phase-3b-planning.md](phase-3b-planning.md). This document freezes
> the `provider_real_*` audit events a future Phase 3B implementation must emit.
> It extends — and does **not** replace — the Phase 2B provider audit model. No
> audit file is written in this planning phase.

---

## 1. Relationship to Phase 2B Audit

Phase 2B already audits the fake round-trip lifecycle (`provider_schema_built`,
`provider_request_built`, `provider_response_received`,
`provider_tool_call_parsed`, `provider_tool_call_blocked`,
`provider_tool_call_executed`, `provider_final_response_received`) into a dev-only
JSONL and the Phase 2D durable store (`auditKind=provider`).

Phase 3B adds a **distinct, prefixed** set of `provider_real_*` events for the
real path, so a real round-trip is always distinguishable from a fake one in the
audit store. The writer, sanitizer, containment rules, and durable-store
dual-write are **reused unchanged** from Phase 2B / 2D.

---

## 2. Audit Events (frozen)

| Event type | When |
|------------|------|
| `provider_real_request_previewed` | after the operator previews the redacted request before the call |
| `provider_real_request_blocked` | after a request is blocked before any network call |
| `provider_real_request_started` | after the single HTTPS call begins |
| `provider_real_request_completed` | after the adapter returns a normalized, redacted response |
| `provider_real_request_failed` | after the call fails (timeout / oversize / unavailable / malformed) |
| `provider_real_response_redacted` | after the response is run through the sanitizer |
| `provider_real_tool_call_requested` | after a provider tool call parses as valid |
| `provider_real_tool_call_blocked` | after a provider tool call is rejected by validation |
| `provider_real_tool_call_completed` | after a tool call runs through the controlled chain |
| `provider_real_budget_blocked` | after the daily-budget / token cap blocks the request |
| `provider_real_rate_limit_blocked` | after the per-minute / daily request cap blocks the request |

Every event is written with `redactionApplied=true` and a bounded payload. Write
failure never enables execution, never leaks a secret, and never silently drops
the event (an oversized event is replaced with a truncated marker).

---

## 3. Common Envelope (frozen)

Every `provider_real_*` event carries:

```
eventId, eventType, phase (3B), schemaVersion, timestamp,
providerName, providerMode, requestId, responseId,
workflowId, toolCallId, toolId, status, blockedReason,
redactionApplied (always true), externalNetworkCalled,
usageSummary, costEstimate, safeMetadata, payload (boundary-relevant facts only)
```

### `safeMetadata` (the only place provider context may appear)

```
apiKeySource: env
apiKeyPresent: true | false
apiKeySourceDetail: env_present | env_missing
allowlistedBaseUrl: <host only, no secret-bearing query>
modelName: <safe string>
adapterName: openai_compatible | anthropic_compatible | zai_compatible | openrouter_compatible
```

### What `safeMetadata` never carries

The API-key value, the env-var value, the Authorization / API-key header, a raw
token, a full tokenHash, the full secret-bearing URL, or a callable repr.

---

## 4. What Is NEVER Stored (frozen)

- API keys (any provider key env value).
- The Authorization / API-key header value.
- Raw tokens, full tokenHash, raw tool arguments.
- Callable / function / bound-method reprs.
- A raw provider request body that may contain secrets.
- A raw provider response body (only a bounded `contentSummary`).
- The full secret-bearing URL (only the allowlisted host).
- Anything outside the dev `HERMES_HOME`.

---

## 5. Containment (reused from Phase 2B)

The audit path resolver rejects:

- a missing `HERMES_HOME`;
- `HERMES_HOME` equal to `/Users/huangruibang/.hermes` (production);
- any path that does not resolve under the dev `HERMES_HOME`;
- any path ending in `state.db`.

File rotation caps the dev-only JSONL at 5 MiB with 3 retained copies (mirrors
the Phase 2B writer). Durable-store dual-write goes to the Phase 2D store with
`auditKind=provider` and is queryable by `providerMode` / `eventType` with cursor
pagination.

---

## 6. Redaction (reused from Phase 2B-H1)

`build_provider_audit_event` defensively re-redacts the entire event via
`_sanitize` before serialization:

- replaces secret-looking string values (`sk-…`, `Bearer …`, `Authorization: …`,
  `-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----`) with `[REDACTED]`;
- drops forbidden field-name stems (`token`, `secret`, `password`, `auth`,
  `api_key`, `authorization`, `apikey`, `privatekey`, `credential`) by replacing
  their values with `[REDACTED]`;
- renders any non-JSON-native value (callables, objects) as a fixed
  `<non_json_value>` placeholder — never the repr, never the type name;
- bounds nesting depth to 8.

---

## 7. Audit Coverage Invariants (for a future Phase 3B implementation)

1. Every real round-trip emits at least one terminal event (`…completed`,
   `…blocked`, or `…failed`).
2. A blocked request emits `provider_real_request_blocked` (or a specific
   `…_blocked` variant) with `externalNetworkCalled=false`.
3. A completed round-trip emits `…started` → `…response_redacted` →
   `…completed` (plus per-tool-call events).
4. A failed round-trip emits `…started` → `…failed` with the failure classified
   by `blockedReason` / status.
5. Budget / rate-limit blocks emit `…budget_blocked` / `…rate_limit_blocked`.
6. No terminal event carries a secret (verified by the no-leak test).

---

## 8. Audit Viewer

The `provider_real_*` events are surfaced by the existing read-only audit-events
route (`GET /tools/audit-events`) by `canonicalName` / `eventType` (read-only).
The durable-store query path (`store` mode) supports `providerMode` /
`eventType` filters. The provider-specific dev-only JSONL is read by the
security-boundary tests and the smoke profile.

---

## 9. Cross-References

- [Phase 3B planning](phase-3b-planning.md)
- [Phase 3B scope freeze](phase-3b-provider-readonly-scope-freeze.md)
- [Phase 3B request / response schema](phase-3b-provider-request-response-schema.md)
- [Phase 3B failure / timeout / retry policy](phase-3b-failure-timeout-retry-policy.md)
- [Phase 3B cost / rate-limit policy](phase-3b-cost-and-rate-limit-policy.md)
- [Phase 3B redaction & no-leak policy](phase-3b-provider-redaction-and-no-leak-policy.md)
- [Phase 2B provider audit model](phase-2b-provider-audit-model.md)
- [Phase 2B-H1 provider round-trip hardening](phase-2b-h1-provider-roundtrip-hardening.md)
- [Phase 2D-H1 audit storage hardening](phase-2d-h1-audit-storage-hardening.md)
