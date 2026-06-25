"""Phase 4C — Target B route authorization plan tests.

Asserts ``hermes_cli/dev_web_target_b_route_authorization.py`` is inert, frozen,
and fail-closed:

  - no route is authorized by default;
  - every proposed route is ``disabled`` (documentation only — never registered);
  - zero proposed routes are registered;
  - both deltas (openapi / runtime) are zero;
  - the route governance baseline is unchanged (34/34/5/0/1/1);
  - no backend route is changed;
  - metadata cannot authorize a route;
  - the aggregate report keeps production authorization NO-GO;
  - the module source contains NO forbidden primitive / production path.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_route_authorization as route_authorization
from hermes_cli.dev_web_target_b_route_authorization import (
    assert_route_authorization_not_approved,
    build_route_authorization_plan,
    build_route_authorization_report,
    evaluate_route_governance_for_target_b,
    validate_route_authorization_plan,
)


class TestRouteAuthorizationNotApproved:
    def test_plan_disabled(self) -> None:
        plan = build_route_authorization_plan()
        assert plan.approved is False
        assert plan.openapi_delta == 0
        assert plan.runtime_route_delta == 0
        assert plan.security_review_status == "not_reviewed"
        for route in plan.proposed_routes:
            assert route.disabled is True
            assert route.security_review_status == "not_reviewed"

    def test_evaluation_unchanged(self) -> None:
        decision = evaluate_route_governance_for_target_b()
        assert decision.route_authorized is False
        assert decision.proposed_routes_registered == 0
        assert decision.openapi_delta == 0
        assert decision.runtime_route_delta == 0
        assert decision.route_governance_baseline == "34/34/5/0/1/1"
        assert decision.backend_routes_changed is False
        assert decision.production_authorization == "NO-GO"

    def test_metadata_cannot_authorize(self) -> None:
        decision = evaluate_route_governance_for_target_b(
            untrusted_metadata={"route_exception_approved": "true"}
        )
        assert decision.route_authorized is False
        assert decision.backend_routes_changed is False
        assert "route_exception_approved" in decision.ignored_metadata_keys

    def test_report_unchanged(self) -> None:
        report = build_route_authorization_report()
        assert report.route_authorized is False
        assert report.proposed_routes_count > 0
        assert report.proposed_routes_registered == 0
        assert report.openapi_delta == 0
        assert report.runtime_route_delta == 0
        assert report.route_governance_baseline == "34/34/5/0/1/1"
        assert report.backend_routes_changed is False
        assert report.production_authorization == "NO-GO"


class TestPlanValidation:
    def test_default_plan_not_authorized(self) -> None:
        ok, reasons = validate_route_authorization_plan(build_route_authorization_plan())
        assert ok is False
        assert "approval_required" in reasons


class TestSourcePurity:
    MODULE_PATH = Path(route_authorization.__file__)

    FORBIDDEN_USAGE_PATTERNS = (
        "import subprocess",
        "subprocess.",
        "import importlib",
        "importlib.",
        "__import__",
        "import socket",
        "socket.",
        "requests.",
        "httpx.",
        "aiohttp.",
        "urllib",
        "eval(",
        "exec(",
        "os.system",
        "os.popen",
        "Path(",
        "Path.home",
        ".resolve(",
        "open(",
        "read_text(",
        "write_text(",
        "shutil.",
        "APIRouter",
        "add_api_route",
        "@app.",
        "include_router",
    )

    FORBIDDEN_PATH_STEMS = (
        "~/.hermes",
        ".hermes/state.db",
        "production/state.db",
        "state.db",
    )

    def test_module_source_contains_no_forbidden_usage_primitive(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8")
        for pattern in self.FORBIDDEN_USAGE_PATTERNS:
            assert pattern not in source, f"source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"source must not reference {stem!r}"

    def test_assert_route_authorization_not_approved_passes(self) -> None:
        assert_route_authorization_not_approved()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
