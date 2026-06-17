# Phase 3C — UI & Status Design

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Capability Registry UI & Status Surface (Frozen Design) |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |
| Design ID | `PHASE-3C-UI-STATUS-001` |

> This document freezes the future read-only UI / status surface for the
> Capability Registry. No component is built here. The surface is read-only and
> inherits the Phase 2E-H1 / 3A no-leak closure.

## 1. Recommended UI regions (future)

| Region | Purpose |
|--------|---------|
| Capability Registry Panel | Lists capabilities grouped by category with badges |
| Capability Detail Drawer | Shows one capability's full safe record |
| Capability Permission Badge | Visual `permissionClass` tag |
| Capability Trust Badge | Visual `trustLevel` tag |
| Capability Blocked Reason | Shows `blockedReason` when `status=blocked` |
| Capability Audit Links | Cross-navigates to the capability's audit events |
| Capability Search / Filter | Filter by category / permission / trust / status |

The panel is **additive** to the unified developer console (`/#/console`),
mirroring the Phase 2E / 3A additive pattern. `/#/` (the 3-column chat
workbench) stays unchanged.

## 2. What the UI must show

```
capabilityId
displayName
category
permissionClass
trustLevel
status
requiresApproval
requiresAudit
devOnly
productionAllowed   (always false in the first version)
blockedReason       (when status=blocked)
relatedTool         (toolBinding, if any)
relatedProvider     (providerBinding, if any)
relatedWorkflow     (workflowBinding, if any)
```

## 3. What the UI must NOT show

The UI must never surface any of:

```
API key
Authorization header
Bearer token
raw token
full tokenHash
raw prompt secret
raw response secret
callable repr
production path
local plugin path
dynamic import path
shell command
SQL mutation
```

This is the same no-leak closure used by the Phase 2E-H1 / 3A / 3B surfaces. A
no-leak test must assert none of these appears in any registry UI state.

## 4. Status surface

Capability status rides the **existing** `/status` response (under a new
`capabilityRegistry` block) **only if no new route is required**. If surfacing
status would require a new route, it must instead be read from the static module
in-process — the default is `routeExposure = existing_route_only` or `no_route`,
never `forbidden_new_route`.

`/status` must carry only value-free, safe markers:

```
capabilityRegistry:
  loaded:            bool
  validationPassed:  bool
  capabilityCount:   int
  enabledCount:      int
  blockedCount:      int
  devOnly:           true
  productionAllowed: false
  dynamicLoading:    false
```

No capability detail, no secret, no path is carried in `/status`.

## 5. Accessibility & motion

The panel inherits the Phase 2E-H1 accessibility baseline (vertical tablist /
roving tabindex / non-color badges / focus-visible) and respects
`prefers-reduced-motion`. Permission / trust badges are non-color (icon + label),
not color-only.

## 6. Read-only by default

The UI is **read-only by default.** There are no enable / disable / promote /
delete controls in the first version. A capability's `status` is read from the
static manifest; the UI never mutates it. (A future, separately-authorized phase
may add gated operator controls — never automatic ones.)

## 7. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3C scope freeze](phase-3c-capability-registry-scope-freeze.md)
- [Phase 3C capability model](phase-3c-capability-model.md)
- [Phase 3C audit policy](phase-3c-capability-audit-policy.md)
- [Phase 3C UI wireframe (optional)](phase-3c-capability-registry-ui-wireframe.md)
