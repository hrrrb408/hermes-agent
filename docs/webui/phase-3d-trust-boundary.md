# Phase 3D — Trust Boundary

| Field | Value |
|-------|-------|
| Phase | 3D (Planning) |
| Title | Plugin Runtime — Trust Boundary (Frozen) |
| Status | Frozen (docs-only planning; Plugin Runtime **not started**) |
| Date | 2026-06-18 |
| Planning ID | `PHASE-3D-PLANNING-001` |
| Boundary ID | `PHASE-3D-TRUST-BOUNDARY-001` |

> This document freezes the trust boundary a future Phase 3D Plugin Runtime must
> enforce. Trust zones are **descriptive labels**, not runtime grants. They map
> onto (and must stay consistent with) the Phase 3C trust levels.

## 1. Trust zones

| Zone | Meaning | Visible in planning? | Executable? |
|------|---------|----------------------|-------------|
| `trusted_builtin_code` | Built into the current code, test-covered, audited boundary | yes | only via existing gates |
| `trusted_static_descriptor` | Declared in a tracked static descriptor; loads no code | yes | no (descriptor only) |
| `dev_reviewed_descriptor` | A reviewed descriptor bound to a Phase 3C capability | yes | no (descriptor only) |
| `experimental_disabled_descriptor` | A planned descriptor; default disabled | yes (as disabled) | no |
| `external_forbidden` | External source, remote plugin, marketplace, dynamic download | no | no — forbidden |
| `unknown_forbidden` | Unknown source | no | no — forbidden |
| `production_forbidden` | Production operation / `~/.hermes` / production `state.db` | no | no — forbidden |

## 2. What the boundary guarantees

- **Only `trusted_builtin_code` and `trusted_static_descriptor` may be visible in
  planning.** `dev_reviewed_descriptor` is visible as a disabled, descriptor-only
  object.
- **No external descriptor can become executable.** External / unknown /
  production sources are forbidden and never rendered as runnable.
- **No descriptor can upgrade itself.** Trust never auto-promotes.
- **No provider response can create a plugin.**
- **No workflow can create a plugin.**
- **No UI input can create a plugin.**
- **No local file path can create a plugin.**
- **No remote URL can create a plugin.**

## 3. Trust movement (frozen)

```
Trust downgrade: ALLOWED   (e.g. reviewed → experimental_disabled)
Trust upgrade:   FORBIDDEN without code review + tests + explicit user approval
```

A descriptor's trust level may only stay the same or move **down** (toward
disabled / blocked / removed). Any upgrade (e.g. `experimental_disabled` →
`dev_reviewed`, or `DEV_STATIC_MANIFEST` → `BUILTIN_VERIFIED`) requires a code
review, tests, and explicit user approval recorded in a separately authorized
phase.

## 4. Mapping to Phase 3C trust levels

| Phase 3D zone | Phase 3C trust level |
|---------------|----------------------|
| `trusted_builtin_code` | `BUILTIN_VERIFIED` |
| `trusted_static_descriptor` | `DEV_STATIC_MANIFEST` |
| `dev_reviewed_descriptor` | `DEV_STATIC_MANIFEST` (bound + reviewed) |
| `experimental_disabled_descriptor` | `EXPERIMENTAL_DISABLED` |
| `external_forbidden` | `EXTERNAL_FORBIDDEN` |
| `unknown_forbidden` | `UNKNOWN_FORBIDDEN` |
| `production_forbidden` | (maps to `PRODUCTION_FORBIDDEN` permission class; terminal) |

Consistency rule: a descriptor's zone and its Phase 3C `trustLevel` may never
contradict. A descriptor with `trustLevel = EXTERNAL_FORBIDDEN` is always
`external_forbidden` here and never executable.

## 5. Boundary checks (future implementation)

- A descriptor with a forbidden zone is rejected fail-closed at validation.
- A descriptor cannot be enabled unless its zone is `trusted_builtin_code` or
  `trusted_static_descriptor` **and** its bound capability is enabled.
- Trust-level changes are audited; an upgrade attempt without recorded approval
  is blocked.

## 6. Cross-references

- [Phase 3D planning](phase-3d-planning.md)
- [Phase 3D threat model](phase-3d-threat-model.md)
- [Phase 3D permission / approval model](phase-3d-permission-and-approval-model.md)
- [Phase 3C capability permission classes](phase-3c-capability-permission-classes.md)
