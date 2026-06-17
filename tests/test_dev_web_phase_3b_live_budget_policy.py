"""Phase 3B-Live-Enablement — Live Budget / Rate-limit Policy tests.

Verifies:
  - frozen caps (1 request, 1000 total, 200 output, 5 cents, 0 retry, 60s)
  - budget cap enforced
  - request cap enforced
  - token cap enforced
  - retry cap zero (non-zero retry blocked)
  - counter corruption fails closed
  - cost estimate is conservative (rounded up) + value-free
  - dev-only counter store (production home rejected)

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
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
    meter_live_usage,
    read_live_counters,
    record_live_attempt,
    reset_live_counters,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))


_NOW = "2026-06-17T10:00:00+00:00"


class TestFrozenCaps:
    def test_first_live_caps(self) -> None:
        caps = LiveBudgetCaps()
        assert caps.max_requests == MAX_REQUESTS == 1
        assert caps.max_total_tokens == MAX_TOTAL_TOKENS == 1000
        assert caps.max_output_tokens == MAX_OUTPUT_TOKENS == 200
        assert caps.max_budget_cents == MAX_BUDGET_CENTS == 5
        assert caps.max_retries == MAX_RETRIES == 0
        assert caps.max_runtime_seconds == 60

    def test_caps_badge_value_free(self) -> None:
        blob = json.dumps(LiveBudgetCaps().to_safe_dict())
        assert "sk-" not in blob
        assert "Bearer" not in blob
        assert json.loads(blob)["failClosedOnCounterError"] is True


class TestEvaluation:
    def test_within_caps_allowed(self, tmp_path) -> None:
        d = evaluate_live_budget(
            caps=LiveBudgetCaps(), model="gpt-4o-mini",
            hermes_home=str(tmp_path / "dev-home"), now_iso=_NOW,
            estimated_input_tokens=100, estimated_output_tokens=50,
        )
        assert d.allowed is True
        assert d.blocked_reason is None

    def test_missing_caps_blocked(self, tmp_path) -> None:
        d = evaluate_live_budget(
            caps=None, model="gpt-4o-mini",
            hermes_home=str(tmp_path / "dev-home"), now_iso=_NOW,
            estimated_input_tokens=10, estimated_output_tokens=10,
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_BUDGET_NOT_CONFIGURED

    def test_retry_nonzero_blocked(self, tmp_path) -> None:
        caps = LiveBudgetCaps(max_retries=1)
        d = evaluate_live_budget(
            caps=caps, model="gpt-4o-mini",
            hermes_home=str(tmp_path / "dev-home"), now_iso=_NOW,
            estimated_input_tokens=10, estimated_output_tokens=10,
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_RETRY_NOT_ALLOWED

    def test_token_cap_exceeded(self, tmp_path) -> None:
        d = evaluate_live_budget(
            caps=LiveBudgetCaps(), model="gpt-4o-mini",
            hermes_home=str(tmp_path / "dev-home"), now_iso=_NOW,
            estimated_input_tokens=900, estimated_output_tokens=200,
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_TOKEN_CAP_EXCEEDED

    def test_output_token_cap_exceeded(self, tmp_path) -> None:
        d = evaluate_live_budget(
            caps=LiveBudgetCaps(), model="gpt-4o-mini",
            hermes_home=str(tmp_path / "dev-home"), now_iso=_NOW,
            estimated_input_tokens=100, estimated_output_tokens=201,
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_TOKEN_CAP_EXCEEDED

    def test_request_cap_exceeded_after_use(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        assert record_live_attempt(hermes_home=home, now_iso=_NOW) is True
        d = evaluate_live_budget(
            caps=LiveBudgetCaps(), model="gpt-4o-mini",
            hermes_home=home, now_iso=_NOW,
            estimated_input_tokens=10, estimated_output_tokens=10,
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_REQUEST_CAP_EXCEEDED

    def test_budget_cap_exceeded_after_use(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        # Spend the full budget (5 cents) with minimal tokens so the token cap
        # is not the binding constraint; then evaluate a request whose cost
        # estimate pushes cents over the cap.
        meter_live_usage(
            hermes_home=home, now_iso=_NOW, prompt_tokens=1, completion_tokens=1,
            cost_cents=5,
        )
        d = evaluate_live_budget(
            caps=LiveBudgetCaps(), model="gpt-4o",
            hermes_home=home, now_iso=_NOW,
            estimated_input_tokens=100, estimated_output_tokens=50,
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_BUDGET_EXCEEDED


class TestCounterIntegrity:
    def test_corruption_fails_closed(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        from pathlib import Path

        counters_path = Path(home) / "gateway/dev/provider-live-budget/counters.json"
        counters_path.parent.mkdir(parents=True, exist_ok=True)
        counters_path.write_text("{not json", encoding="utf-8")
        d = evaluate_live_budget(
            caps=LiveBudgetCaps(), model="gpt-4o-mini",
            hermes_home=home, now_iso=_NOW,
            estimated_input_tokens=10, estimated_output_tokens=10,
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_COUNTER_UNAVAILABLE

    def test_production_home_rejected(self, tmp_path) -> None:
        d = evaluate_live_budget(
            caps=LiveBudgetCaps(), model="gpt-4o-mini",
            hermes_home="/Users/huangruibang/.hermes", now_iso=_NOW,
            estimated_input_tokens=10, estimated_output_tokens=10,
        )
        assert d.allowed is False
        assert d.blocked_reason == BLOCKED_LIVE_PROVIDER_COUNTER_UNAVAILABLE

    def test_reset_clears_counters(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        record_live_attempt(hermes_home=home, now_iso=_NOW)
        assert reset_live_counters(hermes_home=home, now_iso=_NOW) is True
        c = read_live_counters(hermes_home=home, now_iso=_NOW)
        assert c is not None
        assert c.requests_this_window == 0


class TestCostEstimate:
    def test_estimate_is_conservative_and_value_free(self) -> None:
        cost = estimate_live_cost_cents(
            model="gpt-4o-mini", prompt_tokens=100, completion_tokens=50,
        )
        assert cost["estimateCents"] >= 0
        assert cost["roundedUp"] is True
        blob = json.dumps(cost)
        assert "sk-" not in blob
        assert "Bearer" not in blob
