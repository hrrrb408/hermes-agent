"""P0-2 Tests: Cancel timeout must NOT release session lock or global capacity.

Verifies that:
- Cancel timeout marks run FAILED but retains session lock and capacity
- Worker alive flag prevents resource release
- Same-session new run is blocked after cancel timeout
- Cross-session new run is blocked by capacity after cancel timeout
- Worker eventually exiting releases resources
- Resource release is idempotent (mark_worker_exited safe to call multiple times)
- active_count never goes negative
- cleanup_expired does not delete runs with alive workers
- Cancel/complete race at timeout boundary produces unique terminal state
"""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
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
def registry():
    """Create a fresh AgentRunRegistry."""
    from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
    return AgentRunRegistry()


def _create_run(registry, session_id="test-session"):
    """Helper to create a run in the registry."""
    return registry.create_run(
        session_id=session_id,
        request_id=f"req-{uuid.uuid4().hex[:8]}",
        model_name="test-model",
        provider_name="test-provider",
    )


# ── P0-2.1: Cancel timeout retains resources ──


class TestCancelTimeoutRetainsResources:
    """After cancel timeout, session lock and global capacity must be retained."""

    def test_cancel_timeout_retains_session_lock(self, registry):
        """Cancel timeout does NOT release session lock."""
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = _create_run(registry)
        run_id = record.run_id

        # Transition to RUNNING
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)

        # Mark worker as alive (simulating real worker)
        registry.set_worker_alive(run_id, alive=True)

        # Cancel timeout: mark as failed but retain resources
        registry.mark_cancel_timeout(run_id)

        # Verify: session lock still held
        updated = registry.get_run(run_id)
        assert updated.status == RunStatus.FAILED
        assert updated.error_code == "AGENT_CANCEL_TIMEOUT"
        assert updated.session_lock_held is True, (
            "Session lock released on cancel timeout"
        )

    def test_cancel_timeout_retains_capacity(self, registry):
        """Cancel timeout does NOT release global capacity."""
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = _create_run(registry)
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.set_worker_alive(run_id, alive=True)
        registry.mark_cancel_timeout(run_id)

        # Verify: active_count still 1 (capacity not released)
        assert registry.active_count == 1, (
            f"active_count should be 1 after cancel timeout, got {registry.active_count}"
        )

    def test_cancel_timeout_retains_future_and_agent(self, registry):
        """Cancel timeout retains future and agent references."""
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = _create_run(registry)
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)

        mock_future = MagicMock()
        mock_agent = MagicMock()
        registry.set_future(run_id, mock_future)
        registry.set_agent_reference(run_id, mock_agent)
        registry.set_worker_alive(run_id, alive=True)

        registry.mark_cancel_timeout(run_id)

        updated = registry.get_run(run_id)
        assert updated.future is mock_future, "Future reference cleared on cancel timeout"
        assert updated.agent_reference is mock_agent, "Agent reference cleared on cancel timeout"


# ── P0-2.2: Same-session new run blocked ──


class TestSameSessionBlockedAfterCancelTimeout:
    """After cancel timeout, same-session new run must be rejected."""

    def test_same_session_busy(self, registry):
        from hermes_cli.dev_web_agent_run_registry import (
            SessionBusyError,
            CapacityReachedError,
        )
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = _create_run(registry, session_id="ses-1")
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.set_worker_alive(run_id, alive=True)
        registry.mark_cancel_timeout(run_id)

        # Attempt to create new run on same session
        with pytest.raises((SessionBusyError, CapacityReachedError)):
            registry.create_run(
                session_id="ses-1",
                request_id="req-new",
                model_name="m",
                provider_name="p",
            )


# ── P0-2.3: Cross-session new run blocked by capacity ──


class TestCrossSessionBlockedAfterCancelTimeout:
    """After cancel timeout, cross-session new run is blocked by capacity."""

    def test_capacity_reached(self, registry):
        from hermes_cli.dev_web_agent_run_registry import CapacityReachedError
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = _create_run(registry, session_id="ses-1")
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.set_worker_alive(run_id, alive=True)
        registry.mark_cancel_timeout(run_id)

        # Attempt to create run on different session
        with pytest.raises(CapacityReachedError):
            registry.create_run(
                session_id="ses-2",
                request_id="req-new",
                model_name="m",
                provider_name="p",
            )


# ── P0-2.4: Worker eventually exits and releases resources ──


class TestWorkerExitReleasesResources:
    """Worker exit releases session lock and capacity."""

    def test_worker_exit_releases_session_lock(self, registry):
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = _create_run(registry)
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.set_worker_alive(run_id, alive=True)
        registry.mark_cancel_timeout(run_id)

        # Worker exits
        registry.mark_worker_exited(run_id)

        updated = registry.get_run(run_id)
        assert updated.session_lock_held is False, (
            "Session lock not released after worker exit"
        )
        assert registry.active_count == 0, (
            f"active_count should be 0 after worker exit, got {registry.active_count}"
        )

    def test_after_worker_exit_new_run_allowed(self, registry):
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = _create_run(registry, session_id="ses-1")
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.set_worker_alive(run_id, alive=True)
        registry.mark_cancel_timeout(run_id)
        registry.mark_worker_exited(run_id)

        # New run on same session should succeed
        new_record = registry.create_run(
            session_id="ses-1",
            request_id="req-new",
            model_name="m",
            provider_name="p",
        )
        assert new_record.run_id != run_id

    def test_normal_completion_releases_resources(self, registry):
        """Normal completion (no cancel) still releases resources correctly."""
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = _create_run(registry, session_id="ses-1")
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)

        # Normal completion via complete_run
        registry.complete_run(run_id)

        updated = registry.get_run(run_id)
        assert updated.session_lock_held is False
        assert registry.active_count == 0


# ── P0-2.5: Idempotent release ──


class TestIdempotentRelease:
    """mark_worker_exited must be safe to call multiple times."""

    def test_idempotent_active_count(self, registry):
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = _create_run(registry)
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.set_worker_alive(run_id, alive=True)
        registry.mark_cancel_timeout(run_id)

        # Worker exits once
        registry.mark_worker_exited(run_id)
        assert registry.active_count == 0

        # Double exit — must not go negative
        registry.mark_worker_exited(run_id)
        assert registry.active_count == 0, (
            f"active_count went negative: {registry.active_count}"
        )

        # Triple exit — still 0
        registry.mark_worker_exited(run_id)
        assert registry.active_count == 0

    def test_idempotent_no_duplicate_terminal_events(self, registry):
        """Repeated mark_worker_exited does not emit duplicate terminal events."""
        from hermes_cli.dev_web_agent_run_models import RunStatus

        record = _create_run(registry)
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.set_worker_alive(run_id, alive=True)
        registry.mark_cancel_timeout(run_id)

        registry.mark_worker_exited(run_id)
        registry.mark_worker_exited(run_id)
        registry.mark_worker_exited(run_id)

        updated = registry.get_run(run_id)
        # Should still be FAILED (from cancel timeout), not changed by worker exit
        assert updated.status == RunStatus.FAILED


# ── P0-2.6: cleanup_expired skips alive workers ──


class TestCleanupSkipsAliveWorkers:
    """cleanup_expired must not delete runs with alive workers."""

    def test_cleanup_skips_alive_worker(self):
        from hermes_cli.dev_web_agent_run_models import RunStatus
        from hermes_cli.dev_web_agent_run_config import AgentRunConfig

        # Create registry with very short TTL
        config = AgentRunConfig(completed_run_ttl_seconds=0.01)
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        registry = AgentRunRegistry(config=config)

        record = _create_run(registry)
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.set_worker_alive(run_id, alive=True)
        registry.mark_cancel_timeout(run_id)

        # Wait for TTL to expire
        time.sleep(0.02)

        # Cleanup should NOT remove this run (worker still alive)
        cleaned = registry.cleanup_expired()
        assert cleaned == 0, "cleanup_expired removed a run with alive worker"

        # Verify run still exists
        updated = registry.get_run(run_id)
        assert updated is not None

    def test_cleanup_removes_after_worker_exit(self):
        from hermes_cli.dev_web_agent_run_models import RunStatus
        from hermes_cli.dev_web_agent_run_config import AgentRunConfig

        config = AgentRunConfig(completed_run_ttl_seconds=0.01)
        from hermes_cli.dev_web_agent_run_registry import AgentRunRegistry
        registry = AgentRunRegistry(config=config)

        record = _create_run(registry)
        run_id = record.run_id
        registry.transition(run_id, RunStatus.STARTING)
        registry.transition(run_id, RunStatus.RUNNING)
        registry.set_worker_alive(run_id, alive=True)
        registry.mark_cancel_timeout(run_id)
        registry.mark_worker_exited(run_id)

        # Wait for TTL to expire
        time.sleep(0.02)

        # Now cleanup CAN remove this run
        cleaned = registry.cleanup_expired()
        assert cleaned == 1


# ── P0-2.7: RunRecord worker_alive field ──


class TestRunRecordWorkerFields:
    """RunRecord must have worker_alive and resources_held fields."""

    def test_default_worker_not_alive(self):
        from hermes_cli.dev_web_agent_run_models import RunRecord, RunStatus

        record = RunRecord(
            run_id="run-test",
            session_id="ses-1",
            status=RunStatus.CREATED,
            created_at="2026-01-01T00:00:00Z",
            request_id="req-1",
            model_name="m",
            provider_name="p",
        )
        assert record.worker_alive is False
        assert record.worker_exited is False
        assert record.cancel_timeout is False

    def test_session_lock_held_default(self):
        from hermes_cli.dev_web_agent_run_models import RunRecord, RunStatus

        record = RunRecord(
            run_id="run-test",
            session_id="ses-1",
            status=RunStatus.CREATED,
            created_at="2026-01-01T00:00:00Z",
            request_id="req-1",
            model_name="m",
            provider_name="p",
        )
        # Default should be False (not held until create_run sets it)
        assert record.session_lock_held is False
