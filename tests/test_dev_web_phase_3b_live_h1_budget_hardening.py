"""Phase 3B-Live-Enablement H1 — Budget / Counter / Fail-closed Hardening.

Hardening pass over the live budget + rate-limit policy (LIVE-BUDGET-3B-H1-001).

Verifies the frozen first-live caps, the exact cap boundaries (request / total
token / output token / budget / retry-zero), the fail-closed behavior on a
corrupt counter, the reset path, and that the counters live under the dev
HERMES_HOME only (never ~/.hermes, never state.db).

No network call and no real key read happen here.

Phase: 3B-Live-Enablement H1 — Strict Manual One-shot Live Gate Hardening
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.dev_web_provider_live_budget import (
    BLOCKED_LIVE_PROVIDER_BUDGET_EXCEEDED,
    BLOCKED_LIVE_PROVIDER_BUDGET_NOT_CONFIGURED,
    BLOCKED_LIVE_PROVIDER_COUNTER_UNAVAILABLE,
    BLOCKED_LIVE_PROVIDER_REQUEST_CAP_EXCEEDED,
    BLOCKED_LIVE_PROVIDER_RETRY_NOT_ALLOWED,
    BLOCKED_LIVE_PROVIDER_TOKEN_CAP_EXCEEDED,
    MAX_BUDGET_CENTS,
    MAX_OUTPUT_TOKENS,
    MAX_REQUESTS,
    MAX_RETRIES,
    MAX_TOTAL_TOKENS,
    LiveBudgetCaps,
    estimate_live_cost_cents,
    evaluate_live_budget,
    live_budget_badge,
    meter_live_usage,
    read_live_counters,
    record_live_attempt,
    reset_live_counters,
)

_NOW = "2026-06-17T10:00:00+00:00"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    for env in ("OPENAI_API_KEY", "HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED"):
        monkeypatch.delenv(env, raising=False)


def _eval(home, **overrides):
    kwargs = dict(
        caps=LiveBudgetCaps(), model="gpt-4o-mini", hermes_home=home, now_iso=_NOW,
        estimated_input_tokens=20, estimated_output_tokens=20,
    )
    kwargs.update(overrides)
    return evaluate_live_budget(**kwargs)


class TestFrozenCaps:
    def test_first_live_caps(self) -> None:
        assert MAX_REQUESTS == 1
        assert MAX_TOTAL_TOKENS == 1000
        assert MAX_OUTPUT_TOKENS == 200
        assert MAX_BUDGET_CENTS == 5
        assert MAX_RETRIES == 0
        caps = LiveBudgetCaps().to_safe_dict()
        assert caps["failClosedOnCounterError"] is True
        assert caps["redactionApplied"] is True

    def test_fresh_counters_allowed(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        d = _eval(home)
        assert d.allowed is True
        assert d.blocked_reason is None


class TestRequestCap:
    def test_request_cap_after_one_attempt(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        assert record_live_attempt(hermes_home=home, now_iso=_NOW) is True
        d = _eval(home)
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_REQUEST_CAP_EXCEEDED


class TestTokenCap:
    def test_total_token_over_cap_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        d = _eval(home, estimated_input_tokens=900, estimated_output_tokens=200)
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_TOKEN_CAP_EXCEEDED

    def test_output_token_over_cap_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        d = _eval(home, estimated_input_tokens=10, estimated_output_tokens=201)
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_TOKEN_CAP_EXCEEDED

    def test_accumulated_tokens_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        # Spend 990 tokens in-window; a 20-token request tips over 1000.
        assert meter_live_usage(
            hermes_home=home, now_iso=_NOW, prompt_tokens=985, completion_tokens=5, cost_cents=1,
        ) is True
        d = _eval(home, estimated_input_tokens=15, estimated_output_tokens=5)
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_TOKEN_CAP_EXCEEDED


class TestBudgetCap:
    def test_budget_exceeded_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        # Burn 5 cents in-window; even a 1-cent estimate exceeds the 5-cent cap.
        assert meter_live_usage(
            hermes_home=home, now_iso=_NOW, prompt_tokens=0, completion_tokens=0, cost_cents=5,
        ) is True
        d = _eval(home, estimated_input_tokens=10, estimated_output_tokens=10)
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_BUDGET_EXCEEDED


class TestRetryAndConfig:
    def test_retry_nonzero_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        caps = LiveBudgetCaps(max_retries=1)
        d = evaluate_live_budget(
            caps=caps, model="gpt-4o-mini", hermes_home=home, now_iso=_NOW,
            estimated_input_tokens=10, estimated_output_tokens=10,
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_RETRY_NOT_ALLOWED

    def test_missing_caps_blocked(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        d = evaluate_live_budget(
            caps=None, model="gpt-4o-mini", hermes_home=home, now_iso=_NOW,
            estimated_input_tokens=10, estimated_output_tokens=10,
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_BUDGET_NOT_CONFIGURED


class TestFailClosed:
    def test_corrupt_counter_fail_closed(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        from hermes_cli.dev_web_provider_live_budget import _resolve_store_path

        path, err = _resolve_store_path(home)
        assert err is None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not-json{", encoding="utf-8")
        # read_live_counters returns None on corruption.
        assert read_live_counters(hermes_home=home, now_iso=_NOW) is None
        d = _eval(home)
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_COUNTER_UNAVAILABLE

    def test_production_home_fail_closed(self) -> None:
        d = evaluate_live_budget(
            caps=LiveBudgetCaps(), model="gpt-4o-mini",
            hermes_home="/Users/huangruibang/.hermes", now_iso=_NOW,
            estimated_input_tokens=10, estimated_output_tokens=10,
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_COUNTER_UNAVAILABLE


class TestResetAndBadge:
    def test_reset_zeroes_counters(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        record_live_attempt(hermes_home=home, now_iso=_NOW)
        assert reset_live_counters(hermes_home=home, now_iso=_NOW) is True
        c = read_live_counters(hermes_home=home, now_iso=_NOW)
        assert c is not None and c.requests_this_window == 0

    def test_cost_estimate_rounded_up_cents(self) -> None:
        cost = estimate_live_cost_cents(model="gpt-4o-mini", prompt_tokens=1, completion_tokens=1)
        assert cost["roundedUp"] is True
        assert isinstance(cost["estimateCents"], int)

    def test_badge_value_free(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        c = read_live_counters(hermes_home=home, now_iso=_NOW)
        blob = json.dumps(live_budget_badge(caps=LiveBudgetCaps(), counters=c))
        for needle in ("sk-", "Bearer ", "Authorization", "/Users/huangruibang/.hermes", "state.db"):
            assert needle not in blob

    def test_store_under_dev_home_only(self, tmp_path) -> None:
        from hermes_cli.dev_web_provider_live_budget import _resolve_store_path

        home = tmp_path / "dev-home"
        path, err = _resolve_store_path(str(home))
        assert err is None
        assert "/Users/huangruibang/.hermes" not in str(path)
        assert "state.db" not in str(path)
