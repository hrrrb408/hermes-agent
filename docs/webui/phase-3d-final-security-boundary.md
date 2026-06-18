# Phase 3D — Final Security Boundary (Frozen)

| Field | Value |
|-------|-------|
| Phase | 3D (Planning Closeout) |
| Title | Plugin Runtime Planning — Final Security Boundary |
| Status | Frozen |
| Date | 2026-06-18 |

> The planning boundary is **planning only**. The future runtime, if ever
> authorized, is **descriptor-only**. This is the frozen boundary.

## 1. Frozen boundary

```
Planning only
No implementation
No plugin runtime
No plugin loader
No dynamic loading
No importlib dynamic import
No __import__ dynamic import
No local plugin directory loading
No remote registry
No marketplace
No external plugin fetch
No provider-generated plugin
No LLM-generated plugin install
No shell execution
No database mutation
No external HTTP execution
No production operation
No provider write
No autonomous write
No production rollout
No live provider execution
No real API key read
No external network
No ~/.hermes access
No production state.db access
No new route
```

## 2. Descriptor allowed fields

```
pluginId, displayName, description, version, owner, source, trustLevel, status,
capabilityBindings, permissionClass, executionMode, requiresApproval,
requiresDryRun, requiresConfirmation, requiresAudit, requiresBudget,
requiresKillSwitch, devOnly, productionAllowed, disabledByDefault, blockedReason,
metadataSchema, createdAt, updatedAt
```

## 3. Descriptor forbidden fields

```
pythonImportPath, callable, shellCommand, externalUrl, downloadUrl, pluginPackage,
dynamicModule, evalCode, execCode, sqlStatement, productionPath, apiKey,
Authorization, secret, localPath, remoteUrl, installCommand, postInstallHook,
preExecutionHook, arbitraryArgs
```

Rejected fail-closed at any depth (recursive + scalar type guard).

## 4. Audit safe fields

```
pluginId, capabilityId, permissionClass, trustLevel, status, blockedReason,
devOnly, productionAllowed, requiresApproval, requiresAudit, redactionApplied
```

## 5. Audit forbidden fields

```
API key, Authorization, Bearer token, raw secret, raw prompt, raw response,
full tokenHash, callable repr, shell command, SQL statement, production path,
local plugin path, dynamic import path, external URL, download URL, install command
```

## 6. UI safe fields

```
descriptor list / drawer: pluginId, displayName, description, capabilityBindings,
permissionClass, trustLevel, status, blockedReason, devOnly, productionAllowed,
disabledByDefault
/status pluginRuntime block: status, loaded, descriptorCount, validatedCount,
blockedCount, disabledCount, devOnly, productionAllowed, dynamicLoadingAllowed,
remoteRegistryAllowed, marketplaceAllowed, redactionApplied, validation {valid,errorCount}
```

## 7. UI forbidden fields

```
API key, Authorization, Bearer, raw secret, callable repr, shell command, SQL,
production path, local plugin path, dynamic import path, external URL, download URL,
install command
```

## 8. Implementation red lines

Any future implementation must hold: descriptor-only (no execution); no dynamic
loading; capability-bound to existing Phase 3C IDs; permission class ≤ bound
capability class; `devOnly=true`, `productionAllowed=false`, disabled by default;
no new route; fail-closed audit; no secret/callable/path/command leak; PID `28428`
untouched; no `~/.hermes` / production `state.db` access; no runtime artifacts /
`.claude/` committed.

## 9. Cross-references

- [Phase 3D planning closeout](phase-3d-planning-closeout.md)
- [Final threat model summary](phase-3d-final-threat-model-summary.md)
- [Final trust boundary summary](phase-3d-final-trust-boundary-summary.md)
- [Phase 3C final security boundary](phase-3c-security-boundary-final.md)
