# Phase 3A-H1 — Workflow Audit Security

**ID:** `WORKFLOW-AUDIT-3A-H1-001`
**Lens:** 7 — Workflow Audit / Redaction Boundary

## Scope

The workflow audit bridge: every workflow event type is writable + queryable,
every written event is sanitized with `redactionApplied=true`, audit links and
workflow correlation ids are preserved, and the write is fail-safe.

## Evidence (code)

- `hermes_cli/dev_web_workflow_audit.py`
  - `write_workflow_audit_event` — reuses the Phase 2D durable store under
    `AUDIT_KIND_INTERNAL` with `eventType=workflow_*`. Unknown event types
    normalize to `workflow_timeline_updated` (always queryable).
  - `redact_workflow_audit_payload` — runs the unified sanitizer before append;
    builds `summary`/`safeMetadata` with only public correlation ids
    (`linkedAuditIds`, `workflowId`, `workflowStepId`, `stepType`,
    `workflowExecutionId`, `workflowApprovalId`).
  - The bridge always sets `redaction_applied=True`, `external_network_called=False`,
    `read_only=True`, `write_required=False`, and never raises (best-effort write).
- `hermes_cli/dev_web_workflow_schema.py` — `VALID_WORKFLOW_EVENT_TYPES` covers
  all twelve required event types.

## Commands

```bash
./scripts/run_tests.sh \
  tests/test_dev_web_phase_3a_h1_workflow_audit_security.py -- -q
```

## Findings

The audit boundary already holds. The hardening tests pin it:

- All twelve required event types (`workflow_plan_created` /
  `_blocked`, `workflow_execution_created`, `workflow_step_preview_created`,
  `workflow_step_approval_created` / `_used`, `workflow_step_started` /
  `_completed` / `_blocked` / `_failed`, `workflow_timeline_updated`,
  `workflow_execution_completed`) are writable AND queryable by `eventType`.
- An unknown event type normalizes to `workflow_timeline_updated` and is still
  queryable — a caller bug can never produce an un-queryable event.
- Secret material in `summary` is redacted to `[REDACTED]`; `rawArguments` /
  `apiKey` / `fullTokenHash` / `tokenSecret` / callable reprs / production
  paths / `state.db` never reach disk.
- The on-disk JSONL carries `"redactionApplied":true` and
  `"externalNetworkCalled":false`.
- Audit links are preserved as public correlation ids (`linkedAuditIds`);
  workflow correlation ids (`workflowId`, `workflowStepId`, `stepType`,
  `workflowExecutionId`, `workflowApprovalId`) are carried in summary/metadata.
- `audit_link_from_result` returns `None` on a failed write.
- The write is fail-safe: a hermes_home under a regular file (mkdir fails)
  returns `written=False` and never raises.

## Fixes

None required — no implementation defect found.

## Status

PASS.

## Residual risk

None (P0 = 0, P1 = 0). Audit durability + indexing are owned by the Phase 2D
store (covered by the Phase 2D / 2D-H1 preservation tests).
