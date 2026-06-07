# Phase 0B Workspace Shell

Phase 0B is complete. It adds the desktop workspace shell for Hermes Dev WebUI and remains a pure frontend static Mock preview with no backend or runtime integration.

## Routes

- `#/` renders `WorkspaceView`.
- `#/theme-lab` preserves the Phase 0A Theme Lab.
- Unknown routes redirect to the workspace.
- Both routes share the existing Pinia Theme Store.

## Component Structure

`WorkspaceView` renders `AppLayout`, which owns only the selected static session. The layout contains:

- `TopStatusBar`
- `SessionSidebar`
- `ChatWorkspaceShell` with a fixed Composer
- `WorkspacePanel`
- Static Files, Memory, Context, and Agent placeholders

The same component tree is used by all five themes.

## UI Store

`stores/ui.ts` owns:

- Session sidebar collapsed state
- Workspace panel collapsed state
- Active workspace tab

The store validates localStorage values, uses safe defaults, and guards repeated initialization. It does not contain sessions, messages, or sensitive data.

## Mock Boundary

Session entries and capability labels come from `mocks/workspace-shell.ts`. Placeholder panels are static Vue content. The workspace does not call APIs, read files, access Memory, connect to SessionDB, execute tools, or control the Gateway.

## Layout And Scrolling

The page uses a viewport-height CSS Grid. The status bar is fixed in the first row. The second row is a three-column grid with a flexible center. Session items, chat content, and workspace tab content scroll independently. The Composer remains in the center column's final grid row.

## Collapse Model

The left and right columns collapse independently to icon rails. CSS variables define expanded and collapsed widths. Collapsed workspace tab icons both select the tab and reopen the panel.

## Theme Adaptation

Shared semantic workspace variables define surfaces, dividers, active states, Composer, cards, and shadows. Theme selectors override only these visual values:

- Obsidian uses precise IDE-like boundaries.
- Paper uses even document surfaces and light shadows.
- Song uses a dark lacquer shell with a localized garden view.
- Ink uses moon-white planes, fading edges, and restrained distant layers.
- Sakura Night uses an indigo shell with one localized blossom crown.

Decorative pseudo-elements ignore pointer input and do not alter functionality.

## Phase 0B.1 Visual Refinement

Phase 0B.1 keeps the component tree, stores, routes, Mock data, and behavior unchanged. Shared semantic variables now control top-bar highlights, column boundaries, Empty State material, Composer highlights, and workspace tab states.

- Obsidian remains a compact neutral IDE with a tighter index panel.
- Paper uses a slightly warmer document surface and lighter elevation.
- Song uses lacquer beam and column boundaries, amber reflection, and one localized garden window in the context panel.
- Ink uses moon-white negative space, distant low-contrast mountain and water layers, fading ink boundaries, and one localized bamboo shadow.
- Sakura Night uses a deep-indigo shell, localized blossom canopy and connected branch shadow, cool moonlight, and one restrained warm anchor.

All artwork is original CSS gradient or inline SVG mask work. No external assets, theme-specific functional branches, real Agent, API, or SSE are introduced. The five themes form the current workspace baseline and may receive later visual refinement without changing this static Mock boundary.

## Accessibility

The shell uses semantic `header`, `nav`, `main`, and `aside` regions. Controls expose labels, collapsed state, controlled regions, selected tabs, and active session state. Workspace tabs support arrow, Home, and End keys. Focus indicators and reduced-motion behavior remain active.

## Phase Status

- Phase 0A: Completed and frozen as the five-theme system baseline.
- Phase 0B and Phase 0B.1: Completed.
- Phase 0C: Not started.
- Real Agent, API, SSE, SessionDB, Gateway, and formal Memory integration: Not started.

## Phase 0C Extension Points

Phase 0C can replace the center empty state with mock messages and add detailed mock tool, Memory, and Context states. Those additions should continue using the current layout, stores, semantic variables, and static-data boundary.
