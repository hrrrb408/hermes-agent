# Phase 3C — Risk Register

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Capability Registry — Risk Register |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Register ID | `PHASE-3C-RISK-REGISTER-001` |

## 1. Risk model

- **P0** = stop conditions. Any materialization halts work, blocks push, and
  triggers rollback / disable.
- **P1** = implementation push-gates. Must pass before a future Capability
  Registry implementation can ship.
- **P2** = deferred sequencing risks. Non-blocking; tracked for later phases.

## 2. P0 risks (stop conditions)

| ID | Risk | Mitigation |
|----|------|-----------|
| CAP-P0-01 | Dynamic plugin loading introduced (`importlib`, path load, npm / remote JS plugin) | No-dynamic-loading policy frozen; manifest forbids code pointers; load-time `capability_registry_no_dynamic_loading_checked`; any path = halt |
| CAP-P0-02 | External marketplace or remote registry introduced | Marketplace / remote registry / remote manifest / arbitrary-URL fetch forbidden; P0 stop if any appears |
| CAP-P0-03 | Capability grants permission instead of describing it | Registry is descriptive only; permissionClass is a label, not a grant; execution still gated by tool policy / approval / route / live gate |
| CAP-P0-04 | Write capability bypasses dry-run / confirmation | WRITE_CONFIRM still requires dry-run + confirmation token + digest + audit; ROLLBACK_CONFIRM still requires rollback manifest + confirmation + audit; registry does not relax |
| CAP-P0-05 | Provider live gate bypassed | LIVE_PROVIDER_GATED capabilities still require the full Phase 3B-Live-Enablement gate; manual one-shot stays NO-GO until separately authorized |
| CAP-P0-06 | Shell / database / external-HTTP capability exposed | These are declared `blocked` with a precise reason and never executable; manifest forbids `shellCommand` / `sqlStatement` / `externalUrl` |
| CAP-P0-07 | Production operation exposed | `productionAllowed=false` for all capabilities; PRODUCTION_FORBIDDEN class terminal; no `~/.hermes` / production `state.db` access |
| CAP-P0-08 | `~/.hermes` or production `state.db` accessed | Dev-only `HERMES_HOME` gate; production path detection; PID `28428` gate |
| CAP-P0-09 | Route governance drift | Default no new route; routeExposure ∈ {existing_route_only, no_route, forbidden_new_route}; governance re-asserted at load (34 / 34 / 5 / 0 / 1 / 1) |
| CAP-P0-10 | Secret / callable / path leak in registry or UI | No-leak closure inherited from 2E-H1 / 3A / 3B; manifest + UI + audit forbid the forbidden-field lists; defensive re-redaction before audit |
| CAP-P0-11 | Runtime artifact committed | Manifest is tracked source; no audit JSONL / store / token / rollback / workflow store committed |
| CAP-P0-12 | `.claude/` committed | Pre-commit check asserts `.claude/` is not staged |

## 3. P1 risks (push-gates for the future implementation)

| ID | Risk | Gate |
|----|------|------|
| CAP-P1-01 | Permission class ambiguity | Frozen taxonomy; validator rejects unknown classes; test asserts each capability maps to a known class |
| CAP-P1-02 | Trust level ambiguity | Frozen taxonomy; validator rejects unknown levels; test asserts each capability maps to a known level |
| CAP-P1-03 | Missing audit event | Every load / validate / view / block / classification writes a `capability_registry_*` event; test asserts coverage |
| CAP-P1-04 | UI displays a blocked capability as enabled | UI reads status from the manifest; badge shows `blocked` + `blockedReason`; test asserts blocked capabilities render blocked |
| CAP-P1-05 | Registry stale with tool policy | Capability mappings reference real tool / provider / workflow ids; test asserts the manifest does not declare a non-existent binding |
| CAP-P1-06 | Provider capability not aligned with live gate | Provider mapping frozen against the Phase 3B-Live-Enablement gate; test asserts LIVE_PROVIDER_GATED stays disabled by default |
| CAP-P1-07 | Workflow capability not aligned with workflow approval | Workflow mapping frozen against the Phase 3A approval gates; test asserts no workflow auto-executes a write |

## 4. P2 risks (deferred)

| ID | Risk | Disposition |
|----|------|-------------|
| CAP-P2-01 | Future plugin runtime | Deferred to a separately-authorized future phase (3D / 3E); out of scope here |
| CAP-P2-02 | Multi-user capability ownership | Deferred; first version is single-user dev-only |
| CAP-P2-03 | Capability marketplace | Deferred; explicitly forbidden in the first version |
| CAP-P2-04 | Runtime manifest reload | Deferred; first version loads a static, tracked manifest |
| CAP-P2-05 | Capability version migration | Deferred; first version has a single frozen manifest version |

## 5. Relationship to existing registers

This register is additive to
[phase-3b-security-risk-register.md](phase-3b-security-risk-register.md),
[phase-3b-live-enablement-risk-register.md](phase-3b-live-enablement-risk-register.md),
and [phase-1g-05-risk-register.md](phase-1g-05-risk-register.md). It does not
relax any P0/P1 there; it adds the capability-registry risks.

## 6. Cross-references

- [Phase 3C GO / NO-GO](phase-3c-go-no-go.md)
- [Phase 3C scope freeze](phase-3c-capability-registry-scope-freeze.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
- [Phase 3C threat model (optional)](phase-3c-capability-threat-model.md)
