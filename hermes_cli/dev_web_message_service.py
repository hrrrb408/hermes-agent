"""Dev Web API message query service.

Read-only service that queries message data from the development state.db
using SessionDB(read_only=True). All queries are side-effect-free.

Importing this module has no side effects.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_state import SessionDB


# ── Custom exceptions ──


class MessageStoreUnavailableError(Exception):
    """Raised when the session/message database is not available."""


class MessageSessionNotFoundError(Exception):
    """Raised when a requested session does not exist for message queries."""


# ── Constants ──

# Maximum number of messages per page (frozen contract)
_MAX_LIMIT = 100

# Default number of messages per page
_DEFAULT_LIMIT = 50

# Maximum safe text length for a single message
_MAX_MESSAGE_CHARS = 50_000

# Maximum tool call arguments display length
_MAX_TOOL_CALL_ARGS_CHARS = 200

# Safe role whitelist
_SAFE_ROLES = frozenset({"user", "assistant", "tool", "system"})


# ── Time conversion (reuse pattern from session service) ──


def _unix_to_iso(timestamp: float | None) -> str | None:
    """Convert a Unix timestamp (seconds) to ISO 8601 UTC string."""
    if timestamp is None:
        return None
    try:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OSError, OverflowError):
        return None


# ── Content transformers (explicit whitelist) ──


def _normalize_role(raw_role: str | None) -> str:
    """Normalize a message role to a safe value.

    Returns 'unknown' for null, empty, or unrecognized roles.
    """
    if not raw_role:
        return "unknown"
    lowered = raw_role.strip().lower()
    if lowered in _SAFE_ROLES:
        return lowered
    return "unknown"


def _sanitize_text(text: str, max_chars: int = _MAX_MESSAGE_CHARS) -> tuple[str, bool]:
    """Sanitize text content for safe display.

    Returns (sanitized_text, was_truncated).
    Removes control characters except newlines and tabs.
    """
    if not text:
        return "", False

    # Remove null bytes and other non-displayable control characters
    # but preserve newline (0x0A), carriage return (0x0D), tab (0x09)
    cleaned_chars = []
    for ch in text:
        code = ord(ch)
        if code == 0:
            # Strip null bytes (part of \x00json: prefix handling)
            continue
        if code < 0x20 and code not in (0x09, 0x0A, 0x0D):
            # Replace other control characters with space
            cleaned_chars.append(" ")
        elif code == 0x7F:
            cleaned_chars.append(" ")
        else:
            cleaned_chars.append(ch)

    cleaned = "".join(cleaned_chars)

    if len(cleaned) > max_chars:
        return cleaned[:max_chars], True
    return cleaned, False


def _extract_safe_text_from_decoded_content(decoded: Any) -> str | None:
    """Extract safe text from decoded structured content.

    Handles the content after _decode_content() has run, which means:
    - Plain text strings are returned as-is
    - Structured content (lists/dicts) came from \x00json: prefix

    Returns None if no safe text can be extracted.
    """
    if decoded is None:
        return None
    if isinstance(decoded, str):
        return decoded
    if isinstance(decoded, list):
        # Multimodal content: [{"type": "text", "text": "..."}, ...]
        text_parts = []
        for part in decoded:
            if isinstance(part, dict):
                # Only extract from type=text parts
                if part.get("type") == "text" and isinstance(part.get("text"), str):
                    text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        if text_parts:
            return "\n".join(text_parts)
        return None
    if isinstance(decoded, dict):
        # Unknown dict structure — do not extract
        return None
    return None


def _transform_content(raw_content: Any) -> dict[str, Any]:
    """Transform raw message content into a safe content DTO.

    Content may be:
    - A plain string (most common)
    - A parsed Python object (from \x00json: decoded by SessionDB)
    - None (empty message)

    Returns a content object with type discriminator:
    - {"type": "text", "text": "...", "truncated": false}
    - {"type": "empty"}
    - {"type": "unsupported"}
    """
    if raw_content is None:
        return {"type": "empty"}

    # If it's still a string (not decoded to structured), treat as text
    if isinstance(raw_content, str):
        if not raw_content.strip():
            return {"type": "empty"}
        safe_text, truncated = _sanitize_text(raw_content)
        if not safe_text:
            return {"type": "empty"}
        result: dict[str, Any] = {"type": "text", "text": safe_text}
        if truncated:
            result["truncated"] = True
        return result

    # Structured content (decoded from \x00json:)
    safe_text = _extract_safe_text_from_decoded_content(raw_content)
    if safe_text is not None and safe_text.strip():
        cleaned, truncated = _sanitize_text(safe_text)
        if cleaned:
            result = {"type": "text", "text": cleaned}
            if truncated:
                result["truncated"] = True
            return result

    # Could not extract safe text
    return {"type": "unsupported"}


def _truncate_tool_call_args(args_str: str, max_chars: int = _MAX_TOOL_CALL_ARGS_CHARS) -> str:
    """Truncate tool call arguments string for safe display."""
    if len(args_str) <= max_chars:
        return args_str
    return args_str[: max_chars - 3] + "..."


def _transform_tool_calls(raw_tool_calls: list[Any] | None) -> list[dict[str, Any]] | None:
    """Transform tool_calls into a safe DTO.

    Returns None if no tool calls. Otherwise returns a list of safe tool call
    objects with name and truncated arguments.
    """
    if not raw_tool_calls:
        return None

    safe_calls = []
    for tc in raw_tool_calls:
        if not isinstance(tc, dict):
            continue

        func = tc.get("function", {})
        if not isinstance(func, dict):
            func = {}

        # Safely extract function name
        func_name = func.get("name", "")
        if not isinstance(func_name, str):
            func_name = str(func_name)

        # Safely extract and truncate arguments
        raw_args = func.get("arguments", "")
        if not isinstance(raw_args, str):
            try:
                raw_args = json.dumps(raw_args)
            except (TypeError, ValueError):
                raw_args = "{}"

        safe_calls.append({
            "id": tc.get("id", ""),
            "type": "function",
            "function": {
                "name": func_name,
                "arguments": _truncate_tool_call_args(raw_args),
            },
        })

    return safe_calls if safe_calls else None


def _transform_message(row: dict[str, Any]) -> dict[str, Any]:
    """Transform a database message row into a MessageItem DTO.

    Uses an explicit whitelist — only safe fields are included.
    Sensitive fields (reasoning, reasoning_content, codex_*,
    observed, active, platform_message_id) are never included.
    """
    role = _normalize_role(row.get("role"))
    content = _transform_content(row.get("content"))
    tool_calls = _transform_tool_calls(row.get("tool_calls"))

    dto: dict[str, Any] = {
        "id": row["id"],
        "role": role,
        "content": content,
        "timestamp": _unix_to_iso(row.get("timestamp")),
    }

    # Optional fields (nullable in contract)
    token_count = row.get("token_count")
    if token_count is not None:
        dto["tokenCount"] = token_count

    finish_reason = row.get("finish_reason")
    if finish_reason is not None:
        dto["finishReason"] = finish_reason

    if tool_calls is not None:
        dto["toolCalls"] = tool_calls

    tool_call_id = row.get("tool_call_id")
    if tool_call_id is not None:
        dto["toolCallId"] = tool_call_id

    tool_name = row.get("tool_name")
    if tool_name is not None:
        dto["toolName"] = tool_name

    return dto


# ── Message query service ──


class DevMessageQueryService:
    """Read-only message query service for the Dev Web API.

    Opens a short-lived SessionDB(read_only=True) connection per query
    and closes it immediately afterwards.
    """

    def __init__(self, state_db_path: Path) -> None:
        self._db_path = state_db_path

    def is_available(self) -> bool:
        """Check whether the session database file exists and is readable."""
        return self._db_path.exists() and self._db_path.is_file()

    def get_messages(
        self,
        session_id: str,
        *,
        limit: int = _DEFAULT_LIMIT,
        offset: int = 0,
        before: int | None = None,
        after: int | None = None,
    ) -> dict[str, Any]:
        """Get messages for a session with pagination.

        Returns a dict with 'items' (list of DTOs) and 'page' (pagination
        metadata).

        Raises:
            MessageStoreUnavailableError: If the database is not available.
            MessageSessionNotFoundError: If the session does not exist.
        """
        if not self.is_available():
            raise MessageStoreUnavailableError()

        db: SessionDB | None = None
        try:
            db = SessionDB(db_path=self._db_path, read_only=True)
            return self._execute_message_query(
                db, session_id, limit=limit, offset=offset,
                before=before, after=after,
            )
        except (MessageSessionNotFoundError, MessageStoreUnavailableError):
            raise
        except Exception as exc:
            raise MessageStoreUnavailableError() from exc
        finally:
            if db is not None:
                db.close()

    def _execute_message_query(
        self,
        db: SessionDB,
        session_id: str,
        *,
        limit: int,
        offset: int,
        before: int | None,
        after: int | None,
    ) -> dict[str, Any]:
        """Execute the message query with pagination."""
        # Verify session exists
        session_row = db.get_session(session_id)
        if session_row is None:
            raise MessageSessionNotFoundError()

        # Build query with optional anchor filters
        where_clauses = ["session_id = ?", "active = 1"]
        params: list[Any] = [session_id]

        if before is not None:
            where_clauses.append("id < ?")
            params.append(before)
        if after is not None:
            where_clauses.append("id > ?")
            params.append(after)

        where_sql = " AND ".join(where_clauses)

        # Count query
        count_sql = f"SELECT COUNT(*) FROM messages WHERE {where_sql}"

        # Data query — select safe columns via whitelist, not SELECT *
        # We need all columns for the DTO transformer, but we'll whitelist
        # in the transformer, not in SQL (some columns like tool_calls are
        # needed for display).
        data_sql = (
            f"SELECT * FROM messages WHERE {where_sql} "
            f"ORDER BY id ASC LIMIT ? OFFSET ?"
        )

        with db._lock:
            total_row = db._conn.execute(count_sql, params).fetchone()
            total = total_row[0] if total_row else 0

            rows = db._conn.execute(
                data_sql, params + [limit, offset]
            ).fetchall()

        # Decode content and tool_calls (same as get_messages does)
        decoded_rows = []
        for row in rows:
            msg = dict(row)
            if "content" in msg:
                msg["content"] = db._decode_content(msg["content"])
            if msg.get("tool_calls"):
                try:
                    msg["tool_calls"] = json.loads(msg["tool_calls"])
                except (json.JSONDecodeError, TypeError):
                    msg["tool_calls"] = []
            decoded_rows.append(msg)

        items = [_transform_message(msg) for msg in decoded_rows]

        # Compute messages_before and messages_after for anchor pagination
        messages_before = None
        messages_after = None
        if before is not None:
            # Count messages before the anchor
            with db._lock:
                before_count = db._conn.execute(
                    "SELECT COUNT(*) FROM messages "
                    "WHERE session_id = ? AND id < ? AND active = 1",
                    (session_id, before),
                ).fetchone()
            messages_before = before_count[0] if before_count else 0

        if after is not None:
            # Count messages after the anchor
            with db._lock:
                after_count = db._conn.execute(
                    "SELECT COUNT(*) FROM messages "
                    "WHERE session_id = ? AND id > ? AND active = 1",
                    (session_id, after),
                ).fetchone()
            messages_after = after_count[0] if after_count else 0

        page: dict[str, Any] = {
            "offset": offset,
            "limit": limit,
            "total": total,
            "hasMore": (offset + limit) < total,
        }
        if messages_before is not None:
            page["messagesBefore"] = messages_before
        if messages_after is not None:
            page["messagesAfter"] = messages_after

        return {
            "items": items,
            "page": page,
        }
