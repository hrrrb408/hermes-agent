"""Tests for hermes_cli.dev_web_tool_execute_confirmation — Confirmation Token.

Phase 1G-04-20: Confirmation Token Minimal Backend Implementation.

All tests verify:
  - Token issuance only when dry-run decision == would_allow
  - No token when dry-run decision != would_allow
  - No token when auditWritten false
  - No token when dryRunRequestId missing
  - No token for non-clarify
  - Raw token returned once, not stored
  - TokenHash stored, raw token not stored
  - Token store path under $HERMES_HOME/gateway/dev/tokens
  - Production path blocks before file write
  - Symlink/path traversal blocks
  - .hermes-dev not falsely blocked
  - TTL <= 5 minutes
  - expiresAt <= dry-run expiresAt when available
  - Token verification blocks on missing/invalid/expired/consumed/binding mismatch
  - Valid token verifies and consumes
  - Reused token blocks
  - No handler / no dispatch / no provider / no execution invariants
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hermes_cli.dev_web_tool_execute_confirmation import (
    ERROR_CONFIRMATION_MISSING,
    ERROR_CONFIRMATION_INVALID,
    ERROR_CONFIRMATION_STORE_UNAVAILABLE,
    ERROR_CONFIRMATION_NOT_FOUND,
    ERROR_CONFIRMATION_EXPIRED,
    ERROR_CONFIRMATION_REUSED,
    ERROR_CONFIRMATION_DRY_RUN_MISMATCH,
    ERROR_CONFIRMATION_DIGEST_MISMATCH,
    ERROR_CONFIRMATION_CANONICAL_NAME_MISMATCH,
    ERROR_CONFIRMATION_RISK_TIER_MISMATCH,
    ERROR_CONFIRMATION_POLICY_VERSION_MISMATCH,
    ERROR_CONFIRMATION_AUDIT_EVENT_MISMATCH,
    ERROR_CONFIRMATION_ARGUMENTS_MISMATCH,
    ERROR_CONFIRMATION_CONSUME_FAILED,
    ERROR_CONFIRMATION_ISSUANCE_REJECTED,
    ERROR_CONFIRMATION_PRODUCTION_PATH,
    ERROR_CONFIRMATION_NOT_ALLOWED,
    ERROR_CONFIRMATION_AUDIT_NOT_WRITTEN,
    ConfirmationTokenIssueResult,
    ConfirmationTokenVerificationResult,
    issue_confirmation_token,
    verify_confirmation_token,
    _hash_token,
    _build_token_id,
    _generate_raw_token,
    _resolve_token_store_path,
    _PRODUCTION_HERMES_HOME,
    _TOKEN_DIR_RELATIVE,
    _TOKEN_FILENAME,
    _TOKEN_TTL_SECONDS,
    _DEV_HMAC_NAMESPACE,
)
from hermes_cli.dev_web_tool_execute_preflight import DryRunHistoricalLookupResult


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def tmp_hermes_home(tmp_path):
    """Provide a temporary HERMES_HOME for testing."""
    return tmp_path / "hermes-home-dev"


@pytest.fixture
def token_dir(tmp_hermes_home):
    """Create the token directory."""
    d = tmp_hermes_home / _TOKEN_DIR_RELATIVE
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def token_path(token_dir):
    """Return the token file path."""
    return token_dir / _TOKEN_FILENAME


@pytest.fixture
def now():
    """Return a fixed current time for testing."""
    return datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)


def _make_dry_run_record(
    decision="would_allow",
    audit_written=True,
    dry_run_request_id="dr-req-001",
    canonical_name="clarify",
    risk_tier="R0",
    expires_at=None,
    audit_event_id="evt-001",
):
    """Helper to create a DryRunHistoricalLookupResult for testing."""
    from datetime import timedelta
    ts = datetime(2026, 6, 13, 11, 59, 0, tzinfo=timezone.utc)
    return DryRunHistoricalLookupResult(
        found=True,
        error_code=None,
        dry_run_request_id=dry_run_request_id,
        canonical_name=canonical_name,
        decision=decision,
        risk_tier=risk_tier,
        policy_version=None,
        arguments_digest=None,
        dry_run_decision_digest=None,
        audit_written=audit_written,
        audit_event_id=audit_event_id,
        created_at=ts.isoformat(),
        expires_at=expires_at,
        lookup_source="test",
        redaction_status="none",
    )


# ===================================================================
# 1. Token Issuance Tests
# ===================================================================


class TestTokenIssuance:
    """Tests for issue_confirmation_token()."""

    def test_issue_token_when_dry_run_would_allow(self, tmp_hermes_home, now):
        """Issue token only when dry-run decision == would_allow."""
        record = _make_dry_run_record(decision="would_allow")
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is True
        assert result.raw_token is not None
        assert result.token_id is not None
        assert result.expires_at is not None
        assert result.error_code is None

    def test_no_token_when_dry_run_decision_not_allow(self, tmp_hermes_home, now):
        """No token when dry-run decision != would_allow."""
        record = _make_dry_run_record(decision="would_block")
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is False
        assert result.raw_token is None
        assert result.error_code == ERROR_CONFIRMATION_NOT_ALLOWED

    def test_no_token_when_audit_not_written(self, tmp_hermes_home, now):
        """No token when auditWritten false."""
        record = _make_dry_run_record(audit_written=False)
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is False
        assert result.error_code == ERROR_CONFIRMATION_AUDIT_NOT_WRITTEN

    def test_no_token_when_dry_run_request_id_missing(self, tmp_hermes_home, now):
        """No token when dryRunRequestId missing."""
        record = _make_dry_run_record()
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id=None,
            now=now,
        )
        assert result.issued is False
        assert result.error_code == ERROR_CONFIRMATION_ISSUANCE_REJECTED

    def test_no_token_for_non_allowlisted(self, tmp_hermes_home, now):
        """No token for non-clarify (not on STATIC_ALLOWLIST)."""
        record = _make_dry_run_record(canonical_name="search_files")
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="search_files",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is False
        assert result.error_code == ERROR_CONFIRMATION_NOT_ALLOWED

    def test_no_token_when_no_dry_run_record(self, tmp_hermes_home, now):
        """No token when dry_run_record is None."""
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=None,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is False
        assert result.error_code == ERROR_CONFIRMATION_ISSUANCE_REJECTED

    def test_raw_token_returned_once(self, tmp_hermes_home, now):
        """Raw token returned once in issuance result."""
        record = _make_dry_run_record()
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is True
        assert isinstance(result.raw_token, str)
        assert len(result.raw_token) >= 20  # base64url of 32 bytes

    def test_token_hash_stored_not_raw_token(self, tmp_hermes_home, now):
        """tokenHash stored, raw token not stored in JSONL."""
        record = _make_dry_run_record()
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is True

        # Read token store
        token_file = tmp_hermes_home / _TOKEN_DIR_RELATIVE / _TOKEN_FILENAME
        assert token_file.exists()
        with open(token_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert result.raw_token not in content
        assert "rawToken" not in content
        # tokenHash should be present
        stored = json.loads(content.strip())
        assert "tokenHash" in stored
        assert stored["tokenHash"] == _hash_token(result.raw_token)

    def test_token_id_stored(self, tmp_hermes_home, now):
        """tokenId stored in token store record."""
        record = _make_dry_run_record()
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is True
        token_file = tmp_hermes_home / _TOKEN_DIR_RELATIVE / _TOKEN_FILENAME
        with open(token_file, "r", encoding="utf-8") as f:
            stored = json.loads(f.readline().strip())
        assert stored["tokenId"] == result.token_id
        assert stored["tokenId"].startswith("ctok_")

    def test_token_store_path_under_hermes_home(self, tmp_hermes_home, now):
        """Token store path is under $HERMES_HOME/gateway/dev/tokens."""
        record = _make_dry_run_record()
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is True
        token_file = tmp_hermes_home / _TOKEN_DIR_RELATIVE / _TOKEN_FILENAME
        assert token_file.exists()
        # Verify it's under the expected path
        resolved = token_file.resolve()
        expected_dir = (tmp_hermes_home / _TOKEN_DIR_RELATIVE).resolve()
        assert resolved.is_relative_to(expected_dir)

    def test_exact_production_home_blocks(self, now):
        """Exact production home blocks before file write."""
        result = issue_confirmation_token(
            hermes_home=_PRODUCTION_HERMES_HOME,
            dry_run_record=_make_dry_run_record(),
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is False
        assert result.error_code == ERROR_CONFIRMATION_PRODUCTION_PATH

    def test_production_subtree_blocks(self, now):
        """Production subtree blocks before file write."""
        result = issue_confirmation_token(
            hermes_home=f"{_PRODUCTION_HERMES_HOME}/gateway/dev",
            dry_run_record=_make_dry_run_record(),
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is False
        assert result.error_code == ERROR_CONFIRMATION_PRODUCTION_PATH

    def test_hermes_dev_not_falsely_blocked(self, tmp_path, now):
        """.hermes-dev style path is not falsely blocked."""
        # This should NOT be blocked — it's not inside ~/.hermes
        home = tmp_path / ".hermes-dev"
        home.mkdir(parents=True, exist_ok=True)
        record = _make_dry_run_record()
        result = issue_confirmation_token(
            hermes_home=home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is True

    def test_ttl_at_most_5_minutes(self, tmp_hermes_home, now):
        """TTL <= 5 minutes."""
        record = _make_dry_run_record()
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is True
        from datetime import datetime as _dt
        expires_at = _dt.fromisoformat(result.expires_at)
        max_ttl = now + timedelta(seconds=_TOKEN_TTL_SECONDS)
        assert expires_at <= max_ttl

    def test_expires_at_not_exceed_dry_run_expiry(self, tmp_hermes_home, now):
        """expiresAt <= dry-run expiresAt when available."""
        # dry-run expires in 2 minutes
        dr_expires = (now + timedelta(minutes=2)).isoformat()
        record = _make_dry_run_record(expires_at=dr_expires)
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is True
        from datetime import datetime as _dt
        token_expires = _dt.fromisoformat(result.expires_at)
        dr_expires_dt = _dt.fromisoformat(dr_expires)
        assert token_expires <= dr_expires_dt


# ===================================================================
# 2. Token Verification Tests
# ===================================================================


class TestTokenVerification:
    """Tests for verify_confirmation_token()."""

    def _issue_and_get_raw_token(self, tmp_hermes_home, now, **kwargs):
        """Helper to issue a token and return the raw token + result."""
        record = _make_dry_run_record(**kwargs)
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name=kwargs.get("canonical_name", "clarify"),
            risk_tier=kwargs.get("risk_tier", "R0"),
            dry_run_request_id=kwargs.get("dry_run_request_id", "dr-req-001"),
            now=now,
        )
        assert result.issued is True
        return result.raw_token, result

    def test_missing_token_blocks(self, tmp_hermes_home, now):
        """Missing token blocks."""
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=None,
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            now=now,
        )
        assert result.verified is False
        assert result.error_code == ERROR_CONFIRMATION_MISSING

    def test_malformed_token_blocks(self, tmp_hermes_home, now):
        """Malformed token (empty string) blocks as missing."""
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token="",
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            now=now,
        )
        assert result.verified is False
        # Empty string is treated as missing
        assert result.error_code == ERROR_CONFIRMATION_MISSING

    def test_too_short_token_blocks(self, tmp_hermes_home, now):
        """Token too short blocks."""
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token="abc",
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            now=now,
        )
        assert result.verified is False
        assert result.error_code == ERROR_CONFIRMATION_INVALID

    def test_token_store_unavailable_blocks(self, now):
        """Token store unavailable blocks."""
        result = verify_confirmation_token(
            hermes_home=_PRODUCTION_HERMES_HOME,
            raw_token="some-valid-looking-token-value",
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            now=now,
        )
        assert result.verified is False
        assert result.error_code == ERROR_CONFIRMATION_PRODUCTION_PATH

    def test_token_not_found_blocks(self, tmp_hermes_home, now):
        """Token not found blocks."""
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token="nonexistent_token_value_that_is_long_enough",
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            now=now,
        )
        assert result.verified is False
        assert result.error_code == ERROR_CONFIRMATION_NOT_FOUND

    def test_expired_token_blocks(self, tmp_hermes_home, now):
        """Expired token blocks."""
        raw_token, _ = self._issue_and_get_raw_token(tmp_hermes_home, now)
        # Verify with time past expiry
        future_time = now + timedelta(minutes=6)
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=raw_token,
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            now=future_time,
        )
        assert result.verified is False
        assert result.error_code == ERROR_CONFIRMATION_EXPIRED

    def test_consumed_token_blocks(self, tmp_hermes_home, now):
        """Consumed token blocks (reuse)."""
        raw_token, _ = self._issue_and_get_raw_token(tmp_hermes_home, now)
        # First verification consumes
        v1 = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=raw_token,
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            now=now,
            consume=True,
        )
        assert v1.verified is True
        assert v1.consumed is True
        # Second verification with same token blocks
        v2 = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=raw_token,
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            now=now,
            consume=True,
        )
        assert v2.verified is False
        assert v2.error_code == ERROR_CONFIRMATION_REUSED

    def test_dry_run_request_id_mismatch_blocks(self, tmp_hermes_home, now):
        """dryRunRequestId mismatch blocks."""
        raw_token, _ = self._issue_and_get_raw_token(
            tmp_hermes_home, now, dry_run_request_id="dr-req-001"
        )
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=raw_token,
            dry_run_request_id="dr-req-999",  # different
            canonical_name="clarify",
            now=now,
        )
        assert result.verified is False
        assert result.error_code == ERROR_CONFIRMATION_DRY_RUN_MISMATCH

    def test_canonical_name_mismatch_blocks(self, tmp_hermes_home, now):
        """canonicalName mismatch blocks."""
        raw_token, _ = self._issue_and_get_raw_token(tmp_hermes_home, now)
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=raw_token,
            dry_run_request_id="dr-req-001",
            canonical_name="search_files",  # different
            now=now,
        )
        assert result.verified is False
        assert result.error_code == ERROR_CONFIRMATION_CANONICAL_NAME_MISMATCH

    def test_risk_tier_mismatch_blocks(self, tmp_hermes_home, now):
        """riskTier mismatch blocks when both sides have values."""
        raw_token, _ = self._issue_and_get_raw_token(
            tmp_hermes_home, now, risk_tier="R0"
        )
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=raw_token,
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            risk_tier="R1",  # different
            now=now,
        )
        assert result.verified is False
        assert result.error_code == ERROR_CONFIRMATION_RISK_TIER_MISMATCH

    def test_valid_token_verifies(self, tmp_hermes_home, now):
        """Valid token verifies successfully."""
        raw_token, _ = self._issue_and_get_raw_token(tmp_hermes_home, now)
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=raw_token,
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            risk_tier="R0",
            now=now,
            consume=False,  # Don't consume, just verify
        )
        assert result.verified is True
        assert result.error_code is None
        assert result.token_id is not None

    def test_valid_token_consumes(self, tmp_hermes_home, now):
        """Valid token consumes when consume=True."""
        raw_token, _ = self._issue_and_get_raw_token(tmp_hermes_home, now)
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=raw_token,
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            risk_tier="R0",
            now=now,
            consume=True,
        )
        assert result.verified is True
        assert result.consumed is True

    def test_reused_token_blocks(self, tmp_hermes_home, now):
        """Reused token blocks."""
        raw_token, _ = self._issue_and_get_raw_token(tmp_hermes_home, now)
        # Consume
        v1 = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=raw_token,
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            now=now,
            consume=True,
        )
        assert v1.verified is True
        # Reuse
        v2 = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=raw_token,
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            now=now,
            consume=True,
        )
        assert v2.verified is False
        assert v2.error_code == ERROR_CONFIRMATION_REUSED

    def test_policy_version_mismatch_blocks(self, tmp_hermes_home, now):
        """policyVersion mismatch blocks when both sides have values."""
        record = _make_dry_run_record()
        issue_result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            policy_version="v1",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert issue_result.issued is True
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=issue_result.raw_token,
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            risk_tier="R0",
            policy_version="v2",  # different
            now=now,
        )
        assert result.verified is False
        assert result.error_code == ERROR_CONFIRMATION_POLICY_VERSION_MISMATCH

    def test_audit_event_mismatch_blocks(self, tmp_hermes_home, now):
        """auditEventId mismatch blocks when both sides have values."""
        record = _make_dry_run_record(audit_event_id="evt-001")
        issue_result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            audit_event_id="evt-001",
            now=now,
        )
        assert issue_result.issued is True
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=issue_result.raw_token,
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            risk_tier="R0",
            audit_event_id="evt-999",  # different
            now=now,
        )
        assert result.verified is False
        assert result.error_code == ERROR_CONFIRMATION_AUDIT_EVENT_MISMATCH

    def test_arguments_digest_mismatch_blocks(self, tmp_hermes_home, now):
        """argumentsDigest mismatch blocks when both sides have values."""
        record = _make_dry_run_record()
        issue_result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            arguments_digest="sha256:abc123",
            now=now,
        )
        assert issue_result.issued is True
        result = verify_confirmation_token(
            hermes_home=tmp_hermes_home,
            raw_token=issue_result.raw_token,
            dry_run_request_id="dr-req-001",
            canonical_name="clarify",
            risk_tier="R0",
            arguments_digest="sha256:xyz789",  # different
            now=now,
        )
        assert result.verified is False
        assert result.error_code == ERROR_CONFIRMATION_ARGUMENTS_MISMATCH


# ===================================================================
# 3. Safety Invariant Tests
# ===================================================================


class TestSafetyInvariants:
    """Safety invariants that must hold across all operations."""

    def test_raw_token_not_stored(self, tmp_hermes_home, now):
        """Raw token is never stored in token store."""
        record = _make_dry_run_record()
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is True
        token_file = tmp_hermes_home / _TOKEN_DIR_RELATIVE / _TOKEN_FILENAME
        with open(token_file, "r", encoding="utf-8") as f:
            for line in f:
                assert result.raw_token not in line
                record = json.loads(line)
                assert "rawToken" not in record

    def test_raw_token_not_logged_in_safe_summary(self, tmp_hermes_home, now):
        """Raw token does not appear in safe_summary."""
        record = _make_dry_run_record()
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is True
        summary_str = json.dumps(result.safe_summary)
        assert result.raw_token not in summary_str

    def test_token_hash_full_not_exposed_in_safe_summary(self, tmp_hermes_home, now):
        """tokenHash full value not exposed in user-facing safe summary."""
        record = _make_dry_run_record()
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is True
        # safe_summary should have tokenHashPrefix, not full hash
        full_hash = _hash_token(result.raw_token)
        summary_str = json.dumps(result.safe_summary)
        assert full_hash not in summary_str
        assert "tokenHashPrefix" in result.safe_summary

    def test_no_provider_call(self, tmp_hermes_home, now):
        """No provider API is called during token operations."""
        # Token issuance/verification are pure local operations
        record = _make_dry_run_record()
        result = issue_confirmation_token(
            hermes_home=tmp_hermes_home,
            dry_run_record=record,
            canonical_name="clarify",
            risk_tier="R0",
            dry_run_request_id="dr-req-001",
            now=now,
        )
        assert result.issued is True
        # No network calls made (can't verify directly, but module has no network imports)
        # Verify module uses only stdlib
        import hermes_cli.dev_web_tool_execute_confirmation as mod
        source = open(mod.__file__, "r").read()
        assert "requests" not in source
        assert "httpx" not in source
        assert "urllib" not in source

    def test_no_handler_call(self, tmp_hermes_home, now):
        """No tool handler is called during token operations."""
        import hermes_cli.dev_web_tool_execute_confirmation as mod
        source = open(mod.__file__, "r").read()
        # Check imports only — the docstring mentions handler/dispatch as prohibitions
        import_lines = [l for l in source.split("\n") if l.startswith("import ") or l.startswith("from ")]
        for line in import_lines:
            assert "tool_handler" not in line
            assert "dispatch" not in line

    def test_no_dispatch(self, tmp_hermes_home, now):
        """No dispatch during token operations."""
        import hermes_cli.dev_web_tool_execute_confirmation as mod
        source = open(mod.__file__, "r").read()
        import_lines = [l for l in source.split("\n") if l.startswith("import ") or l.startswith("from ")]
        for line in import_lines:
            assert "tool_dispatch" not in line
            assert "dispatch" not in line

    def test_no_execution(self, tmp_hermes_home, now):
        """No execution during token operations."""
        import hermes_cli.dev_web_tool_execute_confirmation as mod
        source = open(mod.__file__, "r").read()
        import_lines = [l for l in source.split("\n") if l.startswith("import ") or l.startswith("from ")]
        for line in import_lines:
            assert "execute_tool" not in line
            assert "subprocess" not in line


# ===================================================================
# 4. Path Guard Tests
# ===================================================================


class TestTokenStorePathGuard:
    """Path guard tests for token store."""

    def test_resolve_valid_path(self, tmp_hermes_home):
        """Valid path resolves correctly."""
        token_dir, token_file, error = _resolve_token_store_path(tmp_hermes_home)
        assert error is None
        assert token_file.name == _TOKEN_FILENAME
        assert _TOKEN_DIR_RELATIVE in str(token_dir)

    def test_production_home_rejected(self):
        """Production home is rejected."""
        _, _, error = _resolve_token_store_path(_PRODUCTION_HERMES_HOME)
        assert error == ERROR_CONFIRMATION_PRODUCTION_PATH

    def test_production_subtree_rejected(self):
        """Production subtree is rejected."""
        _, _, error = _resolve_token_store_path(
            f"{_PRODUCTION_HERMES_HOME}/gateway/dev"
        )
        assert error == ERROR_CONFIRMATION_PRODUCTION_PATH

    def test_hermes_dev_not_blocked(self, tmp_path):
        """A path like .hermes-dev is not falsely blocked."""
        home = tmp_path / ".hermes-dev"
        _, _, error = _resolve_token_store_path(home)
        assert error is None

    def test_none_hermes_home_with_no_env(self):
        """None hermes_home with no env var returns error."""
        old = os.environ.pop("HERMES_HOME", None)
        try:
            _, _, error = _resolve_token_store_path(None)
            assert error == ERROR_CONFIRMATION_STORE_UNAVAILABLE
        finally:
            if old is not None:
                os.environ["HERMES_HOME"] = old


# ===================================================================
# 5. Token Hash / ID Tests
# ===================================================================


class TestTokenHashAndId:
    """Tests for token hash and ID derivation."""

    def test_hash_is_deterministic(self):
        """Same input produces same hash."""
        raw = "test-token-value"
        h1 = _hash_token(raw)
        h2 = _hash_token(raw)
        assert h1 == h2

    def test_hash_is_64_hex(self):
        """HMAC-SHA256 produces 64-char hex string."""
        h = _hash_token("test-token")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_inputs_different_hashes(self):
        """Different inputs produce different hashes."""
        h1 = _hash_token("token-a")
        h2 = _hash_token("token-b")
        assert h1 != h2

    def test_token_id_starts_with_ctok(self):
        """tokenId starts with ctok_ prefix."""
        h = _hash_token("test-token")
        tid = _build_token_id(h)
        assert tid.startswith("ctok_")

    def test_token_id_is_29_chars(self):
        """tokenId is ctok_ (5) + 24 hash prefix chars."""
        h = _hash_token("test-token")
        tid = _build_token_id(h)
        assert len(tid) == 5 + 24  # "ctok_" + 24 hex chars

    def test_raw_token_is_base64url(self):
        """Raw token is base64url-compatible."""
        raw = _generate_raw_token()
        # base64url chars: A-Z, a-z, 0-9, -, _
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', raw)
        assert len(raw) >= 20  # 32 bytes base64 encoded is ~43 chars

    def test_raw_tokens_are_unique(self):
        """Each raw token is unique."""
        tokens = {_generate_raw_token() for _ in range(100)}
        assert len(tokens) == 100
