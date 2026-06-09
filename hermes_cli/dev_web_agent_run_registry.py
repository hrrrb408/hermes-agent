"""Dev Web API Agent Run Registry.

In-process Run Registry with thread-safe state management, event buffering,
session locks, global concurrency control, and TTL cleanup.

This module does NOT call LLM, initialize providers, or perform I/O
beyond in-memory data structure operations.

Thread safety:
    All state mutations are protected by a single threading.Lock.
    No I/O operations are performed while holding the lock.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from hermes_cli.dev_web_agent_run_config import AGENT_RUN_CONFIG
from dataclasses import dataclass

from hermes_cli.dev_web_agent_run_models import (
    TERMINAL_EVENT_TYPES,
    TERMINAL_STATES,
    RunEvent,
    RunEventType,
    RunRecord,
    RunStatus,
    RunUsage,
    generate_run_id,
    is_transition_allowed,
    validate_run_id,
)

logger = logging.getLogger(__name__)


class RunRegistryError(Exception):
    """Base error for registry operations."""


class RunNotFoundError(RunRegistryError):
    """Run ID does not exist in registry."""


class TransitionError(RunRegistryError):
    """Invalid state transition attempted."""


class SessionBusyError(RunRegistryError):
    """Session already has an active run."""


class CapacityReachedError(RunRegistryError):
    """Global active run limit reached."""


class TerminalEventDuplicateError(RunRegistryError):
    """Attempted to emit a second terminal event."""


class EventBufferExpiredError(RunRegistryError):
    """Requested event sequence has been trimmed from buffer."""


class InvalidLastEventIdError(RunRegistryError):
    """Last-Event-ID is invalid or ahead of current sequence."""


@dataclass
class CancelDecision:
    """Result of an atomic cancel request.

    Produced by AgentRunRegistry.request_cancel() inside a single lock
    acquisition.  The caller (Service) uses this to decide what to do
    *without* touching Registry state again.
    """

    run_id: str
    status_before: RunStatus
    status_after: RunStatus
    cancel_requested: bool
    already_requested: bool
    already_terminal: bool
    emit_cancelling_event: bool
    agent_reference: Any
    future_reference: Any


class AgentRunRegistry:
    """In-process Run Registry with thread-safe state management.

    Lifecycle:
        1. Created at application startup
        2. Runs created via create_run()
        3. State transitions via transition()
        4. Events appended via append_event()
        5. Terminal state handled via complete_run() / cancel_run() / fail_run()
        6. TTL cleanup via cleanup_expired()
    """

    def __init__(self, config: Any = None) -> None:
        self._config = config or AGENT_RUN_CONFIG
        self._lock = threading.Lock()
        self._runs: Dict[str, RunRecord] = {}
        self._session_locks: Dict[str, str] = {}  # session_id → run_id
        self._active_count = 0

    @property
    def active_count(self) -> int:
        """Current number of active (non-released) runs."""
        with self._lock:
            return self._active_count

    # ── Run creation ──

    def create_run(
        self,
        *,
        session_id: str,
        request_id: str,
        model_name: str,
        provider_name: str,
    ) -> RunRecord:
        """Create a new Run record.

        Checks global capacity and session lock before creation.

        Returns:
            The newly created RunRecord.

        Raises:
            CapacityReachedError: Global active run limit reached.
            SessionBusyError: Session already has an active run.
        """
        with self._lock:
            if self._active_count >= self._config.global_max_active_runs:
                raise CapacityReachedError(
                    f"Global active run limit ({self._config.global_max_active_runs}) reached."
                )
            if session_id in self._session_locks:
                raise SessionBusyError(
                    f"Session {session_id} already has an active run."
                )

            run_id = generate_run_id()
            now = _utc_now_iso()
            record = RunRecord(
                run_id=run_id,
                session_id=session_id,
                status=RunStatus.CREATED,
                created_at=now,
                request_id=request_id,
                model_name=model_name,
                provider_name=provider_name,
                session_lock_held=True,
            )
            self._runs[run_id] = record
            self._session_locks[session_id] = run_id
            self._active_count += 1
            return record

    # ── State transitions ──

    def transition(
        self,
        run_id: str,
        to_status: RunStatus,
        *,
        expected_from: Optional[RunStatus] = None,
    ) -> RunRecord:
        """Atomically transition a Run to a new status.

        Args:
            run_id: The run to transition.
            to_status: Target status.
            expected_from: If set, assert current status matches.

        Returns:
            Updated RunRecord.

        Raises:
            RunNotFoundError: Run does not exist.
            TransitionError: Transition not allowed.
        """
        with self._lock:
            record = self._get_locked(run_id)
            current = record.status

            if expected_from is not None and current != expected_from:
                raise TransitionError(
                    f"Expected status {expected_from.value}, "
                    f"got {current.value} for run {run_id}"
                )

            if not is_transition_allowed(current, to_status):
                raise TransitionError(
                    f"Transition {current.value} → {to_status.value} "
                    f"not allowed for run {run_id}"
                )

            record.status = to_status
            now = _utc_now_iso()

            if to_status == RunStatus.STARTING:
                record.started_at = now
            elif to_status == RunStatus.COMPLETED:
                record.completed_at = now
            elif to_status == RunStatus.CANCELLED:
                record.cancelled_at = now
            elif to_status == RunStatus.FAILED:
                record.failed_at = now
            elif to_status == RunStatus.EXPIRED:
                self._release_session_lock_locked(record)
                self._active_count = max(0, self._active_count - 1)

            return record

    # ── Event management ──

    def append_event(
        self,
        run_id: str,
        event_type: RunEventType,
        data: Dict[str, Any],
    ) -> RunEvent:
        """Append an event to a Run's buffer and return it.

        Thread-safe: acquires lock, appends, notifies SSE waiters.

        Returns:
            The appended RunEvent.

        Raises:
            RunNotFoundError: Run does not exist.
            TerminalEventDuplicateError: Terminal event already emitted.
        """
        with self._lock:
            record = self._get_locked(run_id)

            if event_type in TERMINAL_EVENT_TYPES:
                if record.terminal_event_emitted:
                    raise TerminalEventDuplicateError(
                        f"Terminal event already emitted for run {run_id}"
                    )
                record.terminal_event_emitted = True

            record.event_sequence += 1
            seq = record.event_sequence
            now = _utc_now_iso()

            event = RunEvent(
                sequence=seq,
                event_type=event_type,
                data=data,
                timestamp=now,
                run_id=run_id,
            )

            # Check buffer limits before appending
            self._enforce_buffer_limits_locked(record)

            # Serialize to calculate byte size
            event_json = json.dumps(event.data, ensure_ascii=False, separators=(",", ":"))
            event_bytes = len(event_json.encode("utf-8"))

            record.event_buffer.append(event)
            record.event_buffer_bytes += event_bytes

            # Notify SSE waiters

            return event

    # ── Run queries ──

    def get_run(self, run_id: str) -> RunRecord:
        """Get a run record by ID.

        Raises:
            RunNotFoundError: Run does not exist.
        """
        with self._lock:
            return self._get_locked(run_id)

    def try_get_run(self, run_id: str) -> Optional[RunRecord]:
        """Get a run record, returning None if not found."""
        with self._lock:
            return self._runs.get(run_id)

    def get_events_after(
        self, run_id: str, after_sequence: int
    ) -> List[RunEvent]:
        """Get buffered events after a given sequence number.

        Returns:
            List of events with sequence > after_sequence.

        Raises:
            RunNotFoundError: Run does not exist.
            EventBufferExpiredError: Requested sequence has been trimmed.
            InvalidLastEventIdError: Sequence is ahead of current.
        """
        with self._lock:
            record = self._get_locked(run_id)

            if after_sequence > record.event_sequence:
                raise InvalidLastEventIdError(
                    f"Last-Event-ID {after_sequence} is ahead of "
                    f"current sequence {record.event_sequence}"
                )

            # Check if the requested sequence is still in buffer
            if record.event_buffer:
                earliest = record.event_buffer[0].sequence
                if after_sequence < earliest - 1:
                    raise EventBufferExpiredError(
                        f"Events after sequence {after_sequence} "
                        f"have been trimmed (earliest={earliest})"
                    )

            return [
                evt for evt in record.event_buffer
                if evt.sequence > after_sequence
            ]

    # ── Cancel ──

    def mark_cancelling(self, run_id: str) -> RunRecord:
        """Mark a run as CANCELLING (cancel requested).

        Raises:
            RunNotFoundError: Run does not exist.
        """
        with self._lock:
            record = self._get_locked(run_id)
            record.cancel_requested = True
            if record.status == RunStatus.CREATED:
                # Cancel before start
                record.status = RunStatus.CANCELLED
                record.cancelled_at = _utc_now_iso()
                self._release_terminal_locked(record)
            elif record.status in (RunStatus.STARTING, RunStatus.RUNNING):
                if is_transition_allowed(record.status, RunStatus.CANCELLING):
                    record.status = RunStatus.CANCELLING
            # If already CANCELLING, terminal, or EXPIRED → no-op
            return record

    def request_cancel(self, run_id: str) -> CancelDecision:
        """Atomic cancel decision — read state, decide, and update in one lock.

        This is the ONLY method the Service cancel handler should call for
        state transitions.  It guarantees that no TransitionError leaks to
        the caller regardless of concurrent Worker state changes.

        Returns:
            CancelDecision with all information the Service needs.

        Raises:
            RunNotFoundError: Run does not exist.
        """
        with self._lock:
            record = self._get_locked(run_id)
            status_before = record.status

            # 1. Already terminal → idempotent return
            if status_before in TERMINAL_STATES:
                return CancelDecision(
                    run_id=run_id,
                    status_before=status_before,
                    status_after=status_before,
                    cancel_requested=record.cancel_requested,
                    already_requested=record.cancel_requested,
                    already_terminal=True,
                    emit_cancelling_event=False,
                    agent_reference=record.agent_reference,
                    future_reference=record.future,
                )

            # 2. Already CANCELLING → idempotent return
            if status_before == RunStatus.CANCELLING:
                return CancelDecision(
                    run_id=run_id,
                    status_before=status_before,
                    status_after=status_before,
                    cancel_requested=True,
                    already_requested=True,
                    already_terminal=False,
                    emit_cancelling_event=False,
                    agent_reference=record.agent_reference,
                    future_reference=record.future,
                )

            # 3. ACTIVE (CREATED / STARTING / RUNNING) — attempt cancel
            record.cancel_requested = True
            emit_cancelling = False

            if status_before == RunStatus.CREATED:
                # Cancel before worker started
                record.status = RunStatus.CANCELLED
                record.cancelled_at = _utc_now_iso()
                self._release_terminal_locked(record)
            elif is_transition_allowed(status_before, RunStatus.CANCELLING):
                record.status = RunStatus.CANCELLING
                emit_cancelling = True
            # else: status changed between read and lock — treat as
            # already-terminal check below

            status_after = record.status

            # If the transition didn't happen (unexpected state), check
            # if it's now terminal from a concurrent worker
            if status_after in TERMINAL_STATES:
                return CancelDecision(
                    run_id=run_id,
                    status_before=status_before,
                    status_after=status_after,
                    cancel_requested=True,
                    already_requested=False,
                    already_terminal=True,
                    emit_cancelling_event=False,
                    agent_reference=record.agent_reference,
                    future_reference=record.future,
                )

            return CancelDecision(
                run_id=run_id,
                status_before=status_before,
                status_after=status_after,
                cancel_requested=True,
                already_requested=False,
                already_terminal=False,
                emit_cancelling_event=emit_cancelling,
                agent_reference=record.agent_reference,
                future_reference=record.future,
            )

    # ── Connection management ──

    def set_client_connected(self, run_id: str, connected: bool) -> None:
        """Update client connection state.

        Sets disconnect_deadline when disconnecting.
        """
        with self._lock:
            record = self._get_locked(run_id)
            record.client_connected = connected
            if connected:
                record.disconnect_deadline = None
            else:
                from datetime import timedelta
                deadline = datetime.now(timezone.utc) + timedelta(
                    seconds=self._config.disconnect_grace_seconds
                )
                record.disconnect_deadline = deadline.isoformat()

    def get_disconnected_runs_past_grace(self) -> List[str]:
        """Get run IDs where disconnect grace period has expired."""
        with self._lock:
            now = datetime.now(timezone.utc)
            result = []
            for run_id, record in self._runs.items():
                if (
                    record.disconnect_deadline
                    and not record.client_connected
                    and not record.is_terminal()
                ):
                    try:
                        deadline = datetime.fromisoformat(record.disconnect_deadline)
                        if now >= deadline:
                            result.append(run_id)
                    except (ValueError, TypeError):
                        pass
            return result

    # ── Worker references ──

    def set_future(self, run_id: str, future: Any) -> None:
        """Store the Future reference for the worker thread."""
        with self._lock:
            record = self._get_locked(run_id)
            record.future = future

    def set_agent_reference(self, run_id: str, agent: Any) -> None:
        """Store the Agent reference for interrupt."""
        with self._lock:
            record = self._get_locked(run_id)
            record.agent_reference = agent

    # ── Worker lifecycle ──

    def set_worker_alive(self, run_id: str, alive: bool) -> None:
        """Mark worker thread as alive or not.

        Called by the service when the worker thread starts and is about
        to run the agent.
        """
        with self._lock:
            record = self._get_locked(run_id)
            record.worker_alive = alive

    def mark_cancel_timeout(self, run_id: str) -> RunRecord:
        """Mark run as FAILED with AGENT_CANCEL_TIMEOUT.

        Unlike fail_run(), this does NOT release session lock or capacity.
        Resources are held until mark_worker_exited() is called.

        Raises:
            RunNotFoundError: Run does not exist.
        """
        with self._lock:
            record = self._get_locked(run_id)
            if record.status not in (
                RunStatus.RUNNING, RunStatus.CANCELLING,
                RunStatus.STARTING,
            ):
                raise TransitionError(
                    f"Cannot mark cancel timeout for run {run_id} "
                    f"in status {record.status.value}"
                )
            record.status = RunStatus.FAILED
            record.failed_at = _utc_now_iso()
            record.error_code = "AGENT_CANCEL_TIMEOUT"
            record.error_message = "Cancel wait timed out — worker may still be running"
            record.cancel_timeout = True
            # Do NOT call _release_terminal_locked — worker still alive
            return record

    def mark_worker_exited(self, run_id: str) -> None:
        """Mark worker thread as exited and release resources.

        Idempotent: safe to call multiple times.
        Only releases resources on the first call.
        """
        with self._lock:
            record = self._get_locked(run_id)

            if record.worker_exited:
                # Already exited — no-op (idempotent)
                return

            record.worker_alive = False
            record.worker_exited = True

            # Release resources if run is terminal
            if record.is_terminal() and record.session_lock_held:
                self._session_locks.pop(record.session_id, None)
                record.session_lock_held = False
                self._active_count = max(0, self._active_count - 1)

    # ── Usage ──

    def set_usage(self, run_id: str, usage: RunUsage) -> None:
        """Update token usage for a run."""
        with self._lock:
            record = self._get_locked(run_id)
            record.usage = usage

    def set_error(self, run_id: str, error_code: str, error_message: str) -> None:
        """Set error info for a failed run."""
        with self._lock:
            record = self._get_locked(run_id)
            record.error_code = error_code
            record.error_message = error_message

    # ── Terminal state ──

    def complete_run(self, run_id: str, usage: Optional[RunUsage] = None) -> RunRecord:
        """Transition to COMPLETED and release session lock.

        Returns:
            The updated RunRecord.
        """
        with self._lock:
            record = self._get_locked(run_id)
            if record.status == RunStatus.CANCELLING:
                # Cancel takes priority
                record.status = RunStatus.CANCELLED
                record.cancelled_at = _utc_now_iso()
            elif is_transition_allowed(record.status, RunStatus.COMPLETED):
                record.status = RunStatus.COMPLETED
                record.completed_at = _utc_now_iso()
            else:
                raise TransitionError(
                    f"Cannot complete run {run_id} in status {record.status.value}"
                )
            if usage:
                record.usage = usage
            self._release_terminal_locked(record)
            return record

    def fail_run(
        self, run_id: str, error_code: str, error_message: str
    ) -> RunRecord:
        """Transition to FAILED.

        Only releases session lock if NOT in cancel-timeout scenario
        (where worker thread may still be alive).
        """
        with self._lock:
            record = self._get_locked(run_id)
            if is_transition_allowed(record.status, RunStatus.FAILED):
                record.status = RunStatus.FAILED
                record.failed_at = _utc_now_iso()
            else:
                raise TransitionError(
                    f"Cannot fail run {run_id} in status {record.status.value}"
                )
            record.error_code = error_code
            record.error_message = error_message
            self._release_terminal_locked(record)
            return record

    def cancel_run_completed(self, run_id: str) -> RunRecord:
        """Transition from CANCELLING to CANCELLED.

        Releases session lock since worker confirmed exit.
        """
        with self._lock:
            record = self._get_locked(run_id)
            if is_transition_allowed(record.status, RunStatus.CANCELLED):
                record.status = RunStatus.CANCELLED
                record.cancelled_at = _utc_now_iso()
            self._release_terminal_locked(record)
            return record

    # ── TTL Cleanup ──

    def cleanup_expired(self) -> int:
        """Remove expired terminal runs.

        Skips runs where worker is still alive (P0-2 fix).

        Returns:
            Number of runs cleaned up.
        """
        from datetime import timedelta

        ttl = timedelta(seconds=self._config.completed_run_ttl_seconds)
        now = datetime.now(timezone.utc)
        cleaned = 0

        with self._lock:
            to_remove = []
            for run_id, record in self._runs.items():
                # Skip runs with alive workers
                if record.worker_alive and not record.worker_exited:
                    continue

                if record.is_terminal() and not record.status == RunStatus.EXPIRED:
                    # Check if terminal state was reached long enough ago
                    terminal_time_str = (
                        record.completed_at
                        or record.cancelled_at
                        or record.failed_at
                    )
                    if terminal_time_str:
                        try:
                            terminal_time = datetime.fromisoformat(terminal_time_str)
                            if now - terminal_time > ttl:
                                to_remove.append(run_id)
                        except (ValueError, TypeError):
                            pass

            for run_id in to_remove:
                record = self._runs[run_id]
                record.status = RunStatus.EXPIRED
                # Don't decrement active count again — already done at terminal
                del self._runs[run_id]
                cleaned += 1

        return cleaned

    # ── Internal helpers (must be called with lock held) ──

    def _get_locked(self, run_id: str) -> RunRecord:
        """Get run or raise. Caller must hold lock."""
        record = self._runs.get(run_id)
        if record is None:
            raise RunNotFoundError(f"Run {run_id} not found.")
        return record

    def _release_session_lock_locked(self, record: RunRecord) -> None:
        """Release session lock. Caller must hold lock."""
        if record.session_lock_held:
            self._session_locks.pop(record.session_id, None)
            record.session_lock_held = False

    def _release_terminal_locked(self, record: RunRecord) -> None:
        """Handle terminal state: release session lock and decrement counter.

        Does NOT release if worker thread may still be running
        (worker_alive=True). Resources are deferred until mark_worker_exited().
        """
        if record.worker_alive and not record.worker_exited:
            # Worker still running — defer release
            return

        if record.session_lock_held:
            self._session_locks.pop(record.session_id, None)
            record.session_lock_held = False
        self._active_count = max(0, self._active_count - 1)

    def _enforce_buffer_limits_locked(self, record: RunRecord) -> None:
        """Trim oldest events if buffer exceeds limits. Caller must hold lock."""
        max_events = self._config.event_buffer_max_events
        max_bytes = self._config.event_buffer_max_bytes

        while len(record.event_buffer) >= max_events:
            self._pop_oldest_event_locked(record)

        while record.event_buffer_bytes > max_bytes and record.event_buffer:
            self._pop_oldest_event_locked(record)

    def _pop_oldest_event_locked(self, record: RunRecord) -> None:
        """Remove the oldest event from the buffer. Caller must hold lock."""
        if record.event_buffer:
            old = record.event_buffer.popleft()
            old_json = json.dumps(old.data, ensure_ascii=False, separators=(",", ":"))
            record.event_buffer_bytes -= len(old_json.encode("utf-8"))
            record.event_buffer_bytes = max(0, record.event_buffer_bytes)


# ── Utility ──


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ── Module-level singleton ──

_registry: Optional[AgentRunRegistry] = None
_registry_lock = threading.Lock()


def get_run_registry() -> AgentRunRegistry:
    """Get or create the singleton Run Registry."""
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = AgentRunRegistry()
        return _registry


def reset_run_registry() -> None:
    """Reset the singleton registry (for testing only)."""
    global _registry
    with _registry_lock:
        _registry = None
