"""Phase 2A — Read-only tool frontend contract tests.

These tests pin the backend response contract that the Vue frontend consumes,
so a backend change that breaks the frontend is caught at the Python level:

  - The set of selectable tools (clarify + five read-only) matches STATIC_ALLOWLIST
    and matches the frontend's expected constant.
  - The execute result envelope for each read-only tool carries the fields the
    frontend reads: executionCompleted, decision, toolResult.type,
    toolResult.result, sideEffects (all false), and the correlation IDs.
  - The "completed" signal is the executionCompleted boolean (not the decision
    string), so the frontend's generic completed-check works for every tool.

Phase: 2A — Real Tool Execution MVP (Read-only Multi-tool Execution)
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_read_only_tool_registry import (
    PHASE_2A_READ_ONLY_TOOL_IDS,
    list_read_only_tool_definitions,
)
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST
from tests.test_dev_web_phase_2a_read_only_execute import (
    READ_ONLY_TOOLS_WITH_RISK,
    run_read_only_tool_to_completion,
)

# The frontend's selectable tool list must equal the backend allowlist. This
# constant is duplicated in apps/hermes-dev-webui/src (the frontend cannot import
# Python); this test keeps the two in sync.
FRONTEND_SELECTABLE_TOOLS = (
    "clarify",
    "tool_policy_read",
    "route_governance_read",
    "audit_events_read",
    "dev_environment_read",
    "release_status_read",
)


@pytest.fixture
def phase_2a_home(tmp_path):
    home = tmp_path / "hermes-home-dev"
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    (home / "gateway" / "dev" / "tokens").mkdir(parents=True, exist_ok=True)
    return str(home)


def _fake_probe():
    return {
        "productionGatewayPidObserved": 1962,
        "productionGatewayProcessCount": 1,
        "productionGatewayCommandSummary": "hermes_cli.main gateway run",
        "port5180": "free",
        "port5181": "free",
    }


class TestSelectableToolContract:
    def test_frontend_selectable_matches_static_allowlist(self) -> None:
        assert frozenset(FRONTEND_SELECTABLE_TOOLS) == STATIC_ALLOWLIST
        assert len(FRONTEND_SELECTABLE_TOOLS) == 6

    def test_frontend_selectable_is_clarify_plus_five_read_only(self) -> None:
        assert FRONTEND_SELECTABLE_TOOLS[0] == "clarify"  # default first
        assert frozenset(FRONTEND_SELECTABLE_TOOLS[1:]) == PHASE_2A_READ_ONLY_TOOL_IDS

    def test_each_read_only_tool_has_frontend_metadata(self) -> None:
        # The frontend renders display_name + description + category per tool.
        for d in list_read_only_tool_definitions():
            assert d.tool_id in FRONTEND_SELECTABLE_TOOLS
            assert d.display_name and d.description and d.category


class TestExecuteResultContract:
    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_result_envelope_shape(self, phase_2a_home, tool_id, risk_tier) -> None:
        rd = run_read_only_tool_to_completion(
            phase_2a_home, tool_id, risk_tier=risk_tier, monkeypatch_probe=_fake_probe
        )
        # The frontend reads these top-level fields.
        for key in (
            "canonicalName", "decision", "executionCompleted", "toolHandlerCalled",
            "providerApiCalled", "resultPreview", "toolResult", "sideEffects",
            "handlerCallId", "postExecutionAuditId", "preExecutionAuditId",
            "dispatchId", "handlerLookupId", "executeRequestId",
        ):
            assert key in rd, f"missing frontend field {key}"

    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_completed_signal_is_boolean(self, phase_2a_home, tool_id, risk_tier) -> None:
        # The frontend's generic completed-check uses executionCompleted === true.
        rd = run_read_only_tool_to_completion(
            phase_2a_home, tool_id, risk_tier=risk_tier, monkeypatch_probe=_fake_probe
        )
        assert rd["executionCompleted"] is True
        assert isinstance(rd["executionCompleted"], bool)

    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_tool_result_structure(self, phase_2a_home, tool_id, risk_tier) -> None:
        rd = run_read_only_tool_to_completion(
            phase_2a_home, tool_id, risk_tier=risk_tier, monkeypatch_probe=_fake_probe
        )
        tr = rd["toolResult"]
        assert tr["type"] == tool_id
        assert isinstance(tr["result"], dict)  # structured payload for the result panel
        assert isinstance(tr["message"], str)  # one-line summary

    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_side_effects_contract(self, phase_2a_home, tool_id, risk_tier) -> None:
        rd = run_read_only_tool_to_completion(
            phase_2a_home, tool_id, risk_tier=risk_tier, monkeypatch_probe=_fake_probe
        )
        se = rd["sideEffects"]
        # The frontend renders these badges; all must be False for read-only.
        for key in (
            "providerSchemaSent", "providerApiCalled", "externalSideEffects",
        ):
            assert se[key] is False


class TestClarifyContractUnchanged:
    def test_clarify_still_completes_with_legacy_decision(self, phase_2a_home) -> None:
        # Clarify must keep its Phase 1G decision string so the existing
        # frontend/contract tests for clarify remain valid.
        rd = run_read_only_tool_to_completion(
            phase_2a_home, "clarify", risk_tier="R0"
        )
        assert rd["executionCompleted"] is True
        assert rd["decision"] == "clarify_execution_completed"
        assert rd["resultPreview"]["previewType"] == "clarify"
        assert rd["toolResult"]["type"] == "clarify"


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
