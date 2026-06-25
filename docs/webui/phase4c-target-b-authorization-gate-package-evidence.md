# Phase 4C — Target B Authorization & Gate Resolution Package (Evidence)

**Phase:** 4C — Target B Authorization & Gate Resolution Package
**Status:** authorization package implemented; readiness evaluator implemented and denies by default; Target B remains BLOCKED; production runtime remains NO-GO; trust token not provisioned; P0 resolved_count remains 0; route governance unchanged (34/34/5/0/1/1).
**Branch:** `dev-huangruibang`
**Preceding commit:** `feat(webui): implement gated target b runtime architecture` (`68a038fce`)

> This document is **evidence**, not an authorization. It records that the
> Target B authorization-material validation structure has been implemented
> while every gate stays fail-closed. It is not a signoff, not a closeout, not an
> approval, and not production authorization. No approval is fabricated, no P0
> gate is bypassed, no trust token is minted, and the production runtime is not
> flipped to GO. Target B remains BLOCKED.

---

## 1. Phase 4C scope

Phase 4C builds the **authorization-material validation structure** on top of
the Phase 4B gated engineering layers. It does **not** fabricate an approval,
does **not** bypass P0, does **not** mint a trust token, does **not** treat
metadata / a static manifest / an AI-generated approval as authorization, and
does **not** flip the production runtime to GO. It builds the deterministic,
fail-closed structure that real out-of-band authorization materials would have
to satisfy, plus the unified enablement readiness evaluator that composes them:

- Human approval record schema + validator.
- Trust token validation pipeline.
- Trusted publisher set + policy.
- Production signature verifier authorization adapter.
- Sandbox worker lifecycle approval model.
- Registry trust policy approval model.
- Network allowlist policy.
- Secret handling policy.
- Rollback / incident plan approval model.
- Route authorization plan (disabled — never registered).
- P0 pending-gate resolution evaluator.
- Unified enablement readiness evaluator (the aggregator).
- WebUI Phase 4C Authorization Package region (read-only).

## 2. Why Target B remains blocked

Target B remains BLOCKED because **no real out-of-band authorization material
exists**. Concretely:

- No real human approval is present (the validator returns
  `human_approval_missing`).
- No trust token is provisioned (the validator returns
  `trust_token_not_provisioned`).
- The production trusted publisher set is empty.
- The production signature verifier is not authorized (fixture-only).
- No sandbox worker lifecycle is approved.
- No registry trust policy is approved.
- No network allowlist is approved.
- No secret handling policy is approved.
- No rollback / incident plan is approved.
- No route is authorized.
- P0-15 / P0-16 / P0-18 / P0-19 / P0-22 remain pending human review.

The enablement readiness evaluator returns `BLOCKED` by default. A complete set
of **fixture** inputs may reach `AUTHORIZATION_READY_BUT_NOT_ENABLED` in test-only
mode, but `production_enablement_allowed` stays `False`. The
`ENABLEMENT_ALLOWED_BY_POLICY` status requires `production_mode=True` AND a
non-fixture complete package — which the dev skeleton never provides.

## 3. Human approval record schema

`hermes_cli/dev_web_target_b_human_approval.py` defines the real out-of-band
human approval record schema (`HumanApprovalRecord` plus `HumanReviewer`,
`ApprovalScope`, `ApprovalGateCoverage`, `ApprovalValidityWindow`,
`ApprovalDecision`, `ApprovalEvidenceRef`) and the validator
(`validate_human_approval_record`). A valid approval must be signed by a
`trusted_human_reviewer`, cover the required Target B gates, carry a non-wildcard
environment scope, an explicit validity window, a replay nonce, evidence
references, and a token-derived signature. The dev skeleton holds no trust
token, so every record is invalid — including fake, AI, metadata, static-manifest,
forged, and fixture approvals. Default result: `valid=False`,
`reason="human_approval_missing"`. A test-only fixture builder
(`build_fixture_human_approval`) is explicitly `fixture_only` and never authorizes
production.

## 4. Trust token validation

`hermes_cli/dev_web_target_b_trust_token.py` defines the trust token validation
pipeline (`TrustTokenEnvelope`, `TrustTokenClaims`, `TrustTokenPolicy`,
`TrustTokenValidationResult`). The validator rejects every fake / smuggled token
without reading any environment secret, any production home file, any production
config, or any network resource. It never accepts `trust_token=fake`,
`approved_by_ai=true`, `target_b_authorized=true`, or
`production_runtime_go=true`. Default result: `provisioned=False`, `valid=False`,
`production_authorized=False`, `reason="trust_token_not_provisioned"`. A
deterministic fixture token proves the validator's positive logic but never
authorizes production.

## 5. Trusted publisher set

`hermes_cli/dev_web_target_b_trusted_publishers.py` defines the trusted publisher
set (`TrustedPublisher`, `PublisherTrustPolicy`, `PublisherVerificationResult`).
The production set is empty. Unknown, marketplace, unsigned, wildcard, and
overbroad-permission publishers are rejected. A fixture publisher is honored only
under the fixture policy and never authorizes production.

## 6. Production signature verifier

`hermes_cli/dev_web_target_b_production_signature.py` extends the Phase 4B
signature layer with a production verifier authorization adapter
(`ProductionSignatureVerifierStatus`, `SignatureEnablementEvaluation`). The
verifier interface is implemented; the production verifier is NOT authorized
(no real signing key / trust policy / trusted publishers); the fixture verifier
is test-only. The evaluation proves deterministically that a valid fixture
signature does not imply production authorization, that a forged signature is
rejected, that an unknown publisher is rejected, and that a mismatched checksum
is rejected.

## 7. Sandbox lifecycle

`hermes_cli/dev_web_target_b_sandbox_lifecycle.py` defines the sandbox worker
lifecycle approval model (`SandboxWorkerLifecyclePlan`, `SandboxIsolationPolicy`,
`SandboxResourceLimits`, `SandboxLifecycleApprovalResult`). The lifecycle is not
approved: no worker start, no process spawn, no network, no filesystem write, no
secrets, and the production gateway (PID 28428) is untouched. No worker is ever
started, no Docker is run, and no shell is executed.

## 8. Registry trust policy

`hermes_cli/dev_web_target_b_registry_policy.py` defines the registry trust
policy approval model (`RegistryTrustPolicyApproval`, `RegistryAllowlist`,
`RegistryPackagePolicy`, `RegistryAuthorizationReport`). The registry is DISABLED.
No fetch, no marketplace, no unsigned packages, no wildcard domains, and no
external network. The `.invalid` example domain is documentation-only.

## 9. Network allowlist

`hermes_cli/dev_web_target_b_network_policy.py` defines the network allowlist
policy (`NetworkAllowlistPolicy`, `NetworkDestination`, `NetworkPolicyEvaluation`).
The default policy is deny-all: zero destinations allowed, wildcard hosts denied,
cleartext HTTP denied, private ranges denied, and no socket is ever opened.

## 10. Secret handling policy

`hermes_cli/dev_web_target_b_secret_policy.py` defines the secret handling policy
(`SecretHandlingPolicy`, `SecretScope`, `SecretAccessDecision`). Default deny: no
API key, no environment secret, no production-home secret, no provider key is
read. Secret values are always redacted. No environment secret is read and no
production home path is resolved.

## 11. Rollback / incident plan

`hermes_cli/dev_web_target_b_incident_rollback.py` extends the Phase 4B rollback
layer with an incident response plan approval model (`RollbackPlan`,
`IncidentResponsePlan`, `KillSwitchAuthorization`, `RollbackReadinessResult`).
The rollback plan is design-only; the incident plan is not approved; the kill
switch is design-ready only (not armed, not production-authorized); production
rollout stays NO-GO; the production gateway is untouched. No process is signaled.

## 12. Route authorization plan

`hermes_cli/dev_web_target_b_route_authorization.py` defines the route
authorization plan (`RouteAuthorizationPlan`, `RouteChangeRequest`,
`RouteGovernanceDecision`, `RouteAuthorizationReport`). No route is authorized.
The proposed routes are disabled documentation-only — never registered, zero
OpenAPI delta, zero runtime-route delta, and the route baseline is unchanged
(34/34/5/0/1/1). No backend route is added and no `dev_web_api` integration is
performed. Because P0 is unresolved and the trust token is missing, the real
routes are not registered.

## 13. P0 gate resolution evaluator

`hermes_cli/dev_web_target_b_p0_gate_resolution.py` defines the P0 pending-gate
resolution evaluator (`P0GateResolutionInput`, `P0GateCoverageRow`,
`P0GateResolutionResult`, `P0GateCoverageReport`). A pending gate can be resolved
only by a valid (non-fixture) human approval AND a valid (non-fixture) trust
token AND evidence coverage. Code evidence alone, metadata, AI, fake approval,
and fixture approval all leave the gate unresolved. Default result:
`resolved_count_delta=0`, `p0_resolved_count=0`, `pending_human_review=5`.

## 14. Enablement readiness evaluator

`hermes_cli/dev_web_target_b_enablement_readiness.py` is the aggregator
(`EnablementReadinessInput`, `EnablementReadinessResult`,
`TargetBAuthorizationPackageReport`). It composes the 11 authorization sub-layers
and the P0 gate coverage into a single readiness verdict. The four statuses are
`BLOCKED`, `AUTHORIZATION_PACKAGE_INCOMPLETE`, `AUTHORIZATION_READY_BUT_NOT_ENABLED`,
and `ENABLEMENT_ALLOWED_BY_POLICY`. The default verdict is `BLOCKED`.
`production_enablement_allowed` is `False` unless a complete, non-fixture package
AND `production_mode=True` are supplied — which the dev skeleton never provides.
Even `AUTHORIZATION_READY_BUT_NOT_ENABLED` does not start the production runtime.

## 15. WebUI authorization package panel

The read-only region `apps/hermes-dev-webui/src/components/devconsole/GovernanceHubTargetBAuthorization.vue`
is rendered inside the Governance Hub. It projects, from frozen static data only,
the authorization banner (BLOCKED), summary cards, the 11 authorization layers,
the human approval / trust token / trusted publisher / production signature /
sandbox lifecycle / registry-network-secret / rollback-incident / route
authorization / P0 gate coverage / enablement readiness panels, the enablement
blockers, and the forbidden / allowed action lists. It performs no approval, no
authorization, no provisioning, no execution, no route change, and no production
access. The only controls are harmless client-only toggles (filter, inspect,
copy, view cross-linked sections). The data layer is
`apps/hermes-dev-webui/src/lib/targetBAuthorizationViewModel.ts` (pure
projections with defense-in-depth redaction), the manifest is
`apps/hermes-dev-webui/src/constants/targetBAuthorizationManifest.ts` (frozen),
and the types are
`apps/hermes-dev-webui/src/types/api/targetBAuthorization.ts`.

## 16. Tests and validation

Python (13 files): `tests/test_target_b_human_approval.py`,
`tests/test_target_b_trust_token.py`, `tests/test_target_b_trusted_publishers.py`,
`tests/test_target_b_production_signature.py`,
`tests/test_target_b_sandbox_lifecycle.py`,
`tests/test_target_b_registry_authorization.py`,
`tests/test_target_b_network_policy.py`, `tests/test_target_b_secret_policy.py`,
`tests/test_target_b_incident_rollback.py`,
`tests/test_target_b_route_authorization.py`,
`tests/test_target_b_p0_gate_resolution.py`,
`tests/test_target_b_enablement_readiness.py`,
`tests/test_target_b_phase4c_isolation.py`.

Frontend (4 files): `phase4c-target-b-authorization-view-model.spec.ts`,
`phase4c-target-b-authorization-panel.spec.ts`,
`phase4c-target-b-authorization-no-leak.spec.ts`,
`phase4c-target-b-authorization-routes.spec.ts`.

The tests prove: missing human approval blocks; fake / AI / metadata / static
approvals rejected; missing trust token blocks; fake token rejected; trusted
publisher set empty; unknown publisher rejected; production signature verifier
unavailable blocks; fixture signature does not approve production; sandbox
lifecycle missing blocks; registry / network / secret policies default-deny;
rollback / incident missing blocks; route authorization missing blocks; P0
resolution delta 0; enablement readiness BLOCKED by default; a test-only complete
fixture reaches `AUTHORIZATION_READY_BUT_NOT_ENABLED` but never production
enabled; source purity (no forbidden primitives); no `~/.hermes` access; no
production `state.db` access; route governance unchanged; `dev_web_api` imports
no Phase 4C module; the production gateway is untouched.

## 17. Route governance unchanged

Route governance remains exactly `34/34/5/0/1/1`:

- OpenAPI paths = 34
- Runtime routes = 34
- Tool GET = 5
- Tool write HTTP route = 0
- Tool dry-run route = 1
- Tool execution route = 1
- New HTTP route = 0
- New Tool write route = 0
- New Provider route = 0
- New plugin route = 0
- New runtime route = 0

No backend route was added. The Phase 4C authorization modules are **not**
imported by `dev_web_api`, so they add no backend route and change no route
governance counts. The route authorization plan exists only as a disabled,
documentation-only plan.

## 18. Production safety unchanged

- The production Gateway (PID 28428) is referenced only as a do-not-touch
  string; it is never stopped, restarted, replaced, signaled, or modified.
- The dev Gateway remains stopped; the Dashboard is not started; ports 5180 /
  5181 remain free.
- No `~/.hermes` access (including metadata-only access); no production
  `state.db` access; no real API key read; no real trust token; no real plugin
  signature; no external network; no socket; no subprocess; no dynamic import;
  no eval / exec.

## 19. Exact blockers remaining

1. Real out-of-band human approval (covering P0-15 / P0-16 / P0-18 / P0-19 /
   P0-22) — none exists.
2. Real out-of-band trust token — not provisioned.
3. Trusted publisher set — empty.
4. Production signature verifier — not authorized (fixture-only).
5. Sandbox worker lifecycle — not approved.
6. Registry trust policy — not approved.
7. Network allowlist — not approved.
8. Secret handling policy — not approved.
9. Rollback / incident plan — not approved (design-ready only).
10. Route authorization — not approved.
11. P0 gate resolution — P0-15 / P0-16 / P0-18 / P0-19 / P0-22 unresolved.

## 20. What a future Phase 4D actual enablement would require

A future Phase 4D actual enablement (explicitly out of scope here) would require,
all out-of-band and auditable:

- A real, signed human approval from a `trusted_human_reviewer` covering the five
  pending gates, with a token-derived signature, evidence references, a
  non-wildcard environment scope, a validity window, a replay nonce, and a known
  out-of-band channel.
- A real provisioned trust token with matching issuer / audience / subject /
  scope / gate claims.
- A real reviewed trusted publisher set.
- A real production signature verifier (real signing key + trust policy).
- An approved sandbox worker lifecycle.
- An approved registry trust policy + network allowlist + secret handling policy.
- An approved rollback / incident plan with an armed kill switch.
- An approved route authorization plan (only then could a real route be
  registered, under a separate route-governance change).
- Resolution of P0-15 / P0-16 / P0-18 / P0-19 / P0-22.

Only when every one of those is real (not fixture, not metadata, not AI, not a
static manifest) and `production_mode` is explicitly authorized would the
readiness evaluator return `ENABLEMENT_ALLOWED_BY_POLICY`. Phase 4C implements
the validation structure that would make that determination trustworthy; it does
not provide any of the materials.

---

**Conclusion:** the Phase 4C Target B authorization package is implemented.
Target B remains BLOCKED. The production runtime remains NO-GO. The trust token
remains not provisioned. P0 resolved_count remains 0. The readiness evaluator is
implemented and denies by default. No new backend route was added and no
production state was touched.
