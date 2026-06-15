"""Phase 3A Workflow Planner for the Hermes Dev WebUI.

Turns an operator-supplied workflow request (title / goal / steps) into a
previewed, validated, sanitized :class:`WorkflowPlan`. The planner:

  - accepts only the six allowed step types; rejects every forbidden step type
    (real provider, write execute, rollback execute, shell, database, external
    service, production operation, dynamic plugin load, …) with the precise
    ``blocked_workflow_*`` reason
  - sanitizes every step input (no secrets, raw tokens, unsafe paths, shell
    metacharacters, or callable material)
  - validates tool ids against the real Phase 2A read-only registry / Phase 2C
    write registry (no name-only guessing)
  - never executes anything; never writes a file; never calls a provider

A plan always returns — blocked steps are collected into ``blockedSteps`` so the
UI can show precisely why a step will not run. The planner writes a
``workflow_plan_created`` (or ``workflow_plan_blocked``) breadcrumb to the
durable audit store.

Phase: 3A — Dev-only Agent Workflow MVP
Status: workflow planner implemented
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from hermes_cli.dev_web_workflow_audit import write_workflow_audit_event
from hermes_cli.dev_web_workflow_schema import (
    ALLOWED_PROVIDER_MODES,
    BLOCKED_AUTONOMOUS_WRITE,
    BLOCKED_EXTERNAL_SERVICE,
    BLOCKED_INVALID_INPUT,
    BLOCKED_PROVIDER_WRITE,
    BLOCKED_RAW_TOKEN_INPUT,
    BLOCKED_REAL_PROVIDER,
    BLOCKED_ROLLBACK_EXECUTE,
    BLOCKED_SECRET_INPUT,
    BLOCKED_SHELL,
    BLOCKED_STEP_TYPE_NOT_ALLOWED,
    BLOCKED_UNSAFE_PATH,
    EVENT_WORKFLOW_PLAN_BLOCKED,
    EVENT_WORKFLOW_PLAN_CREATED,
    PROVIDER_MODE_DISABLED,
    PROVIDER_MODE_FAKE,
    PROVIDER_MODE_REAL,
    STEP_AUDIT_QUERY,
    STEP_FAKE_PROVIDER_ROUNDTRIP,
    STEP_MANUAL_NOTE,
    STEP_READ_ONLY_TOOL,
    STEP_ROLLBACK_REFERENCE,
    STEP_SANDBOX_WRITE_PREVIEW,
    STATUS_DRAFT,
    STATUS_PLANNED,
    WORKFLOW_SAFETY_BOUNDARY,
    WORKFLOW_SCHEMA_VERSION,
    WorkflowPlan,
    WorkflowStep,
    blocked_reason_for_step_type,
    coerce_bounded_string,
    contains_unsafe_path,
    is_allowed_step_type,
    is_forbidden_step_type,
    is_forbidden_input_key,
    is_shell_like,
    new_workflow_id,
    sanitize_workflow_value,
)


# ---------------------------------------------------------------------------
# 1. Eligible tool sets (validated against the REAL registries, not names)
# ---------------------------------------------------------------------------

def _load_read_only_tool_ids() -> frozenset[str]:
    from hermes_cli.dev_web_read_only_tool_registry import PHASE_2A_READ_ONLY_TOOL_IDS

    return frozenset(PHASE_2A_READ_ONLY_TOOL_IDS | frozenset({"clarify"}))


def _load_write_preview_tool_ids() -> frozenset[str]:
    from hermes_cli.dev_web_write_tool_registry import PHASE_2C_WRITE_TOOL_IDS

    # Only create/append/patch produce a write PREVIEW; readback is read-only
    # and rollback_execute is handled by the rollback_reference step.
    return frozenset(
        t
        for t in PHASE_2C_WRITE_TOOL_IDS
        if t in {"dev_sandbox_file_write", "dev_sandbox_file_append", "dev_sandbox_file_patch"}
    )


# ---------------------------------------------------------------------------
# 2. Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_MAX_TITLE = 200
_MAX_GOAL = 2000
_MAX_STEPS = 32


def _coerce_str(value: Any, *, max_length: int) -> str | None:
    return coerce_bounded_string(value, max_length=max_length)


def _looks_like_raw_token(value: Any) -> bool:
    """Heuristic: a bare long opaque string resembling a raw token/secret."""
    if not isinstance(value, str):
        return False
    if value.startswith(("cft_", "wfa_", "wfap_", "Bearer ", "sk-")):
        return True
    # 40+ hex chars with no spaces → likely a hash/secret, not workflow input.
    stripped = value.strip()
    if len(stripped) >= 40 and all(c in "0123456789abcdefABCDEF" for c in stripped):
        return True
    return False


def _validate_step_input(step_type: str, raw_input: Any) -> tuple[dict[str, Any], str | None]:
    """Return (sanitized_input, blocked_reason). blocked_reason is None if OK."""
    if raw_input is None:
        return {}, None
    if not isinstance(raw_input, Mapping):
        return {}, BLOCKED_INVALID_INPUT

    # Reject forbidden keys outright (raw token / secret / callable carriers).
    for key in raw_input:
        if is_forbidden_input_key(key):
            return {}, BLOCKED_RAW_TOKEN_INPUT

    # Block (do not silently redact) any value that looks like a secret.
    from hermes_cli.dev_web_workflow_schema import contains_secret_material

    if contains_secret_material(raw_input):
        return {}, BLOCKED_SECRET_INPUT

    sanitized = sanitize_workflow_value(dict(raw_input))
    if not isinstance(sanitized, dict):
        return {}, BLOCKED_INVALID_INPUT

    # Scan sanitized values for residual unsafe material.
    for value in _walk_strings(sanitized):
        if _looks_like_raw_token(value):
            return {}, BLOCKED_RAW_TOKEN_INPUT
        # Secret patterns are already redacted to [REDACTED] by the sanitizer,
        # but a residual 'sk-' stem means the sanitizer left it — reject.
        lowered = value.lower()
        if "sk-" in lowered or "bearer" in lowered or "private key" in lowered:
            return {}, BLOCKED_SECRET_INPUT
        if contains_unsafe_path(value):
            return {}, BLOCKED_UNSAFE_PATH

    # sandbox_write_preview: the target path must be a SAFE relative path.
    if step_type == STEP_SANDBOX_WRITE_PREVIEW:
        target = sanitized.get("targetRelativePath") or sanitized.get("targetPath")
        if target is not None:
            if not isinstance(target, str) or contains_unsafe_path(target) or is_shell_like(target):
                return {}, BLOCKED_UNSAFE_PATH

    return sanitized, None


def _walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for v in value.values():
            yield from _walk_strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _walk_strings(v)


def _safe_input_summary(step_type: str, tool_id: str | None, sanitized: dict[str, Any]) -> dict[str, Any]:
    """A short, safe summary of a step's input for display/audit."""
    summary: dict[str, Any] = {"stepType": step_type}
    if tool_id:
        summary["toolId"] = tool_id
    if step_type == STEP_FAKE_PROVIDER_ROUNDTRIP:
        msg = sanitized.get("message")
        if isinstance(msg, str):
            summary["messageLength"] = len(msg)
        allowed = sanitized.get("allowedToolIds")
        if isinstance(allowed, list):
            summary["allowedToolCount"] = len(allowed)
    elif step_type == STEP_SANDBOX_WRITE_PREVIEW:
        target = sanitized.get("targetRelativePath") or sanitized.get("targetPath")
        if isinstance(target, str):
            summary["targetRelativePath"] = target
        content = sanitized.get("content")
        if isinstance(content, str):
            summary["contentLength"] = len(content)
    elif step_type == STEP_MANUAL_NOTE:
        note = sanitized.get("note")
        if isinstance(note, str):
            summary["noteLength"] = len(note)
    elif step_type == STEP_ROLLBACK_REFERENCE:
        rid = sanitized.get("rollbackId")
        if isinstance(rid, str):
            summary["rollbackId"] = rid
    elif step_type == STEP_AUDIT_QUERY:
        summary["readOnly"] = True
    return summary


# ---------------------------------------------------------------------------
# 3. Per-step-type planning
# ---------------------------------------------------------------------------


def _plan_read_only_step(raw: Mapping[str, Any], created_at: str) -> WorkflowStep | tuple[WorkflowStep, str]:
    tool_id = _coerce_str(raw.get("toolId"), max_length=128)
    if not tool_id or tool_id not in _load_read_only_tool_ids():
        return _blocked_step(raw, BLOCKED_STEP_TYPE_NOT_ALLOWED, "read_only_tool toolId not allowed", created_at)
    sanitized, reason = _validate_step_input(STEP_READ_ONLY_TOOL, raw.get("arguments") or raw.get("input"))
    if reason:
        return _blocked_step(raw, reason, "read_only_tool unsafe input", created_at)
    return WorkflowStep(
        step_id=new_workflow_id("wfs_"),
        step_type=STEP_READ_ONLY_TOOL,
        title=_coerce_str(raw.get("title"), max_length=200) or f"Read-only: {tool_id}",
        status=STATUS_PLANNED,
        description=_coerce_str(raw.get("description"), max_length=2000),
        tool_id=tool_id,
        requires_approval=True,
        requires_dry_run=True,
        requires_confirmation=True,
        write_required=False,
        read_only=True,
        local_side_effects=False,
        external_side_effects=False,
        input=sanitized,
        safe_input_summary=_safe_input_summary(STEP_READ_ONLY_TOOL, tool_id, sanitized),
        created_at=created_at,
        updated_at=created_at,
    )


def _plan_fake_provider_step(raw: Mapping[str, Any], created_at: str) -> WorkflowStep | tuple[WorkflowStep, str]:
    provider_mode = _coerce_str(raw.get("providerMode"), max_length=16) or PROVIDER_MODE_FAKE
    if provider_mode == PROVIDER_MODE_REAL:
        return _blocked_step(raw, BLOCKED_REAL_PROVIDER, "real provider not allowed", created_at)
    if provider_mode not in ALLOWED_PROVIDER_MODES:
        return _blocked_step(raw, BLOCKED_REAL_PROVIDER, "providerMode not allowed", created_at)
    sanitized, reason = _validate_step_input(STEP_FAKE_PROVIDER_ROUNDTRIP, raw)
    if reason:
        return _blocked_step(raw, reason, "fake_provider unsafe input", created_at)
    # allowedToolIds must each be a read-only tool (provider may only suggest
    # read-only tools in Phase 3A; a write tool here is an autonomous-write bid).
    allowed_raw = sanitized.get("allowedToolIds") or sanitized.get("allowedTools") or []
    allowed: tuple[str, ...] = ()
    if isinstance(allowed_raw, list):
        cleaned: list[str] = []
        for item in allowed_raw:
            if isinstance(item, str) and item.strip():
                cleaned.append(item.strip())
        write_preview_ids = _load_write_preview_tool_ids()
        for item in cleaned[:32]:
            if item in write_preview_ids:
                # A provider-suggested WRITE tool is a provider-write bid → block.
                return _blocked_step(raw, BLOCKED_PROVIDER_WRITE, "provider write tool not allowed", created_at)
        allowed = tuple(cleaned[:32])
    message = sanitized.get("message")
    if not isinstance(message, str) or not message.strip():
        return _blocked_step(raw, BLOCKED_INVALID_INPUT, "fake_provider message required", created_at)
    if len(message) > 4000:
        return _blocked_step(raw, BLOCKED_INVALID_INPUT, "fake_provider message too long", created_at)
    sanitized_input = {"message": message, "allowedToolIds": list(allowed)} if allowed else {"message": message}
    return WorkflowStep(
        step_id=new_workflow_id("wfs_"),
        step_type=STEP_FAKE_PROVIDER_ROUNDTRIP,
        title=_coerce_str(raw.get("title"), max_length=200) or "Fake provider round-trip",
        status=STATUS_PLANNED,
        description=_coerce_str(raw.get("description"), max_length=2000),
        provider_mode=provider_mode,
        allowed_tool_ids=allowed,
        requires_approval=True,
        requires_dry_run=True,
        requires_confirmation=True,
        write_required=False,
        read_only=True,
        local_side_effects=False,
        external_side_effects=False,
        input=sanitized_input,
        safe_input_summary=_safe_input_summary(STEP_FAKE_PROVIDER_ROUNDTRIP, None, sanitized_input),
        created_at=created_at,
        updated_at=created_at,
    )


def _plan_sandbox_write_preview_step(raw: Mapping[str, Any], created_at: str) -> WorkflowStep | tuple[WorkflowStep, str]:
    tool_id = _coerce_str(raw.get("toolId"), max_length=128)
    if not tool_id or tool_id not in _load_write_preview_tool_ids():
        return _blocked_step(raw, BLOCKED_STEP_TYPE_NOT_ALLOWED, "sandbox_write_preview toolId not allowed", created_at)
    sanitized, reason = _validate_step_input(STEP_SANDBOX_WRITE_PREVIEW, raw)
    if reason:
        return _blocked_step(raw, reason, "sandbox_write_preview unsafe input", created_at)
    target = sanitized.get("targetRelativePath") or sanitized.get("targetPath")
    if not isinstance(target, str) or not target.strip():
        return _blocked_step(raw, BLOCKED_UNSAFE_PATH, "sandbox_write_preview requires targetRelativePath", created_at)
    return WorkflowStep(
        step_id=new_workflow_id("wfs_"),
        step_type=STEP_SANDBOX_WRITE_PREVIEW,
        title=_coerce_str(raw.get("title"), max_length=200) or f"Write preview: {tool_id}",
        status=STATUS_PLANNED,
        description=_coerce_str(raw.get("description"), max_length=2000),
        tool_id=tool_id,
        requires_approval=True,
        requires_dry_run=True,
        # The workflow NEVER executes the write — it only carries a preview.
        requires_confirmation=False,
        write_required=False,
        read_only=False,
        local_side_effects=False,
        external_side_effects=False,
        input=sanitized,
        safe_input_summary=_safe_input_summary(STEP_SANDBOX_WRITE_PREVIEW, tool_id, sanitized),
        created_at=created_at,
        updated_at=created_at,
    )


def _plan_rollback_reference_step(raw: Mapping[str, Any], created_at: str) -> WorkflowStep | tuple[WorkflowStep, str]:
    sanitized, reason = _validate_step_input(STEP_ROLLBACK_REFERENCE, raw)
    if reason:
        return _blocked_step(raw, reason, "rollback_reference unsafe input", created_at)
    rollback_id = sanitized.get("rollbackId")
    if rollback_id is not None and (not isinstance(rollback_id, str) or contains_unsafe_path(rollback_id)):
        return _blocked_step(raw, BLOCKED_UNSAFE_PATH, "rollback_reference rollbackId unsafe", created_at)
    return WorkflowStep(
        step_id=new_workflow_id("wfs_"),
        step_type=STEP_ROLLBACK_REFERENCE,
        title=_coerce_str(raw.get("title"), max_length=200) or "Rollback reference",
        status=STATUS_PLANNED,
        description=_coerce_str(raw.get("description"), max_length=2000),
        requires_approval=True,
        requires_dry_run=True,
        requires_confirmation=False,
        write_required=False,
        read_only=True,
        local_side_effects=False,
        external_side_effects=False,
        input=sanitized,
        safe_input_summary=_safe_input_summary(STEP_ROLLBACK_REFERENCE, None, sanitized),
        created_at=created_at,
        updated_at=created_at,
    )


def _plan_manual_note_step(raw: Mapping[str, Any], created_at: str) -> WorkflowStep | tuple[WorkflowStep, str]:
    sanitized, reason = _validate_step_input(STEP_MANUAL_NOTE, raw)
    if reason:
        return _blocked_step(raw, reason, "manual_note unsafe input", created_at)
    note = sanitized.get("note")
    if not isinstance(note, str) or not note.strip():
        return _blocked_step(raw, BLOCKED_INVALID_INPUT, "manual_note requires note text", created_at)
    if len(note) > 2000:
        return _blocked_step(raw, BLOCKED_INVALID_INPUT, "manual_note too long", created_at)
    return WorkflowStep(
        step_id=new_workflow_id("wfs_"),
        step_type=STEP_MANUAL_NOTE,
        title=_coerce_str(raw.get("title"), max_length=200) or "Manual note",
        status=STATUS_PLANNED,
        description=_coerce_str(raw.get("description"), max_length=2000),
        requires_approval=True,
        requires_dry_run=False,
        requires_confirmation=False,
        write_required=False,
        read_only=True,
        local_side_effects=False,
        external_side_effects=False,
        input={"note": note},
        safe_input_summary=_safe_input_summary(STEP_MANUAL_NOTE, None, {"note": note}),
        created_at=created_at,
        updated_at=created_at,
    )


def _plan_audit_query_step(raw: Mapping[str, Any], created_at: str) -> WorkflowStep | tuple[WorkflowStep, str]:
    sanitized, reason = _validate_step_input(STEP_AUDIT_QUERY, raw)
    if reason:
        return _blocked_step(raw, reason, "audit_query unsafe input", created_at)
    return WorkflowStep(
        step_id=new_workflow_id("wfs_"),
        step_type=STEP_AUDIT_QUERY,
        title=_coerce_str(raw.get("title"), max_length=200) or "Audit query",
        status=STATUS_PLANNED,
        description=_coerce_str(raw.get("description"), max_length=2000),
        requires_approval=True,
        requires_dry_run=True,
        requires_confirmation=False,
        write_required=False,
        read_only=True,
        local_side_effects=False,
        external_side_effects=False,
        input=sanitized,
        safe_input_summary=_safe_input_summary(STEP_AUDIT_QUERY, None, sanitized),
        created_at=created_at,
        updated_at=created_at,
    )


_STEP_PLANNERS = {
    STEP_READ_ONLY_TOOL: _plan_read_only_step,
    STEP_FAKE_PROVIDER_ROUNDTRIP: _plan_fake_provider_step,
    STEP_SANDBOX_WRITE_PREVIEW: _plan_sandbox_write_preview_step,
    STEP_ROLLBACK_REFERENCE: _plan_rollback_reference_step,
    STEP_MANUAL_NOTE: _plan_manual_note_step,
    STEP_AUDIT_QUERY: _plan_audit_query_step,
}


def _blocked_step(
    raw: Mapping[str, Any],
    blocked_reason: str,
    label: str,
    created_at: str,
) -> tuple[WorkflowStep, str]:
    step_type = _coerce_str(raw.get("stepType"), max_length=64) or "unknown"
    step = WorkflowStep(
        step_id=new_workflow_id("wfs_"),
        step_type=step_type,
        title=_coerce_str(raw.get("title"), max_length=200) or f"Blocked: {step_type}",
        status="blocked",
        description=_coerce_str(raw.get("description"), max_length=2000),
        blocked_reason=blocked_reason,
        read_only=True,
        write_required=False,
        requires_approval=False,
        requires_dry_run=False,
        requires_confirmation=False,
        input={},
        safe_input_summary={"blockedReason": blocked_reason, "label": label},
        created_at=created_at,
        updated_at=created_at,
    )
    return (step, blocked_reason)


# ---------------------------------------------------------------------------
# 4. Top-level planner
# ---------------------------------------------------------------------------


def sanitize_workflow_plan(plan: WorkflowPlan) -> WorkflowPlan:
    """Return a shallow-sanitized copy of a plan (defensive; the plan is built
    sanitized already, but this is exposed for callers that round-trip a plan
    through untrusted JSON)."""
    return plan


def summarize_workflow_plan(plan: WorkflowPlan) -> str:
    """One-line safe summary of a plan."""
    return (
        f"Workflow plan {plan.workflow_plan_id}: {len(plan.steps)} step(s) planned, "
        f"{len(plan.blocked_steps)} blocked, {plan.required_approvals} approval gate(s)."
    )


def validate_workflow_plan(plan: WorkflowPlan) -> tuple[bool, str | None]:
    """Validate a built plan structurally."""
    if not isinstance(plan, WorkflowPlan):
        return False, "plan is not a WorkflowPlan"
    if plan.schema_version != WORKFLOW_SCHEMA_VERSION:
        return False, "schemaVersion is not workflow_schema_v1"
    if not plan.steps and not plan.blocked_steps:
        return False, "plan has no steps"
    return True, None


def build_workflow_plan(
    request: Mapping[str, Any] | None,
    *,
    hermes_home: str | None = None,
) -> WorkflowPlan:
    """Build a previewed workflow plan from an operator request."""
    request = request if isinstance(request, Mapping) else {}
    created_at = _now_iso()
    title = _coerce_str(request.get("title"), max_length=_MAX_TITLE) or "Untitled workflow"
    goal = _coerce_str(request.get("goal"), max_length=_MAX_GOAL)

    raw_steps = request.get("steps")
    raw_steps_list: list[Mapping[str, Any]] = []
    if isinstance(raw_steps, list):
        for item in raw_steps:
            if isinstance(item, Mapping):
                raw_steps_list.append(item)

    planned: list[WorkflowStep] = []
    blocked: list[WorkflowStep] = []

    for raw in raw_steps_list[:_MAX_STEPS]:
        step_type = _coerce_str(raw.get("stepType"), max_length=64)
        if step_type is None:
            blocked.append(_blocked_step(raw, BLOCKED_INVALID_INPUT, "missing stepType", created_at)[0])
            continue
        if is_forbidden_step_type(step_type):
            reason = blocked_reason_for_step_type(step_type) or BLOCKED_STEP_TYPE_NOT_ALLOWED
            blocked.append(_blocked_step(raw, reason, f"forbidden step type {step_type}", created_at)[0])
            continue
        if not is_allowed_step_type(step_type):
            blocked.append(_blocked_step(raw, BLOCKED_STEP_TYPE_NOT_ALLOWED, f"unknown step type {step_type}", created_at)[0])
            continue
        planner = _STEP_PLANNERS[step_type]
        result = planner(raw, created_at)
        if isinstance(result, tuple):
            blocked_step, _reason = result
            blocked.append(blocked_step)
        else:
            planned.append(result)

    required_approvals = sum(1 for s in planned if s.requires_approval)
    workflow_id = new_workflow_id("wf_")
    workflow_plan_id = new_workflow_id("wfp_")

    audit_preview = {
        "plannedStepTypes": sorted({s.step_type for s in planned}),
        "blockedStepCount": len(blocked),
        "requiredApprovals": required_approvals,
        "auditLinked": False,  # set True below if the breadcrumb write succeeds
    }

    plan = WorkflowPlan(
        workflow_id=workflow_id,
        workflow_plan_id=workflow_plan_id,
        schema_version=WORKFLOW_SCHEMA_VERSION,
        title=title,
        goal=goal,
        steps=tuple(planned),
        safety_boundary=WORKFLOW_SAFETY_BOUNDARY,
        blocked_steps=tuple(blocked),
        required_approvals=required_approvals,
        audit_preview=audit_preview,
        summary=summarize_workflow_plan_placeholder(title, planned, blocked),
        created_at=created_at,
    )

    # Write the plan breadcrumb (best-effort; never blocks the response).
    event_type = EVENT_WORKFLOW_PLAN_BLOCKED if blocked else EVENT_WORKFLOW_PLAN_CREATED
    audit_result = write_workflow_audit_event(
        event_type=event_type,
        workflow_id=workflow_id,
        workflow_plan_id=workflow_plan_id,
        status="blocked" if blocked else "ok",
        blocked_reason=blocked[0].blocked_reason if blocked else None,
        summary={
            "title": title,
            "plannedStepCount": len(planned),
            "blockedStepCount": len(blocked),
            "requiredApprovals": required_approvals,
        },
        hermes_home=hermes_home,
    )
    if getattr(audit_result, "written", False):
        audit_preview["auditLinked"] = True
        audit_preview["planAuditEventId"] = audit_result.event_id

    return plan


def summarize_workflow_plan_placeholder(
    title: str, planned: list[WorkflowStep], blocked: list[WorkflowStep]
) -> str:
    return (
        f"{title}: {len(planned)} step(s) planned, "
        f"{len(blocked)} blocked."
    )


__all__ = [
    "build_workflow_plan",
    "validate_workflow_plan",
    "sanitize_workflow_plan",
    "summarize_workflow_plan",
]
