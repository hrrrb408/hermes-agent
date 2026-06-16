"""Phase 3B-H1 — Provider Policy HARDENING (Lens 4 + 5).

Deterministic, adversarial verification of the gating + cost/rate/budget policy:

  Lens 4 (Base URL / Timeout / Retry):
    - the enablement gate fails closed on the FIRST missing condition with a
      precise blocked_provider_* reason (no network call on any failure)
    - retry is safe-transient ONLY (auth / policy / budget / oversize / secret
      never retry)
    - HTTP failure classification is deterministic

  Lens 5 (Budget / Rate-limit / Response-size):
    - per-minute / daily-request / daily-token / daily-budget caps are enforced
      BEFORE any network call
    - cost is estimated before the call (rounded up, conservative)
    - a corrupt / out-of-home counter file fails CLOSED (request blocked)
    - budget breach → blocked_provider_budget_exceeded
    - rate-limit breach → blocked_provider_rate_limit_exceeded

Phase: 3B-H1 — Provider Boundary Hardening
Provider Policy Hardening ID: PROVIDER-POLICY-3B-H1-001
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_config import load_provider_real_config
from hermes_cli.dev_web_provider_real_budget import (
    BLOCKED_PROVIDER_BUDGET_EXCEEDED,
    BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED,
    ProviderUsageCounters,
    estimate_cost_cents,
    evaluate_rate_and_budget,
    read_usage_counters,
)
from hermes_cli.dev_web_provider_real_policy import (
    BLOCKED_PROVIDER_API_DISABLED,
    BLOCKED_PROVIDER_API_KEY_MISSING,
    BLOCKED_PROVIDER_AUTH_FAILED,
    BLOCKED_PROVIDER_BASE_URL_NOT_ALLOWED,
    BLOCKED_PROVIDER_BUDGET_EXCEEDED as POLICY_BUDGET,
    BLOCKED_PROVIDER_MODEL_NOT_ALLOWED,
    BLOCKED_PROVIDER_NAME_NOT_SUPPORTED,
    BLOCKED_PROVIDER_NOT_DEV_HOME,
    BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT,
    BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED as POLICY_RATE,
    BLOCKED_PROVIDER_REAL_NOT_ENABLED,
    BLOCKED_PROVIDER_RESPONSE_TOO_LARGE,
    BLOCKED_PROVIDER_RETRY_EXHAUSTED,
    BLOCKED_PROVIDER_SECRET_DETECTED,
    BLOCKED_PROVIDER_TIMEOUT_INVALID,
    BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    classify_http_failure,
    evaluate_real_provider_gating,
    is_auth_failure,
    is_safe_transient_failure,
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


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    for env in _PROVIDER_ENVS:
        monkeypatch.delenv(env, raising=False)
    for env in _KEY_ENVS:
        monkeypatch.delenv(env, raising=False)


def _cfg():
    return load_provider_real_config()


# ===========================================================================
# Lens 4 — enablement gate: first failure wins, all fail closed
# ===========================================================================


class TestGateFirstFailureWins:
    def test_default_disabled_blocks_first(self) -> None:
        ok, reason = evaluate_real_provider_gating(_cfg(), production_gate_override=True)
        assert ok is False
        assert reason == BLOCKED_PROVIDER_REAL_NOT_ENABLED

    def test_real_mode_without_api_enabled(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        ok, reason = evaluate_real_provider_gating(_cfg(), production_gate_override=True)
        assert (ok, reason) == (False, BLOCKED_PROVIDER_API_DISABLED)

    def test_real_enabled_unimplemented_name(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_NAME", "anthropic_compatible")
        ok, reason = evaluate_real_provider_gating(_cfg(), production_gate_override=True)
        assert (ok, reason) == (False, BLOCKED_PROVIDER_NAME_NOT_SUPPORTED)

    def test_real_enabled_missing_key(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        ok, reason = evaluate_real_provider_gating(_cfg(), production_gate_override=True)
        assert (ok, reason) == (False, BLOCKED_PROVIDER_API_KEY_MISSING)

    def test_real_enabled_not_dev_home(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        monkeypatch.setenv("HERMES_HOME", "/Users/huangruibang/.hermes")
        ok, reason = evaluate_real_provider_gating(_cfg(), production_gate_override=True)
        assert (ok, reason) == (False, BLOCKED_PROVIDER_NOT_DEV_HOME)

    def test_real_enabled_production_gate_drift(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        ok, reason = evaluate_real_provider_gating(_cfg(), production_gate_override=False)
        assert (ok, reason) == (False, BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT)

    def test_real_enabled_bad_base_url(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://evil.example.com")
        ok, reason = evaluate_real_provider_gating(_cfg(), production_gate_override=True)
        assert (ok, reason) == (False, BLOCKED_PROVIDER_BASE_URL_NOT_ALLOWED)

    def test_real_enabled_bad_model(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-hacker-edition")
        ok, reason = evaluate_real_provider_gating(_cfg(), production_gate_override=True)
        assert (ok, reason) == (False, BLOCKED_PROVIDER_MODEL_NOT_ALLOWED)

    def test_timeout_floor_is_structurally_guaranteed(self, monkeypatch) -> None:
        # The timeout gate's precondition (timeout >= 1) is structurally enforced
        # by HARD clamping in the config loader, so the gate is defense-in-depth.
        monkeypatch.setenv("HERMES_PROVIDER_TIMEOUT_SECONDS", "0")
        assert _cfg().timeout_seconds >= 1
        monkeypatch.setenv("HERMES_PROVIDER_TIMEOUT_SECONDS", "-5")
        assert _cfg().timeout_seconds >= 1

    def test_every_gate_passes_when_enabled(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-4o-mini")
        ok, reason = evaluate_real_provider_gating(_cfg(), production_gate_override=True)
        assert (ok, reason) == (True, None)


# ===========================================================================
# Lens 4 — retry classification (safe-transient only)
# ===========================================================================


class TestRetryClassification:
    @pytest.mark.parametrize("status", [408, 425, 500, 502, 503, 504])
    def test_safe_transient_http_status_retries(self, status: int) -> None:
        assert is_safe_transient_failure(http_status=status, blocked_reason=None) is True

    @pytest.mark.parametrize("status", [200, 301, 400, 401, 403, 404, 409, 422, 429])
    def test_non_transient_http_status_never_retries(self, status: int) -> None:
        assert is_safe_transient_failure(http_status=status, blocked_reason=None) is False

    @pytest.mark.parametrize("reason", [
        BLOCKED_PROVIDER_AUTH_FAILED, POLICY_BUDGET, POLICY_RATE,
        BLOCKED_PROVIDER_RESPONSE_TOO_LARGE, BLOCKED_PROVIDER_SECRET_DETECTED,
        BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED, BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
        BLOCKED_PROVIDER_BASE_URL_NOT_ALLOWED, BLOCKED_PROVIDER_TIMEOUT_INVALID,
    ])
    def test_non_transient_reason_never_retries(self, reason: str) -> None:
        assert is_safe_transient_failure(http_status=None, blocked_reason=reason) is False

    def test_only_network_unavailable_and_retry_exhausted_are_transient_reasons(self) -> None:
        assert is_safe_transient_failure(http_status=None, blocked_reason="blocked_provider_network_unavailable") is True
        assert is_safe_transient_failure(http_status=None, blocked_reason="blocked_provider_retry_exhausted") is True


class TestHttpFailureClassification:
    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_failure(self, status: int) -> None:
        assert is_auth_failure(status) is True
        assert classify_http_failure(status) == BLOCKED_PROVIDER_AUTH_FAILED

    def test_rate_limit_429(self) -> None:
        assert classify_http_failure(429) == BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED

    @pytest.mark.parametrize("status", [400, 404, 422])
    def test_client_error_is_schema_mismatch(self, status: int) -> None:
        assert classify_http_failure(status) == "blocked_provider_schema_mismatch"

    @pytest.mark.parametrize("status", [500, 502, 503, 504])
    def test_server_error_is_network_unavailable(self, status: int) -> None:
        assert classify_http_failure(status) == "blocked_provider_network_unavailable"

    def test_none_status_is_network_unavailable(self) -> None:
        assert classify_http_failure(None) == "blocked_provider_network_unavailable"


# ===========================================================================
# Lens 5 — cost estimate (conservative, rounded up, before the call)
# ===========================================================================


class TestCostEstimate:
    def test_estimate_is_rounded_up(self) -> None:
        # 1 prompt token of gpt-4o-mini (0.15c/1K) rounds up to 1 cent.
        est = estimate_cost_cents(model="gpt-4o-mini", prompt_tokens=1, completion_tokens=0)
        assert est["estimateCents"] >= 1
        assert est["roundedUp"] is True

    def test_zero_tokens_zero_cost(self) -> None:
        est = estimate_cost_cents(model="gpt-4o-mini", prompt_tokens=0, completion_tokens=0)
        assert est["estimateCents"] == 0

    def test_negative_tokens_clamped_to_zero(self) -> None:
        est = estimate_cost_cents(model="gpt-4o-mini", prompt_tokens=-100, completion_tokens=-100)
        assert est["promptTokens"] == 0
        assert est["completionTokens"] == 0

    def test_unknown_model_uses_default_price(self) -> None:
        est = estimate_cost_cents(model="unknown-model", prompt_tokens=1000, completion_tokens=0)
        # default prompt price 1.0c/1K → 1 cent per 1K prompt tokens.
        assert est["estimateCents"] >= 1

    def test_free_model_is_zero(self) -> None:
        est = estimate_cost_cents(model="glm-4-flash", prompt_tokens=9999, completion_tokens=9999)
        assert est["estimateCents"] == 0


# ===========================================================================
# Lens 5 — rate / budget evaluation (fail-closed, before the call)
# ===========================================================================


class TestRateBudgetEnforcement:
    def _full_cfg(self, monkeypatch) -> object:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-4o-mini")
        return _cfg()

    def test_allowed_when_under_caps(self, monkeypatch, tmp_path) -> None:
        cfg = self._full_cfg(monkeypatch)
        decision = evaluate_rate_and_budget(
            config=cfg, now_iso="2026-06-16T10:00:00",
            hermes_home=str(tmp_path / "dev-home"),
            estimated_prompt_tokens=10, estimated_completion_tokens=5,
        )
        assert decision.allowed is True
        assert decision.blocked_reason is None

    def test_per_minute_cap_blocks(self, monkeypatch, tmp_path) -> None:
        cfg = self._full_cfg(monkeypatch)
        home = str(tmp_path / "dev-home")
        # Burn the per-minute cap with attempts.
        for _ in range(cfg.per_minute_request_cap):
            evaluate_rate_and_budget(
                config=cfg, now_iso="2026-06-16T10:00:00", hermes_home=home,
                estimated_prompt_tokens=1, estimated_completion_tokens=1,
            ).blocked_reason  # evaluate (does not record); use read path below
        # Simulate the cap directly via the counters file.
        from hermes_cli.dev_web_provider_real_budget import record_request_attempt
        for _ in range(cfg.per_minute_request_cap):
            record_request_attempt(hermes_home=home, now_iso="2026-06-16T10:00:00")
        decision = evaluate_rate_and_budget(
            config=cfg, now_iso="2026-06-16T10:00:00", hermes_home=home,
            estimated_prompt_tokens=1, estimated_completion_tokens=1,
        )
        assert decision.allowed is False
        assert decision.blocked_reason == BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED

    def test_budget_cap_blocks(self, monkeypatch, tmp_path) -> None:
        cfg = self._full_cfg(monkeypatch)
        home = str(tmp_path / "dev-home")
        # Exhaust the daily budget (cents) directly.
        from hermes_cli.dev_web_provider_real_budget import meter_usage
        meter_usage(
            hermes_home=home, now_iso="2026-06-16T10:00:00",
            prompt_tokens=cfg.daily_token_cap, completion_tokens=0, cost_cents=cfg.daily_budget_cents,
        )
        decision = evaluate_rate_and_budget(
            config=cfg, now_iso="2026-06-16T10:00:00", hermes_home=home,
            estimated_prompt_tokens=1, estimated_completion_tokens=1,
        )
        assert decision.allowed is False
        assert decision.blocked_reason == BLOCKED_PROVIDER_BUDGET_EXCEEDED

    def test_corrupt_counters_fail_closed(self, monkeypatch, tmp_path) -> None:
        cfg = self._full_cfg(monkeypatch)
        home = str(tmp_path / "dev-home")
        # Write a corrupt counters file (not valid JSON).
        corrupt_path = tmp_path / "dev-home" / "gateway" / "dev" / "provider" / "usage-counters.json"
        corrupt_path.parent.mkdir(parents=True, exist_ok=True)
        corrupt_path.write_text("{ this is not json", encoding="utf-8")
        assert read_usage_counters(hermes_home=home, now_iso="2026-06-16T10:00:00") is None
        decision = evaluate_rate_and_budget(
            config=cfg, now_iso="2026-06-16T10:00:00", hermes_home=home,
            estimated_prompt_tokens=1, estimated_completion_tokens=1,
        )
        assert decision.allowed is False

    def test_production_home_counters_fail_closed(self, monkeypatch) -> None:
        cfg = self._full_cfg(monkeypatch)
        decision = evaluate_rate_and_budget(
            config=cfg, now_iso="2026-06-16T10:00:00",
            hermes_home="/Users/huangruibang/.hermes",
            estimated_prompt_tokens=1, estimated_completion_tokens=1,
        )
        assert decision.allowed is False

    def test_counters_to_safe_dict_has_no_secret(self) -> None:
        counters = ProviderUsageCounters(window_minute="m", window_day="d")
        blob = repr(counters.to_safe_dict())
        for needle in ("sk-", "Bearer ", "Authorization", "apiKey"):
            assert needle not in blob
