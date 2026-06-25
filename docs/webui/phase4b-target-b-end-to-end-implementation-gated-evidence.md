# Phase 4B — Target B End-to-End Implementation (Gated Evidence)

**Phase:** 4B — Target B End-to-End Implementation
**Status:** implementation scaffold complete; execution policy implemented and denies; production runtime remains NO-GO; WebUI execution remains disabled; P0 resolved_count remains 0.
**Branch:** `dev-huangruibang`
**Preceding commit:** `feat(webui): add target b readiness scaffold` (`8adeec35a`)

> This document is **evidence**, not an authorization. It records that the full
> Target B engineering path has been drafted while every dangerous capability
> stays gated and disabled. It is not a signoff, not a closeout, not an approval,
> and not production authorization. Target B remains gated.

---

## 1. Scope

Phase 4B implements the **full engineering path** for the Target B production
plugin runtime in a single, coherent, fail-closed layer set:

- Signed plugin package schema + shape/format validators.
- Signature verification interface + deterministic fixture verifier.
- Permission / capability model (15 permissions, all denied by default).
- Registry trust policy (disabled / allowlisted-off).
- Sandbox broker interface (disabled / design-only profile).
- Approval / authorization gate (no trust token; forgery defeated).
- Unified execution policy gate (aggregates every layer; always denies today).
- Runtime orchestrator (prepare = preview only; execute = denied).
- Audit trail (in-memory only; defense-in-depth redaction).
- Rollback / kill-switch model (design-ready only; no process touched).
- End-to-end readiness report (the gated aggregate).
- WebUI gated Target B Implementation region (read-only preview).

**This is not a small step.** The complete code structure, models, validators,
broker, policy gate, WebUI flow, audit, rollback, tests, and docs are all
landed in one commit. But because the authorization preconditions are not met,
the final state is **gated**: Target B implementation present, Target B
execution disabled, production runtime NO-GO, WebUI execution disabled,
registry disabled, marketplace disabled, approval NO-GO, P0 unchanged.

## 2. What is implemented

| Layer | Module | State |
|-------|--------|-------|
| Shared common | `hermes_cli/dev_web_target_b_common.py` | scaffolded, disabled |
| Package schema | `hermes_cli/dev_web_target_b_package.py` | scaffolded, disabled |
| Signature verification | `hermes_cli/dev_web_target_b_signature.py` | scaffolded, disabled (fixture-only verify) |
| Permission / capability | `hermes_cli/dev_web_target_b_permissions.py` | scaffolded, denied-by-default |
| Registry trust | `hermes_cli/dev_web_target_b_registry.py` | scaffolded, disabled |
| Sandbox broker | `hermes_cli/dev_web_target_b_sandbox.py` | scaffolded, disabled |
| Approval / authorization | `hermes_cli/dev_web_target_b_approval.py` | scaffolded, NO-GO |
| Execution policy | `hermes_cli/dev_web_target_b_execution_policy.py` | implemented, denies |
| Runtime orchestrator | `hermes_cli/dev_web_target_b_runtime.py` | scaffolded, denies |
| Audit trail | `hermes_cli/dev_web_target_b_audit.py` | scaffolded, in-memory only |
| Rollback / kill switch | `hermes_cli/dev_web_target_b_rollback.py` | design-ready only |
| Aggregate report | `hermes_cli/dev_web_target_b_report.py` | scaffolded, gated |
| WebUI region | `apps/hermes-dev-webui/.../GovernanceHubTargetBImplementation.vue` | read-only preview |

## 3. What remains disabled

- Production plugin runtime — **NO-GO**.
- Arbitrary / signed plugin loading — **NO-GO** (no package is ever loaded,
  imported, or executed).
- Local plugin directory scanning — **none** (no directory is ever scanned).
- Remote registry fetch — **disabled** (no network I/O of any kind).
- Marketplace — **disabled** (never reachable).
- External network — **disabled** (no socket / requests / httpx / aiohttp /
  urllib primitive anywhere in the layer set).
- Real API key / secret read — **none** (no real secret is read; all payloads
  are defense-in-depth redacted).
- WebUI execution — **disabled** (no execute / run / submit control; the flow
  is rendered as disabled TEXT only).
- Approval / authorization — **NO-GO** (no trust token provisioned; fake / AI /
  metadata approval rejected).
- Production rollout — **NO-GO** (kill switch design-ready only; production
  rollback not authorized).
- New backend route — **none added** (route governance unchanged).

## 4. Signed plugin package schema

The package descriptor carries: `package_id`, `package_name`, `version`,
`publisher`, `manifest_version`, `hermes_min_version`, `descriptor`,
`capabilities`, `permissions`, `entrypoints`, `checksum`, `signature`,
`signature_algorithm`, `registry_source`, `sandbox_profile`, `created_at`,
`review_metadata`. Validators check shape + format only —
`validate_plugin_package_without_loading` never loads, imports, unpacks,
executes, fetches, or trusts a package. A perfectly-shaped package is `valid`
but `trusted` / `loadable` / `executable` are **always False**.

## 5. Signature verification

The verifier interface (`SignatureVerificationRequest` / `SignatureVerificationResult`
/ `TrustPolicy`) is implemented. The **production verifier is not authorized**:
`real_verification_enabled` is False, the trusted-publisher set is empty, and no
real trust token is provisioned. Every production-path verification returns
`trusted=False` / `production_approved=False` with reason
`signature_verification_not_authorized`.

A deterministic **fixture verifier** (`fixture-hmac-sha256`, stdlib `hmac` +
`hashlib`) is provided for tests only. It accepts a genuine fixture signature
for the single `fixture` publisher while leaving `production_approved=False`.
It rejects unsigned, forged, marketplace, and unknown-publisher inputs. It is
explicitly `fixture_only` and is **never** the production verifier.

## 6. Permission model

15 permissions (`filesystem.read`, `filesystem.write`, `network.http`,
`network.registry`, `secrets.read`, `provider.read`, `provider.write`,
`ui.render`, `tool.invoke`, `database.read`, `database.write`, `process.spawn`,
`runtime.execute`, `plugin.install`, `marketplace.fetch`). Every one is
`DENIED_BY_DEFAULT` and `grantable=False`. Dangerous permissions are denied
unconditionally. Capabilities (`display.surface`, `read.descriptor`, …) are
non-executable metadata.

## 7. Registry trust policy

`registry_mode = "DISABLED"`, `allow_network = False`,
`marketplace_enabled = False`, `allow_unsigned = False`, signature required,
no trusted publisher. The example URL is `https://registry.example.invalid`
(reserved, never contacted). Every fetch / marketplace request returns a denied
result. The registry client is disabled / allowlisted-off.

## 8. Sandbox broker

The broker interface (`SandboxProfile`, `SandboxLimits`,
`SandboxExecutionRequest`, `SandboxExecutionResult`, `SandboxBrokerStatus`) is
implemented. The broker is disabled; the profile is design-only and never
enforced; every limit is at its most restrictive value (zero / False). No
process is spawned, no shell is opened, no Docker is touched, no plugin is
imported. Every execution request returns a denied result.

## 9. Approval / authorization gate

The gate mirrors the Phase 3E–H `HumanApprovalRecord` fail-closed pattern.
Validity is derived from a token-derived signature that only the real
out-of-band trust token can produce. The dev skeleton provisions **no** token,
so `validate_trust_token` is always False and `is_approval_valid` is always
False — defeating both metadata smuggling and direct dataclass forgery. Fake,
AI-attributed, and metadata approvals are rejected. Production authorization
stays NO-GO.

## 10. Execution policy

`evaluate_target_b_execution_policy` aggregates every layer. Execution is
`allowed` only when **all** of these pass: P0 resolved > 0 AND required gates
resolved, human approval valid, trust token valid, signature verified, registry
trust valid, sandbox broker enabled, route governance authorized, rollback plan
accepted, production safety accepted, kill switch ready. **None** passes today,
so the policy is `allowed=False` / `webui_execute_enabled=False` /
`runtime_route_enabled=False` / `production_runtime_enabled=False`, with a
reason list naming every unresolved precondition.

## 11. Runtime orchestrator

`prepare_plugin_execution` returns a **preview only** (nothing loaded /
imported / executed). `execute_plugin_gated` returns a **denied** result
unconditionally and builds an in-memory denied-execution audit event.
`dry_run_plugin_execution_policy` evaluates without side effects. The future
"all gates pass" execution branch is **explicitly not implemented** — it is a
documented, unreachable placeholder because no real authorization exists.

## 12. WebUI gated flow

The Governance Hub now renders a read-only **Target B Implementation** region
(`GovernanceHubTargetBImplementation.vue`) that projects the frozen gated state:
banner, summary cards, the 12-layer board, the package schema preview, the
signature / permission / registry / sandbox / approval / execution-policy /
audit-rollback panels, the enablement blockers, and the allowed / forbidden
action lists. The only controls are harmless client-only toggles (filter,
inspect, copy, view-section). There is **no** execute / run / approve /
authorize / signoff / resolve / override / rollout control, no API-key input,
no file input, no JSON execution input. No fetch / XHR is made.

## 13. Audit

The audit trail is **in-memory only**: `persisted=False`,
`audit_log_committed=False`. Nothing is written to disk; no JSONL store exists.
Every audit payload is defense-in-depth redacted (secrets / production paths /
fake-authorization markers masked).

## 14. Rollback

The kill switch is `DESIGN_READY_ONLY` — never armed. Production rollback is not
authorized; production rollout stays NO-GO. The production gateway (pid 28428)
is referenced **only** as a do-not-touch string. No signal, no stop, no restart,
no replace, no process control of any kind.

## 15. P0 evidence summary

- Total P0 gates: **24**
- Partial evidence: **19**
- Resolved / approved: **0** (unchanged)
- Pending human review: **5** — `P0-15`, `P0-16`, `P0-18`, `P0-19`, `P0-22`

No P0 gate was resolved by this work. Phase 4B drafts engineering layers; it
does not approve, sign off, or close out any gate.

## 16. Route governance

The frozen baseline is **unchanged**:

- OpenAPI paths = **34**
- Runtime routes = **34**
- Tool GET = **5**
- Tool write HTTP route = **0**
- Tool dry-run route = **1**
- Tool execution route = **1**
- New HTTP route = **0**
- New Tool write route = **0**
- New Provider route = **0**
- New plugin route = **0**
- New runtime route = **0**

The Phase 4B layers are **not imported by `dev_web_api`**; the WebUI reads from
a frozen static frontend manifest. No backend route was added. Verified by
`tests/test_target_b_isolation.py` against `assert_route_governance_unchanged`.

## 17. Production safety

- The production gateway (pid 28428) is **unchanged** — not stopped, restarted,
  replaced, signaled, or modified.
- The Dev Gateway remains stopped.
- The Dashboard is not started.
- Ports 5180 / 5181 remain free.
- No `~/.hermes` access of any kind (not even metadata-only stat / ls / read /
  open / resolve).
- No production `state.db` access.

## 18. Why production still NO-GO

Production authorization requires, at minimum: the five pending P0 gates
resolved via out-of-band human review, a provisioned out-of-band trust token, an
authorized production signature verifier (with a real signing key and a real
trusted-publisher registry), an approved production sandbox / worker lifecycle,
a reviewed registry trust policy with an external-network allowlist, an approved
secret-handling policy, an approved rollback / incident-response plan, and an
explicit route-governance authorization. **None** of these exists. No code or
metadata path in this commit can manufacture any of them.

## 19. Exact enablement blockers

1. Resolve the 24 P0 gates (0 resolved; 5 pending human review).
2. Out-of-band human approval (signed, token-derived).
3. Trust token (provisioned out of band; none today).
4. Production signature verifier (interface scaffolded; not authorized).
5. Sandbox worker lifecycle (interface scaffolded; not approved).
6. Registry trust policy (scaffolded disabled; not reviewed).
7. Network allowlist (none; external network stays denied).
8. Secret handling (no approved policy; no real secret read).
9. Rollback plan (kill switch design-ready only).
10. Incident response (no approved plan).
11. Route authorization (none granted).

## 20. Future authorization requirements

A future Target B enablement would require, verifiably and out of band:

- A real out-of-band trust token provisioned into the skeleton
  (`_REAL_TRUST_TOKEN` is deliberately `None`).
- A real trusted-publisher set populated under a reviewed trust policy
  (`real_trusted_publishers()` is deliberately empty).
- The production signature verifier implemented and authorized
  (`real_verification_enabled` deliberately False).
- An approved production sandbox / worker lifecycle model.
- A reviewed, pinned, signed registry + external-network allowlist.
- An approved rollback / incident-response plan and an armed kill switch.
- Explicit route-governance authorization for any execution / install /
  approval / registry route.
- The five pending P0 gates resolved by human review.

Until every one of those is verifiably present, the execution policy's
`allowed` flag stays False and Target B stays gated. This commit implements the
**path**; it does not open the **gate**.

## 21. Tests

- **Python (11 files, 270 tests):** `tests/test_target_b_plugin_package.py`,
  `tests/test_target_b_signature.py`, `tests/test_target_b_permissions.py`,
  `tests/test_target_b_registry.py`, `tests/test_target_b_sandbox_broker.py`,
  `tests/test_target_b_approval_gate.py`,
  `tests/test_target_b_execution_policy.py`, `tests/test_target_b_runtime.py`,
  `tests/test_target_b_audit.py`, `tests/test_target_b_rollback.py`,
  `tests/test_target_b_isolation.py`. Each layer test asserts behavior,
  forgery resistance, source purity (no forbidden primitives), and no
  production-home / production-`state.db` reference. The isolation test
  asserts no backend route, route-governance unchanged, and the gated report.
- **Frontend (4 files):**
  `phase4b-target-b-implementation-view-model.spec.ts`,
  `phase4b-target-b-implementation-panel.spec.ts`,
  `phase4b-target-b-implementation-no-leak.spec.ts`,
  `phase4b-target-b-implementation-routes.spec.ts`. The no-leak test asserts
  no approval / execution / loading control, no `<input>` / `<textarea>` /
  `<select>`, no fetch / XHR, and no secret / fake-authorization token in the
  DOM or copied summary. Three existing no-leak allow-lists were updated to
  recognize the new harmless layer-filter / copy controls.

## 22. Wording discipline

This document and the code use only allowed wording: "Target B implementation
scaffold complete", "Target B remains gated", "execution policy implemented and
denies", "production runtime remains NO-GO", "WebUI execution remains
disabled", "P0 resolved_count remains 0". The forbidden wording
("Target B complete", "Production runtime GO", "Implementation Authorization
GO", "P0 resolved", "Human review approved", "Registry enabled", "Marketplace
enabled", "WebUI execution enabled") does **not** appear.
