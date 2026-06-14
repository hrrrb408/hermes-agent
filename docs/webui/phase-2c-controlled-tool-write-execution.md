# Phase 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)

## Scope

Phase 2C upgrades the Dev WebUI from a **read-only tool platform** to a
**controlled dev-sandbox write platform**. It adds four bounded write tools
that operate **only** inside a dev sandbox root under the dev `HERMES_HOME`:

| Tool ID | Operation |
|---------|-----------|
| `dev_sandbox_file_write` | create-or-replace a UTF-8 text file |
| `dev_sandbox_file_append` | append UTF-8 text to a file |
| `dev_sandbox_file_patch` | single-occurrence find-and-replace patch |
| `dev_sandbox_file_readback` | bounded read-back summary (write workflow) |

Every write is gated by the **two-phase model**: Phase A (plan / dry-run /
preview) and Phase B (confirm / execute). No write may occur without a prior
preview, a confirmation token, an argument-digest match, pre/post execution
audit, and a rollback manifest.

## Architecture

Write tools live in a **completely separate** registry, allowlist, and
execution chain from the Phase 2A read-only tools. The Phase 1G/2A
`STATIC_ALLOWLIST` stays **frozen at exactly six read-only tools** — write
tools never join it (verified by ~30 frozen assertions + an import-time
integrity check). Write tools are not registered Hermes agent tools and are not
in the production tool dispatch path.

Backend modules:

| Module | Responsibility |
|--------|----------------|
| `hermes_cli/dev_web_write_tool_registry.py` | write definitions, `STATIC_WRITE_ALLOWLIST`, argument validation |
| `hermes_cli/dev_web_write_sandbox.py` | sandbox root, path validation, safe IO, hashing, diff |
| `hermes_cli/dev_web_write_rollback.py` | rollback manifest + preview |
| `hermes_cli/dev_web_write_plan.py` | plan, preview, audit writer, confirmation token |
| `hermes_cli/dev_web_write_handlers.py` | 4 handlers + `dispatch_write_tool` chain |

## API (no new routes)

Phase 2C reuses the existing routes via `mode` branches, exactly as Phase 2B
reused `/tools/execute` for `provider_roundtrip`:

- `POST /api/dev/v1/tools/dry-run` with `body.mode = "write_preview"` →
  plan + preview + confirmation token (no file written).
- `POST /api/dev/v1/tools/execute` with `body.mode = "write"` → full
  controlled-write chain.
- `POST /api/dev/v1/tools/execute` with `mode = "provider_roundtrip"` +
  `providerWriteMode = "preview_only"` (or write tool ids in `allowedToolIds`)
  → provider write preview only; **never auto-executes**.

Route governance is unchanged: **OpenAPI paths 34, runtime routes 34, Tool GET
5, Tool write route 0, Tool dry-run route 1, Tool execution route 1**.

## Enablement

Write execution is **disabled by default**. The single env gate is
`HERMES_TOOL_WRITE_EXECUTION_ENABLED` (accepts `1` or `true`). When unset,
`manual_write` execute is blocked with `blocked_write_execution_not_enabled`
and `provider_write_preview` returns a preview but blocks auto-execution. The
smoke harness exports this gate only for the `phase2c_write_sandbox` profile
and the script process exit cleans it up.

## Safety boundaries (non-negotiable)

- Writes happen ONLY inside `$HERMES_HOME/gateway/dev/tool-write-sandbox`.
- Path traversal, absolute paths, symlink escape, `~` references, and
  backslashes are blocked.
- Forbidden targets are blocked: `.env`, `.claude`, `.git`, `*.db`,
  `*.sqlite*`, `*.jsonl`, `*.log`, `test-results`, `playwright-report`,
  `node_modules`, `dist`, `build`, `state.db`.
- Only text file types are accepted (`.txt/.md/.json/.yaml/.yml/.csv`); binary
  content (NUL / C0 control chars) is rejected.
- Size limits: single write ≤ 64 KiB; file after write ≤ 256 KiB; filename
  ≤ 120 chars; path depth ≤ 5.
- No shell command execution, no database mutation, no external service write,
  no production rollout, no `~/.hermes` access, no production `state.db` access.
- No raw token / full tokenHash / raw arguments / secrets / callable repr are
  ever exposed in responses or audit JSONL.

See the companion docs: [write-tool-registry](phase-2c-write-tool-registry.md),
[write-sandbox-security](phase-2c-write-sandbox-security.md),
[write-audit-model](phase-2c-write-audit-model.md),
[write-rollback-plan](phase-2c-write-rollback-plan.md),
[write-test-report](phase-2c-write-test-report.md).

## Production gateway PID baseline refresh

During the Phase 2C session the production Gateway was **externally
restarted** (live PID moved `1962 → 28428`; one healthy process; not caused by
Phase 2C work). Under user authorization, the PID baseline constant was
refreshed from `1962` to `28428` in `dev_web_provider_request.py`,
`dev_web_read_only_tool_handlers.py`, the smoke harness, and the relevant
tests. The task sanctions an authorized PID refresh on drift (P2). Historical
docs retain the `1962` baseline they recorded at their own time.
