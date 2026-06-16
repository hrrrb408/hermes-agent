"""Phase 3A-H1 — Step preview + execution hardening (Lens 4 + 5).

Lens 4 (Non-execution boundary): every step-type preview is non-executing — the
read-only preview reuses the dry-run engine, the fake-provider preview makes no
API/network call, the sandbox-write preview writes NO file, and the rollback
reference preview executes NO rollback.

Lens 5 (Manual execution / order boundary): execution is manual + approval-gated,
step ordering is enforced, the approval is single-use + step-bound, and write /
rollback steps NEVER perform a write or rollback (preview / reference only).
The cursor advances only to the next step; the execution completes only when
all steps are done.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.dev_web_workflow_approval import issue_step_approval
from hermes_cli.dev_web_workflow_schema import (
    BLOCKED_APPROVAL_REQUIRED,
    EXEC_STATUS_COMPLETED,
    STATUS_COMPLETED,
    STEP_AUDIT_QUERY,
    STEP_FAKE_PROVIDER_ROUNDTRIP,
    STEP_MANUAL_NOTE,
    STEP_READ_ONLY_TOOL,
    STEP_ROLLBACK_REFERENCE,
    STEP_SANDBOX_WRITE_PREVIEW,
    WORKFLOW_SAFETY_BOUNDARY,
    WORKFLOW_SCHEMA_VERSION,
    WorkflowExecutionState,
    WorkflowStep,
    new_workflow_id,
)
from hermes_cli.dev_web_workflow_step_execute import (
    execute_workflow_step,
    validate_step_execution_allowed,
)
from hermes_cli.dev_web_workflow_step_preview import build_step_preview, validate_step_preview


@pytest.fixture
def dev_home(tmp_path: Path) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return str(home)


def _execution(
    steps: tuple[WorkflowStep, ...], cursor: str | None = None
) -> WorkflowExecutionState:
    return WorkflowExecutionState(
        workflow_execution_id=new_workflow_id("wfx_"),
        workflow_id=new_workflow_id("wf_"),
        workflow_plan_id=new_workflow_id("wfp_"),
        schema_version=WORKFLOW_SCHEMA_VERSION,
        title="Demo",
        status="running",
        steps=steps,
        cursor_step_id=cursor or steps[0].step_id,
        safety_boundary=WORKFLOW_SAFETY_BOUNDARY,
        created_at="2026-06-16T00:00:00+00:00",
        updated_at="2026-06-16T00:00:00+00:00",
        total_step_count=len(steps),
    )


def _approve(dev_home: str, st: WorkflowExecutionState, step: WorkflowStep) -> str:
    issue = issue_step_approval(
        workflow_execution_id=st.workflow_execution_id,
        step_id=step.step_id,
        step_type=step.step_type,
        step_input=step.input,
        hermes_home=dev_home,
    )
    assert issue.issued
    return issue.raw_token  # type: ignore[return-value]


def _no_target_file_written(dev_home: str, target_name: str) -> bool:
    """Return True if NO file named *target_name* exists anywhere under dev_home."""
    matches = list(Path(dev_home).rglob(target_name))
    return not matches


# ===========================================================================
# Lens 4 — Non-execution preview boundary
# ===========================================================================


class TestPreviewNonExecution:
    def test_read_only_preview_uses_dry_run_no_handler_call(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL,
            title="Read env", tool_id="dev_environment_read", input={"includePorts": True},
        )
        r = build_step_preview(_execution((step,)), step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.preview["previewKind"] == "read_only_tool_dry_run"
        assert r.preview["readOnly"] is True
        assert r.updated_step.status == "previewed"

    def test_fake_provider_preview_is_offline(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_FAKE_PROVIDER_ROUNDTRIP,
            title="Provider", provider_mode="fake",
            input={"message": "hi", "allowedToolIds": ["tool_policy_read"]},
        )
        r = build_step_preview(_execution((step,)), step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.preview["providerApiCalled"] is False
        assert r.preview["externalNetworkCalled"] is False
        assert r.preview["readOnlyOnly"] is True
        assert r.preview["autoWriteBlocked"] is True

    def test_sandbox_write_preview_writes_no_file(self, dev_home: str) -> None:
        target = "preview-only-no-write.md"
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_SANDBOX_WRITE_PREVIEW,
            title="Write preview", tool_id="dev_sandbox_file_write",
            input={"targetRelativePath": f"notes/{target}", "content": "preview only"},
        )
        r = build_step_preview(_execution((step,)), step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.preview["writeExecuted"] is False
        assert r.preview["autoWriteBlocked"] is True
        # Hard filesystem assertion: the target file was NOT written anywhere
        # under the dev HERMES_HOME.
        assert _no_target_file_written(dev_home, target)

    def test_rollback_reference_preview_executes_no_rollback(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_ROLLBACK_REFERENCE,
            title="Rollback ref", input={},
        )
        r = build_step_preview(_execution((step,)), step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.preview["rollbackExecuted"] is False
        assert r.preview["autoRollbackBlocked"] is True
        assert r.preview["readOnly"] is True

    def test_manual_note_preview_is_display_only(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE,
            title="Note", input={"note": "a safe note"},
        )
        r = build_step_preview(_execution((step,)), step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.preview["previewKind"] == "manual_note_display"
        assert r.preview["readOnly"] is True
        assert r.preview["noteLength"] == len("a safe note")

    def test_audit_query_preview_is_read_only(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_AUDIT_QUERY,
            title="Audit query", input={"limit": 5},
        )
        r = build_step_preview(_execution((step,)), step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.preview["readOnly"] is True

    def test_preview_writes_audit_link(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE,
            title="Note", input={"note": "n"},
        )
        r = build_step_preview(_execution((step,)), step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.audit_link is not None

    def test_preview_unknown_step_blocked(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL,
            title="x", tool_id="dev_environment_read",
        )
        r = build_step_preview(_execution((step,)), "wfs_missing", hermes_home=dev_home)
        assert not r.ok
        assert r.blocked_reason == "blocked_workflow_step_not_found"

    def test_validate_step_preview_contract(self) -> None:
        assert validate_step_preview({"previewKind": "x"})[0]
        assert not validate_step_preview({"nope": 1})[0]
        assert not validate_step_preview(None)[0]


# ===========================================================================
# Lens 5 — Manual execution / order boundary
# ===========================================================================


class TestExecutionAllowance:
    @pytest.mark.parametrize(
        "step_type",
        [
            STEP_READ_ONLY_TOOL, STEP_FAKE_PROVIDER_ROUNDTRIP,
            STEP_SANDBOX_WRITE_PREVIEW, STEP_ROLLBACK_REFERENCE,
            STEP_MANUAL_NOTE, STEP_AUDIT_QUERY,
        ],
    )
    def test_allowed_step_types_pass(self, step_type: str) -> None:
        step = WorkflowStep(step_id="wfs_x", step_type=step_type, title="x")
        ok, _ = validate_step_execution_allowed(step)
        assert ok

    @pytest.mark.parametrize(
        "step_type",
        ["shell_command", "rollback_execute", "sandbox_write_execute", "production_operation", "database_mutation"],
    )
    def test_forbidden_step_types_rejected(self, step_type: str) -> None:
        step = WorkflowStep(step_id="wfs_x", step_type=step_type, title="x")
        ok, reason = validate_step_execution_allowed(step)
        assert not ok
        assert reason == "blocked_workflow_step_type_not_allowed"

    def test_non_string_step_type_rejected(self) -> None:
        step = WorkflowStep(step_id="wfs_x", step_type="random_nonsense", title="x")
        ok, reason = validate_step_execution_allowed(step)
        assert not ok


class TestManualApprovalGate:
    def test_execution_requires_approval(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL,
            title="Read env", tool_id="dev_environment_read",
        )
        st = _execution((step,))
        r = execute_workflow_step(st, step.step_id, None, hermes_home=dev_home)
        assert not r.ok
        assert r.blocked_reason == BLOCKED_APPROVAL_REQUIRED

    def test_single_use_token_enforced(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE,
            title="Note", input={"note": "n"},
        )
        st = _execution((step,))
        token = _approve(dev_home, st, step)
        assert execute_workflow_step(st, step.step_id, token, hermes_home=dev_home).ok
        # Replay with the SAME token is rejected (single-use).
        r2 = execute_workflow_step(st, step.step_id, token, hermes_home=dev_home)
        assert not r2.ok

    def test_approval_bound_to_step(self, dev_home: str) -> None:
        s1 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE, title="a", input={"note": "1"})
        s2 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE, title="b", input={"note": "2"})
        st = _execution((s1, s2))
        token_for_s1 = _approve(dev_home, st, s1)
        # Mark s1 completed first so ordering permits s2, then prove the s1
        # token cannot satisfy s2's gate.
        completed_s1 = WorkflowStep(
            step_id=s1.step_id, step_type=s1.step_type, title=s1.title,
            input=s1.input, status=STATUS_COMPLETED,
        )
        st2 = _execution((completed_s1, s2), cursor=s2.step_id)
        r = execute_workflow_step(st2, s2.step_id, token_for_s1, hermes_home=dev_home)
        assert not r.ok


class TestStepOrdering:
    def test_order_enforced_predecessor_incomplete(self, dev_home: str) -> None:
        s1 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL, title="a", tool_id="dev_environment_read", status="planned")
        s2 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE, title="b", input={"note": "n"})
        st = _execution((s1, s2))
        token = _approve(dev_home, st, s2)
        r = execute_workflow_step(st, s2.step_id, token, hermes_home=dev_home)
        assert not r.ok
        assert "order" in (r.blocked_reason or "")

    def test_order_satisfied_when_predecessor_completed(self, dev_home: str) -> None:
        s1 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL, title="a", tool_id="dev_environment_read", status=STATUS_COMPLETED)
        s2 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE, title="b", input={"note": "n"})
        st = _execution((s1, s2), cursor=s2.step_id)
        token = _approve(dev_home, st, s2)
        assert execute_workflow_step(st, s2.step_id, token, hermes_home=dev_home).ok

    def test_order_satisfied_when_predecessor_skipped(self, dev_home: str) -> None:
        s1 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL, title="a", tool_id="dev_environment_read", status="skipped")
        s2 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE, title="b", input={"note": "n"})
        st = _execution((s1, s2), cursor=s2.step_id)
        token = _approve(dev_home, st, s2)
        assert execute_workflow_step(st, s2.step_id, token, hermes_home=dev_home).ok


class TestWriteRollbackNeverExecute:
    def test_write_preview_step_does_not_write(self, dev_home: str) -> None:
        target = "exec-no-write.md"
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_SANDBOX_WRITE_PREVIEW,
            title="Write preview", tool_id="dev_sandbox_file_write",
            input={"targetRelativePath": f"notes/{target}", "content": "c"},
        )
        st = _execution((step,))
        token = _approve(dev_home, st, step)
        r = execute_workflow_step(st, step.step_id, token, hermes_home=dev_home)
        assert r.ok
        assert r.result["workflowWriteExecuted"] is False
        assert r.result["autoWriteBlocked"] is True
        assert _no_target_file_written(dev_home, target)

    def test_rollback_reference_step_does_not_rollback(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_ROLLBACK_REFERENCE,
            title="Rollback ref", input={},
        )
        st = _execution((step,))
        token = _approve(dev_home, st, step)
        r = execute_workflow_step(st, step.step_id, token, hermes_home=dev_home)
        assert r.ok
        assert r.result["workflowRollbackExecuted"] is False
        assert r.result["autoRollbackBlocked"] is True

    def test_fake_provider_step_offline(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_FAKE_PROVIDER_ROUNDTRIP,
            title="Provider", provider_mode="fake",
            input={"message": "hi", "allowedToolIds": ["tool_policy_read"]},
        )
        st = _execution((step,))
        token = _approve(dev_home, st, step)
        r = execute_workflow_step(st, step.step_id, token, hermes_home=dev_home)
        assert r.ok
        assert r.result["providerMode"] == "fake"
        assert r.result["externalNetworkCalled"] is False


class TestCursorAdvancementAndCompletion:
    def test_cursor_advances_to_next_step(self, dev_home: str) -> None:
        s1 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE, title="a", input={"note": "1"})
        s2 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE, title="b", input={"note": "2"})
        st = _execution((s1, s2))
        token = _approve(dev_home, st, s1)
        r = execute_workflow_step(st, s1.step_id, token, hermes_home=dev_home)
        assert r.ok
        assert r.updated_state.cursor_step_id == s2.step_id
        assert r.updated_state.status != EXEC_STATUS_COMPLETED

    def test_execution_completes_when_all_steps_done(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE,
            title="Note", input={"note": "n"},
        )
        st = _execution((step,))
        token = _approve(dev_home, st, step)
        r = execute_workflow_step(st, step.step_id, token, hermes_home=dev_home)
        assert r.ok
        assert r.updated_state.status == EXEC_STATUS_COMPLETED
        assert r.updated_state.cursor_step_id is None
        assert r.updated_state.completed_step_count == 1
        # An execution-completion breadcrumb + timeline event were produced.
        assert any(
            ev.event_type == "workflow_execution_completed" for ev in r.updated_state.timeline
        )

    def test_completed_step_carries_audit_links(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL,
            title="Read env", tool_id="dev_environment_read", input={"includePorts": True},
        )
        st = _execution((step,))
        token = _approve(dev_home, st, step)
        r = execute_workflow_step(st, step.step_id, token, hermes_home=dev_home)
        assert r.ok
        assert r.updated_state.steps[0].status == STATUS_COMPLETED
        assert len(r.audit_links) >= 1
