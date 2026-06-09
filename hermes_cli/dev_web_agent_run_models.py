"""Dev Web API Agent Run Models.

Internal data models for Agent Run lifecycle, state machine, events, and usage.
These models are NOT Pydantic API schemas — they are internal dataclasses
used by the Run Registry and Run Service.

This module does NOT import Provider, Agent, or any I/O modules.
"""

from __future__ import annotations

import enum
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ── Run ID generation ──

_RUN_ID_PREFIX = "run-"


def generate_run_id() -> str:
    """Generate a unique, unpredictable Run ID.

    Format: ``run-<uuid4-hex>``
    """
    return f"{_RUN_ID_PREFIX}{uuid.uuid4().hex}"


def validate_run_id(run_id: str) -> bool:
    """Check if a string is a valid Run ID format."""
    if not run_id or not isinstance(run_id, str):
        return False
    if not run_id.startswith(_RUN_ID_PREFIX):
        return False
    hex_part = run_id[len(_RUN_ID_PREFIX):]
    if len(hex_part) != 32:
        return False
    try:
        int(hex_part, 16)
        return True
    except ValueError:
        return False


# ── State machine ──


class RunStatus(str, enum.Enum):
    """Agent Run lifecycle states.

    Frozen from Phase 1F-00 Section 11.
    """

    CREATED = "CREATED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    CANCELLING = "CANCELLING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


# Allowed transitions (from_state → set of allowed to_states)
_TRANSITIONS: Dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.CREATED: frozenset({RunStatus.STARTING}),
    RunStatus.STARTING: frozenset({
        RunStatus.RUNNING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    }),
    RunStatus.RUNNING: frozenset({
        RunStatus.CANCELLING,
        RunStatus.COMPLETED,
        RunStatus.FAILED,
    }),
    RunStatus.CANCELLING: frozenset({
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    }),
    RunStatus.COMPLETED: frozenset({RunStatus.EXPIRED}),
    RunStatus.CANCELLED: frozenset({RunStatus.EXPIRED}),
    RunStatus.FAILED: frozenset({RunStatus.EXPIRED}),
    RunStatus.EXPIRED: frozenset(),  # No transitions from EXPIRED
}

TERMINAL_STATES = frozenset({
    RunStatus.COMPLETED,
    RunStatus.CANCELLED,
    RunStatus.FAILED,
    RunStatus.EXPIRED,
})


def is_transition_allowed(from_status: RunStatus, to_status: RunStatus) -> bool:
    """Check if a state transition is valid."""
    allowed = _TRANSITIONS.get(from_status, frozenset())
    return to_status in allowed


# ── Event types ──


class RunEventType(str, enum.Enum):
    """SSE event types for Agent Run.

    Phase 1F allows only these event types.
    """

    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    MESSAGE_DELTA = "message.delta"
    MESSAGE_COMPLETED = "message.completed"
    USAGE_UPDATED = "usage.updated"
    RUN_CANCELLING = "run.cancelling"
    RUN_CANCELLED = "run.cancelled"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    HEARTBEAT = "heartbeat"


TERMINAL_EVENT_TYPES = frozenset({
    RunEventType.RUN_COMPLETED,
    RunEventType.RUN_CANCELLED,
    RunEventType.RUN_FAILED,
})


# ── Usage model ──


@dataclass
class RunUsage:
    """Token usage from provider response."""

    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    cost: Optional[float] = None
    cost_estimated: bool = False

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API response dict (null for unknown)."""
        return {
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "totalTokens": self.total_tokens,
            "cachedTokens": self.cached_tokens,
            "cost": self.cost,
            "costEstimated": self.cost_estimated,
        }


# ── SSE Event ──


@dataclass
class RunEvent:
    """A single SSE event for a Run."""

    sequence: int
    event_type: RunEventType
    data: Dict[str, Any]
    timestamp: str
    run_id: str

    def to_sse_lines(self) -> str:
        """Serialize to SSE text/event-stream format.

        Format:
            id: <sequence>
            event: <event_type>
            data: <json>

        (terminated by double newline)
        """
        import json

        payload = {
            "runId": self.run_id,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "type": self.event_type.value,
            "data": self.data,
        }
        lines = [
            f"id: {self.sequence}",
            f"event: {self.event_type.value}",
            f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}",
            "",  # Empty line = event terminator
            "",  # Second newline
        ]
        return "\n".join(lines)


# ── Run Record ──


@dataclass
class RunRecord:
    """In-memory Run state record.

    Stored in the Run Registry. Thread-safe access via Registry lock.
    Does NOT contain secrets, API keys, full prompts, or full messages.
    """

    run_id: str
    session_id: str
    status: RunStatus
    created_at: str
    request_id: str
    model_name: str
    provider_name: str

    # Timestamps
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    failed_at: Optional[str] = None
    expires_at: Optional[str] = None

    # Cancel / connection state
    cancel_requested: bool = False
    client_connected: bool = False
    disconnect_deadline: Optional[str] = None

    # Event buffer
    event_sequence: int = 0
    event_buffer: deque = field(default_factory=deque)
    event_buffer_bytes: int = 0

    # Terminal event tracking
    terminal_event_emitted: bool = False

    # Worker references
    future: Optional[Any] = None  # concurrent.futures.Future
    agent_reference: Optional[Any] = None  # AIAgent for interrupt

    # Result
    usage: Optional[RunUsage] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # Session lock tracking
    session_lock_held: bool = False

    # Condition for SSE waiters
    event_condition: threading.Condition = field(
        default_factory=lambda: threading.Condition(threading.Lock())
    )

    def is_terminal(self) -> bool:
        """Check if this run is in a terminal state."""
        return self.status in TERMINAL_STATES

    def current_event_sequence(self) -> int:
        """Return the current event sequence number."""
        return self.event_sequence

    def buffered_event_count(self) -> int:
        """Return the number of events in the buffer."""
        return len(self.event_buffer)

    def to_status_dict(self) -> Dict[str, Any]:
        """Convert to API status response data dict (whitelisted fields only)."""
        result: Dict[str, Any] = {
            "runId": self.run_id,
            "sessionId": self.session_id,
            "status": self.status.value,
            "createdAt": self.created_at,
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "cancelRequested": self.cancel_requested,
            "clientConnected": self.client_connected,
            "model": {
                "name": self.model_name,
                "provider": self.provider_name,
            },
            "usage": self.usage.to_api_dict() if self.usage else None,
            "capabilities": {
                "streaming": True,
                "tools": False,
                "autoMemory": False,
                "sessionWrite": True,
            },
            "safety": {
                "devOnly": True,
                "killSwitchEnabled": True,
            },
        }
        if self.error_code:
            result["error"] = {
                "code": self.error_code,
                "message": self.error_message,
            }
        return result
