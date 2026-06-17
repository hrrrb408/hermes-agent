# Phase 3B-Live-Enablement H1 — Frontend Live UI No-leak Hardening

| Field | Value |
|-------|-------|
| Lens | 8 — Frontend Live Enablement UI No-leak Boundary |
| Hardening ID | `LIVE-UI-3B-H1-001` |
| Status | PASS |

## Scope

The live-enablement surface rendered by `ProviderBoundaryStatus.vue` +
`toolProvider` store: status, approval, budget, kill-switch rendering, and the
no-leak invariant across every live state.

## Evidence

- Test files:
  - `src/tests/phase3b-live-h1-status-ui.spec.ts`
  - `src/tests/phase3b-live-h1-approval-ui.spec.ts`
  - `src/tests/phase3b-live-h1-budget-ui.spec.ts`
  - `src/tests/phase3b-live-h1-kill-switch-ui.spec.ts`
  - `src/tests/phase3b-live-h1-no-leak-ui.spec.ts`
- Components: `src/components/workspace/ProviderBoundaryStatus.vue`

## Findings & Fixes

- Disabled-by-default label, frozen approval constants (required / single-use /
  300 s TTL), and the tool-execution-disabled line render in the DOM.
- `liveEnabled` is the conjunction of the flag AND an inactive kill switch.
- `manualOneShot` stays `false` in every approval / kill state.
- Frozen caps (1 / 1000 / 200 / 5c / 0 retry) + `failClosedOnCounterError`
  asserted; retry cap renders as `0`.
- Kill banner renders for each trigger reason; kill-active keeps live disabled;
  clearing grants no live-enabled.
- No-leak sweep across 7 live states: no API-key input, no API-key value, no
  Authorization / Bearer / raw token / full tokenHash / raw prompt-response /
  callable repr / production path in payload or rendered DOM.

No implementation change was required.

## Residual risk

None. The live UI is value-free in every state.
