# Phase 1G-08: Pilot Participant Guide

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-08 |
| Title | Pilot Participant Guide |
| Audience | Pilot participants / observers (non-technical-friendly). |
| Status | Prepared (Pilot execution pending explicit approval) |
| Date | 2026-06-14 |
| Pilot Acceptance ID | `PILOT-1G-08-001` |
| Related Release Candidate | `RC-1G-07-001` (Phase 1G-07, **GO**) |
| Scope | Non-technical instructions for observing the Pilot and reporting feedback. No code change. |

---

## 1. What this Pilot is for

This Pilot checks whether the Dev WebUI's controlled tool-execution feature works
correctly and safely **on the development machine only**. The feature lets a
single, pre-approved tool (`clarify`) run in a tightly controlled way, with every
step recorded for later review.

You are here to **watch the screen, try the listed steps, and tell us what you
see** — especially anything that looks wrong, confusing, or unsafe.

This is **not** a test of production, and it does **not** touch any real customer
data.

---

## 2. What you need to do

- Follow the steps the operator shows you (or the steps in the acceptance pack).
- Look at the WebUI the operator opens for you (the address is always
  `http://127.0.0.1:5180` — your local machine only).
- Tell the operator what you see, in plain words.
- Note down anything that looks wrong, using the feedback examples below.

---

## 3. What you do **not** need to do

- You do **not** need to install anything.
- You do **not** need to run terminal commands (the operator does that).
- You do **not** need to know how the code works.
- You do **not** need to provide any password, key, token, or secret — ever.
- You do **not** need to look at any file under `~/.hermes` or any "production"
  folder. If anyone asks you to, **stop and report it**.

---

## 4. How to look at the WebUI

- The operator opens `http://127.0.0.1:5180` in a browser for you.
- You should see a three-panel workspace.
- Try the things the acceptance pack lists for each scenario:
  - Does the page load?
  - Does the **Tools** panel show up?
  - Does a **dry-run** for `clarify` show a result (without showing any long
    secret-looking code)?
  - Does **Execute** either say "blocked" or "completed"?
  - Does the **Audit** view show readable entries (again, without any long
    secret-looking code)?

---

## 5. How to report a problem

Use the defect / feedback template the operator gives you. For each item, write:

- A short title (one line).
- What you did, step by step.
- What you expected.
- What actually happened.
- How serious it felt (see §7).
- A screenshot or a few words describing the screen — **without** any password,
  key, token, or long code.

---

## 6. How to describe reproduction steps

Good reproduction steps let someone else see the same thing. Write them like a
recipe:

1. Open `http://127.0.0.1:5180`.
2. Click the **Tools** panel.
3. Click **Execute**.
4. Choose `clarify`.
5. Click **Dry-run**.
6. I expected: a short result with a token ID.
7. I got: an error message saying "…".

---

## 7. How to tell blocker / major / minor apart

Use these three levels:

- **Blocker (P0 / stop-now):** something that breaks a safety rule — for example,
  a real password or key shown on screen, the wrong tool running, or anything
  that touches a "production" folder. **Stop testing and tell the operator
  immediately.**
- **Major (P1):** a main feature does not work at all, or shows the wrong result.
  The Pilot cannot be marked as passed until this is fixed.
- **Minor (P2):** a small annoyance — a wording issue, a slightly misaligned
  panel, a confusing label. Write it down; it does not stop the Pilot.

When unsure, ask the operator. It is always fine to over-report.

---

## 8. How to submit feedback

- Hand your filled defect / feedback records to the operator.
- The operator copies them into the Pilot acceptance record.
- You may also give verbal feedback; the operator will write it down for you.

---

## 9. When to stop testing

Stop immediately and tell the operator if you see **any** of these:

- A real password, API key, token, or long secret-looking string shown on screen
  or in a log.
- A tool other than `clarify` actually running.
- Anything labeled "Provider Schema sent" or "Provider API called" turned **on**.
- Anything that asks you to open a `~/.hermes` or "production" folder.
- The machine behaves unexpectedly (a process you did not start, a port error
  that will not clear).
- Anything where you simply feel unsure whether it is safe.

---

## 10. What information you must **not** provide

Never type, paste, screenshot, or say any of:

- real API keys, passwords, tokens, or secrets;
- any file path under `~/.hermes`;
- any "production" database content;
- your own or anyone's personal credentials.

If a field on the screen looks like it wants a secret, leave it blank and ask the
operator.

---

## 11. Feedback examples

**Good major (P1) report:**

> Title: Execute button shows "completed" even though gates were off.
> Steps: Tools → Execute → clarify → Confirm & Execute (blocked profile).
> Expected: a "blocked" message.
> Actual: a "completed" message.
> Severity: Major.

**Good minor (P2) report:**

> Title: Audit viewer label "post_execution" is hard to read.
> Steps: Audit viewer → post_execution tab.
> Expected: a friendly label.
> Actual: the raw string "post_execution".
> Severity: Minor.

**Good blocker (P0) report (stop immediately):**

> Title: A long key-looking string appeared in the audit viewer.
> Steps: Audit viewer → post_execution.
> Expected: safe summary only.
> Actual: a long string starting with "sk-…" visible on screen.
> Severity: Blocker — STOPPED.

---

## 12. Cross-References

- Pilot acceptance pack: `docs/webui/phase-1g-08-pilot-acceptance-pack.md`.
- Operator guide: `docs/webui/phase-1g-08-pilot-operator-guide.md`.
- Defect / feedback template:
  `docs/webui/phase-1g-08-pilot-defect-feedback-template.md`.
- Exit criteria: `docs/webui/phase-1g-08-pilot-exit-criteria.md`.

---

*Phase 1G-08 Pilot Participant Guide — plain-language instructions for observing
`PILOT-1G-08-001`. No secrets, no production access, no unsafe commands.*
