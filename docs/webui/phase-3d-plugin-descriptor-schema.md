# Phase 3D — Plugin Descriptor Schema

Source of truth: `hermes_cli/dev_web_plugin_descriptor_schema.py`.

## Frozen taxonomies

**Trust levels** (`PLUGIN_TRUST_LEVELS`):
`trusted_builtin_code`, `trusted_static_descriptor`, `dev_reviewed_descriptor`,
`experimental_disabled_descriptor`, `external_forbidden`, `unknown_forbidden`,
`production_forbidden`.

Forbidden trust levels: `external_forbidden`, `unknown_forbidden`,
`production_forbidden` (must be `blocked`). Visible trust levels:
`trusted_builtin_code`, `trusted_static_descriptor`.

**Statuses** (`PLUGIN_STATUSES`): `planned`, `declared`, `validated`, `visible`,
`disabled`, `blocked`, `deprecated`, `removed`. There is **no** executable
lifecycle status (`installed` / `loaded` / `executing` do not exist).

**Execution modes** (`PLUGIN_EXECUTION_MODES`): `none`, `descriptor_only`,
`read_only_descriptor`, `disabled_runtime`. None represents runtime execution.

**Sources** (`PLUGIN_SOURCES`): `builtin_static`, `tracked_static_descriptor`,
`dev_reviewed_descriptor`, `experimental_disabled`, `external_forbidden`,
`unknown_forbidden`, `production_forbidden`.

**Permission classes** — shared with Phase 3C: `READ_ONLY`, `WRITE_PREVIEW`,
`WRITE_CONFIRM`, `ROLLBACK_CONFIRM`, `LIVE_PROVIDER_GATED`, `ADMIN_FORBIDDEN`,
`EXTERNAL_FORBIDDEN`, `PRODUCTION_FORBIDDEN`.

## Permission restrictiveness order

Most → least restrictive (higher rank = stricter):

```
PRODUCTION_FORBIDDEN (7) > EXTERNAL_FORBIDDEN (6) > ADMIN_FORBIDDEN (5)
> LIVE_PROVIDER_GATED (4) > ROLLBACK_CONFIRM (3) > WRITE_CONFIRM (2)
> WRITE_PREVIEW (1) > READ_ONLY (0)
```

`most_restrictive_permission(classes)` returns the highest-rank class; a
descriptor inherits this from its bindings.

## Fields

- **Allowed**: `pluginId`, `displayName`, `description`, `version`, `owner`,
  `source`, `trustLevel`, `status`, `capabilityBindings`, `permissionClass`,
  `executionMode`, `requiresApproval`, `requiresDryRun`, `requiresConfirmation`,
  `requiresAudit`, `requiresBudget`, `requiresKillSwitch`, `devOnly`,
  `productionAllowed`, `disabledByDefault`, `blockedReason`, `metadataSchema`,
  `createdAt`, `updatedAt`.
- **Required**: `pluginId`, `displayName`, `source`, `trustLevel`, `status`,
  `capabilityBindings`, `permissionClass`, `executionMode`, `devOnly`,
  `productionAllowed`, `disabledByDefault`.
- **Forbidden** (canonical + alias/casing — rejected at any depth): see
  `FORBIDDEN_FIELDS`. Includes `pythonImportPath`, `callable`, `shellCommand`,
  `externalUrl`, `downloadUrl`, `pluginPackage`, `dynamicModule`, `evalCode`,
  `execCode`, `sqlStatement`, `productionPath`, `apiKey`, `Authorization`,
  `secret`, `localPath`, `remoteUrl`, `installCommand`, `postInstallHook`,
  `preExecutionHook`, `arbitraryArgs`, plus aliases (`bearer`, `api_key`,
  `accessToken`, `callable_repr`, `shell_command`, `sql`, `production_path`,
  `dynamic_import`, `importPath`, `modulePath`, `external_url`, `download_url`,
  `install_command`, `post_install_hook`, `pre_execution_hook`, …).

## Formats

- `pluginId` / `capabilityId`: dot-delimited lower-snake tokens
  (`^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$`).
- Recursive forbidden-field scan (`_scan_for_forbidden`) walks dicts / lists /
  tuples so a forbidden key cannot hide inside an allowed field's nested value.
