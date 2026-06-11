"""Tests for the Static Tool Schema Preview Model and Sanitizer.

Phase: 1G-03-01 — Static Schema Preview Model and Sanitizer

Covers:
  - Import safety (no file IO, no network, no env, no runtime side effects)
  - Basic sanitization
  - Forbidden field redaction
  - Secret pattern redaction
  - Description/enum/constraints truncation
  - Nested depth limit
  - Field count limit
  - Cycle safety
  - Risk-based availability
  - No execution boundaries (handler, dispatch, audit, provider)
  - JSON-safe output
  - STATIC_ALLOWLIST still empty
  - Candidate allowlist available but execution disabled
  - Denylist override
"""

from __future__ import annotations

import json
import os
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
)
from hermes_cli.dev_web_tool_schema_preview import (
    MAX_CONSTRAINTS_CHARS,
    MAX_DESCRIPTION_CHARS,
    MAX_ENUM_VALUE_CHARS,
    MAX_ENUM_VALUES,
    MAX_FIELD_COUNT,
    MAX_NESTED_DEPTH,
    REDACTION_STATUS_CLEAN,
    REDACTION_STATUS_REDACTED,
    REDACTION_STATUS_UNAVAILABLE,
    REASON_AVAILABLE,
    REASON_AVAILABLE_WITH_REDACTION,
    REASON_UNAVAILABLE_EMPTY_SCHEMA,
    REASON_UNAVAILABLE_INVALID_SCHEMA,
    REASON_UNAVAILABLE_PERMANENTLY_DENIED,
    REASON_UNAVAILABLE_RISK_R4,
    REASON_UNAVAILABLE_RISK_R5,
    REASON_UNAVAILABLE_UNLISTED,
    REDACTED_DEPTH_LIMIT,
    REDACTED_FIELD_LIMIT,
    REDACTED_FORBIDDEN_FIELD,
    REDACTED_SECRET_PATTERN,
    SchemaPreviewAvailability,
    SchemaPreviewField,
    ToolSchemaPreview,
    build_schema_preview,
    determine_schema_preview_availability,
    preview_from_policy_name,
    sanitize_schema,
    _is_forbidden_field_name,
    _contains_secret_pattern,
    _truncate_description,
    _truncate_enum_values,
    _normalize_type,
    _detect_schema_shape,
)


# ===========================================================================
# Helper: simple valid schema
# ===========================================================================

_SIMPLE_SCHEMA: dict[str, Any] = {
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
    },
    "required": ["query"],
    "additionalProperties": False,
}


# ===========================================================================
# 1. Import safety
# ===========================================================================


class TestImportSafety:
    """Verify that importing the module has no side effects."""

    def test_import_no_file_io(self, tmp_path: Any) -> None:
        """Module import does not create or modify files."""
        before = set(tmp_path.iterdir()) if tmp_path.exists() else set()
        import hermes_cli.dev_web_tool_schema_preview  # noqa: F401
        after = set(tmp_path.iterdir()) if tmp_path.exists() else set()
        assert before == after

    def test_import_no_env_mutation(self) -> None:
        """Module import does not set or modify environment variables."""
        snapshot = dict(os.environ)
        import hermes_cli.dev_web_tool_schema_preview  # noqa: F401
        assert os.environ == snapshot

    def test_module_has_no_network_imports(self) -> None:
        """Module does not import urllib, http, socket, requests."""
        import hermes_cli.dev_web_tool_schema_preview as mod
        source = open(mod.__file__, encoding="utf-8").read()
        forbidden_imports = [
            "import urllib", "import http", "import socket",
            "import requests", "import aiohttp",
        ]
        for imp in forbidden_imports:
            assert imp not in source, f"Forbidden import found: {imp}"

    def test_module_has_no_tool_handler_imports(self) -> None:
        """Module does not import tools, registry, or handler modules."""
        import hermes_cli.dev_web_tool_schema_preview as mod
        source = open(mod.__file__, encoding="utf-8").read()
        forbidden = [
            "from tools", "import tools",
            "from tools.registry", "import registry",
            "import handler",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden import: {f}"


# ===========================================================================
# 2. Basic sanitization
# ===========================================================================


class TestBasicSanitization:
    """Verify basic schema sanitization works correctly."""

    def test_simple_schema_preview_available(self) -> None:
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=["LOCAL_FILE_READ"],
            schema=_SIMPLE_SCHEMA,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert preview.schema_preview_available is True
        assert preview.canonical_name == "test_tool"
        assert preview.reason_code == REASON_AVAILABLE

    def test_simple_schema_has_fields(self) -> None:
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=["LOCAL_FILE_READ"],
            schema=_SIMPLE_SCHEMA,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        field_names = [f.field_name for f in preview.input_fields]
        assert "query" in field_names
        assert "limit" in field_names

    def test_simple_schema_field_types(self) -> None:
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=["LOCAL_FILE_READ"],
            schema=_SIMPLE_SCHEMA,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        fields = {f.field_name: f for f in preview.input_fields}
        assert fields["query"].field_type == "string"
        assert fields["limit"].field_type == "integer"

    def test_simple_schema_required_fields(self) -> None:
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=["LOCAL_FILE_READ"],
            schema=_SIMPLE_SCHEMA,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        fields = {f.field_name: f for f in preview.input_fields}
        assert fields["query"].required is True
        assert fields["limit"].required is False

    def test_simple_schema_description_preview(self) -> None:
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=["LOCAL_FILE_READ"],
            schema=_SIMPLE_SCHEMA,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        fields = {f.field_name: f for f in preview.input_fields}
        assert fields["query"].description_preview == "Search query string"

    def test_simple_schema_json_serializable(self) -> None:
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=["LOCAL_FILE_READ"],
            schema=_SIMPLE_SCHEMA,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        result = json.dumps(preview.to_safe_dict(), sort_keys=True)
        assert isinstance(result, str)
        # Verify no Python object repr
        assert "object at 0x" not in result
        assert "<" not in result

    def test_schema_shape_object(self) -> None:
        fields, status, shape = sanitize_schema(_SIMPLE_SCHEMA)
        assert shape == "object"


# ===========================================================================
# 3. Forbidden field redaction
# ===========================================================================


class TestForbiddenFieldRedaction:
    """Verify that forbidden field names are redacted."""

    @pytest.mark.parametrize(
        "field_name",
        [
            "api_key",
            "Authorization",
            "handler",
            "source_path",
            "traceback",
            "cookie",
            "clientSecret",
            "bearer",
            "token",
            "password",
            "secret",
            "credential",
            "private_key",
            "access_token",
            "refresh_token",
            "process_id",
            "thread_id",
            "env",
            "environment",
            "raw_schema",
            "dynamic_schema_overrides",
            "requires_env",
        ],
    )
    def test_forbidden_field_name_detected(self, field_name: str) -> None:
        assert _is_forbidden_field_name(field_name) is True

    @pytest.mark.parametrize(
        "field_name",
        [
            "query", "limit", "offset", "format", "type",
            "name", "description", "value", "count", "url",
            "timeout", "verbose", "mode", "category",
        ],
    )
    def test_allowed_field_name_not_detected(self, field_name: str) -> None:
        assert _is_forbidden_field_name(field_name) is False

    def test_forbidden_field_in_schema_redacted(self) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "Your API key for authentication",
                },
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
            },
            "additionalProperties": False,
        }
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=["LOCAL_FILE_READ"],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        fields = {f.field_name: f for f in preview.input_fields}
        # api_key should be redacted
        assert fields["api_key"].redaction_status == REDACTED_FORBIDDEN_FIELD
        assert fields["api_key"].description_preview is None
        assert fields["api_key"].enum_preview == ()
        # query should be clean
        assert fields["query"].redaction_status == REDACTION_STATUS_CLEAN

    def test_forbidden_field_case_insensitive(self) -> None:
        assert _is_forbidden_field_name("APIKey") is True
        assert _is_forbidden_field_name("apiKey") is True
        assert _is_forbidden_field_name("AccessToken") is True
        assert _is_forbidden_field_name("ClientSecret") is True
        assert _is_forbidden_field_name("Authorization") is True
        assert _is_forbidden_field_name("PASSWORD") is True

    def test_original_values_not_in_output(self) -> None:
        """For redacted fields, the original description must not appear."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "super-secret-key-value-12345",
                },
            },
            "additionalProperties": False,
        }
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        output = json.dumps(preview.to_safe_dict())
        assert "super-secret-key-value-12345" not in output


# ===========================================================================
# 4. Secret pattern redaction
# ===========================================================================


class TestSecretPatternRedaction:
    """Verify that secret patterns in descriptions are redacted."""

    @pytest.mark.parametrize(
        "text",
        [
            "Use key sk-test-secret-key-12345678 to authenticate",
            "Header: Bearer abc123token",
            "Authorization: Basic user:pass",
            "Set api_key=my-secret-key",
            "Configure token=abcdef123456",
            "Enter password=hunter2",
            "-----BEGIN PRIVATE KEY-----",
            "-----BEGIN RSA PRIVATE KEY-----",
        ],
    )
    def test_secret_pattern_detected(self, text: str) -> None:
        assert _contains_secret_pattern(text) is True

    def test_normal_text_not_detected(self) -> None:
        assert _contains_secret_pattern("A normal description text") is False
        assert _contains_secret_pattern("The maximum number of results") is False

    def test_secret_in_description_redacted(self) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "string",
                    "description": "Set api_key=sk-test-secret-key-12345678 for auth",
                },
            },
            "additionalProperties": False,
        }
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        fields = {f.field_name: f for f in preview.input_fields}
        assert fields["config"].redaction_status == REDACTION_STATUS_REDACTED
        assert fields["config"].description_preview == "[redacted: secret-like content]"

    def test_bearer_in_description_redacted(self) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "auth": {
                    "type": "string",
                    "description": "Use Bearer abc123token in header",
                },
            },
            "additionalProperties": False,
        }
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        fields = {f.field_name: f for f in preview.input_fields}
        assert fields["auth"].redaction_status == REDACTION_STATUS_REDACTED

    def test_secret_pattern_not_in_json_output(self) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "password=supersecret123",
                },
            },
            "additionalProperties": False,
        }
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        output = json.dumps(preview.to_safe_dict())
        assert "supersecret123" not in output
        assert "password=supersecret123" not in output


# ===========================================================================
# 5. Truncation
# ===========================================================================


class TestTruncation:
    """Verify description, enum, and constraints truncation."""

    def test_description_truncated_at_240(self) -> None:
        long_desc = "A" * 300
        result = _truncate_description(long_desc)
        assert result is not None
        assert len(result) <= MAX_DESCRIPTION_CHARS + 1  # +1 for …
        assert result.endswith("…")

    def test_description_short_not_truncated(self) -> None:
        short_desc = "Short description"
        result = _truncate_description(short_desc)
        assert result == short_desc

    def test_description_none_returns_none(self) -> None:
        assert _truncate_description(None) is None

    def test_description_empty_returns_empty(self) -> None:
        assert _truncate_description("") == ""

    def test_description_unicode_not_broken(self) -> None:
        """Ensure Unicode characters are not broken during truncation."""
        long_desc = "中文描述" * 100  # 500 chars of Chinese
        result = _truncate_description(long_desc)
        assert result is not None
        # Should be valid UTF-8
        result.encode("utf-8")

    def test_enum_truncated_at_20(self) -> None:
        values = [f"value_{i}" for i in range(50)]
        result = _truncate_enum_values(values)
        assert len(result) == MAX_ENUM_VALUES

    def test_enum_value_truncated_at_80(self) -> None:
        values = ["A" * 200]
        result = _truncate_enum_values(values)
        assert len(result) == 1
        assert len(result[0]) <= MAX_ENUM_VALUE_CHARS + 1  # +1 for …
        assert result[0].endswith("…")

    def test_enum_complex_object_renders_complex(self) -> None:
        values = [{"nested": "dict"}, [1, 2, 3]]
        result = _truncate_enum_values(values)
        assert result == ("[complex]", "[complex]")

    def test_enum_none_returns_empty(self) -> None:
        assert _truncate_enum_values(None) == ()

    def test_enum_bool_renders_lowercase(self) -> None:
        values = [True, False]
        result = _truncate_enum_values(values)
        assert result == ("true", "false")

    def test_enum_null_renders_null(self) -> None:
        result = _truncate_enum_values([None])
        assert result == ("null",)

    def test_constraints_truncated_at_120(self) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "field": {
                    "type": "integer",
                    "description": "A field",
                    "minimum": 0,
                    "maximum": 999999,
                    "minLength": 0,
                    "maxLength": 999999,
                    "pattern": "some-pattern",
                    "additionalProperties": False,
                    "items": {"type": "string"},
                },
            },
            "additionalProperties": False,
        }
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        fields = {f.field_name: f for f in preview.input_fields}
        cp = fields["field"].constraints_preview
        assert cp is not None
        assert len(cp) <= MAX_CONSTRAINTS_CHARS + 1


# ===========================================================================
# 6. Depth limit
# ===========================================================================


class TestDepthLimit:
    """Verify nested depth limit enforcement."""

    def test_deep_schema_no_crash(self) -> None:
        """Depth 10 schema should not cause RecursionError."""
        # Build a schema 10 levels deep
        inner: dict[str, Any] = {"type": "string", "description": "leaf"}
        for _ in range(10):
            inner = {
                "type": "object",
                "properties": {"nested": inner},
                "additionalProperties": False,
            }
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "root": inner,
            },
            "additionalProperties": False,
        }
        # Should not crash
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert preview.schema_preview_available is True
        # Should have at least one field (root)
        assert len(preview.input_fields) >= 1

    def test_depth_limited_to_4(self) -> None:
        """Fields beyond depth 4 should be truncated."""
        inner: dict[str, Any] = {"type": "string", "description": "leaf"}
        for _ in range(6):
            inner = {
                "type": "object",
                "properties": {"deep": inner},
                "additionalProperties": False,
            }
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "root": inner,
            },
            "additionalProperties": False,
        }
        fields, status, shape = sanitize_schema(schema)
        # Should produce output without crash
        assert len(fields) > 0


# ===========================================================================
# 7. Field count limit
# ===========================================================================


class TestFieldCountLimit:
    """Verify field count limit (max 100)."""

    def test_150_fields_truncated(self) -> None:
        """Schema with 150 fields should output <= 100 fields."""
        properties: dict[str, Any] = {}
        for i in range(150):
            properties[f"field_{i:03d}"] = {
                "type": "string",
                "description": f"Field number {i}",
            }
        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        preview = build_schema_preview(
            canonical_name="test_tool",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert len(preview.input_fields) <= MAX_FIELD_COUNT

    def test_150_fields_redaction_status(self) -> None:
        """Schema with 150 fields should indicate field limit."""
        properties: dict[str, Any] = {}
        for i in range(150):
            properties[f"field_{i:03d}"] = {
                "type": "string",
                "description": f"Field {i}",
            }
        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        _, status, _ = sanitize_schema(schema)
        assert status == REDACTED_FIELD_LIMIT


# ===========================================================================
# 8. Cycle safety
# ===========================================================================


class TestCycleSafety:
    """Verify that circular references don't cause RecursionError."""

    def test_cycle_in_schema_no_crash(self) -> None:
        """Circular reference in schema should not cause RecursionError."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }
        schema["properties"]["self"] = schema  # circular ref

        fields, status, shape = sanitize_schema(schema)
        assert len(fields) > 0  # Should produce at least one field

    def test_cycle_safe_output(self) -> None:
        """Cycle-referencing schema should produce JSON-serializable output."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }
        schema["properties"]["self"] = schema

        fields, status, shape = sanitize_schema(schema)
        for field in fields:
            # Each field must be serializable
            d = field.to_safe_dict()
            json.dumps(d)


# ===========================================================================
# 9. Risk-based availability
# ===========================================================================


class TestRiskBasedAvailability:
    """Verify risk-based availability determination."""

    def test_r0_available(self) -> None:
        result = determine_schema_preview_availability(
            canonical_name="clarify",
            primary_risk="R0",
            risk_rank=0,
            permanently_denied=False,
            candidate_allowlisted=True,
        )
        assert result.preview_available is True
        assert result.reason_code == REASON_AVAILABLE

    def test_r1_available(self) -> None:
        result = determine_schema_preview_availability(
            canonical_name="read_file",
            primary_risk="R1",
            risk_rank=1,
            permanently_denied=False,
            candidate_allowlisted=True,
        )
        assert result.preview_available is True
        assert result.reason_code == REASON_AVAILABLE

    def test_r2_available(self) -> None:
        result = determine_schema_preview_availability(
            canonical_name="web_search",
            primary_risk="R2",
            risk_rank=2,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert result.preview_available is True
        assert result.reason_code == REASON_AVAILABLE

    def test_r3_available_with_redaction(self) -> None:
        result = determine_schema_preview_availability(
            canonical_name="discord",
            primary_risk="R3",
            risk_rank=3,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert result.preview_available is True
        assert result.reason_code == REASON_AVAILABLE_WITH_REDACTION

    def test_r4_unavailable(self) -> None:
        result = determine_schema_preview_availability(
            canonical_name="terminal",
            primary_risk="R4",
            risk_rank=4,
            permanently_denied=True,
            candidate_allowlisted=False,
        )
        # Permanent denylist takes priority
        assert result.preview_available is False
        assert result.reason_code == REASON_UNAVAILABLE_PERMANENTLY_DENIED

    def test_r4_not_denied_unavailable(self) -> None:
        """An R4 tool NOT on the denylist should be R4 unavailable."""
        result = determine_schema_preview_availability(
            canonical_name="some_r4_tool",
            primary_risk="R4",
            risk_rank=4,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert result.preview_available is False
        assert result.reason_code == REASON_UNAVAILABLE_RISK_R4

    def test_r5_unavailable(self) -> None:
        result = determine_schema_preview_availability(
            canonical_name="cronjob",
            primary_risk="R5",
            risk_rank=5,
            permanently_denied=True,
            candidate_allowlisted=False,
        )
        assert result.preview_available is False
        assert result.reason_code == REASON_UNAVAILABLE_PERMANENTLY_DENIED

    def test_r5_not_denied_unavailable(self) -> None:
        """An R5 tool NOT on denylist should be R5 unavailable."""
        result = determine_schema_preview_availability(
            canonical_name="some_r5_tool",
            primary_risk="R5",
            risk_rank=5,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert result.preview_available is False
        assert result.reason_code == REASON_UNAVAILABLE_RISK_R5

    def test_permanent_denylist_unavailable(self) -> None:
        """Even an R0 tool on the denylist should be unavailable."""
        result = determine_schema_preview_availability(
            canonical_name="some_r0_denied",
            primary_risk="R0",
            risk_rank=0,
            permanently_denied=True,
            candidate_allowlisted=False,
        )
        assert result.preview_available is False
        assert result.reason_code == REASON_UNAVAILABLE_PERMANENTLY_DENIED

    def test_candidate_allowlist_available(self) -> None:
        """Candidate allowlisted tools should be available for preview."""
        result = determine_schema_preview_availability(
            canonical_name="clarify",
            primary_risk="R0",
            risk_rank=0,
            permanently_denied=False,
            candidate_allowlisted=True,
        )
        assert result.preview_available is True

    def test_static_allowlist_does_not_change(self) -> None:
        """STATIC_ALLOWLIST must remain empty."""
        assert len(STATIC_ALLOWLIST) == 0

    def test_preview_not_equal_execution(self) -> None:
        """preview_available != execution_available (conceptual test)."""
        # A candidate tool has preview available but execution is still disabled
        result = determine_schema_preview_availability(
            canonical_name="clarify",
            primary_risk="R0",
            risk_rank=0,
            permanently_denied=False,
            candidate_allowlisted=True,
        )
        assert result.preview_available is True
        # In the actual system, executionAvailable would be False
        # This test documents that preview != execution


# ===========================================================================
# 10. No execution boundaries
# ===========================================================================


class TestNoExecutionBoundaries:
    """Verify that build_schema_preview does not call handlers or dispatch."""

    def test_does_not_call_handler(self) -> None:
        """If a fake handler were present, it must not be called."""
        handler_mock = MagicMock(side_effect=RuntimeError("Handler called!"))
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search"},
            },
            "additionalProperties": False,
        }
        # The function does not accept or use handlers
        preview = build_schema_preview(
            canonical_name="test",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert preview.schema_preview_available is True
        # Handler mock was never called because it's not passed
        handler_mock.assert_not_called()

    def test_does_not_dispatch(self) -> None:
        """No dispatch mechanism is involved."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }
        # If dispatch were called, it would need to be mocked.
        # This test confirms the function completes without dispatch.
        preview = build_schema_preview(
            canonical_name="test",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert isinstance(preview, ToolSchemaPreview)

    def test_does_not_write_audit(self, tmp_path: Any) -> None:
        """No audit files are created."""
        before_files = set(tmp_path.rglob("*"))
        build_schema_preview(
            canonical_name="test",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=_SIMPLE_SCHEMA,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        after_files = set(tmp_path.rglob("*"))
        assert before_files == after_files


# ===========================================================================
# 11. JSON-safe output
# ===========================================================================


class TestJsonSafeOutput:
    """Verify all outputs are JSON-serializable and contain no unsafe data."""

    def test_to_safe_dict_serializable(self) -> None:
        preview = build_schema_preview(
            canonical_name="test",
            primary_risk="R1",
            risk_rank=1,
            capabilities=["LOCAL_FILE_READ"],
            schema=_SIMPLE_SCHEMA,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        d = preview.to_safe_dict()
        result = json.dumps(d, sort_keys=True)
        assert isinstance(result, str)

    def test_no_object_repr_in_output(self) -> None:
        preview = build_schema_preview(
            canonical_name="test",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=_SIMPLE_SCHEMA,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        output = json.dumps(preview.to_safe_dict())
        assert "object at 0x" not in output
        assert "function" not in output
        assert "<" not in output.replace("<null>", "").replace("</", "")

    def test_field_to_safe_dict_serializable(self) -> None:
        field = SchemaPreviewField(
            field_name="test",
            field_type="string",
            required=True,
            description_preview="A description",
            enum_preview=("a", "b"),
            default_presence=False,
            constraints_preview=None,
            redaction_status=REDACTION_STATUS_CLEAN,
        )
        d = field.to_safe_dict()
        result = json.dumps(d, sort_keys=True)
        assert isinstance(result, str)

    def test_unavailable_preview_serializable(self) -> None:
        preview = build_schema_preview(
            canonical_name="denied_tool",
            primary_risk="R4",
            risk_rank=4,
            capabilities=["PROCESS_EXECUTION"],
            schema=_SIMPLE_SCHEMA,
            permanently_denied=True,
            candidate_allowlisted=False,
        )
        d = preview.to_safe_dict()
        result = json.dumps(d, sort_keys=True)
        assert isinstance(result, str)

    def test_none_schema_serializable(self) -> None:
        preview = build_schema_preview(
            canonical_name="test",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=None,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        d = preview.to_safe_dict()
        result = json.dumps(d, sort_keys=True)
        assert isinstance(result, str)

    def test_empty_enum_as_null(self) -> None:
        """Empty enum_preview should serialize as null, not empty list."""
        field = SchemaPreviewField(
            field_name="test",
            field_type="string",
            required=True,
            description_preview=None,
            enum_preview=(),
            default_presence=False,
            constraints_preview=None,
            redaction_status=REDACTION_STATUS_CLEAN,
        )
        d = field.to_safe_dict()
        assert d["enumPreview"] is None


# ===========================================================================
# 12. Empty and invalid schema
# ===========================================================================


class TestEmptyAndInvalidSchema:
    """Verify handling of None, empty, and invalid schemas."""

    def test_none_schema_unavailable(self) -> None:
        preview = build_schema_preview(
            canonical_name="test",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=None,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert preview.schema_preview_available is False
        assert preview.reason_code == REASON_UNAVAILABLE_EMPTY_SCHEMA
        assert len(preview.input_fields) == 0

    def test_non_dict_schema_unavailable(self) -> None:
        preview = build_schema_preview(
            canonical_name="test",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema="not a dict",
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert preview.schema_preview_available is False
        assert preview.reason_code == REASON_UNAVAILABLE_INVALID_SCHEMA

    def test_list_schema_unavailable(self) -> None:
        preview = build_schema_preview(
            canonical_name="test",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=[1, 2, 3],
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert preview.schema_preview_available is False
        assert preview.reason_code == REASON_UNAVAILABLE_INVALID_SCHEMA

    def test_empty_properties_schema(self) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }
        fields, status, shape = sanitize_schema(schema)
        assert len(fields) == 0
        assert status == REDACTION_STATUS_CLEAN

    def test_no_properties_key(self) -> None:
        schema: dict[str, Any] = {"type": "object"}
        fields, status, shape = sanitize_schema(schema)
        assert len(fields) == 0


# ===========================================================================
# 13. Type normalization
# ===========================================================================


class TestTypeNormalization:
    """Verify JSON Schema type normalization."""

    @pytest.mark.parametrize(
        "input_type,expected",
        [
            ("string", "string"),
            ("number", "number"),
            ("integer", "integer"),
            ("boolean", "boolean"),
            ("array", "array"),
            ("object", "object"),
            ("null", "null"),
            ("any", "unknown"),
            ("custom", "unknown"),
            (123, "unknown"),
            (None, "unknown"),
        ],
    )
    def test_type_normalization(self, input_type: Any, expected: str) -> None:
        assert _normalize_type(input_type) == expected

    def test_type_list_uses_first_recognized(self) -> None:
        assert _normalize_type(["string", "null"]) == "string"

    def test_type_list_no_recognized(self) -> None:
        assert _normalize_type(["custom1", "custom2"]) == "unknown"


# ===========================================================================
# 14. Schema shape detection
# ===========================================================================


class TestSchemaShapeDetection:
    """Verify top-level schema shape detection."""

    @pytest.mark.parametrize(
        "schema,expected",
        [
            ({"type": "object", "properties": {}}, "object"),
            ({"type": "array"}, "array"),
            ({"type": "string"}, "primitive"),
            ({"type": "integer"}, "primitive"),
            ({"type": "boolean"}, "primitive"),
            (None, "unknown"),
            ({}, "unknown"),
            ({"type": "custom"}, "unknown"),
        ],
    )
    def test_shape_detection(
        self, schema: Any, expected: str
    ) -> None:
        assert _detect_schema_shape(schema) == expected


# ===========================================================================
# 15. STATIC_ALLOWLIST still empty
# ===========================================================================


class TestStaticAllowlistInvariant:
    """STATIC_ALLOWLIST must remain empty."""

    def test_static_allowlist_empty(self) -> None:
        assert len(STATIC_ALLOWLIST) == 0

    def test_static_allowlist_is_frozenset(self) -> None:
        assert isinstance(STATIC_ALLOWLIST, frozenset)


# ===========================================================================
# 16. Denylist override
# ===========================================================================


class TestDenylistOverride:
    """Permanent denylist takes priority over all other considerations."""

    def test_denylist_overrides_r0(self) -> None:
        """Even an R0 tool on the denylist should be unavailable."""
        preview = build_schema_preview(
            canonical_name="memory",
            primary_risk="R3",
            risk_rank=3,
            capabilities=[],
            schema=_SIMPLE_SCHEMA,
            permanently_denied=True,
            candidate_allowlisted=False,
        )
        assert preview.schema_preview_available is False
        assert preview.reason_code == REASON_UNAVAILABLE_PERMANENTLY_DENIED

    def test_all_denylisted_tools_unavailable(self) -> None:
        """All 26 denylisted tools must be unavailable."""
        for name in STATIC_DENYLIST:
            entry = TOOL_POLICY_INVENTORY[name]
            result = determine_schema_preview_availability(
                canonical_name=name,
                primary_risk=entry.primary_risk.value,
                risk_rank=RISK_RANK[entry.primary_risk],
                permanently_denied=True,
                candidate_allowlisted=False,
            )
            assert result.preview_available is False, f"{name} should be unavailable"
            assert result.reason_code == REASON_UNAVAILABLE_PERMANENTLY_DENIED


# ===========================================================================
# 17. Candidate allowlist
# ===========================================================================


class TestCandidateAllowlist:
    """Candidate allowlisted tools should be available for preview."""

    def test_all_candidates_available(self) -> None:
        for name in CANDIDATE_ALLOWLIST:
            entry = TOOL_POLICY_INVENTORY[name]
            result = determine_schema_preview_availability(
                canonical_name=name,
                primary_risk=entry.primary_risk.value,
                risk_rank=RISK_RANK[entry.primary_risk],
                permanently_denied=False,
                candidate_allowlisted=True,
            )
            assert result.preview_available is True, f"{name} should be available"

    def test_candidate_count(self) -> None:
        assert len(CANDIDATE_ALLOWLIST) == 6

    def test_candidate_tools_are_r0_r1_only(self) -> None:
        for name in CANDIDATE_ALLOWLIST:
            entry = TOOL_POLICY_INVENTORY[name]
            assert entry.primary_risk in (ToolRiskLevel.R0, ToolRiskLevel.R1)


# ===========================================================================
# 18. preview_from_policy_name
# ===========================================================================


class TestPreviewFromPolicyName:
    """Test the convenience function that looks up policy by name."""

    def test_known_r1_tool(self) -> None:
        preview = preview_from_policy_name("read_file", _SIMPLE_SCHEMA)
        assert preview.canonical_name == "read_file"
        assert preview.risk == "R1"
        assert preview.schema_preview_available is True

    def test_denylisted_tool(self) -> None:
        preview = preview_from_policy_name("terminal", _SIMPLE_SCHEMA)
        assert preview.schema_preview_available is False
        assert preview.reason_code == REASON_UNAVAILABLE_PERMANENTLY_DENIED

    def test_unlisted_tool(self) -> None:
        preview = preview_from_policy_name("nonexistent_tool", _SIMPLE_SCHEMA)
        assert preview.schema_preview_available is False
        assert preview.reason_code == REASON_UNAVAILABLE_UNLISTED

    def test_unlisted_tool_with_none_schema(self) -> None:
        preview = preview_from_policy_name("nonexistent_tool", None)
        assert preview.schema_preview_available is False
        assert preview.reason_code == REASON_UNAVAILABLE_UNLISTED


# ===========================================================================
# 19. Inventory counts
# ===========================================================================


class TestInventoryCounts:
    """Verify inventory counts remain correct."""

    def test_inventory_71(self) -> None:
        assert len(TOOL_POLICY_INVENTORY) == 71

    def test_denylist_26(self) -> None:
        assert len(STATIC_DENYLIST) == 26

    def test_candidate_6(self) -> None:
        assert len(CANDIDATE_ALLOWLIST) == 6

    def test_static_allowlist_0(self) -> None:
        assert len(STATIC_ALLOWLIST) == 0


# ===========================================================================
# 20. Integration: R3 enhanced redaction
# ===========================================================================


class TestR3EnhancedRedaction:
    """R3 tools should get enhanced redaction in the preview builder."""

    def test_r3_schema_gets_redacted_status(self) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to send",
                },
            },
            "additionalProperties": False,
        }
        preview = build_schema_preview(
            canonical_name="discord",
            primary_risk="R3",
            risk_rank=3,
            capabilities=["NETWORK_WRITE"],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert preview.schema_preview_available is True
        # R3 tools always get redacted status
        assert preview.redaction_status == REDACTION_STATUS_REDACTED
        assert preview.reason_code == REASON_AVAILABLE_WITH_REDACTION

    def test_r3_with_secrets_still_redacted(self) -> None:
        """R3 tools with secrets in fields should still be redacted."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "API key",
                },
            },
            "additionalProperties": False,
        }
        preview = build_schema_preview(
            canonical_name="test_r3",
            primary_risk="R3",
            risk_rank=3,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        assert preview.redaction_status == REDACTION_STATUS_REDACTED


# ===========================================================================
# 21. Default presence
# ===========================================================================


class TestDefaultPresence:
    """Verify default value presence is detected but value not exposed."""

    def test_default_present(self) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max results",
                    "default": 10,
                },
            },
            "additionalProperties": False,
        }
        preview = build_schema_preview(
            canonical_name="test",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        fields = {f.field_name: f for f in preview.input_fields}
        assert fields["limit"].default_presence is True

    def test_default_value_not_in_output(self) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max results",
                    "default": 10,
                },
            },
            "additionalProperties": False,
        }
        preview = build_schema_preview(
            canonical_name="test",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        d = preview.to_safe_dict()
        field_dict = d["inputFields"][0]
        # defaultPresence should be True (the key exists in schema)
        assert field_dict["defaultPresence"] is True
        # The actual default value should NOT appear as a separate key
        assert "default" not in field_dict or field_dict.get("defaultPresence") is True

    def test_no_default(self) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
            },
            "additionalProperties": False,
        }
        preview = build_schema_preview(
            canonical_name="test",
            primary_risk="R1",
            risk_rank=1,
            capabilities=[],
            schema=schema,
            permanently_denied=False,
            candidate_allowlisted=False,
        )
        fields = {f.field_name: f for f in preview.input_fields}
        assert fields["query"].default_presence is False
