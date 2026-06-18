# Phase 3C-H1 — UI / A11y / No-leak Hardening

| Field | Value |
|-------|-------|
| Lens | 11 — Frontend UI / Badges / Accessibility / No-leak |
| Hardening ID | `CAP-UI-3C-H1-001` |
| Status | PASS |

## Scope

The Dev WebUI Capability Registry panel is read-only, accessible (badges are
not color-only), and value-free in every state (default, validation_failed,
empty, every selected detail).

## Evidence

- Section renders summary + table + filters; the "describes only / does not
  grant permission" + "no plugin runtime / dynamic loading / remote registry /
  marketplace" messaging appears in both the intro and the summary note.
- The five frozen policy flags render as yes/no; the route-governance baseline
  `34/34/5/0/1/1` surfaces; validation passed (0 errors).
- Detail drawer renders the safe record — badges, runtime gates, bindings, the
  explicit "Registry describes only — does not grant permission" notice — and
  is read-only (one close button, no inputs). Blocked capabilities surface
  their blocked reason.
- Every permission / trust / status badge renders a human **text label**
  (icon + label), exposes a `title` attribute for screen readers, and carries
  an explicit text marker ("Forbidden" / "Not executable") for the
  non-executable classes — status is never communicated by hue alone.
- No-leak: the section HTML, the store state, and the manifest JSON carry no
  forbidden token; no API-key / password input exists; no production path or
  `state.db` surfaces.
- `validation_failed` and null-summary states render safely (placeholders, no
  crash); an empty filtered table renders gracefully; blocked reasons are
  visible.

## Commands

```bash
cd apps/hermes-dev-webui
npx vitest run src/tests/phase3c-h1-registry-{mirror,panel,detail,badges-a11y,no-leak,validation-states}.spec.ts
```

## Fixes

Test-only. No implementation change.

## Residual risk

None.
