# Phase 3A — Workflow Schema (`workflow_schema_v1`)

## Schema version

`WORKFLOW_SCHEMA_VERSION = "workflow_schema_v1"`.

## ID prefixes

| Entity | Prefix |
|--------|--------|
| Workflow | `wf_` |
| Workflow plan | `wfp_` |
| Workflow step | `wfs_` |
| Workflow execution | `wfx_` |
| Workflow audit event | `wfa_` |

Approval ids reuse the underlying confirmation-token id (`cft_…`) under the
`workflow_step_approval` scope.

## Step types

- **Allowed:** `read_only_tool`, `fake_provider_roundtrip`,
  `sandbox_write_preview`, `rollback_reference`, `manual_note`, `audit_query`.
- **Forbidden:** `real_provider_roundtrip`, `provider_write_execute`,
  `sandbox_write_execute`, `rollback_execute`, `shell_command`,
  `database_query`, `database_mutation`, `external_http_request`,
  `file_delete`, `file_rename`, `file_chmod`, `plugin_dynamic_load`,
  `background_agent`, `scheduled_task`, `production_operation`.

## Step status lifecycle

`draft → planned → previewed → approval_required → approved → ready → running
→ completed`, with terminal `blocked`, `failed`, `skipped`.

Execution-level status: `draft | running | paused | completed | failed`.

## Core records

- `WorkflowDefinition` — `workflowId, schemaVersion, title, description,
  createdAt, updatedAt, createdBy, phase, mode, steps[], safetyBoundary,
  metadata`.
- `WorkflowStep` — `stepId, stepType, title, status, toolId, providerMode,
  requiresApproval, requiresDryRun, requiresConfirmation, writeRequired,
  readOnly, localSideEffects, externalSideEffects, input, safeInputSummary,
  preview, result, auditLinks[], blockedReason, approvalId, createdAt,
  updatedAt`.
- `WorkflowPlan` — planner output: `workflowId, workflowPlanId, steps[],
  safetyBoundary, blockedSteps[], requiredApprovals, auditPreview, summary`.
- `WorkflowExecutionState` — live state: `workflowExecutionId, workflowId,
  workflowPlanId, status, steps[], cursorStepId, timeline[],
  completedStepCount, totalStepCount`.
- `WorkflowTimelineEvent` — append-only event: `eventId, eventType, createdAt,
  stepId, stepType, stepStatus, approvalId, toolId, providerMode,
  writePreviewId, rollbackId, auditLinks[], message, blockedReason`.
- `WorkflowApprovalGate` — `approvalId, stepId, workflowExecutionId,
  stepDigest, issuedAt, expiresAt, usedAt`.
- `WorkflowAuditLink` — `auditId, auditKind, label`.
- `WorkflowSafetyBoundary` — the frozen Phase 3A capability table.

## Sanitizer

`sanitize_workflow_value` recursively redacts secret-looking strings, drops
forbidden input keys (`rawArguments`, `rawArgs`, `fullTokenHash`, `tokenSecret`,
`plainToken`, `apiKey`, `authorization`, callable/path carriers), bounds nesting
depth, and rejects any non-JSON-native type. `contains_secret_material` lets the
planner BLOCK (not silently redact) secret-like input.

## Blocked-reason catalogue

Every workflow blocked reason is a `blocked_workflow_*` code registered in the
shared frontend catalogue (`lib/blockedReasons.ts`, surface `workflow`) so the
unified `BlockedReasonPanel` renders a safe explanation + next action.
