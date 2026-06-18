# PLUG-AUDIT-3D-H1-001 — plugin_descriptor_* Audit / Redaction / No-leak

**Lens 9.** Every `plugin_descriptor_*` audit event is safe.

## Scope

- The frozen 14 event types are present (registry_loaded, validation_passed /
  failed, rejected, blocked, capability_binding_checked, permission_classified,
  trust_classified, visibility_rendered, execution_requested, execution_blocked,
  plugin_runtime_disabled, plugin_no_dynamic_loading_checked,
  plugin_route_governance_checked).
- `SAFE_PAYLOAD_FIELDS` excludes every forbidden key and is exactly the frozen
  safe set.
- `redact_plugin_descriptor_payload` drops every forbidden key, coerces non-JSON
  values safely (callables / bytes dropped), redacts nested `safeMetadata`, and
  always sets `redactionApplied = True`.
- A write succeeds under the dev HERMES_HOME; an execution_blocked event is
  recordable without executing; an unknown event type is normalized to
  `plugin_descriptor_registry_loaded`.
- The persisted event blob carries no forbidden token (sk-, Bearer, BEGIN PRIVATE
  KEY, rm -rf, DELETE FROM, ~/.hermes, importlib, eval(). A defensive failure
  returns `written = False`, never raises, and never enables a descriptor / grants
  permission. No event is written to the production home.

## Evidence

`tests/test_dev_web_phase_3d_h1_descriptor_audit_no_leak.py` (49 tests).

## Result

PASS. Audit events are safe, redacted, fail-safe, and confined to the dev home.
