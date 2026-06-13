# Phase 1G-08: Pilot Exit Criteria

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-08 |
| Title | Pilot Exit Criteria |
| Status | Prepared (Pilot execution pending explicit approval) |
| Date | 2026-06-14 |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Related Release Candidate | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Baseline HEAD | `6f9176953cec7676d668aa3b4b7a654a374834de` |
| Scope | The PASS / NO-GO / PAUSED rules for `PILOT-1G-08-001`. No code change. |

---

## 1. Outcomes

A Pilot run resolves to exactly one of:

| Outcome | Meaning |
|---------|---------|
| **PASS** | The Pilot is accepted. The mainline may proceed toward Pilot-accepted status (subject to approver sign-off). |
| **NO-GO** | The Pilot is rejected. A P0 boundary violation or an unresolved P1 was found. Phase 1G-04 is **not** reopened; the finding is addressed via a separately approved phase. |
| **PAUSED** | The Pilot is temporarily suspended on an unresolved P1 or an environment issue that does not touch a P0 boundary. Resume after the blocker is cleared and the baseline is re-verified. |

---

## 2. PASS Conditions

The Pilot is **PASS** only when **all** hold:

1. No P0 in any scenario (A–O).
2. No unresolved P1 in any scenario.
3. All required scenarios pass (applicable scenarios in both gate profiles).
4. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1).
5. `STATIC_ALLOWLIST` unchanged (`frozenset({"clarify"})`).
6. Production Gateway PID `69355` unaffected.
7. No `~/.hermes` access.
8. No production `state.db` access.
9. No Provider Schema sent; no Provider API called.
10. No non-clarify execution.
11. Evidence complete for every scenario.
12. Acceptance record signed off (operator + approver).

---

## 3. NO-GO Conditions

The Pilot is **NO-GO** if **any** of these occur:

1. Any P0.
2. Any unresolved P1 at Pilot end.
3. Route governance changed.
4. `STATIC_ALLOWLIST` expanded beyond `clarify`.
5. Provider Schema sent or Provider API called.
6. Non-clarify execution.
7. Tool write route introduced.
8. Production Gateway PID `69355` changed.
9. `~/.hermes` accessed.
10. Production `state.db` accessed.
11. Critical evidence missing (a required scenario has no recorded result).

A NO-GO does **not** reopen Phase 1G-04. It is recorded as a Pilot finding and
addressed via a separately approved phase.

---

## 4. PAUSED Conditions

The Pilot is **PAUSED** if:

- an unresolved P1 is blocking a required scenario but does not touch a P0
  boundary; or
- an environment issue occurs (port conflict, smoke harness abort, transient
  failure) that does not indicate a P0.

Resume only after the blocker is cleared and the baseline (git, route
governance, allowlist, production PID, ports) is re-verified.

---

## 5. P0 Handling Rule

A P0 finding:

- **stops the Pilot immediately** (do not proceed to the next scenario);
- is recorded against the defect / feedback template with full evidence (no
  secret values);
- forces a **NO-GO** outcome unless the P0 is later proven to be a false
  positive (e.g., a test artifact) and retracted with a recorded reason;
- never triggers an automatic rollback — rollback requires explicit user
  confirmation and a `git revert` commit.

---

## 6. P1 Handling Rule

A P1 finding:

- **blocks a PASS** until resolved or formally waived by an approver;
- is recorded against the defect / feedback template;
- allows the Pilot to continue with the remaining scenarios (to gather full
  evidence) unless the operator judges the P1 to be environment-destabilizing;
- if unresolved at Pilot end → **NO-GO** (or **PAUSED** if a near-term fix is
  expected).

---

## 7. P2 Handling Rule

A P2 finding:

- is recorded against the defect / feedback template;
- is appended to `docs/webui/phase-1g-05-risk-register.md` with a Risk ID,
  current impact, reason it is not a blocker, owner, suggested action, and exit
  criteria;
- **does not block** PASS;
- is never silently ignored.

---

## 8. Phase 1G-09 Entry

- Phase 1G-09 is **not started** by `PILOT-1G-08-001`. Its scope, if any, must be
  defined and approved separately.
- A Pilot PASS does **not** automatically start Phase 1G-09.
- A Pilot NO-GO does **not** authorize any phase to reopen Phase 1G-04.

---

## 9. Pilot Execution Entry

- Pilot execution may begin only after a human approver approves it against the
  sealed mainline.
- Pilot execution uses the acceptance pack, the operator guide, the participant
  guide, the acceptance record template, the defect / feedback template, and
  these exit criteria.
- Phase 1G-08 **prepares** the pack; it does **not** execute the Pilot.

---

## 10. Supplemental RC Rule

- A Pilot NO-GO does **not** by itself require a new RC.
- If the NO-GO reveals a code defect that requires a code change, a new RC
  (e.g., `RC-1G-07-002` or a later phase) must be produced and re-validated
  before a re-Pilot.
- Phase 1G-08 does **not** produce a new RC; `RC-1G-07-001` remains the GO RC.

---

## 11. Rollback / Revert Rule

- No automatic rollback during the Pilot.
- If rollback is needed: **stop and request user confirmation**; use a new
  `git revert` commit; never `git reset --hard`; never force push; never
  production state mutation. Preserve evidence first.
- See `docs/webui/phase-1g-05-ops-and-rollback-runbook.md`.

---

## 12. Evidence Requirements

A Pilot record is complete only when:

- every scenario (A–O) has a recorded status (PASS / FAIL / BLOCKED / SKIPPED);
- every required scenario that ran has evidence (decision string, provider /
  external flags, audit-viewer state, route-governance summary, PID before/after,
  final port state);
- no evidence contains a secret, an API key, the raw confirmation token, the full
  token hash, or raw arguments;
- every defect has a record with severity + category.

---

## 13. Sign-off Requirements

| Role | Required for |
|------|--------------|
| Operator | Records all scenarios + evidence + defects; signs the record. |
| Observer (optional) | Confirms observed behavior; signs or marks "none". |
| Approver (human) | **Required for a final PASS.** A PASS without an approver is a recommendation only. |

---

## 14. Emergency Stop Conditions (carry in every Pilot)

Stop the Pilot immediately and report if any of these occur:

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

---

## 15. Cross-References

- Pilot acceptance pack: `docs/webui/phase-1g-08-pilot-acceptance-pack.md`.
- Operator guide: `docs/webui/phase-1g-08-pilot-operator-guide.md`.
- Participant guide: `docs/webui/phase-1g-08-pilot-participant-guide.md`.
- Acceptance record template:
  `docs/webui/phase-1g-08-pilot-acceptance-record-template.md`.
- Defect / feedback template:
  `docs/webui/phase-1g-08-pilot-defect-feedback-template.md`.
- Pilot preparation: `docs/webui/phase-1g-08-pilot-acceptance-preparation.md`.
- RC Go / No-Go: `docs/webui/phase-1g-07-go-no-go-decision.md`.
- Ops / rollback runbook: `docs/webui/phase-1g-05-ops-and-rollback-runbook.md`.
- Risk register: `docs/webui/phase-1g-05-risk-register.md`.

---

*Phase 1G-08 Pilot Exit Criteria — PASS / NO-GO / PAUSED for `PILOT-1G-08-001`
against RC `RC-1G-07-001` (GO). P0 stops; P1 blocks PASS; P2 records. Phase 1G-04
remains sealed.*
