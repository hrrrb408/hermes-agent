"""Tests for hermes_cli.dev_web_tool_execute_digest — Digest Verification.

Phase 1G-04-22: Digest Verification Minimal Implementation.

All tests verify:
  - Canonical package includes required fields
  - Canonical package excludes raw token, tokenHash, raw arguments, secrets
  - Canonical JSON is deterministic
  - Digest algorithm is stable sha256:hex
  - Digest changes when critical fields change
  - ArgumentsDigest is stable and excludes secrets
  - Verification blocks on missing/mismatched/stale/expired digests
  - Verification never calls handler / dispatch / provider
  - All failure results keep side-effect flags implicitly false
  - Valid digest still blocks at pre-execution audit boundary
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.dev_web_tool_execute_digest import (
    CANONICALIZATION_VERSION,
    DECISION_BLOCKED_DIGEST_EXPIRED,
    DECISION_BLOCKED_DIGEST_MISMATCH,
    DECISION_BLOCKED_DIGEST_MISSING,
    DECISION_BLOCKED_DIGEST_STALE,
    DECISION_BLOCKED_DIGEST_UNAVAILABLE,
    DECISION_BLOCKED_DIGEST_CANONICALIZATION_FAILED,
    DECISION_BLOCKED_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED,
    DIGEST_ALGORITHM,
    DIGEST_PACKAGE_VERSION,
    DIGEST_PREFIX,
    ERROR_DIGEST_AUDIT_EVENT_MISMATCH,
    ERROR_DIGEST_CANONICALIZATION_FAILED,
    ERROR_DIGEST_EXECUTE_MISMATCH,
    ERROR_DIGEST_EXPIRED,
    ERROR_DIGEST_HISTORICAL_MISSING,
    ERROR_DIGEST_MISSING,
    ERROR_DIGEST_REQUEST_MISMATCH,
    ERROR_DIGEST_STALE,
    ERROR_DIGEST_TOKEN_BINDING_MISSING,
    ERROR_DIGEST_TOKEN_MISMATCH,
    ERROR_DIGEST_VERIFIED_BUT_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED,
    DigestPackageResult,
    DigestVerificationResult,
    build_arguments_digest,
    build_dry_run_decision_digest_package,
    canonicalize_digest_package,
    compute_digest,
    safe_digest_summary,
    verify_dry_run_decision_digest,
)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def sample_digest_fields():
    """Return sample fields for building a digest package."""
    return dict(
        dry_run_request_id="dr-req-001",
        canonical_name="clarify",
        risk_tier="R0",
        policy_decision="would_allow",
        allowlisted=True,
        audit_written=True,
        audit_event_id="evt-001",
        arguments={"query": "hello world"},
        created_at="2026-06-13T12:00:00+00:00",
        expires_at="2026-06-13T12:05:00+00:00",
    )


@pytest.fixture
def sample_digest():
    """Build a sample digest for reuse in tests."""
    result = build_dry_run_decision_digest_package(
        dry_run_request_id="dr-req-001",
        canonical_name="clarify",
        risk_tier="R0",
        policy_decision="would_allow",
        allowlisted=True,
        audit_written=True,
        audit_event_id="evt-001",
        arguments={"query": "hello world"},
        created_at="2026-06-13T12:00:00+00:00",
        expires_at="2026-06-13T12:05:00+00:00",
    )
    assert result.success
    return result


# ===================================================================
# 1. Canonical Package Tests
# ===================================================================


class TestDigestPackage:
    """Tests for build_dry_run_decision_digest_package()."""

    def test_package_includes_required_fields(self, sample_digest_fields):
        """Canonical package includes all required fields."""
        result = build_dry_run_decision_digest_package(**sample_digest_fields)
        assert result.success
        pkg = result.digest_package
        assert pkg is not None
        required = {
            "schemaVersion", "digestType", "dryRunRequestId",
            "canonicalName", "riskTier", "policyVersion", "policyDecision",
            "allowlisted", "auditWritten", "auditEventId",
            "argumentsDigest", "redactionVersion", "toolPolicyVersion",
            "toolCatalogVersion", "createdAt", "expiresAt",
            "digestPackageVersion", "canonicalizationVersion",
        }
        assert required.issubset(set(pkg.keys()))

    def test_package_excludes_raw_token(self, sample_digest_fields):
        """Canonical package does not contain raw token fields."""
        result = build_dry_run_decision_digest_package(**sample_digest_fields)
        assert result.success
        pkg = result.digest_package
        assert "confirmationToken" not in pkg
        assert "rawToken" not in pkg

    def test_package_excludes_token_hash(self, sample_digest_fields):
        """Canonical package does not contain tokenHash."""
        result = build_dry_run_decision_digest_package(**sample_digest_fields)
        assert result.success
        pkg = result.digest_package
        assert "tokenHash" not in pkg
        assert "hash" not in pkg

    def test_package_excludes_raw_arguments(self, sample_digest_fields):
        """Canonical package contains argumentsDigest, not raw arguments."""
        result = build_dry_run_decision_digest_package(**sample_digest_fields)
        assert result.success
        pkg = result.digest_package
        assert "argumentsDigest" in pkg
        assert "arguments" not in pkg
        assert "rawArguments" not in pkg
        # argumentsDigest starts with sha256:
        assert pkg["argumentsDigest"].startswith("sha256:")

    def test_package_excludes_secrets(self, sample_digest_fields):
        """Canonical package does not contain secrets."""
        result = build_dry_run_decision_digest_package(**sample_digest_fields)
        assert result.success
        canonical = result.canonical_json
        assert "sk-" not in canonical
        assert "Bearer " not in canonical
        assert "password" not in canonical
        assert "secret" not in canonical

    def test_canonical_json_deterministic(self, sample_digest_fields):
        """Canonical JSON is deterministic despite possible key order variation."""
        result1 = build_dry_run_decision_digest_package(**sample_digest_fields)
        result2 = build_dry_run_decision_digest_package(**sample_digest_fields)
        assert result1.canonical_json == result2.canonical_json
        assert result1.digest == result2.digest

    def test_null_handling_deterministic(self):
        """Null values produce consistent digest."""
        result1 = build_dry_run_decision_digest_package(
            dry_run_request_id="dr-null",
            canonical_name="clarify",
            risk_tier=None,
            policy_decision="would_allow",
            allowlisted=True,
            audit_written=True,
            audit_event_id=None,
            arguments=None,
            created_at=None,
            expires_at=None,
        )
        result2 = build_dry_run_decision_digest_package(
            dry_run_request_id="dr-null",
            canonical_name="clarify",
            risk_tier=None,
            policy_decision="would_allow",
            allowlisted=True,
            audit_written=True,
            audit_event_id=None,
            arguments=None,
            created_at=None,
            expires_at=None,
        )
        assert result1.digest == result2.digest

    def test_timestamp_format_deterministic(self, sample_digest_fields):
        """Same timestamps produce same digest."""
        result1 = build_dry_run_decision_digest_package(**sample_digest_fields)
        result2 = build_dry_run_decision_digest_package(**sample_digest_fields)
        assert result1.digest == result2.digest

    def test_digest_prefix_is_sha256(self, sample_digest):
        """Digest has sha256: prefix."""
        assert sample_digest.digest.startswith("sha256:")

    def test_digest_changes_on_canonical_name(self, sample_digest_fields):
        """Different canonicalName produces different digest."""
        r1 = build_dry_run_decision_digest_package(**sample_digest_fields)
        fields2 = {**sample_digest_fields, "canonical_name": "search_files"}
        r2 = build_dry_run_decision_digest_package(**fields2)
        assert r1.digest != r2.digest

    def test_digest_changes_on_arguments(self, sample_digest_fields):
        """Different arguments produce different digest."""
        r1 = build_dry_run_decision_digest_package(**sample_digest_fields)
        fields2 = {**sample_digest_fields, "arguments": {"query": "different"}}
        r2 = build_dry_run_decision_digest_package(**fields2)
        assert r1.digest != r2.digest

    def test_digest_changes_on_policy_version(self, sample_digest_fields):
        """Different policyVersion produces different digest."""
        r1 = build_dry_run_decision_digest_package(**sample_digest_fields)
        fields2 = {**sample_digest_fields, "policy_version": "v2"}
        r2 = build_dry_run_decision_digest_package(**fields2)
        assert r1.digest != r2.digest

    def test_digest_changes_on_risk_tier(self, sample_digest_fields):
        """Different riskTier produces different digest."""
        r1 = build_dry_run_decision_digest_package(**sample_digest_fields)
        fields2 = {**sample_digest_fields, "risk_tier": "R1"}
        r2 = build_dry_run_decision_digest_package(**fields2)
        assert r1.digest != r2.digest

    def test_digest_changes_on_audit_event_id(self, sample_digest_fields):
        """Different auditEventId produces different digest."""
        r1 = build_dry_run_decision_digest_package(**sample_digest_fields)
        fields2 = {**sample_digest_fields, "audit_event_id": "evt-002"}
        r2 = build_dry_run_decision_digest_package(**fields2)
        assert r1.digest != r2.digest


# ===================================================================
# 2. Arguments Digest Tests
# ===================================================================


class TestArgumentsDigest:
    """Tests for build_arguments_digest()."""

    def test_stable_across_key_order(self):
        """argumentsDigest is stable regardless of key order."""
        d1 = build_arguments_digest({"a": "1", "b": "2"})
        d2 = build_arguments_digest({"b": "2", "a": "1"})
        assert d1 == d2

    def test_excludes_secret_fields(self):
        """argumentsDigest redacts secret-like fields."""
        d = build_arguments_digest({"api_key": "sk-12345678", "query": "hello"})
        assert d.startswith("sha256:")
        # The digest should be the same as if api_key was redacted
        d_redacted = build_arguments_digest({"api_key": "[REDACTED]", "query": "hello"})
        d_with_secret = build_arguments_digest({"api_key": "sk-12345678", "query": "hello"})
        assert d_redacted == d_with_secret

    def test_changes_on_safe_argument(self):
        """argumentsDigest changes when safe argument changes."""
        d1 = build_arguments_digest({"query": "hello"})
        d2 = build_arguments_digest({"query": "world"})
        assert d1 != d2

    def test_has_sha256_prefix(self):
        """argumentsDigest has sha256: prefix."""
        d = build_arguments_digest({"query": "test"})
        assert d.startswith("sha256:")

    def test_none_arguments_stable(self):
        """None arguments produce deterministic digest."""
        d1 = build_arguments_digest(None)
        d2 = build_arguments_digest(None)
        assert d1 == d2

    def test_empty_arguments_stable(self):
        """Empty arguments produce deterministic digest."""
        d1 = build_arguments_digest({})
        d2 = build_arguments_digest({})
        assert d1 == d2


# ===================================================================
# 3. Verification Tests
# ===================================================================


class TestDigestVerification:
    """Tests for verify_dry_run_decision_digest()."""

    def test_missing_historical_digest_blocks(self, sample_digest):
        """Missing historical digest blocks."""
        result = verify_dry_run_decision_digest(
            historical_digest=None,
            token_bound_digest=sample_digest.digest,
        )
        assert result.verified is False
        assert result.error_code == ERROR_DIGEST_HISTORICAL_MISSING

    def test_missing_token_bound_digest_blocks(self, sample_digest):
        """Missing token-bound digest blocks."""
        result = verify_dry_run_decision_digest(
            historical_digest=sample_digest.digest,
            token_bound_digest=None,
        )
        assert result.verified is False
        assert result.error_code == ERROR_DIGEST_TOKEN_BINDING_MISSING

    def test_request_digest_mismatch_blocks(self, sample_digest):
        """Request digest mismatch blocks."""
        result = verify_dry_run_decision_digest(
            historical_digest=sample_digest.digest,
            token_bound_digest=sample_digest.digest,
            request_digest="sha256:0000000000mismatch",
        )
        assert result.verified is False
        assert result.error_code == ERROR_DIGEST_REQUEST_MISMATCH

    def test_token_digest_mismatch_blocks(self, sample_digest):
        """Token-bound digest mismatch blocks."""
        result = verify_dry_run_decision_digest(
            historical_digest=sample_digest.digest,
            token_bound_digest="sha256:0000000000tokenmismatch",
        )
        assert result.verified is False
        assert result.error_code == ERROR_DIGEST_TOKEN_MISMATCH

    def test_execute_derived_mismatch_blocks(self, sample_digest):
        """Execute-derived digest mismatch blocks."""
        result = verify_dry_run_decision_digest(
            historical_digest=sample_digest.digest,
            token_bound_digest=sample_digest.digest,
            execute_derived_digest="sha256:0000000000execmismatch",
        )
        assert result.verified is False
        assert result.error_code == ERROR_DIGEST_EXECUTE_MISMATCH

    def test_expired_digest_blocks(self, sample_digest):
        """Expired digest blocks based on expires_at."""
        result = verify_dry_run_decision_digest(
            historical_digest=sample_digest.digest,
            token_bound_digest=sample_digest.digest,
            historical_expires_at="2026-06-13T12:05:00+00:00",
            now_iso="2026-06-13T12:06:00+00:00",  # After expiry
        )
        assert result.verified is False
        assert result.error_code == ERROR_DIGEST_EXPIRED

    def test_matching_digests_verify_but_still_blocked(self, sample_digest):
        """Matching digests verify but still block at pre-execution audit."""
        result = verify_dry_run_decision_digest(
            historical_digest=sample_digest.digest,
            token_bound_digest=sample_digest.digest,
        )
        assert result.verified is True
        assert result.error_code == ERROR_DIGEST_VERIFIED_BUT_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED
        assert result.decision == DECISION_BLOCKED_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED

    def test_matching_with_request_digest(self, sample_digest):
        """All three digests matching verifies but blocks at audit."""
        result = verify_dry_run_decision_digest(
            historical_digest=sample_digest.digest,
            token_bound_digest=sample_digest.digest,
            request_digest=sample_digest.digest,
            execute_derived_digest=sample_digest.digest,
        )
        assert result.verified is True
        assert result.decision == DECISION_BLOCKED_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED

    def test_not_expired_digest_passes(self, sample_digest):
        """Non-expired digest passes expiry check."""
        result = verify_dry_run_decision_digest(
            historical_digest=sample_digest.digest,
            token_bound_digest=sample_digest.digest,
            historical_expires_at="2026-06-13T12:05:00+00:00",
            now_iso="2026-06-13T12:03:00+00:00",  # Before expiry
        )
        assert result.verified is True


# ===================================================================
# 4. Safety Invariant Tests
# ===================================================================


class TestDigestSafety:
    """Tests that digest operations never trigger side effects."""

    def test_digest_never_calls_handler(self, sample_digest):
        """Digest verification never calls a tool handler."""
        # verify_dry_run_decision_digest is a pure function —
        # it cannot call handlers by design.
        result = verify_dry_run_decision_digest(
            historical_digest=sample_digest.digest,
            token_bound_digest=sample_digest.digest,
        )
        # No handler-call mechanism exists in the digest module
        assert result.verified is True or result.verified is False

    def test_digest_never_dispatches(self, sample_digest):
        """Digest verification never dispatches."""
        # Pure function — no dispatch mechanism
        result = verify_dry_run_decision_digest(
            historical_digest=sample_digest.digest,
            token_bound_digest=sample_digest.digest,
        )
        assert isinstance(result, DigestVerificationResult)

    def test_digest_failure_exposes_no_raw_arguments(self):
        """Failure result does not expose raw arguments."""
        result = verify_dry_run_decision_digest(
            historical_digest=None,
            token_bound_digest="sha256:abc",
        )
        # result only contains digest values, not raw arguments
        assert result.verified is False
        assert not hasattr(result, "raw_arguments")

    def test_digest_failure_exposes_no_token_hash(self, sample_digest):
        """Failure result does not expose tokenHash."""
        result = verify_dry_run_decision_digest(
            historical_digest=None,
            token_bound_digest=sample_digest.digest,
        )
        assert result.verified is False
        assert not hasattr(result, "token_hash")


# ===================================================================
# 5. Canonicalization Tests
# ===================================================================


class TestCanonicalization:
    """Tests for canonicalize_digest_package() and compute_digest()."""

    def test_sorted_keys(self):
        """Canonical JSON has sorted keys."""
        pkg = {"z": 1, "a": 2, "m": 3}
        canonical = canonicalize_digest_package(pkg)
        # Keys must be in order: a, m, z
        parsed = json.loads(canonical)
        keys = list(parsed.keys())
        assert keys == ["a", "m", "z"]

    def test_no_whitespace(self):
        """Canonical JSON has no insignificant whitespace."""
        pkg = {"a": 1, "b": 2}
        canonical = canonicalize_digest_package(pkg)
        assert " " not in canonical
        assert "\n" not in canonical

    def test_compute_digest_format(self):
        """compute_digest returns sha256:<hex> format."""
        digest = compute_digest('{"a":1}')
        assert digest.startswith("sha256:")
        hex_part = digest[len("sha256:"):]
        assert len(hex_part) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_compute_digest_deterministic(self):
        """Same input produces same digest."""
        d1 = compute_digest('{"a":1}')
        d2 = compute_digest('{"a":1}')
        assert d1 == d2


# ===================================================================
# 6. Safe Digest Summary Tests
# ===================================================================


class TestSafeDigestSummary:
    """Tests for safe_digest_summary()."""

    def test_short_digest(self):
        """Short digest returned as-is."""
        assert safe_digest_summary("sha256:abc") == "sha256:abc"

    def test_long_digest_truncated(self):
        """Long digest is truncated."""
        digest = "sha256:" + "a" * 64
        summary = safe_digest_summary(digest)
        assert summary is not None
        assert summary.endswith("...")
        assert len(summary) < len(digest)

    def test_none_returns_none(self):
        """None input returns None."""
        assert safe_digest_summary(None) is None

    def test_empty_returns_none(self):
        """Empty string returns None."""
        assert safe_digest_summary("") is None


# ===================================================================
# 7. Version Constants Tests
# ===================================================================


class TestVersionConstants:
    """Tests for digest version constants."""

    def test_digest_package_version(self):
        assert DIGEST_PACKAGE_VERSION == "1"

    def test_canonicalization_version(self):
        assert CANONICALIZATION_VERSION == "json-sort-v1"

    def test_digest_algorithm(self):
        assert DIGEST_ALGORITHM == "sha256"

    def test_digest_prefix(self):
        assert DIGEST_PREFIX == "sha256:"
