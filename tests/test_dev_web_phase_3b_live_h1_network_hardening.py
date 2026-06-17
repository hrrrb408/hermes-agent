"""Phase 3B-Live-Enablement H1 — Network Allowlist Hardening.

Hardening pass over the live network allowlist (LIVE-NETWORK-3B-H1-001).

Verifies the single allowed egress (a single HTTPS POST to api.openai.com)
and that everything else — http, file://, localhost, loopback, private IP
ranges (10/127/192.168/169.254/172.16-31), off-allowlist host, host that
differs from the approval host, and any redirect — fails closed with a precise
reason and no network call. Also verifies the provider external-HTTP tool
denylist.

This module performs no network call.

Phase: 3B-Live-Enablement H1 — Strict Manual One-shot Live Gate Hardening
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_live_network import (
    BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED,
    BLOCKED_LIVE_PROVIDER_PRIVATE_NETWORK_NOT_ALLOWED,
    BLOCKED_LIVE_PROVIDER_REDIRECT_NOT_ALLOWED,
    BLOCKED_LIVE_PROVIDER_SCHEME_NOT_HTTPS,
    LIVE_ALLOWED_HOSTS,
    LiveNetworkDecision,
    evaluate_live_network,
    is_tool_external_http,
    validate_live_redirect,
)

_APPROVED = "api.openai.com"


class TestAllowlistSurface:
    def test_only_openai_allowed(self) -> None:
        assert LIVE_ALLOWED_HOSTS == frozenset({"api.openai.com"})

    def test_approved_host_allowed(self) -> None:
        d = evaluate_live_network(base_url="https://api.openai.com", approval_host=_APPROVED)
        assert d.allowed is True
        assert d.host == _APPROVED
        assert d.blocked_reason is None

    def test_decision_value_free(self) -> None:
        d = evaluate_live_network(base_url="https://api.openai.com", approval_host=_APPROVED)
        blob = repr(d.to_safe_dict())
        for needle in ("sk-", "Bearer ", "Authorization"):
            assert needle not in blob


class TestScheme:
    @pytest.mark.parametrize(
        "url", ["http://api.openai.com", "ftp://api.openai.com", "file://api.openai.com"],
    )
    def test_non_https_blocked(self, url: str) -> None:
        d = evaluate_live_network(base_url=url, approval_host=_APPROVED)
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_SCHEME_NOT_HTTPS

    def test_bare_string_blocked(self) -> None:
        d = evaluate_live_network(base_url="api.openai.com", approval_host=_APPROVED)
        assert d.allowed is False


class TestPrivateLoopback:
    @pytest.mark.parametrize(
        "host",
        [
            "127.0.0.1", "localhost", "10.0.0.1", "192.168.1.1",
            "169.254.169.254", "172.16.0.1", "172.31.255.255", "[::1]", "0.0.0.0",
        ],
    )
    def test_private_blocked(self, host: str) -> None:
        url = f"https://{host}"
        d = evaluate_live_network(base_url=url, approval_host=host)
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_PRIVATE_NETWORK_NOT_ALLOWED

    @pytest.mark.parametrize("host", ["172.15.0.1", "172.32.0.1"])
    def test_172_outside_private_range_not_private_flag(self, host: str) -> None:
        # 172.15 / 172.32 are NOT private — they fail on HOST_NOT_APPROVED
        # (not in the allowlist), not on PRIVATE_NETWORK.
        url = f"https://{host}"
        d = evaluate_live_network(base_url=url, approval_host=host)
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED


class TestHostMismatch:
    def test_off_allowlist_host_blocked(self) -> None:
        d = evaluate_live_network(
            base_url="https://evil.example.com", approval_host="evil.example.com",
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED

    def test_url_host_differs_from_approval_host_blocked(self) -> None:
        d = evaluate_live_network(
            base_url="https://api.openai.com", approval_host="evil.example.com",
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED


class TestRedirect:
    def test_empty_redirect_blocked(self) -> None:
        d = validate_live_redirect(current_host=_APPROVED, location="")
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_REDIRECT_NOT_ALLOWED

    def test_off_allowlist_redirect_blocked(self) -> None:
        d = validate_live_redirect(current_host=_APPROVED, location="https://evil.example.com/x")
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_REDIRECT_NOT_ALLOWED

    def test_private_redirect_blocked(self) -> None:
        d = validate_live_redirect(current_host=_APPROVED, location="https://127.0.0.1/x")
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_PRIVATE_NETWORK_NOT_ALLOWED


class TestExternalHttpTools:
    @pytest.mark.parametrize(
        "tool_id",
        ["external_http", "web_search", "web_extract", "browser_navigate", "browser_action", "send_message"],
    )
    def test_external_http_tool_forbidden(self, tool_id: str) -> None:
        assert is_tool_external_http(tool_id) is True

    @pytest.mark.parametrize("tool_id", ["route_governance_read", "session_search", "", 123, None])
    def test_non_external_http_tool_allowed(self, tool_id) -> None:
        assert is_tool_external_http(tool_id) is False
