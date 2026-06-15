# Phase 3 Planning — Post-Phase-2 Strategy, Scope Freeze & Risk Gate

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3 Planning |
| Title | Post-Phase-2 Strategy, Scope Freeze & Risk Gate |
| Status | Planning complete; Phase 3A not started |
| Date | 2026-06-15 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3-PLANNING-001` |
| Planning type | docs-only — no product code, no frontend, no backend, no script |
| Input HEAD | `bb373d61e98d57e9ea470fde7162f706bd32f23e` |
| Input HEAD message | `chore(webui): harden dev console ux` |
| Predecessor | Phase 2E-H1 (Console UX Hardening) — completed and pushed |

> **This is a planning phase.** It evaluates the Phase 3 direction, freezes the
> Phase 3A scope, records the risk register and GO/NO-GO decision, and prepares
> the Phase 3A execution prompt. **Phase 3A is not implemented here.** No real
> provider is enabled, no production rollout is performed, no shell / database /
> external-service write is introduced, and no new HTTP route is added.

---

## 1. Phase 3 Planning ID

`PHASE-3-PLANNING-001`

---

## 2. Current Baseline

| Item | Value |
|------|-------|
| Branch | `dev-huangruibang` |
| Local HEAD | `bb373d61e98d57e9ea470fde7162f706bd32f23e` |
| Remote HEAD | `bb373d61e98d57e9ea470fde7162f706bd32f23e` |
| Merge base | `bb373d61e98d57e9ea470fde7162f706bd32f23e` |
| Ahead / behind | 0 / 0 |
| Tracked worktree | clean |
| Only untracked | `.claude/` |
| HERMES_HOME | `/Users/huangruibang/Code/hermes-home-dev` |
| Production Gateway expected PID | `28428` |
| Production Gateway observed PID | `28428` |
| Production Gateway process count | `1` |
| Dev Gateway | stopped |
| Dashboard | not started |
| 5180 / 5181 | free / free |
| `~/.hermes` access | none |
| Production `state.db` access | none |

### Route governance baseline (frozen)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 34 |
| Runtime routes | 34 |
| Tool GET | 5 |
| Tool write HTTP route | 0 |
| Tool dry-run route | 1 |
| Tool execution route | 1 |

### Completed capability chain

```
Read-only Tools (2A)
  → Provider Fake Round-trip (2B)
    → Sandbox Write (2C)
      → Rollback (2C-H1)
        → Durable Audit Store / Indexing (2D)
          → Audit Store Hardening (2D-H1)
            → Unified Dev Console (2E)
              → Frontend UX Hardening (2E-H1)
```

Phase 1G = SEALED. Phase 2 = functionally complete for dev-only controlled tool
execution and auditability.

---

## 3. Phase 2 Final Capability Map (summary)

| Phase | Capability |
|-------|------------|
| 2A / 2A-H1 | Read-only multi-tool execution (6 tools), dry-run / execute / audit, adversarial-review closure |
| 2B / 2B-H1 | Provider fake (offline) round-trip, real provider blocked by default, write preview-only, PEM / secret redaction |
| 2C | Dev-sandbox write tools (write / append / patch / readback), write preview / execute, rollback manifest generation |
| 2C-H1 | Rollback execute, file-backed confirmation-token TTL, persistent single-use protection |
| 2D | Durable audit store (`audit_schema_v2`), unified sanitizer, append-only writer, index, cursor pagination, rotation, corruption quarantine |
| 2D-H1 | Audit storage hardening (10-lens), consistency / stress / security closure |
| 2E | Unified developer console (`/#/console`), 7 sections, cross-navigation |
| 2E-H1 | Console UX hardening (9-lens), blocked-reason catalogue fix, no-leak closure |

Full detail: [phase-2-final-capability-map.md](phase-2-final-capability-map.md).

---

## 4. Phase 2 Remaining P2 (carried forward, non-blocking)

| ID | Item | Owner / phase |
|----|------|---------------|
| P2 | Real-vendor provider network call not wired | Separately-authorized future phase (Phase 3B) |
| P2 | Token encryption at rest | Future phase |
| P2 | Multi-user namespace (token, audit) | Future phase |
| P2 | Audit retention deletion / compression | Phase 3E candidate |
| P2 | Audit encryption at rest | Phase 3E candidate |
| P2 | Advanced full-text indexing | Phase 3E candidate |
| P2 | Full WCAG 2.1 AA certification | Future phase |
| P2 | Advanced visual design system / motion polish | Future phase |
| P2 | Provider streaming / long multi-turn memory | Future phase |
| P2 | Future Production Gateway PID drift on host reboot | Smoke harness fails closed; an authorized refresh phase updates the constant |

None of these block Phase 3 planning or Phase 3A.

---

## 5. Phase 3 Objective

Phase 3 grows the Dev WebUI from a **demonstrable, auditable single-step tool
execution workbench** into the next layer of agent value — while preserving
every Phase 1G / Phase 2 safety invariant. The objective of this planning
phase is:

1. Decide which Phase 3 direction delivers the most value at the lowest risk.
2. Freeze the Phase 3A scope, entry criteria, exit criteria, and risk model.
3. Record the GO / NO-GO decision.
4. Prepare the Phase 3A execution prompt — without executing it.

Phase 3 is **not** a single deliverable. It is a roadmap of separately
authorized slices (3A → 3B → 3C → 3D → 3E), each individually gated.

---

## 6. Candidate Options

Five candidate directions were evaluated. Full scoring in
[phase-3-options-evaluation.md](phase-3-options-evaluation.md).

| Option | Direction |
|--------|-----------|
| A | Real Provider Controlled Integration |
| B | Production Pilot Readiness |
| C | Agent Workflow Automation |
| D | Plugin / Tool Registry Expansion |
| E | Audit / Compliance Advanced Phase |

---

## 7. Evaluation Matrix (summary)

| Option | User Value | Readiness | Security Risk | Complexity | Demo Value | Production Dep. | Reversibility | Recommendation |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A — Real Provider Controlled Integration | 5 | 3 | 5 | 4 | 5 | 2 | 4 | Phase 3B |
| B — Production Pilot Readiness | 3 | 4 | 4 | 3 | 2 | 5 | 3 | Phase 3D |
| C — Agent Workflow Automation | 4 | 5 | 2 | 3 | 5 | 1 | 5 | **Phase 3A** |
| D — Plugin / Tool Registry Expansion | 3 | 3 | 4 | 4 | 3 | 1 | 3 | Phase 3C |
| E — Audit / Compliance Advanced Phase | 2 | 4 | 1 | 3 | 2 | 1 | 4 | Phase 3E |

Scoring: 1–5. For Security Risk, 5 = highest risk. For Complexity, 5 = hardest.
For Production Dependency, 5 = high dependency. For Reversibility, 5 = easy
rollback.

---

## 8. Recommended Path

```
Phase 3A — Dev-only Agent Workflow MVP                 ← recommended first slice
Phase 3B — Real Provider Read-only Controlled Integration
Phase 3C — Plugin / Capability Registry
Phase 3D — Production Pilot Readiness
Phase 3E — Audit Compliance Advanced
```

**Rationale:** Phase 3A (Option C) is the only candidate that simultaneously
delivers high user value, has maximum technical readiness (it reuses 100 % of
the Phase 2A–2E capabilities with no new external surface), carries the lowest
security risk, is fully dev-only, is highly reversible, and naturally becomes
the *container* that later phases (real provider, plugin registry) plug into.
It is selected as Phase 3A.

---

## 9. Rejected / Deferred Paths

| Path | Disposition | Reason |
|------|-------------|--------|
| A — Real Provider as Phase 3A | Deferred to 3B | Highest security risk (API key, network, prompt injection, token leak). Needs a workflow container + hardened audit first. Phase 3A keeps provider write blocked and real provider blocked. |
| B — Production Pilot as Phase 3A | Deferred to 3D | Requires production dependency (5/5); capabilities are still dev-only (write / audit / token stores are dev-only). Premature until core agent value (workflow + real provider) exists. |
| D — Plugin Registry as Phase 3A | Deferred to 3C | Supply-chain / dynamic-loading risk; needs a capability / policy framework first. |
| E — Audit Compliance Advanced as Phase 3A | Deferred to 3E | Low marginal user value now — Phase 2D-H1 already hardened the audit store. Over-engineering if scheduled before core agent capability. |

These are **not cancelled** — they are sequenced behind Phase 3A.

---

## 10. Phase 3A Proposed Scope

**Dev-only Agent Workflow MVP.**

| # | Allowed |
|---|---------|
| 1 | Workflow definition schema |
| 2 | Workflow plan / dry-run preview |
| 3 | Step list |
| 4 | Manual step execution (operator-driven) |
| 5 | Approval gates between steps |
| 6 | Read-only tool step (reuse 2A) |
| 7 | Fake provider step (reuse 2B) |
| 8 | Sandbox write preview step (reuse 2C) |
| 9 | Rollback reference step (reuse 2C-H1) |
| 10 | Audit linkage (reuse 2D) |
| 11 | Workflow timeline UI (reuse console shell) |
| 12 | Workflow state stored under dev `HERMES_HOME` |
| 13 | Console "Workflow" section |
| 14 | Tests |
| 15 | Smoke |

Full freeze: [phase-3-scope-freeze.md](phase-3-scope-freeze.md).

---

## 11. Phase 3A Non-Goals

| # | Forbidden |
|---|-----------|
| 1 | Real provider vendor call |
| 2 | Provider auto-write |
| 3 | Autonomous write execution |
| 4 | Shell command execution |
| 5 | Database mutation |
| 6 | External service write |
| 7 | Production rollout |
| 8 | `~/.hermes` access |
| 9 | Production `state.db` access |
| 10 | Dynamic plugin loading |
| 11 | Background autonomous agent |
| 12 | Schedule / cron automation |
| 13 | Multi-user workflow namespace |
| 14 | Production workflow store |

---

## 12. Phase 3A Entry Criteria

Phase 3A may start only when **all** are true:

1. The user explicitly asks for the Phase 3A execution prompt / implementation.
2. Phase 3A is separately authorized by the user.
3. Branch = `dev-huangruibang`; tree clean (only `.claude/` untracked).
4. Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1) or an explicitly
   approved, separately-authorized change.
5. Production Gateway PID healthy (expected `28428`) or consciously refreshed
   by a separately authorized safety phase.
6. `~/.hermes` and production `state.db` not accessed.
7. This planning phase committed and pushed (`PHASE-3-PLANNING-001`).
8. The Phase 3A execution prompt in [phase-3a-prompt.md](phase-3a-prompt.md) is
   the approved starting brief.

---

## 13. Phase 3A Exit Criteria

Phase 3A exits when all hold:

1. Workflow schema + planner + dry-run preview implemented.
2. Manual step execution with approval gates enforced.
3. Read-only / fake-provider / sandbox-write-preview / rollback-reference steps
   work end-to-end and reuse the Phase 2 capabilities.
4. Audit linkage works (every step links to its audit events).
5. Workflow timeline UI works inside the console.
6. No autonomous write; no real provider; no shell / db / external write.
7. Route governance unchanged or explicitly approved.
8. All tests pass; smoke pass; memory-check / dev-check PASS.
9. Production untouched (PID `28428`, no `~/.hermes` / `state.db` access).
10. Committed and pushed under its own authorization.

---

## 14. Phase 3A Risk Model

| Tier | Count | Examples |
|------|-------|----------|
| P0 | see register | autonomous write, real provider enabled, shell/db/external write, production rollout, route drift, secret exposure |
| P1 | see register | workflow state corruption, approval-gate bypass, audit link broken, write-preview step writing, smoke failure |
| P2 | see register | real provider deferred, plugin registry deferred, scheduling deferred, multi-user deferred |

Full register: [phase-3-risk-register.md](phase-3-risk-register.md).

---

## 15. GO / NO-GO Recommendation

| Field | Value |
|-------|-------|
| Decision | **GO** for Phase 3A prompt preparation |
| Recommended Phase 3A | Dev-only Agent Workflow MVP |
| Human approval required before execution | yes |
| Phase 3A may start | only after the user explicitly asks |
| Phase 3A may code | only inside `dev-huangruibang`, separately authorized |
| Phase 3A may use real provider | no |
| Phase 3A may write | preview / sandbox only (reuse Phase 2C gate); no autonomous write |
| Phase 3A may production rollout | no |
| Shell / DB / external-service write | no |

Full decision: [phase-3-go-no-go.md](phase-3-go-no-go.md).

---

## 16. Safety Boundaries Preserved by This Planning Phase

No production rollout. No `~/.hermes` access. No production `state.db` access.
No shell command execution. No database mutation. No external service write.
No real provider vendor network call. No Provider auto-write / auto-rollback.
No new HTTP route. No Tool write HTTP route. No Provider route. No audit /
token / rollback-manifest / runtime-JSONL artifact committed. No `.claude/`
committed. No API key / raw token / full tokenHash / raw arguments / callable
repr exposed. Route governance stays 34 / 34 / 5 / 0 / 1 / 1. Production
Gateway PID `28428` untouched.

---

## 17. Deliverables of This Planning Phase

| Deliverable | Path |
|-------------|------|
| Phase 3 planning (this doc) | `phase-3-planning.md` |
| Options evaluation | `phase-3-options-evaluation.md` |
| Scope freeze | `phase-3-scope-freeze.md` |
| Risk register | `phase-3-risk-register.md` |
| GO / NO-GO | `phase-3-go-no-go.md` |
| Phase 3A execution brief | `phase-3a-execution-brief.md` |
| Phase 3A prompt draft | `phase-3a-prompt.md` |
| Phase 2 final capability map | `phase-2-final-capability-map.md` |
| Phase 2 → Phase 3 transition | `phase-2-to-phase-3-transition.md` |

Updated: `phase-1-implementation-plan.md`, `phase-1g-05-risk-register.md`,
`phase-2-unlock-plan.md`, `phase-2e-h1-frontend-ux-hardening.md`.

---

## 18. Cross-References

- [Phase 2 final capability map](phase-2-final-capability-map.md)
- [Phase 2 → Phase 3 transition](phase-2-to-phase-3-transition.md)
- [Phase 3 options evaluation](phase-3-options-evaluation.md)
- [Phase 3 scope freeze](phase-3-scope-freeze.md)
- [Phase 3 risk register](phase-3-risk-register.md)
- [Phase 3 GO / NO-GO](phase-3-go-no-go.md)
- [Phase 3A execution brief](phase-3a-execution-brief.md)
- [Phase 3A prompt draft](phase-3a-prompt.md)
- [Phase 2E-H1 frontend UX hardening](phase-2e-h1-frontend-ux-hardening.md)
- [Phase 2 unlock plan](phase-2-unlock-plan.md)
- [Phase 1G-05 risk register](phase-1g-05-risk-register.md)

---

## 19. Conclusion

Phase 3 Planning is complete. Phase 2 is documented as functionally complete
for dev-only controlled tool execution, provider fake round-trip, sandbox
write, rollback, durable audit storage, unified console, and frontend UX
hardening. Five Phase 3 candidate directions were evaluated. The recommended
Phase 3 path is **Dev-only Agent Workflow MVP → Real Provider → Plugin
Registry → Production Pilot → Audit Compliance**. The selected Phase 3A is
**Dev-only Agent Workflow MVP**. Phase 3A was **not** executed during this
planning phase. No product code, frontend, backend, or script was modified —
this is a docs-only planning phase. Route governance stays 34 / 34 / 5 / 0 /
1 / 1 and the Production Gateway PID `28428` is untouched.
