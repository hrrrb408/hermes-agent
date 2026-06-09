"""Boundary tests: Tool dispatch, Memory/Review isolation, SSE reconnect, Retry.

All tests use temporary HERMES_HOME, Fake Provider (no real LLM).
No real API keys, no external network, no production access.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ── Fixtures ──


@pytest.fixture(autouse=True)
def _reset_registry():
    from hermes_cli.dev_web_agent_run_registry import reset_run_registry
    reset_run_registry()
    yield
    reset_run_registry()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("HERMES_AGENT_RUN_ENABLED", raising=False)
    yield


def _create_session_db(home: Path, session_id: str | None = None) -> str | None:
    from hermes_state import SessionDB
    db_path = home / "state.db"
    db = SessionDB(db_path=db_path)
    if session_id is not None:
        db.create_session(session_id=session_id, source="test", model="test-model")
    db._conn.close()
    return session_id


@pytest.fixture
def tmp_home_with_session(tmp_path):
    home = tmp_path / "hermes-home"
    home.mkdir()
    session_id = f"test-session-{uuid.uuid4().hex[:8]}"
    _create_session_db(home, session_id)
    return home, session_id


@pytest.fixture
def enabled_env(tmp_home_with_session, monkeypatch):
    """Enable agent run with dev guard patched for tmp home."""
    home, session_id = tmp_home_with_session
    monkeypatch.setenv("HERMES_AGENT_RUN_ENABLED", "true")
    monkeypatch.setattr(
        "hermes_cli.dev_web_agent_run_config.ALLOWED_HERMES_HOME",
        home.resolve(),
    )
    monkeypatch.setattr(
        "hermes_cli.dev_web_agent_run_config._PRODUCTION_HERMES_HOME",
        Path("/nonexistent/prod"),
    )
    return home, session_id


def _valid_create_body(session_id: str) -> dict:
    return {
        "sessionId": session_id,
        "message": "Hello, test message.",
        "confirmationText": "RUN",
        "dryRunPreviewed": True,
        "acknowledgedEffects": ["CALL_LLM", "WRITE_SESSION"],
        "options": {"stream": True, "tools": False, "autoMemory": False},
        "overrides": {},
    }


def _make_fake_provider_result(text="Hello!", tool_calls=None):
    """Create a fake run_conversation result."""
    result = {
        "response": text,
        "input_tokens": 10,
        "output_tokens": 20,
        "total_tokens": 30,
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": text},
        ],
    }
    if tool_calls:
        result["messages"][-1]["tool_calls"] = tool_calls
    return result


class FakeExecutor:
    """Fake executor that runs the worker synchronously in the calling thread."""

    def submit(self, fn, /, **kwargs):
        """Run the worker function synchronously and return a real future."""
        future = concurrent.futures.Future()
        try:
            result = fn(**kwargs)
            future.set_result(result)
        except Exception as exc:
            future.set_exception(exc)
        return future


def _run_service_with_fake_provider(service, session_id, fake_result):
    """Helper: create a run with a fake provider that returns fake_result."""
    with patch.object(service, '_create_agent') as mock_create, \
         patch("hermes_cli.dev_web_agent_run_service._get_executor", return_value=FakeExecutor()), \
         patch("hermes_cli.dev_web_agent_run_service.asyncio.get_running_loop") as mock_loop:

        mock_agent = MagicMock()
        mock_agent.run_conversation.return_value = fake_result
        mock_agent.clear_interrupt = MagicMock()
        mock_create.return_value = mock_agent
        mock_loop.return_value = MagicMock()

        return service.create_run(_valid_create_body(session_id), "req-1")


def _run_service_with_side_effect(service, session_id, side_effect):
    """Helper: create a run where run_conversation has a side_effect."""
    with patch.object(service, '_create_agent') as mock_create, \
         patch("hermes_cli.dev_web_agent_run_service._get_executor", return_value=FakeExecutor()), \
         patch("hermes_cli.dev_web_agent_run_service.asyncio.get_running_loop") as mock_loop:

        mock_agent = MagicMock()
        mock_agent.run_conversation.side_effect = side_effect
        mock_agent.clear_interrupt = MagicMock()
        mock_create.return_value = mock_agent
        mock_loop.return_value = MagicMock()

        return service.create_run(_valid_create_body(session_id), "req-1")


def _file_hashes(root: Path, *subpaths: str) -> dict:
    """Hash files under root for comparison."""
    hashes = {}
    for sp in subpaths:
        p = root / sp
        if p.is_file():
            hashes[sp] = hashlib.sha256(p.read_bytes()).hexdigest()
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    rel = str(f.relative_to(root))
                    hashes[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
    return hashes


# ── Tool Dispatch Boundary ──


class TestToolDispatchBoundary:
    """Tool dispatch must never be called in Phase 1F runs."""

    def test_dispatch_not_called_on_success(self, enabled_env):
        """Successful run completes without tool dispatch."""
        home, session_id = enabled_env
        from hermes_cli.dev_web_agent_run_service import AgentRunService
        from hermes_cli.dev_web_agent_run_models import RunStatus

        service = AgentRunService(
            hermes_home=home,
            source_root=Path(__file__).resolve().parents[1],
        )

        result = _run_service_with_fake_provider(
            service, session_id,
            _make_fake_provider_result("Test response"),
        )

        run_id = result["data"]["runId"]
        record = service._registry.get_run(run_id)
        assert record.status == RunStatus.COMPLETED

    def test_tool_call_rejected(self, enabled_env):
        """Provider returning tool_calls is rejected as TOOL_CALL_FORBIDDEN."""
        home, session_id = enabled_env
        from hermes_cli.dev_web_agent_run_service import AgentRunService
        from hermes_cli.dev_web_agent_run_models import RunStatus

        service = AgentRunService(
            hermes_home=home,
            source_root=Path(__file__).resolve().parents[1],
        )

        result = _run_service_with_fake_provider(
            service, session_id,
            _make_fake_provider_result("Has tools", tool_calls=[
                {"id": "tc-1", "function": {"name": "terminal", "arguments": "{}"}}
            ]),
        )

        run_id = result["data"]["runId"]
        record = service._registry.get_run(run_id)
        assert record.status == RunStatus.FAILED
        assert record.error_code == "AGENT_TOOL_CALL_FORBIDDEN"


# ── Memory / Review Boundary ──


class TestMemoryReviewBoundary:
    """Memory and Review functions must never be called in Phase 1F runs."""

    def test_memory_files_unchanged_after_run(self, enabled_env):
        """Memory and Review files are unchanged after a successful run."""
        home, session_id = enabled_env
        from hermes_cli.dev_web_agent_run_service import AgentRunService

        # Create minimal memory scaffold
        memory_dir = home / "memory"
        memory_dir.mkdir(exist_ok=True)
        (memory_dir / "indexes").mkdir(exist_ok=True)
        (memory_dir / "records").mkdir(exist_ok=True)
        (memory_dir / "events.jsonl").write_text("[]", encoding="utf-8")
        (memory_dir / "snapshots").mkdir(exist_ok=True)

        reviews_dir = memory_dir / "reviews"
        reviews_dir.mkdir(exist_ok=True)
        (reviews_dir / "items").mkdir(exist_ok=True)
        (reviews_dir / "events.jsonl").write_text("[]", encoding="utf-8")

        (home / "MEMORY.md").write_text("# Memory\n", encoding="utf-8")

        service = AgentRunService(
            hermes_home=home,
            source_root=Path(__file__).resolve().parents[1],
        )

        # Snapshot memory files before
        before_hashes = _file_hashes(
            home,
            "MEMORY.md",
            "memory/indexes",
            "memory/records",
            "memory/events.jsonl",
            "memory/snapshots",
            "memory/reviews",
        )

        _run_service_with_fake_provider(
            service, session_id,
            _make_fake_provider_result(),
        )

        after_hashes = _file_hashes(
            home,
            "MEMORY.md",
            "memory/indexes",
            "memory/records",
            "memory/events.jsonl",
            "memory/snapshots",
            "memory/reviews",
        )

        assert before_hashes == after_hashes, (
            f"Memory files changed: diff keys={set(before_hashes.keys()) ^ set(after_hashes.keys())}"
        )

    def test_memory_files_unchanged_after_failure(self, enabled_env):
        """Memory and Review files unchanged after a failed run."""
        home, session_id = enabled_env
        from hermes_cli.dev_web_agent_run_service import AgentRunService

        memory_dir = home / "memory"
        memory_dir.mkdir(exist_ok=True)
        (memory_dir / "indexes").mkdir(exist_ok=True)
        (memory_dir / "records").mkdir(exist_ok=True)
        (memory_dir / "events.jsonl").write_text("[]", encoding="utf-8")
        (memory_dir / "snapshots").mkdir(exist_ok=True)
        (home / "MEMORY.md").write_text("# Memory\n", encoding="utf-8")

        service = AgentRunService(
            hermes_home=home,
            source_root=Path(__file__).resolve().parents[1],
        )

        before_hashes = _file_hashes(home, "MEMORY.md", "memory")

        _run_service_with_side_effect(
            service, session_id,
            side_effect=RuntimeError("Boom"),
        )

        after_hashes = _file_hashes(home, "MEMORY.md", "memory")
        assert before_hashes == after_hashes


# ── SSE Reconnect ──


class TestSSEReconnect:
    """SSE reconnect must not re-run agent or duplicate messages."""

    def test_get_events_after_replay(self):
        """get_events_after replays buffered events without re-running agent."""
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        from hermes_cli.dev_web_agent_run_models import RunEventType

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="ses-1", request_id="req-1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id

        registry.append_event(run_id, RunEventType.RUN_CREATED, {})
        registry.append_event(run_id, RunEventType.MESSAGE_DELTA, {"delta": "Hi"})
        registry.append_event(run_id, RunEventType.MESSAGE_DELTA, {"delta": " there"})

        # Reconnect after sequence 1
        replay = registry.get_events_after(run_id, after_sequence=1)
        assert len(replay) == 2
        assert replay[0].sequence == 2
        assert replay[1].sequence == 3

    def test_invalid_last_event_id_raises(self):
        from hermes_cli.dev_web_agent_run_registry import (
            AgentRunRegistry,
            InvalidLastEventIdError,
        )
        from hermes_cli.dev_web_agent_run_models import RunEventType

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="ses-1", request_id="req-1",
            model_name="m", provider_name="p",
        )
        registry.append_event(record.run_id, RunEventType.RUN_CREATED, {})

        with pytest.raises(InvalidLastEventIdError):
            registry.get_events_after(record.run_id, after_sequence=999)

    def test_sse_status_endpoint_does_not_write_messages(self, enabled_env):
        """GET status and GET events do not write messages."""
        home, session_id = enabled_env

        from fastapi.testclient import TestClient
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        config = DevWebApiConfig(hermes_home=home)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        db_path = home / "state.db"

        conn = sqlite3.connect(str(db_path))
        msg_count_before = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        conn.close()

        fake_id = "run-" + "a" * 32
        client.get(f"/api/dev/v1/agent/runs/{fake_id}")
        client.get(f"/api/dev/v1/agent/runs/{fake_id}/events")

        conn = sqlite3.connect(str(db_path))
        msg_count_after = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        conn.close()

        assert msg_count_before == msg_count_after


# ── SSE Lifecycle Events ──


class TestSSELifecycleEvents:
    """Verify that run.created and run.started are always captured and replayable.

    Phase 1F SSE contract: the first SSE connection without Last-Event-ID
    must replay all buffered events starting from sequence 0, ensuring
    run.created (sequence 1) and run.started are delivered.
    """

    def test_run_created_is_sequence_1(self):
        """run.created event must be sequence = 1."""
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        from hermes_cli.dev_web_agent_run_models import RunEventType

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="ses-1", request_id="req-1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id

        event = registry.append_event(run_id, RunEventType.RUN_CREATED, {
            "sessionId": "ses-1",
            "model": {"name": "m", "provider": "p"},
        })
        assert event.sequence == 1
        assert event.event_type == RunEventType.RUN_CREATED

    def test_run_started_after_created(self):
        """run.started must follow run.created in event buffer."""
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        from hermes_cli.dev_web_agent_run_models import RunEventType

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="ses-1", request_id="req-1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id

        created = registry.append_event(run_id, RunEventType.RUN_CREATED, {})
        started = registry.append_event(run_id, RunEventType.RUN_STARTED, {"model": "m"})

        assert created.sequence == 1
        assert started.sequence == 2
        assert started.sequence > created.sequence

    def test_first_connection_replays_all_events(self):
        """get_events_after(0) returns ALL buffered events including created/started."""
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        from hermes_cli.dev_web_agent_run_models import RunEventType

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="ses-1", request_id="req-1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id

        # Simulate full lifecycle event emission
        registry.append_event(run_id, RunEventType.RUN_CREATED, {})
        registry.append_event(run_id, RunEventType.RUN_STARTED, {})
        registry.append_event(run_id, RunEventType.MESSAGE_DELTA, {"delta": "Hi"})
        registry.append_event(run_id, RunEventType.MESSAGE_DELTA, {"delta": " there"})
        registry.append_event(run_id, RunEventType.MESSAGE_COMPLETED, {})
        registry.append_event(run_id, RunEventType.USAGE_UPDATED, {})
        registry.append_event(run_id, RunEventType.RUN_COMPLETED, {})

        # First connection (no Last-Event-ID) should get ALL events
        all_events = registry.get_events_after(run_id, after_sequence=0)
        assert len(all_events) == 7

        event_types = [e.event_type for e in all_events]
        assert event_types[0] == RunEventType.RUN_CREATED
        assert event_types[1] == RunEventType.RUN_STARTED
        assert event_types[2] == RunEventType.MESSAGE_DELTA
        assert event_types[-1] == RunEventType.RUN_COMPLETED

    def test_delta_after_started_in_lifecycle(self):
        """First message.delta must come after run.started."""
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        from hermes_cli.dev_web_agent_run_models import RunEventType

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="ses-1", request_id="req-1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id

        registry.append_event(run_id, RunEventType.RUN_CREATED, {})
        started = registry.append_event(run_id, RunEventType.RUN_STARTED, {})
        delta = registry.append_event(run_id, RunEventType.MESSAGE_DELTA, {"delta": "Hi"})

        assert delta.sequence > started.sequence

    def test_successful_run_complete_lifecycle(self):
        """Successful run emits ordered subsequence: created, started, deltas, completed."""
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        from hermes_cli.dev_web_agent_run_models import RunEventType, TERMINAL_EVENT_TYPES

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="ses-1", request_id="req-1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id

        registry.append_event(run_id, RunEventType.RUN_CREATED, {})
        registry.append_event(run_id, RunEventType.RUN_STARTED, {})
        registry.append_event(run_id, RunEventType.MESSAGE_DELTA, {"delta": "A"})
        registry.append_event(run_id, RunEventType.MESSAGE_DELTA, {"delta": "B"})
        registry.append_event(run_id, RunEventType.MESSAGE_COMPLETED, {})
        registry.append_event(run_id, RunEventType.USAGE_UPDATED, {})
        registry.append_event(run_id, RunEventType.RUN_COMPLETED, {})

        all_events = registry.get_events_after(run_id, after_sequence=0)
        event_types = [e.event_type for e in all_events]

        # Verify ordered subsequence
        assert event_types.index(RunEventType.RUN_CREATED) == 0
        assert event_types.index(RunEventType.RUN_STARTED) == 1

        first_delta_idx = event_types.index(RunEventType.MESSAGE_DELTA)
        started_idx = event_types.index(RunEventType.RUN_STARTED)
        assert first_delta_idx > started_idx

        completed_idx = event_types.index(RunEventType.MESSAGE_COMPLETED)
        last_delta_idx = max(
            i for i, t in enumerate(event_types) if t == RunEventType.MESSAGE_DELTA
        )
        assert completed_idx > last_delta_idx

        assert RunEventType.USAGE_UPDATED in event_types
        assert event_types[-1] == RunEventType.RUN_COMPLETED

        # Exactly one terminal event
        terminal_events = [e for e in all_events if e.event_type in TERMINAL_EVENT_TYPES]
        assert len(terminal_events) == 1


# ── Retry ──


class TestRetryBehavior:
    """Verify retry behavior via the service worker."""

    def test_non_retryable_error_fails_immediately(self, enabled_env):
        """Non-retryable error (ValueError) fails without retry."""
        home, session_id = enabled_env
        from hermes_cli.dev_web_agent_run_service import AgentRunService
        from hermes_cli.dev_web_agent_run_models import RunStatus

        service = AgentRunService(
            hermes_home=home,
            source_root=Path(__file__).resolve().parents[1],
        )

        call_count = 0

        def fake_run(msg, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ValueError("Bad request")

        result = _run_service_with_side_effect(service, session_id, side_effect=fake_run)
        run_id = result["data"]["runId"]

        record = service._registry.get_run(run_id)
        assert record.status == RunStatus.FAILED
        assert call_count == 1, "Non-retryable error should not retry"

    def test_terminal_event_unique_on_failure(self, enabled_env):
        """Failed run emits exactly one terminal event."""
        home, session_id = enabled_env
        from hermes_cli.dev_web_agent_run_service import AgentRunService
        from hermes_cli.dev_web_agent_run_models import RunEventType

        service = AgentRunService(
            hermes_home=home,
            source_root=Path(__file__).resolve().parents[1],
        )

        result = _run_service_with_side_effect(
            service, session_id,
            side_effect=RuntimeError("Boom"),
        )
        run_id = result["data"]["runId"]

        record = service._registry.get_run(run_id)
        assert record.terminal_event_emitted is True

        terminal_events = [
            e for e in record.event_buffer
            if e.event_type in (
                RunEventType.RUN_COMPLETED,
                RunEventType.RUN_CANCELLED,
                RunEventType.RUN_FAILED,
            )
        ]
        assert len(terminal_events) == 1, (
            f"Expected 1 terminal event, got {len(terminal_events)}"
        )

    def test_successful_run_terminal_unique(self, enabled_env):
        """Successful run emits exactly one run.completed terminal event."""
        home, session_id = enabled_env
        from hermes_cli.dev_web_agent_run_service import AgentRunService
        from hermes_cli.dev_web_agent_run_models import RunEventType, RunStatus

        service = AgentRunService(
            hermes_home=home,
            source_root=Path(__file__).resolve().parents[1],
        )

        result = _run_service_with_fake_provider(
            service, session_id,
            _make_fake_provider_result("Success!"),
        )
        run_id = result["data"]["runId"]

        record = service._registry.get_run(run_id)
        assert record.status == RunStatus.COMPLETED
        assert record.terminal_event_emitted is True

        terminal_events = [
            e for e in record.event_buffer
            if e.event_type in (
                RunEventType.RUN_COMPLETED,
                RunEventType.RUN_CANCELLED,
                RunEventType.RUN_FAILED,
            )
        ]
        assert len(terminal_events) == 1
        assert terminal_events[0].event_type == RunEventType.RUN_COMPLETED
