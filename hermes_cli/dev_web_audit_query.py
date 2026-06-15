"""Audit Query Engine + Cursor Pagination for the Hermes Dev WebUI (Phase 2D).

High-level read path over the durable audit store. Supports:

  - cursor-based pagination (preferred) with opaque, tamper-resistant cursors
  - offset-based pagination kept for backward compatibility
  - ordering (``asc`` / ``desc``) by monotonic ``sequence``
  - equality filters: ``eventType`` / ``toolId`` / ``status`` / ``auditKind`` /
    ``source`` / ``providerMode`` / ``readOnly`` / ``writeRequired``
  - time-range filters: ``fromCreatedAt`` / ``toCreatedAt``
  - safe substring ``search`` over summary / metadata text
  - ``includeSummary`` toggle

The cursor token is a base64url JSON object carrying ``lastSequence``,
``direction``, ``queryHash``, and ``issuedAt`` — never a file path, an
absolute path, an index internal, a secret, or a full token hash.

Hard guarantees:
  - source of truth is a full segment scan (robust to rotation / corruption /
    a stale index); the index is used opportunistically for status only
  - invalid / mismatched / tampered cursors are rejected with explicit codes
  - oversized / negative limits are rejected
  - invalid dates and unsafe search strings are rejected
  - output items are sanitized (whitelist) and never expose raw arguments,
    secrets, full token hashes, callable reprs, or production paths

Phase: 2D — Durable Dev Audit Store MVP
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from hermes_cli.dev_web_audit_schema import (
    AUDIT_SCHEMA_VERSION,
    VALID_AUDIT_KINDS,
    VALID_PROVIDER_MODES,
    VALID_SOURCES,
    VALID_STATUSES,
)
from hermes_cli.dev_web_audit_sanitizer import sanitize_audit_value, strip_forbidden_keys
from hermes_cli.dev_web_audit_store import (
    ERROR_HERMES_HOME_MISSING,
    ERROR_STORE_ROOT_FORBIDDEN,
    get_audit_store_root,
    iter_all_events,
)
from hermes_cli.dev_web_audit_index import (
    validate_audit_index,
    repair_audit_index_if_needed,
)
from hermes_cli.dev_web_audit_rotation import validate_audit_segments

# ---------------------------------------------------------------------------
# 1. Limits + error codes
# ---------------------------------------------------------------------------

DEFAULT_LIMIT = 50
MAX_LIMIT = 100
MIN_LIMIT = 1

MAX_SEARCH_LENGTH = 128
MAX_CURSOR_LENGTH = 512

# Safe item output whitelist (everything else is dropped).
_SAFE_ITEM_FIELDS: tuple[str, ...] = (
    "eventId",
    "sequence",
    "createdAt",
    "eventType",
    "auditKind",
    "source",
    "phase",
    "toolId",
    "toolCategory",
    "mode",
    "status",
    "blockedReason",
    "readOnly",
    "writeRequired",
    "providerMode",
    "providerSchemaSent",
    "providerApiCalled",
    "externalNetworkCalled",
    "localSideEffects",
    "externalSideEffects",
    "redactionApplied",
    "executionId",
    "dryRunId",
    "dispatchId",
    "handlerCallId",
    "preExecutionAuditId",
    "postExecutionAuditId",
    "providerRequestId",
    "providerResponseId",
    "writePlanId",
    "writePreviewId",
    "rollbackId",
    "confirmationTokenId",
)

# Query error / blocked codes.
ERROR_HERMES_HOME_MISSING_Q = ERROR_HERMES_HOME_MISSING
ERROR_STORE_ROOT_FORBIDDEN_Q = ERROR_STORE_ROOT_FORBIDDEN
BLOCKED_CURSOR_INVALID = "blocked_audit_cursor_invalid"
BLOCKED_CURSOR_QUERY_MISMATCH = "blocked_audit_cursor_query_mismatch"
BLOCKED_LIMIT_TOO_LARGE = "blocked_audit_limit_too_large"
BLOCKED_QUERY_INVALID = "blocked_audit_query_invalid"

# Direction constants.
DIR_DESC = "desc"
DIR_ASC = "asc"

_ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})$"
)
_UNSAFE_SEARCH_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# ---------------------------------------------------------------------------
# 2. Query + cursor dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuditQuery:
    """Immutable query specification."""

    limit: int = DEFAULT_LIMIT
    cursor: str | None = None
    order: str = DIR_DESC
    event_type: str | None = None
    tool_id: str | None = None
    status: str | None = None
    audit_kind: str | None = None
    source: str | None = None
    provider_mode: str | None = None
    read_only: bool | None = None
    write_required: bool | None = None
    from_created_at: str | None = None
    to_created_at: str | None = None
    search: str | None = None
    include_summary: bool = True


@dataclass(frozen=True, slots=True)
class AuditCursor:
    """Opaque cursor payload (no paths, no secrets)."""

    last_sequence: int
    direction: str
    query_hash: str
    issued_at: str


@dataclass(frozen=True, slots=True)
class AuditQueryResult:
    """Immutable result of an audit query."""

    success: bool
    items: tuple[dict[str, Any], ...]
    next_cursor: str | None
    previous_cursor: str | None
    has_more: bool
    limit: int
    order: str
    store_status: dict[str, Any]
    index_status: dict[str, Any]
    schema_version: str
    skipped_malformed: int
    query_echo: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# 3. Query-hash + cursor codec
# ---------------------------------------------------------------------------


def _query_hash(q: AuditQuery) -> str:
    """Stable hash of the filter shape (ignores cursor / limit / order)."""
    payload = json.dumps(
        {
            "eventType": q.event_type,
            "toolId": q.tool_id,
            "status": q.status,
            "auditKind": q.audit_kind,
            "source": q.source,
            "providerMode": q.provider_mode,
            "readOnly": q.read_only,
            "writeRequired": q.write_required,
            "fromCreatedAt": q.from_created_at,
            "toCreatedAt": q.to_created_at,
            "search": (q.search.strip().lower() if q.search else None),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def encode_audit_cursor(cursor: AuditCursor) -> str:
    """Encode a cursor to an opaque base64url token."""
    payload = json.dumps(
        {
            "v": 1,
            "lastSequence": cursor.last_sequence,
            "direction": cursor.direction,
            "queryHash": cursor.query_hash,
            "issuedAt": cursor.issued_at,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_audit_cursor(token: str) -> AuditCursor | None:
    """Decode an opaque cursor token. Returns ``None`` if invalid/tampered."""
    if not isinstance(token, str) or not token or len(token) > MAX_CURSOR_LENGTH:
        return None
    padding = "=" * (-len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode(token + padding).decode("utf-8")
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get("v") != 1:
        return None
    last_sequence = data.get("lastSequence")
    direction = data.get("direction")
    query_hash = data.get("queryHash")
    issued_at = data.get("issuedAt")
    if not isinstance(last_sequence, int) or isinstance(last_sequence, bool):
        return None
    if direction not in (DIR_ASC, DIR_DESC):
        return None
    if not isinstance(query_hash, str) or not query_hash:
        return None
    if not isinstance(issued_at, str) or not issued_at:
        return None
    return AuditCursor(
        last_sequence=last_sequence,
        direction=direction,
        query_hash=query_hash,
        issued_at=issued_at,
    )


# ---------------------------------------------------------------------------
# 4. Validation
# ---------------------------------------------------------------------------


def _is_offset_cursor(token: str | None) -> bool:
    """Legacy cursors are bare non-negative integer strings."""
    if not isinstance(token, str) or not token:
        return False
    return token.isdigit()


def validate_query(q: AuditQuery) -> tuple[bool, str | None, str | None]:
    """Validate a query. Returns ``(ok, error_code, error_message)``."""
    if not isinstance(q.limit, int) or isinstance(q.limit, bool):
        return False, BLOCKED_QUERY_INVALID, "limit must be an integer."
    if q.limit < MIN_LIMIT:
        return False, BLOCKED_QUERY_INVALID, "limit must be >= 1."
    if q.limit > MAX_LIMIT:
        return False, BLOCKED_LIMIT_TOO_LARGE, f"limit must be <= {MAX_LIMIT}."

    if q.order not in (DIR_ASC, DIR_DESC):
        return False, BLOCKED_QUERY_INVALID, "order must be 'asc' or 'desc'."

    for name, value in (
        ("auditKind", q.audit_kind),
        ("status", q.status),
        ("source", q.source),
        ("providerMode", q.provider_mode),
    ):
        valid_sets = {
            "auditKind": VALID_AUDIT_KINDS,
            "status": VALID_STATUSES,
            "source": VALID_SOURCES,
            "providerMode": VALID_PROVIDER_MODES,
        }
        if value is not None and value not in valid_sets[name]:
            return False, BLOCKED_QUERY_INVALID, f"{name} has an invalid value."

    for label, ts in (
        ("fromCreatedAt", q.from_created_at),
        ("toCreatedAt", q.to_created_at),
    ):
        if ts is not None and not _ISO_RE.match(ts):
            return False, BLOCKED_QUERY_INVALID, f"{label} must be ISO-8601."

    if q.search is not None:
        if not isinstance(q.search, str):
            return False, BLOCKED_QUERY_INVALID, "search must be a string."
        if len(q.search) > MAX_SEARCH_LENGTH:
            return False, BLOCKED_QUERY_INVALID, "search is too long."
        if _UNSAFE_SEARCH_RE.search(q.search):
            return False, BLOCKED_QUERY_INVALID, "search contains unsafe characters."

    return True, None, None


def build_audit_query(
    *,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
    order: str = DIR_DESC,
    event_type: str | None = None,
    tool_id: str | None = None,
    status: str | None = None,
    audit_kind: str | None = None,
    source: str | None = None,
    provider_mode: str | None = None,
    read_only: bool | None = None,
    write_required: bool | None = None,
    from_created_at: str | None = None,
    to_created_at: str | None = None,
    search: str | None = None,
    include_summary: bool = True,
) -> AuditQuery:
    """Construct an :class:`AuditQuery`, trimming string inputs."""
    def _trim(v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    return AuditQuery(
        limit=limit,
        cursor=cursor,
        order=order,
        event_type=_trim(event_type),
        tool_id=_trim(tool_id),
        status=_trim(status),
        audit_kind=_trim(audit_kind),
        source=_trim(source),
        provider_mode=_trim(provider_mode),
        read_only=read_only,
        write_required=write_required,
        from_created_at=_trim(from_created_at),
        to_created_at=_trim(to_created_at),
        search=_trim(search),
        include_summary=bool(include_summary),
    )


# ---------------------------------------------------------------------------
# 5. Safe item normalization
# ---------------------------------------------------------------------------


def _to_safe_item(event: dict[str, Any], *, include_summary: bool) -> dict[str, Any]:
    """Whitelist + re-sanitize a canonical event for output."""
    item: dict[str, Any] = {}
    for key in _SAFE_ITEM_FIELDS:
        if key in event and event[key] is not None:
            item[key] = sanitize_audit_value(event[key], field_name=key)
    if include_summary:
        summary = event.get("summary")
        item["summary"] = strip_forbidden_keys(
            sanitize_audit_value(summary, field_name="summary")
        )
        meta = event.get("safeMetadata")
        item["safeMetadata"] = strip_forbidden_keys(
            sanitize_audit_value(meta, field_name="safeMetadata")
        )
    item["schemaVersion"] = event.get("schemaVersion", AUDIT_SCHEMA_VERSION)
    return item


# ---------------------------------------------------------------------------
# 6. Filtering
# ---------------------------------------------------------------------------


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _event_matches(event: dict[str, Any], q: AuditQuery) -> bool:
    if q.event_type is not None and event.get("eventType") != q.event_type:
        return False
    if q.tool_id is not None and event.get("toolId") != q.tool_id:
        return False
    if q.status is not None and event.get("status") != q.status:
        return False
    if q.audit_kind is not None and event.get("auditKind") != q.audit_kind:
        return False
    if q.source is not None and event.get("source") != q.source:
        return False
    if q.provider_mode is not None and event.get("providerMode") != q.provider_mode:
        return False
    if q.read_only is not None and bool(event.get("readOnly")) != q.read_only:
        return False
    if q.write_required is not None and bool(event.get("writeRequired")) != q.write_required:
        return False

    created = event.get("createdAt")
    if isinstance(created, str):
        if q.from_created_at is not None:
            c_dt = _parse_dt(created)
            f_dt = _parse_dt(q.from_created_at)
            if c_dt and f_dt and c_dt < f_dt:
                return False
        if q.to_created_at is not None:
            c_dt = _parse_dt(created)
            t_dt = _parse_dt(q.to_created_at)
            if c_dt and t_dt and c_dt > t_dt:
                return False

    if q.search:
        needle = q.search.lower()
        haystack_parts: list[str] = []
        summary = event.get("summary")
        if isinstance(summary, dict):
            haystack_parts.append(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        meta = event.get("safeMetadata")
        if isinstance(meta, dict):
            haystack_parts.append(json.dumps(meta, ensure_ascii=False, sort_keys=True))
        for key in ("eventType", "toolId", "status", "auditKind", "source"):
            v = event.get(key)
            if isinstance(v, str):
                haystack_parts.append(v)
        haystack = " ".join(haystack_parts).lower()
        if needle not in haystack:
            return False
    return True


# ---------------------------------------------------------------------------
# 7. Core query
# ---------------------------------------------------------------------------


def query_audit_events(
    query: AuditQuery,
    *,
    hermes_home: str | None = None,
    now_iso: str | None = None,
) -> AuditQueryResult:
    """Execute an audit query against the durable store.

    Returns an :class:`AuditQueryResult`. Failures (invalid input, forbidden
    path, bad cursor) are reported via ``error_code`` and never raise.
    """
    ok, code, msg = validate_query(query)
    if not ok:
        return _error_result(query, code, msg or "Invalid query.")

    root, perr = get_audit_store_root(hermes_home)
    if perr is not None:
        return _error_result(
            query,
            perr,
            "Audit store is unavailable (no dev HERMES_HOME or forbidden root).",
        )

    issued_at = now_iso or _fallback_now_iso()

    # Cursor decode: legacy offset cursor OR opaque cursor.
    cursor: AuditCursor | None = None
    offset = 0
    if query.cursor is not None:
        if _is_offset_cursor(query.cursor):
            offset = int(query.cursor)
        else:
            cursor = decode_audit_cursor(query.cursor)
            if cursor is None:
                return _error_result(
                    query, BLOCKED_CURSOR_INVALID, "Cursor is invalid or tampered."
                )
            expected_hash = _query_hash(query)
            if cursor.query_hash != expected_hash:
                return _error_result(
                    query,
                    BLOCKED_CURSOR_QUERY_MISMATCH,
                    "Cursor does not match the current query filters.",
                )
            if cursor.direction != query.order:
                return _error_result(
                    query,
                    BLOCKED_CURSOR_QUERY_MISMATCH,
                    "Cursor direction does not match the requested order.",
                )

    # Collect + filter (full scan — source of truth). Iterate with
    # include_corrupt=True so we can COUNT corrupt lines we skip (the index
    # and a rebuild elsewhere handle quarantine; the query never crashes).
    matched: list[dict[str, Any]] = []
    skipped = 0
    if root.is_dir():
        for _seg, _line, event, _raw in iter_all_events(root, include_corrupt=True):
            if event is None:
                skipped += 1
                continue
            if _event_matches(event, query):
                matched.append(event)

    # Sort by sequence.
    matched.sort(key=lambda e: int(e.get("sequence", 0) or 0))

    # Cursor windowing (opaque cursor): boundary by sequence.
    boundary = cursor.last_sequence if cursor is not None else None
    if query.order == DIR_DESC:
        # Newest first.
        matched.reverse()
        if boundary is not None:
            matched = [e for e in matched if int(e.get("sequence", 0) or 0) < boundary]
        if offset:
            matched = matched[offset:]
    else:
        if boundary is not None:
            matched = [e for e in matched if int(e.get("sequence", 0) or 0) > boundary]
        if offset:
            matched = matched[offset:]

    page = matched[: query.limit]
    has_more = len(matched) > query.limit

    # Build next cursor from the last item of this page.
    next_cursor: str | None = None
    if has_more and page:
        last_seq = int(page[-1].get("sequence", 0) or 0)
        next_cursor = encode_audit_cursor(
            AuditCursor(
                last_sequence=last_seq,
                direction=query.order,
                query_hash=_query_hash(query),
                issued_at=issued_at,
            )
        )

    # Opportunistic index maintenance + status (never affects correctness).
    idx_status_obj = validate_audit_index(root)
    if idx_status_obj.stale or not idx_status_obj.present:
        repair_audit_index_if_needed(root)
        idx_status_obj = validate_audit_index(root)

    store_status = _store_status(root)
    items = tuple(
        _to_safe_item(e, include_summary=query.include_summary) for e in page
    )

    return AuditQueryResult(
        success=True,
        items=items,
        next_cursor=next_cursor,
        previous_cursor=None,
        has_more=has_more,
        limit=query.limit,
        order=query.order,
        store_status=store_status,
        index_status=idx_status_obj.to_safe_dict(),
        schema_version=AUDIT_SCHEMA_VERSION,
        skipped_malformed=skipped,
        query_echo=_query_echo(query),
    )


# ---------------------------------------------------------------------------
# 8. Helpers
# ---------------------------------------------------------------------------


def _store_status(root: Path) -> dict[str, Any]:
    seg = validate_audit_segments(root)
    return {
        "present": root.is_dir(),
        "segmentCount": seg["segmentCount"],
        "monotonic": seg["monotonic"],
        "activeSegment": seg["activeSegment"],
        "schemaVersion": AUDIT_SCHEMA_VERSION,
    }


def _query_echo(q: AuditQuery) -> dict[str, Any]:
    return {
        "limit": q.limit,
        "order": q.order,
        "eventType": q.event_type,
        "toolId": q.tool_id,
        "status": q.status,
        "auditKind": q.audit_kind,
        "source": q.source,
        "providerMode": q.provider_mode,
        "readOnly": q.read_only,
        "writeRequired": q.write_required,
        "fromCreatedAt": q.from_created_at,
        "toCreatedAt": q.to_created_at,
        "search": q.search,
        "includeSummary": q.include_summary,
    }


def _error_result(
    q: AuditQuery, code: str, message: str
) -> AuditQueryResult:
    return AuditQueryResult(
        success=False,
        items=(),
        next_cursor=None,
        previous_cursor=None,
        has_more=False,
        limit=q.limit,
        order=q.order,
        store_status={
            "present": False,
            "segmentCount": 0,
            "monotonic": True,
            "activeSegment": None,
            "schemaVersion": AUDIT_SCHEMA_VERSION,
        },
        index_status={
            "present": False,
            "consistent": False,
            "stale": True,
            "lastSequence": 0,
            "eventCount": 0,
            "segmentCount": 0,
            "fields": [],
        },
        schema_version=AUDIT_SCHEMA_VERSION,
        skipped_malformed=0,
        query_echo=_query_echo(q),
        error_code=code,
        error_message=message,
    )


def _fallback_now_iso() -> str:
    # Kept simple; callers pass ``now_iso`` when deterministic timestamps are
    # needed (tests). Production paths accept the small non-determinism.
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def audit_query_result_to_safe_dict(result: AuditQueryResult) -> dict[str, Any]:
    """Convert an :class:`AuditQueryResult` to a JSON-safe response dict."""
    return {
        "items": [dict(i) for i in result.items],
        "nextCursor": result.next_cursor,
        "previousCursor": result.previous_cursor,
        "hasMore": result.has_more,
        "limit": result.limit,
        "order": result.order,
        "query": result.query_echo,
        "storeStatus": result.store_status,
        "indexStatus": result.index_status,
        "schemaVersion": result.schema_version,
        "skippedMalformed": result.skipped_malformed,
    }
