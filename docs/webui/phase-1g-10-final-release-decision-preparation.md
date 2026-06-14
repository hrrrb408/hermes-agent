# Phase 1G-10: Final Release Decision Preparation — `RELEASE-DECISION-PREP-1G-10-001`

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-10 |
| Title | Final Release Decision Preparation |
| Status | Prepared locally (not pushed) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Final Decision Preparation ID | `RELEASE-DECISION-PREP-1G-10-001` |
| Closeout ID | `CLOSEOUT-1G-10-001` |
| Related RC ID | `RC-1G-07-001` |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Pilot Execution ID | `PILOT-EXEC-1G-09-001` |
| Baseline HEAD | `cd7298416d82a1dabe22b783bf5656ca8393e6f0` |
| Scope | Assemble the final release decision preparation package for human approver review. No code change. |
| Author | Dev Agent (Phase 1G-10 post-Pilot closeout) |

---

## 1. Decision Preparation Identification

| Field | Value |
|-------|-------|
| Final Decision Preparation ID | `RELEASE-DECISION-PREP-1G-10-001` |
| Closeout ID | `CLOSEOUT-1G-10-001` |
| Baseline HEAD | `cd7298416d82a1dabe22b783bf5656ca8393e6f0` |
| Related RC ID | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Pilot Acceptance ID | `PILOT-1G-08-001` (Phase 1G-08) |
| Pilot Execution ID | `PILOT-EXEC-1G-09-001` (Phase 1G-09, **PASS**) |

This package is **preparation only**. It does not authorize a release and does
not record a final decision. The final GO / NO-GO / PAUSED release decision is
the designated human approver's to make.

---

## 2. Technical Pilot Result

| Field | Value |
|-------|-------|
| Pilot Result | **PASS** (operator-executed; all technical PASS criteria met) |
| P0 count | 0 |
| P1 count | 0 |
| P2 count | 8 carried over + P2-09 (human approver sign-off pending) |
| Required scenarios passing | 15 / 15 (A–O) |
| Route governance | unchanged (34 / 34 / 5 / 0 / 1 / 1) |
| `STATIC_ALLOWLIST` | unchanged (`frozenset({"clarify"})`) |
| Operator sign-off | recorded (Dev Agent, Phase 1G-09) |
| Human approver sign-off | **pending** |

> A PASS recorded without a human approver is a **recommendation only**, not a
> release authorization.

Full Pilot decision: `docs/webui/phase-1g-09-pilot-final-decision.md`.

---

## 3. Required Approver

| Field | Value |
|-------|-------|
| Required approver type | **Human approver** (not the Dev Agent / operator) |
| Approver identity | to be provided by the user outside this task |
| Approver sign-off status | **pending** |
| Approval mechanism | complete the human approver sign-off template (`docs/webui/phase-1g-10-human-approver-signoff-template.md`) |

The Dev Agent and the Pilot operator are **not** authorized to grant release
authorization. Only the designated human approver may convert the technical
PASS recommendation into a final release decision.

---

## 4. Sign-off Status

| Field | Value |
|-------|-------|
| Operator sign-off | recorded (Phase 1G-09 acceptance record) |
| Observer sign-off | n/a (single-operator execution) |
| Human approver sign-off | **pending** |
| Release authorization | **not granted** |

---

## 5. GO Decision Prerequisites

A final **GO** release decision requires **all** of the following to be true at
decision time. Each is verifiable from the committed record:

| # | GO prerequisite | Status |
|---|-----------------|--------|
| 1 | Pilot Result = PASS | ✅ met |
| 2 | 15 / 15 required scenarios PASS (A–O) | ✅ met |
| 3 | no P0 | ✅ met (0 P0) |
| 4 | no unresolved P1 | ✅ met (0 P1) |
| 5 | route governance unchanged (34 / 34 / 5 / 0 / 1 / 1) | ✅ met |
| 6 | `STATIC_ALLOWLIST` unchanged (`frozenset({"clarify"})`) | ✅ met |
| 7 | Production Gateway unaffected (exactly one healthy process running; not stopped / restarted / replaced / reconfigured by release work) | ✅ met |
| 8 | no `~/.hermes` access | ✅ met |
| 9 | no production `state.db` access | ✅ met |
| 10 | no Provider Schema sent; no Provider API called | ✅ met |
| 11 | no non-clarify execution | ✅ met |
| 12 | no Tool write route | ✅ met |
| 13 | no new backend route | ✅ met |
| 14 | no secret / raw token / raw arguments exposure | ✅ met |
| 15 | human approver sign-off completed | ⏳ **pending** |

> Prerequisites 1–14 are met at the technical level. Prerequisite 15 is the
> single remaining gate and is **outside** the Dev Agent's authority. It is the
> release authorization dependency recorded as P2-09.

---

## 6. NO-GO Decision Triggers

A **NO-GO** release decision is required if **any** of the following is true:

| # | NO-GO trigger |
|---|---------------|
| 1 | any P0 |
| 2 | any unresolved P1 |
| 3 | route governance changed |
| 4 | `STATIC_ALLOWLIST` expanded |
| 5 | Provider Schema sent |
| 6 | Provider API called |
| 7 | non-clarify execution occurred |
| 8 | Tool write route introduced |
| 9 | new backend route added |
| 10 | production gateway stopped / restarted / replaced / reconfigured by release work |
| 11 | `~/.hermes` accessed |
| 12 | production `state.db` accessed |
| 13 | critical evidence missing |
| 14 | approver rejects release |

None of these are present. They are listed so the approver has an explicit
checklist to negate.

---

## 7. PAUSED Decision Triggers

A **PAUSED** release decision (defer, do not release yet) is appropriate if any
of the following is true, none of which is a hard P0:

- an unresolved P1 expected to be remediable within a short, bounded window;
- an environment issue (port conflict, smoke harness failure) that does not
  touch a P0 boundary;
- the approver wants additional evidence or a remediation cycle before deciding;
- a non-blocking defect requires a follow-up RC before public rollout.

A PAUSED decision does **not** revoke the RC GO (`RC-1G-07-001`) and does **not**
reopen Phase 1G-04.

---

## 8. Release Scope

If a GO release decision is granted, the release scope is exactly the sealed
Phase 1G-04 WebUI mainline as carried through Phase 1G-05 → 1G-06 → 1G-07 →
1G-08 → 1G-09:

- OpenAPI paths: **34**; runtime routes: **34**.
- Tool GET routes: **5**; Tool write routes: **0**; Tool dry-run routes: **1**;
  Tool execution routes: **1**.
- `STATIC_ALLOWLIST = frozenset({"clarify"})` — only `clarify` is allowlisted.
- Controlled-execution chain: dry-run → confirmation token → digest verification
  → pre-execution audit → handler lookup → dispatch planning → clarify-only
  handler call → post-execution audit → read-only audit events API.
- Dev-only: `HERMES_HOME = /Users/huangruibang/Code/hermes-home-dev`;
  `127.0.0.1` only; production fail-closed.

---

## 9. Release Non-Goals

Even after a GO decision, the release explicitly does **not** include:

- non-clarify tool execution;
- Provider Schema sending;
- Provider API calls;
- Tool write routes;
- a second Tool execution route;
- a Provider route;
- production `~/.hermes` access;
- production `state.db` access;
- public rollout to arbitrary endpoints (the WebUI binds to `127.0.0.1` only).

---

## 10. Safety Boundary

| Boundary | Value |
|----------|-------|
| `STATIC_ALLOWLIST` | exactly `frozenset({"clarify"})` |
| Raw confirmation token | never in response / DOM / log / console / `localStorage` / `sessionStorage` / audit event |
| Full tokenHash | never surfaced |
| Raw arguments | never in the audit viewer |
| Secrets / API keys / credentials | never logged or committed |
| Callable / function repr | never exposed |
| Audit JSONL / `.claude/` | never committed |
| Force push / rebase / `git reset --hard` | never attempted |

---

## 11. Route Governance Boundary

| Metric | Value |
|--------|-------|
| OpenAPI paths | 34 |
| Runtime routes | 34 |
| Tool GET routes | 5 |
| Tool write routes | 0 |
| Tool dry-run routes | 1 |
| Tool execution routes | 1 |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` |

**No deviation.** This boundary is the GO/NO-GO contract.

---

## 12. Production Safety Boundary

| Check | Result |
|-------|--------|
| Production Gateway process count | exactly 1 |
| Production Gateway command | `hermes_cli.main gateway run --replace` (identical) |
| Production Gateway stopped / restarted / replaced / reconfigured by release work | no |
| `~/.hermes` access | no |
| Production `state.db` access | no |
| Dev Gateway | stopped |
| Ports `5180` / `5181` | free |
| Dev `HERMES_HOME` isolation | PASS |

> **Production Gateway PID note.** The sealed baseline PID referenced
> throughout Phase 1G-04 → 1G-09 is `69355`. At Phase 1G-10 closeout time the
> host had rebooted (kernel boot `2026-06-14 04:02:09`) and `launchd` respawned
> the gateway at `04:04:30` as PID `1962` (PPID = 1). PID `69355` no longer
> exists. This is environmental host-reboot drift, not a release-work action.
> The invariant that matters — exactly one healthy production gateway running
> with the identical command — holds.

---

## 13. P0 / P1 / P2 Summary

| Severity | Count | Status |
|----------|-------|--------|
| P0 | 0 | none |
| P1 | 0 | none |
| P2 (carried over) | 8 | accepted, non-blocking (P2-01 … P2-08) |
| P2 (release dependency) | 1 | P2-09 — human approver sign-off pending |

P2-09 is a **release authorization dependency**, not a technical Pilot failure.

---

## 14. Evidence Required Before Approval

The approver should confirm the following evidence is present and consistent
before issuing a final decision:

| # | Evidence | Source |
|---|----------|--------|
| 1 | Pilot Result = PASS | `docs/webui/phase-1g-09-pilot-final-decision.md` |
| 2 | 15 / 15 scenarios A–O | `docs/webui/phase-1g-09-pilot-acceptance-record.md` |
| 3 | Evidence index (text summaries) | `docs/webui/phase-1g-09-pilot-evidence-index.md` |
| 4 | Defect / feedback log (no new P0 / P1 / P2) | `docs/webui/phase-1g-09-pilot-defect-feedback-log.md` |
| 5 | Route governance unchanged | `tests/test_dev_check_webui.py`, `tests/test_dev_web_0c06_closure.py` |
| 6 | `STATIC_ALLOWLIST` unchanged | same |
| 7 | Backend regression (19 files) | `tests/test_dev_web_tool_*.py` |
| 8 | Frontend type-check / lint / unit / build | `apps/hermes-dev-webui` |
| 9 | Browser smoke (both profiles) | `scripts/run-dev-webui-execute-audit-smoke.sh all` |
| 10 | memory-check / dev-check | `./scripts/run-dev-hermes.sh` |
| 11 | Production safety (PID, ports, isolation) | this package §12 |
| 12 | Pilot closeout report | `docs/webui/phase-1g-10-pilot-closeout-report.md` |
| 13 | Release readiness summary | `docs/webui/phase-1g-10-release-readiness-summary.md` |
| 14 | Final GO / NO-GO draft | `docs/webui/phase-1g-10-final-go-no-go-draft.md` |

No raw logs / screenshots / audit JSONL are required (they are deliberately not
committed); text-summary evidence is sufficient.

---

## 15. Final Approver Checklist

- [ ] Reviewed baseline HEAD `cd7298416` against the local and remote branches.
- [ ] Confirmed Pilot Result = PASS and 15 / 15 scenarios A–O.
- [ ] Confirmed 0 P0 and 0 unresolved P1.
- [ ] Confirmed route governance = 34 / 34 / 5 / 0 / 1 / 1.
- [ ] Confirmed `STATIC_ALLOWLIST = frozenset({"clarify"})`.
- [ ] Confirmed exactly one Production Gateway running; not stopped / restarted /
      replaced / reconfigured by release work.
- [ ] Confirmed no `~/.hermes` access and no production `state.db` access.
- [ ] Confirmed no Provider Schema / API, no non-clarify execution, no Tool write
      route, no new backend route.
- [ ] Confirmed no secret / raw token / full tokenHash / raw arguments exposure.
- [ ] Confirmed carried-over P2-01 … P2-08 remain accepted and non-blocking.
- [ ] Reviewed the final GO / NO-GO draft and the human approver sign-off
      template.
- [ ] Issued a final GO / NO-GO / PAUSED decision.

---

## 16. Decision Output Format

The approver records the final decision by completing
`docs/webui/phase-1g-10-human-approver-signoff-template.md`:

```text
Decision:
  [ ] GO
  [ ] NO-GO
  [ ] PAUSED
```

together with the approver name, role, decision date, reviewed baseline HEAD,
reviewed RC / Pilot IDs, P0/P1/P2 counts, conditions, required follow-up,
approval notes, and signature. A GO requires every GO prerequisite (§5) to be
true; a NO-GO requires at least one NO-GO trigger (§6).

The decision output is the **only** artifact that may convert the technical
PASS into a release authorization. Until then, release authorization remains
**not granted**.

---

## 17. Eligibility / Next Action

| Field | Value |
|-------|-------|
| Eligible next step | final release decision review by the human approver |
| Release authorization | **not granted** in this phase |
| Push? | **no** (Phase 1G-10 = local commit only, no push) |
| Start Phase 1G-11? | **no** |

---

## 18. Cross-References

- Post-Pilot closeout: `docs/webui/phase-1g-10-post-pilot-closeout.md`.
- Human approver sign-off template:
  `docs/webui/phase-1g-10-human-approver-signoff-template.md`.
- Release readiness summary:
  `docs/webui/phase-1g-10-release-readiness-summary.md`.
- Pilot closeout report: `docs/webui/phase-1g-10-pilot-closeout-report.md`.
- Final GO / NO-GO draft: `docs/webui/phase-1g-10-final-go-no-go-draft.md`.
- Phase 1G-09 final decision: `docs/webui/phase-1g-09-pilot-final-decision.md`.
- Phase 1G-07 RC Go / No-Go: `docs/webui/phase-1g-07-go-no-go-decision.md`.
- Risk register: `docs/webui/phase-1g-05-risk-register.md`.

---

## 19. Phase 1G-10B Addendum — Human Approver Final Decision

| Field | Value |
|-------|-------|
| GO prerequisite 15 (human approver sign-off) | **met** |
| Human approver sign-off | **completed** (2026-06-14) |
| Human Decision ID | `HUMAN-DECISION-1G-10B-001` |
| Release authorization | **granted** by the designated human approver (黄瑞邦) |
| Decision record | `docs/webui/phase-1g-10b-human-approver-final-decision.md` |
| Reviewed baseline HEAD | `56b571fec1f61b8d6554b1c4a0bf597576266bd1` |

GO prerequisite 15 is now met. All fifteen GO prerequisites (§5) are satisfied.
Release authorization is granted by the designated human approver.

> **This does not perform a production rollout.**
> **This does not modify production.**
> **This does not start Phase 1G-11.**

---

## 20. Phase 1G-11 Addendum — Final Seal & Phase 2 Unlock

| Field | Value |
|-------|-------|
| Final Seal ID | `FINAL-SEAL-1G-11-001` |
| Phase 2 Unlock ID | `PHASE-2-UNLOCK-1G-11-001` |
| Phase 1G final status | **sealed** |
| Phase 2 status | **unlocked** |
| Production rollout performed by Phase 1G-11 | **no** |
| Phase 2A implementation started by Phase 1G-11 | **no** |
| Baseline input HEAD | `3c6ae479b37f3cb4e02c18f6dbef97334b1355e1` |

Phase 1G-11 (Final Release Seal & Phase 2 Unlock) recorded the final seal of
Phase 1G (`FINAL-SEAL-1G-11-001`) and unlocked Phase 2
(`PHASE-2-UNLOCK-1G-11-001`). All fifteen GO prerequisites (§5) remain
satisfied; release authorization granted under `HUMAN-DECISION-1G-10B-001`
remains in force; Phase 1G is now sealed. Route governance remains unchanged
(34 / 34 / 5 / 0 / 1 / 1); `STATIC_ALLOWLIST` remains `frozenset({"clarify"})`;
the Production Gateway PID `1962` was unaffected.

This addendum records the seal and unlock only. It does **not** perform a
production rollout, does **not** modify production, and does **not** start Phase
2A implementation. Phase 2A starts only after the user separately authorizes it.
See `docs/webui/phase-1g-11-final-release-seal-and-phase-2-unlock.md` and
`docs/webui/phase-1g-final-release-seal.md`.

---

*Phase 1G-10 Final Release Decision Preparation —
`RELEASE-DECISION-PREP-1G-10-001`. GO prerequisite 15 (human approver sign-off) is
**met** (`HUMAN-DECISION-1G-10B-001`); release authorization **granted** by the
designated human approver. Phase 1G is **sealed** (`FINAL-SEAL-1G-11-001`); Phase
2 is **unlocked** (`PHASE-2-UNLOCK-1G-11-001`). This does not perform a production
rollout, does not modify production, and does not start Phase 2A. See
`docs/webui/phase-1g-10b-human-approver-final-decision.md` and
`docs/webui/phase-1g-11-final-release-seal-and-phase-2-unlock.md`.*
