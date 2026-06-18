# Phase 3D — Plugin Descriptor Validation

Source of truth: `hermes_cli/dev_web_plugin_descriptor_registry.py`
(`validate_manifest`, `_validate_entry`) + `dev_web_plugin_descriptor_policy.py`.

## Fail-closed semantics

`valid` is `True` only when every descriptor passes schema + policy + uniqueness.
If validation fails, the registry status is `validation_failed` and invalid
descriptors are blocked out (never exposed as enabled / visible-executable).

## Per-descriptor checks

1. Entry is a dict; no forbidden field at any depth (recursive) → reject.
2. Required fields present.
3. `pluginId` stable dot-delimited format.
4. Enum membership: `trustLevel`, `status`, `executionMode`, `source`,
   `permissionClass`.
5. Boolean fields are real booleans; scalar string fields are not nested
   structures; `capabilityBindings` is a list of strings.
6. First-version invariants: `devOnly=true`, `productionAllowed=false`,
   `disabledByDefault=true`.
7. `blocked` status requires a `blockedReason`.
8. Allowed-field whitelist (no unknown keys).
9. Policy composition (binding + inheritance + trust — see binding/trust docs).

## Manifest-level checks

- `pluginId` uniqueness across the manifest.
- Aggregated counts (`visibleCount`, `disabledCount`, `blockedCount`,
  `boundCapabilityCount`, permission/trust/status/execution/source counts).

## Invalid-descriptor read model

Invalid entries (e.g. a forbidden field smuggled in) are reduced to a blocked
record (`status=blocked`,
`blockedReason=forbidden_field_present_validation_failed`) so the read model
never exposes an execution surface even for an unvalidated manifest.
