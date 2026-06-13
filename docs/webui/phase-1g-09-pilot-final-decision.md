# Phase 1G-09: Pilot Final Decision — `PILOT-EXEC-1G-09-001`

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-09 |
| Title | Pilot Final Decision |
| Status | Decision recorded |
| Date | 2026-06-14 |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Pilot Execution ID | `PILOT-EXEC-1G-09-001` |
| Related Release Candidate | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Baseline HEAD | `9812c069ee4370babdb8599efd67ac4cb12ce148` |
| Scope | The Pilot PASS / NO-GO / PAUSED outcome for `PILOT-EXEC-1G-09-001`. No code change. |

---

## 1. Decision

| Field | Value |
|-------|-------|
| Decision | **PASS** (operator-executed; all technical PASS criteria met) |
| Date | 2026-06-14 |
| Pilot Result | PASS |

> **Decision: PASS.**
> `PILOT-1G-08-001` has passed Pilot Acceptance Execution
> (`PILOT-EXEC-1G-09-001`).
> The current `dev-huangruibang` is eligible for post-Pilot closeout / final
> release decision preparation, **subject to human approver sign-off**.

---

## 2. PASS Conditions Check

All PASS conditions from `docs/webui/phase-1g-08-pilot-exit-criteria.md` §2 are
met:

| # | PASS condition | Result |
|---|----------------|--------|
| 1 | No P0 in any scenario (A–O) | ✅ 0 P0 |
| 2 | No unresolved P1 in any scenario | ✅ 0 P1 |
| 3 | All required scenarios pass (both gate profiles) | ✅ 15 / 15 (A–O) |
| 4 | Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1) | ✅ unchanged |
| 5 | `STATIC_ALLOWLIST` unchanged (`frozenset({"clarify"})`) | ✅ unchanged |
| 6 | Production Gateway PID `69355` unaffected | ✅ 69355 before/after |
| 7 | No `~/.hermes` access | ✅ none |
| 8 | No production `state.db` access | ✅ none |
| 9 | No Provider Schema sent; no Provider API called | ✅ false on both profiles |
| 10 | No non-clarify execution | ✅ none |
| 11 | Evidence complete for every scenario | ✅ complete |
| 12 | Acceptance record signed off | ⚠️ operator signed; human approver pending |

> Condition 12: the operator has signed the record. A **final** Pilot-accepted
> PASS requires a human approver sign-off. A PASS recorded without an approver
> is a **recommendation only**, not a release authorization. All other PASS
> conditions are fully met at the technical level.

---

## 3. Reason

No P0, no unresolved P1. All 15 required scenarios (A–O) passed under the two
named server-gate profiles (blocked + completed) via the committed smoke
harness. Route governance remains unchanged at OpenAPI 34 / runtime 34 / Tool
GET 5 / Tool write 0 / dry-run 1 / execution 1. `STATIC_ALLOWLIST` remains
`frozenset({"clarify"})`. No Provider Schema was sent, no Provider API was
called, no non-clarify tool executed, and no Tool write / second execution /
Provider route was introduced. The Production Gateway PID `69355` was unchanged
throughout and after the Pilot; ports `5180` / `5181` were free; no production
`~/.hermes` or production `state.db` was accessed; no secret, raw confirmation
token, full tokenHash, or raw arguments were exposed. Evidence is complete for
every scenario; the 8 carried-over P2 items remain accepted and non-blocking.

---

## 4. P0 / P1 / P2

| Severity | Count | Items |
|----------|-------|-------|
| P0 | 0 | — |
| P1 | 0 | — |
| P2 | 8 | Carried over from the Phase 1G-05 risk register (P2-01 … P2-08). All non-blocking; none new; none aggravated by Phase 1G-09. |

---

## 5. Required Scenarios

| Scenario | Name | Status | Profile |
|----------|------|--------|---------|
| A | WebUI loads | PASS | A + B |
| B | Tools panel visible | PASS | A + B |
| C | Tool schema / policy read-only | PASS | A + B |
| D | clarify dry-run | PASS | A + B |
| E | blocked profile | PASS | A |
| F | completed profile | PASS | B |
| G | audit viewer dry-run event | PASS | A + B |
| H | audit viewer pre-execution event | PASS | A + B |
| I | audit viewer post-execution event | PASS | B |
| J | `providerSchemaSent=false` | PASS | A + B |
| K | `providerApiCalled=false` | PASS | A + B |
| L | no non-clarify execution | PASS | A + B |
| M | route governance unchanged | PASS | A + B |
| N | Production Gateway PID unaffected | PASS | A + B |
| O | final ports free | PASS | A + B |

**Required scenarios passing: 15 / 15.**

---

## 6. Route Governance

| Metric | Observed | Expected |
|--------|----------|----------|
| OpenAPI paths | 34 | 34 |
| Runtime routes | 34 | 34 |
| Tool GET routes | 5 | 5 |
| Tool write routes | 0 | 0 |
| Tool dry-run routes | 1 | 1 |
| Tool execution routes | 1 | 1 |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` | `frozenset({"clarify"})` |

**No deviation.**

---

## 7. Security Boundary

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
| Second execution route added | no |
| Provider route added | no |
| Audit JSONL committed | no |
| `.claude/` committed | no |

---

## 8. Production Safety

| Check | Result |
|-------|--------|
| Production Gateway PID before | `69355` |
| Production Gateway PID after | `69355` |
| Production gateway process count | exactly 1 |
| Dev Gateway | stopped |
| Ports `5180` / `5181` | free |
| Production `~/.hermes` accessed | no |
| Production `state.db` accessed | no |

**No production impact.**

---

## 9. Gates Summary

| Gate | Result |
|------|--------|
| Route governance tests | 124 passed / 0 failed |
| Related backend regression (19 files) | 1471 passed / 0 failed |
| compileall (14 modules) | pass (exit 0) |
| `py_compile toolsets.py` | pass |
| ruff (14 files) | all checks passed |
| Frontend type-check | pass (exit 0) |
| Frontend lint | 0 errors / 0 warnings |
| Frontend unit | 674 passed (31 files) |
| Frontend build | 1862 modules (exit 0) |
| Smoke Profile A (blocked) | 6 passed / 1 skipped / 0 failed |
| Smoke Profile B (completed) | 7 passed / 0 failed |
| memory-check | PASS |
| dev-check | WARN (only `.claude/` untracked) |

---

## 10. Approver

| Field | Value |
|-------|-------|
| Operator | Dev Agent (Phase 1G-09 pilot acceptance execution) |
| Observer | none (single-operator execution) |
| Approver (human) | **pending** |

> A real Pilot-accepted PASS requires a human approver sign-off. This Pilot
> execution establishes technical eligibility (all PASS criteria met at the
> technical level); it is **not** a release authorization until a human
> approver signs off.

---

## 11. Eligibility / Next Action

| Field | Value |
|-------|-------|
| Eligible next phase | post-Pilot closeout / final release decision preparation (separately approved) |
| Push? | **no** (Phase 1G-09 = local commit only, no push) |
| Start Phase 1G-10? | **no** (Phase 1G-10 explicitly not started) |
| Reopen Phase 1G-04? | **no** |
| New RC required? | **no** (this is a Pilot PASS, not a code change) |

---

## 12. Rollback Note

- No automatic rollback during this Pilot.
- If rollback is needed: **stop and request user confirmation** first.
- Use a new `git revert` commit — never `git reset --hard`, never force push,
  never production state mutation.
- See `docs/webui/phase-1g-05-ops-and-rollback-runbook.md`.

---

## 13. Emergency Stop Conditions (carry in every Pilot)

Stop immediately and report if any of these occur:

1. `STATIC_ALLOWLIST` is not exactly `frozenset({"clarify"})`.
2. A non-`clarify` tool executes or becomes allowlisted.
3. `providerSchemaSent=true` or `providerApiCalled=true` appears anywhere.
4. The raw confirmation token appears in a response, the DOM, a log, the
   console, `localStorage`, `sessionStorage`, or an audit event.
5. The full token hash is surfaced.
6. Raw arguments appear in the audit viewer.
7. A secret / API key / credential is logged or committed.
8. The production `~/.hermes` or production `state.db` is accessed or modified.
9. Production Gateway PID `69355` changes.
10. A Tool write route, a second execution route, or a Provider route appears.
11. Audit JSONL or `.claude/` is staged or committed.
12. Any force push, rebase, or `git reset --hard` is attempted.

**None of these occurred during `PILOT-EXEC-1G-09-001`.**

---

## 14. Conclusion

Phase 1G-09 Pilot Acceptance Execution completed locally.

`PILOT-EXEC-1G-09-001` was executed against `PILOT-1G-08-001` and
`RC-1G-07-001`.

**Pilot Result: PASS.**

Current `dev-huangruibang` is eligible for post-Pilot closeout / final release
decision preparation, subject to human approver sign-off.

All required Pilot scenarios A–O were executed and recorded. No P0 or unresolved
P1 defects were introduced.

Phase 1G-04 remains sealed, Phase 1G-05 remains the pushed readiness baseline,
Phase 1G-06 remains the pushed release rehearsal baseline, Phase 1G-07 remains
the pushed GO RC dry run, and Phase 1G-08 remains the pushed Pilot acceptance
preparation package. No Phase 1G-04 functionality was reopened or expanded.

Route governance remains unchanged at OpenAPI paths 34, runtime routes 34, Tool
GET 5, Tool write 0, Tool dry-run 1, Tool execution 1, and `STATIC_ALLOWLIST`
remains `frozenset({"clarify"})`.

No Provider Schema sending, Provider API call, non-clarify execution, Tool write
route, new backend route, production home access, production `state.db` access,
audit JSONL commit, `.claude/` commit, raw token leak, full tokenHash leak, raw
arguments leak, secret leak, callable/function repr exposure, or allowlist
expansion was introduced.

No `~/.hermes` access was performed.

All required backend, frontend, smoke, memory-check, dev-check, and production
safety gates passed. Production Gateway PID `69355` was not affected.

A local commit was created. Push was not performed. Phase 1G-10 was not started.

---

## 15. Cross-References

- Pilot acceptance pack: `docs/webui/phase-1g-08-pilot-acceptance-pack.md`.
- Pilot preparation: `docs/webui/phase-1g-08-pilot-acceptance-preparation.md`.
- Exit criteria: `docs/webui/phase-1g-08-pilot-exit-criteria.md`.
- Defect / feedback template:
  `docs/webui/phase-1g-08-pilot-defect-feedback-template.md`.
- Phase 1G-09 execution: `docs/webui/phase-1g-09-pilot-acceptance-execution.md`.
- Phase 1G-09 acceptance record:
  `docs/webui/phase-1g-09-pilot-acceptance-record.md`.
- Phase 1G-09 evidence index: `docs/webui/phase-1g-09-pilot-evidence-index.md`.
- Phase 1G-09 defect / feedback log:
  `docs/webui/phase-1g-09-pilot-defect-feedback-log.md`.
- RC Go / No-Go: `docs/webui/phase-1g-07-go-no-go-decision.md`.
- Risk register: `docs/webui/phase-1g-05-risk-register.md`.

---

## 16. Phase 1G-10 Addendum — Post-Pilot Closeout Completed Locally

Phase 1G-10 (Post-Pilot Closeout / Final Release Decision Preparation) was
performed after this Pilot PASS was pushed. The Pilot decision is **unchanged**:
`PILOT-EXEC-1G-09-001` remains **PASS**.

- Closeout ID: `CLOSEOUT-1G-10-001`; Final Decision Preparation ID:
  `RELEASE-DECISION-PREP-1G-10-001`.
- Phase 1G-10 consolidated this Pilot PASS into a post-Pilot closeout package and
  prepared the final release decision materials. It did **not** authorize a
  release, did **not** push, and did **not** start Phase 1G-11.
- **Human approver sign-off remains pending.** Release authorization is **not
  granted** until the designated human approver signs off.
- Closeout package: `docs/webui/phase-1g-10-post-pilot-closeout.md`,
  `docs/webui/phase-1g-10-final-release-decision-preparation.md`,
  `docs/webui/phase-1g-10-human-approver-signoff-template.md`,
  `docs/webui/phase-1g-10-release-readiness-summary.md`,
  `docs/webui/phase-1g-10-pilot-closeout-report.md`,
  `docs/webui/phase-1g-10-final-go-no-go-draft.md`.
- Production Gateway PID note: the sealed-baseline PID `69355` referenced above
  was accurate through the Phase 1G-09 push. At Phase 1G-10 closeout the host had
  rebooted (`2026-06-14 04:02:09`) and `launchd` respawned the Production Gateway
  as PID `1962` (PPID=1). This is environmental host-reboot drift, not a phase
  action; exactly one healthy Production Gateway is running with the identical
  command.

---

*Phase 1G-09 Pilot Final Decision — `PILOT-EXEC-1G-09-001`: **PASS** (technical
criteria met; human approver sign-off pending). Phase 1G-04 remains sealed;
Phase 1G-05 / 1G-06 / 1G-07 / 1G-08 baselines remain as pushed. Phase 1G-10
post-Pilot closeout was completed locally; release authorization remains pending
human approver sign-off. Phase 1G-11 is not started.*
