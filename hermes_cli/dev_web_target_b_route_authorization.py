"""Phase 4C — Target B route authorization plan (pure stdlib, fail-closed).

Layer 10 of the Phase 4C Target B authorization package. Defines the **route
authorization plan** for Target B — a *disabled*, documentation-only plan for the
routes a future enablement *would* require. It is explicitly NOT a route
registration: no backend route is added, no OpenAPI path is added, no
``dev_web_api`` integration is performed, and the route governance baseline
stays ``34/34/5/0/1/1`` (OpenAPI paths 34, runtime routes 34, tool GET 5, tool
write HTTP route 0, tool dry-run route 1, tool execution route 1, and every
"new route" flag 0).

A real route change request would require an approved route authorization plan,
an approved rollback plan, and a route-governance decision — none of which exist
in the dev skeleton. Therefore:

  - ``route_authorized = False``
  - ``openapi_delta = 0``
  - ``runtime_route_delta = 0``
  - every proposed route stays ``disabled``

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no eval / exec, no production access, no FastAPI
app import, no ``dev_web_api`` import.

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
from hermes_cli.dev_web_target_b_common import TARGET_B_ROUTE_GOVERNANCE_BASELINE

# ---------------------------------------------------------------------------
# 1. The route authorization schema (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RouteChangeRequest:
    """A frozen, *disabled* proposed route (documentation only — never registered)."""

    route_id: str
    path: str
    route_type: str  # e.g. "tool-execute", "registry-fetch", "approval"
    method: str
    disabled: bool
    security_review_status: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "routeId": self.route_id,
                "path": self.path,
                "routeType": self.route_type,
                "method": self.method,
                "disabled": self.disabled,
                "securityReviewStatus": self.security_review_status,
            }
        )


@dataclass(frozen=True, slots=True)
class RouteAuthorizationPlan:
    """A frozen, *disabled* route authorization plan (never registered)."""

    plan_id: str
    proposed_routes: tuple[RouteChangeRequest, ...]
    rollback_plan_id: str
    approval_id: str
    security_review_status: str
    openapi_delta: int
    runtime_route_delta: int
    approved: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "planId": self.plan_id,
                "proposedRoutes": [r.to_safe_dict() for r in self.proposed_routes],
                "rollbackPlanId": self.rollback_plan_id,
                "approvalId": self.approval_id,
                "securityReviewStatus": self.security_review_status,
                "openapiDelta": self.openapi_delta,
                "runtimeRouteDelta": self.runtime_route_delta,
                "approved": self.approved,
            }
        )


@dataclass(frozen=True, slots=True)
class RouteGovernanceDecision:
    """The frozen route-governance decision for Target B. Unchanged by default."""

    route_authorized: bool
    proposed_routes_registered: int
    openapi_delta: int
    runtime_route_delta: int
    route_governance_baseline: str
    backend_routes_changed: bool
    production_authorization: str
    reason: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "routeAuthorized": self.route_authorized,
                "proposedRoutesRegistered": self.proposed_routes_registered,
                "openapiDelta": self.openapi_delta,
                "runtimeRouteDelta": self.runtime_route_delta,
                "routeGovernanceBaseline": self.route_governance_baseline,
                "backendRoutesChanged": self.backend_routes_changed,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


@dataclass(frozen=True, slots=True)
class RouteAuthorizationReport:
    """The frozen aggregate route-authorization report."""

    route_authorized: bool
    proposed_routes_count: int
    proposed_routes_registered: int
    openapi_delta: int
    runtime_route_delta: int
    route_governance_baseline: str
    backend_routes_changed: bool
    production_authorization: str
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "routeAuthorized": self.route_authorized,
                "proposedRoutesCount": self.proposed_routes_count,
                "proposedRoutesRegistered": self.proposed_routes_registered,
                "openapiDelta": self.openapi_delta,
                "runtimeRouteDelta": self.runtime_route_delta,
                "routeGovernanceBaseline": self.route_governance_baseline,
                "backendRoutesChanged": self.backend_routes_changed,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
            }
        )


# ---------------------------------------------------------------------------
# 2. The frozen disabled route plan
# ---------------------------------------------------------------------------


#: The frozen, disabled proposed routes (documentation only — never registered).
_PROPOSED_ROUTES: tuple[RouteChangeRequest, ...] = (
    RouteChangeRequest(
        route_id="target-b-plugin-execute",
        path="/api/dev/v1/target-b/execute",
        route_type="tool-execute",
        method="POST",
        disabled=True,
        security_review_status="not_reviewed",
    ),
    RouteChangeRequest(
        route_id="target-b-plugin-install",
        path="/api/dev/v1/target-b/install",
        route_type="plugin-install",
        method="POST",
        disabled=True,
        security_review_status="not_reviewed",
    ),
    RouteChangeRequest(
        route_id="target-b-registry-fetch",
        path="/api/dev/v1/target-b/registry/fetch",
        route_type="registry-fetch",
        method="POST",
        disabled=True,
        security_review_status="not_reviewed",
    ),
    RouteChangeRequest(
        route_id="target-b-approval",
        path="/api/dev/v1/target-b/approval",
        route_type="approval",
        method="POST",
        disabled=True,
        security_review_status="not_reviewed",
    ),
)


def build_route_authorization_plan() -> RouteAuthorizationPlan:
    """Build the frozen, *disabled* route authorization plan.

    Every proposed route is ``disabled``. The plan is not approved. The
    OpenAPI / runtime route deltas are zero. Nothing is registered.
    """
    return RouteAuthorizationPlan(
        plan_id="hermes-target-b-route-authorization",
        proposed_routes=_PROPOSED_ROUTES,
        rollback_plan_id="",
        approval_id="",
        security_review_status="not_reviewed",
        openapi_delta=0,
        runtime_route_delta=0,
        approved=False,
    )


def validate_route_authorization_plan(plan: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate a route authorization plan. Returns ``(ok, reasons)``.

    A plan is invalid (cannot authorize) if any proposed route is not disabled,
    if any route has passed security review, if the deltas are non-zero, or if
    the plan is not approved. The dev skeleton plan is always invalid for
    authorization.
    """
    if not isinstance(plan, RouteAuthorizationPlan):
        return False, ("plan_not_a_route_authorization_plan",)
    reasons: list[str] = []
    for route in plan.proposed_routes:
        if not route.disabled:
            reasons.append(f"route_not_disabled:{route.route_id}")
        if route.security_review_status == "approved":
            reasons.append(f"route_security_review_not_allowed:{route.route_id}")
    if plan.openapi_delta != 0:
        reasons.append("openapi_delta_must_be_zero")
    if plan.runtime_route_delta != 0:
        reasons.append("runtime_route_delta_must_be_zero")
    if not plan.rollback_plan_id:
        reasons.append("rollback_plan_required")
    if not plan.approval_id:
        reasons.append("approval_required")
    return (len(reasons) == 0 and plan.approved), tuple(reasons)


def evaluate_route_governance_for_target_b(
    plan: Any = None,
    untrusted_metadata: Any = None,
) -> RouteGovernanceDecision:
    """Evaluate route governance for Target B. Unchanged by default.

    No route is authorized; zero proposed routes are registered; both deltas are
    zero; the route governance baseline is frozen unchanged. *untrusted_metadata*
    is inspected only to report ignored bypass keys.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    active = (
        plan if isinstance(plan, RouteAuthorizationPlan) else build_route_authorization_plan()
    )
    _ = active  # the plan is read for diagnostics; nothing is registered
    return RouteGovernanceDecision(
        route_authorized=False,
        proposed_routes_registered=0,
        openapi_delta=0,
        runtime_route_delta=0,
        route_governance_baseline=TARGET_B_ROUTE_GOVERNANCE_BASELINE,
        backend_routes_changed=False,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="route_authorization_not_approved",
        ignored_metadata_keys=ignored,
    )


def build_route_authorization_report() -> RouteAuthorizationReport:
    """Build the frozen aggregate route-authorization report.

    No route is authorized; the disabled proposed routes are documentation only;
    zero are registered; both deltas are zero; the route governance baseline is
    unchanged (34/34/5/0/1/1). Production authorization stays NO-GO. Pure and
    deterministic.
    """
    return RouteAuthorizationReport(
        route_authorized=False,
        proposed_routes_count=len(_PROPOSED_ROUTES),
        proposed_routes_registered=0,
        openapi_delta=0,
        runtime_route_delta=0,
        route_governance_baseline=TARGET_B_ROUTE_GOVERNANCE_BASELINE,
        backend_routes_changed=False,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="route_authorization_not_approved",
    )


def assert_route_authorization_not_approved() -> None:
    """Re-affirm no route is authorized for Target B. Pure."""
    report = build_route_authorization_report()
    assert report.route_authorized is False
    assert report.proposed_routes_registered == 0
    assert report.openapi_delta == 0
    assert report.runtime_route_delta == 0
    assert report.route_governance_baseline == "34/34/5/0/1/1"
    assert report.backend_routes_changed is False
    assert report.production_authorization == TARGET_B_AUTHORIZATION_NO_GO
    plan = build_route_authorization_plan()
    # Every proposed route is disabled.
    for route in plan.proposed_routes:
        assert route.disabled is True
    # The plan is not authorized.
    assert validate_route_authorization_plan(plan)[0] is False
    decision = evaluate_route_governance_for_target_b(
        plan,
        untrusted_metadata={"route_exception_approved": "true"},
    )
    assert decision.route_authorized is False
    assert decision.backend_routes_changed is False
    assert "route_exception_approved" in decision.ignored_metadata_keys


__all__ = [
    # schema
    "RouteChangeRequest",
    "RouteAuthorizationPlan",
    "RouteGovernanceDecision",
    "RouteAuthorizationReport",
    # plan
    "build_route_authorization_plan",
    "validate_route_authorization_plan",
    "evaluate_route_governance_for_target_b",
    "build_route_authorization_report",
    # boundary
    "assert_route_authorization_not_approved",
]
