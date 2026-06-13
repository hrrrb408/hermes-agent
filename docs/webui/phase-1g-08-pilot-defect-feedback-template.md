# Phase 1G-08: Pilot Defect / Feedback Template

> Copy this template once per finding into a defect record (for example
> `docs/webui/phase-1g-08-defect-DEF-001.md`), or keep a single running log of
> defects as append-only blocks. Phase 1G-08 ships the **template** only; defect
> records are produced when the Pilot is executed.

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-08 |
| Title | Pilot Defect / Feedback Template |
| Status | Template (awaiting Pilot execution) |
| Date | _(fill on finding)_ |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Related Release Candidate | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Scope | A copy-fill defect / feedback record. No code change. |

---

## 1. Defect Template (copy per finding)

```text
Defect ID:                  DEF-###
Found in Pilot:             PILOT-1G-08-001
Found by:                   <operator / participant name or role>
Date:                       <YYYY-MM-DD>
Severity:                   <P0 / P1 / P2>
Category:                   <see §3>
Area:                       <Tools panel / Execute / Audit viewer / theme / docs / smoke harness / other>
Summary:                    <one line>
Steps to reproduce:         <numbered steps>
Expected:                   <what should have happened>
Actual:                     <what did happen>
Evidence:                   <text summary / screenshot ref — no secrets>
Environment:                HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev ;
                            Dev API 127.0.0.1:5181 ; WebUI 127.0.0.1:5180 ;
                            gate profile <blocked / completed / n/a>
Route governance impact:    <none / describe — default none>
Security boundary impact:   <none / describe — default none>
Production impact:          <none / describe — default none>
Suggested owner:            <role / phase>
Decision:                   <open / accepted-as-P2 / to-fix / wont-fix>
```

> Never include a real secret, API key, raw confirmation token, full token hash,
> or raw arguments in any field. If the finding involves one of those, describe
> it in words ("a long key-looking string appeared") and **do not** paste the
> value.

---

## 2. Severity Levels

| Severity | Meaning | Pilot action |
|----------|---------|--------------|
| **P0** | A safety boundary is violated: security, production, data, route governance, or allowlist violation; or a secret / raw token / full tokenHash / raw-arguments leak; or a non-clarify tool executes; or Provider Schema / API activity. | **Stop the Pilot immediately.** Do not proceed. Preserve evidence. Report and remediate before any further Pilot step. |
| **P1** | A Pilot blocker / core flow failure: a sealed capability does not work, or a required gate fails (regression, route governance count, build, smoke). | **The Pilot cannot pass.** Record; do not mark the Pilot accepted until resolved or formally waived. |
| **P2** | A non-blocking limitation: documentation, polish, a recorded by-design limitation (audit pagination, non-clarify disabled by design, Provider permanent non-goal). | **Record against the risk register; do not block.** See `docs/webui/phase-1g-05-risk-register.md`. |

### Severity quick map (from the acceptance pack)

| Failure | Severity |
|---------|----------|
| Allowlist shows more than `clarify` | P0 |
| Provider Schema sent | P0 |
| Provider API called | P0 |
| Non-clarify tool executes / allowlisted | P0 |
| Raw confirmation token exposed (response / DOM / log / console / storage / audit) | P0 |
| Full tokenHash surfaced | P0 |
| Raw arguments visible in audit viewer | P0 |
| Secret / API key / credential logged or committed | P0 |
| `~/.hermes` or production `state.db` accessed | P0 |
| Production Gateway PID `69355` changes | P0 |
| Tool write route / second execution route / Provider route appears | P0 |
| Dry-run errors, decision wrong, viewer errors, ID missing | P1 |
| Port still held by an accountable process | P1 |
| Documentation wording, theme polish, label clarity | P2 |

---

## 3. Feedback Categories

Use one category per finding:

| Category | Use for |
|----------|---------|
| UX feedback | Layout, interaction flow, clarity, theme rendering, labels. |
| Documentation feedback | Wording, missing steps, contradictions in the docs. |
| Operational feedback | Command ergonomics, harness output, runbook gaps. |
| Smoke harness feedback | `scripts/run-dev-webui-execute-audit-smoke.sh` behavior, profiles, cleanup. |
| Audit viewer feedback | Audit viewer rendering, empty state, malformed-line skip, pagination. |
| Execution flow feedback | Dry-run, confirm, execute, blocked vs completed decisions. |
| Security concern | Anything touching a safety boundary (escalate to P0 if confirmed). |
| Other | Anything that does not fit the above. |

---

## 4. Worked Examples

**P0 example (stop immediately):**

```text
Defect ID:                  DEF-001
Found in Pilot:             PILOT-1G-08-001
Found by:                   participant
Date:                       2026-06-14
Severity:                   P0
Category:                   Security concern
Area:                       Audit viewer
Summary:                    Long key-looking string visible in post-execution audit
Steps to reproduce:         1) completed profile; 2) Audit viewer → post_execution.
Expected:                   safe summary only; no long code.
Actual:                     a long string starting with "sk-…" visible on screen.
Evidence:                   text description (value NOT pasted).
Environment:                completed gate profile.
Route governance impact:    unknown — investigate.
Security boundary impact:   secret / token-class leak suspected.
Production impact:          none observed.
Suggested owner:            security review.
Decision:                   open — Pilot STOPPED.
```

**P1 example:**

```text
Defect ID:                  DEF-002
Found in Pilot:             PILOT-1G-08-001
Found by:                   operator
Date:                       2026-06-14
Severity:                   P1
Category:                   Execution flow feedback
Area:                       Execute
Summary:                    Execute returns completed under the blocked profile
Steps to reproduce:         1) blocked profile; 2) Tools → Execute → clarify;
                            3) Confirm & Execute.
Expected:                   blocked_tool_handler_call_not_enabled.
Actual:                     clarify_execution_completed.
Evidence:                   decision string captured.
Environment:                blocked gate profile.
Route governance impact:    none.
Security boundary impact:   none directly (investigate handler-call gate).
Production impact:          none.
Suggested owner:            backend.
Decision:                   to-fix — Pilot PAUSED.
```

**P2 example:**

```text
Defect ID:                  DEF-003
Found in Pilot:             PILOT-1G-08-001
Found by:                   participant
Date:                       2026-06-14
Severity:                   P2
Category:                   UX feedback
Area:                       Audit viewer
Summary:                    "post_execution" label is not human-friendly
Steps to reproduce:         1) Audit viewer → post_execution tab.
Expected:                   a friendly label.
Actual:                     the raw string "post_execution".
Evidence:                   text description.
Environment:                n/a.
Route governance impact:    none.
Security boundary impact:   none.
Production impact:          none.
Suggested owner:            frontend polish (future phase).
Decision:                   accepted-as-P2 — recorded against risk register.
```

---

## 5. Triage Rules

- A P0 finding **always** stops the Pilot, regardless of category.
- A P1 finding prevents a Pilot PASS until resolved or formally waived by an
  approver.
- A P2 finding is appended to `docs/webui/phase-1g-05-risk-register.md` with a
  Risk ID, current impact, reason it is not a blocker, owner, suggested action,
  and exit criteria.
- No finding, regardless of severity, may reopen Phase 1G-04 or expand
  `STATIC_ALLOWLIST`. Remediation of any boundary-affecting finding requires a
  separately approved phase.

---

## 6. Cross-References

- Pilot acceptance pack: `docs/webui/phase-1g-08-pilot-acceptance-pack.md`.
- Operator guide: `docs/webui/phase-1g-08-pilot-operator-guide.md`.
- Participant guide: `docs/webui/phase-1g-08-pilot-participant-guide.md`.
- Acceptance record template:
  `docs/webui/phase-1g-08-pilot-acceptance-record-template.md`.
- Exit criteria: `docs/webui/phase-1g-08-pilot-exit-criteria.md`.
- Risk register: `docs/webui/phase-1g-05-risk-register.md`.

---

*Phase 1G-08 Pilot Defect / Feedback Template — copy per finding. P0 stops the
Pilot; P1 blocks PASS; P2 records against the risk register. No secrets, ever.*
