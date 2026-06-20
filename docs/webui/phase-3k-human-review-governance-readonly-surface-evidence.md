# Phase 3K — Human Review Governance Read-only Surface (Evidence)

> Phase 3K implements a **read-only** Human Review / Approval Governance panel
> for the Dev WebUI. It is a higher-level decision-readiness surface that
> unifies the P0 human-review picture across the Phase 3 capability chain.
>
> **Code is allowed. Production is forbidden.** This surface approves nothing,
> authorizes nothing, signs off on nothing, executes nothing, and adds no
> backend route.

## 1. Scope and boundary

This phase adds **only** a client-side Dev Console section. It does **not**:

- approve / reject / authorize / sign off / resolve / override any gate;
- enable a production runtime or trigger a production rollout;
- execute a plugin, run a batch, or load any plugin (arbitrary, local-directory,
  remote-registry, or marketplace);
- read a real API key or secret, or accept an API-key / secret / file / JSON
  input;
- add a backend HTTP route, an OpenAPI path, a dev_web_api integration, or any
  write / execution / approval / authorization endpoint;
- access `~/.hermes` (not even a metadata-only stat / ls / resolve) or production
  `state.db`;
- reach the external network, a remote registry, or a marketplace;
- write a persistent runtime audit store, or read/write CLI input/output files.

The surface is served entirely from frozen static data under
`apps/hermes-dev-webui/src/`. No backend, no runtime, no CLI, no Gateway, and no
production state is touched.

## 2. Page location and nav label

- Nav label: **Human Review** (Dev Console left rail).
- Section id: `humanReview` (a first-class `DevConsoleSection`, registered in
  `stores/devConsoleNav.ts`).
- Rendered by `HumanReviewGovernanceSection.vue` inside the existing `/console`
  view via `DevConsoleLayout.vue`.
- **No new SPA route** and **no new backend route** — it is a client-side
  section.

## 3. What the panel displays

### 3.1 Header / boundary banner

Page title `Human Review Governance` plus frozen status badges: `READ-ONLY`,
`P0 GATES`, `HUMAN REVIEW REQUIRED`, `NO APPROVAL FROM WEBUI`, `PRODUCTION
NO-GO`. The boundary banner states the page cannot approve gates, cannot
authorize a runtime, cannot resolve P0, cannot enable production, and cannot
replace human review; code evidence is partial evidence only; valid approval
requires an out-of-band trusted human process.

### 3.2 Summary cards

| Card | Value |
|------|-------|
| Total P0 gates | 24 |
| Resolved | 0 (always — requires human approval) |
| Partial evidence | 19 |
| Pending human review | 5 |
| Governance-only | 0 |
| Implementation Authorization | NO-GO |
| Production runtime | NO-GO |
| Production rollout | NO-GO |
| Backend routes changed | no (34/34/5/0/1/1) |

### 3.3 The 24 P0 gates

Mirrors the backend frozen registry in `hermes_cli/dev_web_p0_evidence.py`
(titles, classifications, reviewers, and resolution requirements verbatim):

- **19 partial evidence**: P0-01 … P0-14, P0-17, P0-20, P0-21, P0-23, P0-24.
- **5 pending human review** (`blocked_by_human_review`): P0-15 (No
  implementation authorization), P0-16 (No runtime endpoint authorization),
  P0-18 (No plugin source trust decision), P0-19 (No worker lifecycle
  approval), P0-22 (No human review signoff).
- **0 resolved.**

Each gate is unresolved (`resolved=false`, `approved=false`) with a production
authorization impact of `NO-GO`.

### 3.4 Client-side filters

Five harmless filters over static data only (no fetch, no backend):
`All gates` (24), `Partial evidence` (19), `Pending human review` (5),
`Blocked by human review` (5), `Governance-only / no evidence` (0).

### 3.5 Gate detail panel

For the selected gate: status, category, evidence level, resolved/approved
(both false), production authorization (NO-GO), required reviewer category,
source phase, human-review requirement, code-evidence summary, blocked reason,
related artifacts, and the gate's forbidden actions. The only interactive
control is a harmless **Copy ID** (clipboard-only). The detail clearly states
`resolved=false`, `approved=false`, and `production authorization = NO-GO`.

### 3.6 Evidence trail (Phase 3 capability chain)

Seven sources, each stating what it proves and what it does NOT prove, every one
"partial evidence only — no production authorization":

1. Phase 3E-H safety baseline
2. Phase 3H proof runner
3. Phase 3I local runtime MVP
4. Phase 3I runtime expansion
5. Phase 3I descriptor runtime integration
6. Phase 3I runtime governance CLI
7. Phase 3J read-only WebUI

### 3.7 NO-GO decision panel

Implementation Authorization (NO-GO), Phase 3I Production Authorization
(NOT_AUTHORIZED), Production Runtime (NO-GO), New Backend Route (NO-GO),
Production Rollout (NO-GO) — each with its reason (resolved_count 0, pending
human review 5, no trust token provisioned, metadata / AI / placeholder approval
cannot approve, production access forbidden).

### 3.8 Runtime Governance ↔ Human Review relationship

Runtime Governance (CLI / WebUI) is the **evidence surface**; Human Review
Governance is the **decision-readiness surface**. Neither approves production,
neither executes a production runtime, neither changes route governance.

### 3.9 Allowed vs forbidden actions

Read-only allowed actions: view gate details, filter gates, inspect evidence
summary, copy gate id, read NO-GO explanation. Forbidden (never offered, shown
as explanatory text only): approve, reject, authorize, signoff, resolve,
override, production rollout, enable production runtime, arbitrary plugin
loading, local plugin directory loading, remote registry, marketplace, API key
entry, external network, run plugin from WebUI, batch execute from WebUI, upload
evidence.

## 4. No approval / authorize / production-rollout controls

Code and tests prove there is no interactive control for approve, reject,
authorize, sign off, resolve, override, mark reviewed, mark approved, enable
runtime, enable production runtime, run, execute, batch execute, production
rollout, upload evidence, API-key input, secret input, JSON input, or file
upload. Forbidden action words appear only as **descriptive text** (e.g.
"cannot approve"), never as a button's visible text or accessible name. The only
buttons are: the five filter toggles, the per-gate `Inspect`, and the `Copy ID`
clipboard affordance.

## 5. No backend route added / no dev_web_api integration

- `hermes_cli/dev_web_api.py` does not import any human-review-governance,
  runtime-governance, or plugin-runtime module.
- No OpenAPI path is named for human review / approval governance.
- Candidate paths (`/api/dev/v1/human-review-governance`, `…/approval-governance`,
  `…/human-review/approve|authorize|signoff|resolve`, …) all return **404** (GET
  and POST).
- Route governance baseline unchanged: **34 / 34 / 5 / 0 / 1 / 1**; new HTTP
  route 0; new runtime route 0; new plugin route 0; new provider route 0; new
  tool-write route 0.

## 6. No production / no `~/.hermes` / no `state.db` access

The dev app binds to `127.0.0.1` only. This phase never stats, lists, reads,
opens, or resolves `~/.hermes` or production `state.db` — not even for
metadata-only checks. Forbidden-path assertions in tests use fake / string-policy
paths only. No arbitrary plugin loading, no local plugin directory loading, no
remote registry, no marketplace, no external network, no real API key.

## 7. P0 evidence summary (conservative)

- Total P0 gates: **24**
- Resolved / approved: **0**
- Partial evidence: **19**
- Pending human review: **5**
- Implementation Authorization: **NO-GO**
- Phase 3I production authorization: **NOT_AUTHORIZED**
- Production runtime: **NO-GO**
- New route: **NO-GO**
- Production rollout: **NO-GO**

Implementation Authorization remains **NO-GO** for production / a real external
runtime because: the dev-only descriptor-backed fixture runtime and the
read-only WebUI are partial evidence only; code cannot self-approve production
authorization; metadata, AI, or placeholder approval cannot resolve a P0 gate;
and the 5 pending-human-review gates require a valid out-of-band human approval
the dev skeleton cannot produce. No change from the Phase 3J state.

## 8. Files

### Frontend — types / manifest / view-model

- `src/types/api/humanReviewGovernance.ts`
- `src/constants/humanReviewGovernanceManifest.ts`
- `src/lib/humanReviewGovernanceViewModel.ts`

### Frontend — components

- `src/components/devconsole/HumanReviewGovernanceSection.vue`
- `src/components/devconsole/HumanReviewBoundaryBanner.vue`
- `src/components/devconsole/HumanReviewGateTable.vue`
- `src/components/devconsole/HumanReviewGateDetail.vue`
- `src/components/devconsole/HumanReviewEvidenceTrail.vue`
- `src/components/devconsole/HumanReviewNogoPanel.vue`

### Frontend — navigation wiring

- `src/stores/devConsoleNav.ts` (new `humanReview` section + label)
- `src/components/devconsole/DevConsoleLayout.vue` (section → component map)
- `src/components/devconsole/DevConsoleNav.vue` (`UserCheck` icon)

### Frontend — tests

- `src/tests/phase3k-human-review-governance-view-model.spec.ts`
- `src/tests/phase3k-human-review-governance-panel.spec.ts`
- `src/tests/phase3k-human-review-governance-no-leak.spec.ts`
- `src/tests/phase3k-human-review-governance-routes.spec.ts`

### Backend — isolation test

- `tests/test_dev_web_phase_3k_human_review_governance_webui_isolation.py`

## 9. Tests and validation

Frontend (Vitest / jsdom):

- view-model: determinism, 24/0/19/5 counts, gate lookup, all five filters,
  evidence trail, relationship, immutability (canonical manifest frozen; external
  mutation cannot flip resolved/approved/NO-GO), defense-in-depth redaction
  (corpus M).
- panel: header + badges, boundary banner, summary cards, 24-gate table, filter
  counts (24/19/5/0), gate detail (resolved/approved/NO-GO), evidence trail,
  NO-GO + relationship panel, allowed/forbidden actions, route governance.
- no-leak: no `<input>`/`<textarea>`/`<select>`/file-picker; no approval /
  authorization / execution / loading button; every button text is an allowed
  control; no network/XHR on render + filter + inspect + copy; no forbidden
  secret/path/fake-approval token in the DOM across every gate; copy clipboard
  affordance (copied / unavailable / never fetches).
- routes: SPA router unchanged (3 named views + catch-all); no human-review
  route; `humanReview` is a client-side section; Runtime Governance intact; no
  backend route.

Backend isolation (pytest):

- `dev_web_api.py` imports no governance / human-review module and references no
  human-review route.
- No OpenAPI path named for human review; candidate paths 404 (GET + POST).
- Route governance unchanged (34/34/5/0/1/1; `assert_route_governance_unchanged`
  passes; no drift).
- P0 model frozen (24 gates, none resolved, 19 partial + 5 blocked, every
  authorization flag NO-GO / not-authorized).
- No production access: dev app binds 127.0.0.1; forbidden-path stems are
  string-policy only; never stats/ls/resolves `~/.hermes`.

## 10. Still NOT authorized (deferred)

Production plugin runtime; arbitrary plugin loading; user-uploaded plugins; local
plugin directory loading outside the fixture allowlist; remote registry;
marketplace; external plugin fetch; provider-generated / LLM-generated plugin
install; real API key reading; external network; new backend route; approval /
authorization backend route; WebUI execution route; WebUI run / approve / reject
/ authorize / production-rollout action; production rollout; provider write;
autonomous write; live provider execution; shell execution; database mutation
outside approved tests; production operation; CLI input-file reading; CLI
output-file writing; persistent runtime audit store.
