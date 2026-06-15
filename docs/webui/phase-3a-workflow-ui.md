# Phase 3A — Workflow UI

## Section

An additive **Workflow** section in the unified developer console (`/#/console`),
mirroring the Phase 2E additive pattern. It is registered in the nav rail after
**Safety Boundary** and before **Diagnostics**.

## Components

```
src/components/devconsole/
  WorkflowSection.vue         composes the section
  WorkflowPlanForm.vue        create-plan form (title / goal / draft steps)
  WorkflowPlanPreview.vue     plan preview (ids, planned steps, blocked steps)
  WorkflowStepList.vue        ordered step list with status + cursor
  WorkflowStepDetail.vue      selected step: preview / approve / execute controls
  WorkflowTimeline.vue        append-only timeline + audit links
  WorkflowApprovalGate.vue    approval gate state (required / ready / none)
  WorkflowSafetyBoundary.vue  frozen capability table
```

## Lib + store + API

```
src/lib/workflowTypes.ts            TypeScript mirror of workflow_schema_v1
src/lib/workflowBlockedReasons.ts   workflow blocked-reason index
src/lib/workflowFormatters.ts       step type / status / boundary formatters
src/types/api/workflow.ts           request/response types
src/api/workflow.ts                 4 API fns (plan/step/state via existing routes)
src/stores/toolWorkflow.ts          Pinia store (form, plan, execution, tokens)
```

## UX state machine

```
Build Plan  →  Review safety boundary  →  (execution materialized)
Preview step  →  Approve step (token issued)  →  Execute step manually
Review result  →  Next step  →  Workflow completed / blocked
```

Button rules: Build Plan enabled when the request is valid; Preview enabled
when prior steps are valid; Execute disabled until an approval token exists;
Execute disabled for forbidden step types; write/rollback steps render a
"preview / reference only" notice (no write/rollback execute affordance).

## Safety affordances

The section clearly states: **No real provider, no autonomous write, no shell /
database / external service write, no production rollout; sandbox write preview
only; rollback reference only; manual approval required.** The safety boundary
panel lists every capability as Allowed / Blocked / Required / Enabled.

## No-leak

The section inherits the Phase 2E-H1 no-leak closure: no API key, raw token,
full token hash, raw arguments, callable repr, or production path is ever
rendered. Covered by `phase3a-workflow-no-leak.spec.ts` + the smoke no-leak UI
leg.

## Themes

All components use semantic CSS variables only (no hardcoded colors), so the
five frozen themes render the Workflow section correctly.
