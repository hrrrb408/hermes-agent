"""Dev Web API Agent Run Audit Trail.

Records metadata-only audit events for Agent Run lifecycle.
Uses state.db agent_run_audit table for transactional consistency.

Forbidden fields (must NEVER appear in audit):
    - Complete user message
    - Complete assistant response
    - Complete system prompt
    - API key, authorization, base URL
    - Local absolute paths
    - Traceback
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ── SQL ──

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agent_run_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'dev-webui',
    action TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    cancel_requested INTEGER DEFAULT 0,
    tools_enabled INTEGER DEFAULT 0,
    auto_memory_enabled INTEGER DEFAULT 0,
    input_token_count INTEGER,
    output_token_count INTEGER,
    total_token_count INTEGER,
    duration_ms INTEGER,
    error_code TEXT,
    dev_only INTEGER DEFAULT 1
)
"""

_CREATE_INDEXES_SQL = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_audit_run_id ON agent_run_audit (run_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_session_id ON agent_run_audit (session_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_created_at ON agent_run_audit (created_at)",
    "CREATE INDEX IF NOT EXISTS idx_audit_status ON agent_run_audit (status)",
]


class AgentRunAuditError(Exception):
    """Audit write failure."""


class AgentRunAudit:
    """Agent Run audit trail writer.

    Writes to state.db agent_run_audit table.
    Each Run creates an initial audit row on creation, then updates
    it on completion/cancellation/failure.
    """

    def __init__(self, state_db_path: Path) -> None:
        self._db_path = str(state_db_path)
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create the audit table and indexes if they don't exist."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(_CREATE_TABLE_SQL)
                for idx_sql in _CREATE_INDEXES_SQL:
                    conn.execute(idx_sql)
                conn.commit()
        except Exception as exc:
            logger.warning("Agent run audit table creation failed: %s", exc)

    def record_created(
        self,
        *,
        run_id: str,
        session_id: str,
        request_id: str,
        model: str,
        provider: str,
    ) -> None:
        """Record run creation audit event.

        This is the initial audit row. Must be created BEFORE the run starts.
        """
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO agent_run_audit
                    (request_id, run_id, session_id, action, model, provider,
                     status, created_at, cancel_requested, tools_enabled,
                     auto_memory_enabled, dev_only)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 1)
                    """,
                    (
                        request_id,
                        run_id,
                        session_id,
                        "run.created",
                        model,
                        provider,
                        "CREATED",
                        _utc_now_iso(),
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.warning("Agent run audit create failed: %s", exc)
            raise AgentRunAuditError(f"Failed to create audit record: {exc}") from exc

    def record_started(
        self,
        *,
        run_id: str,
    ) -> None:
        """Record run started audit event."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    UPDATE agent_run_audit
                    SET action = 'run.started',
                        status = 'STARTING',
                        started_at = ?
                    WHERE run_id = ?
                    """,
                    (_utc_now_iso(), run_id),
                )
                conn.commit()
        except Exception as exc:
            logger.warning("Agent run audit started update failed: %s", exc)
            # Non-fatal: run result preserved

    def record_completed(
        self,
        *,
        run_id: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Record run completion audit event."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    UPDATE agent_run_audit
                    SET action = 'run.completed',
                        status = 'COMPLETED',
                        completed_at = ?,
                        input_token_count = ?,
                        output_token_count = ?,
                        total_token_count = ?,
                        duration_ms = ?
                    WHERE run_id = ?
                    """,
                    (
                        _utc_now_iso(),
                        input_tokens,
                        output_tokens,
                        total_tokens,
                        duration_ms,
                        run_id,
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.warning("Agent run audit completed update failed: %s", exc)
            # Non-fatal: run result preserved, audit incomplete

    def record_cancelled(
        self,
        *,
        run_id: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Record run cancellation audit event."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    UPDATE agent_run_audit
                    SET action = 'run.cancelled',
                        status = 'CANCELLED',
                        completed_at = ?,
                        cancel_requested = 1,
                        input_token_count = ?,
                        output_token_count = ?,
                        total_token_count = ?,
                        duration_ms = ?
                    WHERE run_id = ?
                    """,
                    (
                        _utc_now_iso(),
                        input_tokens,
                        output_tokens,
                        total_tokens,
                        duration_ms,
                        run_id,
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.warning("Agent run audit cancelled update failed: %s", exc)

    def record_failed(
        self,
        *,
        run_id: str,
        error_code: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Record run failure audit event."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    UPDATE agent_run_audit
                    SET action = 'run.failed',
                        status = 'FAILED',
                        completed_at = ?,
                        error_code = ?,
                        input_token_count = ?,
                        output_token_count = ?,
                        total_token_count = ?,
                        duration_ms = ?
                    WHERE run_id = ?
                    """,
                    (
                        _utc_now_iso(),
                        error_code,
                        input_tokens,
                        output_tokens,
                        total_tokens,
                        duration_ms,
                        run_id,
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.warning("Agent run audit failed update failed: %s", exc)

    def get_audit_count(self) -> int:
        """Return total audit row count (for testing)."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM agent_run_audit"
                ).fetchone()
                return row[0] if row else 0
        except Exception:
            return 0


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()
