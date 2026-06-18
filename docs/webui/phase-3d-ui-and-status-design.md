# Phase 3D — UI & Status Design

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime — UI & Status Design (Frozen) |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Design ID | `PHASE-3D-UI-STATUS-001` |

> This document plans the **future** read-only plugin descriptor UI. It does not
> implement it. The UI is strictly read-only and carries a runtime-disabled
> banner.

## 1. Read-only UI areas (future)

```
Plugin Runtime Planning Status
Plugin Descriptor List
Plugin Descriptor Detail Drawer
Plugin Trust Badge
Plugin Permission Badge
Plugin Blocked Reason
Plugin Capability Binding View
Plugin Runtime Disabled Banner
```

## 2. What the UI must display

- Plugin runtime **disabled**.
- Dynamic loading **disabled**.
- Remote registry **disabled**.
- Marketplace **disabled**.
- Production allowed **false**.
- **Descriptor only**.
- **Does not grant permission**.
- **Does not execute plugin**.

## 3. What the UI must NOT display

- API key
- Authorization
- Bearer token
- raw secret
- callable repr
- shell command
- SQL statement
- production path
- local plugin path
- dynamic import path
- external URL
- download URL
- install command

## 4. `/status` block (future, no new route)

If a future implementation surfaces plugin descriptor status, it rides the
existing `GET /api/dev/v1/status` response under `data.pluginRuntime` **only if no
new route is required**. The block carries only safe, value-free fields:

```
status, loaded, descriptorCount, validatedCount, blockedCount,
disabledCount, devOnly, productionAllowed, dynamicLoadingAllowed,
remoteRegistryAllowed, marketplaceAllowed, redactionApplied, validation {valid,errorCount}
```

All frozen policy flags are constants: `dynamicLoadingAllowed =
remoteRegistryAllowed = marketplaceAllowed = productionAllowed = false`;
`devOnly = true`; `redactionApplied = true`.

## 5. Accessibility & no-leak inheritance

The UI inherits the Phase 2E-H1 accessibility baseline (vertical tablist /
roving tabindex / non-color badges / focus-visible) and the Phase 3C no-leak
closure. Badges carry text labels (non-color). No API-key / password input
exists. Every selected detail renders no secret / callable repr / path / command.

## 6. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D audit / redaction policy](phase-3d-audit-and-redaction-policy.md)
- [Phase 3D trust boundary](phase-3d-trust-boundary.md)
- [Phase 3C UI & status design](phase-3c-ui-and-status-design.md)
- [Phase 3C final security boundary](phase-3c-security-boundary-final.md)
