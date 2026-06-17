# Phase 3C — Capability Registry /status Integration

| Field | Value |
|-------|-------|
| Phase | 3C (Implementation) |
| Route | `GET /api/dev/v1/status` (existing — no new route) |
| Block | `data.capabilityRegistry` |
| Status | Implemented |

`_capability_registry_status()` in `hermes_cli/dev_web_api.py` calls
`get_registry_status_block()` (load + validate the static manifest). The block
is value-free and never fails `/status` (load failure → `status=validation_failed`).

Fields: `status, registryVersion, loaded, validationPassed, capabilityCount,
enabledCount, disabledCount, blockedCount, plannedCount, deprecatedCount,
permissionClassCounts, trustLevelCounts, categoryCounts, devOnly,
productionAllowed, dynamicLoadingAllowed, remoteRegistryAllowed,
marketplaceAllowed, routeGovernanceExpected, validation {valid,errorCount,
warningCount}, redactionApplied`.

Route governance unchanged: OpenAPI 34 / runtime 34 / Tool GET 5 / write 0 /
dry-run 1 / execution 1. No capability HTTP route exists.
