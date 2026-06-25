"""Phase 4C — Target B enablement readiness evaluator (pure stdlib, fail-closed).

Layer 12 of the Phase 4C Target B authorization package — the **aggregator**.
It composes the 11 authorization sub-layers and the P0 gate coverage into a
single, frozen **enablement readiness** verdict.

The four allowed readiness statuses are:

  - ``BLOCKED`` — no real authorization material present (the default);
  - ``AUTHORIZATION_PACKAGE_INCOMPLETE`` — some material present, but not all;
  - ``AUTHORIZATION_READY_BUT_NOT_ENABLED`` — a complete (fixture) package is
    present, but production is not enabled (test-only);
  - ``ENABLEMENT_ALLOWED_BY_POLICY`` — a complete REAL package AND production
    mode explicitly authorized (never in the dev skeleton).

The evaluator is **fail-closed**:

  - the default verdict is ``BLOCKED`` (no real approval / trust token exists);
  - a complete set of *fixture* inputs may reach ``AUTHORIZATION_READY_BUT_NOT_ENABLED``
    in test-only mode, but ``production_enablement_allowed`` stays False;
  - ``ENABLEMENT_ALLOWED_BY_POLICY`` requires ``production_mode=True`` AND a
    non-fixture complete package — the dev skeleton never sets production mode;
  - even ``AUTHORIZATION_READY_BUT_NOT_ENABLED`` does NOT start the production
    runtime.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no eval / exec, no production access.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hermes_cli.dev_web_target_b_authorization_common import (
    READINESS_AUTHORIZED_NOT_ENABLED,
    READINESS_BLOCKED,
    READINESS_ENABLEMENT_ALLOWED,
    READINESS_PACKAGE_INCOMPLETE,
    TARGET_B_AUTHORIZATION_NO_GO,
    TARGET_B_AUTHORIZATION_VERSION,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
)
from hermes_cli.dev_web_target_b_common import (
    TARGET_B_PENDING_HUMAN_REVIEW_GATES,
    TARGET_B_P0_PARTIAL_EVIDENCE,
    TARGET_B_P0_PENDING_HUMAN_REVIEW,
    TARGET_B_P0_RESOLVED,
    TARGET_B_P0_TOTAL,
    TARGET_B_ROUTE_GOVERNANCE_BASELINE,
)
from hermes_cli.dev_web_target_b_human_approval import build_human_approval_report
from hermes_cli.dev_web_target_b_incident_rollback import build_incident_rollback_report
from hermes_cli.dev_web_target_b_network_policy import build_network_policy_report
from hermes_cli.dev_web_target_b_p0_gate_resolution import build_p0_gate_coverage_report
from hermes_cli.dev_web_target_b_production_signature import (
    build_production_signature_report,
)
from hermes_cli.dev_web_target_b_registry_policy import build_registry_authorization_report
from hermes_cli.dev_web_target_b_route_authorization import build_route_authorization_report
from hermes_cli.dev_web_target_b_sandbox_lifecycle import build_sandbox_lifecycle_report
from hermes_cli.dev_web_target_b_secret_policy import build_secret_policy_report
from hermes_cli.dev_web_target_b_trust_token import build_trust_token_report
from hermes_cli.dev_web_target_b_trusted_publishers import build_trusted_publisher_report

# ---------------------------------------------------------------------------
# 1. The enablement readiness input (frozen dataclass)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EnablementReadinessInput:
    """The inputs to a Target B enablement readiness evaluation.

    Every authorization sub-layer defaults to "not authorized". A complete,
    non-fixture, production-mode package is required for enablement — which the
    dev skeleton never provides.
    """

    human_approval_valid: bool = False
    trust_token_valid: bool = False
    trusted_publishers_present: bool = False
    production_signature_verifier_authorized: bool = False
    sandbox_lifecycle_approved: bool = False
    registry_trust_policy_approved: bool = False
    network_allowlist_approved: bool = False
    secret_policy_approved: bool = False
    incident_rollback_plan_approved: bool = False
    route_authorization_approved: bool = False
    p0_gates_resolved: bool = False
    production_mode: bool = False
    fixture_only: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "humanApprovalValid": self.human_approval_valid,
                "trustTokenValid": self.trust_token_valid,
                "trustedPublishersPresent": self.trusted_publishers_present,
                "productionSignatureVerifierAuthorized": self.production_signature_verifier_authorized,
                "sandboxLifecycleApproved": self.sandbox_lifecycle_approved,
                "registryTrustPolicyApproved": self.registry_trust_policy_approved,
                "networkAllowlistApproved": self.network_allowlist_approved,
                "secretPolicyApproved": self.secret_policy_approved,
                "incidentRollbackPlanApproved": self.incident_rollback_plan_approved,
                "routeAuthorizationApproved": self.route_authorization_approved,
                "p0GatesResolved": self.p0_gates_resolved,
                "productionMode": self.production_mode,
                "fixtureOnly": self.fixture_only,
            }
        )

    def all_gates_pass(self) -> bool:
        """True iff every one of the 11 authorization sub-layers passes."""
        return (
            self.human_approval_valid
            and self.trust_token_valid
            and self.trusted_publishers_present
            and self.production_signature_verifier_authorized
            and self.sandbox_lifecycle_approved
            and self.registry_trust_policy_approved
            and self.network_allowlist_approved
            and self.secret_policy_approved
            and self.incident_rollback_plan_approved
            and self.route_authorization_approved
            and self.p0_gates_resolved
        )

    def any_supplied(self) -> bool:
        """True iff any sub-layer is supplied / production mode / fixture mode."""
        return (
            self.human_approval_valid
            or self.trust_token_valid
            or self.trusted_publishers_present
            or self.production_signature_verifier_authorized
            or self.sandbox_lifecycle_approved
            or self.registry_trust_policy_approved
            or self.network_allowlist_approved
            or self.secret_policy_approved
            or self.incident_rollback_plan_approved
            or self.route_authorization_approved
            or self.p0_gates_resolved
            or self.production_mode
            or self.fixture_only
        )


# ---------------------------------------------------------------------------
# 2. The enablement readiness result (frozen dataclass)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EnablementReadinessResult:
    """The frozen Target B enablement readiness verdict. Defaults to BLOCKED."""

    readiness_status: str
    production_enablement_allowed: bool
    all_gates_pass: bool
    fixture_only: bool
    production_mode: bool
    blockers: tuple[str, ...]
    ignored_metadata_keys: tuple[str, ...]
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "readinessStatus": self.readiness_status,
                "productionEnablementAllowed": self.production_enablement_allowed,
                "allGatesPass": self.all_gates_pass,
                "fixtureOnly": self.fixture_only,
                "productionMode": self.production_mode,
                "blockers": list(self.blockers),
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
                "reason": self.reason,
            }
        )


@dataclass(frozen=True, slots=True)
class TargetBAuthorizationPackageReport:
    """The frozen aggregate Target B authorization package report.

    Every authorization verdict is NO-GO / BLOCKED; the readiness status is
    BLOCKED; production enablement is not allowed; P0 resolved stays 0; the trust
    token stays not provisioned; the route baseline is unchanged; no backend
    route is added.
    """

    schema_version: str
    authorization_status: str
    readiness_status: str
    production_enablement_allowed: bool
    production_runtime: str
    registry: str
    marketplace: str
    webui_execution: str
    approval_authorization: str
    production_rollout: str
    trust_token_provisioned: bool
    p0_total: int
    p0_resolved: int
    p0_partial_evidence: int
    p0_pending_human_review: int
    pending_human_review_gates: tuple[str, ...]
    route_governance_baseline: str
    backend_routes_changed: bool
    blockers: tuple[str, ...]
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "schemaVersion": self.schema_version,
                "authorizationStatus": self.authorization_status,
                "readinessStatus": self.readiness_status,
                "productionEnablementAllowed": self.production_enablement_allowed,
                "productionRuntime": self.production_runtime,
                "registry": self.registry,
                "marketplace": self.marketplace,
                "webuiExecution": self.webui_execution,
                "approvalAuthorization": self.approval_authorization,
                "productionRollout": self.production_rollout,
                "trustTokenProvisioned": self.trust_token_provisioned,
                "p0Total": self.p0_total,
                "p0Resolved": self.p0_resolved,
                "p0PartialEvidence": self.p0_partial_evidence,
                "p0PendingHumanReview": self.p0_pending_human_review,
                "pendingHumanReviewGates": list(self.pending_human_review_gates),
                "routeGovernanceBaseline": self.route_governance_baseline,
                "backendRoutesChanged": self.backend_routes_changed,
                "blockers": list(self.blockers),
                "reason": self.reason,
            }
        )


# ---------------------------------------------------------------------------
# 3. Evaluation
# ---------------------------------------------------------------------------


def _blockers_for(inputs: EnablementReadinessInput) -> tuple[str, ...]:
    """Return the human-readable blockers for the missing sub-layers."""
    blockers: list[str] = []
    if not inputs.human_approval_valid:
        blockers.append("human_approval_missing")
    if not inputs.trust_token_valid:
        blockers.append("trust_token_not_provisioned")
    if not inputs.trusted_publishers_present:
        blockers.append("trusted_publisher_set_empty")
    if not inputs.production_signature_verifier_authorized:
        blockers.append("production_signature_verifier_not_authorized")
    if not inputs.sandbox_lifecycle_approved:
        blockers.append("sandbox_lifecycle_not_approved")
    if not inputs.registry_trust_policy_approved:
        blockers.append("registry_trust_policy_not_approved")
    if not inputs.network_allowlist_approved:
        blockers.append("network_allowlist_not_approved")
    if not inputs.secret_policy_approved:
        blockers.append("secret_policy_default_deny")
    if not inputs.incident_rollback_plan_approved:
        blockers.append("incident_rollback_plan_not_approved")
    if not inputs.route_authorization_approved:
        blockers.append("route_authorization_not_approved")
    if not inputs.p0_gates_resolved:
        blockers.append("p0_gates_not_resolved")
    return tuple(blockers)


def evaluate_target_b_enablement_readiness(
    inputs: Any = None,
    untrusted_metadata: Any = None,
) -> EnablementReadinessResult:
    """Evaluate Target B enablement readiness. Defaults to BLOCKED.

    The default verdict (no inputs) is ``BLOCKED`` because no real approval or
    trust token exists. A complete set of *fixture* inputs may reach
    ``AUTHORIZATION_READY_BUT_NOT_ENABLED`` (test-only), but
    ``production_enablement_allowed`` stays False. ``ENABLEMENT_ALLOWED_BY_POLICY``
    requires ``production_mode=True`` AND a non-fixture complete package — which
    the dev skeleton never provides. Even ``AUTHORIZATION_READY_BUT_NOT_ENABLED``
    does NOT start the production runtime.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    active = inputs if isinstance(inputs, EnablementReadinessInput) else EnablementReadinessInput()

    all_pass = active.all_gates_pass()
    any_supplied = active.any_supplied()
    blockers = _blockers_for(active)

    # Production enablement requires a complete, NON-fixture package AND
    # production mode explicitly authorized.
    production_enablement_allowed = bool(
        all_pass and active.production_mode and not active.fixture_only
    )

    if production_enablement_allowed:
        readiness_status = READINESS_ENABLEMENT_ALLOWED
        reason = "enablement_allowed_by_policy"
    elif all_pass and not active.fixture_only and active.production_mode is False:
        # A complete real package without production mode — not reachable in the
        # dev skeleton, but documented for completeness.
        readiness_status = READINESS_AUTHORIZED_NOT_ENABLED
        reason = "authorization_ready_but_not_enabled"
    elif all_pass and active.fixture_only:
        # A complete fixture package (test-only) — never production-enabled.
        readiness_status = READINESS_AUTHORIZED_NOT_ENABLED
        reason = "fixture_authorization_ready_but_not_enabled"
    elif any_supplied:
        readiness_status = READINESS_PACKAGE_INCOMPLETE
        reason = "authorization_package_incomplete"
    else:
        readiness_status = READINESS_BLOCKED
        reason = "no_real_authorization_material"

    return EnablementReadinessResult(
        readiness_status=readiness_status,
        production_enablement_allowed=production_enablement_allowed,
        all_gates_pass=all_pass,
        fixture_only=active.fixture_only,
        production_mode=active.production_mode,
        blockers=blockers,
        ignored_metadata_keys=ignored,
        reason=reason,
    )


def build_target_b_authorization_package_report() -> TargetBAuthorizationPackageReport:
    """Build the frozen aggregate Target B authorization package report.

    The readiness status is BLOCKED; production enablement is not allowed; every
    authorization verdict is NO-GO; the trust token is not provisioned; P0
    resolved stays 0; the route baseline is unchanged; no backend route is
    added. Pure and deterministic.
    """
    result = evaluate_target_b_enablement_readiness()
    return TargetBAuthorizationPackageReport(
        schema_version=TARGET_B_AUTHORIZATION_VERSION,
        authorization_status="AUTHORIZATION_PACKAGE_IMPLEMENTED",
        readiness_status=result.readiness_status,
        production_enablement_allowed=result.production_enablement_allowed,
        production_runtime=TARGET_B_AUTHORIZATION_NO_GO,
        registry=TARGET_B_AUTHORIZATION_NO_GO,
        marketplace=TARGET_B_AUTHORIZATION_NO_GO,
        webui_execution=TARGET_B_AUTHORIZATION_NO_GO,
        approval_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        production_rollout=TARGET_B_AUTHORIZATION_NO_GO,
        trust_token_provisioned=False,
        p0_total=TARGET_B_P0_TOTAL,
        p0_resolved=TARGET_B_P0_RESOLVED,
        p0_partial_evidence=TARGET_B_P0_PARTIAL_EVIDENCE,
        p0_pending_human_review=TARGET_B_P0_PENDING_HUMAN_REVIEW,
        pending_human_review_gates=TARGET_B_PENDING_HUMAN_REVIEW_GATES,
        route_governance_baseline=TARGET_B_ROUTE_GOVERNANCE_BASELINE,
        backend_routes_changed=False,
        blockers=result.blockers,
        reason=result.reason,
    )


def assert_target_b_not_enabled_without_full_authorization() -> None:
    """Re-affirm Target B is not enabled without full authorization. Pure."""
    # Default evaluation is BLOCKED.
    default = evaluate_target_b_enablement_readiness()
    assert default.readiness_status == READINESS_BLOCKED
    assert default.production_enablement_allowed is False
    assert default.all_gates_pass is False
    assert len(default.blockers) == 11

    # A complete FIXTURE package is "ready but not enabled" — never production.
    fixture_inputs = EnablementReadinessInput(
        human_approval_valid=True,
        trust_token_valid=True,
        trusted_publishers_present=True,
        production_signature_verifier_authorized=True,
        sandbox_lifecycle_approved=True,
        registry_trust_policy_approved=True,
        network_allowlist_approved=True,
        secret_policy_approved=True,
        incident_rollback_plan_approved=True,
        route_authorization_approved=True,
        p0_gates_resolved=True,
        production_mode=False,
        fixture_only=True,
    )
    fixture_result = evaluate_target_b_enablement_readiness(fixture_inputs)
    assert fixture_result.readiness_status == READINESS_AUTHORIZED_NOT_ENABLED
    assert fixture_result.production_enablement_allowed is False
    assert fixture_result.all_gates_pass is True
    assert fixture_result.fixture_only is True

    # Even a complete fixture package WITH production_mode cannot enable — it is
    # fixture-only.
    fixture_prod = EnablementReadinessInput(
        human_approval_valid=True,
        trust_token_valid=True,
        trusted_publishers_present=True,
        production_signature_verifier_authorized=True,
        sandbox_lifecycle_approved=True,
        registry_trust_policy_approved=True,
        network_allowlist_approved=True,
        secret_policy_approved=True,
        incident_rollback_plan_approved=True,
        route_authorization_approved=True,
        p0_gates_resolved=True,
        production_mode=True,
        fixture_only=True,
    )
    fixture_prod_result = evaluate_target_b_enablement_readiness(fixture_prod)
    assert fixture_prod_result.production_enablement_allowed is False

    # The aggregate report stays gated.
    report = build_target_b_authorization_package_report()
    assert report.readiness_status == READINESS_BLOCKED
    assert report.production_enablement_allowed is False
    for verdict in (
        report.production_runtime,
        report.registry,
        report.marketplace,
        report.webui_execution,
        report.approval_authorization,
        report.production_rollout,
    ):
        assert verdict == TARGET_B_AUTHORIZATION_NO_GO
    assert report.trust_token_provisioned is False
    assert report.p0_resolved == 0
    assert report.backend_routes_changed is False
    assert report.route_governance_baseline == "34/34/5/0/1/1"


__all__ = [
    # schema
    "EnablementReadinessInput",
    "EnablementReadinessResult",
    "TargetBAuthorizationPackageReport",
    # evaluation
    "evaluate_target_b_enablement_readiness",
    "build_target_b_authorization_package_report",
    # boundary
    "assert_target_b_not_enabled_without_full_authorization",
]
