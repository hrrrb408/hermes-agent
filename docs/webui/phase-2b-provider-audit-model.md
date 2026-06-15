# Phase 2B — Provider Audit Model

Status: **implemented**
Writer: `hermes_cli/dev_web_provider_audit.py`
Store: `$HERMES_HOME/gateway/dev/audit/provider-roundtrip-audit.jsonl` (dev only, never committed)

## 1. Event types

| Event type | When |
|------------|------|
| `provider_schema_built` | after the provider schema is projected from the allowlist |
| `provider_request_built` | after the controlled request envelope is built |
| `provider_response_received` | after the adapter returns a response |
| `provider_tool_call_parsed` | after a tool call parses as valid |
| `provider_tool_call_blocked` | after a tool call is rejected by validation |
| `provider_tool_call_executed` | after a tool call runs through the controlled chain |
| `provider_final_response_received` | after the fake provider emits the final answer |

## 2. Common envelope

Every event carries:

```
eventId, eventType, phase (2B), schemaVersion, timestamp,
providerMode, providerRequestId, providerResponseId,
toolCallId, toolId, status, blockedReason,
redactionApplied (always true), payload (boundary-relevant facts only)
```

## 3. Redaction guarantees

`build_provider_audit_event` defensively re-redacts the entire event via
`_sanitize` before serialization. The sanitizer:

- replaces secret-looking string values (`sk-…`, `Bearer …`, `Authorization: …`,
  `-----BEGIN … PRIVATE KEY-----`) with `[REDACTED]`;
- drops forbidden field-name stems (`token`, `secret`, `password`, `auth`,
  `api_key`, `authorization`, …) by replacing their values with `[REDACTED]`;
- renders any non-JSON-native value (callables, objects) as a fixed
  `<non_json_value>` placeholder — never the repr, never the type name;
- bounds nesting depth to 8.

Write failure never enables execution, never calls a provider, and never
leaks secrets. Oversized events are replaced with a truncated marker (the
event is never silently dropped).

## 4. Containment

`_resolve_audit_path` rejects:
- a missing `HERMES_HOME`;
- `HERMES_HOME` equal to `/Users/huangruibang/.hermes` (production);
- any path that does not resolve under the dev `HERMES_HOME`;
- any path ending in `state.db`.

File rotation caps the file at 5 MiB with 3 retained copies (current + 2
rotated), mirroring the dry-run audit writer.

## 5. What is NEVER stored

- API keys (any provider key env value).
- Raw tokens, full tokenHash, raw arguments.
- Callable / function / bound-method reprs.
- Full provider request bodies that may contain secrets.
- Anything outside the dev `HERMES_HOME`.

## 6. Audit Viewer

The provider round-trip also writes a dry-run audit event and a
post-execution audit event per executed tool (via the existing controlled
chain). Those events are surfaced by the existing read-only audit-events
route (`GET /tools/audit-events`) by `canonicalName`. The provider-specific
`provider-roundtrip-audit.jsonl` is read by the security-boundary tests and
the smoke profile.

## Phase 2D update — durable store dual-write

Provider audit events now also dual-write into the Phase 2D durable audit
store (`auditKind=provider`, with `providerMode`, `providerSchemaSent`,
`providerApiCalled`, `externalNetworkCalled`). They are queryable in store mode
by `providerMode` / `eventType` filters and cursor pagination. Legacy JSONL
remains. See [phase-2d-audit-query-and-indexing](phase-2d-audit-query-and-indexing.md).
