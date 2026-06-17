# Phase 3C — Capability Registry Schema (Implementation Reference)

| Field | Value |
|-------|-------|
| Phase | 3C (Implementation) |
| Module | `hermes_cli/dev_web_capability_registry_schema.py` |
| Status | Implemented |

Frozen taxonomies implemented as `frozenset` constants:

- **Categories**: `tool, provider, workflow, sandbox, audit, registry, system`
- **Statuses**: `enabled, disabled, blocked, planned, deprecated`
- **Permission classes**: `READ_ONLY, WRITE_PREVIEW, WRITE_CONFIRM, ROLLBACK_CONFIRM, LIVE_PROVIDER_GATED, ADMIN_FORBIDDEN, EXTERNAL_FORBIDDEN, PRODUCTION_FORBIDDEN` (last three terminal/forbidden)
- **Trust levels**: `BUILTIN_VERIFIED, DEV_STATIC_MANIFEST, EXPERIMENTAL_DISABLED, EXTERNAL_FORBIDDEN, UNKNOWN_FORBIDDEN`
- **Execution modes**: `none, read_only, dry_run, confirmed_execute, manual_live`
- **Route exposures**: `existing_route_only, no_route, forbidden_new_route`
- **Sources**: `builtin, static_manifest, provider_boundary, workflow_boundary`

Field sets: `ALLOWED_FIELDS` (max), `REQUIRED_FIELDS` (capabilityId, category,
permissionClass, trustLevel, status), `FORBIDDEN_FIELDS` (14 execution-surface
fields). `capabilityId` format: `[a-z][a-z0-9_]*(\.[a-z0-9_]+)+`.

Validation predicates: `is_valid_category`, `is_valid_status`,
`is_valid_permission_class`, `is_valid_trust_level`, `is_valid_execution_mode`,
`is_valid_route_exposure`, `is_valid_source`, `is_valid_capability_id`,
`is_forbidden_field_present`, `is_terminal_forbidden`, `is_executable_status`.

Dataclasses: `CapabilityValidationError`, `ValidationReport` (to_dict()).

See [capability model](phase-3c-capability-model.md),
[manifest schema](phase-3c-static-manifest-schema.md).
