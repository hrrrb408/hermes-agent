"""Phase 3B-Live-Enablement — Live Network Allowlist tests.

Verifies:
  - only api.openai.com allowed (static allowlist)
  - http scheme blocked
  - localhost blocked
  - private IP blocked
  - approval-host mismatch blocked
  - arbitrary URL blocked
  - off-allowlist redirect blocked
  - file:// blocked
  - external-HTTP tool detection

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_live_network import (
    BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED,
    BLOCKED_LIVE_PROVIDER_PRIVATE_NETWORK_NOT_ALLOWED,
    BLOCKED_LIVE_PROVIDER_REDIRECT_NOT_ALLOWED,
    BLOCKED_LIVE_PROVIDER_SCHEME_NOT_HTTPS,
    LIVE_ALLOWED_HOSTS,
    evaluate_live_network,
    is_tool_external_http,
    validate_live_redirect,
)


class TestAllowlist:
    def test_openai_allowed(self) -> None:
        d = evaluate_live_network(
            base_url="https://api.openai.com/v1/chat/completions",
            approval_host="api.openai.com",
        )
        assert d.allowed is True
        assert d.host == "api.openai.com"
        assert d.blocked_reason is None

    def test_static_allowlist_is_openai_only(self) -> None:
        assert LIVE_ALLOWED_HOSTS == frozenset({"api.openai.com"})

    def test_host_must_match_approval(self) -> None:
        d = evaluate_live_network(
            base_url="https://api.openai.com", approval_host="api.z.ai",
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED


class TestSchemeAndHost:
    def test_http_blocked(self) -> None:
        d = evaluate_live_network(
            base_url="http://api.openai.com", approval_host="api.openai.com",
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_SCHEME_NOT_HTTPS

    def test_file_scheme_blocked(self) -> None:
        d = evaluate_live_network(
            base_url="file:///etc/passwd", approval_host="api.openai.com",
        )
        assert d.allowed is False

    @pytest.mark.parametrize(
        "url",
        [
            "https://localhost",
            "https://127.0.0.1",
            "https://10.0.0.1",
            "https://192.168.1.1",
            "https://172.16.0.1",
            "https://169.254.169.254",
        ],
    )
    def test_private_or_loopback_blocked(self, url: str) -> None:
        d = evaluate_live_network(base_url=url, approval_host="api.openai.com")
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_PRIVATE_NETWORK_NOT_ALLOWED

    @pytest.mark.parametrize(
        "url",
        ["https://evil.example.com", "https://api.openai.com.evil.com", ""],
    )
    def test_arbitrary_url_blocked(self, url: str) -> None:
        d = evaluate_live_network(base_url=url, approval_host="api.openai.com")
        assert d.allowed is False


class TestRedirect:
    def test_off_allowlist_redirect_blocked(self) -> None:
        d = validate_live_redirect(
            current_host="api.openai.com", location="https://evil.example.com/x",
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_REDIRECT_NOT_ALLOWED

    def test_loopback_redirect_blocked(self) -> None:
        d = validate_live_redirect(
            current_host="api.openai.com", location="https://127.0.0.1/x",
        )
        assert d.allowed is False

    def test_empty_redirect_blocked(self) -> None:
        d = validate_live_redirect(current_host="api.openai.com", location="")
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_REDIRECT_NOT_ALLOWED

    def test_same_host_redirect_allowed(self) -> None:
        # The first live slice forbids redirects in practice, but the validator
        # allows an exact same-allowlisted-host redirect (no off-allowlist hop).
        d = validate_live_redirect(
            current_host="api.openai.com", location="https://api.openai.com/v2/x",
        )
        assert d.allowed is True


class TestExternalHttpTool:
    @pytest.mark.parametrize(
        "tool_id,expected",
        [
            ("external_http", True),
            ("web_search", True),
            ("send_message", True),
            ("route_governance_read", False),
            ("clarify", False),
        ],
    )
    def test_external_http_detection(self, tool_id: str, expected: bool) -> None:
        assert is_tool_external_http(tool_id) is expected
