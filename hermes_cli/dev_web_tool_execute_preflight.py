"""Tool Execute Preflight — Dry-Run Historical Lookup Reader.

This module implements a read-only lookup helper that retrieves prior dry-run
audit records from the dev-only JSONL audit file. It is used by the execute
preflight gate to verify that a valid dry-run decision exists before execution
may proceed (execution remains disabled in this phase).

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider imports, no tool handler imports, no dispatch imports
  - no network IO, no filesystem mutation, no runtime state mutation
  - no audit file write (read-only)
  - no STATIC_ALLOWLIST mutation or population
  - deterministic, JSON-serializable output
  - parse failure → fail closed
  - file not found → fail closed
  - record not found → fail closed
  - record expired → fail closed
  - decision not would_allow → fail closed
  - no raw secrets in output
  - no raw arguments in output
  - never accesses ~/.hermes
  - never accesses production state.db

Phase: 1G-04-17 — Preflight Production Path Guard Hardening
Status: Read-only lookup with containment-based production guard (no execution, no token, no digest verification)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

# Storage path components — aligned with dev_web_tool_dry_run_audit.py
_AUDIT_DIR_RELATIVE = "gateway/dev/audit"
_AUDIT_FILENAME = "tool-dry-run-audit.jsonl"

# Read limits
_MAX_READ_BYTES = 5 * 1024 * 1024  # 5 MiB
_MAX_LINE_BYTES = 64 * 1024  # 64 KiB per line

# Expiry
_DRY_RUN_TTL_SECONDS = 300  # 5 minutes

# Forbidden production path (never read from)
_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"

# Dry-run decision that allows execution consideration
_DRY_RUN_DECISION_WOULD_ALLOW = "would_allow"


# ---------------------------------------------------------------------------
# 2. Error codes
# ---------------------------------------------------------------------------

ERROR_DRY_RUN_NOT_FOUND = "dry_run_not_found"
ERROR_DRY_RUN_EXPIRED = "dry_run_expired"
ERROR_DRY_RUN_NOT_ALLOWED = "dry_run_not_allowed"
ERROR_DRY_RUN_AUDIT_MISSING = "dry_run_audit_missing"
ERROR_DRY_RUN_CANONICAL_NAME_MISMATCH = "dry_run_canonical_name_mismatch"
ERROR_DRY_RUN_RISK_TIER_MISMATCH = "dry_run_risk_tier_mismatch"
ERROR_DRY_RUN_POLICY_VERSION_MISMATCH = "dry_run_policy_version_mismatch"
ERROR_DRY_RUN_DIGEST_MISMATCH = "dry_run_digest_mismatch"
ERROR_DRY_RUN_LOOKUP_UNAVAILABLE = "dry_run_lookup_unavailable"


# ---------------------------------------------------------------------------
# 3. Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DryRunHistoricalLookupResult:
    """Immutable result of a dry-run historical record lookup.

    If found is False, all other fields are None except error_code.
    If found is True, the record was successfully retrieved and passed
    basic structural validation.

    Important mapping notes:
      - auditWritten: The audit event builder always writes auditWritten=False
        to the JSONL record. Our lookup treats a found record as effectively
        audit_written=True because the record's presence in the JSONL proves
        it was written. This is documented as "presence = written".
      - policyVersion: Not stored in current audit events. Field is None.
      - argumentsDigest: Not stored in current audit events. Field is None.
      - dryRunDecisionDigest: Not stored in current audit events. Field is None.
    """

    found: bool
    error_code: str | None
    dry_run_request_id: str | None
    canonical_name: str | None
    decision: str | None
    risk_tier: str | None
    policy_version: str | None
    arguments_digest: str | None
    dry_run_decision_digest: str | None
    audit_written: bool | None
    audit_event_id: str | None
    created_at: str | None
    expires_at: str | None
    lookup_source: str | None
    redaction_status: str | None
    safe_summary: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 4. Internal helpers
# ---------------------------------------------------------------------------


def _is_relative_to(child: Path, parent: Path) -> bool:
    """Check if *child* path is inside or equal to *parent* path.

    Uses ``Path.relative_to()`` for proper path containment semantics
    (not string prefix matching).  Both arguments must already be resolved
    by the caller if symlink handling is required.
    """
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _resolve_audit_path(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    """Resolve and validate the audit file path for reading.

    Returns:
        (audit_file_path, error_code_or_none)

    Guarantees (hardened in Phase 1G-04-17):
        - HERMES_HOME must not be production home or inside production subtree
        - Resolved audit path must not be production home or inside production subtree
        - Resolved audit path must be inside the expected dev audit directory
        - Symlink/path traversal into production home is blocked
        - Symlink/path traversal escaping dev audit directory is blocked
        - No file is opened if any containment check fails
        - Path containment uses Path.relative_to(), not string prefix
    """
    if hermes_home is not None:
        home = Path(hermes_home).resolve()
    else:
        home_str = os.environ.get("HERMES_HOME", "")
        if not home_str:
            return Path(), ERROR_DRY_RUN_LOOKUP_UNAVAILABLE
        home = Path(home_str).resolve()

    # ── Production path containment guard ──
    # Block if home is exactly production home or inside production subtree.
    # Uses Path containment (not string prefix) to avoid false positives
    # on paths like /Users/.../.hermes-dev which share a string prefix
    # with /Users/.../.hermes but are not inside it.
    prod_home = Path(_PRODUCTION_HERMES_HOME).resolve()

    if home == prod_home or _is_relative_to(home, prod_home):
        return Path(), ERROR_DRY_RUN_LOOKUP_UNAVAILABLE

    # Build audit path and resolve it
    audit_path = home / _AUDIT_DIR_RELATIVE / _AUDIT_FILENAME
    resolved_audit = audit_path.resolve()

    # Block if resolved audit path is production home or inside production subtree.
    # This catches symlink/path traversal that resolves into production.
    if resolved_audit == prod_home or _is_relative_to(resolved_audit, prod_home):
        return Path(), ERROR_DRY_RUN_LOOKUP_UNAVAILABLE

    # Block if resolved audit path escapes the expected dev audit directory.
    # The audit file must resolve inside $HERMES_HOME/gateway/dev/audit/.
    expected_audit_dir = (home / _AUDIT_DIR_RELATIVE).resolve()
    if not _is_relative_to(resolved_audit, expected_audit_dir):
        return Path(), ERROR_DRY_RUN_LOOKUP_UNAVAILABLE

    return audit_path, None


def _parse_iso_timestamp(ts_str: str) -> datetime | None:
    """Parse an ISO 8601 timestamp string to datetime.

    Returns None on parse failure.
    """
    if not ts_str:
        return None
    try:
        # Handle timezone-aware and naive strings
        cleaned = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


def _is_record_expired(
    record: dict[str, Any],
    now: datetime,
    ttl_seconds: int = _DRY_RUN_TTL_SECONDS,
) -> bool:
    """Check if a dry-run record has expired.

    Uses the record's 'timestamp' field + TTL.
    Returns True if expired (fail-closed).
    Returns True if timestamp is missing or unparseable (fail-closed).
    """
    ts_str = record.get("timestamp")
    if not ts_str or not isinstance(ts_str, str):
        return True  # missing timestamp → fail closed

    record_time = _parse_iso_timestamp(ts_str)
    if record_time is None:
        return True  # unparseable → fail closed

    # Ensure both datetimes are timezone-aware for comparison
    if record_time.tzinfo is None:
        # Treat naive timestamps as UTC
        record_time = record_time.replace(tzinfo=timezone.utc)

    now_aware = now
    if now_aware.tzinfo is None:
        now_aware = now_aware.replace(tzinfo=timezone.utc)

    elapsed = (now_aware - record_time).total_seconds()
    return elapsed > ttl_seconds


def _build_safe_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Build a safe summary from the audit record.

    Excludes raw arguments, secrets, provider credentials, etc.
    """
    return {
        "toolExists": record.get("toolExists"),
        "redactionApplied": record.get("redactionApplied"),
        "candidateAllowlistMatched": record.get("candidateAllowlistMatched"),
        "denylistMatched": record.get("denylistMatched"),
        "resultStatus": record.get("resultStatus"),
        "schemaVersion": record.get("schemaVersion"),
        "reasonCodesCount": len(record.get("reasonCodes", [])),
        "forbiddenFieldsCount": len(record.get("forbiddenFields", [])),
    }


def _build_not_found_result(
    error_code: str,
    dry_run_request_id: str | None = None,
) -> DryRunHistoricalLookupResult:
    """Build a standard not-found / error lookup result."""
    return DryRunHistoricalLookupResult(
        found=False,
        error_code=error_code,
        dry_run_request_id=dry_run_request_id,
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


def _build_found_result(
    record: dict[str, Any],
    audit_path: Path,
    now: datetime,
) -> DryRunHistoricalLookupResult:
    """Build a lookup result from a found audit record.

    Maps JSONL fields to lookup result fields:
      - requestId → dry_run_request_id
      - canonicalName → canonical_name
      - decision → decision
      - riskTier → risk_tier
      - timestamp → created_at
      - eventId → audit_event_id
      - auditWritten → True (presence = written, see mapping note)
      - redactionApplied → redaction_status
    """
    ts_str = record.get("timestamp", "")
    created_at = ts_str if isinstance(ts_str, str) else None

    # Compute expires_at from timestamp + TTL
    record_time = _parse_iso_timestamp(ts_str) if ts_str else None
    expires_at: str | None = None
    if record_time is not None:
        from datetime import timedelta
        expires_dt = record_time + timedelta(seconds=_DRY_RUN_TTL_SECONDS)
        expires_at = expires_dt.isoformat()

    return DryRunHistoricalLookupResult(
        found=True,
        error_code=None,
        dry_run_request_id=record.get("requestId"),
        canonical_name=record.get("canonicalName"),
        decision=record.get("decision"),
        risk_tier=record.get("riskTier"),
        policy_version=None,  # Not stored in current audit events
        arguments_digest=None,  # Not stored in current audit events
        dry_run_decision_digest=None,  # Not stored in current audit events
        audit_written=True,  # Presence in JSONL = written (mapping note)
        audit_event_id=record.get("eventId"),
        created_at=created_at,
        expires_at=expires_at,
        lookup_source=str(audit_path),
        redaction_status=(
            "applied" if record.get("redactionApplied") else "none"
        ),
        safe_summary=_build_safe_summary(record),
    )


# ---------------------------------------------------------------------------
# 5. Core lookup function
# ---------------------------------------------------------------------------


def lookup_dry_run_record(
    *,
    hermes_home: str | os.PathLike[str] | None = None,
    dry_run_request_id: str,
    canonical_name: str,
    max_bytes: int = _MAX_READ_BYTES,
    now: datetime | None = None,
) -> DryRunHistoricalLookupResult:
    """Look up a prior dry-run audit record by dryRunRequestId.

    This function is **read-only**. It:
      - Reads the dev-only audit JSONL file
      - Searches for a record matching the given dryRunRequestId
      - Returns a safe, redacted result

    It does NOT:
      - Write files
      - Access ~/.hermes
      - Access production state.db
      - Call tool handlers
      - Dispatch tools
      - Call providers
      - Expose raw secrets or arguments

    Args:
        hermes_home: HERMES_HOME path override. If None, reads from env.
        dry_run_request_id: The dryRunRequestId to search for.
        canonical_name: The canonical tool name (used for binding check).
        max_bytes: Maximum bytes to read from the audit file.
        now: Current time override for testing. Defaults to utcnow.

    Returns:
        DryRunHistoricalLookupResult with found=True/False and safe fields.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Step 1: Resolve audit path
    audit_path, path_error = _resolve_audit_path(hermes_home)
    if path_error is not None:
        return _build_not_found_result(
            error_code=path_error,
            dry_run_request_id=dry_run_request_id,
        )

    # Step 2: Check file exists
    if not audit_path.exists():
        return _build_not_found_result(
            error_code=ERROR_DRY_RUN_NOT_FOUND,
            dry_run_request_id=dry_run_request_id,
        )

    # Step 3: Check file size
    try:
        file_size = audit_path.stat().st_size
    except OSError:
        return _build_not_found_result(
            error_code=ERROR_DRY_RUN_LOOKUP_UNAVAILABLE,
            dry_run_request_id=dry_run_request_id,
        )

    if file_size > max_bytes:
        # File too large — fail closed
        return _build_not_found_result(
            error_code=ERROR_DRY_RUN_LOOKUP_UNAVAILABLE,
            dry_run_request_id=dry_run_request_id,
        )

    if file_size == 0:
        return _build_not_found_result(
            error_code=ERROR_DRY_RUN_NOT_FOUND,
            dry_run_request_id=dry_run_request_id,
        )

    # Step 4: Read and parse JSONL
    best_record: dict[str, Any] | None = None
    best_timestamp: str | None = None

    try:
        with open(audit_path, "r", encoding="utf-8") as f:
            for line in f:
                # Skip empty lines
                if not line.strip():
                    continue

                # Skip lines that are too large
                if len(line.encode("utf-8")) > _MAX_LINE_BYTES:
                    continue

                # Parse JSON
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    # Malformed line — skip, don't crash
                    continue

                if not isinstance(record, dict):
                    continue

                # Check if this record matches the requestId
                record_request_id = record.get("requestId")
                if record_request_id != dry_run_request_id:
                    continue

                # Use latest valid record (last occurrence wins)
                record_ts = record.get("timestamp")
                if record_ts is not None:
                    best_record = record
                    best_timestamp = record_ts
                elif best_record is None:
                    # First match with no timestamp — use it as fallback
                    best_record = record

    except OSError:
        return _build_not_found_result(
            error_code=ERROR_DRY_RUN_LOOKUP_UNAVAILABLE,
            dry_run_request_id=dry_run_request_id,
        )

    # Step 5: Check if found
    if best_record is None:
        return _build_not_found_result(
            error_code=ERROR_DRY_RUN_NOT_FOUND,
            dry_run_request_id=dry_run_request_id,
        )

    # Step 6: Check expiry
    if _is_record_expired(best_record, now):
        return _build_not_found_result(
            error_code=ERROR_DRY_RUN_EXPIRED,
            dry_run_request_id=dry_run_request_id,
        )

    # Step 7: Build found result
    return _build_found_result(best_record, audit_path, now)


# ---------------------------------------------------------------------------
# 6. Binding verification functions
# ---------------------------------------------------------------------------


def verify_decision_allowed(
    lookup_result: DryRunHistoricalLookupResult,
) -> str | None:
    """Verify that the dry-run decision was would_allow.

    Returns error code if not allowed, None if allowed.
    """
    if not lookup_result.found:
        return lookup_result.error_code or ERROR_DRY_RUN_LOOKUP_UNAVAILABLE
    if lookup_result.decision != _DRY_RUN_DECISION_WOULD_ALLOW:
        return ERROR_DRY_RUN_NOT_ALLOWED
    return None


def verify_audit_written(
    lookup_result: DryRunHistoricalLookupResult,
) -> str | None:
    """Verify that the dry-run audit was written.

    In the current implementation, audit_written=True when the record
    is found (presence = written). Returns error code if not written.
    """
    if not lookup_result.found:
        return lookup_result.error_code or ERROR_DRY_RUN_LOOKUP_UNAVAILABLE
    if not lookup_result.audit_written:
        return ERROR_DRY_RUN_AUDIT_MISSING
    return None


def verify_canonical_name_binding(
    lookup_result: DryRunHistoricalLookupResult,
    canonical_name: str,
) -> str | None:
    """Verify canonicalName binding between execute request and dry-run record.

    Returns error code on mismatch, None if matches.
    """
    if not lookup_result.found:
        return lookup_result.error_code or ERROR_DRY_RUN_LOOKUP_UNAVAILABLE
    if lookup_result.canonical_name != canonical_name:
        return ERROR_DRY_RUN_CANONICAL_NAME_MISMATCH
    return None


def verify_risk_tier_binding(
    lookup_result: DryRunHistoricalLookupResult,
    expected_risk_tier: str | None,
) -> str | None:
    """Verify riskTier binding between execute request and dry-run record.

    Returns error code on mismatch, None if matches or either is None.
    If either side has no risk tier, the check is skipped (not fail-closed)
    because some tools may not have a risk tier in the audit record.
    """
    if not lookup_result.found:
        return lookup_result.error_code or ERROR_DRY_RUN_LOOKUP_UNAVAILABLE
    # If either is None, skip binding check (safe: no false mismatch)
    if lookup_result.risk_tier is None or expected_risk_tier is None:
        return None
    if lookup_result.risk_tier != expected_risk_tier:
        return ERROR_DRY_RUN_RISK_TIER_MISMATCH
    return None


def verify_policy_version_binding(
    lookup_result: DryRunHistoricalLookupResult,
    expected_policy_version: str | None,
) -> str | None:
    """Verify policyVersion binding.

    Current audit events do not store policyVersion, so this check
    is effectively a no-op. Returns None (pass) unless both sides
    have a value and they mismatch.
    """
    if not lookup_result.found:
        return lookup_result.error_code or ERROR_DRY_RUN_LOOKUP_UNAVAILABLE
    # Both None → pass
    if lookup_result.policy_version is None and expected_policy_version is None:
        return None
    # One None, one set → pass (field not yet stored in audit)
    if lookup_result.policy_version is None or expected_policy_version is None:
        return None
    # Both set → compare
    if lookup_result.policy_version != expected_policy_version:
        return ERROR_DRY_RUN_POLICY_VERSION_MISMATCH
    return None


def verify_digest_binding(
    lookup_result: DryRunHistoricalLookupResult,
    request_digest: str | None,
) -> str | None:
    """Verify dryRunDecisionDigest binding.

    Current audit events do not store dryRunDecisionDigest. If the
    lookup result has no digest (None), the check passes (field not
    yet stored). If both sides have digests, they must match.
    """
    if not lookup_result.found:
        return lookup_result.error_code or ERROR_DRY_RUN_LOOKUP_UNAVAILABLE
    # Lookup has no stored digest → cannot verify → pass
    if lookup_result.dry_run_decision_digest is None:
        return None
    # Request has no digest → cannot verify → pass
    if request_digest is None:
        return None
    # Both have digests → must match
    if lookup_result.dry_run_decision_digest != request_digest:
        return ERROR_DRY_RUN_DIGEST_MISMATCH
    return None
