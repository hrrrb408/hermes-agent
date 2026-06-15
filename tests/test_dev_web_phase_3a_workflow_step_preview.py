"""Phase 3A — Workflow step preview tests.

Verifies each step-type preview reuses the existing preview surfaces and NEVER
executes: read-only dry-run, fake-provider schema preview (no API call), sandbox
write preview (no file write), rollback reference (no rollback execute), manual
note display, and audit query (read-only).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.dev_web_workflow_schema import (
    STEP_AUDIT_QUERY,
    STEP_FAKE_PROVIDER_ROUNDTRIP,
    STEP_MANUAL_NOTE,
    STEP_READ_ONLY_TOOL,
    STEP_ROLLBACK_REFERENCE,
    STEP_SANDBOX_WRITE_PREVIEW,
    STATUS_PREVIEWED,
    WORKFLOW_SAFETY_BOUNDARY,
    WORKFLOW_SCHEMA_VERSION,
    WorkflowExecutionState,
    WorkflowStep,
    new_workflow_id,
)
from hermes_cli.dev_web_workflow_step_preview import build_step_preview, validate_step_preview


@pytest.fixture
def dev_home(tmp_path: Path) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return str(home)


def _execution(steps: tuple[WorkflowStep, ...]) -> WorkflowExecutionState:
    return WorkflowExecutionState(
        workflow_execution_id=new_workflow_id("wfx_"),
        workflow_id=new_workflow_id("wf_"),
        workflow_plan_id=new_workflow_id("wfp_"),
        schema_version=WORKFLOW_SCHEMA_VERSION,
        title="Demo",
        status="running",
        steps=steps,
        cursor_step_id=steps[0].step_id,
        safety_boundary=WORKFLOW_SAFETY_BOUNDARY,
        created_at="2026-06-16T00:00:00+00:00",
        updated_at="2026-06-16T00:00:00+00:00",
        total_step_count=len(steps),
    )


class TestPreviews:
    def test_read_only_preview_uses_dry_run(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL,
            title="Read env", tool_id="dev_environment_read", input={"includePorts": True},
        )
        st = _execution((step,))
        r = build_step_preview(st, step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.preview["previewKind"] == "read_only_tool_dry_run"
        assert r.updated_step.status == STATUS_PREVIEWED
        assert r.audit_link is not None

    def test_fake_provider_preview_no_api_call(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_FAKE_PROVIDER_ROUNDTRIP,
            title="Provider", provider_mode="fake",
            input={"message": "hi", "allowedToolIds": ["tool_policy_read"]},
        )
        st = _execution((step,))
        r = build_step_preview(st, step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.preview["providerApiCalled"] is False
        assert r.preview["externalNetworkCalled"] is False
        assert r.preview["readOnlyOnly"] is True

    def test_sandbox_write_preview_does_not_write(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_SANDBOX_WRITE_PREVIEW,
            title="Write preview", tool_id="dev_sandbox_file_write",
            input={"targetRelativePath": "notes/preview.md", "content": "c"},
        )
        st = _execution((step,))
        r = build_step_preview(st, step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.preview["writeExecuted"] is False
        assert r.preview["autoWriteBlocked"] is True

    def test_rollback_reference_preview_does_not_execute(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_ROLLBACK_REFERENCE,
            title="Rollback ref", input={},
        )
        st = _execution((step,))
        r = build_step_preview(st, step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.preview["rollbackExecuted"] is False
        assert r.preview["autoRollbackBlocked"] is True

    def test_manual_note_preview_display_only(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_MANUAL_NOTE,
            title="Note", input={"note": "a safe note"},
        )
        st = _execution((step,))
        r = build_step_preview(st, step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.preview["previewKind"] == "manual_note_display"
        assert r.preview["noteLength"] == len("a safe note")

    def test_audit_query_preview_read_only(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_AUDIT_QUERY,
            title="Audit query", input={"limit": 5},
        )
        st = _execution((step,))
        r = build_step_preview(st, step.step_id, hermes_home=dev_home)
        assert r.ok
        assert r.preview["readOnly"] is True

    def test_unknown_step_blocked(self, dev_home: str) -> None:
        step = WorkflowStep(
            step_id=new_workflow_id("wfs_"), step_type=STEP_READ_ONLY_TOOL,
            title="x", tool_id="dev_environment_read",
        )
        st = _execution((step,))
        # Step id not in the execution → not found.
        r = build_step_preview(st, "wfs_missing", hermes_home=dev_home)
        assert not r.ok

    def test_validate_step_preview(self) -> None:
        ok, _ = validate_step_preview({"previewKind": "x"})
        assert ok
        ok2, _ = validate_step_preview({"nope": 1})
        assert not ok2
