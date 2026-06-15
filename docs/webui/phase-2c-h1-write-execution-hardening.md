# Phase 2C-H1 — Write Execution Hardening

## Scope

Phase 2C-H1 closes the two write-execution P2 items left open by Phase 2C:

1. **Automatic rollback execution** — Phase 2C generated rollback manifests but
   did not execute them. Phase 2C-H1 adds a controlled `dev_sandbox_rollback_execute`
   tool that loads a stored manifest, verifies current sandbox state, and either
   deletes a created file or restores the previous content.
2. **File-backed confirmation token TTL** — Phase 2C used a stateless +
   in-memory single-use token. Phase 2C-H1 migrates write + rollback tokens to
   a dev-only file-backed store with TTL, scope binding, digest binding, and
   persistent single-use replay protection.

Provider write remains **preview-only** and never auto-executes. Read-only
(Phase 1G/2A) confirmation is intentionally left on its existing path to avoid
regression.

## What is NOT done (P2)

Token encryption at rest, multi-user token namespace, delete/rename/chmod
tools, binary write, shell command tools, database mutation, external service
write, production rollout, advanced audit storage/indexing, Phase 2D.

## Backend modules

| Module | Responsibility |
|--------|----------------|
| `hermes_cli/dev_web_confirmation_store.py` | file-backed token create/load/verify/mark_used/cleanup/redact |
| `hermes_cli/dev_web_write_rollback_store.py` | manifest save/load/list/mark_executed/validate/redact |
| `hermes_cli/dev_web_write_rollback.py` | rollback execution plan + preview builder + token helpers |
| `hermes_cli/dev_web_write_handlers.py` | `dispatch_rollback_tool` + rollback handler + manifest persistence at write time |
| `hermes_cli/dev_web_write_plan.py` | migrated write token to the file-backed store; rollback/confirmation audit events |

## Route governance (unchanged)

No new HTTP route. Rollback reuses the existing routes via `mode` branches:

- `POST /api/dev/v1/tools/dry-run` `mode=rollback_preview`
- `POST /api/dev/v1/tools/execute` `mode=rollback`

OpenAPI paths **34**, runtime routes **34**, Tool GET **5**, Tool write route
**0**, Tool dry-run route **1**, Tool execution route **1**.

See [phase-2c-h1-confirmation-token-ttl](phase-2c-h1-confirmation-token-ttl.md),
[phase-2c-h1-rollback-execution](phase-2c-h1-rollback-execution.md),
[phase-2c-h1-security-boundary](phase-2c-h1-security-boundary.md),
[phase-2c-h1-test-report](phase-2c-h1-test-report.md).
