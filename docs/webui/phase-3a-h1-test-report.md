# Phase 3A-H1 — Test Report

## Summary

| Suite | Files | Tests | Result |
|-------|-------|-------|--------|
| Backend Phase 3A-H1 hardening | 7 | 300 | PASS |
| Frontend Phase 3A-H1 hardening | 5 | 33 | PASS |
| Full frontend suite (incl. new specs) | 65 | 918 | PASS |
| Phase 3A backend preservation | 9 | — | PASS |
| Route governance | 2 | — | PASS (34/34/5/0/1/1) |
| Controlled-chain preservation (1G→2E-H1) | 7 | — | PASS |
| Smoke `phase3a_h1_workflow_hardening` | 1 spec | — | PASS (skip-if-down) |
| Smoke `all` (incl. hardening profile) | 11 profiles | — | PASS |
| `vue-tsc` / `eslint` / `vite build` | — | — | PASS |
| `memory-check` / `dev-check` | — | — | PASS |
| Hardening audit script (11 lenses) | 1 script | 11 | PASS |

## Backend coverage (Phase 3A-H1)

`test_dev_web_phase_3a_h1_workflow_schema_hardening.py` — schema version is an
immutable literal; 6 allowed / 15 forbidden step types are frozen, disjoint,
complete, each forbidden type maps to a precise reason; the forbidden-input-key
carrier list covers the full brief; the sanitizer is deep, side-effect-free,
and never raises on hostile input; path/shell detection; definition validation.

`test_dev_web_phase_3a_h1_workflow_store_hardening.py` — dev-home confinement
(not repo / `~/.hermes` / production); atomic write + overwrite; append-only
timeline merge; corruption safety (bad JSON, bad JSONL line, symlink refused);
input rejection (bad ids, oversized document); listing bounds + corrupt-skip;
no-leak on every persisted document type.

`test_dev_web_phase_3a_h1_workflow_planner_hardening.py` — all 15 forbidden
step types blocked; the 6 allowed types plan with a safe summary; tool ids
validated against the REAL registries; real provider / provider-write /
unsafe path / secret / raw-token input blocked; bounds + hostile request
shapes; a no-op plan is rejected by validate.

`test_dev_web_phase_3a_h1_workflow_preview_execute_hardening.py` — every
preview is non-executing (read-only dry-run, offline fake provider, no-file
write preview, no-rollback reference, display-only note, read-only audit
query); execution is approval-gated, order-enforced, single-use, step-bound;
write/rollback never execute (verified against the dev-home filesystem); the
cursor advances and the execution completes with a breadcrumb + timeline.

`test_dev_web_phase_3a_h1_workflow_approval_hardening.py` — scope isolation
(distinct from write/rollback); single-use; step + execution + digest binding;
TTL expiry; the raw token secret is never persisted; the public approval id is
the confirmation-token id.

`test_dev_web_phase_3a_h1_workflow_audit_security.py` — all 12 event types are
writable + queryable; unknown types normalize; `redactionApplied=true`;
`externalNetworkCalled=false`; no raw args/token/hash/secret/callable/prod
path; correlation ids + audit links preserved; fail-safe write.

`test_dev_web_phase_3a_h1_workflow_api_security.py` — route governance
(34/34/5/0/1/1, no `/workflows`/`/provider/` path); the four workflow modes
over the existing routes; full lifecycle + replay-blocked + token-step-bound;
write/rollback never executed over HTTP; forbidden steps blocked; no-leak
across plan / execute / state-read responses.

## Frontend coverage (Phase 3A-H1)

`phase3a-h1-workflow-routing.spec.ts` — section registered once + labelled;
API client reuses ONLY the two existing routes (static scan); invented ids
rejected.

`phase3a-h1-workflow-ui-state.spec.ts` — phase transitions; blocked-plan phase;
safe error surfacing; approval-gated execute; single-use token drop on consume;
reset clears all state.

`phase3a-h1-workflow-approval.spec.ts` — required/ready/none; Execute disabled
before token + while loading; write/rollback execute never offered; public id
rendered but raw token never rendered.

`phase3a-h1-workflow-no-leak.spec.ts` — deep no-leak scan across every
component including blocked-reason panels.

`phase3a-h1-workflow-safety-boundary.spec.ts` — every high-risk capability
Blocked; allowed/required/enabled labels; blocked-reason catalogue complete and
`blocked_workflow_`-prefixed.

## Route governance

OpenAPI paths **34**, runtime routes **34**, Tool GET **5**, Tool write HTTP
route **0**, dry-run route **1**, execution route **1**. No new path. No
`/workflows` or `/provider/` path.

## Production safety

Production Gateway PID `28428` unchanged (1 process, read-only); Dev Gateway
stopped; Dashboard not started; 5180/5181 free; no `~/.hermes` access; no
production `state.db` access. No runtime artifact (`workflow-store`,
`audit-store`, token store, rollback manifest, audit JSONL, `.claude/`) staged.
