"""Phase 3A — Workflow state store tests.

Verifies the dev-only file-backed store: it lives under the dev HERMES_HOME,
never under the repo / ~/.hermes / production; definitions + executions +
timelines round-trip; corruption is skipped safely; and the persisted documents
contain no raw tokens / hashes / arguments / file content / API keys.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_workflow_schema import (
    WORKFLOW_SAFETY_BOUNDARY,
    WORKFLOW_SCHEMA_VERSION,
    WorkflowDefinition,
    WorkflowExecutionState,
    WorkflowStep,
    WorkflowTimelineEvent,
    STEP_READ_ONLY_TOOL,
    new_workflow_id,
)
from hermes_cli.dev_web_workflow_store import (
    ERROR_HOME_PRODUCTION,
    ERROR_HOME_REPO,
    append_workflow_timeline_event,
    ensure_workflow_store,
    get_workflow_store_root,
    list_workflow_executions,
    load_workflow_definition,
    load_workflow_execution,
    save_workflow_definition,
    save_workflow_execution,
    validate_workflow_store_root,
)


@pytest.fixture
def dev_home(tmp_path: Path) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return str(home)


def _step(step_type: str = STEP_READ_ONLY_TOOL) -> WorkflowStep:
    return WorkflowStep(
        step_id=new_workflow_id("wfs_"),
        step_type=step_type,
        title="Read env",
        tool_id="dev_environment_read",
    )


def _execution(dev_home: str) -> WorkflowExecutionState:
    return WorkflowExecutionState(
        workflow_execution_id=new_workflow_id("wfx_"),
        workflow_id=new_workflow_id("wf_"),
        workflow_plan_id=new_workflow_id("wfp_"),
        schema_version=WORKFLOW_SCHEMA_VERSION,
        title="Demo",
        status="running",
        steps=(_step(),),
        cursor_step_id=None,
        safety_boundary=WORKFLOW_SAFETY_BOUNDARY,
        created_at="2026-06-16T00:00:00+00:00",
        updated_at="2026-06-16T00:00:00+00:00",
        total_step_count=1,
    )


class TestConfinement:
    def test_store_root_under_dev_home(self, dev_home: str) -> None:
        root, err = ensure_workflow_store(dev_home)
        assert err is None
        assert str(root).startswith(dev_home)
        assert "workflow-store" in str(root)
        for sub in ("workflows", "executions", "timelines", "meta"):
            assert (root / sub).is_dir()

    def test_store_not_under_repo(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        assert validate_workflow_store_root(repo_root) == ERROR_HOME_REPO

    def test_store_not_under_production_home(self) -> None:
        prod = Path("/Users/huangruibang/.hermes")
        assert validate_workflow_store_root(prod) == ERROR_HOME_PRODUCTION

    def test_store_rejects_unset_home(self, monkeypatch) -> None:
        monkeypatch.delenv("HERMES_HOME", raising=False)
        root, err = ensure_workflow_store(None)
        assert err is not None
        assert root == Path() or not str(root)


class TestDefinitionRoundTrip:
    def test_definition_round_trips(self, dev_home: str) -> None:
        d = WorkflowDefinition(
            workflow_id=new_workflow_id("wf_"),
            schema_version=WORKFLOW_SCHEMA_VERSION,
            title="Demo",
            description="d",
            created_at="2026-06-16T00:00:00+00:00",
            updated_at="2026-06-16T00:00:00+00:00",
            created_by="dev-webui",
            phase="3A",
            mode="dev_workflow_mvp",
            steps=(_step(),),
            safety_boundary=WORKFLOW_SAFETY_BOUNDARY,
        )
        r = save_workflow_definition(d, hermes_home=dev_home)
        assert r.ok
        loaded = load_workflow_definition(d.workflow_id, hermes_home=dev_home)
        assert loaded is not None
        assert loaded.title == "Demo"
        assert len(loaded.steps) == 1
        assert loaded.steps[0].tool_id == "dev_environment_read"

    def test_missing_definition_returns_none(self, dev_home: str) -> None:
        assert load_workflow_definition("wf_" + "0" * 20, hermes_home=dev_home) is None


class TestExecutionRoundTrip:
    def test_execution_round_trips_with_timeline(self, dev_home: str) -> None:
        st = _execution(dev_home)
        r = save_workflow_execution(st, hermes_home=dev_home)
        assert r.ok
        ev = WorkflowTimelineEvent(
            event_id=new_workflow_id("wfa_"),
            event_type="workflow_step_started",
            created_at="2026-06-16T00:00:00+00:00",
            step_id=st.steps[0].step_id,
            step_type=STEP_READ_ONLY_TOOL,
            message="started",
        )
        ar = append_workflow_timeline_event(st.workflow_execution_id, ev, hermes_home=dev_home)
        assert ar.ok
        loaded = load_workflow_execution(st.workflow_execution_id, hermes_home=dev_home)
        assert loaded is not None
        assert len(loaded.timeline) == 1
        assert loaded.timeline[0].event_type == "workflow_step_started"

    def test_corrupt_document_skipped_safely(self, dev_home: str) -> None:
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        path = get_workflow_store_root(dev_home) / "executions" / f"{st.workflow_execution_id}.json"
        path.write_text("{ not valid json", encoding="utf-8")
        # Corrupt document returns None, never raises.
        assert load_workflow_execution(st.workflow_execution_id, hermes_home=dev_home) is None


class TestListingAndSafety:
    def test_list_executions(self, dev_home: str) -> None:
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        items = list_workflow_executions(limit=10, hermes_home=dev_home)
        assert any(i["workflowExecutionId"] == st.workflow_execution_id for i in items)

    def test_persisted_document_has_no_secrets(self, dev_home: str) -> None:
        st = _execution(dev_home)
        save_workflow_execution(st, hermes_home=dev_home)
        path = get_workflow_store_root(dev_home) / "executions" / f"{st.workflow_execution_id}.json"
        blob = path.read_text(encoding="utf-8")
        data = json.loads(blob)
        # No raw token / hash / secret / file content keys present.
        for forbidden in (
            "rawArguments", "rawArgs", "fullTokenHash", "tokenSecret",
            "plainToken", "apiKey", "fileContent", "absolutePath",
        ):
            assert forbidden not in json.dumps(data), forbidden
        assert "<function" not in blob
        assert "object at 0x" not in blob
