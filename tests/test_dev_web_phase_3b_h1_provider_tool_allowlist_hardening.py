"""Phase 3B-H1 — Provider Read-only Tool-call Allowlist HARDENING (Lens 7).

Deterministic, adversarial verification that a provider-requested tool call can
ONLY invoke the read-only allowlist, and that every write / shell / db /
external / production / plugin-load / rollback capability is permanently blocked
with a precise reason.

Allowed (the ONLY tools): clarify, tool_policy_read, route_governance_read,
audit_events_read, dev_environment_read, release_status_read.

Blocked: every write tool, rollback execute, shell/terminal/process, database,
external_http, execute_code, delegate_task, send_message, cronjob,
image_generate, production_operation, plugin_dynamic_load, and any unknown name.

Phase: 3B-H1 — Provider Boundary Hardening
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_real_policy import (
    BLOCKED_PROVIDER_EXTERNAL_URL_NOT_ALLOWED,
    BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    _FORBIDDEN_TOOL_REASONS,
    classify_provider_tool_call,
    get_read_only_tool_allowlist,
)
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

_ALLOWED = frozenset({
    "clarify", "tool_policy_read", "route_governance_read",
    "audit_events_read", "dev_environment_read", "release_status_read",
})


# ===========================================================================
# Lens 7 — allowlist source + immutability
# ===========================================================================


class TestAllowlistSource:
    def test_allowlist_is_the_phase_2a_static_allowlist(self) -> None:
        assert get_read_only_tool_allowlist() == STATIC_ALLOWLIST

    def test_allowlist_exactly_equals_the_six_read_only_tools(self) -> None:
        assert get_read_only_tool_allowlist() == _ALLOWED

    def test_allowlist_is_a_frozen_snapshot(self) -> None:
        assert isinstance(get_read_only_tool_allowlist(), frozenset)


# ===========================================================================
# Lens 7 — allowed tools (exhaustive)
# ===========================================================================


class TestAllowedToolsExhaustive:
    @pytest.mark.parametrize("tool_id", sorted(_ALLOWED))
    def test_only_these_six_are_allowed(self, tool_id: str) -> None:
        allowed, reason = classify_provider_tool_call(tool_id, {"x": 1})
        assert allowed is True
        assert reason is None

    def test_no_other_tool_is_allowed(self) -> None:
        # Anything outside the six is rejected.
        for tool_id in ("read_file", "search_files", "memory", "web_search", "clarify2"):
            allowed, _ = classify_provider_tool_call(tool_id, {})
            assert allowed is False


# ===========================================================================
# Lens 7 — forbidden catalogue (precise reasons)
# ===========================================================================


class TestForbiddenCatalogue:
    @pytest.mark.parametrize("tool_id", [
        "dev_sandbox_file_write", "dev_sandbox_file_append", "dev_sandbox_file_patch",
        "write_file", "patch", "memory", "memory_add", "memory_update",
        "todo", "skill_manage",
    ])
    def test_write_tools_blocked_with_write_reason(self, tool_id: str) -> None:
        allowed, reason = classify_provider_tool_call(tool_id, {})
        assert (allowed, reason) == (False, BLOCKED_PROVIDER_WRITE_NOT_ALLOWED)

    @pytest.mark.parametrize("tool_id", ["dev_sandbox_rollback_execute", "dev_sandbox_file_readback"])
    def test_rollback_blocked(self, tool_id: str) -> None:
        allowed, reason = classify_provider_tool_call(tool_id, {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED

    def test_external_http_uses_external_reason(self) -> None:
        allowed, reason = classify_provider_tool_call("external_http", {})
        assert (allowed, reason) == (False, BLOCKED_PROVIDER_EXTERNAL_URL_NOT_ALLOWED)

    @pytest.mark.parametrize("tool_id", [
        "shell", "terminal", "process", "database", "execute_code", "delegate_task",
        "send_message", "cronjob", "image_generate", "production_operation",
        "plugin_dynamic_load",
    ])
    def test_capability_tools_blocked(self, tool_id: str) -> None:
        allowed, reason = classify_provider_tool_call(tool_id, {})
        assert (allowed, reason) == (False, BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED)

    def test_every_forbidden_reason_is_in_catalogue(self) -> None:
        # The forbidden-name → reason map must only reference allowlist names.
        for name, reason in _FORBIDDEN_TOOL_REASONS.items():
            assert name not in _ALLOWED
            assert reason.startswith("blocked_provider_")


# ===========================================================================
# Lens 7 — adversarial inputs (unknown / non-string / empty / case)
# ===========================================================================


class TestAdversarialInputs:
    def test_unknown_tool_blocked_not_write(self) -> None:
        # An unknown tool must never fall back to a write tool.
        allowed, reason = classify_provider_tool_call("random_unknown_tool", {})
        assert (allowed, reason) == (False, BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED)

    def test_case_sensitive_no_fallthrough(self) -> None:
        # Uppercase / mixed case must NOT match the allowlist.
        for variant in ("CLARIFY", "Clarify", "Route_Governance_Read"):
            allowed, _ = classify_provider_tool_call(variant, {})
            assert allowed is False

    @pytest.mark.parametrize("bad", [12345, None, 3.14, [], {}, object()])
    def test_non_string_name_blocked(self, bad) -> None:
        allowed, reason = classify_provider_tool_call(bad, {})  # type: ignore[arg-type]
        assert (allowed, reason) == (False, BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED)

    def test_empty_and_whitespace_name_blocked(self) -> None:
        for name in ("", "   ", "\t"):
            allowed, reason = classify_provider_tool_call(name, {})
            assert (allowed, reason) == (False, BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED)

    def test_allowlisted_name_with_disguise_blocked(self) -> None:
        # A tool that LOOKS allowlisted but has trailing junk is rejected.
        for name in ("clarify ", " clarify", "clarify\n", "route_governance_read\x00"):
            allowed, _ = classify_provider_tool_call(name, {})
            assert allowed is False
