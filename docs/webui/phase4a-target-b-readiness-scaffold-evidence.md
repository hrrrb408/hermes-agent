# Phase 4A — Target B Readiness Scaffold (Evidence)

> Phase 4A implements **only the Target B readiness scaffold** — the frozen
> architecture models, the disabled interfaces, the permission / approval gate
> models, the read-only WebUI preview, and the tests proving every dangerous
> capability stays disabled. Target B is the long-term goal of opening a real
> production plugin runtime (signed / arbitrary plugin loading, a remote
> registry, a marketplace, WebUI execution, and a production rollout).
>
> **The scaffold is implemented. Target B remains disabled.** This surface
> enables nothing, authorizes nothing, executes nothing, loads no plugin, fetches
> no registry, opens no marketplace, reads no real API key, provisions no trust
> token, approves no gate, and adds no backend route. P0 `resolved_count` remains
> 0.

## 1. Target B long-term goal

Target B is the real **production plugin runtime / real plugin ecosystem**:

- a production plugin runtime (an approved sandbox / worker lifecycle);
- signed / arbitrary plugin loading from a reviewed supply chain;
- a pinned, signed remote registry;
- a reviewed marketplace;
- WebUI execution of reviewed plugins;
- a production rollout with rollback / incident response.

None of these are enabled by Phase 4A. They are the **long-term** goal that the
readiness scaffold is drafted to prepare for.

## 2. Why Target B cannot be enabled in one step

Target B cannot be enabled in a single step because every prerequisite gate is
still unresolved:

- **P0 `resolved_count` is 0.** No gate is resolved.
- **Five gates remain pending human review** (P0-15, P0-16, P0-18, P0-19,
  P0-22). These can only advance via an out-of-band human approval the dev
  skeleton cannot produce.
- **No trust token is provisioned.** Metadata / AI / placeholder approval cannot
  advance any gate.
- **Production authorization remains NO-GO.** No approved sandbox / worker
  lifecycle, no reviewed supply-chain trust model, no registry trust policy, no
  network allowlist, no approved rollback / incident plan.

Directly enabling Target B would violate the governance established across
Phase 3D → 3M (the Target A capability chain) and the route-governance freeze
(`34/34/5/0/1/1`). Phase 4A therefore implements the **readiness scaffold**
only.

## 3. Phase 4A readiness scaffold scope

Phase 4A adds **only** read-only, disabled-scaffold artifacts:

- a frozen Target B readiness **view-model** (TypeScript types, a deep-frozen
  static manifest, and pure projection functions);
- a read-only **Target B Readiness region** inside the existing Governance Hub
  DevConsole section (no new SPA route, no new DevConsole section, no new backend
  route);
- a pure-stdlib **backend disabled scaffold** (`hermes_cli/dev_web_target_b_readiness.py`)
  that mirrors the disabled contract and ships deny builders + a shape validator;
- frontend tests proving the region renders the disabled picture with no
  forbidden control, no input, no network call, and no leaked secret / path /
  fake-authorization token;
- backend tests proving the scaffold is disabled, pure, and adds no backend
  route;
- this evidence document.

It does **not**:

- approve / reject / authorize / sign off / resolve / override any gate;
- mark Target B as started, enabled, or production-authorized;
- enable a production runtime, a registry, a marketplace, WebUI execution, or a
  production rollout;
- execute a plugin, run a batch, load any plugin (arbitrary, local-directory,
  remote-registry, or marketplace), or fetch a registry;
- read a real API key or secret, or accept an API-key / secret / file / JSON /
  trust-token / signature input;
- add a backend HTTP route, an OpenAPI path, a `dev_web_api` integration, or any
  write / execution / install / approval / authorization / registry / marketplace
  endpoint;
- access the production home directory (not even a metadata-only stat / ls /
  resolve) or the production state database;
- reach the external network, a remote registry, or a marketplace;
- write a persistent runtime audit store, or read/write CLI input/output files.

## 4. Architecture modules

Sixteen designed / scaffolded-disabled modules. Every one is disabled,
non-executing, non-networking, non-production, and adds no route.

| # | Module | Status | Risk |
|---|--------|--------|------|
| 1 | Plugin Package Format | DESIGNED | high |
| 2 | Plugin Signature Verification | SCAFFOLDED_DISABLED | critical |
| 3 | Plugin Permission Model | DESIGNED | high |
| 4 | Plugin Capability Declaration | DESIGNED | medium |
| 5 | Remote Registry Protocol | SCAFFOLDED_DISABLED | critical |
| 6 | Registry Trust Policy | DESIGNED | critical |
| 7 | Marketplace Policy | SCAFFOLDED_DISABLED | critical |
| 8 | Runtime Sandbox Boundary | DESIGNED | critical |
| 9 | Execution Broker | SCAFFOLDED_DISABLED | critical |
| 10 | WebUI Execution Request Flow | SCAFFOLDED_DISABLED | high |
| 11 | Approval / Authorization Gate | DESIGNED | critical |
| 12 | Audit Trail | SCAFFOLDED_DISABLED | medium |
| 13 | Rollback / Kill Switch | DESIGNED | high |
| 14 | Secret Handling Boundary | DESIGNED | critical |
| 15 | Network Policy | SCAFFOLDED_DISABLED | critical |
| 16 | Production Rollout Plan | DESIGNED | critical |

Every row: `enabled=false`, `executionCapable=false`, `networkCapable=false`,
`productionCapable=false`, `routeImpact=none`.

## 5. Plugin package schema preview

A fake, static, non-executable schema preview (example only, not loaded, not
executable, no file read, no install). Fields: packageId, version, descriptor,
capabilities, permissions, entrypoints, signature, publisher, registrySource,
checksum, sandboxProfile, minimumHermesVersion. Every value is a documentation
placeholder. The example registry source uses a reserved `.invalid` domain.

## 6. Signature / trust model

A signature requirement is scaffolded (`signatureRequired=true`,
`allowUnsigned=false`), but **no signature verifier is implemented**. Unsigned
plugins are never accepted. The real trust token is deliberately absent
(`_REAL_TRUST_TOKEN = None`), so no approval constructed from request metadata
— or forged by direct construction — can enable Target B.

## 7. Permission model

Twelve permissions, every one `DENIED_BY_DEFAULT`:

`filesystem.read`, `filesystem.write`, `network.http`, `network.registry`,
`secrets.read`, `provider.read`, `provider.write`, `ui.render`, `tool.invoke`,
`database.read`, `database.write`, `process.spawn`.

None is granted no matter what renders or what untrusted metadata is supplied.

## 8. Registry protocol preview

| Field | Value |
|-------|-------|
| Registry URL (example) | `https://registry.example.invalid` |
| Fetch enabled | false |
| Network enabled | false |
| Trust policy required | true |
| Signature required | true |
| Allow unsigned | false |
| Marketplace enabled | false |

The `.invalid` URL is documentation only — never fetched.

## 9. WebUI execution preview (disabled)

The execution flow is **visible in the WebUI but every step is disabled**:
Select plugin package, Validate signature, Request approval, Execute, Audit.
There is **no execute button, no run button, no form, no input, and no submit
control**. `executeButtonEnabled=false`, `runtimeRouteAvailable=false`,
`canSubmit=false`, `status=PREVIEW_ONLY_DISABLED`. The flow is rendered as
disabled TEXT status items only — never as interactive buttons.

## 10. Approval gate model

| Field | Value |
|-------|-------|
| Human approval required | true |
| Trust token provisioned | false |
| Fake approval accepted | false |
| AI approval accepted | false |
| Metadata approval accepted | false |
| Production authorization | NO-GO |

## 11. Enablement blockers

What must be completed before Target B could even be considered (every blocker
stays unresolved): trusted human approval; signature verifier; sandbox
enforcement; registry trust policy; network allowlist; secret handling; route
authorization; rollback plan; incident response.

## 12. Target A relationship

- Target A complete is **prerequisite evidence** for any future Target B review.
- Target A complete **does NOT authorize** Target B.
- Target B **remains disabled** until the human-approval gates are resolved.

## 13. P0 state (24 / 0 / 19 / 5)

| Dimension | Value |
|-----------|-------|
| Total P0 gates | 24 |
| Resolved / approved | 0 |
| Partial evidence | 19 |
| Pending human review | 5 |
| Pending gates | P0-15 / P0-16 / P0-18 / P0-19 / P0-22 |

P0 `resolved_count` remains **0**. This is unchanged by Phase 4A.

## 14. Route governance (unchanged — 34/34/5/0/1/1)

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

Baseline `34/34/5/0/1/1`, every new-route flag `0`,
`assert_route_governance_unchanged` passes, no drift. Unchanged by Phase 4A.

## 15. Production safety (unchanged)

Static wording only (the frontend does not inspect a live process). Every flag
is frozen false: production Gateway expected unchanged and untouched, Dev Gateway
stopped, Dashboard not started, ports 5180 / 5181 free, no production home access
(not even metadata), no production state database access, no external network, no
real secret / API key read.

> The exact production Gateway PID (expected `28428`) is deliberately NOT carried
> in the frontend view-model — it is environment-specific. The frontend states the
> gateway is expected unchanged; the exact PID lives in docs / tests only.

## 16. No production home access

The dev WebUI binds to `127.0.0.1` only. There is **no** production home access
— not even a metadata-only stat / ls / resolve. Forbidden path assertions use
fake / string-policy paths only. The backend scaffold source contains no
production-home path reference.

## 17. No production state database access

There is no production state database access. Forbidden path assertions use fake
/ string-policy paths only. The backend scaffold source contains no production
state-database path reference.

## 18. Tests and validation

- Phase 4A frontend tests (panel + view-model + no-leak + routes): 84 pass
  (19 + 47 + 10 + 8).
- Backend scaffold test (`test_dev_web_phase4a_target_b_readiness_scaffold.py`)
  and isolation test (`test_dev_web_phase4a_target_b_readiness_isolation.py`):
  72 pass; the scaffold returns disabled, the deny builders deny every forged
  metadata payload, the shape validator trusts nothing, the source carries no
  filesystem / network / subprocess / dynamic-import / eval / exec primitive, and
  route governance is unchanged (`34/34/5/0/1/1`).
- `pnpm run lint`: clean. `pnpm run type-check` (`vue-tsc --noEmit`): clean.
  Full frontend suite: 1650 pass (regression preserved — Target A, Governance
  Hub, Human Review, Runtime Governance, and all Phase 3 surfaces intact).
- `ruff check` on the new Python files: clean.
- `memory-check` PASS; `dev-check` passes (only expected dirty-worktree WARN).

## 19. Exact still-NO-GO list

Every item below remains NO-GO / disabled and is rendered as explanatory TEXT
only — never as an interactive control:

- Target B execution — DISABLED.
- Production plugin runtime — NO-GO.
- Arbitrary / signed plugin loading — NO-GO.
- Local plugin directory loading (outside the fixture allowlist) — NO-GO.
- Remote registry fetch — NO-GO / disabled.
- Marketplace — NO-GO / disabled.
- External plugin fetch — NO-GO.
- External network — NO-GO.
- Real API key reading — NO-GO.
- WebUI execution (execute / run / batch / submit) — NO-GO / disabled.
- Approval / authorize / signoff / resolve / override — NO-GO.
- Trust token provisioning — not provisioned.
- Production rollout — NO-GO.
- New backend route — NO-GO (route counts unchanged).

**Allowed wording** (used here): "Target B readiness scaffold implemented.";
"Target B remains disabled."; "Production runtime remains NO-GO."; "Registry
remains disabled."; "Marketplace remains disabled."; "WebUI execution remains
disabled."; "P0 `resolved_count` remains 0."

**Forbidden wording** (never used): "Production runtime approved."; "Target B
complete."; "Implementation Authorization GO."; "Production rollout approved.";
"P0 resolved."; "Human review approved."; "Registry enabled."; "Marketplace
enabled."; "WebUI execution enabled."

## 20. Recommended future phases

The next step is **not** automatic. Before any Target B implementation could be
considered, the human-approver gate must advance the five pending P0 gates
(P0-15, P0-16, P0-18, P0-19, P0-22) through an out-of-band human approval,
provision a real trust token, approve a production sandbox / worker lifecycle,
a signature verifier, a registry trust policy, a network allowlist, a
secret-handling policy, and a rollback / incident plan, and authorize any new
route via a route-governance review. That authorization is a separate
human-governed decision — it is not implied or enabled by this readiness
scaffold.

## 21. Authorization boundary (unchanged)

This is a **read-only** readiness scaffold. It is **not** an authorization, **not**
an approval, **not** a signoff, **not** a closeout, and **not** production
authorization. Production plugin runtime, arbitrary plugin loading, remote
registry, marketplace, external network, real API keys, WebUI execution,
approval / authorization, and production rollout all remain **NO-GO / disabled**.

## 22. Files

### Frontend source (`apps/hermes-dev-webui/src/`)

- `types/api/targetBReadiness.ts` — Target B readiness view-model types (new).
- `constants/targetBReadinessManifest.ts` — frozen Target B constants (new).
- `lib/targetBReadinessViewModel.ts` — pure Target B projections + redactor (new).
- `components/devconsole/GovernanceHubTargetBReadiness.vue` — Target B region (new).
- `components/devconsole/GovernanceHubSection.vue` — wires the region in (extended).

### Frontend tests

- `tests/phase4a-target-b-readiness-panel.spec.ts`
- `tests/phase4a-target-b-readiness-view-model.spec.ts`
- `tests/phase4a-target-b-readiness-no-leak.spec.ts`
- `tests/phase4a-target-b-readiness-routes.spec.ts`

### Backend disabled scaffold + tests

- `hermes_cli/dev_web_target_b_readiness.py` — pure-stdlib disabled scaffold (new).
- `tests/test_dev_web_phase4a_target_b_readiness_scaffold.py` — scaffold behavior (new).
- `tests/test_dev_web_phase4a_target_b_readiness_isolation.py` — backend isolation (new).

### Docs

- `docs/webui/phase4a-target-b-readiness-scaffold-evidence.md` (this file)
