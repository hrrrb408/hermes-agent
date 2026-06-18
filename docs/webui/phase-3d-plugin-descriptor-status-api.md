# Phase 3D — Plugin Descriptor /status API

Integration point: `hermes_cli/dev_web_api.py` (`_plugin_descriptor_registry_status`
+ the `/status` handler). **No new HTTP route is introduced** — the block rides
the existing `GET /api/dev/v1/status` response.

## Block location

`GET /api/dev/v1/status` → `data.pluginDescriptorRegistry`.

## Fields (all value-free)

```
status, registryVersion, descriptorCount, visibleCount, disabledCount,
blockedCount, devOnly, productionAllowed, pluginRuntimeImplemented,
pluginLoaderImplemented, dynamicLoadingAllowed,
localPluginDirectoryLoadingAllowed, remoteRegistryAllowed, marketplaceAllowed,
externalPluginFetchAllowed, providerGeneratedPluginAllowed,
llmGeneratedPluginInstallAllowed, pluginExecutionAllowed, newRouteIntroduced,
routeGovernanceExpected, validation{valid,errorCount,warningCount},
redactionApplied
```

## Frozen flag values (first version)

- `pluginRuntimeImplemented = false`
- `pluginLoaderImplemented = false`
- `dynamicLoadingAllowed = false`
- `localPluginDirectoryLoadingAllowed = false`
- `remoteRegistryAllowed = false`
- `marketplaceAllowed = false`
- `externalPluginFetchAllowed = false`
- `providerGeneratedPluginAllowed = false`
- `llmGeneratedPluginInstallAllowed = false`
- `pluginExecutionAllowed = false`
- `newRouteIntroduced = false`
- `productionAllowed = false`; `devOnly = true`; `redactionApplied = true`
- `routeGovernanceExpected = "34/34/5/0/1/1"` (unchanged baseline)

## No-leak

The block never carries an API key, Authorization header, Bearer token, raw
secret, callable repr, shell command, SQL statement, production path, local
plugin path, dynamic import path, external URL, download URL, or install
command.

## Failure mode

`get_plugin_descriptor_status_block()` never raises — a load/validation failure
surfaces as `status=validation_failed` so `/status` itself never fails because
of the descriptor registry.
