# Phase 3C — Capability Registry Audit (Implementation Reference)

| Field | Value |
|-------|-------|
| Phase | 3C (Implementation) |
| Module | `hermes_cli/dev_web_capability_registry_audit.py` |
| Audit kind | `AUDIT_KIND_INTERNAL` (reused — no new kind) |
| Event prefix | `capability_registry_*` |
| Status | Implemented |

Events: `capability_registry_{loaded,validation_passed,validation_failed,
capability_viewed,capability_blocked,permission_classified,trust_classified,
manifest_rejected,route_governance_checked,no_dynamic_loading_checked}`.

`write_capability_registry_audit(...)` builds a canonical event via
`build_audit_event`, applies `redact_capability_registry_payload` (keeps only
`SAFE_PAYLOAD_FIELDS`), and appends via the existing durable store. Unknown
event types normalize to `capability_registry_loaded`. Writes are fail-safe
(never raise; audit failure never enables a capability) and confined to the dev
`HERMES_HOME` (never `~/.hermes`).

Safe payload fields: `capabilityId, category, permissionClass, trustLevel,
status, blockedReason, requiresApproval, requiresAudit, devOnly,
productionAllowed, routeExposure, safeMetadata` (+ `redactionApplied=true`).

Forbidden fields never reach the store (defensive re-redaction at the bridge
and again at the store sanitizer).
