# Phase 3 Options Evaluation

## Document Information

| Field | Value |
|-------|-------|
| Phase | 3 Planning |
| Title | Phase 3 Candidate Options Evaluation |
| Status | Evaluated |
| Date | 2026-06-15 |
| Branch | `dev-huangruibang` |
| Planning ID | `PHASE-3-PLANNING-001` |
| Evaluation ID | `PHASE-3-OPTIONS-EVAL-001` |

> Companion to [phase-3-planning.md](phase-3-planning.md). This document scores
> the five Phase 3 candidate directions and records the recommended ordering.

---

## 1. Scoring Dimensions

Each option is scored 1–5 across seven dimensions:

| Dimension | Meaning |
|-----------|---------|
| User value | Direct value to the operator / end user (5 = highest) |
| Technical readiness | How ready the current codebase is to support it with low new external surface (5 = most ready) |
| Security risk | Risk to the frozen safety boundary (5 = highest risk) |
| Implementation complexity | Engineering effort (5 = hardest) |
| Demo value | How demonstrable the outcome is (5 = highest) |
| Production dependency | How much it depends on production access / rollout (5 = high dependency) |
| Reversibility | How easily it can be rolled back (5 = easy rollback) |

Recommendation rule (from `phase-3-planning.md` §5): do **not** select the
highest-security-risk / lowest-readiness direction as Phase 3A; do **not**
select a direction that requires production rollout as Phase 3A; prefer
dev-only, auditable, reversible, demonstrable, boundary-clear directions.

---

## 2. Scoring Table

| Option | User Value | Readiness | Security Risk | Complexity | Demo Value | Production Dep. | Reversibility | Recommendation |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A — Real Provider Controlled Integration | 5 | 3 | 5 | 4 | 5 | 2 | 4 | Phase 3B |
| B — Production Pilot Readiness | 3 | 4 | 4 | 3 | 2 | 5 | 3 | Phase 3D |
| C — Agent Workflow Automation | 4 | 5 | 2 | 3 | 5 | 1 | 5 | **Phase 3A** |
| D — Plugin / Tool Registry Expansion | 3 | 3 | 4 | 4 | 3 | 1 | 3 | Phase 3C |
| E — Audit / Compliance Advanced Phase | 2 | 4 | 1 | 3 | 2 | 1 | 4 | Phase 3E |

---

## 3. Per-Option Detail

### Option A — Real Provider Controlled Integration

Extend the Phase 2B fake provider round-trip into a controlled real-vendor
integration: real provider adapter, API-key loading, request / response
redaction, timeout / retry / rate-limit, read-only real provider tool call,
real provider write preview-only, no auto-write / auto-rollback, full audit.

- **Strengths:** highest user value — moves the system from fake to real AI.
- **Risks:** API-key management, network call, provider prompt injection,
  provider tool-call hallucination, token / secret leakage, audit volume
  growth, real cost, flaky network, external dependency, possible boundary
  expansion.
- **Why not Phase 3A:** security risk is 5/5 and readiness is only 3/5. The
  real-vendor adapter is not wired (Phase 2B-H1 left it deferred), and wiring
  it before a workflow container exists concentrates risk in one slice.
  Phase 3A keeps provider write blocked and real provider blocked; Phase 3B
  introduces read-only real provider after the workflow container (3A) and the
  hardened audit (2D-H1) exist.

### Option B — Production Pilot Readiness

Package the current dev-only capabilities for a production pilot: rollout
checklist, config review, production audit separation, launchd / process
safety, rollback plan, observability, kill switches, operator manual, release
decision pack, human-approval template.

- **Strengths:** reduces launch risk.
- **Risks:** current capabilities are still dev-only (write / audit / token
  stores); production state must not be touched; needs human approval;
  conflicts with the dev-only boundary.
- **Why not Phase 3A:** production dependency is 5/5. There is no core agent
  value (workflow + real provider) yet to pilot. Scheduling it now packages a
  dev-only workbench as if it were production-ready. Deferred to Phase 3D,
  after 3A and 3B.

### Option C — Agent Workflow Automation

Chain the existing tools into a higher-layer automation workflow:
plan → dry-run → provider/tool → write preview → confirmation → execute →
rollback / audit. Workflow definition, state machine, step-by-step execution,
approval gates, pause / resume, workflow audit, workflow visualization.

- **Strengths:** best fit for the Hermes Agent long-term value; moves tool
  execution from single-step to structured agent workflow; reuses 100 % of
  Phase 2A–2E; dev-only; reversible; high demo value; becomes the container
  for later phases.
- **Risks:** state-machine complexity, more audit, more UI, provider still
  fake/blocked — all manageable inside the dev-only boundary.
- **Why Phase 3A:** highest readiness (5/5), lowest security risk (2/5), no
  production dependency (1/5), highest reversibility (5/5), high demo value.
  It is the only candidate that compounds every existing capability without
  introducing a new external surface.

### Option D — Plugin / Tool Registry Expansion

Move the tool system from a fixed allowlist to a structured plugin / tool
registry: plugin manifest, tool metadata schema, tool category, policy gates,
registry viewer, disabled tools, capability negotiation.

- **Strengths:** foundation for a future tool ecosystem.
- **Risks:** easily misread as "allow arbitrary plugin execution"; dynamic
  loading risk; supply-chain risk; complex policy.
- **Why not Phase 3A:** security risk 4/5 and readiness 3/5. Phase 3A forbids
  dynamic code loading; a registry needs a capability / policy framework
  first. Deferred to Phase 3C.

### Option E — Audit / Compliance Advanced Phase

Continue hardening audit: encryption at rest, retention, compression, export,
reporting, integrity hash chain, tamper evidence, compliance view.

- **Strengths:** further secures the compliance foundation.
- **Risks:** marginal user value now (Phase 2D-H1 already hardened the store);
  premature engineering; can delay core agent capability.
- **Why not Phase 3A:** user value 2/5 and demo value 2/5. Diminishing returns
  ahead of core agent value. Deferred to Phase 3E.

---

## 4. Decision Rationale

Phase 3A must maximize **(value × readiness × reversibility) ÷ (security risk ×
production dependency × complexity)**. Option C dominates that ratio:

- It is the only candidate with **no new external surface** (no network, no
  production, no dynamic loading).
- It reuses the entire Phase 2 capability chain instead of superseding it.
- It is the natural **container** for Options A and D — a real provider step
  and a plugin-tool step both become workflow step types in later phases.
- Its risk is bounded by the same gates Phase 2 already enforces
  (read-only allowlist, fake provider, sandbox write + rollback, durable audit,
  route governance).

Option A is the highest-value candidate but is gated behind Phase 3A because
its risk (5/5) is unmanageable as a first slice. Options B, D, E are lower
value or higher risk now and are sequenced later.

---

## 5. Why Not Now / Why Later

| Option | Why not now | Why later |
|--------|-------------|-----------|
| A — Real Provider | Risk 5/5; real adapter not wired; needs workflow container + hardened audit | After 3A (container) and 2D-H1 (audit), a read-only real-provider step fits cleanly as Phase 3B |
| B — Production Pilot | Production dependency 5/5; capabilities still dev-only; no core agent value yet | After 3A + 3B deliver real operator value worth piloting |
| D — Plugin Registry | Risk 4/5; dynamic-loading / supply-chain exposure; needs policy framework | After a capability framework exists; fits as Phase 3C |
| E — Audit Compliance | User value 2/5; Phase 2D-H1 already hardened the store | After core agent value; Phase 3E |

---

## 6. Recommended Order

```
Phase 3A — Dev-only Agent Workflow MVP                 (Option C)  ← selected
Phase 3B — Real Provider Read-only Controlled Integration (Option A)
Phase 3C — Plugin / Capability Registry                 (Option D)
Phase 3D — Production Pilot Readiness                   (Option B)
Phase 3E — Audit Compliance Advanced                    (Option E)
```

This ordering is risk-ascending and dependency-respecting:

1. **3A (Workflow)** compounds existing capability with no new external surface.
2. **3B (Real Provider)** plugs a read-only real-provider step into the 3A
   container; write stays blocked.
3. **3C (Plugin Registry)** introduces a structured capability framework after
   the workflow + provider steps exist to consume it.
4. **3D (Production Pilot)** packages real operator value for a pilot only after
   3A + 3B deliver it.
5. **3E (Audit Compliance)** hardens compliance once the system has real usage
   volume to justify retention / encryption / reporting.

The order may be adjusted by the user, but each slice remains individually
authorized.

---

## 7. Recommendation

**Phase 3A = Dev-only Agent Workflow MVP.**

Phase 3A does **not**: use a real provider, enable provider auto-write, perform
autonomous write, run shell commands, mutate a database, write to an external
service, roll out to production, access `~/.hermes` or production `state.db`,
dynamically load plugins, schedule / cron, or run a background autonomous
agent. It is fully dev-only and reversible.

See [phase-3-scope-freeze.md](phase-3-scope-freeze.md) for the frozen scope,
[phase-3-risk-register.md](phase-3-risk-register.md) for the risk model, and
[phase-3-go-no-go.md](phase-3-go-no-go.md) for the decision.
