# Phase 2A — Real Tool Execution MVP (Read-only Multi-tool Execution)

## 1. Summary

Phase 2A upgrades the Hermes Dev WebUI from the Phase 1G clarify-only
controlled-execution MVP to a **read-only multi-tool execution MVP**. The
WebUI can now execute five Dev-WebUI-local read-only inspection tools through
the full Phase 1G controlled-execution chain, in addition to `clarify`.

The five new tools are **Dev-WebUI-local bounded read-only inspection
surfaces**, NOT registered Hermes agent tools. They mirror the bounded-
reimplementation pattern already used for the `clarify` handler in
`hermes_cli/dev_web_tool_handler_call.py`: each is a deterministic,
side-effect-free pure function that inspects only dev-local / in-process state.

- **clarify** — Phase 1G baseline (unchanged, backward compatible).
- **tool_policy_read** — returns the static tool-execution policy.
- **route_governance_read** — returns the OpenAPI/runtime/tool route summary.
- **audit_events_read** — queries the dev JSONL audit stores (containment-guarded).
- **dev_environment_read** — dev HERMES_HOME health + read-only production gateway PID observation.
- **release_status_read** — docs/webui release-status summary.

## 2. Status

| Item | Value |
|------|-------|
| Phase | 2A |
| Goal | Read-only multi-tool execution MVP |
| Predecessor | Phase 1G SEALED (FINAL-SEAL-1G-11-001) |
| Phase 2 Unlock | PHASE-2-UNLOCK-1G-11-001 |
| Human Decision | HUMAN-DECISION-1G-10B-001 (GO) |
| Implemented capability | read-only multi-tool execution |
| Provider integration | delivered in Phase 2B (controlled fake-provider round-trip; real blocked by default) |
| Tool write | deferred to Phase 2C |
| Production rollout | NOT performed |
| Production `~/.hermes` | NOT accessed |
| Production `state.db` | NOT accessed |

## 3. Implemented Tools

| Tool ID | Status | Read-only | Provider | External Side Effects | Risk |
|---------|--------|-----------|----------|-----------------------|------|
| clarify | supported (Phase 1G) | yes | false | false | R0 |
| tool_policy_read | implemented | yes | false | false | R0 |
| route_governance_read | implemented | yes | false | false | R0 |
| audit_events_read | implemented | yes | false | false | R1 |
| dev_environment_read | implemented | yes | false | false | R1 |
| release_status_read | implemented | yes | false | false | R1 |

All five read-only tools: `readOnly=true`, `providerRequired=false`,
`writeRequired=false`, `externalSideEffects=false`, `requiresConfirmation=true`
(they flow through the full controlled-execution chain, including the
confirmation token).

## 4. Backend Deliverables

- **Registry** — `hermes_cli/dev_web_read_only_tool_registry.py`: the single
  metadata source for the five read-only tools. Re-exports `STATIC_ALLOWLIST`
  from the policy module (single source of truth — no second allowlist).
  Cross-checks consistency at import time.
- **Handlers** — `hermes_cli/dev_web_read_only_tool_handlers.py`: five bounded
  handlers + `dispatch_read_only_tool`. All hermes_cli imports are lazy.
- **Policy** — `hermes_cli/dev_web_tool_policy.py`: inventory expanded 71→76,
  `STATIC_ALLOWLIST` expanded `{clarify}`→6 tools, both import-time validators
  + all count invariants updated in lockstep.
- **Handler descriptors** — `hermes_cli/dev_web_tool_handler_lookup.py`:
  `_SAFE_HANDLER_DESCRIPTORS` extended with the five tools (each
  `registryKey == canonicalName`, all permission flags False).
- **Handler call** — `hermes_cli/dev_web_tool_handler_call.py`: the clarify-only
  gate generalized to dispatch-by-name (clarify inline handler + read-only
  dispatcher). The clarify path is preserved exactly.
- **Execute** — `hermes_cli/dev_web_tool_execute.py`: `_build_success_result`
  generalized — clarify keeps `clarify_execution_completed`; each read-only
  tool returns `<toolId>_execution_completed`; `executionCompleted` is the
  authoritative boolean.
- **Audit** — `dev_web_tool_dry_run_audit.py` `staticAllowlistSize` is now
  dynamic (`len(STATIC_ALLOWLIST)`); `dev_web_tool_post_execution_audit.py`
  records `resultSizeBytes` for read-only structured results;
  `dev_web_tool_audit_read.py` surfaces the per-tool summary.

## 5. Frontend Deliverables

- `src/constants/readOnlyTools.ts` — the selectable tool list + per-tool
  metadata + argument specs (mirrors the backend registry).
- `src/stores/toolExecute.ts` — multi-tool dispatch: `setCanonicalName`,
  `setArgumentValue`, generic per-tool argument builder, and a generic
  completed-check (`executionCompleted === true`).
- `src/components/workspace/ToolExecutePanel.vue` — multi-tool `<select>`,
  per-tool argument forms, safety badges, structured result panel.
- `src/components/workspace/AuditViewerPanel.vue` — tool (toolId) dropdown
  filter.
- `src/types/api/toolExecute.ts` — `ClarifyToolResult.result` added for
  read-only structured payloads.

## 6. Route Governance (Unchanged)

| Metric | Phase 1G | Phase 2A |
|--------|----------|----------|
| OpenAPI paths | 34 | 34 |
| Runtime routes | 34 | 34 |
| Tool GET routes | 5 | 5 |
| Tool write routes | 0 | 0 |
| Tool dry-run routes | 1 | 1 |
| Tool execution routes | 1 | 1 |
| STATIC_ALLOWLIST size | 1 ({clarify}) | 6 (clarify + 5 read-only) |

Phase 2A added **zero** HTTP routes. The allowlist expansion is membership-only,
not route-count. The single `/tools/dry-run` and `/tools/execute` routes now
serve all six tools.

## 7. Audit / Security

- dry-run, pre-execution, and post-execution audits are written for every tool.
- Each audit record carries `canonicalName` (the toolId).
- `providerSchemaSent`, `providerApiCalled`, `externalSideEffects` are recorded
  and are always False.
- No raw token, full tokenHash, raw arguments, secrets, or callable/function
  repr are ever exposed in responses, DOM, or audit JSONL.
- `~/.hermes` and production `state.db` are never accessed.

## 8. Deferred / Not Implemented

- Provider Schema sending (Phase 2B).
- Provider API calling (Phase 2B).
- Tool write route (Phase 2C).
- Production rollout.
- Advanced audit storage (cursor pagination / rotation / indexing — Phase 2D).
- Frontend full visual polish (Phase 2E).

## 9. Acceptance

Phase 2A Real Tool Execution MVP completed successfully. The Hermes Dev WebUI
now supports read-only multi-tool execution for `clarify`,
`tool_policy_read`, `route_governance_read`, `audit_events_read`,
`dev_environment_read`, and `release_status_read`, through the preserved
Phase 1G controlled-execution chain. Next recommended task: Phase 2B Provider
Schema / API Controlled Integration.
