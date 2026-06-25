"""Phase 4B — Target B execution policy gate (pure stdlib, fail-closed).

Layer 8 of the Phase 4B Target B engineering path. Defines the **unified
execution policy** that aggregates every other layer into a single
``allowed`` verdict.

Execution is **allowed only when every gate passes**:

  1. P0 ``resolved_count > 0`` AND every required human-review gate resolved;
  2. human approval valid;
  3. trust token valid;
  4. signature verified (production verifier authorized);
  5. registry trust policy valid;
  6. sandbox broker enabled;
  7. route governance authorized;
  8. rollback plan accepted;
  9. production safety accepted;
  10. kill switch ready.

In the dev skeleton **none** of these passes, so the policy is always
``allowed=False`` / ``webui_execute_enabled=False`` / ``runtime_route_enabled=
False`` / ``production_runtime_enabled=False``. The reason list names every
unresolved precondition.

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
from hermes_cli.dev_web_target_b_common import (
    TARGET_B_DISABLED_REASON,
    TARGET_B_NO_GO,
    TARGET_B_P0_PENDING_HUMAN_REVIEW,
    TARGET_B_P0_RESOLVED,
    TARGET_B_PENDING_HUMAN_REVIEW_GATES,
    TARGET_B_ROUTE_GOVERNANCE_BASELINE,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
)
from hermes_cli.dev_web_target_b_registry import build_registry_readiness_report
from hermes_cli.dev_web_target_b_rollback import build_rollback_report
from hermes_cli.dev_web_target_b_sandbox import build_sandbox_broker_report
from hermes_cli.dev_web_target_b_signature import build_signature_verification_report

# ---------------------------------------------------------------------------
# 1. Frozen gate-condition inputs (every one False / unresolved today)
# ---------------------------------------------------------------------------

#: The frozen set of gate conditions. Every one is False in the dev skeleton.
#: These are the *only* inputs the policy reads; none can be flipped by request
#: metadata.
@dataclass(frozen=True, slots=True)
class ExecutionGateInputs:
    """The frozen inputs the execution policy evaluates. All unresolved today."""

    p0_resolved_count: int
    required_gates_resolved: bool
    human_approval_valid: bool
    trust_token_valid: bool
    signature_verified: bool
    registry_trust_valid: bool
    sandbox_broker_enabled: bool
    route_governance_authorized: bool
    rollback_plan_accepted: bool
    production_safety_accepted: bool
    kill_switch_ready: bool


def build_execution_gate_inputs() -> ExecutionGateInputs:
    """Build the frozen execution gate inputs. Every one unresolved."""
    return ExecutionGateInputs(
        p0_resolved_count=TARGET_B_P0_RESOLVED,
        required_gates_resolved=False,
        human_approval_valid=False,
        trust_token_valid=False,
        signature_verified=False,
        registry_trust_valid=False,
        sandbox_broker_enabled=False,
        route_governance_authorized=False,
        rollback_plan_accepted=False,
        production_safety_accepted=False,
        kill_switch_ready=False,
    )


# ---------------------------------------------------------------------------
# 2. The execution policy verdict
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExecutionPolicyReport:
    """The frozen execution-policy verdict. Always denied in the dev skeleton."""

    allowed: bool
    can_execute_plugin: bool
    can_load_plugin_package: bool
    can_fetch_registry: bool
    can_render_webui_execute_control: bool
    webui_execute_enabled: bool
    runtime_route_enabled: bool
    production_runtime_enabled: bool
    production_authorization: str
    p0_resolved_count: int
    route_governance_baseline: str
    reasons: tuple[str, ...]
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "allowed": self.allowed,
                "canExecutePlugin": self.can_execute_plugin,
                "canLoadPluginPackage": self.can_load_plugin_package,
                "canFetchRegistry": self.can_fetch_registry,
                "canRenderWebuiExecuteControl": self.can_render_webui_execute_control,
                "webuiExecuteEnabled": self.webui_execute_enabled,
                "runtimeRouteEnabled": self.runtime_route_enabled,
                "productionRuntimeEnabled": self.production_runtime_enabled,
                "productionAuthorization": self.production_authorization,
                "p0ResolvedCount": self.p0_resolved_count,
                "routeGovernanceBaseline": self.route_governance_baseline,
                "reasons": list(self.reasons),
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


def _collect_blocker_reasons(inputs: ExecutionGateInputs) -> tuple[str, ...]:
    reasons: list[str] = []
    if inputs.p0_resolved_count <= 0:
        reasons.append("p0_resolved_count_is_zero")
    if not inputs.required_gates_resolved:
        reasons.append(
            f"required_gates_unresolved:{'|'.join(TARGET_B_PENDING_HUMAN_REVIEW_GATES)}"
        )
    if not inputs.human_approval_valid:
        reasons.append("human_approval_missing")
    if not inputs.trust_token_valid:
        reasons.append("trust_token_missing")
    if not inputs.signature_verified:
        reasons.append("signature_not_verified")
    if not inputs.registry_trust_valid:
        reasons.append("registry_trust_policy_not_valid")
    if not inputs.sandbox_broker_enabled:
        reasons.append("sandbox_broker_not_enabled")
    if not inputs.route_governance_authorized:
        reasons.append("route_governance_not_authorized")
    if not inputs.rollback_plan_accepted:
        reasons.append("rollback_plan_not_accepted")
    if not inputs.production_safety_accepted:
        reasons.append("production_safety_not_accepted")
    if not inputs.kill_switch_ready:
        reasons.append("kill_switch_not_ready")
    return tuple(reasons)


def evaluate_target_b_execution_policy(
    inputs: ExecutionGateInputs | None = None,
    untrusted_metadata: Any = None,
) -> ExecutionPolicyReport:
    """Evaluate the unified Target B execution policy. Always denied today.

    *inputs* defaults to the frozen unresolved set. *untrusted_metadata* is
    inspected only to report ignored bypass keys. The verdict is
    ``allowed=False`` unless **every** gate condition is True — which the dev
    skeleton guarantees is never the case.
    """
    active = inputs if inputs is not None else build_execution_gate_inputs()
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    all_pass = (
        active.p0_resolved_count > 0
        and active.required_gates_resolved
        and active.human_approval_valid
        and active.trust_token_valid
        and active.signature_verified
        and active.registry_trust_valid
        and active.sandbox_broker_enabled
        and active.route_governance_authorized
        and active.rollback_plan_accepted
        and active.production_safety_accepted
        and active.kill_switch_ready
    )
    reasons = _collect_blocker_reasons(active) if not all_pass else ()
    return ExecutionPolicyReport(
        allowed=all_pass,
        can_execute_plugin=all_pass,
        can_load_plugin_package=False,  # loading is never authorized
        can_fetch_registry=False,  # registry fetch is never authorized
        can_render_webui_execute_control=False,  # no active execute control
        webui_execute_enabled=False,
        runtime_route_enabled=False,
        production_runtime_enabled=False,
        production_authorization=TARGET_B_NO_GO,
        p0_resolved_count=active.p0_resolved_count,
        route_governance_baseline=TARGET_B_ROUTE_GOVERNANCE_BASELINE,
        reasons=reasons,
        ignored_metadata_keys=ignored,
    )


# ---------------------------------------------------------------------------
# 3. Per-capability policy predicates (deny by default)
# ---------------------------------------------------------------------------


def can_execute_plugin(untrusted_metadata: Any = None) -> bool:
    """True iff plugin execution is authorized. Always False today."""
    return evaluate_target_b_execution_policy(untrusted_metadata=untrusted_metadata).allowed


def can_load_plugin_package(untrusted_metadata: Any = None) -> bool:
    """True iff a plugin package may be loaded. Always False today."""
    # Touch the metadata detector so a smuggler's keys are observed even though
    # the answer is unchanged.
    detect_target_b_untrusted_metadata(untrusted_metadata)
    return False


def can_fetch_registry(untrusted_metadata: Any = None) -> bool:
    """True iff the registry may be fetched. Always False today."""
    detect_target_b_untrusted_metadata(untrusted_metadata)
    return False


def can_render_webui_execute_control(untrusted_metadata: Any = None) -> bool:
    """True iff the WebUI may render an ACTIVE execute control. Always False.

    The WebUI may *render a disabled preview* of the execution flow; it may
    never render an active, clickable execute control.
    """
    detect_target_b_untrusted_metadata(untrusted_metadata)
    return False


def build_execution_policy_report() -> ExecutionPolicyReport:
    """Build the frozen aggregate execution-policy report. Denied."""
    report = evaluate_target_b_execution_policy()
    assert report.allowed is False
    return report


def assert_execution_policy_layer_disabled() -> None:
    """Re-affirm the execution-policy layer disabled invariants. Pure."""
    report = build_execution_policy_report()
    assert report.allowed is False
    assert report.can_execute_plugin is False
    assert report.can_load_plugin_package is False
    assert report.can_fetch_registry is False
    assert report.can_render_webui_execute_control is False
    assert report.webui_execute_enabled is False
    assert report.runtime_route_enabled is False
    assert report.production_runtime_enabled is False
    assert report.production_authorization == TARGET_B_NO_GO
    assert report.p0_resolved_count == 0
    # Cross-layer: the other layers are disabled too.
    assert build_authorization_decision().production_authorization == TARGET_B_NO_GO
    assert build_signature_verification_report().production_approved is False
    assert build_sandbox_broker_report().broker_enabled is False
    assert build_registry_readiness_report().network_enabled is False
    assert build_rollback_report().production_rollout == TARGET_B_NO_GO


__all__ = [
    # inputs
    "ExecutionGateInputs",
    "build_execution_gate_inputs",
    # report
    "ExecutionPolicyReport",
    "evaluate_target_b_execution_policy",
    "build_execution_policy_report",
    # predicates
    "can_execute_plugin",
    "can_load_plugin_package",
    "can_fetch_registry",
    "can_render_webui_execute_control",
    # boundary
    "assert_execution_policy_layer_disabled",
]
