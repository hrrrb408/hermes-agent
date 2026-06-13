# Phase 1G-04-31: Final WebUI Sealing

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-04-31 |
| Title | Final WebUI Sealing — Phase 1G-04 WebUI Mainline Closure |
| Status | Completed locally / pushed |
| Date | 2026-06-13 |
| Author | Dev Agent (Phase 1G-04-31 final sealing) |
| Dependencies | Phase 1G-04-30 completed and pushed (`5d498fd7e`) |
| Branch | dev-huangruibang |
| Base commit | `5d498fd7e09e2353ce0aa9d6a99444e59d388ef6` |
| Implementation | Docs closure + final acceptance report + implementation-plan/scope sealing markers + final regression / frontend / smoke / gate verification. No new routes, no allowlist change, no Provider, no non-clarify execution. |

---

## 1. Phase Definition

Phase 1G-04-31 is the **final sealing** phase of the Phase 1G-04 WebUI mainline.
It does **not** add new functionality. It performs:

1. Final Git / remote / worktree verification.
2. Final route-governance verification.
3. Final backend regression.
4. Final frontend typecheck / lint / unit / build.
5. Final browser smoke / E2E (both default-block and completed scenarios).
6. Final security-boundary search.
7. Final production-isolation verification.
8. P2 risk transparency (recorded, not fixed).
9. Final documentation closure.
10. A single final sealing commit.
11. A single final push.
12. This final sealing report.

This phase makes only **small sealing-touch** changes:

- Documentation closure (this doc + the final acceptance report).
- Implementation-plan and scope sealing markers.
- No route, allowlist, Provider, execution-boundary, or test-strength change.

---

## 2. Baseline HEAD

| Item | Value |
|------|-------|
| Branch | `dev-huangruibang` |
| Pre-sealing HEAD | `5d498fd7e09e2353ce0aa9d6a99444e59d388ef6` |
| Pre-sealing remote HEAD | `5d498fd7e09e2353ce0aa9d6a99444e59d388ef6` |
| Merge base | `5d498fd7e09e2353ce0aa9d6a99444e59d388ef6` |
| ahead / behind | `0 / 0` |
| Tracked worktree | clean |
| Untracked | `.claude/` only |
| HERMES_HOME (dev) | `/Users/huangruibang/Code/hermes-home-dev` |
| Production Gateway baseline PID | `69355` |

---

## 3. Completed Backend Chain

The full controlled-execution backend loop was built across Phase 1G-04-02 …
1G-04-30 and is now sealed. The end-to-end gate order on the execute route is:

1. **Dry-run historical lookup** (Phase 1G-04-15/16) — bind the request to a prior
   dry-run audit event by `dryRunRequestId` + `dryRunDecisionDigest`.
2. **Confirmation token gate** (Phase 1G-04-18/19/20) — verify + consume the
   one-shot confirmation token issued by the dry-run endpoint.
3. **Digest verification gate** (Phase 1G-04-21/22) — recompute the digest bound
   to the real audit `eventId` / timestamp / expiry and require an exact match.
4. **Pre-execution audit** (Phase 1G-04-23/24) — write the pre-execution audit
   record before any handler call.
5. **Handler lookup** (Phase 1G-04-25/26) — resolve the registered handler
   descriptor for the canonical name.
6. **Dispatch planning** (Phase 1G-04-27/28) — build a side-effect-free dispatch
   envelope / plan.
7. **Clarify-only Tool Handler call** (Phase 1G-04-29) — invoke the bounded,
   safe clarify handler when the explicit handler-call gate is enabled.
8. **Post-execution audit** (Phase 1G-04-29) — write the post-execution audit
   record with provider / external side-effect flags (all false).

The backend chain is supported by:

- Read-only **audit events API** `GET /api/dev/v1/tools/audit-events`
  (Phase 1G-04-30) returning redacted, whitelist-normalized audit items for
  `dry_run` / `pre_execution` / `post_execution`.
- A safe **audit JSONL reader** (`hermes_cli/dev_web_tool_audit_read.py`) with
  production-path containment and per-kind normalization.
- A **digest-binding fix** (Phase 1G-04-30) so the real dry-run → execute chain
  no longer returns `blocked_digest_mismatch`.

---

## 4. Completed Frontend Chain

The Dev WebUI (independent Vue 3 app at `apps/hermes-dev-webui/`) ships:

- **Execute UI** (`ToolExecutePanel.vue`) — a clarify-only controlled-execution
  workbench surfaced as Tools → Execute / Audit sub-tabs. Exposes Dry Run →
  decision / risk / digest (short) / confirmation-token ID, and Confirm &
  Execute → execute-gate decision. Default gate unset shows
  `blocked_tool_handler_call_not_enabled`; explicit dev/test gate shows
  `clarify_execution_completed` with `handlerCallId` / `postExecutionAuditId`
  and false provider side-effect flags.
- **Audit Viewer** (`AuditViewerPanel.vue`) — read-only audit events with
  `auditKind` switching, limit / canonical-name filter / refresh, empty state,
  malformed-line-skip note, per-event safe summary, and expandable correlation
  IDs.
- **API client + stores** (`api/toolExecute.ts`, `api/toolAudit.ts`,
  `stores/toolExecute.ts`, `stores/toolAudit.ts`) with the raw confirmation
  token held in an in-memory, non-reactive closure (never persisted, logged,
  or rendered).

---

## 5. Route Governance Final State

| Metric | Value |
|--------|-------|
| OpenAPI paths | **34** |
| Runtime routes | **34** |
| Tool GET routes | **5** |
| Tool write routes | **0** |
| Tool dry-run routes | **1** |
| Tool execution routes | **1** |
| STATIC_ALLOWLIST | `frozenset({"clarify"})` |

Exactly one read-only GET route (`/tools/audit-events`) was added across the
1G-04-30 closeout. No Tool write route, no second execution route, no Provider
route exists. The route count is unchanged from the 1G-04-30 baseline.

---

## 6. Security Boundary

| Item | Status |
|------|--------|
| STATIC_ALLOWLIST changed | No — remains `frozenset({"clarify"})` |
| Allowlist expanded | No |
| Raw token exposed | No (in-memory only; never persisted / logged / rendered / audited) |
| Full tokenHash exposed | No (only short digest / token ID surfaced) |
| Raw arguments exposed (audit viewer) | No (whitelist normalization) |
| Secrets exposed | No (defensive redaction) |
| Callable / function repr exposed | No |
| Production `~/.hermes` accessed | No |
| Production `state.db` accessed | No |
| Provider Schema sent | No |
| Provider API called | No |
| Non-clarify execution | No |
| Tool write route added | No |
| Route expansion beyond approved state | No |
| Audit JSONL committed | No (runtime-generated under dev `HERMES_HOME` only) |
| `.claude/` committed | No (remains untracked) |

---

## 7. Browser Smoke Summary

The phase-1g-04-30 execute + audit viewer smoke was run against an isolated
dev API (`127.0.0.1:5181`) + WebUI (`127.0.0.1:5180`), in two gate
configurations:

| Scenario | Server gate config | Expected decision | Result |
|----------|--------------------|-------------------|--------|
| Blocked | `HERMES_TOOL_EXECUTION_ENABLED=true`, `HERMES_AGENT_TOOLS_ENABLED=true`, handler-call gate unset | `blocked_tool_handler_call_not_enabled` | **6 passed, 1 skipped, 0 failed** |
| Completed | all three gates `=true` (incl. handler-call) | `clarify_execution_completed` | **7 passed, 0 failed** |

Coverage: audit events API (read-only, invalid-kind 400, POST 405), controlled
execution chain (dry-run → execute), `postExecutionAuditId` visibility in the
audit viewer API, provider / external side-effect flags always false, and UI
(Execute + Audit sub-tabs render; UI dry-run surfaces a safe decision without
the raw token). The single skip in the blocked scenario is the
post-execution-audit-visibility test, which is correctly skipped on the blocked
path (no post-execution audit is written when execution is blocked).

Servers were isolated to `127.0.0.1`, started/stopped by a PID-tracked harness,
and torn down after each run. Production Gateway PID `69355` was not affected.

---

## 8. Backend Regression Summary

| Gate | Result |
|------|--------|
| Audit read module tests | pass |
| Audit read API tests | pass |
| Execute / execution chain tests | pass |
| Dry-run / policy / schema tests | pass |
| Route governance (`test_dev_check_webui.py`, `test_dev_web_0c06_closure.py`) | pass |
| **Full related backend regression (19 files)** | **1471 passed, 2 skipped, 5 deselected, 0 failed** |
| `compileall` (changed modules) | pass |
| `toolsets.py` compile | pass |
| `ruff check` (changed files) | all checks passed |

---

## 9. Frontend Quality Summary

| Gate | Result |
|------|--------|
| Package manager | pnpm (`pnpm-lock.yaml`, pnpm 10.33.0) |
| `pnpm type-check` (vue-tsc) | pass |
| `pnpm lint` (eslint) | pass (0 errors / 0 warnings) |
| `pnpm test` (vitest) | **674 passed (31 files), 0 failed** |
| `pnpm build` (vite) | pass |
| Browser smoke / E2E | both scenarios pass (see §7) |

---

## 10. Production Isolation Summary

| Item | Value |
|------|-------|
| Dev HERMES_HOME used | `/Users/huangruibang/Code/hermes-home-dev` |
| Production `~/.hermes` | untouched |
| Production `state.db` | untouched |
| Production Gateway PID (before) | `69355` |
| Production Gateway PID (after) | `69355` (unchanged) |
| Dev Gateway | stopped throughout |
| Dashboard | not started |
| `5180` final | free |
| `5181` final | free |
| Bind host | `127.0.0.1` only |

All verification used the dev `HERMES_HOME` and bound only to `127.0.0.1`. No
production Gateway process was stopped, restarted, replaced, or reconfigured.

---

## 11. Risks

### P0
- (none) — no allowlist change, no non-clarify execution, no Provider
  Schema/API, no raw secret exposure, no production access, no route expansion.

### P1
- (none) — backend regression, frontend typecheck/lint/unit/build, route
  governance, compileall, ruff, memory-check, dev-check, and browser smoke
  (both scenarios) all pass.

### P2 (recorded, non-blocking)
- **Stale `auditWritten=false` assumption** in the dormant
  `phase-1g-04-dry-run-api-safety-smoke.spec.ts`. The `auditWritten` field now
  reflects dry-run audit-event persistence (true under a configured
  `HERMES_HOME` since Phase 1G-04-06 dry-run audit storage), not an execution
  side effect. The spec is not wired into any active smoke runner, so it does
  not affect any gate. Left as a historical stale test assumption rather than
  modified, to avoid touching a security-flag assertion during the conservative
  sealing phase.
- Audit pagination is offset-based; multi-file JSONL rotation / race handling
  is future local-dev work.
- The audit read API caps total lines parsed per request at 1000; large-scale
  audit search / indexing is future work.
- Non-clarify tools remain disabled (by design).
- Provider integration is a permanent non-goal for this controlled path.
- Frontend visual polish is optional / future.

---

## 12. Acceptance Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Final sealing doc created | ✅ |
| 2 | Final acceptance report created | ✅ |
| 3 | Implementation plan marked sealed | ✅ |
| 4 | Route governance = 34 / 34 / 5 / 0 / 1 / 1 | ✅ |
| 5 | STATIC_ALLOWLIST = `frozenset({"clarify"})` | ✅ |
| 6 | No allowlist expansion | ✅ |
| 7 | No Provider Schema / API | ✅ |
| 8 | No non-clarify execution | ✅ |
| 9 | No Tool write route | ✅ |
| 10 | No route expansion beyond 34 | ✅ |
| 11 | No production `~/.hermes` access | ✅ |
| 12 | No production `state.db` access | ✅ |
| 13 | No raw token / full tokenHash / raw args / secret leak | ✅ |
| 14 | No callable / function repr exposure | ✅ |
| 15 | No audit JSONL committed | ✅ |
| 16 | `.claude/` not committed | ✅ |
| 17 | Backend regression passed (1471) | ✅ |
| 18 | Frontend typecheck / lint / unit / build passed | ✅ |
| 19 | Browser smoke / E2E passed (both scenarios) | ✅ |
| 20 | memory-check PASS | ✅ |
| 21 | dev-check PASS (only `.claude/` dirty WARN) | ✅ |
| 22 | Production Gateway PID `69355` unaffected | ✅ |
| 23 | Dev Gateway stopped; 5180 / 5181 free | ✅ |
| 24 | Final sealing commit created | ✅ |
| 25 | Final sealing commit pushed | ✅ |
| 26 | local == remote; ahead / behind = 0 / 0 | ✅ |
| 27 | Phase 1G-04 WebUI mainline sealed | ✅ |

---

## 13. Final Push Criteria

A single normal push (`git push origin dev-huangruibang`) was performed after
all final gates passed. No force push, force-with-lease, rebase, or merge was
used. Local and remote are synchronized with `ahead / behind = 0 / 0`.

Final HEAD after the sealing commit: recorded in the final acceptance report
(see `docs/webui/phase-1g-04-final-acceptance-report.md`).

---

*Phase 1G-04-31 Final WebUI Sealing: documentation closure, final acceptance
report, implementation-plan and scope sealing markers, and a full final
verification pass (backend regression 1471 / frontend typecheck-lint-unit(674)-build
/ both browser-smoke scenarios / memory-check / dev-check / compileall / ruff).
STATIC_ALLOWLIST remains `frozenset({"clarify"})`. Route governance is stable at
OpenAPI 34 / runtime 34 / Tool GET 5 / Tool write 0 / Tool dry-run 1 /
Tool execution 1. No Provider, no non-clarify execution, no Tool write route,
no production access. The final sealing commit was pushed to
origin/dev-huangruibang. Phase 1G-04 WebUI mainline is sealed.*
