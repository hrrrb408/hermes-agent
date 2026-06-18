# Phase 3D — Final Acceptance

| Field | Value |
|-------|-------|
| Phase | 3D (Closeout) |
| Title | Static Plugin Descriptor Registry — Final Acceptance |
| Status | Accepted (dev-only milestone) |
| Date | 2026-06-19 |
| Acceptance ID | `PHASE-3D-ACCEPTANCE-001` |

## 1. Acceptance scope

Final acceptance of the Phase 3D static dev-only Plugin Descriptor Registry as a
**dev-only descriptive milestone**: the registry + its read-only `/status` block
+ its read-only Dev WebUI panel + its `plugin_descriptor_*` audit + its
smoke / hardening coverage. Acceptance is for the dev branch only; it is **not**
a production acceptance.

## 2. Accepted deliverables

- Static plugin descriptor schema (frozen taxonomies: trust levels, statuses,
  execution modes, sources, permission classes; allowed / required / forbidden
  field sets, canonical + alias; restrictiveness ordering; validation
  predicates).
- Static plugin descriptor manifest — 12 deterministic, descriptor-only
  descriptors (3 visible, 4 disabled, 5 blocked); pure data, no executable
  reference.
- Static descriptor registry loader (validation, read model, `/status` block
  builder); fail-closed.
- Descriptor validation — required fields, enum membership, allowed-field
  whitelist, uniqueness, first-version invariants.
- Descriptor **forbidden-field** rejection — canonical + alias + casing
  variants, **recursive at any depth**, with a scalar-string type guard;
  fail-closed.
- Descriptor **capability binding** to existing Phase 3C capabilityIds — no new
  capability, no new permission class, no dangling binding.
- **Most-restrictive permission inheritance** — escalation and trust self-upgrade
  rejected fail-closed.
- Trust-boundary classification — visible requires verified trust; forbidden
  capability must be blocked; experimental disabled.
- **Disabled-by-default** enforcement — `disabledByDefault = true`,
  `executionMode = descriptor_only` for every descriptor.
- **Dev-only** enforcement — `devOnly = true`, `productionAllowed = false` for
  every descriptor; `enforce_dev_environment()` refuses the production home.
- `plugin_descriptor_*` audit bridge into the Phase 2D durable store — redacted,
  no-leak, fail-safe; never writes to the production home.
- `/status pluginDescriptorRegistry` read-only block — all runtime flags false;
  value-free (no secret / callable / path / command / URL); no new route.
- Read-only Dev WebUI Plugin Descriptor panel — summary / table / detail drawer /
  non-color badges + runtime-disabled banner; `plugins` nav section.
- Phase 3D-H1 12-lens hardening — 10 backend + 8 frontend hardening tests; the
  H1 smoke profile + spec; the hardening audit script.
- Smoke Profile R (`phase3d_plugin_descriptor_registry_static`) and the H1
  profile (`phase3d_h1_plugin_descriptor_registry_hardening`), both in `all`.

## 3. Accepted safety guarantees

- Descriptor-only; no plugin runtime; no plugin loader; no plugin execution.
- No dynamic loading (`importlib` / `__import__` / path load / directory scan) —
  AST-guarded across all five descriptor modules.
- No local plugin directory loading; no remote registry; no marketplace; no
  external plugin fetch; no provider-generated plugin; no LLM-generated plugin
  install.
- No shell execution, database mutation, external HTTP execution, or production
  operation.
- Permission class is the most-restrictive among bindings; no escalation; no
  trust self-upgrade; a forbidden binding must be `blocked`.
- Recursive forbidden-field rejection; value-free `/status` and UI; no-leak
  audit.
- Route governance unchanged (34 / 34 / 5 / 0 / 1 / 1); no new route.
- No `~/.hermes` access; no production `state.db` access; no runtime artifacts
  or `.claude/` committed.

## 4. Rejected / not-implemented capabilities

- Real plugin runtime.
- Plugin loader execution.
- Plugin execution.
- Dynamic loading.
- `importlib` / `__import__` dynamic import.
- Local plugin directory loading.
- Remote registry.
- Marketplace.
- External plugin fetch.
- Provider-generated plugin.
- LLM-generated plugin install.
- Shell command execution.
- Database mutation.
- External HTTP execution.
- Production operation.
- Provider write.
- Autonomous write.
- Production rollout.
- New HTTP route.

## 5. Test evidence

- Phase 3D backend tests (10 files): **316 PASS**.
- Phase 3D-H1 backend tests (10 files): **297 PASS**.
- Preservation + route governance: **3002 PASS**.
- Broader preservation: **PASS**.
- Frontend unit: **1188 PASS** (104 files).
- Frontend H1 tests (8 files): **50 PASS**.
- Frontend type-check / lint / build: **PASS**.
- Smoke `all` (including Profile R and the H1 profile): **PASS**.
- Hardening audit script: **20 / 20 gates PASS**.
- `memory-check` / `dev-check`: **PASS** (dev-check allows `.claude/` untracked
  WARN).
- Production Gateway PID gate: **PASS**.
- Route governance: **PASS** (34 / 34 / 5 / 0 / 1 / 1).

## 6. Hardening evidence

Phase 3D-H1 (HARDENING-3D-H1-001) verified the registry across **12 lenses**:
manifest consistency, forbidden fields, capability binding, permission
inheritance, trust boundary, non-execution, no dynamic loading,
provider/workflow boundary, audit no-leak, status API, UI a11y / no-leak, and
smoke / preservation / production isolation. All 12 lenses PASS. **No
implementation code changed** — no defect required a fix.

## 7. Production safety evidence

- Production Gateway PID `28428` (count 1), not stopped / restarted / replaced /
  signaled / reconfigured before, during, or after Phase 3D Implementation and
  Phase 3D-H1.
- Dev services bind to `127.0.0.1` only; 5180 / 5181 free before and after.
- No `~/.hermes` access; no production `state.db` access.
- No live provider request; no real API-key read; no external network call.

## 8. Route governance evidence

OpenAPI paths **34** · runtime routes **34** · Tool GET **5** · Tool write HTTP
route **0** · Tool dry-run route **1** · Tool execution route **1**. No new HTTP
route, no new Tool write route, no Provider route, no plugin route, no descriptor
route. The registry is exposed via the existing `/status` response only.

## 9. Risk state

P0 open = **0**. P1 open = **0**. P0 introduced by Phase 3D = **0**; P1 = **0**.
P0 introduced by Phase 3D-H1 = **0**; P1 = **0**. P2 deferred = runtime-related
items only (intentional deferrals, not defects). See
[phase-3d-risk-closure-after-h1](phase-3d-risk-closure-after-h1.md).

## 10. Known limitations

See
[phase-3d-known-limitations-and-deferred-work](phase-3d-known-limitations-and-deferred-work.md).
These are intentional deferrals, not unfinished defects.

## 11. Final acceptance statement

**Phase 3D is accepted as a static dev-only Plugin Descriptor Registry
milestone.** The registry is descriptor-only, disabled-by-default,
capability-bound, read-only, and dev-only. It does not grant permissions, does
not execute plugins / providers / workflows, does not create approvals /
confirmations / dry-runs / routes / execution paths, and does not bypass Tool
policy, the Provider live gate, Workflow approval, dry-run, confirmation, or
audit. Descriptors bind only to existing Phase 3C capabilityIds. Real plugin
runtime execution remains NO-GO.

## 12. Cross-references

- [Closeout](phase-3d-closeout.md)
- [Final security boundary after H1](phase-3d-final-security-boundary-after-h1.md)
- [Risk closure after H1](phase-3d-risk-closure-after-h1.md)
- [Test gate summary after H1](phase-3d-test-gate-summary-after-h1.md)
- [Real runtime NO-GO](phase-3d-real-runtime-no-go.md)
