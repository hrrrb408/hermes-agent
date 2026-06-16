# Phase 3A-H1 — Workflow UI Security

**ID:** `WORKFLOW-UI-3A-H1-001`
**Lens:** 8 — Workflow UI / Timeline / Cross-link Boundary

## Scope

The Workflow console surface (section, plan form/preview, step list/detail,
timeline, approval gate, safety boundary) and the `toolWorkflow` store: the
surface is stable, approval-gated, and leaks no secret / raw token / full
hash / raw argument / callable repr / production path.

## Evidence (code)

- `apps/hermes-dev-webui/src/components/devconsole/Workflow*.vue` — the seven
  workflow components render only safe summaries and public correlation ids.
- `apps/hermes-dev-webui/src/stores/toolWorkflow.ts` — owns the plan/execution
  state, the transient per-step approval token (issued by preview, consumed +
  dropped by execute), and the loading/error/phase flags.
- `apps/hermes-dev-webui/src/api/workflow.ts` — reuses ONLY
  `POST /tools/dry-run` and `POST /tools/execute` (no `/workflows` path).
- `apps/hermes-dev-webui/src/lib/workflowBlockedReasons.ts` — the 21-entry
  `blocked_workflow_*` catalogue + safe lookup/fallback.

## Commands

```bash
cd apps/hermes-dev-webui
pnpm test -- --run phase3a-h1-workflow-routing phase3a-h1-workflow-ui-state \
  phase3a-h1-workflow-approval phase3a-h1-workflow-no-leak \
  phase3a-h1-workflow-safety-boundary
```

## Findings

The UI boundary already holds. The hardening tests pin it:

- The Workflow section is registered exactly once in the console nav, labelled
  "Workflow"; an invented section id is rejected.
- The workflow API client targets ONLY `/tools/dry-run` and `/tools/execute`
  (static source scan); it never constructs a `/workflows` or `/provider/` path.
- The store enforces the approval gate (no execute without a preview-issued
  token), drops the single-use token after consumption, transitions
  `idle → loading → ready/blocked/error`, surfaces errors safely, and `reset()`
  clears the plan, execution, and all approval tokens.
- The approval gate renders required / ready / none; Execute is disabled until
  a token exists (and while loading); write-execute and rollback-execute
  affordances are NEVER offered (the blocked badge is shown instead).
- The approval gate renders the public approval id (`cft_…`) but NEVER the raw
  token (`cft_x.secret`), a full hash, or secret material.
- A deep no-leak scan across every workflow component — including blocked-reason
  panels — surfaces no API key, raw token, full hash, raw argument, callable
  repr, production path, or `state.db`.
- The safety boundary renders every high-risk capability as Blocked; the
  blocked-reason catalogue is `blocked_workflow_`-prefixed and complete (≥21).

## Fixes

None required — no implementation defect found.

## Status

PASS.

## Residual risk

None (P0 = 0, P1 = 0). The raw approval token lives only in the transient
`approvalTokens` map and is deleted on consume/reset; it is never rendered.
