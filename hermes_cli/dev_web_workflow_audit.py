"""Phase 3A Workflow Audit Bridge for the Hermes Dev WebUI.

Writes dev-only workflow breadcrumb events into the existing Phase 2D durable
audit store. This module does NOT introduce a new audit kind — workflow events
reuse ``AUDIT_KIND_INTERNAL`` with ``eventType=workflow_*`` so they are
discoverable by the existing audit viewer / query engine without any new
audit-writer surface.

Design constraints (frozen):
  - stdlib only (besides the existing dev audit store, which is stdlib only)
  - every event is sanitized by the unified store sanitizer before append
  - no raw arguments, secrets, full token hashes, callable reprs, file content,
    or production paths ever reach the store
  - the write is confined to the dev ``HERMES_HOME``; never ``~/.hermes``
  - the write is best-effort: a failure is reported in the result and never
    raises (callers fail safe — a missing audit id means "no link", not "abort")
  - every workflow breadcrumb carries its workflow / plan / execution / step
    correlation ids so the UI can cross-navigate

Phase: 3A — Dev-only Agent Workflow MVP
Status: workflow audit bridge implemented
"""

from __future__ import annotations

from typing import Any, Mapping

from hermes_cli.dev_web_audit_schema import AUDIT_KIND_INTERNAL, AUDIT_SCHEMA_VERSION
from hermes_cli.dev_web_audit_store import (
    AuditStoreWriteResult,
    append_audit_event,
    build_audit_event,
)
from hermes_cli.dev_web_workflow_schema import (
    WORKFLOW_AUDIT_SOURCE,
    WORKFLOW_PHASE,
    WorkflowAuditLink,
    is_valid_workflow_event_type,
)


def redact_workflow_audit_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a safe, shallow copy of a workflow audit payload.

    Drops any key that resembles a secret / token / hash / callable / path and
    bounds string values. Never raises.
    """
    from hermes_cli.dev_web_workflow_schema import sanitize_workflow_value

    if not isinstance(payload, Mapping):
        return {}
    cleaned = sanitize_workflow_value(dict(payload))
    if not isinstance(cleaned, dict):
        return {}
    return cleaned


def write_workflow_audit_event(
    *,
    event_type: str,
    workflow_id: str | None = None,
    workflow_plan_id: str | None = None,
    workflow_execution_id: str | None = None,
    workflow_step_id: str | None = None,
    step_type: str | None = None,
    step_status: str | None = None,
    approval_id: str | None = None,
    tool_id: str | None = None,
    provider_mode: str | None = None,
    write_preview_id: str | None = None,
    rollback_id: str | None = None,
    audit_links: tuple[WorkflowAuditLink, ...] | tuple[()] = (),
    blocked_reason: str | None = None,
    status: str | None = None,
    summary: Mapping[str, Any] | None = None,
    safe_metadata: Mapping[str, Any] | None = None,
    hermes_home: str | None = None,
) -> AuditStoreWriteResult:
    """Append one workflow breadcrumb event to the Phase 2D durable store.

    Returns the :class:`AuditStoreWriteResult`. The ``event_id`` (on success)
    is the correlation id the caller should link back to the workflow step /
    timeline. Never raises.
    """
    if not is_valid_workflow_event_type(event_type):
        # Unknown event types are normalized to the timeline-updated breadcrumb
        # so a caller bug can never produce an un-queryable event.
        event_type = "workflow_timeline_updated"

    link_ids = [link.audit_id for link in audit_links if isinstance(link, WorkflowAuditLink)]

    safe_summary = redact_workflow_audit_payload(summary)
    safe_summary.setdefault("workflowId", workflow_id)
    if workflow_plan_id:
        safe_summary["workflowPlanId"] = workflow_plan_id
    if workflow_step_id:
        safe_summary["workflowStepId"] = workflow_step_id
    if step_type:
        safe_summary["stepType"] = step_type
    if step_status:
        safe_summary["stepStatus"] = step_status
    if link_ids:
        # Keep only the public correlation ids — never any payload.
        safe_summary["linkedAuditIds"] = link_ids[:16]

    meta = redact_workflow_audit_payload(safe_metadata)
    meta["schemaOrigin"] = "workflow_audit_v1"
    if workflow_execution_id:
        meta["workflowExecutionId"] = workflow_execution_id
    if approval_id:
        meta["workflowApprovalId"] = approval_id

    event = build_audit_event(
        event_type=event_type,
        audit_kind=AUDIT_KIND_INTERNAL,
        source=WORKFLOW_AUDIT_SOURCE,
        phase=WORKFLOW_PHASE,
        tool_id=tool_id,
        mode=None,
        status=status,
        blocked_reason=blocked_reason,
        read_only=True,
        write_required=False,
        provider_mode=provider_mode,
        provider_schema_sent=None,
        provider_api_called=None,
        external_network_called=False,
        local_side_effects=False,
        external_side_effects=False,
        redaction_applied=True,
        execution_id=workflow_execution_id,
        write_preview_id=write_preview_id,
        rollback_id=rollback_id,
        confirmation_token_id=approval_id,
        summary=safe_summary,
        safe_metadata=meta,
    )
    event["schemaVersion"] = AUDIT_SCHEMA_VERSION
    try:
        return append_audit_event(event, hermes_home=hermes_home)
    except Exception:
        # Fail safe: never propagate a store error to the workflow caller.
        return AuditStoreWriteResult(
            written=False,
            event_id=None,
            sequence=None,
            segment=None,
            rotated=False,
            error_code="workflow_audit_write_failed",
            error_message="Workflow audit write failed.",
        )


def audit_link_from_result(
    result: AuditStoreWriteResult | None,
    *,
    audit_kind: str = AUDIT_KIND_INTERNAL,
    label: str | None = None,
) -> WorkflowAuditLink | None:
    """Build a :class:`WorkflowAuditLink` from a store write result.

    Returns ``None`` when the write did not succeed (no event id to link).
    """
    if result is None or not getattr(result, "written", False):
        return None
    event_id = getattr(result, "event_id", None)
    if not isinstance(event_id, str) or not event_id:
        return None
    return WorkflowAuditLink(audit_id=event_id, audit_kind=audit_kind, label=label)


__all__ = [
    "write_workflow_audit_event",
    "redact_workflow_audit_payload",
    "audit_link_from_result",
]
