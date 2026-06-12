"""Tests for hermes_cli.dev_web_tool_policy — static tool execution policy.

Phase 1G-01: Tool Inventory and Static Policy Module.

All tests use pure functions, in-memory data, and AST for registry verification.
No real tool execution, filesystem access, or network access.
"""

from __future__ import annotations

import ast
import json
import math
import subprocess
import sys
import textwrap
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

import pytest

from hermes_cli.dev_web_tool_policy import (
    ALL_CANONICAL_TOOLS,
    CANDIDATE_ALLOWLIST,
    MAX_AGENT_VISIBLE_OUTPUT_BYTES,
    MAX_ARGUMENT_ARRAY_LENGTH,
    MAX_ARGUMENT_NESTING_DEPTH,
    MAX_ARGUMENT_PAYLOAD_BYTES,
    MAX_ARGUMENT_STRING_LENGTH,
    DEFAULT_R0_TIMEOUT_SECONDS,
    DEFAULT_R1_TIMEOUT_SECONDS,
    MAX_GLOBAL_TOOL_CONCURRENCY,
    MAX_SERIALIZED_OUTPUT_BYTES,
    MAX_TOOL_CALLS_PER_RUN,
    MAX_TOOL_CONCURRENCY_PER_RUN,
    MAX_TOOL_TIMEOUT_SECONDS,
    MAX_WEB_PREVIEW_OUTPUT_BYTES,
    RISK_RANK,
    STATIC_ALLOWLIST,
    STATIC_DENYLIST,
    TOOL_POLICY_INVENTORY,
    TOOLS_BY_RISK,
    ToolArgumentValidationResult,
    ToolCapability,
    ToolPolicyDecision,
    ToolPolicyEntry,
    ToolPolicyValidationResult,
    ToolRiskLevel,
    ToolSchemaValidationResult,
    evaluate_static_tool_policy,
    get_all_tool_policies,
    get_tool_policy,
    get_tools_by_risk,
    is_candidate_allowlisted,
    is_permanently_denied,
    is_statically_allowed,
    validate_argument_structure,
    validate_static_tool_policy,
    validate_tool_schema_safety,
    REASON_TOOL_NOT_ALLOWED,
    REASON_TOOL_NOT_FOUND,
    REASON_TOOL_PERMANENTLY_DENIED,
)


# ===================================================================
# 25.1 Inventory Tests
# ===================================================================


class TestInventory:
    """Inventory count, uniqueness, and immutability."""

    def test_inventory_has_71_tools(self) -> None:
        assert len(TOOL_POLICY_INVENTORY) == 71

    def test_inventory_names_are_unique(self) -> None:
        names = list(TOOL_POLICY_INVENTORY.keys())
        assert len(names) == len(set(names))

    def test_inventory_has_no_empty_names(self) -> None:
        for name in TOOL_POLICY_INVENTORY:
            assert name, f"Empty name found"
            assert name == name.strip(), f"Padded name: {name!r}"

    def test_inventory_entries_are_immutable(self) -> None:
        entry = next(iter(TOOL_POLICY_INVENTORY.values()))
        assert entry.__dataclass_fields__ is not None
        with pytest.raises(AttributeError):
            entry.canonical_name = "mutated"  # type: ignore[misc]

    def test_all_canonical_tools_matches_inventory(self) -> None:
        assert ALL_CANONICAL_TOOLS == frozenset(TOOL_POLICY_INVENTORY.keys())

    def test_inventory_is_mapping_proxy(self) -> None:
        assert isinstance(TOOL_POLICY_INVENTORY, MappingProxyType)


# ===================================================================
# Registry Equality — AST-based extraction
# ===================================================================


def _extract_registry_names_via_ast() -> set[str]:
    """Extract all canonical tool names from tools/*.py via AST parsing.

    Also checks plugins/spotify/__init__.py for plugin-registered tools.

    Handles two registration patterns:
    - ``registry.register(name="tool_name", ...)`` — keyword arg
    - ``registry.register("tool_name", ...)`` — positional arg
    """
    names: set[str] = set()
    source_root = Path(__file__).resolve().parents[1]

    def _extract_name_from_call(node: ast.Call) -> str | None:
        # Positional: registry.register("tool_name", ...)
        if node.args and isinstance(node.args[0], ast.Constant):
            val = node.args[0].value
            if isinstance(val, str) and val:
                return val
        # Keyword: registry.register(name="tool_name", ...)
        for kw in node.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                val = kw.value.value
                if isinstance(val, str) and val:
                    return val
        return None

    # Standard tools/*.py files — use registry.register()
    for path in sorted((source_root / "tools").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "register":
                name = _extract_name_from_call(node)
                if name:
                    names.add(name)

    # Spotify plugin — uses ctx.register_tool() in a loop over _TOOLS tuple
    # The _TOOLS tuple contains ("spotify_playback", ...), ("spotify_devices", ...), etc.
    spotify_path = source_root / "plugins" / "spotify" / "__init__.py"
    if spotify_path.exists():
        content = spotify_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.startswith("spotify_"):
                    names.add(node.value)

    return names


class TestRegistryEquality:
    """Verify policy inventory matches the real registry canonical names."""

    def test_inventory_matches_registry(self) -> None:
        registry_names = _extract_registry_names_via_ast()
        policy_names = ALL_CANONICAL_TOOLS

        missing = registry_names - policy_names
        unknown = policy_names - registry_names

        assert not missing, f"Tools in registry but missing from policy: {missing}"
        assert not unknown, f"Tools in policy but not in registry: {unknown}"
        assert len(registry_names) == 71
        assert len(policy_names) == 71


# ===================================================================
# 25.2 Risk Tests
# ===================================================================


class TestRiskClassification:
    """Risk level distribution and uniqueness."""

    def test_risk_counts_are_exact(self) -> None:
        assert len(TOOLS_BY_RISK[ToolRiskLevel.R0]) == 1
        assert len(TOOLS_BY_RISK[ToolRiskLevel.R1]) == 5
        assert len(TOOLS_BY_RISK[ToolRiskLevel.R2]) == 19
        assert len(TOOLS_BY_RISK[ToolRiskLevel.R3]) == 26
        assert len(TOOLS_BY_RISK[ToolRiskLevel.R4]) == 17
        assert len(TOOLS_BY_RISK[ToolRiskLevel.R5]) == 3

    def test_each_tool_has_one_primary_risk(self) -> None:
        for name in ALL_CANONICAL_TOOLS:
            entry = TOOL_POLICY_INVENTORY[name]
            # Should be in exactly one risk set
            risk_matches = sum(
                1
                for risk in ToolRiskLevel
                if name in TOOLS_BY_RISK[risk]
            )
            assert risk_matches == 1, f"{name} in {risk_matches} risk sets"

    def test_risk_sets_are_pairwise_disjoint(self) -> None:
        risks = list(ToolRiskLevel)
        for i in range(len(risks)):
            for j in range(i + 1, len(risks)):
                intersect = TOOLS_BY_RISK[risks[i]] & TOOLS_BY_RISK[risks[j]]
                assert not intersect, (
                    f"{risks[i]} ∩ {risks[j]} = {intersect}"
                )

    def test_all_tools_are_classified(self) -> None:
        classified = set()
        for risk in ToolRiskLevel:
            classified |= TOOLS_BY_RISK[risk]
        assert classified == ALL_CANONICAL_TOOLS
        assert len(classified) == 71

    def test_candidate_tools_are_only_r0_or_r1(self) -> None:
        for name in CANDIDATE_ALLOWLIST:
            entry = TOOL_POLICY_INVENTORY[name]
            assert entry.primary_risk in (
                ToolRiskLevel.R0,
                ToolRiskLevel.R1,
            ), f"Candidate {name} has risk {entry.primary_risk}"

    def test_risk_rank_ordering(self) -> None:
        assert RISK_RANK[ToolRiskLevel.R0] < RISK_RANK[ToolRiskLevel.R1]
        assert RISK_RANK[ToolRiskLevel.R1] < RISK_RANK[ToolRiskLevel.R2]
        assert RISK_RANK[ToolRiskLevel.R2] < RISK_RANK[ToolRiskLevel.R3]
        assert RISK_RANK[ToolRiskLevel.R3] < RISK_RANK[ToolRiskLevel.R4]
        assert RISK_RANK[ToolRiskLevel.R4] < RISK_RANK[ToolRiskLevel.R5]


# ===================================================================
# 25.3 Denylist Tests
# ===================================================================


class TestDenylist:
    """Permanent denylist contents and properties."""

    def test_denylist_has_26_tools(self) -> None:
        assert len(STATIC_DENYLIST) == 26

    EXPECTED_DENYLIST = frozenset(
        {
            "terminal",
            "process",
            "execute_code",
            "write_file",
            "patch",
            "memory",
            "skill_manage",
            "delegate_task",
            "browser_navigate",
            "browser_snapshot",
            "browser_click",
            "browser_type",
            "browser_scroll",
            "browser_back",
            "browser_press",
            "browser_get_images",
            "browser_vision",
            "browser_console",
            "browser_cdp",
            "browser_dialog",
            "computer_use",
            "send_message",
            "cronjob",
            "image_generate",
            "discord_admin",
            "ha_call_service",
        }
    )

    def test_denylist_exact_contents(self) -> None:
        assert STATIC_DENYLIST == self.EXPECTED_DENYLIST

    def test_denylist_is_inventory_subset(self) -> None:
        assert STATIC_DENYLIST <= ALL_CANONICAL_TOOLS

    def test_denylist_has_no_duplicates(self) -> None:
        assert len(STATIC_DENYLIST) == len(set(STATIC_DENYLIST))

    def test_denylist_and_candidates_are_disjoint(self) -> None:
        assert not (STATIC_DENYLIST & CANDIDATE_ALLOWLIST)

    def test_all_denylist_tools_are_denied(self) -> None:
        for name in STATIC_DENYLIST:
            entry = TOOL_POLICY_INVENTORY[name]
            assert entry.permanently_denied, f"{name} not marked as denied"
            assert not entry.statically_allowed, f"{name} is statically_allowed"
            assert not entry.candidate_allowlisted, f"{name} is candidate"


# ===================================================================
# 25.4 Candidate / Allowlist Tests
# ===================================================================


class TestCandidateAllowlist:
    """Candidate allowlist contents and empty static allowlist."""

    EXPECTED_CANDIDATES = frozenset(
        {
            "clarify",
            "skills_list",
            "skill_view",
            "read_file",
            "search_files",
            "session_search",
        }
    )

    def test_candidate_allowlist_has_6_tools(self) -> None:
        assert len(CANDIDATE_ALLOWLIST) == 6

    def test_candidate_allowlist_exact_names(self) -> None:
        assert CANDIDATE_ALLOWLIST == self.EXPECTED_CANDIDATES

    def test_static_allowlist_is_clarify_only(self) -> None:
        assert len(STATIC_ALLOWLIST) == 1
        assert STATIC_ALLOWLIST == frozenset({"clarify"})

    def test_candidate_does_not_mean_enabled_except_clarify(self) -> None:
        for name in CANDIDATE_ALLOWLIST:
            entry = TOOL_POLICY_INVENTORY[name]
            assert entry.candidate_allowlisted
            if name == "clarify":
                assert entry.statically_allowed, (
                    f"clarify must be statically_allowed after Phase 1G-04-14"
                )
            else:
                assert not entry.statically_allowed, (
                    f"Candidate {name} is marked statically_allowed but not allowlisted"
                )

    def test_only_clarify_is_statically_allowed(self) -> None:
        for name, entry in TOOL_POLICY_INVENTORY.items():
            if name == "clarify":
                assert entry.statically_allowed, (
                    f"clarify must be statically_allowed after Phase 1G-04-14"
                )
            else:
                assert not entry.statically_allowed, (
                    f"{name} is statically_allowed but not on STATIC_ALLOWLIST"
                )


# ===================================================================
# 25.5 Decision Tests
# ===================================================================


class TestDecisions:
    """Default-deny decision behavior."""

    def test_unknown_tool_fails_closed(self) -> None:
        d = evaluate_static_tool_policy("unknown_tool")
        assert not d.allowed
        assert not d.known
        assert d.canonical_name is None
        assert d.reason_code == REASON_TOOL_NOT_FOUND

    def test_permanent_deny_tool_fails_closed(self) -> None:
        d = evaluate_static_tool_policy("terminal")
        assert not d.allowed
        assert d.known
        assert d.permanently_denied
        assert d.reason_code == REASON_TOOL_PERMANENTLY_DENIED

    def test_clarify_is_allowed_on_static_allowlist(self) -> None:
        d = evaluate_static_tool_policy("clarify")
        assert d.allowed
        assert d.known
        assert d.candidate_allowlisted
        assert d.statically_allowed
        assert not d.permanently_denied
        assert d.reason_code == "TOOL_ALLOWED"

    def test_r2_tool_fails_closed(self) -> None:
        d = evaluate_static_tool_policy("web_search")
        assert not d.allowed
        assert d.known
        assert d.reason_code == REASON_TOOL_NOT_ALLOWED

    def test_case_variant_is_unknown(self) -> None:
        d = evaluate_static_tool_policy("Clarify")
        assert not d.known
        assert d.reason_code == REASON_TOOL_NOT_FOUND

    def test_whitespace_variant_is_unknown(self) -> None:
        d = evaluate_static_tool_policy(" clarify ")
        assert not d.known
        assert d.reason_code == REASON_TOOL_NOT_FOUND

    def test_wildcard_name_is_unknown(self) -> None:
        d = evaluate_static_tool_policy("browser_*")
        assert not d.known
        assert d.reason_code == REASON_TOOL_NOT_FOUND

    def test_prefix_is_unknown(self) -> None:
        d = evaluate_static_tool_policy("spotify_")
        assert not d.known
        assert d.reason_code == REASON_TOOL_NOT_FOUND

    def test_only_clarify_allowed_others_not(self) -> None:
        for name in ALL_CANONICAL_TOOLS:
            d = evaluate_static_tool_policy(name)
            if name == "clarify":
                assert d.allowed, f"clarify should be allowed"
            else:
                assert not d.allowed, f"{name} was allowed"

    def test_decision_is_frozen(self) -> None:
        d = evaluate_static_tool_policy("terminal")
        with pytest.raises(AttributeError):
            d.allowed = True  # type: ignore[misc]


# ===================================================================
# 25.6 Schema Tests
# ===================================================================


class TestSchemaValidation:
    """Tool schema safety validation."""

    def test_schema_requires_object_root(self) -> None:
        result = validate_tool_schema_safety({"type": "string"})
        assert not result.valid
        assert any("Root type must be 'object'" in e for e in result.errors)

    def test_schema_requires_additional_properties_false(self) -> None:
        schema = {
            "type": "object",
            "properties": {"x": {"type": "string"}},
        }
        result = validate_tool_schema_safety(schema)
        assert not result.valid
        assert any("additionalProperties" in e for e in result.errors)

    def test_nested_objects_require_additional_properties_false(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {"inner": {"type": "string"}},
                },
            },
        }
        result = validate_tool_schema_safety(schema)
        assert not result.valid
        assert any("additionalProperties" in e for e in result.errors)

    def test_schema_rejects_missing_required_property(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"x": {"type": "string"}},
            "required": ["x", "y"],
        }
        result = validate_tool_schema_safety(schema)
        assert not result.valid
        assert any("'y' not in properties" in e for e in result.errors)

    def test_schema_rejects_forbidden_keys(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"__proto__": {"type": "string"}},
        }
        result = validate_tool_schema_safety(schema)
        assert not result.valid
        assert any("Forbidden" in e for e in result.errors)

    def test_schema_rejects_excessive_depth(self) -> None:
        # Build deeply nested schema
        schema: dict = {"type": "string"}
        for _ in range(10):
            schema = {"type": "object", "additionalProperties": False, "properties": {"x": schema}}
        # The root itself has additionalProperties=false, so check depth only
        result = validate_tool_schema_safety(schema)
        assert not result.valid
        assert any("depth" in e.lower() for e in result.errors)

    def test_valid_schema_passes(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["name"],
        }
        result = validate_tool_schema_safety(schema)
        assert result.valid
        assert len(result.errors) == 0

    def test_schema_result_is_frozen(self) -> None:
        result = validate_tool_schema_safety({"type": "object", "additionalProperties": False})
        with pytest.raises(AttributeError):
            result.valid = False  # type: ignore[misc]


# ===================================================================
# 25.7 Argument Tests
# ===================================================================


class TestArgumentValidation:
    """Tool argument structure validation."""

    def test_arguments_reject_payload_over_limit(self) -> None:
        args = {"data": "x" * 50000}
        result = validate_argument_structure(args)
        assert not result.valid
        assert result.payload_bytes > MAX_ARGUMENT_PAYLOAD_BYTES

    def test_arguments_reject_depth_over_limit(self) -> None:
        args: object = {}
        for _ in range(10):
            args = {"nested": args}
        result = validate_argument_structure(args)
        assert not result.valid
        assert any("depth" in e.lower() for e in result.errors)

    def test_arguments_reject_long_string(self) -> None:
        args = {"text": "a" * 5000}
        result = validate_argument_structure(args)
        assert not result.valid
        assert any("String length" in e for e in result.errors)

    def test_arguments_reject_large_array(self) -> None:
        args = {"items": list(range(200))}
        result = validate_argument_structure(args)
        assert not result.valid
        assert any("Array length" in e for e in result.errors)

    def test_arguments_reject_forbidden_keys(self) -> None:
        args = {"__proto__": "evil"}
        result = validate_argument_structure(args)
        assert not result.valid
        assert any("Forbidden" in e for e in result.errors)

    def test_arguments_reject_nan(self) -> None:
        args = {"value": float("nan")}
        result = validate_argument_structure(args)
        assert not result.valid
        assert any("NaN" in e for e in result.errors)

    def test_arguments_reject_infinity(self) -> None:
        args = {"value": float("inf")}
        result = validate_argument_structure(args)
        assert not result.valid
        assert any("Infinity" in e for e in result.errors)

    def test_arguments_reject_non_json_value(self) -> None:
        args = {"func": lambda: None}
        result = validate_argument_structure(args)
        assert not result.valid
        assert any("JSON" in e for e in result.errors)

    def test_valid_arguments_pass(self) -> None:
        args = {
            "name": "test",
            "count": 42,
            "items": [1, 2, 3],
            "nested": {"key": "value"},
            "flag": True,
            "empty": None,
        }
        result = validate_argument_structure(args)
        assert result.valid
        assert len(result.errors) == 0
        assert result.payload_bytes > 0

    def test_argument_result_is_frozen(self) -> None:
        result = validate_argument_structure({"x": 1})
        with pytest.raises(AttributeError):
            result.valid = False  # type: ignore[misc]

    def test_constructor_key_rejected(self) -> None:
        result = validate_argument_structure({"constructor": "bad"})
        assert not result.valid

    def test_prototype_key_rejected(self) -> None:
        result = validate_argument_structure({"prototype": "bad"})
        assert not result.valid


# ===================================================================
# 25.8 Import Safety Tests
# ===================================================================


class TestImportSafety:
    """Import-time side-effect verification."""

    def test_import_has_no_filesystem_side_effects(self, tmp_path: Path) -> None:
        """Importing the module in a subprocess does not create tool-audit or
        tool-execution related files under HERMES_HOME."""
        hermes_home = tmp_path / "hermes-home"
        script = textwrap.dedent(f"""\
            import sys
            sys.argv = ["test"]
            from hermes_cli.dev_web_tool_policy import TOOL_POLICY_INVENTORY
            import os
            # Check no tool-related files created under HERMES_HOME
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
        # No tool-related files should have been created
        tool_related = [
            line for line in result.stdout.splitlines()
            if line.startswith("FILE:") and (
                "tool" in line.lower() or "audit" in line.lower()
            )
        ]
        assert not tool_related, f"Unexpected tool-related files: {tool_related}"

    def test_import_does_not_initialize_registry(self) -> None:
        """Module does not import or initialize the Tool Registry."""
        import hermes_cli.dev_web_tool_policy as policy

        source = Path(policy.__file__).read_text(encoding="utf-8")
        assert "tools.registry" not in source
        assert "tools/registry" not in source
        assert "registry.dispatch" not in source
        assert "handle_function_call" not in source

    def test_import_does_not_create_threads(self) -> None:
        """Module source contains no threading or subprocess imports."""
        import hermes_cli.dev_web_tool_policy as policy

        source = Path(policy.__file__).read_text(encoding="utf-8")
        # Check for import statements, not docstring mentions
        assert "import threading" not in source
        assert "import subprocess" not in source
        assert "from threading" not in source
        assert "from subprocess" not in source

    def test_import_does_not_create_audit_table(self, tmp_path: Path) -> None:
        """Importing the module does not create any SQLite tables."""
        script = textwrap.dedent(f"""\
            import sys, sqlite3
            sys.argv = ["test"]
            from hermes_cli.dev_web_tool_policy import TOOL_POLICY_INVENTORY
            db_path = "{tmp_path / "test.db"}"
            conn = sqlite3.connect(db_path)
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            conn.close()
            # No tables should exist (empty db)
            for t in tables:
                if 'tool' in t[0].lower() or 'audit' in t[0].lower():
                    print(f"UNEXPECTED: {{t[0]}}")
                    sys.exit(1)
            print("OK")
        """)
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout


# ===================================================================
# Immutability Tests
# ===================================================================


class TestImmutability:
    """Verify all public collections are immutable."""

    def test_inventory_cannot_be_modified(self) -> None:
        with pytest.raises(TypeError):
            TOOL_POLICY_INVENTORY["new_tool"] = None  # type: ignore[index]

    def test_denylist_cannot_add(self) -> None:
        with pytest.raises(AttributeError):
            STATIC_DENYLIST.add("something")  # type: ignore[attr-defined]

    def test_candidate_cannot_add(self) -> None:
        with pytest.raises(AttributeError):
            CANDIDATE_ALLOWLIST.add("something")  # type: ignore[attr-defined]

    def test_static_allowlist_cannot_add(self) -> None:
        with pytest.raises(AttributeError):
            STATIC_ALLOWLIST.add("something")  # type: ignore[attr-defined]

    def test_tools_by_risk_cannot_be_modified(self) -> None:
        with pytest.raises(TypeError):
            TOOLS_BY_RISK[ToolRiskLevel.R0] = frozenset()  # type: ignore[index]

    def test_entry_capabilities_cannot_be_modified(self) -> None:
        entry = next(iter(TOOL_POLICY_INVENTORY.values()))
        with pytest.raises(AttributeError):
            entry.capabilities.add(ToolCapability.PURE_COMPUTE)  # type: ignore[attr-defined]

    def test_query_returns_new_tuples(self) -> None:
        """get_all_tool_policies returns a new tuple each call."""
        t1 = get_all_tool_policies()
        t2 = get_all_tool_policies()
        assert t1 == t2
        assert t1 is not t2


# ===================================================================
# Global Limits Tests
# ===================================================================


class TestGlobalLimits:
    """Verify frozen constants are correct."""

    def test_argument_limits(self) -> None:
        assert MAX_ARGUMENT_PAYLOAD_BYTES == 32 * 1024
        assert MAX_ARGUMENT_NESTING_DEPTH == 8
        assert MAX_ARGUMENT_STRING_LENGTH == 4000
        assert MAX_ARGUMENT_ARRAY_LENGTH == 100

    def test_timeout_limits(self) -> None:
        assert DEFAULT_R0_TIMEOUT_SECONDS == 2
        assert DEFAULT_R1_TIMEOUT_SECONDS == 5
        assert MAX_TOOL_TIMEOUT_SECONDS == 30

    def test_concurrency_limits(self) -> None:
        assert MAX_TOOL_CALLS_PER_RUN == 3
        assert MAX_GLOBAL_TOOL_CONCURRENCY == 1
        assert MAX_TOOL_CONCURRENCY_PER_RUN == 1

    def test_output_limits(self) -> None:
        assert MAX_SERIALIZED_OUTPUT_BYTES == 64 * 1024
        assert MAX_AGENT_VISIBLE_OUTPUT_BYTES == 16 * 1024
        assert MAX_WEB_PREVIEW_OUTPUT_BYTES == 8 * 1024


# ===================================================================
# Completeness Validation Tests
# ===================================================================


class TestCompletenessValidation:
    """validate_static_tool_policy() correctness."""

    def test_completeness_check_passes(self) -> None:
        result = validate_static_tool_policy()
        assert result.valid
        assert len(result.errors) == 0
        assert result.canonical_count == 71

    def test_completeness_risk_counts(self) -> None:
        result = validate_static_tool_policy()
        assert result.risk_counts[ToolRiskLevel.R0] == 1
        assert result.risk_counts[ToolRiskLevel.R1] == 5
        assert result.risk_counts[ToolRiskLevel.R2] == 19
        assert result.risk_counts[ToolRiskLevel.R3] == 26
        assert result.risk_counts[ToolRiskLevel.R4] == 17
        assert result.risk_counts[ToolRiskLevel.R5] == 3

    def test_completeness_result_is_frozen(self) -> None:
        result = validate_static_tool_policy()
        with pytest.raises(AttributeError):
            result.valid = False  # type: ignore[misc]


# ===================================================================
# Specific Tool Classification Tests
# ===================================================================


class TestSpecificToolClassification:
    """Spot-check individual tool classifications."""

    def test_clarify_is_r0(self) -> None:
        entry = TOOL_POLICY_INVENTORY["clarify"]
        assert entry.primary_risk == ToolRiskLevel.R0
        assert ToolCapability.PURE_COMPUTE in entry.capabilities

    def test_read_file_is_r1(self) -> None:
        entry = TOOL_POLICY_INVENTORY["read_file"]
        assert entry.primary_risk == ToolRiskLevel.R1
        assert ToolCapability.LOCAL_FILE_READ in entry.capabilities

    def test_terminal_is_r4_and_denied(self) -> None:
        entry = TOOL_POLICY_INVENTORY["terminal"]
        assert entry.primary_risk == ToolRiskLevel.R4
        assert entry.permanently_denied
        assert ToolCapability.PROCESS_EXECUTION in entry.capabilities

    def test_cronjob_is_r5_and_denied(self) -> None:
        entry = TOOL_POLICY_INVENTORY["cronjob"]
        assert entry.primary_risk == ToolRiskLevel.R5
        assert entry.permanently_denied
        assert ToolCapability.SCHEDULING in entry.capabilities

    def test_spotify_playback_is_r3(self) -> None:
        entry = TOOL_POLICY_INVENTORY["spotify_playback"]
        assert entry.primary_risk == ToolRiskLevel.R3
        assert ToolCapability.REMOTE_STATE_MUTATION in entry.capabilities

    def test_discord_admin_is_r5(self) -> None:
        entry = TOOL_POLICY_INVENTORY["discord_admin"]
        assert entry.primary_risk == ToolRiskLevel.R5
        assert entry.permanently_denied
        assert ToolCapability.ADMINISTRATIVE_ACTION in entry.capabilities

    def test_session_search_is_r1(self) -> None:
        entry = TOOL_POLICY_INVENTORY["session_search"]
        assert entry.primary_risk == ToolRiskLevel.R1
        assert ToolCapability.DATABASE_READ in entry.capabilities

    def test_source_field_no_absolute_paths(self) -> None:
        """source fields must not contain absolute paths."""
        for name, entry in TOOL_POLICY_INVENTORY.items():
            assert not entry.source.startswith("/"), (
                f"{name} source has absolute path: {entry.source}"
            )

    def test_rationale_no_secrets(self) -> None:
        """rationale fields must not contain common secret patterns."""
        for name, entry in TOOL_POLICY_INVENTORY.items():
            assert "api_key" not in entry.rationale.lower()
            assert "password" not in entry.rationale.lower()
            assert "secret" not in entry.rationale.lower()
            assert "token" not in entry.rationale.lower()
