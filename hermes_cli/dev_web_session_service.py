"""Dev Web API session query service.

Read-only service that queries session data from the development state.db
using SessionDB(read_only=True). All queries are side-effect-free.

Importing this module has no side effects.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_state import SessionDB


# ── Custom exceptions ──


class SessionStoreUnavailableError(Exception):
    """Raised when the session database is not available."""


class SessionNotFoundError(Exception):
    """Raised when a requested session does not exist."""


# ── Constants ──

# Session ID maximum length for API input validation
_MAX_SESSION_ID_LENGTH = 256

# Maximum preview length matching the frozen OpenAPI contract
_MAX_PREVIEW_LENGTH = 63


# ── Time conversion ──


def _unix_to_iso(timestamp: float | None) -> str | None:
    """Convert a Unix timestamp (seconds) to ISO 8601 UTC string.

    Returns None for None input or unparseable values.
    """
    if timestamp is None:
        return None
    try:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OSError, OverflowError):
        return None


# ── DTO transformers (explicit whitelist) ──


def _build_preview(raw_preview: str | None) -> str | None:
    """Build a safe preview string from the raw SQL result.

    Returns None if the preview is empty or whitespace-only.
    Truncates to _MAX_PREVIEW_LENGTH characters, appending '...' when
    the original text exceeds that limit.
    """
    if not raw_preview or not raw_preview.strip():
        return None
    text = raw_preview.strip()
    if len(text) > _MAX_PREVIEW_LENGTH:
        # Leave room for '...'
        return text[: _MAX_PREVIEW_LENGTH - 3] + "..."
    return text


def _transform_list_item(row: dict[str, Any]) -> dict[str, Any]:
    """Transform a database row into a SessionListItem DTO.

    Uses an explicit whitelist — only safe fields are included.
    """
    return {
        "id": row["id"],
        "title": row.get("title") or None,
        "source": row["source"],
        "model": row.get("model") or None,
        "messageCount": row.get("message_count", 0),
        "toolCallCount": row.get("tool_call_count", 0),
        "archived": bool(row.get("archived", 0)),
        "startedAt": _unix_to_iso(row.get("started_at")),
        "endedAt": _unix_to_iso(row.get("ended_at")),
        "lastActiveAt": _unix_to_iso(row.get("last_active")),
        "preview": _build_preview(row.get("preview")),
    }


def _transform_detail(
    row: dict[str, Any],
    last_active: float | None = None,
) -> dict[str, Any]:
    """Transform a database row into a SessionDetail DTO.

    Uses an explicit whitelist — only safe fields are included.
    Sensitive fields (system_prompt, model_config, user_id, cwd,
    billing_*) are never included.
    """
    return {
        "id": row["id"],
        "title": row.get("title") or None,
        "source": row["source"],
        "model": row.get("model") or None,
        "messageCount": row.get("message_count", 0),
        "toolCallCount": row.get("tool_call_count", 0),
        "inputTokens": row.get("input_tokens"),
        "outputTokens": row.get("output_tokens"),
        "archived": bool(row.get("archived", 0)),
        "startedAt": _unix_to_iso(row.get("started_at")),
        "endedAt": _unix_to_iso(row.get("ended_at")),
        "lastActiveAt": _unix_to_iso(
            last_active if last_active is not None
            else row.get("last_active", row.get("started_at"))
        ),
        "endReason": row.get("end_reason") or None,
    }


# ── LIKE escape helper ──


def _escape_like(value: str) -> str:
    """Escape SQL LIKE wildcard characters in a search value."""
    return (
        value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )


# ── Session query service ──


class DevSessionQueryService:
    """Read-only session query service for the Dev Web API.

    Opens a short-lived SessionDB(read_only=True) connection per query
    and closes it immediately afterwards.
    """

    def __init__(self, state_db_path: Path) -> None:
        self._db_path = state_db_path

    def is_available(self) -> bool:
        """Check whether the session database file exists and is readable."""
        return self._db_path.exists() and self._db_path.is_file()

    # ── List sessions ──

    def list_sessions(
        self,
        *,
        query: str | None = None,
        offset: int = 0,
        limit: int = 30,
        order: str = "recent",
        source: str | None = None,
        archived: str = "exclude",
    ) -> dict[str, Any]:
        """List sessions with pagination and optional search/filter.

        Returns a dict with 'items' (list of DTOs) and 'page' (pagination
        metadata).

        Raises:
            SessionStoreUnavailableError: If the database is not available.
        """
        if not self.is_available():
            raise SessionStoreUnavailableError()

        db: SessionDB | None = None
        try:
            db = SessionDB(db_path=self._db_path, read_only=True)
            return self._execute_list_query(
                db, query=query, offset=offset, limit=limit,
                order=order, source=source, archived=archived,
            )
        except SessionStoreUnavailableError:
            raise
        except Exception as exc:
            # Map any unexpected database error to unavailable
            raise SessionStoreUnavailableError() from exc
        finally:
            if db is not None:
                db.close()

    def _execute_list_query(
        self,
        db: SessionDB,
        *,
        query: str | None,
        offset: int,
        limit: int,
        order: str,
        source: str | None,
        archived: str,
    ) -> dict[str, Any]:
        """Build and execute the session list SQL queries."""
        where_clauses: list[str] = []
        params: list[Any] = []

        # Source filter
        if source:
            where_clauses.append("s.source = ?")
            params.append(source)

        # Archived filter
        if archived == "exclude":
            where_clauses.append("s.archived = 0")
        elif archived == "only":
            where_clauses.append("s.archived = 1")
        # "include" → no filter

        # Search filter (title + session ID)
        if query and query.strip():
            escaped = _escape_like(query.strip())
            like_pattern = f"%{escaped}%"
            where_clauses.append(
                "(s.title LIKE ? ESCAPE '\\' OR s.id LIKE ? ESCAPE '\\')"
            )
            params.extend([like_pattern, like_pattern])

        where_sql = (
            f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        )

        # Order clause (whitelist — no user input in ORDER BY)
        if order == "created":
            order_sql = "s.started_at DESC, s.id DESC"
        else:
            # "recent" — use correlated subquery for last_active
            order_sql = (
                "COALESCE("
                "  (SELECT MAX(m2.timestamp) FROM messages m2"
                "   WHERE m2.session_id = s.id),"
                "  s.started_at"
                ") DESC, s.started_at DESC, s.id DESC"
            )

        # Count query (same WHERE, no LIMIT/OFFSET)
        count_sql = f"SELECT COUNT(*) FROM sessions s {where_sql}"

        # Data query with preview and last_active
        data_sql = f"""
            SELECT
                s.id, s.title, s.source, s.model,
                s.message_count, s.tool_call_count,
                s.archived, s.started_at, s.ended_at,
                COALESCE(
                    (SELECT SUBSTR(
                        REPLACE(REPLACE(m.content, X'0A', ' '), X'0D', ' '),
                        1, 63
                     )
                     FROM messages m
                     WHERE m.session_id = s.id
                       AND m.role = 'user'
                       AND m.content IS NOT NULL
                     ORDER BY m.timestamp, m.id
                     LIMIT 1),
                    ''
                ) AS preview,
                COALESCE(
                    (SELECT MAX(m2.timestamp)
                     FROM messages m2
                     WHERE m2.session_id = s.id),
                    s.started_at
                ) AS last_active
            FROM sessions s
            {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
        """

        with db._lock:
            total_row = db._conn.execute(count_sql, params).fetchone()
            total = total_row[0] if total_row else 0
            rows = db._conn.execute(
                data_sql, params + [limit, offset]
            ).fetchall()

        items = [_transform_list_item(dict(r)) for r in rows]

        return {
            "items": items,
            "page": {
                "offset": offset,
                "limit": limit,
                "total": total,
                "hasMore": (offset + limit) < total,
            },
        }

    # ── Get session detail ──

    def get_session(self, session_id: str) -> dict[str, Any]:
        """Get a single session's detail by ID.

        Returns a DTO dict.

        Raises:
            SessionStoreUnavailableError: If the database is not available.
            SessionNotFoundError: If the session does not exist.
        """
        if not self.is_available():
            raise SessionStoreUnavailableError()

        db: SessionDB | None = None
        try:
            db = SessionDB(db_path=self._db_path, read_only=True)
            return self._execute_detail_query(db, session_id)
        except SessionNotFoundError:
            raise
        except SessionStoreUnavailableError:
            raise
        except Exception as exc:
            raise SessionStoreUnavailableError() from exc
        finally:
            if db is not None:
                db.close()

    def _execute_detail_query(
        self, db: SessionDB, session_id: str,
    ) -> dict[str, Any]:
        """Execute the session detail query."""
        # Use public get_session() for the base row
        row = db.get_session(session_id)
        if row is None:
            raise SessionNotFoundError()

        # Compute last_active via a separate lightweight query
        with db._lock:
            la_row = db._conn.execute(
                "SELECT MAX(timestamp) AS last_active "
                "FROM messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        last_active = la_row["last_active"] if la_row else None

        return _transform_detail(dict(row), last_active=last_active)

    # ── Validation helpers ──

    @staticmethod
    def validate_session_id(session_id: str) -> str | None:
        """Validate a session ID string.

        Returns None if valid, or an error description string if invalid.
        """
        if not session_id:
            return "Session ID is required."
        if len(session_id) > _MAX_SESSION_ID_LENGTH:
            return "Session ID is too long."
        # Reject control characters
        if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in session_id):
            return "Session ID contains invalid characters."
        return None
