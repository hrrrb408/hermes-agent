# Phase 3A Execution Brief — Dev-only Agent Workflow MVP

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3A |
| Title | Dev-only Agent Workflow MVP (Execution Brief) |
| Status | Brief prepared — Phase 3A not started |
| Date | 2026-06-15 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3-PLANNING-001` |
| Brief ID | `PHASE-3A-EXECUTION-BRIEF-001` |

> This brief is the one-page contract for a future, separately-authorized
> Phase 3A. **Phase 3A is not started by this planning phase.** The full
> copy-paste prompt is [phase-3a-prompt.md](phase-3a-prompt.md).

---

## 1. Name

Dev-only Agent Workflow MVP.

## 2. Goal

Chain the Phase 2 capabilities (read-only tool, fake provider, sandbox write
preview, rollback reference, durable audit) into an operator-driven workflow
runner with a plan, manual step execution, and approval gates — fully dev-only,
no autonomous execution, no real provider.

## 3. Scope (allowed)

- Workflow definition schema.
- Workflow planner + dry-run preview.
- Step list + manual step execution.
- Approval gates between steps (reuse Phase 2C-H1 confirmation model).
- Step types: read-only tool (2A), fake provider (2B), sandbox write preview
  (2C), rollback reference (2C-H1).
- Audit linkage (reuse 2D durable store).
- Workflow timeline UI (additive console "Workflow" section).
- Workflow state under the dev `HERMES_HOME`.
- Tests + smoke.

## 4. Non-goals (forbidden)

Real provider call; provider auto-write; autonomous write; shell command;
database mutation; external service write; production rollout; `~/.hermes`
access; production `state.db` access; dynamic plugin loading; background
autonomous agent; schedule / cron; multi-user workflow; production workflow
store; new HTTP route (default), Tool write HTTP route, or Provider route.

## 5. Inputs

- Baseline: `bb373d61e98d57e9ea470fde7162f706bd32f23e` (Phase 2E-H1).
- HERMES_HOME: `/Users/huangruibang/Code/hermes-home-dev`.
- Reused capabilities: Phase 2A read-only tools, 2B fake provider, 2C sandbox
  write preview, 2C-H1 rollback, 2D durable audit store, 2E/2E-H1 console shell.

## 6. Outputs

- A dev-only workflow runner (backend) + a Workflow console section (frontend).
- Workflow state store under the dev `HERMES_HOME`.
- New tests + a new additive smoke profile.
- Phase 3A closeout docs (planner doc, scope doc, test report).

## 7. Architecture notes

- Workflow = an ordered list of typed steps, each step = (type, target tool /
  mode, inputs, approval-gate flag, audit-link placeholder).
- The runner advances one step at a time on operator action; it never advances
  automatically past an approval gate.
- Steps call the **existing** controlled-execution surface via `mode` branches
  on `POST /tools/dry-run` + `POST /tools/execute` — **no new route**.
- Workflow state is a small JSON document under the dev `HERMES_HOME`,
  validated on load, failing safe (read-only) on corruption.

## 8. State model

```
workflow:
  id, name, createdAt, status (draft|running|paused|completed|failed)
  steps: [{ id, type, mode, inputs, gateRequired, status, auditLinkIds[] }]
  cursor: <current step id>
```

State transitions: `draft → running ⇄ paused → completed | failed`. A gate
step requires explicit operator approval before its successor runs.

## 9. UI model

- Additive `/#/console` "Workflow" section: step timeline, current-step panel,
  "advance" / "approve gate" controls, audit cross-navigation chips.
- Inherits the Phase 2E-H1 accessibility + no-leak closure.
- `/#/` chat workbench unchanged.

## 10. Audit model

- Every executed step links to its dry-run / execute / provider / write /
  rollback audit event ids in the Phase 2D durable store.
- No new audit writer is required; if a workflow-specific breadcrumb event is
  needed it must be explicitly approved.

## 11. Risk gates

P0 stop conditions and P1 push-gates from
[phase-3-risk-register.md](phase-3-risk-register.md). In particular: no real
provider, no autonomous write, no shell / db / external write, no route drift,
no secret exposure, PID `28428` unchanged.

## 12. Test gates

- Backend unit / contract: schema, planner, dry-run preview, step execution,
  approval gates, audit linkage.
- Frontend unit: Workflow section timeline, step list, approval gate,
  cross-navigation, no-leak.
- Route-governance contract: no new route.
- Smoke: new additive profile + zero regression.

## 13. Commit message

```
docs(webui): plan phase 3 scope
```

(this planning phase). The future Phase 3A execution uses its own conventional
commit, e.g. `feat(webui): add dev workflow mvp`.

## 14. Final report format

A Phase 3A closeout report mirroring the Phase 2E-H1 structure: scope, what
changed, what did not change, route governance, production safety, gates,
residual risks (P2), conclusion.

---

## 15. Phase 3A Must Not Start Here

This brief is the contract for a future, separately-authorized phase. It does
not start Phase 3A. The copy-paste prompt lives at
[phase-3a-prompt.md](phase-3a-prompt.md).
