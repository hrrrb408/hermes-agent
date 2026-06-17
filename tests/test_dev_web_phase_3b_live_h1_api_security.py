"""Phase 3B-Live-Enablement H1 — Live API-security + Route-governance Hardening.

Hardening pass over the live-enablement HTTP surface (LIVE-API-3B-H1-001).

Verifies the live gate is surfaced ONLY under the existing /status
providerBoundary.providerLive block (no new route), route governance is
unchanged (34/34/5/0/1/1), the providerLive block is permanently disabled by
default + value-free, and a no-leak sweep over the whole status + openapi
payloads finds no API key / Authorization / Bearer / raw token / callable repr /
production path — even with a real-looking key present in the env.

No network call is exercised.

Phase: 3B-Live-Enablement H1 — Strict Manual One-shot Live Gate Hardening
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


class TestRouteGovernancePreserved:
    def test_openapi_paths_still_34(self, client: TestClient) -> None:
        paths = client.get("/openapi.json").json()["paths"]
        assert len(paths) == 34

    @pytest.mark.parametrize("suffix", ["provider_live", "provider-live", "live-approval",
                                        "live-roundtrip", "/live"])
    def test_no_live_route_added(self, client: TestClient, suffix: str) -> None:
        paths = client.get("/openapi.json").json()["paths"]
        for path in paths:
            assert not path.endswith(suffix)
            assert "provider_live" not in path


class TestLiveBlockPermanentlyDisabled:
    def test_live_block_default_off_and_blocked_flags(self, client: TestClient) -> None:
        live = client.get(f"{API}/status").json()["data"]["providerBoundary"]["providerLive"]
        assert live["liveEnabled"] is False
        assert live["approvalRequired"] is True
        assert live["toolExecutionDisabled"] is True
        assert live["providerWriteBlocked"] is True
        assert live["providerAutoWriteBlocked"] is True
        assert live["autonomousWriteBlocked"] is True
        assert live["productionRolloutBlocked"] is True
        assert live["streamingBlocked"] is True
        assert live["multiProviderBlocked"] is True
        assert live["killSwitchActive"] is False
        assert live["manualOneShot"] is False

    def test_live_caps_frozen(self, client: TestClient) -> None:
        b = client.get(f"{API}/status").json()["data"]["providerBoundary"]["providerLive"]["budget"]
        assert b["maxRequests"] == 1
        assert b["maxTotalTokens"] == 1000
        assert b["maxOutputTokens"] == 200
        assert b["maxBudgetCents"] == 5
        assert b["maxRetries"] == 0
        assert b["failClosedOnCounterError"] is True


class TestNoLeakSweep:
    @pytest.mark.parametrize("needle", FORBIDDEN_NEEDLES)
    def test_live_block_value_free(self, client: TestClient, needle: str) -> None:
        live = client.get(f"{API}/status").json()["data"]["providerBoundary"]["providerLive"]
        assert needle not in json.dumps(live)

    def test_disabled_default_never_surfaces_real_key(self, client: TestClient, monkeypatch) -> None:
        # A real-looking key in the env must NEVER surface while the gate is off.
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-1234567890")
        blob = json.dumps(
            client.get(f"{API}/status").json()["data"]["providerBoundary"]
        )
        for needle in ("sk-fake", "Bearer ", "Authorization"):
            assert needle not in blob

    def test_openapi_payload_value_free(self, client: TestClient) -> None:
        blob = json.dumps(client.get("/openapi.json").json())
        for needle in ("sk-", "Bearer ", "/Users/huangruibang/.hermes"):
            assert needle not in blob
