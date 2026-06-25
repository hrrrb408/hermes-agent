"""Phase 4C — Target B rollback / incident plan approval (pure stdlib, fail-closed).

Layer 9 of the Phase 4C Target B authorization package. Extends the Phase 4B
rollback layer with an **incident response plan approval model**: the rollback
plan, the incident response plan, the kill-switch authorization, and the
readiness result that gates whether production rollout may proceed.

The production rollout stays **NO-GO** by default. The kill-switch design being
ready is **not** production approval. No process is ever signaled, no gateway is
ever stopped / restarted / replaced, and the rollback must be reviewed before
enablement (which it is not).

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no signal, no dynamic import, no eval / exec, no production access,
and no production gateway interaction (PID 28428 is referenced only as a
do-not-touch target).

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hermes_cli.dev_web_target_b_authorization_common import (
    TARGET_B_AUTHORIZATION_NO_GO,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
)

# ---------------------------------------------------------------------------
# 1. The rollback / incident schema (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RollbackPlan:
    """A frozen production rollback plan. Design-only / not approved by default."""

    plan_id: str
    rollback_targets: tuple[str, ...]
    rollback_steps: tuple[str, ...]
    verification_steps: tuple[str, ...]
    max_blip_seconds: int
    reviewer_approval_id: str
    approved: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "planId": self.plan_id,
                "rollbackTargets": list(self.rollback_targets),
                "rollbackSteps": list(self.rollback_steps),
                "verificationSteps": list(self.verification_steps),
                "maxBlipSeconds": self.max_blip_seconds,
                "reviewerApprovalId": self.reviewer_approval_id,
                "approved": self.approved,
            }
        )


@dataclass(frozen=True, slots=True)
class IncidentResponsePlan:
    """A frozen incident response plan. Not approved by default."""

    plan_id: str
    on_call_roles: tuple[str, ...]
    severity_matrix: tuple[str, ...]
    escalation_steps: tuple[str, ...]
    postmortem_required: bool
    reviewer_approval_id: str
    approved: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "planId": self.plan_id,
                "onCallRoles": list(self.on_call_roles),
                "severityMatrix": list(self.severity_matrix),
                "escalationSteps": list(self.escalation_steps),
                "postmortemRequired": self.postmortem_required,
                "reviewerApprovalId": self.reviewer_approval_id,
                "approved": self.approved,
            }
        )


@dataclass(frozen=True, slots=True)
class KillSwitchAuthorization:
    """The frozen kill-switch authorization. Design-ready only, not armed."""

    kill_switch_id: str
    design_ready: bool
    armed: bool
    production_rollback_authorized: bool
    reviewer_approval_id: str


@dataclass(frozen=True, slots=True)
class RollbackReadinessResult:
    """The frozen result of evaluating rollback readiness for enablement."""

    rollback_plan_approved: bool
    incident_plan_approved: bool
    kill_switch_armed: bool
    production_rollback_authorized: bool
    production_gateway_untouched: bool
    production_rollout: str
    production_authorization: str
    reason: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "rollbackPlanApproved": self.rollback_plan_approved,
                "incidentPlanApproved": self.incident_plan_approved,
                "killSwitchArmed": self.kill_switch_armed,
                "productionRollbackAuthorized": self.production_rollback_authorized,
                "productionGatewayUntouched": self.production_gateway_untouched,
                "productionRollout": self.production_rollout,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


@dataclass(frozen=True, slots=True)
class IncidentRollbackReport:
    """The frozen aggregate incident / rollback authorization report."""

    rollback_plan_present: bool
    rollback_plan_approved: bool
    incident_plan_present: bool
    incident_plan_approved: bool
    kill_switch_ready: str
    production_rollback_authorized: bool
    production_rollout: str
    production_gateway_untouched: bool
    production_authorization: str
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "rollbackPlanPresent": self.rollback_plan_present,
                "rollbackPlanApproved": self.rollback_plan_approved,
                "incidentPlanPresent": self.incident_plan_present,
                "incidentPlanApproved": self.incident_plan_approved,
                "killSwitchReady": self.kill_switch_ready,
                "productionRollbackAuthorized": self.production_rollback_authorized,
                "productionRollout": self.production_rollout,
                "productionGatewayUntouched": self.production_gateway_untouched,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
            }
        )


# ---------------------------------------------------------------------------
# 2. Frozen defaults + validation
# ---------------------------------------------------------------------------


#: The frozen kill-switch design-ready authorization (not armed).
KILL_SWITCH_DESIGN_READY: KillSwitchAuthorization = KillSwitchAuthorization(
    kill_switch_id="hermes-target-b-kill-switch",
    design_ready=True,
    armed=False,
    production_rollback_authorized=False,
    reviewer_approval_id="",
)


def build_rollback_plan() -> RollbackPlan:
    """Build the frozen default rollback plan (design-only, not approved)."""
    return RollbackPlan(
        plan_id="hermes-target-b-rollback",
        rollback_targets=("dev-home", "dev-state"),
        rollback_steps=(
            "design-only: disable new runtime routes",
            "design-only: revert schema migration",
            "design-only: restore prior session store",
        ),
        verification_steps=(
            "design-only: smoke read-only API",
            "design-only: verify P0 counts unchanged",
        ),
        max_blip_seconds=0,
        reviewer_approval_id="",
        approved=False,
    )


def build_incident_response_plan() -> IncidentResponsePlan:
    """Build the frozen default incident response plan (not approved)."""
    return IncidentResponsePlan(
        plan_id="hermes-target-b-incident",
        on_call_roles=("project owner", "security reviewer", "production safety reviewer"),
        severity_matrix=("sev1: production outage", "sev2: degraded", "sev3: minor"),
        escalation_steps=(
            "design-only: page on-call",
            "design-only: open incident channel",
            "design-only: schedule postmortem",
        ),
        postmortem_required=True,
        reviewer_approval_id="",
        approved=False,
    )


def validate_rollback_plan(plan: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate a rollback plan. Returns ``(ok, reasons)``."""
    if not isinstance(plan, RollbackPlan):
        return False, ("plan_not_a_rollback_plan",)
    reasons: list[str] = []
    if not plan.rollback_steps:
        reasons.append("rollback_steps_required")
    if not plan.verification_steps:
        reasons.append("verification_steps_required")
    if not plan.reviewer_approval_id:
        reasons.append("reviewer_approval_required")
    return (len(reasons) == 0 and plan.approved), tuple(reasons)


def validate_incident_response_plan(plan: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate an incident response plan. Returns ``(ok, reasons)``."""
    if not isinstance(plan, IncidentResponsePlan):
        return False, ("plan_not_an_incident_response_plan",)
    reasons: list[str] = []
    if not plan.on_call_roles:
        reasons.append("on_call_roles_required")
    if not plan.escalation_steps:
        reasons.append("escalation_steps_required")
    if not plan.postmortem_required:
        reasons.append("postmortem_required")
    if not plan.reviewer_approval_id:
        reasons.append("reviewer_approval_required")
    return (len(reasons) == 0 and plan.approved), tuple(reasons)


def evaluate_rollback_readiness_for_enablement(
    rollback_plan: Any = None,
    incident_plan: Any = None,
    kill_switch: Any = None,
    untrusted_metadata: Any = None,
) -> RollbackReadinessResult:
    """Evaluate rollback readiness for Target B enablement. Always not-ready today.

    The kill-switch design being ready is NOT production approval. No process is
    signaled and the production gateway is never touched. *untrusted_metadata*
    is inspected only to report ignored bypass keys.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    rp = rollback_plan if isinstance(rollback_plan, RollbackPlan) else build_rollback_plan()
    ip = incident_plan if isinstance(incident_plan, IncidentResponsePlan) else build_incident_response_plan()
    ks = (
        kill_switch
        if isinstance(kill_switch, KillSwitchAuthorization)
        else KILL_SWITCH_DESIGN_READY
    )
    rollback_ok, _ = validate_rollback_plan(rp)
    incident_ok, _ = validate_incident_response_plan(ip)
    # Enablement requires BOTH plans approved AND the kill switch armed AND
    # production rollback authorized — none of which is true today.
    ready = bool(rollback_ok and incident_ok and ks.armed and ks.production_rollback_authorized)
    return RollbackReadinessResult(
        rollback_plan_approved=rollback_ok,
        incident_plan_approved=incident_ok,
        kill_switch_armed=ks.armed,
        production_rollback_authorized=ks.production_rollback_authorized,
        production_gateway_untouched=True,
        production_rollout=TARGET_B_AUTHORIZATION_NO_GO if not ready else "NO-GO",
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="rollback_incident_plan_not_approved",
        ignored_metadata_keys=ignored,
    )


def build_incident_rollback_report() -> IncidentRollbackReport:
    """Build the frozen aggregate incident / rollback authorization report.

    The rollback plan is design-only; the incident plan is not approved; the
    kill switch is design-ready only; production rollback is not authorized;
    production rollout stays NO-GO; the production gateway is untouched.
    Production authorization stays NO-GO. Pure and deterministic.
    """
    return IncidentRollbackReport(
        rollback_plan_present=True,
        rollback_plan_approved=False,
        incident_plan_present=True,
        incident_plan_approved=False,
        kill_switch_ready="DESIGN_READY_ONLY",
        production_rollback_authorized=False,
        production_rollout=TARGET_B_AUTHORIZATION_NO_GO,
        production_gateway_untouched=True,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="rollback_incident_plan_not_approved",
    )


def assert_rollback_incident_not_authorized() -> None:
    """Re-affirm the rollback / incident plan is not authorized. Pure."""
    report = build_incident_rollback_report()
    assert report.rollback_plan_present is True
    assert report.rollback_plan_approved is False
    assert report.incident_plan_approved is False
    assert report.kill_switch_ready == "DESIGN_READY_ONLY"
    assert report.production_rollback_authorized is False
    assert report.production_rollout == TARGET_B_AUTHORIZATION_NO_GO
    assert report.production_gateway_untouched is True
    assert report.production_authorization == TARGET_B_AUTHORIZATION_NO_GO
    # The default plans are not approved.
    assert validate_rollback_plan(build_rollback_plan())[0] is False
    assert validate_incident_response_plan(build_incident_response_plan())[0] is False
    # The kill switch is design-ready only — not armed, not production-authorized.
    assert KILL_SWITCH_DESIGN_READY.armed is False
    assert KILL_SWITCH_DESIGN_READY.production_rollback_authorized is False
    result = evaluate_rollback_readiness_for_enablement(
        untrusted_metadata={"kill_switch_armed": "true", "production_rollout_approved": "true"},
    )
    assert result.kill_switch_armed is False
    assert "kill_switch_armed" in result.ignored_metadata_keys
    assert "production_rollout_approved" in result.ignored_metadata_keys


__all__ = [
    # schema
    "RollbackPlan",
    "IncidentResponsePlan",
    "KillSwitchAuthorization",
    "RollbackReadinessResult",
    "IncidentRollbackReport",
    # defaults
    "KILL_SWITCH_DESIGN_READY",
    # builders
    "build_rollback_plan",
    "build_incident_response_plan",
    # validation
    "validate_rollback_plan",
    "validate_incident_response_plan",
    "evaluate_rollback_readiness_for_enablement",
    "build_incident_rollback_report",
    # boundary
    "assert_rollback_incident_not_authorized",
]
