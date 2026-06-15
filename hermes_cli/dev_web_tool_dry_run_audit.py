"""Tool Dry-Run Audit Writer for the Hermes Dev WebUI.

This module implements a local dev-only JSONL audit writer that records
Dry-Run API decision results to a file under HERMES_HOME.

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider imports, no tool handler imports, no dispatch imports
  - no frontend imports, no network IO
  - only local file append under HERMES_HOME dev audit path
  - never accesses ~/.hermes
  - never accesses production state.db
  - never stores raw arguments or raw secrets
  - never calls tool handlers, providers, or dispatch
  - never mutates STATIC_ALLOWLIST
  - never executes any tool
  - all public data structures JSON-safe
  - all exceptions handled safely

Phase: 1G-04-07 — Internal Audit Writer
Status: Internal module (no API, no OpenAPI, no frontend)
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

# Event metadata
_EVENT_TYPE = "tool_dry_run"
_SCHEMA_VERSION = 1
_PHASE = "1G-04-07"

# Storage path components
_AUDIT_DIR_RELATIVE = "gateway/dev/audit"
_AUDIT_FILENAME = "tool-dry-run-audit.jsonl"

# Size limits
_MAX_EVENT_BYTES = 32 * 1024  # 32 KiB
_MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MiB
_MAX_RETAINED_FILES = 3  # current + 2 rotated copies

# Forbidden production paths (never write here)
_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"

# Secret value patterns for defensive re-check
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
)

# Forbidden field name stems (normalized for matching)
_FORBIDDEN_FIELD_STEMS: frozenset[str] = frozenset(
    n.replace("_", "").replace("-", "").lower()
    for n in (
        "api_key", "apikey", "authorization", "auth_header", "bearer",
        "token", "secret", "password", "passwd", "credential", "cookie",
        "session", "private_key", "client_secret", "access_token",
        "refresh_token", "access_key",
    )
)


def _live_static_allowlist_size() -> int:
    """Return the live ``len(STATIC_ALLOWLIST)`` for forensic accuracy.

    Lazy import keeps this writer free of a module-level policy dependency.
    On any import failure, returns 0 (fail-safe; never raises).
    """
    try:
        from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

        return len(STATIC_ALLOWLIST)
    except Exception:
        return 0

# Error codes
ERROR_HERMES_HOME_MISSING = "HERMES_HOME_MISSING"
ERROR_AUDIT_PATH_OUTSIDE_HERMES_HOME = "AUDIT_PATH_OUTSIDE_HERMES_HOME"
ERROR_AUDIT_EVENT_TOO_LARGE = "AUDIT_EVENT_TOO_LARGE"
ERROR_AUDIT_WRITE_FAILED = "AUDIT_WRITE_FAILED"
ERROR_AUDIT_ROTATION_FAILED = "AUDIT_ROTATION_FAILED"
ERROR_AUDIT_SERIALIZATION_FAILED = "AUDIT_SERIALIZATION_FAILED"
ERROR_AUDIT_REDACTION_FAILED = "AUDIT_REDACTION_FAILED"


# ---------------------------------------------------------------------------
# 2. Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DryRunAuditWriteResult:
    """Immutable result of an audit write attempt.

    Attributes:
        written: Whether the audit event was successfully written.
        path: The file path written to, or None.
        event_id: The event UUID, or None.
        error_code: Error code if write failed, or None.
        error_message: Human-readable error message, or None.
        rotated: Whether a file rotation occurred during this write.
        retained_files: Number of retained files after write attempt.
    """

    written: bool
    path: str | None
    event_id: str | None
    error_code: str | None
    error_message: str | None
    rotated: bool
    retained_files: int


# ---------------------------------------------------------------------------
# 3. Defensive sanitization helpers
# ---------------------------------------------------------------------------


def _normalize_field_name(name: str) -> str:
    """Normalize a field name for comparison."""
    return name.replace("_", "").replace("-", "").lower()


def _is_secret_value(value: str) -> bool:
    """Check if a string value matches known secret patterns."""
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.search(value):
            return True
    return False


def _is_forbidden_field(key: str) -> bool:
    """Check if a field name is a forbidden secret-like key."""
    return _normalize_field_name(key) in _FORBIDDEN_FIELD_STEMS


def _sanitize_event_value(value: Any, path: str = "", depth: int = 0) -> Any:
    """Defensively sanitize a value for audit storage.

    This is a secondary defense layer — the primary redaction is done by
    sanitize_arguments_preview() before data reaches the audit writer.
    """
    if depth > 6:
        return "[truncated: depth exceeded]"

    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value

    if isinstance(value, str):
        # Check for secret value patterns
        if _is_secret_value(value):
            return "[REDACTED]"
        # Truncate overly long strings
        if len(value) > 200:
            return value[:200] + "…"
        return value

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for k, v in value.items():
            if _is_forbidden_field(k):
                result[k] = "[REDACTED]"
            else:
                result[k] = _sanitize_event_value(
                    v, path=f"{path}.{k}", depth=depth + 1
                )
        return result

    if isinstance(value, (list, tuple)):
        return [
            _sanitize_event_value(
                item, path=f"{path}[{i}]", depth=depth + 1
            )
            for i, item in enumerate(value)
        ]

    # Unknown type → safe string representation
    try:
        s = str(value)
        if len(s) > 200:
            return s[:200] + "…"
        return s
    except Exception:
        return "[unsupported type]"


def _sanitize_event(event: dict[str, Any]) -> dict[str, Any]:
    """Sanitize an entire audit event for safe storage.

    Applies defensive redaction to all string and nested values.
    """
    try:
        return _sanitize_event_value(event)  # type: ignore[return-value]
    except Exception:
        # If sanitization itself fails, return minimal safe event
        return {
            "eventType": _EVENT_TYPE,
            "error": "Audit event sanitization failed",
            "schemaVersion": _SCHEMA_VERSION,
        }


# ---------------------------------------------------------------------------
# 4. Audit event builder
# ---------------------------------------------------------------------------


def build_dry_run_audit_event(
    *,
    dry_run_result: Any,
    source_context: str | None = None,
    ui_origin: str | None = None,
    request_id: str | None = None,
    duration_ms: int | None = None,
    result_status: str = "ok",
    error_code: str | None = None,
    error_class: str | None = None,
    dry_run_decision_digest: str | None = None,
    digest_algorithm: str | None = None,
    digest_package_version: str | None = None,
    canonicalization_version: str | None = None,
) -> dict[str, Any]:
    """Build a safe audit event from a ToolDryRunResult.

    This function constructs a JSON-safe audit event dict that can be
    written to the local dev audit JSONL file.

    Args:
        dry_run_result: A ToolDryRunResult instance (uses to_safe_dict()).
        source_context: Source context from the request.
        ui_origin: UI origin from the request.
        request_id: Client-provided request correlation ID.
        duration_ms: Dry-run evaluation duration in milliseconds.
        result_status: "ok" or "error".
        error_code: Error code if result was error.
        error_class: Error class if result was error.

    Returns:
        A JSON-safe dict representing the audit event.

    Guarantees:
        - executionAllowed is always False
        - dispatchAllowed is always False
        - providerSchemaAllowed is always False
        - No raw secrets in any field
        - Only redactedArgumentsPreview stored, never raw arguments
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    # Extract safe dict from the dry-run result
    result_dict: dict[str, Any]
    try:
        result_dict = dry_run_result.to_safe_dict()
    except Exception:
        result_dict = {
            "canonicalName": "unknown",
            "exists": False,
            "riskTier": None,
            "decision": "would_block",
            "reasonCodes": [],
            "policyNotes": [],
            "redactedArgumentsPreview": {},
            "forbiddenFields": [],
            "missingRequiredFields": [],
            "executionAllowed": False,
            "dispatchAllowed": False,
            "providerSchemaAllowed": False,
            "auditWritten": False,
        }

    # Determine redaction info from result
    redaction_applied = bool(result_dict.get("forbiddenFields"))
    redaction_reason_codes = [
        code for code in result_dict.get("reasonCodes", [])
        if "REDACT" in code.upper()
    ]

    # Build the event
    event: dict[str, Any] = {
        "eventId": event_id,
        "eventType": _EVENT_TYPE,
        "timestamp": timestamp,
        "schemaVersion": _SCHEMA_VERSION,
        "phase": _PHASE,
        "requestId": request_id,
        "canonicalName": result_dict.get("canonicalName", "unknown"),
        "toolExists": result_dict.get("exists", False),
        "riskTier": result_dict.get("riskTier"),
        "decision": result_dict.get("decision", "would_block"),
        "reasonCodes": result_dict.get("reasonCodes", []),
        "policyNotes": result_dict.get("policyNotes", []),
        "forbiddenFields": result_dict.get("forbiddenFields", []),
        "missingRequiredFields": result_dict.get("missingRequiredFields", []),
        "redactionApplied": redaction_applied,
        "redactionReasonCodes": redaction_reason_codes,
        "redactedArgumentsPreview": result_dict.get(
            "redactedArgumentsPreview", {}
        ),
        "sourceContext": source_context,
        "uiOrigin": ui_origin,
        # Hard invariants: always false
        "executionAllowed": False,
        "dispatchAllowed": False,
        "providerSchemaAllowed": False,
        # auditWritten for this event: will be updated by write_dry_run_audit_event
        "auditWritten": False,
        # Phase 2A: report the live allowlist size for forensic accuracy.
        # Lazy import avoids a module-level dependency on the policy module.
        "staticAllowlistSize": _live_static_allowlist_size(),
        "candidateAllowlistMatched": any(
            "CANDIDATE" in code.upper()
            for code in result_dict.get("reasonCodes", [])
        ),
        "denylistMatched": any(
            "DENYLIST" in code.upper()
            for code in result_dict.get("reasonCodes", [])
        ),
        "durationMs": duration_ms,
        "resultStatus": result_status,
        "errorCode": error_code,
        "errorClass": error_class,
        # Phase 1G-04-22: Digest verification fields
        "dryRunDecisionDigest": dry_run_decision_digest,
        "digestAlgorithm": digest_algorithm,
        "digestPackageVersion": digest_package_version,
        "canonicalizationVersion": canonicalization_version,
    }

    # Defensive: enforce hard invariants
    event["executionAllowed"] = False
    event["dispatchAllowed"] = False
    event["providerSchemaAllowed"] = False

    # Defensive sanitization of the entire event
    event = _sanitize_event(event)

    # Re-enforce hard invariants after sanitization (safety net)
    event["executionAllowed"] = False
    event["dispatchAllowed"] = False
    event["providerSchemaAllowed"] = False

    return event


# ---------------------------------------------------------------------------
# 5. Path resolution and validation
# ---------------------------------------------------------------------------


def _resolve_audit_path(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    """Resolve and validate the audit file path.

    Returns:
        (audit_file_path, error_code_or_none)

    Guarantees:
        - Path is always under HERMES_HOME
        - Path never points to ~/.hermes
        - Path never points to production state.db
    """
    # Resolve HERMES_HOME
    if hermes_home is not None:
        home = Path(hermes_home).resolve()
    else:
        home_str = os.environ.get("HERMES_HOME", "")
        if not home_str:
            return Path(), ERROR_HERMES_HOME_MISSING
        home = Path(home_str).resolve()

    # Reject production path
    prod_home = Path(_PRODUCTION_HERMES_HOME).resolve()
    if home == prod_home:
        return Path(), ERROR_AUDIT_PATH_OUTSIDE_HERMES_HOME

    # Build audit path
    audit_path = home / _AUDIT_DIR_RELATIVE / _AUDIT_FILENAME

    # Validate resolved path is under home
    try:
        audit_path.resolve().relative_to(home)
    except ValueError:
        return Path(), ERROR_AUDIT_PATH_OUTSIDE_HERMES_HOME

    # Reject if path somehow resolves to production state.db
    resolved = audit_path.resolve()
    if str(resolved).endswith("state.db"):
        return Path(), ERROR_AUDIT_PATH_OUTSIDE_HERMES_HOME

    return audit_path, None


# ---------------------------------------------------------------------------
# 6. File rotation
# ---------------------------------------------------------------------------


def _count_retained_files(audit_path: Path) -> int:
    """Count retained audit files (current + rotated copies)."""
    base_dir = audit_path.parent
    base_name = audit_path.name
    count = 0
    # Current file
    if audit_path.exists():
        count += 1
    # Rotated files: .1.jsonl, .2.jsonl, ...
    # Only count up to _MAX_RETAINED_FILES - 1 rotated copies
    # (current + rotated copies = _MAX_RETAINED_FILES total)
    for i in range(1, _MAX_RETAINED_FILES):
        rotated = base_dir / f"{base_name}.{i}"
        if rotated.exists():
            count += 1
    return count


def _rotate_audit_file(audit_path: Path) -> tuple[bool, int]:
    """Rotate the audit file if it exceeds max size.

    Returns:
        (rotated, retained_count)

    Rotation naming:
        tool-dry-run-audit.jsonl → .1.jsonl
        .1.jsonl → .2.jsonl
        .2.jsonl → .3.jsonl (max retained)
        .3.jsonl → deleted
    """
    if not audit_path.exists():
        return False, 0

    try:
        file_size = audit_path.stat().st_size
    except OSError:
        return False, 0

    if file_size < _MAX_FILE_BYTES:
        return False, _count_retained_files(audit_path)

    # Perform rotation
    base_dir = audit_path.parent
    base_name = audit_path.name

    try:
        # Maximum rotated file index = _MAX_RETAINED_FILES - 1
        # e.g., _MAX_RETAINED_FILES=3 → current + .1 + .2 = 3 files total
        max_rotated_index = _MAX_RETAINED_FILES - 1

        # Delete the oldest if it exists
        oldest = base_dir / f"{base_name}.{max_rotated_index}"
        if oldest.exists():
            oldest.unlink()

        # Shift: .2 → .3 (if max is 3), .1 → .2
        for i in range(max_rotated_index - 1, 0, -1):
            src = base_dir / f"{base_name}.{i}"
            dst = base_dir / f"{base_name}.{i + 1}"
            if src.exists():
                src.rename(dst)

        # Current → .1
        audit_path.rename(base_dir / f"{base_name}.1")

        return True, _count_retained_files(audit_path)
    except OSError:
        # Rotation failed — return failure but don't crash
        return False, _count_retained_files(audit_path)


# ---------------------------------------------------------------------------
# 7. Core write function
# ---------------------------------------------------------------------------


def write_dry_run_audit_event(
    event: Mapping[str, Any],
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> DryRunAuditWriteResult:
    """Write a single audit event to the local dev JSONL file.

    This is the main write entry point. It:
      1. Resolves and validates the audit file path
      2. Checks and performs file rotation if needed
      3. Serializes the event to JSON
      4. Validates event size
      5. Appends the event as a single JSONL line

    Args:
        event: A JSON-safe audit event dict (from build_dry_run_audit_event).
        hermes_home: Override HERMES_HOME path. If None, reads from env.

    Returns:
        DryRunAuditWriteResult indicating success or failure.

    Guarantees:
        - Write failure never enables execution
        - Write failure never calls provider
        - Write failure never calls tool handler
        - Write failure never leaks secrets
        - Path is always under HERMES_HOME dev path
        - Never writes to ~/.hermes
        - Never writes to production state.db
        - No raw arguments or secrets stored
    """
    # Step 1: Resolve path
    audit_path, path_error = _resolve_audit_path(hermes_home)
    if path_error is not None:
        return DryRunAuditWriteResult(
            written=False,
            path=None,
            event_id=event.get("eventId"),
            error_code=path_error,
            error_message=_error_message_for_code(path_error),
            rotated=False,
            retained_files=0,
        )

    # Step 2: Serialize event to JSON
    try:
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        return DryRunAuditWriteResult(
            written=False,
            path=str(audit_path),
            event_id=event.get("eventId"),
            error_code=ERROR_AUDIT_SERIALIZATION_FAILED,
            error_message=f"Event serialization failed: {exc!s}",
            rotated=False,
            retained_files=_count_retained_files(audit_path),
        )

    # Add newline for JSONL
    line_bytes = (line + "\n").encode("utf-8")

    # Step 3: Validate event size
    if len(line_bytes) > _MAX_EVENT_BYTES:
        return DryRunAuditWriteResult(
            written=False,
            path=str(audit_path),
            event_id=event.get("eventId"),
            error_code=ERROR_AUDIT_EVENT_TOO_LARGE,
            error_message=(
                f"Event size ({len(line_bytes)} bytes) exceeds "
                f"maximum ({_MAX_EVENT_BYTES} bytes)"
            ),
            rotated=False,
            retained_files=_count_retained_files(audit_path),
        )

    # Step 4: Rotate if needed
    try:
        rotated, retained = _rotate_audit_file(audit_path)
    except Exception:
        rotated = False
        retained = _count_retained_files(audit_path)

    # Step 5: Ensure directory exists
    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return DryRunAuditWriteResult(
            written=False,
            path=str(audit_path),
            event_id=event.get("eventId"),
            error_code=ERROR_AUDIT_WRITE_FAILED,
            error_message=f"Cannot create audit directory: {exc!s}",
            rotated=rotated,
            retained_files=retained,
        )

    # Step 6: Append event
    try:
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(line_bytes.decode("utf-8"))
    except OSError as exc:
        return DryRunAuditWriteResult(
            written=False,
            path=str(audit_path),
            event_id=event.get("eventId"),
            error_code=ERROR_AUDIT_WRITE_FAILED,
            error_message=f"Cannot write audit event: {exc!s}",
            rotated=rotated,
            retained_files=retained,
        )

    # Step 7: Best-effort dual-write to the Phase 2D durable audit store.
    # This never affects the legacy write result above and never raises.
    try:
        from hermes_cli.dev_web_audit_bridge import bridge_legacy_audit_to_store

        bridge_legacy_audit_to_store(
            event, audit_kind="dry_run", hermes_home=hermes_home
        )
    except Exception:
        pass

    # Step 8: Success
    return DryRunAuditWriteResult(
        written=True,
        path=str(audit_path),
        event_id=event.get("eventId"),
        error_code=None,
        error_message=None,
        rotated=rotated,
        retained_files=retained,
    )


# ---------------------------------------------------------------------------
# 8. Helpers
# ---------------------------------------------------------------------------


_ERROR_MESSAGES: dict[str, str] = {
    ERROR_HERMES_HOME_MISSING: "HERMES_HOME is not set.",
    ERROR_AUDIT_PATH_OUTSIDE_HERMES_HOME: (
        "Audit path is outside HERMES_HOME or points to production."
    ),
    ERROR_AUDIT_EVENT_TOO_LARGE: "Audit event exceeds maximum size.",
    ERROR_AUDIT_WRITE_FAILED: "Audit write failed.",
    ERROR_AUDIT_ROTATION_FAILED: "Audit file rotation failed.",
    ERROR_AUDIT_SERIALIZATION_FAILED: "Audit event serialization failed.",
    ERROR_AUDIT_REDACTION_FAILED: "Audit event redaction failed.",
}


def _error_message_for_code(code: str) -> str:
    """Get a safe error message for an error code."""
    return _ERROR_MESSAGES.get(code, "Unknown audit error.")
