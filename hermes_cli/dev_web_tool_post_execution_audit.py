"""Post-Execution Audit for the Hermes Dev WebUI Tool Execute Gate.

This module implements minimal post-execution audit writing for the
clarify-only controlled execution path.  It builds an audit event from the
safe execution context (after a successful clarify handler call), validates
the dev-only audit store path, and writes an append-only JSONL record.

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider imports, no tool handler imports, no dispatch imports
  - no network IO, no runtime state mutation outside audit JSONL
  - no STATIC_ALLOWLIST mutation
  - deterministic, JSON-serializable output
  - never stores raw confirmationToken
  - never stores full tokenHash
  - never stores raw arguments (only a safe result summary)
  - never stores secrets
  - never calls handler / dispatch / provider
  - post-execution audit is REQUIRED for a successful controlled execution
  - post-execution audit write failure FAILS CLOSED — no success response

Phase: 1G-04-29 — Clarify-only Handler Call + Post-execution Audit
Status: append-only JSONL post-execution audit implemented, fail-closed
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

POST_EXECUTION_AUDIT_SCHEMA_VERSION = 1
POST_EXECUTION_AUDIT_RECORD_TYPE = "tool_post_execution_audit"
POST_EXECUTION_AUDIT_EVENT_TYPE = "clarify_execution_completed"
POST_EXECUTION_AUDIT_FILENAME = "tool-post-execution-audit.jsonl"
POST_EXECUTION_AUDIT_ID_PREFIX = "pexa_"

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

ERROR_POST_EXECUTION_AUDIT_UNAVAILABLE = "post_execution_audit_unavailable"
ERROR_POST_EXECUTION_AUDIT_PATH_FORBIDDEN = "post_execution_audit_path_forbidden"
ERROR_POST_EXECUTION_AUDIT_WRITE_FAILED = "post_execution_audit_write_failed"
ERROR_POST_EXECUTION_AUDIT_INVALID_STATE = "post_execution_audit_invalid_state"
ERROR_POST_EXECUTION_AUDIT_MISSING_REQUIRED_FIELD = (
    "post_execution_audit_missing_required_field"
)
ERROR_POST_EXECUTION_AUDIT_SERIALIZATION_FAILED = (
    "post_execution_audit_serialization_failed"
)

DECISION_BLOCKED_POST_EXECUTION_AUDIT_UNAVAILABLE = (
    "blocked_post_execution_audit_unavailable"
)
DECISION_BLOCKED_POST_EXECUTION_AUDIT_PATH_FORBIDDEN = (
    "blocked_post_execution_audit_path_forbidden"
)
DECISION_BLOCKED_POST_EXECUTION_AUDIT_WRITE_FAILED = (
    "blocked_post_execution_audit_write_failed"
)
DECISION_BLOCKED_POST_EXECUTION_AUDIT_INVALID_STATE = (
    "blocked_post_execution_audit_invalid_state"
)
DECISION_BLOCKED_POST_EXECUTION_AUDIT_MISSING_REQUIRED_FIELD = (
    "blocked_post_execution_audit_missing_required_field"
)
DECISION_BLOCKED_POST_EXECUTION_AUDIT_SERIALIZATION_FAILED = (
    "blocked_post_execution_audit_serialization_failed"
)
DECISION_BLOCKED_POST_EXECUTION_AUDIT_FAILED = "blocked_post_execution_audit_failed"

# Gate constants
GATE_POST_EXECUTION_AUDIT_PACKAGE = "post_execution_audit_package"
GATE_POST_EXECUTION_AUDIT_PATH = "post_execution_audit_path"
GATE_POST_EXECUTION_AUDIT_SERIALIZATION = "post_execution_audit_serialization"
GATE_POST_EXECUTION_AUDIT_WRITE = "post_execution_audit_write"
GATE_POST_EXECUTION_AUDIT_ID = "post_execution_audit_id"


# ---------------------------------------------------------------------------
# 3. Required fields for audit package
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "recordType",
        "schemaVersion",
        "eventType",
        "postExecutionAuditId",
        "executeRequestId",
        "preExecutionAuditId",
        "handlerLookupId",
        "dispatchId",
        "handlerCallId",
        "canonicalName",
        "executionStatus",
        "handlerCallStatus",
        "dryRunDecisionDigest",
        "confirmationTokenId",
        "digestAlgorithm",
        "sideEffectFlags",
        "resultSummary",
        "gateStatus",
        "createdAt",
        "status",
    }
)


# ---------------------------------------------------------------------------
# 4. Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PostExecutionAuditPackageResult:
    """Immutable result of post-execution audit package building."""

    success: bool
    audit_package: dict[str, Any] | None
    post_execution_audit_id: str | None
    error_code: str | None


@dataclass(frozen=True, slots=True)
class PostExecutionAuditWriteResult:
    """Immutable result of post-execution audit JSONL write.

    When ``written`` is False, the controlled execution MUST fail closed — no
    success response may be returned to the caller.
    """

    written: bool
    post_execution_audit_id: str | None
    error_code: str | None
    decision: str | None
    gate: str | None
    safe_summary: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 5. Internal helpers
# ---------------------------------------------------------------------------


def _is_relative_to(child: Path, parent: Path) -> bool:
    """Check if *child* path is inside or equal to *parent* path."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _post_execution_audit_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def _generate_post_execution_audit_id() -> str:
    """Generate a unique post-execution audit ID.

    Format: ``pexa_`` + base64url-safe random string.
    The ID is not an authorization credential — it is only for correlation.
    It never contains raw token, full tokenHash, or secrets.
    """
    return f"{POST_EXECUTION_AUDIT_ID_PREFIX}{secrets.token_urlsafe(_ID_RANDOM_BYTES)}"


def _validate_required_fields(package: dict[str, Any]) -> str | None:
    """Validate that all required fields are present and non-None."""
    for key in sorted(_REQUIRED_FIELDS):
        if key not in package or package[key] is None:
            return ERROR_POST_EXECUTION_AUDIT_MISSING_REQUIRED_FIELD
    return None


def _build_side_effect_flags() -> dict[str, bool]:
    """Build side-effect flags — all always false.

    Clarify controlled execution is side-effect-free: no provider, no
    filesystem change, no network call, no external side effects.
    """
    return {
        "externalSideEffects": False,
        "providerSchemaSent": False,
        "providerApiCalled": False,
        "filesystemChanged": False,
        "networkCalled": False,
    }


def _build_gate_status() -> dict[str, str]:
    """Build gate status map for the post-execution audit event."""
    return {
        "killSwitch": "passed",
        "allowlist": "passed",
        "dryRunLookup": "passed",
        "confirmationToken": "passed",
        "digestVerification": "passed",
        "preExecutionAudit": "written",
        "handlerLookup": "found",
        "dispatch": "planned",
        "toolHandlerCall": "completed",
        "postExecutionAudit": "written",
    }


def _build_result_summary(tool_result: dict[str, Any] | None) -> dict[str, Any]:
    """Build a SAFE result summary — no raw arguments, no message content.

    Only structural metadata is recorded: the tool result type, message length,
    question count, and (Phase 2A) the structured-result size in bytes. This
    complies with the "no raw arguments in audit" invariant and works for both
    the clarify shape (message + questions) and the Phase 2A read-only shape
    (message + structured result).
    """
    summary: dict[str, Any] = {
        "toolResultType": None,
        "messageLength": 0,
        "questionCount": 0,
        "resultSizeBytes": 0,
    }
    if isinstance(tool_result, dict):
        summary["toolResultType"] = tool_result.get("type")
        message = tool_result.get("message")
        if isinstance(message, str):
            summary["messageLength"] = len(message)
        questions = tool_result.get("questions")
        if isinstance(questions, list):
            summary["questionCount"] = len(questions)
        # Phase 2A: record the serialized size of the structured result. The
        # structured result itself is NEVER stored (no raw arguments); only
        # its byte length, for observability.
        result_body = tool_result.get("result")
        if result_body is not None:
            try:
                summary["resultSizeBytes"] = len(
                    json.dumps(result_body, ensure_ascii=False)
                )
            except (TypeError, ValueError):
                summary["resultSizeBytes"] = 0
    return summary


def _fail_closed(
    *,
    error_code: str,
    decision: str,
    gate: str,
) -> PostExecutionAuditWriteResult:
    """Return a fail-closed write result — never an unhandled exception."""
    return PostExecutionAuditWriteResult(
        written=False,
        post_execution_audit_id=None,
        error_code=error_code,
        decision=decision,
        gate=gate,
    )


def _canonical_json_line(event: dict[str, Any]) -> str | None:
    """Serialize an event to a canonical JSON line. Returns None on failure."""
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


def get_post_execution_audit_store_path(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, Path, str | None]:
    """Resolve and validate the post-execution audit store path.

    Returns (audit_dir, audit_file, error_code_or_none).

    Guarantees (mirrors pre-execution audit path guard):
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
            return Path(), Path(), ERROR_POST_EXECUTION_AUDIT_UNAVAILABLE
        home = Path(home_str).resolve()

    prod_home = Path(_PRODUCTION_HERMES_HOME).resolve()

    # Block exact production home
    if home == prod_home:
        return Path(), Path(), ERROR_POST_EXECUTION_AUDIT_PATH_FORBIDDEN

    # Block inside production subtree
    if _is_relative_to(home, prod_home):
        return Path(), Path(), ERROR_POST_EXECUTION_AUDIT_PATH_FORBIDDEN

    # Build audit dir and file paths
    audit_dir = home / _AUDIT_DIR_RELATIVE
    audit_file = audit_dir / POST_EXECUTION_AUDIT_FILENAME

    resolved_dir = audit_dir.resolve()
    resolved_file = audit_file.resolve()

    # Block if resolved dir is production home or inside production subtree
    if resolved_dir == prod_home or _is_relative_to(resolved_dir, prod_home):
        return Path(), Path(), ERROR_POST_EXECUTION_AUDIT_PATH_FORBIDDEN

    # Block if resolved file is production home or inside production subtree
    if resolved_file == prod_home or _is_relative_to(resolved_file, prod_home):
        return Path(), Path(), ERROR_POST_EXECUTION_AUDIT_PATH_FORBIDDEN

    # Validate audit dir is inside expected path under home
    expected_dir = (home / _AUDIT_DIR_RELATIVE).resolve()
    if not _is_relative_to(resolved_dir, expected_dir):
        return Path(), Path(), ERROR_POST_EXECUTION_AUDIT_PATH_FORBIDDEN

    # Validate audit file is inside audit dir
    if not _is_relative_to(resolved_file, resolved_dir):
        return Path(), Path(), ERROR_POST_EXECUTION_AUDIT_PATH_FORBIDDEN

    return audit_dir, audit_file, None


def validate_post_execution_audit_path(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[bool, str | None]:
    """Validate post-execution audit store path without opening the file."""
    _, _, error = get_post_execution_audit_store_path(hermes_home)
    if error is not None:
        return False, error
    return True, None


# ---------------------------------------------------------------------------
# 7. Audit package builder
# ---------------------------------------------------------------------------


def build_post_execution_audit_package(
    *,
    execute_request_id: str,
    pre_execution_audit_id: str,
    handler_lookup_id: str,
    dispatch_id: str,
    handler_call_id: str,
    canonical_name: str,
    execution_status: str,
    handler_call_status: str,
    dry_run_decision_digest: str | None = None,
    confirmation_token_id: str | None = None,
    digest_algorithm: str = "sha256",
    tool_result: dict[str, Any] | None = None,
) -> PostExecutionAuditPackageResult:
    """Build a post-execution audit package from safe execution context fields.

    The package contains only safe, deterministic fields and a SAFE result
    summary (type + counts).  It never contains raw token, full tokenHash,
    raw arguments, raw message content, or secrets.
    """
    post_execution_audit_id = _generate_post_execution_audit_id()
    now = _post_execution_audit_now()

    package: dict[str, Any] = {
        "recordType": POST_EXECUTION_AUDIT_RECORD_TYPE,
        "schemaVersion": POST_EXECUTION_AUDIT_SCHEMA_VERSION,
        "eventType": POST_EXECUTION_AUDIT_EVENT_TYPE,
        "postExecutionAuditId": post_execution_audit_id,
        "executeRequestId": execute_request_id,
        "preExecutionAuditId": pre_execution_audit_id,
        "handlerLookupId": handler_lookup_id,
        "dispatchId": dispatch_id,
        "handlerCallId": handler_call_id,
        "canonicalName": canonical_name,
        "executionStatus": execution_status,
        "handlerCallStatus": handler_call_status,
        "dryRunDecisionDigest": dry_run_decision_digest or "sha256:unavailable",
        "confirmationTokenId": confirmation_token_id or "ctok_unknown",
        "digestAlgorithm": digest_algorithm,
        "sideEffectFlags": _build_side_effect_flags(),
        "resultSummary": _build_result_summary(tool_result),
        "gateStatus": _build_gate_status(),
        "createdAt": now.isoformat(),
        "status": "written",
    }

    # Validate required fields
    validation_error = _validate_required_fields(package)
    if validation_error is not None:
        return PostExecutionAuditPackageResult(
            success=False,
            audit_package=None,
            post_execution_audit_id=None,
            error_code=validation_error,
        )

    return PostExecutionAuditPackageResult(
        success=True,
        audit_package=package,
        post_execution_audit_id=post_execution_audit_id,
        error_code=None,
    )


# ---------------------------------------------------------------------------
# 8. JSONL writer
# ---------------------------------------------------------------------------


def write_post_execution_audit_event(
    *,
    hermes_home: str | os.PathLike[str] | None = None,
    audit_package: dict[str, Any],
) -> PostExecutionAuditWriteResult:
    """Write a post-execution audit event to the dev-only JSONL store.

    This function is dev-only. It:
      - Validates the audit store path (containment-based guard)
      - Serializes the audit package to canonical JSON
      - Appends a single JSON line to the JSONL store
      - Returns safe result with postExecutionAuditId

    On ANY failure it returns written=False (fail-closed). A successful
    controlled execution response requires written=True.

    It does NOT:
      - Call tool handlers / dispatch / providers
      - Access ~/.hermes
      - Expose raw token, full tokenHash, raw arguments, or secrets
    """
    # Gate 80: Post-execution audit package available
    if not audit_package or not isinstance(audit_package, dict):
        return _fail_closed(
            error_code=ERROR_POST_EXECUTION_AUDIT_INVALID_STATE,
            decision=DECISION_BLOCKED_POST_EXECUTION_AUDIT_INVALID_STATE,
            gate=GATE_POST_EXECUTION_AUDIT_PACKAGE,
        )

    # Extract ID from package
    post_execution_audit_id = audit_package.get("postExecutionAuditId")

    # Gate 81: Post-execution audit path guard passes
    audit_dir, audit_file, path_error = get_post_execution_audit_store_path(
        hermes_home
    )
    if path_error is not None:
        return _fail_closed(
            error_code=path_error,
            decision=DECISION_BLOCKED_POST_EXECUTION_AUDIT_PATH_FORBIDDEN,
            gate=GATE_POST_EXECUTION_AUDIT_PATH,
        )

    # Gate 82a: Post-execution audit serialization succeeds
    json_line = _canonical_json_line(audit_package)
    if json_line is None:
        return _fail_closed(
            error_code=ERROR_POST_EXECUTION_AUDIT_SERIALIZATION_FAILED,
            decision=DECISION_BLOCKED_POST_EXECUTION_AUDIT_SERIALIZATION_FAILED,
            gate=GATE_POST_EXECUTION_AUDIT_SERIALIZATION,
        )

    # Check line size
    line_bytes = (json_line + "\n").encode("utf-8")
    if len(line_bytes) > _MAX_LINE_BYTES:
        return _fail_closed(
            error_code=ERROR_POST_EXECUTION_AUDIT_SERIALIZATION_FAILED,
            decision=DECISION_BLOCKED_POST_EXECUTION_AUDIT_SERIALIZATION_FAILED,
            gate=GATE_POST_EXECUTION_AUDIT_SERIALIZATION,
        )

    # Gate 82b: Post-execution audit write succeeds (fail-closed on error)
    try:
        audit_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return _fail_closed(
            error_code=ERROR_POST_EXECUTION_AUDIT_WRITE_FAILED,
            decision=DECISION_BLOCKED_POST_EXECUTION_AUDIT_WRITE_FAILED,
            gate=GATE_POST_EXECUTION_AUDIT_WRITE,
        )

    try:
        with audit_file.open("a", encoding="utf-8") as f:
            f.write(json_line)
            f.write("\n")
    except OSError:
        return _fail_closed(
            error_code=ERROR_POST_EXECUTION_AUDIT_WRITE_FAILED,
            decision=DECISION_BLOCKED_POST_EXECUTION_AUDIT_WRITE_FAILED,
            gate=GATE_POST_EXECUTION_AUDIT_WRITE,
        )

    # Gate 83: Post-execution audit ID returned
    return PostExecutionAuditWriteResult(
        written=True,
        post_execution_audit_id=post_execution_audit_id,
        error_code=None,
        decision=None,
        gate=None,
        safe_summary=safe_post_execution_audit_summary(post_execution_audit_id),
    )


# ---------------------------------------------------------------------------
# 9. Safe summary
# ---------------------------------------------------------------------------


def safe_post_execution_audit_summary(
    post_execution_audit_id: str | None,
) -> dict[str, Any]:
    """Build a safe summary from post-execution audit result.

    Never exposes raw token, full tokenHash, raw arguments, or secrets.
    """
    return {
        "postExecutionAuditId": post_execution_audit_id,
        "postExecutionAuditStatus": "written" if post_execution_audit_id else None,
    }
