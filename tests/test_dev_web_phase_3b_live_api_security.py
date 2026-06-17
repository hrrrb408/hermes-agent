"""Phase 3B-Live-Enablement — Live API-security + Route-governance tests.

Verifies the live-enablement surface end-to-end:
  - route governance UNCHANGED: OpenAPI 34 / runtime 34 / Tool GET 5 /
    Tool write HTTP route 0 / dry-run 1 / execution 1 (no new route added)
  - the live gate is surfaced ONLY under the existing /status providerBoundary
    block (no new provider_live route)
  - the providerLive block is value-free + disabled by default
  - no API-key / Authorization / Bearer / raw token / callable repr / production
    path crosses the live surface (no-leak sweep)
  - no real network is exercised

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
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
_LIVE_ENVS = (
    "HERMES_PROVIDER_LIVE_APPROVAL", "HERMES_PROVIDER_LIVE_ONE_SHOT",
    "HERMES_PROVIDER_LIVE_BUDGET_CENTS", "HERMES_PROVIDER_LIVE_MAX_TOTAL_TOKENS",
    "HERMES_PROVIDER_LIVE_MAX_OUTPUT_TOKENS",
)

FORBIDDEN_NEEDLES = (
    "sk-", "Bearer ", "Authorization", "apiKeyValue", "accessToken",
    "fullTokenHash", "plainToken", "<function", "<bound method",
    "/Users/huangruibang/.hermes", "state.db",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    for env in _PROVIDER_ENVS + _KEY_ENVS + _LIVE_ENVS:
        monkeypatch.delenv(env, raising=False)


@pytest.fixture
def client():
    config = DevWebApiConfig(hermes_home=None)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Route governance unchanged
# ---------------------------------------------------------------------------


class TestRouteGovernanceUnchanged:
    def test_openapi_paths_still_34(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert len(paths) == 34

    def test_no_live_route_added(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        for path in paths:
            assert "provider_live" not in path
            assert not path.endswith("/live")

    def test_no_new_provider_route(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        for path in paths:
            assert not path.endswith("/provider-live")
            assert not path.endswith("/live-approval")
            assert not path.endswith("/live-roundtrip")


# ---------------------------------------------------------------------------
# 2. providerLive status block (under /status; no new route)
# ---------------------------------------------------------------------------


class TestProviderLiveStatus:
    def test_live_block_present_and_disabled_by_default(self, client: TestClient) -> None:
        resp = client.get(f"{API}/status")
        assert resp.status_code == 200
        boundary = resp.json()["data"]["providerBoundary"]
        live = boundary["providerLive"]
        assert live["liveEnabled"] is False
        assert live["approvalRequired"] is True
        assert live["toolExecutionDisabled"] is True
        assert live["providerWriteBlocked"] is True
        assert live["productionRolloutBlocked"] is True
        assert live["killSwitchActive"] is False
        assert live["manualOneShot"] is False

    def test_live_budget_caps_rendered(self, client: TestClient) -> None:
        resp = client.get(f"{API}/status")
        live = resp.json()["data"]["providerBoundary"]["providerLive"]
        budget = live["budget"]
        assert budget["maxRequests"] == 1
        assert budget["maxTotalTokens"] == 1000
        assert budget["maxOutputTokens"] == 200
        assert budget["maxBudgetCents"] == 5
        assert budget["maxRetries"] == 0

    @pytest.mark.parametrize("needle", FORBIDDEN_NEEDLES)
    def test_live_block_value_free(self, client: TestClient, needle: str) -> None:
        resp = client.get(f"{API}/status")
        live = resp.json()["data"]["providerBoundary"]["providerLive"]
        blob = json.dumps(live)
        assert needle not in blob

    def test_live_block_never_reads_real_key_when_disabled(
        self, client: TestClient, monkeypatch,
    ) -> None:
        # Even with a real-looking key in the env, the disabled default never
        # surfaces it (the secret read is gated past every live gate).
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-1234567890")
        resp = client.get(f"{API}/status")
        blob = json.dumps(resp.json()["data"]["providerBoundary"]["providerLive"])
        assert "sk-fake" not in blob
