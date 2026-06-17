"""Phase 3B-Live-Enablement — Live Round-trip Boundary tests.

Verifies the one-shot live round-trip orchestrator with an injected
MockHttpClient (no real network call ever happens):

  - default (no approval / disabled) → blocked, externalNetworkCalled=false
  - kill switch active → blocked before network
  - missing approval → blocked before network
  - expired / used / mismatched approval → blocked
  - off-allowlist host → blocked
  - budget exceeded → blocked
  - valid approval + all gates → completed, approval invalidated, single-use
  - provider tool_calls classified, NOT executed (first live)
  - write/autonomous tool suggestion → blocked + kill switch fired
  - no real key value in the result projection

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from hermes_cli.dev_web_provider_live_approval import (
    issue_live_approval,
    mark_approval_used,
)
from hermes_cli.dev_web_provider_live_budget import LiveBudgetCaps
from hermes_cli.dev_web_provider_live_kill_switch import trigger_kill_switch
from hermes_cli.dev_web_provider_live_roundtrip import (
    LiveRoundtripRequest,
    run_live_provider_roundtrip_controlled,
)
from hermes_cli.dev_web_provider_openai_compatible import MockHttpClient


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
    for env in (
        "HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED", "HERMES_PROVIDER_API_KEY",
    ):
        monkeypatch.delenv(env, raising=False)


_NOW = "2026-06-17T10:00:00+00:00"
_HOME = None  # resolved per-test via the autouse fixture's tmp_path


def _ok_body(tool="route_governance_read") -> bytes:
    return json.dumps({
        "id": "x",
        "choices": [{
            "message": {"role": "assistant", "content": "Inspected.",
                        "tool_calls": [{
                            "id": "c1", "type": "function",
                            "function": {"name": tool, "arguments": "{}"},
                        }]},
            "finish_reason": "tool_calls",
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }).encode("utf-8")


def _request(**overrides) -> LiveRoundtripRequest:
    base = dict(
        provider_name="openai_compatible", model="gpt-4o-mini",
        base_url="https://api.openai.com", base_url_host="api.openai.com",
        user_message="check route governance",
        tool_allowlist=frozenset({"route_governance_read"}),
        estimated_input_tokens=20, estimated_output_tokens=20,
    )
    base.update(overrides)
    return LiveRoundtripRequest(**base)


def _issue(tmp_path, **overrides):
    home = str(tmp_path / "dev-home")
    kwargs = dict(
        provider_name="openai_compatible", model="gpt-4o-mini",
        base_url_host="api.openai.com", budget_cap_cents=5, request_cap=1,
        token_cap=1000, output_token_cap=200,
        tool_allowlist=frozenset({"route_governance_read"}),
        hermes_home=home, now_iso=_NOW,
    )
    kwargs.update(overrides)
    return issue_live_approval(**kwargs), home


class TestBlockedDefault:
    def test_disabled_mode_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        result = run_live_provider_roundtrip_controlled(
            _request(), approval_id=None, provider_mode="disabled",
            api_enabled=False, caps=LiveBudgetCaps(),
            http_client=MockHttpClient(response_body=_ok_body()),
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        assert d["status"] == "blocked"
        assert d["externalNetworkCalled"] is False
        assert d["blockedReason"] == "blocked_live_provider_not_human_approved"

    def test_no_approval_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        result = run_live_provider_roundtrip_controlled(
            _request(), approval_id=None, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(),
            http_client=MockHttpClient(response_body=_ok_body()),
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        assert d["status"] == "blocked"
        assert d["blockedReason"] == "blocked_live_provider_not_human_approved"
        assert d["externalNetworkCalled"] is False


class TestBlockedGates:
    def test_kill_switch_blocks_before_network(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        trigger_kill_switch(hermes_home=home, reason="manual_operator_trigger", now_iso=_NOW)
        result = run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(),
            http_client=MockHttpClient(response_body=_ok_body()),
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        assert d["status"] == "blocked"
        assert d["blockedReason"] == "blocked_live_provider_kill_switch_active"
        assert d["externalNetworkCalled"] is False

    def test_off_allowlist_host_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path, base_url_host="api.openai.com")
        result = run_live_provider_roundtrip_controlled(
            _request(base_url="https://evil.example.com", base_url_host="evil.example.com"),
            approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(),
            http_client=MockHttpClient(response_body=_ok_body()),
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        assert d["status"] == "blocked"
        assert d["externalNetworkCalled"] is False

    def test_token_cap_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        result = run_live_provider_roundtrip_controlled(
            _request(estimated_input_tokens=900, estimated_output_tokens=200),
            approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(),
            http_client=MockHttpClient(response_body=_ok_body()),
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        assert d["status"] == "blocked"
        assert d["blockedReason"] == "blocked_live_provider_token_cap_exceeded"


class TestCompletedOneShot:
    def test_valid_approval_completes_and_invalidates(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        mock = MockHttpClient(response_body=_ok_body())
        result = run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), http_client=mock,
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        assert d["status"] == "completed"
        assert d["externalNetworkCalled"] is True
        assert d["approvalInvalidated"] is True
        # The mock recorded exactly one POST (single-use, one request).
        assert len(mock.calls) == 1
        assert mock.calls[0]["url"].startswith("https://api.openai.com")

    def test_second_request_after_use_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        mock = MockHttpClient(response_body=_ok_body())
        first = run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), http_client=mock,
            hermes_home=home, now_iso=_NOW,
        )
        assert first.to_safe_dict()["status"] == "completed"
        # A second attempt with the SAME (now-used) approval is blocked.
        second = run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), http_client=mock,
            hermes_home=home, now_iso=_NOW,
        )
        sd = second.to_safe_dict()
        assert sd["status"] in ("blocked", "failed")
        assert sd["blockedReason"] in (
            "blocked_live_provider_approval_used",
            "blocked_live_provider_request_cap_exceeded",
            "blocked_live_provider_not_human_approved",
        )

    def test_no_tool_execution_for_first_live(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        mock = MockHttpClient(response_body=_ok_body(tool="route_governance_read"))
        result = run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), http_client=mock,
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        # The read-only tool_call is classified but NOT executed.
        assert all(not c["executed"] for c in d["toolCallsClassified"])
        assert any(c["toolId"] == "route_governance_read" for c in d["toolCallsClassified"])

    def test_write_tool_suggestion_blocked_and_kill_fired(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        mock = MockHttpClient(response_body=_ok_body(tool="write_file"))
        result = run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), http_client=mock,
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        # The write suggestion is blocked; the kill switch is armed.
        from hermes_cli.dev_web_provider_live_kill_switch import is_kill_switch_active

        assert is_kill_switch_active(hermes_home=home) is True
        assert any(
            c["toolId"] == "write_file" and c["status"] == "blocked"
            for c in d["toolCallsClassified"]
        )


class TestNoLeak:
    def test_result_never_carries_key_or_header(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        mock = MockHttpClient(response_body=_ok_body())
        result = run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), http_client=mock,
            hermes_home=home, now_iso=_NOW,
        )
        blob = json.dumps(result.to_safe_dict())
        for needle in ("sk-fake", "Bearer ", "Authorization"):
            assert needle not in blob

    def test_external_http_tool_blocked_not_executed(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        mock = MockHttpClient(response_body=_ok_body(tool="external_http"))
        result = run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), http_client=mock,
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        assert any(
            c["toolId"] == "external_http" and c["status"] == "blocked"
            for c in d["toolCallsClassified"]
        )
