"""Phase 2B — Provider security-boundary tests.

Comprehensive boundary assertions for the Provider Schema / API integration:
no API key leak, external network never called in fake mode, real mode
blocked unless fully enabled, write tools never reachable, raw token /
tokenHash / raw arguments / secrets / callable repr never exposed, and route
governance unchanged (Tool write = 0).

Phase: 2B — Provider Schema / API Controlled Integration
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_provider_roundtrip import run_provider_tool_roundtrip


@pytest.fixture
def provider_home(tmp_path):
    home = tmp_path / "hermes-home-dev"
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    (home / "gateway" / "dev" / "tokens").mkdir(parents=True, exist_ok=True)
    return str(home)


@pytest.fixture(autouse=True)
def _enable_gates(monkeypatch):
    monkeypatch.setenv("HERMES_TOOL_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("HERMES_AGENT_TOOLS_ENABLED", "true")
    monkeypatch.setenv("HERMES_TOOL_HANDLER_CALL_ENABLED", "true")
    import hermes_cli.dev_web_read_only_tool_handlers as handlers

    monkeypatch.setattr(handlers, "_probe_system_state", lambda: {
        "productionGatewayPidObserved": 1962, "productionGatewayProcessCount": 1,
        "productionGatewayCommandSummary": "x", "port5180": "free", "port5181": "free",
    })


def _roundtrip_repr(home: str, message="check route governance", tool="route_governance_read") -> str:
    result = run_provider_tool_roundtrip(
        message, "fake",
        selected_tool_ids=frozenset({tool}),
        hermes_home=home,
    )
    return repr(result.to_safe_dict())


class TestNoSecretLeak:
    def test_no_api_key_in_result(self, provider_home) -> None:
        blob = _roundtrip_repr(provider_home)
        for needle in ("apiKey", "api_key", "Bearer ", "sk-", "BEGIN PRIVATE KEY"):
            assert needle not in blob

    def test_no_callable_repr_in_result(self, provider_home) -> None:
        blob = _roundtrip_repr(provider_home)
        assert "<function" not in blob
        assert "<bound method" not in blob

    def test_no_raw_arguments_exposed_beyond_allowlist(self, provider_home) -> None:
        # Tool results carry the structured handler output, never raw provider
        # request arguments with secrets.
        result = run_provider_tool_roundtrip(
            "read tool policy arg=sk-abcdefghijklmnopqrstuvwxyz", "fake",
            selected_tool_ids=frozenset({"tool_policy_read"}),
            hermes_home=provider_home,
        )
        blob = repr(result.to_safe_dict())
        assert "sk-abcdefghijklmnopqrstuvwxyz" not in blob


class TestFakeModeNetworkBoundary:
    def test_external_network_never_called_in_fake(self, provider_home) -> None:
        for msg in ("read tool policy", "check route governance", "read audit events"):
            result = run_provider_tool_roundtrip(
                msg, "fake", hermes_home=provider_home,
            )
            assert result.external_network_called is False
            assert result.provider_api_called is True

    def test_tool_write_remains_disabled(self, provider_home) -> None:
        result = run_provider_tool_roundtrip(
            "write a file please", "fake", hermes_home=provider_home,
        )
        # No write tool is in the allowlist → no tool call executes write_file.
        for tr in result.tool_results:
            assert tr["toolId"] != "write_file"


class TestRealModeComprehensivelyBlocked:
    @pytest.mark.parametrize(
        "env_setup",
        [
            {},  # nothing set
            {"HERMES_PROVIDER_API_ENABLED": "1"},  # mode not set
            {"HERMES_PROVIDER_API_ENABLED": "1", "HERMES_PROVIDER_MODE": "real"},  # no key
        ],
    )
    def test_real_blocked_under_partial_enablement(self, provider_home, monkeypatch, env_setup) -> None:
        for k, v in env_setup.items():
            monkeypatch.setenv(k, v)
        monkeypatch.setenv("HERMES_HOME", provider_home)
        result = run_provider_tool_roundtrip("x", "real", hermes_home=provider_home)
        assert result.status == "blocked"
        assert result.external_network_called is False


class TestRouteGovernanceUnchanged:
    def test_no_new_provider_route_added(self) -> None:
        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=None))
        prefix = DevWebApiConfig().api_prefix
        spec = app.openapi()
        paths = [p for p in spec.get("paths", {}) if p.startswith(prefix)]
        # Frozen baseline: 34 business paths, no provider-specific route.
        assert len(paths) == 34
        assert not any("provider" in p for p in paths)

    def test_tool_write_routes_remain_zero(self) -> None:
        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=None))
        prefix = DevWebApiConfig().api_prefix
        spec = app.openapi()
        write_methods = {"post", "put", "patch", "delete"}
        nonwrite = {f"{prefix}/tools/dry-run", f"{prefix}/tools/execute"}
        tool_write = [
            p for p in spec["paths"]
            if p.startswith(f"{prefix}/tools")
            and (write_methods & set(spec["paths"][p]))
            and p not in nonwrite
        ]
        assert tool_write == []
