# Phase 2D — Audit Schema v2

## Schema version

Every durable audit event carries `schemaVersion = "audit_schema_v2"`.

## Canonical event fields

Required (every event):

| Field | Type | Notes |
|-------|------|-------|
| `eventId` | string | unique; reused from legacy id where one exists |
| `sequence` | int | monotonic, non-negative, gap-free; assigned by the store writer |
| `createdAt` | string | ISO-8601 with timezone offset |
| `eventType` | string | e.g. `clarify_execution_completed` |
| `auditKind` | string | one of the valid kinds below |
| `schemaVersion` | string | `audit_schema_v2` |

Optional classification + flags:

`source`, `phase`, `toolId`, `toolCategory`, `mode`, `status`,
`blockedReason`, `readOnly`, `writeRequired`, `providerMode`,
`providerSchemaSent`, `providerApiCalled`, `externalNetworkCalled`,
`localSideEffects`, `externalSideEffects`, `redactionApplied`.

Optional correlation ids:

`executionId`, `dryRunId`, `dispatchId`, `handlerCallId`,
`preExecutionAuditId`, `postExecutionAuditId`, `providerRequestId`,
`providerResponseId`, `writePlanId`, `writePreviewId`, `rollbackId`,
`confirmationTokenId`.

Safe payload:

`summary` (object), `safeMetadata` (object) — both sanitized recursively.

## Valid audit kinds

`dry_run`, `pre_execution`, `post_execution`, `write`, `provider`,
`rollback`, `confirmation`, `internal`.

`internal` covers system / fallback events (e.g. sanitization fallbacks).

## Valid enumerations

- **status**: `ok`, `blocked`, `error`, `preview`, `completed`
- **source**: `dry_run_api`, `execute_api`, `provider_api`, `write_api`,
  `rollback_api`, `confirmation`, `internal`
- **providerMode**: `disabled`, `fake`, `real`
- **mode**: `read_only`, `write_preview`

## JSON-native guarantee

Every persisted value is JSON-native (`None` / `bool` / `int` / `float` /
`str` / sanitized `dict` / sanitized `list`). Non-JSON-native values (callables,
functions, arbitrary objects, bytes, exceptions) never reach the store — the
unified sanitizer collapses them before validation.

## Field principles (never persisted)

- raw arguments
- plain token / tokenSecret
- full tokenHash
- API key / secret / credential
- file content
- callable / function / object repr
- production path (`~/.hermes`, `state.db`)
