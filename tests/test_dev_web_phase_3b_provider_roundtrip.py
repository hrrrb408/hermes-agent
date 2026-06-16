"""Phase 3B — Real Provider gated Round-trip tests (mock HTTP client only).

Verifies the orchestrator's full gated path with an injected MockHttpClient:
  - disabled / not-enabled / missing-key / bad-URL / unimplemented-name → blocked
    with the precise frozen-catalogue reason and externalNetworkCalled=false
  - fully-enabled + valid response → completed, externalNetworkCalled=true
  - write / unknown tool calls → blocked with precise reason (not executed)
  - secret in request → blocked_provider_secret_detected (no network)
  - auth failure → failed, not retried
  - budget exceeded → blocked_provider_budget_exceeded (no network)
  - rate limit exceeded → blocked_provider_rate_limit_exceeded (no network)
  - NO real network call is ever made (mock-only)

Phase: 3B — Real Provider Read-only Controlled Integration
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_provider_openai_compatible import MockHttpClient, RawHttpResponse
from hermes_cli.dev_web_provider_real_roundtrip import (
    build_real_request_from_message,
    preview_real_request,
    run_real_provider_roundtrip_controlled,
)

_PROVIDER_ENVS = (
    "HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED", "HERMES_PROVIDER_NAME",
    "HERMES_PROVIDER_BASE_URL", "HERMES_PROVIDER_MODEL", "HERMES_PROVIDER_TIMEOUT_SECONDS",
    "HERMES_PROVIDER_MAX_RETRIES", "HERMES_PROVIDER_DAILY_BUDGET_CENTS",
)
_KEY_ENVS = (
    "HERMES_PROVIDER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY",
    "ZAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY",
)


@pytest.fixture
def provider_home(tmp_path):
    home = tmp_path / "hermes-home-dev"
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    (home / "gateway" / "dev" / "provider").mkdir(parents=True, exist_ok=True)
    return str(home)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, provider_home):
    monkeypatch.setenv("HERMES_HOME", provider_home)
    for env in _PROVIDER_ENVS + _KEY_ENVS:
        monkeypatch.delenv(env, raising=False)


def _enable_real(monkeypatch, *, model="gpt-4o-mini", base_url="https://api.openai.com"):
    monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
    monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
    monkeypatch.setenv("HERMES_PROVIDER_NAME", "openai_compatible")
    monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", base_url)
    monkeypatch.setenv("HERMES_PROVIDER_MODEL", model)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")


def _ok_body(tool="route_governance_read") -> bytes:
    return json.dumps({
        "id": "x",
        "choices": [{
            "message": {"role": "assistant", "content": "I will inspect.",
                        "tool_calls": [{
                            "id": "c1", "type": "function",
                            "function": {"name": tool, "arguments": "{}"},
                        }]},
            "finish_reason": "tool_calls",
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }).encode("utf-8")


class TestBlockedWhenNotEnabled:
    def test_disabled_blocks(self, monkeypatch, provider_home) -> None:
        # No env → disabled.
        req = build_real_request_from_message("check route governance")
        resp = run_real_provider_roundtrip_controlled(
            req, http_client=MockHttpClient(response_body=_ok_body()),
            hermes_home=provider_home, production_gate_override=True,
        )
        d = resp.to_safe_dict()
        assert d["status"] == "blocked"
        assert d["externalNetworkCalled"] is False
        assert d["blockedReason"] == "blocked_provider_real_not_enabled"

    def test_real_without_api_enable_blocks(self, monkeypatch, provider_home) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        # API_ENABLED unset
        req = build_real_request_from_message("x")
        resp = run_real_provider_roundtrip_controlled(
            req, http_client=MockHttpClient(response_body=_ok_body()),
            hermes_home=provider_home, production_gate_override=True,
        )
        d = resp.to_safe_dict()
        assert d["blockedReason"] == "blocked_provider_api_disabled"
        assert d["externalNetworkCalled"] is False

    def test_missing_key_blocks(self, monkeypatch, provider_home) -> None:
        _enable_real(monkeypatch)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("HERMES_PROVIDER_API_KEY", raising=False)
        req = build_real_request_from_message("x")
        resp = run_real_provider_roundtrip_controlled(
            req, http_client=MockHttpClient(response_body=_ok_body()),
            hermes_home=provider_home, production_gate_override=True,
        )
        d = resp.to_safe_dict()
        assert d["blockedReason"] == "blocked_provider_api_key_missing"
        assert d["externalNetworkCalled"] is False

    def test_bad_base_url_blocks(self, monkeypatch, provider_home) -> None:
        _enable_real(monkeypatch, base_url="https://evil.example.com")
        req = build_real_request_from_message("x")
        resp = run_real_provider_roundtrip_controlled(
            req, http_client=MockHttpClient(response_body=_ok_body()),
            hermes_home=provider_home, production_gate_override=True,
        )
        d = resp.to_safe_dict()
        assert d["blockedReason"] == "blocked_provider_base_url_not_allowed"
        assert d["externalNetworkCalled"] is False

    def test_unsupported_name_blocks(self, monkeypatch, provider_home) -> None:
        _enable_real(monkeypatch)
        monkeypatch.setenv("HERMES_PROVIDER_NAME", "anthropic_compatible")
        req = build_real_request_from_message("x")
        resp = run_real_provider_roundtrip_controlled(
            req, http_client=MockHttpClient(response_body=_ok_body()),
            hermes_home=provider_home, production_gate_override=True,
        )
        d = resp.to_safe_dict()
        assert d["blockedReason"] == "blocked_provider_name_not_supported"
        assert d["externalNetworkCalled"] is False


class TestCompletedPath:
    def test_completed_when_enabled(self, monkeypatch, provider_home) -> None:
        _enable_real(monkeypatch)
        mock = MockHttpClient(response_body=_ok_body(tool="route_governance_read"))
        req = build_real_request_from_message("check route governance")
        resp = run_real_provider_roundtrip_controlled(
            req, http_client=mock, hermes_home=provider_home, production_gate_override=True,
        )
        d = resp.to_safe_dict()
        assert d["status"] == "completed"
        assert d["externalNetworkCalled"] is True
        assert len(d["toolCalls"]) == 1
        assert d["toolCalls"][0]["toolId"] == "route_governance_read"
        assert d["toolCalls"][0]["status"] == "parsed"
        assert d["usageSummary"]["totalTokens"] == 15
        assert d["costEstimate"] is not None
        # audit links were produced
        assert len(d["auditLinks"]) > 0

    def test_write_tool_call_blocked_not_executed(self, monkeypatch, provider_home) -> None:
        _enable_real(monkeypatch)
        body = json.dumps({"choices": [{
            "message": {"role": "assistant", "content": "x", "tool_calls": [{
                "id": "c1", "type": "function",
                "function": {"name": "write_file", "arguments": "{}"},
            }]}, "finish_reason": "tool_calls",
        }], "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}).encode()
        resp = run_real_provider_roundtrip_controlled(
            build_real_request_from_message("write a file"),
            http_client=MockHttpClient(response_body=body),
            hermes_home=provider_home, production_gate_override=True,
        )
        d = resp.to_safe_dict()
        tc = d["toolCalls"][0]
        assert tc["status"] == "blocked"
        assert tc["blockedReason"] == "blocked_provider_write_not_allowed"
        # response still completed (the tool call was blocked, not the round-trip)
        assert d["status"] == "completed"

    def test_secret_in_request_blocks_pre_network(self, monkeypatch, provider_home) -> None:
        _enable_real(monkeypatch)
        mock = MockHttpClient(response_body=_ok_body())
        resp = run_real_provider_roundtrip_controlled(
            build_real_request_from_message("here is my key sk-leakedkey-1234567890ab"),
            http_client=mock, hermes_home=provider_home, production_gate_override=True,
        )
        d = resp.to_safe_dict()
        assert d["blockedReason"] == "blocked_provider_secret_detected"
        assert d["externalNetworkCalled"] is False
        # The mock must NOT have been called (no network).
        assert len(mock.calls) == 0


class TestFailurePath:
    def test_auth_failure_not_retried(self, monkeypatch, provider_home) -> None:
        _enable_real(monkeypatch)
        mock = MockHttpClient(responses=tuple(
            RawHttpResponse(status=401, body=b'{}', error=None) for _ in range(5)
        ))
        resp = run_real_provider_roundtrip_controlled(
            build_real_request_from_message("hi"), http_client=mock,
            hermes_home=provider_home, production_gate_override=True,
        )
        d = resp.to_safe_dict()
        assert d["status"] == "failed"
        assert d["blockedReason"] == "blocked_provider_auth_failed"
        # Only one attempt (no retry) → only one recorded call.
        assert len(mock.calls) == 1


class TestBudgetAndRateLimit:
    def test_budget_exceeded_blocks_pre_network(self, monkeypatch, provider_home) -> None:
        _enable_real(monkeypatch)
        monkeypatch.setenv("HERMES_PROVIDER_DAILY_BUDGET_CENTS", "0")  # zero budget
        mock = MockHttpClient(response_body=_ok_body())
        resp = run_real_provider_roundtrip_controlled(
            build_real_request_from_message("hi"), http_client=mock,
            hermes_home=provider_home, production_gate_override=True,
        )
        d = resp.to_safe_dict()
        assert d["blockedReason"] == "blocked_provider_budget_exceeded"
        assert d["externalNetworkCalled"] is False
        assert len(mock.calls) == 0

    def test_rate_limit_exceeded_blocks(self, monkeypatch, provider_home) -> None:
        # Exhaust the daily request cap by pre-writing the counter file.
        _enable_real(monkeypatch)
        monkeypatch.setenv("HERMES_PROVIDER_MAX_RETRIES", "0")
        day = "2026-06-16"
        counter_path = Path(provider_home) / "gateway/dev/provider/usage-counters.json"
        counter_path.parent.mkdir(parents=True, exist_ok=True)
        counter_path.write_text(json.dumps({
            "windowMinute": "2026-06-16T00:00", "windowDay": day,
            "requestsThisMinute": 0, "requestsToday": 9999,
            "tokensToday": 0, "centsToday": 0, "lastUpdated": "x",
        }), encoding="utf-8")
        mock = MockHttpClient(response_body=_ok_body())
        resp = run_real_provider_roundtrip_controlled(
            build_real_request_from_message("hi"), http_client=mock,
            hermes_home=provider_home, production_gate_override=True,
            now_iso="2026-06-16T10:00:00Z",
        )
        d = resp.to_safe_dict()
        assert d["blockedReason"] == "blocked_provider_rate_limit_exceeded"
        assert d["externalNetworkCalled"] is False
        assert len(mock.calls) == 0


class TestPreview:
    def test_preview_redacted_no_key(self, monkeypatch, provider_home) -> None:
        _enable_real(monkeypatch)
        req = build_real_request_from_message("check route governance")
        preview = preview_real_request(req, hermes_home=provider_home)
        assert preview["previewed"] is True
        blob = json.dumps(preview)
        for needle in ("sk-", "Bearer ", "Authorization"):
            assert needle not in blob

    def test_preview_blocks_on_secret(self, monkeypatch, provider_home) -> None:
        _enable_real(monkeypatch)
        req = build_real_request_from_message("key sk-leakedkey-1234567890ab")
        preview = preview_real_request(req, hermes_home=provider_home)
        assert preview["previewed"] is False
        assert preview["blockedReason"] == "blocked_provider_secret_detected"


class TestNoRealNetwork:
    def test_no_real_network_in_any_test(self) -> None:
        # Every test above uses MockHttpClient; this class documents the
        # invariant that the real round-trip surface never makes a real call
        # under the default (disabled) config.
        from hermes_cli.dev_web_provider_config import load_provider_real_config

        cfg = load_provider_real_config()
        assert cfg.provider_mode == "disabled"
        assert cfg.api_enabled is False
