"""Confirmation Token Issuance / Verification for the Hermes Dev WebUI.

This module implements dev-only confirmation token issuance and verification
as part of the execute gate stack. Tokens are short-lived, single-use approval
artifacts that bind to dry-run records.

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider imports, no tool handler imports, no dispatch imports
  - no network IO, no runtime state mutation outside token store
  - no STATIC_ALLOWLIST mutation
  - deterministic, JSON-serializable output
  - never stores raw token
  - never stores raw arguments
  - never stores secrets
  - never calls handler / dispatch / provider
  - token verification does NOT imply execution

Phase: 1G-04-20 — Confirmation Token Minimal Backend Implementation
Status: Token issuance + verification implemented, execute still blocked-only
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

_TOKEN_DIR_RELATIVE = "gateway/dev/tokens"
_TOKEN_FILENAME = "confirmation-tokens.jsonl"

# Token TTL
_TOKEN_TTL_SECONDS = 300  # 5 minutes
_MAX_TOKEN_TTL_SECONDS = 300

# Token raw size
_RAW_TOKEN_BYTES = 32  # 256 bits

# Token hash prefix length for tokenId
_TOKEN_ID_PREFIX_LEN = 24

# Forbidden production paths
_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"

# Dev HMAC namespace (deterministic, not a secret)
_DEV_HMAC_NAMESPACE = "hermes-dev-webui-confirmation-token-v1"

# Read limits
_MAX_READ_BYTES = 5 * 1024 * 1024  # 5 MiB
_MAX_LINE_BYTES = 64 * 1024  # 64 KiB per line


# ---------------------------------------------------------------------------
# 2. Error codes
# ---------------------------------------------------------------------------

ERROR_CONFIRMATION_MISSING = "confirmation_missing"
ERROR_CONFIRMATION_INVALID = "confirmation_invalid"
ERROR_CONFIRMATION_STORE_UNAVAILABLE = "confirmation_store_unavailable"
ERROR_CONFIRMATION_NOT_FOUND = "confirmation_not_found"
ERROR_CONFIRMATION_EXPIRED = "confirmation_expired"
ERROR_CONFIRMATION_REUSED = "confirmation_reused"
ERROR_CONFIRMATION_DRY_RUN_MISMATCH = "confirmation_dry_run_mismatch"
ERROR_CONFIRMATION_DIGEST_MISMATCH = "confirmation_digest_mismatch"
ERROR_CONFIRMATION_CANONICAL_NAME_MISMATCH = "confirmation_canonical_name_mismatch"
ERROR_CONFIRMATION_RISK_TIER_MISMATCH = "confirmation_risk_tier_mismatch"
ERROR_CONFIRMATION_POLICY_VERSION_MISMATCH = "confirmation_policy_version_mismatch"
ERROR_CONFIRMATION_AUDIT_EVENT_MISMATCH = "confirmation_audit_event_mismatch"
ERROR_CONFIRMATION_ARGUMENTS_MISMATCH = "confirmation_arguments_mismatch"
ERROR_CONFIRMATION_CONSUME_FAILED = "confirmation_consume_failed"
ERROR_CONFIRMATION_ISSUANCE_REJECTED = "confirmation_issuance_rejected"
ERROR_CONFIRMATION_PRODUCTION_PATH = "confirmation_production_path"
ERROR_CONFIRMATION_NOT_ALLOWED = "confirmation_not_allowed"
ERROR_CONFIRMATION_AUDIT_NOT_WRITTEN = "confirmation_audit_not_written"


# ---------------------------------------------------------------------------
# 3. Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConfirmationTokenIssueResult:
    """Immutable result of a confirmation token issuance attempt."""

    issued: bool
    error_code: str | None
    raw_token: str | None  # Returned exactly once, never stored
    token_id: str | None
    expires_at: str | None
    safe_summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConfirmationTokenVerificationResult:
    """Immutable result of a confirmation token verification attempt."""

    verified: bool
    consumed: bool
    error_code: str | None
    token_id: str | None
    binding_summary: dict[str, Any] = field(default_factory=dict)
    safe_summary: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 4. Internal helpers
# ---------------------------------------------------------------------------


def _is_relative_to(child: Path, parent: Path) -> bool:
    """Check if *child* path is inside or equal to *parent* path.

    Uses ``Path.relative_to()`` for proper containment semantics.
    """
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _resolve_hermes_home(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    """Resolve and validate HERMES_HOME.

    Returns (resolved_home, error_code_or_none).
    """
    if hermes_home is not None:
        home = Path(hermes_home).resolve()
    else:
        home_str = os.environ.get("HERMES_HOME", "")
        if not home_str:
            return Path(), ERROR_CONFIRMATION_STORE_UNAVAILABLE
        home = Path(home_str).resolve()

    prod_home = Path(_PRODUCTION_HERMES_HOME).resolve()

    # Block exact production home
    if home == prod_home:
        return Path(), ERROR_CONFIRMATION_PRODUCTION_PATH

    # Block inside production subtree
    if _is_relative_to(home, prod_home):
        return Path(), ERROR_CONFIRMATION_PRODUCTION_PATH

    return home, None


def _resolve_token_store_path(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, Path, str | None]:
    """Resolve and validate the token store path.

    Returns (token_dir, token_file, error_code_or_none).

    Guarantees:
        - HERMES_HOME must not be production home or inside production subtree
        - Token dir must be inside $HERMES_HOME/gateway/dev/tokens
        - Token file must be inside token dir
        - Symlink / path traversal into production is blocked
        - No file is opened if any containment check fails
    """
    home, home_error = _resolve_hermes_home(hermes_home)
    if home_error is not None:
        return Path(), Path(), home_error

    # Build token dir and file paths
    token_dir = home / _TOKEN_DIR_RELATIVE
    token_file = token_dir / _TOKEN_FILENAME

    resolved_dir = token_dir.resolve()
    resolved_file = token_file.resolve()

    prod_home = Path(_PRODUCTION_HERMES_HOME).resolve()

    # Block if resolved dir is production home or inside production subtree
    if resolved_dir == prod_home or _is_relative_to(resolved_dir, prod_home):
        return Path(), Path(), ERROR_CONFIRMATION_PRODUCTION_PATH

    # Block if resolved file is production home or inside production subtree
    if resolved_file == prod_home or _is_relative_to(resolved_file, prod_home):
        return Path(), Path(), ERROR_CONFIRMATION_PRODUCTION_PATH

    # Validate token dir is inside expected path under home
    expected_dir = (home / _TOKEN_DIR_RELATIVE).resolve()
    if not _is_relative_to(resolved_dir, expected_dir):
        return Path(), Path(), ERROR_CONFIRMATION_PRODUCTION_PATH

    # Validate token file is inside token dir
    if not _is_relative_to(resolved_file, resolved_dir):
        return Path(), Path(), ERROR_CONFIRMATION_PRODUCTION_PATH

    return token_dir, token_file, None


def _generate_raw_token() -> str:
    """Generate a 256-bit random token as base64url-safe string."""
    return secrets.token_urlsafe(_RAW_TOKEN_BYTES)


def _hash_token(raw_token: str) -> str:
    """Hash a raw token using HMAC-SHA256 with a dev namespace.

    Uses a deterministic HMAC key derived from the dev namespace.
    This is a dev-only implementation; the HMAC key is not a real secret.
    In production, a real server secret would be used instead.
    """
    key = _DEV_HMAC_NAMESPACE.encode("utf-8")
    return hmac.new(key, raw_token.encode("utf-8"), hashlib.sha256).hexdigest()


def _build_token_id(token_hash: str) -> str:
    """Derive a safe tokenId from tokenHash prefix."""
    return f"ctok_{token_hash[:_TOKEN_ID_PREFIX_LEN]}"


def _now_utc() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def _parse_iso_timestamp(ts_str: str) -> datetime | None:
    """Parse an ISO 8601 timestamp string to datetime."""
    if not ts_str:
        return None
    try:
        cleaned = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


def _append_token_record(
    token_file: Path,
    token_dir: Path,
    record: dict[str, Any],
) -> bool:
    """Append a token record to the JSONL store.

    Returns True on success, False on failure.
    Creates token_dir if needed.
    """
    try:
        token_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    try:
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return False

    line_bytes = (line + "\n").encode("utf-8")

    # Check individual record size
    if len(line_bytes) > _MAX_LINE_BYTES:
        return False

    try:
        with open(token_file, "a", encoding="utf-8") as f:
            f.write(line_bytes.decode("utf-8"))
        return True
    except OSError:
        return False


def _read_token_events(
    token_file: Path,
) -> list[dict[str, Any]]:
    """Read all token events from JSONL store.

    Returns list of parsed records (malformed lines skipped).
    """
    if not token_file.exists():
        return []

    try:
        file_size = token_file.stat().st_size
    except OSError:
        return []

    if file_size > _MAX_READ_BYTES:
        return []

    if file_size == 0:
        return []

    events: list[dict[str, Any]] = []
    try:
        with open(token_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                if len(line.encode("utf-8")) > _MAX_LINE_BYTES:
                    continue
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(record, dict):
                    events.append(record)
    except OSError:
        return []

    return events


def _find_latest_token_state(
    events: list[dict[str, Any]],
    token_hash: str,
) -> dict[str, Any] | None:
    """Find the latest state for a token by scanning events.

    Returns the issued event if found, or None.
    Also determines consumed status from consumed events.
    """
    issued_record: dict[str, Any] | None = None
    consumed = False

    for event in events:
        if event.get("tokenHash") != token_hash:
            continue
        event_type = event.get("eventType")
        if event_type == "issued":
            issued_record = event
            consumed = False  # Reset consumed for latest issued
        elif event_type == "consumed":
            consumed = True

    if issued_record is None:
        return None

    # Attach consumed status
    issued_record = dict(issued_record)
    issued_record["_consumed"] = consumed
    return issued_record


def _is_token_expired(
    token_state: dict[str, Any],
    now: datetime,
) -> bool:
    """Check if a token has expired.

    Returns True if expired (fail-closed).
    """
    expires_at_str = token_state.get("expiresAt")
    if not expires_at_str:
        return True  # Missing expiresAt → fail closed

    expires_at = _parse_iso_timestamp(expires_at_str)
    if expires_at is None:
        return True  # Unparseable → fail closed

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    now_aware = now
    if now_aware.tzinfo is None:
        now_aware = now_aware.replace(tzinfo=timezone.utc)

    return now_aware >= expires_at


def _safe_token_summary(token_state: dict[str, Any]) -> dict[str, Any]:
    """Build a safe summary from token state for user-facing responses.

    Never exposes tokenHash full value, raw token, or secrets.
    """
    token_hash = token_state.get("tokenHash", "")
    return {
        "tokenId": token_state.get("tokenId"),
        "tokenHashPrefix": token_hash[:8] + "..." if len(token_hash) >= 8 else None,
        "canonicalName": token_state.get("canonicalName"),
        "riskTier": token_state.get("riskTier"),
        "status": "consumed" if token_state.get("_consumed") else token_state.get("status"),
        "issuedAt": token_state.get("issuedAt"),
        "expiresAt": token_state.get("expiresAt"),
    }


# ---------------------------------------------------------------------------
# 5. Token issuance
# ---------------------------------------------------------------------------


def issue_confirmation_token(
    *,
    hermes_home: str | os.PathLike[str] | None = None,
    dry_run_record: Mapping[str, Any] | None = None,
    canonical_name: str,
    risk_tier: str | None = None,
    policy_version: str | None = None,
    dry_run_request_id: str | None = None,
    dry_run_decision_digest: str | None = None,
    audit_event_id: str | None = None,
    arguments_digest: str | None = None,
    redaction_version: str | None = None,
    now: datetime | None = None,
) -> ConfirmationTokenIssueResult:
    """Issue a confirmation token after an eligible dry-run.

    This function is dev-only. It:
      - Validates all preconditions
      - Generates a 256-bit raw token
      - Stores only tokenHash + binding metadata in dev-only JSONL
      - Returns the raw token exactly once (never stored)

    It does NOT:
      - Call tool handlers
      - Dispatch tools
      - Call providers
      - Access ~/.hermes
      - Modify STATIC_ALLOWLIST

    Args:
        hermes_home: HERMES_HOME path override.
        dry_run_record: Dry-run lookup result (may be None if not available).
        canonical_name: Tool canonical name (must be allowlisted).
        risk_tier: Tool risk tier.
        policy_version: Policy version.
        dry_run_request_id: Dry-run request correlation ID.
        dry_run_decision_digest: Dry-run decision digest.
        audit_event_id: Audit event ID.
        arguments_digest: Arguments digest.
        redaction_version: Redaction version.
        now: Current time override for testing.

    Returns:
        ConfirmationTokenIssueResult with raw_token, token_id, expires_at.
    """
    if now is None:
        now = _now_utc()

    # Step 1: Validate canonicalName is allowlisted
    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST
    if canonical_name not in STATIC_ALLOWLIST:
        return ConfirmationTokenIssueResult(
            issued=False,
            error_code=ERROR_CONFIRMATION_NOT_ALLOWED,
            raw_token=None,
            token_id=None,
            expires_at=None,
        )

    # Step 2: Validate dry-run record decision
    # Accept either a DryRunHistoricalLookupResult-like object or a dict
    if dry_run_record is not None:
        decision = (
            dry_run_record.decision
            if hasattr(dry_run_record, "decision")
            else dry_run_record.get("decision")
        )
        if decision != "would_allow":
            return ConfirmationTokenIssueResult(
                issued=False,
                error_code=ERROR_CONFIRMATION_NOT_ALLOWED,
                raw_token=None,
                token_id=None,
                expires_at=None,
            )

        # Step 3: Validate auditWritten
        audit_written = (
            dry_run_record.audit_written
            if hasattr(dry_run_record, "audit_written")
            else dry_run_record.get("audit_written")
        )
        if not audit_written:
            return ConfirmationTokenIssueResult(
                issued=False,
                error_code=ERROR_CONFIRMATION_AUDIT_NOT_WRITTEN,
                raw_token=None,
                token_id=None,
                expires_at=None,
            )
    else:
        # No dry-run record provided — cannot validate
        return ConfirmationTokenIssueResult(
            issued=False,
            error_code=ERROR_CONFIRMATION_ISSUANCE_REJECTED,
            raw_token=None,
            token_id=None,
            expires_at=None,
        )

    # Step 4: Validate dryRunRequestId present
    if not dry_run_request_id:
        return ConfirmationTokenIssueResult(
            issued=False,
            error_code=ERROR_CONFIRMATION_ISSUANCE_REJECTED,
            raw_token=None,
            token_id=None,
            expires_at=None,
        )

    # Step 5: Resolve and validate token store path
    token_dir, token_file, path_error = _resolve_token_store_path(hermes_home)
    if path_error is not None:
        return ConfirmationTokenIssueResult(
            issued=False,
            error_code=path_error,
            raw_token=None,
            token_id=None,
            expires_at=None,
        )

    # Step 6: Generate raw token and compute hash
    raw_token = _generate_raw_token()
    token_hash = _hash_token(raw_token)
    token_id = _build_token_id(token_hash)

    # Step 7: Compute TTL
    issued_at = now
    expires_at = issued_at + timedelta(seconds=_TOKEN_TTL_SECONDS)

    # Step 7a: If dry-run record has expiresAt, token must not exceed it
    dr_expires_at_str = (
        dry_run_record.expires_at
        if hasattr(dry_run_record, "expires_at")
        else dry_run_record.get("expires_at")
    )
    if dr_expires_at_str:
        dr_expires_at = _parse_iso_timestamp(dr_expires_at_str)
        if dr_expires_at is not None:
            if dr_expires_at.tzinfo is None:
                dr_expires_at = dr_expires_at.replace(tzinfo=timezone.utc)
            if expires_at > dr_expires_at:
                expires_at = dr_expires_at

    # Step 8: Build issued record
    record: dict[str, Any] = {
        "recordType": "confirmation_token",
        "schemaVersion": 1,
        "eventType": "issued",
        "tokenId": token_id,
        "tokenHash": token_hash,
        "dryRunRequestId": dry_run_request_id,
        "dryRunDecisionDigest": dry_run_decision_digest,
        "canonicalName": canonical_name,
        "riskTier": risk_tier,
        "policyVersion": policy_version,
        "auditEventId": audit_event_id,
        "argumentsDigest": arguments_digest,
        "redactionVersion": redaction_version,
        "issuedAt": issued_at.isoformat(),
        "expiresAt": expires_at.isoformat(),
        "consumedAt": None,
        "status": "issued",
    }

    # Step 9: Append to token store
    if not _append_token_record(token_file, token_dir, record):
        return ConfirmationTokenIssueResult(
            issued=False,
            error_code=ERROR_CONFIRMATION_STORE_UNAVAILABLE,
            raw_token=None,
            token_id=None,
            expires_at=None,
        )

    # Step 10: Return raw token exactly once
    return ConfirmationTokenIssueResult(
        issued=True,
        error_code=None,
        raw_token=raw_token,
        token_id=token_id,
        expires_at=expires_at.isoformat(),
        safe_summary={
            "tokenId": token_id,
            "tokenHashPrefix": token_hash[:8] + "...",
            "canonicalName": canonical_name,
            "riskTier": risk_tier,
            "status": "issued",
            "issuedAt": issued_at.isoformat(),
            "expiresAt": expires_at.isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# 6. Token verification
# ---------------------------------------------------------------------------


def verify_confirmation_token(
    *,
    hermes_home: str | os.PathLike[str] | None = None,
    raw_token: str | None,
    dry_run_request_id: str,
    dry_run_decision_digest: str | None = None,
    canonical_name: str,
    risk_tier: str | None = None,
    policy_version: str | None = None,
    audit_event_id: str | None = None,
    arguments_digest: str | None = None,
    now: datetime | None = None,
    consume: bool = True,
) -> ConfirmationTokenVerificationResult:
    """Verify a confirmation token against the dev-only token store.

    This function is dev-only. It:
      - Validates raw token presence and shape
      - Hashes raw token and looks up in token store
      - Checks expiry, single-use, and all binding fields
      - Optionally consumes the token (append consumed event)
      - Returns a safe verification result

    It does NOT:
      - Call tool handlers
      - Dispatch tools
      - Call providers
      - Access ~/.hermes
      - Expose raw token or full tokenHash

    Args:
        hermes_home: HERMES_HOME path override.
        raw_token: The raw confirmation token string.
        dry_run_request_id: Execute request's dryRunRequestId.
        dry_run_decision_digest: Execute request's dryRunDecisionDigest.
        canonical_name: Execute request's canonicalName.
        risk_tier: Execute request's riskTier.
        policy_version: Execute request's policyVersion.
        audit_event_id: Execute request's auditEventId.
        arguments_digest: Execute request's argumentsDigest.
        now: Current time override for testing.
        consume: Whether to consume the token on successful verification.

    Returns:
        ConfirmationTokenVerificationResult with verified status and safe summary.
    """
    if now is None:
        now = _now_utc()

    # Step 1: Validate raw token present
    if not raw_token:
        return ConfirmationTokenVerificationResult(
            verified=False,
            consumed=False,
            error_code=ERROR_CONFIRMATION_MISSING,
            token_id=None,
        )

    # Step 2: Validate raw token shape (basic sanity: non-empty, reasonable length)
    if not isinstance(raw_token, str) or len(raw_token) < 10 or len(raw_token) > 512:
        return ConfirmationTokenVerificationResult(
            verified=False,
            consumed=False,
            error_code=ERROR_CONFIRMATION_INVALID,
            token_id=None,
        )

    # Step 3: Resolve and validate token store path
    token_dir, token_file, path_error = _resolve_token_store_path(hermes_home)
    if path_error is not None:
        return ConfirmationTokenVerificationResult(
            verified=False,
            consumed=False,
            error_code=path_error,
            token_id=None,
        )

    # Step 4: Hash raw token
    token_hash = _hash_token(raw_token)
    token_id = _build_token_id(token_hash)

    # Step 5: Read token store
    events = _read_token_events(token_file)
    if events is None:
        return ConfirmationTokenVerificationResult(
            verified=False,
            consumed=False,
            error_code=ERROR_CONFIRMATION_STORE_UNAVAILABLE,
            token_id=token_id,
        )

    # Step 6: Find latest token state
    token_state = _find_latest_token_state(events, token_hash)
    if token_state is None:
        return ConfirmationTokenVerificationResult(
            verified=False,
            consumed=False,
            error_code=ERROR_CONFIRMATION_NOT_FOUND,
            token_id=token_id,
        )

    # Step 7: Check expiry
    if _is_token_expired(token_state, now):
        return ConfirmationTokenVerificationResult(
            verified=False,
            consumed=False,
            error_code=ERROR_CONFIRMATION_EXPIRED,
            token_id=token_id,
            safe_summary=_safe_token_summary(token_state),
        )

    # Step 8: Check consumed
    if token_state.get("_consumed"):
        return ConfirmationTokenVerificationResult(
            verified=False,
            consumed=False,
            error_code=ERROR_CONFIRMATION_REUSED,
            token_id=token_id,
            safe_summary=_safe_token_summary(token_state),
        )

    # Step 9: Verify dryRunRequestId binding
    if token_state.get("dryRunRequestId") != dry_run_request_id:
        return ConfirmationTokenVerificationResult(
            verified=False,
            consumed=False,
            error_code=ERROR_CONFIRMATION_DRY_RUN_MISMATCH,
            token_id=token_id,
            safe_summary=_safe_token_summary(token_state),
        )

    # Step 10: Verify dryRunDecisionDigest binding
    # Phase 1G-04-22: Token must have non-null dryRunDecisionDigest binding.
    # Legacy tokens with null digest fail closed.
    stored_digest = token_state.get("dryRunDecisionDigest")
    if stored_digest is None:
        # Legacy token with null digest binding → fail closed
        return ConfirmationTokenVerificationResult(
            verified=False,
            consumed=False,
            error_code=ERROR_CONFIRMATION_DIGEST_MISMATCH,
            token_id=token_id,
            safe_summary=_safe_token_summary(token_state),
        )
    if dry_run_decision_digest is not None:
        if stored_digest != dry_run_decision_digest:
            return ConfirmationTokenVerificationResult(
                verified=False,
                consumed=False,
                error_code=ERROR_CONFIRMATION_DIGEST_MISMATCH,
                token_id=token_id,
                safe_summary=_safe_token_summary(token_state),
            )

    # Step 11: Verify canonicalName binding
    if token_state.get("canonicalName") != canonical_name:
        return ConfirmationTokenVerificationResult(
            verified=False,
            consumed=False,
            error_code=ERROR_CONFIRMATION_CANONICAL_NAME_MISMATCH,
            token_id=token_id,
            safe_summary=_safe_token_summary(token_state),
        )

    # Step 12: Verify riskTier binding (when available)
    stored_risk_tier = token_state.get("riskTier")
    if stored_risk_tier is not None and risk_tier is not None:
        if stored_risk_tier != risk_tier:
            return ConfirmationTokenVerificationResult(
                verified=False,
                consumed=False,
                error_code=ERROR_CONFIRMATION_RISK_TIER_MISMATCH,
                token_id=token_id,
                safe_summary=_safe_token_summary(token_state),
            )

    # Step 13: Verify policyVersion binding (when available)
    stored_policy_version = token_state.get("policyVersion")
    if stored_policy_version is not None and policy_version is not None:
        if stored_policy_version != policy_version:
            return ConfirmationTokenVerificationResult(
                verified=False,
                consumed=False,
                error_code=ERROR_CONFIRMATION_POLICY_VERSION_MISMATCH,
                token_id=token_id,
                safe_summary=_safe_token_summary(token_state),
            )

    # Step 14: Verify auditEventId binding (when available)
    stored_audit_event_id = token_state.get("auditEventId")
    if stored_audit_event_id is not None and audit_event_id is not None:
        if stored_audit_event_id != audit_event_id:
            return ConfirmationTokenVerificationResult(
                verified=False,
                consumed=False,
                error_code=ERROR_CONFIRMATION_AUDIT_EVENT_MISMATCH,
                token_id=token_id,
                safe_summary=_safe_token_summary(token_state),
            )

    # Step 15: Verify argumentsDigest binding (when available)
    stored_arguments_digest = token_state.get("argumentsDigest")
    if stored_arguments_digest is not None and arguments_digest is not None:
        if stored_arguments_digest != arguments_digest:
            return ConfirmationTokenVerificationResult(
                verified=False,
                consumed=False,
                error_code=ERROR_CONFIRMATION_ARGUMENTS_MISMATCH,
                token_id=token_id,
                safe_summary=_safe_token_summary(token_state),
            )

    # Step 16: Token verified — consume if requested
    consumed = False
    if consume:
        consumed_event: dict[str, Any] = {
            "recordType": "confirmation_token",
            "schemaVersion": 1,
            "eventType": "consumed",
            "tokenId": token_state.get("tokenId"),
            "tokenHash": token_hash,
            "dryRunRequestId": dry_run_request_id,
            "consumedAt": now.isoformat(),
            "status": "consumed",
        }
        consumed = _append_token_record(token_file, token_dir, consumed_event)
        if not consumed:
            return ConfirmationTokenVerificationResult(
                verified=False,
                consumed=False,
                error_code=ERROR_CONFIRMATION_CONSUME_FAILED,
                token_id=token_id,
                safe_summary=_safe_token_summary(token_state),
            )

    # Step 17: Return verified result with safe summary
    return ConfirmationTokenVerificationResult(
        verified=True,
        consumed=consumed,
        error_code=None,
        token_id=token_id,
        binding_summary={
            "dryRunRequestId": dry_run_request_id,
            "canonicalName": canonical_name,
            "riskTier": risk_tier,
        },
        safe_summary=_safe_token_summary(token_state),
    )
