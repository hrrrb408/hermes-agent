# Phase 3A — Workflow Audit Model

## Store

Workflow breadcrumb events are written into the **existing Phase 2D durable
audit store** via `append_audit_event`. No new audit kind is introduced —
workflow events reuse `AUDIT_KIND_INTERNAL` with `eventType=workflow_*`, so they
are discoverable by the existing audit viewer / query engine (filter by
`auditKind=internal` or `eventType=workflow_*`) without any new audit-writer
surface.

## Event types

```
workflow_plan_created
workflow_plan_blocked
workflow_execution_created
workflow_step_preview_created
workflow_step_approval_created
workflow_step_approval_used
workflow_step_started
workflow_step_completed
workflow_step_blocked
workflow_step_failed
workflow_timeline_updated
workflow_execution_completed
```

## Per-event fields

Every event carries the workflow correlation ids (`workflowId`,
`workflowPlanId`, `workflowExecutionId`, `workflowStepId`, `stepType`,
`stepStatus`, `approvalId`, `toolId`, `providerMode`, `writePreviewId`,
`rollbackId`), the linked audit ids, `redactionApplied=true`, and a safe
summary / safe metadata.

## Sanitization

`redact_workflow_audit_payload` runs every summary/metadata value through
`sanitize_workflow_value` before the event is built. The store's own sanitizer
runs again on append. No raw arguments, secrets, full token hashes, callable
reprs, file content, or production paths ever reach the store.

## Linkage

Each executed step links to its audit event ids:

- `audit_link_from_result` builds a `WorkflowAuditLink` from the store write
  result.
- Fake-provider steps additionally link the provider audit ids returned by
  `run_provider_tool_roundtrip`.
- The Workflow console surfaces these as cross-navigation chips to the Audit
  Viewer.

## Best-effort

Audit writes are best-effort: a store failure is reported in the result and
never raises. A missing audit id means "no link", never "abort the workflow".
