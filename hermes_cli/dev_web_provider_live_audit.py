"""Phase 3B-Live-Enablement — Live Provider Audit Writers (Frozen).

Emits the ``provider_live_*`` audit events a live round-trip must record.
Extends — and does **not** replace — the Phase 2B / 3B provider audit model.
The writer, sanitizer, containment rules, and durable-store dual-write are
**reused unchanged** from Phase 2B / 2D via ``write_provider_audit_event``.

Frozen events:
  - ``provider_live_enablement_requested``
  - ``provider_live_enablement_approved``
  - ``provider_live_enablement_denied``
  - ``provider_live_enablement_expired``
  - ``provider_live_enablement_started``
  - ``provider_live_enablement_completed``
  - ``provider_live_enablement_failed``
  - ``provider_live_enablement_kill_switch_triggered``
  - ``provider_live_secret_state_checked``
  - ``provider_live_network_request_started``
  - ``provider_live_network_request_completed``
  - ``provider_live_network_request_blocked``
  - ``provider_live_budget_checked``
  - ``provider_live_budget_blocked``
  - ``provider_live_tool_call_requested``
  - ``provider_live_tool_call_blocked``
  - ``provider_live_tool_call_completed``
  - ``provider_live_disable_completed``

Every event carries ``redactionApplied=true`` and is defensively re-redacted
before serialization. No API key, Authorization header, bearer token, full
tokenHash, raw prompt/response body, raw tool args, callable repr, or
production path may ever appear. An audit write failure on a live request
**fails closed** (the request is aborted by the orchestrator).

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
Status: live-provider audit writers implemented
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from hermes_cli.dev_web_provider_audit import (
    ProviderAuditWriteResult,
    write_provider_audit_event,
)

_PHASE = "3B-Live-Enablement"
_SCHEMA_VERSION = 1

# Event type constants (exported for the round-trip + tests).
EVENT_LIVE_ENABLEMENT_REQUESTED = "provider_live_enablement_requested"
EVENT_LIVE_ENABLEMENT_APPROVED = "provider_live_enablement_approved"
EVENT_LIVE_ENABLEMENT_DENIED = "provider_live_enablement_denied"
EVENT_LIVE_ENABLEMENT_EXPIRED = "provider_live_enablement_expired"
EVENT_LIVE_ENABLEMENT_STARTED = "provider_live_enablement_started"
EVENT_LIVE_ENABLEMENT_COMPLETED = "provider_live_enablement_completed"
EVENT_LIVE_ENABLEMENT_FAILED = "provider_live_enablement_failed"
EVENT_LIVE_ENABLEMENT_KILL_SWITCH_TRIGGERED = "provider_live_enablement_kill_switch_triggered"
EVENT_LIVE_SECRET_STATE_CHECKED = "provider_live_secret_state_checked"
EVENT_LIVE_NETWORK_REQUEST_STARTED = "provider_live_network_request_started"
EVENT_LIVE_NETWORK_REQUEST_COMPLETED = "provider_live_network_request_completed"
EVENT_LIVE_NETWORK_REQUEST_BLOCKED = "provider_live_network_request_blocked"
EVENT_LIVE_BUDGET_CHECKED = "provider_live_budget_checked"
EVENT_LIVE_BUDGET_BLOCKED = "provider_live_budget_blocked"
EVENT_LIVE_TOOL_CALL_REQUESTED = "provider_live_tool_call_requested"
EVENT_LIVE_TOOL_CALL_BLOCKED = "provider_live_tool_call_blocked"
EVENT_LIVE_TOOL_CALL_COMPLETED = "provider_live_tool_call_completed"
EVENT_LIVE_DISABLE_COMPLETED = "provider_live_disable_completed"

ALL_LIVE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        EVENT_LIVE_ENABLEMENT_REQUESTED,
        EVENT_LIVE_ENABLEMENT_APPROVED,
        EVENT_LIVE_ENABLEMENT_DENIED,
        EVENT_LIVE_ENABLEMENT_EXPIRED,
        EVENT_LIVE_ENABLEMENT_STARTED,
        EVENT_LIVE_ENABLEMENT_COMPLETED,
        EVENT_LIVE_ENABLEMENT_FAILED,
        EVENT_LIVE_ENABLEMENT_KILL_SWITCH_TRIGGERED,
        EVENT_LIVE_SECRET_STATE_CHECKED,
        EVENT_LIVE_NETWORK_REQUEST_STARTED,
        EVENT_LIVE_NETWORK_REQUEST_COMPLETED,
        EVENT_LIVE_NETWORK_REQUEST_BLOCKED,
        EVENT_LIVE_BUDGET_CHECKED,
        EVENT_LIVE_BUDGET_BLOCKED,
        EVENT_LIVE_TOOL_CALL_REQUESTED,
        EVENT_LIVE_TOOL_CALL_BLOCKED,
        EVENT_LIVE_TOOL_CALL_COMPLETED,
        EVENT_LIVE_DISABLE_COMPLETED,
    }
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_provider_live_audit_event(
    *,
    event_type: str,
    provider_name: str | None,
    provider_mode: str | None,
    approval_id: str | None = None,
    request_id: str | None = None,
    response_id: str | None = None,
    workflow_id: str | None = None,
    model: str | None = None,
    base_url_host: str | None = None,
    tool_id: str | None = None,
    tool_call_id: str | None = None,
    status: str | None = None,
    blocked_reason: str | None = None,
    usage_summary: Mapping[str, Any] | None = None,
    cost_estimate: Mapping[str, Any] | None = None,
    secret_state: Mapping[str, Any] | None = None,
    budget: Mapping[str, Any] | None = None,
    safe_metadata: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a redacted Phase 3B-Live-Enablement audit event dict.

    Only the safe fields are carried. ``secret_state`` is the value-free
    SecretCheckResult projection (keySource / keyState / keyValue="never").
    The whole event is defensively re-redacted before serialization.
    """
    timestamp = (now or datetime.now(timezone.utc)).isoformat()
    meta = dict(safe_metadata) if safe_metadata else {}
    event: dict[str, Any] = {
        "eventId": f"plve_{uuid.uuid4().hex}",
        "eventType": event_type,
        "phase": _PHASE,
        "schemaVersion": _SCHEMA_VERSION,
        "timestamp": timestamp,
        "providerName": provider_name,
        "providerMode": provider_mode,
        "approvalId": approval_id,
        "requestId": request_id,
        "responseId": response_id,
        "workflowId": workflow_id,
        "model": model,
        "baseUrlHost": base_url_host,
        "toolCallId": tool_call_id,
        "toolId": tool_id,
        "status": status,
        "blockedReason": blocked_reason,
        "redactionApplied": True,
        "usageSummary": dict(usage_summary) if usage_summary else {},
        "costEstimate": dict(cost_estimate) if cost_estimate else None,
        "secretState": dict(secret_state) if secret_state else None,
        "budget": dict(budget) if budget else None,
        "safeMetadata": meta,
    }
    return event


def write_provider_live_audit_event(
    event: Mapping[str, Any],
    *,
    hermes_home: str | None = None,
) -> str | None:
    """Write one Phase 3B-Live-Enablement audit event.

    Reuses the Phase 2B writer (containment guard under the dev HERMES_HOME,
    rotation cap, Phase 2D durable-store dual-write with ``auditKind=provider``).
    Returns the eventId on success, else None. Write failure never enables
    execution and never leaks a secret.

    Defensive re-redaction is applied before the writer sees the event.
    """
    from hermes_cli.dev_web_provider_real_redaction import redact_real_payload

    try:
        redacted = redact_real_payload(event)
    except Exception:  # pragma: no cover — defensive
        redacted = dict(event)
    for key in ("eventId", "eventType", "phase"):
        if key in event and key not in redacted:
            redacted[key] = event[key]
    redacted.setdefault("eventType", "provider_live_unknown")

    result: ProviderAuditWriteResult = write_provider_audit_event(
        redacted, hermes_home=hermes_home
    )
    return result.event_id if result.written else None


def _write(
    *,
    event_type: str,
    hermes_home: str | None,
    provider_name: str | None,
    provider_mode: str | None,
    approval_id: str | None = None,
    request_id: str | None = None,
    response_id: str | None = None,
    workflow_id: str | None = None,
    model: str | None = None,
    base_url_host: str | None = None,
    tool_id: str | None = None,
    tool_call_id: str | None = None,
    status: str | None = None,
    blocked_reason: str | None = None,
    usage_summary: Mapping[str, Any] | None = None,
    cost_estimate: Mapping[str, Any] | None = None,
    secret_state: Mapping[str, Any] | None = None,
    budget: Mapping[str, Any] | None = None,
    safe_metadata: Mapping[str, Any] | None = None,
) -> str | None:
    event = build_provider_live_audit_event(
        event_type=event_type,
        provider_name=provider_name,
        provider_mode=provider_mode,
        approval_id=approval_id,
        request_id=request_id,
        response_id=response_id,
        workflow_id=workflow_id,
        model=model,
        base_url_host=base_url_host,
        tool_id=tool_id,
        tool_call_id=tool_call_id,
        status=status,
        blocked_reason=blocked_reason,
        usage_summary=usage_summary,
        cost_estimate=cost_estimate,
        secret_state=secret_state,
        budget=budget,
        safe_metadata=safe_metadata,
    )
    return write_provider_live_audit_event(event, hermes_home=hermes_home)


# ---------------------------------------------------------------------------
# Typed convenience writers (one per frozen event)
# ---------------------------------------------------------------------------


def write_live_enablement_requested(
    *, hermes_home: str | None, provider_name: str | None, model: str | None,
    base_url_host: str | None, provider_mode: str = "real",
    safe_metadata: Mapping[str, Any] | None = None,
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_ENABLEMENT_REQUESTED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, model=model, base_url_host=base_url_host,
        status="requested", safe_metadata=safe_metadata,
    )


def write_live_enablement_approved(
    *, hermes_home: str | None, provider_name: str, model: str,
    base_url_host: str, approval_id: str, budget: Mapping[str, Any] | None,
    provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_ENABLEMENT_APPROVED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, model=model, base_url_host=base_url_host,
        approval_id=approval_id, status="approved", budget=budget,
    )


def write_live_enablement_denied(
    *, hermes_home: str | None, provider_name: str | None, blocked_reason: str,
    approval_id: str | None = None, provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_ENABLEMENT_DENIED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, approval_id=approval_id,
        status="denied", blocked_reason=blocked_reason,
    )


def write_live_enablement_expired(
    *, hermes_home: str | None, provider_name: str | None,
    approval_id: str | None, provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_ENABLEMENT_EXPIRED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, approval_id=approval_id, status="expired",
    )


def write_live_enablement_started(
    *, hermes_home: str | None, provider_name: str, model: str,
    base_url_host: str, approval_id: str, request_id: str,
    budget: Mapping[str, Any] | None, provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_ENABLEMENT_STARTED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, model=model, base_url_host=base_url_host,
        approval_id=approval_id, request_id=request_id, status="started",
        budget=budget,
    )


def write_live_enablement_completed(
    *, hermes_home: str | None, provider_name: str, model: str,
    base_url_host: str, approval_id: str, request_id: str, response_id: str,
    usage_summary: Mapping[str, Any] | None, cost_estimate: Mapping[str, Any] | None,
    provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_ENABLEMENT_COMPLETED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, model=model, base_url_host=base_url_host,
        approval_id=approval_id, request_id=request_id, response_id=response_id,
        status="completed", usage_summary=usage_summary, cost_estimate=cost_estimate,
    )


def write_live_enablement_failed(
    *, hermes_home: str | None, provider_name: str, blocked_reason: str,
    approval_id: str | None = None, request_id: str | None = None,
    provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_ENABLEMENT_FAILED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, approval_id=approval_id,
        request_id=request_id, status="failed", blocked_reason=blocked_reason,
    )


def write_live_kill_switch_triggered(
    *, hermes_home: str | None, provider_name: str | None,
    blocked_reason: str, provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_ENABLEMENT_KILL_SWITCH_TRIGGERED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, status="kill_switch",
        blocked_reason=blocked_reason,
    )


def write_live_secret_state_checked(
    *, hermes_home: str | None, provider_name: str | None,
    secret_state: Mapping[str, Any], provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_SECRET_STATE_CHECKED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, status="secret_checked",
        secret_state=secret_state,
    )


def write_live_network_request_started(
    *, hermes_home: str | None, provider_name: str, base_url_host: str,
    approval_id: str, request_id: str, provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_NETWORK_REQUEST_STARTED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, base_url_host=base_url_host,
        approval_id=approval_id, request_id=request_id, status="network_started",
    )


def write_live_network_request_completed(
    *, hermes_home: str | None, provider_name: str, base_url_host: str,
    request_id: str, response_id: str, provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_NETWORK_REQUEST_COMPLETED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, base_url_host=base_url_host,
        request_id=request_id, response_id=response_id, status="network_completed",
    )


def write_live_network_request_blocked(
    *, hermes_home: str | None, provider_name: str | None,
    blocked_reason: str, base_url_host: str | None = None,
    provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_NETWORK_REQUEST_BLOCKED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, base_url_host=base_url_host,
        status="network_blocked", blocked_reason=blocked_reason,
    )


def write_live_budget_checked(
    *, hermes_home: str | None, provider_name: str | None,
    budget: Mapping[str, Any], provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_BUDGET_CHECKED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, status="budget_checked", budget=budget,
    )


def write_live_budget_blocked(
    *, hermes_home: str | None, provider_name: str | None,
    blocked_reason: str, budget: Mapping[str, Any] | None = None,
    provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_BUDGET_BLOCKED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, status="budget_blocked",
        blocked_reason=blocked_reason, budget=budget,
    )


def write_live_tool_call_requested(
    *, hermes_home: str | None, provider_name: str, request_id: str,
    response_id: str, tool_call_id: str, tool_id: str,
    provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_TOOL_CALL_REQUESTED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, request_id=request_id, response_id=response_id,
        tool_call_id=tool_call_id, tool_id=tool_id, status="requested",
    )


def write_live_tool_call_blocked(
    *, hermes_home: str | None, provider_name: str, request_id: str,
    response_id: str, tool_call_id: str, tool_id: str, blocked_reason: str,
    provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_TOOL_CALL_BLOCKED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, request_id=request_id, response_id=response_id,
        tool_call_id=tool_call_id, tool_id=tool_id, status="blocked",
        blocked_reason=blocked_reason,
    )


def write_live_tool_call_completed(
    *, hermes_home: str | None, provider_name: str, request_id: str,
    response_id: str, tool_call_id: str, tool_id: str,
    provider_mode: str = "real",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_TOOL_CALL_COMPLETED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, request_id=request_id, response_id=response_id,
        tool_call_id=tool_call_id, tool_id=tool_id, status="completed",
    )


def write_live_disable_completed(
    *, hermes_home: str | None, provider_name: str | None,
    provider_mode: str = "disabled",
) -> str | None:
    return _write(
        event_type=EVENT_LIVE_DISABLE_COMPLETED,
        hermes_home=hermes_home, provider_name=provider_name,
        provider_mode=provider_mode, status="disabled",
    )


__all__ = [
    "ALL_LIVE_EVENT_TYPES",
    "EVENT_LIVE_ENABLEMENT_REQUESTED",
    "EVENT_LIVE_ENABLEMENT_APPROVED",
    "EVENT_LIVE_ENABLEMENT_DENIED",
    "EVENT_LIVE_ENABLEMENT_EXPIRED",
    "EVENT_LIVE_ENABLEMENT_STARTED",
    "EVENT_LIVE_ENABLEMENT_COMPLETED",
    "EVENT_LIVE_ENABLEMENT_FAILED",
    "EVENT_LIVE_ENABLEMENT_KILL_SWITCH_TRIGGERED",
    "EVENT_LIVE_SECRET_STATE_CHECKED",
    "EVENT_LIVE_NETWORK_REQUEST_STARTED",
    "EVENT_LIVE_NETWORK_REQUEST_COMPLETED",
    "EVENT_LIVE_NETWORK_REQUEST_BLOCKED",
    "EVENT_LIVE_BUDGET_CHECKED",
    "EVENT_LIVE_BUDGET_BLOCKED",
    "EVENT_LIVE_TOOL_CALL_REQUESTED",
    "EVENT_LIVE_TOOL_CALL_BLOCKED",
    "EVENT_LIVE_TOOL_CALL_COMPLETED",
    "EVENT_LIVE_DISABLE_COMPLETED",
    "build_provider_live_audit_event",
    "write_provider_live_audit_event",
    "write_live_enablement_requested",
    "write_live_enablement_approved",
    "write_live_enablement_denied",
    "write_live_enablement_expired",
    "write_live_enablement_started",
    "write_live_enablement_completed",
    "write_live_enablement_failed",
    "write_live_kill_switch_triggered",
    "write_live_secret_state_checked",
    "write_live_network_request_started",
    "write_live_network_request_completed",
    "write_live_network_request_blocked",
    "write_live_budget_checked",
    "write_live_budget_blocked",
    "write_live_tool_call_requested",
    "write_live_tool_call_blocked",
    "write_live_tool_call_completed",
    "write_live_disable_completed",
]
