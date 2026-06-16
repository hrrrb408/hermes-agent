"""Phase 3B-H1 — Provider API Security + Route Governance HARDENING (Lens 10).

Deterministic, adversarial verification at the FastAPI surface:

  - route governance is UNCHANGED: OpenAPI 34 / runtime 34 / Tool GET 5 /
    Tool write HTTP route 0 / dry-run 1 / execution 1
  - NO provider-real / provider/real route path exists
  - a provider_roundtrip branch over the EXISTING execute route never leaks an
    API key / Authorization / Bearer / raw token / full tokenHash / callable repr /
    production path
  - the /status providerBoundary block is value-free (no key value)
  - no real network is exercised (mock-only; the round-trip is blocked here)

Phase: 3B-H1 — Provider Boundary Hardening
Hardening ID: HARDENING-3B-H1-001
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig

API = "/api/dev/v1"

_PROVIDER_ENVS = (
    "HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED", "HERMES_PROVIDER_NAME",
    "HERMES_PROVIDER_BASE_URL", "HERMES_PROVIDER_MODEL",
)
_KEY_ENVS = (
    "HERMES_PROVIDER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY",
    "ZAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY",
)

_LEAK_NEEDLES = (
    "sk-fake-placeholder", "sk-realkey", "Bearer ", "Authorization:",
    "accessToken", "refresh_token", "client_secret", "<function",
    "<bound method", "/Users/huangruibang/.hermes", "production state.db",
    "rawPrompt", "rawResponse", "rawArguments", "fullTokenHash", "plainToken",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    for env in _PROVIDER_ENVS + _KEY_ENVS:
        monkeypatch.delenv(env, raising=False)


@pytest.fixture
def client() -> TestClient:
    config = DevWebApiConfig(hermes_home=None)
    return TestClient(create_dev_web_api_app(config))


# ===========================================================================
# Lens 10 — route governance (unchanged, no provider route)
# ===========================================================================


class TestRouteGovernanceUnchanged:
    def _paths(self, client: TestClient) -> dict:
        spec = client.app.openapi()
        return spec["paths"]

    def test_openapi_path_count_is_34(self, client: TestClient) -> None:
        assert len(self._paths(client)) == 34

    def test_runtime_route_count_is_34(self, client: TestClient) -> None:
        prefix = DevWebApiConfig().api_prefix
        runtime = [r for r in client.app.routes if getattr(r, "path", "").startswith(prefix)]
        assert len(runtime) == 34

    def test_tool_get_routes_are_five(self, client: TestClient) -> None:
        prefix = DevWebApiConfig().api_prefix
        spec = client.app.openapi()
        tool_get = [
            p for p in spec["paths"]
            if p.startswith(prefix + "/tools") and "get" in spec["paths"][p]
        ]
        assert len(tool_get) == 5

    def test_tool_write_http_route_is_zero(self, client: TestClient) -> None:
        prefix = DevWebApiConfig().api_prefix
        spec = client.app.openapi()
        write_methods = {"post", "put", "patch", "delete"}
        tool_write = [
            p for p in spec["paths"]
            if p.startswith(prefix + "/tools")
            and (write_methods & set(spec["paths"][p].keys()))
            and p not in {prefix + "/tools/dry-run", prefix + "/tools/execute"}
        ]
        assert len(tool_write) == 0

    def test_dry_run_and_execute_are_the_only_tool_post_routes(self, client: TestClient) -> None:
        prefix = DevWebApiConfig().api_prefix
        spec = client.app.openapi()
        tool_post = sorted(
            p for p in spec["paths"]
            if p.startswith(prefix + "/tools")
            and (set(spec["paths"][p].keys()) & {"post", "put", "patch", "delete"})
        )
        assert tool_post == sorted([prefix + "/tools/dry-run", prefix + "/tools/execute"])

    def test_no_provider_real_route_path(self, client: TestClient) -> None:
        spec = client.app.openapi()
        for path in spec["paths"]:
            assert "provider-real" not in path
            assert "provider/real" not in path


# ===========================================================================
# Lens 10 — provider_roundtrip branch (blocked real) leaks nothing
# ===========================================================================


class TestProviderRoundtripNoLeak:
    def _execute(self, client: TestClient, provider_mode: str) -> dict:
        resp = client.post(
            f"{API}/tools/execute",
            json={
                "mode": "provider_roundtrip",
                "providerMode": provider_mode,
                "message": "check route governance",
                "allowedToolIds": ["route_governance_read"],
            },
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    def test_real_provider_roundtrip_blocked_no_network(self, client: TestClient) -> None:
        data = self._execute(client, "real")["data"]
        assert data["status"] == "blocked"
        assert data["externalNetworkCalled"] is False
        blob = json.dumps(data)
        for needle in _LEAK_NEEDLES:
            assert needle not in blob

    def test_disabled_provider_roundtrip_no_leak(self, client: TestClient) -> None:
        data = self._execute(client, "disabled")["data"]
        blob = json.dumps(data)
        for needle in _LEAK_NEEDLES:
            assert needle not in blob

    def test_unknown_provider_mode_handled_safely(self, client: TestClient) -> None:
        # An invented providerMode is rejected at the schema layer (400), never
        # materializing a real round-trip or a network call.
        resp = client.post(
            f"{API}/tools/execute",
            json={
                "mode": "provider_roundtrip", "providerMode": "live-hacker-mode",
                "message": "x", "allowedToolIds": ["route_governance_read"],
            },
        )
        assert resp.status_code == 400
        blob = json.dumps(resp.json())
        for needle in _LEAK_NEEDLES:
            assert needle not in blob


# ===========================================================================
# Lens 10 — /status providerBoundary block is value-free
# ===========================================================================


class TestStatusBoundaryValueFree:
    def test_status_boundary_has_no_secret(self, client: TestClient) -> None:
        resp = client.get(f"{API}/status")
        assert resp.status_code == 200
        boundary = resp.json()["data"]["providerBoundary"]
        blob = json.dumps(boundary)
        for needle in ("sk-", "Bearer ", "Authorization", "apiKeyValue", "accessToken"):
            assert needle not in blob
        # Permanently-blocked flags are surfaced.
        assert boundary["providerWriteBlocked"] is True
        assert boundary["providerAutoWriteBlocked"] is True
        assert boundary["autonomousWriteBlocked"] is True
        assert boundary["productionRolloutBlocked"] is True

    def test_status_boundary_key_marker_only(self, client: TestClient) -> None:
        resp = client.get(f"{API}/status")
        boundary = resp.json()["data"]["providerBoundary"]
        assert boundary["apiKeySource"] == "env"
        assert boundary["apiKeySourceDetail"] in ("env_present", "env_missing")
        assert boundary["redactionApplied"] is True
        assert boundary["apiEnabled"] is False
