# Phase 1G-10A: Smoke Harness PID Baseline Refresh — `SMOKE-PID-REFRESH-1G-10A-001`

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-10A |
| Title | Smoke Harness PID Baseline Refresh |
| Status | Authored locally (not pushed) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Refresh ID | `SMOKE-PID-REFRESH-1G-10A-001` |
| Related Closeout ID | `CLOSEOUT-1G-10-001` |
| Related Final Decision Preparation ID | `RELEASE-DECISION-PREP-1G-10-001` |
| Related Pilot Execution ID | `PILOT-EXEC-1G-09-001` |
| Related Pilot Acceptance ID | `PILOT-1G-08-001` |
| Related RC ID | `RC-1G-07-001` |
| Baseline HEAD (remote) | `cd7298416d82a1dabe22b783bf5656ca8393e6f0` |
| Local pre-refresh HEAD | `f403eb1cb68b5975e45c5fc6f39a7b010cc6ea0f` |
| Scope | Refresh the dev-only browser smoke harness Production Gateway PID baseline after the host-reboot drift observed in Phase 1G-10, then rerun fresh smoke. One script line + comment; no production change. |
| Author | Dev Agent (Phase 1G-10A smoke harness PID baseline refresh) |

---

## 1. Phase Definition

Phase 1G-10A is an **independent dev-only maintenance phase** that runs *after*
the Phase 1G-10 Post-Pilot Closeout (`CLOSEOUT-1G-10-001`) was completed
locally (commit `f403eb1cb`, not pushed).

Phase 1G-10A refreshes the pinned Production Gateway PID baseline inside the
**dev-only** browser smoke harness
(`scripts/run-dev-webui-execute-audit-smoke.sh`) from the sealed value `69355`
to the currently observed healthy value `1962`, because the host reboot
documented in Phase 1G-10 changed the Production Gateway's PID via `launchd`
restart. It then reruns the fresh browser smoke / E2E and the relevant gates,
and records the result. It does **not** authorize a release, does **not** modify
production, and does **not** start Phase 1G-11.

> **Phase 1G-10A updates a dev-only smoke harness PID baseline.**
> **Phase 1G-10A does not authorize release.**
> **Phase 1G-10A does not complete human approver sign-off.**
> **Phase 1G-10A does not modify production.**
> **Phase 1G-10A does not access `~/.hermes`.**
> **Phase 1G-10A does not access production `state.db`.**

---

## 2. Identification

| Field | Value |
|------|-------|
| Refresh ID | `SMOKE-PID-REFRESH-1G-10A-001` |
| Related Closeout ID | `CLOSEOUT-1G-10-001` |
| Related Final Decision Preparation ID | `RELEASE-DECISION-PREP-1G-10-001` |
| Related Pilot Execution ID | `PILOT-EXEC-1G-09-001` |
| Related Pilot Acceptance ID | `PILOT-1G-08-001` |
| Related RC ID | `RC-1G-07-001` |
| Baseline HEAD (remote) | `cd7298416d82a1dabe22b783bf5656ca8393e6f0` |
| Local pre-refresh HEAD | `f403eb1cb68b5975e45c5fc6f39a7b010cc6ea0f` |

All Phase 1G-10A deliverables record these identifiers consistently.

---

## 3. Baselines Re-Confirmation

| Baseline | State at Phase 1G-10A start |
|----------|----------------------------|
| Phase 1G-04 WebUI mainline | **SEALED** |
| Phase 1G-05 readiness | **pushed** |
| Phase 1G-06 release rehearsal | **pushed** |
| Phase 1G-07 RC dry run | **pushed, GO** (`RC-1G-07-001`) |
| Phase 1G-08 Pilot preparation | **pushed** (`PILOT-1G-08-001`) |
| Phase 1G-09 Pilot execution | **pushed, PASS** (`PILOT-EXEC-1G-09-001`) |
| Phase 1G-10 Post-Pilot closeout | **completed locally, not pushed** (`CLOSEOUT-1G-10-001`) |

Git baseline at refresh start:

| Item | Value |
|------|-------|
| Branch | `dev-huangruibang` |
| Local HEAD | `f403eb1cb68b5975e45c5fc6f39a7b010cc6ea0f` |
| Remote HEAD | `cd7298416d82a1dabe22b783bf5656ca8393e6f0` |
| Merge base | `cd7298416d82a1dabe22b783bf5656ca8393e6f0` |
| ahead / behind | `1 / 0` (local ahead by 1; remote ahead by 0) |
| Tracked worktree | clean (before the Phase 1G-10A script edit) |
| Untracked | `.claude/` only |

---

## 4. Sealed PID Baseline vs. Observed PID

| Field | Value |
|-------|-------|
| Sealed smoke harness PID baseline (Phase 1G-04 → 1G-09) | `69355` |
| Production Gateway observed PID after host reboot | `1962` |
| Production Gateway process count | exactly **1** |
| Production Gateway command | `hermes_cli.main gateway run --replace` |
| Production Gateway start time | `2026-06-14 04:04:30` (PPID = 1, `launchd`) |
| Root cause of drift | host reboot (`2026-06-14 04:02:09`) → `launchd` respawn |

---

## 5. Root Cause

The host rebooted on `2026-06-14 04:02:09`. `launchd` respawned the Production
Gateway at `04:04:30` as PID `1962` (PPID = 1), with the identical command
`hermes_cli.main gateway run --replace`. The sealed baseline PID `69355`
(referenced throughout Phase 1G-04 → Phase 1G-09) no longer exists. Exactly
**one** Production Gateway process is running.

This is **environmental host-reboot drift**, not an action of any phase. Phase
1G-10 discovered and documented this drift; Phase 1G-10A refreshes the dev-only
smoke harness baseline so the harness's read-only production-PID preflight stops
failing-closed on the now-stale `69355` value and instead pins the currently
healthy `1962` value, while still failing-closed on any *future* PID drift.

---

## 6. Scope

Phase 1G-10A is permitted to:

1. Read current Git state (branch, HEAD, ahead/behind, worktree).
2. Read current Production Gateway process state (read-only `ps` / `pgrep`).
3. Confirm exactly one Production Gateway process with observed PID `1962`.
4. Modify the dev-only smoke harness PID baseline `69355` → `1962`.
5. Add a comment documenting the Phase 1G-10 host-reboot drift origin.
6. Rerun fresh browser smoke / E2E and the relevant gates.
7. Update docs (`docs/webui/...`) to record Phase 1G-10A.
8. Create a **local** commit. **No push.**

The change runs **only** against the development instance:

- Dev `HERMES_HOME`: `/Users/huangruibang/Code/hermes-home-dev`
- Production `~/.hermes`: **never accessed**
- Production `state.db`: **never accessed**

---

## 7. Out of Scope

Phase 1G-10A does **not**:

- authorize a formal release or production rollout;
- modify production data, the production gateway, or production configuration;
- access production `~/.hermes` or production `state.db` in any form
  (`ls`, `stat`, `find`, `cat`, `sqlite3`, `du`, mtime checks, …);
- stop, restart, replace, signal, or reconfigure the Production Gateway;
- reopen Phase 1G-04, 1G-05, 1G-06, 1G-07, 1G-08, 1G-09, or 1G-10;
- add any WebUI product capability;
- modify any backend or frontend functional code;
- add a backend route, a Tool write route, a second Tool execution route, or a
  Provider route;
- enable any non-clarify execution;
- expand `STATIC_ALLOWLIST` beyond `frozenset({"clarify"})`;
- send a Provider Schema or call a Provider API;
- bypass the smoke harness preflight (the PID value is refreshed; the preflight
  logic itself is unchanged and still fails-closed on future drift);
- fabricate human approver sign-off or release authorization;
- push to the remote;
- start Phase 1G-11.

---

## 8. Script Change Summary

Script: `scripts/run-dev-webui-execute-audit-smoke.sh`

| Item | Value |
|------|-------|
| Old value | `PRODUCTION_GATEWAY_PID=69355` |
| New value | `PRODUCTION_GATEWAY_PID=1962` |
| Comment added | `Phase 1G-10A refresh: host reboot changed the sealed production gateway PID from 69355 to 1962. Keep this value pinned so the dev-only smoke harness fails closed on future PID drift.` |
| Smoke logic changed | **no** |
| Preflight logic changed | **no** |
| Production gateway count check relaxed | **no** |
| Ports cleanup check relaxed | **no** |
| PID check bypassed | **no** |
| `bash -n` syntax check | **pass** |

The old value `69355` now appears **only** in the explanatory comment (as sealed
baseline history), never as an executable value.

---

## 9. Safety Checks Retained

The dev-only smoke harness continues to enforce (all unchanged by Phase 1G-10A):

- read-only Production Gateway sanity (informational, never acted upon);
- read-only Production Gateway preflight — expects exactly one process whose PID
  equals `PRODUCTION_GATEWAY_PID`, otherwise **fail-closed**;
- dev services bind to `127.0.0.1` only (`5180` WebUI / `5181` Dev API);
- cleanup of only the PIDs this harness started;
- final Production Gateway PID re-check (must remain unchanged);
- final port `5180` / `5181` free check;
- `~/.hermes` refused by the dev environment guard.

Only the pinned PID *value* was refreshed. The fail-closed behavior is preserved
and will trigger again on the *next* host-reboot PID drift.

---

## 10. Fresh Smoke Result

Command: `./scripts/run-dev-webui-execute-audit-smoke.sh all`

| Item | Value |
|------|-------|
| Profile A (`blocked_tool_handler_call_not_enabled`) | **6 passed / 1 skipped / 0 failed** |
| Profile B (`clarify_execution_completed`) | **7 passed / 0 failed** |
| Overall | **PASS** |
| `postExecutionAuditId` visible in audit viewer | yes (Profile B, audit-viewer API assertion passed) |
| `providerSchemaSent` | `false` (asserted in the dry-run → execute safe-decision test) |
| `providerApiCalled` | `false` (asserted in the dry-run → execute safe-decision test) |
| `externalSideEffects` | `false` (controlled-execution chain) |
| Preflight | accepted Production Gateway PID `1962`; confirmed "Will not touch it." |
| Final port `5180` | free |
| Final port `5181` | free |
| Prod Gateway PID (final) | `1962` (unchanged) |

The smoke harness now accepts the current healthy Production Gateway PID `1962`,
and still fails-closed if the PID drifts again.

---

## 11. Route Governance (unchanged)

| Metric | Value |
|--------|-------|
| OpenAPI paths | **34** |
| Runtime routes | **34** |
| Tool GET routes | **5** |
| Tool write routes | **0** |
| Tool dry-run routes | **1** |
| Tool execution routes | **1** |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` |

Phase 1G-10A changes **nothing** about route governance or the allowlist. Both
are re-verified by `tests/test_dev_check_webui.py`,
`tests/test_dev_web_0c06_closure.py`, and
`./scripts/run-dev-hermes.sh dev-check`.

---

## 12. Backend / Frontend Gate Result

| Gate | Result |
|------|--------|
| Route governance (`test_dev_check_webui.py`, `test_dev_web_0c06_closure.py`) | **124 passed / 0 failed** |
| Related backend regression (19 files) | **1471 passed / 0 failed** |
| `compileall` (14 dev_web modules) | **pass** |
| `py_compile toolsets.py` | **pass** |
| `ruff check` (modules + tests) | **All checks passed!** |
| Frontend `pnpm type-check` (`vue-tsc --noEmit`) | **pass** (0 errors) |
| Frontend `pnpm lint` (`eslint .`) | **pass** (0 errors / 0 warnings) |
| Frontend `pnpm test` (`vitest run`) | **674 passed (31 files)** |
| Frontend `pnpm build` (`vue-tsc -b && vite build`) | **pass** (1862 modules transformed) |
| `memory-check` | **PASS** |
| `dev-check` | **WARN** — only "Git worktree: dirty" from this phase's own uncommitted script edit + `.claude/`; all route / allowlist / provider / isolation checks PASS |

---

## 13. Production Safety Result

| Check | Result |
|-------|--------|
| Production Gateway PID (before refresh) | `1962` |
| Production Gateway PID (after refresh + fresh smoke) | `1962` (unchanged) |
| Production Gateway process count | exactly **1** |
| Production Gateway stopped / restarted / replaced / reconfigured by this phase | **no** |
| Dev Gateway | stopped |
| Ports `5180` / `5181` | free |
| Production `~/.hermes` accessed | no |
| Production `state.db` accessed | no |
| Dev isolation | PASS |

---

## 14. Security Boundary

The refresh keeps all of these invariants true. Any violation is a P0 and stops
the phase:

| Check | Result |
|-------|--------|
| `STATIC_ALLOWLIST` changed | no |
| Allowlist expanded beyond clarify | no |
| Raw token exposed | no |
| Full tokenHash exposed | no |
| Raw arguments exposed | no |
| Secrets exposed | no |
| Callable / function repr exposed | no |
| `~/.hermes` accessed | no |
| Production `state.db` accessed | no |
| Provider Schema sent | no |
| Provider API called | no |
| Non-clarify execution | no |
| Tool write route added | no |
| New backend route added | no |
| Smoke preflight bypassed | no |
| Audit JSONL committed | no |
| `.claude/` committed | no |

---

## 15. Final Conclusion

Phase 1G-10A refreshed the dev-only smoke harness Production Gateway PID baseline
from `69355` to `1962` after the host-reboot drift observed in Phase 1G-10. The
smoke harness fail-closed production PID preflight remains enabled; no bypass was
introduced — only the pinned *value* was refreshed, so the harness will still
fail-closed on any future PID drift.

Fresh browser smoke / E2E passed after the refresh (Profile A 6 passed / 1
skipped; Profile B 7 passed; Overall PASS), and final ports `5180` / `5181` were
free. Production Gateway PID `1962` was not stopped, restarted, replaced,
signaled, or reconfigured by this phase; exactly one Production Gateway process
remained healthy throughout.

Route governance remains unchanged (OpenAPI 34 / runtime 34 / Tool GET 5 /
write 0 / dry-run 1 / execution 1); `STATIC_ALLOWLIST` remains
`frozenset({"clarify"})`. No Provider Schema sending, Provider API call,
non-clarify execution, Tool write route, new backend route, production home
access, production `state.db` access, audit JSONL commit, `.claude/` commit, raw
token leak, full tokenHash leak, raw arguments leak, secret leak, or
callable/function repr exposure was introduced.

---

## 16. Push Status

Phase 1G-10A creates a **local** commit only. **No push.** A push requires a
separately authorized step and the human approver sign-off.

---

## 17. Phase 1G-11 Status

Phase 1G-11 is **not started**. Starting Phase 1G-11 is out of scope for
Phase 1G-10A.

---

## 18. Non-Reopening Declaration

> **Phase 1G-10A does not reopen Phase 1G-04.**
> **Phase 1G-10A does not add a new product capability.**
> **Phase 1G-10A only refreshes a dev-only smoke harness PID baseline and
> reruns fresh smoke.**

No Phase 1G-04 route, allowlist, execute gate, audit behavior, frontend
capability, or test strength is changed, weakened, or expanded by Phase 1G-10A.

---

## 19. Cross-References

- Phase 1G-10 Post-Pilot Closeout: `docs/webui/phase-1g-10-post-pilot-closeout.md`.
- Phase 1G-10 release readiness summary:
  `docs/webui/phase-1g-10-release-readiness-summary.md`.
- Phase 1G-10 final release decision preparation:
  `docs/webui/phase-1g-10-final-release-decision-preparation.md`.
- Phase 1G-10 final GO / NO-GO draft:
  `docs/webui/phase-1g-10-final-go-no-go-draft.md`.
- Phase 1G-09 Pilot final decision: `docs/webui/phase-1g-09-pilot-final-decision.md`.
- Risk register: `docs/webui/phase-1g-05-risk-register.md`.
- Implementation plan: `docs/webui/phase-1-implementation-plan.md`.
- Refreshed script: `scripts/run-dev-webui-execute-audit-smoke.sh`.

---

*Phase 1G-10A Smoke Harness PID Baseline Refresh —
`SMOKE-PID-REFRESH-1G-10A-001`. The dev-only smoke harness Production Gateway
PID baseline was refreshed from `69355` to `1962` after the Phase 1G-10
host-reboot drift. Fresh browser smoke / E2E passed. Route governance remains
34 / 34 / 5 / 0 / 1 / 1; `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`.
Release authorization remains pending human approver sign-off; no release was
authorized in this phase. Phase 1G-11 is not started.*
