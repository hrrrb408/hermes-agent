# Phase 2E-H1 — Accessibility & Responsive Review

**Review ID:** `ACCESSIBILITY-2E-H1-001`
**Scope:** The practical accessibility baseline + responsive layout of the
unified developer console (`/#/console`) after the Phase 2E-H1 hardening.

This review targets a **practical, keyboard-operable baseline** — not full WCAG
2.1 AA certification, which remains a deferred P2 item.

## Keyboard navigation

- The left nav rail is a `role="tablist"` (`aria-orientation="vertical"`) with
  **roving tabindex**: the active section is `tabindex=0`, all others `-1`.
- ArrowUp / ArrowDown / ArrowLeft / ArrowRight move selection **and focus** to
  the neighbouring tab (`#devconsole-nav-{section}`); Home / End jump to the
  first / last section; ArrowDown on the last item wraps to the first.
- Verified in a real browser by the Phase 2E-H1 smoke spec (ArrowDown moves the
  active section + reveals the target section content) and in jsdom by
  `phase2e-h1-console-routing` / `phase2e-h1-accessibility-responsive`.

## Tablist / nav rail semantics

- `nav[aria-label="Developer console sections"]` wraps a `role="tablist"`.
- One `role="tab"` per section (7), each with a visible text label and a
  decorative icon (`aria-hidden="true"`).
- The active tab carries `aria-selected="true"` and is the sole tab in the tab
  order.

## Labels

- Every interactive element is a real `<button>` / `<select>` / `<input>` with an
  accessible name (visible label, `aria-label`, or `aria-labelledby`).
- `AuditIdLink` carries `aria-label="Jump to audit viewer for {label} {id}"`.
- The Back-to-Workspace link carries `aria-label="Back to Workspace"`.

## Focus states

- `.devconsole-nav__item:focus-visible` provides a visible focus ring
  (`outline: 2px solid var(--color-focus-ring, …)`).
- `AuditIdLink:focus-visible` likewise draws a focus ring.
- Pinned by a hardening test that asserts the focus-visible rule exists in
  `devconsole.css`.

## Loading / error / blocked states

- `LoadingState`: `role="status"`, `aria-busy="true"`, `aria-live="polite"`.
- `ErrorState`: `role="alert"` with a retry button (`aria-label`).
- `BlockedReasonPanel`: `role="alert"` with a severity badge rendered as **text**
  (Info / Caution / Blocked) in addition to the `data-severity` tone.
- `EmptyState`: a message + optional hint.

## Non-color badges

- Safety badges carry visible text labels (e.g. "Real provider blocked") in
  addition to their tone — status is not conveyed by color alone.
- Overview summary cards use `data-tone` **plus** a textual value.
- Blocked-reason severity is rendered as both a colored badge and a text word.

## Responsive layout

- `devconsole.css` collapses the two-pane (nav rail | content) layout to a single
  column below **820px**: the nav rail becomes a horizontal wrap and the content
  stacks beneath it.
- The content area scrolls (`overflow-y: auto`); long JSON / diffs remain in
  scrollable blocks — no horizontal page overflow from the console.
- Pinned by a hardening test that asserts the `@media (max-width: 820px)` rule
  and the `overflow-y: auto` rule exist in `devconsole.css`.

## Reduced motion

- Transitions use the existing `--transition-fast` token; `prefers-reduced-motion`
  is honored by the theme system the console inherits.

## Known deferred items (P2)

- Full WCAG 2.1 AA audit.
- Focus-trap management for the future audit-event detail drawer.
- Screen-reader flow testing across all five themes.
- Advanced visual design system refinement / motion polish.
