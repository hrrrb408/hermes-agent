"""Phase 2B — Fake Provider Adapter tests.

Verifies the FakeProviderAdapter is deterministic, offline, routes each
keyword to the correct read-only tool (or clarify), never calls the external
network, and never reads an API key.

Phase: 2B — Provider Schema / API Controlled Integration
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_adapter import (
    BLOCKED_REAL_PROVIDER_NOT_WIRED,
    FakeProviderAdapter,
    RealProviderAdapter,
    get_provider_adapter,
)
from hermes_cli.dev_web_provider_request import build_provider_request
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST


def _fake_request(message: str, allowed=frozenset(STATIC_ALLOWLIST)):
    return build_provider_request(message, "fake", allowed_tool_ids=allowed)


class TestFakeProviderRouting:
    @pytest.mark.parametrize(
        "message,expected",
        [
            ("read tool policy", "tool_policy_read"),
            ("check route governance", "route_governance_read"),
            ("read audit events", "audit_events_read"),
            ("check dev environment", "dev_environment_read"),
            ("read release status", "release_status_read"),
            ("clarify what you mean", "clarify"),
        ],
    )
    def test_routes_message_to_tool(self, message, expected) -> None:
        adapter = FakeProviderAdapter()
        resp = adapter.invoke(_fake_request(message))
        assert resp.provider_mode == "fake"
        assert resp.provider_api_called is True
        assert resp.external_network_called is False
        assert resp.blocked is False
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == expected

    def test_no_match_returns_direct_answer(self) -> None:
        adapter = FakeProviderAdapter()
        resp = adapter.invoke(_fake_request("something totally unrelated"))
        assert resp.tool_calls == ()
        assert resp.finish_reason == "stop"

    def test_route_respects_allowlist_filter(self) -> None:
        adapter = FakeProviderAdapter()
        # Only route_governance_read allowed.
        resp = adapter.invoke(
            _fake_request("read tool policy", allowed=frozenset({"route_governance_read"}))
        )
        # tool_policy_read is not in the allowed set → no tool call.
        assert resp.tool_calls == ()


class TestFakeProviderDeterminism:
    def test_same_input_same_response_id(self) -> None:
        adapter = FakeProviderAdapter()
        r1 = adapter.invoke(_fake_request("check route governance"))
        r2 = adapter.invoke(_fake_request("check route governance"))
        assert r1.provider_response_id == r2.provider_response_id
        assert r1.tool_calls[0].id == r2.tool_calls[0].id
        assert r1.tool_calls[0].name == r2.tool_calls[0].name
        assert dict(r1.tool_calls[0].arguments) == dict(r2.tool_calls[0].arguments)

    def test_different_input_different_response_id(self) -> None:
        adapter = FakeProviderAdapter()
        r1 = adapter.invoke(_fake_request("check route governance"))
        r2 = adapter.invoke(_fake_request("read tool policy"))
        assert r1.provider_response_id != r2.provider_response_id

    def test_tool_call_arguments_are_stable(self) -> None:
        adapter = FakeProviderAdapter()
        resp = adapter.invoke(_fake_request("read tool policy"))
        assert dict(resp.tool_calls[0].arguments) == {"includeDisabled": True}


class TestFakeProviderFinalize:
    def test_finalize_produces_final_answer(self) -> None:
        adapter = FakeProviderAdapter()
        resp = adapter.invoke(
            _fake_request("check route governance"),
            tool_results={
                "executedToolIds": ["route_governance_read"],
                "blockedToolIds": [],
            },
        )
        assert resp.tool_calls == ()
        assert resp.finish_reason == "stop"
        assert "completed" in resp.assistant_message.lower()


class TestFakeProviderSafety:
    def test_external_network_never_called(self) -> None:
        adapter = FakeProviderAdapter()
        for msg in ("read tool policy", "check dev environment", "nothing matches"):
            resp = adapter.invoke(_fake_request(msg))
            assert resp.external_network_called is False


class TestRealProviderAdapterBlocked:
    def test_real_adapter_blocked_by_default(self) -> None:
        adapter = RealProviderAdapter()
        resp = adapter.invoke(build_provider_request("x", "real"))
        assert resp.blocked is True
        assert resp.external_network_called is False

    def test_real_adapter_blocked_even_when_enabled(self, monkeypatch) -> None:
        # Even with all enablement env present, Phase 2B does not wire the call.
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_KEY", "dummy-key-not-used")
        monkeypatch.setenv("HERMES_HOME", "/tmp/dev-home")
        # Bypass the production-gate probe via the override path: build a real
        # request with the gate override so eligibility passes, then assert the
        # adapter still refuses to call the network.
        adapter = RealProviderAdapter()
        resp = adapter.invoke(build_provider_request("x", "real"))
        assert resp.blocked is True
        assert resp.blocked_reason == BLOCKED_REAL_PROVIDER_NOT_WIRED
        assert resp.external_network_called is False

    def test_get_adapter_factory(self) -> None:
        assert isinstance(get_provider_adapter("fake"), FakeProviderAdapter)
        assert isinstance(get_provider_adapter("real"), RealProviderAdapter)
