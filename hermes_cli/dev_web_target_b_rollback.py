"""Phase 4B — Target B rollback / kill-switch layer (pure stdlib, fail-closed).

Layer 11 of the Phase 4B Target B engineering path. Defines the **rollback /
kill-switch** model.

The kill switch is **design-ready only** (``DESIGN_READY_ONLY``) — no production
rollback is authorized, no production rollout is approved, and no process is
ever signaled, stopped, restarted, or replaced. The model is a pure,
deterministic readiness projection: it describes what an approved rollback /
kill-switch would do without ever performing an action.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no signal, no process control, no dynamic import, no real secret
read, no production access, **no touch of the production gateway (pid 28428)**.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hermes_cli.dev_web_target_b_common import (
    TARGET_B_NO_GO,
    TARGET_B_PRODUCTION_GATEWAY_PID_REFERENCE,
    TARGET_B_ROLLBACK_DESIGN_ONLY_REASON,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
)

# ---------------------------------------------------------------------------
# 1. Frozen kill-switch / rollback status
# ---------------------------------------------------------------------------

#: The kill-switch readiness. DESIGN_READY_ONLY — never armed for production.
KILL_SWITCH_DESIGN_READY_ONLY: str = "DESIGN_READY_ONLY"
KILL_SWITCH_ARMED: str = "ARMED"
KILL_SWITCH_DISABLED: str = "DISABLED"

#: The production rollout verdict. Always NO-GO in the dev skeleton.
PRODUCTION_ROLLOUT_NO_GO: str = TARGET_B_NO_GO


@dataclass(frozen=True, slots=True)
class KillSwitchStatus:
    """The frozen kill-switch status. Design-ready only — never armed."""

    readiness: str
    armed: bool
    production_rollback_authorized: bool
    production_rollout: str
    incident_owner: str
    rollback_targets: tuple[str, ...]
    production_gateway_untouched: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "readiness": self.readiness,
                "armed": self.armed,
                "productionRollbackAuthorized": self.production_rollback_authorized,
                "productionRollout": self.production_rollout,
                "incidentOwner": self.incident_owner,
                "rollbackTargets": list(self.rollback_targets),
                "productionGatewayUntouched": self.production_gateway_untouched,
            }
        )


def build_kill_switch_status() -> KillSwitchStatus:
    """Build the frozen kill-switch status: design-ready only."""
    return KillSwitchStatus(
        readiness=KILL_SWITCH_DESIGN_READY_ONLY,
        armed=False,
        production_rollback_authorized=False,
        production_rollout=PRODUCTION_ROLLOUT_NO_GO,
        incident_owner="unassigned (no approved incident-response plan)",
        # Rollback targets are DESIGN documentation only — fake/temp identifiers,
        # never resolved, never acted on.
        rollback_targets=(
            "design-only: disable dev fixture runtime",
            "design-only: revert dev descriptor registry",
        ),
        production_gateway_untouched=True,
    )


def evaluate_rollback_readiness() -> tuple[bool, tuple[str, ...]]:
    """Evaluate whether a production rollback is ready. Always ``(False, reasons)``.

    The kill switch is design-ready only; no production rollback is authorized;
    no incident-response plan is approved; the production gateway is never
    touched.
    """
    status = build_kill_switch_status()
    reasons: list[str] = []
    if status.readiness != KILL_SWITCH_ARMED:
        reasons.append("kill_switch_design_ready_only")
    if not status.production_rollback_authorized:
        reasons.append("production_rollback_not_authorized")
    if status.incident_owner.startswith("unassigned"):
        reasons.append("incident_owner_unassigned")
    reasons.append("no_approved_incident_response_plan")
    return False, tuple(reasons)


def deny_without_kill_switch(untrusted_metadata: Any = None) -> KillSwitchStatus:
    """Return the kill-switch status, ignoring any bypass metadata.

    The kill switch is design-ready only no matter what untrusted metadata a
    request supplies. *untrusted_metadata* is inspected only to report ignored
    keys.
    """
    detect_target_b_untrusted_metadata(untrusted_metadata)
    return build_kill_switch_status()


@dataclass(frozen=True, slots=True)
class RollbackReport:
    """The frozen aggregate rollback / kill-switch readiness report."""

    kill_switch_ready: str
    production_rollback_authorized: bool
    production_rollout: str
    production_gateway_untouched: bool
    reason: str
    status: KillSwitchStatus

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "killSwitchReady": self.kill_switch_ready,
                "productionRollbackAuthorized": self.production_rollback_authorized,
                "productionRollout": self.production_rollout,
                "productionGatewayUntouched": self.production_gateway_untouched,
                "reason": self.reason,
                "status": self.status.to_safe_dict(),
            }
        )


def build_rollback_report() -> RollbackReport:
    """Build the frozen aggregate rollback report. Design-ready only.

    The kill switch is ``DESIGN_READY_ONLY``; production rollback is not
    authorized; production rollout is NO-GO; the production gateway is
    untouched. Pure and deterministic — no signal, no process control.
    """
    status = build_kill_switch_status()
    return RollbackReport(
        kill_switch_ready=KILL_SWITCH_DESIGN_READY_ONLY,
        production_rollback_authorized=False,
        production_rollout=PRODUCTION_ROLLOUT_NO_GO,
        production_gateway_untouched=True,
        reason=TARGET_B_ROLLBACK_DESIGN_ONLY_REASON,
        status=status,
    )


def assert_rollback_layer_disabled() -> None:
    """Re-affirm the rollback layer disabled invariants. Pure."""
    status = build_kill_switch_status()
    assert status.readiness == KILL_SWITCH_DESIGN_READY_ONLY
    assert status.armed is False
    assert status.production_rollback_authorized is False
    assert status.production_rollout == PRODUCTION_ROLLOUT_NO_GO
    assert status.production_gateway_untouched is True
    ready, _reasons = evaluate_rollback_readiness()
    assert ready is False
    report = build_rollback_report()
    assert report.kill_switch_ready == KILL_SWITCH_DESIGN_READY_ONLY
    assert report.production_rollout == PRODUCTION_ROLLOUT_NO_GO
    assert report.production_gateway_untouched is True
    # The production gateway is referenced ONLY as a do-not-touch string.
    assert TARGET_B_PRODUCTION_GATEWAY_PID_REFERENCE.startswith("production gateway pid")


__all__ = [
    # statuses
    "KILL_SWITCH_DESIGN_READY_ONLY",
    "KILL_SWITCH_ARMED",
    "KILL_SWITCH_DISABLED",
    "PRODUCTION_ROLLOUT_NO_GO",
    # models
    "KillSwitchStatus",
    "build_kill_switch_status",
    "evaluate_rollback_readiness",
    "deny_without_kill_switch",
    "RollbackReport",
    "build_rollback_report",
    # boundary
    "assert_rollback_layer_disabled",
]
