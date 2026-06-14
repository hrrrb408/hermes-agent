"""Phase 2A — Read-only Tool Registry unit tests.

Verifies the unified Phase 2A read-only tool registry:
  - lists exactly the five Phase 2A read-only tools (+ clarify handled separately)
  - every tool is readOnly=True, providerRequired=False, writeRequired=False,
    externalSideEffects=False, requiresConfirmation=True
  - the registry re-exports STATIC_ALLOWLIST as the single source of truth
  - all five tool ids are members of STATIC_ALLOWLIST (consistency)
  - argument validation is strict-whitelist (rejects forbidden/secret/path keys)
  - unknown tool ids are rejected

Phase: 2A — Real Tool Execution MVP (Read-only Multi-tool Execution)
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_read_only_tool_registry import (
    PHASE_2A_READ_ONLY_TOOL_IDS,
    READ_ONLY_TOOL_DEFINITIONS,
    STATIC_ALLOWLIST,
    get_read_only_tool_definition,
    is_phase_2a_read_only_tool,
    list_read_only_tool_definitions,
    normalize_read_only_tool_arguments,
    validate_read_only_tool_arguments,
)
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST as POLICY_STATIC_ALLOWLIST


EXPECTED_FIVE = frozenset(
    {
        "tool_policy_read",
        "route_governance_read",
        "audit_events_read",
        "dev_environment_read",
        "release_status_read",
    }
)


class TestRegistryContents:
    def test_registry_lists_exactly_five_read_only_tools(self) -> None:
        assert PHASE_2A_READ_ONLY_TOOL_IDS == EXPECTED_FIVE
        assert len(PHASE_2A_READ_ONLY_TOOL_IDS) == 5

    def test_list_definitions_returns_five_sorted(self) -> None:
        defs = list_read_only_tool_definitions()
        assert len(defs) == 5
        ids = [d.tool_id for d in defs]
        assert ids == sorted(ids)

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_get_definition_returns_record(self, tool_id: str) -> None:
        d = get_read_only_tool_definition(tool_id)
        assert d is not None
        assert d.tool_id == tool_id

    def test_get_definition_unknown_returns_none(self) -> None:
        assert get_read_only_tool_definition("not_a_read_only_tool") is None

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_is_phase_2a_read_only_tool_true(self, tool_id: str) -> None:
        assert is_phase_2a_read_only_tool(tool_id) is True

    def test_is_phase_2a_read_only_tool_false_for_clarify(self) -> None:
        # clarify is the Phase 1G baseline tool, handled separately — not a
        # Phase 2A read-only tool.
        assert is_phase_2a_read_only_tool("clarify") is False

    def test_is_phase_2a_read_only_tool_false_for_unknown(self) -> None:
        assert is_phase_2a_read_only_tool("terminal") is False
        assert is_phase_2a_read_only_tool("read_file") is False


class TestRegistrySingleSourceOfTruth:
    def test_registry_re_exports_same_static_allowlist_object(self) -> None:
        # The registry must NOT define a second allowlist — it re-exports the
        # policy module's STATIC_ALLOWLIST (single source of truth).
        assert STATIC_ALLOWLIST is POLICY_STATIC_ALLOWLIST

    def test_all_five_read_only_tools_are_in_static_allowlist(self) -> None:
        # Consistency invariant: every registry tool must be allowlisted,
        # otherwise it could not pass the execute Gate 3.
        assert PHASE_2A_READ_ONLY_TOOL_IDS.issubset(STATIC_ALLOWLIST)

    def test_static_allowlist_is_clarify_plus_five(self) -> None:
        assert STATIC_ALLOWLIST == EXPECTED_FIVE | {"clarify"}
        assert len(STATIC_ALLOWLIST) == 6


class TestSafetyProfile:
    """Every Phase 2A read-only tool must carry the invariant safety profile."""

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_read_only_true(self, tool_id: str) -> None:
        assert get_read_only_tool_definition(tool_id).read_only is True

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_provider_required_false(self, tool_id: str) -> None:
        assert get_read_only_tool_definition(tool_id).provider_required is False

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_write_required_false(self, tool_id: str) -> None:
        assert get_read_only_tool_definition(tool_id).write_required is False

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_external_side_effects_false(self, tool_id: str) -> None:
        assert get_read_only_tool_definition(tool_id).external_side_effects is False

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_requires_confirmation_true(self, tool_id: str) -> None:
        assert get_read_only_tool_definition(tool_id).requires_confirmation is True

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_safety_tier_and_phase(self, tool_id: str) -> None:
        d = get_read_only_tool_definition(tool_id)
        assert d.safety_tier == "read_only_safe"
        assert d.enabled_in_phase == "2A"

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FIVE))
    def test_category_and_display_name(self, tool_id: str) -> None:
        d = get_read_only_tool_definition(tool_id)
        assert d.category in {"policy", "governance", "audit", "environment", "release"}
        assert isinstance(d.display_name, str) and d.display_name.strip()
        assert isinstance(d.description, str) and d.description.strip()


class TestArgumentValidation:
    def test_unknown_tool_rejected(self) -> None:
        _, err = validate_read_only_tool_arguments("not_a_tool", None)
        assert err == "READ_ONLY_ARG_UNKNOWN_TOOL"

    def test_non_dict_arguments_rejected(self) -> None:
        _, err = validate_read_only_tool_arguments("tool_policy_read", "not a dict")
        assert err == "READ_ONLY_ARG_NON_DICT"

    def test_none_arguments_accepted_with_defaults(self) -> None:
        norm, err = validate_read_only_tool_arguments("tool_policy_read", None)
        assert err is None
        assert norm == {"includeDisabled": False}

    def test_forbidden_key_rejected(self) -> None:
        for bad in ("token", "secret", "password", "api_key", "path", "command", "sql"):
            _, err = validate_read_only_tool_arguments(
                "audit_events_read", {bad: "x", "limit": 5}
            )
            assert err == "READ_ONLY_ARG_FORBIDDEN_KEY", bad

    def test_unknown_key_rejected(self) -> None:
        _, err = validate_read_only_tool_arguments(
            "tool_policy_read", {"includeDisabled": True, "bogus": 1}
        )
        assert err == "READ_ONLY_ARG_UNKNOWN_KEY"

    def test_path_like_value_rejected(self) -> None:
        # toolId filter must not accept path traversal / absolute paths.
        _, err = validate_read_only_tool_arguments(
            "audit_events_read", {"toolId": "/etc/passwd"}
        )
        assert err == "READ_ONLY_ARG_INVALID_VALUE"

    def test_shell_like_value_rejected(self) -> None:
        _, err = validate_read_only_tool_arguments(
            "audit_events_read", {"toolId": "x; rm -rf /"}
        )
        assert err == "READ_ONLY_ARG_INVALID_VALUE"

    def test_secret_value_rejected(self) -> None:
        _, err = validate_read_only_tool_arguments(
            "audit_events_read", {"toolId": "sk-abcdef1234567890"}
        )
        assert err == "READ_ONLY_ARG_INVALID_VALUE"

    def test_audit_events_limit_bounds(self) -> None:
        # valid
        norm, err = validate_read_only_tool_arguments(
            "audit_events_read", {"limit": 100}
        )
        assert err is None and norm["limit"] == 100
        # over max
        _, err = validate_read_only_tool_arguments(
            "audit_events_read", {"limit": 101}
        )
        assert err == "READ_ONLY_ARG_INVALID_VALUE"
        # under min
        _, err = validate_read_only_tool_arguments(
            "audit_events_read", {"limit": 0}
        )
        assert err == "READ_ONLY_ARG_INVALID_VALUE"
        # default applied
        norm, err = validate_read_only_tool_arguments("audit_events_read", None)
        assert err is None and norm["limit"] == 20

    def test_normalize_returns_safe_dict_for_invalid(self) -> None:
        # normalize must never raise and never return untrusted values.
        norm = normalize_read_only_tool_arguments(
            "audit_events_read", {"token": "leak", "limit": 999}
        )
        assert "token" not in norm
        assert norm["limit"] == 20  # default

    def test_bool_coercion(self) -> None:
        norm, err = validate_read_only_tool_arguments(
            "tool_policy_read", {"includeDisabled": "true"}
        )
        assert err is None and norm["includeDisabled"] is True


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
