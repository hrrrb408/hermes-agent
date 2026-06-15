# Phase 3A — Workflow Approval Gates

## Model

Every workflow step carries an explicit, single-use human-approval gate. The
gate **reuses the Phase 2C-H1 file-backed confirmation store** under a dedicated
scope:

```
SCOPE_WORKFLOW_STEP_APPROVAL = "workflow_step_approval"
DEFAULT_TTL_WORKFLOW_APPROVAL_SECONDS = 5 * 60   # 5 minutes
```

A workflow approval token can NEVER authorize a write or a rollback — those keep
their own scopes (`write_execute`, `rollback_execute`), so a workflow approval
cannot be replayed against them.

## Issuance (preview = approve)

The `workflow_step_preview` mode issues the approval token bound to the step.
The act of previewing is the operator review; issuing the step-bound token IS
the "approve step" gate. The response returns the opaque single-use token, the
approval id, and the expiry.

## Binding

An approval is bound to one step by a SHA-256 digest covering the execution id,
step id, step type, and the sanitized step input:

```
compute_step_digest(execution_id, step_id, step_type, step_input)
```

Verification recomputes the digest from the step's stored input, so an approval
issued for one step/input cannot satisfy a different step or a step whose input
changed after approval.

## Single-use

`consume_step_approval` verifies AND marks the underlying token used. A replay
is blocked with `blocked_workflow_approval_already_used` (the `usedAt` flag
persists across process restarts).

## Blocked reasons

| Reason | Meaning |
|--------|---------|
| `blocked_workflow_approval_required` | No approval token supplied |
| `blocked_workflow_approval_expired` | Token TTL elapsed |
| `blocked_workflow_approval_scope_mismatch` | Token scope is not `workflow_step_approval` |
| `blocked_workflow_approval_step_mismatch` | Token bound to a different step/execution |
| `blocked_workflow_approval_digest_mismatch` | Step input changed after approval |
| `blocked_workflow_approval_already_used` | Token already consumed (single-use) |

## What the approval does NOT authorize

- Write execution (use the write confirmation flow).
- Rollback execution (use the rollback confirmation flow).
- Real provider, shell, database, external service, production operations.
