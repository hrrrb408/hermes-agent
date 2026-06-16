"""Phase 3B — Real Provider API-security + Route-governance tests.

Verifies the end-to-end security boundary of the real-provider surface:
  - route governance UNCHANGED: OpenAPI 34 / runtime 34 / Tool GET 5 /
    Tool write HTTP route 0 / dry-run 1 / execution 1 (no new route added)
  - no API-key / Authorization / Bearer / raw token / full tokenHash / callable
    repr / production path crosses the real-provider surface (no-leak sweep)
  - the real-provider boundary is NOT reachable as a new route; it reuses the
    existing ``mode``-branched surface
  - no real network is exercised (mock-only)

Phase: 3B — Real Provider Read-only Controlled Integration
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_provider_openai_compatible import MockHttpClient
from hermes_cli.dev_web_provider_real_roundtrip import (
    build_real_request_from_message,
    run_real_provider_roundtrip_controlled,
)

API = "/api/dev/v1"

_PROVIDER_ENVS = (
    "HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED", "HERMES_PROVIDER_NAME",
    "HERMES_PROVIDER_BASE_URL", "HERMES_PROVIDER_MODEL",
)
_KEY_ENVS = (
    "HERMES_PROVIDER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY",
    "ZAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    for env in _PROVIDER_ENVS + _KEY_ENVS:
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
    @staticmethod
    def _paths(client) -> dict:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        return resp.json()["paths"]

    @staticmethod
    def _strip_prefix(path: str) -> str:
        # OpenAPI paths carry the /api/dev/v1 base; strip it for matching.
        prefix = "/api/dev/v1"
        return path[len(prefix):] if path.startswith(prefix) else path

    def test_openapi_path_count_is_34(self, client) -> None:
        paths = self._paths(client)
        assert len(paths) == 34

    def test_no_provider_route_added(self, client) -> None:
        paths = self._paths(client)
        # No dedicated provider-real route exists; the real round-trip reuses
        # the existing mode-branched /tools/execute + /tools/dry-run surface.
        for path in paths:
            assert "provider-real" not in path
            assert "provider/real" not in path

    def test_tool_get_routes_are_five(self, client) -> None:
        paths = self._paths(client)
        tool_get = [
            self._strip_prefix(p) for p, ops in paths.items()
            if self._strip_prefix(p).startswith("/tools") and "get" in ops
        ]
        assert len(tool_get) == 5  # policy, catalog, schemas, schemas/{name}, audit-events

    def test_tool_write_http_route_is_zero(self, client) -> None:
        paths = self._paths(client)
        # No POST/PATCH/PUT/DELETE on a tool WRITE route (write_file / patch /
        # dispatch / calls). dry-run + execute are the only tool POST routes.
        tool_post = sorted(
            self._strip_prefix(p) for p, ops in paths.items()
            if self._strip_prefix(p).startswith("/tools")
            and (set(ops) & {"post", "put", "patch", "delete"})
        )
        assert "/tools/dry-run" in tool_post
        assert "/tools/execute" in tool_post
        # Exactly one dry-run + one execution route.
        assert sum(1 for p in tool_post if p == "/tools/dry-run") == 1
        assert sum(1 for p in tool_post if p == "/tools/execute") == 1
        # No tool write / dispatch / calls route.
        for p in tool_post:
            assert "write" not in p
            assert "dispatch" not in p
            assert "calls" not in p


# ---------------------------------------------------------------------------
# 2. No-leak sweep across the real-provider surface
# ---------------------------------------------------------------------------


_LEAK_NEEDLES = (
    "sk-fake-placeholder", "Bearer ", "Authorization:", "accessToken",
    "refresh_token", "client_secret", "<function", "<bound method",
    "/Users/huangruibang/.hermes", "production state.db",
)


class TestNoLeakAcrossSurface:
    def _enabled_roundtrip(self, monkeypatch, tmp_path, *, body_overrides=None):
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        home = str(tmp_path / "dev-home")
        body = json.dumps({
            "choices": [{
                "message": {"role": "assistant", "content": "I will inspect route governance.",
                            "tool_calls": [{
                                "id": "c1", "type": "function",
                                "function": {"name": "route_governance_read", "arguments": "{}"},
                            }]},
                "finish_reason": "tool_calls",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }).encode()
        if body_overrides:
            body = body_overrides
        req = build_real_request_from_message("check route governance")
        resp = run_real_provider_roundtrip_controlled(
            req, http_client=MockHttpClient(response_body=body),
            hermes_home=home, production_gate_override=True,
        )
        return resp.to_safe_dict(), home

    def test_response_envelope_no_leak(self, monkeypatch, tmp_path) -> None:
        d, _ = self._enabled_roundtrip(monkeypatch, tmp_path)
        blob = json.dumps(d)
        for needle in _LEAK_NEEDLES:
            assert needle not in blob, f"leak: {needle}"

    def test_audit_file_no_leak(self, monkeypatch, tmp_path) -> None:
        _, home = self._enabled_roundtrip(monkeypatch, tmp_path)
        audit_path = f"{home}/gateway/dev/audit/provider-roundtrip-audit.jsonl"
        with open(audit_path, encoding="utf-8") as fh:
            blob = fh.read()
        for needle in _LEAK_NEEDLES:
            assert needle not in blob, f"audit leak: {needle}"

    def test_token_counts_present_not_redacted(self, monkeypatch, tmp_path) -> None:
        d, _ = self._enabled_roundtrip(monkeypatch, tmp_path)
        # Safe usage counts are surfaced (not redacted to [REDACTED]).
        assert d["usageSummary"]["totalTokens"] == 15
        assert d["usageSummary"]["promptTokens"] == 10


# ---------------------------------------------------------------------------
# 3. No real network in any test
# ---------------------------------------------------------------------------


class TestNoRealNetwork:
    def test_default_config_disabled(self) -> None:
        from hermes_cli.dev_web_provider_config import load_provider_real_config

        cfg = load_provider_real_config()
        assert cfg.provider_mode == "disabled"
        assert cfg.api_enabled is False

    def test_real_roundtrip_uses_only_injected_client(self, monkeypatch, tmp_path) -> None:
        # Even fully enabled, the round-trip only calls the injected MockHttpClient;
        # there is no default real-network path.
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        home = str(tmp_path / "dev-home")
        mock = MockHttpClient(response_body=b'{"choices":[{"message":{"content":"hi"},"finish_reason":"stop"}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}')
        resp = run_real_provider_roundtrip_controlled(
            build_real_request_from_message("hi"), http_client=mock,
            hermes_home=home, production_gate_override=True,
        )
        d = resp.to_safe_dict()
        assert d["status"] == "completed"
        assert d["externalNetworkCalled"] is True
        assert len(mock.calls) == 1  # exactly one injected-mock call, no real network
