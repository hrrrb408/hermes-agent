# Phase 3E — Permission Review

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — Permission Review (Frozen, Design-only) |
| Status | Frozen (docs-only planning; Real Plugin Runtime **not started**) |
| Date | 2026-06-19 |
| Planning ID | `PHASE-3E-PLANNING-001` |
| Permission-Review ID | `PHASE-3E-PERMISSION-REVIEW-001` |

> This document reviews — but does **not** implement — the permission model a
> future real plugin runtime would inherit. No implementation is authorized.

## 1. Sources (inherited, never re-created)

```
Phase 3C Capability Registry — source of capability classification
Phase 3D Plugin Descriptor Registry — source of descriptors
```

The runtime never re-classifies capability or re-authors descriptors. It binds to
existing Phase 3C `capabilityId`s and consumes existing Phase 3D descriptors.

## 2. Runtime permission rules

```
The runtime must NOT grant permission.
The runtime must inherit the MOST RESTRICTIVE permission of its bound capability.
The runtime must NOT bypass Tool policy.
The runtime must NOT bypass the Provider live gate.
The runtime must NOT bypass Workflow approval.
The runtime must NOT create an approval automatically.
The runtime must NOT create a confirmation automatically.
The runtime must NOT create a dry-run automatically.
```

## 3. Permission classes (future-runtime handling)

Each class describes how a future runtime would treat a plugin bound to a
capability of that class:

```
READ_ONLY            — runtime may dispatch only through the read-only controlled
                       chain; never writes / executes a side effect.
WRITE_PREVIEW        — runtime may render a preview via the dry-run chain; never
                       persists.
WRITE_CONFIRM        — runtime may perform a write ONLY after an explicit human
                       confirmation token (Phase 2C chain); never auto-writes.
ROLLBACK_CONFIRM     — runtime may perform a rollback ONLY after an explicit
                       human confirmation (Phase 2C-H1 chain); never auto-rolls.
LIVE_PROVIDER_GATED  — runtime may reach a live provider ONLY through the Phase
                       3B-Live-Enablement gate (approval + budget + kill switch +
                       allowlist); never directly.
ADMIN_FORBIDDEN      — runtime must NOT expose admin / config / route mutation
                       capabilities.
EXTERNAL_FORBIDDEN   — runtime must NOT expose external-fetch / remote-registry /
                       marketplace capabilities.
PRODUCTION_FORBIDDEN — runtime must NOT expose any production capability
                       (devOnly = true; productionAllowed = false).
```

For every class, the runtime's permission class is **≤** the most-restrictive
bound capability class (escalation is rejected — RUNTIME-THREAT-15).

## 4. What the runtime may never do

- Grant a permission its bound capability does not have.
- Self-authorize, self-enable, or auto-promote.
- Create an approval / confirmation / dry-run token on its own.
- Bypass the dry-run → confirmation → audit chain.
- Reach the provider live path outside the live gate.
- Advance a workflow or write without the workflow approval gate.

## 5. Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E audit / redaction review](phase-3e-audit-redaction-review.md)
- [Phase 3C capability permission classes](phase-3c-capability-permission-classes.md)
- [Phase 3D permission / approval model](phase-3d-permission-and-approval-model.md)
- [Phase 3A workflow approval gates](phase-3a-workflow-approval-gates.md)
- [Phase 3B-Live-Enablement approval implementation](phase-3b-live-enablement-approval-implementation.md)
