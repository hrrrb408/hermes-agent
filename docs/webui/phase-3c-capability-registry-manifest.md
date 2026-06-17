# Phase 3C — Capability Registry Manifest (Implementation Reference)

| Field | Value |
|-------|-------|
| Phase | 3C (Implementation) |
| Module | `hermes_cli/dev_web_capability_registry_manifest.py` |
| Version | `phase3c-static-v1` |
| Status | Implemented |

The manifest is a literal tuple of dicts — `STATIC_CAPABILITY_MANIFEST` (46
entries). Pinned `CREATED_AT` / `UPDATED_AT` (`2026-06-17T00:00:00Z`); no
wall-clock sampling. No entry carries a forbidden field.

Capability groups:

1. **Registry** (4): `registry.capability_registry_{status,list,detail,audit}`
2. **Read-only tools** (6): `tool.read.{clarify,tool_policy_read,route_governance_read,audit_events_read,dev_environment_read,release_status_read}`
3. **Sandbox write/rollback** (5): write/append/patch → `WRITE_CONFIRM`; readback → `READ_ONLY`; rollback → `ROLLBACK_CONFIRM`
4. **Provider** (10): fake/real-boundary/preview/classification → `READ_ONLY`; `real_gated_roundtrip` + `live_manual_one_shot` → `LIVE_PROVIDER_GATED` (disabled, not executed); `tool_execution`/`write`/`auto_write`/`autonomous_action` → `ADMIN_FORBIDDEN` (blocked)
5. **Workflow** (11): step types (read-only / write-preview); `write_execute`/`rollback_execute` → blocked (separate authorization); `auto_advance`/`autonomous_write`/`background_schedule` → `ADMIN_FORBIDDEN` (blocked)
6. **Forbidden** (10): `capability.forbidden.{dynamic_plugin_load,remote_registry,marketplace,shell,database_mutation,external_http,production_operation,provider_write,provider_auto_write,autonomous_write}` → all `blocked`

Frontend mirror: `apps/hermes-dev-webui/src/constants/capabilityRegistryManifest.ts`.
