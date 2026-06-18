# PLUG-UI-3D-H1-001 — Frontend UI / Runtime Disabled Banner / A11y / No-leak

**Lens 11.** The Plugin Descriptor Registry UI is read-only, accessible, and leaks
nothing.

## Scope

- The section renders (`plugin-descriptor-registry-section`), states it is
  descriptor-only (`does not grant permission`, `does not execute a plugin`,
  `disabled by default`), and surfaces every frozen disabled boundary as text
  (no plugin runtime, plugin loader not implemented, dynamic loading disabled,
  local plugin directory loading disabled, remote registry disabled, marketplace
  disabled, external plugin fetch disabled, no provider-generated plugin, no
  LLM-generated plugin install).
- The runtime-disabled banner renders with `role="status"` / `aria-live="polite"`,
  one row per disabled invariant, and the descriptor-only header.
- Badges are not color-only: every trust level, status, and permission class
  renders a non-empty text label; forbidden classes / trust levels carry a
  "Forbidden" marker; non-visible statuses carry a "Not executable" marker;
  decorative icons are `aria-hidden`.
- The summary renders the frozen-flags list, the counts (12), the route-governance
  baseline (34/34/5/0/1/1), the validation summary, degrades on null, and the
  `validation_failed` state still renders frozen flags as false and leaks nothing.
- The table partitions descriptors (3 visible / 4 disabled / 5 blocked), marks
  blocked rows, surfaces capability bindings as plain ids, emits select, and
  handles the empty state. The detail drawer renders the safe record + the
  describes-only notice for every descriptor.
- No forbidden token, production path, `state.db`, `OPENAI_API_KEY`, or `sk-`
  surfaces in any rendered HTML.

## Evidence

8 frontend spec files (`phase3d-h1-plugin-descriptor-registry-*.spec.ts`,
`phase3d-h1-plugin-runtime-disabled-banner.spec.ts`,
`phase3d-h1-plugin-descriptor-validation-states.spec.ts`) — 50 tests.

## Result

PASS. The UI is read-only, accessible (text labels, not color-only), and leak-free.
