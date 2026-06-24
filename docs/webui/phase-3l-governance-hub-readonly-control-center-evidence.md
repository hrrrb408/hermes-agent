# Phase 3L — Governance Hub Unified Read-only Control Center (Evidence)

> Phase 3L implements a **read-only** Governance Hub / Unified Control Center for
> the Dev WebUI. It is a single read-only board that aggregates the governance
> state already surfaced by the Runtime Governance (Phase 3J) and Human Review
> Governance (Phase 3K) sections.
>
> **Code is allowed. Production is forbidden.** This surface approves nothing,
> authorizes nothing, signs off on nothing, executes nothing, loads no plugin,
> rolls out no production, and adds no backend route.

## 1. Scope and boundary

This phase adds **only** a client-side Dev Console section. It does **not**:

- approve / reject / authorize / sign off / resolve / override any gate;
- enable a production runtime or trigger a production rollout;
- execute a plugin, run a batch, or load any plugin (arbitrary, local-directory,
  remote-registry, or marketplace);
- read a real API key or secret, or accept an API-key / secret / file / JSON
  input;
- add a backend HTTP route, an OpenAPI path, a `dev_web_api` integration, or any
  write / execution / approval / authorization endpoint;
- access `~/.hermes` (not even a metadata-only stat / ls / resolve) or production
  `state.db`;
- reach the external network, a remote registry, or a marketplace;
- write a persistent runtime audit store, or read/write CLI input/output files.

The surface is served entirely from frozen static data under
`apps/hermes-dev-webui/src/`. No backend, no runtime, no CLI, no Gateway, and no
production state is touched.

## 2. Page location and nav label

- Nav label: **Governance Hub** (Dev Console left rail).
- Section id: `governanceHub` (a first-class `DevConsoleSection`, registered in
  `stores/devConsoleNav.ts`).
- Rendered by `GovernanceHubSection.vue` inside the existing `/console` view via
  `DevConsoleLayout.vue`.
- **No new SPA route** and **no new backend route** — it is a client-side
  section. The SPA router still exposes exactly three named views (workspace /
  console / theme-lab) plus the catch-all redirect.

## 3. What the panel displays

### 3.1 Header / boundary banner

Page title `Governance Hub` plus frozen status badges: `READ-ONLY`, `UNIFIED
CONTROL CENTER`, `NO PRODUCTION RUNTIME`, `NO APPROVAL ACTIONS`, `ROUTES
UNCHANGED`. The boundary banner states the page cannot execute a runtime, cannot
approve gates, cannot authorize production, and cannot change routes; every P0
count is frozen and every authorization verdict is frozen NO-GO /
not-authorized.

### 3.2 Overview summary cards

| Card | Value |
|------|-------|
| Runtime Governance | COMPLETE |
| Human Review Governance | IMPLEMENTED |
| P0 gates | 24 |
| P0 resolved | 0 (always — requires human approval) |
| Pending human review | 5 |
| Route governance | 34/34/5/0/1/1 |
| Production runtime | NO-GO |
| Production rollout | NO-GO |
| Backend route changes | 0 (no backend route added) |
| Side effects | all false |

### 3.3 Governance module status board

A read-only table of the 10 Phase 3 capability-chain modules. Each module
carries: phase, lifecycle status (COMPLETE / IMPLEMENTED / READ_ONLY), a
read-only evidence summary, a frozen route impact (`No new route`), a frozen
production impact (`No production authorization`), a frozen authorization impact
(`NO-GO`), and a read-only flag. Modules: Static Descriptor Registry, Runtime
Sandbox Safety Baseline, Sandbox Proof Runner, Dev-only Local Runtime MVP,
Runtime Fixture Expansion, Descriptor Runtime Integration, Runtime Governance
CLI, Runtime Governance WebUI, Human Review Governance WebUI, Governance Hub.
None of these authorizes production.

### 3.4 P0 / human review summary

The 24 frozen P0 gates: 0 resolved, 19 partial evidence, 5 blocked by human
review. The five pending gates are P0-15, P0-16, P0-18, P0-19, P0-22.

### 3.5 Route governance summary

Exact frozen counts (34/34/5/0/1/1):

| Dimension | Count |
|-----------|-------|
| OpenAPI paths | 34 |
| Runtime routes | 34 |
| Tool GET | 5 |
| Tool write HTTP route | 0 |
| Tool dry-run route | 1 |
| Tool execution route | 1 |
| New HTTP route | 0 |
| New Tool write route | 0 |
| New Provider route | 0 |
| New plugin route | 0 |
| New runtime route | 0 |

The panel explicitly states: no backend route added, no approval / authorization
route, no runtime execution route, no production rollout route.

### 3.6 Production safety summary

Static wording only (the frontend does not inspect a live process). Every flag is
frozen false: production Gateway expected unchanged and untouched, Dev Gateway
stopped, Dashboard not started, ports 5180 / 5181 free, no production home access
(not even metadata), no production state database access, no external network,
no real secret / API key read.

> The exact production Gateway PID (expected `28428`) is deliberately NOT carried
> in the frontend view-model — it is environment-specific. The frontend states the
> gateway is expected unchanged; the exact PID lives in docs / tests only.

### 3.7 Evidence trail summary

Read-only timeline of the Phase 3 capability chain (Phase 3D, 3E-H, 3H, 3I, 3J,
3K, 3L). Each source states the completed deliverable, what it proves, what it
does NOT prove, and the authorization impact (`Partial evidence only — no
production authorization`). The evidence is partial only: it proves no production
authorization, resolves no P0 gate, and is no replacement for human approval.

### 3.8 NO-GO decision summary

Implementation Authorization (`NO-GO`), Phase 3I Production Authorization
(`NOT_AUTHORIZED`), Production Runtime (`NO-GO`), New Backend Route (`NO-GO`),
Approval / Authorization Backend Route (`NO-GO`), WebUI Execution Route
(`NO-GO`), WebUI Approve / Reject / Authorize Action (`NO-GO`), Production
Rollout (`NO-GO`).

### 3.9 Deferred / still-not-authorized list

A read-only list of every capability that remains NO-GO / not-authorized:
production plugin runtime; arbitrary plugin loading; user-uploaded plugins;
local plugin directory loading outside fixture allowlist; remote registry;
marketplace; external plugin fetch; provider-generated plugin install;
LLM-generated plugin install; real API key reading; external network; new backend
route; approval backend route; authorization backend route; WebUI execution
route; WebUI run button; WebUI approve / reject / authorize action; WebUI
production rollout action; production rollout; provider write; autonomous write;
live provider execution; shell execution; database mutation outside approved
tests; production operation; CLI input-file reading; CLI output-file writing;
persistent runtime audit store. These words are explanatory text, never
interactive controls.

### 3.10 Cross-links

Read-only navigation to the existing **Runtime Governance** (Phase 3J) and
**Human Review** (Phase 3K) Dev Console sections. Clicking a link switches the
section client-side — no backend call, no SPA route change, no runtime call.

## 4. What the WebUI can and cannot do

Allowed (read-only): view module status board; inspect module details; view
runtime governance section; view human review section; filter modules by status;
copy summary text; read NO-GO explanation.

Forbidden (never offered, rendered as explanatory text only): approve, reject,
authorize, signoff, resolve, override, production rollout, enable production
runtime, enable runtime, arbitrary plugin loading, local plugin directory
loading, remote registry, marketplace, external plugin fetch, API key entry, file
upload, JSON execution input, external network, run plugin from WebUI, batch
execute from WebUI, upload evidence, load plugin.

There is **no** `<input>`, `<textarea>`, `<select>`, file picker, API-key input,
secret input, or JSON execution input anywhere on the surface.

## 5. No backend route / no dev_web_api integration

- `hermes_cli/dev_web_api.py` does **not** import any governance-hub,
  human-review-governance, runtime-governance, or plugin-runtime module.
- No OpenAPI path is named for governance hub / control center / governance.
- Probing candidate paths (`/api/dev/v1/governance-hub`, `/control-center`,
  `/governance`, and their `/approve` / `/authorize` / `/signoff` / `/resolve`
  / `/execute` / `/rollout` sub-paths) returns 404 for GET and POST.
- The route-governance baseline is unchanged: `34/34/5/0/1/1`, every new-route
  flag `0`, `assert_route_governance_unchanged` passes, no drift.

## 6. No production access

- The dev WebUI binds to `127.0.0.1` only (never `0.0.0.0`).
- No `~/.hermes` access — not even a metadata-only stat / ls / resolve.
- No production `state.db` access.
- No external network, no real API key read.
- Forbidden path assertions use fake / string-policy paths only.

## 7. Frozen invariants (unchanged by this surface)

- P0 `resolved_count` remains **0**.
- Implementation Authorization remains **NO-GO**.
- Phase 3I production authorization remains **NOT_AUTHORIZED**.
- Production runtime remains **NO-GO**.
- New route remains **NO-GO**.
- Production rollout remains **NO-GO**.
- Route governance remains `34/34/5/0/1/1` (all new-route flags 0).
- No arbitrary plugin loading; no local plugin directory loading; no remote
  registry; no marketplace; no external network; no real API key.

## 8. Files

### Frontend source (`apps/hermes-dev-webui/src/`)

- `types/api/governanceHub.ts` — read-only view-model types.
- `constants/governanceHubManifest.ts` — frozen static manifest (deep-frozen).
- `lib/governanceHubViewModel.ts` — pure projections + defense-in-depth redactor.
- `components/devconsole/GovernanceHubSection.vue` — main section.
- `components/devconsole/GovernanceHubBoundaryBanner.vue`
- `components/devconsole/GovernanceHubModuleBoard.vue`
- `components/devconsole/GovernanceHubRoutePanel.vue`
- `components/devconsole/GovernanceHubProductionSafetyPanel.vue`
- `components/devconsole/GovernanceHubEvidenceTrail.vue`
- `components/devconsole/GovernanceHubNogoPanel.vue`
- `components/devconsole/GovernanceHubDeferredPanel.vue`
- `components/devconsole/GovernanceHubCrossLinks.vue`
- `stores/devConsoleNav.ts` — `governanceHub` section registration.
- `components/devconsole/DevConsoleNav.vue`, `DevConsoleLayout.vue` — nav + mapping.

### Frontend tests

- `tests/phase3l-governance-hub-panel.spec.ts`
- `tests/phase3l-governance-hub-view-model.spec.ts`
- `tests/phase3l-governance-hub-no-leak.spec.ts`
- `tests/phase3l-governance-hub-routes.spec.ts`

### Backend isolation test

- `tests/test_dev_web_phase_3l_governance_hub_webui_isolation.py`

## 9. Tests and validation

- Phase 3L frontend tests (panel + view-model + no-leak + routes): 81 pass.
- Backend isolation (Phase 3L + 3K + 3J): pass; route governance unchanged
  (`34/34/5/0/1/1`); P0 frozen (24 / 0 / 19 / 5); no backend route; no
  production access.
- `vue-tsc --noEmit` type-check: clean.
- Existing Phase 3K / 3J frontend tests, Runtime Governance CLI tests, descriptor
  runtime integration tests, runtime expansion / MVP tests, Phase 3D descriptor
  registry tests, and Phase 3E-H safety / route governance tests continue to
  pass (regression preserved).
- `memory-check` PASS; `dev-check` passes (only expected dirty-worktree WARN).

## 10. Authorization boundary (unchanged)

This is a **read-only** surface. It is **not** a closeout, **not** a signoff,
**not** an archive, **not** an authorization approval, and **not** a production
runtime. Production plugin runtime, arbitrary plugin loading, user-uploaded
plugins, local plugin directory loading, remote registry, marketplace, external
plugin fetch, provider-generated / LLM-generated plugin install, real API key
reading, external network, new backend route, approval / authorization backend
route, WebUI execution route, WebUI approve / reject / authorize action, WebUI
production rollout action, production rollout, CLI input/output file handling,
and the persistent runtime audit store all remain **NO-GO / not-authorized**.
