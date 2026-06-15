"""Phase 2E — Frontend contract tests for the unified developer console.

These tests pin the read-only backend response contract that the new Dev Console
Overview / Safety / Diagnostics sections consume, so a backend change that breaks
the frontend (or drifts the route-governance baseline) is caught at the Python
level. Phase 2E is frontend-only polish — these tests assert that NO new HTTP
route, tool-write route, or provider route was introduced and that the Overview
data sources remain leak-free.

Covered:
  - GET /tools/policy (Overview live source) shape + safety invariants + no leak
  - GET /tools/audit-events (Overview audit-store source) no leak
  - Route governance unchanged: OpenAPI 34, runtime 34, tool GET 5,
    tool write HTTP route 0, tool dry-run route 1, tool execution route 1
  - No dedicated tool-write HTTP route and no provider HTTP route were added

Phase: 2E — Frontend UX Polish (Unified Developer Console)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig

API = "/api/dev/v1"

# Patterns that must NEVER appear in any dev-console-facing payload.
LEAK_PATTERNS = (
    "sk-",
    "Bearer ",
    "<function",
    "object at 0x",
    "/Users/huangruibang/.hermes",
    "rawArguments",
    "fullTokenHash",
    "plainToken",
    "tokenSecret",
)


@pytest.fixture
def client(tmp_path: Path):
    home = tmp_path / "hermes-home-dev"
    home.mkdir(parents=True)
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    app = create_dev_web_api_app(DevWebApiConfig(hermes_home=home))
    return TestClient(app)


def _api_paths(spec) -> list[str]:
    return [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]


class TestOverviewPolicySource:
    """GET /tools/policy — the Overview dashboard's live policy source."""

    def test_policy_responds_with_expected_shape(self, client):
        resp = client.get(f"{API}/tools/policy")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data["inventoryCount"], int)
        # Safety invariants the frontend relies on.
        assert data["safety"]["readOnly"] is True
        assert data["safety"]["writeEnabled"] is False
        assert data["execution"]["enabled"] is False
        assert data["execution"]["providerSchemaSent"] is False

    def test_policy_payload_is_leak_free(self, client):
        body = client.get(f"{API}/tools/policy").text
        for pattern in LEAK_PATTERNS:
            assert pattern not in body, f"policy body must not contain {pattern}"


class TestOverviewAuditSource:
    """GET /tools/audit-events — the Overview audit-store health source."""

    def test_audit_events_responds(self, client):
        resp = client.get(f"{API}/tools/audit-events", params={"auditKind": "post_execution"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data

    def test_audit_payload_is_leak_free(self, client):
        body = client.get(
            f"{API}/tools/audit-events", params={"auditKind": "post_execution"}
        ).text
        for pattern in LEAK_PATTERNS:
            assert pattern not in body, f"audit body must not contain {pattern}"


class TestRouteGovernanceUnchanged:
    """Phase 2E must not drift the route-governance baseline (34/34/5/0/1/1)."""

    def test_openapi_paths_still_34(self, client):
        spec = client.get("/openapi.json").json()
        assert len(_api_paths(spec)) == 34

    def test_tool_get_routes_still_5(self, client):
        spec = client.get("/openapi.json").json()
        tool_paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/tools")]
        get_routes = [p for p in tool_paths if "get" in spec["paths"][p]]
        assert len(get_routes) == 5

    def test_no_dedicated_tool_write_http_route(self, client):
        spec = client.get("/openapi.json").json()
        tool_paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/tools")]
        # Mutating routes under /tools excluding dry-run + execute (which are
        # the controlled-execution gate, not write routes).
        mutating = [
            p
            for p in tool_paths
            if set(spec["paths"][p].keys()) & {"post", "put", "patch", "delete"}
        ]
        mutating = [p for p in mutating if p not in {f"{API}/tools/dry-run", f"{API}/tools/execute"}]
        assert mutating == [], f"unexpected tool write HTTP routes: {mutating}"

    def test_dry_run_and_execute_routes_present(self, client):
        spec = client.get("/openapi.json").json()
        assert f"{API}/tools/dry-run" in spec["paths"]
        assert f"{API}/tools/execute" in spec["paths"]

    def test_no_provider_http_route(self, client):
        spec = client.get("/openapi.json").json()
        provider_routes = [p for p in spec["paths"] if "/provider" in p]
        assert provider_routes == [], (
            f"Phase 2E must not add a provider HTTP route: {provider_routes}"
        )
