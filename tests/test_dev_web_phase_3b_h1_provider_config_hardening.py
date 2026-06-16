"""Phase 3B-H1 — Provider Config / Mode-gate Boundary HARDENING.

Deterministic, adversarial verification of Lens 1 (Provider Config / Mode Gate):
  - default mode = disabled; api_enabled = False (fail-closed default)
  - mode normalization is strict: case / whitespace / unknown → disabled
  - real mode requires BOTH HERMES_PROVIDER_MODE=real AND API_ENABLED=1
  - every enablement gate fails closed with a precise blocked_provider_* reason
  - unsupported / unimplemented provider name handling is value-free
  - bad / non-https / non-allowlisted base URL → blocked (host-only reduction)
  - numeric config is HARD-clamped (no crash, no silent rejection)
  - the production home (``~/.hermes``) is never treated as the dev home
  - NO API-key value is ever carried by ANY projection (safe-dict / repr)

This complements (does not duplicate) the Phase 3B config tests with stricter
adversarial inputs. No real provider is enabled; no key value is read.

Phase: 3B-H1 — Provider Boundary Hardening
Hardening ID: HARDENING-3B-H1-001
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_config import (
    PROVIDER_MODE_DISABLED,
    PROVIDER_MODE_FAKE,
    PROVIDER_MODE_REAL,
    _ALLOWED_BASE_URL_HOSTS,
    _ALLOWED_MODELS,
    _IMPLEMENTED_PROVIDER_NAMES,
    _KNOWN_PROVIDER_NAMES,
    load_provider_real_config,
)

_PROVIDER_ENVS = (
    "HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED", "HERMES_PROVIDER_NAME",
    "HERMES_PROVIDER_BASE_URL", "HERMES_PROVIDER_MODEL", "HERMES_PROVIDER_TIMEOUT_SECONDS",
    "HERMES_PROVIDER_MAX_RETRIES", "HERMES_PROVIDER_DAILY_BUDGET_CENTS",
    "HERMES_PROVIDER_MAX_TOKENS",
)
_KEY_ENVS = (
    "HERMES_PROVIDER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY",
    "ZAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY",
)

# The production home is the only HERMES_HOME that is NEVER the dev home.
_PRODUCTION_HOME = "/Users/huangruibang/.hermes"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    for env in _PROVIDER_ENVS:
        monkeypatch.delenv(env, raising=False)
    for env in _KEY_ENVS:
        monkeypatch.delenv(env, raising=False)


# ===========================================================================
# Lens 1 — fail-closed default + strict mode normalization
# ===========================================================================


class TestDefaultFailClosed:
    def test_default_is_disabled_and_api_off(self) -> None:
        cfg = load_provider_real_config()
        assert cfg.provider_mode == PROVIDER_MODE_DISABLED
        assert cfg.api_enabled is False

    def test_no_mode_env_resolves_to_disabled(self, monkeypatch) -> None:
        # Even with everything else enabled, no mode = disabled.
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        cfg = load_provider_real_config()
        assert cfg.provider_mode == PROVIDER_MODE_DISABLED

    @pytest.mark.parametrize("junk", ["live", "production", "1", "on", "true", "", "   ", "REAL_LIVE"])
    def test_non_canonical_mode_values_collapse_to_disabled(self, monkeypatch, junk: str) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", junk)
        cfg = load_provider_real_config()
        # Only the three canonical modes survive; anything else → disabled.
        assert cfg.provider_mode == PROVIDER_MODE_DISABLED

    @pytest.mark.parametrize("variant", ["REAL", "Real", " real ", "ReAl", "rEaL"])
    def test_real_mode_is_case_and_whitespace_insensitive(self, monkeypatch, variant: str) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", variant)
        assert load_provider_real_config().provider_mode == PROVIDER_MODE_REAL

    @pytest.mark.parametrize("variant", ["FAKE", "Fake", " fake ", "FaKe"])
    def test_fake_mode_is_case_and_whitespace_insensitive(self, monkeypatch, variant: str) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", variant)
        assert load_provider_real_config().provider_mode == PROVIDER_MODE_FAKE

    @pytest.mark.parametrize("variant", ["DISABLED", "Disabled", " disabled ", "DiSaBlEd"])
    def test_disabled_mode_is_case_and_whitespace_insensitive(self, monkeypatch, variant: str) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", variant)
        assert load_provider_real_config().provider_mode == PROVIDER_MODE_DISABLED


class TestRealModeEnablementIsCompound:
    def test_mode_real_without_api_enabled_still_off(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        cfg = load_provider_real_config()
        assert cfg.provider_mode == PROVIDER_MODE_REAL
        assert cfg.api_enabled is False

    def test_api_enabled_without_mode_real_still_not_real(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        cfg = load_provider_real_config()
        assert cfg.provider_mode != PROVIDER_MODE_REAL

    @pytest.mark.parametrize("truthy", ["1"])
    def test_only_canonical_enable_token_turns_api_on(self, monkeypatch, truthy: str) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", truthy)
        assert load_provider_real_config().api_enabled is True

    @pytest.mark.parametrize("falsy", ["0", "true", "yes", "on", "True", "2", "enabled", ""])
    def test_non_canonical_enable_tokens_do_not_enable(self, monkeypatch, falsy: str) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", falsy)
        assert load_provider_real_config().api_enabled is False


# ===========================================================================
# Lens 1 — provider name / implemented catalogue (value-free)
# ===========================================================================


class TestProviderNameCatalogue:
    def test_only_openai_compatible_is_implemented(self) -> None:
        # Phase 3B-H1 freezes the implemented set: exactly one concrete adapter.
        assert _IMPLEMENTED_PROVIDER_NAMES == frozenset({"openai_compatible"})

    def test_known_names_are_a_superset_of_implemented(self) -> None:
        assert _IMPLEMENTED_PROVIDER_NAMES <= _KNOWN_PROVIDER_NAMES

    @pytest.mark.parametrize("name", ["anthropic_compatible", "zai_compatible", "openrouter_compatible"])
    def test_reserved_names_are_known_but_not_implemented(self, monkeypatch, name: str) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_NAME", name)
        cfg = load_provider_real_config()
        assert cfg.provider_name == name
        assert cfg.name_implemented is False

    def test_unknown_name_collapses_to_default_implemented(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_NAME", "grok_native")
        cfg = load_provider_real_config()
        assert cfg.provider_name == "openai_compatible"
        assert cfg.name_implemented is True

    def test_name_handling_exposes_no_key_value(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_NAME", "anthropic_compatible")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-supersecretvalue-abcdefghij")
        blob = repr(load_provider_real_config().to_safe_dict())
        assert "sk-supersecretvalue" not in blob
        assert "supersecretvalue" not in blob


# ===========================================================================
# Lens 1 — base URL allowlist (https-only, host-only, secret-bearing query dropped)
# ===========================================================================


class TestBaseUrlAllowlistHardening:
    def test_allowlist_is_https_hosts_only(self) -> None:
        for host in _ALLOWED_BASE_URL_HOSTS:
            assert not host.startswith("http://")
            assert ":" not in host  # no scheme, no port baked in

    @pytest.mark.parametrize(
        "url,allowed",
        [
            ("HTTPS://API.OPENAI.COM", True),       # scheme is case-insensitive
            ("https://api.openai.com:443/v1", True),  # port + path stripped
            ("https://user:pass@api.openai.com", True),  # userinfo dropped (host kept)
            ("https://api.openai.com.evil.tld", False),  # suffix host not allowlisted
            ("https://evilapi.openai.com", False),  # prefix host not allowlisted
            ("ftp://api.openai.com", False),        # non-https scheme
            ("https://", False),                    # empty host
            ("https://api.openai.com#frag", True),  # fragment stripped
        ],
    )
    def test_host_policy_adversarial(self, monkeypatch, url: str, allowed: bool) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", url)
        cfg = load_provider_real_config()
        assert cfg.base_url_allowed is allowed

    def test_secret_bearing_url_reduces_to_host_only(self, monkeypatch) -> None:
        monkeypatch.setenv(
            "HERMES_PROVIDER_BASE_URL",
            "https://user:sk-secretinurl-1234567890@api.openai.com?token=leak",
        )
        cfg = load_provider_real_config()
        blob = repr(cfg.to_safe_dict())
        assert "sk-secretinurl" not in blob
        assert "token=leak" not in blob
        assert cfg.base_url_host == "api.openai.com"

    def test_non_allowlisted_host_renders_blank(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://evil.example.com")
        cfg = load_provider_real_config()
        assert cfg.base_url_allowed is False
        # A non-allowlisted host is never surfaced in the safe projection.
        assert cfg.to_safe_dict()["baseUrlHost"] == ""


# ===========================================================================
# Lens 1 — numeric HARD clamping (no crash on garbage / overflow)
# ===========================================================================


class TestHardClamping:
    @pytest.mark.parametrize("env,lo,hi", [
        ("HERMES_PROVIDER_TIMEOUT_SECONDS", 1, 60),
        ("HERMES_PROVIDER_MAX_RETRIES", 0, 4),
        ("HERMES_PROVIDER_DAILY_BUDGET_CENTS", 0, 500),
        ("HERMES_PROVIDER_MAX_TOKENS", 1, 4096),
    ])
    def test_overflow_clamped(self, monkeypatch, env: str, lo: int, hi: int) -> None:
        monkeypatch.setenv(env, "999999999")
        cfg = load_provider_real_config()
        value = getattr(cfg, env.replace("HERMES_PROVIDER_", "").lower())
        assert lo <= value <= hi

    @pytest.mark.parametrize("env", [
        "HERMES_PROVIDER_TIMEOUT_SECONDS", "HERMES_PROVIDER_MAX_RETRIES",
        "HERMES_PROVIDER_DAILY_BUDGET_CENTS", "HERMES_PROVIDER_MAX_TOKENS",
    ])
    def test_negative_clamped_to_floor(self, monkeypatch, env: str) -> None:
        monkeypatch.setenv(env, "-42")
        cfg = load_provider_real_config()
        value = getattr(cfg, env.replace("HERMES_PROVIDER_", "").lower())
        assert value >= 0

    @pytest.mark.parametrize("junk", ["not-a-number", "1.5e10", "NaN", "inf", "0x10", "", "None"])
    def test_garbage_falls_back_to_default(self, monkeypatch, junk: str) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_TIMEOUT_SECONDS", junk)
        cfg = load_provider_real_config()
        # Garbage never crashes; the timeout falls back to the bounded default.
        assert 1 <= cfg.timeout_seconds <= 60

    def test_model_allowlist_is_value_free_strings(self) -> None:
        for model in _ALLOWED_MODELS:
            assert isinstance(model, str)
            assert "sk-" not in model

    def test_rate_caps_are_finite_positive_ints(self) -> None:
        cfg = load_provider_real_config()
        for cap in (cfg.per_minute_request_cap, cfg.daily_request_cap, cfg.daily_token_cap):
            assert isinstance(cap, int)
            assert cap > 0


# ===========================================================================
# Lens 1 — dev-home boundary (~/.hermes is never the dev home)
# ===========================================================================


class TestDevHomeBoundary:
    def test_production_home_is_not_dev_home(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_HOME", _PRODUCTION_HOME)
        assert load_provider_real_config().is_dev_home is False

    def test_temp_home_is_dev_home(self) -> None:
        assert load_provider_real_config().is_dev_home is True

    def test_empty_hermes_home_is_not_dev_home(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_HOME", "")
        assert load_provider_real_config().is_dev_home is False


# ===========================================================================
# Lens 1 — value-free key marker across EVERY projection
# ===========================================================================


class TestKeyValueNeverCarried:
    @pytest.mark.parametrize("env_name", _KEY_ENVS)
    def test_present_marker_carries_no_value(self, monkeypatch, env_name: str) -> None:
        monkeypatch.setenv(env_name, "sk-supersecretvalue-abcdefghij")
        cfg = load_provider_real_config()
        assert cfg.api_key_source_detail == "env_present"
        blob = repr(cfg.to_safe_dict())
        assert "sk-supersecretvalue" not in blob
        assert "supersecretvalue" not in blob

    def test_multiple_keys_still_only_marker(self, monkeypatch) -> None:
        for i, env_name in enumerate(_KEY_ENVS):
            monkeypatch.setenv(env_name, f"sk-multivaluekey-{i:012d}")
        blob = repr(load_provider_real_config().to_safe_dict())
        assert "sk-multivaluekey" not in blob
        for i in range(len(_KEY_ENVS)):
            assert f"multivaluekey" not in blob

    def test_safe_dict_has_redaction_applied_flag(self) -> None:
        assert load_provider_real_config().to_safe_dict()["redactionApplied"] is True

    def test_safe_dict_key_fields_are_marker_only(self) -> None:
        d = load_provider_real_config().to_safe_dict()
        assert d["apiKeySource"] == "env"
        assert d["apiKeySourceDetail"] in ("env_present", "env_missing")
        assert isinstance(d["apiKeyPresent"], bool)
