"""Phase 3B — Real Provider read-only Tool-call Allowlist tests.

Verifies the provider tool-call boundary:
  - only the Phase 2A STATIC_ALLOWLIST tools pass
  - write tools → blocked_provider_write_not_allowed
  - rollback execute → blocked (not executed)
  - shell / process → blocked
  - database → blocked
  - external_http → blocked_provider_external_url_not_allowed
  - production_operation → blocked
  - plugin_dynamic_load → blocked
  - the allowlist is reused unchanged from Phase 2A (no mutation)

Phase: 3B — Real Provider Read-only Controlled Integration
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_real_policy import (
    BLOCKED_PROVIDER_EXTERNAL_URL_NOT_ALLOWED,
    BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    classify_provider_tool_call,
    get_read_only_tool_allowlist,
)
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST


class TestAllowlistSource:
    def test_allowlist_equals_phase_2a_static_allowlist(self) -> None:
        # The real-provider boundary reuses the Phase 2A allowlist unchanged.
        assert get_read_only_tool_allowlist() == STATIC_ALLOWLIST

    def test_allowlist_is_immutable_snapshot(self) -> None:
        allowlist = get_read_only_tool_allowlist()
        # The boundary allowlist must be a frozenset (immutable).
        assert isinstance(allowlist, frozenset)

    def test_allowlist_contains_only_read_only_tools(self) -> None:
        allowlist = get_read_only_tool_allowlist()
        # Every allowlisted tool is one of the six read-only inspection tools.
        for tool in allowlist:
            assert tool in (
                "clarify", "tool_policy_read", "route_governance_read",
                "audit_events_read", "dev_environment_read", "release_status_read",
            )


class TestAllowedTools:
    @pytest.mark.parametrize(
        "tool_id",
        [
            "clarify", "tool_policy_read", "route_governance_read",
            "audit_events_read", "dev_environment_read", "release_status_read",
        ],
    )
    def test_read_only_tools_allowed(self, tool_id: str) -> None:
        allowed, reason = classify_provider_tool_call(tool_id, {"includeDetails": True})
        assert allowed is True
        assert reason is None


class TestWriteToolsBlocked:
    @pytest.mark.parametrize(
        "tool_id",
        [
            "dev_sandbox_file_write", "dev_sandbox_file_append", "dev_sandbox_file_patch",
            "write_file", "patch", "memory", "memory_add", "memory_update",
            "todo", "skill_manage",
        ],
    )
    def test_write_tools_blocked(self, tool_id: str) -> None:
        allowed, reason = classify_provider_tool_call(tool_id, {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_WRITE_NOT_ALLOWED


class TestRollbackBlocked:
    @pytest.mark.parametrize(
        "tool_id",
        ["dev_sandbox_rollback_execute", "dev_sandbox_file_readback"],
    )
    def test_rollback_blocked(self, tool_id: str) -> None:
        allowed, reason = classify_provider_tool_call(tool_id, {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED


class TestShellDatabaseExternalBlocked:
    @pytest.mark.parametrize("tool_id", ["shell", "terminal", "process", "database"])
    def test_shell_db_blocked(self, tool_id: str) -> None:
        allowed, reason = classify_provider_tool_call(tool_id, {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED

    def test_external_http_blocked(self) -> None:
        allowed, reason = classify_provider_tool_call("external_http", {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_EXTERNAL_URL_NOT_ALLOWED

    def test_send_message_blocked(self) -> None:
        allowed, reason = classify_provider_tool_call("send_message", {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED

    def test_execute_code_blocked(self) -> None:
        allowed, reason = classify_provider_tool_call("execute_code", {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED

    def test_delegate_task_blocked(self) -> None:
        allowed, reason = classify_provider_tool_call("delegate_task", {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED


class TestProductionAndPluginBlocked:
    def test_production_operation_blocked(self) -> None:
        allowed, reason = classify_provider_tool_call("production_operation", {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED

    def test_plugin_dynamic_load_blocked(self) -> None:
        allowed, reason = classify_provider_tool_call("plugin_dynamic_load", {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED


class TestUnknownTool:
    def test_unknown_tool_blocked_not_fallback_to_write(self) -> None:
        # An unknown tool must NEVER fall back to a write tool.
        allowed, reason = classify_provider_tool_call("some_random_tool", {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED

    def test_non_string_name_blocked(self) -> None:
        allowed, reason = classify_provider_tool_call(12345, {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED

    def test_empty_name_blocked(self) -> None:
        allowed, reason = classify_provider_tool_call("", {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED
