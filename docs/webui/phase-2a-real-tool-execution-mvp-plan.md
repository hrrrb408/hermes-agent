# Phase 2A: Real Tool Execution MVP Plan — (planning only, not started)

## Document Information

| Field | Value |
|-------|-------|
| Phase | 2A (planning; not started) |
| Title | Real Tool Execution MVP — Read-Only Multi-Tool Execution |
| Status | Planning only — not implemented, not authorized to start |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Phase 2 Unlock ID | `PHASE-2-UNLOCK-1G-11-001` |
| Final Seal ID | `FINAL-SEAL-1G-11-001` |
| Baseline input HEAD | `3c6ae479b37f3cb4e02c18f6dbef97334b1355e1` |
| Scope | Plan the Phase 2A Real Tool Execution MVP. No code change. No implementation. |

---

## 1. Phase 2A Purpose

Phase 2A is the **first Phase 2 slice**. It extends the sealed Phase 1G
clarify-only controlled execution MVP into a **real, multi-tool, read-only**
execution capability: an operator can run more than just `clarify` through the
controlled execution chain, provided each additional tool is provably
read-only, individually audited, and individually authorized.

Phase 2A is **planning only** in this document. Phase 1G-11 does **not**
implement Phase 2A. Phase 2A implementation begins only after the user
separately authorizes it.

---

## 2. User-Facing Outcome

An operator, working on the dev instance only, can:

1. See a read-only catalog of candidate read-only tools beyond `clarify`.
2. Dry-run any candidate tool without dispatch.
3. Walk a controlled execution chain (dry-run → confirmation token → digest →
   pre-execution audit → handler lookup → dispatch → handler call →
   post-execution audit) for any candidate tool that has passed its per-tool
   audit.
4. Inspect the redacted, whitelist-normalized audit trail for each execution.

The outcome is **real multi-tool execution**, but strictly **read-only**: no
writes, no shell, no Provider, no production, no side effects.

---

## 3. MVP Scope

- **Real Tool Execution MVP, read-only only.**
- Extend the existing controlled execution chain to additional **read-only**
  tools.
- Each additional tool is **per-tool audited** (registered name, input / output
  schema, side effects) before it is added to the execution surface.
- Each additional tool is **individually authorized**.
- All Phase 1G safety invariants preserved unchanged.

---

## 4. Out-of-Scope

Phase 2A explicitly excludes:

1. no Tool write;
2. no shell command execution as a user-facing tool;
3. no database mutation;
4. no Provider API until Phase 2B;
5. no production state access;
6. no `~/.hermes` access;
7. no non-read-only external side effects;
8. no arbitrary file access.

Provider integration is Phase 2B. Tool write is Phase 2C. Both remain out of
Phase 2A.

---

## 5. Tool Category Strategy

Phase 2A admits only **read-only, side-effect-free** tools. A candidate tool
qualifies for Phase 2A only if all of the following are true:

- Its handler performs no writes (no file write, no DB mutation, no event
  append, no memory write / update / archive).
- It performs no shell / process execution.
- It makes no Provider API call.
- It accesses no production path.
- Its output is bounded, serializable, and redactable under the existing output
  validation rules (64 KiB serialized / 16 KiB agent / 8 KiB preview).
- Its registered name and input / output schema are audited and recorded.

A tool that fails any of these is not a Phase 2A candidate (it is either a
Phase 2C write candidate or out of scope entirely).

---

## 6. Read-Only First Principle

Phase 2A is **read-only first**. The rationale:

- Read-only tools cannot mutate state, so a defect cannot corrupt data.
- Read-only tools are reversible by definition (re-run them).
- Read-only tools make the controlled execution chain auditable end-to-end
  without rollback complexity.
- Read-only tools establish the per-tool audit discipline that Phase 2B
  (Provider) and Phase 2C (write) will inherit.

If a candidate tool's read-only status is ambiguous, it is **not** admitted to
Phase 2A. Ambiguity is resolved toward exclusion.

---

## 7. Candidate Tools (Planned, Not Implemented)

The following are **candidate** tools for Phase 2A discussion. They are
**not** enabled, **not** audited in detail here, and **not** added to
`STATIC_ALLOWLIST` by Phase 1G-11. Each is a placeholder for the per-tool audit
that Phase 2A will perform when it is separately authorized.

| # | Candidate tool | Read-only? | Phase 2A fit |
|---|----------------|------------|--------------|
| 1 | `clarify` | yes (no-op / metadata) | existing baseline — already allowlisted |
| 2 | status / readiness inspection tool | yes (read state) | candidate |
| 3 | route governance inspection tool | yes (read counts) | candidate |
| 4 | audit event search / read tool | yes (read JSONL) | candidate |
| 5 | environment-safe diagnostic summary tool | yes (read env summary) | candidate |
| 6 | dev-only file read summary tool | yes (read only) | candidate — only if explicitly authorized later |

> **Phase 2A may discuss candidate tools, but Phase 1G-11 must not implement
> them.** Each candidate requires its own per-tool audit (registered name,
> input / output schema, side effects) before any addition to the execution
> surface. None of the above is enabled by Phase 1G-11.

---

## 8. Backend Work Items (Phase 2A, when authorized)

- Per-tool audit module: record the registered name, input / output schema,
  and side-effect classification for each Phase 2A candidate.
- Extend the controlled execution chain's allowlist gate to admit per-tool
  audited read-only tools (generalize beyond the single `clarify` entry).
- Per-tool output validation (size, serialization, redaction) reusing the
  Phase 1G output rules.
- Per-tool audit records (pre / post execution) extended to carry the tool name.
- Route governance transition planned and reviewed (the exact new counts will
  be recorded when the slice is implemented).

No backend work is performed by Phase 1G-11.

---

## 9. Frontend Work Items (Phase 2A, when authorized)

- Tools panel: surface Phase 2A candidate tools as individually authorized.
- Execute UI: generalize the clarify-only workbench to the per-tool authorized
  set.
- Audit Viewer: show the tool name per audit event.
- Theme parity across all five frozen themes for any new UI.

No frontend work is performed by Phase 1G-11.

---

## 10. Audit Work Items (Phase 2A, when authorized)

- Pre / post execution audit records carry the tool name and a per-tool
  redacted argument summary.
- Audit Viewer whitelist normalization extended to the new tool outputs.
- No raw token / full `tokenHash` / raw arguments / secrets / callable repr in
  any audit surface.

No audit work is performed by Phase 1G-11.

---

## 11. Safety Gates (Phase 2A, when authorized)

Each Phase 2A candidate must pass:

- read-only proof (no writes, no shell, no Provider, no production, no side
  effect);
- per-tool audit (registered name, input / output schema);
- output validation (size, serialization, redaction);
- controlled execution chain integration (confirmation token, digest,
  pre-execution audit, handler lookup, dispatch, post-execution audit);
- backend, frontend, smoke, memory-check, dev-check gates;
- production isolation (PID `1962` or refreshed baseline unaffected);
- route governance review (intentional changes only, reviewed and gated).

Any invariant break is a P0 and stops the slice.

---

## 12. Test Plan (Phase 2A, when authorized)

- Per-tool unit tests (input validation, output bounding, redaction).
- Per-tool integration tests (dry-run → execute chain).
- Allowlist tests (only per-tool audited tools execute; others blocked).
- Route governance tests (new counts recorded and asserted).
- Smoke / E2E tests (both blocked + completed profiles per tool).
- Audit tests (tool name recorded; no raw token / hash / arguments / secrets).
- Production isolation tests (no `~/.hermes`, no production `state.db`).

No tests are written by Phase 1G-11.

---

## 13. Acceptance Criteria (Phase 2A, when authorized)

1. read-only multi-tool execution delivered end-to-end;
2. every added tool per-tool audited and individually authorized;
3. `STATIC_ALLOWLIST` expansion (if any) is per-tool audited — never blanket;
4. all Phase 1G safety invariants still hold;
5. raw token / full `tokenHash` / raw arguments / secrets / callable repr never
   exposed;
6. no `~/.hermes` access; no production `state.db` access;
7. backend, frontend, smoke, memory-check, dev-check gates pass;
8. Production Gateway unaffected;
9. the slice is committed and pushed under its own authorization.

---

## 14. Rollback Plan (Phase 2A, when authorized)

- No automatic rollback during execution.
- If rollback is needed: **stop and request user confirmation** first.
- Use a new `git revert` commit — never `git reset --hard`, never force push,
  never production state mutation.
- A per-tool candidate can be removed from the execution surface independently
  of the others (per-tool authorization is individually reversible).
- See `docs/webui/phase-1g-05-ops-and-rollback-runbook.md`.

---

## 15. Risks (Phase 2A, when authorized)

See the Phase 2 risks in `docs/webui/phase-1g-05-risk-register.md` §14
addendum:

- R2A-01: expanding beyond clarify may introduce unintended tool execution;
- R2A-02: read-only tool boundaries may be ambiguous;
- R2A-03: Provider integration must remain out of Phase 2A;
- R2A-04: Tool write must remain out of Phase 2A;
- R2A-05: audit volume may grow with more tools.

Each risk has a mitigation recorded in the risk register.

---

## 16. Expected Commit Strategy (Phase 2A, when authorized)

- One or more conventional-commit commits under `docs(webui)`, `feat(webui)`,
  `test(webui)` scopes as appropriate.
- Each commit respects the Phase 1G forbidden-file list (no `hermes_cli/` /
  `apps/` / `tests/` / `scripts/` / `toolsets.py` changes outside the slice's
  explicit scope; no runtime JSONL; no `.claude/`; no `*.log`).
- Push only with `git push origin dev-huangruibang`.
- No force push / rebase / `git reset --hard`.

Phase 1G-11 creates no Phase 2A commits.

---

## 17. Phase 1G-11 Boundary (Restated)

Phase 1G-11:

- plans Phase 2A (this document);
- does **not** audit any candidate tool in detail;
- does **not** add any tool to the execution surface;
- does **not** expand `STATIC_ALLOWLIST`;
- does **not** change route governance;
- does **not** write any Phase 2A backend / frontend / test code;
- does **not** start Phase 2A implementation.

Phase 2A starts only after the user separately authorizes it.

---

## 18. Cross-References

- Phase 1G-11 seal & Phase 2 unlock:
  `docs/webui/phase-1g-11-final-release-seal-and-phase-2-unlock.md`.
- Phase 1G final release seal: `docs/webui/phase-1g-final-release-seal.md`.
- Phase 2 unlock plan: `docs/webui/phase-2-unlock-plan.md`.
- Phase 1G-00 tool execution safety scope:
  `docs/webui/phase-1g-00-tool-execution-safety-scope.md`.
- Risk register: `docs/webui/phase-1g-05-risk-register.md`.
- Implementation plan: `docs/webui/phase-1-implementation-plan.md`.

---

*Phase 2A Real Tool Execution MVP Plan — planning only, not implemented.
Phase 2A will deliver real, read-only, per-tool-audited, individually-authorized
multi-tool execution as the first Phase 2 slice. Phase 1G-11 plans Phase 2A but
does not implement it, does not audit any candidate tool in detail, does not
expand `STATIC_ALLOWLIST`, and does not change route governance. Phase 2A
implementation begins only after the user separately authorizes it.*
