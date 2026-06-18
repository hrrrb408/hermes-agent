# Phase 3E — Risk Register

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — Risk Register (Frozen) |
| Status | Frozen (docs-only planning; Real Plugin Runtime **not started**) |
| Date | 2026-06-19 |
| Planning ID | `PHASE-3E-PLANNING-001` |
| Risk-Register ID | `PHASE-3E-RISK-REGISTER-001` |

> This register records the P0 / P1 / P2 risks that govern a **future**
> real Plugin Runtime. It is **additive** to
> [phase-1g-05-risk-register](phase-1g-05-risk-register.md) and
> [phase-3d-risk-register](phase-3d-risk-register.md); it relaxes nothing.
> Every P0 here is a **stop condition** (must not occur; if it does, stop and do
> not push). Every P1 is a **push-gate**. P2 items are deferred sequencing. None
> is introduced by this docs-only planning phase.

## 1. Summary

| Severity | Count | Blocks this planning phase? |
|----------|-------|------------------------------|
| **P0** | 24 (RUNTIME-P0-01 … RUNTIME-P0-24) | No — none is introduced; all are stop conditions for a future runtime |
| **P1** | 10 (RUNTIME-P1-01 … RUNTIME-P1-10) | No — all are future-runtime ambiguity push-gates |
| **P2** | 5 (RUNTIME-P2-01 … RUNTIME-P2-05) | No — intentional deferrals |

> **P0 introduced by Phase 3E Planning = 0. P1 introduced = 0.** This phase is
> docs-only; it introduces no code, no route, no runtime, and no execution.

## 2. P0 Risks (stop conditions for a future runtime)

Each P0 below is a hard stop condition. If the listed condition ever becomes true
during any future runtime work, **stop immediately; do not commit; do not push.**

### RUNTIME-P0-01 — Real runtime implemented during planning

- **Risk:** a real plugin runtime is implemented inside the docs-only planning
  phase.
- **Current state:** not introduced (docs-only).
- **Stop condition:** any runtime dispatch / loader / sandbox code added ⇒ STOP.

### RUNTIME-P0-02 — Plugin execution introduced

- **Risk:** any plugin code executes.
- **Current state:** not introduced.
- **Stop condition:** any plugin executes ⇒ STOP.

### RUNTIME-P0-03 — Dynamic loading introduced

- **Risk:** `importlib` / `__import__` / path load / `pkgutil` walk is introduced.
- **Current state:** not introduced.
- **Stop condition:** any dynamic-loading primitive ⇒ STOP.

### RUNTIME-P0-04 — Local plugin directory loading introduced

- **Risk:** a local plugin directory is scanned / loaded.
- **Current state:** not introduced.
- **Stop condition:** any directory walk / glob of a plugin folder ⇒ STOP.

### RUNTIME-P0-05 — Remote registry introduced

- **Risk:** a remote plugin registry is fetched.
- **Current state:** not introduced.
- **Stop condition:** any remote registry / manifest fetch ⇒ STOP.

### RUNTIME-P0-06 — Marketplace introduced

- **Risk:** a plugin marketplace path exists.
- **Current state:** not introduced.
- **Stop condition:** any marketplace path ⇒ STOP.

### RUNTIME-P0-07 — External plugin fetch introduced

- **Risk:** external plugins are fetched (arbitrary URL).
- **Current state:** not introduced.
- **Stop condition:** any `externalUrl` / `downloadUrl` honored ⇒ STOP.

### RUNTIME-P0-08 — Provider-generated plugin introduced

- **Risk:** provider responses can create / install / enable / execute a plugin.
- **Current state:** not introduced (Phase 3D forbids it).
- **Stop condition:** provider response mutates the runtime ⇒ STOP.

### RUNTIME-P0-09 — LLM-generated plugin install introduced

- **Risk:** LLM-generated tools are auto-installed as plugins.
- **Current state:** not introduced.
- **Stop condition:** any auto-registration path ⇒ STOP.

### RUNTIME-P0-10 — Shell execution introduced

- **Risk:** `subprocess` / `os.system` / `shell=True` / `shellCommand`.
- **Current state:** not introduced.
- **Stop condition:** any shell primitive ⇒ STOP.

### RUNTIME-P0-11 — Database mutation introduced

- **Risk:** `sqlite3` / ORM write / DML against any DB incl. production
  `state.db`.
- **Current state:** not introduced.
- **Stop condition:** any DB mutation ⇒ STOP.

### RUNTIME-P0-12 — External HTTP execution introduced

- **Risk:** outbound HTTP from a plugin path.
- **Current state:** not introduced.
- **Stop condition:** any outbound network call ⇒ STOP.

### RUNTIME-P0-13 — Production operation introduced

- **Risk:** a runtime path performs a production operation.
- **Current state:** not introduced.
- **Stop condition:** any production operation ⇒ STOP.

### RUNTIME-P0-14 — Secret exfiltration risk unresolved

- **Risk:** the runtime can read env / secrets without an approved
  secret-isolation model.
- **Current state:** no runtime exists; risk is unresolved-by-absence.
- **Stop condition:** runtime approved before secret isolation ⇒ STOP.

### RUNTIME-P0-15 — Filesystem boundary unresolved but runtime approved

- **Risk:** a runtime is approved before its filesystem-boundary model is
  approved.
- **Current state:** neither approved.
- **Stop condition:** runtime approved before filesystem boundary ⇒ STOP.

### RUNTIME-P0-16 — Network boundary unresolved but runtime approved

- **Risk:** a runtime is approved before its network-boundary model is approved.
- **Current state:** neither approved.
- **Stop condition:** runtime approved before network boundary ⇒ STOP.

### RUNTIME-P0-17 — Supply-chain policy unresolved but runtime approved

- **Risk:** a runtime is approved before its supply-chain policy is approved.
- **Current state:** neither approved.
- **Stop condition:** runtime approved before supply-chain policy ⇒ STOP.

### RUNTIME-P0-18 — Permission escalation path introduced

- **Risk:** the runtime grants a permission higher than the bound capability.
- **Current state:** not introduced.
- **Stop condition:** any permission escalation ⇒ STOP.

### RUNTIME-P0-19 — Audit bypass introduced

- **Risk:** a runtime action is un-audited or audit fails open.
- **Current state:** not introduced.
- **Stop condition:** any audit bypass / fail-open ⇒ STOP.

### RUNTIME-P0-20 — Route governance drift introduced

- **Risk:** the runtime adds a route, drifting from 34 / 34 / 5 / 0 / 1 / 1.
- **Current state:** not introduced.
- **Stop condition:** route count drifts ⇒ STOP.

### RUNTIME-P0-21 — `~/.hermes` or production `state.db` access introduced

- **Risk:** the runtime reaches production paths.
- **Current state:** not introduced.
- **Stop condition:** any production-path reachability ⇒ STOP.

### RUNTIME-P0-22 — Production Gateway affected

- **Risk:** the runtime / phase stops / restarts / replaces / signals the
  Production Gateway (PID 28428).
- **Current state:** not introduced.
- **Stop condition:** any PID 28428 drift ⇒ STOP.

### RUNTIME-P0-23 — Runtime artifact committed

- **Risk:** a runtime store / JSONL / token / manifest runtime file is committed.
- **Current state:** not introduced.
- **Stop condition:** any runtime artifact staged ⇒ STOP.

### RUNTIME-P0-24 — `.claude/` committed

- **Risk:** `.claude/` is staged / committed.
- **Current state:** not introduced.
- **Stop condition:** `.claude/` staged ⇒ STOP.

## 3. P1 Risks (future-runtime ambiguity push-gates)

Each P1 is a push-gate for a future runtime: the ambiguity must be resolved
(approved model exists) before a runtime may proceed.

```
RUNTIME-P1-01 — Sandbox architecture ambiguity (no approved sandbox model)
RUNTIME-P1-02 — Process isolation ambiguity (no approved process-isolation model)
RUNTIME-P1-03 — Filesystem boundary ambiguity (no approved filesystem-boundary model)
RUNTIME-P1-04 — Network boundary ambiguity (no approved network-boundary model)
RUNTIME-P1-05 — Supply-chain policy ambiguity (no approved supply-chain policy)
RUNTIME-P1-06 — Permission review ambiguity (inheritance rules unapproved for runtime)
RUNTIME-P1-07 — Audit model ambiguity (no approved runtime audit model)
RUNTIME-P1-08 — UI warning ambiguity (runtime-disabled banner unapproved)
RUNTIME-P1-09 — Route governance ambiguity (no approved runtime route policy)
RUNTIME-P1-10 — Production isolation ambiguity (no approved production-isolation model)
```

Each is closed only by the matching approved model in
[phase-3e-sandbox-architecture](phase-3e-sandbox-architecture.md),
[phase-3e-process-isolation-model](phase-3e-process-isolation-model.md),
[phase-3e-filesystem-boundary-model](phase-3e-filesystem-boundary-model.md),
[phase-3e-network-boundary-model](phase-3e-network-boundary-model.md),
[phase-3e-supply-chain-policy](phase-3e-supply-chain-policy.md),
[phase-3e-permission-review](phase-3e-permission-review.md),
[phase-3e-audit-redaction-review](phase-3e-audit-redaction-review.md),
[phase-3e-ui-review](phase-3e-ui-review.md),
[phase-3e-route-governance-review](phase-3e-route-governance-review.md), and
[phase-3e-production-isolation-review](phase-3e-production-isolation-review.md).
**None is approved by this planning phase** — the models are designed, not
authorized.

## 4. P2 Risks (intentional deferrals)

```
RUNTIME-P2-01 — Runtime disabled skeleton deferred (no skeleton built)
RUNTIME-P2-02 — Container sandbox feasibility deferred (Option D not designed out)
RUNTIME-P2-03 — Signed manifest deferred (future supply-chain hardening)
RUNTIME-P2-04 — Multi-user plugin ownership deferred (single-user today)
RUNTIME-P2-05 — Plugin version migration deferred (no version floor built)
```

## 5. Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E threat model](phase-3e-real-runtime-threat-model.md)
- [Phase 3E runtime GO / NO-GO](phase-3e-runtime-go-no-go.md)
- [Phase 3E implementation entry criteria](phase-3e-implementation-entry-criteria.md)
- [Phase 1G-05 risk register](phase-1g-05-risk-register.md)
- [Phase 3D risk register](phase-3d-risk-register.md)
