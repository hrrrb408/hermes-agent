"""Phase 3B-Live-Enablement H1 — Live Round-trip / No-tool-execution Hardening.

Hardening pass over the one-shot live round-trip boundary (LIVE-ROUNDTRIP-3B-H1-001).

Probes the gate ORDERING (first failure wins, all fail closed with
externalNetworkCalled=false), the single-use invalidation, the
no-tool-execution invariant for the first live request, and that write /
autonomous / shell / DB / external-HTTP / rollback / production suggestions all
fire the kill switch and are blocked. Uses the injected MockHttpClient only — no
real network call, no real key read.

Phase: 3B-Live-Enablement H1 — Strict Manual One-shot Live Gate Hardening
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.dev_web_provider_live_approval import issue_live_approval
from hermes_cli.dev_web_provider_live_budget import LiveBudgetCaps
from hermes_cli.dev_web_provider_live_kill_switch import (
    is_kill_switch_active,
    trigger_kill_switch,
)
from hermes_cli.dev_web_provider_live_roundtrip import (
    LiveRoundtripRequest,
    evaluate_live_enablement,
    run_live_provider_roundtrip_controlled,
)
from hermes_cli.dev_web_provider_openai_compatible import MockHttpClient

_NOW = "2026-06-17T10:00:00+00:00"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-synthetic-sentinel-key-0123456789")
    for env in ("HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED"):
        monkeypatch.delenv(env, raising=False)


def _request(**overrides) -> LiveRoundtripRequest:
    base = dict(
        provider_name="openai_compatible", model="gpt-4o-mini",
        base_url="https://api.openai.com", base_url_host="api.openai.com",
        user_message="inspect route governance",
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


# ---------------------------------------------------------------------------
# 1. Gate ordering on the evaluate surface (no network)
# ---------------------------------------------------------------------------


class TestGateOrdering:
    def test_non_real_mode_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        outcome = evaluate_live_enablement(
            _request(), approval_id=None, provider_mode="disabled",
            api_enabled=True, caps=LiveBudgetCaps(), hermes_home=home, now_iso=_NOW,
        )
        assert outcome.allowed is False
        assert outcome.blocked_reason == "blocked_live_provider_not_human_approved"

    def test_api_not_enabled_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        outcome = evaluate_live_enablement(
            _request(), approval_id=None, provider_mode="real",
            api_enabled=False, caps=LiveBudgetCaps(), hermes_home=home, now_iso=_NOW,
        )
        assert outcome.allowed is False
        assert outcome.blocked_reason == "blocked_live_provider_not_human_approved"

    def test_dev_only_violation_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        outcome = evaluate_live_enablement(
            _request(), approval_id=None, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), hermes_home=home,
            now_iso=_NOW, is_dev_home=False,
        )
        assert outcome.allowed is False
        assert outcome.blocked_reason == "blocked_live_provider_dev_only_violation"

    def test_kill_switch_before_approval(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        trigger_kill_switch(hermes_home=home, reason="manual_operator_trigger", now_iso=_NOW)
        outcome = evaluate_live_enablement(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), hermes_home=home, now_iso=_NOW,
        )
        assert outcome.allowed is False
        assert outcome.blocked_reason == "blocked_live_provider_kill_switch_active"

    def test_approval_mismatch_before_network(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        outcome = evaluate_live_enablement(
            _request(model="gpt-4o"), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), hermes_home=home, now_iso=_NOW,
        )
        assert outcome.allowed is False
        assert outcome.blocked_reason == "blocked_live_provider_approval_mismatch"

    def test_network_before_budget(self, tmp_path) -> None:
        # Approval host matches the request host (so approval-match passes at
        # step 4), but the host is OFF the allowlist → the network gate (step 5)
        # blocks BEFORE the budget gate (step 6) is even consulted.
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path, base_url_host="evil.example.com")
        outcome = evaluate_live_enablement(
            _request(base_url="https://evil.example.com", base_url_host="evil.example.com"),
            approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), hermes_home=home, now_iso=_NOW,
        )
        assert outcome.allowed is False
        assert outcome.blocked_reason == "blocked_live_provider_host_not_approved"

    def test_approval_host_mismatch_before_network(self, tmp_path) -> None:
        # When the request host differs from the approved host, approval-match
        # (step 4) fails closed BEFORE any network check.
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path, base_url_host="api.openai.com")
        outcome = evaluate_live_enablement(
            _request(base_url="https://evil.example.com", base_url_host="evil.example.com"),
            approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), hermes_home=home, now_iso=_NOW,
        )
        assert outcome.allowed is False
        assert outcome.blocked_reason == "blocked_live_provider_approval_mismatch"

    def test_all_gates_pass_allowed(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        outcome = evaluate_live_enablement(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(), hermes_home=home, now_iso=_NOW,
        )
        assert outcome.allowed is True
        assert outcome.network_host == "api.openai.com"


# ---------------------------------------------------------------------------
# 2. Single-use invalidation + no tool execution
# ---------------------------------------------------------------------------


class TestSingleUseAndTools:
    def test_approval_invalidated_after_call(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        result = run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(),
            http_client=MockHttpClient(response_body=_ok_body()),
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        assert d["status"] == "completed"
        assert d["approvalInvalidated"] is True

    @pytest.mark.parametrize("tool", ["route_governance_read", "session_search"])
    def test_readonly_tool_classified_not_executed(self, tmp_path, tool: str) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path, tool_allowlist=frozenset({tool}))
        result = run_live_provider_roundtrip_controlled(
            _request(tool_allowlist=frozenset({tool})),
            approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(),
            http_client=MockHttpClient(response_body=_ok_body(tool=tool)),
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        assert all(not c["executed"] for c in d["toolCallsClassified"])
        assert any(c["toolId"] == tool for c in d["toolCallsClassified"])


# ---------------------------------------------------------------------------
# 3. Forbidden provider suggestions → kill switch + block
# ---------------------------------------------------------------------------


_FORBIDDEN_TOOLS = [
    "write_file", "patch", "memory_add", "memory_update", "todo", "skill_manage",
    "send_message", "terminal", "process", "execute_code", "delegate_task",
    "cronjob", "image_generate", "shell", "database", "production_operation",
]


class TestForbiddenSuggestions:
    @pytest.mark.parametrize("tool", _FORBIDDEN_TOOLS)
    def test_forbidden_suggestion_blocked_and_kill_fired(self, tmp_path, tool: str) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        result = run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(),
            http_client=MockHttpClient(response_body=_ok_body(tool=tool)),
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        assert is_kill_switch_active(hermes_home=home) is True
        assert any(
            c["toolId"] == tool and c["status"] == "blocked" for c in d["toolCallsClassified"]
        )
        assert all(not c["executed"] for c in d["toolCallsClassified"])

    def test_external_http_tool_blocked_not_executed(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        result = run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(),
            http_client=MockHttpClient(response_body=_ok_body(tool="external_http")),
            hermes_home=home, now_iso=_NOW,
        )
        d = result.to_safe_dict()
        assert any(
            c["toolId"] == "external_http" and c["status"] == "blocked"
            for c in d["toolCallsClassified"]
        )

    def test_secret_in_content_fires_kill(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        leaky = json.dumps({
            "id": "x",
            "choices": [{"message": {"role": "assistant", "content": "sk-leaked-key-1234567890"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
        }).encode("utf-8")
        run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(),
            http_client=MockHttpClient(response_body=leaky),
            hermes_home=home, now_iso=_NOW,
        )
        assert is_kill_switch_active(hermes_home=home) is True


# ---------------------------------------------------------------------------
# 4. No-leak invariant on the full result projection
# ---------------------------------------------------------------------------


class TestNoLeak:
    def test_result_blob_value_free(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        approval, _ = _issue(tmp_path)
        result = run_live_provider_roundtrip_controlled(
            _request(), approval_id=approval.approval_id, provider_mode="real",
            api_enabled=True, caps=LiveBudgetCaps(),
            http_client=MockHttpClient(response_body=_ok_body()),
            hermes_home=home, now_iso=_NOW,
        )
        blob = json.dumps(result.to_safe_dict())
        for needle in ("sk-synthetic", "sk-leaked", "Bearer ", "Authorization"):
            assert needle not in blob
