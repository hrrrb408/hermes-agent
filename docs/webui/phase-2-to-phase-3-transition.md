# Phase 2 → Phase 3 Transition

## Document Information

| Field | Value |
|-------|-------|
| Phase | 2 → 3 Transition |
| Title | Phase 2 Final → Phase 3 Planning Transition |
| Status | Transition recorded |
| Date | 2026-06-15 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3-PLANNING-001` |

> Companion to [phase-2-final-capability-map.md](phase-2-final-capability-map.md)
> and [phase-3-planning.md](phase-3-planning.md). This document records the
> transition from the functionally-complete Phase 2 into Phase 3 planning.

---

## 1. Where Phase 2 Ends

Phase 2 ends at **Phase 2E-H1 — Console UX Hardening**:

- Phase 2E-H1 = completed and pushed (`bb373d61e98d57e9ea470fde7162f706bd32f23e`).
- The unified developer console (`/#/console`) is hardened through 9 lenses.
- The `blocked_write_forbidden_path` catalogue drift is corrected and the
  backend vocabulary is pinned as a contract.
- Route governance stays 34 / 34 / 5 / 0 / 1 / 1.
- Production Gateway PID `28428` untouched.
- Phase 1G = SEALED; Phase 2 = functionally complete.

Phase 2 delivered, in risk order: read-only tool execution (2A) → fake
provider round-trip (2B) → sandbox write (2C) → rollback execution + file-backed
token TTL (2C-H1) → durable audit store (2D) → audit hardening (2D-H1) →
unified console (2E) → console UX hardening (2E-H1).

---

## 2. Why Transition Now

- Every Phase 2 slice is delivered, hardened, and pushed.
- The capability chain (read / provider fake / write / rollback / audit /
  console) is closed and demonstrable.
- There are no open P0 or P1 risks in Phase 2.
- The carry-forward items are all P2 (non-blocking) and naturally map onto
  future Phase 3 slices (real provider, audit compliance advanced, etc.).

There is no remaining Phase 2 slice to deliver. The next value is a new layer
(agent workflow) built on top of the Phase 2 capabilities — i.e. Phase 3.

---

## 3. What Is Preserved Across the Transition

Phase 3 inherits every frozen Phase 1G / Phase 2 invariant:

- `STATIC_ALLOWLIST` per-tool audited expansion only.
- The controlled-execution chain as the template for any execution surface.
- Route governance 34 / 34 / 5 / 0 / 1 / 1 (no new route by default).
- Raw token / full `tokenHash` / raw arguments / secrets / callable repr never
  exposed.
- `~/.hermes` and production `state.db` never accessed.
- WebUI binds to `127.0.0.1` only; dev `HERMES_HOME` enforced (fail-closed).
- Audit JSONL / token / rollback-manifest stores never committed; `.claude/`
  never committed.
- Force push / rebase / `git reset --hard` never attempted.
- Production Gateway never stopped / restarted / replaced / signaled /
  reconfigured.

---

## 4. What Changes at the Transition

| Aspect | Phase 2 | Phase 3 (planned) |
|--------|---------|-------------------|
| Shape | vertical capability slices (one capability each) | a workflow layer that composes Phase 2 capabilities |
| Delivery model | per-slice verticals, each separately authorized | same: each Phase 3 slice separately authorized |
| Default risk posture | dev-only, read-first / fake-first | dev-only, no new external surface in 3A |
| Real provider | blocked (2B/2B-H1) | still blocked in 3A; read-only candidate for 3B |
| Autonomous execution | none | still none in 3A (manual step + approval gates) |
| Routes | unchanged | unchanged by default (reuse `mode` branches) |

---

## 5. The Phase 3 Roadmap (recommended)

```
Phase 3A — Dev-only Agent Workflow MVP            (reuses 2A/2B/2C/2C-H1/2D/2E)
Phase 3B — Real Provider Read-only Controlled Integration
Phase 3C — Plugin / Capability Registry
Phase 3D — Production Pilot Readiness
Phase 3E — Audit Compliance Advanced
```

See [phase-3-options-evaluation.md](phase-3-options-evaluation.md) for the
scoring and rationale.

---

## 6. Transition Gate (this planning phase)

This transition is recorded by the docs-only planning phase
`PHASE-3-PLANNING-001`:

- 7 required Phase 3 docs + 2 transition docs authored.
- 4 existing docs updated with Phase 3 pointers.
- No product / frontend / backend / script change.
- Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1).
- Production Gateway PID `28428` unchanged.
- Phase 3A not started.

---

## 7. What the Transition Does Not Do

It does **not** start Phase 3A, enable a real provider, perform autonomous
write, add shell / db / external write, roll out to production, access
`~/.hermes` or production `state.db`, add a route, or change any safety
boundary.

---

## 8. Next Step

Ask for the **Phase 3A execution prompt** when ready (see
[phase-3a-prompt.md](phase-3a-prompt.md)). Until then, Phase 3A remains not
started and the system stays at the Phase 2E-H1 baseline.
