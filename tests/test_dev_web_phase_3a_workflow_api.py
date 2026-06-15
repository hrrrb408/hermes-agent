"""Phase 3A — Workflow API integration tests.

Verifies the four workflow modes are served as branches on the existing
/tools/dry-run and /tools/execute routes (NO new route), the response shape is
correct, the full plan→preview→approve→execute lifecycle works over HTTP, and
route governance is unchanged (OpenAPI 34 / runtime 34 / Tool GET 5 / write 0 /
dry-run 1 / execution 1).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig

API = "/api/dev/v1"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    config = DevWebApiConfig(hermes_home=home)
    return TestClient(create_dev_web_api_app(config))


def _plan(client: TestClient, steps: list) -> dict:
    r = client.post(
        f"{API}/tools/dry-run",
        json={"mode": "workflow_plan_preview", "title": "t", "steps": steps},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


class TestWorkflowModes:
    def test_plan_preview_creates_execution(self, client: TestClient) -> None:
        data = _plan(client, [{"stepType": "read_only_tool", "toolId": "dev_environment_read"}])
        assert data["mode"] == "workflow_plan_preview"
        assert data["workflowExecutionId"]
        assert len(data["steps"]) == 1
        assert data["executionStatus"] == "running"

    def test_state_read_returns_execution(self, client: TestClient) -> None:
        data = _plan(client, [{"stepType": "manual_note", "note": "n"}])
        wfx = data["workflowExecutionId"]
        r = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_state_read", "workflowExecutionId": wfx})
        assert r.status_code == 200
        assert r.json()["data"]["workflowExecutionId"] == wfx

    def test_state_read_lists_executions(self, client: TestClient) -> None:
        _plan(client, [{"stepType": "manual_note", "note": "n"}])
        r = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_state_read"})
        assert r.status_code == 200
        assert r.json()["data"]["count"] >= 1

    def test_step_preview_issues_approval_token(self, client: TestClient) -> None:
        data = _plan(client, [{"stepType": "read_only_tool", "toolId": "dev_environment_read"}])
        wfx, step = data["workflowExecutionId"], data["steps"][0]["stepId"]
        r = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": step})
        assert r.status_code == 200
        pd = r.json()["data"]
        assert pd["approvalToken"]
        assert pd["approvalId"]

    def test_execute_without_approval_blocked(self, client: TestClient) -> None:
        data = _plan(client, [{"stepType": "read_only_tool", "toolId": "dev_environment_read"}])
        wfx, step = data["workflowExecutionId"], data["steps"][0]["stepId"]
        r = client.post(f"{API}/tools/execute", json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": step})
        assert r.status_code == 400
        assert "approval" in r.json()["error"]["message"]

    def test_full_lifecycle_over_http(self, client: TestClient) -> None:
        data = _plan(client, [
            {"stepType": "read_only_tool", "toolId": "dev_environment_read"},
            {"stepType": "manual_note", "note": "n"},
        ])
        wfx = data["workflowExecutionId"]
        # Step 0
        s0 = data["steps"][0]["stepId"]
        pv0 = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": s0}).json()["data"]
        ex0 = client.post(f"{API}/tools/execute", json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": s0, "approvalToken": pv0["approvalToken"]})
        assert ex0.status_code == 200
        assert ex0.json()["data"]["result"]["type"] == "dev_environment_read"
        # Replay blocked
        replay = client.post(f"{API}/tools/execute", json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": s0, "approvalToken": pv0["approvalToken"]})
        assert replay.status_code == 400
        # Step 1
        s1 = data["steps"][1]["stepId"]
        pv1 = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": s1}).json()["data"]
        ex1 = client.post(f"{API}/tools/execute", json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": s1, "approvalToken": pv1["approvalToken"]})
        assert ex1.status_code == 200
        assert ex1.json()["data"]["executionStatus"] == "completed"


class TestRouteGovernance:
    def test_no_new_route_added(self) -> None:
        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=None))
        prefix = DevWebApiConfig().api_prefix
        spec = app.openapi()
        openapi = [p for p in spec["paths"] if p.startswith(prefix)]
        runtime = [r.path for r in app.routes if getattr(r, "path", "").startswith(prefix)]
        tool_get = [p for p in openapi if p.startswith(prefix + "/tools") and "get" in spec["paths"][p]]
        write_methods = {"post", "put", "patch", "delete"}
        tool_write = [
            p for p in openapi
            if p.startswith(prefix + "/tools")
            and (write_methods & set(spec["paths"][p].keys()))
            and p not in {prefix + "/tools/dry-run", prefix + "/tools/execute"}
        ]
        assert len(openapi) == 34
        assert len(runtime) == 34
        assert len(tool_get) == 5
        assert len(tool_write) == 0
        assert prefix + "/tools/dry-run" in openapi
        assert prefix + "/tools/execute" in openapi
        # No workflow-specific route was added.
        assert all("/workflows" not in p for p in openapi)
