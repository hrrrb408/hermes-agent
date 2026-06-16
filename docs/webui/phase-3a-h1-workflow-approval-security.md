# Phase 3A-H1 — Workflow Approval Security

**ID:** `WORKFLOW-APPROVAL-3A-H1-001`
**Lens:** 6 — Approval Gate / Token Scope Boundary

## Scope

The per-step human-approval gate: scope isolation, single-use consumption,
step + execution + digest binding, TTL, and the guarantee that a workflow
approval can never authorize a write or rollback execution.

## Evidence (code)

- `hermes_cli/dev_web_workflow_approval.py`
  - `compute_step_digest` — SHA-256 over `{execution, step, type, input}`,
    binding an approval to one step's exact input.
  - `issue_step_approval` / `verify_step_approval` / `consume_step_approval` —
    reuse the Phase 2C-H1 confirmation store under
    `SCOPE_WORKFLOW_STEP_APPROVAL`.
  - `_map_token_blocked_reason` — maps the underlying store reasons to the
    `blocked_workflow_approval_*` reasons (required / expired / already-used /
    scope-mismatch / digest-mismatch / step-mismatch).
- `hermes_cli/dev_web_confirmation_store.py`
  - `SCOPE_WORKFLOW_STEP_APPROVAL` is a distinct scope; `verify_confirmation_token`
    checks scope, expiry (`_now() > expires_dt`), used-status, and digest
    (constant-time). The plain token secret is never persisted.

## Commands

```bash
./scripts/run_tests.sh \
  tests/test_dev_web_phase_3a_h1_workflow_approval_hardening.py -- -q
```

## Findings

The approval boundary already holds. The hardening tests pin it:

- `workflow_step_approval` is registered and is distinct from `write_execute`,
  `rollback_execute`, and `provider_write_preview_confirm`.
- A workflow-scoped token does NOT verify under `write_execute` or
  `rollback_execute` (scope mismatch) — it can never authorize a write or
  rollback.
- The approval is single-use: a second `consume_step_approval` with the same
  token is rejected with `blocked_workflow_approval_already_used`.
- It is step-bound: a token issued for step A fails for step B; it is
  execution-bound; it is digest-bound (a changed `step_input` →
  `blocked_workflow_approval_digest_mismatch`).
- TTL: `ttl_seconds=0` expires immediately →
  `blocked_workflow_approval_expired` (the mapping is also unit-pinned).
- The raw token secret never appears in any persisted file; the token record
  is valid JSON scoped to `workflow_step_approval`; no raw step input
  arguments are persisted on the token record.
- The public approval id IS the underlying confirmation-token id (`cft_…`).

## Fixes

None required — no implementation defect found.

## Status

PASS.

## Residual risk

None (P0 = 0, P1 = 0). The TTL is enforced by the shared confirmation store,
whose own expiry path is covered by the Phase 2C-H1 tests.
