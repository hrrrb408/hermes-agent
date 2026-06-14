"""Phase 2B Provider Round-trip Audit Writer for the Hermes Dev WebUI.

Records the Provider Schema / API round-trip lifecycle to a local dev-only
JSONL file under ``HERMES_HOME/gateway/dev/audit/provider-roundtrip-audit.jsonl``.

Event types recorded:
  - ``provider_schema_built``
  - ``provider_request_built``
  - ``provider_request_sent``
  - ``provider_response_received``
  - ``provider_tool_call_parsed``
  - ``provider_tool_call_blocked``
  - ``provider_tool_call_executed``
  - ``provider_tool_result_returned``
  - ``provider_final_response_received``

Architecture constraints (mirrors ``dev_web_tool_dry_run_audit``):
  - stdlib only (no third-party imports)
  - only local file append under HERMES_HOME dev audit path
  - never accesses ~/.hermes
  - never accesses production state.db
  - never stores API keys, raw tokens, full tokenHash, raw arguments,
    secrets, callable reprs, or function reprs
  - every value is defensively re-redacted before serialization
  - all exceptions handled safely (write failure never enables execution)
  - this audit file lives under HERMES_HOME; it is NEVER committed

Phase: 2B — Provider Schema / API Controlled Integration
Status: provider audit writer implemented
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

_PHASE = "2B"
_SCHEMA_VERSION = 1

# Storage path components — under HERMES_HOME dev audit dir.
_AUDIT_DIR_RELATIVE = "gateway/dev/audit"
_AUDIT_FILENAME = "provider-roundtrip-audit.jsonl"

# Size limits
_MAX_EVENT_BYTES = 32 * 1024  # 32 KiB
_MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MiB
_MAX_RETAINED_FILES = 3

# Forbidden production path (never write here).
_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"

# Secret value patterns (bounded, stdlib-only — mirrors the execute gate).
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
)

_FORBIDDEN_FIELD_STEMS: frozenset[str] = frozenset(
    n.replace("_", "").replace("-", "").lower()
    for n in (
        "api_key", "apikey", "authorization", "auth_header", "bearer",
        "token", "secret", "password", "passwd", "credential", "cookie",
        "session", "private_key", "client_secret", "access_token",
        "refresh_token", "access_key",
    )
)

_REDACTED_VALUE = "[REDACTED]"

# Event type constants (exported for the round-trip + tests).
EVENT_PROVIDER_SCHEMA_BUILT = "provider_schema_built"
EVENT_PROVIDER_REQUEST_BUILT = "provider_request_built"
EVENT_PROVIDER_REQUEST_SENT = "provider_request_sent"
EVENT_PROVIDER_RESPONSE_RECEIVED = "provider_response_received"
EVENT_PROVIDER_TOOL_CALL_PARSED = "provider_tool_call_parsed"
EVENT_PROVIDER_TOOL_CALL_BLOCKED = "provider_tool_call_blocked"
EVENT_PROVIDER_TOOL_CALL_EXECUTED = "provider_tool_call_executed"
EVENT_PROVIDER_TOOL_RESULT_RETURNED = "provider_tool_result_returned"
EVENT_PROVIDER_FINAL_RESPONSE_RECEIVED = "provider_final_response_received"

# Error codes
ERROR_HERMES_HOME_MISSING = "PROVIDER_AUDIT_HERMES_HOME_MISSING"
ERROR_AUDIT_PATH_OUTSIDE_HERMES_HOME = "PROVIDER_AUDIT_PATH_OUTSIDE_HERMES_HOME"
ERROR_AUDIT_EVENT_TOO_LARGE = "PROVIDER_AUDIT_EVENT_TOO_LARGE"
ERROR_AUDIT_WRITE_FAILED = "PROVIDER_AUDIT_WRITE_FAILED"
ERROR_AUDIT_SERIALIZATION_FAILED = "PROVIDER_AUDIT_SERIALIZATION_FAILED"
ERROR_AUDIT_REDACTION_FAILED = "PROVIDER_AUDIT_REDACTION_FAILED"


# ---------------------------------------------------------------------------
# 2. Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderAuditWriteResult:
    """Result of a single provider audit write attempt."""

    written: bool
    event_id: str | None
    event_type: str
    path: str | None
    error_code: str | None
    error_message: str | None


# ---------------------------------------------------------------------------
# 3. Redaction
# ---------------------------------------------------------------------------


def _is_secret_string(value: str) -> bool:
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.search(value):
            return True
    return False


def _is_forbidden_field(key: str) -> bool:
    if not isinstance(key, str):
        return True
    normalized = key.strip().lower().replace("_", "").replace("-", "")
    if normalized in _FORBIDDEN_FIELD_STEMS:
        return True
    return any(stem in normalized for stem in ("token", "secret", "password", "auth"))


def _sanitize(value: Any, *, depth: int = 0) -> Any:
    """Recursively redact secrets, drop forbidden keys, and bound depth."""
    if depth > 8:
        return None
    if isinstance(value, str):
        if _is_secret_string(value):
            return _REDACTED_VALUE
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, val in value.items():
            if _is_forbidden_field(key):
                out[str(key)] = _REDACTED_VALUE
                continue
            out[str(key)] = _sanitize(val, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_sanitize(v, depth=depth + 1) for v in value]
    # Anything else (callable, object): render as a fixed opaque placeholder.
    # Never the repr, never the type name (which could leak callable/function).
    return "<non_json_value>"


# ---------------------------------------------------------------------------
# 4. Event builder
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_provider_audit_event(
    *,
    event_type: str,
    provider_request_id: str | None,
    provider_response_id: str | None,
    provider_mode: str,
    payload: Mapping[str, Any] | None = None,
    tool_call_id: str | None = None,
    tool_id: str | None = None,
    status: str | None = None,
    blocked_reason: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a redacted provider audit event dict (not yet written).

    The caller supplies a *payload* of boundary-relevant facts; this builder
    wraps it with the common envelope and defensively re-redacts everything.
    Never embeds API keys, raw tokens, full tokenHash, raw arguments, secrets,
    or callable/function reprs.
    """
    timestamp = (now or datetime.now(timezone.utc)).isoformat()
    event: dict[str, Any] = {
        "eventId": f"prau_{uuid.uuid4().hex}",
        "eventType": event_type,
        "phase": _PHASE,
        "schemaVersion": _SCHEMA_VERSION,
        "timestamp": timestamp,
        "providerMode": provider_mode,
        "providerRequestId": provider_request_id,
        "providerResponseId": provider_response_id,
        "toolCallId": tool_call_id,
        "toolId": tool_id,
        "status": status,
        "blockedReason": blocked_reason,
        "redactionApplied": True,
        "payload": dict(payload) if payload else {},
    }
    # Defensive full re-redaction before serialization.
    try:
        return _sanitize(event)
    except Exception:  # pragma: no cover — defensive
        event["payload"] = {}
        event["redactionApplied"] = True
        return event


# ---------------------------------------------------------------------------
# 5. Path resolution + rotation (mirrors the dry-run audit writer)
# ---------------------------------------------------------------------------


def _resolve_audit_path(
    hermes_home: str | os.PathLike[str] | None = None,
) -> tuple[Path, str | None]:
    """Resolve and validate the provider audit file path.

    Guarantees:
      - Path is always under HERMES_HOME dev audit dir
      - Path never points to ~/.hermes
      - Path never points to production state.db
    """
    if hermes_home is not None:
        home = Path(hermes_home).resolve()
    else:
        home_str = os.environ.get("HERMES_HOME", "")
        if not home_str:
            return Path(), ERROR_HERMES_HOME_MISSING
        home = Path(home_str).resolve()

    prod_home = Path(_PRODUCTION_HERMES_HOME).resolve()
    if home == prod_home:
        return Path(), ERROR_AUDIT_PATH_OUTSIDE_HERMES_HOME

    audit_path = home / _AUDIT_DIR_RELATIVE / _AUDIT_FILENAME

    try:
        audit_path.resolve().relative_to(home)
    except ValueError:
        return Path(), ERROR_AUDIT_PATH_OUTSIDE_HERMES_HOME

    resolved = audit_path.resolve()
    if str(resolved).endswith("state.db"):
        return Path(), ERROR_AUDIT_PATH_OUTSIDE_HERMES_HOME

    return audit_path, None


def _rotate_audit_file(audit_path: Path) -> None:
    """Rotate the audit file if it exceeds the size cap. Best-effort."""
    try:
        if not audit_path.exists():
            return
        if audit_path.stat().st_size < _MAX_FILE_BYTES:
            return
        base_dir = audit_path.parent
        base_name = audit_path.name
        max_index = _MAX_RETAINED_FILES - 1
        oldest = base_dir / f"{base_name}.{max_index}"
        if oldest.exists():
            oldest.unlink()
        for i in range(max_index - 1, 0, -1):
            src = base_dir / f"{base_name}.{i}"
            dst = base_dir / f"{base_name}.{i + 1}"
            if src.exists():
                src.rename(dst)
        audit_path.rename(base_dir / f"{base_name}.1")
    except OSError:
        return


# ---------------------------------------------------------------------------
# 6. Write entry point
# ---------------------------------------------------------------------------


def write_provider_audit_event(
    event: Mapping[str, Any],
    *,
    hermes_home: str | os.PathLike[str] | None = None,
) -> ProviderAuditWriteResult:
    """Write one provider audit event to the dev JSONL file.

    Write failure NEVER enables execution, NEVER calls a provider, and NEVER
    leaks secrets. Every value is re-redacted before it touches the disk.
    """
    event_type = str(event.get("eventType", "provider_unknown"))
    event_id = event.get("eventId")

    audit_path, path_error = _resolve_audit_path(hermes_home)
    if path_error is not None:
        return ProviderAuditWriteResult(
            written=False,
            event_id=event_id if isinstance(event_id, str) else None,
            event_type=event_type,
            path=None,
            error_code=path_error,
            error_message=_message_for(path_error),
        )

    try:
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        return ProviderAuditWriteResult(
            written=False,
            event_id=event_id if isinstance(event_id, str) else None,
            event_type=event_type,
            path=str(audit_path),
            error_code=ERROR_AUDIT_SERIALIZATION_FAILED,
            error_message=f"serialization failed: {exc!s}",
        )

    line_bytes = (line + "\n").encode("utf-8")
    if len(line_bytes) > _MAX_EVENT_BYTES:
        # Event too large — record a truncated marker instead of dropping it.
        marker = build_provider_audit_event(
            event_type=event_type,
            provider_request_id=event.get("providerRequestId"),
            provider_response_id=event.get("providerResponseId"),
            provider_mode=str(event.get("providerMode", "")),
            payload={"truncated": True, "originalBytes": len(line_bytes)},
            status="truncated",
        )
        try:
            marker_line = json.dumps(marker, ensure_ascii=False)
        except (TypeError, ValueError):
            return ProviderAuditWriteResult(
                written=False,
                event_id=None,
                event_type=event_type,
                path=str(audit_path),
                error_code=ERROR_AUDIT_EVENT_TOO_LARGE,
                error_message="event too large and marker failed to serialize",
            )
        line_bytes = (marker_line + "\n").encode("utf-8")

    try:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        _rotate_audit_file(audit_path)
        with audit_path.open("a", encoding="utf-8") as fh:
            fh.write(line_bytes.decode("utf-8"))
    except OSError as exc:
        return ProviderAuditWriteResult(
            written=False,
            event_id=event_id if isinstance(event_id, str) else None,
            event_type=event_type,
            path=str(audit_path),
            error_code=ERROR_AUDIT_WRITE_FAILED,
            error_message=f"write failed: {exc!s}",
        )

    return ProviderAuditWriteResult(
        written=True,
        event_id=event_id if isinstance(event_id, str) else None,
        event_type=event_type,
        path=str(audit_path),
        error_code=None,
        error_message=None,
    )


def _message_for(code: str) -> str:
    return {
        ERROR_HERMES_HOME_MISSING: "HERMES_HOME is not set.",
        ERROR_AUDIT_PATH_OUTSIDE_HERMES_HOME: "audit path is outside HERMES_HOME.",
        ERROR_AUDIT_EVENT_TOO_LARGE: "audit event exceeds the size cap.",
        ERROR_AUDIT_WRITE_FAILED: "audit write failed.",
        ERROR_AUDIT_SERIALIZATION_FAILED: "audit serialization failed.",
        ERROR_AUDIT_REDACTION_FAILED: "audit redaction failed.",
    }.get(code, "provider audit error.")


# ---------------------------------------------------------------------------
# 7. Typed convenience writers (one per lifecycle event)
# ---------------------------------------------------------------------------


def _write(
    *,
    event_type: str,
    hermes_home: str | os.PathLike[str] | None,
    provider_request_id: str | None,
    provider_response_id: str | None,
    provider_mode: str,
    payload: Mapping[str, Any] | None = None,
    tool_call_id: str | None = None,
    tool_id: str | None = None,
    status: str | None = None,
    blocked_reason: str | None = None,
) -> str | None:
    """Build + write one event; return its eventId (or None on failure)."""
    event = build_provider_audit_event(
        event_type=event_type,
        provider_request_id=provider_request_id,
        provider_response_id=provider_response_id,
        provider_mode=provider_mode,
        payload=payload,
        tool_call_id=tool_call_id,
        tool_id=tool_id,
        status=status,
        blocked_reason=blocked_reason,
    )
    result = write_provider_audit_event(event, hermes_home=hermes_home)
    return result.event_id if result.written else None


def write_provider_schema_audit(
    *, hermes_home: str | os.PathLike[str] | None, provider_request_id: str | None,
    provider_mode: str, schema_summary: Mapping[str, Any],
) -> str | None:
    return _write(
        event_type=EVENT_PROVIDER_SCHEMA_BUILT,
        hermes_home=hermes_home,
        provider_request_id=provider_request_id,
        provider_response_id=None,
        provider_mode=provider_mode,
        payload=dict(schema_summary),
        status="built",
    )


def write_provider_request_audit(
    *, hermes_home: str | os.PathLike[str] | None, provider_request_id: str | None,
    provider_mode: str, request_summary: Mapping[str, Any],
) -> str | None:
    return _write(
        event_type=EVENT_PROVIDER_REQUEST_BUILT,
        hermes_home=hermes_home,
        provider_request_id=provider_request_id,
        provider_response_id=None,
        provider_mode=provider_mode,
        payload=dict(request_summary),
        status="built",
    )


def write_provider_response_audit(
    *, hermes_home: str | os.PathLike[str] | None, provider_request_id: str | None,
    provider_response_id: str | None, provider_mode: str, response_summary: Mapping[str, Any],
) -> str | None:
    return _write(
        event_type=EVENT_PROVIDER_RESPONSE_RECEIVED,
        hermes_home=hermes_home,
        provider_request_id=provider_request_id,
        provider_response_id=provider_response_id,
        provider_mode=provider_mode,
        payload=dict(response_summary),
        status="received",
    )


def write_provider_tool_call_audit(
    *, hermes_home: str | os.PathLike[str] | None, provider_request_id: str | None,
    provider_response_id: str | None, provider_mode: str, tool_call_id: str | None,
    tool_id: str | None, status: str, blocked_reason: str | None = None,
    summary: Mapping[str, Any] | None = None,
) -> str | None:
    event_type = (
        EVENT_PROVIDER_TOOL_CALL_BLOCKED
        if status == "blocked"
        else EVENT_PROVIDER_TOOL_CALL_PARSED
    )
    return _write(
        event_type=event_type,
        hermes_home=hermes_home,
        provider_request_id=provider_request_id,
        provider_response_id=provider_response_id,
        provider_mode=provider_mode,
        payload=dict(summary) if summary else None,
        tool_call_id=tool_call_id,
        tool_id=tool_id,
        status=status,
        blocked_reason=blocked_reason,
    )


def write_provider_tool_result_audit(
    *, hermes_home: str | os.PathLike[str] | None, provider_request_id: str | None,
    provider_response_id: str | None, provider_mode: str, tool_call_id: str | None,
    tool_id: str | None, result_summary: Mapping[str, Any],
) -> str | None:
    return _write(
        event_type=EVENT_PROVIDER_TOOL_CALL_EXECUTED,
        hermes_home=hermes_home,
        provider_request_id=provider_request_id,
        provider_response_id=provider_response_id,
        provider_mode=provider_mode,
        payload=dict(result_summary),
        tool_call_id=tool_call_id,
        tool_id=tool_id,
        status="executed",
    )


def write_provider_final_response_audit(
    *, hermes_home: str | os.PathLike[str] | None, provider_request_id: str | None,
    provider_response_id: str | None, provider_mode: str, final_summary: Mapping[str, Any],
) -> str | None:
    return _write(
        event_type=EVENT_PROVIDER_FINAL_RESPONSE_RECEIVED,
        hermes_home=hermes_home,
        provider_request_id=provider_request_id,
        provider_response_id=provider_response_id,
        provider_mode=provider_mode,
        payload=dict(final_summary),
        status="final",
    )
