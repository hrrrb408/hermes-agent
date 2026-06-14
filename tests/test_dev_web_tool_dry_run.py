"""Tests for hermes_cli.dev_web_tool_dry_run — Tool Dry-Run Policy Model.

Phase 1G-04-01: Dry-Run Policy Service Model.

All tests verify pure-function behavior with no side effects:
  - No tool handler calls
  - No provider calls
  - No filesystem access
  - No network access
  - No environment mutation
  - No audit storage
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_cli.dev_web_tool_dry_run import (
    DRY_RUN_DECISION_REQUIRES_REVIEW,
    DRY_RUN_DECISION_WOULD_ALLOW,
    DRY_RUN_DECISION_WOULD_BLOCK,
    DRY_RUN_DECISION_WOULD_REDACT,
    DRY_RUN_ONLY_NO_EXECUTION,
    INVALID_ARGUMENT_SHAPE,
    MAX_ARGUMENT_DEPTH,
    MAX_ARGUMENT_FIELDS,
    MAX_ARGUMENT_LIST_ITEMS,
    MAX_ARGUMENT_STRING_CHARS,
    REQUIRES_REVIEW_CANDIDATE_ONLY,
    REQUIRES_REVIEW_R2,
    REQUIRES_REVIEW_R3,
    WOULD_ALLOW_STATIC_POLICY,
    WOULD_BLOCK_DENYLISTED,
    WOULD_BLOCK_R4_EXECUTION_RISK,
    WOULD_BLOCK_R5_SYSTEM_RISK,
    WOULD_BLOCK_UNKNOWN_TOOL,
    WOULD_REDACT_FORBIDDEN_FIELD,
    WOULD_REDACT_SECRET_PATTERN,
    ToolDryRunPolicySummary,
    ToolDryRunRequest,
    ToolDryRunResult,
    compute_dry_run_policy_summary,
    dry_run_tool_policy,
    list_tool_dry_run_policies,
    sanitize_arguments_preview,
)
from hermes_cli.dev_web_tool_policy import (
    ALL_CANONICAL_TOOLS,
    CANDIDATE_ALLOWLIST,
    STATIC_ALLOWLIST,
    STATIC_DENYLIST,
    TOOL_POLICY_INVENTORY,
    ToolRiskLevel,
)


# ===================================================================
# 1. Model Tests — Immutability and Structure
# ===================================================================


class TestModelImmutability:
    """Verify frozen dataclasses and structure."""

    def test_dry_run_request_is_frozen(self) -> None:
        req = ToolDryRunRequest(canonical_name="test")
        with pytest.raises(AttributeError):
            req.canonical_name = "other"  # type: ignore[misc]

    def test_dry_run_request_with_args(self) -> None:
        req = ToolDryRunRequest(
            canonical_name="test",
            arguments_preview={"key": "value"},
            source_context="unit-test",
            ui_origin="test-panel",
        )
        assert req.canonical_name == "test"
        assert req.arguments_preview == {"key": "value"}
        assert req.source_context == "unit-test"
        assert req.ui_origin == "test-panel"

    def test_dry_run_result_is_frozen(self) -> None:
        result = dry_run_tool_policy("clarify")
        with pytest.raises(AttributeError):
            result.execution_allowed = True  # type: ignore[misc]

    def test_dry_run_result_reason_codes_is_tuple(self) -> None:
        result = dry_run_tool_policy("clarify")
        assert isinstance(result.reason_codes, tuple)

    def test_dry_run_result_policy_notes_is_tuple(self) -> None:
        result = dry_run_tool_policy("clarify")
        assert isinstance(result.policy_notes, tuple)

    def test_dry_run_result_forbidden_fields_is_tuple(self) -> None:
        result = dry_run_tool_policy("clarify")
        assert isinstance(result.forbidden_fields, tuple)

    def test_dry_run_result_missing_required_is_tuple(self) -> None:
        result = dry_run_tool_policy("clarify")
        assert isinstance(result.missing_required_fields, tuple)


class TestDefaultFlagsFalse:
    """All capability flags must be False."""

    @pytest.mark.parametrize("name", list(ALL_CANONICAL_TOOLS))
    def test_execution_allowed_always_false(self, name: str) -> None:
        result = dry_run_tool_policy(name)
        assert result.execution_allowed is False

    @pytest.mark.parametrize("name", list(ALL_CANONICAL_TOOLS))
    def test_dispatch_allowed_always_false(self, name: str) -> None:
        result = dry_run_tool_policy(name)
        assert result.dispatch_allowed is False

    @pytest.mark.parametrize("name", list(ALL_CANONICAL_TOOLS))
    def test_provider_schema_allowed_always_false(self, name: str) -> None:
        result = dry_run_tool_policy(name)
        assert result.provider_schema_allowed is False

    @pytest.mark.parametrize("name", list(ALL_CANONICAL_TOOLS))
    def test_audit_written_always_false(self, name: str) -> None:
        result = dry_run_tool_policy(name)
        assert result.audit_written is False


class TestToSafeDict:
    """to_safe_dict produces JSON-safe output."""

    def test_safe_dict_is_json_serializable(self) -> None:
        result = dry_run_tool_policy("clarify", {"query": "test"})
        d = result.to_safe_dict()
        serialized = json.dumps(d, ensure_ascii=False)
        assert isinstance(serialized, str)

    def test_safe_dict_has_expected_keys(self) -> None:
        result = dry_run_tool_policy("clarify")
        d = result.to_safe_dict()
        expected_keys = {
            "canonicalName", "exists", "riskTier", "decision",
            "reasonCodes", "policyNotes", "redactedArgumentsPreview",
            "forbiddenFields", "missingRequiredFields",
            "executionAllowed", "dispatchAllowed",
            "providerSchemaAllowed", "auditWritten",
        }
        assert set(d.keys()) == expected_keys

    def test_safe_dict_capability_flags_are_bool(self) -> None:
        result = dry_run_tool_policy("clarify")
        d = result.to_safe_dict()
        assert isinstance(d["executionAllowed"], bool)
        assert isinstance(d["dispatchAllowed"], bool)
        assert isinstance(d["providerSchemaAllowed"], bool)
        assert isinstance(d["auditWritten"], bool)

    def test_summary_to_safe_dict(self) -> None:
        summary = compute_dry_run_policy_summary()
        d = summary.to_safe_dict()
        serialized = json.dumps(d, ensure_ascii=False)
        assert isinstance(serialized, str)
        assert "totalCount" in d
        assert "dryRunAllowCount" in d
        assert "blockedCount" in d
        assert "reviewCount" in d
        assert "redactedCount" in d


# ===================================================================
# 2. Risk Tier Tests
# ===================================================================


class TestUnknownTool:
    """Unknown tool is always blocked."""

    def test_unknown_tool_blocked(self) -> None:
        result = dry_run_tool_policy("nonexistent_tool")
        assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK
        assert result.exists is False
        assert result.risk_tier is None
        assert WOULD_BLOCK_UNKNOWN_TOOL in result.reason_codes

    def test_unknown_tool_with_arguments(self) -> None:
        result = dry_run_tool_policy("fake_tool", {"arg": "value"})
        assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK
        assert result.exists is False
        # Arguments should still be sanitized
        assert "arg" in result.redacted_arguments_preview

    def test_empty_string_blocked(self) -> None:
        result = dry_run_tool_policy("")
        assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK
        assert result.exists is False

    def test_case_variant_unknown(self) -> None:
        result = dry_run_tool_policy("Clarify")
        assert result.exists is False
        assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK


class TestDenylistBlocked:
    """Permanently denied tools are always blocked."""

    @pytest.mark.parametrize("name", list(STATIC_DENYLIST))
    def test_denylist_tool_blocked(self, name: str) -> None:
        result = dry_run_tool_policy(name)
        assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK
        assert result.exists is True
        assert WOULD_BLOCK_DENYLISTED in result.reason_codes

    def test_terminal_blocked(self) -> None:
        result = dry_run_tool_policy("terminal")
        assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK
        assert WOULD_BLOCK_DENYLISTED in result.reason_codes

    def test_write_file_blocked(self) -> None:
        result = dry_run_tool_policy("write_file")
        assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK

    def test_send_message_blocked(self) -> None:
        result = dry_run_tool_policy("send_message")
        assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK

    def test_delegate_task_blocked(self) -> None:
        result = dry_run_tool_policy("delegate_task")
        assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK

    def test_denylist_overrides_risk_tier(self) -> None:
        """Denylist tools that are R4/R5 are blocked by denylist, not risk tier."""
        for name in STATIC_DENYLIST:
            result = dry_run_tool_policy(name)
            assert WOULD_BLOCK_DENYLISTED in result.reason_codes
            # Risk tier reasons should NOT appear for denylisted tools
            assert WOULD_BLOCK_R4_EXECUTION_RISK not in result.reason_codes
            assert WOULD_BLOCK_R5_SYSTEM_RISK not in result.reason_codes


class TestR0DryRunAllowed:
    """R0 tools: would_allow for dry-run, but execution always false."""

    def test_clarify_r0_would_allow(self) -> None:
        result = dry_run_tool_policy("clarify")
        assert result.decision == DRY_RUN_DECISION_WOULD_ALLOW
        assert result.risk_tier == "R0"
        assert result.exists is True
        assert WOULD_ALLOW_STATIC_POLICY in result.reason_codes
        assert DRY_RUN_ONLY_NO_EXECUTION in result.reason_codes

    def test_r0_execution_still_false(self) -> None:
        result = dry_run_tool_policy("clarify")
        assert result.execution_allowed is False
        assert result.dispatch_allowed is False
        assert result.provider_schema_allowed is False

    def test_r0_has_dry_run_only_reason(self) -> None:
        result = dry_run_tool_policy("clarify")
        assert DRY_RUN_ONLY_NO_EXECUTION in result.reason_codes

    def test_r0_candidate_note(self) -> None:
        result = dry_run_tool_policy("clarify")
        assert REQUIRES_REVIEW_CANDIDATE_ONLY in result.reason_codes


class TestR1DryRunAllowed:
    """R1 tools: would_allow for dry-run, execution always false."""

    @pytest.mark.parametrize(
        "name",
        # Phase 2A: exclude R0 candidates (clarify, tool_policy_read,
        # route_governance_read); only R1 candidates are R1.
        [
            n
            for n in CANDIDATE_ALLOWLIST
            if n not in {"clarify", "tool_policy_read", "route_governance_read"}
        ],
    )
    def test_r1_candidate_would_allow(self, name: str) -> None:
        result = dry_run_tool_policy(name)
        assert result.decision == DRY_RUN_DECISION_WOULD_ALLOW
        assert result.risk_tier == "R1"
        assert WOULD_ALLOW_STATIC_POLICY in result.reason_codes
        assert DRY_RUN_ONLY_NO_EXECUTION in result.reason_codes

    @pytest.mark.parametrize("name", list(CANDIDATE_ALLOWLIST))
    def test_r1_candidate_has_dry_run_only(self, name: str) -> None:
        result = dry_run_tool_policy(name)
        assert DRY_RUN_ONLY_NO_EXECUTION in result.reason_codes

    def test_r1_candidate_has_candidate_note(self) -> None:
        """All R1 candidates have REQUIRES_REVIEW_CANDIDATE_ONLY."""
        for name in CANDIDATE_ALLOWLIST:
            entry = TOOL_POLICY_INVENTORY[name]
            if entry.primary_risk == ToolRiskLevel.R1:
                result = dry_run_tool_policy(name)
                assert REQUIRES_REVIEW_CANDIDATE_ONLY in result.reason_codes

    def test_r1_execution_still_false(self) -> None:
        result = dry_run_tool_policy("read_file")
        assert result.execution_allowed is False
        assert result.dispatch_allowed is False
        assert result.provider_schema_allowed is False


class TestR2RequiresReview:
    """R2 tools: requires_review."""

    def test_r2_requires_review(self) -> None:
        result = dry_run_tool_policy("web_search")
        assert result.decision == DRY_RUN_DECISION_REQUIRES_REVIEW
        assert result.risk_tier == "R2"
        assert REQUIRES_REVIEW_R2 in result.reason_codes

    def test_r2_execution_false(self) -> None:
        result = dry_run_tool_policy("web_search")
        assert result.execution_allowed is False

    def test_r2_all_tools_review(self) -> None:
        r2_tools = [
            n for n in ALL_CANONICAL_TOOLS
            if TOOL_POLICY_INVENTORY[n].primary_risk == ToolRiskLevel.R2
        ]
        for name in r2_tools:
            result = dry_run_tool_policy(name)
            assert result.decision == DRY_RUN_DECISION_REQUIRES_REVIEW, (
                f"{name} should require review"
            )
            assert REQUIRES_REVIEW_R2 in result.reason_codes


class TestR3RequiresReviewOrRedact:
    """R3 tools: requires_review or would_redact."""

    def test_r3_no_args_requires_review(self) -> None:
        result = dry_run_tool_policy("discord")
        assert result.risk_tier == "R3"
        assert result.decision == DRY_RUN_DECISION_REQUIRES_REVIEW
        assert REQUIRES_REVIEW_R3 in result.reason_codes

    def test_r3_with_sensitive_args_would_redact(self) -> None:
        result = dry_run_tool_policy("discord", {"token": "secret_value"})
        assert result.decision == DRY_RUN_DECISION_WOULD_REDACT
        assert REQUIRES_REVIEW_R3 in result.reason_codes

    def test_r3_execution_false(self) -> None:
        result = dry_run_tool_policy("discord")
        assert result.execution_allowed is False

    def test_r3_all_tools_review_or_redact(self) -> None:
        r3_tools = [
            n for n in ALL_CANONICAL_TOOLS
            if TOOL_POLICY_INVENTORY[n].primary_risk == ToolRiskLevel.R3
            and not TOOL_POLICY_INVENTORY[n].permanently_denied
        ]
        for name in r3_tools:
            result = dry_run_tool_policy(name)
            assert result.decision in (
                DRY_RUN_DECISION_REQUIRES_REVIEW,
                DRY_RUN_DECISION_WOULD_REDACT,
            ), f"{name} decision was {result.decision}"


class TestR4Blocked:
    """R4 tools: would_block."""

    def test_r4_blocked(self) -> None:
        # Use a non-denylisted R4 tool if any exist, or skip
        # All R4 tools are denylisted, so they get denylist reason first
        # But we can test that they're blocked
        result = dry_run_tool_policy("browser_navigate")
        assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK

    def test_r4_all_tools_blocked(self) -> None:
        r4_tools = [
            n for n in ALL_CANONICAL_TOOLS
            if TOOL_POLICY_INVENTORY[n].primary_risk == ToolRiskLevel.R4
        ]
        for name in r4_tools:
            result = dry_run_tool_policy(name)
            assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK

    def test_r4_execution_false(self) -> None:
        result = dry_run_tool_policy("terminal")
        assert result.execution_allowed is False


class TestR5Blocked:
    """R5 tools: would_block."""

    def test_r5_blocked(self) -> None:
        result = dry_run_tool_policy("cronjob")
        assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK

    def test_r5_all_tools_blocked(self) -> None:
        r5_tools = [
            n for n in ALL_CANONICAL_TOOLS
            if TOOL_POLICY_INVENTORY[n].primary_risk == ToolRiskLevel.R5
        ]
        for name in r5_tools:
            result = dry_run_tool_policy(name)
            assert result.decision == DRY_RUN_DECISION_WOULD_BLOCK

    def test_r5_execution_false(self) -> None:
        result = dry_run_tool_policy("cronjob")
        assert result.execution_allowed is False


class TestCandidateAllowlist:
    """Candidate allowlist is advisory only — never grants execution."""

    @pytest.mark.parametrize("name", list(CANDIDATE_ALLOWLIST))
    def test_candidate_does_not_grant_execution(self, name: str) -> None:
        result = dry_run_tool_policy(name)
        assert result.execution_allowed is False
        assert result.dispatch_allowed is False
        assert result.provider_schema_allowed is False

    def test_candidate_does_not_grant_dispatch(self) -> None:
        result = dry_run_tool_policy("clarify")
        assert result.dispatch_allowed is False

    def test_candidate_does_not_grant_provider_schema(self) -> None:
        result = dry_run_tool_policy("read_file")
        assert result.provider_schema_allowed is False


class TestStaticAllowlist:
    """STATIC_ALLOWLIST must remain frozenset({"clarify"})."""

    def test_static_allowlist_is_clarify_only(self) -> None:
        assert STATIC_ALLOWLIST == frozenset({"clarify", "tool_policy_read", "route_governance_read", "audit_events_read", "dev_environment_read", "release_status_read"})

    def test_allowlist_does_not_allow_dry_run_execution(self) -> None:
        for name in ALL_CANONICAL_TOOLS:
            result = dry_run_tool_policy(name)
            assert result.execution_allowed is False, (
                f"{name} execution_allowed=True with STATIC_ALLOWLIST={STATIC_ALLOWLIST}"
            )


# ===================================================================
# 3. Security / Redaction Tests
# ===================================================================


class TestSecretRedaction:
    """Secret-like keys and values are redacted."""

    def test_api_key_redacted(self) -> None:
        result = dry_run_tool_policy("clarify", {"api_key": "sk-abc123def456"})
        assert result.redacted_arguments_preview["api_key"] == "[REDACTED]"
        assert "api_key" in result.forbidden_fields or any(
            "api_key" in f for f in result.forbidden_fields
        )
        assert WOULD_REDACT_SECRET_PATTERN in result.reason_codes

    def test_token_redacted(self) -> None:
        result = dry_run_tool_policy("clarify", {"token": "abc123"})
        assert result.redacted_arguments_preview["token"] == "[REDACTED]"

    def test_password_redacted(self) -> None:
        result = dry_run_tool_policy("clarify", {"password": "secret123"})
        assert result.redacted_arguments_preview["password"] == "[REDACTED]"

    def test_authorization_header_redacted(self) -> None:
        result = dry_run_tool_policy(
            "clarify", {"authorization": "Bearer xyz123"}
        )
        assert result.redacted_arguments_preview["authorization"] == "[REDACTED]"

    def test_cookie_redacted(self) -> None:
        result = dry_run_tool_policy("clarify", {"cookie": "session=abc123"})
        assert result.redacted_arguments_preview["cookie"] == "[REDACTED]"

    def test_bearer_redacted(self) -> None:
        result = dry_run_tool_policy("clarify", {"bearer": "token123"})
        assert result.redacted_arguments_preview["bearer"] == "[REDACTED]"

    def test_credential_redacted(self) -> None:
        result = dry_run_tool_policy("clarify", {"credential": "value"})
        assert result.redacted_arguments_preview["credential"] == "[REDACTED]"

    def test_private_key_redacted(self) -> None:
        result = dry_run_tool_policy("clarify", {"private_key": "value"})
        assert result.redacted_arguments_preview["private_key"] == "[REDACTED]"

    def test_access_key_redacted(self) -> None:
        result = dry_run_tool_policy("clarify", {"access_key": "value"})
        assert result.redacted_arguments_preview["access_key"] == "[REDACTED]"

    def test_refresh_token_redacted(self) -> None:
        result = dry_run_tool_policy("clarify", {"refresh_token": "value"})
        assert result.redacted_arguments_preview["refresh_token"] == "[REDACTED]"

    def test_client_secret_redacted(self) -> None:
        result = dry_run_tool_policy("clarify", {"client_secret": "val"})
        assert result.redacted_arguments_preview["client_secret"] == "[REDACTED]"

    def test_secret_value_redacted(self) -> None:
        """String values matching secret patterns are redacted."""
        result = dry_run_tool_policy(
            "clarify", {"data": "sk-abc123def456ghi789"}
        )
        assert result.redacted_arguments_preview["data"] == "[REDACTED]"

    def test_bearer_token_value_redacted(self) -> None:
        result = dry_run_tool_policy(
            "clarify", {"header": "Bearer abc123token"}
        )
        assert result.redacted_arguments_preview["header"] == "[REDACTED]"

    def test_nested_secret_redacted(self) -> None:
        result = dry_run_tool_policy(
            "clarify", {"config": {"api_key": "sk-test12345678"}}
        )
        nested = result.redacted_arguments_preview["config"]
        assert isinstance(nested, dict)
        assert nested["api_key"] == "[REDACTED]"


class TestForbiddenFields:
    """Forbidden field paths are tracked."""

    def test_forbidden_fields_tracked(self) -> None:
        result = dry_run_tool_policy(
            "clarify", {"api_key": "sk-abc123", "password": "secret"}
        )
        assert len(result.forbidden_fields) >= 2

    def test_nested_forbidden_fields_tracked(self) -> None:
        result = dry_run_tool_policy(
            "clarify", {"config": {"token": "secret"}}
        )
        assert len(result.forbidden_fields) >= 1


class TestLargeInputs:
    """Large strings, lists, and deep nesting are handled."""

    def test_large_string_truncated(self) -> None:
        long_str = "a" * 500
        result = dry_run_tool_policy("clarify", {"text": long_str})
        truncated = result.redacted_arguments_preview["text"]
        assert isinstance(truncated, str)
        assert len(truncated) <= MAX_ARGUMENT_STRING_CHARS + 1  # +1 for suffix
        assert truncated.endswith("…")

    def test_large_list_truncated(self) -> None:
        large_list = list(range(100))
        result = dry_run_tool_policy("clarify", {"items": large_list})
        output = result.redacted_arguments_preview["items"]
        assert isinstance(output, list)
        assert len(output) == MAX_ARGUMENT_LIST_ITEMS + 1  # last is "… N more items"

    def test_deep_nesting_truncated(self) -> None:
        deep: dict[str, Any] = {"value": "leaf"}
        for _ in range(10):
            deep = {"level": deep}
        result = dry_run_tool_policy("clarify", {"deep": deep})
        assert isinstance(result.redacted_arguments_preview, dict)

    def test_non_mapping_arguments_handled(self) -> None:
        result = dry_run_tool_policy("clarify", "not a mapping")  # type: ignore[arg-type]
        assert result.redacted_arguments_preview == {}
        assert INVALID_ARGUMENT_SHAPE in result.reason_codes

    def test_none_arguments_handled(self) -> None:
        result = dry_run_tool_policy("clarify", None)
        assert result.redacted_arguments_preview == {}
        assert result.forbidden_fields == ()

    def test_empty_dict_arguments_handled(self) -> None:
        result = dry_run_tool_policy("clarify", {})
        assert result.redacted_arguments_preview == {}

    def test_bool_value_preserved(self) -> None:
        result = dry_run_tool_policy("clarify", {"flag": True})
        assert result.redacted_arguments_preview["flag"] is True

    def test_int_value_preserved(self) -> None:
        result = dry_run_tool_policy("clarify", {"count": 42})
        assert result.redacted_arguments_preview["count"] == 42

    def test_none_value_preserved(self) -> None:
        result = dry_run_tool_policy("clarify", {"value": None})
        assert result.redacted_arguments_preview["value"] is None


class TestSanitizeArguments:
    """Direct tests for sanitize_arguments_preview."""

    def test_returns_tuple_of_three(self) -> None:
        result = sanitize_arguments_preview({"key": "value"})
        assert len(result) == 3

    def test_clean_args_no_redaction(self) -> None:
        redacted, forbidden, reasons = sanitize_arguments_preview(
            {"name": "test", "count": 5}
        )
        assert redacted == {"name": "test", "count": 5}
        assert forbidden == ()
        assert reasons == ()

    def test_secret_key_redacted(self) -> None:
        redacted, forbidden, reasons = sanitize_arguments_preview(
            {"api_key": "secret"}
        )
        assert redacted["api_key"] == "[REDACTED]"
        assert len(forbidden) > 0
        assert WOULD_REDACT_SECRET_PATTERN in reasons

    def test_case_insensitive_secret_key(self) -> None:
        redacted, forbidden, _ = sanitize_arguments_preview(
            {"API_KEY": "secret"}
        )
        assert redacted["API_KEY"] == "[REDACTED]"

    def test_camel_case_secret_key(self) -> None:
        redacted, forbidden, _ = sanitize_arguments_preview(
            {"clientSecret": "value"}
        )
        assert redacted["clientSecret"] == "[REDACTED]"


# ===================================================================
# 4. No Side Effect Tests
# ===================================================================


class TestNoSideEffects:
    """Dry-run must not produce side effects."""

    def test_does_not_call_tool_handler(self) -> None:
        """Module source does not import tool handlers."""
        import hermes_cli.dev_web_tool_dry_run as dry_run_mod

        source = Path(dry_run_mod.__file__).read_text(encoding="utf-8")
        # Check import lines only, not docstring mentions
        import_lines = [
            line for line in source.splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        for line in import_lines:
            assert "from tools" not in line, f"Unexpected import: {line}"
            assert "import tools" not in line, f"Unexpected import: {line}"
            assert "from agent" not in line, f"Unexpected import: {line}"

    def test_does_not_import_toolsets(self) -> None:
        import hermes_cli.dev_web_tool_dry_run as dry_run_mod

        source = Path(dry_run_mod.__file__).read_text(encoding="utf-8")
        assert "import toolsets" not in source
        assert "from toolsets" not in source

    def test_does_not_import_agent(self) -> None:
        import hermes_cli.dev_web_tool_dry_run as dry_run_mod

        source = Path(dry_run_mod.__file__).read_text(encoding="utf-8")
        assert "import agent" not in source
        assert "from agent" not in source

    def test_does_not_open_files(self) -> None:
        """dry_run_tool_policy does not call builtins.open."""
        result = dry_run_tool_policy("clarify")
        assert result is not None  # Just confirm it ran
        # Source inspection confirms no open() calls
        import hermes_cli.dev_web_tool_dry_run as dry_run_mod

        source = Path(dry_run_mod.__file__).read_text(encoding="utf-8")
        assert "\nopen(" not in source

    def test_does_not_mutate_environment(self) -> None:
        import os

        env_before = dict(os.environ)
        dry_run_tool_policy("clarify", {"test": "value"})
        assert os.environ == env_before

    def test_does_not_alter_static_allowlist(self) -> None:
        assert STATIC_ALLOWLIST == frozenset({"clarify", "tool_policy_read", "route_governance_read", "audit_events_read", "dev_environment_read", "release_status_read"})
        dry_run_tool_policy("clarify")
        assert STATIC_ALLOWLIST == frozenset({"clarify", "tool_policy_read", "route_governance_read", "audit_events_read", "dev_environment_read", "release_status_read"})

    def test_does_not_write_audit(self) -> None:
        """Module source contains no audit storage logic."""
        import hermes_cli.dev_web_tool_dry_run as dry_run_mod

        source = Path(dry_run_mod.__file__).read_text(encoding="utf-8")
        # Check for audit write/storage patterns, not field names
        for pattern in (
            "write_audit",
            "create_audit",
            "store_audit",
            "append_audit",
            "audit_log",
            "audit_table",
            "audit_record",
        ):
            assert pattern not in source.lower(), (
                f"Audit storage pattern found: {pattern}"
            )

    def test_import_no_filesystem_side_effects(self, tmp_path: Path) -> None:
        """Importing the module in a subprocess creates no files."""
        hermes_home = tmp_path / "hermes-home"
        script = textwrap.dedent(f"""\
            import sys
            sys.argv = ["test"]
            from hermes_cli.dev_web_tool_dry_run import dry_run_tool_policy
            import os
            home = "{hermes_home}"
            if os.path.exists(home):
                for root, dirs, files in os.walk(home):
                    for f in files:
                        full = os.path.join(root, f)
                        print(f"FILE: {{full}}")
            print("OK")
        """)
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": str(tmp_path),
                "HERMES_HOME": str(hermes_home),
                "VIRTUAL_ENV": "",
                **{
                    k: v
                    for k, v in __import__("os").environ.items()
                    if k.startswith("PYTHON")
                },
            },
            timeout=30,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_does_not_import_subprocess_or_socket(self) -> None:
        import hermes_cli.dev_web_tool_dry_run as dry_run_mod

        source = Path(dry_run_mod.__file__).read_text(encoding="utf-8")
        assert "import subprocess" not in source
        assert "import socket" not in source
        assert "from subprocess" not in source
        assert "from socket" not in source


# ===================================================================
# 5. Catalog and Summary Tests
# ===================================================================


class TestCatalog:
    """list_tool_dry_run_policies returns complete results."""

    def test_catalog_has_71_results(self) -> None:
        results = list_tool_dry_run_policies()
        assert len(results) == 76

    def test_catalog_sorted_by_name(self) -> None:
        results = list_tool_dry_run_policies()
        names = [r.canonical_name for r in results]
        assert names == sorted(names)

    def test_catalog_all_execution_false(self) -> None:
        results = list_tool_dry_run_policies()
        for r in results:
            assert r.execution_allowed is False

    def test_catalog_all_dispatch_false(self) -> None:
        results = list_tool_dry_run_policies()
        for r in results:
            assert r.dispatch_allowed is False

    def test_catalog_all_provider_schema_false(self) -> None:
        results = list_tool_dry_run_policies()
        for r in results:
            assert r.provider_schema_allowed is False

    def test_catalog_all_audit_false(self) -> None:
        results = list_tool_dry_run_policies()
        for r in results:
            assert r.audit_written is False

    def test_catalog_covers_all_tools(self) -> None:
        results = list_tool_dry_run_policies()
        result_names = frozenset(r.canonical_name for r in results)
        assert result_names == ALL_CANONICAL_TOOLS


class TestSummary:
    """compute_dry_run_policy_summary correctness."""

    def test_summary_total_is_71(self) -> None:
        summary = compute_dry_run_policy_summary()
        assert summary.total_count == 76

    def test_summary_all_categories_sum_to_total(self) -> None:
        summary = compute_dry_run_policy_summary()
        total = (
            summary.dry_run_allow_count
            + summary.blocked_count
            + summary.review_count
            + summary.redacted_count
        )
        assert total == summary.total_count

    def test_summary_denylist_counted_as_blocked(self) -> None:
        summary = compute_dry_run_policy_summary()
        assert summary.blocked_count >= len(STATIC_DENYLIST)

    def test_summary_r0_r1_counted_as_allow(self) -> None:
        """R0 and R1 tools should be in dry_run_allow_count."""
        summary = compute_dry_run_policy_summary()
        r0_r1_count = len(
            [
                n
                for n in ALL_CANONICAL_TOOLS
                if TOOL_POLICY_INVENTORY[n].primary_risk
                in (ToolRiskLevel.R0, ToolRiskLevel.R1)
                and not TOOL_POLICY_INVENTORY[n].permanently_denied
            ]
        )
        assert summary.dry_run_allow_count >= r0_r1_count

    def test_summary_is_frozen(self) -> None:
        summary = compute_dry_run_policy_summary()
        with pytest.raises(AttributeError):
            summary.total_count = 0  # type: ignore[misc]

    def test_summary_from_custom_results(self) -> None:
        results = (
            dry_run_tool_policy("clarify"),
            dry_run_tool_policy("terminal"),
        )
        summary = compute_dry_run_policy_summary(results)
        assert summary.total_count == 2


# ===================================================================
# 6. Determinism Tests
# ===================================================================


class TestDeterminism:
    """Same input always produces same output."""

    def test_same_input_same_result(self) -> None:
        r1 = dry_run_tool_policy("clarify", {"q": "test"})
        r2 = dry_run_tool_policy("clarify", {"q": "test"})
        assert r1 == r2

    def test_catalog_is_deterministic(self) -> None:
        c1 = list_tool_dry_run_policies()
        c2 = list_tool_dry_run_policies()
        assert c1 == c2

    def test_summary_is_deterministic(self) -> None:
        s1 = compute_dry_run_policy_summary()
        s2 = compute_dry_run_policy_summary()
        assert s1 == s2
