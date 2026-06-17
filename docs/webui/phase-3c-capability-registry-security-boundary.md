# Phase 3C — Capability Registry Security Boundary

| Field | Value |
|-------|-------|
| Phase | 3C (Implementation) |
| Title | Static Capability Registry Security Boundary |
| Status | Frozen |
| Date | 2026-06-17 |

> The registry is **descriptive**, never an execution surface. This document
> records the boundary the implementation enforces.

## 1. What the registry may do

- Declare capabilities statically in a tracked manifest.
- Validate, classify (permission class / trust level), expose read-only, and
  audit them.
- Reference an existing built-in capability by a stable id
  (`toolBinding` / `providerBinding` / `workflowBinding`) **without** a code
  pointer.
- Block capabilities with a precise `blockedReason`.

## 2. What the registry may NOT do

- No dynamic loading (no `importlib`, no path-based load, no plugin dir walk).
- No remote registry / marketplace / external plugin fetch.
- No shell command, SQL mutation, external HTTP, or production operation.
- No provider write / auto-write / autonomous action.
- No live provider request, no real API key read, no external network.
- No self-modification; no auto-enable; no trust auto-upgrade.
- No new HTTP route; no production `~/.hermes` or production `state.db` access.

## 3. Forbidden fields (rejected by validation)

```
pythonImportPath, callable, shellCommand, externalUrl, downloadUrl,
pluginPackage, dynamicModule, evalCode, execCode, sqlStatement,
productionPath, apiKey, Authorization, secret
```

Any manifest entry carrying one fails closed (`capability_registry_manifest_rejected`).

## 4. Frozen composition rules

- `enabled` requires `trustLevel ∈ {BUILTIN_VERIFIED, DEV_STATIC_MANIFEST}`
  and a non-forbidden permission class.
- Forbidden trust/permission classes are always `disabled`/`blocked`.
- `EXPERIMENTAL_DISABLED` capabilities are non-executable.
- `WRITE_CONFIRM` ⇒ dry-run + confirmation + audit.
- `ROLLBACK_CONFIRM` ⇒ confirmation + audit.
- `LIVE_PROVIDER_GATED` ⇒ approval + budget + kill switch + audit.
- `READ_ONLY` cannot declare `confirmed_execute`/`manual_live`.
- No first-version capability has `productionAllowed = true`.

## 5. No-leak closure

The `/status` block, every detail, and every `capability_registry_*` audit
event carry only safe, value-free fields. Defensive re-redaction runs at the
audit bridge and again at the store layer.

## 6. Production safety

The Production Gateway (PID 28428) is never touched. The dev services bind to
`127.0.0.1` only. No runtime artifact and no `.claude/` is committed.

## 7. Cross-references

- [Implementation](phase-3c-static-capability-registry-implementation.md)
- [No dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
- [Audit policy](phase-3c-capability-audit-policy.md)
- [Risk register](phase-3c-security-risk-register.md)
