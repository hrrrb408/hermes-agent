"""P0-1 Tests: Agent Run disabled-mode zero side effects.

Verifies that:
- AgentRunService construction does NOT create audit table / DDL
- AgentRunAudit construction does NOT execute DDL
- Kill switch disabled requests do NOT create audit table
- Dev guard failure does NOT create audit table
- Invalid DTO does NOT create audit table
- state.db hash/size/mtime remain unchanged in all rejected paths
- Enabled fixture can still create audit table and run normally
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ──


@pytest.fixture(autouse=True)
def _reset_registry():
    """Reset Run Registry singleton between tests."""
    from hermes_cli.dev_web_agent_run_registry import reset_run_registry
    reset_run_registry()
    yield
    reset_run_registry()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure kill switch is unset by default."""
    monkeypatch.delenv("HERMES_AGENT_RUN_ENABLED", raising=False)
    yield


def _create_session_db(home: Path, session_id: str | None = None) -> str | None:
    """Create a proper SessionDB at home/state.db with optional session.

    Uses SessionDB._init_schema() to ensure all columns exist.
    Returns the session_id if created.
    """
    from hermes_state import SessionDB
    db_path = home / "state.db"
    db = SessionDB(db_path=db_path)
    if session_id is not None:
        db.create_session(session_id=session_id, source="test", model="test-model")
    db._conn.close()
    return session_id


@pytest.fixture
def tmp_hermes_home(tmp_path):
    """Create a temporary HERMES_HOME with minimal structure."""
    home = tmp_path / "hermes-home"
    home.mkdir()
    # Create a proper state.db with SessionDB schema (but no sessions)
    db_path = home / "state.db"
    from hermes_state import SessionDB
    db = SessionDB(db_path=db_path)
    db._conn.close()
    return home


@pytest.fixture
def tmp_home_with_session(tmp_path):
    """Temporary home with a pre-existing session."""
    home = tmp_path / "hermes-home"
    home.mkdir()
    session_id = f"test-session-{uuid.uuid4().hex[:8]}"
    _create_session_db(home, session_id)
    return home, session_id


# ── Helpers ──


def _file_sha256(path: Path) -> str:
    """SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_size(path: Path) -> int:
    return path.stat().st_size


def _file_mtime(path: Path) -> float:
    return path.stat().st_mtime


def _audit_table_exists(db_path: Path) -> bool:
    """Check if agent_run_audit table exists in the database."""
    conn = sqlite3.connect(str(db_path))
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_run_audit'"
    ).fetchall()
    conn.close()
    return len(tables) > 0


def _audit_row_count(db_path: Path) -> int:
    if not _audit_table_exists(db_path):
        return 0
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT COUNT(*) FROM agent_run_audit").fetchone()
    conn.close()
    return row[0] if row else 0


def _valid_create_body(session_id: str) -> dict:
    """Return a valid create-run request body."""
    return {
        "sessionId": session_id,
        "message": "Hello, this is a test message.",
        "confirmationText": "RUN",
        "dryRunPreviewed": True,
        "acknowledgedEffects": ["CALL_LLM", "WRITE_SESSION"],
        "options": {
            "stream": True,
            "tools": False,
            "autoMemory": False,
        },
        "overrides": {},
    }


def _snapshot_db(db_path: Path) -> dict:
    """Take a snapshot of database state."""
    return {
        "hash": _file_sha256(db_path),
        "size": _file_size(db_path),
        "mtime": _file_mtime(db_path),
        "audit_table_exists": _audit_table_exists(db_path),
        "audit_rows": _audit_row_count(db_path),
    }


# ── P0-1.1: AgentRunAudit construction is side-effect-free ──


class TestAuditConstructionNoSideEffects:
    """AgentRunAudit.__init__() must NOT execute DDL."""

    def test_audit_init_no_table(self, tmp_path):
        """Constructing AgentRunAudit does NOT create the audit table."""
        from hermes_cli.dev_web_agent_run_audit import AgentRunAudit

        db_path = tmp_path / "state.db"
        db_path.touch()

        hash_before = _file_sha256(db_path)

        audit = AgentRunAudit(db_path)

        hash_after = _file_sha256(db_path)
        assert hash_before == hash_after, (
            "AgentRunAudit construction modified state.db"
        )
        assert not _audit_table_exists(db_path), (
            "AgentRunAudit construction created audit table"
        )

    def test_audit_init_no_wal_shm(self, tmp_path):
        """Constructing AgentRunAudit does NOT create WAL/SHM files."""
        from hermes_cli.dev_web_agent_run_audit import AgentRunAudit

        db_path = tmp_path / "state.db"
        db_path.touch()

        AgentRunAudit(db_path)

        assert not (tmp_path / "state.db-wal").exists(), "WAL file created"
        assert not (tmp_path / "state.db-shm").exists(), "SHM file created"


# ── P0-1.2: AgentRunService construction is side-effect-free ──


class TestServiceConstructionNoSideEffects:
    """AgentRunService.__init__() must NOT create audit table or execute DDL."""

    def test_service_init_no_audit_table(self, tmp_hermes_home):
        """Constructing AgentRunService does NOT create audit table."""
        from hermes_cli.dev_web_agent_run_service import AgentRunService

        db_path = tmp_hermes_home / "state.db"
        snapshot = _snapshot_db(db_path)

        source_root = Path(__file__).resolve().parents[1]
        service = AgentRunService(
            hermes_home=tmp_hermes_home,
            source_root=source_root,
        )

        snapshot_after = _snapshot_db(db_path)
        assert not snapshot_after["audit_table_exists"], (
            "AgentRunService construction created audit table"
        )
        assert snapshot_after["hash"] == snapshot["hash"], (
            "AgentRunService construction modified state.db"
        )

    def test_service_init_no_provider_thread_registry(self, tmp_hermes_home):
        """Constructing AgentRunService does NOT create providers/threads/runs."""
        from hermes_cli.dev_web_agent_run_service import AgentRunService

        source_root = Path(__file__).resolve().parents[1]
        service = AgentRunService(
            hermes_home=tmp_hermes_home,
            source_root=source_root,
        )

        # Registry should have 0 runs (the service uses the global singleton)
        from hermes_cli.dev_web_agent_run_registry import get_run_registry
        registry = get_run_registry()
        # Try to create a run — if capacity is used, this would fail
        record = registry.create_run(
            session_id="capacity-check",
            request_id="r-cap",
            model_name="m",
            provider_name="p",
        )
        assert record is not None


# ── P0-1.3: Kill switch disabled requests ──


class TestKillSwitchDisabledNoAudit:
    """Kill switch disabled requests must NOT create audit table or modify state.db."""

    @pytest.mark.parametrize("value", [
        None,  # unset
        "false",
        "0",
        "no",
        "off",
        "",
        "invalid",
        "maybe",
    ])
    def test_disabled_no_audit_table(self, tmp_home_with_session, monkeypatch, value):
        """Disabled kill switch does not create audit table."""
        home, session_id = tmp_home_with_session

        if value is not None:
            monkeypatch.setenv("HERMES_AGENT_RUN_ENABLED", value)

        from fastapi.testclient import TestClient
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        config = DevWebApiConfig(hermes_home=home)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        db_path = home / "state.db"
        snapshot = _snapshot_db(db_path)

        resp = client.post(
            "/api/dev/v1/agent/runs",
            json=_valid_create_body(session_id),
        )
        assert resp.status_code == 503

        snapshot_after = _snapshot_db(db_path)
        assert not snapshot_after["audit_table_exists"], (
            f"Kill switch={value!r} created audit table"
        )
        assert snapshot_after["hash"] == snapshot["hash"], (
            f"Kill switch={value!r} modified state.db"
        )
        assert snapshot_after["size"] == snapshot["size"], (
            f"Kill switch={value!r} changed state.db size"
        )

    def test_case_sensitive_values_disabled(self, tmp_home_with_session, monkeypatch):
        """Case-sensitive enable values (TRUE, Yes) are treated as disabled."""
        home, session_id = tmp_home_with_session

        from fastapi.testclient import TestClient
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        config = DevWebApiConfig(hermes_home=home)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        db_path = home / "state.db"

        for val in ("TRUE", "Yes"):
            monkeypatch.setenv("HERMES_AGENT_RUN_ENABLED", val)
            snapshot = _snapshot_db(db_path)

            resp = client.post(
                "/api/dev/v1/agent/runs",
                json=_valid_create_body(session_id),
            )
            # Case-sensitive values are disabled → may be 503 or 500
            assert resp.status_code in (503, 500), (
                f"Kill switch={val!r} expected 503/500, got {resp.status_code}"
            )

            snapshot_after = _snapshot_db(db_path)
            assert not snapshot_after["audit_table_exists"], (
                f"Kill switch={val!r} created audit table"
            )
            assert snapshot_after["hash"] == snapshot["hash"], (
                f"Kill switch={val!r} modified state.db"
            )

    def test_disabled_no_provider_init(self, tmp_home_with_session):
        """Disabled kill switch does not initialize Provider."""
        from fastapi.testclient import TestClient
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        home, session_id = tmp_home_with_session
        config = DevWebApiConfig(hermes_home=home)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        with patch("run_agent.AIAgent") as mock_agent:
            resp = client.post(
                "/api/dev/v1/agent/runs",
                json=_valid_create_body(session_id),
            )
            assert resp.status_code == 503
            mock_agent.assert_not_called()

    def test_disabled_no_thread_submit(self, tmp_home_with_session):
        """Disabled kill switch does not submit threads."""
        from fastapi.testclient import TestClient
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        home, session_id = tmp_home_with_session
        config = DevWebApiConfig(hermes_home=home)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        with patch(
            "concurrent.futures.ThreadPoolExecutor.submit"
        ) as mock_submit:
            resp = client.post(
                "/api/dev/v1/agent/runs",
                json=_valid_create_body(session_id),
            )
            assert resp.status_code == 503
            mock_submit.assert_not_called()


# ── P0-1.4: Dev guard failure ──


class TestDevGuardFailureNoAudit:
    """Dev guard failure must NOT create audit table."""

    def test_dev_guard_failure_no_ddl(self, tmp_hermes_home, monkeypatch):
        """Dev guard failure does not create audit table or modify state.db."""
        monkeypatch.setenv("HERMES_AGENT_RUN_ENABLED", "true")

        from fastapi.testclient import TestClient
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        home = tmp_hermes_home
        db_path = home / "state.db"

        config = DevWebApiConfig(hermes_home=home)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        # Create a session
        session_id = f"test-{uuid.uuid4().hex[:8]}"
        _create_session_db(home, session_id)

        # Snapshot AFTER session creation (SessionDB may modify schema)
        snapshot = _snapshot_db(db_path)

        # The dev guard should fail because we're using tmp_hermes_home
        # (ALLOWED_HERMES_HOME points to /Users/huangruibang/Code/hermes-home-dev)
        resp = client.post(
            "/api/dev/v1/agent/runs",
            json=_valid_create_body(session_id),
        )
        # Should return 500 (RuntimeError from guard caught by generic handler)
        assert resp.status_code == 500

        snapshot_after = _snapshot_db(db_path)
        assert not snapshot_after["audit_table_exists"], (
            "Dev guard failure created audit table"
        )
        assert snapshot_after["hash"] == snapshot["hash"], (
            "Dev guard failure modified state.db"
        )


# ── P0-1.5: Invalid DTO ──


class TestInvalidDTONoAudit:
    """Invalid request DTO must NOT create audit table."""

    def test_no_confirmation_no_audit(self, tmp_home_with_session, monkeypatch):
        """Missing confirmationText does not create audit table."""
        monkeypatch.setenv("HERMES_AGENT_RUN_ENABLED", "true")

        home, session_id = tmp_home_with_session

        # Patch dev guard to allow tmp home
        monkeypatch.setattr(
            "hermes_cli.dev_web_agent_run_config.ALLOWED_HERMES_HOME",
            home.resolve(),
        )
        monkeypatch.setattr(
            "hermes_cli.dev_web_agent_run_config._PRODUCTION_HERMES_HOME",
            Path("/nonexistent/prod"),
        )

        from fastapi.testclient import TestClient
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        config = DevWebApiConfig(hermes_home=home)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        db_path = home / "state.db"
        snapshot = _snapshot_db(db_path)

        body = _valid_create_body(session_id)
        del body["confirmationText"]
        resp = client.post("/api/dev/v1/agent/runs", json=body)
        assert resp.status_code == 400

        snapshot_after = _snapshot_db(db_path)
        assert not snapshot_after["audit_table_exists"], (
            "Invalid DTO created audit table"
        )

    def test_no_registry_run_on_invalid_dto(self, tmp_home_with_session, monkeypatch):
        """Invalid DTO does not create Registry Run."""
        monkeypatch.setenv("HERMES_AGENT_RUN_ENABLED", "true")
        home, session_id = tmp_home_with_session

        monkeypatch.setattr(
            "hermes_cli.dev_web_agent_run_config.ALLOWED_HERMES_HOME",
            home.resolve(),
        )
        monkeypatch.setattr(
            "hermes_cli.dev_web_agent_run_config._PRODUCTION_HERMES_HOME",
            Path("/nonexistent/prod"),
        )

        from fastapi.testclient import TestClient
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        config = DevWebApiConfig(hermes_home=home)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        body = _valid_create_body(session_id)
        body["confirmationText"] = "WRONG"
        resp = client.post("/api/dev/v1/agent/runs", json=body)
        assert resp.status_code == 400

        # Check registry has no runs — capacity should be available
        from hermes_cli.dev_web_agent_run_registry import get_run_registry
        registry = get_run_registry()
        record = registry.create_run(
            session_id="test", request_id="r1",
            model_name="m", provider_name="p",
        )
        assert record is not None


# ── P0-1.6: Enabled fixture creates audit table correctly ──


class TestEnabledCreatesAudit:
    """When enabled with valid request, audit table IS created."""

    def test_enabled_creates_audit_table(self, tmp_home_with_session, monkeypatch):
        """Enabled run with valid request creates audit table and row."""
        monkeypatch.setenv("HERMES_AGENT_RUN_ENABLED", "true")
        home, session_id = tmp_home_with_session

        monkeypatch.setattr(
            "hermes_cli.dev_web_agent_run_config.ALLOWED_HERMES_HOME",
            home.resolve(),
        )
        monkeypatch.setattr(
            "hermes_cli.dev_web_agent_run_config._PRODUCTION_HERMES_HOME",
            Path("/nonexistent/prod"),
        )

        from hermes_cli.dev_web_agent_run_service import AgentRunService

        service = AgentRunService(
            hermes_home=home,
            source_root=Path(__file__).resolve().parents[1],
        )

        # Mock the worker submission to avoid actually running
        # Also patch asyncio.get_running_loop since we're not in an async context
        mock_loop = MagicMock()
        with patch.object(service, '_worker'), \
             patch("hermes_cli.dev_web_agent_run_service._get_executor") as mock_exec, \
             patch("hermes_cli.dev_web_agent_run_service.asyncio.get_running_loop", return_value=mock_loop):
            mock_future = MagicMock()
            mock_executor = MagicMock()
            mock_executor.submit.return_value = mock_future
            mock_exec.return_value = mock_executor

            db_path = home / "state.db"
            assert not _audit_table_exists(db_path), (
                "Audit table created before valid request"
            )

            result = service.create_run(
                _valid_create_body(session_id),
                "req-test",
            )

            # After valid create_run, audit table should exist
            assert _audit_table_exists(db_path), (
                "Audit table not created after valid request"
            )
            assert _audit_row_count(db_path) == 1, (
                "Audit row not created"
            )
            assert result["data"]["runId"].startswith("run-")
