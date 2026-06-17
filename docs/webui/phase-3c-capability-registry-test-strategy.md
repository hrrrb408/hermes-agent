# Phase 3C — Capability Registry Test Strategy (Optional)

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Capability Registry — Test Strategy |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |

> Optional companion to the execution brief. The future implementation must
> cover these lenses. No tests are written in this planning phase.

## 1. Backend test lenses

| Lens | Asserts |
|------|---------|
| Manifest validation | Allowed fields accepted; every forbidden field rejected (fail-closed) |
| Required fields | Missing `capabilityId` / `category` / `permissionClass` / `trustLevel` / `status` rejected |
| Taxonomy | Unknown permission class / trust level rejected; forbidden classes terminal |
| Duplicate ids | Duplicate `capabilityId` rejected |
| Production flag | `productionAllowed=true` rejected in the first version |
| No dynamic loading | No `importlib` / path / `subprocess` / network call path exists in the module |
| Status block | `/status` `capabilityRegistry` carries only value-free markers; no new route |
| Audit | load / validate / view / block / classification each emit a `capability_registry_*` event; safe fields only |
| Route governance | Route count unchanged (34 / 34 / 5 / 0 / 1 / 1) |

## 2. Frontend test lenses

| Lens | Asserts |
|------|---------|
| Read-only | No enable / disable / promote / delete control renders |
| Badges | `blocked` capabilities render blocked + `blockedReason` |
| No-leak | No API key / token / hash / callable repr / path in any state |
| Accessibility | Vertical tablist / roving tabindex / non-color badges / focus-visible |

## 3. Smoke

- A new additive smoke profile (in `all`) that loads the registry, views a
  capability, and confirms the no-leak + route-governance invariants.
- Existing smoke profiles keep passing (zero regression).

## 4. Production safety tests

- No `~/.hermes` access; no production `state.db` access.
- `.claude/` is not staged in the diff.
- No runtime artifact (audit JSONL / store / token / rollback / workflow) is
  committed.

## 5. Cross-references

- [Phase 3C execution brief](phase-3c-execution-brief.md)
- [Phase 3C risk register](phase-3c-security-risk-register.md)
- [Phase 3C UI & status design](phase-3c-ui-and-status-design.md)
