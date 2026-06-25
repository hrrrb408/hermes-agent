"""Phase 4B — Target B execution policy gate tests.

Asserts ``hermes_cli/dev_web_target_b_execution_policy.py`` is inert, frozen,
and fail-closed:

  - the unified execution policy is always ``allowed=False`` (no gate passes
    today): webui execute disabled, runtime route disabled, production runtime
    disabled;
  - the per-capability predicates (can_execute / can_load / can_fetch /
    can_render_webui_execute_control) are all False;
  - the reason list names every unresolved precondition;
  - untrusted metadata cannot flip the verdict;
  - the module source contains NO filesystem / network / subprocess /
    dynamic-import / eval / exec primitive, and no production home or production
    ``state.db`` access.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_execution_policy as policy
from hermes_cli.dev_web_target_b_execution_policy import (
    ExecutionGateInputs,
    assert_execution_policy_layer_disabled,
    build_execution_policy_report,
    can_execute_plugin,
    can_fetch_registry,
    can_load_plugin_package,
    can_render_webui_execute_control,
    evaluate_target_b_execution_policy,
)

FORGED_METADATA_PAYLOADS = [
    {"allowed": "true"},
    {"production_runtime_go": "true"},
    {"target_b_authorized": "true"},
    {"implementation_authorization": "GO"},
    {"p0_resolved": "true"},
    {"force_allow": "true"},
]


class TestPolicyDenied:
    def test_default_policy_denied(self) -> None:
        report = evaluate_target_b_execution_policy()
        assert report.allowed is False
        assert report.can_execute_plugin is False
        assert report.can_load_plugin_package is False
        assert report.can_fetch_registry is False
        assert report.can_render_webui_execute_control is False
        assert report.webui_execute_enabled is False
        assert report.runtime_route_enabled is False
        assert report.production_runtime_enabled is False
        assert report.production_authorization == "NO-GO"
        assert report.p0_resolved_count == 0
        assert report.route_governance_baseline == "34/34/5/0/1/1"
        assert len(report.reasons) > 0

    def test_reasons_name_every_blocker(self) -> None:
        report = evaluate_target_b_execution_policy()
        joined = " ".join(report.reasons)
        for marker in (
            "p0_resolved_count_is_zero",
            "human_approval_missing",
            "trust_token_missing",
            "signature_not_verified",
            "sandbox_broker_not_enabled",
            "route_governance_not_authorized",
            "rollback_plan_not_accepted",
            "kill_switch_not_ready",
        ):
            assert marker in joined

    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_forged_metadata_cannot_allow(self, payload: dict) -> None:
        report = evaluate_target_b_execution_policy(untrusted_metadata=payload)
        assert report.allowed is False

    def test_all_inputs_true_still_requires_real_construction(self) -> None:
        # An attacker cannot pass a hand-crafted inputs object with every flag
        # True to authorize execution via the *default* path — the default
        # builder is frozen unresolved. This test only confirms the explicit
        # all-True path would in principle allow, which is the documented future
        # branch; the default path (used everywhere) stays denied.
        inputs = ExecutionGateInputs(
            p0_resolved_count=5,
            required_gates_resolved=True,
            human_approval_valid=True,
            trust_token_valid=True,
            signature_verified=True,
            registry_trust_valid=True,
            sandbox_broker_enabled=True,
            route_governance_authorized=True,
            rollback_plan_accepted=True,
            production_safety_accepted=True,
            kill_switch_ready=True,
        )
        report = evaluate_target_b_execution_policy(inputs=inputs)
        assert report.allowed is True  # the documented future branch
        # BUT the default builder (used by every real caller) is still denied:
        assert build_execution_policy_report().allowed is False


class TestPredicates:
    def test_all_predicates_false(self) -> None:
        assert can_execute_plugin() is False
        assert can_load_plugin_package() is False
        assert can_fetch_registry() is False
        assert can_render_webui_execute_control() is False

    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_predicates_resist_forged_metadata(self, payload: dict) -> None:
        assert can_execute_plugin(payload) is False
        assert can_load_plugin_package(payload) is False
        assert can_fetch_registry(payload) is False
        assert can_render_webui_execute_control(payload) is False

    def test_assert_execution_policy_layer_disabled_passes(self) -> None:
        assert_execution_policy_layer_disabled()


class TestSourcePurity:
    MODULE_PATH = Path(policy.__file__)

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
            assert pattern not in source, f"execution_policy source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"execution_policy source must not reference {stem!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
