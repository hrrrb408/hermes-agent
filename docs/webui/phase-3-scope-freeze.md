# Phase 3A Scope Freeze

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3A Scope Freeze |
| Title | Phase 3A — Dev-only Agent Workflow MVP (Scope Freeze) |
| Status | Frozen — not started |
| Date | 2026-06-15 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3-PLANNING-001` |
| Scope-Freeze ID | `PHASE-3A-SCOPE-FREEZE-001` |
| Selected Phase 3A | Dev-only Agent Workflow MVP |

> This document freezes the Phase 3A scope. **Phase 3A must not start in this
> planning phase.** It may start only after the user explicitly asks for the
> Phase 3A execution prompt / implementation and separately authorizes it.

---

## 1. Selected Phase 3A

**Dev-only Agent Workflow MVP.**

A dev-only, operator-driven workflow runner that chains the Phase 2
capabilities (read-only tool, fake provider, sandbox write preview, rollback
reference, audit) into a structured plan with manual step execution and
approval gates. No autonomous execution; no real provider; no shell / db /
external write; no production rollout.

---

## 2. Allowed Changes

| Area | Allowed |
|------|---------|
| Workflow definition schema | New dev-only schema describing a plan + ordered steps + per-step type + approval gate |
| Workflow planner / dry-run preview | Render a plan and a preview without executing any write |
| Step list + timeline UI | New console "Workflow" section (additive, like Phase 2E) |
| Manual step execution | Operator advances one step at a time; each step reuses the existing controlled-execution chain |
| Approval gates | Confirmation required between steps; gates reuse the Phase 2 confirmation model |
| Step types | read-only tool step (2A), fake-provider step (2B), sandbox write **preview** step (2C), rollback reference step (2C-H1) |
| Audit linkage | Each step links to its dry-run / execute / provider / write / rollback audit event ids (2D store) |
| State storage | Workflow state stored under the **dev** `HERMES_HOME` only |
| Tests | Backend + frontend unit / contract tests |
| Smoke | New smoke profile + spec (additive) |

---

## 3. Forbidden Changes

| Area | Forbidden |
|------|-----------|
| Real provider | No real provider vendor call; provider stays disabled / fake |
| Provider write | No provider auto-write; provider write preview-only (existing 2B/2C behaviour) |
| Autonomous write | No step may execute a write without an explicit operator approval at that step |
| Shell / process | No shell command execution, no process spawn |
| Database | No database mutation (no new DB, no `state.db` write) |
| External service | No external service write (no network mutation outside the existing offline fake provider) |
| Production | No production rollout, no `~/.hermes` access, no production `state.db` access |
| Routes | No new HTTP route, no Tool write HTTP route, no Provider route — workflow reuses the existing `/tools/dry-run` + `/tools/execute` `mode` branches (the Phase 2 "no new route" discipline) |
| Dynamic loading | No dynamic plugin / code loading |
| Scheduling | No cron / scheduler / background autonomous agent |
| Multi-user | No multi-user workflow namespace |
| Production store | No production workflow store; the workflow store is dev-only |

---

## 4. APIs Allowed

- **Reuse only.** No new route. Workflow steps call the existing controlled-
  execution surface:
  - `POST /api/dev/v1/tools/dry-run` (read-only / provider / write_preview /
    rollback_preview modes — unchanged).
  - `POST /api/dev/v1/tools/execute` (read-only / provider / write / rollback
    modes — unchanged).
  - `GET /api/dev/v1/tools/policy`, `GET /api/dev/v1/tools/audit-events`
    (read-only — unchanged).
- Workflow **definition / state** lives in a dev-only store under the dev
  `HERMES_HOME`. If a new read endpoint for workflow state is needed, it must
  be **explicitly approved and separately authorized** before being added — it
  is not assumed by this freeze.

---

## 5. Routes Allowed

**None new.** Route governance must remain **OpenAPI 34 / runtime 34 / Tool
GET 5 / Tool write HTTP route 0 / dry-run 1 / execution 1** unless an
explicit, separately-authorized change is approved and recorded. The default
assumption is: workflow reuses the existing `mode`-branched routes.

---

## 6. Storage Allowed

| Store | Location | Notes |
|-------|----------|-------|
| Workflow state | dev `HERMES_HOME` only (e.g. `$HERMES_HOME/gateway/dev/workflows`) | Dev-only, gitignored, never committed |
| Audit events | existing Phase 2D durable store | Reused read-only / linked |
| Confirmation tokens | existing Phase 2C-H1 file-backed store | Reused |
| Rollback manifests | existing Phase 2C-H1 store | Reused |

No workflow state, audit store, token store, rollback manifest, or runtime
audit JSONL may be committed. No `.claude/` may be committed.

---

## 7. UI Allowed

- A new additive "Workflow" section in the unified developer console
  (`/#/console`), mirroring the Phase 2E additive pattern.
- A workflow timeline / step-list view, manual "advance step" + "approve gate"
  controls, and audit cross-navigation (reuse `AuditIdLink` /
  `devConsoleNav.prefillAuditSearch`).
- The section inherits the Phase 2E-H1 accessibility baseline (vertical
  tablist / roving tabindex / non-color badges / focus-visible) and the
  no-leak closure (no API key / raw token / full hash / raw args / callable
  repr / production path).
- `/#/` (the 3-column chat workbench) stays unchanged.

---

## 8. Tests Required

- Backend unit / contract tests for the workflow schema, planner, dry-run
  preview, step execution, approval gates, and audit linkage.
- Frontend unit tests for the Workflow section (timeline, step list, approval
  gate, cross-navigation) under the Phase 2E-H1 hardening lens style.
- A no-leak test asserting the Workflow section surfaces no secret / token /
  hash / raw arg / callable repr / production path.
- A route-governance contract test asserting no new route was added.

---

## 9. Smoke Required

- A new additive smoke profile + spec (e.g. `phase3a_workflow_mvp`) wired into
  the `all` smoke target, mirroring the Phase 2E-H1 profile addition.
- Existing smoke profiles must keep passing (zero regression).

---

## 10. Production Boundary

- No production rollout.
- No `~/.hermes` access.
- No production `state.db` access.
- Production Gateway PID `28428` never stopped / restarted / replaced /
  signaled / reconfigured.
- WebUI binds to `127.0.0.1` only.

---

## 11. Provider Boundary

- Provider stays **disabled** (default) or **fake** (offline). Real provider
  remains blocked.
- Provider write stays **preview-only**; no auto-write; no auto-rollback.

---

## 12. Write Boundary

- Write is **preview-only** inside the workflow unless the operator explicitly
  approves the write step at its gate.
- Writes operate only inside the dev sandbox and require the existing
  `HERMES_TOOL_WRITE_EXECUTION_ENABLED` gate.
- No autonomous write. No shell / db / external write.

---

## 13. Audit Boundary

- Every workflow step links to its audit event ids in the Phase 2D durable
  store.
- Workflow steps reuse the existing controlled-execution audit chain (no new
  audit writer; no new audit kind is required — if one is needed it must be
  explicitly approved).
- No secret / token / hash / raw arg / callable repr leak via the workflow
  surface.

---

## 14. Success Criteria

1. Workflow schema implemented.
2. Workflow planner + dry-run preview implemented.
3. Manual step execution implemented.
4. Approval gates enforced (no step auto-executes a write).
5. Read-only / fake-provider / sandbox-write-preview / rollback-reference steps
   work end-to-end and reuse Phase 2 capabilities.
6. Audit linkage works for every step.
7. Workflow timeline UI works inside the console.
8. No autonomous write; no real provider; no shell / db / external write.
9. Route governance unchanged (or explicitly approved + recorded).
10. All tests pass; smoke pass; memory-check / dev-check PASS.
11. Production untouched (PID `28428`; no `~/.hermes` / `state.db` access).

---

## 15. Phase 3A Must Not Start in This Planning Phase

This document freezes the scope. The actual Phase 3A work is deferred to a
separately authorized phase that begins only when the user explicitly asks for
the Phase 3A execution prompt / implementation. The execution brief is
[phase-3a-execution-brief.md](phase-3a-execution-brief.md); the prompt draft
is [phase-3a-prompt.md](phase-3a-prompt.md).

---

## 16. Cross-References

- [Phase 3 planning](phase-3-planning.md)
- [Phase 3 options evaluation](phase-3-options-evaluation.md)
- [Phase 3 risk register](phase-3-risk-register.md)
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)
- [Phase 3A execution brief](phase-3a-execution-brief.md)
- [Phase 3A prompt draft](phase-3a-prompt.md)
