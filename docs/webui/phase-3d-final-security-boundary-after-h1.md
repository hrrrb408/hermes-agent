# Phase 3D — Final Security Boundary (After H1, Frozen)

| Field | Value |
|-------|-------|
| Phase | 3D (Closeout) |
| Title | Static Plugin Descriptor Registry — Final Security Boundary (After H1) |
| Status | Frozen |
| Date | 2026-06-19 |
| Boundary ID | `PHASE-3D-SECURITY-BOUNDARY-FINAL-AFTER-H1-001` |

> The frozen final security boundary of the Phase 3D Static Plugin Descriptor
> Registry after Implementation and the H1 12-lens hardening. This supersedes
> the planning-time boundary for the descriptor registry as built; the
> planning-time runtime-NO-GO boundary
> ([phase-3d-final-security-boundary](phase-3d-final-security-boundary.md))
> remains the governing boundary for any future runtime.

## 1. Frozen boundary

```
Descriptor-only
Disabled-by-default
Capability-bound
Read-only
Dev-only
No plugin runtime
No plugin loader
No plugin execution
No dynamic loading
No importlib dynamic import
No __import__
No local plugin directory loading
No plugins/ directory scan
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
No live provider execution as part of Phase 3D
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

Every descriptor additionally enforces `devOnly = true`,
`productionAllowed = false`, `disabledByDefault = true`,
`executionMode = descriptor_only`.

## 3. Descriptor forbidden fields

```
pythonImportPath, callable, shellCommand, externalUrl, downloadUrl, pluginPackage,
dynamicModule, evalCode, execCode, sqlStatement, productionPath, apiKey,
Authorization, secret, localPath, remoteUrl, installCommand, postInstallHook,
preExecutionHook, arbitraryArgs
```

Rejected fail-closed at **any depth** (recursive scan + scalar-string type guard),
including alias and casing variants.

## 4. Nested forbidden fields

A forbidden key nested inside an allowed field's value (e.g.
`{"metadataSchema": {"shellCommand": ...}}`) is rejected by the recursive scan
plus the scalar-string type guard. The shallow-only scanner defect class
(seen and closed in Phase 3C-H1) is explicitly covered here and cannot recur.

## 5. Alias forbidden fields

Casing / spelling aliases of every forbidden field (e.g. `shell_command`,
`ShellCommand`, `PYTHON_IMPORT_PATH`) are rejected by the alias table; the scan
is case-insensitive against the canonical + alias set.

## 6. Audit safe fields

```
pluginId, capabilityId, permissionClass, trustLevel, status, blockedReason,
devOnly, productionAllowed, requiresApproval, requiresAudit, redactionApplied
```

## 7. Audit forbidden fields

```
API key, Authorization, Bearer token, raw secret, raw prompt, raw response,
full tokenHash, callable repr, shell command, SQL statement, production path,
local plugin path, dynamic import path, external URL, download URL, install command
```

The `plugin_descriptor_*` audit bridge re-redacts defensively and never writes to
the production home.

## 8. `/status` safe fields

```
pluginDescriptorRegistry block:
  descriptorCount, validatedCount, blockedCount, disabledCount, visibleCount,
  devOnly, productionAllowed, disabledByDefault, dynamicLoadingAllowed,
  remoteRegistryAllowed, marketplaceAllowed, externalPluginFetchAllowed,
  redactionApplied, validation {valid, errorCount}
summary entries:
  pluginId, displayName, description, capabilityBindings, permissionClass,
  trustLevel, status, blockedReason, devOnly, productionAllowed, disabledByDefault
```

Every runtime flag is false; `devOnly = true`; `redactionApplied = true`.

## 9. `/status` forbidden fields

```
API key, Authorization, Bearer, raw secret, callable repr, shell command, SQL,
production path, local plugin path, dynamic import path, external URL, download URL,
install command, full tokenHash, raw prompt, raw response
```

## 10. UI safe fields

```
descriptor list / drawer:
  pluginId, displayName, description, capabilityBindings, permissionClass,
  trustLevel, status, blockedReason, devOnly, productionAllowed, disabledByDefault
runtime-disabled banner invariants:
  descriptor-only, does not execute a plugin, does not grant permission
```

## 11. UI forbidden fields

```
API key, Authorization, Bearer, raw secret, callable repr, shell command, SQL,
production path, local plugin path, dynamic import path, external URL, download URL,
install command
```

Badges are non-color (label + icon) and accessible.

## 12. Implementation red lines

Any future change must hold: descriptor-only (no execution); no dynamic loading;
capability-bound to existing Phase 3C IDs; permission class ≤ the
most-restrictive bound capability class; `devOnly = true`,
`productionAllowed = false`, disabled by default; no new route; fail-closed
audit; no secret / callable / path / command leak; PID `28428` untouched; no
`~/.hermes` / production `state.db` access; no runtime artifacts / `.claude/`
committed.

## 13. Future runtime prerequisites

A real runtime — if ever considered — requires, at minimum: a new planning phase,
a runtime threat-model refresh, a sandbox model, a process-isolation model, a
filesystem-boundary model, a network-boundary model, a supply-chain policy, a
permission-model review, an audit-model review, a UI review, a route-governance
review, a production-isolation review, and explicit user approval. None of these
exists today; the runtime remains NO-GO.

## 14. Verification basis

- Recursive forbidden-field scan + alias + nested coverage (schema tests).
- Permission-inheritance + escalation / trust-self-upgrade rejection (binding +
  trust policy tests).
- No-execution / no-dynamic-loading AST guards across all five descriptor
  modules (no `importlib` / `subprocess` / remote fetch / directory walk).
- `/status` + read-model + UI no-leak (status-API, security, frontend no-leak
  tests; H1 smoke profile).
- Route governance preserved (34 OpenAPI / 34 runtime / 5 / 0 / 1 / 1).
- Production isolation preserved (PID `28428`, count 1, ports free).

## 15. Cross-references

- [Closeout](phase-3d-closeout.md)
- [Final acceptance](phase-3d-final-acceptance.md)
- [Planning final security boundary](phase-3d-final-security-boundary.md)
- [Plugin descriptor security boundary](phase-3d-plugin-descriptor-security-boundary.md)
- [Real runtime NO-GO](phase-3d-real-runtime-no-go.md)
- [Phase 3C final security boundary](phase-3c-security-boundary-final.md)
