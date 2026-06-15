"""Phase 3A — Workflow step execution tests.

Verifies manual, approval-gated step execution: step ordering is enforced, an
approval token is required + consumed (single-use), read-only and fake-provider
steps execute, while write-execute and rollback-execute are NEVER performed
(the workflow only carries previews/references). Audit links are produced.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.dev_web_workflow_approval import issue_step_approval
from hermes_cli.dev_web_workflow_schema import (
    BLOCKED_APPROVAL_REQUIRED,
    EXEC_STATUS_COMPLETED,
    STEP_FAKE_PROVIDER_ROUNDTRIP,
    STEP_MANUAL_NOTE,
    STEP_READ_ONLY_TOOL,
    STEP_ROLLBACK_REFERENCE,
    STEP_SANDBOX_WRITE_PREVIEW,
    STATUS_COMPLETED,
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


@pytest.fixture
def dev_home(tmp_path: Path) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return str(home)


def _execution(steps: tuple[WorkflowStep, ...], cursor: str | None = None) -> WorkflowExecutionState:
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
        step_id=step.step_id, step_type=step.step_type, step_input=step.input,
        hermes_home=dev_home,
    )
    assert issue.issued
    return issue.raw_token  # type: ignore[return-value]


class TestExecutionAllowance:
    def test_allowed_step_types_pass_validation(self) -> None:
        for t in (STEP_READ_ONLY_TOOL, STEP_FAKE_PROVIDER_ROUNDTRIP, STEP_SANDBOX_WRITE_PREVIEW, STEP_ROLLBACK_REFERENCE, STEP_MANUAL_NOTE):
            step = WorkflowStep(step_id="wfs_x", step_type=t, title="x")
            ok, _ = validate_step_execution_allowed(step)
            assert ok

    def test_forbidden_step_type_rejected(self) -> None:
        step = WorkflowStep(step_id="wfs_x", step_type="shell_command", title="x")
        ok, reason = validate_step_execution_allowed(step)
        assert not ok
        assert reason == "blocked_workflow_step_type_not_allowed"


class TestManualExecution:
    def test_read_only_step_executes_with_approval(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL,
            title="Read env", tool_id="dev_environment_read", input={"includePorts": True},
        )
        st = _execution((step,))
        token = _approve(dev_home, st, step)
        r = execute_workflow_step(st, step.step_id, token, hermes_home=dev_home)
        assert r.ok
        assert r.updated_state.steps[0].status == STATUS_COMPLETED
        assert r.updated_state.status == EXEC_STATUS_COMPLETED
        assert len(r.audit_links) >= 1

    def test_execution_requires_approval(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL,
            title="Read env", tool_id="dev_environment_read",
        )
        st = _execution((step,))
        r = execute_workflow_step(st, step.step_id, None, hermes_home=dev_home)
        assert not r.ok
        assert r.blocked_reason == BLOCKED_APPROVAL_REQUIRED

    def test_single_use_token(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE,
            title="Note", input={"note": "n"},
        )
        st = _execution((step,))
        token = _approve(dev_home, st, step)
        r1 = execute_workflow_step(st, step.step_id, token, hermes_home=dev_home)
        assert r1.ok
        r2 = execute_workflow_step(st, step.step_id, token, hermes_home=dev_home)
        assert not r2.ok

    def test_step_order_enforced(self, dev_home: str) -> None:
        s1 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL, title="a", tool_id="dev_environment_read", status=STATUS_COMPLETED)
        s2 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE, title="b", input={"note": "n"})
        st = _execution((s1, s2), cursor=s2.step_id)
        token = _approve(dev_home, st, s2)
        # s1 is completed, so s2 may execute.
        r = execute_workflow_step(st, s2.step_id, token, hermes_home=dev_home)
        assert r.ok

    def test_step_order_blocks_unfinished_predecessor(self, dev_home: str) -> None:
        s1 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL, title="a", tool_id="dev_environment_read", status="planned")
        s2 = WorkflowStep(step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE, title="b", input={"note": "n"})
        st = _execution((s1, s2))
        token = _approve(dev_home, st, s2)
        r = execute_workflow_step(st, s2.step_id, token, hermes_home=dev_home)
        assert not r.ok
        assert "order" in (r.blocked_reason or "")


class TestWriteRollbackNeverExecute:
    def test_write_preview_step_does_not_write(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_SANDBOX_WRITE_PREVIEW,
            title="Write preview", tool_id="dev_sandbox_file_write",
            input={"targetRelativePath": "notes/x.md", "content": "c"},
        )
        st = _execution((step,))
        token = _approve(dev_home, st, step)
        r = execute_workflow_step(st, step.step_id, token, hermes_home=dev_home)
        assert r.ok
        assert r.result["workflowWriteExecuted"] is False
        assert r.result["autoWriteBlocked"] is True

    def test_rollback_reference_step_does_not_execute(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_ROLLBACK_REFERENCE,
            title="Rollback ref", input={},
        )
        st = _execution((step,))
        token = _approve(dev_home, st, step)
        r = execute_workflow_step(st, step.step_id, token, hermes_home=dev_home)
        assert r.ok
        assert r.result["workflowRollbackExecuted"] is False

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
