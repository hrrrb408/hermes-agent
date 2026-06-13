# Phase 1G-08: Pilot Acceptance Preparation

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-08 |
| Title | Pilot Acceptance Preparation |
| Status | Prepared locally (Pilot execution pending explicit approval) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Related Release Candidate | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Baseline HEAD | `6f9176953cec7676d668aa3b4b7a654a374834de` |
| Scope | Convert the RC-1G-07-001 GO decision into an executable Pilot acceptance preparation pack. No code feature, no route, no allowlist change. |
| Author | Dev Agent (Phase 1G-08 pilot acceptance preparation) |

---

## 1. Phase Definition

Phase 1G-08 is an **independent Pilot-acceptance preparation phase** that runs
*after* the Phase 1G-07 Release Candidate Dry Run (`RC-1G-07-001`, **GO**) was
pushed at `6f9176953`.

Phase 1G-08 does **not** reopen Phase 1G-04. It does **not** introduce any new
product capability. It converts the RC GO conclusion into a ready-to-run Pilot
acceptance package:

1. Define the Pilot Acceptance ID (`PILOT-1G-08-001`).
2. Re-confirm the Phase 1G-04 sealed baseline (`94f22f67b`).
3. Re-confirm the Phase 1G-05 pushed readiness baseline (`da5c31a8c`).
4. Re-confirm the Phase 1G-06 pushed release rehearsal baseline (`311221e0d`).
5. Re-confirm the Phase 1G-07 pushed RC GO dry-run baseline (`6f9176953`).
6. Author the Pilot Acceptance Pack (scenarios A–O, evidence, pass/fail).
7. Author the Pilot Operator Guide (commands, checklists, escalation).
8. Author the Pilot Participant Guide (non-technical instructions).
9. Author the Pilot Acceptance Record Template (copy-fill record).
10. Author the Pilot Defect / Feedback Template (severity + categories).
11. Author the Pilot Exit Criteria (PASS / NO-GO / PAUSED).
12. Update the implementation plan with the Phase 1G-08 record.
13. Run the final backend / frontend / smoke / memory / dev / production gates.
14. Confirm route governance and `STATIC_ALLOWLIST` are unchanged.
15. Confirm the Production Gateway PID `69355` is unchanged.
16. Create a single local commit.
17. Do **not** push.
18. Do **not** start Phase 1G-09.

> **Hard separation:** Phase 1G-04 is sealed. Phase 1G-05 is the pushed
> readiness baseline. Phase 1G-06 is the pushed release rehearsal baseline.
> Phase 1G-07 is the pushed GO RC dry run. Phase 1G-08 adds **no**
> functionality. It prepares Pilot acceptance execution only.

---

## 2. Pilot Acceptance ID

| Field | Value |
|-------|-------|
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Related Release Candidate | `RC-1G-07-001` |
| Baseline HEAD | `6f9176953cec7676d668aa3b4b7a654a374834de` |
| Chosen because | No prior `PILOT-1G-08-*` document or reference exists. |
| Recorded consistently in | this doc, the acceptance pack, the operator guide, the participant guide, the acceptance record template, the defect / feedback template, the exit criteria, and the implementation plan update. |

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

### 3.4 Phase 1G-07 RC GO baseline

| Item | Value |
|------|-------|
| Phase 1G-07 status | **Pushed GO RC dry run** |
| Push commit | `docs(webui): add phase 1g-07 rc dry run` → `6f9176953` |
| RC ID | `RC-1G-07-001` |
| Decision | **GO** |
| Deliverables | RC dry run, RC validation report, Go / No-Go decision (`RC-1G-07-001` GO) |

### 3.5 Current HEAD at Phase 1G-08 start

| Item | Value |
|------|-------|
| Local HEAD | `6f9176953cec7676d668aa3b4b7a654a374834de` |
| Remote HEAD | `6f9176953cec7676d668aa3b4b7a654a374834de` |
| Merge base | `6f9176953cec7676d668aa3b4b7a654a374834de` |
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

Phase 1G-08 changes **nothing** about route governance or the allowlist. Both
are re-verified by `tests/test_dev_check_webui.py`,
`tests/test_dev_web_0c06_closure.py`, and `./scripts/run-dev-hermes.sh dev-check`.

---

## 5. Pilot Preparation Goal

Take the Phase 1G-07 GO decision and turn it into a self-contained, ready-to-run
Pilot acceptance package, so that a Pilot operator or participant can execute the
Pilot against the sealed Phase 1G-04 mainline on the Phase 1G-05 / 1G-06 / 1G-07
baselines with:

- a fixed Pilot ID and a fixed RC ID;
- a fixed scenario list (A–O) with explicit pass / fail criteria;
- a fixed evidence-capture list;
- a fixed defect / feedback severity scheme;
- a fixed PASS / NO-GO / PAUSED exit rule.

The Pilot is **prepared** in Phase 1G-08 but **not executed** in Phase 1G-08.
Pilot execution itself is a separately approved follow-on activity.

The Pilot runs **only** against the development instance:

- Dev `HERMES_HOME`: `/Users/huangruibang/Code/hermes-home-dev`
- Dev API bind: `127.0.0.1:5181` (isolated)
- WebUI bind: `127.0.0.1:5180` (isolated)
- Production `~/.hermes`: **never accessed**
- Production `state.db`: **never accessed**
- Production Gateway PID `69355`: **never affected**

---

## 6. Pilot Acceptance Scope

Phase 1G-08 prepares the Pilot to validate, against the sealed mainline:

1. Pilot Acceptance ID creation (`PILOT-1G-08-001`).
2. Pilot Acceptance Pack authoring.
3. Pilot Operator Guide authoring.
4. Pilot Participant Guide authoring.
5. Pilot Acceptance Record Template authoring.
6. Pilot Defect / Feedback Template authoring.
7. Pilot Exit Criteria authoring.
8. Implementation plan update.
9. Final gate re-verification (backend, frontend, smoke, memory, dev, production).
10. Route governance and `STATIC_ALLOWLIST` invariance re-confirmation.
11. Production Gateway PID `69355` invariance re-confirmation.

The Pilot acceptance scenarios themselves (when the Pilot is later executed)
cover:

- WebUI load and theme rendering.
- Tools panel, schema / policy read-only inspection.
- clarify dry-run (safe decision, no raw token).
- Blocked execution profile (`blocked_tool_handler_call_not_enabled`).
- Completed execution profile (`clarify_execution_completed`).
- Audit viewer (dry-run / pre-execution / post-execution).
- Provider invariants (`providerSchemaSent=false`, `providerApiCalled=false`).
- Non-clarify rejection.
- Route governance stability.
- Production Gateway PID `69355` invariance.
- Final port state (`5180` / `5181` free).

The full scenario list is fixed in
`docs/webui/phase-1g-08-pilot-acceptance-pack.md`.

---

## 7. Explicit Non-Goals

Phase 1G-08 does **not**:

- reopen Phase 1G-04, Phase 1G-05, Phase 1G-06, or Phase 1G-07;
- execute the Pilot (it only prepares the pack);
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
- start Phase 1G-09.

> **Phase 1G-08 does not reopen Phase 1G-04.**
> **Phase 1G-08 does not add a new product capability.**
> **Phase 1G-08 prepares Pilot acceptance execution.**

---

## 8. Participating Roles

| Role | Responsibility | Phase 1G-08 involvement |
|------|----------------|-------------------------|
| Pilot owner | Owns the Pilot ID, the acceptance pack, and the final Pilot record. | Authors the pack; signs the readiness declaration. |
| Pilot operator | Executes the Pilot against the dev instance; captures evidence; records defects. | Uses the Operator Guide. (Pilot execution is not Phase 1G-08.) |
| Pilot participant / observer | Observes the WebUI; records non-blocking feedback; reports blockers. | Uses the Participant Guide. (Pilot execution is not Phase 1G-08.) |
| Dev Agent | Prepares the pack, runs the gates, creates the local commit. | This phase. |
| Approver | Approves Pilot execution and any push. | Not invoked in Phase 1G-08 (local prep only). |

---

## 9. Pilot Acceptance Process

1. **Prepare** (Phase 1G-08) — author the pack, guides, templates, and exit
   criteria; re-verify the baseline gates.
2. **Approve** (separately) — a human approver approves Pilot execution against
   the sealed mainline.
3. **Execute** (separately) — the operator runs scenarios A–O in the two server-gate
   configurations (blocked + completed) and fills the acceptance record.
4. **Record** (separately) — the operator captures evidence per scenario, logs
   defects against the defect template, and records a PASS / NO-GO / PAUSED
   outcome against the exit criteria.
5. **Decide** (separately) — the approver signs the Pilot record. A Pilot NO-GO
   does **not** reopen Phase 1G-04; it is reported as a Pilot finding and
   addressed via a separately approved phase.

---

## 10. Pilot Preconditions

Before Pilot execution, all of the following must hold (they are re-verified in
Phase 1G-08 and recorded in the Operator Guide):

1. Branch `dev-huangruibang`, HEAD = `6f9176953…`, local == remote, ahead/behind
   `0 / 0`, tracked worktree clean, only `.claude/` untracked.
2. Route governance = 34 / 34 / 5 / 0 / 1 / 1.
3. `STATIC_ALLOWLIST = frozenset({"clarify"})`.
4. Production Gateway PID = `69355` (exactly one production gateway process).
5. Dev Gateway stopped; Dashboard not started; `5180` / `5181` free.
6. Dev `HERMES_HOME = /Users/huangruibang/Code/hermes-home-dev`.
7. No Provider keys in env; all execute gates unset by default.
8. The committed smoke harness (`scripts/run-dev-webui-execute-audit-smoke.sh`)
   is available and self-cleaning.

---

## 11. Pilot Execution Order

The Pilot is executed in this order when approved (recorded for the Operator
Guide; **not** performed in Phase 1G-08):

1. Git + environment + production baseline checks.
2. `memory-check` / `dev-check`.
3. Route governance + backend regression.
4. Backend blocked profile (Scenario E).
5. Backend completed profile (Scenario F).
6. Browser smoke (both profiles) via the committed harness.
7. Frontend type-check / lint / unit / build.
8. Scenario-by-scenario capture (A–O).
9. Final port + production PID re-verification.
10. Boundary verification (no forbidden file / secret / token exposure).
11. Acceptance record sign-off.

---

## 12. Pilot Recording Method

The Pilot is recorded via:

- `docs/webui/phase-1g-08-pilot-acceptance-record-template.md` — one record per
  Pilot run (Pilot ID, RC ID, branch, HEAD, environment, per-scenario status,
  evidence, defects, decision, sign-off).
- `docs/webui/phase-1g-08-pilot-defect-feedback-template.md` — one record per
  defect / feedback item.

A completed Pilot record and its defect records together form the Pilot
acceptance dossier. They are stored under `docs/webui/` and version-controlled
the same way as the other phase docs (local commit first; push only on explicit
approval).

---

## 13. Pilot Defect / Feedback Method

Findings observed during Pilot execution are recorded against the defect /
feedback template:

- **P0** (security / production / data / route governance / allowlist violation)
  → stop the Pilot immediately.
- **P1** (Pilot blocker / core flow failure) → the Pilot cannot pass; record and
  remediate.
- **P2** (non-blocking limitation / documentation / polish) → record against the
  risk register; do not block.

Feedback is also categorized (UX, documentation, operational, smoke harness,
audit viewer, execution flow, security concern, other) for triage.

---

## 14. Pilot Pause / Rollback Criteria

| Trigger | Action |
|---------|--------|
| Any P0 boundary violation | **Stop the Pilot immediately.** Do not proceed. Preserve evidence. Do **not** reopen Phase 1G-04. Report and remediate via a separately approved phase. |
| Any unresolved P1 | **Pause the Pilot.** The Pilot cannot be marked PASS until the P1 is resolved or formally waived. |
| Production Gateway PID `69355` changes | **Stop.** Treat as a P0. Do not modify the gateway. Report and investigate. |
| `~/.hermes` or production `state.db` accessed | **Stop.** Treat as a P0. Report immediately. |
| Rollback needed | **Stop and request user confirmation.** Use a new `git revert` commit. Never `git reset --hard`, never force push, never production state mutation. See `docs/webui/phase-1g-05-ops-and-rollback-runbook.md`. |

---

## 15. Pilot Exit Criteria

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

---

## 16. Next-Phase Recommendation

Phase 1G-08 does not start any follow-on phase. Candidate follow-on work (each
must be separately approved):

- **Pilot execution** — run `PILOT-1G-08-001` against the sealed mainline,
  driven by the committed rehearsal harness, now that `RC-1G-07-001` is GO and
  the acceptance pack is prepared.
- **Polish (optional, P2)** — frontend visual polish / accessibility pass.
- **Audit hardening (optional, P2)** — JSONL rotation, cursor pagination, audit
  search / indexing.
- **Phase 1G-09** — explicitly **not started** by this phase. Its scope, if any,
  must be defined and approved separately.

---

## 17. Non-Reopening Declaration

> **Phase 1G-08 does not reopen Phase 1G-04.**
> **Phase 1G-08 does not add a new product capability.**
> **Phase 1G-08 only prepares Pilot acceptance execution.**

No Phase 1G-04 route, allowlist, execute gate, audit behavior, frontend
capability, or test strength is changed, weakened, or expanded by Phase 1G-08.
The only deliverables are the Pilot acceptance preparation docs (this doc, the
acceptance pack, the operator guide, the participant guide, the acceptance record
template, the defect / feedback template, the exit criteria), the implementation
plan update, cross-references to the Phase 1G-05 / 1G-07 docs, and the final
re-verification pass.

---

## 18. Cross-References

- Sealed baseline & boundaries:
  `docs/webui/phase-1g-04-final-acceptance-report.md`,
  `docs/webui/phase-1g-04-31-final-webui-sealing.md`.
- Readiness baseline:
  `docs/webui/phase-1g-05-post-sealing-readiness.md`.
- Pilot acceptance baseline (scenarios, severities):
  `docs/webui/phase-1g-05-pilot-acceptance-baseline.md`.
- Release checklist / ops runbook / risk register:
  `docs/webui/phase-1g-05-release-checklist.md`,
  `docs/webui/phase-1g-05-ops-and-rollback-runbook.md`,
  `docs/webui/phase-1g-05-risk-register.md`.
- Release rehearsal + smoke harness:
  `docs/webui/phase-1g-06-pilot-release-rehearsal.md`,
  `docs/webui/phase-1g-06-smoke-harness-runbook.md`.
- RC dry run + RC validation + Go / No-Go:
  `docs/webui/phase-1g-07-release-candidate-dry-run.md`,
  `docs/webui/phase-1g-07-rc-validation-report.md`,
  `docs/webui/phase-1g-07-go-no-go-decision.md`.
- Phase 1G-08 deliverables:
  `docs/webui/phase-1g-08-pilot-acceptance-pack.md`,
  `docs/webui/phase-1g-08-pilot-operator-guide.md`,
  `docs/webui/phase-1g-08-pilot-participant-guide.md`,
  `docs/webui/phase-1g-08-pilot-acceptance-record-template.md`,
  `docs/webui/phase-1g-08-pilot-defect-feedback-template.md`,
  `docs/webui/phase-1g-08-pilot-exit-criteria.md`.

---

*Phase 1G-08 Pilot Acceptance Preparation — Pilot `PILOT-1G-08-001` prepared
against RC `RC-1G-07-001` (GO). Phase 1G-04 remains sealed; Phase 1G-05 remains
the pushed readiness baseline; Phase 1G-06 remains the pushed release rehearsal
baseline; Phase 1G-07 remains the pushed GO RC dry run.*
