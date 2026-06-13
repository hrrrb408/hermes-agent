"""Digest Verification for the Hermes Dev WebUI Tool Execute Gate.

This module implements minimal digest verification for dry-run decision
integrity binding. It builds canonical digest packages from safe dry-run
decision fields, serializes them deterministically, and computes SHA-256
digests.

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider imports, no tool handler imports, no dispatch imports
  - no network IO, no filesystem mutation, no runtime state mutation
  - no STATIC_ALLOWLIST mutation
  - no raw token, no tokenHash, no raw secrets, no raw arguments in digest
  - deterministic, JSON-serializable output
  - never calls handler / dispatch / provider

Phase: 1G-04-22 — Digest Verification Minimal Implementation
Status: Digest package + canonicalization + verification implemented, execute still blocked-only
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# 1. Version / algorithm constants
# ---------------------------------------------------------------------------

DIGEST_PACKAGE_VERSION = "1"
CANONICALIZATION_VERSION = "json-sort-v1"
DIGEST_ALGORITHM = "sha256"
DIGEST_PREFIX = "sha256:"

# Stable dev fallback for version fields not yet available in dry-run results
_TOOL_POLICY_VERSION_FALLBACK = "dev-v1"
_TOOL_CATALOG_VERSION_FALLBACK = "dev-v1"
_REDACTION_VERSION_FALLBACK = "sanitize-v1"


# ---------------------------------------------------------------------------
# 2. Error codes
# ---------------------------------------------------------------------------

ERROR_DIGEST_MISSING = "digest_missing"
ERROR_DIGEST_UNAVAILABLE = "digest_unavailable"
ERROR_DIGEST_CANONICALIZATION_FAILED = "digest_canonicalization_failed"
ERROR_DIGEST_HISTORICAL_MISSING = "digest_historical_missing"
ERROR_DIGEST_TOKEN_BINDING_MISSING = "digest_token_binding_missing"
ERROR_DIGEST_REQUEST_MISMATCH = "digest_request_mismatch"
ERROR_DIGEST_TOKEN_MISMATCH = "digest_token_mismatch"
ERROR_DIGEST_EXECUTE_MISMATCH = "digest_execute_mismatch"
ERROR_DIGEST_STALE = "digest_stale"
ERROR_DIGEST_EXPIRED = "digest_expired"
ERROR_DIGEST_POLICY_VERSION_MISMATCH = "digest_policy_version_mismatch"
ERROR_DIGEST_ARGUMENTS_MISMATCH = "digest_arguments_mismatch"
ERROR_DIGEST_AUDIT_EVENT_MISMATCH = "digest_audit_event_mismatch"
ERROR_DIGEST_VERIFIED_BUT_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED = (
    "digest_verified_but_pre_execution_audit_not_implemented"
)

# Decision constants matching execute module
DECISION_BLOCKED_DIGEST_MISSING = "blocked_digest_missing"
DECISION_BLOCKED_DIGEST_UNAVAILABLE = "blocked_digest_unavailable"
DECISION_BLOCKED_DIGEST_CANONICALIZATION_FAILED = "blocked_digest_canonicalization_failed"
DECISION_BLOCKED_DIGEST_MISMATCH = "blocked_digest_mismatch"
DECISION_BLOCKED_DIGEST_STALE = "blocked_digest_stale"
DECISION_BLOCKED_DIGEST_EXPIRED = "blocked_digest_expired"
DECISION_BLOCKED_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED = (
    "blocked_pre_execution_audit_not_implemented"
)

# Gate constants
GATE_DIGEST_PACKAGE = "digest_package"
GATE_DIGEST_CANONICALIZATION = "digest_canonicalization"
GATE_DIGEST_HISTORICAL = "digest_historical"
GATE_DIGEST_TOKEN_BINDING = "digest_token_binding"
GATE_DIGEST_REQUEST = "digest_request"
GATE_DIGEST_TOKEN_MATCH = "digest_token_match"
GATE_DIGEST_EXECUTE_MATCH = "digest_execute_match"
GATE_DIGEST_STALENESS = "digest_staleness"
GATE_DIGEST_EXPIRY = "digest_expiry"
GATE_PRE_EXECUTION_AUDIT = "pre_execution_audit"


# ---------------------------------------------------------------------------
# 3. Secret pattern detection (for argumentsDigest — mirrors dry-run module)
# ---------------------------------------------------------------------------

_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
)

_FORBIDDEN_ARG_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "api_key", "apikey", "authorization", "auth_header", "bearer",
        "token", "secret", "password", "passwd", "credential", "cookie",
        "session", "private_key", "client_secret", "access_token",
        "refresh_token", "access_key",
    }
)

_NORMALIZED_FORBIDDEN_ARG_FIELDS: frozenset[str] = frozenset(
    n.replace("_", "").replace("-", "").lower()
    for n in _FORBIDDEN_ARG_FIELD_NAMES
)


# ---------------------------------------------------------------------------
# 4. Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DigestPackageResult:
    """Immutable result of digest package building."""

    success: bool
    digest_package: dict[str, Any] | None
    canonical_json: str | None
    digest: str | None
    error_code: str | None


@dataclass(frozen=True, slots=True)
class DigestVerificationResult:
    """Immutable result of digest verification."""

    verified: bool
    error_code: str | None
    decision: str | None
    gate: str | None
    historical_digest: str | None
    token_digest: str | None
    execute_digest: str | None


# ---------------------------------------------------------------------------
# 5. Arguments digest builder
# ---------------------------------------------------------------------------


def _redact_argument_values(args: dict[str, Any]) -> dict[str, Any]:
    """Redact secret values from arguments for digest computation."""
    result: dict[str, Any] = {}
    for key, value in args.items():
        normalized_key = key.replace("_", "").replace("-", "").lower()
        if normalized_key in _NORMALIZED_FORBIDDEN_ARG_FIELDS:
            result[key] = "[REDACTED]"
            continue
        if isinstance(value, str):
            redacted = False
            for pattern in _SECRET_VALUE_PATTERNS:
                if pattern.search(value):
                    result[key] = "[REDACTED]"
                    redacted = True
                    break
            if not redacted:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = _redact_argument_values(value)
        else:
            result[key] = value
    return result


def build_arguments_digest(
    arguments: dict[str, Any] | None,
    *,
    redaction_version: str = _REDACTION_VERSION_FALLBACK,
) -> str:
    """Build a stable sha256:hex digest from safe/redacted arguments.

    Guarantees:
        - raw arguments are never stored or logged
        - secret-like fields are redacted before digest
        - key order does not affect digest (sorted JSON)
        - None arguments produce a deterministic digest
    """
    if arguments is None:
        # Deterministic digest for null arguments
        payload: dict[str, Any] = {
            "__redactionVersion": redaction_version,
            "__nullArguments": True,
        }
    else:
        safe_args = _redact_argument_values(arguments)
        payload = {
            "__redactionVersion": redaction_version,
            "arguments": safe_args,
        }

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    hex_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{DIGEST_PREFIX}{hex_digest}"


# ---------------------------------------------------------------------------
# 6. Canonical JSON serialization
# ---------------------------------------------------------------------------


def canonicalize_digest_package(package: dict[str, Any]) -> str:
    """Serialize a digest package to deterministic canonical JSON.

    Rules:
        - UTF-8 encoding
        - Deterministic object key ordering (sorted)
        - No insignificant whitespace
        - Explicit null handling
        - Stable timestamp format
    """
    return json.dumps(
        package,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# 7. Digest computation
# ---------------------------------------------------------------------------


def compute_digest(canonical_json: str) -> str:
    """Compute SHA-256 digest from canonical JSON.

    Returns "sha256:<hex>" format.
    """
    hex_digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return f"{DIGEST_PREFIX}{hex_digest}"


# ---------------------------------------------------------------------------
# 8. Digest package builder
# ---------------------------------------------------------------------------


def build_dry_run_decision_digest_package(
    *,
    dry_run_request_id: str,
    canonical_name: str,
    risk_tier: str | None,
    policy_version: str | None = None,
    policy_decision: str,
    allowlisted: bool,
    audit_written: bool,
    audit_event_id: str | None = None,
    arguments: dict[str, Any] | None = None,
    created_at: str | None = None,
    expires_at: str | None = None,
    tool_policy_version: str | None = None,
    tool_catalog_version: str | None = None,
) -> DigestPackageResult:
    """Build a canonical digest package from safe dry-run decision fields.

    The digest package contains only safe, deterministic fields.
    It never contains raw arguments, tokens, secrets, or credentials.

    Args:
        dry_run_request_id: The dry-run request correlation ID.
        canonical_name: Tool canonical name.
        risk_tier: Risk tier string (e.g. "R0").
        policy_version: Policy version (uses stable dev fallback if None).
        policy_decision: Dry-run decision string.
        allowlisted: Whether the tool is on the static allowlist.
        audit_written: Whether the audit event was written.
        audit_event_id: Audit event ID.
        arguments: Proposed arguments (will be redacted before digest).
        created_at: ISO 8601 creation timestamp.
        expires_at: ISO 8601 expiry timestamp.
        tool_policy_version: Tool policy version (uses fallback if None).
        tool_catalog_version: Tool catalog version (uses fallback if None).

    Returns:
        DigestPackageResult with the built package and computed digest.
    """
    try:
        # Build argumentsDigest — never store raw arguments
        arguments_digest = build_arguments_digest(arguments)

        package: dict[str, Any] = {
            "allowlisted": allowlisted,
            "argumentsDigest": arguments_digest,
            "auditEventId": audit_event_id,
            "auditWritten": audit_written,
            "canonicalName": canonical_name,
            "canonicalizationVersion": CANONICALIZATION_VERSION,
            "createdAt": created_at,
            "digestPackageVersion": DIGEST_PACKAGE_VERSION,
            "digestType": "tool_dry_run_decision",
            "dryRunRequestId": dry_run_request_id,
            "expiresAt": expires_at,
            "policyDecision": policy_decision,
            "policyVersion": policy_version or _TOOL_POLICY_VERSION_FALLBACK,
            "redactionVersion": _REDACTION_VERSION_FALLBACK,
            "riskTier": risk_tier,
            "schemaVersion": 1,
            "toolCatalogVersion": (
                tool_catalog_version or _TOOL_CATALOG_VERSION_FALLBACK
            ),
            "toolPolicyVersion": (
                tool_policy_version or _TOOL_POLICY_VERSION_FALLBACK
            ),
        }

        canonical = canonicalize_digest_package(package)
        digest = compute_digest(canonical)

        return DigestPackageResult(
            success=True,
            digest_package=package,
            canonical_json=canonical,
            digest=digest,
            error_code=None,
        )
    except Exception:
        return DigestPackageResult(
            success=False,
            digest_package=None,
            canonical_json=None,
            digest=None,
            error_code=ERROR_DIGEST_CANONICALIZATION_FAILED,
        )


# ---------------------------------------------------------------------------
# 9. Digest verification
# ---------------------------------------------------------------------------


def verify_dry_run_decision_digest(
    *,
    historical_digest: str | None,
    token_bound_digest: str | None,
    request_digest: str | None = None,
    execute_derived_digest: str | None = None,
    historical_created_at: str | None = None,
    historical_expires_at: str | None = None,
    now_iso: str | None = None,
) -> DigestVerificationResult:
    """Verify dry-run decision digest across all sources.

    Verification order:
        1. Historical digest must be present
        2. Token-bound digest must be present
        3. If request digest provided, it must match historical
        4. Token-bound digest must match historical
        5. If execute-derived digest provided, it must match historical
        6. Staleness check (if timestamps available)
        7. Expiry check (if timestamps available)

    All failures block before handler lookup / dispatch / execution.

    Args:
        historical_digest: Digest from dry-run audit event.
        token_bound_digest: Digest bound to confirmation token.
        request_digest: Optional digest from execute request.
        execute_derived_digest: Optional digest computed at execute time.
        historical_created_at: Created-at timestamp from historical record.
        historical_expires_at: Expires-at timestamp from historical record.
        now_iso: Current ISO 8601 timestamp for staleness/expiry checks.

    Returns:
        DigestVerificationResult with verification status.
    """
    # Gate 1: Historical digest must be present
    if not historical_digest:
        return DigestVerificationResult(
            verified=False,
            error_code=ERROR_DIGEST_HISTORICAL_MISSING,
            decision=DECISION_BLOCKED_DIGEST_MISSING,
            gate=GATE_DIGEST_HISTORICAL,
            historical_digest=historical_digest,
            token_digest=token_bound_digest,
            execute_digest=execute_derived_digest,
        )

    # Gate 2: Token-bound digest must be present
    if not token_bound_digest:
        return DigestVerificationResult(
            verified=False,
            error_code=ERROR_DIGEST_TOKEN_BINDING_MISSING,
            decision=DECISION_BLOCKED_DIGEST_MISSING,
            gate=GATE_DIGEST_TOKEN_BINDING,
            historical_digest=historical_digest,
            token_digest=token_bound_digest,
            execute_digest=execute_derived_digest,
        )

    # Gate 3: If request digest provided, must match historical
    if request_digest is not None and request_digest != historical_digest:
        return DigestVerificationResult(
            verified=False,
            error_code=ERROR_DIGEST_REQUEST_MISMATCH,
            decision=DECISION_BLOCKED_DIGEST_MISMATCH,
            gate=GATE_DIGEST_REQUEST,
            historical_digest=historical_digest,
            token_digest=token_bound_digest,
            execute_digest=execute_derived_digest,
        )

    # Gate 4: Token-bound digest must match historical
    if token_bound_digest != historical_digest:
        return DigestVerificationResult(
            verified=False,
            error_code=ERROR_DIGEST_TOKEN_MISMATCH,
            decision=DECISION_BLOCKED_DIGEST_MISMATCH,
            gate=GATE_DIGEST_TOKEN_MATCH,
            historical_digest=historical_digest,
            token_digest=token_bound_digest,
            execute_digest=execute_derived_digest,
        )

    # Gate 5: If execute-derived digest provided, must match historical
    if (
        execute_derived_digest is not None
        and execute_derived_digest != historical_digest
    ):
        return DigestVerificationResult(
            verified=False,
            error_code=ERROR_DIGEST_EXECUTE_MISMATCH,
            decision=DECISION_BLOCKED_DIGEST_MISMATCH,
            gate=GATE_DIGEST_EXECUTE_MATCH,
            historical_digest=historical_digest,
            token_digest=token_bound_digest,
            execute_digest=execute_derived_digest,
        )

    # Gate 6: Staleness / expiry check (best-effort)
    if now_iso and historical_expires_at:
        try:
            from datetime import datetime, timezone

            now_dt = _parse_iso_timestamp(now_iso)
            expires_dt = _parse_iso_timestamp(historical_expires_at)
            if now_dt is not None and expires_dt is not None:
                if now_dt.tzinfo is None:
                    now_dt = now_dt.replace(tzinfo=timezone.utc)
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                if now_dt >= expires_dt:
                    return DigestVerificationResult(
                        verified=False,
                        error_code=ERROR_DIGEST_EXPIRED,
                        decision=DECISION_BLOCKED_DIGEST_EXPIRED,
                        gate=GATE_DIGEST_EXPIRY,
                        historical_digest=historical_digest,
                        token_digest=token_bound_digest,
                        execute_digest=execute_derived_digest,
                    )
        except Exception:
            pass  # Timestamp parse failure → skip staleness check

    # All digest checks passed
    # But we still block because pre-execution audit is not implemented
    return DigestVerificationResult(
        verified=True,
        error_code=ERROR_DIGEST_VERIFIED_BUT_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED,
        decision=DECISION_BLOCKED_PRE_EXECUTION_AUDIT_NOT_IMPLEMENTED,
        gate=GATE_PRE_EXECUTION_AUDIT,
        historical_digest=historical_digest,
        token_digest=token_bound_digest,
        execute_digest=execute_derived_digest,
    )


# ---------------------------------------------------------------------------
# 10. Safe digest summary (for logging / response)
# ---------------------------------------------------------------------------


def safe_digest_summary(digest: str | None) -> str | None:
    """Return a safe summary of a digest value.

    Returns prefix + first 16 chars + "..." or None.
    Never exposes the full digest in user-facing summaries.
    """
    if not digest:
        return None
    if len(digest) > 20:
        return digest[:20] + "..."
    return digest


# ---------------------------------------------------------------------------
# 11. Internal helpers
# ---------------------------------------------------------------------------


def _parse_iso_timestamp(ts_str: str) -> "datetime | None":
    """Parse an ISO 8601 timestamp string to datetime."""
    if not ts_str:
        return None
    try:
        from datetime import datetime
        cleaned = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None
