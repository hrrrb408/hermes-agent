"""Tests for Phase 1F Agent Run — Kill Switch, Dev Guard, Registry, API routes.

All tests use temporary HERMES_HOME, temporary state.db.
No real LLM calls, no real API keys, no writes to production or dev-home.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
import time
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


@pytest.fixture
def tmp_hermes_home(tmp_path):
    """Create a temporary HERMES_HOME with minimal structure."""
    home = tmp_path / "hermes-home"
    home.mkdir()
    (home / "state.db").touch()
    # Create minimal state.db schema
    conn = sqlite3.connect(str(home / "state.db"))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            source TEXT,
            model TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    return home


@pytest.fixture
def tmp_home_with_session(tmp_hermes_home):
    """Temporary home with a pre-existing session."""
    db_path = tmp_hermes_home / "state.db"
    session_id = f"test-session-{uuid.uuid4().hex[:8]}"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO sessions (session_id, source, model, created_at) VALUES (?, ?, ?, ?)",
        (session_id, "test", "test-model", datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return tmp_hermes_home, session_id


@pytest.fixture
def client_no_home():
    """FastAPI test client without HERMES_HOME."""
    from fastapi.testclient import TestClient
    from hermes_cli.dev_web_api import create_dev_web_api_app
    from hermes_cli.dev_web_config import DevWebApiConfig

    config = DevWebApiConfig(hermes_home=None)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def client_with_home(tmp_hermes_home):
    """FastAPI test client with temporary HERMES_HOME."""
    from fastapi.testclient import TestClient
    from hermes_cli.dev_web_api import create_dev_web_api_app
    from hermes_cli.dev_web_config import DevWebApiConfig

    config = DevWebApiConfig(hermes_home=tmp_hermes_home)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def client_with_session(tmp_home_with_session):
    """FastAPI test client with temporary home and pre-existing session."""
    from fastapi.testclient import TestClient
    from hermes_cli.dev_web_api import create_dev_web_api_app
    from hermes_cli.dev_web_config import DevWebApiConfig

    home, session_id = tmp_home_with_session
    config = DevWebApiConfig(hermes_home=home)
    app = create_dev_web_api_app(config)
    client = TestClient(app)
    return client, session_id, home


@pytest.fixture
def enabled_client_with_session(tmp_home_with_session, monkeypatch):
    """Client with kill switch enabled AND dev guard patched for tmp home."""
    from fastapi.testclient import TestClient
    from hermes_cli.dev_web_api import create_dev_web_api_app
    from hermes_cli.dev_web_config import DevWebApiConfig

    home, session_id = tmp_home_with_session
    monkeypatch.setenv("HERMES_AGENT_RUN_ENABLED", "true")

    # Patch the dev guard to allow the tmp home
    monkeypatch.setattr(
        "hermes_cli.dev_web_agent_run_config.ALLOWED_HERMES_HOME",
        home.resolve(),
    )
    monkeypatch.setattr(
        "hermes_cli.dev_web_agent_run_config._PRODUCTION_HERMES_HOME",
        Path("/nonexistent/prod"),
    )

    config = DevWebApiConfig(hermes_home=home)
    app = create_dev_web_api_app(config)
    client = TestClient(app)
    return client, session_id, home


# ── Valid request body helper ──


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


def _make_fake_run_id() -> str:
    """Generate a valid-looking run ID for tests."""
    return "run-" + uuid.uuid4().hex


# ── Kill Switch Tests ──


class TestKillSwitch:
    """Verify kill switch behavior."""

    def test_unset_is_disabled(self):
        from hermes_cli.dev_web_agent_run_config import is_agent_run_enabled
        assert is_agent_run_enabled() is False

    def test_false_is_disabled(self, monkeypatch):
        monkeypatch.setenv("HERMES_AGENT_RUN_ENABLED", "false")
        from hermes_cli.dev_web_agent_run_config import is_agent_run_enabled
        assert is_agent_run_enabled() is False

    def test_invalid_is_disabled(self, monkeypatch):
        monkeypatch.setenv("HERMES_AGENT_RUN_ENABLED", "maybe")
        from hermes_cli.dev_web_agent_run_config import is_agent_run_enabled
        assert is_agent_run_enabled() is False

    def test_true_is_enabled(self, monkeypatch):
        monkeypatch.setenv("HERMES_AGENT_RUN_ENABLED", "true")
        from hermes_cli.dev_web_agent_run_config import is_agent_run_enabled
        assert is_agent_run_enabled() is True

    def test_1_is_enabled(self, monkeypatch):
        monkeypatch.setenv("HERMES_AGENT_RUN_ENABLED", "1")
        from hermes_cli.dev_web_agent_run_config import is_agent_run_enabled
        assert is_agent_run_enabled() is True

    def test_disabled_returns_503(self, client_with_session):
        """Create Run returns 503 when kill switch is off."""
        client, session_id, _ = client_with_session
        resp = client.post(
            "/api/dev/v1/agent/runs",
            json=_valid_create_body(session_id),
        )
        assert resp.status_code == 503
        body = resp.json()
        assert body["error"]["code"] == "AGENT_RUN_DISABLED"

    def test_disabled_no_provider_init(self, client_with_session):
        """When disabled, no Provider/Thread/SessionDB write is created."""
        client, session_id, _ = client_with_session

        with patch("run_agent.AIAgent") as mock_agent, \
             patch("concurrent.futures.ThreadPoolExecutor.submit") as mock_submit:
            resp = client.post(
                "/api/dev/v1/agent/runs",
                json=_valid_create_body(session_id),
            )
            assert resp.status_code == 503
            mock_agent.assert_not_called()
            mock_submit.assert_not_called()


# ── Dev Guard Tests ──


class TestDevGuard:
    """Verify dev-only environment guard."""

    def test_dev_home_allowed(self, tmp_hermes_home):
        """Dev home passes with patched allowed values."""
        from hermes_cli.dev_web_agent_run_config import (
            enforce_agent_run_dev_environment,
        )
        source_root = Path(__file__).resolve().parents[1]
        with patch(
            "hermes_cli.dev_web_agent_run_config.ALLOWED_HERMES_HOME",
            tmp_hermes_home.resolve(),
        ), patch(
            "hermes_cli.dev_web_agent_run_config.ALLOWED_SOURCE_ROOT",
            source_root,
        ), patch(
            "hermes_cli.dev_web_agent_run_config._PRODUCTION_HERMES_HOME",
            Path("/nonexistent/prod"),
        ):
            # Should not raise
            enforce_agent_run_dev_environment(
                hermes_home=tmp_hermes_home,
                source_root=source_root,
            )

    def test_production_rejected(self):
        """Production home is rejected."""
        from hermes_cli.dev_web_agent_run_config import (
            enforce_agent_run_dev_environment,
            ALLOWED_SOURCE_ROOT,
        )
        prod_home = Path("/Users/huangruibang/.hermes")
        # Use the actual ALLOWED_SOURCE_ROOT so only the home check fails
        with pytest.raises(RuntimeError):
            enforce_agent_run_dev_environment(
                hermes_home=prod_home,
                source_root=ALLOWED_SOURCE_ROOT,
            )


# ── Run Registry Tests ──


class TestRunRegistry:
    """Verify Run Registry behavior."""

    def test_create_run(self):
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        from hermes_cli.dev_web_agent_run_models import RunStatus

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="test-session",
            request_id="req-1",
            model_name="test-model",
            provider_name="test-provider",
        )
        assert record.status == RunStatus.CREATED
        assert record.session_id == "test-session"
        assert record.run_id.startswith("run-")

    def test_global_capacity_limit(self):
        from hermes_cli.dev_web_agent_run_registry import (
            AgentRunRegistry,
            CapacityReachedError,
        )

        registry = AgentRunRegistry()
        registry.create_run(
            session_id="s1", request_id="r1",
            model_name="m", provider_name="p",
        )
        with pytest.raises(CapacityReachedError):
            registry.create_run(
                session_id="s2", request_id="r2",
                model_name="m", provider_name="p",
            )

    def test_session_busy_rejects(self):
        """Second run on same session is rejected (global limit = 1 also blocks this)."""
        from hermes_cli.dev_web_agent_run_registry import (
            AgentRunRegistry,
            SessionBusyError,
            CapacityReachedError,
        )

        registry = AgentRunRegistry()
        registry.create_run(
            session_id="s1", request_id="r1",
            model_name="m", provider_name="p",
        )
        # With global max = 1, this will hit either SessionBusy or CapacityReached
        with pytest.raises((SessionBusyError, CapacityReachedError)):
            registry.create_run(
                session_id="s1", request_id="r2",
                model_name="m", provider_name="p",
            )

    def test_valid_transition(self):
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        from hermes_cli.dev_web_agent_run_models import RunStatus

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="s1", request_id="r1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id

        # CREATED → STARTING
        updated = registry.transition(run_id, RunStatus.STARTING)
        assert updated.status == RunStatus.STARTING

        # STARTING → RUNNING
        updated = registry.transition(run_id, RunStatus.RUNNING)
        assert updated.status == RunStatus.RUNNING

        # RUNNING → COMPLETED
        updated = registry.transition(run_id, RunStatus.COMPLETED)
        assert updated.status == RunStatus.COMPLETED

    def test_illegal_transition_blocked(self):
        from hermes_cli.dev_web_agent_run_registry import (
            AgentRunRegistry,
            TransitionError,
        )
        from hermes_cli.dev_web_agent_run_models import RunStatus

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="s1", request_id="r1",
            model_name="m", provider_name="p",
        )

        with pytest.raises(TransitionError):
            # CREATED → RUNNING is illegal (must go through STARTING)
            registry.transition(record.run_id, RunStatus.RUNNING)

    def test_terminal_releases_session_lock(self):
        """Terminal state releases session lock, allowing new runs."""
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        from hermes_cli.dev_web_agent_run_models import RunStatus

        registry = AgentRunRegistry()
        r1 = registry.create_run(
            session_id="s1", request_id="r1",
            model_name="m", provider_name="p",
        )
        run_id = r1.run_id

        # Complete the run through the state machine
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        # Use complete_run which handles terminal state properly
        registry.complete_run(run_id)

        # Now a new run on the same session should succeed
        r2 = registry.create_run(
            session_id="s1", request_id="r2",
            model_name="m", provider_name="p",
        )
        assert r2.run_id != run_id

    def test_event_sequence_monotonic(self):
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        from hermes_cli.dev_web_agent_run_models import RunEventType

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="s1", request_id="r1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id

        e1 = registry.append_event(run_id, RunEventType.RUN_CREATED, {})
        e2 = registry.append_event(run_id, RunEventType.MESSAGE_DELTA, {"delta": "Hi"})
        e3 = registry.append_event(run_id, RunEventType.MESSAGE_DELTA, {"delta": " world"})

        assert e1.sequence == 1
        assert e2.sequence == 2
        assert e3.sequence == 3

    def test_terminal_event_only_once(self):
        from hermes_cli.dev_web_agent_run_registry import (
            AgentRunRegistry,
            TerminalEventDuplicateError,
        )
        from hermes_cli.dev_web_agent_run_models import RunEventType

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="s1", request_id="r1",
            model_name="m", provider_name="p",
        )

        registry.append_event(record.run_id, RunEventType.RUN_COMPLETED, {})
        with pytest.raises(TerminalEventDuplicateError):
            registry.append_event(record.run_id, RunEventType.RUN_COMPLETED, {})


# ── Run ID Tests ──


class TestRunId:
    """Verify Run ID generation and validation."""

    def test_generate_format(self):
        from hermes_cli.dev_web_agent_run_models import generate_run_id
        run_id = generate_run_id()
        assert run_id.startswith("run-")
        assert len(run_id) == 36  # "run-" + 32 hex chars

    def test_validate_valid(self):
        from hermes_cli.dev_web_agent_run_models import validate_run_id
        run_id = "run-" + "a" * 32
        assert validate_run_id(run_id) is True

    def test_validate_invalid_prefix(self):
        from hermes_cli.dev_web_agent_run_models import validate_run_id
        assert validate_run_id("not-a-run-id") is False

    def test_validate_empty(self):
        from hermes_cli.dev_web_agent_run_models import validate_run_id
        assert validate_run_id("") is False


# ── API Route Tests (kill switch disabled) ──


class TestAgentRunAPIDisabled:
    """Test Agent Run API routes with kill switch disabled."""

    def test_create_run_disabled_returns_503(self, client_with_session):
        client, session_id, _ = client_with_session
        resp = client.post(
            "/api/dev/v1/agent/runs",
            json=_valid_create_body(session_id),
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "AGENT_RUN_DISABLED"

    def test_create_run_no_home_returns_503(self, client_no_home):
        resp = client_no_home.post(
            "/api/dev/v1/agent/runs",
            json=_valid_create_body("any-session"),
        )
        assert resp.status_code == 503

    def test_get_run_status_disabled_returns_503(self, client_with_home):
        """GET status returns 503 when kill switch is off."""
        fake_id = _make_fake_run_id()
        resp = client_with_home.get(f"/api/dev/v1/agent/runs/{fake_id}")
        assert resp.status_code == 503

    def test_cancel_run_disabled_returns_503(self, client_with_home):
        fake_id = _make_fake_run_id()
        resp = client_with_home.post(f"/api/dev/v1/agent/runs/{fake_id}/cancel")
        assert resp.status_code == 503

    def test_get_run_status_invalid_id(self, client_with_home):
        resp = client_with_home.get("/api/dev/v1/agent/runs/not-a-valid-id")
        assert resp.status_code == 400

    def test_sse_run_not_found(self, client_with_home):
        """SSE endpoint returns 404 for unknown run."""
        fake_id = _make_fake_run_id()
        resp = client_with_home.get(f"/api/dev/v1/agent/runs/{fake_id}/events")
        assert resp.status_code == 404


# ── API Route Tests (kill switch enabled) ──


class TestAgentRunAPIEnabled:
    """Test Agent Run API routes with kill switch enabled."""

    def test_create_run_missing_confirmation(self, enabled_client_with_session):
        client, session_id, _ = enabled_client_with_session
        body = _valid_create_body(session_id)
        body["confirmationText"] = ""
        resp = client.post("/api/dev/v1/agent/runs", json=body)
        assert resp.status_code == 400

    def test_create_run_wrong_confirmation(self, enabled_client_with_session):
        client, session_id, _ = enabled_client_with_session
        body = _valid_create_body(session_id)
        body["confirmationText"] = "WRONG"
        resp = client.post("/api/dev/v1/agent/runs", json=body)
        assert resp.status_code == 400

    def test_create_run_missing_dry_run(self, enabled_client_with_session):
        client, session_id, _ = enabled_client_with_session
        body = _valid_create_body(session_id)
        body["dryRunPreviewed"] = False
        resp = client.post("/api/dev/v1/agent/runs", json=body)
        assert resp.status_code == 400

    def test_create_run_wrong_effects(self, enabled_client_with_session):
        client, session_id, _ = enabled_client_with_session
        body = _valid_create_body(session_id)
        body["acknowledgedEffects"] = ["CALL_LLM"]
        resp = client.post("/api/dev/v1/agent/runs", json=body)
        assert resp.status_code == 400

    def test_create_run_tools_true_rejected(self, enabled_client_with_session):
        client, session_id, _ = enabled_client_with_session
        body = _valid_create_body(session_id)
        body["options"]["tools"] = True
        resp = client.post("/api/dev/v1/agent/runs", json=body)
        assert resp.status_code == 400

    def test_create_run_auto_memory_true_rejected(self, enabled_client_with_session):
        client, session_id, _ = enabled_client_with_session
        body = _valid_create_body(session_id)
        body["options"]["autoMemory"] = True
        resp = client.post("/api/dev/v1/agent/runs", json=body)
        assert resp.status_code == 400

    def test_create_run_stream_false_rejected(self, enabled_client_with_session):
        client, session_id, _ = enabled_client_with_session
        body = _valid_create_body(session_id)
        body["options"]["stream"] = False
        resp = client.post("/api/dev/v1/agent/runs", json=body)
        assert resp.status_code == 400

    def test_create_run_forbidden_field_rejected(self, enabled_client_with_session):
        client, session_id, _ = enabled_client_with_session
        body = _valid_create_body(session_id)
        body["apiKey"] = "sk-test"
        resp = client.post("/api/dev/v1/agent/runs", json=body)
        assert resp.status_code == 400

    def test_create_run_session_not_found(self, enabled_client_with_session):
        """Returns 404 for nonexistent session."""
        client, _, _ = enabled_client_with_session
        body = _valid_create_body("nonexistent-session-12345")
        # Patch _verify_session_exists to check our simple DB
        from hermes_cli import dev_web_agent_run_service
        original = dev_web_agent_run_service.AgentRunService._verify_session_exists
        def _simple_verify(self, session_id):
            import sqlite3
            conn = sqlite3.connect(str(self._hermes_home / "state.db"))
            row = conn.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            conn.close()
            if row is None:
                from hermes_cli.dev_web_agent_run_service import SessionNotFoundError
                raise SessionNotFoundError(f"Session {session_id} not found")
        with patch.object(dev_web_agent_run_service.AgentRunService, '_verify_session_exists', _simple_verify):
            resp = client.post("/api/dev/v1/agent/runs", json=body)
        assert resp.status_code == 404

    def test_get_run_not_found(self, enabled_client_with_session):
        """GET /runs/{id} returns 404 for unknown run when enabled."""
        client, _, _ = enabled_client_with_session
        fake_id = _make_fake_run_id()
        resp = client.get(f"/api/dev/v1/agent/runs/{fake_id}")
        assert resp.status_code == 404

    def test_cancel_run_not_found(self, enabled_client_with_session):
        """POST /runs/{id}/cancel returns 404 for unknown run when enabled."""
        client, _, _ = enabled_client_with_session
        fake_id = _make_fake_run_id()
        resp = client.post(f"/api/dev/v1/agent/runs/{fake_id}/cancel")
        assert resp.status_code == 404


# ── Route Presence Tests ──


class TestRoutePresence:
    """Verify route registration and forbidden routes."""

    def test_total_27_paths(self):
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        config = DevWebApiConfig(hermes_home=None)
        app = create_dev_web_api_app(config)
        api_paths = [
            r for r in app.routes
            if hasattr(r, 'path') and r.path.startswith('/api/dev/v1')
        ]
        assert len(api_paths) == 27

    def test_agent_run_routes_present(self):
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        config = DevWebApiConfig(hermes_home=None)
        app = create_dev_web_api_app(config)
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        assert "/api/dev/v1/agent/runs" in paths
        assert "/api/dev/v1/agent/runs/{runId}" in paths
        assert "/api/dev/v1/agent/runs/{runId}/events" in paths
        assert "/api/dev/v1/agent/runs/{runId}/cancel" in paths

    def test_legacy_routes_absent(self):
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        config = DevWebApiConfig(hermes_home=None)
        app = create_dev_web_api_app(config)
        paths = [r.path for r in app.routes if hasattr(r, 'path')]
        assert "/api/dev/v1/agent/run" not in paths
        assert "/api/dev/v1/agent/stream" not in paths
        assert "/api/dev/v1/agent/tools" not in paths


# ── Audit Tests ──


class TestAudit:
    """Verify audit trail behavior."""

    def test_audit_table_creation(self, tmp_path):
        from hermes_cli.dev_web_agent_run_audit import AgentRunAudit

        db_path = tmp_path / "state.db"
        db_path.touch()
        audit = AgentRunAudit(db_path)

        conn = sqlite3.connect(str(db_path))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_run_audit'"
        ).fetchall()
        conn.close()
        assert len(tables) == 1

    def test_audit_record_created(self, tmp_path):
        from hermes_cli.dev_web_agent_run_audit import AgentRunAudit

        db_path = tmp_path / "state.db"
        db_path.touch()
        audit = AgentRunAudit(db_path)

        audit.record_created(
            run_id="run-test",
            session_id="session-1",
            request_id="req-1",
            model="test-model",
            provider="test-provider",
        )
        assert audit.get_audit_count() == 1

    def test_audit_no_secrets(self, tmp_path):
        from hermes_cli.dev_web_agent_run_audit import AgentRunAudit

        db_path = tmp_path / "state.db"
        db_path.touch()
        audit = AgentRunAudit(db_path)

        audit.record_created(
            run_id="run-test",
            session_id="session-1",
            request_id="req-1",
            model="test-model",
            provider="test-provider",
        )

        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT * FROM agent_run_audit").fetchone()
        conn.close()

        row_str = str(row).lower()
        for forbidden in ["api_key", "secret", "password", "token", "authorization"]:
            assert forbidden not in row_str


# ── State Machine Tests ──


class TestStateMachine:
    """Verify state machine transitions."""

    def test_all_defined_transitions_valid(self):
        from hermes_cli.dev_web_agent_run_models import (
            RunStatus,
            _TRANSITIONS,
        )
        for from_status, allowed in _TRANSITIONS.items():
            for to_status in allowed:
                from hermes_cli.dev_web_agent_run_models import is_transition_allowed
                assert is_transition_allowed(from_status, to_status)

    def test_terminal_states_limited_transitions(self):
        from hermes_cli.dev_web_agent_run_models import (
            RunStatus,
            TERMINAL_STATES,
            _TRANSITIONS,
        )
        for terminal in TERMINAL_STATES:
            allowed = _TRANSITIONS[terminal]
            # Only EXPIRED or empty is allowed from terminal
            for non_allowed in [
                RunStatus.CREATED, RunStatus.STARTING,
                RunStatus.RUNNING, RunStatus.CANCELLING,
            ]:
                assert non_allowed not in allowed


# ── Side-effect verification (disabled mode) ──


class TestDisabledModeSideEffects:
    """Verify kill switch OFF produces zero side effects."""

    def test_no_session_or_message_changes(self, tmp_hermes_home):
        """When kill switch is off, no sessions/messages change."""
        from fastapi.testclient import TestClient
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        config = DevWebApiConfig(hermes_home=tmp_hermes_home)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        # Create a session
        db_path = tmp_hermes_home / "state.db"
        conn = sqlite3.connect(str(db_path))
        sid = f"test-{uuid.uuid4().hex[:8]}"
        conn.execute(
            "INSERT INTO sessions (session_id, source, model, created_at) VALUES (?, ?, ?, ?)",
            (sid, "test", "m", datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()

        # Count before (after app init)
        msg_count_before = _count_messages(db_path)
        session_count_before = _count_sessions(db_path)

        # Attempt create run (kill switch off)
        resp = client.post("/api/dev/v1/agent/runs", json=_valid_create_body(sid))
        assert resp.status_code == 503

        # Verify counts unchanged
        msg_count_after = _count_messages(db_path)
        session_count_after = _count_sessions(db_path)

        assert msg_count_before == msg_count_after
        assert session_count_before == session_count_after


# ── Helpers ──


def _count_messages(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT COUNT(*) FROM messages").fetchone()
        return row[0] if row else 0
    except Exception:
        return -1
    finally:
        conn.close()


def _count_sessions(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()
        return row[0] if row else 0
    except Exception:
        return -1
    finally:
        conn.close()
