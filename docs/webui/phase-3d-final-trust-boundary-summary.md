# Phase 3D — Final Trust Boundary Summary

| Field | Value |
|-------|-------|
| Phase | 3D (Planning Closeout) |
| Title | Plugin Runtime — Final Trust Boundary Summary |
| Status | Frozen |
| Date | 2026-06-18 |
| Summary ID | `PHASE-3D-FINAL-TRUST-001` |

> Final trust boundary for the future plugin descriptor runtime. Full detail
> lives in [phase-3d-trust-boundary.md](phase-3d-trust-boundary.md).

## 1. Trust zones

| Zone | Visible in planning? | Executable? |
|------|----------------------|-------------|
| `trusted_builtin_code` | yes | only via existing gates |
| `trusted_static_descriptor` | yes | no (descriptor only) |
| `dev_reviewed_descriptor` | yes (as disabled descriptor) | no |
| `experimental_disabled_descriptor` | yes (as disabled) | no |
| `external_forbidden` | no | no — forbidden |
| `unknown_forbidden` | no | no — forbidden |
| `production_forbidden` | no | no — forbidden |

## 2. What a descriptor CANNOT do

```
Descriptor cannot self-upgrade.
Descriptor cannot grant permission.
Descriptor cannot create approval.
Descriptor cannot create route.
Descriptor cannot create execution path.
Descriptor cannot create plugin code.
Provider response cannot create descriptor.
Workflow cannot create descriptor.
UI input cannot create descriptor.
Remote source cannot create descriptor.
Local path cannot create descriptor.
```

## 3. Trust movement (frozen)

```
Trust upgrade is NO-GO without code review + tests + explicit user approval.
Trust downgrade is allowed.
```

A descriptor's trust level may only stay the same or move **down** (toward
disabled / blocked / removed). Any upgrade requires a separately authorized phase
with code review, tests, and explicit user approval.

## 4. Zone ↔ Phase 3C trust-level mapping

| Phase 3D zone | Phase 3C trust level |
|---------------|----------------------|
| `trusted_builtin_code` | `BUILTIN_VERIFIED` |
| `trusted_static_descriptor` | `DEV_STATIC_MANIFEST` |
| `dev_reviewed_descriptor` | `DEV_STATIC_MANIFEST` (bound + reviewed) |
| `experimental_disabled_descriptor` | `EXPERIMENTAL_DISABLED` |
| `external_forbidden` | `EXTERNAL_FORBIDDEN` |
| `unknown_forbidden` | `UNKNOWN_FORBIDDEN` |
| `production_forbidden` | (`PRODUCTION_FORBIDDEN` permission class; terminal) |

## 5. Cross-references

- [Phase 3D trust boundary (full)](phase-3d-trust-boundary.md)
- [Final security boundary](phase-3d-final-security-boundary.md)
- [Phase 3C capability permission classes](phase-3c-capability-permission-classes.md)
