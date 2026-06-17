"""Phase 3B-Live-Enablement H1 — Secret Read Gate Hardening.

Hardening pass over the live secret-read policy (LIVE-SECRET-3B-H1-001).

Verifies the gate ordering: ``OPENAI_API_KEY`` is inspected ONLY past every gate.
On every blocked path the result is ``blocked_before_secret_read`` (or
``not_checked`` for a non-real mode), the env is NEVER inspected, and the
returned state is value-free (no key value / prefix / suffix / length / hash).

The module uses a sentinel key + an ``os.environ`` access spy to PROVE the env
is not touched on blocked paths. No real key is ever required.

Phase: 3B-Live-Enablement H1 — Strict Manual One-shot Live Gate Hardening
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.dev_web_provider_live_secret import (
    LIVE_API_KEY_ENV,
    is_secret_state_safe_for_audit,
    read_provider_api_key_if_live_approved,
)

_SENTINEL = "sk-synthetic-sentinel-key-0123456789-abcdef"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    # A real-looking sentinel key. Blocked paths must NEVER inspect it.
    monkeypatch.setenv(LIVE_API_KEY_ENV, _SENTINEL)
    for env in ("HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED"):
        monkeypatch.delenv(env, raising=False)


def _call(**overrides):
    kwargs = dict(
        provider_mode="real", api_enabled=True, kill_switch_active=False,
        approval_valid=True, budget_ok=True, host_ok=True,
    )
    kwargs.update(overrides)
    return read_provider_api_key_if_live_approved(**kwargs)


class TestGateOrdering:
    def test_env_named_openai_api_key(self) -> None:
        assert LIVE_API_KEY_ENV == "OPENAI_API_KEY"

    @pytest.mark.parametrize(
        "overrides",
        [
            dict(provider_mode="disabled"),                  # non-real → not_checked
            dict(api_enabled=False),                          # api not enabled
            dict(kill_switch_active=True),                    # kill switch active
            dict(approval_valid=False),                       # no approval
            dict(budget_ok=False),                            # budget invalid
            dict(host_ok=False),                              # host not allowlisted
        ],
    )
    def test_blocked_path_never_reads_env(self, overrides, monkeypatch) -> None:
        # Spy ONLY on os.environ.get (patching the bound method leaves
        # subscript access — which pytest's terminal writer uses — intact).
        import os

        calls: list[str] = []
        real_get = os.environ.get

        def _spy_get(key, default=None):
            calls.append(str(key))
            return real_get(key, default)

        monkeypatch.setattr(os.environ, "get", _spy_get)
        result = _call(**overrides)
        # The env var must NEVER have been read on a blocked path.
        assert LIVE_API_KEY_ENV not in calls
        if overrides == dict(provider_mode="disabled"):
            assert result.key_state == "not_checked"
        else:
            assert result.key_state == "blocked_before_secret_read"

    def test_all_gates_pass_reads_presence(self) -> None:
        result = _call()
        assert result.key_state == "env_present"

    def test_all_gates_pass_missing_env(self, monkeypatch) -> None:
        monkeypatch.delenv(LIVE_API_KEY_ENV, raising=False)
        result = _call()
        assert result.key_state == "env_missing"


class TestValueFree:
    def test_result_carries_no_key_value(self) -> None:
        result = _call()
        blob = json.dumps(result.to_safe_dict())
        for needle in ("sk-", _SENTINEL, "Bearer ", "Authorization", "prefix", "suffix"):
            assert needle not in blob
        assert result.to_safe_dict()["keyValue"] == "never"

    def test_key_source_is_environment_only(self) -> None:
        assert _call().key_source == "environment"

    def test_safe_for_audit_on_every_state(self, monkeypatch) -> None:
        for state_case in (
            dict(provider_mode="disabled"),
            dict(api_enabled=False),
            dict(kill_switch_active=True),
            dict(approval_valid=False),
            dict(budget_ok=False),
            dict(host_ok=False),
            dict(),
        ):
            monkeypatch.setenv(LIVE_API_KEY_ENV, _SENTINEL)
            assert is_secret_state_safe_for_audit(_call(**state_case)) is True

    def test_no_key_value_in_any_state_blob(self, monkeypatch) -> None:
        for state_case in (
            dict(provider_mode="disabled"),
            dict(api_enabled=False),
            dict(kill_switch_active=True),
            dict(approval_valid=False),
            dict(),
        ):
            monkeypatch.setenv(LIVE_API_KEY_ENV, _SENTINEL)
            blob = json.dumps(_call(**state_case).to_safe_dict())
            assert _SENTINEL not in blob
            assert "sk-" not in blob
