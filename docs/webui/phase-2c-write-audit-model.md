# Phase 2C — Write Audit Model

## Storage

Write audit events are appended to a dev-only JSONL file under the dev
`HERMES_HOME`:

```
$HERMES_HOME/gateway/dev/audit/tool-write-audit.jsonl
```

The writer mirrors the Phase 2B provider-audit writer: stdlib only, rotation at
5 MiB (3 retained files), 32 KiB per-event cap with a truncated marker, and
defensive full re-redaction before serialization. Write failures never enable
execution.

## Event types

| Event type | When emitted |
|------------|--------------|
| `write_plan_built` | a dry-run plan is built |
| `write_preview_generated` | the preview envelope is returned |
| `write_confirmation_required` | confirmation is required before execute |
| `write_execution_blocked` | any gate fails (enablement / allowlist / digest / confirmation / path / handler) |
| `write_pre_execution_audit` | pre-execution audit written |
| `write_handler_called` | the write handler was invoked |
| `write_post_execution_audit` | post-execution audit written |
| `write_rollback_manifest_built` | the rollback manifest was built |
| `provider_write_preview_generated` | provider write preview generated |
| `provider_write_auto_execute_blocked` | provider write auto-execute denied |

## Record shape (safe)

Every event carries: `eventId`, `eventType`, `phase=2C`, `timestamp`,
`toolId`, `writePlanId`, `writePreviewId`, `rollbackId`, `operation`,
`targetRelativePath`, `status`, `blockedReason`, the write side-effect flags
(`readOnly=false`, `writeRequired=true`, `localSideEffects=true`,
`externalSideEffects=false`), `requiresConfirmation=true`,
`requiresWriteEnablement=true`, `redactionApplied=true`, and a redacted payload.

## Read surface

The existing read-only `GET /api/dev/v1/tools/audit-events` route gained a
fourth kind: `auditKind=write` (mapped to `tool-write-audit.jsonl`). This adds
no new route — route governance stays 34/34/5/0/1/1. The write normalizer
surfaces only safe fields (ids, operation, hashes, status, flags); it never
echoes raw arguments, full content, secrets, or callable reprs.

## Redaction

Every value is re-redacted via the audit `_sanitize`: secret value patterns
(`sk-…`, `Bearer …`, `Authorization: …`, PEM private keys) become
`[REDACTED]`; forbidden field stems (`token`, `secret`, `password`, `apikey`,
…) become `[REDACTED]`; non-JSON values become `<non_json_value>` (never a
callable/function repr). The raw file content body is never stored verbatim —
only a content digest and bounded lengths.
