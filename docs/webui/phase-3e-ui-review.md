# Phase 3E — UI Review

| Field | Value |
|-------|-------|
| Phase | 3E (Planning) |
| Title | Real Plugin Runtime — UI Review (Frozen, Design-only) |
| Status | Frozen (docs-only planning; Real Plugin Runtime **not started**) |
| Date | 2026-06-19 |
| Planning ID | `PHASE-3E-PLANNING-001` |
| UI-Review ID | `PHASE-3E-UI-REVIEW-001` |

> This document reviews — but does **not** implement — the UI a future real
> plugin runtime would surface. No implementation is authorized.

## 1. UI must show

```
Real runtime disabled
Plugin execution disabled
Dynamic loading disabled
Local plugin directory disabled
Remote registry disabled
Marketplace disabled
External plugin fetch disabled
Production rollout disabled
```

The runtime-disabled banner invariants carry over from Phase 3D: descriptor-only,
does not execute a plugin, does not grant permission.

## 2. UI must NOT show

```
secret
API key
Authorization
Bearer
raw token
callable repr
shell command
SQL
production path
filesystem path
network URL
download URL
install command
```

## 3. Planned UI surfaces (future, not built now)

- A **runtime warning banner** stating the runtime is disabled and that
  execution / loading / fetch / marketplace / production rollout are all
  disabled.
- A **NO-GO decision card** summarizing the runtime GO / NO-GO.
- A **sandbox planning panel** (read-only summary of the four sandbox options and
  the recommendation).
- A **threat-model summary** (read-only, count of threats, default verdict).
- A **human-review status** line (planning reviewed; implementation not
  authorized).
- An **"implementation not authorized"** label.

All surfaces are read-only, accessible (non-color badges, focus-visible, keyboard
nav), and no-leak.

## 4. No-leak closure

- Badges are label + icon (never color-only).
- No raw descriptor value that could carry a forbidden field is rendered without
  the recursive safe-allowlist pass.
- The runtime-disabled banner is always shown; it is never hidden by a feature
  flag in this phase.

## 5. Cross-references

- [Phase 3E planning](phase-3e-planning.md)
- [Phase 3E audit / redaction review](phase-3e-audit-redaction-review.md)
- [Phase 3E human review brief](phase-3e-human-review-brief.md)
- [Phase 3D UI / status design](phase-3d-ui-and-status-design.md)
- [Phase 2E-H1 UI security closure](phase-2e-h1-ui-security-closure.md)
