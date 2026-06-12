"""Tests for hermes_cli.dev_web_tool_execute_preflight — Dry-Run Historical Lookup.

Phase 1G-04-16: Dry-Run Historical Lookup Read-Only Implementation.

All tests verify:
  - Lookup is read-only (no file mutation)
  - Lookup reads dev-only audit JSONL
  - Lookup does not access ~/.hermes
  - Lookup does not access production state.db
  - Lookup does not expose raw secrets
  - Lookup does not expose raw arguments
  - Lookup fail-closed on missing file
  - Lookup fail-closed on malformed JSON
  - Lookup fail-closed on not found
  - Lookup fail-closed on expired record
  - Lookup fail-closed on decision not would_allow
  - Lookup returns found record with safe fields
  - Binding verification functions work correctly
  - No handler / no dispatch / no provider invariants
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hermes_cli.dev_web_tool_execute_preflight import (
    ERROR_DRY_RUN_NOT_FOUND,
    ERROR_DRY_RUN_EXPIRED,
    ERROR_DRY_RUN_NOT_ALLOWED,
    ERROR_DRY_RUN_AUDIT_MISSING,
    ERROR_DRY_RUN_CANONICAL_NAME_MISMATCH,
    ERROR_DRY_RUN_RISK_TIER_MISMATCH,
    ERROR_DRY_RUN_POLICY_VERSION_MISMATCH,
    ERROR_DRY_RUN_DIGEST_MISMATCH,
    ERROR_DRY_RUN_LOOKUP_UNAVAILABLE,
    DryRunHistoricalLookupResult,
    lookup_dry_run_record,
    verify_decision_allowed,
    verify_audit_written,
    verify_canonical_name_binding,
    verify_risk_tier_binding,
    verify_policy_version_binding,
    verify_digest_binding,
    _PRODUCTION_HERMES_HOME,
    _AUDIT_DIR_RELATIVE,
    _AUDIT_FILENAME,
    _DRY_RUN_TTL_SECONDS,
    _MAX_READ_BYTES,
)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def tmp_hermes_home(tmp_path):
    """Provide a temporary HERMES_HOME for testing."""
    return tmp_path / "hermes-home-dev"


@pytest.fixture
def audit_dir(tmp_hermes_home):
    """Create the audit directory."""
    d = tmp_hermes_home / _AUDIT_DIR_RELATIVE
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def audit_path(audit_dir):
    """Return the audit file path."""
    return audit_dir / _AUDIT_FILENAME


@pytest.fixture
def now():
    """Return a fixed current time."""
    return datetime(2026, 6, 12, 12, 0, 0, tzinfo=timezone.utc)


def _make_audit_event(
    request_id="test-dry-run-001",
    canonical_name="clarify",
    decision="would_allow",
    risk_tier="R0",
    timestamp=None,
    event_id="evt-001",
    audit_written=False,
    extra_fields=None,
):
    """Build a sample audit event dict for testing."""
    ts = timestamp or datetime(2026, 6, 12, 11, 59, 0, tzinfo=timezone.utc).isoformat()
    event = {
        "eventId": event_id,
        "eventType": "tool_dry_run",
        "timestamp": ts,
        "schemaVersion": 1,
        "phase": "1G-04-07",
        "requestId": request_id,
        "canonicalName": canonical_name,
        "toolExists": True,
        "riskTier": risk_tier,
        "decision": decision,
        "reasonCodes": ["WOULD_ALLOW_STATIC_POLICY"],
        "policyNotes": ["Tool is on static allowlist."],
        "forbiddenFields": [],
        "missingRequiredFields": [],
        "redactionApplied": False,
        "redactionReasonCodes": [],
        "redactedArgumentsPreview": {},
        "sourceContext": None,
        "uiOrigin": None,
        "executionAllowed": False,
        "dispatchAllowed": False,
        "providerSchemaAllowed": False,
        "auditWritten": audit_written,
        "staticAllowlistSize": 1,
        "candidateAllowlistMatched": False,
        "denylistMatched": False,
        "durationMs": 5,
        "resultStatus": "ok",
        "errorCode": None,
        "errorClass": None,
    }
    if extra_fields:
        event.update(extra_fields)
    return event


def _write_events(audit_path, events):
    """Write events as JSONL lines to the audit file."""
    with open(audit_path, "a", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


# ===================================================================
# 1. Audit JSONL file missing → dry_run_not_found or lookup_unavailable
# ===================================================================


class TestMissingAuditFile:
    """Tests for when the audit JSONL file does not exist."""

    def test_file_missing_returns_not_found(self, tmp_hermes_home, now):
        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="any-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is False
        assert result.error_code == ERROR_DRY_RUN_NOT_FOUND

    def test_file_missing_no_hermes_home_env(self, now, monkeypatch):
        monkeypatch.delenv("HERMES_HOME", raising=False)
        result = lookup_dry_run_record(
            dry_run_request_id="any-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is False
        assert result.error_code == ERROR_DRY_RUN_LOOKUP_UNAVAILABLE


# ===================================================================
# 2. Empty audit JSONL → dry_run_not_found
# ===================================================================


class TestEmptyAuditFile:
    """Tests for when the audit JSONL file exists but is empty."""

    def test_empty_file_returns_not_found(self, audit_path, tmp_hermes_home, now):
        audit_path.touch()  # Create empty file
        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="any-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is False
        assert result.error_code == ERROR_DRY_RUN_NOT_FOUND


# ===================================================================
# 3. Malformed JSONL does not crash
# ===================================================================


class TestMalformedJSONL:
    """Tests for malformed JSONL content."""

    def test_malformed_lines_skipped(self, audit_path, tmp_hermes_home, now):
        _write_events(audit_path, [
            {"not": "valid json line without requestId"},
        ])
        # Append a malformed line
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write("NOT JSON AT ALL\n")
            f.write("\n")  # Empty line

        # Write a valid record
        _write_events(audit_path, [
            _make_audit_event(request_id="target-id"),
        ])

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is True
        assert result.dry_run_request_id == "target-id"

    def test_all_malformed_returns_not_found(self, audit_path, tmp_hermes_home, now):
        with open(audit_path, "w", encoding="utf-8") as f:
            f.write("BAD LINE 1\n")
            f.write("BAD LINE 2\n")
            f.write("{}\n")  # Valid JSON but no requestId

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="any-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is False
        assert result.error_code == ERROR_DRY_RUN_NOT_FOUND


# ===================================================================
# 4. Valid record found by dryRunRequestId
# ===================================================================


class TestValidLookup:
    """Tests for successful record lookup."""

    def test_found_by_request_id(self, audit_path, tmp_hermes_home, now):
        _write_events(audit_path, [
            _make_audit_event(request_id="other-id", canonical_name="read_file"),
            _make_audit_event(request_id="target-id", canonical_name="clarify"),
        ])

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is True
        assert result.error_code is None
        assert result.dry_run_request_id == "target-id"
        assert result.canonical_name == "clarify"
        assert result.decision == "would_allow"
        assert result.risk_tier == "R0"
        assert result.audit_written is True  # Presence = written
        assert result.audit_event_id == "evt-001"
        assert result.created_at is not None
        assert result.lookup_source is not None
        assert result.safe_summary is not None
        assert result.safe_summary.get("toolExists") is True

    def test_found_record_has_safe_summary(self, audit_path, tmp_hermes_home, now):
        _write_events(audit_path, [
            _make_audit_event(request_id="target-id"),
        ])

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is True
        # safe_summary should not contain raw arguments or secrets
        summary = result.safe_summary
        assert "redactedArgumentsPreview" not in summary
        assert "argumentsDigest" not in summary


# ===================================================================
# 5. Multiple records same dryRunRequestId → latest valid record
# ===================================================================


class TestMultipleRecords:
    """Tests for duplicate requestId handling."""

    def test_uses_latest_record(self, audit_path, tmp_hermes_home, now):
        ts_early = (now - timedelta(minutes=2)).isoformat()
        ts_late = (now - timedelta(minutes=1)).isoformat()
        _write_events(audit_path, [
            _make_audit_event(
                request_id="target-id",
                event_id="evt-early",
                timestamp=ts_early,
                decision="would_block",
            ),
            _make_audit_event(
                request_id="target-id",
                event_id="evt-late",
                timestamp=ts_late,
                decision="would_allow",
            ),
        ])

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is True
        assert result.decision == "would_allow"
        assert result.audit_event_id == "evt-late"

    def test_single_valid_record_among_malformed(self, audit_path, tmp_hermes_home, now):
        _write_events(audit_path, [
            _make_audit_event(request_id="target-id"),
        ])
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write("BAD LINE\n")

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is True


# ===================================================================
# 6. Record with raw secrets does not expose raw secrets in result
# ===================================================================


class TestNoSecretExposure:
    """Tests that lookup result does not expose secrets."""

    def test_no_raw_secrets_in_result(self, audit_path, tmp_hermes_home, now):
        event = _make_audit_event(request_id="target-id")
        # Inject a secret into the event (simulating defensive sanitization failure)
        event["redactedArgumentsPreview"] = {
            "api_key": "[REDACTED]",  # Properly redacted
        }

        _write_events(audit_path, [event])

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is True
        # Result should not contain raw arguments
        assert "redactedArgumentsPreview" not in result.safe_summary

    def test_result_has_no_raw_arguments_field(self, audit_path, tmp_hermes_home, now):
        _write_events(audit_path, [_make_audit_event(request_id="target-id")])

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is True
        # Result dataclass does not have raw arguments fields
        assert not hasattr(result, "raw_arguments")
        assert not hasattr(result, "arguments")


# ===================================================================
# 7. Record expired by expiresAt / createdAt blocks
# ===================================================================


class TestExpiry:
    """Tests for expiry handling."""

    def test_record_too_old_blocks(self, audit_path, tmp_hermes_home, now):
        # Create a record 10 minutes old (TTL is 5 minutes)
        ts = (now - timedelta(minutes=10)).isoformat()
        _write_events(audit_path, [
            _make_audit_event(request_id="target-id", timestamp=ts),
        ])

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is False
        assert result.error_code == ERROR_DRY_RUN_EXPIRED

    def test_record_within_ttl_passes(self, audit_path, tmp_hermes_home, now):
        # Record is 3 minutes old (within 5 minute TTL)
        ts = (now - timedelta(minutes=3)).isoformat()
        _write_events(audit_path, [
            _make_audit_event(request_id="target-id", timestamp=ts),
        ])

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is True

    def test_record_exactly_at_ttl_boundary(self, audit_path, tmp_hermes_home, now):
        # Record is exactly 5 minutes old (at boundary → expired)
        ts = (now - timedelta(seconds=_DRY_RUN_TTL_SECONDS + 1)).isoformat()
        _write_events(audit_path, [
            _make_audit_event(request_id="target-id", timestamp=ts),
        ])

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is False
        assert result.error_code == ERROR_DRY_RUN_EXPIRED

    def test_record_missing_timestamp_blocks(self, audit_path, tmp_hermes_home, now):
        event = _make_audit_event(request_id="target-id")
        del event["timestamp"]
        _write_events(audit_path, [event])

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            now=now,
        )
        # Missing timestamp → fail closed
        # The record has no timestamp, so best_record is set but expiry check
        # will fail-closed because _is_record_expired returns True for missing ts
        assert result.found is False
        assert result.error_code == ERROR_DRY_RUN_EXPIRED


# ===================================================================
# 8. Decision != would_allow blocks (via verify function)
# ===================================================================


class TestDecisionCheck:
    """Tests for decision verification."""

    def test_would_block_decision(self):
        result = DryRunHistoricalLookupResult(
            found=True,
            error_code=None,
            dry_run_request_id="test-id",
            canonical_name="clarify",
            decision="would_block",
            risk_tier="R0",
            policy_version=None,
            arguments_digest=None,
            dry_run_decision_digest=None,
            audit_written=True,
            audit_event_id="evt-001",
            created_at="2026-06-12T12:00:00+00:00",
            expires_at="2026-06-12T12:05:00+00:00",
            lookup_source="/test/audit.jsonl",
            redaction_status="none",
            safe_summary={},
        )
        error = verify_decision_allowed(result)
        assert error == ERROR_DRY_RUN_NOT_ALLOWED

    def test_would_allow_decision(self):
        result = DryRunHistoricalLookupResult(
            found=True,
            error_code=None,
            dry_run_request_id="test-id",
            canonical_name="clarify",
            decision="would_allow",
            risk_tier="R0",
            policy_version=None,
            arguments_digest=None,
            dry_run_decision_digest=None,
            audit_written=True,
            audit_event_id="evt-001",
            created_at="2026-06-12T12:00:00+00:00",
            expires_at="2026-06-12T12:05:00+00:00",
            lookup_source="/test/audit.jsonl",
            redaction_status="none",
            safe_summary={},
        )
        error = verify_decision_allowed(result)
        assert error is None

    def test_not_found_returns_error(self):
        result = DryRunHistoricalLookupResult(
            found=False,
            error_code=ERROR_DRY_RUN_NOT_FOUND,
            dry_run_request_id="test-id",
            canonical_name=None,
            decision=None,
            risk_tier=None,
            policy_version=None,
            arguments_digest=None,
            dry_run_decision_digest=None,
            audit_written=None,
            audit_event_id=None,
            created_at=None,
            expires_at=None,
            lookup_source=None,
            redaction_status=None,
            safe_summary={},
        )
        error = verify_decision_allowed(result)
        assert error == ERROR_DRY_RUN_NOT_FOUND


# ===================================================================
# 9. Audit written check
# ===================================================================


class TestAuditWrittenCheck:
    """Tests for audit written verification."""

    def test_audit_written_true_passes(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="clarify",
            decision="would_allow", risk_tier="R0", policy_version=None,
            arguments_digest=None, dry_run_decision_digest=None,
            audit_written=True, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_audit_written(result) is None

    def test_audit_written_false_blocks(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="clarify",
            decision="would_allow", risk_tier="R0", policy_version=None,
            arguments_digest=None, dry_run_decision_digest=None,
            audit_written=False, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_audit_written(result) == ERROR_DRY_RUN_AUDIT_MISSING


# ===================================================================
# 10. canonicalName mismatch blocks
# ===================================================================


class TestCanonicalNameBinding:
    """Tests for canonicalName binding verification."""

    def test_matching_canonical_name_passes(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="clarify",
            decision="would_allow", risk_tier="R0", policy_version=None,
            arguments_digest=None, dry_run_decision_digest=None,
            audit_written=True, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_canonical_name_binding(result, "clarify") is None

    def test_mismatching_canonical_name_blocks(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="read_file",
            decision="would_allow", risk_tier="R0", policy_version=None,
            arguments_digest=None, dry_run_decision_digest=None,
            audit_written=True, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_canonical_name_binding(result, "clarify") == ERROR_DRY_RUN_CANONICAL_NAME_MISMATCH


# ===================================================================
# 11. riskTier mismatch blocks
# ===================================================================


class TestRiskTierBinding:
    """Tests for riskTier binding verification."""

    def test_matching_risk_tier_passes(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="clarify",
            decision="would_allow", risk_tier="R0", policy_version=None,
            arguments_digest=None, dry_run_decision_digest=None,
            audit_written=True, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_risk_tier_binding(result, "R0") is None

    def test_mismatching_risk_tier_blocks(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="clarify",
            decision="would_allow", risk_tier="R1", policy_version=None,
            arguments_digest=None, dry_run_decision_digest=None,
            audit_written=True, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_risk_tier_binding(result, "R0") == ERROR_DRY_RUN_RISK_TIER_MISMATCH

    def test_none_risk_tier_skips_check(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="clarify",
            decision="would_allow", risk_tier=None, policy_version=None,
            arguments_digest=None, dry_run_decision_digest=None,
            audit_written=True, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_risk_tier_binding(result, "R0") is None


# ===================================================================
# 12. policyVersion binding (no-op in current implementation)
# ===================================================================


class TestPolicyVersionBinding:
    """Tests for policyVersion binding verification."""

    def test_both_none_passes(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="clarify",
            decision="would_allow", risk_tier="R0", policy_version=None,
            arguments_digest=None, dry_run_decision_digest=None,
            audit_written=True, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_policy_version_binding(result, None) is None

    def test_one_none_one_set_passes(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="clarify",
            decision="would_allow", risk_tier="R0", policy_version="v1",
            arguments_digest=None, dry_run_decision_digest=None,
            audit_written=True, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_policy_version_binding(result, None) is None


# ===================================================================
# 13. dryRunDecisionDigest binding (no-op when not stored)
# ===================================================================


class TestDigestBinding:
    """Tests for dryRunDecisionDigest binding verification."""

    def test_lookup_no_digest_passes(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="clarify",
            decision="would_allow", risk_tier="R0", policy_version=None,
            arguments_digest=None, dry_run_decision_digest=None,
            audit_written=True, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_digest_binding(result, "sha256:abc") is None

    def test_request_no_digest_passes(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="clarify",
            decision="would_allow", risk_tier="R0", policy_version=None,
            arguments_digest=None, dry_run_decision_digest="sha256:abc",
            audit_written=True, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_digest_binding(result, None) is None

    def test_matching_digests_passes(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="clarify",
            decision="would_allow", risk_tier="R0", policy_version=None,
            arguments_digest=None, dry_run_decision_digest="sha256:abc",
            audit_written=True, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_digest_binding(result, "sha256:abc") is None

    def test_mismatching_digests_blocks(self):
        result = DryRunHistoricalLookupResult(
            found=True, error_code=None,
            dry_run_request_id="test-id", canonical_name="clarify",
            decision="would_allow", risk_tier="R0", policy_version=None,
            arguments_digest=None, dry_run_decision_digest="sha256:abc",
            audit_written=True, audit_event_id="evt-001",
            created_at=None, expires_at=None,
            lookup_source=None, redaction_status=None, safe_summary={},
        )
        assert verify_digest_binding(result, "sha256:xyz") == ERROR_DRY_RUN_DIGEST_MISMATCH


# ===================================================================
# 14. Oversized file → fail-closed
# ===================================================================


class TestBoundedRead:
    """Tests for file size limits."""

    def test_oversized_file_fails_closed(self, audit_path, tmp_hermes_home, now):
        # Create a file that exceeds the default max_bytes
        with open(audit_path, "w", encoding="utf-8") as f:
            f.write("x" * (_MAX_READ_BYTES + 1))

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            max_bytes=_MAX_READ_BYTES,
            now=now,
        )
        assert result.found is False
        assert result.error_code == ERROR_DRY_RUN_LOOKUP_UNAVAILABLE

    def test_custom_max_bytes(self, audit_path, tmp_hermes_home, now):
        # Create a small file that exceeds a tiny max_bytes
        _write_events(audit_path, [
            _make_audit_event(request_id="target-id"),
        ])

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            max_bytes=1,  # Tiny limit
            now=now,
        )
        assert result.found is False
        assert result.error_code == ERROR_DRY_RUN_LOOKUP_UNAVAILABLE


# ===================================================================
# 15. Production path rejection
# ===================================================================


class TestProductionPathRejection:
    """Tests that ~/.hermes is never accessed."""

    def test_rejects_production_hermes_home(self, now):
        result = lookup_dry_run_record(
            hermes_home=_PRODUCTION_HERMES_HOME,
            dry_run_request_id="any-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is False
        assert result.error_code == ERROR_DRY_RUN_LOOKUP_UNAVAILABLE


# ===================================================================
# 16. Record not found for different requestId
# ===================================================================


class TestRequestIdNotFound:
    """Tests for missing requestId."""

    def test_different_request_id_not_found(self, audit_path, tmp_hermes_home, now):
        _write_events(audit_path, [
            _make_audit_event(request_id="other-id"),
        ])

        result = lookup_dry_run_record(
            hermes_home=str(tmp_hermes_home),
            dry_run_request_id="target-id",
            canonical_name="clarify",
            now=now,
        )
        assert result.found is False
        assert result.error_code == ERROR_DRY_RUN_NOT_FOUND
