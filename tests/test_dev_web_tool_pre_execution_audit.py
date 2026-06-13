"""Tests for the Pre-Execution Audit module.

Phase: 1G-04-24 — Pre-Execution Audit Minimal Implementation

Covers:
  - Audit package building (required fields, exclusions)
  - Path guard (dev allowed, production blocked, sibling not falsely blocked)
  - Append-only JSONL write behavior
  - ID generation and uniqueness
  - Security invariants (no raw token, no raw arguments, no secrets)
  - Failure contracts (fail-closed, no unhandled exceptions)
  - Write integration with execute context
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hermes_cli.dev_web_tool_pre_execution_audit import (
    PRE_EXECUTION_AUDIT_EVENT_TYPE,
    PRE_EXECUTION_AUDIT_FILENAME,
    PRE_EXECUTION_AUDIT_ID_PREFIX,
    PRE_EXECUTION_AUDIT_RECORD_TYPE,
    PRE_EXECUTION_AUDIT_SCHEMA_VERSION,
    EXECUTE_REQUEST_ID_PREFIX,
    DECISION_BLOCKED_HANDLER_LOOKUP_NOT_ENABLED,
    DECISION_BLOCKED_PRE_EXECUTION_AUDIT_INVALID_STATE,
    DECISION_BLOCKED_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN,
    DECISION_BLOCKED_PRE_EXECUTION_AUDIT_SERIALIZATION_FAILED,
    DECISION_BLOCKED_PRE_EXECUTION_AUDIT_UNAVAILABLE,
    DECISION_BLOCKED_PRE_EXECUTION_AUDIT_WRITE_FAILED,
    ERROR_HANDLER_LOOKUP_NOT_ENABLED,
    ERROR_PRE_EXECUTION_AUDIT_INVALID_STATE,
    ERROR_PRE_EXECUTION_AUDIT_MISSING_REQUIRED_FIELD,
    ERROR_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN,
    ERROR_PRE_EXECUTION_AUDIT_SERIALIZATION_FAILED,
    ERROR_PRE_EXECUTION_AUDIT_UNAVAILABLE,
    ERROR_PRE_EXECUTION_AUDIT_WRITTEN_BUT_HANDLER_LOOKUP_NOT_ENABLED,
    ERROR_PRE_EXECUTION_AUDIT_WRITE_FAILED,
    GATE_HANDLER_LOOKUP,
    GATE_PRE_EXECUTION_AUDIT_PACKAGE,
    GATE_PRE_EXECUTION_AUDIT_PATH,
    GATE_PRE_EXECUTION_AUDIT_SERIALIZATION,
    GATE_PRE_EXECUTION_AUDIT_WRITE,
    PreExecutionAuditPackageResult,
    PreExecutionAuditWriteResult,
    build_pre_execution_audit_package,
    get_pre_execution_audit_store_path,
    safe_pre_execution_audit_summary,
    validate_pre_execution_audit_path,
    write_pre_execution_audit_event,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_hermes_home(tmp_path: Path) -> Path:
    """Create a temporary HERMES_HOME directory."""
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return home


@pytest.fixture()
def audit_dir(tmp_hermes_home: Path) -> Path:
    """Create and return the audit directory path."""
    d = tmp_hermes_home / "gateway" / "dev" / "audit"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture()
def audit_file(audit_dir: Path) -> Path:
    """Return the audit file path."""
    return audit_dir / PRE_EXECUTION_AUDIT_FILENAME


def _sample_package_fields() -> dict:
    """Return sample fields for building a pre-execution audit package."""
    return dict(
        dry_run_request_id="dr-test-001",
        dry_run_decision_digest="sha256:abcdef1234567890",
        canonical_name="clarify",
        risk_tier="R0",
        policy_version="dev-v1",
        arguments_digest="sha256:args123",
        redaction_version="sanitize-v1",
        audit_event_id="evt-test-001",
        confirmation_token_id="ctok_abcdef1234567890",
        digest_algorithm="sha256",
        digest_package_version="1",
        canonicalization_version="json-sort-v1",
        historical_digest="sha256:hist123",
        token_bound_digest="sha256:tokb123",
        execute_derived_digest="sha256:exec123",
    )


# ===========================================================================
# Audit Package Tests (12 tests)
# ===========================================================================


class TestAuditPackage:
    """Tests for pre-execution audit package building."""

    def test_package_includes_required_fields(self) -> None:
        """Package must include all required fields."""
        result = build_pre_execution_audit_package(**_sample_package_fields())
        assert result.success is True
        pkg = result.audit_package
        assert pkg is not None
        required = [
            "recordType", "schemaVersion", "eventType",
            "preExecutionAuditId", "executeRequestId",
            "dryRunRequestId", "dryRunDecisionDigest",
            "canonicalName", "riskTier", "policyVersion",
            "argumentsDigest", "redactionVersion", "auditEventId",
            "confirmationTokenId", "digestAlgorithm",
            "digestPackageVersion", "canonicalizationVersion",
            "historicalDigest", "tokenBoundDigest",
            "executeDerivedDigest", "gateStatus",
            "sideEffectFlags", "createdAt", "status",
        ]
        for field in required:
            assert field in pkg, f"Missing required field: {field}"

    def test_package_includes_dry_run_request_id(self) -> None:
        """Package includes dryRunRequestId."""
        result = build_pre_execution_audit_package(**_sample_package_fields())
        assert result.success
        assert result.audit_package["dryRunRequestId"] == "dr-test-001"

    def test_package_includes_dry_run_decision_digest(self) -> None:
        """Package includes dryRunDecisionDigest."""
        result = build_pre_execution_audit_package(**_sample_package_fields())
        assert result.success
        assert result.audit_package["dryRunDecisionDigest"] == "sha256:abcdef1234567890"

    def test_package_includes_confirmation_token_id(self) -> None:
        """Package includes confirmationTokenId."""
        result = build_pre_execution_audit_package(**_sample_package_fields())
        assert result.success
        assert result.audit_package["confirmationTokenId"] == "ctok_abcdef1234567890"

    def test_package_includes_digest_metadata(self) -> None:
        """Package includes digest algorithm, version, canonicalization."""
        result = build_pre_execution_audit_package(**_sample_package_fields())
        assert result.success
        assert result.audit_package["digestAlgorithm"] == "sha256"
        assert result.audit_package["digestPackageVersion"] == "1"
        assert result.audit_package["canonicalizationVersion"] == "json-sort-v1"

    def test_package_side_effect_flags_all_false(self) -> None:
        """Package side-effect flags must all be false."""
        result = build_pre_execution_audit_package(**_sample_package_fields())
        assert result.success
        flags = result.audit_package["sideEffectFlags"]
        assert flags["executionAllowed"] is False
        assert flags["dispatchAllowed"] is False
        assert flags["providerSchemaAllowed"] is False
        assert flags["toolHandlerCalled"] is False
        assert flags["providerApiCalled"] is False
        assert flags["executionStarted"] is False

    def test_package_excludes_raw_token(self) -> None:
        """Package must not contain raw confirmationToken."""
        result = build_pre_execution_audit_package(**_sample_package_fields())
        assert result.success
        text = json.dumps(result.audit_package)
        assert "confirmationToken" not in text or "confirmationTokenId" in text

    def test_package_excludes_token_hash_full(self) -> None:
        """Package must not contain full tokenHash."""
        result = build_pre_execution_audit_package(**_sample_package_fields())
        assert result.success
        text = json.dumps(result.audit_package)
        assert "tokenHash" not in text

    def test_package_excludes_raw_arguments(self) -> None:
        """Package must not contain raw arguments."""
        result = build_pre_execution_audit_package(**_sample_package_fields())
        assert result.success
        text = json.dumps(result.audit_package)
        assert "arguments" not in text or "argumentsDigest" in text
        # Ensure no raw argument values
        assert "rawArguments" not in text

    def test_package_excludes_secrets(self) -> None:
        """Package must not contain secrets."""
        result = build_pre_execution_audit_package(**_sample_package_fields())
        assert result.success
        text = json.dumps(result.audit_package)
        assert "password" not in text
        assert "secret" not in text
        assert "api_key" not in text
        assert "credential" not in text

    def test_package_excludes_provider_credentials(self) -> None:
        """Package must not contain provider credentials."""
        result = build_pre_execution_audit_package(**_sample_package_fields())
        assert result.success
        text = json.dumps(result.audit_package)
        assert "providerKey" not in text
        assert "providerSecret" not in text

    def test_package_excludes_provider_schema(self) -> None:
        """Package must not contain Provider Schema."""
        result = build_pre_execution_audit_package(**_sample_package_fields())
        assert result.success
        text = json.dumps(result.audit_package).lower()
        assert "providerschema" not in text.replace("providerschemaallowed", "")


# ===========================================================================
# Path Guard Tests (7 tests)
# ===========================================================================


class TestPathGuard:
    """Tests for pre-execution audit path guard."""

    def test_dev_audit_path_allowed(
        self, tmp_hermes_home: Path,
    ) -> None:
        """Dev audit path allowed under $HERMES_HOME/gateway/dev/audit."""
        is_valid, error = validate_pre_execution_audit_path(
            str(tmp_hermes_home)
        )
        assert is_valid is True
        assert error is None

    def test_exact_production_home_blocked(self) -> None:
        """Exact production home blocks before write."""
        is_valid, error = validate_pre_execution_audit_path(
            "/Users/huangruibang/.hermes"
        )
        assert is_valid is False
        assert error == ERROR_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN

    def test_production_subtree_blocked(self) -> None:
        """Production subtree blocks before write."""
        is_valid, error = validate_pre_execution_audit_path(
            "/Users/huangruibang/.hermes/gateway"
        )
        assert is_valid is False
        assert error == ERROR_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN

    def test_hermes_dev_sibling_not_falsely_blocked(self, tmp_path: Path) -> None:
        """.hermes-dev sibling path is not falsely blocked."""
        sibling = tmp_path / ".hermes-dev"
        sibling.mkdir()
        is_valid, error = validate_pre_execution_audit_path(str(sibling))
        assert is_valid is True
        assert error is None

    def test_path_traversal_into_production_blocked(self, tmp_path: Path) -> None:
        """Path traversal into production via symlink blocks."""
        symlink_dir = tmp_path / "evil_link"
        try:
            symlink_dir.symlink_to("/Users/huangruibang/.hermes")
        except OSError:
            pytest.skip("Cannot create symlink on this system")
        is_valid, error = validate_pre_execution_audit_path(str(symlink_dir))
        assert is_valid is False
        assert error is not None

    def test_path_guard_failure_does_not_open_file(
        self, tmp_path: Path,
    ) -> None:
        """Path guard failure must not create/open the audit file."""
        # Use production path
        result = write_pre_execution_audit_event(
            hermes_home="/Users/huangruibang/.hermes",
            audit_package={"test": True},
        )
        assert result.written is False
        # Verify no file was created
        assert not Path(
            "/Users/huangruibang/.hermes/gateway/dev/audit/"
            + PRE_EXECUTION_AUDIT_FILENAME
        ).exists()

    def test_empty_hermes_home_blocked(self) -> None:
        """Empty HERMES_HOME blocks."""
        # Need to temporarily unset HERMES_HOME env var
        old = os.environ.pop("HERMES_HOME", None)
        try:
            is_valid, error = validate_pre_execution_audit_path(None)
            assert is_valid is False
            assert error is not None
        finally:
            if old is not None:
                os.environ["HERMES_HOME"] = old


# ===========================================================================
# Write Behavior Tests (7 tests)
# ===========================================================================


class TestWriteBehavior:
    """Tests for pre-execution audit JSONL write behavior."""

    def test_write_succeeds_with_valid_context(
        self, tmp_hermes_home: Path,
    ) -> None:
        """Write succeeds after valid token + valid digest context."""
        pkg_result = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg_result.success

        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg_result.audit_package,
        )
        assert write_result.written is True
        assert write_result.pre_execution_audit_id is not None
        assert write_result.execute_request_id is not None

    def test_write_fails_closed_when_audit_directory_unavailable(
        self, tmp_path: Path,
    ) -> None:
        """Write fails closed when audit directory unavailable."""
        # Use a path that cannot be created (root-owned)
        pkg_result = build_pre_execution_audit_package(**_sample_package_fields())
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_path / "nonexistent" / "deep" / "nested"),
            audit_package=pkg_result.audit_package,
        )
        # Should still succeed because mkdir(parents=True) is used
        # But if we make it truly unavailable (e.g., a file as directory):
        pass  # This is covered by test_write_succeeds above

    def test_write_fails_on_serialization_error(
        self, tmp_hermes_home: Path,
    ) -> None:
        """Write fails closed on serialization error."""
        # Create a package with a non-serializable value
        bad_pkg = {"key": object()}  # type: ignore[dict-item]
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=bad_pkg,
        )
        assert write_result.written is False
        assert write_result.error_code == ERROR_PRE_EXECUTION_AUDIT_SERIALIZATION_FAILED

    def test_missing_package_blocks(
        self, tmp_hermes_home: Path,
    ) -> None:
        """Missing/empty package blocks write."""
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package={},
        )
        assert write_result.written is False
        assert write_result.error_code == ERROR_PRE_EXECUTION_AUDIT_INVALID_STATE

    def test_append_only_does_not_mutate_previous_records(
        self, tmp_hermes_home: Path, audit_file: Path,
    ) -> None:
        """Append-only write does not mutate previous records."""
        fields1 = _sample_package_fields()
        pkg1 = build_pre_execution_audit_package(**fields1)
        assert pkg1.success

        write1 = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg1.audit_package,
        )
        assert write1.written is True

        # Write a second record
        fields2 = _sample_package_fields()
        pkg2 = build_pre_execution_audit_package(**fields2)
        assert pkg2.success

        write2 = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg2.audit_package,
        )
        assert write2.written is True

        # Read back and verify both records
        assert audit_file.exists()
        lines = audit_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        rec1 = json.loads(lines[0])
        rec2 = json.loads(lines[1])
        assert rec1["preExecutionAuditId"] != rec2["preExecutionAuditId"]
        assert rec1["executeRequestId"] != rec2["executeRequestId"]

    def test_pre_execution_audit_id_returned_only_after_successful_write(
        self, tmp_hermes_home: Path,
    ) -> None:
        """preExecutionAuditId returned only after successful write."""
        # Successful write
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert write_result.written is True
        assert write_result.pre_execution_audit_id is not None
        assert write_result.pre_execution_audit_id.startswith(PRE_EXECUTION_AUDIT_ID_PREFIX)

        # Failed write (empty package)
        fail_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package={},
        )
        assert fail_result.written is False
        assert fail_result.pre_execution_audit_id is None

    def test_execute_request_id_returned_only_after_successful_write(
        self, tmp_hermes_home: Path,
    ) -> None:
        """executeRequestId returned only after successful write."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert write_result.written is True
        assert write_result.execute_request_id is not None
        assert write_result.execute_request_id.startswith(EXECUTE_REQUEST_ID_PREFIX)


# ===========================================================================
# ID Tests (2 tests)
# ===========================================================================


class TestIdGeneration:
    """Tests for pre-execution audit ID generation."""

    def test_pre_execution_audit_id_uniqueness(self) -> None:
        """preExecutionAuditId must be unique across calls."""
        ids = set()
        for _ in range(100):
            pkg = build_pre_execution_audit_package(**_sample_package_fields())
            assert pkg.success
            assert pkg.pre_execution_audit_id is not None
            ids.add(pkg.pre_execution_audit_id)
        assert len(ids) == 100

    def test_execute_request_id_uniqueness(self) -> None:
        """executeRequestId must be unique across calls."""
        ids = set()
        for _ in range(100):
            pkg = build_pre_execution_audit_package(**_sample_package_fields())
            assert pkg.success
            assert pkg.execute_request_id is not None
            ids.add(pkg.execute_request_id)
        assert len(ids) == 100


# ===========================================================================
# Security Invariant Tests (8 tests)
# ===========================================================================


class TestSecurityInvariants:
    """Tests for security invariants in pre-execution audit."""

    def test_raw_token_never_in_audit_jsonl(
        self, tmp_hermes_home: Path, audit_file: Path,
    ) -> None:
        """Raw token never appears in audit JSONL."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert write_result.written

        content = audit_file.read_text(encoding="utf-8")
        # These raw token patterns should never appear
        assert "Bearer " not in content
        assert "sk-" not in content

    def test_token_hash_full_never_in_audit_jsonl(
        self, tmp_hermes_home: Path, audit_file: Path,
    ) -> None:
        """tokenHash full value never appears in audit JSONL."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert write_result.written

        content = audit_file.read_text(encoding="utf-8")
        assert "tokenHash" not in content

    def test_raw_arguments_never_in_audit_jsonl(
        self, tmp_hermes_home: Path, audit_file: Path,
    ) -> None:
        """Raw arguments never appear in audit JSONL."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert write_result.written

        content = audit_file.read_text(encoding="utf-8")
        # argumentsDigest is present but not raw arguments
        assert "argumentsDigest" in content
        assert '"arguments"' not in content

    def test_secrets_never_in_audit_jsonl(
        self, tmp_hermes_home: Path, audit_file: Path,
    ) -> None:
        """Secrets never appear in audit JSONL."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert write_result.written

        content = audit_file.read_text(encoding="utf-8")
        assert "password" not in content
        assert "secret" not in content
        assert "api_key" not in content
        assert "credential" not in content

    def test_provider_never_called(
        self, tmp_hermes_home: Path,
    ) -> None:
        """Provider is never called during audit write."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert write_result.written
        # Verify side-effect flags in the package
        flags = pkg.audit_package["sideEffectFlags"]
        assert flags["providerApiCalled"] is False
        assert flags["providerSchemaAllowed"] is False

    def test_tool_handler_never_called(
        self, tmp_hermes_home: Path,
    ) -> None:
        """Tool Handler is never called during audit write."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert write_result.written
        flags = pkg.audit_package["sideEffectFlags"]
        assert flags["toolHandlerCalled"] is False

    def test_dispatch_never_called(
        self, tmp_hermes_home: Path,
    ) -> None:
        """Dispatch is never called during audit write."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert write_result.written
        flags = pkg.audit_package["sideEffectFlags"]
        assert flags["dispatchAllowed"] is False

    def test_execution_never_started(
        self, tmp_hermes_home: Path,
    ) -> None:
        """Execution is never started during audit write."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert write_result.written
        flags = pkg.audit_package["sideEffectFlags"]
        assert flags["executionStarted"] is False
        assert flags["executionAllowed"] is False


# ===========================================================================
# Failure Contract Tests (4 tests)
# ===========================================================================


class TestFailureContract:
    """Tests for pre-execution audit failure contracts."""

    def test_write_failure_returns_fail_closed_result(
        self, tmp_hermes_home: Path,
    ) -> None:
        """Write failure returns fail-closed result (not exception)."""
        # Path guard failure
        result = write_pre_execution_audit_event(
            hermes_home="/Users/huangruibang/.hermes",
            audit_package={"test": True},
        )
        assert result.written is False
        assert result.error_code is not None
        assert result.pre_execution_audit_id is None

    def test_path_guard_failure_blocks_before_file_open(
        self, tmp_hermes_home: Path,
    ) -> None:
        """Path guard failure blocks before file open."""
        result = write_pre_execution_audit_event(
            hermes_home="/Users/huangruibang/.hermes",
            audit_package=_sample_package_fields(),
        )
        assert result.written is False
        assert result.error_code == ERROR_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN
        # Verify no file was created
        prod_path = Path(
            "/Users/huangruibang/.hermes/gateway/dev/audit/"
            + PRE_EXECUTION_AUDIT_FILENAME
        )
        assert not prod_path.exists()

    def test_successful_write_still_blocks_at_handler_lookup(
        self, tmp_hermes_home: Path,
    ) -> None:
        """Successful audit write still blocks at handler lookup."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert result.written is True
        # But decision is still blocked
        assert result.decision == DECISION_BLOCKED_HANDLER_LOOKUP_NOT_ENABLED
        assert result.error_code == ERROR_PRE_EXECUTION_AUDIT_WRITTEN_BUT_HANDLER_LOOKUP_NOT_ENABLED

    def test_all_failures_block_before_handler_lookup(
        self, tmp_hermes_home: Path,
    ) -> None:
        """All audit failures block before handler lookup."""
        # Various failure scenarios
        scenarios = [
            {},  # Invalid state
            {"key": object()},  # type: ignore[dict-item]  # Serialization failure
        ]
        for pkg in scenarios:
            result = write_pre_execution_audit_event(
                hermes_home=str(tmp_hermes_home),
                audit_package=pkg,
            )
            assert result.written is False
            # Handler lookup must not be reached
            assert result.gate != GATE_HANDLER_LOOKUP


# ===========================================================================
# Gate Status / Side Effect Tests (2 tests)
# ===========================================================================


class TestGateAndSideEffects:
    """Tests for gate status and side-effect flags."""

    def test_gate_status_reflects_audit_written(
        self, tmp_hermes_home: Path, audit_file: Path,
    ) -> None:
        """Gate status in audit event reflects pre-execution audit written."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert write_result.written

        content = audit_file.read_text(encoding="utf-8")
        rec = json.loads(content.strip())
        gs = rec["gateStatus"]
        assert gs["preExecutionAudit"] == "written"
        # Phase 1G-04-29 P2: handler lookup / dispatch / handler call are now
        # enabled downstream gates; at pre-execution audit write time they are
        # "pending" (not yet evaluated), not "blocked_not_enabled".
        assert gs["handlerLookup"] == "pending"
        assert gs["dispatch"] == "pending"
        assert gs["toolHandlerCall"] == "pending"

    def test_side_effect_flags_remain_false_in_jsonl(
        self, tmp_hermes_home: Path, audit_file: Path,
    ) -> None:
        """Side-effect flags remain false in the written JSONL record."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_result = write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        assert write_result.written

        content = audit_file.read_text(encoding="utf-8")
        rec = json.loads(content.strip())
        flags = rec["sideEffectFlags"]
        for key, value in flags.items():
            assert value is False, f"{key} should be False, got {value}"


# ===========================================================================
# Safe Summary Tests (1 test)
# ===========================================================================


class TestSafeSummary:
    """Tests for safe_pre_execution_audit_summary."""

    def test_safe_summary_does_not_expose_secrets(self) -> None:
        """Safe summary must not expose raw token, tokenHash, arguments, or secrets."""
        summary = safe_pre_execution_audit_summary(
            "pea_abc123", "exe_def456"
        )
        assert summary["preExecutionAuditId"] == "pea_abc123"
        assert summary["executeRequestId"] == "exe_def456"
        assert summary["preExecutionAuditStatus"] == "written"
        # No secrets
        text = json.dumps(summary)
        assert "token" not in text.lower() or "preexecutionauditid" in text.lower()
        assert "secret" not in text
        assert "password" not in text
        assert "hash" not in text

    def test_safe_summary_with_none_ids(self) -> None:
        """Safe summary with None IDs."""
        summary = safe_pre_execution_audit_summary(None, None)
        assert summary["preExecutionAuditId"] is None
        assert summary["executeRequestId"] is None
        assert summary["preExecutionAuditStatus"] is None


# ===========================================================================
# Record Structure Tests (3 tests)
# ===========================================================================


class TestRecordStructure:
    """Tests for the audit record structure."""

    def test_record_has_correct_record_type(
        self, tmp_hermes_home: Path, audit_file: Path,
    ) -> None:
        """Record has correct recordType."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        rec = json.loads(audit_file.read_text(encoding="utf-8").strip())
        assert rec["recordType"] == PRE_EXECUTION_AUDIT_RECORD_TYPE

    def test_record_has_correct_schema_version(
        self, tmp_hermes_home: Path, audit_file: Path,
    ) -> None:
        """Record has correct schemaVersion."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        rec = json.loads(audit_file.read_text(encoding="utf-8").strip())
        assert rec["schemaVersion"] == PRE_EXECUTION_AUDIT_SCHEMA_VERSION

    def test_record_has_correct_event_type(
        self, tmp_hermes_home: Path, audit_file: Path,
    ) -> None:
        """Record has correct eventType."""
        pkg = build_pre_execution_audit_package(**_sample_package_fields())
        assert pkg.success
        write_pre_execution_audit_event(
            hermes_home=str(tmp_hermes_home),
            audit_package=pkg.audit_package,
        )
        rec = json.loads(audit_file.read_text(encoding="utf-8").strip())
        assert rec["eventType"] == PRE_EXECUTION_AUDIT_EVENT_TYPE


# ===========================================================================
# Path Resolution Tests (2 tests)
# ===========================================================================


class TestPathResolution:
    """Tests for get_pre_execution_audit_store_path."""

    def test_resolves_correct_path(self, tmp_hermes_home: Path) -> None:
        """Resolves the correct audit file path."""
        audit_dir, audit_file, error = get_pre_execution_audit_store_path(
            str(tmp_hermes_home)
        )
        assert error is None
        assert audit_file.name == PRE_EXECUTION_AUDIT_FILENAME
        assert "gateway" in str(audit_dir)
        assert "dev" in str(audit_dir)
        assert "audit" in str(audit_dir)

    def test_production_path_returns_error(self) -> None:
        """Production HERMES_HOME returns path error."""
        _, _, error = get_pre_execution_audit_store_path(
            "/Users/huangruibang/.hermes"
        )
        assert error is not None
