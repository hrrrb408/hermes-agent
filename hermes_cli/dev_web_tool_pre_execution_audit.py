"""Pre-Execution Audit for the Hermes Dev WebUI Tool Execute Gate.

This module implements minimal pre-execution audit writing for the execute gate
stack.  It builds an audit event from the safe execute context, validates the
dev-only audit store path, and writes an append-only JSONL record.

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider imports, no tool handler imports, no dispatch imports
  - no network IO, no runtime state mutation outside audit JSONL
  - no STATIC_ALLOWLIST mutation
  - deterministic, JSON-serializable output
  - never stores raw confirmationToken
  - never stores full tokenHash
  - never stores raw arguments
  - never stores secrets
  - never calls handler / dispatch / provider
  - pre-execution audit write success does NOT imply execution

Phase: 1G-04-24 — Pre-Execution Audit Minimal Implementation
Status: Audit package + path guard + JSONL writer implemented, execute still blocked-only
"""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

PRE_EXECUTION_AUDIT_SCHEMA_VERSION = 1
PRE_EXECUTION_AUDIT_RECORD_TYPE = "tool_pre_execution_audit"
PRE_EXECUTION_AUDIT_EVENT_TYPE = "pre_execution_gate_passed"
PRE_EXECUTION_AUDIT_FILENAME = "tool-pre-execution-audit.jsonl"
PRE_EXECUTION_AUDIT_ID_PREFIX = "pea_"
EXECUTE_REQUEST_ID_PREFIX = "exe_"

_AUDIT_DIR_RELATIVE = "gateway/dev/audit"

# Forbidden production paths
_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"

# Write limits
_MAX_LINE_BYTES = 64 * 1024  # 64 KiB per line

# ID random bytes
_ID_RANDOM_BYTES = 16  # 128 bits of randomness


# ---------------------------------------------------------------------------
# 2. Error codes / decisions
# ---------------------------------------------------------------------------

ERROR_PRE_EXECUTION_AUDIT_UNAVAILABLE = "pre_execution_audit_unavailable"
ERROR_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN = "pre_execution_audit_path_forbidden"
ERROR_PRE_EXECUTION_AUDIT_WRITE_FAILED = "pre_execution_audit_write_failed"
ERROR_PRE_EXECUTION_AUDIT_INVALID_STATE = "pre_execution_audit_invalid_state"
ERROR_PRE_EXECUTION_AUDIT_MISSING_REQUIRED_FIELD = (
    "pre_execution_audit_missing_required_field"
)
ERROR_PRE_EXECUTION_AUDIT_SERIALIZATION_FAILED = (
    "pre_execution_audit_serialization_failed"
)
ERROR_PRE_EXECUTION_AUDIT_WRITTEN_BUT_HANDLER_LOOKUP_NOT_ENABLED = (
    "pre_execution_audit_written_but_handler_lookup_not_enabled"
)
ERROR_HANDLER_LOOKUP_NOT_ENABLED = "handler_lookup_not_enabled"
ERROR_HANDLER_LOOKUP_WRITTEN_BUT_DISPATCH_NOT_ENABLED = (
    "handler_lookup_written_but_dispatch_not_enabled"
)
ERROR_DISPATCH_NOT_ENABLED = "dispatch_not_enabled"

DECISION_BLOCKED_PRE_EXECUTION_AUDIT_UNAVAILABLE = (
    "blocked_pre_execution_audit_unavailable"
)
DECISION_BLOCKED_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN = (
    "blocked_pre_execution_audit_path_forbidden"
)
DECISION_BLOCKED_PRE_EXECUTION_AUDIT_WRITE_FAILED = (
    "blocked_pre_execution_audit_write_failed"
)
DECISION_BLOCKED_PRE_EXECUTION_AUDIT_INVALID_STATE = (
    "blocked_pre_execution_audit_invalid_state"
)
DECISION_BLOCKED_PRE_EXECUTION_AUDIT_MISSING_REQUIRED_FIELD = (
    "blocked_pre_execution_audit_missing_required_field"
)
DECISION_BLOCKED_PRE_EXECUTION_AUDIT_SERIALIZATION_FAILED = (
    "blocked_pre_execution_audit_serialization_failed"
)
DECISION_BLOCKED_HANDLER_LOOKUP_NOT_ENABLED = "blocked_handler_lookup_not_enabled"

# Gate constants
GATE_PRE_EXECUTION_AUDIT_PACKAGE = "pre_execution_audit_package"
GATE_PRE_EXECUTION_AUDIT_PATH = "pre_execution_audit_path"
GATE_PRE_EXECUTION_AUDIT_SERIALIZATION = "pre_execution_audit_serialization"
GATE_PRE_EXECUTION_AUDIT_WRITE = "pre_execution_audit_write"
GATE_PRE_EXECUTION_AUDIT_ID = "pre_execution_audit_id"
GATE_HANDLER_LOOKUP = "handler_lookup"
GATE_DISPATCH = "dispatch"
GATE_EXECUTION = "execution"


# ---------------------------------------------------------------------------
# 3. Required fields for audit package
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "recordType",
        "schemaVersion",
        "eventType",
        "preExecutionAuditId",
        "executeRequestId",
        "dryRunRequestId",
        "dryRunDecisionDigest",
        "canonicalName",
        "riskTier",
        "policyVersion",
        "argumentsDigest",
        "redactionVersion",
        "auditEventId",
        "confirmationTokenId",
        "digestAlgorithm",
        "digestPackageVersion",
        "canonicalizationVersion",
        "historicalDigest",
        "tokenBoundDigest",
        "executeDerivedDigest",
        "gateStatus",
        "sideEffectFlags",
        "createdAt",
        "status",
    }
)


# ---------------------------------------------------------------------------
# 4. Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PreExecutionAuditPackageResult:
    """Immutable result of pre-execution audit package building."""

    success: bool
    audit_package: dict[str, Any] | None
    pre_execution_audit_id: str | None
    execute_request_id: str | None
    error_code: str | None


@dataclass(frozen=True, slots=True)
class PreExecutionAuditWriteResult:
    """Immutable result of pre-execution audit JSONL write."""

    written: bool
    pre_execution_audit_id: str | None
    execute_request_id: str | None
    error_code: str | None
    decision: str | None
    gate: str | None
    safe_summary: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 5. Internal helpers
# ---------------------------------------------------------------------------


def _is_relative_to(child: Path, parent: Path) -> bool:
    """Check if *child* path is inside or equal to *parent* path.

    Uses ``Path.relative_to()`` for proper path containment semantics.
    """
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _pre_execution_audit_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def _generate_pre_execution_audit_id() -> str:
    """Generate a unique pre-execution audit ID.

    Format: ``pea_`` + base64url-safe random string.
    The ID is not an authorization credential — it is only for correlation.
    It never contains raw token, full tokenHash, or secrets.
    """
    return f"{PRE_EXECUTION_AUDIT_ID_PREFIX}{secrets.token_urlsafe(_ID_RANDOM_BYTES)}"


def _generate_execute_request_id() -> str:
    """Generate a unique execute request ID.

    Format: ``exe_`` + base64url-safe random string.
    The ID is not an authorization credential — it is only for correlation.
    It never contains raw token, full tokenHash, or secrets.
    """
    return f"{EXECUTE_REQUEST_ID_PREFIX}{secrets.token_urlsafe(_ID_RANDOM_BYTES)}"


def _validate_required_fields(package: dict[str, Any]) -> str | None:
    """Validate that all required fields are present and non-None.

    Returns error_code if any required field is missing or None, else None.
    """
    for key in sorted(_REQUIRED_FIELDS):
        if key not in package or package[key] is None:
            return ERROR_PRE_EXECUTION_AUDIT_MISSING_REQUIRED_FIELD
    return None


def _build_side_effect_flags() -> dict[str, bool]:
    """Build side-effect flags — all always false."""
    return {
        "executionAllowed": False,
        "dispatchAllowed": False,
        "providerSchemaAllowed": False,
        "toolHandlerCalled": False,
        "providerApiCalled": False,
        "executionStarted": False,
    }


def _build_gate_status(
    *,
    pre_execution_audit_status: str = "written",
) -> dict[str, str]:
    """Build gate status map for pre-execution audit event."""
    return {
        "killSwitch": "passed",
        "allowlist": "passed",
        "dryRunLookup": "passed",
        "confirmationToken": "passed",
        "digestVerification": "passed",
        "preExecutionAudit": pre_execution_audit_status,
        # At pre-execution audit write time, handler lookup / dispatch /
        # handler call are downstream gates not yet evaluated. They are now
        # enabled (Phases 1G-04-26 .. 1G-04-29); the earlier
        # "blocked_not_enabled" label was stale metadata only and never
        # affected the response path.
        "handlerLookup": "pending",
        "dispatch": "pending",
        "toolHandlerCall": "pending",
    }


def _fail_closed(
    *,
    error_code: str,
    decision: str,
    gate: str,
) -> PreExecutionAuditWriteResult:
    """Return a fail-closed write result — never an unhandled exception."""
    return PreExecutionAuditWriteResult(
        written=False,
        pre_execution_audit_id=None,
        execute_request_id=None,
        error_code=error_code,
        decision=decision,
        gate=gate,
    )


def _canonical_json_line(event: dict[str, Any]) -> str | None:
    """Serialize an event to a canonical JSON line.

    Returns None on serialization failure.
    """
    try:
        return json.dumps(
            event,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 6. Path guard
# ---------------------------------------------------------------------------


def get_pre_execution_audit_store_path(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, Path, str | None]:
    """Resolve and validate the pre-execution audit store path.

    Returns (audit_dir, audit_file, error_code_or_none).

    Guarantees:
      - HERMES_HOME must not equal production home
      - HERMES_HOME must not be inside production subtree
      - Resolved audit_dir must be inside $HERMES_HOME/gateway/dev/audit
      - Resolved audit_file must be inside $HERMES_HOME/gateway/dev/audit
      - Resolved audit_dir/file must not be inside ~/.hermes
      - Symlink / path traversal into production is blocked
      - No file is opened if any containment check fails
      - Path containment uses Path.relative_to(), not string prefix
    """
    if hermes_home is not None:
        home = Path(hermes_home).resolve()
    else:
        home_str = os.environ.get("HERMES_HOME", "")
        if not home_str:
            return Path(), Path(), ERROR_PRE_EXECUTION_AUDIT_UNAVAILABLE
        home = Path(home_str).resolve()

    prod_home = Path(_PRODUCTION_HERMES_HOME).resolve()

    # Block exact production home
    if home == prod_home:
        return Path(), Path(), ERROR_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN

    # Block inside production subtree
    if _is_relative_to(home, prod_home):
        return Path(), Path(), ERROR_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN

    # Build audit dir and file paths
    audit_dir = home / _AUDIT_DIR_RELATIVE
    audit_file = audit_dir / PRE_EXECUTION_AUDIT_FILENAME

    resolved_dir = audit_dir.resolve()
    resolved_file = audit_file.resolve()

    # Block if resolved dir is production home or inside production subtree
    if resolved_dir == prod_home or _is_relative_to(resolved_dir, prod_home):
        return Path(), Path(), ERROR_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN

    # Block if resolved file is production home or inside production subtree
    if resolved_file == prod_home or _is_relative_to(resolved_file, prod_home):
        return Path(), Path(), ERROR_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN

    # Validate audit dir is inside expected path under home
    expected_dir = (home / _AUDIT_DIR_RELATIVE).resolve()
    if not _is_relative_to(resolved_dir, expected_dir):
        return Path(), Path(), ERROR_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN

    # Validate audit file is inside audit dir
    if not _is_relative_to(resolved_file, resolved_dir):
        return Path(), Path(), ERROR_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN

    return audit_dir, audit_file, None


def validate_pre_execution_audit_path(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[bool, str | None]:
    """Validate pre-execution audit store path without opening the file.

    Returns (is_valid, error_code_or_none).
    """
    _, _, error = get_pre_execution_audit_store_path(hermes_home)
    if error is not None:
        return False, error
    return True, None


# ---------------------------------------------------------------------------
# 7. Audit package builder
# ---------------------------------------------------------------------------


def build_pre_execution_audit_package(
    *,
    dry_run_request_id: str,
    dry_run_decision_digest: str,
    canonical_name: str,
    risk_tier: str | None,
    policy_version: str | None = None,
    arguments_digest: str | None = None,
    redaction_version: str | None = None,
    audit_event_id: str | None = None,
    confirmation_token_id: str | None = None,
    confirmation_issued_at: str | None = None,
    confirmation_consumed_at: str | None = None,
    digest_algorithm: str = "sha256",
    digest_package_version: str = "1",
    canonicalization_version: str = "json-sort-v1",
    historical_digest: str | None = None,
    token_bound_digest: str | None = None,
    execute_derived_digest: str | None = None,
) -> PreExecutionAuditPackageResult:
    """Build a pre-execution audit package from safe execute context fields.

    The package contains only safe, deterministic fields.
    It never contains raw token, full tokenHash, raw arguments, or secrets.

    Returns:
        PreExecutionAuditPackageResult with the built package and IDs.
    """
    pre_execution_audit_id = _generate_pre_execution_audit_id()
    execute_request_id = _generate_execute_request_id()
    now = _pre_execution_audit_now()

    package: dict[str, Any] = {
        "recordType": PRE_EXECUTION_AUDIT_RECORD_TYPE,
        "schemaVersion": PRE_EXECUTION_AUDIT_SCHEMA_VERSION,
        "eventType": PRE_EXECUTION_AUDIT_EVENT_TYPE,
        "preExecutionAuditId": pre_execution_audit_id,
        "executeRequestId": execute_request_id,
        "dryRunRequestId": dry_run_request_id,
        "dryRunDecisionDigest": dry_run_decision_digest,
        "canonicalName": canonical_name,
        "riskTier": risk_tier or "unknown",
        "policyVersion": policy_version or "dev-v1",
        "argumentsDigest": arguments_digest or "sha256:unknown",
        "redactionVersion": redaction_version or "sanitize-v1",
        "auditEventId": audit_event_id,
        "confirmationTokenId": confirmation_token_id or "ctok_unknown",
        "digestAlgorithm": digest_algorithm,
        "digestPackageVersion": digest_package_version,
        "canonicalizationVersion": canonicalization_version,
        "historicalDigest": historical_digest or "sha256:unavailable",
        "tokenBoundDigest": token_bound_digest or "sha256:unavailable",
        "executeDerivedDigest": execute_derived_digest or "sha256:unavailable",
        "gateStatus": _build_gate_status(),
        "sideEffectFlags": _build_side_effect_flags(),
        "createdAt": now.isoformat(),
        "status": "written",
    }

    # Optional fields
    if confirmation_issued_at is not None:
        package["confirmationIssuedAt"] = confirmation_issued_at
    if confirmation_consumed_at is not None:
        package["confirmationConsumedAt"] = confirmation_consumed_at

    # Validate required fields
    validation_error = _validate_required_fields(package)
    if validation_error is not None:
        return PreExecutionAuditPackageResult(
            success=False,
            audit_package=None,
            pre_execution_audit_id=None,
            execute_request_id=None,
            error_code=validation_error,
        )

    return PreExecutionAuditPackageResult(
        success=True,
        audit_package=package,
        pre_execution_audit_id=pre_execution_audit_id,
        execute_request_id=execute_request_id,
        error_code=None,
    )


# ---------------------------------------------------------------------------
# 8. JSONL writer
# ---------------------------------------------------------------------------


def write_pre_execution_audit_event(
    *,
    hermes_home: str | os.PathLike[str] | None = None,
    audit_package: dict[str, Any],
) -> PreExecutionAuditWriteResult:
    """Write a pre-execution audit event to the dev-only JSONL store.

    This function is dev-only. It:
      - Validates the audit store path (containment-based guard)
      - Serializes the audit package to canonical JSON
      - Appends a single JSON line to the JSONL store
      - Returns safe result with preExecutionAuditId and executeRequestId

    It does NOT:
      - Call tool handlers
      - Dispatch tools
      - Call providers
      - Access ~/.hermes
      - Expose raw token, full tokenHash, raw arguments, or secrets

    Args:
        hermes_home: HERMES_HOME path override.
        audit_package: The pre-built audit package dict.

    Returns:
        PreExecutionAuditWriteResult with written status and safe IDs.
    """
    # Gate 38: Pre-execution audit package available
    if not audit_package or not isinstance(audit_package, dict):
        return _fail_closed(
            error_code=ERROR_PRE_EXECUTION_AUDIT_INVALID_STATE,
            decision=DECISION_BLOCKED_PRE_EXECUTION_AUDIT_INVALID_STATE,
            gate=GATE_PRE_EXECUTION_AUDIT_PACKAGE,
        )

    # Extract IDs from package
    pre_execution_audit_id = audit_package.get("preExecutionAuditId")
    execute_request_id = audit_package.get("executeRequestId")

    # Gate 39: Pre-execution audit path guard passes
    audit_dir, audit_file, path_error = get_pre_execution_audit_store_path(
        hermes_home
    )
    if path_error is not None:
        return _fail_closed(
            error_code=path_error,
            decision=DECISION_BLOCKED_PRE_EXECUTION_AUDIT_PATH_FORBIDDEN,
            gate=GATE_PRE_EXECUTION_AUDIT_PATH,
        )

    # Gate 40: Pre-execution audit serialization succeeds
    json_line = _canonical_json_line(audit_package)
    if json_line is None:
        return _fail_closed(
            error_code=ERROR_PRE_EXECUTION_AUDIT_SERIALIZATION_FAILED,
            decision=DECISION_BLOCKED_PRE_EXECUTION_AUDIT_SERIALIZATION_FAILED,
            gate=GATE_PRE_EXECUTION_AUDIT_SERIALIZATION,
        )

    # Check line size
    line_bytes = (json_line + "\n").encode("utf-8")
    if len(line_bytes) > _MAX_LINE_BYTES:
        return _fail_closed(
            error_code=ERROR_PRE_EXECUTION_AUDIT_SERIALIZATION_FAILED,
            decision=DECISION_BLOCKED_PRE_EXECUTION_AUDIT_SERIALIZATION_FAILED,
            gate=GATE_PRE_EXECUTION_AUDIT_SERIALIZATION,
        )

    # Gate 41: Pre-execution audit write succeeds
    try:
        audit_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _fail_closed(
            error_code=ERROR_PRE_EXECUTION_AUDIT_WRITE_FAILED,
            decision=DECISION_BLOCKED_PRE_EXECUTION_AUDIT_WRITE_FAILED,
            gate=GATE_PRE_EXECUTION_AUDIT_WRITE,
        )

    try:
        with audit_file.open("a", encoding="utf-8") as f:
            f.write(json_line)
            f.write("\n")
    except OSError:
        return _fail_closed(
            error_code=ERROR_PRE_EXECUTION_AUDIT_WRITE_FAILED,
            decision=DECISION_BLOCKED_PRE_EXECUTION_AUDIT_WRITE_FAILED,
            gate=GATE_PRE_EXECUTION_AUDIT_WRITE,
        )

    # Gate 42: Pre-execution audit ID returned
    # Gate 43: Block because handler lookup is not enabled
    # Gate 44: Dispatch still disabled
    # Gate 45: Execution still disabled
    return PreExecutionAuditWriteResult(
        written=True,
        pre_execution_audit_id=pre_execution_audit_id,
        execute_request_id=execute_request_id,
        error_code=ERROR_PRE_EXECUTION_AUDIT_WRITTEN_BUT_HANDLER_LOOKUP_NOT_ENABLED,
        decision=DECISION_BLOCKED_HANDLER_LOOKUP_NOT_ENABLED,
        gate=GATE_HANDLER_LOOKUP,
        safe_summary=safe_pre_execution_audit_summary(
            pre_execution_audit_id, execute_request_id
        ),
    )


# ---------------------------------------------------------------------------
# 9. Safe summary
# ---------------------------------------------------------------------------


def safe_pre_execution_audit_summary(
    pre_execution_audit_id: str | None,
    execute_request_id: str | None,
) -> dict[str, Any]:
    """Build a safe summary from pre-execution audit result.

    Never exposes raw token, full tokenHash, raw arguments, or secrets.
    """
    return {
        "preExecutionAuditId": pre_execution_audit_id,
        "executeRequestId": execute_request_id,
        "preExecutionAuditStatus": "written" if pre_execution_audit_id else None,
    }
