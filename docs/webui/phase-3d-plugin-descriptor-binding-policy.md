# Phase 3D — Plugin Descriptor Capability Binding & Permission Inheritance

Source of truth: `hermes_cli/dev_web_plugin_descriptor_policy.py`.

## Capability index

`build_capability_index()` reads the **validated** Phase 3C Capability Registry
manifest read-only and returns a `{capabilityId: permissionClass}` view. A
descriptor's `capabilityBindings` must reference keys present in this index
(fail-closed: an empty index rejects every binding).

## Rules

- A descriptor **must** bind ≥1 existing Phase 3C capabilityId. It never
  introduces a new capabilityId or a new permission class.
- A descriptor inherits the **most-restrictive** permission class among its
  bindings (`most_restrictive_permission`).
- Declaring a **less-restrictive** class than inherited is permission
  escalation → rejected fail-closed.
- A descriptor bound to a terminal-forbidden capability (ADMIN/EXTERNAL/
  PRODUCTION_FORBIDDEN) **must** be `blocked`; it can never be `visible`.
- A descriptor never creates an approval / confirmation / dry-run / route /
  execution path. It never executes a tool / provider / workflow.

## Worked example

`plugin.descriptor.external_execution_blocked` binds:
`capability.forbidden.external_http` (EXTERNAL_FORBIDDEN, rank 6),
`capability.forbidden.shell` (ADMIN_FORBIDDEN, rank 5),
`capability.forbidden.database_mutation` (ADMIN_FORBIDDEN, rank 5).

Inherited = max rank = `EXTERNAL_FORBIDDEN`. The descriptor declares
`EXTERNAL_FORBIDDEN` (rank 6 ≥ 6) → accepted, `status=blocked`.
