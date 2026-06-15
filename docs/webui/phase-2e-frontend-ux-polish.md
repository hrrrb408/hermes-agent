# Phase 2E — Frontend UX Polish (Unified Developer Console)

**Status:** completed
**Branch:** `dev-huangruibang`
**Scope:** Frontend UX polish only. **No backend functional change, no new HTTP route, no production access.**

## Goal

Phases 2A–2D-H1 delivered the Dev WebUI backend capabilities (read-only tool
execution, controlled provider fake round-trip, sandbox write + rollback, durable
audit store). The frontend panels existed but were scattered as tabs inside the
chat workbench's right-hand panel. Phase 2E organizes those capabilities into a
**unified, demonstrable developer console** with a single at-a-glance landing
surface, consistent safety badges, unified empty/loading/error/blocked states,
and result→audit cross-navigation.

## What changed

### New `/#/console` route (additive, zero regression)

A full-screen developer console mirroring the `/#/theme-lab` pattern. `/#/`
remains the 3-column chat workbench **unchanged** — every Phase 2A/2B/2C smoke
spec keeps passing. `TopStatusBar` gains a "Dev Console" link (appended after the
Theme Lab link).

`DevConsoleLayout` = top bar + two-pane body (left nav rail | content). Seven
first-class sections, switchable via a `<KeepAlive>` dynamic component so each
section's shared store state survives section switches:

1. **Overview** — at-a-glance dashboard
2. **Tool Execution** — reuses `ToolExecutePanel`
3. **Provider Round-trip** — reuses `ProviderRoundtripPanel`
4. **Sandbox Write & Rollback** — reuses `ToolWritePanel`
5. **Audit Viewer** — reuses `AuditViewerPanel` (Phase 2D durable store)
6. **Safety Boundary** — consolidated invariant panel
7. **Diagnostics** — dev environment + release status

### Data sourcing (no backend changes)

- **Live** (read-only GETs): `GET /tools/policy` (inventory, risk, safety flags)
  and `GET /tools/audit-events` store-mode (store/index health), consumed
  through the existing `toolPolicy` / `toolAudit` Pinia stores.
- **Frozen baselines** (verified by gates, not fetched live): route governance
  34/34/5/0/1/1, production PID 28428, the sealed phase timeline. Centralized in
  `src/lib/frozenBaseline.ts`.

The Overview and Diagnostics sections do **not** execute `route_governance_read`
/ `dev_environment_read` / `release_status_read` live — doing so would consume
confirmation tokens and pollute the audit trail. The frozen values are
continuously verified by the smoke preflight and the backend invariant tests.

### Cross-navigation (回链)

`AuditIdLink` chips on result blocks (execute `postExecutionAuditId`, write
`rollbackId` + audit IDs, rollback audit IDs, provider `providerAuditIds`) call
`devConsoleNav.prefillAuditSearch(id)`, which switches to the Audit section,
enables store mode, sets the search filter, **and fires the query** — so the
located event is shown. This satisfies "jump from execution result to audit
event" and "see the rollback entry from the write result".

### Unified state + safety surface

New reusable components using the existing `.panel-*` CSS classes:
`LoadingState`, `EmptyState`, `ErrorState`, `BlockedReasonPanel` (fed by
`src/lib/blockedReasons.ts` — the authoritative backend blocked-reason catalogue
with a graceful unknown-code fallback), `AuditIdLink`. New libs: `safetyBadges`,
`formatters`, `frozenBaseline`.

## Scope discipline

The existing workspace panels keep their inline badge arrays and their own
`formatBytes` — they are **not** refactored (blast radius onto the 2A/2B/2C smoke
specs). Only the new console sections consume the new libs. The existing panels
are reused as-is inside console section wrappers.

## Files

- **Frontend:** `apps/hermes-dev-webui/src/{lib,stores,components/devconsole,components/common,views,router,styles}` —
  see `phase-2e-dev-console-ux-map.md` for the full map.
- **Smoke:** `scripts/run-dev-webui-execute-audit-smoke.sh` (new
  `phase2e_frontend_ux_polish` profile) +
  `apps/hermes-dev-webui/tests/smoke/phase-2e-frontend-ux-polish-smoke.spec.ts`.
- **Backend:** no source changes. `tests/test_dev_web_phase_2e_frontend_contract.py`
  pins the Overview data-source contract + route-governance baseline.

## Safety guarantees (unchanged)

No production rollout. No `~/.hermes` access. No production `state.db` access.
No shell command execution. No database mutation. No external service write. No
real provider vendor network call. No Provider auto-write / auto-rollback. No
new Tool write HTTP route. No Provider route. The UI never exposes API keys,
raw tokens, full token hashes, raw arguments, secrets, callable/function reprs,
or production paths.

Route governance remains **OpenAPI 34 / runtime 34 / tool GET 5 / tool write
route 0 / dry-run 1 / execution 1**. Production Gateway PID **28428** untouched.

## Gates

- Frontend: `pnpm type-check` / `lint` / `test` (807 tests) / `build` — all PASS.
- Backend contract: `tests/test_dev_web_phase_2e_frontend_contract.py` — 9 PASS.
- Smoke: `./scripts/run-dev-webui-execute-audit-smoke.sh all` — all profiles
  including `phase2e_frontend_ux_polish` PASS; PID 28428 unchanged; ports free.

## Deferred (P2)

Full WCAG certification; advanced visual design system refinement; production
audit rollout; audit encryption at rest; multi-user namespace; retention
deletion; compression; advanced full-text indexing; real provider vendor
integration; Phase 3.
