# Phase 1G-07: Release Candidate Dry Run

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-07 |
| Title | Release Candidate Dry Run |
| Status | Pushed (RC dry run baseline, `6f9176953`) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| RC ID | `RC-1G-07-001` |
| Base commit | `311221e0dd7c583dcd6c07f3bcef7f304bd669e0` (Phase 1G-06 pushed release rehearsal baseline) |
| Scope | A formal Release Candidate dry run against `dev-huangruibang`. No code feature, no route, no allowlist change. |
| Author | Dev Agent (Phase 1G-07 RC dry run) |

---

## 1. Phase Definition

Phase 1G-07 is an **independent release-candidate dry-run phase** that runs
*after* the Phase 1G-06 Pilot Release Rehearsal baseline was pushed at
`311221e0d`.

Phase 1G-07 does **not** reopen Phase 1G-04. It does **not** introduce any new
product capability. It validates release-candidate readiness only:

1. Define the RC ID (`RC-1G-07-001`).
2. Re-confirm the Phase 1G-04 sealed baseline.
3. Re-confirm the Phase 1G-05 pushed readiness baseline.
4. Re-confirm the Phase 1G-06 pushed release rehearsal baseline.
5. Run the committed smoke harness across the blocked + completed profiles.
6. Run the backend regression.
7. Run the frontend type-check / lint / unit / build.
8. Run `memory-check` / `dev-check`.
9. Re-verify route governance is unchanged.
10. Re-verify `STATIC_ALLOWLIST` is unchanged.
11. Re-verify the Production Gateway PID `69355` is unchanged.
12. Produce an RC validation report.
13. Produce a Go / No-Go decision.
14. Update the implementation plan.
15. Create a single local commit.
16. Do **not** push.
17. Do **not** start Phase 1G-08.

> **Hard separation:** Phase 1G-04 is sealed. Phase 1G-05 is the pushed
> readiness baseline. Phase 1G-06 is the pushed release rehearsal baseline.
> Phase 1G-07 adds **no** functionality. It is a read-only validation pass that
> decides whether the current branch is eligible to enter Pilot acceptance.

---

## 2. RC ID

| Field | Value |
|-------|-------|
| RC ID | `RC-1G-07-001` |
| Chosen because | No prior `RC-1G-07-*` document or reference exists. |
| Recorded consistently in | this doc, the RC validation report, the Go / No-Go decision, and the implementation plan update. |

---

## 3. Baselines

### 3.1 Phase 1G-04 sealed baseline

| Item | Value |
|------|-------|
| Phase 1G-04 status | **SEALED** |
| Sealing commit | `docs(webui): seal phase 1g-04` → `94f22f67b` |
| Full chain | dry-run historical lookup → confirmation token → digest verification → pre-execution audit → handler lookup → dispatch planning → clarify-only handler call → post-execution audit → read-only audit events API → frontend Execute UI → audit viewer → browser smoke / E2E |

### 3.2 Phase 1G-05 readiness baseline

| Item | Value |
|------|-------|
| Phase 1G-05 status | **Pushed readiness baseline** |
| Push commit | `docs(webui): add phase 1g-05 readiness baseline` → `da5c31a8c` |
| Deliverables | post-sealing readiness, pilot acceptance baseline, release checklist, ops / rollback runbook, risk register |

### 3.3 Phase 1G-06 release rehearsal baseline

| Item | Value |
|------|-------|
| Phase 1G-06 status | **Pushed release rehearsal baseline** |
| Push commit | `chore(webui): add pilot release rehearsal baseline` → `311221e0d` |
| Deliverables | pilot release rehearsal, smoke harness runbook, release-candidate validation, go / no-go template, committed dev-only smoke harness |

### 3.4 Current HEAD at Phase 1G-07 start

| Item | Value |
|------|-------|
| Local HEAD | `311221e0dd7c583dcd6c07f3bcef7f304bd669e0` |
| Remote HEAD | `311221e0dd7c583dcd6c07f3bcef7f304bd669e0` |
| Merge base | `311221e0dd7c583dcd6c07f3bcef7f304bd669e0` |
| ahead / behind | `0 / 0` |
| Tracked worktree | clean |
| Untracked | `.claude/` only |
| Dev `HERMES_HOME` | `/Users/huangruibang/Code/hermes-home-dev` |
| Production Gateway PID | `69355` |

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

Phase 1G-07 changes **nothing** about route governance or the allowlist. Both
are re-verified by `tests/test_dev_check_webui.py`,
`tests/test_dev_web_0c06_closure.py`, and `./scripts/run-dev-hermes.sh dev-check`.

---

## 5. RC Dry Run Goal

Decide whether the current `dev-huangruibang` branch is eligible to enter Pilot
acceptance, by re-running the full release gate sequence through the committed
rehearsal harness and recording the observed results:

- Anyone reproducing this RC dry run gets the identical gate results via the
  committed smoke harness (`scripts/run-dev-webui-execute-audit-smoke.sh`).
- The RC decision is recorded against the fixed go / no-go template from
  Phase 1G-06.

The dry run does **not** execute a real Pilot against production. It runs only
against the development instance:

- Dev `HERMES_HOME`: `/Users/huangruibang/Code/hermes-home-dev`
- Dev API bind: `127.0.0.1:5181`
- WebUI bind: `127.0.0.1:5180`
- Production `~/.hermes`: **never accessed**
- Production `state.db`: **never accessed**
- Production Gateway PID `69355`: **never affected**

---

## 6. RC Validation Scope

This RC dry run re-verifies, against the current branch:

1. Git baseline (branch, HEAD, remote sync, clean worktree).
2. Route governance (OpenAPI / runtime / tool GET / write / dry-run / execution / allowlist).
3. Backend regression (route governance + 18 related backend files).
4. Compile / `py_compile toolsets.py` / `ruff`.
5. Frontend type-check / lint / unit / build.
6. Browser smoke — blocked profile (A).
7. Browser smoke — completed profile (B).
8. `memory-check`.
9. `dev-check`.
10. Production Gateway PID `69355` unaffected.
11. Final port status (`5180` / `5181` free).
12. Forbidden-file / secret / token-exposure boundary.

---

## 7. Explicit Non-Goals

Phase 1G-07 does **not**:

- reopen Phase 1G-04, Phase 1G-05, or Phase 1G-06;
- add any WebUI product capability;
- add a backend route, a Tool write route, a second Tool execution route, or a
  Provider route;
- enable any non-clarify execution;
- expand `STATIC_ALLOWLIST` beyond `frozenset({"clarify"})`;
- send a Provider Schema or call a Provider API;
- access production `~/.hermes` or production `state.db` in any form
  (`ls`, `stat`, `find`, `cat`, `sqlite3`, `du`, mtime checks, …);
- stop, restart, replace, or reconfigure the Production Gateway;
- push to the remote;
- start Phase 1G-08.

---

## 8. Smoke Profiles

The execute route's behavior is determined by the gate env vars the Dev API
process inherits at startup. `EXECUTE_EXPECTED` tells the Playwright smoke spec
which decision string to assert. (See
`docs/webui/phase-1g-06-smoke-harness-runbook.md` for the exact env vars.)

### 8.1 Profile A — `blocked_tool_handler_call_not_enabled`

Upstream execution gates on, handler-call gate **unset** → blocks right before
the handler call.

### 8.2 Profile B — `clarify_execution_completed`

All three gates `=true` (incl. handler-call) with `canonicalName=clarify` → the
bounded clarify handler is invoked and a post-execution audit is written.

### 8.3 Profile C — fully disabled (documented only)

All gates unset (shipping default) → `blocked_by_kill_switch`. Profile C is an
optional safety supplement; it is not a harness mode (the smoke spec asserts one
of the two Profile A / B decision strings) and is not run by this RC dry run.

---

## 9. Backend Validation

| Gate | Expected | Command |
|------|----------|---------|
| Route governance | 124 passed / 5 deselected / 0 failed | `./scripts/run_tests.sh tests/test_dev_check_webui.py tests/test_dev_web_0c06_closure.py -- -q` |
| Related backend regression | 1471 passed / 2 skipped / 0 failed | `./scripts/run_tests.sh <18 related files> -- -q` |
| `compileall` (14 modules) | exit 0 | `python -m compileall <14 dev_web modules>` |
| `py_compile toolsets.py` | OK | `python -m py_compile toolsets.py` |
| `ruff check` (14 files) | all checks passed | `ruff check <14 files>` |

Observed results are recorded in
`docs/webui/phase-1g-07-rc-validation-report.md`.

---

## 10. Frontend Validation

| Gate | Expected | Command |
|------|----------|---------|
| `pnpm type-check` | pass | `pnpm type-check` |
| `pnpm lint` | 0 errors / 0 warnings | `pnpm lint` |
| `pnpm test` | 674 passed (31 files) / 0 failed | `pnpm test` |
| `pnpm build` | pass | `pnpm build` |

Observed results are recorded in
`docs/webui/phase-1g-07-rc-validation-report.md`.

---

## 11. Production Isolation Validation

| Check | Expected |
|-------|----------|
| Production Gateway PID | `69355` before and after (unchanged) |
| Production gateway process count | exactly 1 |
| Production Gateway stopped / restarted / replaced | no |
| Dev Gateway | stopped |
| Dashboard | not started |
| `5180` / `5181` | free throughout and after |
| Production `~/.hermes` accessed | no (no `ls` / `stat` / `find` / `cat` / `sqlite3` / `du` / mtime) |
| Production `state.db` accessed | no |

> **Historical note (carried from Phase 1G-06):** from Phase 1G-07 onward, any
> form of `~/.hermes` access is forbidden — including `ls`, `stat`, `find`,
> `cat`, `sqlite3`, `du`, and mtime checks. Production-untouched is established
> only via the Production Gateway PID, the dev `HERMES_HOME` isolation, the port
> state, the git diff scope, and the runtime safety gates.

---

## 12. Security Boundary Validation

The RC dry run asserts that none of the following occurred:

- `STATIC_ALLOWLIST` changed or was expanded beyond `clarify`;
- a non-clarify tool executed or became allowlisted;
- `providerSchemaSent=true` or `providerApiCalled=true` appeared anywhere;
- the raw confirmation token appeared in a response, the DOM, a log, the
  console, `localStorage`, `sessionStorage`, or an audit event;
- the full token hash was surfaced;
- raw arguments appeared in the audit viewer;
- a secret / API key / credential was logged or committed;
- the production `~/.hermes` or production `state.db` was accessed or modified;
- a Tool write route, a second execution route, or a Provider route appeared;
- audit JSONL or `.claude/` was staged or committed;
- any force push, rebase, or `git reset --hard` was attempted.

---

## 13. Go / No-Go Criteria

**GO requires** (all of):

1. no P0;
2. no P1;
3. backend regression passed;
4. frontend type-check / lint / unit / build passed;
5. browser smoke blocked profile (A) passed;
6. browser smoke completed profile (B) passed;
7. route governance unchanged (34 / 34 / 5 / 0 / 1 / 1);
8. `STATIC_ALLOWLIST` unchanged (`frozenset({"clarify"})`);
9. no Provider Schema;
10. no Provider API;
11. no non-clarify execution;
12. no Tool write route;
13. no new backend route;
14. Production Gateway PID `69355` unchanged;
15. no `~/.hermes` access;
16. no production `state.db` access;
17. no runtime artifacts committed;
18. `.claude/` not committed.

**NO-GO on:** any P0, any P1, backend regression failure, frontend build
failure, smoke failure, route governance change, allowlist change, production
PID change, or any provider-boundary / production-access violation.

On a NO-GO: do **not** push; do **not** reopen Phase 1G-04; do **not** start
Phase 1G-08; record the finding and address it via a separately approved phase.

---

## 14. Exit Criteria

Phase 1G-07 is complete when **all** hold:

1. The RC ID is defined (`RC-1G-07-001`).
2. The RC dry run doc, the RC validation report, and the Go / No-Go decision
   exist.
3. The implementation plan references Phase 1G-07.
4. Route governance and `STATIC_ALLOWLIST` are unchanged.
5. All required gates pass with 0 failures.
6. Production Gateway PID `69355` is unchanged; ports `5180` / `5181` are free.
7. No forbidden file is touched; no audit JSONL / `.claude/` is committed.
8. A single local commit is created and **not** pushed.
9. Phase 1G-08 is **not** started.

---

## 15. Next Phase Options

Phase 1G-07 does not start any follow-on phase. Candidate follow-on work (each
must be separately approved):

- **Pilot execution** — run the Pilot acceptance baseline
  (`docs/webui/phase-1g-05-pilot-acceptance-baseline.md`) against the sealed
  mainline, driven by the committed rehearsal harness, now that this RC is GO.
- **Polish (optional, P2)** — frontend visual polish / accessibility pass.
- **Audit hardening (optional, P2)** — JSONL rotation, cursor pagination, audit
  search / indexing.
- **Phase 1G-08** — explicitly **not started** by this phase. Its scope, if any,
  must be defined and approved separately.

---

## 16. Non-Reopening Declaration

> **Phase 1G-07 does not reopen Phase 1G-04.**
> **Phase 1G-07 does not add a new product capability.**
> **Phase 1G-07 only validates release-candidate readiness.**

No Phase 1G-04 route, allowlist, execute gate, audit behavior, frontend
capability, or test strength is changed, weakened, or expanded by Phase 1G-07.
The only deliverables are the RC dry run docs (this doc, the validation report,
the Go / No-Go decision), the implementation plan update, the risk register
addendum, and the final re-verification pass.

---

## 17. Phase 1G-08 Addendum — Pilot Acceptance Preparation

Phase 1G-08 (Pilot Acceptance Preparation, Pilot `PILOT-1G-08-001`) ran *after*
this RC dry run was pushed at `6f9176953`. It converts the `RC-1G-07-001` GO
decision into an executable Pilot acceptance pack.

- **No new P0. No new P1.** Phase 1G-08 added no product capability and no route
  governance change.
- Phase 1G-04 remains **SEALED**; Phase 1G-05 remains the **pushed** readiness
  baseline; Phase 1G-06 remains the **pushed** release rehearsal baseline;
  Phase 1G-07 remains the **pushed** GO RC dry run. `RC-1G-07-001` remains the GO
  RC; no supplemental RC was produced.
- Route governance and `STATIC_ALLOWLIST` remain unchanged (34 / 34 / 5 / 0 / 1
  / 1; `frozenset({"clarify"})`).
- The Pilot pack, guides, templates, and exit criteria live under
  `docs/webui/phase-1g-08-*.md`; the implementation plan records Phase 1G-08.
- Pilot execution is **separately approved**; Phase 1G-08 only prepares the pack.
  Phase 1G-09 is explicitly **not started**.

---

*Phase 1G-07 Release Candidate Dry Run — RC `RC-1G-07-001`. Phase 1G-04 remains
sealed; Phase 1G-05 remains the pushed readiness baseline; Phase 1G-06 remains
the pushed release rehearsal baseline.*
