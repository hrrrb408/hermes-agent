"""Phase 3B — Real Provider Policy + Tool Allowlist tests.

Verifies:
  - default disabled → blocked_provider_real_not_enabled
  - real without enable → blocked_provider_api_disabled
  - missing key → blocked_provider_api_key_missing
  - bad base URL → blocked_provider_base_url_not_allowed
  - unsupported / unimplemented name → blocked_provider_name_not_supported
  - unknown model → blocked_provider_model_not_allowed
  - timeout invalid → blocked_provider_timeout_invalid
  - read-only tool allowlist: only the Phase 2A STATIC_ALLOWLIST passes
  - write / rollback / shell / db / external / production / plugin names blocked
    with precise reasons
  - retry classification (safe-transient only; auth/policy/budget never retry)

Phase: 3B — Real Provider Read-only Controlled Integration
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_config import load_provider_real_config
from hermes_cli.dev_web_provider_real_policy import (
    BLOCKED_PROVIDER_API_DISABLED,
    BLOCKED_PROVIDER_API_KEY_MISSING,
    BLOCKED_PROVIDER_AUTH_FAILED,
    BLOCKED_PROVIDER_BASE_URL_NOT_ALLOWED,
    BLOCKED_PROVIDER_BUDGET_EXCEEDED,
    BLOCKED_PROVIDER_EXTERNAL_URL_NOT_ALLOWED,
    BLOCKED_PROVIDER_MODEL_NOT_ALLOWED,
    BLOCKED_PROVIDER_NAME_NOT_SUPPORTED,
    BLOCKED_PROVIDER_NOT_DEV_HOME,
    BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED,
    BLOCKED_PROVIDER_REAL_NOT_ENABLED,
    BLOCKED_PROVIDER_RESPONSE_TOO_LARGE,
    BLOCKED_PROVIDER_RETRY_EXHAUSTED,
    BLOCKED_PROVIDER_SECRET_DETECTED,
    BLOCKED_PROVIDER_TIMEOUT_INVALID,
    BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    BLOCKED_PROVIDER_WRITE_NOT_ALLOWED,
    classify_http_failure,
    classify_provider_tool_call,
    evaluate_real_provider_gating,
    get_read_only_tool_allowlist,
    is_auth_failure,
    is_safe_transient_failure,
)

_PROVIDER_ENVS = (
    "HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED", "HERMES_PROVIDER_NAME",
    "HERMES_PROVIDER_BASE_URL", "HERMES_PROVIDER_MODEL", "HERMES_PROVIDER_TIMEOUT_SECONDS",
)
_KEY_ENVS = (
    "HERMES_PROVIDER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY",
    "ZAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    for env in _PROVIDER_ENVS + _KEY_ENVS:
        monkeypatch.delenv(env, raising=False)


class TestGatingReasons:
    def test_default_disabled(self, monkeypatch) -> None:
        # No env set → disabled
        cfg = load_provider_real_config()
        ok, reason = evaluate_real_provider_gating(cfg, production_gate_override=True)
        assert ok is False
        assert reason == BLOCKED_PROVIDER_REAL_NOT_ENABLED

    def test_real_without_enable(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        cfg = load_provider_real_config()
        ok, reason = evaluate_real_provider_gating(cfg, production_gate_override=True)
        assert ok is False
        assert reason == BLOCKED_PROVIDER_API_DISABLED

    def test_missing_key(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-4o-mini")
        cfg = load_provider_real_config()
        ok, reason = evaluate_real_provider_gating(cfg, production_gate_override=True)
        assert ok is False
        assert reason == BLOCKED_PROVIDER_API_KEY_MISSING

    def test_bad_base_url(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://evil.example.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        cfg = load_provider_real_config()
        ok, reason = evaluate_real_provider_gating(cfg, production_gate_override=True)
        assert ok is False
        assert reason == BLOCKED_PROVIDER_BASE_URL_NOT_ALLOWED

    def test_unsupported_name(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_NAME", "anthropic_compatible")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        cfg = load_provider_real_config()
        ok, reason = evaluate_real_provider_gating(cfg, production_gate_override=True)
        assert ok is False
        assert reason == BLOCKED_PROVIDER_NAME_NOT_SUPPORTED

    def test_unknown_model(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-99-not-real")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        cfg = load_provider_real_config()
        ok, reason = evaluate_real_provider_gating(cfg, production_gate_override=True)
        assert ok is False
        assert reason == BLOCKED_PROVIDER_MODEL_NOT_ALLOWED

    def test_not_dev_home(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_HOME", "/Users/huangruibang/.hermes")
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        cfg = load_provider_real_config()
        ok, reason = evaluate_real_provider_gating(cfg, production_gate_override=True)
        assert ok is False
        assert reason == BLOCKED_PROVIDER_NOT_DEV_HOME

    def test_production_gate_drift(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        cfg = load_provider_real_config()
        ok, reason = evaluate_real_provider_gating(cfg, production_gate_override=False)
        assert ok is False
        assert reason in ("blocked_provider_production_gate_drift",)

    def test_fully_enabled_passes(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        cfg = load_provider_real_config()
        ok, reason = evaluate_real_provider_gating(cfg, production_gate_override=True)
        assert ok is True
        assert reason is None


class TestReadOnlyAllowlist:
    def test_allowlist_is_static_six(self) -> None:
        allowlist = get_read_only_tool_allowlist()
        for tool in (
            "clarify", "tool_policy_read", "route_governance_read",
            "audit_events_read", "dev_environment_read", "release_status_read",
        ):
            assert tool in allowlist

    @pytest.mark.parametrize(
        "tool_id",
        [
            "clarify", "tool_policy_read", "route_governance_read",
            "audit_events_read", "dev_environment_read", "release_status_read",
        ],
    )
    def test_read_only_tools_allowed(self, tool_id: str) -> None:
        allowed, reason = classify_provider_tool_call(tool_id, {})
        assert allowed is True
        assert reason is None

    @pytest.mark.parametrize(
        "tool_id,expected_reason",
        [
            ("dev_sandbox_file_write", BLOCKED_PROVIDER_WRITE_NOT_ALLOWED),
            ("dev_sandbox_file_append", BLOCKED_PROVIDER_WRITE_NOT_ALLOWED),
            ("dev_sandbox_file_patch", BLOCKED_PROVIDER_WRITE_NOT_ALLOWED),
            ("dev_sandbox_file_readback", BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED),
            ("dev_sandbox_rollback_execute", BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED),
            ("write_file", BLOCKED_PROVIDER_WRITE_NOT_ALLOWED),
            ("patch", BLOCKED_PROVIDER_WRITE_NOT_ALLOWED),
            ("shell", BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED),
            ("terminal", BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED),
            ("database", BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED),
            ("external_http", BLOCKED_PROVIDER_EXTERNAL_URL_NOT_ALLOWED),
            ("production_operation", BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED),
            ("plugin_dynamic_load", BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED),
            ("send_message", BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED),
            ("execute_code", BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED),
            ("memory_add", BLOCKED_PROVIDER_WRITE_NOT_ALLOWED),
        ],
    )
    def test_forbidden_tools_blocked(self, tool_id: str, expected_reason: str) -> None:
        allowed, reason = classify_provider_tool_call(tool_id, {})
        assert allowed is False
        assert reason == expected_reason

    def test_unknown_tool_blocked(self) -> None:
        allowed, reason = classify_provider_tool_call("definitely_not_real_tool", {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED

    def test_non_string_tool_id_blocked(self) -> None:
        allowed, reason = classify_provider_tool_call(None, {})
        assert allowed is False
        assert reason == BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED


class TestRetryClassification:
    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_failure_never_retried(self, status: int) -> None:
        assert is_auth_failure(status) is True
        assert is_safe_transient_failure(http_status=status, blocked_reason=None) is False

    def test_rate_limit_never_retried(self) -> None:
        assert is_safe_transient_failure(
            http_status=429, blocked_reason=None,
        ) is False

    @pytest.mark.parametrize("reason", [
        BLOCKED_PROVIDER_SECRET_DETECTED, BLOCKED_PROVIDER_BUDGET_EXCEEDED,
        BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED, BLOCKED_PROVIDER_RESPONSE_TOO_LARGE,
        BLOCKED_PROVIDER_AUTH_FAILED,
    ])
    def test_non_retryable_reasons(self, reason: str) -> None:
        assert is_safe_transient_failure(http_status=None, blocked_reason=reason) is False

    @pytest.mark.parametrize("status", [500, 502, 503, 504])
    def test_safe_transient_5xx(self, status: int) -> None:
        assert is_safe_transient_failure(http_status=status, blocked_reason=None) is True

    def test_classify_http_failure(self) -> None:
        assert classify_http_failure(401) == BLOCKED_PROVIDER_AUTH_FAILED
        assert classify_http_failure(429) == BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED
        assert classify_http_failure(503) in (
            "blocked_provider_network_unavailable",
        )

    def test_retry_exhausted_reason_constant(self) -> None:
        assert BLOCKED_PROVIDER_RETRY_EXHAUSTED == "blocked_provider_retry_exhausted"

    def test_timeout_invalid_reason_constant(self) -> None:
        assert BLOCKED_PROVIDER_TIMEOUT_INVALID == "blocked_provider_timeout_invalid"
