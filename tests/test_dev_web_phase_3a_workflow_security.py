"""Phase 3A — Workflow security boundary tests.

Verifies the workflow surface leaks no secrets / raw tokens / full hashes / raw
arguments / callable reprs / API keys / production paths; that every forbidden
step type is blocked at the API; that real provider is blocked; and that write /
rollback execution are never performed from the workflow.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig

API = "/api/dev/v1"

LEAK_TOKENS = [
    "rawArguments",
    "rawArgs",
    "fullTokenHash",
    "tokenSecret",
    "plainToken",
    "apiKey",
    "fileContent",
    "absolutePath",
    "/Users/huangruibang/.hermes",
]


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return TestClient(create_dev_web_api_app(DevWebApiConfig(hermes_home=home)))


def _assert_no_leak(blob: str, label: str) -> None:
    data = json.dumps(blob)
    for token in LEAK_TOKENS:
        assert token not in data, f"{label} leaked {token}"
    assert "<function" not in data
    assert "object at 0x" not in data
    assert "sk-" + "a" * 16 not in data


@pytest.mark.parametrize(
    "step_type",
    [
        "real_provider_roundtrip",
        "provider_write_execute",
        "sandbox_write_execute",
        "rollback_execute",
        "shell_command",
        "database_mutation",
        "external_http_request",
        "production_operation",
        "plugin_dynamic_load",
    ],
)
def test_forbidden_step_types_blocked_at_api(client: TestClient, step_type: str) -> None:
    r = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_plan_preview", "title": "t", "steps": [{"stepType": step_type}]})
    data = r.json()["data"]
    assert data["steps"] == []
    assert any(s["blockedReason"].startswith("blocked_workflow_") for s in data["blockedSteps"])


def test_plan_response_no_secret_carriers(client: TestClient) -> None:
    r = client.post(
        f"{API}/tools/dry-run",
        json={"mode": "workflow_plan_preview", "title": "t", "steps": [
            {"stepType": "manual_note", "note": "n", "apiKey": "k", "rawArguments": {"x": 1}},
        ]},
    )
    _assert_no_leak(r.text, "plan_preview")


def test_execute_response_no_secret_carriers(client: TestClient) -> None:
    plan = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_plan_preview", "title": "t", "steps": [{"stepType": "read_only_tool", "toolId": "dev_environment_read"}]}).json()["data"]
    wfx, step = plan["workflowExecutionId"], plan["steps"][0]["stepId"]
    pv = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": step}).json()["data"]
    ex = client.post(f"{API}/tools/execute", json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": step, "approvalToken": pv["approvalToken"]})
    _assert_no_leak(ex.text, "step_execute")


def test_write_execute_never_offered(client: TestClient) -> None:
    # A sandbox_write_preview step records a preview but the execute result
    # always reports writeExecuted=false.
    plan = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_plan_preview", "title": "t", "steps": [
        {"stepType": "sandbox_write_preview", "toolId": "dev_sandbox_file_write", "targetRelativePath": "notes/x.md", "content": "c"},
    ]}).json()["data"]
    wfx, step = plan["workflowExecutionId"], plan["steps"][0]["stepId"]
    pv = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": step}).json()["data"]
    ex = client.post(f"{API}/tools/execute", json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": step, "approvalToken": pv["approvalToken"]}).json()["data"]
    assert ex["result"]["workflowWriteExecuted"] is False
    assert ex["result"]["autoWriteBlocked"] is True


def test_rollback_execute_never_offered(client: TestClient) -> None:
    plan = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_plan_preview", "title": "t", "steps": [
        {"stepType": "rollback_reference"},
    ]}).json()["data"]
    wfx, step = plan["workflowExecutionId"], plan["steps"][0]["stepId"]
    pv = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": step}).json()["data"]
    ex = client.post(f"{API}/tools/execute", json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": step, "approvalToken": pv["approvalToken"]}).json()["data"]
    assert ex["result"]["workflowRollbackExecuted"] is False


def test_no_workflow_route_path_added() -> None:
    app = create_dev_web_api_app(DevWebApiConfig(hermes_home=None))
    prefix = DevWebApiConfig().api_prefix
    spec = app.openapi()
    for path in spec["paths"]:
        if path.startswith(prefix):
            assert "/workflows" not in path
            assert "/provider/" not in path
