# Phase 3D — Pre-Implementation Smoke Strategy (Optional)

| Field | Value |
|-------|-------|
| Phase | 3D (Planning Closeout) |
| Title | Plugin Runtime — Pre-Implementation Smoke Strategy |
| Status | Optional companion |
| Date | 2026-06-18 |

> The smoke strategy a **future** Phase 3D implementation must follow. This
> closeout phase adds **no smoke profile / spec** (docs-only).

## 1. Principle

If a future implementation adds a UI / status surface, smoke is **additive** and
**zero-regression** — mirroring the Phase 3C Profile P / Q pattern.

## 2. Candidate smoke profile (future)

- Name (candidate): `phase3d_plugin_descriptor`.
- Wired into the `all` smoke target.
- Scope: read-only descriptor list / drawer renders; runtime-disabled banner
  visible; no secret / callable / path / command leak in any state; `/status`
  `pluginRuntime` block present with value-free markers; no new route.

## 3. Must-pass invariants (future smoke)

- No API key / Authorization / Bearer / callable repr / shell command / SQL /
  production path / local plugin path / dynamic import path / external URL /
  install command rendered.
- `dynamicLoadingAllowed = remoteRegistryAllowed = marketplaceAllowed =
  productionAllowed = false`; `devOnly = true`; `redactionApplied = true`.
- Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1).
- Existing profiles keep passing (zero regression).

## 4. Out of scope for this closeout

No smoke profile / spec is added now. This document only records the future
strategy.

## 5. Cross-references

- [Phase 3D test strategy](phase-3d-test-strategy.md)
- [Phase 3D UI / status design](phase-3d-ui-and-status-design.md)
- [Final security boundary](phase-3d-final-security-boundary.md)
