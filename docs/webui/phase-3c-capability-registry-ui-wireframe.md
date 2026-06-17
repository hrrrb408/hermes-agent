# Phase 3C — Capability Registry UI Wireframe (Optional)

| Field | Value |
|-------|-------|
| Phase | 3C (Planning) |
| Title | Capability Registry — UI Wireframe (ASCII) |
| Status | Frozen (docs-only planning; Capability Registry **not started**) |
| Date | 2026-06-17 |
| Planning ID | `PHASE-3C-PLANNING-001` |

> Optional companion to the UI & status design. ASCII sketches only — no
> component is built in this phase. Read-only throughout.

## 1. Console: Capability Registry panel

```
┌─ Capability Registry ──────────────────────────────────────────┐
│ Filter: [ category ▾ ] [ permission ▾ ] [ trust ▾ ] [ status ▾ ]│
│ Search: [____________________]              dev-only · read-only │
├────────────────────────────────────────────────────────────────┤
│ ID                          CATEGORY   PERMISSION     STATUS     │
│ tool.read.route_governance  system     READ_ONLY      ● enabled │
│ provider.fake_roundtrip     provider   READ_ONLY      ● enabled │
│ provider.live_manual_one…   provider   LIVE_GATED     ○ disabled│
│ sandbox.write.file_write    sandbox    WRITE_CONFIRM  ● enabled │
│ tool.forbidden.shell        tool       ADMIN_FORBIDDN ✕ blocked│
└────────────────────────────────────────────────────────────────┘
```

Badges are icon + label (non-color), not color-only. Blocked rows show a
`blockedReason` tooltip / drawer line.

## 2. Capability Detail Drawer

```
┌─ tool.read.route_governance ───────────────────────────────────┐
│ Display name     Route governance read                          │
│ Category         system                                          │
│ Permission       READ_ONLY                                       │
│ Trust            BUILTIN_VERIFIED                                │
│ Status           enabled                                         │
│ requiresApproval no    requiresAudit yes                         │
│ devOnly          true   productionAllowed false                  │
│ relatedTool      route_governance_read                           │
│ Audit            [capability_registry_capability_viewed] →       │
└────────────────────────────────────────────────────────────────┘
```

The drawer shows **only** safe fields. No key, token, hash, callable repr, path,
shell command, or SQL ever appears.

## 3. `/status` capabilityRegistry block

```
capabilityRegistry:
  loaded: true
  validationPassed: true
  capabilityCount: <n>
  enabledCount: <n>
  blockedCount: <n>
  devOnly: true
  productionAllowed: false
  dynamicLoading: false
```

## 4. Notes

- Panel is additive to `/#/console`; `/#/` chat workbench is unchanged.
- No enable / disable / promote / delete control in the first version.
- Motion respects `prefers-reduced-motion`.

## 5. Cross-references

- [Phase 3C UI & status design](phase-3c-ui-and-status-design.md)
- [Phase 3C capability model](phase-3c-capability-model.md)
