# Phase 3C — Static Capability Registry Implementation

| Field | Value |
|-------|-------|
| Phase | 3C (Implementation) |
| Title | Static dev-only Capability Registry |
| Status | Implemented |
| Date | 2026-06-17 |
| Impl ID | `PHASE-3C-IMPL-001` |

## 1. What shipped

A **static, dev-only Capability Registry** that *describes* the capabilities the
dev instance knows about — read-only tools, sandbox write/rollback, provider
capabilities (including the live manual one-shot, listed but **not executed**),
workflow step types, audit/system reads, and a set of explicitly blocked
forbidden capabilities (dynamic plugin load, remote registry, marketplace,
shell, database mutation, external HTTP, production operation).

The registry **describes only — it does not grant permission.** It does not
bypass Tool policy, the Provider live gate, Workflow approval, dry-run,
confirmation, or audit.

## 2. What did NOT ship (deferred / forbidden)

- No plugin runtime. No dynamic loading (no `importlib`, no path-based load).
- No remote registry / marketplace / external plugin fetch.
- No provider write, provider auto-write, or autonomous write.
- No live provider execution, no real API key read, no external network.
- No production rollout, no `~/.hermes` access, no production `state.db` access.
- No new HTTP route, no Provider route, no Tool write route.

A future Plugin Runtime, if ever needed, must be a separately authorized phase
(Phase 3D / 3E) with its own scope freeze, threat model, and GO / NO-GO.

## 3. Backend deliverables

| Module | Responsibility |
|--------|----------------|
| `hermes_cli/dev_web_capability_registry_schema.py` | Frozen taxonomies (categories, statuses, permission classes, trust levels, execution modes, route exposures, sources), allowed/required/forbidden field sets, validation predicates |
| `hermes_cli/dev_web_capability_registry_manifest.py` | The static, deterministic, tracked manifest (single source of truth). Pinned timestamps; no execution surface |
| `hermes_cli/dev_web_capability_registry_policy.py` | Permission-class / trust-level / status composition checks (gate coherence, forbidden-class non-executability) |
| `hermes_cli/dev_web_capability_registry_audit.py` | `capability_registry_*` audit bridge — reuses `AUDIT_KIND_INTERNAL`, defensive re-redaction, fail-safe |
| `hermes_cli/dev_web_capability_registry.py` | Loader: validates the manifest (fail-closed), exposes the read-only summary + per-capability safe detail |

## 4. API integration (no new route)

The frozen registry summary rides the **existing** `GET /api/dev/v1/status`
response under `data.capabilityRegistry`. No new HTTP route is introduced. The
per-capability list / detail is a deterministic static mirror on the frontend
(`constants/capabilityRegistryManifest.ts`); only the authoritative validation
status + counts come from the live `/status` block.

Route governance is unchanged: OpenAPI paths **34**, runtime routes **34**,
Tool GET **5**, Tool write HTTP route **0**, Tool dry-run **1**, Tool execution
**1**.

## 5. Frontend deliverables

A read-only Dev Console section (`/#/console` → "Capability Registry"):

- `CapabilityRegistrySection.vue` — section shell + filters
- `CapabilityRegistrySummary.vue` — frozen policy flags + live counts
- `CapabilityRegistryTable.vue` — capability list with badges + blocked reason
- `CapabilityRegistryDetailDrawer.vue` — full safe record for one capability
- `CapabilityPermissionBadge.vue` / `CapabilityTrustBadge.vue` /
  `CapabilityStatusBadge.vue` — non-color badges (icon + label)

## 6. Frozen invariants

- `devOnly = true`, `productionAllowed = false`.
- `dynamicLoadingAllowed = false`, `remoteRegistryAllowed = false`,
  `marketplaceAllowed = false`.
- Validation fails closed: an invalid manifest surfaces
  `status = validation_failed`; invalid entries are blocked, never enabled.
- No-leak: the summary, every detail, and every audit event carry no API key,
  Authorization, Bearer, secret, callable repr, shell command, SQL statement,
  production path, local plugin path, dynamic import path, or external URL.

## 7. Tests

- Backend: `tests/test_dev_web_phase_3c_capability_{schema,manifest,validation,policy,status_api,audit,no_dynamic_loading,security}.py`
  (160 tests).
- Frontend: `src/tests/phase3c-capability-registry-{panel,summary,table,detail,no-leak,badges}.spec.ts`.
- Smoke: `tests/smoke/phase-3c-capability-registry-smoke.spec.ts`
  (Profile P, included in `all`).

## 8. Cross-references

- [Phase 3C planning](phase-3c-planning.md)
- [Phase 3C scope freeze](phase-3c-capability-registry-scope-freeze.md)
- [Phase 3C no dynamic loading policy](phase-3c-no-dynamic-loading-policy.md)
- [Phase 3C security boundary](phase-3c-capability-registry-security-boundary.md)
- [Phase 3C test report](phase-3c-capability-registry-test-report.md)

---

## 9. Phase 3C-H1 Hardening Update (2026-06-18)

The registry was hardened by `HARDENING-3C-H1-001` — 12 / 12 lenses PASS,
P0 = 0, P1 = 0. One real defect was found and fixed minimally: the forbidden-
field scanner is now **recursive** (a nested forbidden field inside an allowed
field's value is detected and blocked), and scalar-string fields are type-
guarded (no nested structure smuggling). All 160 Phase 3C backend tests still
pass. Coverage added: 8 backend + 6 frontend hardening test files, a new smoke
profile (Profile Q), and `scripts/run-dev-webui-phase3c-hardening-audit.sh`.
Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1); no new route; production
untouched. See [Phase 3C-H1 hardening](phase-3c-h1-capability-registry-hardening.md).
