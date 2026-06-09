"""Cancel Transition Race regression tests.

Verifies that concurrent cancel / complete / fail operations never return
HTTP 500 due to TransitionError races.  All cancel requests must return 200
with the correct DTO, regardless of concurrent state changes.

Tests use temporary HERMES_HOME, Fake Provider, zero external network.
"""

from __future__ import annotations

import concurrent.futures
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


# ── Fixtures ──────────────────────────────────────────────────────────────


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


# ── 12.1 Worker Complete vs Cancel Race ─────────────────────────────────


class TestWorkerCompleteVsCancelRace:
    """Cancel handler and worker completion run concurrently.

    Cancel must ALWAYS return 200, never 500 from TransitionError.
    """

    def test_cancel_always_200_during_complete(self, enabled_env):
        """Cancel concurrent with worker completion must return 200.

        Iterates 50 times to ensure statistical coverage.
        """
        home, session_id = enabled_env
        from hermes_cli.dev_web_agent_run_service import AgentRunService
        from hermes_cli.dev_web_agent_run_models import RunStatus, RunEventType

        ITERATIONS = 50
        http_500_count = 0
        cancel_200_count = 0
        non_terminal_count = 0

        for i in range(ITERATIONS):
            from hermes_cli.dev_web_agent_run_registry import reset_run_registry
            reset_run_registry()

            service = AgentRunService(
                hermes_home=home,
                source_root=Path(__file__).resolve().parents[1],
            )

            # Use a barrier to synchronize cancel and worker
            barrier = threading.Barrier(2, timeout=10)
            cancel_result = [None]  # [response_dict | exception]
            cancel_exc = [None]

            def worker_fn(**kwargs):
                """Worker that pauses right before complete_run."""
                run_id = kwargs["run_id"]
                registry = service._registry

                registry.transition(run_id, RunStatus.STARTING)
                registry.append_event(run_id, RunEventType.RUN_STARTED, {"model": "test"})
                registry.transition(run_id, RunStatus.RUNNING)

                # Signal that we're about to complete
                barrier.wait(timeout=10)

                # Complete the run (may race with cancel)
                try:
                    registry.append_event(run_id, RunEventType.MESSAGE_COMPLETED, {"usage": {}})
                    registry.append_event(run_id, RunEventType.USAGE_UPDATED, {"usage": {}})
                    registry.complete_run(run_id)
                    registry.append_event(run_id, RunEventType.RUN_COMPLETED, {})
                except Exception:
                    pass

            def cancel_fn(run_id):
                """Cancel handler."""
                try:
                    barrier.wait(timeout=10)
                    result = service.cancel_run(run_id, f"req-cancel-{i}")
                    cancel_result[0] = result
                except Exception as exc:
                    cancel_exc[0] = exc

            # Create run manually
            from hermes_cli.dev_web_agent_run_registry import get_run_registry
            registry = get_run_registry()
            record = registry.create_run(
                session_id=session_id,
                request_id=f"req-{i}",
                model_name="test-model",
                provider_name="test-provider",
            )
            run_id = record.run_id

            # Set up a mock future
            mock_future = MagicMock()
            mock_future.result.return_value = None
            registry.set_future(run_id, mock_future)

            # Start worker and cancel in parallel
            with patch("hermes_cli.dev_web_agent_run_service._get_executor") as mock_exec, \
                 patch("hermes_cli.dev_web_agent_run_service.asyncio.get_running_loop") as mock_loop:

                # Use a real executor for concurrent execution
                real_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
                mock_exec.return_value = real_executor
                mock_loop.return_value = MagicMock()

                # Start worker
                worker_future = real_executor.submit(worker_fn, run_id=run_id)
                registry.set_future(run_id, worker_future)

                # Start cancel
                cancel_future = real_executor.submit(cancel_fn, run_id)

                # Wait for both
                worker_future.result(timeout=15)
                cancel_future.result(timeout=15)

                real_executor.shutdown(wait=True)

            # Verify cancel result
            if cancel_exc[0] is not None:
                # An exception is NOT acceptable for a normal race
                import traceback
                tb = traceback.format_exception(type(cancel_exc[0]), cancel_exc[0], cancel_exc[0].__traceback__)
                print(f"Iteration {i}: cancel raised {cancel_exc[0]}\n{''.join(tb)}")
                http_500_count += 1
            else:
                result = cancel_result[0]
                if result is not None:
                    cancel_200_count += 1
                    # Verify the DTO is well-formed
                    data = result.get("data", {})
                    assert "cancelRequested" in data or "alreadyTerminal" in data, (
                        f"Cancel DTO missing expected fields: {data}"
                    )

            # Verify terminal state
            final_record = registry.get_run(run_id)
            if not final_record.is_terminal():
                non_terminal_count += 1

        assert http_500_count == 0, (
            f"Cancel returned 500 in {http_500_count}/{ITERATIONS} iterations"
        )
        assert non_terminal_count == 0, (
            f"Run not terminal in {non_terminal_count}/{ITERATIONS} iterations"
        )


# ── 12.2 Worker Fail vs Cancel Race ─────────────────────────────────────


class TestWorkerFailVsCancelRace:
    """Cancel handler and worker failure run concurrently."""

    def test_cancel_always_200_during_failure(self, enabled_env):
        """Cancel concurrent with worker failure must return 200."""
        home, session_id = enabled_env
        from hermes_cli.dev_web_agent_run_service import AgentRunService
        from hermes_cli.dev_web_agent_run_models import RunStatus, RunEventType

        ITERATIONS = 50
        http_500_count = 0
        non_terminal_count = 0

        for i in range(ITERATIONS):
            from hermes_cli.dev_web_agent_run_registry import reset_run_registry
            reset_run_registry()

            service = AgentRunService(
                hermes_home=home,
                source_root=Path(__file__).resolve().parents[1],
            )

            barrier = threading.Barrier(2, timeout=10)
            cancel_result = [None]
            cancel_exc = [None]

            def worker_fn(**kwargs):
                run_id = kwargs["run_id"]
                registry = service._registry

                registry.transition(run_id, RunStatus.STARTING)
                registry.append_event(run_id, RunEventType.RUN_STARTED, {"model": "test"})
                registry.transition(run_id, RunStatus.RUNNING)

                barrier.wait(timeout=10)

                try:
                    registry.fail_run(run_id, "AGENT_RUN_FAILED", "Test failure")
                    registry.append_event(run_id, RunEventType.RUN_FAILED, {
                        "errorCode": "AGENT_RUN_FAILED",
                    })
                except Exception:
                    pass

            def cancel_fn(run_id):
                try:
                    barrier.wait(timeout=10)
                    result = service.cancel_run(run_id, f"req-cancel-{i}")
                    cancel_result[0] = result
                except Exception as exc:
                    cancel_exc[0] = exc

            from hermes_cli.dev_web_agent_run_registry import get_run_registry
            registry = get_run_registry()
            record = registry.create_run(
                session_id=session_id,
                request_id=f"req-{i}",
                model_name="test-model",
                provider_name="test-provider",
            )
            run_id = record.run_id

            mock_future = MagicMock()
            mock_future.result.return_value = None
            registry.set_future(run_id, mock_future)

            with patch("hermes_cli.dev_web_agent_run_service._get_executor") as mock_exec, \
                 patch("hermes_cli.dev_web_agent_run_service.asyncio.get_running_loop") as mock_loop:

                real_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
                mock_exec.return_value = real_executor
                mock_loop.return_value = MagicMock()

                worker_future = real_executor.submit(worker_fn, run_id=run_id)
                registry.set_future(run_id, worker_future)
                cancel_future = real_executor.submit(cancel_fn, run_id)

                worker_future.result(timeout=15)
                cancel_future.result(timeout=15)

                real_executor.shutdown(wait=True)

            if cancel_exc[0] is not None:
                http_500_count += 1
            else:
                result = cancel_result[0]
                if result is not None:
                    data = result.get("data", {})
                    assert "cancelRequested" in data or "alreadyTerminal" in data

            final_record = registry.get_run(run_id)
            if not final_record.is_terminal():
                non_terminal_count += 1

        assert http_500_count == 0, (
            f"Cancel returned 500 in {http_500_count}/{ITERATIONS} iterations"
        )
        assert non_terminal_count == 0, (
            f"Run not terminal in {non_terminal_count}/{ITERATIONS} iterations"
        )


# ── 12.3 Double Cancel ──────────────────────────────────────────────────


class TestDoubleCancel:
    """Two concurrent cancel requests must both return 200."""

    def test_double_cancel_both_200(self, enabled_env):
        """Both cancel requests return 200, one gets alreadyRequested=true."""
        home, session_id = enabled_env
        from hermes_cli.dev_web_agent_run_service import AgentRunService
        from hermes_cli.dev_web_agent_run_models import RunStatus, RunEventType

        ITERATIONS = 30
        http_500_count = 0

        for i in range(ITERATIONS):
            from hermes_cli.dev_web_agent_run_registry import reset_run_registry
            reset_run_registry()

            service = AgentRunService(
                hermes_home=home,
                source_root=Path(__file__).resolve().parents[1],
            )

            from hermes_cli.dev_web_agent_run_registry import get_run_registry
            registry = get_run_registry()
            record = registry.create_run(
                session_id=session_id,
                request_id=f"req-{i}",
                model_name="test-model",
                provider_name="test-provider",
            )
            run_id = record.run_id

            # Transition to RUNNING
            registry.transition(run_id, RunStatus.STARTING)
            registry.append_event(run_id, RunEventType.RUN_STARTED, {"model": "test"})
            registry.transition(run_id, RunStatus.RUNNING)

            # Set up a mock future that never completes (simulates running worker)
            mock_future = MagicMock()
            mock_future.result.side_effect = TimeoutError()
            registry.set_future(run_id, mock_future)

            cancel_results = [None, None]
            cancel_exc = [None, None]

            def cancel_fn(idx, rid):
                try:
                    cancel_results[idx] = service.cancel_run(rid, f"req-cancel-{idx}-{i}")
                except Exception as exc:
                    cancel_exc[idx] = exc

            t1 = threading.Thread(target=cancel_fn, args=(0, run_id))
            t2 = threading.Thread(target=cancel_fn, args=(1, run_id))

            t1.start()
            t2.start()
            t1.join(timeout=10)
            t2.join(timeout=10)

            for idx in range(2):
                if cancel_exc[idx] is not None:
                    http_500_count += 1

            # At least one must have a result
            results = [r for r in cancel_results if r is not None]
            assert len(results) >= 1, "At least one cancel must succeed"

        assert http_500_count == 0, (
            f"Cancel returned 500 in {http_500_count}/{ITERATIONS * 2} calls"
        )


# ── 12.4 Cancel Terminal Run ────────────────────────────────────────────


class TestCancelTerminalRun:
    """Cancel on terminal states must return 200 alreadyTerminal."""

    @pytest.fixture
    def _service_and_registry(self, enabled_env):
        home, session_id = enabled_env
        from hermes_cli.dev_web_agent_run_service import AgentRunService
        from hermes_cli.dev_web_agent_run_registry import get_run_registry

        service = AgentRunService(
            hermes_home=home,
            source_root=Path(__file__).resolve().parents[1],
        )
        registry = get_run_registry()
        return service, registry, session_id

    def test_cancel_completed_returns_200(self, _service_and_registry):
        service, registry, session_id = _service_and_registry
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = registry.create_run(
            session_id=session_id, request_id="req-1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.complete_run(run_id)

        result = service.cancel_run(run_id, "req-cancel")
        assert result["data"]["alreadyTerminal"] is True

    def test_cancel_cancelled_returns_200(self, _service_and_registry):
        service, registry, session_id = _service_and_registry
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = registry.create_run(
            session_id=session_id, request_id="req-1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.transition(run_id, RunStatus.CANCELLING)
        registry.cancel_run_completed(run_id)

        result = service.cancel_run(run_id, "req-cancel")
        assert result["data"]["alreadyTerminal"] is True

    def test_cancel_failed_returns_200(self, _service_and_registry):
        service, registry, session_id = _service_and_registry
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = registry.create_run(
            session_id=session_id, request_id="req-1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.fail_run(run_id, "TEST_ERROR", "Test failure")

        result = service.cancel_run(run_id, "req-cancel")
        assert result["data"]["alreadyTerminal"] is True


# ── 12.5 Cancel Timeout Regression ──────────────────────────────────────


class TestCancelTimeoutRegression:
    """Cancel timeout must preserve resources — no regression."""

    def test_cancel_timeout_retains_session_lock(self):
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        from hermes_cli.dev_web_agent_run_models import RunStatus

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="ses-1", request_id="req-1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.set_worker_alive(run_id, alive=True)
        registry.mark_cancel_timeout(run_id)

        updated = registry.get_run(run_id)
        assert updated.status == RunStatus.FAILED
        assert updated.session_lock_held is True
        assert registry.active_count == 1

    def test_worker_exit_after_timeout_releases(self):
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        from hermes_cli.dev_web_agent_run_models import RunStatus

        registry = AgentRunRegistry()
        record = registry.create_run(
            session_id="ses-1", request_id="req-1",
            model_name="m", provider_name="p",
        )
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.set_worker_alive(run_id, alive=True)
        registry.mark_cancel_timeout(run_id)

        # Idempotent exit
        registry.mark_worker_exited(run_id)
        registry.mark_worker_exited(run_id)

        assert registry.active_count == 0
        assert registry.get_run(run_id).session_lock_held is False
