# Phase 3D — Audit & Redaction Policy

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime — Audit & Redaction Policy (Frozen) |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Policy ID | `PHASE-3D-AUDIT-REDACTION-001` |

> This document freezes the future audit / redaction policy for plugin descriptor
> lifecycle events. It reuses the Phase 2D durable audit store and the Phase 3C
> `capability_registry_*` redaction discipline. Every event carries safe fields
> only, dual-written, fail-closed.

## 1. Planned audit events

```
plugin_descriptor_declared
plugin_descriptor_validated
plugin_descriptor_rejected
plugin_descriptor_blocked
plugin_capability_binding_checked
plugin_permission_classified
plugin_trust_classified
plugin_visibility_rendered
plugin_execution_requested
plugin_execution_blocked
plugin_runtime_disabled
plugin_no_dynamic_loading_checked
plugin_route_governance_checked
```

Every event is dual-written (Phase 2D durable store + dev JSONL) and fail-closed:
an audit write failure blocks the lifecycle step.

## 2. Safe fields

Audit events carry only these fields:

```
pluginId
capabilityId
permissionClass
trustLevel
status
blockedReason
devOnly
productionAllowed
requiresApproval
requiresAudit
redactionApplied
```

Every event sets `redactionApplied = true`.

## 3. Forbidden fields (never persisted)

Never written to audit:

```
API key
Authorization
Bearer token
raw secret
raw prompt
raw response
full tokenHash
callable repr
shell command
SQL statement
production path
local plugin path
dynamic import path
external URL
download URL
install command
```

Defensive re-redaction runs at the audit bridge **and** again at the store layer
(inheriting the Phase 3C-H1 layered discipline).

## 4. Fail-closed rules

```
redactionApplied = true        (always)
audit fail-closed              (write failure blocks the step)
audit failure cannot enable a plugin
audit failure cannot grant permission
```

If the audit store cannot accept an event, the descriptor lifecycle step that
produced it does not proceed.

## 5. No-leak policy

No `plugin_*` audit event, read model, or UI surface may carry a secret,
Authorization header, bearer token, raw token hash, callable repr, shell command,
SQL statement, production path, local plugin path, dynamic import path, external
URL, download URL, or install command.

## 6. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D UI / status design](phase-3d-ui-and-status-design.md)
- [Phase 3C capability audit policy](phase-3c-capability-audit-policy.md)
- [Phase 3C final security boundary](phase-3c-security-boundary-final.md)
- [Phase 2D audit security boundary](phase-2d-audit-security-boundary.md)
