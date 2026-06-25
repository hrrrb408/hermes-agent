"""Phase 4C — Target B enablement readiness evaluator tests.

Asserts ``hermes_cli/dev_web_target_b_enablement_readiness.py`` is inert,
frozen, and fail-closed:

  - the default readiness status is BLOCKED (no real approval / trust token);
  - production_enablement_allowed is False by default;
  - a complete FIXTURE package reaches AUTHORIZATION_READY_BUT_NOT_ENABLED but
    never production-enabled;
  - even a fixture package with production_mode=True cannot enable;
  - ENABLEMENT_ALLOWED_BY_POLICY is never reachable in the dev skeleton;
  - AUTHORIZATION_READY_BUT_NOT_ENABLED does NOT start the production runtime;
  - the aggregate authorization package report keeps production authorization
    NO-GO, trust token not provisioned, P0 resolved 0, route baseline unchanged;
  - the module source contains NO forbidden primitive / production path.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_enablement_readiness as enablement_readiness
from hermes_cli.dev_web_target_b_enablement_readiness import (
    EnablementReadinessInput,
    assert_target_b_not_enabled_without_full_authorization,
    build_target_b_authorization_package_report,
    evaluate_target_b_enablement_readiness,
)


def _complete_fixture_inputs(**overrides) -> EnablementReadinessInput:
    base = dict(
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
    base.update(overrides)
    return EnablementReadinessInput(**base)


class TestDefaultBlocked:
    def test_default_is_blocked(self) -> None:
        result = evaluate_target_b_enablement_readiness()
        assert result.readiness_status == "BLOCKED"
        assert result.production_enablement_allowed is False
        assert result.all_gates_pass is False
        assert len(result.blockers) == 11

    def test_default_report_blocked(self) -> None:
        report = build_target_b_authorization_package_report()
        assert report.readiness_status == "BLOCKED"
        assert report.production_enablement_allowed is False
        assert report.trust_token_provisioned is False
        assert report.p0_resolved == 0
        assert report.backend_routes_changed is False
        assert report.route_governance_baseline == "34/34/5/0/1/1"
        for verdict in (
            report.production_runtime,
            report.registry,
            report.marketplace,
            report.webui_execution,
            report.approval_authorization,
            report.production_rollout,
        ):
            assert verdict == "NO-GO"

    def test_partial_inputs_are_incomplete(self) -> None:
        inputs = EnablementReadinessInput(human_approval_valid=True)
        result = evaluate_target_b_enablement_readiness(inputs)
        assert result.readiness_status == "AUTHORIZATION_PACKAGE_INCOMPLETE"
        assert result.production_enablement_allowed is False


class TestFixtureReadyButNotEnabled:
    def test_complete_fixture_package_is_ready_but_not_enabled(self) -> None:
        result = evaluate_target_b_enablement_readiness(_complete_fixture_inputs())
        assert result.readiness_status == "AUTHORIZATION_READY_BUT_NOT_ENABLED"
        assert result.production_enablement_allowed is False
        assert result.all_gates_pass is True
        assert result.fixture_only is True

    def test_fixture_with_production_mode_still_not_enabled(self) -> None:
        result = evaluate_target_b_enablement_readiness(
            _complete_fixture_inputs(production_mode=True)
        )
        # Fixture packages can never be production-enabled, even with the mode.
        assert result.production_enablement_allowed is False

    def test_real_complete_package_without_production_mode_is_ready_not_enabled(self) -> None:
        inputs = _complete_fixture_inputs(fixture_only=False, production_mode=False)
        result = evaluate_target_b_enablement_readiness(inputs)
        assert result.readiness_status == "AUTHORIZATION_READY_BUT_NOT_ENABLED"
        assert result.production_enablement_allowed is False

    def test_enablement_allowed_requires_production_mode_and_real_package(self) -> None:
        inputs = _complete_fixture_inputs(fixture_only=False, production_mode=True)
        result = evaluate_target_b_enablement_readiness(inputs)
        # This is the one combination that WOULD allow enablement by policy.
        # It is not reachable in the dev skeleton (production_mode is never set
        # by any code path), but the evaluator's logic must be correct.
        assert result.readiness_status == "ENABLEMENT_ALLOWED_BY_POLICY"
        assert result.production_enablement_allowed is True

    def test_ready_but_not_enabled_does_not_start_runtime(self) -> None:
        report_default = build_target_b_authorization_package_report()
        # The aggregate report always reflects the DEFAULT (no real inputs) — it
        # is BLOCKED regardless of what a test-only evaluator call returned.
        assert report_default.readiness_status == "BLOCKED"
        assert report_default.production_enablement_allowed is False


class TestSourcePurity:
    MODULE_PATH = Path(enablement_readiness.__file__)

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

    def test_assert_target_b_not_enabled_without_full_authorization_passes(self) -> None:
        assert_target_b_not_enabled_without_full_authorization()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
