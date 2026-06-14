# Phase 1G-11: Final Release Seal & Phase 2 Unlock — `FINAL-SEAL-1G-11-001` / `PHASE-2-UNLOCK-1G-11-001`

## Document Information

| Field | Value |
|-------|-------|
| Phase | 1G-11 |
| Title | Final Release Seal & Phase 2 Unlock |
| Status | Final seal recorded locally (pushed by this phase) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Final Seal ID | `FINAL-SEAL-1G-11-001` |
| Phase 2 Unlock ID | `PHASE-2-UNLOCK-1G-11-001` |
| Baseline input HEAD | `3c6ae479b37f3cb4e02c18f6dbef97334b1355e1` |
| Related Human Decision ID | `HUMAN-DECISION-1G-10B-001` |
| Related RC ID | `RC-1G-07-001` |
| Related Pilot Acceptance ID | `PILOT-1G-08-001` |
| Related Pilot Execution ID | `PILOT-EXEC-1G-09-001` |
| Related Closeout ID | `CLOSEOUT-1G-10-001` |
| Related Final Decision Preparation ID | `RELEASE-DECISION-PREP-1G-10-001` |
| Related Smoke Refresh ID | `SMOKE-PID-REFRESH-1G-10A-001` |
| Scope | Record the Phase 1G final seal and the Phase 2 unlock in a single pushed commit. No code, OpenAPI, test, frontend, or route change. |
| Author | Dev Agent (Phase 1G-11 final release seal) |

---

## 1. Phase 1G-11 Definition

Phase 1G-11 is the **final seal** of Phase 1G. It runs *after* Phase 1G-10B
(Human Approver Final Decision, `HUMAN-DECISION-1G-10B-001`) was recorded and
pushed at `3c6ae479b`. Phase 1G-11 is the terminal phase of Phase 1G: it
formally declares Phase 1G sealed, freezes the Phase 1G release baseline, and
**unlocks Phase 2** for separately authorized future work.

Phase 1G-11 does exactly two things, both recorded in a single pushed commit:

1. It records the **final seal** of Phase 1G (`FINAL-SEAL-1G-11-001`).
2. It records the **Phase 2 unlock** (`PHASE-2-UNLOCK-1G-11-001`).

> **Phase 1G-11 records the final seal and the Phase 2 unlock only.**
> **Phase 1G-11 does not perform a production rollout.**
> **Phase 1G-11 does not modify production.**
> **Phase 1G-11 does not start Phase 2A implementation.**

---

## 2. Final Seal Identification

| Field | Value |
|------|-------|
| Final Seal ID | `FINAL-SEAL-1G-11-001` |
| Phase 2 Unlock ID | `PHASE-2-UNLOCK-1G-11-001` |
| Seal Date | 2026-06-14 |
| Seal Branch | `dev-huangruibang` |
| Baseline input HEAD | `3c6ae479b37f3cb4e02c18f6dbef97334b1355e1` |
| Authorizing Human Decision | `HUMAN-DECISION-1G-10B-001` (GO; approver 黄瑞邦; 2026-06-14) |

---

## 3. Reviewed Baseline

| Field | Value |
|------|-------|
| Branch | `dev-huangruibang` |
| Baseline input HEAD (local = remote at seal time) | `3c6ae479b37f3cb4e02c18f6dbef97334b1355e1` |
| Baseline input HEAD short | `3c6ae479b` |
| Baseline input HEAD subject | `docs(webui): record human approver final decision` |
| Merge base | `3c6ae479b37f3cb4e02c18f6dbef97334b1355e1` |
| ahead / behind (at seal time) | `0 / 0` |
| Tracked worktree | clean |
| Untracked | `.claude/` only |

The baseline input HEAD `3c6ae479b` is the pushed Phase 1G-10B human approver
final decision record. It is the head of the Phase 1G commit chain
(`1G-04` sealed → `1G-05` → `1G-06` → `1G-07` → `1G-08` → `1G-09` → `1G-10` →
`1G-10A` → `1G-10B`). The human approver reviewed the combined Phase 1G-10 +
Phase 1G-10A state at HEAD `56b571fec` and recorded GO; that decision was then
committed and pushed as `3c6ae479b` (Phase 1G-10B).

---

## 4. Reviewed Human Decision Baseline

| Field | Value |
|------|-------|
| Human Decision ID | `HUMAN-DECISION-1G-10B-001` |
| Approver | 黄瑞邦 — Project Owner / Release Approver |
| Decision | **GO** |
| Decision Date | 2026-06-14 |
| Release authorization | **granted by the designated human approver** |
| Reviewed HEAD (by the approver) | `56b571fec1f61b8d6554b1c4a0bf597576266bd1` |
| Pilot Result reviewed | **PASS** (15 / 15 scenarios A–O) |
| P0 | 0 |
| P1 | 0 |
| P2-09 (human approver sign-off dependency) | **resolved** by this decision |
| P2-01 … P2-08 | remain accepted, non-blocking backlog items |
| Phase 2 eligibility | **granted** by this phase (`PHASE-2-UNLOCK-1G-11-001`) |

> **Decision: GO. Release authorization granted by the designated human approver.**

The Phase 1G-11 seal is built directly on top of the human approver's GO
decision. The Dev Agent did not invent, infer, auto-select, or fabricate that
decision.

---

## 5. Related IDs (Full Phase 1G Chain)

| ID | Phase | Purpose | Outcome |
|----|-------|---------|---------|
| `RC-1G-07-001` | 1G-07 | Release Candidate Dry Run | GO |
| `PILOT-1G-08-001` | 1G-08 | Pilot Acceptance Preparation | prepared |
| `PILOT-EXEC-1G-09-001` | 1G-09 | Pilot Acceptance Execution | PASS (15 / 15) |
| `CLOSEOUT-1G-10-001` | 1G-10 | Post-Pilot Closeout | completed |
| `RELEASE-DECISION-PREP-1G-10-001` | 1G-10 | Final Release Decision Preparation | prepared |
| `SMOKE-PID-REFRESH-1G-10A-001` | 1G-10A | Smoke Harness PID Baseline Refresh | `69355` → `1962` |
| `HUMAN-DECISION-1G-10B-001` | 1G-10B | Human Approver Final Decision | GO; authorization granted |
| `FINAL-SEAL-1G-11-001` | 1G-11 | Phase 1G Final Release Seal | **SEALED** |
| `PHASE-2-UNLOCK-1G-11-001` | 1G-11 | Phase 2 Unlock | **UNLOCKED** |

---

## 6. Phase 1G Final Release Status

| Field | Value |
|------|-------|
| Phase 1G status | **SEALED** (`FINAL-SEAL-1G-11-001`) |
| Release decision | **GO** (`HUMAN-DECISION-1G-10B-001`) |
| Release authorization | **granted by the designated human approver** |
| Phase 1G capability | clarify-only controlled execution MVP — delivered and piloted |
| Phase 1G pilot result | **PASS** (15 / 15 scenarios A–O) |
| Production rollout | **not performed** in Phase 1G |
| Production rollout performed by Phase 1G-11 | **no** |

Phase 1G is now sealed. No further Phase 1G-`xx` micro-phases will be created.
The strategy from Phase 1G-11 onward is **vertical feature slices** under Phase 2
(see `docs/webui/phase-2-unlock-plan.md`), not additional seal / push / gate
micro-phases for Phase 1G.

---

## 7. Phase 1G Capability Summary

Phase 1G delivered a **clarify-only controlled execution MVP** for the Dev
WebUI. The delivered, end-to-end capability chain is:

1. Dev WebUI loads (`127.0.0.1` only; dev `HERMES_HOME` only).
2. Tools panel visible (read-only catalog).
3. Tool policy / schema read-only inspection.
4. `clarify` dry-run (no dispatch).
5. Confirmation token (held in-memory only; never persisted / logged / rendered).
6. Digest verification (binding the dry-run event to the execute gate).
7. Pre-execution audit.
8. Handler lookup.
9. Dispatch planning.
10. **clarify-only** handler call (the single allowlisted tool).
11. Post-execution audit.
12. Read-only audit events API (`GET /api/dev/v1/tools/audit-events`).
13. Audit Viewer (frontend, redacted, whitelist-normalized).
14. Browser smoke / E2E harness (both blocked + completed profiles).
15. Release rehearsal, RC dry run, Pilot preparation, Pilot execution.
16. **Pilot PASS** (`PILOT-EXEC-1G-09-001`; 15 / 15 scenarios A–O).
17. **Human approver GO** (`HUMAN-DECISION-1G-10B-001`).
18. **Phase 2 unlock** (`PHASE-2-UNLOCK-1G-11-001`).

Full delivered-capability table: `docs/webui/phase-1g-final-release-seal.md`.

---

## 8. Phase 1G Security Boundary Summary (Frozen Release Baseline)

The Phase 1G release baseline freezes the following security boundary. Any
future phase that touches any of these is a P0 and stops immediately.

| Check | Release-baseline value |
|-------|------------------------|
| `STATIC_ALLOWLIST` | exactly `frozenset({"clarify"})` |
| Raw confirmation token in response / DOM / log / console / `localStorage` / `sessionStorage` / audit event | never |
| Full `tokenHash` surfaced | never |
| Raw arguments in the audit viewer | never |
| Secrets / API keys / credentials logged or committed | never |
| Callable / function repr exposed | never |
| Audit JSONL committed | never |
| `.claude/` committed | never |
| `~/.hermes` accessed | never |
| Production `state.db` accessed | never |
| Force push / rebase / `git reset --hard` attempted | never |

---

## 9. Phase 1G Route Governance Baseline

| Metric | Release-baseline value |
|--------|------------------------|
| OpenAPI paths | **34** |
| Runtime routes | **34** |
| Tool GET routes | **5** |
| Tool write routes | **0** |
| Tool dry-run routes | **1** |
| Tool execution routes | **1** |
| `STATIC_ALLOWLIST` | `frozenset({"clarify"})` |

**No deviation.** This is the Phase 1G frozen release baseline. Phase 1G-11
does not change it.

---

## 10. Phase 1G Production Safety Baseline

| Check | Release-baseline value |
|-------|------------------------|
| Production Gateway process count | exactly 1 |
| Production Gateway PID | `1962` (Phase 1G-10A refreshed baseline) |
| Production Gateway command | `hermes_cli.main gateway run --replace` (identical) |
| Production Gateway stopped / restarted / replaced / reconfigured by Phase 1G | no |
| Dev Gateway | stopped |
| Ports `5180` / `5181` | free |
| Dev `HERMES_HOME` isolation | PASS |
| Production `~/.hermes` accessed | no |
| Production `state.db` accessed | no |

The Production Gateway PID `1962` is the Phase 1G-10A refreshed baseline. It
replaced the through-Phase-1G-09 sealed value `69355` after an environmental
host reboot (`2026-06-14 04:02:09`) caused `launchd` to respawn the gateway.
This is environmental drift, not a phase action. Phase 1G-11 did not touch
production.

---

## 11. Phase 1G Final Gates Summary

Phase 1G-11 is docs-only, but because it pushes, the core gates were re-run.

| Gate | Result |
|------|--------|
| Route governance (`test_dev_check_webui.py`, `test_dev_web_0c06_closure.py`) | pass |
| Related backend regression (19 files) | pass (0 failed) |
| `compileall` (14 dev_web modules) + `py_compile toolsets.py` | pass |
| `ruff check` (modules + tests) | all checks passed |
| Frontend `pnpm type-check` / `pnpm lint` / `pnpm test` / `pnpm build` | pass |
| Browser smoke / E2E (`run-dev-webui-execute-audit-smoke.sh all`) | PASS (Profile A 6 passed / 1 skipped; Profile B 7 passed; Overall PASS) |
| `memory-check` | PASS |
| `dev-check` | PASS / WARN (only `.claude/` untracked) |
| Production Gateway PID gate | `1962` unchanged |

---

## 12. P0 / P1 / P2 Status

| Severity | Count | Status |
|----------|-------|--------|
| P0 | 0 | none |
| P1 | 0 | none |
| P2 (technical) | 8 | P2-01 … P2-08 — accepted, non-blocking backlog; carry into Phase 2 |
| P2 (release dependency) | 1 | P2-09 — **resolved** by `HUMAN-DECISION-1G-10B-001` |

P2-09 is no longer open. The 8 technical P2 items remain accepted, non-blocking,
and carry forward into Phase 2 planning (see `docs/webui/phase-1g-05-risk-register.md`
§14 addendum and the new Phase 2 risks R2A-01 … R2A-05).

---

## 13. Phase 2 Unlock Decision

| Field | Value |
|------|-------|
| Phase 2 status | **UNLOCKED** (`PHASE-2-UNLOCK-1G-11-001`) |
| Phase 2 eligibility | granted — Phase 2 may start as the next major phase |
| Phase 2A status | **not started** |
| Phase 2A implementation started by Phase 1G-11 | **no** |
| Phase 2A separately authorized? | required before Phase 2A implementation begins |

Phase 2 is unlocked. Phase 2A (Real Tool Execution MVP — read-only multi-tool
execution) is the recommended first Phase 2 slice, but it remains a
**separately authorized** phase: Phase 1G-11 does not itself start Phase 2A
implementation.

---

## 14. Phase 2 Roadmap (Unlocked, Not Implemented)

The recommended Phase 2 vertical-slice sequence (planning only; none
implemented by Phase 1G-11):

| Phase | Target |
|-------|--------|
| Phase 2A | Real Tool Execution MVP — read-only multi-tool execution |
| Phase 2B | Provider Schema / Provider API controlled integration |
| Phase 2C | Tool write execution under stronger confirmation / rollback / sandbox |
| Phase 2D | Advanced audit storage / search / pagination / rotation |
| Phase 2E | Frontend product workflow and operator polish |

Full roadmap and entry / exit conditions: `docs/webui/phase-2-unlock-plan.md`.
Phase 2A detailed MVP plan: `docs/webui/phase-2a-real-tool-execution-mvp-plan.md`.

---

## 15. Phase 2A Immediate Next Target

Phase 2A — **Real Tool Execution MVP (read-only only)** — is the recommended
next phase. Its user-facing outcome is: an operator can run more than just
`clarify` through the controlled execution chain, provided each additional tool
is **read-only**, **individually audited**, and **individually authorized**.

Phase 2A is read-only first. It explicitly excludes:
- Tool write;
- shell command execution as a user-facing tool;
- database mutation;
- Provider API (deferred to Phase 2B);
- production state access;
- `~/.hermes` access;
- any non-read-only external side effect;
- arbitrary file access.

Phase 1G-11 does **not** implement any Phase 2A code. Phase 2A starts only after
the user separately authorizes it.

---

## 16. Non-Goals of Phase 1G-11

Phase 1G-11 does **not**:

- perform a production rollout;
- modify production data, the production gateway, or production configuration;
- access production `~/.hermes` or production `state.db`;
- stop, restart, replace, signal, or reconfigure the Production Gateway;
- add any WebUI product capability;
- modify any backend, frontend, test, OpenAPI, or script file;
- add a backend route, a Tool write route, a second Tool execution route, or a
  Provider route;
- enable any non-clarify execution;
- expand `STATIC_ALLOWLIST` beyond `frozenset({"clarify"})`;
- send a Provider Schema or call a Provider API;
- start Phase 2A implementation;
- create a release tag or a GitHub Release;
- fabricate, infer, or auto-select the human approver's GO decision.

---

## 17. What Phase 1G-11 Does Not Authorize

This phase records the **final seal** and the **Phase 2 unlock**. It does **not**
authorize:

- a production rollout (the WebUI binds to `127.0.0.1` only);
- any change to production;
- the start of Phase 2A implementation (Phase 2A is separately authorized);
- any expansion of `STATIC_ALLOWLIST`;
- any Provider Schema sending or Provider API call;
- any non-clarify execution;
- any Tool write route, second execution route, or Provider route;
- any release tag or GitHub Release;
- any production deployment.

The Phase 2 unlock authorizes Phase 2 **planning and separately authorized
start** only. Each Phase 2 slice must be individually authorized before
implementation begins.

---

## 18. Final Conclusion

Phase 1G-11 records the Phase 1G final seal and the Phase 2 unlock.

**Phase 1G is now SEALED** (`FINAL-SEAL-1G-11-001`). The Phase 1G release
decision remains **GO**, and release authorization remains granted by the
designated human approver under `HUMAN-DECISION-1G-10B-001`.

**Phase 2 is now UNLOCKED** (`PHASE-2-UNLOCK-1G-11-001`). Phase 2A is eligible
to start as the next separately authorized phase. Phase 2A implementation was
**not** started in this phase.

This phase recorded final seal and Phase 2 unlock only. It did not perform a
production rollout, did not modify production, did not access `~/.hermes`, did
not access production `state.db`, and did not start Phase 2A implementation.

Route governance remains unchanged at OpenAPI paths 34, runtime routes 34,
Tool GET 5, Tool write 0, Tool dry-run 1, Tool execution 1, and
`STATIC_ALLOWLIST` remains `frozenset({"clarify"})`. Production Gateway PID
`1962` was not affected.

---

## 19. Cross-References

- Phase 1G final release seal: `docs/webui/phase-1g-final-release-seal.md`.
- Phase 2 unlock plan: `docs/webui/phase-2-unlock-plan.md`.
- Phase 2A Real Tool Execution MVP plan:
  `docs/webui/phase-2a-real-tool-execution-mvp-plan.md`.
- Human approver final decision: `docs/webui/phase-1g-10b-human-approver-final-decision.md`.
- Final release decision preparation:
  `docs/webui/phase-1g-10-final-release-decision-preparation.md`.
- Final GO / NO-GO draft: `docs/webui/phase-1g-10-final-go-no-go-draft.md`.
- Release readiness summary: `docs/webui/phase-1g-10-release-readiness-summary.md`.
- Phase 1G-10A smoke harness PID baseline refresh:
  `docs/webui/phase-1g-10a-smoke-harness-pid-baseline-refresh.md`.
- Phase 1G-09 Pilot final decision: `docs/webui/phase-1g-09-pilot-final-decision.md`.
- Implementation plan: `docs/webui/phase-1-implementation-plan.md`.
- Risk register: `docs/webui/phase-1g-05-risk-register.md`.

---

*Phase 1G-11 Final Release Seal & Phase 2 Unlock — `FINAL-SEAL-1G-11-001` /
`PHASE-2-UNLOCK-1G-11-001`. Phase 1G is **SEALED** (release decision GO;
release authorization granted by the designated human approver under
`HUMAN-DECISION-1G-10B-001`). Phase 2 is **UNLOCKED** for separately authorized
work; Phase 2A is eligible to start as the next separately authorized phase.
Phase 1G-11 did not perform a production rollout, did not modify production,
did not access `~/.hermes`, did not access production `state.db`, and did not
start Phase 2A implementation.*
