"""Dev Web API Agent Run SSE Bridge.

Handles SSE serialization, heartbeat, event replay, Last-Event-ID,
connection registration, disconnect grace, and terminal state closing.

This module does NOT call providers or initialize agents.
It operates purely on the Run Registry event buffer.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Optional

from hermes_cli.dev_web_agent_run_config import AGENT_RUN_CONFIG
from hermes_cli.dev_web_agent_run_models import (
    TERMINAL_EVENT_TYPES,
    RunEvent,
    RunEventType,
    RunRecord,
    RunStatus,
)
from hermes_cli.dev_web_agent_run_registry import (
    AgentRunRegistry,
    EventBufferExpiredError,
    InvalidLastEventIdError,
    RunNotFoundError,
)

logger = logging.getLogger(__name__)

# ── SSE Headers ──

SSE_HEADERS = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


# ── SSE serialization ──


def serialize_sse_event(event: RunEvent) -> str:
    """Serialize a RunEvent to SSE text/event-stream format.

    Format:
        id: <sequence>\\n
        event: <type>\\n
        data: <json>\\n
        \\n
    """
    payload = {
        "runId": event.run_id,
        "sequence": event.sequence,
        "timestamp": event.timestamp,
        "type": event.event_type.value,
        "data": event.data,
    }
    lines = [
        f"id: {event.sequence}",
        f"event: {event.event_type.value}",
        f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}",
        "",  # Empty line terminates event
    ]
    return "\n".join(lines) + "\n"


def serialize_heartbeat(run_id: str, sequence: int) -> str:
    """Serialize a heartbeat SSE event."""
    payload = {
        "runId": run_id,
        "sequence": sequence,
        "timestamp": _utc_now_iso(),
        "type": "heartbeat",
    }
    lines = [
        f"id: {sequence}",
        "event: heartbeat",
        f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}",
        "",
    ]
    return "\n".join(lines) + "\n"


# ── SSE Event Stream ──


async def stream_run_events(
    run_id: str,
    registry: AgentRunRegistry,
    last_event_id: Optional[int] = None,
    disconnect_event: Optional[asyncio.Event] = None,
) -> AsyncIterator[str]:
    """Async generator that yields SSE events for a run.

    Handles:
    - Initial replay from Last-Event-ID
    - Live event streaming via Registry condition
    - Heartbeat on idle
    - Terminal event detection and close
    - Client disconnect via disconnect_event

    Args:
        run_id: The run to stream events for.
        registry: The Run Registry.
        last_event_id: Client's Last-Event-ID header value (or None).
        disconnect_event: Set when client disconnects.

    Yields:
        SSE-formatted event strings.
    """
    config = AGENT_RUN_CONFIG

    # 1. Resolve run and register connection
    try:
        run = registry.get_run(run_id)
    except RunNotFoundError:
        yield serialize_error_event("RUN_NOT_FOUND", "Run not found")
        return

    registry.set_client_connected(run_id, True)

    try:
        # 2. Replay buffered events
        # When no Last-Event-ID is provided (first connection), replay ALL
        # buffered events from sequence 0 to ensure run.created and
        # run.started are delivered even if they were emitted before the
        # client connected.
        if last_event_id is not None:
            replay_after = last_event_id
        else:
            replay_after = 0

        try:
            replay_events = registry.get_events_after(run_id, replay_after)
            for evt in replay_events:
                yield serialize_sse_event(evt)
        except EventBufferExpiredError:
            yield serialize_error_event(
                "AGENT_EVENT_BUFFER_EXPIRED",
                "Event buffer expired, cannot replay"
            )
            return
        except InvalidLastEventIdError:
            yield serialize_error_event(
                "INVALID_LAST_EVENT_ID",
                "Invalid Last-Event-ID value"
            )
            return

        # 3. Stream live events
        last_heartbeat = time.monotonic()
        heartbeat_seq = run.event_sequence

        while True:
            # Check if run is terminal
            current_run = registry.get_run(run_id)
            if current_run.is_terminal() and current_run.terminal_event_emitted:
                # Stream any remaining buffered events
                remaining = registry.get_events_after(
                    run_id, heartbeat_seq
                )
                for evt in remaining:
                    yield serialize_sse_event(evt)
                break

            # Wait for new events with timeout for heartbeat
            try:
                new_events = registry.get_events_after(run_id, heartbeat_seq)
                if new_events:
                    for evt in new_events:
                        yield serialize_sse_event(evt)
                        heartbeat_seq = evt.sequence
                        last_heartbeat = time.monotonic()

                        # Check if this was a terminal event
                        if evt.event_type in TERMINAL_EVENT_TYPES:
                            return
                else:
                    # No new events — check heartbeat
                    now = time.monotonic()
                    if now - last_heartbeat >= config.heartbeat_interval_seconds:
                        heartbeat_seq += 1
                        yield serialize_heartbeat(run_id, heartbeat_seq)
                        last_heartbeat = now

            except (EventBufferExpiredError, InvalidLastEventIdError):
                # Buffer issues during streaming — continue with current position
                pass
            except RunNotFoundError:
                break

            # Check for client disconnect
            if disconnect_event and disconnect_event.is_set():
                break

            # Brief sleep to avoid busy-loop
            await asyncio.sleep(0.1)

    finally:
        registry.set_client_connected(run_id, False)


def serialize_error_event(code: str, message: str) -> str:
    """Serialize an error as an SSE event."""
    payload = {
        "code": code,
        "message": message,
    }
    lines = [
        "event: error",
        f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}",
        "",
    ]
    return "\n".join(lines) + "\n"


# ── Callback Bridge (sync → async queue) ──


class SSEBridge:
    """Bridges synchronous stream_delta_callback to async SSE events.

    The agent runs in a worker thread and calls stream_delta_callback(delta)
    synchronously. This bridge converts those calls into Registry event
    appends, which the SSE stream then reads.
    """

    def __init__(
        self,
        run_id: str,
        registry: AgentRunRegistry,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._run_id = run_id
        self._registry = registry
        self._loop = loop

    def stream_delta_callback(self, text: Optional[str]) -> None:
        """Called synchronously from the agent worker thread.

        Args:
            text: Incremental text delta, or None for end-of-stream signal.
        """
        if text is None:
            # End-of-stream signal — don't emit as event
            # (terminal event is handled by the service)
            return

        # Validate and limit delta size
        if not isinstance(text, str):
            return
        if len(text) > 10000:
            text = text[:10000]

        try:
            self._registry.append_event(
                self._run_id,
                RunEventType.MESSAGE_DELTA,
                {"delta": text},
            )
        except Exception as exc:
            logger.debug(
                "SSE bridge event append failed for run %s: %s",
                self._run_id, exc,
            )


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()
