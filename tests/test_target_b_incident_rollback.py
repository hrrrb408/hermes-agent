"""Phase 4C — Target B rollback / incident plan approval tests.

Asserts ``hermes_cli/dev_web_target_b_incident_rollback.py`` is inert, frozen,
and fail-closed:

  - the rollback plan is design-only / not approved;
  - the incident response plan is not approved;
  - the kill switch is design-ready only (NOT armed, NOT production-authorized);
  - production rollback is not authorized;
  - production rollout stays NO-GO;
  - the production gateway is untouched;
  - metadata cannot arm the kill switch or authorize rollout;
  - the module source contains NO forbidden primitive / production path.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts / stops / signals a gateway, and introduces no new
route.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_incident_rollback as incident_rollback
from hermes_cli.dev_web_target_b_incident_rollback import (
    KILL_SWITCH_DESIGN_READY,
    assert_rollback_incident_not_authorized,
    build_incident_rollback_report,
    build_incident_response_plan,
    build_rollback_plan,
    evaluate_rollback_readiness_for_enablement,
    validate_incident_response_plan,
    validate_rollback_plan,
)


class TestRollbackIncidentNotApproved:
    def test_default_plans_not_approved(self) -> None:
        assert build_rollback_plan().approved is False
        assert build_incident_response_plan().approved is False

    def test_kill_switch_design_ready_only(self) -> None:
        assert KILL_SWITCH_DESIGN_READY.design_ready is True
        assert KILL_SWITCH_DESIGN_READY.armed is False
        assert KILL_SWITCH_DESIGN_READY.production_rollback_authorized is False

    def test_evaluation_not_ready(self) -> None:
        result = evaluate_rollback_readiness_for_enablement()
        assert result.rollback_plan_approved is False
        assert result.incident_plan_approved is False
        assert result.kill_switch_armed is False
        assert result.production_rollback_authorized is False
        assert result.production_gateway_untouched is True
        assert result.production_rollout == "NO-GO"
        assert result.production_authorization == "NO-GO"

    def test_metadata_cannot_arm_kill_switch(self) -> None:
        result = evaluate_rollback_readiness_for_enablement(
            untrusted_metadata={"kill_switch_armed": "true", "production_rollout_approved": "true"}
        )
        assert result.kill_switch_armed is False
        assert result.production_rollback_authorized is False
        assert "kill_switch_armed" in result.ignored_metadata_keys
        assert "production_rollout_approved" in result.ignored_metadata_keys

    def test_report_not_authorized(self) -> None:
        report = build_incident_rollback_report()
        assert report.rollback_plan_present is True
        assert report.rollback_plan_approved is False
        assert report.incident_plan_approved is False
        assert report.kill_switch_ready == "DESIGN_READY_ONLY"
        assert report.production_rollback_authorized is False
        assert report.production_rollout == "NO-GO"
        assert report.production_gateway_untouched is True
        assert report.production_authorization == "NO-GO"


class TestPlanValidation:
    def test_default_rollback_plan_not_valid(self) -> None:
        ok, reasons = validate_rollback_plan(build_rollback_plan())
        assert ok is False
        assert "reviewer_approval_required" in reasons

    def test_default_incident_plan_not_valid(self) -> None:
        ok, reasons = validate_incident_response_plan(build_incident_response_plan())
        assert ok is False
        assert "reviewer_approval_required" in reasons


class TestSourcePurity:
    MODULE_PATH = Path(incident_rollback.__file__)

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
        "os.kill",
        "signal.",
        "Path(",
        "Path.home",
        ".resolve(",
        "open(",
        "read_text(",
        "write_text(",
        "shutil.",
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

    def test_assert_rollback_incident_not_authorized_passes(self) -> None:
        assert_rollback_incident_not_authorized()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
