# Phase 2E — Dev Console UX Map

A reference map of the unified developer console introduced in Phase 2E: the
navigation structure, the section components, and the data flow for each.

## Top-level navigation

```
Dev WebUI (createWebHashHistory)
├── /            → WorkspaceView      (3-column chat workbench, unchanged)
├── /console     → DevConsoleView     (Phase 2E unified developer console)
├── /theme-lab   → ThemeLabView       (unchanged)
└── *            → redirect /
```

`TopStatusBar` (present on every view) links to both `/console` and `/theme-lab`.

## `/console` structure

```
DevConsoleView
└── DevConsoleLayout
    ├── top bar (title + ThemeSwitcher + "Back to Workspace")
    └── body
        ├── DevConsoleNav            (left rail, roving-tabindex tablist)
        └── content
            └── <KeepAlive>
                └── <component :is="activeSection" />
                    ├── OverviewSection
                    ├── ToolExecutionSection
                    ├── ProviderSection
                    ├── WriteRollbackSection
                    ├── AuditViewerSection
                    ├── SafetySection
                    └── DiagnosticsSection
```

The `<KeepAlive>` wrapper is deliberate: it keeps each section's instance alive
across switches so shared Pinia store state (notably `AuditViewerPanel`'s
`onUnmounted(() => store.reset())`) is not torn down when the user navigates
between sections.

## Section → component → store → API

| Section | Reuses / builds | Store(s) read | API |
|---|---|---|---|
| Overview | new (`StatusSummaryCards`, `SafetyBadgeBar`, `LoadingState`/`ErrorState`) | `toolPolicy`, `toolAudit`, `devConsoleNav` | GET /tools/policy, GET /tools/audit-events (store mode) |
| Tool Execution | `ToolExecutePanel` + cross-nav strip | `toolExecute` | POST /tools/dry-run, /tools/execute |
| Provider Round-trip | `ProviderRoundtripPanel` + `BlockedReasonPanel` + cross-nav | `toolProvider` | POST /tools/execute (mode=provider_roundtrip) |
| Sandbox Write & Rollback | `ToolWritePanel` + `BlockedReasonPanel` + cross-nav | `toolWrite` | POST /tools/dry-run (write_preview/rollback_preview), /tools/execute (write/rollback) |
| Audit Viewer | `AuditViewerPanel` + prefill marker | `toolAudit`, `devConsoleNav` | GET /tools/audit-events (legacy + V2 store) |
| Safety Boundary | new (`SafetyBadgeBar`, grouped badges) | `toolPolicy` | GET /tools/policy |
| Diagnostics | new (frozen baseline) | — | none (frozen constants) |

## Cross-navigation bridge (`devConsoleNav.prefillAuditSearch`)

```
result block (Tool/Write/Provider section)
  └── AuditIdLink @navigate="locate(id)"
       └── devConsoleNav.prefillAuditSearch(id)
            ├── activeSection = 'audit'
            ├── toolAudit.setStoreMode(true)
            ├── toolAudit.setSearchInput(id)
            └── toolAudit.loadStoreEvents()   ← the load is essential
```

Setting the filter alone is not enough — `AuditViewerPanel` only queries from
`onMounted` / Apply / pagination, so the bridge must fire the query.

## New frontend files

```
apps/hermes-dev-webui/src/
├── lib/
│   ├── frozenBaseline.ts        # pinned governance/PID/phase constants
│   ├── formatters.ts            # formatBytes / truncateHash / formatTimestamp / formatCount / formatFlag
│   ├── safetyBadges.ts          # unified SafetyBadge[] (8 invariant badges)
│   └── blockedReasons.ts        # code → {title, explanation, safeNextAction, severity} + fallback
├── stores/
│   └── devConsoleNav.ts         # activeSection (persisted) + prefillAuditSearch
├── components/
│   ├── common/
│   │   ├── LoadingState.vue
│   │   ├── EmptyState.vue
│   │   ├── ErrorState.vue
│   │   ├── BlockedReasonPanel.vue
│   │   └── AuditIdLink.vue
│   └── devconsole/
│       ├── DevConsoleLayout.vue
│       ├── DevConsoleNav.vue
│       ├── OverviewSection.vue
│       ├── ToolExecutionSection.vue
│       ├── ProviderSection.vue
│       ├── WriteRollbackSection.vue
│       ├── AuditViewerSection.vue
│       ├── SafetySection.vue
│       ├── DiagnosticsSection.vue
│       ├── StatusSummaryCards.vue
│       └── SafetyBadgeBar.vue
├── views/
│   └── DevConsoleView.vue
└── styles/
    └── devconsole.css           # global dev-console stylesheet (semantic vars only)
```

Plus edits (additive only): `router/index.ts` (`/console` route),
`components/layout/TopStatusBar.vue` (Dev Console link),
`styles/workspace.css` (`.dev-console-link`), `main.ts` (import `devconsole.css`).

## Test hooks

- Nav rail buttons: `#devconsole-nav-{section}` (role=tab, roving tabindex).
- Overview: `[data-testid="dev-safety-badges"]`, `[data-testid="dev-summary-cards"]`.
- State components: `[data-testid="dev-loading-state|dev-empty-state|dev-error-state|dev-blocked-reason|dev-audit-id-link|dev-audit-clear-prefill"]`.
- Reused panels keep their existing hooks (`#tool-execute-canonical`, `#write-tool`, `#provider-mode`, `#audit-viewer-store-toggle`, …).
