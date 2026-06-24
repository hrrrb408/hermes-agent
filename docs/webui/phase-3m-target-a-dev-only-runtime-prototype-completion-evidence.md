# Phase 3M — Target A Dev-only Runtime Prototype Completion (Evidence)

> Phase 3M marks **Target A — the dev-only runtime prototype — as COMPLETE** in
> the Governance Hub. Target A is the full Phase 3 capability chain: Static
> Descriptor Registry → Runtime Binding → Fixture Runtime → CLI → read-only
> Runtime Governance WebUI → read-only Human Review Governance WebUI → unified
> read-only Governance Hub. It is complete **in the dev-only sense only**.
>
> **Code is allowed. Production is forbidden.** This surface approves nothing,
> authorizes nothing, signs off on nothing, executes nothing, loads no plugin,
> rolls out no production, and adds no backend route. Target A COMPLETE is **not**
> production authorization.

## 1. Scope and boundary

This phase adds **only** a read-only client-side region inside the existing
Governance Hub Dev Console section. It does **not**:

- approve / reject / authorize / sign off / resolve / override any gate;
- mark Target A as production-ready, production-authorized, or production-approved;
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

## 2. Target A definition

**Target A = the dev-only runtime prototype.** It is the demonstrable, testable,
governable runtime prototype built across Phase 3D → 3L.

**Target A includes:**

- a reviewed, descriptor-only Static Plugin Descriptor Registry;
- reviewed fixture descriptors;
- registry-to-runtime binding (deny-by-default provenance);
- a dev-only, in-process fixture runtime (fixture allowlist only);
- fixture runtime expansion (batch + redacted in-memory audit);
- the runtime governance CLI (list / show / run / batch / audit / p0-report);
- the read-only Runtime Governance WebUI;
- the read-only Human Review Governance WebUI;
- the unified read-only Governance Hub;
- a unified capability status matrix, the NO-GO boundaries, the P0 gate state,
  the route-governance / production-safety / side-effect invariants, and the test
  coverage / regression evidence.

**Target A excludes (still NO-GO):** everything in the Target B deferred matrix
(see §15) — production runtime, arbitrary plugin loading, real plugin ecosystem,
remote registry, marketplace, external network, real API keys, WebUI execution,
approval / authorization, and production rollout.

**Why Target A can be COMPLETE while production remains NO-GO:** Target A is
scoped to dev-only, fixture-only, read-only-governed evidence. Complete means the
prototype capability chain is implemented, the governance surfaces exist, and the
tests are green — not that any P0 gate is resolved, that human review is
satisfied, that a trust token is provisioned, or that production is authorized.
P0 `resolved_count` remains **0**, five gates remain pending human review, and
every authorization verdict remains NO-GO / not-authorized.

## 3. Target A completion criteria

Target A is accepted as COMPLETE because all of the following hold (each is
visible in the Governance Hub Target A region or its backing tests):

1. Static Plugin Descriptor Registry implemented.
2. Reviewed fixture descriptors available.
3. Registry-to-runtime binding implemented.
4. Dev-only fixture runtime implemented.
5. Fixture runtime expanded.
6. Runtime Governance CLI complete.
7. Runtime Governance read-only WebUI complete.
8. Human Review Governance read-only WebUI implemented.
9. Governance Hub unified read-only control center implemented.
10. P0 gates visible (24 total).
11. P0 resolved count remains **0** and visible.
12. P0 pending human review remains visible (5).
13. Route governance unchanged (34/34/5/0/1/1).
14. Production safety unchanged.
15. No production runtime. 16. No arbitrary plugin loading.
17. No remote registry. 18. No marketplace.
19. No WebUI execution. 20. No approval / authorization.
21. No production rollout. 22. Tests pass.
23. Docs / evidence updated.
24. Dev-only target accepted as complete while production remains NO-GO.

## 4. Completed capability chain

| # | Capability | Phase | Status |
|---|-----------|-------|--------|
| 1 | Static Descriptor Registry | 3D | IMPLEMENTED |
| 2 | Reviewed Fixture Descriptors | 3D | IMPLEMENTED |
| 3 | Sandbox Safety Baseline | 3E-H | IMPLEMENTED |
| 4 | P0 Evidence Projection | 3E-H | IMPLEMENTED |
| 5 | Proof Runner | 3H | IMPLEMENTED |
| 6 | Adversarial Hardening | 3H | IMPLEMENTED |
| 7 | Dev-only Fixture Runtime | 3I | IMPLEMENTED |
| 8 | Fixture Runtime Expansion | 3I | IMPLEMENTED |
| 9 | Descriptor Runtime Binding | 3I | IMPLEMENTED |
| 10 | Runtime Governance CLI | 3I | IMPLEMENTED |
| 11 | Runtime Governance CLI Completion | 3I | COMPLETE |
| 12 | Runtime Governance WebUI | 3J | COMPLETE |
| 13 | Runtime Governance WebUI QA | 3J | COMPLETE |
| 14 | Human Review Governance WebUI | 3K | IMPLEMENTED |
| 15 | Governance Hub | 3L | IMPLEMENTED |

Every row adds **no route** and authorizes **no production** (Target B impact is
stated per row: not required for Target A / required for a future production
phase). The matrix is rendered read-only in the Governance Hub.

## 5. CLI coverage

The runtime governance CLI (Phase 3I, complete) exposes the dev-only projections:
`list` / `show` / `run` / `batch` / `audit` / `p0-report`. The WebUI does **not**
call the CLI; it mirrors the frozen projections from static data only.

## 6. WebUI coverage

The Governance Hub renders, read-only: the Runtime Governance summary (Phase 3J),
the Human Review Governance summary (Phase 3K), the Governance Hub summary
(Phase 3L), and — added in Phase 3M — the **Target A Completion region**
(banner, completion cards, capability matrix, readiness checklist, Target A vs
Target B boundary, and the final dev-only prototype acceptance panel).

## 7. Governance Hub coverage

Phase 3M integrates the Target A Completion region **into** the existing
Governance Hub section (no new SPA route, no new Dev Console section, no new
backend route). The region is positioned directly after the boundary banner so
"Target A: COMPLETE" is the headline of the hub.

## 8. Human Review visibility

The 24 frozen P0 gates are visible: **0 resolved**, **19 partial evidence**,
**5 pending human review** (P0-15, P0-16, P0-18, P0-19, P0-22). The five pending
gates can only advance via an out-of-band human approval the dev skeleton cannot
produce.

## 9. P0 state

| Dimension | Value |
|-----------|-------|
| Total P0 gates | 24 |
| Resolved / approved | 0 |
| Partial evidence | 19 |
| Pending human review | 5 |
| Pending gates | P0-15 / P0-16 / P0-18 / P0-19 / P0-22 |

P0 `resolved_count` remains **0**. This is unchanged by Phase 3M.

## 10. Route governance (unchanged)

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

Baseline: `34/34/5/0/1/1`, every new-route flag `0`,
`assert_route_governance_unchanged` passes, no drift. Unchanged by Phase 3M.

## 11. Production safety (unchanged)

Static wording only (the frontend does not inspect a live process). Every flag is
frozen false: production Gateway expected unchanged and untouched, Dev Gateway
stopped, Dashboard not started, ports 5180 / 5181 free, no production home access
(not even metadata), no production state database access, no external network, no
real secret / API key read.

> The exact production Gateway PID (expected `28428`) is deliberately NOT carried
> in the frontend view-model — it is environment-specific. The frontend states the
> gateway is expected unchanged; the exact PID lives in docs / tests only.

## 12. No `~/.hermes` access

The dev WebUI binds to `127.0.0.1` only. There is **no** `~/.hermes` access — not
even a metadata-only stat / ls / resolve. Forbidden path assertions use fake /
string-policy paths only.

## 13. No production `state.db` access

There is no production `state.db` access. Forbidden path assertions use fake /
string-policy paths only.

## 14. NO-GO boundaries

Implementation Authorization (`NO-GO`), Phase 3I Production Authorization
(`NOT_AUTHORIZED`), Production Runtime (`NO-GO`), New Backend Route (`NO-GO`),
Approval / Authorization Backend Route (`NO-GO`), WebUI Execution Route
(`NO-GO`), WebUI Approve / Reject / Authorize Action (`NO-GO`), Production
Rollout (`NO-GO`).

## 15. Target B deferred list (still not authorized)

Every item below remains NO-GO / not-authorized and is rendered as explanatory
TEXT only — never as an interactive control:

production plugin runtime; arbitrary plugin loading; user-uploaded plugins; local
plugin directory loading outside fixture allowlist; remote registry; marketplace;
external plugin fetch; provider-generated plugin install; LLM-generated plugin
install; real API key reading; external network; new backend route; approval
backend route; authorization backend route; WebUI execution route; WebUI run
button; WebUI approve / reject / authorize action; WebUI production rollout
action; production rollout; provider write; autonomous write; live provider
execution; shell execution; database mutation outside approved tests; production
operation; CLI input-file reading; CLI output-file writing; persistent runtime
audit store.

## 16. Tests and validation

- Phase 3M frontend tests (completion + view-model + no-leak + routes): 74 pass
  (17 + 40 + 9 + 8).
- Backend isolation (Phase 3M + 3L + 3K + 3J): 61 pass; route governance unchanged
  (`34/34/5/0/1/1`); P0 frozen (24 / 0 / 19 / 5); no backend route; no
  production access; Target A status text is frontend-only and carries no
  positive-authorization marker.
- `pnpm run lint`: clean. `pnpm run type-check` (`vue-tsc --noEmit`): clean.
- Existing Phase 3L / 3K / 3J frontend tests, Runtime Governance CLI tests,
  descriptor runtime integration tests, runtime expansion / MVP tests, Phase 3D
  descriptor registry tests, and Phase 3E-H safety / route governance tests
  continue to pass (regression preserved). Full frontend suite: 1566 pass.
- `memory-check` PASS; `dev-check` passes (only expected dirty-worktree WARN).

## 17. Why Target A is complete

All 15 capability-chain capabilities are implemented; the three read-only
governance surfaces (Runtime Governance, Human Review, Governance Hub) are
complete; the test suites are green; route governance is unchanged; and
production is untouched. Target A is therefore accepted as a complete dev-only,
fixture-only, read-only-governed prototype.

## 18. Why Target B is not complete

Target B (the real production plugin runtime / real plugin ecosystem) requires an
approved production sandbox / worker lifecycle model, a reviewed supply-chain
trust model, human approval of the five pending P0 gates, a provisioned trust
token, and an approved rollback / incident plan. None of these exist; every
Target B item remains NO-GO / not-authorized.

## 19. Why this is not production authorization

Target A COMPLETE is **not** production runtime authorized, **not** P0 resolved,
**not** human review approved, **not** arbitrary plugin loading allowed, **not**
WebUI execution allowed, and **not** production rollout allowed. P0
`resolved_count` remains 0, five gates remain pending human review, no trust token
is provisioned, and metadata / AI / placeholder approval cannot advance any gate.

**Allowed wording** (used here): "Target A dev-only runtime prototype is
complete."; "Production runtime remains NO-GO."; "P0 resolved_count remains 0.";
"This does not authorize Target B."; "This does not authorize production
rollout."

**Forbidden wording** (never used): "Implementation Authorization GO"; "Production
runtime approved"; "P0 resolved"; "Human review approved"; "Target B started";
"Production ready"; "Production rollout approved".

## 20. Next recommended phase after Target A

The next step is **not** automatic. Before any Target B work could be considered,
the human-approver gate must advance the five pending P0 gates (P0-15, P0-16,
P0-18, P0-19, P0-22) through an out-of-band human approval, provision a trust
token, and approve a production sandbox / worker lifecycle / rollback / incident
plan. That authorization is a separate human-governed decision — it is not
implied or enabled by Target A completion.

## 21. Authorization boundary (unchanged)

This is a **read-only** surface. It is **not** a closeout, **not** a signoff,
**not** an archive, **not** an authorization approval, and **not** a production
runtime. Production plugin runtime, arbitrary plugin loading, user-uploaded
plugins, local plugin directory loading, remote registry, marketplace, external
plugin fetch, provider-generated / LLM-generated plugin install, real API key
reading, external network, new backend route, approval / authorization backend
route, WebUI execution route, WebUI approve / reject / authorize action, WebUI
production rollout action, production rollout, CLI input/output file handling,
and the persistent runtime audit store all remain **NO-GO / not-authorized**.

## 22. Files

### Frontend source (`apps/hermes-dev-webui/src/`)

- `types/api/governanceHub.ts` — Target A view-model types (extended).
- `constants/governanceHubManifest.ts` — frozen Target A constants (extended).
- `lib/governanceHubViewModel.ts` — pure Target A projections + redactor (extended).
- `components/devconsole/GovernanceHubTargetACompletion.vue` — Target A region (new).
- `components/devconsole/GovernanceHubSection.vue` — wires the region in (extended).

### Frontend tests

- `tests/phase3m-target-a-completion.spec.ts`
- `tests/phase3m-target-a-view-model.spec.ts`
- `tests/phase3m-target-a-no-leak.spec.ts`
- `tests/phase3m-target-a-routes.spec.ts`

### Backend isolation test

- `tests/test_dev_web_phase_3m_target_a_completion_isolation.py`

### Docs

- `docs/webui/phase-3m-target-a-dev-only-runtime-prototype-completion-evidence.md` (this file)
