"""Phase 3B-Live-Enablement — Live Secret Read Policy tests.

Verifies:
  - secret not read before approval (blocked_before_secret_read)
  - secret not read before enabled mode (not_checked)
  - secret not read before kill switch inactive
  - secret not read before budget valid
  - secret not read before host allowlisted
  - secret state is value-free (no key value / prefix / hash)
  - default test path never returns the env key value

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.dev_web_provider_live_secret import (
    LIVE_API_KEY_ENV,
    read_provider_api_key_if_live_approved,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    monkeypatch.delenv(LIVE_API_KEY_ENV, raising=False)


class TestBlockedBeforeSecretRead:
    def test_disabled_mode_not_checked(self, monkeypatch) -> None:
        monkeypatch.setenv(LIVE_API_KEY_ENV, "sk-fake-placeholder-1234567890")
        r = read_provider_api_key_if_live_approved(
            provider_mode="disabled", api_enabled=True, kill_switch_active=False,
            approval_valid=True, budget_ok=True, host_ok=True,
        )
        assert r.key_state == "not_checked"

    def test_api_disabled_blocked(self, monkeypatch) -> None:
        monkeypatch.setenv(LIVE_API_KEY_ENV, "sk-fake-placeholder-1234567890")
        r = read_provider_api_key_if_live_approved(
            provider_mode="real", api_enabled=False, kill_switch_active=False,
            approval_valid=True, budget_ok=True, host_ok=True,
        )
        assert r.key_state == "blocked_before_secret_read"

    def test_kill_switch_blocked(self, monkeypatch) -> None:
        monkeypatch.setenv(LIVE_API_KEY_ENV, "sk-fake-placeholder-1234567890")
        r = read_provider_api_key_if_live_approved(
            provider_mode="real", api_enabled=True, kill_switch_active=True,
            approval_valid=True, budget_ok=True, host_ok=True,
        )
        assert r.key_state == "blocked_before_secret_read"

    def test_no_approval_blocked(self, monkeypatch) -> None:
        monkeypatch.setenv(LIVE_API_KEY_ENV, "sk-fake-placeholder-1234567890")
        r = read_provider_api_key_if_live_approved(
            provider_mode="real", api_enabled=True, kill_switch_active=False,
            approval_valid=False, budget_ok=True, host_ok=True,
        )
        assert r.key_state == "blocked_before_secret_read"

    def test_budget_invalid_blocked(self, monkeypatch) -> None:
        monkeypatch.setenv(LIVE_API_KEY_ENV, "sk-fake-placeholder-1234567890")
        r = read_provider_api_key_if_live_approved(
            provider_mode="real", api_enabled=True, kill_switch_active=False,
            approval_valid=True, budget_ok=False, host_ok=True,
        )
        assert r.key_state == "blocked_before_secret_read"

    def test_host_invalid_blocked(self, monkeypatch) -> None:
        monkeypatch.setenv(LIVE_API_KEY_ENV, "sk-fake-placeholder-1234567890")
        r = read_provider_api_key_if_live_approved(
            provider_mode="real", api_enabled=True, kill_switch_active=False,
            approval_valid=True, budget_ok=True, host_ok=False,
        )
        assert r.key_state == "blocked_before_secret_read"


class TestValueFree:
    def test_all_gates_pass_env_present(self, monkeypatch) -> None:
        monkeypatch.setenv(LIVE_API_KEY_ENV, "sk-fake-placeholder-1234567890")
        r = read_provider_api_key_if_live_approved(
            provider_mode="real", api_enabled=True, kill_switch_active=False,
            approval_valid=True, budget_ok=True, host_ok=True,
        )
        assert r.key_state == "env_present"
        blob = json.dumps(r.to_safe_dict())
        # The value is never carried — only the state marker.
        assert "sk-fake" not in blob
        assert r.to_safe_dict()["keyValue"] == "never"

    def test_all_gates_pass_env_missing(self, monkeypatch) -> None:
        monkeypatch.delenv(LIVE_API_KEY_ENV, raising=False)
        r = read_provider_api_key_if_live_approved(
            provider_mode="real", api_enabled=True, kill_switch_active=False,
            approval_valid=True, budget_ok=True, host_ok=True,
        )
        assert r.key_state == "env_missing"

    def test_never_carries_value_or_header(self, monkeypatch) -> None:
        monkeypatch.setenv(LIVE_API_KEY_ENV, "sk-fake-placeholder-1234567890")
        for mode in ("disabled", "real"):
            r = read_provider_api_key_if_live_approved(
                provider_mode=mode, api_enabled=True, kill_switch_active=False,
                approval_valid=True, budget_ok=True, host_ok=True,
            )
            blob = json.dumps(r.to_safe_dict())
            assert "Bearer" not in blob
            assert "sk-fake" not in blob
            assert r.key_source == "environment"

    def test_default_test_path_needs_no_real_key(self) -> None:
        # With no env set and disabled mode, the key is never inspected.
        r = read_provider_api_key_if_live_approved(
            provider_mode="disabled", api_enabled=False, kill_switch_active=True,
            approval_valid=False, budget_ok=False, host_ok=False,
        )
        assert r.key_state == "not_checked"
