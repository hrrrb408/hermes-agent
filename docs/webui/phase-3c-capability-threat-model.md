# Phase 3C — Capability Registry Threat Model (Optional)

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Capability Registry — Threat Model |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |

> Optional companion to the risk register. Maps the capability registry's trust
> boundaries and the controls that keep them.

## 1. Trust boundaries

| Boundary | What crosses it | Control |
|----------|-----------------|---------|
| Static manifest → registry | Declared capability records | Frozen schema; forbidden-fields list; fail-closed validation |
| Registry → execution | "I want to run capability X" | Registry grants nothing; existing tool / approval / route / live gate governs |
| External source → registry | A remote / marketplace / uploaded manifest | Forbidden (`EXTERNAL_FORBIDDEN` / `UNKNOWN_FORBIDDEN`); never auto-enabled |
| Registry → UI | Capability records for display | No-leak closure; safe fields only |
| Registry → audit | Audit events | Safe fields; defensive re-redaction; fail-closed |

## 2. Primary adversaries / misuse

- **Code-execution attacker:** tries to turn the registry into an execution
  surface (import path, callable, shell command, external URL). Control:
  forbidden-fields list + no-dynamic-loading check + no runtime plugin path.
- **Permission-forger:** tries to classify a blocked capability as executable.
  Control: frozen taxonomy; terminal forbidden classes; registry is descriptive.
- **Auto-enabler:** tries to auto-promote a disabled / blocked capability.
  Control: no auto-enable; no trust auto-upgrade; static status from manifest.
- **Secret-leaker:** tries to exfiltrate a key / token / path via the registry
  or UI. Control: no-leak closure; safe-fields-only audit; re-redaction.
- **Route-drifter:** tries to add a route. Control: default no new route;
  routeExposure frozen; governance re-asserted.

## 3. Invariants the model protects

- Descriptive only — never authoritative.
- Static only — never dynamic.
- Dev-only — never production.
- No secret carriage — in manifest, status, UI, or audit.

## 4. Cross-references

- [Phase 3C risk register](phase-3c-security-risk-register.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
- [Phase 3C static manifest schema](phase-3c-static-manifest-schema.md)
