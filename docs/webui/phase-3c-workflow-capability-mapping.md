# Phase 3C — Workflow Capability Mapping

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Workflow Capability Mapping (Phase 3A Steps → Capabilities) |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Mapping ID | `PHASE-3C-WORKFLOW-MAP-001` |

> This document maps the **existing** Phase 3A workflow step types to capability
> records. The registry describes these; it does **not** change any workflow
> approval gate. Workflow write / rollback execution still requires the existing
> per-step operator approval.

## 1. Phase 3A workflow step types

| Step type | capabilityId | permissionClass | trustLevel | status |
|-----------|--------------|-----------------|------------|--------|
| `read_only_tool` | `workflow.step.read_only_tool` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |
| `fake_provider_roundtrip` | `workflow.step.fake_provider_roundtrip` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |
| `sandbox_write_preview` | `workflow.step.sandbox_write_preview` | `WRITE_PREVIEW` | `BUILTIN_VERIFIED` | `enabled` |
| `rollback_reference` | `workflow.step.rollback_reference` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |
| `manual_note` | `workflow.step.manual_note` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |
| `audit_query` | `workflow.step.audit_query` | `READ_ONLY` | `BUILTIN_VERIFIED` | `enabled` |

## 2. Forbidden / deferred workflow capabilities

| Capability | capabilityId | permissionClass | trustLevel | status | blockedReason |
|------------|--------------|-----------------|------------|--------|---------------|
| Workflow write execute | `workflow.write.execute` | `WRITE_CONFIRM` / forbidden | `BUILTIN_VERIFIED` | `blocked` until separately authorized | `blocked_workflow_write_not_authorized` |
| Workflow rollback execute | `workflow.rollback.execute` | `ROLLBACK_CONFIRM` / forbidden | `BUILTIN_VERIFIED` | `blocked` until separately authorized | `blocked_workflow_rollback_not_authorized` |
| Workflow auto-advance | `workflow.auto.advance` | `ADMIN_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_workflow_auto_advance_forbidden` |
| Workflow autonomous write | `workflow.autonomous.write` | `ADMIN_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_workflow_autonomous_write_forbidden` |
| Workflow background schedule | `workflow.background.schedule` | `ADMIN_FORBIDDEN` | `EXTERNAL_FORBIDDEN` | `blocked` | `blocked_workflow_background_schedule_forbidden` |

`workflow.write.execute` and `workflow.rollback.execute` are deferred — they
reuse the existing per-step approval gate (the operator explicitly approves a
write / rollback step at its gate). They are declared as capabilities so the
registry makes the gating explicit and auditable, but they **must not** auto-
execute.

## 3. Invariants preserved

- No workflow step may execute a write without an explicit operator approval at
  that step. The registry does not change this.
- No workflow step may bypass an approval gate. The registry does not change
  this.
- No workflow may auto-advance, autonomously write, or run on a background
  schedule. Those are `blocked`.
- Workflow state stays in the dev `HERMES_HOME` only; no production workflow
  store.

## 4. Non-negotiable statement

The Capability Registry **does not allow** a workflow to auto-execute a write
or to bypass an approval gate. Registering a workflow capability describes it;
it does not authorize auto-execution.

## 5. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3A scope freeze](phase-3-scope-freeze.md)
- [Phase 3A workflow approval gates](phase-3a-workflow-approval-gates.md)
- [Phase 3A-H1 workflow hardening](phase-3a-h1-workflow-hardening.md)
