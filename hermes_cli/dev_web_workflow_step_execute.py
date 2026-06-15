"""Phase 3A Workflow Step Execution for the Hermes Dev WebUI.

Executes ONE workflow step at a time, manually and approval-gated, by reusing
the existing Phase 2 controlled-execution surfaces. The runner:

  - enforces step ordering (a step runs only after its predecessors completed)
  - consumes a single-use ``workflow_step_approval`` token before any execution
  - executes read-only tools via the existing bounded read-only dispatch
  - executes fake-provider round-trips via the existing offline fake provider
  - for sandbox_write_preview / rollback_reference steps it produces a PREVIEW /
    reference ONLY — it NEVER executes a write and NEVER executes a rollback
    (those keep their own scopes and confirmation flows)
  - writes workflow_step_started / completed / blocked / failed breadcrumbs and
    appends timeline events

Hard guarantees (frozen):
  - NEVER calls a real provider
  - NEVER auto-writes; NEVER auto-rolls-back
  - NEVER shells out, NEVER mutates a database, NEVER writes an external service
  - NEVER touches ``~/.hermes`` or production ``state.db``
  - every result is safe (no secrets / tokens / hashes / raw args / callables)

Phase: 3A — Dev-only Agent Workflow MVP
Status: workflow step execution implemented
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from hermes_cli.dev_web_workflow_approval import consume_step_approval
from hermes_cli.dev_web_workflow_audit import audit_link_from_result, write_workflow_audit_event
from hermes_cli.dev_web_workflow_schema import (
    BLOCKED_AUTONOMOUS_WRITE,
    BLOCKED_INVALID_INPUT,
    BLOCKED_ROLLBACK_EXECUTE,
    EVENT_WORKFLOW_EXECUTION_COMPLETED,
    EVENT_WORKFLOW_STEP_BLOCKED,
    EVENT_WORKFLOW_STEP_COMPLETED,
    EVENT_WORKFLOW_STEP_FAILED,
    EVENT_WORKFLOW_STEP_STARTED,
    EXEC_STATUS_COMPLETED,
    PROVIDER_MODE_FAKE,
    STATUS_BLOCKED,
    STATUS_COMPLETED,
    STATUS_SKIPPED,
    STEP_AUDIT_QUERY,
    STEP_FAKE_PROVIDER_ROUNDTRIP,
    STEP_MANUAL_NOTE,
    STEP_READ_ONLY_TOOL,
    STEP_ROLLBACK_REFERENCE,
    STEP_SANDBOX_WRITE_PREVIEW,
    WorkflowAuditLink,
    WorkflowExecutionState,
    WorkflowStep,
    WorkflowTimelineEvent,
    is_allowed_step_type,
    is_forbidden_step_type,
    new_workflow_id,
)


_COMPLETED_OR_SKIPPED = frozenset({STATUS_COMPLETED, STATUS_SKIPPED})


@dataclass(frozen=True, slots=True)
class WorkflowStepExecuteResult:
    ok: bool
    result: dict[str, Any] | None
    updated_state: WorkflowExecutionState | None
    audit_links: tuple[WorkflowAuditLink, ...]
    blocked_reason: str | None
    approval_id: str | None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_step_execution_allowed(step: WorkflowStep) -> tuple[bool, str | None]:
    """Return (allowed, blocked_reason). Never allows a forbidden step type."""
    if is_forbidden_step_type(step.step_type):
        return False, "blocked_workflow_step_type_not_allowed"
    if not is_allowed_step_type(step.step_type):
        return False, "blocked_workflow_step_type_not_allowed"
    return True, None


def _find_step_index(state: WorkflowExecutionState, step_id: str) -> int:
    for idx, step in enumerate(state.steps):
        if step.step_id == step_id:
            return idx
    return -1


def _rebuild_step(step: WorkflowStep, **changes: Any) -> WorkflowStep:
    """Return a copy of *step* with the given fields replaced."""
    from dataclasses import fields

    current = {f.name: getattr(step, f.name) for f in fields(step)}
    current.update(changes)
    return WorkflowStep(**current)


def _rebuild_state(state: WorkflowExecutionState, **changes: Any) -> WorkflowExecutionState:
    from dataclasses import fields

    current = {f.name: getattr(state, f.name) for f in fields(state)}
    current.update(changes)
    return WorkflowExecutionState(**current)


def _append_audit_link(
    existing: tuple[WorkflowAuditLink, ...], link: WorkflowAuditLink | None
) -> tuple[WorkflowAuditLink, ...]:
    return existing + ((link,) if link else ())


# ---------------------------------------------------------------------------
# Per-type executors (all side-effect-free w.r.t. write/rollback/shell/db)
# ---------------------------------------------------------------------------


def _exec_read_only_tool(step: WorkflowStep, hermes_home: str | None) -> dict[str, Any]:
    tool_id = step.tool_id or ""
    args = dict(step.input) if step.input else None
    if tool_id == "clarify":
        # Bounded deterministic clarify contract: present a clarifying question.
        question = ""
        choices: list[str] = []
        if isinstance(args, Mapping):
            q = args.get("question")
            if isinstance(q, str):
                question = q.strip()[:500]
            ch = args.get("choices")
            if isinstance(ch, list):
                choices = [str(c).strip()[:120] for c in ch if isinstance(c, (str, int))][:4]
        return {
            "type": "clarify",
            "message": "Clarifying question recorded (no tool side effects).",
            "result": {"question": question or "No question provided.", "choices": choices},
            "readOnly": True,
        }
    from hermes_cli.dev_web_read_only_tool_handlers import dispatch_read_only_tool

    result = dispatch_read_only_tool(tool_id, args, hermes_home=hermes_home)
    result["readOnly"] = True
    return result


def _exec_fake_provider(step: WorkflowStep, hermes_home: str | None) -> tuple[dict[str, Any], tuple[str, ...]]:
    from hermes_cli.dev_web_provider_roundtrip import run_provider_tool_roundtrip

    raw_input = dict(step.input) if step.input else {}
    message = raw_input.get("message") if isinstance(raw_input.get("message"), str) else ""
    allowed = raw_input.get("allowedToolIds")
    selected = frozenset(allowed) if isinstance(allowed, list) and allowed else None
    result = run_provider_tool_roundtrip(
        user_message=message,
        provider_mode=PROVIDER_MODE_FAKE,
        selected_tool_ids=selected,
        context={"uiOrigin": "dev-webui-workflow"},
        hermes_home=hermes_home,
    )
    data = result.to_safe_dict()
    data["workflowProviderMode"] = PROVIDER_MODE_FAKE
    return data, tuple(result.provider_audit_ids)


def _exec_sandbox_write_preview(step: WorkflowStep, hermes_home: str | None) -> dict[str, Any]:
    """Generate the write PREVIEW only. NEVER executes the write."""
    from hermes_cli.dev_web_write_plan import build_write_preview

    tool_id = step.tool_id or "dev_sandbox_file_write"
    raw_input = dict(step.input) if step.input else {}
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
    preview["workflowWriteExecuted"] = False
    preview["autoWriteBlocked"] = True
    preview["message"] = (
        "Sandbox write preview recorded. The workflow does not execute writes; "
        "execute the write separately via the existing write confirmation flow."
    )
    return preview


def _exec_rollback_reference(step: WorkflowStep, hermes_home: str | None) -> dict[str, Any]:
    """Read/preview the rollback reference only. NEVER executes the rollback."""
    from hermes_cli.dev_web_write_rollback import build_rollback_execution_preview
    from hermes_cli.dev_web_write_rollback_store import list_rollback_manifests

    raw_input = dict(step.input) if step.input else {}
    rollback_id = raw_input.get("rollbackId")
    out: dict[str, Any] = {
        "workflowRollbackExecuted": False,
        "autoRollbackBlocked": True,
        "readOnly": True,
        "message": (
            "Rollback reference recorded. The workflow does not execute rollbacks; "
            "execute the rollback separately via the existing rollback confirmation flow."
        ),
    }
    if isinstance(rollback_id, str) and rollback_id.strip():
        out["rollbackId"] = rollback_id.strip()
        try:
            out["rollbackPreview"] = build_rollback_execution_preview(
                rollback_id.strip(), hermes_home=hermes_home
            )
        except Exception:
            out["rollbackPreview"] = {"available": False}
    else:
        try:
            out["manifestList"] = list_rollback_manifests(limit=50, hermes_home=hermes_home)
        except Exception:
            out["manifestList"] = []
    return out


def _exec_audit_query(step: WorkflowStep, hermes_home: str | None) -> dict[str, Any]:
    from hermes_cli.dev_web_workflow_step_preview import _preview_audit_query

    return _preview_audit_query(step, hermes_home)


def _exec_manual_note(step: WorkflowStep, hermes_home: str | None) -> dict[str, Any]:
    raw_input = dict(step.input) if step.input else {}
    note = raw_input.get("note") if isinstance(raw_input.get("note"), str) else ""
    return {
        "type": "manual_note",
        "message": "Manual note recorded.",
        "result": {"noteLength": len(note), "readOnly": True},
        "readOnly": True,
    }


# ---------------------------------------------------------------------------
# Timeline helpers
# ---------------------------------------------------------------------------


def _make_timeline(
    *,
    event_type: str,
    step: WorkflowStep,
    audit_link: WorkflowAuditLink | None = None,
    message: str | None = None,
    blocked_reason: str | None = None,
    write_preview_id: str | None = None,
    rollback_id: str | None = None,
) -> WorkflowTimelineEvent:
    return WorkflowTimelineEvent(
        event_id=new_workflow_id("wfa_"),
        event_type=event_type,
        created_at=_now_iso(),
        step_id=step.step_id,
        step_type=step.step_type,
        step_status=step.status,
        approval_id=step.approval_id,
        tool_id=step.tool_id,
        provider_mode=step.provider_mode,
        write_preview_id=write_preview_id,
        rollback_id=rollback_id,
        audit_links=(audit_link,) if audit_link else (),
        message=message,
        blocked_reason=blocked_reason,
    )


# ---------------------------------------------------------------------------
# Top-level executor
# ---------------------------------------------------------------------------


def execute_workflow_step(
    state: WorkflowExecutionState,
    step_id: str,
    approval_token: str | None,
    *,
    hermes_home: str | None = None,
) -> WorkflowStepExecuteResult:
    """Manually execute one approved workflow step."""
    idx = _find_step_index(state, step_id)
    if idx < 0:
        return WorkflowStepExecuteResult(
            False, None, None, (), "blocked_workflow_step_not_found", None
        )
    step = state.steps[idx]

    # 1. Step-type allowlist (defense-in-depth; forbidden types never execute).
    allowed, type_reason = validate_step_execution_allowed(step)
    if not allowed:
        return WorkflowStepExecuteResult(False, None, None, (), type_reason, None)

    # 2. Step ordering — all predecessors must be completed / skipped.
    for prior in state.steps[:idx]:
        if prior.status not in _COMPLETED_OR_SKIPPED:
            return WorkflowStepExecuteResult(
                False, None, None, (), "blocked_workflow_step_order_not_satisfied", None
            )

    # 3. Approval gate — consume the single-use token bound to THIS step.
    consume = consume_step_approval(
        raw_token=approval_token,
        workflow_execution_id=state.workflow_execution_id,
        step_id=step.step_id,
        step_type=step.step_type,
        step_input=step.input,
        hermes_home=hermes_home,
    )
    if not consume.verified:
        return WorkflowStepExecuteResult(
            False, None, None, (), consume.blocked_reason, None
        )

    # 4. Execute per type (all preview/reference-only for write/rollback).
    audit_links: list[WorkflowAuditLink] = []
    timeline_events: list[WorkflowTimelineEvent] = []
    provider_audit_ids: tuple[str, ...] = ()
    try:
        if step.step_type == STEP_READ_ONLY_TOOL:
            result = _exec_read_only_tool(step, hermes_home)
        elif step.step_type == STEP_FAKE_PROVIDER_ROUNDTRIP:
            result, provider_audit_ids = _exec_fake_provider(step, hermes_home)
        elif step.step_type == STEP_SANDBOX_WRITE_PREVIEW:
            result = _exec_sandbox_write_preview(step, hermes_home)
        elif step.step_type == STEP_ROLLBACK_REFERENCE:
            result = _exec_rollback_reference(step, hermes_home)
        elif step.step_type == STEP_AUDIT_QUERY:
            result = _exec_audit_query(step, hermes_home)
        elif step.step_type == STEP_MANUAL_NOTE:
            result = _exec_manual_note(step, hermes_home)
        else:  # pragma: no cover — guarded by validate_step_execution_allowed
            return WorkflowStepExecuteResult(
                False, None, None, (), "blocked_workflow_step_type_not_allowed", None
            )
    except Exception:
        # Any execution failure → fail the step safely, never raise.
        fail_audit = write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_STEP_FAILED,
            workflow_id=state.workflow_id,
            workflow_plan_id=state.workflow_plan_id,
            workflow_execution_id=state.workflow_execution_id,
            workflow_step_id=step.step_id,
            step_type=step.step_type,
            tool_id=step.tool_id,
            status="error",
            hermes_home=hermes_home,
        )
        link = audit_link_from_result(fail_audit)
        failed_step = _rebuild_step(
            step, status=STATUS_BLOCKED, blocked_reason="blocked_workflow_step_failed", updated_at=_now_iso()
        )
        new_steps = state.steps[:idx] + (failed_step,) + state.steps[idx + 1 :]
        failed_state = _rebuild_state(state, steps=new_steps, updated_at=_now_iso())
        return WorkflowStepExecuteResult(
            False, None, failed_state, ((link,) if link else ()), "blocked_workflow_step_failed", None
        )

    # 5. Audit breadcrumbs + timeline.
    started_audit = write_workflow_audit_event(
        event_type=EVENT_WORKFLOW_STEP_STARTED,
        workflow_id=state.workflow_id,
        workflow_plan_id=state.workflow_plan_id,
        workflow_execution_id=state.workflow_execution_id,
        workflow_step_id=step.step_id,
        step_type=step.step_type,
        step_status="running",
        approval_id=consume.approval_id,
        tool_id=step.tool_id,
        provider_mode=step.provider_mode,
        status="ok",
        hermes_home=hermes_home,
    )
    started_link = audit_link_from_result(started_audit)
    timeline_events.append(
        _make_timeline(
            event_type=EVENT_WORKFLOW_STEP_STARTED,
            step=_rebuild_step(step, approval_id=consume.approval_id),
            audit_link=started_link,
            message=f"Step started: {step.title}",
        )
    )
    if started_link:
        audit_links.append(started_link)

    # Link any provider audit ids produced by the fake round-trip.
    for paid in provider_audit_ids:
        if isinstance(paid, str) and paid:
            audit_links.append(
                WorkflowAuditLink(audit_id=paid, audit_kind="provider", label="provider audit")
            )

    write_preview_id = result.get("writePreviewId") or result.get("writePlanId") if isinstance(result, Mapping) else None
    rollback_id = result.get("rollbackId") if isinstance(result, Mapping) else None

    completed_audit = write_workflow_audit_event(
        event_type=EVENT_WORKFLOW_STEP_COMPLETED,
        workflow_id=state.workflow_id,
        workflow_plan_id=state.workflow_plan_id,
        workflow_execution_id=state.workflow_execution_id,
        workflow_step_id=step.step_id,
        step_type=step.step_type,
        step_status=STATUS_COMPLETED,
        approval_id=consume.approval_id,
        tool_id=step.tool_id,
        provider_mode=step.provider_mode,
        write_preview_id=write_preview_id,
        rollback_id=rollback_id,
        status="completed",
        audit_links=tuple(audit_links),
        summary={"providerAuditIds": list(provider_audit_ids)},
        hermes_home=hermes_home,
    )
    completed_link = audit_link_from_result(completed_audit)
    if completed_link:
        audit_links.append(completed_link)
    timeline_events.append(
        _make_timeline(
            event_type=EVENT_WORKFLOW_STEP_COMPLETED,
            step=_rebuild_step(step, status=STATUS_COMPLETED, approval_id=consume.approval_id),
            audit_link=completed_link,
            message=f"Step completed: {step.title}",
            write_preview_id=write_preview_id,
            rollback_id=rollback_id,
        )
    )

    # 6. Build the updated state (mark step completed, advance cursor).
    completed_step = _rebuild_step(
        step,
        status=STATUS_COMPLETED,
        result=result,
        approval_id=consume.approval_id,
        audit_links=step.audit_links + tuple(audit_links),
        updated_at=_now_iso(),
    )
    new_steps = state.steps[:idx] + (completed_step,) + state.steps[idx + 1 :]
    completed_count = sum(1 for s in new_steps if s.status == STATUS_COMPLETED)

    # Advance the cursor to the next non-completed step (or None if done).
    next_cursor: str | None = None
    for s in new_steps[idx + 1 :]:
        if s.status not in _COMPLETED_OR_SKIPPED:
            next_cursor = s.step_id
            break

    exec_status = state.status
    if completed_count == len(new_steps):
        exec_status = EXEC_STATUS_COMPLETED
        # Workflow-completion breadcrumb.
        done_audit = write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_EXECUTION_COMPLETED,
            workflow_id=state.workflow_id,
            workflow_plan_id=state.workflow_plan_id,
            workflow_execution_id=state.workflow_execution_id,
            status="completed",
            summary={"completedStepCount": completed_count, "totalStepCount": len(new_steps)},
            hermes_home=hermes_home,
        )
        done_link = audit_link_from_result(done_audit)
        if done_link:
            audit_links.append(done_link)
        timeline_events.append(
            WorkflowTimelineEvent(
                event_id=new_workflow_id("wfa_"),
                event_type=EVENT_WORKFLOW_EXECUTION_COMPLETED,
                created_at=_now_iso(),
                message="Workflow execution completed.",
                audit_links=(done_link,) if done_link else (),
            )
        )

    # Persist timeline events (best-effort).
    from hermes_cli.dev_web_workflow_store import append_workflow_timeline_event

    for event in timeline_events:
        append_workflow_timeline_event(
            state.workflow_execution_id, event, hermes_home=hermes_home
        )

    updated_state = _rebuild_state(
        state,
        steps=new_steps,
        cursor_step_id=next_cursor,
        status=exec_status,
        updated_at=_now_iso(),
        completed_step_count=completed_count,
        timeline=state.timeline + tuple(timeline_events),
    )
    return WorkflowStepExecuteResult(
        True, result, updated_state, tuple(audit_links), None, consume.approval_id
    )


__all__ = [
    "execute_workflow_step",
    "validate_step_execution_allowed",
    "WorkflowStepExecuteResult",
]
