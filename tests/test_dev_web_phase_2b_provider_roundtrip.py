"""Phase 2B — Provider Round-trip orchestrator tests.

Drives the controlled Provider round-trip end-to-end for each Phase 2A
read-only tool and for clarify, and verifies the block paths (unknown tool,
write-like tool, provider-recursive tool, malformed arguments, real mode).

Phase: 2B — Provider Schema / API Controlled Integration
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_adapter import FakeProviderAdapter, ProviderToolCall
from hermes_cli.dev_web_provider_roundtrip import (
    run_provider_tool_roundtrip,
    validate_provider_tool_call,
    TOOL_CALL_BLOCKED_MALFORMED_ARGS,
    TOOL_CALL_BLOCKED_NOT_ALLOWLISTED,
    TOOL_CALL_BLOCKED_PROVIDER_RECURSIVE,
    TOOL_CALL_BLOCKED_WRITE_LIKE,
    TOOL_CALL_VALID,
)
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST


READ_ONLY_TOOLS = [
    "tool_policy_read",
    "route_governance_read",
    "audit_events_read",
    "dev_environment_read",
    "release_status_read",
]

ALLOWED = frozenset(STATIC_ALLOWLIST)


@pytest.fixture
def provider_home(tmp_path):
    home = tmp_path / "hermes-home-dev"
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    (home / "gateway" / "dev" / "tokens").mkdir(parents=True, exist_ok=True)
    return str(home)


@pytest.fixture(autouse=True)
def _enable_gates(monkeypatch):
    # The controlled execution chain requires these kill-switch gates.
    monkeypatch.setenv("HERMES_TOOL_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("HERMES_AGENT_TOOLS_ENABLED", "true")
    monkeypatch.setenv("HERMES_TOOL_HANDLER_CALL_ENABLED", "true")
    # dev_environment_read probes the system; inject a safe fake via monkeypatch.
    import hermes_cli.dev_web_read_only_tool_handlers as handlers

    monkeypatch.setattr(
        handlers,
        "_probe_system_state",
        lambda: {
            "productionGatewayPidObserved": 1962,
            "productionGatewayProcessCount": 1,
            "productionGatewayCommandSummary": "hermes_cli.main gateway run",
            "port5180": "free",
            "port5181": "free",
        },
    )


class TestFakeRoundtripPerTool:
    @pytest.mark.parametrize("tool_id", READ_ONLY_TOOLS)
    def test_fake_roundtrip_executes_read_only_tool(self, provider_home, tool_id) -> None:
        message = {
            "tool_policy_read": "read tool policy",
            "route_governance_read": "check route governance",
            "audit_events_read": "read audit events",
            "dev_environment_read": "check dev environment",
            "release_status_read": "read release status",
        }[tool_id]
        result = run_provider_tool_roundtrip(
            message, "fake",
            selected_tool_ids=frozenset({tool_id}),
            hermes_home=provider_home,
        )
        d = result.to_safe_dict()
        assert d["status"] == "completed", d
        assert d["providerMode"] == "fake"
        assert d["providerSchemaSent"] is True
        assert d["providerApiCalled"] is True
        assert d["externalNetworkCalled"] is False
        assert len(d["toolCalls"]) == 1
        assert d["toolCalls"][0]["name"] == tool_id
        assert d["toolResults"][0]["executed"] is True
        assert d["toolResults"][0]["readOnlyOnly"] is True
        assert len(d["providerAuditIds"]) >= 4

    def test_clarify_roundtrip(self, provider_home) -> None:
        result = run_provider_tool_roundtrip(
            "clarify what you mean", "fake",
            selected_tool_ids=frozenset({"clarify"}),
            hermes_home=provider_home,
        )
        d = result.to_safe_dict()
        assert d["status"] == "completed"
        assert d["toolCalls"][0]["name"] == "clarify"
        assert d["toolResults"][0]["executed"] is True

    def test_full_allowlist_roundtrip(self, provider_home) -> None:
        result = run_provider_tool_roundtrip(
            "check route governance", "fake",
            selected_tool_ids=None,  # full allowlist
            hermes_home=provider_home,
        )
        d = result.to_safe_dict()
        assert d["status"] == "completed"
        # Schema carries all 6 tools even though only one is called.
        assert d["schemaSummary"]["toolCount"] == 6


class TestFakeRoundtripBlocked:
    def test_real_mode_blocked(self, provider_home) -> None:
        result = run_provider_tool_roundtrip("x", "real", hermes_home=provider_home)
        d = result.to_safe_dict()
        assert d["status"] == "blocked"
        assert d["blockedReason"] == "blocked_provider_real_mode_not_enabled"
        assert d["providerApiCalled"] is False

    def test_disabled_mode_blocked(self, provider_home) -> None:
        result = run_provider_tool_roundtrip("x", "disabled", hermes_home=provider_home)
        assert result.status == "blocked"
        assert result.blocked_reason == "provider_mode_disabled"


class TestProviderToolCallValidation:
    def test_unknown_tool_blocked(self) -> None:
        call = {"id": "ptc_1", "name": "totally_unknown", "arguments": {}}
        parsed = validate_provider_tool_call(call, allowlist=ALLOWED)
        assert parsed.status == TOOL_CALL_BLOCKED_NOT_ALLOWLISTED

    def test_write_like_tool_blocked(self) -> None:
        call = {"id": "ptc_1", "name": "write_file", "arguments": {}}
        parsed = validate_provider_tool_call(call, allowlist=ALLOWED)
        assert parsed.status == TOOL_CALL_BLOCKED_WRITE_LIKE

    def test_malformed_args_blocked(self) -> None:
        call = {"id": "ptc_1", "name": "route_governance_read", "arguments": "not-an-object"}
        parsed = validate_provider_tool_call(call, allowlist=ALLOWED)
        assert parsed.status == TOOL_CALL_BLOCKED_MALFORMED_ARGS

    def test_secret_in_args_blocked(self) -> None:
        call = {
            "id": "ptc_1", "name": "route_governance_read",
            "arguments": {"x": "sk-abcdefghijklmnopqrstuvwxyz"},
        }
        parsed = validate_provider_tool_call(call, allowlist=ALLOWED)
        assert parsed.status == TOOL_CALL_BLOCKED_MALFORMED_ARGS

    def test_valid_call_passes(self) -> None:
        call = {"id": "ptc_1", "name": "route_governance_read", "arguments": {}}
        parsed = validate_provider_tool_call(call, allowlist=ALLOWED)
        assert parsed.status == TOOL_CALL_VALID

    def test_provider_recursive_blocked(self) -> None:
        # A tool literally named "provider_*" not in the allowlist.
        call = {"id": "ptc_1", "name": "provider_invoke", "arguments": {}}
        parsed = validate_provider_tool_call(call, allowlist=ALLOWED)
        assert parsed.status in {
            TOOL_CALL_BLOCKED_NOT_ALLOWLISTED,
            TOOL_CALL_BLOCKED_PROVIDER_RECURSIVE,
        }


class TestPhase2ACompatibility:
    def test_manual_phase2a_execution_still_works(self, provider_home) -> None:
        """The existing manual execute path is unaffected by the provider branch."""
        from hermes_cli.dev_web_tool_dry_run import dry_run_tool_policy

        dr = dry_run_tool_policy("route_governance_read", {})
        assert dr.decision == "would_allow"
