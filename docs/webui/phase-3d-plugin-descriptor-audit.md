# Phase 3D — Plugin Descriptor Audit

Source of truth: `hermes_cli/dev_web_plugin_descriptor_audit.py`.

The bridge writes dev-only `plugin_descriptor_*` breadcrumb events into the
existing Phase 2D durable audit store (reuses `AUDIT_KIND_INTERNAL` — no new
audit kind / writer surface).

## Event types (frozen)

```
plugin_descriptor_registry_loaded
plugin_descriptor_validation_passed
plugin_descriptor_validation_failed
plugin_descriptor_rejected
plugin_descriptor_blocked
plugin_descriptor_capability_binding_checked
plugin_descriptor_permission_classified
plugin_descriptor_trust_classified
plugin_descriptor_visibility_rendered
plugin_descriptor_execution_requested   # records an intercepted request only
plugin_descriptor_execution_blocked      # always emitted on any exec path
plugin_runtime_disabled
plugin_no_dynamic_loading_checked
plugin_route_governance_checked
```

`plugin_descriptor_execution_requested` / `plugin_descriptor_execution_blocked`
exist **only** to record that an execution request was intercepted — they never
execute (there is no plugin runtime).

## Safe payload fields

`pluginId`, `capabilityId`, `permissionClass`, `trustLevel`, `status`,
`blockedReason`, `devOnly`, `productionAllowed`, `requiresApproval`,
`requiresAudit`, value-free `safeMetadata`.

## No-leak

Forbidden fields never reach the store: API key, Authorization, Bearer token,
raw secret, raw prompt/response, full tokenHash, callable repr, shell command,
SQL statement, production path, local plugin path, dynamic import path, external
URL, download URL, install command. The bridge applies its own defensive
re-redaction (`redact_plugin_descriptor_payload`) before the store's sanitizer
runs.

## Failure semantics

- `redactionApplied = true` on every event.
- Best-effort write: a store failure is reported in the result and never raises.
- Audit failure **never** enables a descriptor, never grants permission, never
  creates an execution path.
- The write is confined to the dev `HERMES_HOME`; never `~/.hermes`.
