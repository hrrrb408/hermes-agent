"""Phase 4B — Target B end-to-end readiness report (pure stdlib, fail-closed).

Layer 11 of the Phase 4B Target B engineering path. Aggregates every layer
into a single, frozen, **gated** readiness report that the WebUI mirrors via a
static frontend manifest.

The report is the **gated engineering contract**: every layer is present, every
capability is disabled, every authorization verdict is NO-GO, P0 resolved stays
0, the route baseline is unchanged, and no backend route is added. It is **not**
an authorization, not an approval, not a signoff, not a closeout, and not
production authorization.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no real secret read, no production access.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hermes_cli.dev_web_target_b_approval import build_authorization_decision
from hermes_cli.dev_web_target_b_audit import build_audit_trail_report
from hermes_cli.dev_web_target_b_common import (
    TARGET_B_IMPLEMENTATION_STATUS,
    TARGET_B_IMPLEMENTATION_VERSION,
    TARGET_B_NO_GO,
    TARGET_B_P0_PARTIAL_EVIDENCE,
    TARGET_B_P0_PENDING_HUMAN_REVIEW,
    TARGET_B_P0_RESOLVED,
    TARGET_B_P0_TOTAL,
    TARGET_B_PENDING_HUMAN_REVIEW_GATES,
    TARGET_B_ROUTE_GOVERNANCE_BASELINE,
    redact_target_b_payload,
)
from hermes_cli.dev_web_target_b_execution_policy import build_execution_policy_report
from hermes_cli.dev_web_target_b_package import build_example_package_descriptor
from hermes_cli.dev_web_target_b_permissions import (
    CAPABILITY_MODEL,
    PERMISSION_MODEL,
    build_permission_model_report,
)
from hermes_cli.dev_web_target_b_registry import build_registry_readiness_report
from hermes_cli.dev_web_target_b_rollback import build_rollback_report
from hermes_cli.dev_web_target_b_runtime import build_runtime_readiness_report
from hermes_cli.dev_web_target_b_sandbox import build_sandbox_broker_report
from hermes_cli.dev_web_target_b_signature import build_signature_verification_report

# ---------------------------------------------------------------------------
# 1. Frozen layer-status board (12 implemented / scaffolded-disabled layers)
# ---------------------------------------------------------------------------

#: One Target B implementation layer: ``(key, layer, status, risk, gate)``.
#: Every layer is present (scaffolded / designed) but disabled.
_LAYERS_RAW: tuple[tuple[str, str, str, str, str], ...] = (
    ("common", "Shared Common Helpers", "SCAFFOLDED_DISABLED", "medium", "n/a (pure helpers)"),
    ("package", "Signed Plugin Package Schema", "SCAFFOLDED_DISABLED", "high", "supply-chain policy (P0-05)"),
    ("signature", "Plugin Signature Verification", "SCAFFOLDED_DISABLED", "critical", "signature verification + trust policy"),
    ("permissions", "Permission / Capability Model", "SCAFFOLDED_DISABLED", "high", "permission model approval (P0-06)"),
    ("registry", "Registry Trust Policy", "SCAFFOLDED_DISABLED", "critical", "registry trust policy + network review"),
    ("sandbox", "Sandbox Broker", "SCAFFOLDED_DISABLED", "critical", "approved sandbox / worker lifecycle (P0-19)"),
    ("approval", "Approval / Authorization Gate", "SCAFFOLDED_DISABLED", "critical", "implementation authorization (P0-15 / P0-22)"),
    ("executionPolicy", "Execution Policy Gate", "SCAFFOLDED_DISABLED", "critical", "all gates + route authorization"),
    ("runtime", "Runtime Orchestrator", "SCAFFOLDED_DISABLED", "critical", "all gates + runtime authorization"),
    ("audit", "Audit Trail", "SCAFFOLDED_DISABLED", "medium", "audit / redaction model (P0-07)"),
    ("rollback", "Rollback / Kill Switch", "DESIGNED", "high", "rollback / incident plan (P0-21 / P0-23)"),
    ("report", "End-to-End Readiness Report", "SCAFFOLDED_DISABLED", "medium", "n/a (aggregate projection)"),
)


@dataclass(frozen=True, slots=True)
class ImplementationLayer:
    """One Target B implementation layer — present but disabled."""

    key: str
    layer: str
    status: str
    enabled: bool
    execution_capable: bool
    network_capable: bool
    production_capable: bool
    risk_level: str
    required_gate: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "key": self.key,
                "layer": self.layer,
                "status": self.status,
                "enabled": self.enabled,
                "executionCapable": self.execution_capable,
                "networkCapable": self.network_capable,
                "productionCapable": self.production_capable,
                "riskLevel": self.risk_level,
                "requiredGate": self.required_gate,
            }
        )


def _build_layers() -> tuple[ImplementationLayer, ...]:
    return tuple(
        ImplementationLayer(
            key=str(row[0]),
            layer=str(row[1]),
            status=str(row[2]),
            enabled=False,
            execution_capable=False,
            network_capable=False,
            production_capable=False,
            risk_level=str(row[3]),
            required_gate=str(row[4]),
        )
        for row in _LAYERS_RAW
    )


#: The frozen implementation layer board. Immutable; every layer disabled.
IMPLEMENTATION_LAYERS: tuple[ImplementationLayer, ...] = _build_layers()

assert len(IMPLEMENTATION_LAYERS) == 12
assert all(
    not layer.enabled
    and not layer.execution_capable
    and not layer.network_capable
    and not layer.production_capable
    for layer in IMPLEMENTATION_LAYERS
)


# ---------------------------------------------------------------------------
# 2. The aggregate gated readiness report
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TargetBImplementationReport:
    """The frozen, gated Target B end-to-end implementation report.

    Every authorization verdict is NO-GO; execution is DISABLED; production
    authorization is NO-GO; ``p0_resolved`` is 0; the route baseline is
    unchanged; and every layer / capability is disabled. No field implies
    enablement.
    """

    schema_version: str
    implementation_status: str
    execution_status: str
    production_runtime: str
    arbitrary_plugin_loading: str
    remote_registry: str
    marketplace: str
    webui_execution: str
    approval_authorization: str
    production_rollout: str
    p0_total: int
    p0_resolved: int
    p0_partial_evidence: int
    p0_pending_human_review: int
    pending_human_review_gates: tuple[str, ...]
    route_governance_baseline: str
    backend_routes_changed: bool
    implementation_layers: tuple[ImplementationLayer, ...]
    permission_model_size: int
    capability_model_size: int
    package_schema: Any
    signature_report: Any
    registry_report: Any
    sandbox_report: Any
    approval_decision: Any
    execution_policy_report: Any
    runtime_report: Any
    audit_report: Any
    rollback_report: Any

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "schemaVersion": self.schema_version,
                "implementationStatus": self.implementation_status,
                "executionStatus": self.execution_status,
                "productionRuntime": self.production_runtime,
                "arbitraryPluginLoading": self.arbitrary_plugin_loading,
                "remoteRegistry": self.remote_registry,
                "marketplace": self.marketplace,
                "webuiExecution": self.webui_execution,
                "approvalAuthorization": self.approval_authorization,
                "productionRollout": self.production_rollout,
                "p0Total": self.p0_total,
                "p0Resolved": self.p0_resolved,
                "p0PartialEvidence": self.p0_partial_evidence,
                "p0PendingHumanReview": self.p0_pending_human_review,
                "pendingHumanReviewGates": list(self.pending_human_review_gates),
                "routeGovernanceBaseline": self.route_governance_baseline,
                "backendRoutesChanged": self.backend_routes_changed,
                "implementationLayers": [l.to_safe_dict() for l in self.implementation_layers],
                "permissionModelSize": self.permission_model_size,
                "capabilityModelSize": self.capability_model_size,
                "packageSchema": self.package_schema.to_safe_dict(),
                "signatureReport": self.signature_report.to_safe_dict(),
                "registryReport": self.registry_report.to_safe_dict(),
                "sandboxReport": self.sandbox_report.to_safe_dict(),
                "approvalDecision": self.approval_decision.to_safe_dict(),
                "executionPolicyReport": self.execution_policy_report.to_safe_dict(),
                "runtimeReport": self.runtime_report.to_safe_dict(),
                "auditReport": self.audit_report.to_safe_dict(),
                "rollbackReport": self.rollback_report.to_safe_dict(),
            }
        )


def build_target_b_implementation_report() -> TargetBImplementationReport:
    """Build the frozen, gated Target B end-to-end implementation report.

    Pure and deterministic — no time, no random, no network, no file, no
    production access. Every authorization verdict is NO-GO; execution is
    DISABLED; ``p0_resolved`` is 0; the route baseline is unchanged; and every
    layer / capability is disabled.
    """
    return TargetBImplementationReport(
        schema_version=TARGET_B_IMPLEMENTATION_VERSION,
        implementation_status=TARGET_B_IMPLEMENTATION_STATUS,
        execution_status="DISABLED",
        production_runtime=TARGET_B_NO_GO,
        arbitrary_plugin_loading=TARGET_B_NO_GO,
        remote_registry=TARGET_B_NO_GO,
        marketplace=TARGET_B_NO_GO,
        webui_execution=TARGET_B_NO_GO,
        approval_authorization=TARGET_B_NO_GO,
        production_rollout=TARGET_B_NO_GO,
        p0_total=TARGET_B_P0_TOTAL,
        p0_resolved=TARGET_B_P0_RESOLVED,
        p0_partial_evidence=TARGET_B_P0_PARTIAL_EVIDENCE,
        p0_pending_human_review=TARGET_B_P0_PENDING_HUMAN_REVIEW,
        pending_human_review_gates=TARGET_B_PENDING_HUMAN_REVIEW_GATES,
        route_governance_baseline=TARGET_B_ROUTE_GOVERNANCE_BASELINE,
        backend_routes_changed=False,
        implementation_layers=IMPLEMENTATION_LAYERS,
        permission_model_size=len(PERMISSION_MODEL),
        capability_model_size=len(CAPABILITY_MODEL),
        package_schema=build_example_package_descriptor(),
        signature_report=build_signature_verification_report(),
        registry_report=build_registry_readiness_report(),
        sandbox_report=build_sandbox_broker_report(),
        approval_decision=build_authorization_decision(),
        execution_policy_report=build_execution_policy_report(),
        runtime_report=build_runtime_readiness_report(),
        audit_report=build_audit_trail_report(),
        rollback_report=build_rollback_report(),
    )


def assert_target_b_implementation_gated() -> None:
    """Re-affirm the gated implementation invariants. Pure."""
    report = build_target_b_implementation_report()
    assert report.implementation_status == TARGET_B_IMPLEMENTATION_STATUS
    assert report.execution_status == "DISABLED"
    for verdict in (
        report.production_runtime,
        report.arbitrary_plugin_loading,
        report.remote_registry,
        report.marketplace,
        report.webui_execution,
        report.approval_authorization,
        report.production_rollout,
    ):
        assert verdict == TARGET_B_NO_GO
    assert report.p0_total == TARGET_B_P0_TOTAL
    assert report.p0_resolved == 0
    assert report.p0_partial_evidence == TARGET_B_P0_PARTIAL_EVIDENCE
    assert report.p0_pending_human_review == TARGET_B_P0_PENDING_HUMAN_REVIEW
    assert set(report.pending_human_review_gates) == set(TARGET_B_PENDING_HUMAN_REVIEW_GATES)
    assert report.route_governance_baseline == TARGET_B_ROUTE_GOVERNANCE_BASELINE
    assert report.backend_routes_changed is False
    assert len(report.implementation_layers) == 12
    for layer in report.implementation_layers:
        assert layer.enabled is False
        assert layer.execution_capable is False
        assert layer.network_capable is False
        assert layer.production_capable is False
    # The report never states a positive authorization marker.
    text = str(report.to_safe_dict()).lower()
    for marker in (
        "production_runtime_go=true",
        "target_b_authorized=true",
        "implementation_authorization=go",
        "production rollout approved",
        "approved_by_ai=true",
    ):
        assert marker not in text


__all__ = [
    "ImplementationLayer",
    "IMPLEMENTATION_LAYERS",
    "TargetBImplementationReport",
    "build_target_b_implementation_report",
    "assert_target_b_implementation_gated",
]
