# Phase 3C — Final Security Boundary (Frozen)

| Field | Value |
|-------|-------|
| Phase | 3C (Closeout) |
| Title | Static Capability Registry — Final Security Boundary |
| Status | Frozen |
| Date | 2026-06-18 |

> The Capability Registry is **descriptive**, never an execution surface. This
> is the final, frozen boundary the shipped + hardened registry enforces.

## 1. Frozen boundary

- The Capability Registry is **static**.
- The Capability Registry is **dev-only** (`devOnly = true`,
  `productionAllowed = false`).
- The Capability Registry is **read-only**.
- The Capability Registry is **descriptive-only**.
- The Capability Registry **does not grant permissions**.
- The Capability Registry **does not execute anything**.
- The Capability Registry **does not bypass existing policies** (Tool policy,
  Provider live gate, Workflow approval, dry-run, confirmation, audit).
- **No plugin runtime. No dynamic loading. No `importlib` dynamic import. No
  `__import__` dynamic import. No `eval` / `exec`. No `subprocess` / shell. No
  remote registry. No marketplace. No external plugin fetch. No
  provider-generated plugin. No production operation. No `~/.hermes` access.
  No production `state.db` access. No new route.**

## 2. Forbidden-field rejection list

Validation rejects (fail-closed) any manifest entry carrying, at any depth:

```
pythonImportPath, callable, shellCommand, externalUrl, downloadUrl,
pluginPackage, dynamicModule, evalCode, execCode, sqlStatement,
productionPath, apiKey, Authorization, secret
```

The scan is **recursive** (top-level keys + any nested dict / list / tuple),
and scalar-string fields are type-guarded against nested-structure smuggling.

## 3. No-leak policy

The `/status` block, every capability detail, and every `capability_registry_*`
audit event carry **only safe, value-free fields**. Defensive re-redaction runs
at the audit bridge and again at the store layer. Never surfaced: API key,
Authorization header, Bearer token, raw secret, raw prompt/response, full
tokenHash, callable repr, shell command, SQL statement, production path, local
plugin path, dynamic import path, external URL.

## 4. Audit safe fields

```
capabilityId, category, permissionClass, trustLevel, status, blockedReason,
requiresApproval, requiresAudit, devOnly, productionAllowed, routeExposure,
safeMetadata (re-redacted)
```

## 5. Audit forbidden fields

Never persisted: `apiKey`, `Authorization`, `secret`, `tokenHash`, `rawPrompt`,
`rawResponse`, `callable`, `shellCommand`, `sqlStatement`, `productionPath`,
`pythonImportPath`, and any field outside the safe set.

## 6. `/status` safe fields

```
status, registryVersion, loaded, validationPassed, capabilityCount,
enabledCount, disabledCount, blockedCount, plannedCount, deprecatedCount,
permissionClassCounts, trustLevelCounts, categoryCounts, devOnly,
productionAllowed, dynamicLoadingAllowed, remoteRegistryAllowed,
marketplaceAllowed, routeGovernanceExpected, validation {valid,errorCount,
warningCount}, redactionApplied
```

All frozen policy flags are constants: `dynamicLoadingAllowed =
remoteRegistryAllowed = marketplaceAllowed = productionAllowed = false`;
`devOnly = true`; `redactionApplied = true`.

## 7. UI no-leak requirements

The Dev WebUI panel renders no API key / Authorization / Bearer / callable
repr / shell command / SQL / production path / plugin path / dynamic import
path, in any state (default, validation_failed, empty, every selected detail).
No API-key / password input exists. Badges carry text labels (non-color).

## 8. Cross-references

- [Final acceptance](phase-3c-final-acceptance.md)
- [Risk closure](phase-3c-risk-closure.md)
- [Implementation security boundary](phase-3c-capability-registry-security-boundary.md)
- [Forbidden-fields hardening](phase-3c-h1-forbidden-fields-hardening.md)
- [Audit no-leak hardening](phase-3c-h1-audit-no-leak-hardening.md)
