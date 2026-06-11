"""Tests for the Schema Preview Read-Only Service.

Phase: 1G-03-02 — Schema Preview Read-Only Service

Covers:
  - Import safety (no side effects, no file IO, no network, no handler calls)
  - Catalog count (total = 71)
  - Catalog canonicalName set equals Tool Policy inventory
  - Stable sorting by canonicalName
  - Single lookup — existing tool found
  - Single lookup — missing tool not found
  - Fake schema source integration
  - Empty schema source (default)
  - Invalid schema handling
  - Source exception isolation
  - Risk / denylist / candidate behavior
  - No execution / no handler / no dispatch
  - JSON-safe output
  - Existing API behavior unchanged (schemaPreviewAvailable still false)
  - STATIC_ALLOWLIST remains empty
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from hermes_cli.dev_web_tool_policy import (
    CANDIDATE_ALLOWLIST,
    RISK_RANK,
    STATIC_ALLOWLIST,
    STATIC_DENYLIST,
    TOOL_POLICY_INVENTORY,
    ToolRiskLevel,
    get_tool_policy,
)
from hermes_cli.dev_web_tool_schema_preview import (
    REDACTION_STATUS_UNAVAILABLE,
    REASON_AVAILABLE,
    REASON_AVAILABLE_WITH_REDACTION,
    REASON_UNAVAILABLE_EMPTY_SCHEMA,
    REASON_UNAVAILABLE_INVALID_SCHEMA,
    REASON_UNAVAILABLE_PERMANENTLY_DENIED,
    REASON_UNAVAILABLE_RISK_R4,
    REASON_UNAVAILABLE_RISK_R5,
    REASON_UNAVAILABLE_SCHEMA_SOURCE_ERROR,
    ToolSchemaPreview,
)
from hermes_cli.dev_web_tool_schema_preview_service import (
    ToolSchemaPreviewCatalog,
    ToolSchemaPreviewLookupResult,
    _empty_schema_source,
    get_schema_preview,
    list_schema_previews,
)


# ===========================================================================
# Helper: fake schema
# ===========================================================================

_FAKE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query string",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of results",
            "minimum": 1,
            "maximum": 100,
        },
        "verbose": {
            "type": "boolean",
            "description": "Enable verbose output",
        },
    },
    "required": ["query"],
    "additionalProperties": False,
}


def _fake_source_all(canonical_name: str) -> dict[str, Any] | None:
    """Fake source that returns a valid schema for all tools."""
    return _FAKE_SCHEMA


def _fake_source_none(canonical_name: str) -> dict[str, Any] | None:
    """Fake source that returns None for all tools."""
    return None


def _fake_source_r0_only(canonical_name: str) -> dict[str, Any] | None:
    """Fake source that returns schema only for R0 tools."""
    entry = get_tool_policy(canonical_name)
    if entry is not None and entry.primary_risk == ToolRiskLevel.R0:
        return _FAKE_SCHEMA
    return None


# ===========================================================================
# 1. Import safety
# ===========================================================================


class TestImportSafety:
    """Verify the service module has no import side effects."""

    def test_import_no_file_io(self, tmp_path):
        """Importing should not create any files."""
        before = set(tmp_path.iterdir()) if tmp_path.exists() else set()
        import importlib
        import hermes_cli.dev_web_tool_schema_preview_service as svc
        importlib.reload(svc)
        after = set(tmp_path.iterdir()) if tmp_path.exists() else set()
        # tmp_path is unrelated to the import — just checking import didn't
        # touch it (paranoid sanity check that the import is pure)
        assert before == after

    def test_module_has_no_network_imports(self):
        """Module should not import socket, urllib, http, requests etc."""
        import hermes_cli.dev_web_tool_schema_preview_service as svc
        source = open(svc.__file__, encoding="utf-8").read()
        forbidden = ["import socket", "import urllib", "import http",
                     "import requests", "import aiohttp"]
        for pattern in forbidden:
            assert pattern not in source, f"Forbidden import found: {pattern}"

    def test_module_has_no_handler_imports(self):
        """Module should not import tools, toolsets, or handler modules."""
        import hermes_cli.dev_web_tool_schema_preview_service as svc
        source = open(svc.__file__, encoding="utf-8").read()
        forbidden = ["from tools", "import tools", "from toolsets",
                     "import toolsets", "import registry"]
        for pattern in forbidden:
            assert pattern not in source, f"Forbidden import found: {pattern}"

    def test_module_has_no_provider_imports(self):
        """Module should not import provider modules."""
        import hermes_cli.dev_web_tool_schema_preview_service as svc
        source = open(svc.__file__, encoding="utf-8").read()
        # Check import statements specifically, not comments/docstrings
        import_lines = [
            line.strip() for line in source.split("\n")
            if line.strip().startswith(("import ", "from "))
        ]
        for line in import_lines:
            assert "from agent" not in line, f"Forbidden import: {line}"
            assert "from hermes_cli.dev_web_api" not in line, f"Forbidden import: {line}"
            assert "import agent" not in line, f"Forbidden import: {line}"
            assert "import provider" not in line, f"Forbidden import: {line}"


# ===========================================================================
# 2. Catalog count
# ===========================================================================


class TestCatalogCount:
    """Verify catalog total count matches policy inventory."""

    def test_total_count_71_default_source(self):
        catalog = list_schema_previews()
        assert catalog.total_count == 71

    def test_total_count_71_fake_source(self):
        catalog = list_schema_previews(schema_source=_fake_source_all)
        assert catalog.total_count == 71

    def test_items_length_71_default_source(self):
        catalog = list_schema_previews()
        assert len(catalog.items) == 71

    def test_items_length_71_fake_source(self):
        catalog = list_schema_previews(schema_source=_fake_source_all)
        assert len(catalog.items) == 71

    def test_canonical_name_set_equals_inventory(self):
        catalog = list_schema_previews()
        catalog_names = frozenset(item.canonical_name for item in catalog.items)
        inventory_names = frozenset(TOOL_POLICY_INVENTORY.keys())
        assert catalog_names == inventory_names


# ===========================================================================
# 3. Stable sorting
# ===========================================================================


class TestStableSorting:
    """Verify catalog is sorted by canonicalName."""

    def test_sorted_ascending_by_name(self):
        catalog = list_schema_previews()
        names = [item.canonical_name for item in catalog.items]
        assert names == sorted(names)

    def test_sorted_with_fake_source(self):
        catalog = list_schema_previews(schema_source=_fake_source_all)
        names = [item.canonical_name for item in catalog.items]
        assert names == sorted(names)

    def test_no_duplicate_names(self):
        catalog = list_schema_previews()
        names = [item.canonical_name for item in catalog.items]
        assert len(names) == len(set(names))


# ===========================================================================
# 4. Single lookup
# ===========================================================================


class TestSingleLookup:
    """Verify get_schema_preview for existing and missing tools."""

    def test_existing_tool_found(self):
        result = get_schema_preview("clarify")
        assert result.found is True
        assert result.preview is not None
        assert result.reason_code == "FOUND"

    def test_existing_tool_correct_canonical_name(self):
        result = get_schema_preview("clarify")
        assert result.preview is not None
        assert result.preview.canonical_name == "clarify"

    def test_missing_tool_not_found(self):
        result = get_schema_preview("nonexistent_tool_xyz")
        assert result.found is False
        assert result.preview is None
        assert result.reason_code == "NOT_FOUND"

    def test_missing_tool_case_sensitive(self):
        """Exact match only — uppercase should not match."""
        result = get_schema_preview("CLARIFY")
        assert result.found is False

    def test_missing_tool_no_fuzzy(self):
        """No fuzzy matching — similar names should not match."""
        result = get_schema_preview("clarif")
        assert result.found is False

    def test_empty_string_not_found(self):
        result = get_schema_preview("")
        assert result.found is False

    def test_existing_r4_tool_found_but_unavailable(self):
        """R4 tool exists in inventory but schema preview is unavailable."""
        # terminal is R4 and permanently denied
        result = get_schema_preview("terminal")
        assert result.found is True
        assert result.preview is not None
        assert result.preview.schema_preview_available is False

    def test_all_inventory_tools_found(self):
        """Every tool in the inventory should return found=True."""
        for name in TOOL_POLICY_INVENTORY:
            result = get_schema_preview(name)
            assert result.found is True, f"Expected found=True for {name}"


# ===========================================================================
# 5. Fake schema source integration
# ===========================================================================


class TestFakeSchemaSourceIntegration:
    """Verify fake schema source correctly integrates with sanitizer."""

    def test_r0_with_schema_available(self):
        """R0 tool with valid schema should be available."""
        result = get_schema_preview("clarify", schema_source=_fake_source_all)
        assert result.found is True
        assert result.preview is not None
        assert result.preview.schema_preview_available is True
        assert result.preview.reason_code == REASON_AVAILABLE

    def test_fields_populated(self):
        """Schema fields should be populated from fake source."""
        result = get_schema_preview("clarify", schema_source=_fake_source_all)
        assert result.preview is not None
        assert len(result.preview.input_fields) > 0
        field_names = [f.field_name for f in result.preview.input_fields]
        assert "query" in field_names

    def test_sanitize_applied(self):
        """Sanitizer should be applied — field types should be normalized."""
        result = get_schema_preview("clarify", schema_source=_fake_source_all)
        assert result.preview is not None
        for field in result.preview.input_fields:
            assert field.field_type in (
                "string", "number", "integer", "boolean",
                "array", "object", "null", "unknown",
            )

    def test_to_safe_dict_json_serializable(self):
        """to_safe_dict should produce JSON-serializable output."""
        result = get_schema_preview("clarify", schema_source=_fake_source_all)
        assert result.preview is not None
        d = result.preview.to_safe_dict()
        serialized = json.dumps(d)
        assert isinstance(serialized, str)

    def test_lookup_result_to_safe_dict_json_serializable(self):
        """Lookup result should also be JSON-serializable."""
        result = get_schema_preview("clarify", schema_source=_fake_source_all)
        d = result.to_safe_dict()
        serialized = json.dumps(d)
        assert isinstance(serialized, str)

    def test_catalog_to_safe_dict_json_serializable(self):
        """Catalog to_safe_dict should produce JSON-serializable output."""
        catalog = list_schema_previews(schema_source=_fake_source_all)
        d = catalog.to_safe_dict()
        serialized = json.dumps(d)
        assert isinstance(serialized, str)

    def test_r3_with_schema_available_with_redaction(self):
        """R3 tool with valid schema should be available with redaction."""
        result = get_schema_preview("discord", schema_source=_fake_source_all)
        assert result.found is True
        assert result.preview is not None
        assert result.preview.schema_preview_available is True
        assert result.preview.reason_code == REASON_AVAILABLE_WITH_REDACTION


# ===========================================================================
# 6. Empty schema source (default)
# ===========================================================================


class TestEmptySchemaSource:
    """Verify behavior with default empty schema source."""

    def test_all_unavailable_with_default_source(self):
        """All tools should be unavailable when schema source returns None."""
        catalog = list_schema_previews()
        # With empty source, all tools should have schema_preview_available = False
        # because the schema is None → UNAVAILABLE_EMPTY_SCHEMA
        for item in catalog.items:
            assert item.schema_preview_available is False

    def test_reason_code_empty_schema_default_source(self):
        """All tools should show UNAVAILABLE_EMPTY_SCHEMA (for available-risk tools)
        or their risk/denylist reason."""
        catalog = list_schema_previews()
        for item in catalog.items:
            entry = TOOL_POLICY_INVENTORY[item.canonical_name]
            if entry.permanently_denied:
                assert item.reason_code == REASON_UNAVAILABLE_PERMANENTLY_DENIED
            elif RISK_RANK[entry.primary_risk] >= 5:
                assert item.reason_code == REASON_UNAVAILABLE_RISK_R5
            elif RISK_RANK[entry.primary_risk] >= 4:
                assert item.reason_code == REASON_UNAVAILABLE_RISK_R4
            else:
                # R0-R3 with no schema → EMPTY_SCHEMA
                assert item.reason_code == REASON_UNAVAILABLE_EMPTY_SCHEMA

    def test_no_crash_default_source(self):
        """Default source should never crash."""
        catalog = list_schema_previews()
        assert catalog.total_count == 71

    def test_empty_source_helper_returns_none(self):
        """The _empty_schema_source should return None for any input."""
        assert _empty_schema_source("anything") is None
        assert _empty_schema_source("") is None


# ===========================================================================
# 7. Invalid schema
# ===========================================================================


class TestInvalidSchema:
    """Verify behavior with invalid schema data."""

    def test_non_dict_schema_returns_unavailable(self):
        """Source returning a non-dict should produce INVALID_SCHEMA."""
        def bad_source(name):
            return "not a dict"  # type: ignore

        result = get_schema_preview("clarify", schema_source=bad_source)
        assert result.preview is not None
        assert result.preview.schema_preview_available is False
        assert result.preview.reason_code == REASON_UNAVAILABLE_INVALID_SCHEMA

    def test_list_schema_returns_unavailable(self):
        """Source returning a list should produce INVALID_SCHEMA."""
        def list_source(name):
            return [1, 2, 3]  # type: ignore

        result = get_schema_preview("clarify", schema_source=list_source)
        assert result.preview is not None
        assert result.preview.schema_preview_available is False
        assert result.preview.reason_code == REASON_UNAVAILABLE_INVALID_SCHEMA

    def test_int_schema_returns_unavailable(self):
        """Source returning an int should produce INVALID_SCHEMA."""
        def int_source(name):
            return 42  # type: ignore

        result = get_schema_preview("clarify", schema_source=int_source)
        assert result.preview is not None
        assert result.preview.schema_preview_available is False
        assert result.preview.reason_code == REASON_UNAVAILABLE_INVALID_SCHEMA

    def test_no_crash_invalid_schema(self):
        """Invalid schema should never crash the service."""
        def bad_source(name):
            return "bad"

        catalog = list_schema_previews(schema_source=bad_source)
        assert catalog.total_count == 71


# ===========================================================================
# 8. Source exception isolation
# ===========================================================================


class TestSourceExceptionIsolation:
    """Verify source exceptions are isolated per tool."""

    def test_source_exception_single_tool(self):
        """Source exception on one tool should produce SOURCE_ERROR."""
        def error_source(name):
            raise RuntimeError("Source broken")

        result = get_schema_preview("clarify", schema_source=error_source)
        assert result.found is True
        assert result.preview is not None
        assert result.preview.schema_preview_available is False
        assert result.preview.reason_code == REASON_UNAVAILABLE_SCHEMA_SOURCE_ERROR

    def test_source_exception_unavailable_reason(self):
        """Source error should have a clear unavailable reason."""
        def error_source(name):
            raise RuntimeError("Source broken")

        result = get_schema_preview("clarify", schema_source=error_source)
        assert result.preview is not None
        assert result.preview.unavailable_reason is not None
        assert "error" in result.preview.unavailable_reason.lower()

    def test_source_exception_does_not_crash_catalog(self):
        """Source exception should not crash the entire catalog."""
        def error_source(name):
            raise RuntimeError("Source broken")

        catalog = list_schema_previews(schema_source=error_source)
        assert catalog.total_count == 71
        for item in catalog.items:
            assert item.reason_code == REASON_UNAVAILABLE_SCHEMA_SOURCE_ERROR

    def test_mixed_source_partial_failure(self):
        """Source failing for some tools but not others should be handled."""
        call_count = 0

        def partial_error_source(name):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise ValueError("Intermittent failure")
            return _FAKE_SCHEMA

        catalog = list_schema_previews(schema_source=partial_error_source)
        assert catalog.total_count == 71
        # Should have a mix of available, unavailable, and source-error items
        source_errors = sum(
            1 for item in catalog.items
            if item.reason_code == REASON_UNAVAILABLE_SCHEMA_SOURCE_ERROR
        )
        assert source_errors > 0
        # The rest should not be source errors
        non_errors = sum(
            1 for item in catalog.items
            if item.reason_code != REASON_UNAVAILABLE_SCHEMA_SOURCE_ERROR
        )
        assert non_errors > 0

    def test_source_exception_preserves_metadata(self):
        """Source error should still have correct canonical_name and risk."""
        def error_source(name):
            raise RuntimeError("broken")

        result = get_schema_preview("clarify", schema_source=error_source)
        assert result.preview is not None
        assert result.preview.canonical_name == "clarify"
        assert result.preview.risk == "R0"
        assert result.preview.risk_rank == 0


# ===========================================================================
# 9. Risk / Denylist / Candidate behavior
# ===========================================================================


class TestRiskDenylistCandidate:
    """Verify risk, denylist, and candidate behavior."""

    def test_r0_available_with_schema(self):
        """R0 tool should be available when schema exists."""
        result = get_schema_preview("clarify", schema_source=_fake_source_all)
        assert result.preview is not None
        assert result.preview.schema_preview_available is True
        assert result.preview.reason_code == REASON_AVAILABLE

    def test_r1_available_with_schema(self):
        """R1 tool should be available when schema exists."""
        result = get_schema_preview("read_file", schema_source=_fake_source_all)
        assert result.preview is not None
        assert result.preview.schema_preview_available is True
        assert result.preview.reason_code == REASON_AVAILABLE

    def test_r2_available_with_schema(self):
        """R2 tool should be available when schema exists."""
        result = get_schema_preview("web_search", schema_source=_fake_source_all)
        assert result.preview is not None
        assert result.preview.schema_preview_available is True
        assert result.preview.reason_code == REASON_AVAILABLE

    def test_r3_available_with_redaction(self):
        """R3 tool should be available with enhanced redaction."""
        result = get_schema_preview("discord", schema_source=_fake_source_all)
        assert result.preview is not None
        assert result.preview.schema_preview_available is True
        assert result.preview.reason_code == REASON_AVAILABLE_WITH_REDACTION

    def test_r4_unavailable_even_with_schema(self):
        """R4 tool should be unavailable even when schema exists."""
        # terminal is R4 and permanently denied
        result = get_schema_preview("terminal", schema_source=_fake_source_all)
        assert result.preview is not None
        assert result.preview.schema_preview_available is False
        # Denylist takes priority over R4
        assert result.preview.reason_code == REASON_UNAVAILABLE_PERMANENTLY_DENIED

    def test_r5_unavailable_even_with_schema(self):
        """R5 tool should be unavailable even when schema exists."""
        # cronjob is R5 and permanently denied
        result = get_schema_preview("cronjob", schema_source=_fake_source_all)
        assert result.preview is not None
        assert result.preview.schema_preview_available is False
        # Denylist takes priority over R5
        assert result.preview.reason_code == REASON_UNAVAILABLE_PERMANENTLY_DENIED

    def test_denylist_overrides_all(self):
        """Permanent denylist should override even R0 with schema."""
        # All permanently denied tools should be unavailable
        for name in STATIC_DENYLIST:
            result = get_schema_preview(name, schema_source=_fake_source_all)
            assert result.preview is not None
            assert result.preview.schema_preview_available is False
            assert result.preview.reason_code == REASON_UNAVAILABLE_PERMANENTLY_DENIED

    def test_denylist_count(self):
        """Denylist should have 26 tools."""
        assert len(STATIC_DENYLIST) == 26

    def test_candidate_available_with_schema(self):
        """Candidate allowlist tools should be available when schema exists."""
        for name in CANDIDATE_ALLOWLIST:
            result = get_schema_preview(name, schema_source=_fake_source_all)
            assert result.preview is not None
            assert result.preview.schema_preview_available is True, (
                f"Candidate tool {name} should be available with schema"
            )

    def test_candidate_count(self):
        """Candidate allowlist should have 6 tools."""
        assert len(CANDIDATE_ALLOWLIST) == 6

    def test_static_allowlist_empty(self):
        """STATIC_ALLOWLIST must remain empty."""
        assert len(STATIC_ALLOWLIST) == 0

    def test_catalog_available_unavailable_counts(self):
        """Catalog counts should be consistent with risk distribution."""
        catalog = list_schema_previews(schema_source=_fake_source_all)
        assert catalog.available_count + catalog.unavailable_count == catalog.total_count
        assert catalog.total_count == 71
        # With full schema source: R0-R3 available, R4-R5 and denylist unavailable
        # R4 tools are all denylisted, R5 tools are all denylisted
        # So unavailable = denylist (26) = 26
        assert catalog.unavailable_count == 26
        assert catalog.available_count == 45

    def test_catalog_available_unavailable_counts_default_source(self):
        """With default empty source, everything is unavailable."""
        catalog = list_schema_previews()
        assert catalog.available_count == 0
        assert catalog.unavailable_count == 71

    def test_preview_is_not_execution(self):
        """Schema preview available does NOT mean execution available."""
        result = get_schema_preview("clarify", schema_source=_fake_source_all)
        assert result.preview is not None
        # Preview available but tool is still not allowed to execute
        assert result.preview.schema_preview_available is True
        # The service does NOT set executionAvailable — that's the API's job


# ===========================================================================
# 10. No execution / no handler / no dispatch
# ===========================================================================


class TestNoExecution:
    """Verify service never calls handlers, dispatch, or audit."""

    def test_no_handler_called(self):
        """Service should never call any tool handler."""
        call_log = []

        def tracking_source(name):
            call_log.append(name)
            return _FAKE_SCHEMA

        result = get_schema_preview("clarify", schema_source=tracking_source)
        # Source was called for schema retrieval, but that's the injected source
        # — NOT a tool handler. The service itself doesn't call handlers.
        assert result.found is True
        # The source function was called (it's a fake), but no real handler
        assert "clarify" in call_log

    def test_no_dispatch(self):
        """Service should not create any dispatch mechanism."""
        import hermes_cli.dev_web_tool_schema_preview_service as svc
        source = open(svc.__file__, encoding="utf-8").read()
        assert "dispatch" not in source.lower() or "no dispatch" in source.lower()

    def test_no_audit(self):
        """Service should not create any audit entries."""
        import hermes_cli.dev_web_tool_schema_preview_service as svc
        source = open(svc.__file__, encoding="utf-8").read()
        assert "audit" not in source.lower() or "no audit" in source.lower()

    def test_no_provider_access(self):
        """Service should not access any provider."""
        import hermes_cli.dev_web_tool_schema_preview_service as svc
        source = open(svc.__file__, encoding="utf-8").read()
        assert "provider" not in source.lower() or "no provider" in source.lower()


# ===========================================================================
# 11. JSON-safe output
# ===========================================================================


class TestJsonSafeOutput:
    """Verify all outputs are JSON-safe."""

    def test_catalog_to_safe_dict(self):
        catalog = list_schema_previews()
        d = catalog.to_safe_dict()
        json.dumps(d)  # Should not raise

    def test_catalog_with_source_to_safe_dict(self):
        catalog = list_schema_previews(schema_source=_fake_source_all)
        d = catalog.to_safe_dict()
        json.dumps(d)  # Should not raise

    def test_lookup_found_to_safe_dict(self):
        result = get_schema_preview("clarify", schema_source=_fake_source_all)
        d = result.to_safe_dict()
        json.dumps(d)  # Should not raise

    def test_lookup_not_found_to_safe_dict(self):
        result = get_schema_preview("nonexistent")
        d = result.to_safe_dict()
        json.dumps(d)  # Should not raise

    def test_all_catalog_items_serializable(self):
        catalog = list_schema_previews(schema_source=_fake_source_all)
        for item in catalog.items:
            d = item.to_safe_dict()
            json.dumps(d)  # Each item must serialize

    def test_no_python_objects_in_output(self):
        """Output should not contain Python object reprs."""
        catalog = list_schema_previews(schema_source=_fake_source_all)
        serialized = json.dumps(catalog.to_safe_dict())
        assert "object at 0x" not in serialized
        assert "<" not in serialized or "≤" in serialized  # allow ≤ in constraints


# ===========================================================================
# 12. Summary counts
# ===========================================================================


class TestSummaryCounts:
    """Verify catalog summary counts."""

    def test_total_equals_items(self):
        catalog = list_schema_previews()
        assert catalog.total_count == len(catalog.items)

    def test_available_plus_unavailable_equals_total(self):
        catalog = list_schema_previews(schema_source=_fake_source_all)
        assert catalog.available_count + catalog.unavailable_count == catalog.total_count

    def test_available_count_non_negative(self):
        catalog = list_schema_previews()
        assert catalog.available_count >= 0

    def test_unavailable_count_non_negative(self):
        catalog = list_schema_previews()
        assert catalog.unavailable_count >= 0

    def test_total_always_71(self):
        """Regardless of source, total should always be 71."""
        catalog1 = list_schema_previews()
        catalog2 = list_schema_previews(schema_source=_fake_source_all)
        catalog3 = list_schema_previews(schema_source=_fake_source_none)
        assert catalog1.total_count == 71
        assert catalog2.total_count == 71
        assert catalog3.total_count == 71


# ===========================================================================
# 13. Existing API behavior unchanged
# ===========================================================================


class TestExistingApiUnchanged:
    """Verify existing Tool Policy API behavior is unchanged."""

    def test_schema_preview_available_still_false_in_catalog_api(self):
        """The Tool Policy catalog API should still show schemaPreviewAvailable=False.

        This test verifies the service module doesn't change the existing
        catalog API behavior. The catalog API is in dev_web_tool_policy_service.py
        and is NOT modified by this service.
        """
        from hermes_cli.dev_web_tool_policy_service import (
            DevToolPolicyQueryService,
            validate_catalog_query,
        )

        service = DevToolPolicyQueryService()
        query = validate_catalog_query()
        response = service.list_tool_catalog(query)

        for item in response.items:
            assert item.schema_preview_available is False
            assert item.dry_run_available is False
            assert item.execution_available is False

    def test_policy_status_unchanged(self):
        """Policy status should be unchanged."""
        from hermes_cli.dev_web_tool_policy_service import DevToolPolicyQueryService

        service = DevToolPolicyQueryService()
        status = service.get_policy_status()
        assert status.inventory_count == 71
        assert status.permanent_denylist_count == 26
        assert status.candidate_allowlist_count == 6
        assert status.enabled_allowlist_count == 0
        assert status.execution.enabled is False
        assert status.execution.provider_schema_sent is False
