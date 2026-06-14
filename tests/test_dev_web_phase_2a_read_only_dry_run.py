"""Phase 2A — Read-only tool dry-run tests.

Verifies the dry-run subsystem (already tool-agnostic) admits each Phase 2A
read-only tool: the dry-run decision is ``would_allow``, the risk tier matches
the inventory, and the execution/dispatch/provider/audit flags stay False.
Also confirms the dry-run route does NOT need a new HTTP route and that
unsupported tools still block.

Phase: 2A — Real Tool Execution MVP (Read-only Multi-tool Execution)
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_tool_dry_run import (
    DRY_RUN_DECISION_WOULD_ALLOW,
    DRY_RUN_ONLY_NO_EXECUTION,
    WOULD_ALLOW_STATIC_POLICY,
    dry_run_tool_policy,
)

# (tool_id, expected_risk_tier)
READ_ONLY_TOOLS_WITH_RISK = [
    ("tool_policy_read", "R0"),
    ("route_governance_read", "R0"),
    ("audit_events_read", "R1"),
    ("dev_environment_read", "R1"),
    ("release_status_read", "R1"),
]


class TestReadOnlyDryRun:
    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_dry_run_would_allow(self, tool_id: str, risk_tier: str) -> None:
        result = dry_run_tool_policy(tool_id, None)
        assert result.decision == DRY_RUN_DECISION_WOULD_ALLOW
        assert result.risk_tier == risk_tier
        assert result.exists is True

    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_dry_run_flags_all_false(self, tool_id: str, risk_tier: str) -> None:
        result = dry_run_tool_policy(tool_id, None)
        d = result.to_safe_dict()
        assert d["executionAllowed"] is False
        assert d["dispatchAllowed"] is False
        assert d["providerSchemaAllowed"] is False
        assert d["auditWritten"] is False

    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_dry_run_has_static_policy_reason(self, tool_id: str, risk_tier: str) -> None:
        result = dry_run_tool_policy(tool_id, None)
        assert WOULD_ALLOW_STATIC_POLICY in result.reason_codes
        assert DRY_RUN_ONLY_NO_EXECUTION in result.reason_codes

    @pytest.mark.parametrize("tool_id,risk_tier", READ_ONLY_TOOLS_WITH_RISK)
    def test_dry_run_arguments_are_redacted(self, tool_id: str, risk_tier: str) -> None:
        # Secret-looking arguments must be redacted in the preview, never leaked.
        result = dry_run_tool_policy(tool_id, {"token": "sk-supersecret123456"})
        preview = result.to_safe_dict()["redactedArgumentsPreview"]
        # The forbidden key must appear in forbiddenFields and be redacted.
        assert "token" in result.to_safe_dict()["forbiddenFields"] or any(
            "REDACT" in str(c).upper() for c in result.reason_codes
        )
        # Never the raw secret in the preview.
        assert "sk-supersecret123456" not in str(preview)

    def test_dry_run_does_not_mutate_static_allowlist(self) -> None:
        from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

        before = frozenset(STATIC_ALLOWLIST)
        for tool_id, _ in READ_ONLY_TOOLS_WITH_RISK:
            dry_run_tool_policy(tool_id, None)
        assert STATIC_ALLOWLIST == before


class TestReadOnlyDryRunBlocksUnsupported:
    def test_unknown_tool_blocks(self) -> None:
        result = dry_run_tool_policy("definitely_not_a_tool", None)
        assert result.decision != DRY_RUN_DECISION_WOULD_ALLOW
        assert result.exists is False

    def test_write_like_tool_blocks(self) -> None:
        # write_file is permanently denied (R3) — never would_allow.
        result = dry_run_tool_policy("write_file", None)
        assert result.decision != DRY_RUN_DECISION_WOULD_ALLOW

    def test_provider_like_tool_blocks(self) -> None:
        # web_search is R2 (network read) — requires_review, not would_allow.
        result = dry_run_tool_policy("web_search", None)
        assert result.decision != DRY_RUN_DECISION_WOULD_ALLOW


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
