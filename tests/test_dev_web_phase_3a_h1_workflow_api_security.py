"""Phase 3A-H1 — Workflow API security hardening (Lens 8 + 10).

Lens 8 (UI / cross-link boundary at the API): the four workflow modes are
served as branches on the EXISTING ``/tools/dry-run`` + ``/tools/execute``
routes (no new HTTP route), the full plan→preview→approve→execute lifecycle
works over HTTP, and every response leaks no secret carrier.

Lens 10 (Route governance): OpenAPI paths 34 / runtime routes 34 / Tool GET 5
/ Tool write HTTP route 0 / dry-run route 1 / execution route 1, with no
``/workflows`` or ``/provider/`` path added.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig

API = "/api/dev/v1"

LEAK_TOKENS = (
    "rawArguments",
    "rawArgs",
    "fullTokenHash",
    "tokenSecret",
    "plainToken",
    "apiKey",
    "fileContent",
    "absolutePath",
    "/Users/huangruibang/.hermes",
    "state.db",
    "<function",
    "object at 0x",
)

FORBIDDEN_STEP_TYPES = (
    "real_provider_roundtrip",
    "provider_write_execute",
    "sandbox_write_execute",
    "rollback_execute",
    "shell_command",
    "database_mutation",
    "database_query",
    "external_http_request",
    "production_operation",
    "plugin_dynamic_load",
    "file_delete",
    "background_agent",
    "scheduled_task",
)


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return TestClient(create_dev_web_api_app(DevWebApiConfig(hermes_home=home)))


def _assert_no_leak(text: str, label: str) -> None:
    blob = json.dumps(text)
    for token in LEAK_TOKENS:
        assert token not in blob, f"{label} leaked {token}"


def _plan(client: TestClient, steps: list[dict], title: str = "t") -> dict:
    r = client.post(
        f"{API}/tools/dry-run",
        json={"mode": "workflow_plan_preview", "title": title, "steps": steps},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


# ===========================================================================
# Lens 10 — Route governance (unchanged: no new route)
# ===========================================================================


class TestRouteGovernance:
    def test_route_counts_unchanged(self) -> None:
        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=None))
        prefix = DevWebApiConfig().api_prefix
        spec = app.openapi()
        openapi = [p for p in spec["paths"] if p.startswith(prefix)]
        runtime = [r.path for r in app.routes if getattr(r, "path", "").startswith(prefix)]
        tool_get = [
            p for p in openapi
            if p.startswith(prefix + "/tools") and "get" in spec["paths"][p]
        ]
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

    def test_no_workflow_or_provider_route_path(self) -> None:
        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=None))
        prefix = DevWebApiConfig().api_prefix
        spec = app.openapi()
        for path in spec["paths"]:
            if path.startswith(prefix):
                assert "/workflows" not in path
                assert "/provider/" not in path

    def test_malformed_workflow_mode_is_not_a_workflow_branch(self, client: TestClient) -> None:
        # An invented workflow mode must NOT be handled as a workflow branch
        # (it falls through to the dry-run default path, never materializing
        # an execution).
        r = client.post(
            f"{API}/tools/dry-run",
            json={"mode": "workflow_evil_mode", "title": "t", "steps": []},
        )
        data = r.json().get("data", {})
        assert data.get("mode") != "workflow_plan_preview"


# ===========================================================================
# Lens 8 — Workflow mode lifecycle over HTTP
# ===========================================================================


class TestWorkflowModesOverHttp:
    def test_plan_preview_materializes_execution(self, client: TestClient) -> None:
        data = _plan(client, [{"stepType": "read_only_tool", "toolId": "dev_environment_read"}])
        assert data["mode"] == "workflow_plan_preview"
        assert data["workflowExecutionId"]
        assert data["executionStatus"] == "running"
        assert len(data["steps"]) == 1

    def test_state_read_single_and_list(self, client: TestClient) -> None:
        data = _plan(client, [{"stepType": "manual_note", "note": "n"}])
        wfx = data["workflowExecutionId"]
        single = client.post(
            f"{API}/tools/dry-run",
            json={"mode": "workflow_state_read", "workflowExecutionId": wfx},
        )
        assert single.status_code == 200
        assert single.json()["data"]["workflowExecutionId"] == wfx
        listing = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_state_read"})
        assert listing.status_code == 200
        assert listing.json()["data"]["count"] >= 1

    def test_step_preview_issues_approval_token(self, client: TestClient) -> None:
        data = _plan(client, [{"stepType": "read_only_tool", "toolId": "dev_environment_read"}])
        wfx, step = data["workflowExecutionId"], data["steps"][0]["stepId"]
        r = client.post(
            f"{API}/tools/dry-run",
            json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": step},
        )
        assert r.status_code == 200
        pd = r.json()["data"]
        assert pd["approvalToken"]
        assert pd["approvalId"]
        assert pd["approvalId"].startswith("cft_")

    def test_execute_without_approval_blocked(self, client: TestClient) -> None:
        data = _plan(client, [{"stepType": "read_only_tool", "toolId": "dev_environment_read"}])
        wfx, step = data["workflowExecutionId"], data["steps"][0]["stepId"]
        r = client.post(
            f"{API}/tools/execute",
            json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": step},
        )
        assert r.status_code == 400
        assert "approval" in r.json()["error"]["message"]

    def test_full_lifecycle_with_replay_blocked(self, client: TestClient) -> None:
        data = _plan(
            client,
            [
                {"stepType": "read_only_tool", "toolId": "dev_environment_read"},
                {"stepType": "manual_note", "note": "n"},
            ],
        )
        wfx = data["workflowExecutionId"]
        s0 = data["steps"][0]["stepId"]
        pv0 = client.post(
            f"{API}/tools/dry-run",
            json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": s0},
        ).json()["data"]
        ex0 = client.post(
            f"{API}/tools/execute",
            json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": s0, "approvalToken": pv0["approvalToken"]},
        )
        assert ex0.status_code == 200
        assert ex0.json()["data"]["result"]["type"] == "dev_environment_read"
        # Replay (single-use) is rejected.
        replay = client.post(
            f"{API}/tools/execute",
            json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": s0, "approvalToken": pv0["approvalToken"]},
        )
        assert replay.status_code == 400
        # Step 1 → execution completes.
        s1 = data["steps"][1]["stepId"]
        pv1 = client.post(
            f"{API}/tools/dry-run",
            json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": s1},
        ).json()["data"]
        ex1 = client.post(
            f"{API}/tools/execute",
            json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": s1, "approvalToken": pv1["approvalToken"]},
        )
        assert ex1.status_code == 200
        assert ex1.json()["data"]["executionStatus"] == "completed"

    def test_token_bound_to_step_at_http_layer(self, client: TestClient) -> None:
        data = _plan(
            client,
            [
                {"stepType": "read_only_tool", "toolId": "dev_environment_read"},
                {"stepType": "manual_note", "note": "n"},
            ],
        )
        wfx = data["workflowExecutionId"]
        s0, s1 = data["steps"][0]["stepId"], data["steps"][1]["stepId"]
        pv0 = client.post(
            f"{API}/tools/dry-run",
            json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": s0},
        ).json()["data"]
        # Use s0's token against s1 → must be rejected.
        r = client.post(
            f"{API}/tools/execute",
            json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": s1, "approvalToken": pv0["approvalToken"]},
        )
        assert r.status_code == 400


class TestWriteRollbackNeverExecutedAtApi:
    def test_write_execute_never_offered(self, client: TestClient) -> None:
        data = _plan(
            client,
            [{"stepType": "sandbox_write_preview", "toolId": "dev_sandbox_file_write", "targetRelativePath": "notes/x.md", "content": "c"}],
        )
        wfx, step = data["workflowExecutionId"], data["steps"][0]["stepId"]
        pv = client.post(
            f"{API}/tools/dry-run",
            json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": step},
        ).json()["data"]
        ex = client.post(
            f"{API}/tools/execute",
            json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": step, "approvalToken": pv["approvalToken"]},
        ).json()["data"]
        assert ex["result"]["workflowWriteExecuted"] is False
        assert ex["result"]["autoWriteBlocked"] is True

    def test_rollback_execute_never_offered(self, client: TestClient) -> None:
        data = _plan(client, [{"stepType": "rollback_reference"}])
        wfx, step = data["workflowExecutionId"], data["steps"][0]["stepId"]
        pv = client.post(
            f"{API}/tools/dry-run",
            json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": step},
        ).json()["data"]
        ex = client.post(
            f"{API}/tools/execute",
            json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": step, "approvalToken": pv["approvalToken"]},
        ).json()["data"]
        assert ex["result"]["workflowRollbackExecuted"] is False

    def test_fake_provider_offline_at_api(self, client: TestClient) -> None:
        data = _plan(
            client,
            [{"stepType": "fake_provider_roundtrip", "providerMode": "fake", "message": "hi", "allowedToolIds": ["tool_policy_read"]}],
        )
        wfx, step = data["workflowExecutionId"], data["steps"][0]["stepId"]
        pv = client.post(
            f"{API}/tools/dry-run",
            json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": step},
        ).json()["data"]
        ex = client.post(
            f"{API}/tools/execute",
            json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": step, "approvalToken": pv["approvalToken"]},
        ).json()["data"]
        assert ex["result"]["externalNetworkCalled"] is False


# ===========================================================================
# Forbidden capability blocking + no-leak at the API
# ===========================================================================


class TestForbiddenBlockingAtApi:
    @pytest.mark.parametrize("step_type", FORBIDDEN_STEP_TYPES)
    def test_forbidden_step_type_blocked(self, client: TestClient, step_type: str) -> None:
        data = _plan(client, [{"stepType": step_type}])
        assert data["steps"] == []
        assert any(
            s["blockedReason"].startswith("blocked_workflow_") for s in data["blockedSteps"]
        ), step_type

    def test_plan_response_no_secret_carrier(self, client: TestClient) -> None:
        r = client.post(
            f"{API}/tools/dry-run",
            json={
                "mode": "workflow_plan_preview", "title": "t",
                "steps": [{"stepType": "manual_note", "note": "n", "apiKey": "k", "rawArguments": {"x": 1}, "fullTokenHash": "h"}],
            },
        )
        _assert_no_leak(r.text, "plan_preview")

    def test_execute_response_no_secret_carrier(self, client: TestClient) -> None:
        data = _plan(client, [{"stepType": "read_only_tool", "toolId": "dev_environment_read"}])
        wfx, step = data["workflowExecutionId"], data["steps"][0]["stepId"]
        pv = client.post(
            f"{API}/tools/dry-run",
            json={"mode": "workflow_step_preview", "workflowExecutionId": wfx, "stepId": step},
        ).json()["data"]
        ex = client.post(
            f"{API}/tools/execute",
            json={"mode": "workflow_step_execute", "workflowExecutionId": wfx, "stepId": step, "approvalToken": pv["approvalToken"]},
        )
        _assert_no_leak(ex.text, "step_execute")

    def test_unsafe_path_blocked_at_api(self, client: TestClient) -> None:
        data = _plan(
            client,
            [{"stepType": "sandbox_write_preview", "toolId": "dev_sandbox_file_write", "targetRelativePath": "/etc/passwd", "content": "c"}],
        )
        assert data["steps"] == []
        assert any("blocked_workflow_" in (s.get("blockedReason") or "") for s in data["blockedSteps"])
        _assert_no_leak(json.dumps(data), "unsafe_path_plan")

    def test_state_read_no_secret_carrier(self, client: TestClient) -> None:
        _plan(client, [{"stepType": "manual_note", "note": "n"}])
        r = client.post(f"{API}/tools/dry-run", json={"mode": "workflow_state_read"})
        _assert_no_leak(r.text, "state_read")
