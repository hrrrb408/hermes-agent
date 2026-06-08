# Phase 0D: Responsive Breakpoints, Accessibility, Motion

**Status:** Completed
**Date:** 2026-06-08
**Branch:** dev-huangruibang
**Precedes:** Phase 0C Final Closure (564c15c98)

## Scope

Phase 0D hardens the Dev WebUI for responsive layout, accessibility compliance, reduced-motion support, and visual regression verification. No new business features, API routes, or backend capabilities were added.

## Responsive Breakpoint Strategy

### Breakpoint Definitions

| Name | Width | Behavior |
|------|-------|----------|
| Wide | ≥ 1440px | Full three-column layout, all panels visible |
| Desktop | 1280–1439px | Three-column with slightly compressed sidebar/panel widths |
| Compact | 1024–1279px | Three-column with narrower sidebar (220px), hidden status bar items |
| Critical | 900–1023px | Right panel auto-collapsed to icon strip |
| Tablet | 768–899px | Both panels auto-collapsed to icon strips, home label hidden |
| Minimum | ≤ 640px | Forced icon-only sidebar/panel, reduced padding |

### Layout Behavior

- **Sidebar**: `--workspace-sidebar-width: 264px` (expanded), `56px` (collapsed). Text content hidden when collapsed; icon-only items remain keyboard-accessible.
- **Workspace Panel**: `--workspace-panel-width: 328px` (expanded), `56px` (collapsed). Tab icons visible when collapsed with `aria-label` for screen readers.
- **Collapse persistence**: Both panels persist their collapse state to `localStorage` via the UI store. Restored on page load.
- **Minimum support width**: 640px. Below this, all side panels are forced to icon-only mode. Core chat workspace remains readable and scrollable.

### What Was Added

Responsive CSS breakpoints in `workspace.css`:
- `@media (max-width: 1320px)` — compress sidebar/panel widths (pre-existing, now consolidated)
- `@media (max-width: 1024px)` — narrower sidebar, hide status bar items
- `@media (max-width: 900px)` — force right panel collapsed
- `@media (max-width: 768px)` — force both panels collapsed
- `@media (max-width: 640px)` — minimum support, reduced padding

## Accessibility Audit

### Semantic HTML

| Component | Element | Role |
|-----------|---------|------|
| TopStatusBar | `<header role="banner">` | Page banner |
| SessionSidebar | `<nav aria-label="Sessions">` | Navigation |
| ChatWorkspaceShell | `<main>` | Main content |
| WorkspacePanel | `<aside aria-label="Workspace context">` | Complementary |
| Message list | `<ol aria-label="Session messages">` | Ordered list |
| Composer form | `<form>` with `<label for>` | Form with label association |
| Time elements | `<time datetime="...">` | Machine-readable timestamps |

### ARIA Attributes Added/Fixed

| Component | Attribute | Purpose |
|-----------|-----------|---------|
| MemoryPanel error | `role="alert"` | Announce errors to screen readers |
| MemoryPanel loading | `aria-busy="true"`, `aria-live="polite"` | Loading state announcement |
| ContextPanel error | `role="alert"` | Announce errors to screen readers |
| AgentPanel error | `role="alert"` | Announce errors to screen readers |
| AgentPanel loading | `aria-busy="true"` | Loading state announcement |
| TopStatusBar | `role="banner"` | Explicit banner landmark |
| Panel retry buttons | `aria-label` with descriptive text | Identifiable retry actions |

### Keyboard Navigation

- **Tab order**: TopStatusBar → Session search → Session items → Load More → Workspace header → Panel tabs → Panel content → Composer
- **Tab panels**: Arrow key navigation (Home/End/Left/Right) cycles through workspace panel tabs
- **Tabindex management**: Active tab has `tabindex="0"`, inactive tabs have `tabindex="-1"`
- **Focus visible**: `:focus-visible` styles added for session items, panel retry buttons, composer actions, new-session button

### Focus Management

- Collapsed panels use `v-if` to remove hidden content from DOM, preventing focus on invisible elements
- Tab/tabpanel structure ensures focus stays within active panel
- IconButton component includes `aria-expanded` and `aria-controls` for collapse toggles

## Reduced Motion

### CSS Support

Already existed in Phase 0C, verified and preserved:

1. **`base.css`** — `@media (prefers-reduced-motion: reduce)`:
   - Sets `--transition-fast: 0ms` and `--transition-normal: 0ms`
   - Sets `animation-duration: 0.01ms !important`
   - Sets `transition-duration: 0.01ms !important`
   - Sets `scroll-behavior: auto !important`

2. **`workspace.css`** — `@media (prefers-reduced-motion: reduce)`:
   - Sets `transition: none` on `.workspace-body`, `.session-item`, `.workspace-tab`, `.theme-lab-link`

3. **Data-attribute motion mapping**:
   - `[data-motion="none"]` → 0ms transitions
   - `[data-motion="reduced"]` → 60ms/100ms transitions
   - `[data-motion="subtle"]` (default) → 120ms/180ms
   - `[data-motion="smooth"]` → 150ms/250ms

### Animation Policy

- Motion is intentionally minimal
- All transitions are cosmetic (color, opacity, border) — never layout-critical
- Spinner uses `aria-hidden="true"` on decorative icon, with text fallback for screen readers
- Reduced motion disables non-essential transitions globally

### Theme Motion Values

| Theme | Motion |
|-------|--------|
| Obsidian | `subtle` |
| Paper | `reduced` |
| 宋韵 Song | `reduced` |
| 墨境 Ink | `reduced` |
| 夜樱 Sakura Night | `subtle` |

## Visual Regression Matrix

### Required Matrix (Executed)

| Check | Result |
|-------|--------|
| API health (status 200, readOnly, isolation) | PASS |
| OpenAPI (11 business paths, 1 POST) | PASS |
| Forbidden routes (reviews, agent/run, tools, SSE, WS) | PASS (all 404) |
| WebUI HTML serves (200, valid DOCTYPE) | PASS |
| No 0.0.0.0, localhost, /Users/ in HTML | PASS |
| No 5182 port references | PASS |
| Path redaction in memory responses | PASS |
| Agent status: readOnly=true, toolExec=false | PASS |
| Session data loads (30 sessions) | PASS |
| Message data loads (3 messages in test session) | PASS |
| Memory status available (2 active memories) | PASS |

### Extended Matrix (Documented)

Full viewport × theme matrix (6 viewports × 5 themes = 30 combinations) requires Playwright browser automation with actual viewport resizing. The CSS breakpoints are defined and tested via unit tests. Manual spot-checking at 1440×900 and 1280×800 with all five themes confirmed no horizontal overflow or layout breakage.

## Non-goals

- No new business API routes
- No write operations or agent execution
- No mobile-first responsive redesign
- No new animation or transition effects
- No new dependencies

## Open Risks

- **P2**: Full Playwright viewport × theme matrix not automated (requires Playwright setup)
- **P2**: `dist/` and `tsconfig.*.tsbuildinfo` are tracked in Git (build artifact policy deferred)
- **P2**: Vite dev mode `data-vite-dev-id` attributes contain local paths (production build does not)
