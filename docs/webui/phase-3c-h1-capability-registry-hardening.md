# Phase 3C-H1 — Capability Registry Hardening

| Field | Value |
|-------|-------|
| Phase | 3C-H1 (Hardening) |
| Title | Static Capability Registry Hardening |
| Status | Complete — 12 / 12 lenses PASS, P0 = 0, P1 = 0 |
| Date | 2026-06-18 |
| Branch | `dev-huangruibang` |
| Hardening ID | `HARDENING-3C-H1-001` |
| Input HEAD | `703a4a980427e2eaac925f4659af74e0a7ace070` |
| Output HEAD | _(set on commit)_ |

## 1. Goal

A deterministic hardening pass over the Phase 3C static dev-only Capability
Registry. The registry already shipped descriptive-only, read-only, and
value-free; this pass **bounds every boundary with a test**, closes one real
defect found during review, and adds a dedicated smoke profile + hardening
audit script.

Phase 3C-H1 hardens the static dev-only Capability Registry.

- **No plugin runtime. No dynamic loading. No remote registry. No marketplace.
  No external plugin fetch. No provider-generated plugin. No provider write.
  No autonomous write. No production rollout. No live provider request. No
  real API key read. No external network. No new route.** The registry
  describes only and does not grant permission.

## 2. Scope

Hardening (tests > smoke > audit script > docs > minimal code fix). Only one
real defect was found and fixed minimally (Lens 2 — nested forbidden field
leak); the rest is verification coverage.

## 3. Hardening IDs

| Lens | ID |
|------|----|
| Overall | `HARDENING-3C-H1-001` |
| Manifest / mirror consistency | `CAP-MANIFEST-3C-H1-001` |
| Forbidden fields / fail-closed | `CAP-FORBIDDEN-FIELDS-3C-H1-001` |
| Non-grant / permission inheritance | `CAP-PERMISSION-NON-GRANT-3C-H1-001` |
| Permission / trust / status coherence | `CAP-PERMISSION-TRUST-3C-H1-001` |
| Tool / provider / workflow mapping | `CAP-MAPPING-3C-H1-001` |
| No dynamic loading / remote / marketplace | `CAP-NO-DYNAMIC-3C-H1-001` |
| Audit no-leak | `CAP-AUDIT-3C-H1-001` |
| /status API / route governance | `CAP-STATUS-API-3C-H1-001` |
| UI / badges / a11y / no-leak | `CAP-UI-3C-H1-001` |
| Smoke / preservation / production isolation | `CAP-SMOKE-3C-H1-001` |

## 4. 12-Lens summary

| Lens | Name | Status | Findings | Fixes |
|------|------|--------|----------|-------|
| 1 | Static Manifest Determinism / Mirror Consistency | PASS | No drift test existed | Added drift detector + mirror-consistency tests |
| 2 | Schema Forbidden Fields / Validation Fail-closed | PASS | **Nested forbidden field leaked** | Recursive forbidden scan + scalar type guard |
| 3 | Registry Non-grant / Permission Inheritance | PASS | Coverage gap | Added non-grant / side-effect-free tests |
| 4 | PermissionClass / TrustLevel / Status Coherence | PASS | Coverage gap | Added coherence rule tests |
| 5 | Tool / Sandbox / Rollback Mapping | PASS | Coverage gap | Added exact mapping tests |
| 6 | Provider / Live Gate / No Tool Execution | PASS | Coverage gap | Added provider mapping tests |
| 7 | Workflow / No Auto-advance / Approval | PASS | Coverage gap | Added workflow mapping tests |
| 8 | No Dynamic Loading / Remote / Marketplace | PASS | Coverage gap | Added AST call-scan + flag tests |
| 9 | capability_registry_* Audit / No-leak | PASS | Coverage gap | Added per-event-type redaction tests |
| 10 | /status API / Route Governance | PASS | Coverage gap | Added route-count + no-route tests |
| 11 | Frontend UI / Badges / A11y / No-leak | PASS | Coverage gap | Added a11y + validation-state tests |
| 12 | Smoke / Preservation / Production Isolation | PASS | No H1 smoke profile | Added Profile Q + hardening audit script |

**12 / 12 PASS. P0 = 0. P1 = 0.**

## 5. The one real defect (Lens 2)

The forbidden-field scanner was shallow: a forbidden field nested inside an
allowed field's value — e.g. `{"metadataSchema": {"shellCommand": "rm -rf",
"secret": "leak", "Authorization": "Bearer x"}}` — passed validation and was
exposed verbatim by the read model. A caller feeding an unvalidated, crafted
manifest could therefore leak a forbidden token.

Fix (minimal, defense-in-depth):

- `is_forbidden_field_present` now scans **recursively** (top-level keys and
  any nested dict / list / tuple value), so a nested forbidden field is
  detected and the entry is blocked fail-closed.
- `_validate_entry` additionally requires the scalar-string fields
  (`displayName`, `description`, `metadataSchema`, …) to be string scalars — a
  nested structure (forbidden or not) is rejected, preventing any content
  smuggling past the scalar read model.

The static manifest is unaffected (it carries no nested structures); all 160
Phase 3C backend tests still pass.

## 6. Deliverables

- Backend hardening tests (8 files):
  `test_dev_web_phase_3c_h1_{manifest_consistency,forbidden_fields,permission_non_grant,permission_trust_coherence,tool_provider_workflow_mapping,no_dynamic_loading,audit_no_leak,status_api_security}.py`.
- Frontend hardening tests (6 files):
  `phase3c-h1-registry-{mirror,panel,detail,badges-a11y,no-leak,validation-states}.spec.ts`.
- Smoke: `phase3c_h1_capability_registry_hardening` profile (Profile Q) +
  `tests/smoke/phase-3c-h1-capability-registry-hardening-smoke.spec.ts`,
  included in `all`.
- Hardening audit script: `scripts/run-dev-webui-phase3c-hardening-audit.sh`.
- Docs: this file + 11 lens/area docs + updates to 8 existing docs.
- Code fixes: `dev_web_capability_registry_schema.py` (recursive scan) +
  `dev_web_capability_registry.py` (scalar type guard).

## 7. What this phase does NOT do

No plugin runtime. No dynamic loading, `importlib`, remote registry,
marketplace, external plugin fetch, provider-generated plugin, shell command,
database mutation, external HTTP capability execution, production operation,
live provider request, real API key read, external network call, production
rollout, `~/.hermes` access, or production `state.db` access. No new HTTP
route, Tool write route, or Provider route.

## 8. Route governance (unchanged)

OpenAPI paths **34**, runtime routes **34**, Tool GET **5**, Tool write HTTP
route **0**, Tool dry-run **1**, Tool execution **1**.

## 9. Production safety

Production Gateway PID 28428 was not affected (count 1, never stopped /
restarted / replaced / signaled). Dev services bind to `127.0.0.1` only;
5180 / 5181 free before and after.

## 10. Deferred / not implemented

Plugin runtime (Phase 3D — not started). Dynamic loading. Remote registry.
Marketplace. External plugin fetch. Provider-generated plugin. Provider write.
Autonomous write. Production rollout. Live provider execution. Real API key
read. External network. New route. Generated frontend mirror (P2 — drift is
bounded by the consistency test; a generator is deferred).

## 11. Cross-references

- [Phase 3C implementation](phase-3c-static-capability-registry-implementation.md)
- [Phase 3C security boundary](phase-3c-capability-registry-security-boundary.md)
- [Phase 3C test report](phase-3c-capability-registry-test-report.md)
- [Manifest consistency hardening](phase-3c-h1-manifest-consistency-hardening.md)
- [Forbidden fields hardening](phase-3c-h1-forbidden-fields-hardening.md)
- [Permission non-grant hardening](phase-3c-h1-permission-non-grant-hardening.md)
- [Permission / trust coherence](phase-3c-h1-permission-trust-coherence.md)
- [Tool / provider / workflow mapping](phase-3c-h1-tool-provider-workflow-mapping.md)
- [No dynamic loading hardening](phase-3c-h1-no-dynamic-loading-hardening.md)
- [Audit no-leak hardening](phase-3c-h1-audit-no-leak-hardening.md)
- [/status API hardening](phase-3c-h1-status-api-hardening.md)
- [UI a11y / no-leak hardening](phase-3c-h1-ui-a11y-no-leak-hardening.md)
- [Smoke + preservation report](phase-3c-h1-smoke-and-preservation-report.md)
- [H1 test report](phase-3c-h1-test-report.md)
