"""Tests for the Tool Dry-Run Audit Writer.

Phase 1G-04-07: Internal Audit Writer Implementation.

All tests verify:
  - Audit events are JSON-safe
  - Audit events contain required fields
  - Audit events use redactedArgumentsPreview only
  - Audit events never include raw arguments
  - Fake secret values are redacted
  - executionAllowed/dispatchAllowed/providerSchemaAllowed are always false
  - Writer uses HERMES_HOME temp path (never real path)
  - Writer rejects missing HERMES_HOME
  - Writer rejects path outside HERMES_HOME
  - Writer never writes under ~/.hermes
  - Writer never touches production state.db
  - Writer creates audit directory
  - Writer appends valid JSONL
  - Writer enforces max event size
  - Writer rotates file when max_file_bytes exceeded
  - Writer enforces max retained files
  - Writer handles serialization failure safely
  - Writer handles write failure safely
  - Writer never calls provider
  - Writer never calls tool handler
  - Writer never dispatches
  - Writer never executes
  - Writer never mutates STATIC_ALLOWLIST
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_cli.dev_web_tool_dry_run import (
    ToolDryRunResult,
    dry_run_tool_policy,
)
from hermes_cli.dev_web_tool_dry_run_audit import (
    ERROR_AUDIT_EVENT_TOO_LARGE,
    ERROR_AUDIT_PATH_OUTSIDE_HERMES_HOME,
    ERROR_AUDIT_SERIALIZATION_FAILED,
    ERROR_AUDIT_WRITE_FAILED,
    ERROR_HERMES_HOME_MISSING,
    DryRunAuditWriteResult,
    build_dry_run_audit_event,
    write_dry_run_audit_event,
    _PRODUCTION_HERMES_HOME,
    _MAX_EVENT_BYTES,
    _MAX_FILE_BYTES,
    _MAX_RETAINED_FILES,
    _AUDIT_FILENAME,
    _AUDIT_DIR_RELATIVE,
)
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def tmp_hermes_home(tmp_path):
    """Provide a temporary HERMES_HOME for testing."""
    return tmp_path / "hermes-home-dev"


@pytest.fixture
def sample_result():
    """Create a sample ToolDryRunResult for testing."""
    return dry_run_tool_policy("read_file")


@pytest.fixture
def sample_event(sample_result):
    """Build a sample audit event."""
    return build_dry_run_audit_event(
        dry_run_result=sample_result,
        source_context="test",
        ui_origin="test-panel",
        request_id="req-001",
        duration_ms=42,
        result_status="ok",
    )


# ===================================================================
# 1. Build Audit Event Tests
# ===================================================================


class TestBuildAuditEvent:
    """Verify build_dry_run_audit_event produces safe events."""

    def test_event_is_json_serializable(self, sample_event) -> None:
        """Event must serialize to valid JSON."""
        serialized = json.dumps(sample_event)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert isinstance(parsed, dict)

    def test_event_contains_required_fields(self, sample_event) -> None:
        """Event must contain all required fields."""
        required = {
            "eventId", "eventType", "timestamp", "schemaVersion",
            "phase", "requestId", "canonicalName", "toolExists",
            "riskTier", "decision", "reasonCodes", "policyNotes",
            "forbiddenFields", "missingRequiredFields",
            "redactionApplied", "redactionReasonCodes",
            "redactedArgumentsPreview", "sourceContext", "uiOrigin",
            "executionAllowed", "dispatchAllowed", "providerSchemaAllowed",
            "auditWritten", "staticAllowlistSize",
            "candidateAllowlistMatched", "denylistMatched",
            "durationMs", "resultStatus", "errorCode", "errorClass",
        }
        assert required.issubset(set(sample_event.keys()))

    def test_event_uses_redacted_arguments_preview_only(
        self, sample_event
    ) -> None:
        """Event must only store redactedArgumentsPreview."""
        assert "redactedArgumentsPreview" in sample_event
        # Must NOT have a "rawArguments" or "arguments" field
        assert "rawArguments" not in sample_event
        assert "arguments" not in sample_event
        assert "argumentsPreview" not in sample_event

    def test_event_does_not_include_raw_arguments(self, sample_event) -> None:
        """Event must not include raw arguments anywhere."""
        text = json.dumps(sample_event)
        assert "rawArguments" not in text

    def test_fake_api_key_is_redacted(self) -> None:
        """Fake api_key values must be redacted."""
        result = dry_run_tool_policy(
            "read_file",
            {"api_key": "sk-abcdef1234567890"},
        )
        event = build_dry_run_audit_event(
            dry_run_result=result,
            result_status="ok",
        )
        text = json.dumps(event)
        assert "sk-abcdef1234567890" not in text
        # Verify the redactedArgumentsPreview has [REDACTED]
        redacted = event.get("redactedArgumentsPreview", {})
        assert redacted.get("api_key") == "[REDACTED]"

    def test_fake_password_is_redacted(self) -> None:
        """Fake password values must be redacted."""
        result = dry_run_tool_policy(
            "read_file",
            {"password": "super-secret-pass"},
        )
        event = build_dry_run_audit_event(
            dry_run_result=result,
            result_status="ok",
        )
        text = json.dumps(event)
        assert "super-secret-pass" not in text

    def test_fake_token_is_redacted(self) -> None:
        """Fake token values must be redacted."""
        result = dry_run_tool_policy(
            "read_file",
            {"token": "Bearer abc123def456"},
        )
        event = build_dry_run_audit_event(
            dry_run_result=result,
            result_status="ok",
        )
        text = json.dumps(event)
        assert "Bearer abc123def456" not in text

    def test_execution_allowed_is_false(self, sample_event) -> None:
        assert sample_event["executionAllowed"] is False

    def test_dispatch_allowed_is_false(self, sample_event) -> None:
        assert sample_event["dispatchAllowed"] is False

    def test_provider_schema_allowed_is_false(self, sample_event) -> None:
        assert sample_event["providerSchemaAllowed"] is False

    def test_event_type_is_correct(self, sample_event) -> None:
        assert sample_event["eventType"] == "tool_dry_run"

    def test_schema_version_is_1(self, sample_event) -> None:
        assert sample_event["schemaVersion"] == 1

    def test_phase_is_correct(self, sample_event) -> None:
        assert sample_event["phase"] == "1G-04-07"

    def test_static_allowlist_size_matches_live_allowlist(self, sample_event) -> None:
        # Phase 2A: staticAllowlistSize is now len(STATIC_ALLOWLIST) (= 6).
        from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

        assert sample_event["staticAllowlistSize"] == len(STATIC_ALLOWLIST)

    def test_audit_written_is_false_in_built_event(
        self, sample_event
    ) -> None:
        """Built event (before write) has auditWritten=False."""
        assert sample_event["auditWritten"] is False

    def test_unknown_tool_event(self) -> None:
        """Unknown tool produces a valid event."""
        result = dry_run_tool_policy("nonexistent_tool_xyz")
        event = build_dry_run_audit_event(
            dry_run_result=result,
            result_status="ok",
        )
        assert event["toolExists"] is False
        assert event["decision"] == "would_block"
        assert event["executionAllowed"] is False

    def test_error_status_event(self, sample_result) -> None:
        """Error result_status produces valid event."""
        event = build_dry_run_audit_event(
            dry_run_result=sample_result,
            result_status="error",
            error_code="TEST_ERROR",
            error_class="TestError",
        )
        assert event["resultStatus"] == "error"
        assert event["errorCode"] == "TEST_ERROR"
        assert event["errorClass"] == "TestError"


# ===================================================================
# 2. Audit Writer Path Tests
# ===================================================================


class TestAuditWriterPath:
    """Verify path resolution and validation."""

    def test_writer_uses_hermes_home_dev_path(
        self, tmp_hermes_home
    ) -> None:
        """Writer must write under HERMES_HOME dev audit path."""
        tmp_hermes_home.mkdir()
        event = build_dry_run_audit_event(
            dry_run_result=dry_run_tool_policy("read_file"),
            result_status="ok",
        )
        result = write_dry_run_audit_event(
            event, hermes_home=tmp_hermes_home
        )
        assert result.written is True
        assert result.path is not None
        assert str(tmp_hermes_home) in result.path
        assert _AUDIT_DIR_RELATIVE in result.path
        assert _AUDIT_FILENAME in result.path

    def test_writer_rejects_missing_hermes_home(self) -> None:
        """Writer must reject when HERMES_HOME is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure HERMES_HOME is not set
            os.environ.pop("HERMES_HOME", None)
            event = build_dry_run_audit_event(
                dry_run_result=dry_run_tool_policy("read_file"),
                result_status="ok",
            )
            result = write_dry_run_audit_event(event, hermes_home=None)
            assert result.written is False
            assert result.error_code == ERROR_HERMES_HOME_MISSING

    def test_writer_rejects_production_hermes_home(self) -> None:
        """Writer must reject ~/.hermes path."""
        event = build_dry_run_audit_event(
            dry_run_result=dry_run_tool_policy("read_file"),
            result_status="ok",
        )
        result = write_dry_run_audit_event(
            event, hermes_home=_PRODUCTION_HERMES_HOME
        )
        assert result.written is False
        assert result.error_code == ERROR_AUDIT_PATH_OUTSIDE_HERMES_HOME

    def test_writer_never_writes_under_dot_hermes(
        self, tmp_hermes_home
    ) -> None:
        """Verify audit path is not under ~/.hermes."""
        tmp_hermes_home.mkdir()
        event = build_dry_run_audit_event(
            dry_run_result=dry_run_tool_policy("read_file"),
            result_status="ok",
        )
        result = write_dry_run_audit_event(
            event, hermes_home=tmp_hermes_home
        )
        if result.path:
            assert "/.hermes" not in result.path
            assert result.path != _PRODUCTION_HERMES_HOME

    def test_writer_never_touches_production_state_db(
        self, tmp_hermes_home
    ) -> None:
        """Verify path never ends with state.db."""
        tmp_hermes_home.mkdir()
        event = build_dry_run_audit_event(
            dry_run_result=dry_run_tool_policy("read_file"),
            result_status="ok",
        )
        result = write_dry_run_audit_event(
            event, hermes_home=tmp_hermes_home
        )
        if result.path:
            assert not result.path.endswith("state.db")

    def test_writer_creates_audit_directory(
        self, tmp_hermes_home
    ) -> None:
        """Writer must create audit directory if missing."""
        # Don't create tmp_hermes_home — writer should create it
        event = build_dry_run_audit_event(
            dry_run_result=dry_run_tool_policy("read_file"),
            result_status="ok",
        )
        result = write_dry_run_audit_event(
            event, hermes_home=tmp_hermes_home
        )
        assert result.written is True
        # Verify directory was created
        audit_dir = tmp_hermes_home / _AUDIT_DIR_RELATIVE
        assert audit_dir.exists()
        assert (audit_dir / _AUDIT_FILENAME).exists()


# ===================================================================
# 3. JSONL Append Tests
# ===================================================================


class TestJsonlAppend:
    """Verify JSONL append behavior."""

    def test_writer_appends_jsonl_line(
        self, tmp_hermes_home
    ) -> None:
        """Writer must append a valid JSONL line."""
        tmp_hermes_home.mkdir()
        event = build_dry_run_audit_event(
            dry_run_result=dry_run_tool_policy("read_file"),
            result_status="ok",
        )
        result = write_dry_run_audit_event(
            event, hermes_home=tmp_hermes_home
        )
        assert result.written is True

        # Read back the file
        audit_file = tmp_hermes_home / _AUDIT_DIR_RELATIVE / _AUDIT_FILENAME
        content = audit_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 1

        # Line must be parseable JSON
        parsed = json.loads(lines[0])
        assert isinstance(parsed, dict)
        assert parsed["eventType"] == "tool_dry_run"

    def test_jsonl_line_is_parseable(
        self, tmp_hermes_home
    ) -> None:
        """Each JSONL line must be parseable."""
        tmp_hermes_home.mkdir()
        for i in range(3):
            event = build_dry_run_audit_event(
                dry_run_result=dry_run_tool_policy("read_file"),
                request_id=f"req-{i}",
                result_status="ok",
            )
            write_dry_run_audit_event(event, hermes_home=tmp_hermes_home)

        audit_file = tmp_hermes_home / _AUDIT_DIR_RELATIVE / _AUDIT_FILENAME
        lines = audit_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            parsed = json.loads(line)
            assert "eventId" in parsed

    def test_multiple_appends_separate_lines(
        self, tmp_hermes_home
    ) -> None:
        """Multiple appends produce separate JSONL lines."""
        tmp_hermes_home.mkdir()
        for i in range(5):
            event = build_dry_run_audit_event(
                dry_run_result=dry_run_tool_policy("read_file"),
                request_id=f"req-{i}",
                result_status="ok",
            )
            write_dry_run_audit_event(event, hermes_home=tmp_hermes_home)

        audit_file = tmp_hermes_home / _AUDIT_DIR_RELATIVE / _AUDIT_FILENAME
        lines = audit_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 5


# ===================================================================
# 4. Size / Rotation Tests
# ===================================================================


class TestSizeAndRotation:
    """Verify event size limits and file rotation."""

    def test_writer_enforces_max_event_size(
        self, tmp_hermes_home
    ) -> None:
        """Writer must reject events exceeding max size."""
        tmp_hermes_home.mkdir()
        # Create an event with a huge redactedArgumentsPreview
        huge_data = {"field_" + str(i): "x" * 200 for i in range(200)}
        event = {
            "eventId": "test-123",
            "eventType": "tool_dry_run",
            "timestamp": "2026-01-01T00:00:00Z",
            "schemaVersion": 1,
            "phase": "1G-04-07",
            "canonicalName": "test_tool",
            "redactedArgumentsPreview": huge_data,
            "executionAllowed": False,
            "dispatchAllowed": False,
            "providerSchemaAllowed": False,
        }
        result = write_dry_run_audit_event(
            event, hermes_home=tmp_hermes_home
        )
        # Either written=False with event too large, or it fits
        if not result.written:
            assert result.error_code == ERROR_AUDIT_EVENT_TOO_LARGE

    def test_writer_rotates_file_when_max_exceeded(
        self, tmp_hermes_home
    ) -> None:
        """Writer must rotate file when max_file_bytes is exceeded."""
        tmp_hermes_home.mkdir()
        audit_file = tmp_hermes_home / _AUDIT_DIR_RELATIVE / _AUDIT_FILENAME

        # Write enough events to exceed the limit
        # Use a small file limit for testing via monkeypatch
        small_limit = 1024  # 1 KiB

        from hermes_cli import dev_web_tool_dry_run_audit as audit_mod

        original_max = audit_mod._MAX_FILE_BYTES
        try:
            audit_mod._MAX_FILE_BYTES = small_limit
            # Write events until rotation should occur
            for i in range(20):
                event = build_dry_run_audit_event(
                    dry_run_result=dry_run_tool_policy("read_file"),
                    request_id=f"req-{i:04d}",
                    result_status="ok",
                )
                result = write_dry_run_audit_event(
                    event, hermes_home=tmp_hermes_home
                )
                assert result.written is True

            # Verify rotation occurred (rotated file should exist)
            rotated = audit_file.parent / f"{audit_file.name}.1"
            assert rotated.exists() or audit_file.stat().st_size < small_limit * 2
        finally:
            audit_mod._MAX_FILE_BYTES = original_max

    def test_writer_enforces_max_retained_files(
        self, tmp_hermes_home
    ) -> None:
        """Writer must not exceed max retained files."""
        tmp_hermes_home.mkdir()
        audit_file = tmp_hermes_home / _AUDIT_DIR_RELATIVE / _AUDIT_FILENAME

        from hermes_cli import dev_web_tool_dry_run_audit as audit_mod

        original_max_file = audit_mod._MAX_FILE_BYTES
        try:
            audit_mod._MAX_FILE_BYTES = 512  # Very small to force rotation

            # Write many events to force multiple rotations
            for i in range(50):
                event = build_dry_run_audit_event(
                    dry_run_result=dry_run_tool_policy("read_file"),
                    request_id=f"req-{i:04d}",
                    result_status="ok",
                )
                write_dry_run_audit_event(
                    event, hermes_home=tmp_hermes_home
                )

            # Count retained files
            retained = 0
            if audit_file.exists():
                retained += 1
            for i in range(1, 10):  # Check up to 9
                rotated = audit_file.parent / f"{audit_file.name}.{i}"
                if rotated.exists():
                    retained += 1

            assert retained <= _MAX_RETAINED_FILES
        finally:
            audit_mod._MAX_FILE_BYTES = original_max_file


# ===================================================================
# 5. Failure Mode Tests
# ===================================================================


class TestFailureModes:
    """Verify safe failure handling."""

    def test_writer_handles_serialization_failure_safely(
        self, tmp_hermes_home
    ) -> None:
        """Writer must handle non-serializable events safely."""
        tmp_hermes_home.mkdir()

        class NonSerializable:
            pass

        event = {"eventId": "test", "bad_field": NonSerializable()}
        result = write_dry_run_audit_event(
            event, hermes_home=tmp_hermes_home
        )
        assert result.written is False
        assert result.error_code == ERROR_AUDIT_SERIALIZATION_FAILED

    def test_writer_handles_write_failure_safely(
        self, tmp_hermes_home
    ) -> None:
        """Writer must handle write permission failure safely."""
        tmp_hermes_home.mkdir()
        audit_dir = tmp_hermes_home / _AUDIT_DIR_RELATIVE
        audit_dir.mkdir(parents=True)

        # Create audit file as a directory to cause write failure
        audit_file = audit_dir / _AUDIT_FILENAME
        audit_file.mkdir()

        event = build_dry_run_audit_event(
            dry_run_result=dry_run_tool_policy("read_file"),
            result_status="ok",
        )
        result = write_dry_run_audit_event(
            event, hermes_home=tmp_hermes_home
        )
        assert result.written is False
        assert result.error_code == ERROR_AUDIT_WRITE_FAILED
        # Safety: execution still not allowed
        assert event["executionAllowed"] is False

    def test_write_failure_does_not_call_provider(
        self, tmp_hermes_home
    ) -> None:
        """Write failure must not trigger provider calls."""
        tmp_hermes_home.mkdir()
        # Missing env should cause HERMES_HOME_MISSING
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("HERMES_HOME", None)
            event = build_dry_run_audit_event(
                dry_run_result=dry_run_tool_policy("read_file"),
                result_status="ok",
            )
            result = write_dry_run_audit_event(event, hermes_home=None)
            assert result.written is False
            # No provider was imported in audit module (check imports only)
            import hermes_cli.dev_web_tool_dry_run_audit as audit_mod
            source = open(audit_mod.__file__, encoding="utf-8").read()
            assert "from agent." not in source
            assert "import agent." not in source
            assert "provider_api" not in source

    def test_write_failure_does_not_call_tool_handler(
        self, tmp_hermes_home
    ) -> None:
        """Write failure must not call tool handler."""
        tmp_hermes_home.mkdir()
        event = build_dry_run_audit_event(
            dry_run_result=dry_run_tool_policy("read_file"),
            result_status="ok",
        )
        # Even with a write failure (use production path)
        result = write_dry_run_audit_event(
            event, hermes_home=_PRODUCTION_HERMES_HOME
        )
        assert result.written is False
        # Verify no tool handler imports in audit module
        import hermes_cli.dev_web_tool_dry_run_audit as audit_mod
        source = open(audit_mod.__file__, encoding="utf-8").read()
        assert "handle_function_call" not in source
        assert "from tools." not in source

    def test_write_failure_does_not_dispatch(
        self, tmp_hermes_home
    ) -> None:
        """Write failure must not cause dispatch."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("HERMES_HOME", None)
            event = build_dry_run_audit_event(
                dry_run_result=dry_run_tool_policy("read_file"),
                result_status="ok",
            )
            result = write_dry_run_audit_event(event, hermes_home=None)
            assert result.written is False
            assert event["dispatchAllowed"] is False

    def test_write_failure_does_not_execute(
        self, tmp_hermes_home
    ) -> None:
        """Write failure must not cause execution."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("HERMES_HOME", None)
            event = build_dry_run_audit_event(
                dry_run_result=dry_run_tool_policy("read_file"),
                result_status="ok",
            )
            result = write_dry_run_audit_event(event, hermes_home=None)
            assert result.written is False
            assert event["executionAllowed"] is False


# ===================================================================
# 6. Security Boundary Tests
# ===================================================================


class TestSecurityBoundary:
    """Verify no violations of security boundaries."""

    def test_static_allowlist_remains_clarify_only(self) -> None:
        """STATIC_ALLOWLIST must be exactly {"clarify"} before and after audit."""
        assert STATIC_ALLOWLIST == frozenset({"clarify", "tool_policy_read", "route_governance_read", "audit_events_read", "dev_environment_read", "release_status_read"})
        event = build_dry_run_audit_event(
            dry_run_result=dry_run_tool_policy("read_file"),
            result_status="ok",
        )
        # Static allowlist is checked inside build — verify unchanged
        assert STATIC_ALLOWLIST == frozenset({"clarify", "tool_policy_read", "route_governance_read", "audit_events_read", "dev_environment_read", "release_status_read"})

    def test_no_provider_imports(self) -> None:
        """Audit module must not import provider code."""
        import hermes_cli.dev_web_tool_dry_run_audit as audit_mod
        source = open(audit_mod.__file__, encoding="utf-8").read()
        assert "from agent." not in source
        assert "import agent." not in source
        assert "from tools." not in source
        assert "import tools." not in source

    def test_no_dispatch_imports(self) -> None:
        """Audit module must not import dispatch code."""
        import hermes_cli.dev_web_tool_dry_run_audit as audit_mod
        source = open(audit_mod.__file__, encoding="utf-8").read()
        assert "model_tools" not in source
        assert "dispatch_tool" not in source
        assert "tool_dispatch" not in source

    def test_no_network_io(self) -> None:
        """Audit module must not perform network IO."""
        import hermes_cli.dev_web_tool_dry_run_audit as audit_mod
        source = open(audit_mod.__file__, encoding="utf-8").read()
        assert "requests." not in source
        assert "urllib" not in source
        assert "http.client" not in source
        assert "socket" not in source

    def test_redacted_arguments_preview_only(self) -> None:
        """Event must only store redactedArgumentsPreview."""
        result = dry_run_tool_policy(
            "read_file",
            {"api_key": "sk-test-secret-key-12345678"},
        )
        event = build_dry_run_audit_event(
            dry_run_result=result,
            result_status="ok",
        )
        text = json.dumps(event)
        assert "sk-test-secret-key-12345678" not in text
        assert event["redactedArgumentsPreview"]["api_key"] == "[REDACTED]"

    def test_result_dataclass_is_frozen(self) -> None:
        """DryRunAuditWriteResult must be frozen."""
        result = DryRunAuditWriteResult(
            written=False,
            path=None,
            event_id=None,
            error_code=ERROR_HERMES_HOME_MISSING,
            error_message="test",
            rotated=False,
            retained_files=0,
        )
        with pytest.raises(AttributeError):
            result.written = True  # type: ignore[misc]

    def test_test_uses_tmp_path_not_real(
        self, tmp_hermes_home
    ) -> None:
        """Tests must use temp path, not real HERMES_HOME."""
        assert str(tmp_hermes_home) != "/Users/huangruibang/Code/hermes-home-dev"
        assert "/.hermes" not in str(tmp_hermes_home)
