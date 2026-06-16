# Phase 3A — Dev-only Agent Workflow MVP

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3A |
| Title | Dev-only Agent Workflow MVP |
| Status | Implemented |
| Date | 2026-06-16 |
| Branch | `dev-huangruibang` |
| Baseline | `418edfea3` (Phase 3 Planning) |
| Implementation ID | `PHASE-3A-WORKFLOW-MVP-001` |

## 1. Goal

Chain the Phase 2 capabilities (read-only tool, fake provider, sandbox write
preview, rollback reference, durable audit) into a **dev-only, manual,
approval-gated Agent Workflow MVP**. The workflow advances one step at a time on
operator action, reuses the existing controlled-execution surface, and never
auto-executes, never calls a real provider, and never performs a write or
rollback.

## 2. What was implemented

- **Workflow schema v1** (`dev_web_workflow_schema.py`) — the definition / plan
  / step / execution-state / timeline / approval-gate / audit-link / safety
  boundary data model, the six allowed step types, the forbidden step types +
  their blocked reasons, the step status lifecycle, and the input sanitizer.
- **Workflow state store** (`dev_web_workflow_store.py`) — a dev-only,
  file-backed, atomic, corruption-safe store under
  `$HERMES_HOME/gateway/dev/workflow-store` (definitions / executions /
  append-only timeline JSONL).
- **Workflow planner** (`dev_web_workflow_planner.py`) — turns an operator
  request into a sanitized plan, accepting only the six allowed step types and
  blocking every forbidden step type + unsafe input.
- **Workflow step preview** (`dev_web_workflow_step_preview.py`) — non-executing
  previews that reuse the existing dry-run / write-preview / rollback-preview /
  audit-query surfaces.
- **Workflow approval gates** (`dev_web_workflow_approval.py`) — single-use,
  step-bound, TTL-bounded approvals reusing the Phase 2C-H1 confirmation store
  under the dedicated `workflow_step_approval` scope.
- **Workflow step execution** (`dev_web_workflow_step_execute.py`) — manual,
  approval-gated, order-enforced execution; read-only + fake-provider steps
  execute, write/rollback steps are preview/reference-only.
- **Workflow audit bridge** (`dev_web_workflow_audit.py`) — writes
  `workflow_*` breadcrumb events into the Phase 2D durable store.
- **API integration** — four new `mode` branches on the EXISTING
  `/api/dev/v1/tools/dry-run` and `/api/dev/v1/tools/execute` routes. **No new
  HTTP route was added.**
- **Workflow console section** — an additive `Workflow` section in `/#/console`
  (plan form, plan preview, step list, step detail, approval gate, timeline,
  safety boundary, audit cross-navigation).
- **Tests + smoke** — 9 backend test files (104 tests), 7 frontend spec files,
  and a `phase3a_workflow_mvp` smoke profile wired into the `all` target.

## 3. Allowed step types

| Step type | Executes | Notes |
|-----------|----------|-------|
| `read_only_tool` | Yes (bounded read-only handler) | Reuses Phase 2A read-only dispatch |
| `fake_provider_roundtrip` | Yes (offline fake provider) | Reuses Phase 2B fake round-trip |
| `sandbox_write_preview` | Preview only | Reuses Phase 2C write preview; **never executes the write** |
| `rollback_reference` | Reference only | Reuses Phase 2C-H1 rollback preview; **never executes the rollback** |
| `manual_note` | Mark completed | Sanitized operator note |
| `audit_query` | Read-only | Reuses Phase 2D audit query |

## 4. Forbidden step types (blocked)

`real_provider_roundtrip`, `provider_write_execute`, `sandbox_write_execute`,
`rollback_execute`, `shell_command`, `database_query`, `database_mutation`,
`external_http_request`, `file_delete`, `file_rename`, `file_chmod`,
`plugin_dynamic_load`, `background_agent`, `scheduled_task`,
`production_operation`. Each maps to a precise `blocked_workflow_*` reason.

## 5. Hard boundaries (unchanged)

- No real provider vendor call; provider stays fake (offline).
- No provider auto-write; provider write is preview-only.
- No autonomous write; the workflow never executes a write.
- No rollback execution; the workflow only references/previews rollbacks.
- No shell, no database mutation, no external service write.
- No production rollout; no `~/.hermes` access; no production `state.db` access.
- No new HTTP route (OpenAPI 34 / runtime 34 / Tool GET 5 / write 0 / dry-run 1
  / execution 1).

## 6. Cross-references

- [Workflow schema](phase-3a-workflow-schema.md)
- [Workflow state model](phase-3a-workflow-state-model.md)
- [Workflow approval gates](phase-3a-workflow-approval-gates.md)
- [Workflow audit model](phase-3a-workflow-audit-model.md)
- [Workflow UI](phase-3a-workflow-ui.md)
- [Security boundary](phase-3a-security-boundary.md)
- [Test report](phase-3a-test-report.md)

## 7. Phase 3A-H1 hardening pass

Phase 3A was followed by **Phase 3A-H1 — Workflow Hardening**
(`HARDENING-3A-H1-001`), a deterministic verification pass (NOT Phase 3B). It
added adversarial backend tests (7 files / 300 tests), frontend hardening
specs (5 files / 33 tests), a `phase3a_h1_workflow_hardening` smoke profile,
and an 11-lens hardening audit script — without changing the implementation.
All 11 lenses PASS; no real provider, provider auto-write, autonomous write,
workflow write/rollback execution, shell, database, external-service write, or
production rollout was introduced; route governance is unchanged. See
[Phase 3A-H1 Workflow Hardening](phase-3a-h1-workflow-hardening.md).
