# Phase 3A — Security Boundary

## Capability table (frozen)

| Capability | State |
|------------|-------|
| Real provider | **Blocked** |
| Provider auto-write | **Blocked** |
| Autonomous write | **Blocked** |
| Write execute | **Blocked** (preview only) |
| Rollback execute | **Blocked** (reference only) |
| Shell command | **Blocked** |
| Database mutation | **Blocked** |
| External service write | **Blocked** |
| Production rollout | **Blocked** |
| Sandbox write preview | Allowed |
| Rollback reference | Allowed |
| Fake provider | Allowed |
| Manual approval | **Required** |
| Audit | Enabled |

## Enforcement layers

1. **Schema** — only six step types are `ALLOWED_STEP_TYPES`; fifteen are
   `FORBIDDEN_STEP_TYPES`, each with a precise blocked reason.
2. **Planner** — rejects forbidden step types, unsafe paths, secret-like input,
   raw-token input, and provider-suggested write tools before any plan is built.
3. **Step execution** — `validate_step_execution_allowed` re-checks the step
   type; `execute_workflow_step` enforces step ordering + consumes the approval.
   Write/rollback step "execution" only records a preview/reference — it never
   calls `_dispatch_write_tool` / `_dispatch_rollback_tool`.
4. **Approval scope** — `workflow_step_approval` is a dedicated scope; it cannot
   authorize `write_execute` or `rollback_execute`.
5. **Route governance** — no new HTTP route; the four workflow modes are
   branches on the existing `/tools/dry-run` + `/tools/execute` routes
   (OpenAPI 34 / runtime 34 / Tool GET 5 / write 0 / dry-run 1 / execution 1).
6. **Sanitization** — every persisted document, audit event, and API response is
   sanitized (no raw args / tokens / hashes / secrets / callable reprs /
   production paths).

## Production isolation

- The workflow store is confined to the dev `HERMES_HOME`.
- The approval store rejects the production home.
- No `~/.hermes` access; no production `state.db` access.
- Production Gateway PID `28428` is never stopped / restarted / replaced /
   signaled.

## Deferred (not in Phase 3A)

Real provider integration, plugin registry, scheduling, multi-user workflow,
production pilot — all deferred to later phases.
