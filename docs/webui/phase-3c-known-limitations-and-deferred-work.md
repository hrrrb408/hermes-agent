# Phase 3C — Known Limitations / Deferred Work

| Field | Value |
|-------|-------|
| Phase | 3C (Closeout) |
| Title | Static Capability Registry — Known Limitations / Deferred Work |
| Status | Intentional deferrals (not defects) |
| Date | 2026-06-18 |

## 1. Limitations / deferrals

1. **No plugin runtime implemented.** The registry describes capabilities; it
   does not load or run them.
2. **No dynamic loading.** No `importlib`, `__import__`, path-based load, or
   `pkgutil` walk.
3. **No remote registry.** No remote manifest fetch.
4. **No marketplace.** No plugin marketplace.
5. **No external plugin fetch.** No arbitrary-URL plugin fetch.
6. **No provider-generated plugin.** Providers cannot generate plugins.
7. **No production rollout.** Every capability is dev-only
   (`productionAllowed = false`).
8. **No runtime manifest reload.** The manifest is static; it is not reloaded
   at runtime.
9. **No multi-user capability ownership.** Capabilities have a single `owner`
   label; there is no per-user ownership model.
10. **Frontend TS manifest mirror is a tracked copy.** The mirror
    (`constants/capabilityRegistryManifest.ts`) is hand-maintained; drift is
    bounded by the H1 manifest-consistency test.
11. **Generated frontend mirror deferred.** A generator that derives the mirror
    from the backend is P2-deferred.
12. **Phase 3D requires explicit approval.** No Phase 3D work begins without a
    separately authorized planning phase.

## 2. These are intentional deferrals

These are **intentional deferrals, not unfinished defects.** Each was a
deliberate scope decision: the first version of the Capability Registry is
static, dev-only, read-only, and descriptive only. Every dynamic / remote /
marketplace / production capability is explicitly **forbidden** in this
version and is described in the manifest as `blocked`.

## 3. Cross-references

- [Risk closure](phase-3c-risk-closure.md)
- [Phase 3D entry criteria](phase-3c-phase-3d-entry-criteria.md)
- [Final GO / NO-GO](phase-3c-final-go-no-go.md)
