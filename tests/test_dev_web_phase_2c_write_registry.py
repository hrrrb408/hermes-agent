"""Phase 2C — Write tool registry tests.

Verifies the four Phase 2C controlled write tools are registered with the
correct safety profile, that the read-only allowlist stays frozen at six
read-only tools, that write tools are disjoint from the read-only allowlist
and from the production tool inventory, and that argument validation is a
strict whitelist.

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_write_tool_registry import (
    PHASE_2C_WRITE_TOOL_IDS,
    STATIC_WRITE_ALLOWLIST,
    STATIC_READ_ONLY_ALLOWLIST,
    UNIFIED_EXECUTABLE_ALLOWLIST,
    WRITE_TOOL_DEFINITIONS,
    WriteToolDefinition,
    get_write_tool_definition,
    is_phase_2c_write_tool,
    list_write_tool_definitions,
    normalize_write_tool_arguments,
    validate_write_tool_arguments,
    validate_write_tool_definition,
)
from hermes_cli.dev_web_tool_policy import (
    STATIC_ALLOWLIST,
    STATIC_DENYLIST,
    TOOL_POLICY_INVENTORY,
)


EXPECTED_FOUR = frozenset(
    {
        "dev_sandbox_file_write",
        "dev_sandbox_file_append",
        "dev_sandbox_file_patch",
        "dev_sandbox_file_readback",
    }
)


class TestWriteAllowlist:
    def test_write_allowlist_exact(self) -> None:
        assert STATIC_WRITE_ALLOWLIST == EXPECTED_FOUR
        assert PHASE_2C_WRITE_TOOL_IDS == EXPECTED_FOUR

    def test_write_allowlist_has_four(self) -> None:
        assert len(STATIC_WRITE_ALLOWLIST) == 4

    def test_read_only_allowlist_preserved_at_six(self) -> None:
        # The Phase 2A read-only allowlist is FROZEN. Write tools do NOT join it.
        assert STATIC_READ_ONLY_ALLOWLIST == STATIC_ALLOWLIST
        assert len(STATIC_READ_ONLY_ALLOWLIST) == 6
        assert STATIC_READ_ONLY_ALLOWLIST == frozenset(
            {
                "clarify",
                "tool_policy_read",
                "route_governance_read",
                "audit_events_read",
                "dev_environment_read",
                "release_status_read",
            }
        )

    def test_unified_executable_allowlist_is_union(self) -> None:
        assert UNIFIED_EXECUTABLE_ALLOWLIST == (
            STATIC_READ_ONLY_ALLOWLIST | STATIC_WRITE_ALLOWLIST
        )
        assert len(UNIFIED_EXECUTABLE_ALLOWLIST) == 10

    def test_write_disjoint_from_read_only(self) -> None:
        assert STATIC_WRITE_ALLOWLIST.isdisjoint(STATIC_READ_ONLY_ALLOWLIST)

    def test_write_disjoint_from_production_inventory(self) -> None:
        assert STATIC_WRITE_ALLOWLIST.isdisjoint(set(TOOL_POLICY_INVENTORY.keys()))

    def test_write_not_on_denylist(self) -> None:
        assert STATIC_WRITE_ALLOWLIST.isdisjoint(STATIC_DENYLIST)


class TestWriteDefinitionProfile:
    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FOUR))
    def test_definition_exists(self, tool_id: str) -> None:
        assert isinstance(WRITE_TOOL_DEFINITIONS[tool_id], WriteToolDefinition)

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FOUR))
    def test_write_safety_profile(self, tool_id: str) -> None:
        d = WRITE_TOOL_DEFINITIONS[tool_id]
        assert d.read_only is False
        assert d.write_required is True
        assert d.external_side_effects is False
        assert d.local_side_effects is True
        assert d.provider_required is False
        assert d.requires_confirmation is True
        assert d.requires_write_enablement is True
        assert d.requires_rollback_plan is True
        assert d.category == "write"
        assert d.safety_tier == "dev_sandbox_write"
        assert d.enabled_in_phase == "2C"

    @pytest.mark.parametrize("tool_id", sorted(EXPECTED_FOUR))
    def test_validate_definition_passes(self, tool_id: str) -> None:
        ok, errors = validate_write_tool_definition(WRITE_TOOL_DEFINITIONS[tool_id])
        assert ok, errors

    def test_list_definitions_count(self) -> None:
        assert len(list_write_tool_definitions()) == 4

    def test_get_definition(self) -> None:
        assert get_write_tool_definition("dev_sandbox_file_write") is not None
        assert get_write_tool_definition("not_a_write_tool") is None

    def test_is_phase_2c_write_tool(self) -> None:
        assert is_phase_2c_write_tool("dev_sandbox_file_append") is True
        assert is_phase_2c_write_tool("clarify") is False
        assert is_phase_2c_write_tool("write_file") is False


class TestArgumentValidation:
    def test_valid_write_args(self) -> None:
        norm, err = validate_write_tool_arguments(
            "dev_sandbox_file_write",
            {"targetPath": "notes/a.md", "content": "hello"},
        )
        assert err is None
        assert norm["targetPath"] == "notes/a.md"
        assert norm["content"] == "hello"
        assert norm["mode"] == "create_or_replace"

    def test_unknown_tool_rejected(self) -> None:
        norm, err = validate_write_tool_arguments("not_real", {"targetPath": "a.md"})
        assert err == "WRITE_ARG_UNKNOWN_TOOL"
        assert norm == {}

    def test_non_dict_rejected(self) -> None:
        norm, err = validate_write_tool_arguments(
            "dev_sandbox_file_write", "not a dict"  # type: ignore[arg-type]
        )
        assert err == "WRITE_ARG_NON_DICT"

    def test_unknown_key_rejected(self) -> None:
        norm, err = validate_write_tool_arguments(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x", "bogus": 1},
        )
        assert err == "WRITE_ARG_UNKNOWN_KEY"

    def test_forbidden_secret_key_rejected(self) -> None:
        norm, err = validate_write_tool_arguments(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x", "apiKey": "sk-xxx"},
        )
        assert err == "WRITE_ARG_FORBIDDEN_KEY"

    def test_forbidden_shell_key_rejected(self) -> None:
        norm, err = validate_write_tool_arguments(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x", "command": "rm -rf /"},
        )
        assert err == "WRITE_ARG_FORBIDDEN_KEY"

    def test_missing_required_rejected(self) -> None:
        norm, err = validate_write_tool_arguments(
            "dev_sandbox_file_write", {"targetPath": "a.md"}
        )
        assert err == "WRITE_ARG_MISSING_REQUIRED"

    def test_non_string_target_rejected(self) -> None:
        norm, err = validate_write_tool_arguments(
            "dev_sandbox_file_write",
            {"targetPath": 123, "content": "x"},
        )
        assert err == "WRITE_ARG_INVALID_VALUE"

    def test_binary_content_rejected(self) -> None:
        # High density of control characters signals binary content.
        binary = "".join(chr(i) for i in range(1, 200))
        norm, err = validate_write_tool_arguments(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": binary},
        )
        assert err == "WRITE_ARG_BINARY_CONTENT"

    def test_nul_in_content_rejected(self) -> None:
        norm, err = validate_write_tool_arguments(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "a\x00b"},
        )
        assert err == "WRITE_ARG_INVALID_VALUE"

    def test_patch_requires_search_and_replace(self) -> None:
        norm, err = validate_write_tool_arguments(
            "dev_sandbox_file_patch",
            {"targetPath": "a.md", "search": "x"},
        )
        assert err == "WRITE_ARG_MISSING_REQUIRED"

        norm2, err2 = validate_write_tool_arguments(
            "dev_sandbox_file_patch",
            {"targetPath": "a.md", "search": "x", "replace": "y"},
        )
        assert err2 is None
        assert norm2["search"] == "x"
        assert norm2["replace"] == "y"

    def test_readback_requires_only_target(self) -> None:
        norm, err = validate_write_tool_arguments(
            "dev_sandbox_file_readback", {"targetPath": "a.md"}
        )
        assert err is None

    def test_normalize_returns_empty_on_invalid(self) -> None:
        assert normalize_write_tool_arguments("dev_sandbox_file_write", {"bogus": 1}) == {}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
