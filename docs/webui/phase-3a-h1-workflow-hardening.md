# Phase 3A-H1 — Workflow Hardening

**Hardening ID:** `HARDENING-3A-H1-001`
**Phase:** 3A-H1 (the hardening pass that follows Phase 3A; NOT Phase 3B)
**Status:** Complete — 11/11 lenses PASS, P0 = 0, P1 = 0
**Scope:** Deterministic hardening of the Phase 3A dev-only Agent Workflow MVP.

## Goal

Verify — not extend — the Phase 3A workflow surface so its safety contract is
deterministic and regression-proof:

- `workflow_schema_v1` is stable; the six allowed / fifteen forbidden step
  types are frozen, disjoint, and complete.
- The workflow store is dev-only, atomic, append-only, and corruption-safe.
- The planner blocks unsafe input (paths, secrets, raw tokens, real provider,
  provider-write bids, every forbidden step type).
- The step preview never executes; a sandbox-write preview writes NO file; a
  rollback reference executes NO rollback.
- Manual execution is approval-gated, order-enforced, single-use, and
  step/digest-bound.
- Workflow audit is complete, cross-linked, and redacted.
- The Workflow UI is stable and leak-free.
- Forbidden capabilities remain blocked; real provider and autonomous write
  remain blocked.

## What this phase is NOT

It is **not** Phase 3B. It does not:

- enable a real provider or make a real provider network call;
- enable provider auto-write, auto-rollback, or autonomous write;
- add a workflow write-execute or rollback-execute path;
- add a shell command, database mutation, or external-service write;
- add a new HTTP route, Tool write HTTP route, or Provider route;
- perform a production rollout, access `~/.hermes`, or access production
  `state.db`.

The only push is `git push origin dev-huangruibang`.

## Hardening IDs

| ID | Lens |
|----|------|
| `HARDENING-3A-H1-001` | Overall workflow hardening |
| `WORKFLOW-STATE-3A-H1-001` | Store / state persistence boundary |
| `WORKFLOW-APPROVAL-3A-H1-001` | Approval gate / token scope boundary |
| `WORKFLOW-AUDIT-3A-H1-001` | Audit / redaction boundary |
| `WORKFLOW-UI-3A-H1-001` | UI / timeline / cross-link boundary |

## 11-Lens Review

| # | Lens | Outcome |
|---|------|---------|
| 1 | Workflow Schema / Step Type Boundary | PASS |
| 2 | Workflow Store / State Persistence Boundary | PASS |
| 3 | Workflow Planner / Unsafe Input Boundary | PASS |
| 4 | Step Preview / Non-execution Boundary | PASS |
| 5 | Manual Step Execution / Order Boundary | PASS |
| 6 | Approval Gate / Token Scope Boundary | PASS |
| 7 | Workflow Audit / Redaction Boundary | PASS |
| 8 | Workflow UI / Timeline / Cross-link Boundary | PASS |
| 9 | Forbidden Capability / No-autonomy Boundary | PASS |
| 10 | Smoke / Regression / Route Governance Boundary | PASS |
| 11 | Production Isolation / Runtime Artifact Boundary | PASS |

Each lens records scope, evidence, commands, findings, fixes, status, and
residual risk in the focused docs below.

## Deliverables

- **Backend hardening tests** (7 files):
  `tests/test_dev_web_phase_3a_h1_workflow_{schema,store,planner,preview_execute,
  approval,audit_security,api_security}_hardening.py`.
- **Frontend hardening tests** (5 files):
  `apps/hermes-dev-webui/src/tests/phase3a-h1-workflow-{routing,ui-state,
  approval,no-leak,safety-boundary}.spec.ts`.
- **Smoke profile** `phase3a_h1_workflow_hardening` + the Playwright spec
  `apps/hermes-dev-webui/tests/smoke/phase-3a-h1-workflow-hardening-smoke.spec.ts`,
  included in the `all` profile.
- **Hardening audit script**
  `scripts/run-dev-webui-phase3a-hardening-audit.sh` (11 lenses, deterministic).
- **Docs:** this file plus the four focused security docs and the test report.

## Code changes

No implementation change was required. The Phase 3A modules already satisfy
every boundary; this phase adds adversarial tests, a smoke profile, the audit
script, and documentation. (Had a real bug surfaced, only the files listed in
the execution brief's "Modifiable code range" would have been touched.)

## Boundary invariants (unchanged from Phase 3A)

- Workflow store root: `$HERMES_HOME/gateway/dev/workflow-store` (dev only).
- Approval scope: `workflow_step_approval` (never `write_execute` /
  `rollback_execute`).
- Audit store: Phase 2D durable store, `redactionApplied=true`,
  `externalNetworkCalled=false`.
- Route governance: OpenAPI 34 / runtime 34 / Tool GET 5 / write 0 / dry-run 1 /
  execution 1.

## Successor — Phase 3B Planning (2026-06-16)

Phase 3A-H1 is the **direct predecessor** of **Phase 3B Planning — Real Provider
Read-only Controlled Integration Scope Freeze** (`PHASE-3B-PLANNING-001`). With
the dev-only workflow container implemented and hardened, the next slice (the
real provider read-only round-trip) had its scope frozen in a separate docs-only
planning phase — **without being implemented**. Phase 3B Planning changes no
product code, reads no API key, makes no network call, and keeps every Phase 3A-H1
boundary: real provider blocked, provider auto-write / autonomous write blocked,
no shell / db / external write, no production rollout, route governance unchanged
(34/34/5/0/1/1), Production Gateway PID `28428` untouched. See
[phase-3b-planning](phase-3b-planning.md) and
[phase-3b-provider-readonly-scope-freeze](phase-3b-provider-readonly-scope-freeze.md).

## Related docs

- [Workflow State Consistency](phase-3a-h1-workflow-state-consistency.md)
- [Workflow Approval Security](phase-3a-h1-workflow-approval-security.md)
- [Workflow Audit Security](phase-3a-h1-workflow-audit-security.md)
- [Workflow UI Security](phase-3a-h1-workflow-ui-security.md)
- [Phase 3A-H1 Test Report](phase-3a-h1-test-report.md)
- [Phase 3A Security Boundary](phase-3a-security-boundary.md)
- [Phase 3B planning](phase-3b-planning.md)
