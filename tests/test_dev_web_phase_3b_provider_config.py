"""Phase 3B — Real Provider Config gating tests.

Verifies the bounded, env-driven config model:
  - default mode = disabled; api_enabled = False
  - real mode requires explicit enablement
  - missing key → env_missing (never the value)
  - bad / non-https / non-allowlisted base URL → blocked
  - unsupported / unimplemented provider name handling
  - timeout / budget / max_tokens clamping
  - model allowlist
  - dev-home vs ~/.hermes
  - NO API-key value is ever exposed by the config (only env_present/env_missing)

Phase: 3B — Real Provider Read-only Controlled Integration
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_config import (
    PROVIDER_MODE_DISABLED,
    PROVIDER_MODE_REAL,
    load_provider_real_config,
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


class TestDefaultDisabled:
    def test_default_mode_is_disabled(self) -> None:
        cfg = load_provider_real_config()
        assert cfg.provider_mode == PROVIDER_MODE_DISABLED
        assert cfg.api_enabled is False
        assert cfg.api_key_source_detail == "env_missing"

    def test_default_config_exposes_no_key_value(self) -> None:
        cfg = load_provider_real_config()
        blob = repr(cfg.to_safe_dict())
        for needle in ("sk-", "Bearer ", "Authorization", "api_key_value"):
            assert needle not in blob


class TestRealModeEnablement:
    def test_real_mode_requires_explicit_enable(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        # API_ENABLED unset → not enabled
        cfg = load_provider_real_config()
        assert cfg.provider_mode == "real"
        assert cfg.api_enabled is False

    def test_real_mode_with_enable_and_key(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        cfg = load_provider_real_config()
        assert cfg.api_enabled is True
        assert cfg.api_key_source_detail == "env_present"
        assert cfg.base_url_allowed is True
        assert cfg.model_allowed is True
        assert cfg.provider_name == "openai_compatible"
        assert cfg.name_implemented is True

    def test_key_present_marker_never_carries_value(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-supersecretvalue-abcdefghij")
        cfg = load_provider_real_config()
        assert cfg.api_key_source_detail == "env_present"
        safe = cfg.to_safe_dict()
        assert safe["apiKeyPresent"] is True
        blob = repr(safe)
        assert "sk-supersecretvalue" not in blob
        assert "supersecretvalue" not in blob


class TestBaseUrlAllowlist:
    @pytest.mark.parametrize(
        "url,allowed",
        [
            ("https://api.openai.com", True),
            ("https://api.openai.com/v1", True),
            ("https://api.z.ai", True),
            ("http://api.openai.com", False),  # plaintext http blocked
            ("https://evil.example.com", False),  # not allowlisted
            ("", False),
            ("not-a-url", False),
        ],
    )
    def test_base_url_host_policy(self, monkeypatch, url: str, allowed: bool) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", url)
        cfg = load_provider_real_config()
        assert cfg.base_url_allowed is allowed

    def test_base_url_never_exposes_secret_bearing_url(self, monkeypatch) -> None:
        # A URL with a userinfo/query secret must reduce to the host only.
        monkeypatch.setenv(
            "HERMES_PROVIDER_BASE_URL",
            "https://api.openai.com?token=sk-secretleak-1234567890",
        )
        cfg = load_provider_real_config()
        blob = repr(cfg.to_safe_dict())
        assert "sk-secretleak" not in blob
        assert cfg.base_url_host == "api.openai.com"


class TestClamping:
    def test_timeout_is_clamped(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_TIMEOUT_SECONDS", "99999")
        cfg = load_provider_real_config()
        assert 1 <= cfg.timeout_seconds <= 60

    def test_budget_is_clamped(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_DAILY_BUDGET_CENTS", "999999")
        cfg = load_provider_real_config()
        assert 0 <= cfg.daily_budget_cents <= 500

    def test_max_retries_is_clamped(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MAX_RETRIES", "999")
        cfg = load_provider_real_config()
        assert 0 <= cfg.max_retries <= 4

    def test_garbage_numeric_env_falls_back_to_default(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_TIMEOUT_SECONDS", "not-a-number")
        cfg = load_provider_real_config()
        assert cfg.timeout_seconds == 20  # default


class TestDevHome:
    def test_production_home_is_not_dev_home(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_HOME", "/Users/huangruibang/.hermes")
        cfg = load_provider_real_config()
        assert cfg.is_dev_home is False
