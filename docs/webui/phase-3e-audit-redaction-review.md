# Phase 3E — Audit / Redaction Review

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — Audit / Redaction Review (Frozen, Design-only) |
| Status | Frozen (docs-only planning; Real Plugin Runtime **not started**) |
| Date | 2026-06-19 |
| Planning ID | `PHASE-3E-PLANNING-001` |
| Audit-Review ID | `PHASE-3E-AUDIT-REDACTION-001` |

> This document reviews — but does **not** implement — the audit / redaction
> model a future real plugin runtime would require. No implementation is
> authorized.

## 1. Position (fail-closed)

```
Audit failure cannot enable runtime.
Audit failure cannot permit execution.
Audit failure cannot grant permission.
Audit must FAIL CLOSED.
```

## 2. Suggested runtime audit events

```
runtime_planning_reviewed
runtime_execution_requested
runtime_execution_denied
runtime_sandbox_selected
runtime_sandbox_denied
runtime_filesystem_access_requested
runtime_filesystem_access_denied
runtime_network_access_requested
runtime_network_access_denied
runtime_package_install_requested
runtime_package_install_denied
runtime_kill_switch_checked
runtime_route_governance_checked
runtime_production_isolation_checked
```

Every event is dual-written, safe-fields-only, and fail-closed (an audit write
failure blocks the action).

## 3. Safe fields

```
runtimeMode, pluginId, capabilityId, permissionClass, trustLevel, decision,
blockedReason, devOnly, productionAllowed, redactionApplied
```

## 4. Forbidden fields

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
local path
filesystem path
network URL
download URL
install command
environment variable value
```

The audit bridge re-redacts defensively and never writes to the production home.

## 5. Redaction guarantees

- Every runtime result / audit / log / UI value is re-redacted before emission.
- Non-JSON-native values collapse to a safe placeholder (never a `repr`).
- No raw path / URL / command / secret is ever written, even in a denied-event
  reason (the reason uses a stable code, not the offending value).

## 6. Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E permission review](phase-3e-permission-review.md)
- [Phase 3E UI review](phase-3e-ui-review.md)
- [Phase 3D audit / redaction policy](phase-3d-audit-and-redaction-policy.md)
- [Phase 2D audit schema v2](phase-2d-audit-schema-v2.md)
- [Phase 2D audit security boundary](phase-2d-audit-security-boundary.md)
