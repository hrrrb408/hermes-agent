# Phase 3J — Runtime Governance Read-only WebUI Surface (evidence)

> **Status:** implemented + completion/QA pass — a **read-only** WebUI surface
> over the Phase 3I dev-only descriptor-backed fixture runtime. This is **not**
> a closeout, **not** a signoff, **not** an archive, **not** an authorization
> review, **not** a production runtime, **not** a real plugin runtime expansion,
> **not** an arbitrary plugin loader, and **not** a WebUI execution surface.
>
> **Code allowed, production forbidden.**

## 1. Scope

Phase 3J exposes the already-implemented Phase 3I runtime governance CLI
capability (`hermes dev-runtime …`) as a **read-only Dev WebUI surface**. The
WebUI may *display* the descriptor list, the registry→runtime binding, the
audit/report projection, the P0 evidence projection, the authorization boundary,
the no-side-effect invariant, the CLI usage examples, the route-governance
summary, and the no-production status. The WebUI may **not** execute, approve,
authorize, load, upload, fetch, roll out, or otherwise mutate anything.

The surface is a **client-side DevConsole section** inside the existing
`/console` view. It introduces **no backend HTTP route**, **no OpenAPI path**,
**no SPA route**, and **no import** of the runtime-governance / plugin-runtime
modules into the FastAPI app.

The completion pass takes the surface from "renders" to "deliverable": a stable
page heading hierarchy, explicit page-header status badges, a horizontally
scrollable / keyboard-focusable descriptor table, a defense-in-depth-frozen
manifest, a harmless clipboard **Copy** affordance for CLI examples, and a
broadened accessibility / no-leak / snapshot / immutability test suite.

## 2. What the WebUI displays

A Dev Console nav entry — **Runtime Governance** — renders a single read-only
page with these regions:

| Region | Content |
|--------|---------|
| Page header | An `<h1>` title, five frozen status badges (**DEV-ONLY / READ-ONLY / FIXTURE-ONLY / NO PRODUCTION / NO WEBUI EXECUTION**), and an explicit read-only explanation (displays only — does not execute, load, authorize, or add a route). |
| Boundary banner | DEV-ONLY / READ-ONLY / FIXTURE-ONLY rows + the frozen authorization verdicts (every dimension NO-GO / NOT_AUTHORIZED / false). |
| Plugin-runtime-disabled banner | Re-used Phase 3D banner: no plugin runtime, no loader, no dynamic loading, no local directory loading, no remote registry, no marketplace, no external fetch, no provider/LLM-generated plugin. |
| Summary cards | Reviewed descriptors (6), supported fixture plugins (7), supported operations (7), P0 gates (24), P0 resolved (0), partial evidence (19), pending human review (5), side effects (all false), backend routes changed (no). |
| Descriptor table | The six reviewed-fixture descriptors with safe metadata only + a single harmless **Inspect** action (opens the read-only binding detail). Wrapped in a keyboard-focusable, horizontally-scrollable region so the wide table never overflows narrow screens; carries a `<caption>` and `aria-current` on the selected row. |
| Descriptor binding detail | Read-only binding projection (descriptorId, bindingAllowed, source=`static_descriptor_registry`, pluginId, operation, devOnly, fixtureOnly, reviewedFixture, denialReasons, triggeredGuards, runtimeFlags, redactedDescriptor) + an empty state and a denied-state preview. |
| Fixture allowlist | The seven dev-only fixture (pluginId, operation) pairs. |
| P0 evidence panel | totalGates=24, resolvedCount=0, partial=19, candidate=0, blocked-by-human-review=5, governance-only/no-evidence=0, unresolved=24; Implementation Authorization NO-GO; Phase 3I production authorization NOT_AUTHORIZED; production runtime NO-GO; new route NO-GO; production rollout NO-GO. |
| Side-effect matrix | The frozen all-False surface (12 flags): productionAccess, externalNetwork, realSecretRead, routeChange, runtimeStoreWrite, auditStoreWrite, arbitraryPluginLoad, localPluginDirectoryRead, remotePluginFetch, marketplaceAccess, inputFileRead, outputFileWrite. No toggle, no input. |
| Route governance | Frozen baseline `34/34/5/0/1/1`; backend routes changed = **no**; new HTTP route = 0; new runtime/plugin route = 0. |
| CLI examples | Text-only `hermes dev-runtime list / show / run / batch / audit / p0-report` examples (run **outside** the WebUI) with a harmless per-command **Copy** button (clipboard only — never executes, never networks). |

### Page / nav location

Client-side Dev Console section `runtimeGovernance` (label **Runtime Governance**)
inside the existing `/console` view. Served by already-approved static data. **No
SPA route and no backend route** was added.

## 3. Data source strategy (frontend-only, deterministic, frozen)

The page reads from a **frozen static TypeScript manifest** derived from the
backend frozen constants — no current time, no random id, no uuid, no network
fetch, no file read, no file write, no process spawn, no CLI call:

- `apps/hermes-dev-webui/src/constants/runtimeGovernanceManifest.ts` — every
  exported constant is `deepFreeze`d at module load (arrays, objects, and their
  nested members), so the canonical governance state is immutable at runtime: an
  external caller can never mutate a returned projection back into the manifest,
  never flip a frozen NO-GO verdict, and never flip a frozen False side-effect
  flag. Holds the reviewed descriptors, fixture allowlist, P0 evidence,
  authorization verdicts, side-effect flags, runtime flags, CLI
  examples/commands/aliases, page-header status badges, boundary-banner rows,
  and the denied-preview denial reasons.
- `apps/hermes-dev-webui/src/lib/runtimeGovernanceViewModel.ts` — pure, total,
  deterministic projection helpers that return **defensive copies** of the frozen
  collections (`buildRuntimeGovernanceViewModel`, `buildDescriptorRows`,
  `buildDescriptorBindingDetail`, `buildSummaryCards`, `buildStatusBadges`,
  `buildBoundaryItems`, `buildDeniedPreview`, `findDescriptorRow`,
  `redactRuntimeValue` / `sanitizeRuntimeGovernanceDisplayText`,
  `allSideEffectsFalse`, `allVerdictsNoGo`) + a defense-in-depth redactor.

Provenance of every frozen value is the backend module set:
`hermes_cli/dev_web_runtime_governance.py`,
`hermes_cli/dev_web_plugin_runtime_binding.py`,
`hermes_cli/dev_web_plugin_runtime.py`, `hermes_cli/dev_web_p0_evidence.py`.

## 4. Files

### Frontend (page, components, view-model, types)

- `apps/hermes-dev-webui/src/types/api/runtimeGovernance.ts`
- `apps/hermes-dev-webui/src/constants/runtimeGovernanceManifest.ts`
- `apps/hermes-dev-webui/src/lib/runtimeGovernanceViewModel.ts`
- `apps/hermes-dev-webui/src/components/devconsole/RuntimeGovernanceSection.vue`
- `apps/hermes-dev-webui/src/components/devconsole/RuntimeBoundaryBanner.vue`
- `apps/hermes-dev-webui/src/components/devconsole/RuntimeDescriptorTable.vue`
- `apps/hermes-dev-webui/src/components/devconsole/RuntimeDescriptorDetail.vue`
- `apps/hermes-dev-webui/src/components/devconsole/RuntimeP0EvidencePanel.vue`
- `apps/hermes-dev-webui/src/components/devconsole/RuntimeSafetyMatrix.vue`
- `apps/hermes-dev-webui/src/components/devconsole/RuntimeCliExamples.vue`

### Wiring (client-side nav only — no route)

- `apps/hermes-dev-webui/src/stores/devConsoleNav.ts` — the
  `runtimeGovernance` DevConsole section (union, `CONSOLE_SECTIONS`,
  `CONSOLE_SECTION_LABELS`).
- `apps/hermes-dev-webui/src/components/devconsole/DevConsoleLayout.vue` — maps
  the section to `RuntimeGovernanceSection`.
- `apps/hermes-dev-webui/src/components/devconsole/DevConsoleNav.vue` — the nav
  icon (`ScrollText`).

### Tests

- `apps/hermes-dev-webui/src/tests/phase3j-runtime-governance-panel.spec.ts`
- `apps/hermes-dev-webui/src/tests/phase3j-runtime-governance-view-model.spec.ts`
- `apps/hermes-dev-webui/src/tests/phase3j-runtime-governance-no-leak.spec.ts`
- `apps/hermes-dev-webui/src/tests/phase3j-runtime-governance-routes.spec.ts`
- `apps/hermes-dev-webui/src/tests/phase3j-runtime-governance-completion.spec.ts`
  (completion/QA: UX regions, descriptor interactions, responsive basics,
  accessibility, no-execution controls, no-network, P0/NO-GO, side effects,
  redaction corpus, inline DOM snapshots, clipboard-copy, route/nav)
- `tests/test_dev_web_phase_3j_runtime_governance_webui_isolation.py`

### Backend Python touched

**None for behavior.** No backend route, no OpenAPI path, no `dev_web_api`
import, and no runtime-governance code path was added or changed. The backend
test file above is **isolation-only**: it asserts the FastAPI app does **not**
import the governance/runtime modules, that no route is named for runtime
governance, that candidate API paths return 404, and that the frozen
`34/34/5/0/1/1` baseline is unchanged. `ruff` is therefore N/A (no Python
modified).

## 5. Read-only guarantee (what the WebUI does NOT do)

- **No WebUI execution.** No Run / Execute / Batch / Approve / Authorize /
  Enable / Load / Upload / Fetch / Install / Deploy / Rollout control. The only
  controls are harmless UI-only selects: **Inspect** (open read-only binding),
  **Preview denied state** (a read-only state preview), and **Copy** (clipboard
  text only).
- **No inputs.** No `<input>`, no `<textarea>`, no `<select>`, no API-key input,
  no secret input, no file picker, no JSON execution input.
- **No new backend route.** No `dev_web_api` route, no OpenAPI path, no
  `dev_web_api` import of runtime-governance / plugin-runtime modules.
- **No production access.** No `~/.hermes` access (not even metadata-only
  stat/ls/resolve), no production `state.db` access.
- **No plugin loading.** No arbitrary plugin loading, no local plugin directory
  loading, no remote registry, no marketplace, no external plugin fetch, no
  provider-generated / LLM-generated plugin install.
- **No external network, no real API key read.** (The Copy affordance writes
  only to the local clipboard — never to the network.)
- **No file I/O.** No input-file reading, no output-file writing, no persistent
  audit store.
- **No authorization drift.** `resolved_count` stays 0; Implementation
  Authorization stays NO-GO; Phase 3I production authorization stays
  NOT_AUTHORIZED; production runtime stays NO-GO; new route stays NO-GO;
  production rollout stays NO-GO.

## 6. P0 evidence summary

- Total P0 gates: **24**
- Resolved / approved: **0**
- Partial evidence: **19**
- Candidate for review: **0**
- Pending human review (blocked_by_human_review): **5**
- Governance-only / no evidence: **0**

A descriptor-backed fixture execution (single or batch) is **dev-only partial
evidence**. It is never Implementation Authorization GO, never Phase 3I
production authorization, never real-runtime authorization, never a P0
resolution. Implementation Authorization remains NO-GO for production / real
external runtime because resolution requires a valid out-of-band human approval
the dev skeleton cannot produce (no trust token is provisioned).

## 7. Route governance (unchanged)

```
OpenAPI paths        = 34
Runtime routes       = 34
Tool GET             = 5
Tool write HTTP      = 0
Tool dry-run route   = 1
Tool execution route = 1
New HTTP route       = 0
New Tool write route = 0
New Provider route   = 0
New plugin route     = 0
New runtime route    = 0
```

Baseline: `34/34/5/0/1/1`. Verified by
`tests/test_dev_web_phase_3j_runtime_governance_webui_isolation.py`
(`TestRouteGovernanceUnchanged`) and the pre-existing
`tests/test_dev_web_phase_3e_h_safety_baseline.py`.

## 8. Accessibility / responsive / snapshot / no-leak tests

- **Accessibility.** Exactly one page `<h1>`; every region is an `<h2>`;
  sub-details (`Runtime flags (frozen)`) are `<h3>`. The descriptor table has a
  `<caption>`, labelled column headers, an accessible name on every Inspect
  button, and `aria-current="true"` on the selected row. Boundary and verdict
  state is conveyed by **text** (non-color), never color alone. No form-control
  input exists on the page.
- **Responsive.** The wide descriptor table is wrapped in a
  keyboard-focusable, horizontally-scrollable region (`role="region"` +
  `tabindex="0"`) so it never overflows narrow screens; summary / verdict / flag
  grids use `auto-fit` so they reflow; CLI commands wrap (`pre-wrap` +
  `word-break`); status badges use a wrapping flex row.
- **Snapshots.** Inline DOM/array snapshots pin the status-badge labels, the
  descriptor id sequence, the side-effect key sequence, and the CLI command list
  for regression.
- **No-leak / no-execution.** The full rendered HTML contains no secret /
  production-path / execution token; no button offers an execution/approval verb;
  no `<input>` / `<textarea>` / file picker exists; render + descriptor selection
  + denied preview + copy make **no** `fetch` / `XMLHttpRequest` call.
- **View-model immutability.** The canonical manifest is `Object.isFrozen`;
  mutating returned descriptor rows, bindings, side-effect flags, or
  authorization verdicts cannot flip the canonical invariants.
- **Redaction.** The defense-in-depth redactor masks the full corpus
  (`sk-…`, `Authorization: Bearer …`, `ghp_…`, `xox…`, `BEGIN PRIVATE KEY`,
  `OPENAI_API_KEY=…`, `db_password=…`, `accessToken=…`, `~/.hermes`,
  `state.db`, `implementation_authorization=GO`, `phase_3i_authorized=true`,
  `production_approved=true`, `route_exception_approved=true`).

## 9. Playwright / smoke

The repo ships a Playwright smoke harness, but it requires the Dev API bound on
`127.0.0.1:5181` and the WebUI on `127.0.0.1:5180`. Under this task's production
safety constraints, **ports 5180 / 5181 must remain free**, the Dev Gateway must
stay stopped, and the Dashboard must not start — so the smoke harness is **not
run** for this change. Coverage is provided instead by the Vitest / jsdom suite
(component DOM, accessibility, no-execution, no-network, snapshots) plus the
backend isolation test. No regression in the smoke harness is introduced (no
backend route, no SPA route, no port binding change).

## 10. Validation

- Frontend: `pnpm test` (Vitest) — full suite green (1331 tests), including the
  five Phase 3J files (panel / view-model / no-leak / routes / completion).
- Frontend: `pnpm run type-check` (`vue-tsc --noEmit`) — clean.
- Frontend: `pnpm run lint` (ESLint) — clean.
- Backend: `python -m pytest
  tests/test_dev_web_phase_3j_runtime_governance_webui_isolation.py` — 12/12
  pass.
- Backend governance + safety scopes (Phase 3I / 3E-H / 3J) — 928 passed.
- Backend Phase 3D descriptor-registry scopes — 614 passed, 2 skipped.
- `./scripts/run-dev-hermes.sh memory-check` — PASS.
- `./scripts/run-dev-hermes.sh dev-check` — route/safety checks PASS (only the
  expected dirty-worktree WARN from this in-flight change).
- `ruff` — N/A (no Python modified).

## 11. Production safety

No `~/.hermes` access (not even metadata-only). No production `state.db` access.
No production Gateway touch (PID unchanged, not stopped / restarted / replaced /
signaled). Dev Gateway remains stopped. Dashboard not started. Ports 5180 / 5181
remain free. `.claude` remains untracked / unstaged / uncommitted.

## 12. Deferred / still not authorized

Production plugin runtime, arbitrary plugin loading, user-uploaded plugins,
local plugin directory loading outside the fixture allowlist, remote registry,
marketplace, external plugin fetch, provider-generated / LLM-generated plugin
install, real API key reading, external network, new backend route, WebUI
execution route, WebUI Run/Approve/Authorize action, production rollout,
provider write, autonomous write, live provider execution, shell execution,
database mutation outside approved tests, production operation, CLI input-file
reading, CLI output-file writing, and persistent runtime audit store all remain
**NO-GO / not authorized**. This phase changes none of those verdicts.
