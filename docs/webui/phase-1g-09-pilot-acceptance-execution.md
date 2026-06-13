# Phase 1G-09: Pilot Acceptance Execution

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-09 |
| Title | Pilot Acceptance Execution |
| Status | Executed locally (Pilot `PILOT-EXEC-1G-09-001`; decision recorded) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Pilot Execution ID | `PILOT-EXEC-1G-09-001` |
| Related Release Candidate | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Baseline HEAD | `9812c069ee4370babdb8599efd67ac4cb12ce148` |
| Scope | Execute the prepared Phase 1G-08 Pilot acceptance pack against the sealed Phase 1G-04 mainline on the Phase 1G-05 / 1G-06 / 1G-07 / 1G-08 baselines. No code change. |
| Author | Dev Agent (Phase 1G-09 pilot acceptance execution) |

---

## 1. Phase Definition

Phase 1G-09 is an **independent Pilot acceptance execution phase** that runs
*after* the Phase 1G-08 Pilot Acceptance Preparation (`PILOT-1G-08-001`) was
pushed at `9812c069e`.

Phase 1G-09 **executes** the prepared Pilot acceptance pack. It runs the 15
scenarios (A–O) in the two named server-gate configurations (blocked +
completed), captures evidence, records any defects, and outputs a Pilot final
decision (PASS / NO-GO / PAUSED) against the Phase 1G-08 exit criteria.

> **Phase 1G-09 does not reopen Phase 1G-04.**
> **Phase 1G-09 does not add a product capability.**
> **Phase 1G-09 executes the prepared Pilot acceptance pack.**

---

## 2. Identification

| Field | Value |
|------|-------|
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Pilot Execution ID | `PILOT-EXEC-1G-09-001` |
| Related RC ID | `RC-1G-07-001` |
| Baseline HEAD | `9812c069ee4370babdb8599efd67ac4cb12ce148` |
| Phase 1G-04 sealed | `94f22f67b` |
| Phase 1G-05 pushed | `da5c31a8c` |
| Phase 1G-06 pushed | `311221e0d` |
| Phase 1G-07 pushed (GO) | `6f9176953` |
| Phase 1G-08 pushed (Pilot preparation) | `9812c069e` |

---

## 3. Baselines Re-Confirmation

| Baseline | State at Phase 1G-09 start |
|----------|----------------------------|
| Phase 1G-04 WebUI mainline | **SEALED** (`94f22f67b`) |
| Phase 1G-05 readiness | **pushed** (`da5c31a8c`) |
| Phase 1G-06 release rehearsal | **pushed** (`311221e0d`) |
| Phase 1G-07 RC dry run | **pushed, GO** (`6f9176953`, `RC-1G-07-001`) |
| Phase 1G-08 Pilot preparation | **pushed** (`9812c069e`, `PILOT-1G-08-001`) |

Git baseline at execution:

| Item | Value |
|------|-------|
| Branch | `dev-huangruibang` |
| Local HEAD | `9812c069ee4370babdb8599efd67ac4cb12ce148` |
| Remote HEAD | `9812c069ee4370babdb8599efd67ac4cb12ce148` |
| Merge base | `9812c069ee4370babdb8599efd67ac4cb12ce148` |
| ahead / behind | `0 / 0` |
| Tracked worktree | clean |
| Untracked | `.claude/` only |

---

## 4. Route Governance (unchanged)

| Metric | Value |
|--------|-------|
| OpenAPI paths | **34** |
| Runtime routes | **34** |
| Tool GET routes | **5** |
| Tool write routes | **0** |
| Tool dry-run routes | **1** |
| Tool execution routes | **1** |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` |

Phase 1G-09 changes **nothing** about route governance or the allowlist. Both
are re-verified by `tests/test_dev_check_webui.py`,
`tests/test_dev_web_0c06_closure.py`, and
`./scripts/run-dev-hermes.sh dev-check`.

---

## 5. Pilot Execution Objective

Execute `PILOT-1G-08-001` (Pilot Execution ID `PILOT-EXEC-1G-09-001`) against
the sealed Phase 1G-04 mainline on the development instance, so that the Pilot
record captures:

1. the 15 scenario results (A–O) under the two server-gate profiles;
2. the evidence index (text summaries only — no raw logs / screenshots /
   audit JSONL committed);
3. the defect / feedback log (none introduced by Phase 1G-09; the 8 carried-over
   P2 items remain);
4. the Pilot final decision (PASS / NO-GO / PAUSED) against the Phase 1G-08 exit
   criteria.

The Pilot runs **only** against the development instance:

- Dev `HERMES_HOME`: `/Users/huangruibang/Code/hermes-home-dev`
- Dev API bind: `127.0.0.1:5181` (isolated)
- WebUI bind: `127.0.0.1:5180` (isolated)
- Production `~/.hermes`: **never accessed**
- Production `state.db`: **never accessed**
- Production Gateway PID `69355`: **never affected**

---

## 6. Pilot Execution Scope

Phase 1G-09 executes:

1. Git + environment + production baseline checks.
2. `memory-check` / `dev-check`.
3. Route governance + related backend regression (19 files).
4. compileall / `py_compile toolsets.py` / ruff.
5. Backend blocked profile (Scenario E) and completed profile (Scenario F).
6. Browser smoke (both profiles) via the committed harness
   `scripts/run-dev-webui-execute-audit-smoke.sh all`.
7. Frontend type-check / lint / unit / build.
8. Scenario-by-scenario capture (A–O) against the acceptance record template.
9. Final port + production PID re-verification.
10. Boundary verification (no forbidden file / secret / token / tokenHash /
    raw-arguments exposure).
11. Pilot final decision + acceptance record sign-off.

---

## 7. Out of Scope

Phase 1G-09 does **not**:

- reopen Phase 1G-04, Phase 1G-05, Phase 1G-06, Phase 1G-07, or Phase 1G-08;
- add any WebUI product capability;
- modify any backend or frontend functional code;
- add a backend route, a Tool write route, a second Tool execution route, or a
  Provider route;
- enable any non-clarify execution;
- expand `STATIC_ALLOWLIST` beyond `frozenset({"clarify"})`;
- send a Provider Schema or call a Provider API;
- access production `~/.hermes` or production `state.db` in any form
  (`ls`, `stat`, `find`, `cat`, `sqlite3`, `du`, mtime checks, …);
- stop, restart, replace, or reconfigure the Production Gateway;
- modify the smoke harness script (a P0/P1 finding is reported, not patched,
  in this phase);
- push to the remote;
- start Phase 1G-10.

---

## 8. Participating Roles

| Role | Responsibility | Phase 1G-09 involvement |
|------|----------------|-------------------------|
| Pilot operator | Executes the Pilot against the dev instance; captures evidence; records defects; signs the record. | This phase (Dev Agent acts as operator). |
| Pilot observer | Confirms observed behavior; signs or marks "none". | none (single-operator execution). |
| Dev Agent | Runs the gates, executes the scenarios, captures evidence, creates the local commit. | This phase. |
| Approver (human) | Approves a final PASS and any push. | **Not invoked in Phase 1G-09** (local execution only). A PASS recorded without an approver is a recommendation only. |

---

## 9. Execution Method

The Pilot is executed via the **committed** Phase 1G-06 smoke harness, which
drives the smoke spec
`apps/hermes-dev-webui/tests/smoke/phase-1g-04-30-execute-audit-smoke.spec.ts`
across the two named gate profiles with a fresh server cycle per profile. The
harness refuses production `HERMES_HOME`, refuses to start when the ports are
occupied, binds to `127.0.0.1` only, kills only the PIDs it started, and
self-cleans on exit.

Gate env vars per profile (from the Phase 1G-06 smoke harness runbook):

- **Profile A — blocked:** `HERMES_TOOL_EXECUTION_ENABLED=true`,
  `HERMES_AGENT_TOOLS_ENABLED=true`, handler-call gate unset →
  `blocked_tool_handler_call_not_enabled`.
- **Profile B — completed:** all three gates `=true` →
  `clarify_execution_completed` (canonicalName=`clarify`).
- **Profile C — fully disabled:** all gates unset → `blocked_by_kill_switch`
  (informational / manual only; not a named harness mode).

Provider keys are unset throughout; no real Provider key is exported and no
Provider API is called.

---

## 10. Scenario List (A–O)

| ID | Scenario | Profile(s) | Severity (on fail) |
|----|----------|------------|--------------------|
| A | WebUI loads | A + B | P1 |
| B | Tools panel visible | A + B | P1 |
| C | Tool schema / policy read-only inspection | A + B | P0 / P1 |
| D | clarify dry-run | A + B | P0 / P1 |
| E | blocked profile (`blocked_tool_handler_call_not_enabled`) | A | P0 |
| F | completed profile (`clarify_execution_completed`) | B | P0 / P1 |
| G | audit viewer: dry-run event | A + B | P0 / P1 |
| H | audit viewer: pre-execution event | A + B | P0 / P1 |
| I | audit viewer: post-execution event | B | P0 / P1 |
| J | `providerSchemaSent=false` | A + B | P0 |
| K | `providerApiCalled=false` | A + B | P0 |
| L | no non-clarify execution | A + B | P0 |
| M | route governance unchanged | A + B | P0 / P1 |
| N | Production Gateway PID unaffected | A + B | P0 |
| O | final ports free | A + B | P1 / P0 |

Full objective / preconditions / steps / expected / evidence / pass / fail per
scenario are fixed in `docs/webui/phase-1g-08-pilot-acceptance-pack.md`. Per-run
results are recorded in
`docs/webui/phase-1g-09-pilot-acceptance-record.md`.

---

## 11. Evidence Policy

- Evidence is captured as **text summaries only** (decision strings, provider /
  external flag values, audit-viewer state notes, route-governance summary
  lines, PID before/after, final port state).
- No raw log file, `test-results/`, `playwright-report/`, screenshot, runtime
  JSONL, or audit JSONL is committed. Build / test / smoke artifacts are
  gitignored or self-cleaned by the harness.
- No evidence entry contains a secret, an API key, the raw confirmation token,
  the full token hash, or raw arguments.
- The evidence index is `docs/webui/phase-1g-09-pilot-evidence-index.md`.

---

## 12. Security Boundary

The Pilot keeps all of these invariants true throughout and after the run. Any
violation is a P0 and stops the Pilot:

- `STATIC_ALLOWLIST` is exactly `frozenset({"clarify"})`.
- No non-clarify tool executes or becomes allowlisted.
- `providerSchemaSent=false` and `providerApiCalled=false` everywhere.
- The raw confirmation token never appears in a response, the DOM, a log, the
  console, `localStorage`, `sessionStorage`, or an audit event.
- The full token hash is never surfaced.
- Raw arguments never appear in the audit viewer.
- No secret / API key / credential is logged or committed.
- Production `~/.hermes` and production `state.db` are never accessed.
- No Tool write route, no second execution route, no Provider route appears.
- No audit JSONL or `.claude/` is staged or committed.
- No force push, rebase, or `git reset --hard` is attempted.

---

## 13. Exit Criteria

The Pilot PASS / NO-GO / PAUSED rules are fixed in
`docs/webui/phase-1g-08-pilot-exit-criteria.md`. Summary:

- **PASS:** no P0; no unresolved P1; all required scenarios pass; route
  governance unchanged; `STATIC_ALLOWLIST` unchanged; Production Gateway PID
  `69355` unaffected; no `~/.hermes` / production `state.db` access; no Provider
  Schema / API; no non-clarify execution; evidence complete; record signed off.
- **NO-GO:** any P0; any unresolved P1; route governance changed; allowlist
  expanded; Provider Schema / API called; non-clarify execution; Tool write
  route introduced; production PID changed; `~/.hermes` / production `state.db`
  accessed; critical evidence missing.
- **PAUSED:** an unresolved P1 that is expected to be remediable, or an
  environment issue (port conflict, smoke harness failure) that does not touch a
  P0 boundary.

A Pilot NO-GO does **not** revoke the RC GO by itself and does **not** reopen
Phase 1G-04.

---

## 14. Final Decision Summary

| Field | Value |
|-------|-------|
| Pilot Result | **PASS** (operator-executed; all technical PASS criteria met) |
| P0 count | 0 |
| P1 count | 0 |
| P2 count | 8 (carried over from the Phase 1G-05 risk register; none new) |
| Required scenarios passing | 15 / 15 (A–O) |
| Route governance | unchanged (34 / 34 / 5 / 0 / 1 / 1) |
| `STATIC_ALLOWLIST` | unchanged (`frozenset({"clarify"})`) |
| Production Gateway PID | `69355` before and after |
| Ports `5180` / `5181` | free |
| `~/.hermes` access | none |
| production `state.db` access | none |
| Approver sign-off | pending human sign-off (a PASS without an approver is a recommendation only) |

> **Pilot Result: PASS.** `PILOT-EXEC-1G-09-001` was executed against
> `PILOT-1G-08-001` and `RC-1G-07-001`. No P0 or unresolved P1 was found. The
> current `dev-huangruibang` is eligible for post-Pilot closeout / final release
> decision preparation, subject to human approver sign-off.

The full decision is in `docs/webui/phase-1g-09-pilot-final-decision.md`. The
per-scenario results are in
`docs/webui/phase-1g-09-pilot-acceptance-record.md`.

---

## 15. Non-Reopening Declaration

> **Phase 1G-09 does not reopen Phase 1G-04.**
> **Phase 1G-09 does not add a new product capability.**
> **Phase 1G-09 only executes the prepared Pilot acceptance pack.**

No Phase 1G-04 route, allowlist, execute gate, audit behavior, frontend
capability, or test strength is changed, weakened, or expanded by Phase 1G-09.
The only deliverables are the Pilot execution docs (this doc, the acceptance
record, the evidence index, the defect / feedback log, the final decision), the
implementation plan update, a Phase 1G-09 addendum to the risk register, and the
final re-verification pass.

---

## 16. Cross-References

- Pilot acceptance pack: `docs/webui/phase-1g-08-pilot-acceptance-pack.md`.
- Pilot preparation: `docs/webui/phase-1g-08-pilot-acceptance-preparation.md`.
- Operator guide: `docs/webui/phase-1g-08-pilot-operator-guide.md`.
- Participant guide: `docs/webui/phase-1g-08-pilot-participant-guide.md`.
- Acceptance record template:
  `docs/webui/phase-1g-08-pilot-acceptance-record-template.md`.
- Defect / feedback template:
  `docs/webui/phase-1g-08-pilot-defect-feedback-template.md`.
- Exit criteria: `docs/webui/phase-1g-08-pilot-exit-criteria.md`.
- Smoke harness runbook: `docs/webui/phase-1g-06-smoke-harness-runbook.md`.
- RC Go / No-Go: `docs/webui/phase-1g-07-go-no-go-decision.md`.
- Risk register: `docs/webui/phase-1g-05-risk-register.md`.
- Phase 1G-09 acceptance record:
  `docs/webui/phase-1g-09-pilot-acceptance-record.md`.
- Phase 1G-09 evidence index:
  `docs/webui/phase-1g-09-pilot-evidence-index.md`.
- Phase 1G-09 defect / feedback log:
  `docs/webui/phase-1g-09-pilot-defect-feedback-log.md`.
- Phase 1G-09 final decision:
  `docs/webui/phase-1g-09-pilot-final-decision.md`.

---

*Phase 1G-09 Pilot Acceptance Execution — `PILOT-EXEC-1G-09-001` executed
against Pilot `PILOT-1G-08-001` and RC `RC-1G-07-001` (GO). Phase 1G-04 remains
sealed; Phase 1G-05 remains the pushed readiness baseline; Phase 1G-06 remains
the pushed release rehearsal baseline; Phase 1G-07 remains the pushed GO RC dry
run; Phase 1G-08 remains the pushed Pilot acceptance preparation. Production
Gateway PID `69355` is never affected.*
