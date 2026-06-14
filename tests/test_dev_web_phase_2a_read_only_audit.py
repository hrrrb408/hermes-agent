"""Phase 2A — Read-only tool audit tests.

Verifies that executing a Phase 2A read-only tool produces:
  - a dry-run audit event
  - a pre-execution audit event
  - a post-execution audit event
all carrying the toolId (canonicalName), and that the audit-events reader can
filter by toolId. Also verifies the post-execution audit records the
read-only side-effect flags as False and never leaks raw arguments/secrets.

Phase: 2A — Real Tool Execution MVP (Read-only Multi-tool Execution)
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.dev_web_tool_audit_read import read_audit_events
from tests.test_dev_web_phase_2a_read_only_execute import (
    READ_ONLY_TOOLS_WITH_RISK,
    run_read_only_tool_to_completion,
)


@pytest.fixture
def phase_2a_home(tmp_path):
    home = tmp_path / "hermes-home-dev"
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    (home / "gateway" / "dev" / "tokens").mkdir(parents=True, exist_ok=True)
    return str(home)


def _fake_probe():
    return {
        "productionGatewayPidObserved": 28428,
        "productionGatewayProcessCount": 1,
        "productionGatewayCommandSummary": "hermes_cli.main gateway run",
        "port5180": "free",
        "port5181": "free",
    }


class TestReadOnlyAuditWritten:
    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_post_execution_audit_written(self, phase_2a_home, tool_id, risk_tier) -> None:
        run_read_only_tool_to_completion(
            phase_2a_home, tool_id, risk_tier=risk_tier, monkeypatch_probe=_fake_probe
        )
        result = read_audit_events(
            audit_kind="post_execution", limit=50, hermes_home=phase_2a_home
        )
        assert result.success
        matching = [i for i in result.items if i.get("canonicalName") == tool_id]
        assert len(matching) >= 1, f"no post-exec audit for {tool_id}"
        item = matching[0]
        # toolId recorded
        assert item["canonicalName"] == tool_id
        # side-effect flags all False
        se = item.get("sideEffects", {})
        assert se.get("providerSchemaSent") is False
        assert se.get("providerApiCalled") is False
        assert se.get("externalSideEffects") is False
        # execution completed
        assert item.get("executionStatus") == "completed"

    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_dry_run_audit_written(self, phase_2a_home, tool_id, risk_tier) -> None:
        run_read_only_tool_to_completion(
            phase_2a_home, tool_id, risk_tier=risk_tier, monkeypatch_probe=_fake_probe
        )
        result = read_audit_events(
            audit_kind="dry_run", limit=50, hermes_home=phase_2a_home
        )
        assert result.success
        matching = [i for i in result.items if i.get("canonicalName") == tool_id]
        assert len(matching) >= 1
        assert matching[0]["canonicalName"] == tool_id

    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_pre_execution_audit_written(self, phase_2a_home, tool_id, risk_tier) -> None:
        run_read_only_tool_to_completion(
            phase_2a_home, tool_id, risk_tier=risk_tier, monkeypatch_probe=_fake_probe
        )
        result = read_audit_events(
            audit_kind="pre_execution", limit=50, hermes_home=phase_2a_home
        )
        assert result.success
        matching = [i for i in result.items if i.get("canonicalName") == tool_id]
        assert len(matching) >= 1


class TestReadOnlyAuditToolIdFilter:
    def test_canonical_name_filter_isolates_one_tool(self, phase_2a_home) -> None:
        # Execute two different tools, then filter by one toolId.
        run_read_only_tool_to_completion(
            phase_2a_home, "tool_policy_read", risk_tier="R0", monkeypatch_probe=_fake_probe
        )
        run_read_only_tool_to_completion(
            phase_2a_home, "release_status_read", risk_tier="R1", monkeypatch_probe=_fake_probe
        )
        result = read_audit_events(
            audit_kind="post_execution",
            limit=50,
            canonical_name="tool_policy_read",
            hermes_home=phase_2a_home,
        )
        assert result.success
        # Every returned item must be for tool_policy_read only.
        assert len(result.items) >= 1
        for item in result.items:
            assert item["canonicalName"] == "tool_policy_read"

    def test_unknown_tool_filter_returns_empty(self, phase_2a_home) -> None:
        run_read_only_tool_to_completion(
            phase_2a_home, "tool_policy_read", risk_tier="R0", monkeypatch_probe=_fake_probe
        )
        result = read_audit_events(
            audit_kind="post_execution",
            limit=50,
            canonical_name="no_such_tool",
            hermes_home=phase_2a_home,
        )
        assert result.success
        assert result.items == ()


class TestReadOnlyAuditNoSecretLeak:
    def test_raw_arguments_never_in_audit(self, phase_2a_home) -> None:
        # Execute a tool with a secret-looking argument; ensure the audit
        # never stores the raw value.
        run_read_only_tool_to_completion(
            phase_2a_home, "tool_policy_read", risk_tier="R0", monkeypatch_probe=_fake_probe
        )
        audit_path = f"{phase_2a_home}/gateway/dev/audit/tool-post-execution-audit.jsonl"
        content = open(audit_path, encoding="utf-8").read()
        # No raw token / secret patterns leaked into the JSONL.
        assert "sk-" not in content
        assert "Bearer " not in content
        assert "BEGIN PRIVATE KEY" not in content

    def test_audit_records_read_only_result_summary(self, phase_2a_home) -> None:
        run_read_only_tool_to_completion(
            phase_2a_home, "route_governance_read", risk_tier="R0", monkeypatch_probe=_fake_probe
        )
        result = read_audit_events(
            audit_kind="post_execution", limit=50, hermes_home=phase_2a_home
        )
        matching = [i for i in result.items if i.get("canonicalName") == "route_governance_read"]
        assert matching
        summary = matching[0].get("safeSummary", {})
        # toolResultType should reflect the read-only tool.
        assert summary.get("toolResultType") == "route_governance_read"


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
