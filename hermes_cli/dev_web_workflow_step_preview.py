"""Phase 3A Workflow Step Preview for the Hermes Dev WebUI.

Builds a non-executing preview for a single workflow step by reusing the
existing Phase 2 controlled-execution preview surfaces:

  - read_only_tool        → existing dry-run policy engine (no handler call)
  - fake_provider_roundtrip → provider schema preview (no API call, no network)
  - sandbox_write_preview → existing write PREVIEW (never writes a file)
  - rollback_reference    → existing rollback PREVIEW / manifest read (no execute)
  - manual_note           → sanitized display only
  - audit_query           → existing read-only audit query

Guarantees (frozen):
  - NEVER executes a tool, NEVER writes a file, NEVER calls a provider,
    NEVER executes a rollback, NEVER mutates state outside the workflow store
  - writes a ``workflow_step_preview_created`` breadcrumb to the durable store
  - every returned field is safe (no secrets / tokens / hashes / raw args /
    callable reprs / production paths)

Phase: 3A — Dev-only Agent Workflow MVP
Status: workflow step preview implemented
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from hermes_cli.dev_web_workflow_audit import audit_link_from_result, write_workflow_audit_event
from hermes_cli.dev_web_workflow_schema import (
    EVENT_WORKFLOW_STEP_PREVIEW_CREATED,
    STEP_AUDIT_QUERY,
    STEP_FAKE_PROVIDER_ROUNDTRIP,
    STEP_MANUAL_NOTE,
    STEP_READ_ONLY_TOOL,
    STEP_ROLLBACK_REFERENCE,
    STEP_SANDBOX_WRITE_PREVIEW,
    STATUS_PREVIEWED,
    WorkflowAuditLink,
    WorkflowExecutionState,
    WorkflowStep,
)


@dataclass(frozen=True, slots=True)
class WorkflowStepPreviewResult:
    ok: bool
    preview: dict[str, Any] | None
    audit_link: WorkflowAuditLink | None
    updated_step: WorkflowStep | None
    blocked_reason: str | None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_step(state: WorkflowExecutionState, step_id: str) -> WorkflowStep | None:
    for step in state.steps:
        if step.step_id == step_id:
            return step
    return None


# ---------------------------------------------------------------------------
# Per-type preview builders
# ---------------------------------------------------------------------------


def _preview_read_only_tool(step: WorkflowStep, hermes_home: str | None) -> dict[str, Any]:
    from hermes_cli.dev_web_tool_dry_run import dry_run_tool_policy

    canonical_name = step.tool_id or ""
    args = dict(step.input) if step.input else None
    result = dry_run_tool_policy(
        canonical_name,
        args,
        source_context="workflow_step_preview",
        ui_origin="dev-webui",
    )
    preview = result.to_safe_dict()
    preview["previewKind"] = "read_only_tool_dry_run"
    preview["readOnly"] = True
    return preview


def _preview_fake_provider(step: WorkflowStep, hermes_home: str | None) -> dict[str, Any]:
    from hermes_cli.dev_web_provider_schema import (
        build_provider_request_schema_summary,
        build_provider_tool_schema,
        redact_provider_schema_for_audit,
    )

    message = ""
    raw_input = dict(step.input) if step.input else {}
    if isinstance(raw_input.get("message"), str):
        message = raw_input["message"]
    allowed = tuple(raw_input.get("allowedToolIds") or []) or None
    try:
        bundle = build_provider_tool_schema(allowed)
        schema_preview = redact_provider_schema_for_audit(bundle)
        schema_summary = build_provider_request_schema_summary()
    except Exception:
        schema_preview = {}
        schema_summary = {}
    preview: dict[str, Any] = {
        "previewKind": "fake_provider_schema_preview",
        "providerMode": step.provider_mode or "fake",
        "messageLength": len(message),
        "allowedToolIds": list(allowed) if allowed else [],
        "schemaSummary": schema_summary,
        "redactedSchemaPreview": schema_preview,
        "providerApiCalled": False,
        "providerSchemaSent": False,
        "externalNetworkCalled": False,
        "readOnlyOnly": True,
        "autoWriteBlocked": True,
    }
    return preview


def _preview_sandbox_write(step: WorkflowStep, hermes_home: str | None) -> dict[str, Any]:
    from hermes_cli.dev_web_write_plan import build_write_preview

    tool_id = step.tool_id or "dev_sandbox_file_write"
    raw_input = dict(step.input) if step.input else {}
    # The write preview wants a normalized args dict shaped for the tool.
    args: dict[str, Any] = {}
    target = raw_input.get("targetRelativePath") or raw_input.get("targetPath")
    if isinstance(target, str):
        args["targetPath"] = target
    content = raw_input.get("content")
    if isinstance(content, str):
        args["content"] = content
    mode = raw_input.get("mode")
    if isinstance(mode, str):
        args["mode"] = mode
    preview = build_write_preview(tool_id, args or None, hermes_home=hermes_home)
    preview["previewKind"] = "sandbox_write_preview"
    preview["writeExecuted"] = False
    preview["autoWriteBlocked"] = True
    return preview


def _preview_rollback_reference(step: WorkflowStep, hermes_home: str | None) -> dict[str, Any]:
    from hermes_cli.dev_web_write_rollback import build_rollback_execution_preview
    from hermes_cli.dev_web_write_rollback_store import list_rollback_manifests

    raw_input = dict(step.input) if step.input else {}
    rollback_id = raw_input.get("rollbackId")
    preview: dict[str, Any] = {
        "previewKind": "rollback_reference_preview",
        "readOnly": True,
        "rollbackExecuted": False,
        "autoRollbackBlocked": True,
    }
    if isinstance(rollback_id, str) and rollback_id.strip():
        preview["rollbackId"] = rollback_id.strip()
        try:
            inner = build_rollback_execution_preview(rollback_id.strip(), hermes_home=hermes_home)
            preview["rollbackPreview"] = inner
        except Exception:
            preview["rollbackPreview"] = {"available": False}
    else:
        # No specific manifest requested → list the known manifests (read-only).
        try:
            manifests = list_rollback_manifests(limit=50, hermes_home=hermes_home)
        except Exception:
            manifests = []
        preview["manifestList"] = manifests
        preview["manifestCount"] = len(manifests) if isinstance(manifests, list) else 0
    return preview


def _preview_manual_note(step: WorkflowStep, hermes_home: str | None) -> dict[str, Any]:
    raw_input = dict(step.input) if step.input else {}
    note = raw_input.get("note") if isinstance(raw_input.get("note"), str) else ""
    return {
        "previewKind": "manual_note_display",
        "readOnly": True,
        "noteLength": len(note),
        "notePreview": (note[:240] + "…") if len(note) > 240 else note,
    }


def _preview_audit_query(step: WorkflowStep, hermes_home: str | None) -> dict[str, Any]:
    from hermes_cli.dev_web_audit_query import (
        audit_query_result_to_safe_dict,
        build_audit_query,
        query_audit_events,
    )

    raw_input = dict(step.input) if step.input else {}
    try:
        query = build_audit_query(
            limit=int(raw_input.get("limit", 20)) if isinstance(raw_input.get("limit"), int) else 20,
            cursor=None,
            order="desc",
            event_type=raw_input.get("eventType") if isinstance(raw_input.get("eventType"), str) else None,
            tool_id=raw_input.get("toolId") if isinstance(raw_input.get("toolId"), str) else None,
            status=raw_input.get("status") if isinstance(raw_input.get("status"), str) else None,
            audit_kind="internal",
            source=None,
            provider_mode=None,
            read_only=None,
            write_required=None,
            from_created_at=None,
            to_created_at=None,
            search=raw_input.get("search") if isinstance(raw_input.get("search"), str) else None,
            include_summary=True,
        )
        result = query_audit_events(query, hermes_home=hermes_home)
        payload = audit_query_result_to_safe_dict(result)
    except TypeError:
        # build_audit_query signature drift — degrade to a safe empty preview.
        payload = {"items": [], "success": False}
    payload["previewKind"] = "audit_query_read_only"
    payload["readOnly"] = True
    return payload


_PREVIEW_BUILDERS = {
    STEP_READ_ONLY_TOOL: _preview_read_only_tool,
    STEP_FAKE_PROVIDER_ROUNDTRIP: _preview_fake_provider,
    STEP_SANDBOX_WRITE_PREVIEW: _preview_sandbox_write,
    STEP_ROLLBACK_REFERENCE: _preview_rollback_reference,
    STEP_MANUAL_NOTE: _preview_manual_note,
    STEP_AUDIT_QUERY: _preview_audit_query,
}


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def validate_step_preview(preview: Mapping[str, Any] | None) -> tuple[bool, str | None]:
    """Validate a built preview envelope structurally."""
    if not isinstance(preview, Mapping):
        return False, "preview is not a JSON object"
    if "previewKind" not in preview:
        return False, "preview missing previewKind"
    return True, None


def build_step_preview(
    state: WorkflowExecutionState,
    step_id: str,
    *,
    hermes_home: str | None = None,
) -> WorkflowStepPreviewResult:
    """Build a non-executing preview for one step of an execution."""
    step = _find_step(state, step_id)
    if step is None:
        return WorkflowStepPreviewResult(False, None, None, None, "blocked_workflow_step_not_found")
    builder = _PREVIEW_BUILDERS.get(step.step_type)
    if builder is None:
        return WorkflowStepPreviewResult(False, None, None, None, "blocked_workflow_step_type_not_allowed")

    try:
        preview = dict(builder(step, hermes_home))
    except Exception:
        return WorkflowStepPreviewResult(False, None, None, None, "blocked_workflow_invalid_input")

    ok, reason = validate_step_preview(preview)
    if not ok:
        return WorkflowStepPreviewResult(False, None, None, None, "blocked_workflow_invalid_input")

    # Write the breadcrumb + link it.
    audit_result = write_workflow_audit_event(
        event_type=EVENT_WORKFLOW_STEP_PREVIEW_CREATED,
        workflow_id=state.workflow_id,
        workflow_plan_id=state.workflow_plan_id,
        workflow_execution_id=state.workflow_execution_id,
        workflow_step_id=step.step_id,
        step_type=step.step_type,
        tool_id=step.tool_id,
        provider_mode=step.provider_mode,
        write_preview_id=preview.get("writePreviewId") or preview.get("writePlanId"),
        rollback_id=preview.get("rollbackId"),
        status="preview",
        summary={"previewKind": preview.get("previewKind")},
        hermes_home=hermes_home,
    )
    audit_link = audit_link_from_result(audit_result)

    updated_step = WorkflowStep(
        step_id=step.step_id,
        step_type=step.step_type,
        title=step.title,
        status=STATUS_PREVIEWED,
        description=step.description,
        tool_id=step.tool_id,
        provider_mode=step.provider_mode,
        allowed_tool_ids=step.allowed_tool_ids,
        requires_approval=step.requires_approval,
        requires_dry_run=step.requires_dry_run,
        requires_confirmation=step.requires_confirmation,
        write_required=step.write_required,
        read_only=step.read_only,
        local_side_effects=step.local_side_effects,
        external_side_effects=step.external_side_effects,
        input=step.input,
        safe_input_summary=step.safe_input_summary,
        preview=preview,
        result=step.result,
        audit_links=step.audit_links + ((audit_link,) if audit_link else ()),
        blocked_reason=step.blocked_reason,
        approval_id=step.approval_id,
        created_at=step.created_at,
        updated_at=_now_iso(),
    )
    return WorkflowStepPreviewResult(True, preview, audit_link, updated_step, None)


__all__ = [
    "build_step_preview",
    "validate_step_preview",
    "WorkflowStepPreviewResult",
]
