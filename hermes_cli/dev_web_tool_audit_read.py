"""Read-Only Audit Events Reader for the Hermes Dev WebUI.

This module implements a **read-only** reader for the dev-only audit JSONL
stores produced by the tool dry-run, pre-execution, and post-execution
audit writers. It exposes a single safe entry point that:

  - Resolves and validates the audit store path with a containment guard
    (only the dev ``HERMES_HOME``; production ``~/.hermes`` is blocked).
  - Reads the appropriate JSONL file for the requested ``auditKind``.
  - Parses each line defensively, skipping malformed lines safely.
  - Normalizes every event to a **whitelisted** safe item — raw
    confirmation tokens, full token hashes, raw arguments, secrets,
    provider payloads, callable objects, and function reprs are never
    surfaced.
  - Applies ``limit`` / ``cursor`` / ``canonicalName`` constraints.
  - Never writes, executes, dispatches, calls a provider, or mutates
    ``STATIC_ALLOWLIST``.

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider / handler / dispatch / agent runtime imports
  - no network IO, no runtime state mutation
  - deterministic, JSON-serializable output
  - never reads production ``~/.hermes``
  - never reads production ``state.db``
  - never exposes raw token / full tokenHash / raw arguments / secrets

Phase: 1G-04-30 — Accelerated WebUI Closeout (audit read API)
Status: read-only audit JSONL reader implemented
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Filenames mirror the three audit writer modules (frozen constants).
_DRY_RUN_AUDIT_FILENAME = "tool-dry-run-audit.jsonl"
_PRE_EXECUTION_AUDIT_FILENAME = "tool-pre-execution-audit.jsonl"
_POST_EXECUTION_AUDIT_FILENAME = "tool-post-execution-audit.jsonl"

_AUDIT_DIR_RELATIVE = "gateway/dev/audit"

# Forbidden production paths (never read here)
_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"

# Read limits
_MAX_LINES_READ = 1000  # cap total lines parsed per request (safety)
_MAX_LIMIT = 100
_DEFAULT_LIMIT = 50
_MAX_CANONICAL_NAME_LENGTH = 256
_DIGEST_SHORT_LENGTH = 24  # short-form prefix for digest fields

# Valid audit kinds
AUDIT_KIND_DRY_RUN = "dry_run"
AUDIT_KIND_PRE_EXECUTION = "pre_execution"
AUDIT_KIND_POST_EXECUTION = "post_execution"
VALID_AUDIT_KINDS: frozenset[str] = frozenset(
    {AUDIT_KIND_DRY_RUN, AUDIT_KIND_PRE_EXECUTION, AUDIT_KIND_POST_EXECUTION}
)

# Map audit kind → JSONL filename
_KIND_FILENAME: dict[str, str] = {
    AUDIT_KIND_DRY_RUN: _DRY_RUN_AUDIT_FILENAME,
    AUDIT_KIND_PRE_EXECUTION: _PRE_EXECUTION_AUDIT_FILENAME,
    AUDIT_KIND_POST_EXECUTION: _POST_EXECUTION_AUDIT_FILENAME,
}

# Error codes
ERROR_HERMES_HOME_MISSING = "audit_read_hermes_home_missing"
ERROR_AUDIT_KIND_INVALID = "audit_read_kind_invalid"
ERROR_AUDIT_PATH_FORBIDDEN = "audit_read_path_forbidden"
ERROR_LIMIT_INVALID = "audit_read_limit_invalid"
ERROR_CURSOR_INVALID = "audit_read_cursor_invalid"

# Secret value patterns for defensive re-check (mirrors dry-run audit writer)
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
)

# Fields that must never be echoed (defense-in-depth; the whitelist below
# already excludes them, but this guards against accidental inclusion).
_FORBIDDEN_FIELD_STEMS: frozenset[str] = frozenset(
    n.replace("_", "").replace("-", "").lower()
    for n in (
        "api_key", "apikey", "authorization", "auth_header", "bearer",
        "token", "secret", "password", "passwd", "credential", "cookie",
        "session", "private_key", "client_secret", "access_token",
        "refresh_token", "access_key", "arguments", "argumentspreview",
        "rawarguments", "tokenhash", "rawtoken", "confirmationtoken",
    )
)


# ---------------------------------------------------------------------------
# 1. Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuditReadResult:
    """Immutable result of an audit events read."""

    success: bool
    audit_kind: str | None
    items: tuple[dict[str, Any], ...]
    next_cursor: str | None
    limit: int
    has_more: bool
    skipped_malformed: int
    error_code: str | None
    error_message: str | None


# ---------------------------------------------------------------------------
# 2. Defensive sanitization helpers
# ---------------------------------------------------------------------------


def _is_secret_value(value: str) -> bool:
    """Check if a string value matches known secret patterns."""
    return any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS)


def _sanitize_scalar(value: Any) -> Any:
    """Defensively sanitize a scalar/leaf value for safe return.

    - Secrets → ``"[REDACTED]"``
    - Long strings → truncated
    - Non-JSON-native scalars → safe string (never a callable/repr leak)
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        if _is_secret_value(value):
            return "[REDACTED]"
        if len(value) > 200:
            return value[:200] + "…"
        return value
    # Anything else (list/dict/object) at a leaf is unexpected for the
    # whitelisted fields — reduce to a safe truncated string, never a repr
    # of a callable or arbitrary object.
    try:
        s = str(value)
    except Exception:
        return "[unsupported]"
    if _is_secret_value(s):
        return "[REDACTED]"
    if len(s) > 200:
        return s[:200] + "…"
    return s


def _short_digest(value: Any) -> str | None:
    """Return a short-form prefix of a digest, or None if absent.

    Digests are correlation-only; the full digest is not needed in the
    audit viewer. A short prefix is returned for at-a-glance matching.
    """
    if not isinstance(value, str) or not value:
        return None
    if _is_secret_value(value):
        return "[REDACTED]"
    if len(value) <= _DIGEST_SHORT_LENGTH:
        return value
    return value[:_DIGEST_SHORT_LENGTH] + "…"


def _safe_get(event: dict[str, Any], key: str) -> Any:
    """Fetch a value from an event, returning None for forbidden keys.

    Forbidden keys are never surfaced even if present in the raw event.
    """
    normalized = key.replace("_", "").replace("-", "").lower()
    if normalized in _FORBIDDEN_FIELD_STEMS:
        return None
    return event.get(key)


# ---------------------------------------------------------------------------
# 3. Path resolution and validation
# ---------------------------------------------------------------------------


def _is_relative_to(child: Path, parent: Path) -> bool:
    """Check if *child* path is inside or equal to *parent* path."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_audit_store_path(
    audit_kind: str,
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    """Resolve and validate the audit file path for *audit_kind*.

    Returns ``(audit_file_path, error_code_or_none)``.

    Guarantees (mirrors the writer path guards):
      - HERMES_HOME must not equal production home
      - HERMES_HOME must not be inside the production subtree
      - Resolved file must be inside ``$HERMES_HOME/gateway/dev/audit``
      - Resolved file must not be inside ``~/.hermes``
      - Path containment uses ``Path.relative_to()``, not string prefix
      - No file is opened here; this only computes and validates the path
      - production ``state.db`` is never the target
    """
    if audit_kind not in VALID_AUDIT_KINDS:
        return Path(), ERROR_AUDIT_KIND_INVALID

    if hermes_home is not None:
        home = Path(hermes_home).resolve()
    else:
        home_str = os.environ.get("HERMES_HOME", "")
        if not home_str:
            return Path(), ERROR_HERMES_HOME_MISSING
        home = Path(home_str).resolve()

    prod_home = Path(_PRODUCTION_HERMES_HOME).resolve()

    # Block exact production home
    if home == prod_home:
        return Path(), ERROR_AUDIT_PATH_FORBIDDEN

    # Block inside production subtree
    if _is_relative_to(home, prod_home):
        return Path(), ERROR_AUDIT_PATH_FORBIDDEN

    filename = _KIND_FILENAME[audit_kind]
    audit_dir = home / _AUDIT_DIR_RELATIVE
    audit_file = audit_dir / filename

    resolved_dir = audit_dir.resolve()
    resolved_file = audit_file.resolve()

    # Block if resolved dir/file touches production
    if resolved_dir == prod_home or _is_relative_to(resolved_dir, prod_home):
        return Path(), ERROR_AUDIT_PATH_FORBIDDEN
    if resolved_file == prod_home or _is_relative_to(resolved_file, prod_home):
        return Path(), ERROR_AUDIT_PATH_FORBIDDEN

    # Validate file is inside the expected audit dir under home
    expected_dir = (home / _AUDIT_DIR_RELATIVE).resolve()
    if not _is_relative_to(resolved_dir, expected_dir):
        return Path(), ERROR_AUDIT_PATH_FORBIDDEN
    if not _is_relative_to(resolved_file, resolved_dir):
        return Path(), ERROR_AUDIT_PATH_FORBIDDEN

    # Never target production state.db (defense-in-depth)
    if resolved_file.name == "state.db":
        return Path(), ERROR_AUDIT_PATH_FORBIDDEN

    return audit_file, None


# ---------------------------------------------------------------------------
# 4. Per-kind safe item normalization (whitelist-based)
# ---------------------------------------------------------------------------


def _normalize_dry_run_item(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize a dry-run audit event to a safe item."""
    item: dict[str, Any] = {
        "auditKind": AUDIT_KIND_DRY_RUN,
        "auditId": _sanitize_scalar(_safe_get(event, "eventId")),
        "timestamp": _sanitize_scalar(_safe_get(event, "timestamp")),
        "canonicalName": _sanitize_scalar(_safe_get(event, "canonicalName")),
        "decision": _sanitize_scalar(_safe_get(event, "decision")),
        "riskTier": _sanitize_scalar(_safe_get(event, "riskTier")),
        "toolExists": bool(_safe_get(event, "toolExists")),
        "dryRunDecisionDigest": _short_digest(
            _safe_get(event, "dryRunDecisionDigest")
        ),
    }
    item["safeSummary"] = {
        "toolExists": item["toolExists"],
        "riskTier": item["riskTier"],
        "decision": item["decision"],
        "redactionApplied": bool(_safe_get(event, "redactionApplied")),
    }
    return item


def _normalize_pre_execution_item(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize a pre-execution audit event to a safe item."""
    item: dict[str, Any] = {
        "auditKind": AUDIT_KIND_PRE_EXECUTION,
        "auditId": _sanitize_scalar(_safe_get(event, "preExecutionAuditId")),
        "timestamp": _sanitize_scalar(_safe_get(event, "createdAt")),
        "canonicalName": _sanitize_scalar(_safe_get(event, "canonicalName")),
        "executeRequestId": _sanitize_scalar(
            _safe_get(event, "executeRequestId")
        ),
        "dryRunRequestId": _sanitize_scalar(
            _safe_get(event, "dryRunRequestId")
        ),
        "preExecutionAuditId": _sanitize_scalar(
            _safe_get(event, "preExecutionAuditId")
        ),
        "dryRunDecisionDigest": _short_digest(
            _safe_get(event, "dryRunDecisionDigest")
        ),
        "riskTier": _sanitize_scalar(_safe_get(event, "riskTier")),
    }
    item["safeSummary"] = {
        "riskTier": item["riskTier"],
        "policyVersion": _sanitize_scalar(_safe_get(event, "policyVersion")),
    }
    return item


def _safe_side_effect_flags(event: dict[str, Any]) -> dict[str, bool]:
    """Extract side-effect flags from an event, defaulting all to False.

    For controlled clarify execution every external flag must be False.
    """
    raw = _safe_get(event, "sideEffectFlags")
    flags = {
        "providerSchemaSent": False,
        "providerApiCalled": False,
        "externalSideEffects": False,
    }
    if isinstance(raw, dict):
        for key in flags:
            val = raw.get(key)
            flags[key] = bool(val) if isinstance(val, bool) else False
    return flags


def _normalize_post_execution_item(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize a post-execution audit event to a safe item."""
    result_summary_raw = _safe_get(event, "resultSummary")
    result_summary: dict[str, Any] = {
        "toolResultType": None,
        "messageLength": 0,
        "questionCount": 0,
    }
    if isinstance(result_summary_raw, dict):
        result_summary["toolResultType"] = _sanitize_scalar(
            result_summary_raw.get("toolResultType")
        )
        ml = result_summary_raw.get("messageLength")
        if isinstance(ml, int):
            result_summary["messageLength"] = ml
        qc = result_summary_raw.get("questionCount")
        if isinstance(qc, int):
            result_summary["questionCount"] = qc

    side_effects = _safe_side_effect_flags(event)

    item: dict[str, Any] = {
        "auditKind": AUDIT_KIND_POST_EXECUTION,
        "auditId": _sanitize_scalar(
            _safe_get(event, "postExecutionAuditId")
        ),
        "timestamp": _sanitize_scalar(_safe_get(event, "createdAt")),
        "canonicalName": _sanitize_scalar(_safe_get(event, "canonicalName")),
        "executeRequestId": _sanitize_scalar(
            _safe_get(event, "executeRequestId")
        ),
        "preExecutionAuditId": _sanitize_scalar(
            _safe_get(event, "preExecutionAuditId")
        ),
        "handlerLookupId": _sanitize_scalar(
            _safe_get(event, "handlerLookupId")
        ),
        "dispatchId": _sanitize_scalar(_safe_get(event, "dispatchId")),
        "handlerCallId": _sanitize_scalar(_safe_get(event, "handlerCallId")),
        "executionStatus": _sanitize_scalar(
            _safe_get(event, "executionStatus")
        ),
        "handlerCallStatus": _sanitize_scalar(
            _safe_get(event, "handlerCallStatus")
        ),
        "decision": _sanitize_scalar(_safe_get(event, "eventType")),
        "sideEffects": side_effects,
        "safeSummary": {
            "toolResultType": result_summary["toolResultType"],
            "messageLength": result_summary["messageLength"],
            "questionCount": result_summary["questionCount"],
        },
    }
    return item


_NORMALIZERS = {
    AUDIT_KIND_DRY_RUN: _normalize_dry_run_item,
    AUDIT_KIND_PRE_EXECUTION: _normalize_pre_execution_item,
    AUDIT_KIND_POST_EXECUTION: _normalize_post_execution_item,
}


def _normalize_event(audit_kind: str, event: dict[str, Any]) -> dict[str, Any]:
    """Dispatch to the per-kind normalizer."""
    return _NORMALIZERS[audit_kind](event)


# ---------------------------------------------------------------------------
# 5. JSONL reader
# ---------------------------------------------------------------------------


def _read_jsonl_items(
    audit_file: Path,
    audit_kind: str,
    canonical_name_filter: str | None,
) -> tuple[list[dict[str, Any]], int]:
    """Read and normalize a JSONL audit file.

    Returns ``(items_newest_first, skipped_malformed_count)``.
    A missing file returns an empty list (no error).
    """
    if not audit_file.exists() or not audit_file.is_file():
        return [], 0

    items: list[dict[str, Any]] = []
    skipped = 0
    lines_read = 0

    try:
        with audit_file.open("r", encoding="utf-8") as f:
            for raw_line in f:
                if lines_read >= _MAX_LINES_READ:
                    break
                lines_read += 1
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except (ValueError, TypeError):
                    # Malformed line — skip safely, never leak content.
                    skipped += 1
                    continue
                if not isinstance(event, dict):
                    skipped += 1
                    continue
                # Optional canonicalName filter (exact match only)
                if canonical_name_filter is not None:
                    cn = event.get("canonicalName")
                    if not isinstance(cn, str) or cn != canonical_name_filter:
                        continue
                try:
                    items.append(_normalize_event(audit_kind, event))
                except Exception:
                    # Normalization failure — skip safely.
                    skipped += 1
                    continue
    except OSError:
        # Read failure — return what we have (empty).
        return [], skipped

    # Newest first (JSONL is append-only; last line is most recent)
    items.reverse()
    return items, skipped


# ---------------------------------------------------------------------------
# 6. Public entry point
# ---------------------------------------------------------------------------


def read_audit_events(
    *,
    audit_kind: str,
    limit: int = _DEFAULT_LIMIT,
    cursor: str | None = None,
    canonical_name: str | None = None,
    hermes_home: str | os.PathLike[str] | None = None,
) -> AuditReadResult:
    """Read safe audit events for *audit_kind*.

    Args:
        audit_kind: One of ``dry_run`` / ``pre_execution`` / ``post_execution``.
        limit: Max items to return (1..100).
        cursor: Opaque offset cursor from a previous ``nextCursor``.
        canonical_name: Optional exact canonicalName filter.
        hermes_home: HERMES_HOME override.

    Returns:
        ``AuditReadResult``. ``success=False`` only for invalid input or a
        forbidden path — never for a missing or malformed file (those return
        an empty/skipped result).
    """
    # Validate audit kind
    if audit_kind not in VALID_AUDIT_KINDS:
        return AuditReadResult(
            success=False,
            audit_kind=None,
            items=(),
            next_cursor=None,
            limit=limit,
            has_more=False,
            skipped_malformed=0,
            error_code=ERROR_AUDIT_KIND_INVALID,
            error_message=f"Invalid auditKind: {audit_kind!r}.",
        )

    # Validate limit
    if not isinstance(limit, int) or limit < 1:
        return AuditReadResult(
            success=False,
            audit_kind=audit_kind,
            items=(),
            next_cursor=None,
            limit=limit,
            has_more=False,
            skipped_malformed=0,
            error_code=ERROR_LIMIT_INVALID,
            error_message="limit must be a positive integer.",
        )
    limit = min(limit, _MAX_LIMIT)

    # Validate canonicalName
    canonical_filter: str | None = None
    if canonical_name is not None:
        if not isinstance(canonical_name, str):
            return AuditReadResult(
                success=False,
                audit_kind=audit_kind,
                items=(),
                next_cursor=None,
                limit=limit,
                has_more=False,
                skipped_malformed=0,
                error_code=ERROR_AUDIT_KIND_INVALID,
                error_message="canonicalName must be a string.",
            )
        canonical_name = canonical_name.strip()
        if canonical_name:
            if len(canonical_name) > _MAX_CANONICAL_NAME_LENGTH:
                return AuditReadResult(
                    success=False,
                    audit_kind=audit_kind,
                    items=(),
                    next_cursor=None,
                    limit=limit,
                    has_more=False,
                    skipped_malformed=0,
                    error_code=ERROR_AUDIT_KIND_INVALID,
                    error_message="canonicalName exceeds maximum length.",
                )
            canonical_filter = canonical_name

    # Validate cursor (opaque integer offset)
    offset = 0
    if cursor is not None:
        if not isinstance(cursor, str) or not cursor:
            return AuditReadResult(
                success=False,
                audit_kind=audit_kind,
                items=(),
                next_cursor=None,
                limit=limit,
                has_more=False,
                skipped_malformed=0,
                error_code=ERROR_CURSOR_INVALID,
                error_message="cursor must be a non-empty string.",
            )
        try:
            offset = int(cursor)
        except (ValueError, TypeError):
            return AuditReadResult(
                success=False,
                audit_kind=audit_kind,
                items=(),
                next_cursor=None,
                limit=limit,
                has_more=False,
                skipped_malformed=0,
                error_code=ERROR_CURSOR_INVALID,
                error_message="cursor must encode a non-negative integer offset.",
            )
        if offset < 0:
            return AuditReadResult(
                success=False,
                audit_kind=audit_kind,
                items=(),
                next_cursor=None,
                limit=limit,
                has_more=False,
                skipped_malformed=0,
                error_code=ERROR_CURSOR_INVALID,
                error_message="cursor offset must be non-negative.",
            )

    # Resolve + validate path (containment guard)
    audit_file, path_error = resolve_audit_store_path(audit_kind, hermes_home)
    if path_error is not None:
        return AuditReadResult(
            success=False,
            audit_kind=audit_kind,
            items=(),
            next_cursor=None,
            limit=limit,
            has_more=False,
            skipped_malformed=0,
            error_code=path_error,
            error_message=_error_message_for_code(path_error),
        )

    # Read + normalize
    all_items, skipped = _read_jsonl_items(
        audit_file, audit_kind, canonical_filter
    )

    # Apply offset/limit pagination
    page = all_items[offset : offset + limit]
    remaining = len(all_items) - (offset + len(page))
    has_more = remaining > 0
    next_cursor = str(offset + limit) if has_more else None

    return AuditReadResult(
        success=True,
        audit_kind=audit_kind,
        items=tuple(page),
        next_cursor=next_cursor,
        limit=limit,
        has_more=has_more,
        skipped_malformed=skipped,
        error_code=None,
        error_message=None,
    )


def audit_read_result_to_safe_dict(result: AuditReadResult) -> dict[str, Any]:
    """Convert an ``AuditReadResult`` to a JSON-safe response dict."""
    return {
        "auditKind": result.audit_kind,
        "items": list(result.items),
        "nextCursor": result.next_cursor,
        "limit": result.limit,
        "hasMore": result.has_more,
        "skippedMalformed": result.skipped_malformed,
    }


# ---------------------------------------------------------------------------
# 7. Error message helper
# ---------------------------------------------------------------------------


_ERROR_MESSAGES: dict[str, str] = {
    ERROR_HERMES_HOME_MISSING: "HERMES_HOME is not set.",
    ERROR_AUDIT_KIND_INVALID: "Invalid audit kind.",
    ERROR_AUDIT_PATH_FORBIDDEN: (
        "Audit path is outside the dev HERMES_HOME or points to production."
    ),
    ERROR_LIMIT_INVALID: "Invalid limit.",
    ERROR_CURSOR_INVALID: "Invalid cursor.",
}


def _error_message_for_code(code: str) -> str:
    """Get a safe error message for an error code."""
    return _ERROR_MESSAGES.get(code, "Unknown audit read error.")
