# Phase 2 Unlock Plan — `PHASE-2-UNLOCK-1G-11-001`

> **Phase 2A Implementation Update:** Phase 2A (the first Phase 2 vertical
> slice — read-only multi-tool execution MVP) has been implemented and verified.
> Entry condition 8 ("Phase 2A separately authorized by the user") was satisfied
> by the explicit Phase 2A task authorization. STATIC_ALLOWLIST expanded from
> `frozenset({"clarify"})` to 6 read-only tools; route governance remains
> 34/34/5/0/1/1 (no new routes). Provider (2B) and Tool write (2C) remain
> deferred. See [phase-2a-real-tool-execution-mvp.md](phase-2a-real-tool-execution-mvp.md).

## Document Information

| Field | Value |
|-------|-------|
| Phase | 2 (unlocked) |
| Title | Phase 2 Unlock Plan |
| Status | Planning (Phase 2 unlocked; no Phase 2 implementation started) |
| Date | 2026-06-14 |
| Branch | `dev-huangruibang` |
| Phase 2 Unlock ID | `PHASE-2-UNLOCK-1G-11-001` |
| Final Seal ID | `FINAL-SEAL-1G-11-001` |
| Baseline input HEAD | `3c6ae479b37f3cb4e02c18f6dbef97334b1355e1` |
| Authorizing Human Decision | `HUMAN-DECISION-1G-10B-001` (GO) |
| Scope | Define the Phase 2 delivery model, roadmap, boundaries, and entry / exit conditions. No code change. |

---

## 1. Phase 2 Unlock Rationale

Phase 1G delivered a clarify-only controlled execution MVP that passed the Pilot
(15 / 15 scenarios), received a human approver GO (`HUMAN-DECISION-1G-10B-001`),
and is sealed (`FINAL-SEAL-1G-11-001`). Phase 1G's safety boundary — route
governance, `STATIC_ALLOWLIST = frozenset({"clarify"})`, the controlled
execution chain, and the production isolation contract — is now the frozen
release baseline.

Phase 2 is unlocked so the Dev WebUI can grow **real capabilities** beyond the
single `clarify` tool, while inheriting every Phase 1G safety invariant. Phase 2
is where actual product value accrues; Phase 1G was the safety scaffold.

---

## 2. Why Phase 1G Should Stop Here

Phase 1G's progression slowed because each safety gate was split into many
micro-phases (1G-04-01 … 1G-04-31, then 1G-05 … 1G-10B). That was appropriate
while the controlled execution chain was being built and audited — every new
execution surface needed its own scope freeze and its own review. But the chain
is now sealed, the Pilot passed, and the human approver signed GO.

Continuing to add 1G-`xx` micro-phases would add documentation overhead without
adding capability. The right move is to **seal Phase 1G** and switch to a
different delivery model for the next capability increments.

Phase 1G therefore stops here. No further 1G-`xx` seal / push / gate
micro-phases will be created.

---

## 3. New Delivery Model

Phase 2 uses **vertical feature slices**, not safety-gate micro-phases.

```
Phase 1G (sealed):  scaffold + clarify-only MVP + Pilot + human GO
                          │
                          ▼
Phase 2 (unlocked):  vertical feature slices
   2A  real read-only multi-tool execution
   2B  Provider Schema / API controlled integration
   2C  tool write execution (stronger confirmation / rollback / sandbox)
   2D  advanced audit storage / search / pagination / rotation
   2E  frontend product workflow and operator polish
```

Rules for the new delivery model:

- **Do not continue micro-phases for Phase 1G.** Phase 1G is sealed.
- **Use vertical feature slices in Phase 2.** Each slice delivers one coherent
  capability end-to-end (backend + frontend + tests + docs).
- **Each Phase 2 slice should deliver a usable capability, not only
  documentation.** A slice whose entire output is docs is not a Phase 2 slice.
- **Each Phase 2 slice is separately authorized** before implementation begins.
- **Each Phase 2 slice preserves every Phase 1G safety invariant.** Any
  invariant break is a P0 and stops the slice.
- **Allowlist expansion is still per-tool audited.** No tool is added to the
  execution surface without a full audit of its registered name, input / output
  schema, and side effects.

---

## 4. Phase 2 Roadmap

| Phase | Target | Write? | Provider? |
|-------|--------|--------|-----------|
| 2A | Real Tool Execution MVP — read-only multi-tool execution | no (read-only) | no |
| 2B | Provider Schema / Provider API controlled integration | no | yes (controlled) |
| 2C | Tool write execution under stronger confirmation / rollback / sandbox | yes (dev, sandboxed) | no |
| 2D | Advanced audit storage / search / pagination / rotation | no | no |
| 2E | Frontend product workflow and operator polish | no | no |

The slices are ordered by risk: read-only first (2A), then Provider (2B), then
write (2C), then audit hardening (2D), then polish (2E). Slices may be
re-sequenced by the user, but each remains individually authorized.

---

## 5. Phase 2 Boundaries

Phase 2 inherits and must not weaken the Phase 1G frozen boundary:

| Boundary | Phase 2 requirement |
|----------|---------------------|
| `STATIC_ALLOWLIST` | per-tool audited expansion only; never blanket expansion |
| Raw confirmation token | never in response / DOM / log / console / storage / audit event |
| Full `tokenHash` | never surfaced |
| Raw arguments | never in the audit viewer |
| Secrets / API keys / credentials | never logged or committed |
| Callable / function repr | never exposed |
| Audit JSONL / `.claude/` | never committed |
| `~/.hermes` | never accessed |
| Production `state.db` | never accessed |
| WebUI bind | `127.0.0.1` only |
| Dev `HERMES_HOME` isolation | enforced, fail-closed |
| Force push / rebase / `git reset --hard` | never attempted |

---

## 6. Phase 2A Target

**Real Tool Execution MVP — read-only multi-tool execution.**

User-facing outcome: an operator can run more than just `clarify` through the
controlled execution chain, provided each additional tool is read-only,
individually audited, and individually authorized.

Read-only first principle: every Phase 2A candidate tool must be provably
side-effect-free (no writes, no shell, no network mutation, no Provider call).
Candidate tools are discussed in `docs/webui/phase-2a-real-tool-execution-mvp-plan.md`
but are **not** implemented by Phase 1G-11.

---

## 7. Phase 2B Target

**Provider Schema / Provider API controlled integration.**

User-facing outcome: the Dev WebUI can exercise a controlled Provider path
(sending a tool schema to a Provider, calling a Provider API) under explicit
kill switches, dev-only guards, full audit, and confirmation gates.

Phase 2B is where `providerSchemaSent` / `providerApiCalled` may move from
`false` to `true` — but only on an explicitly authorized, fully audited,
dev-only path. Until 2B is separately authorized, both remain `false`.

---

## 8. Phase 2C Target

**Tool write execution under stronger confirmation / rollback / sandbox.**

User-facing outcome: a bounded set of write tools (e.g. dev-only file write)
can execute under a stronger confirmation model, rollback, and a sandboxed
target, never touching production.

Phase 2C is the highest-risk slice. It must not start until 2A is stable and
the write boundary (confirmation, rollback, sandbox, dev-only target) is
individually designed and authorized.

---

## 9. Phase 2D Target

**Advanced audit storage / search / pagination / rotation.**

User-facing outcome: the audit subsystem supports cursor-based pagination,
multi-file JSONL rotation, race-safe reads, and read-only full-text search over
audit history. This closes the carried-over P2-02 / P2-03 / P2-04 / P2-08 items.

Phase 2D keeps the read-only, redacted, whitelist-normalized audit contract and
the per-request parse cap as a backstop.

---

## 10. Phase 2E Target

**Frontend product workflow and operator polish.**

User-facing outcome: the Dev WebUI product surface is polished for daily
operator use — micro-interactions, accessibility edge cases, operator workflow
shortcuts, and the carried-over P2-07 polish items.

Phase 2E is non-functional and does not touch any safety boundary.

---

## 11. Required Safety Invariants Carried Forward

Every Phase 2 slice must preserve:

1. `STATIC_ALLOWLIST` expansion is per-tool audited (registered name, input /
   output schema, side effects).
2. The controlled execution chain is the template for any new execution surface.
3. Raw token / full `tokenHash` / raw arguments / secrets / callable repr are
   never exposed.
4. Production `~/.hermes` and production `state.db` are never accessed.
5. The WebUI binds to `127.0.0.1` only.
6. Dev `HERMES_HOME` isolation is enforced (fail-closed).
7. Audit JSONL and `.claude/` are never committed.
8. Force push / rebase / `git reset --hard` are never attempted.
9. The Production Gateway is never stopped / restarted / replaced / signaled /
   reconfigured by Dev WebUI work.

---

## 12. Explicit Non-Goals (Phase 2 Overall)

Phase 2 does **not**, across all slices:

- perform a public production rollout (the WebUI binds to `127.0.0.1` only);
- access production `~/.hermes` or production `state.db`;
- stop / restart / replace / signal / reconfigure the Production Gateway;
- blanket-expand `STATIC_ALLOWLIST` without per-tool audit;
- expose raw token / full `tokenHash` / raw arguments / secrets / callable repr;
- commit audit JSONL or `.claude/`;
- attempt force push / rebase / `git reset --hard`;
- create release tags or GitHub Releases without explicit user authorization.

---

## 13. Entry Conditions

Phase 2 may start when **all** of the following are true:

| # | Entry condition | Met by Phase 1G-11 |
|---|-----------------|--------------------|
| 1 | Phase 1G-11 pushed | ✅ (this phase pushes) |
| 2 | `origin/dev-huangruibang` points to the Phase 1G final seal commit | ✅ |
| 3 | Phase 1G route governance unchanged (34 / 34 / 5 / 0 / 1 / 1) | ✅ |
| 4 | `STATIC_ALLOWLIST` unchanged (`frozenset({"clarify"})`) | ✅ |
| 5 | Production Gateway PID gate healthy (`1962`) or consciously refreshed by a separately authorized safety phase | ✅ |
| 6 | Human approver GO recorded (`HUMAN-DECISION-1G-10B-001`) | ✅ |
| 7 | Release authorization granted | ✅ |
| 8 | Phase 2A separately authorized by the user | ⏳ required before 2A implementation |

Conditions 1–7 are met by Phase 1G-11. Condition 8 is the per-slice gate that
must be satisfied before Phase 2A implementation begins.

---

## 14. Exit Conditions

Phase 2 (as a whole) is complete when all of 2A–2E are individually delivered
and accepted. Each slice has its own exit conditions; for example, Phase 2A
exits when:

- read-only multi-tool execution is delivered end-to-end;
- every added tool is per-tool audited and individually authorized;
- route governance changes (if any) are intentional, reviewed, and gated;
- all Phase 1G safety invariants still hold;
- backend, frontend, smoke, memory-check, and dev-check gates pass;
- the Production Gateway is unaffected;
- the slice is committed and pushed under its own authorization.

Phase 2 does not exit as a single event; it exits slice by slice.

---

## 15. Suggested Sequencing

```
2A (read-only multi-tool)  ←  recommended first slice
 └── 2B (Provider Schema / API, controlled)
      └── 2C (tool write, sandboxed)        ←  highest risk; last execution slice
           └── 2D (audit hardening)
                └── 2E (frontend polish)
```

2A → 2B → 2C is the risk-ordered execution sequence. 2D and 2E may run in
parallel with the later execution slices. The user may re-sequence any slice,
but each remains individually authorized.

---

## 16. Cross-References

- Phase 1G-11 seal & Phase 2 unlock:
  `docs/webui/phase-1g-11-final-release-seal-and-phase-2-unlock.md`.
- Phase 1G final release seal: `docs/webui/phase-1g-final-release-seal.md`.
- Phase 2A MVP plan: `docs/webui/phase-2a-real-tool-execution-mvp-plan.md`.
- Human approver final decision: `docs/webui/phase-1g-10b-human-approver-final-decision.md`.
- Implementation plan: `docs/webui/phase-1-implementation-plan.md`.
- Risk register: `docs/webui/phase-1g-05-risk-register.md`.

---

*Phase 2 Unlock Plan — `PHASE-2-UNLOCK-1G-11-001`. Phase 2 is **unlocked** for
separately authorized work, using vertical feature slices (2A read-only
multi-tool → 2B Provider → 2C tool write → 2D audit hardening → 2E polish).
Phase 1G is sealed; no further 1G-`xx` micro-phases will be created. Each
Phase 2 slice preserves every Phase 1G safety invariant and is individually
authorized before implementation begins. Phase 2A implementation was not started
by Phase 1G-11.*
