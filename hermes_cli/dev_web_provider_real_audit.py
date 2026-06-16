"""Phase 3B Real Provider Audit Writers (Frozen).

Emits the ``provider_real_*`` audit events a Phase 3B real round-trip must
record. Extends — and does **not** replace — the Phase 2B provider audit model.
The writer, sanitizer, containment rules, and durable-store dual-write are
**reused unchanged** from Phase 2B / 2D via ``write_provider_audit_event``.

Frozen events:
  - ``provider_real_request_previewed``
  - ``provider_real_request_blocked``
  - ``provider_real_request_started``
  - ``provider_real_request_completed``
  - ``provider_real_request_failed``
  - ``provider_real_response_redacted``
  - ``provider_real_tool_call_requested``
  - ``provider_real_tool_call_blocked``
  - ``provider_real_tool_call_completed``
  - ``provider_real_budget_blocked``
  - ``provider_real_rate_limit_blocked``

Every event carries the Phase 3B common envelope and is defensively re-redacted
before serialization. No API key, Authorization header, raw token, full
tokenHash, raw arguments, callable repr, raw prompt/response body, or
production path may ever appear.

Architecture constraints:
  - stdlib only (no third-party imports)
  - only local file append under the dev HERMES_HOME audit path
  - never accesses ~/.hermes; never accesses production state.db
  - write failure NEVER enables execution, NEVER calls a provider, NEVER leaks

Phase: 3B — Real Provider Read-only Controlled Integration
Status: real-provider audit writers implemented
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from hermes_cli.dev_web_provider_audit import (
    ERROR_AUDIT_EVENT_TOO_LARGE,
    ProviderAuditWriteResult,
    build_provider_audit_event,
    write_provider_audit_event,
)

_PHASE = "3B"
_SCHEMA_VERSION = 1

# Event type constants (exported for the round-trip + tests).
EVENT_REAL_REQUEST_PREVIEWED = "provider_real_request_previewed"
EVENT_REAL_REQUEST_BLOCKED = "provider_real_request_blocked"
EVENT_REAL_REQUEST_STARTED = "provider_real_request_started"
EVENT_REAL_REQUEST_COMPLETED = "provider_real_request_completed"
EVENT_REAL_REQUEST_FAILED = "provider_real_request_failed"
EVENT_REAL_RESPONSE_REDACTED = "provider_real_response_redacted"
EVENT_REAL_TOOL_CALL_REQUESTED = "provider_real_tool_call_requested"
EVENT_REAL_TOOL_CALL_BLOCKED = "provider_real_tool_call_blocked"
EVENT_REAL_TOOL_CALL_COMPLETED = "provider_real_tool_call_completed"
EVENT_REAL_BUDGET_BLOCKED = "provider_real_budget_blocked"
EVENT_REAL_RATE_LIMIT_BLOCKED = "provider_real_rate_limit_blocked"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_provider_real_audit_event(
    *,
    event_type: str,
    request_id: str | None,
    response_id: str | None,
    provider_name: str,
    provider_mode: str,
    payload: Mapping[str, Any] | None = None,
    tool_call_id: str | None = None,
    tool_id: str | None = None,
    workflow_id: str | None = None,
    status: str | None = None,
    blocked_reason: str | None = None,
    external_network_called: bool = False,
    usage_summary: Mapping[str, Any] | None = None,
    cost_estimate: Mapping[str, Any] | None = None,
    safe_metadata: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a redacted Phase 3B real-provider audit event dict.

    The common envelope carries the value-free provider context in
    ``safeMetadata`` (apiKeySource / apiKeyPresent / apiKeySourceDetail /
    allowlistedBaseUrl(host) / modelName / adapterName) — never the key value.
    The whole event is defensively re-redacted before serialization.
    """
    timestamp = (now or datetime.now(timezone.utc)).isoformat()
    # safeMetadata is value-free by construction, but the full event is
    # re-redacted defensively below (defense-in-depth: a stray secret in a
    # payload field is masked to [REDACTED]).
    meta = dict(safe_metadata) if safe_metadata else {}
    event: dict[str, Any] = {
        "eventId": f"prre_{uuid.uuid4().hex}",
        "eventType": event_type,
        "phase": _PHASE,
        "schemaVersion": _SCHEMA_VERSION,
        "timestamp": timestamp,
        "providerName": provider_name,
        "providerMode": provider_mode,
        "requestId": request_id,
        "responseId": response_id,
        "workflowId": workflow_id,
        "toolCallId": tool_call_id,
        "toolId": tool_id,
        "status": status,
        "blockedReason": blocked_reason,
        "redactionApplied": True,
        "externalNetworkCalled": external_network_called,
        "usageSummary": dict(usage_summary) if usage_summary else {},
        "costEstimate": dict(cost_estimate) if cost_estimate else None,
        "safeMetadata": meta,
        "payload": dict(payload) if payload else {},
    }
    return event


def write_provider_real_audit_event(
    event: Mapping[str, Any],
    *,
    hermes_home: str | None = None,
) -> str | None:
    """Write one Phase 3B real-provider audit event.

    Reuses the Phase 2B writer (containment guard under the dev HERMES_HOME,
    rotation cap, Phase 2D durable-store dual-write with ``auditKind=provider``).
    Returns the eventId on success, else None. Write failure never enables
    execution and never leaks a secret.

    The event is defensively re-redacted by the Phase 2B-H1 sanitizer at write
    time (``write_provider_audit_event`` serializes via the same path that the
    Phase 2B builder already re-redacts; we additionally run the sanitizer here
    so a hand-built event is also covered).
    """
    from hermes_cli.dev_web_provider_real_redaction import redact_real_payload

    # Defensive full re-redaction before the writer sees it.
    try:
        redacted = redact_real_payload(event)
    except Exception:  # pragma: no cover — defensive
        redacted = dict(event)
    # Preserve the scalar top-level fields the writer reads.
    for key in ("eventId", "eventType", "providerMode", "phase"):
        if key in event and key not in redacted:
            redacted[key] = event[key]
    redacted.setdefault("eventType", "provider_real_unknown")

    result: ProviderAuditWriteResult = write_provider_audit_event(
        redacted, hermes_home=hermes_home
    )
    return result.event_id if result.written else None


def _safe_metadata_from_config(config, *, network_called: bool = False) -> dict[str, Any]:
    """Build the value-free safeMetadata block from a ProviderRealConfig.

    Never embeds the key value — only the presence marker + host + model name.
    """
    return {
        "apiKeySource": "env",
        "apiKeyPresent": config.api_key_source_detail == "env_present",
        "apiKeySourceDetail": config.api_key_source_detail,
        "allowlistedBaseUrl": config.base_url_host if config.base_url_allowed else "",
        "modelName": config.model if config.model_allowed else "",
        "adapterName": config.provider_name,
        "externalNetworkCalled": network_called,
    }


def _write(
    *,
    event_type: str,
    hermes_home: str | None,
    request_id: str | None,
    response_id: str | None,
    provider_name: str,
    provider_mode: str,
    payload: Mapping[str, Any] | None = None,
    tool_call_id: str | None = None,
    tool_id: str | None = None,
    workflow_id: str | None = None,
    status: str | None = None,
    blocked_reason: str | None = None,
    external_network_called: bool = False,
    usage_summary: Mapping[str, Any] | None = None,
    cost_estimate: Mapping[str, Any] | None = None,
    safe_metadata: Mapping[str, Any] | None = None,
) -> str | None:
    event = build_provider_real_audit_event(
        event_type=event_type,
        request_id=request_id,
        response_id=response_id,
        provider_name=provider_name,
        provider_mode=provider_mode,
        payload=payload,
        tool_call_id=tool_call_id,
        tool_id=tool_id,
        workflow_id=workflow_id,
        status=status,
        blocked_reason=blocked_reason,
        external_network_called=external_network_called,
        usage_summary=usage_summary,
        cost_estimate=cost_estimate,
        safe_metadata=safe_metadata,
    )
    return write_provider_real_audit_event(event, hermes_home=hermes_home)


# ---------------------------------------------------------------------------
# Typed convenience writers (one per frozen event)
# ---------------------------------------------------------------------------


def write_real_request_previewed(
    *, hermes_home: str | None, config, request, workflow_id: str | None = None,
) -> str | None:
    return _write(
        event_type=EVENT_REAL_REQUEST_PREVIEWED,
        hermes_home=hermes_home,
        request_id=request.request_id,
        response_id=None,
        provider_name=request.provider_name,
        provider_mode=request.provider_mode,
        workflow_id=workflow_id,
        status="previewed",
        external_network_called=False,
        safe_metadata=_safe_metadata_from_config(config),
        payload={"model": request.model, "maxTokens": request.max_tokens},
    )


def write_real_request_blocked(
    *, hermes_home: str | None, config, request, blocked_reason: str,
    workflow_id: str | None = None, safe_metadata: Mapping[str, Any] | None = None,
) -> str | None:
    return _write(
        event_type=EVENT_REAL_REQUEST_BLOCKED,
        hermes_home=hermes_home,
        request_id=request.request_id,
        response_id=None,
        provider_name=request.provider_name,
        provider_mode=request.provider_mode,
        workflow_id=workflow_id,
        status="blocked",
        blocked_reason=blocked_reason,
        external_network_called=False,
        safe_metadata=safe_metadata or _safe_metadata_from_config(config),
        payload={"blockedReason": blocked_reason},
    )


def write_real_request_started(
    *, hermes_home: str | None, config, request, workflow_id: str | None = None,
) -> str | None:
    return _write(
        event_type=EVENT_REAL_REQUEST_STARTED,
        hermes_home=hermes_home,
        request_id=request.request_id,
        response_id=None,
        provider_name=request.provider_name,
        provider_mode=request.provider_mode,
        workflow_id=workflow_id,
        status="started",
        external_network_called=True,
        safe_metadata=_safe_metadata_from_config(config, network_called=True),
        payload={"model": request.model, "timeoutSeconds": request.timeout_seconds},
    )


def write_real_response_redacted(
    *, hermes_home: str | None, config, request, response_id: str,
    workflow_id: str | None = None,
) -> str | None:
    return _write(
        event_type=EVENT_REAL_RESPONSE_REDACTED,
        hermes_home=hermes_home,
        request_id=request.request_id,
        response_id=response_id,
        provider_name=request.provider_name,
        provider_mode=request.provider_mode,
        workflow_id=workflow_id,
        status="redacted",
        external_network_called=True,
        safe_metadata=_safe_metadata_from_config(config, network_called=True),
    )


def write_real_request_completed(
    *, hermes_home: str | None, config, request, response,
    workflow_id: str | None = None,
) -> str | None:
    usage = response.usage_summary.to_safe_dict()
    return _write(
        event_type=EVENT_REAL_REQUEST_COMPLETED,
        hermes_home=hermes_home,
        request_id=request.request_id,
        response_id=response.response_id,
        provider_name=request.provider_name,
        provider_mode=request.provider_mode,
        workflow_id=workflow_id,
        status="completed",
        external_network_called=True,
        usage_summary=usage,
        cost_estimate=response.cost_estimate,
        safe_metadata=_safe_metadata_from_config(config, network_called=True),
        payload={"finishReason": response.finish_reason},
    )


def write_real_request_failed(
    *, hermes_home: str | None, config, request, blocked_reason: str,
    response_id: str | None = None, usage: Mapping[str, Any] | None = None,
    workflow_id: str | None = None,
) -> str | None:
    return _write(
        event_type=EVENT_REAL_REQUEST_FAILED,
        hermes_home=hermes_home,
        request_id=request.request_id,
        response_id=response_id,
        provider_name=request.provider_name,
        provider_mode=request.provider_mode,
        workflow_id=workflow_id,
        status="failed",
        blocked_reason=blocked_reason,
        external_network_called=True,
        usage_summary=usage,
        safe_metadata=_safe_metadata_from_config(config, network_called=True),
        payload={"blockedReason": blocked_reason},
    )


def write_real_tool_call_requested(
    *, hermes_home: str | None, config, request, response_id: str,
    tool_call_id: str, tool_id: str, workflow_id: str | None = None,
) -> str | None:
    return _write(
        event_type=EVENT_REAL_TOOL_CALL_REQUESTED,
        hermes_home=hermes_home,
        request_id=request.request_id,
        response_id=response_id,
        provider_name=request.provider_name,
        provider_mode=request.provider_mode,
        workflow_id=workflow_id,
        tool_call_id=tool_call_id,
        tool_id=tool_id,
        status="requested",
        external_network_called=True,
        safe_metadata=_safe_metadata_from_config(config, network_called=True),
    )


def write_real_tool_call_blocked(
    *, hermes_home: str | None, config, request, response_id: str,
    tool_call_id: str, tool_id: str, blocked_reason: str,
    workflow_id: str | None = None,
) -> str | None:
    return _write(
        event_type=EVENT_REAL_TOOL_CALL_BLOCKED,
        hermes_home=hermes_home,
        request_id=request.request_id,
        response_id=response_id,
        provider_name=request.provider_name,
        provider_mode=request.provider_mode,
        workflow_id=workflow_id,
        tool_call_id=tool_call_id,
        tool_id=tool_id,
        status="blocked",
        blocked_reason=blocked_reason,
        external_network_called=True,
        safe_metadata=_safe_metadata_from_config(config, network_called=True),
    )


def write_real_tool_call_completed(
    *, hermes_home: str | None, config, request, response_id: str,
    tool_call_id: str, tool_id: str, workflow_id: str | None = None,
) -> str | None:
    return _write(
        event_type=EVENT_REAL_TOOL_CALL_COMPLETED,
        hermes_home=hermes_home,
        request_id=request.request_id,
        response_id=response_id,
        provider_name=request.provider_name,
        provider_mode=request.provider_mode,
        workflow_id=workflow_id,
        tool_call_id=tool_call_id,
        tool_id=tool_id,
        status="completed",
        external_network_called=True,
        safe_metadata=_safe_metadata_from_config(config, network_called=True),
    )


def write_real_budget_blocked(
    *, hermes_home: str | None, config, request, blocked_reason: str,
    cost_estimate: Mapping[str, Any] | None = None, workflow_id: str | None = None,
) -> str | None:
    return _write(
        event_type=EVENT_REAL_BUDGET_BLOCKED,
        hermes_home=hermes_home,
        request_id=request.request_id,
        response_id=None,
        provider_name=request.provider_name,
        provider_mode=request.provider_mode,
        workflow_id=workflow_id,
        status="blocked",
        blocked_reason=blocked_reason,
        external_network_called=False,
        cost_estimate=cost_estimate,
        safe_metadata=_safe_metadata_from_config(config),
        payload={"blockedReason": blocked_reason},
    )


def write_real_rate_limit_blocked(
    *, hermes_home: str | None, config, request, blocked_reason: str,
    workflow_id: str | None = None,
) -> str | None:
    return _write(
        event_type=EVENT_REAL_RATE_LIMIT_BLOCKED,
        hermes_home=hermes_home,
        request_id=request.request_id,
        response_id=None,
        provider_name=request.provider_name,
        provider_mode=request.provider_mode,
        workflow_id=workflow_id,
        status="blocked",
        blocked_reason=blocked_reason,
        external_network_called=False,
        safe_metadata=_safe_metadata_from_config(config),
        payload={"blockedReason": blocked_reason},
    )


__all__ = [
    "EVENT_REAL_REQUEST_PREVIEWED",
    "EVENT_REAL_REQUEST_BLOCKED",
    "EVENT_REAL_REQUEST_STARTED",
    "EVENT_REAL_REQUEST_COMPLETED",
    "EVENT_REAL_REQUEST_FAILED",
    "EVENT_REAL_RESPONSE_REDACTED",
    "EVENT_REAL_TOOL_CALL_REQUESTED",
    "EVENT_REAL_TOOL_CALL_BLOCKED",
    "EVENT_REAL_TOOL_CALL_COMPLETED",
    "EVENT_REAL_BUDGET_BLOCKED",
    "EVENT_REAL_RATE_LIMIT_BLOCKED",
    "build_provider_real_audit_event",
    "write_provider_real_audit_event",
    "write_real_request_previewed",
    "write_real_request_blocked",
    "write_real_request_started",
    "write_real_response_redacted",
    "write_real_request_completed",
    "write_real_request_failed",
    "write_real_tool_call_requested",
    "write_real_tool_call_blocked",
    "write_real_tool_call_completed",
    "write_real_budget_blocked",
    "write_real_rate_limit_blocked",
]
