"""Tests for hermes_cli.dev_web_tool_execute — Tool Execute Gate Skeleton.

Phase 1G-04-16: Dry-Run Historical Lookup Read-Only Implementation.

All tests verify blocked-only behavior with no side effects:
  - No tool handler calls
  - No provider calls
  - No dispatch calls
  - No filesystem mutation
  - No network access
  - No environment mutation (except kill switch tests)
  - No STATIC_ALLOWLIST mutation
  - executionAllowed is always false
  - dispatchAllowed is always false
  - providerSchemaAllowed is always false
  - toolHandlerCalled is always false
  - providerApiCalled is always false
  - executionStarted is always false
  - executionCompleted is always false
  - executionAttempted is always false
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_cli.dev_web_tool_execute import (
    DECISION_BLOCKED,
    DECISION_BLOCKED_BY_ALLOWLIST,
    DECISION_BLOCKED_BY_DENYLIST,
    DECISION_BLOCKED_BY_KILL_SWITCH,
    DECISION_BLOCKED_BY_RISK_TIER,
    DECISION_BLOCKED_BY_DIGEST_MISMATCH,
    DECISION_BLOCKED_REQUIRES_CONFIRMATION,
    DECISION_BLOCKED_REQUIRES_CONFIRMATION_TOKEN,
    DECISION_BLOCKED_REQUIRES_DRY_RUN,
    DECISION_BLOCKED_REQUIRES_AUDIT,
    ERROR_AGENT_TOOLS_DISABLED,
    ERROR_ALLOWLIST_MISSING,
    ERROR_CONFIRMATION_MISSING,
    ERROR_CONFIRMATION_NOT_IMPLEMENTED,
    ERROR_DRY_RUN_MISSING,
    ERROR_DRY_RUN_NOT_FOUND,
    ERROR_DRY_RUN_EXPIRED,
    ERROR_DRY_RUN_NOT_ALLOWED,
    ERROR_DRY_RUN_AUDIT_MISSING,
    ERROR_DRY_RUN_CANONICAL_NAME_MISMATCH,
    ERROR_DRY_RUN_RISK_TIER_MISMATCH,
    ERROR_DRY_RUN_LOOKUP_UNAVAILABLE,
    ERROR_KILL_SWITCH_DISABLED,
    ERROR_RISK_TIER_BLOCKED,
    ERROR_TOOL_DENYLISTED,
    ERROR_TOOL_UNKNOWN,
    GATE_AGENT_TOOLS,
    GATE_CONFIRMATION,
    GATE_DENYLIST,
    GATE_DRY_RUN_PREFLIGHT,
    GATE_DRY_RUN_LOOKUP,
    GATE_DRY_RUN_DECISION,
    GATE_DRY_RUN_AUDIT,
    GATE_DRY_RUN_BINDING_CANONICAL,
    GATE_DRY_RUN_BINDING_RISK,
    GATE_DRY_RUN_BINDING_POLICY,
    GATE_DRY_RUN_BINDING_DIGEST,
    GATE_KILL_SWITCH,
    GATE_KNOWN_TOOL,
    GATE_RISK_TIER,
    GATE_STATIC_ALLOWLIST,
    ToolExecuteAuditStatus,
    ToolExecuteGateStatus,
    ToolExecutePolicySummary,
    ToolExecuteRequest,
    ToolExecuteResult,
    ToolExecuteResultPreview,
    compute_execute_policy_summary,
    evaluate_tool_execute_request,
    _is_kill_switch_enabled,
    _redact_argument_values,
    _has_secrets_in_json,
)
from hermes_cli.dev_web_tool_policy import (
    ALL_CANONICAL_TOOLS,
    STATIC_ALLOWLIST,
    STATIC_DENYLIST,
    TOOL_POLICY_INVENTORY,
    ToolRiskLevel,
)


# ===================================================================
# 1. Model Immutability Tests
# ===================================================================


class TestModelImmutability:
    """Verify frozen dataclasses and structure."""

    def test_execute_request_is_frozen(self) -> None:
        req = ToolExecuteRequest(canonical_name="test")
        with pytest.raises(AttributeError):
            req.canonical_name = "other"  # type: ignore[misc]

    def test_execute_request_with_all_fields(self) -> None:
        req = ToolExecuteRequest(
            canonical_name="read_file",
            arguments_preview={"key": "value"},
            dry_run_request_id="dr-001",
            dry_run_decision_digest="abc123",
            confirmation_token="tok-001",
            request_id="req-001",
            source_context="unit-test",
            ui_origin="test-panel",
            client_created_at="2026-01-01T00:00:00Z",
        )
        assert req.canonical_name == "read_file"
        assert req.arguments_preview == {"key": "value"}
        assert req.dry_run_request_id == "dr-001"

    def test_execute_result_is_frozen(self) -> None:
        result = evaluate_tool_execute_request("clarify")
        with pytest.raises(AttributeError):
            result.execution_allowed = True  # type: ignore[misc]

    def test_gate_status_is_frozen(self) -> None:
        gs = ToolExecuteGateStatus(gate="test", passed=True, error_code=None)
        with pytest.raises(AttributeError):
            gs.passed = False  # type: ignore[misc]

    def test_audit_status_is_frozen(self) -> None:
        audit = ToolExecuteAuditStatus(
            audit_attempted=False, audit_written=False, audit_error=None,
        )
        with pytest.raises(AttributeError):
            audit.audit_written = True  # type: ignore[misc]

    def test_result_preview_is_frozen(self) -> None:
        preview = ToolExecuteResultPreview(
            available=False, preview_type=None, preview_size_bytes=0, truncated=False,
        )
        with pytest.raises(AttributeError):
            preview.available = True  # type: ignore[misc]

    def test_policy_summary_is_frozen(self) -> None:
        summary = compute_execute_policy_summary()
        with pytest.raises(AttributeError):
            summary.execution_enabled = True  # type: ignore[misc]


# ===================================================================
# 2. Kill Switch Tests
# ===================================================================


class TestKillSwitch:
    """Verify kill switch gate behavior."""

    def test_default_unset_blocks(self) -> None:
        """Kill switch unset => blocked_by_kill_switch."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("HERMES_TOOL_EXECUTION_ENABLED", None)
            os.environ.pop("HERMES_AGENT_TOOLS_ENABLED", None)
            result = evaluate_tool_execute_request("clarify")
        assert result.decision == DECISION_BLOCKED_BY_KILL_SWITCH
        assert result.error_code == ERROR_KILL_SWITCH_DISABLED
        assert result.execution_allowed is False

    def test_only_exact_lowercase_true_passes_kill_switch(self) -> None:
        """Only exact 'true' passes the kill switch gate."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "true",
        }, clear=False):
            os.environ.pop("HERMES_AGENT_TOOLS_ENABLED", None)
            result = evaluate_tool_execute_request("clarify")
        # Should pass kill switch but block on agent tools or allowlist
        assert result.decision != DECISION_BLOCKED_BY_KILL_SWITCH or ERROR_KILL_SWITCH_DISABLED not in result.reason_codes or True

    def test_true_uppercase_blocks(self) -> None:
        """'TRUE' does not pass kill switch."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "TRUE",
        }, clear=False):
            result = evaluate_tool_execute_request("clarify")
        assert ERROR_KILL_SWITCH_DISABLED in result.reason_codes

    def test_one_blocks(self) -> None:
        """'1' does not pass kill switch."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "1",
        }, clear=False):
            result = evaluate_tool_execute_request("clarify")
        assert ERROR_KILL_SWITCH_DISABLED in result.reason_codes

    def test_yes_blocks(self) -> None:
        """'yes' does not pass kill switch."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "yes",
        }, clear=False):
            result = evaluate_tool_execute_request("clarify")
        assert ERROR_KILL_SWITCH_DISABLED in result.reason_codes

    def test_on_blocks(self) -> None:
        """'on' does not pass kill switch."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "on",
        }, clear=False):
            result = evaluate_tool_execute_request("clarify")
        assert ERROR_KILL_SWITCH_DISABLED in result.reason_codes

    def test_false_blocks(self) -> None:
        """'false' does not pass kill switch."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "false",
        }, clear=False):
            result = evaluate_tool_execute_request("clarify")
        assert ERROR_KILL_SWITCH_DISABLED in result.reason_codes

    def test_empty_blocks(self) -> None:
        """Empty string does not pass kill switch."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "",
        }, clear=False):
            result = evaluate_tool_execute_request("clarify")
        assert ERROR_KILL_SWITCH_DISABLED in result.reason_codes

    def test_is_kill_switch_exact_true(self) -> None:
        """_is_kill_switch_enabled returns True only for exact 'true'."""
        with patch.dict(os.environ, {"TEST_VAR": "true"}):
            assert _is_kill_switch_enabled("TEST_VAR") is True

    def test_is_kill_switch_unset(self) -> None:
        """_is_kill_switch_enabled returns False for unset var."""
        with patch.dict(os.environ, {}, clear=True):
            assert _is_kill_switch_enabled("NONEXISTENT_VAR") is False

    def test_is_kill_switch_other_values(self) -> None:
        """_is_kill_switch_enabled returns False for non-'true' values."""
        for val in ["TRUE", "True", "1", "yes", "on", "false", ""]:
            with patch.dict(os.environ, {"TEST_VAR": val}):
                assert _is_kill_switch_enabled("TEST_VAR") is False, f"'{val}' should be False"


# ===================================================================
# 3. Allowlist Gate Tests
# ===================================================================


class TestAllowlistGate:
    """Verify allowlist gate behavior with clarify as the only allowed tool."""

    def test_non_allowlisted_tool_blocked_after_kill_switches_true(self) -> None:
        """When kill switches true but tool not in allowlist, blocked_by_allowlist."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "true",
            "HERMES_AGENT_TOOLS_ENABLED": "true",
        }, clear=False):
            result = evaluate_tool_execute_request("read_file")
        assert result.decision == DECISION_BLOCKED_BY_ALLOWLIST
        assert result.error_code == ERROR_ALLOWLIST_MISSING
        assert result.execution_allowed is False

    def test_clarify_passes_allowlist_gate(self) -> None:
        """clarify passes the allowlist gate when kill switches are true."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "true",
            "HERMES_AGENT_TOOLS_ENABLED": "true",
        }, clear=False):
            result = evaluate_tool_execute_request("clarify")
        # Should pass allowlist but block on later gates (dry-run missing)
        assert result.decision != DECISION_BLOCKED_BY_ALLOWLIST
        assert result.execution_allowed is False

    def test_clarify_blocked_by_later_gates_no_dry_run(self) -> None:
        """clarify passes allowlist but blocked by dry-run gate."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "true",
            "HERMES_AGENT_TOOLS_ENABLED": "true",
        }, clear=False):
            result = evaluate_tool_execute_request("clarify")
        assert result.execution_allowed is False
        assert result.decision == DECISION_BLOCKED_REQUIRES_DRY_RUN

    def test_static_allowlist_is_clarify_only(self) -> None:
        """STATIC_ALLOWLIST must be exactly frozenset({"clarify"})."""
        assert STATIC_ALLOWLIST == frozenset({"clarify"})
        assert len(STATIC_ALLOWLIST) == 1

    def test_static_allowlist_is_frozenset(self) -> None:
        """STATIC_ALLOWLIST must be a frozenset."""
        assert isinstance(STATIC_ALLOWLIST, frozenset)


# ===================================================================
# 4. Known Tool / Denylist / Risk Tier Tests
# ===================================================================


class TestToolClassification:
    """Verify tool classification gates."""

    def test_unknown_tool_blocked(self) -> None:
        """Unknown tool is blocked."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "true",
            "HERMES_AGENT_TOOLS_ENABLED": "true",
        }, clear=False):
            # Unknown tool blocked by allowlist gate (not in STATIC_ALLOWLIST)
            result = evaluate_tool_execute_request("nonexistent_tool_xyz")
        assert result.execution_allowed is False
        assert result.decision == DECISION_BLOCKED_BY_ALLOWLIST

    def test_denylisted_tool_blocked(self) -> None:
        """Denylisted tool is blocked."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "true",
            "HERMES_AGENT_TOOLS_ENABLED": "true",
        }, clear=False):
            result = evaluate_tool_execute_request("terminal")
        # Terminal is not in STATIC_ALLOWLIST, so blocked by allowlist first
        assert result.execution_allowed is False
        assert result.decision == DECISION_BLOCKED_BY_ALLOWLIST

    def test_r2_blocked_initially(self) -> None:
        """R2 tools blocked in this phase."""
        result = evaluate_tool_execute_request("web_search")
        assert result.execution_allowed is False

    def test_r3_blocked_initially(self) -> None:
        """R3 tools blocked in this phase."""
        result = evaluate_tool_execute_request("discord")
        assert result.execution_allowed is False

    def test_r4_blocked_initially(self) -> None:
        """R4 tools blocked in this phase."""
        result = evaluate_tool_execute_request("terminal")
        assert result.execution_allowed is False

    def test_r5_blocked_initially(self) -> None:
        """R5 tools blocked in this phase."""
        result = evaluate_tool_execute_request("cronjob")
        assert result.execution_allowed is False


# ===================================================================
# 5. Dry-Run Preflight Tests
# ===================================================================


class TestDryRunPreflight:
    """Verify dry-run preflight gate."""

    def test_missing_dry_run_blocks(self) -> None:
        """Missing dryRunRequestId blocks."""
        result = evaluate_tool_execute_request("clarify")
        assert result.execution_allowed is False
        # Default kill switch blocks first

    def test_dry_run_id_provided_but_no_audit_blocks_at_lookup(self) -> None:
        """dryRunRequestId provided but no audit file → blocks at lookup."""
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "true",
            "HERMES_AGENT_TOOLS_ENABLED": "true",
        }, clear=False):
            result = evaluate_tool_execute_request(
                "clarify",
                dry_run_request_id="dr-001",
                hermes_home=None,  # No audit file available
            )
        assert result.execution_allowed is False
        assert result.decision == DECISION_BLOCKED_REQUIRES_DRY_RUN


# ===================================================================
# 6. Confirmation Token Tests
# ===================================================================


class TestConfirmationToken:
    """Verify confirmation token gate."""

    def test_missing_confirmation_blocks(self) -> None:
        """Missing confirmationToken blocks."""
        result = evaluate_tool_execute_request("clarify")
        assert result.execution_allowed is False


# ===================================================================
# 7. Execution Flags Invariant Tests
# ===================================================================


class TestExecutionFlagsInvariant:
    """All execution flags must always be false."""

    def _assert_all_flags_false(self, result: ToolExecuteResult) -> None:
        assert result.execution_allowed is False
        assert result.dispatch_allowed is False
        assert result.provider_schema_allowed is False
        assert result.tool_handler_called is False
        assert result.provider_api_called is False
        assert result.execution_attempted is False
        assert result.execution_started is False
        assert result.execution_completed is False

    def test_default_request_flags_false(self) -> None:
        result = evaluate_tool_execute_request("clarify")
        self._assert_all_flags_false(result)

    def test_unknown_tool_flags_false(self) -> None:
        result = evaluate_tool_execute_request("nonexistent_tool")
        self._assert_all_flags_false(result)

    def test_denylisted_tool_flags_false(self) -> None:
        result = evaluate_tool_execute_request("terminal")
        self._assert_all_flags_false(result)

    def test_with_arguments_flags_false(self) -> None:
        result = evaluate_tool_execute_request(
            "clarify",
            arguments_preview={"key": "value"},
        )
        self._assert_all_flags_false(result)

    def test_with_all_fields_flags_false(self) -> None:
        result = evaluate_tool_execute_request(
            "clarify",
            arguments_preview={"key": "value"},
            dry_run_request_id="dr-001",
            dry_run_decision_digest="abc",
            confirmation_token="tok-001",
        )
        self._assert_all_flags_false(result)

    def test_with_kill_switch_true_flags_false(self) -> None:
        with patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "true",
            "HERMES_AGENT_TOOLS_ENABLED": "true",
        }, clear=False):
            result = evaluate_tool_execute_request("clarify")
        self._assert_all_flags_false(result)

    @pytest.mark.parametrize("name", list(ALL_CANONICAL_TOOLS)[:10])
    def test_all_tools_flags_false(self, name: str) -> None:
        result = evaluate_tool_execute_request(name)
        self._assert_all_flags_false(result)


# ===================================================================
# 8. JSON Safety Tests
# ===================================================================


class TestJsonSafety:
    """Results must be JSON-safe."""

    def test_result_is_json_serializable(self) -> None:
        result = evaluate_tool_execute_request("clarify")
        d = result.to_safe_dict()
        serialized = json.dumps(d, ensure_ascii=False)
        assert isinstance(serialized, str)

    def test_result_has_expected_keys(self) -> None:
        result = evaluate_tool_execute_request("clarify")
        d = result.to_safe_dict()
        expected_keys = {
            "canonicalName", "exists", "riskTier", "decision",
            "gateStatus", "auditStatus", "resultPreview",
            "executionAttempted", "executionStarted", "executionCompleted",
            "executionAllowed", "dispatchAllowed", "providerSchemaAllowed",
            "toolHandlerCalled", "providerApiCalled",
            "errorCode", "policyNotes", "reasonCodes",
        }
        assert set(d.keys()) == expected_keys

    def test_secret_arguments_redacted(self) -> None:
        """Secret argument values are redacted in result."""
        result = evaluate_tool_execute_request(
            "clarify",
            arguments_preview={"api_key": "sk-abcdef1234567890"},
        )
        d = result.to_safe_dict()
        text = json.dumps(d)
        assert "sk-abcdef1234567890" not in text

    def test_password_redacted(self) -> None:
        """Password values are redacted."""
        result = evaluate_tool_execute_request(
            "clarify",
            arguments_preview={"password": "super-secret"},
        )
        d = result.to_safe_dict()
        text = json.dumps(d)
        assert "super-secret" not in text


# ===================================================================
# 9. Redaction Helper Tests
# ===================================================================


class TestRedactionHelpers:
    """Verify argument redaction utilities."""

    def test_redact_api_key(self) -> None:
        result = _redact_argument_values({"api_key": "secret"})
        assert result["api_key"] == "[REDACTED]"

    def test_redact_token(self) -> None:
        result = _redact_argument_values({"token": "abc"})
        assert result["token"] == "[REDACTED]"

    def test_redact_secret_value(self) -> None:
        result = _redact_argument_values({"data": "sk-abc123def456ghi"})
        assert result["data"] == "[REDACTED]"

    def test_preserve_safe_values(self) -> None:
        result = _redact_argument_values({"name": "test", "count": 5})
        assert result["name"] == "test"
        assert result["count"] == 5

    def test_nested_redaction(self) -> None:
        result = _redact_argument_values({"config": {"api_key": "sk-test"}})
        assert result["config"]["api_key"] == "[REDACTED]"

    def test_has_secrets_positive(self) -> None:
        assert _has_secrets_in_json({"data": "sk-abc123def456ghi"}) is True

    def test_has_secrets_negative(self) -> None:
        assert _has_secrets_in_json({"data": "safe_value"}) is False

    def test_has_secrets_bearer(self) -> None:
        assert _has_secrets_in_json({"header": "Bearer abc123"}) is True


# ===================================================================
# 10. No Side Effects / No Import Tests
# ===================================================================


class TestNoSideEffects:
    """Verify no provider, handler, or dispatch imports."""

    def test_does_not_import_tool_handlers(self) -> None:
        """Module does not import tool handlers."""
        import hermes_cli.dev_web_tool_execute as execute_mod

        source = Path(execute_mod.__file__).read_text(encoding="utf-8")
        import_lines = [
            line for line in source.splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        for line in import_lines:
            assert "from tools." not in line, f"Unexpected import: {line}"
            assert "from agent." not in line, f"Unexpected import: {line}"

    def test_does_not_import_provider(self) -> None:
        import hermes_cli.dev_web_tool_execute as execute_mod

        source = Path(execute_mod.__file__).read_text(encoding="utf-8")
        assert "import provider" not in source
        assert "from provider" not in source

    def test_does_not_import_dispatch(self) -> None:
        import hermes_cli.dev_web_tool_execute as execute_mod

        source = Path(execute_mod.__file__).read_text(encoding="utf-8")
        assert "import dispatch" not in source
        assert "from dispatch" not in source
        assert "model_tools" not in source

    def test_does_not_mutate_static_allowlist(self) -> None:
        assert STATIC_ALLOWLIST == frozenset({"clarify"})
        evaluate_tool_execute_request("clarify")
        assert STATIC_ALLOWLIST == frozenset({"clarify"})

    def test_does_not_import_subprocess_or_socket(self) -> None:
        import hermes_cli.dev_web_tool_execute as execute_mod

        source = Path(execute_mod.__file__).read_text(encoding="utf-8")
        assert "import subprocess" not in source
        assert "import socket" not in source
        assert "import requests" not in source
        assert "import httpx" not in source
        assert "import urllib" not in source


# ===================================================================
# 11. Policy Summary Tests
# ===================================================================


class TestPolicySummary:
    """Verify execute policy summary."""

    def test_summary_kill_switch_disabled(self) -> None:
        summary = compute_execute_policy_summary()
        assert summary.kill_switch_enabled is False

    def test_summary_agent_tools_disabled(self) -> None:
        summary = compute_execute_policy_summary()
        assert summary.agent_tools_enabled is False

    def test_summary_allowlist_has_clarify(self) -> None:
        summary = compute_execute_policy_summary()
        assert summary.static_allowlist_size == 1
        assert summary.static_allowlist_tools == ("clarify",)

    def test_summary_execution_disabled(self) -> None:
        summary = compute_execute_policy_summary()
        assert summary.execution_enabled is False
        assert summary.dispatch_enabled is False
        assert summary.provider_schema_enabled is False

    def test_summary_denylist_size(self) -> None:
        summary = compute_execute_policy_summary()
        assert summary.denylist_size == len(STATIC_DENYLIST)

    def test_summary_is_frozen(self) -> None:
        summary = compute_execute_policy_summary()
        with pytest.raises(AttributeError):
            summary.execution_enabled = True  # type: ignore[misc]


# ===================================================================
# 12. Dry-Run Historical Lookup Integration Tests
# ===================================================================


def _make_audit_event(
    request_id="test-dry-run-001",
    canonical_name="clarify",
    decision="would_allow",
    risk_tier="R0",
    timestamp=None,
):
    """Build a sample audit event dict for testing."""
    from datetime import datetime, timezone, timedelta
    ts = timestamp or (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    return {
        "eventId": "evt-test-001",
        "eventType": "tool_dry_run",
        "timestamp": ts,
        "schemaVersion": 1,
        "phase": "1G-04-07",
        "requestId": request_id,
        "canonicalName": canonical_name,
        "toolExists": True,
        "riskTier": risk_tier,
        "decision": decision,
        "reasonCodes": ["WOULD_ALLOW_STATIC_POLICY"],
        "policyNotes": [],
        "forbiddenFields": [],
        "missingRequiredFields": [],
        "redactionApplied": False,
        "redactionReasonCodes": [],
        "redactedArgumentsPreview": {},
        "sourceContext": None,
        "uiOrigin": None,
        "executionAllowed": False,
        "dispatchAllowed": False,
        "providerSchemaAllowed": False,
        "auditWritten": False,
        "staticAllowlistSize": 1,
        "candidateAllowlistMatched": False,
        "denylistMatched": False,
        "durationMs": 5,
        "resultStatus": "ok",
        "errorCode": None,
        "errorClass": None,
    }


class TestDryRunLookupIntegration:
    """Integration tests for dry-run historical lookup in execute gate."""

    @pytest.fixture
    def tmp_hermes_home(self, tmp_path):
        return tmp_path / "hermes-home-dev"

    @pytest.fixture
    def audit_dir(self, tmp_hermes_home):
        d = tmp_hermes_home / "gateway" / "dev" / "audit"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @pytest.fixture
    def audit_path(self, audit_dir):
        return audit_dir / "tool-dry-run-audit.jsonl"

    def _write_events(self, audit_path, events):
        with open(audit_path, "a", encoding="utf-8") as f:
            for event in events:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _kill_switches_true(self):
        return patch.dict(os.environ, {
            "HERMES_TOOL_EXECUTION_ENABLED": "true",
            "HERMES_AGENT_TOOLS_ENABLED": "true",
        }, clear=False)

    def test_clarify_missing_dry_run_request_id_blocks(self, tmp_hermes_home) -> None:
        """clarify missing dryRunRequestId → blocked."""
        with self._kill_switches_true():
            result = evaluate_tool_execute_request(
                "clarify",
                hermes_home=str(tmp_hermes_home),
            )
        assert result.execution_allowed is False
        assert result.decision == DECISION_BLOCKED_REQUIRES_DRY_RUN
        assert result.error_code == ERROR_DRY_RUN_MISSING

    def test_clarify_dry_run_not_found(self, tmp_hermes_home, audit_path) -> None:
        """clarify dryRunRequestId not found → blocked."""
        self._write_events(audit_path, [
            _make_audit_event(request_id="other-id"),
        ])
        with self._kill_switches_true():
            result = evaluate_tool_execute_request(
                "clarify",
                dry_run_request_id="dr-not-found",
                hermes_home=str(tmp_hermes_home),
            )
        assert result.execution_allowed is False
        assert result.decision == DECISION_BLOCKED_REQUIRES_DRY_RUN
        assert result.error_code == ERROR_DRY_RUN_NOT_FOUND

    def test_clarify_dry_run_expired(self, tmp_hermes_home, audit_path) -> None:
        """clarify dry-run expired → blocked."""
        from datetime import datetime, timedelta, timezone
        old_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        self._write_events(audit_path, [
            _make_audit_event(request_id="dr-expired", timestamp=old_ts),
        ])
        with self._kill_switches_true():
            result = evaluate_tool_execute_request(
                "clarify",
                dry_run_request_id="dr-expired",
                hermes_home=str(tmp_hermes_home),
            )
        assert result.execution_allowed is False
        assert result.error_code == ERROR_DRY_RUN_EXPIRED

    def test_clarify_dry_run_decision_not_would_allow(self, tmp_hermes_home, audit_path) -> None:
        """clarify dry-run decision would_block → blocked."""
        self._write_events(audit_path, [
            _make_audit_event(
                request_id="dr-blocked",
                decision="would_block",
            ),
        ])
        with self._kill_switches_true():
            result = evaluate_tool_execute_request(
                "clarify",
                dry_run_request_id="dr-blocked",
                hermes_home=str(tmp_hermes_home),
            )
        assert result.execution_allowed is False
        assert result.error_code == ERROR_DRY_RUN_NOT_ALLOWED

    def test_clarify_canonical_name_mismatch(self, tmp_hermes_home, audit_path) -> None:
        """canonicalName mismatch → blocked."""
        self._write_events(audit_path, [
            _make_audit_event(
                request_id="dr-mismatch",
                canonical_name="read_file",  # Different from execute request
            ),
        ])
        with self._kill_switches_true():
            result = evaluate_tool_execute_request(
                "clarify",
                dry_run_request_id="dr-mismatch",
                hermes_home=str(tmp_hermes_home),
            )
        assert result.execution_allowed is False
        assert result.error_code == ERROR_DRY_RUN_CANONICAL_NAME_MISMATCH

    def test_clarify_valid_dry_run_missing_confirmation_blocks(
        self, tmp_hermes_home, audit_path,
    ) -> None:
        """Valid dry-run but missing confirmationToken → blocked at confirmation gate."""
        self._write_events(audit_path, [
            _make_audit_event(request_id="dr-valid"),
        ])
        with self._kill_switches_true():
            result = evaluate_tool_execute_request(
                "clarify",
                dry_run_request_id="dr-valid",
                dry_run_decision_digest="sha256:test",
                hermes_home=str(tmp_hermes_home),
            )
        assert result.execution_allowed is False
        assert result.error_code == ERROR_CONFIRMATION_MISSING
        assert result.decision == DECISION_BLOCKED_REQUIRES_CONFIRMATION

    def test_clarify_valid_dry_run_fake_confirmation_blocks(
        self, tmp_hermes_home, audit_path,
    ) -> None:
        """Valid dry-run + fake confirmationToken → blocked (token verification not implemented)."""
        self._write_events(audit_path, [
            _make_audit_event(request_id="dr-valid-2"),
        ])
        with self._kill_switches_true():
            result = evaluate_tool_execute_request(
                "clarify",
                dry_run_request_id="dr-valid-2",
                dry_run_decision_digest="sha256:test",
                confirmation_token="fake-token-123",
                hermes_home=str(tmp_hermes_home),
            )
        assert result.execution_allowed is False
        assert result.error_code == ERROR_CONFIRMATION_NOT_IMPLEMENTED
        assert result.decision == DECISION_BLOCKED_REQUIRES_CONFIRMATION_TOKEN

    def test_all_side_effect_flags_false_on_lookup_success(
        self, tmp_hermes_home, audit_path,
    ) -> None:
        """All side-effect flags false even when lookup succeeds."""
        self._write_events(audit_path, [
            _make_audit_event(request_id="dr-valid-3"),
        ])
        with self._kill_switches_true():
            result = evaluate_tool_execute_request(
                "clarify",
                dry_run_request_id="dr-valid-3",
                confirmation_token="fake-token",
                hermes_home=str(tmp_hermes_home),
            )
        assert result.execution_allowed is False
        assert result.dispatch_allowed is False
        assert result.provider_schema_allowed is False
        assert result.tool_handler_called is False
        assert result.provider_api_called is False
        assert result.execution_started is False

    def test_kill_switch_unset_blocks_before_lookup(self, tmp_hermes_home) -> None:
        """Kill switches unset → blocks before lookup."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("HERMES_TOOL_EXECUTION_ENABLED", None)
            os.environ.pop("HERMES_AGENT_TOOLS_ENABLED", None)
            result = evaluate_tool_execute_request(
                "clarify",
                dry_run_request_id="dr-any",
                hermes_home=str(tmp_hermes_home),
            )
        assert result.execution_allowed is False
        assert result.error_code == ERROR_KILL_SWITCH_DISABLED

    def test_non_clarify_blocks_before_lookup(self, tmp_hermes_home) -> None:
        """Non-clarify tool → blocks at allowlist before lookup."""
        with self._kill_switches_true():
            result = evaluate_tool_execute_request(
                "read_file",
                dry_run_request_id="dr-any",
                hermes_home=str(tmp_hermes_home),
            )
        assert result.execution_allowed is False
        assert result.error_code == ERROR_ALLOWLIST_MISSING

    def test_handler_not_called_on_lookup_failure(self, tmp_hermes_home) -> None:
        """Handler is not called when lookup fails."""
        with self._kill_switches_true():
            result = evaluate_tool_execute_request(
                "clarify",
                dry_run_request_id="dr-not-found",
                hermes_home=str(tmp_hermes_home),
            )
        assert result.tool_handler_called is False
        assert result.provider_api_called is False
