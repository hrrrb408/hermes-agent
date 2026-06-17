"""Phase 3B-Live-Enablement — Live Approval Model tests.

Verifies:
  - default missing approval → blocked_live_provider_not_human_approved
  - approval create is value-free (no key / header / token)
  - approval TTL = 5 minutes
  - approval single-use (used approval blocked)
  - expired approval blocked
  - scope mismatch blocked
  - approval mismatch (provider / model / host / tool) blocked
  - approval store is dev-only (production home rejected)
  - approval invalidation after use

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from hermes_cli.dev_web_provider_live_approval import (
    APPROVAL_SCOPE,
    BLOCKED_LIVE_PROVIDER_APPROVAL_EXPIRED,
    BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH,
    BLOCKED_LIVE_PROVIDER_APPROVAL_SCOPE_INVALID,
    BLOCKED_LIVE_PROVIDER_APPROVAL_USED,
    BLOCKED_LIVE_PROVIDER_NOT_HUMAN_APPROVED,
    DEFAULT_TTL_SECONDS,
    find_active_approval,
    issue_live_approval,
    list_approvals,
    mark_approval_used,
    match_live_approval,
    revoke_all_approvals,
    validate_live_approval,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    for env in (
        "OPENAI_API_KEY", "HERMES_PROVIDER_API_KEY", "HERMES_PROVIDER_MODE",
        "HERMES_PROVIDER_API_ENABLED",
    ):
        monkeypatch.delenv(env, raising=False)


_NOW = "2026-06-17T10:00:00+00:00"


def _issue(monkeypatch, tmp_path, **overrides):
    kwargs = dict(
        provider_name="openai_compatible", model="gpt-4o-mini",
        base_url_host="api.openai.com", budget_cap_cents=5, request_cap=1,
        token_cap=1000, output_token_cap=200,
        tool_allowlist=frozenset({"route_governance_read"}),
        hermes_home=str(tmp_path / "dev-home"), now_iso=_NOW,
    )
    kwargs.update(overrides)
    return issue_live_approval(**kwargs)


class TestApprovalLifetime:
    def test_missing_approval_blocked(self) -> None:
        ok, reason = validate_live_approval(None, now_iso=_NOW)
        assert ok is False
        assert reason == BLOCKED_LIVE_PROVIDER_NOT_HUMAN_APPROVED

    def test_create_is_value_free(self, tmp_path) -> None:
        a = _issue(None, tmp_path)
        assert a is not None
        blob = json.dumps(a.to_safe_dict())
        for needle in ("sk-", "Bearer ", "Authorization", "apiKeyValue"):
            assert needle not in blob
        assert a.approval_scope == APPROVAL_SCOPE
        assert a.single_use is True
        assert a.provider_mode == "real"

    def test_ttl_is_five_minutes(self, tmp_path) -> None:
        a = _issue(None, tmp_path)
        assert a is not None
        created = datetime.fromisoformat(a.created_at)
        expires = datetime.fromisoformat(a.expires_at)
        assert (expires - created) == timedelta(seconds=DEFAULT_TTL_SECONDS)
        assert DEFAULT_TTL_SECONDS == 300

    def test_valid_approval_passes(self, tmp_path) -> None:
        a = _issue(None, tmp_path)
        ok, reason = validate_live_approval(a, now_iso=_NOW)
        assert ok is True
        assert reason is None

    def test_expired_approval_blocked(self, tmp_path) -> None:
        a = _issue(None, tmp_path)
        later = (datetime.fromisoformat(_NOW) + timedelta(seconds=301)).isoformat()
        ok, reason = validate_live_approval(a, now_iso=later)
        assert ok is False
        assert reason == BLOCKED_LIVE_PROVIDER_APPROVAL_EXPIRED

    def test_scope_mismatch_blocked(self, tmp_path) -> None:
        a = _issue(None, tmp_path)
        bad = type(a)(
            approval_id=a.approval_id, approval_scope="other_scope",
            provider_name=a.provider_name, provider_mode=a.provider_mode,
            model=a.model, base_url_host=a.base_url_host,
            budget_cap_cents=a.budget_cap_cents, request_cap=a.request_cap,
            token_cap=a.token_cap, output_token_cap=a.output_token_cap,
            tool_allowlist=a.tool_allowlist, expires_at=a.expires_at,
            created_at=a.created_at, approved_by=a.approved_by,
            single_use=a.single_use, used_at=a.used_at, redaction_applied=True,
        )
        ok, reason = validate_live_approval(bad, now_iso=_NOW)
        assert ok is False
        assert reason == BLOCKED_LIVE_PROVIDER_APPROVAL_SCOPE_INVALID


class TestSingleUse:
    def test_used_approval_blocked(self, tmp_path) -> None:
        hermes_home = str(tmp_path / "dev-home")
        a = _issue(None, tmp_path)
        assert mark_approval_used(a.approval_id, hermes_home=hermes_home, now_iso=_NOW) is True
        used = find_active_approval(a.approval_id, hermes_home=hermes_home)
        assert used is not None
        assert used.used_at != ""
        ok, reason = validate_live_approval(used, now_iso=_NOW)
        assert ok is False
        assert reason == BLOCKED_LIVE_PROVIDER_APPROVAL_USED

    def test_mark_used_twice_is_noop(self, tmp_path) -> None:
        hermes_home = str(tmp_path / "dev-home")
        a = _issue(None, tmp_path)
        assert mark_approval_used(a.approval_id, hermes_home=hermes_home, now_iso=_NOW) is True
        # Second call on an already-used single-use approval is a no-op.
        assert mark_approval_used(a.approval_id, hermes_home=hermes_home, now_iso=_NOW) is False

    def test_revoke_all_clears_store(self, tmp_path) -> None:
        hermes_home = str(tmp_path / "dev-home")
        _issue(None, tmp_path)
        assert revoke_all_approvals(hermes_home=hermes_home) is True
        assert list_approvals(hermes_home=hermes_home) == []


class TestMatch:
    def test_matching_request_passes(self, tmp_path) -> None:
        a = _issue(None, tmp_path)
        ok, reason = match_live_approval(
            a, provider_name="openai_compatible", model="gpt-4o-mini",
            base_url_host="api.openai.com",
            tool_allowlist=frozenset({"route_governance_read"}),
        )
        assert ok is True
        assert reason is None

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"provider_name": "anthropic_compatible"},
            {"model": "gpt-4o"},
            {"base_url_host": "api.z.ai"},
            {"tool_allowlist": frozenset({"definitely_not_in_approval"})},
        ],
    )
    def test_mismatch_blocked(self, tmp_path, kwargs) -> None:
        a = _issue(None, tmp_path)
        base = dict(
            provider_name="openai_compatible", model="gpt-4o-mini",
            base_url_host="api.openai.com",
            tool_allowlist=frozenset({"route_governance_read"}),
        )
        base.update(kwargs)
        ok, reason = match_live_approval(a, **base)
        assert ok is False
        assert reason == BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH


class TestDevOnlyStore:
    def test_production_home_rejected(self, tmp_path) -> None:
        a = issue_live_approval(
            provider_name="openai_compatible", model="gpt-4o-mini",
            base_url_host="api.openai.com", budget_cap_cents=5, request_cap=1,
            token_cap=1000, output_token_cap=200,
            tool_allowlist=frozenset({"route_governance_read"}),
            hermes_home="/Users/huangruibang/.hermes", now_iso=_NOW,
        )
        assert a is None  # fail closed; no approval granted on the prod home

    def test_no_real_key_in_approval_payload(self, tmp_path) -> None:
        a = _issue(None, tmp_path)
        blob = json.dumps(a.to_safe_dict())
        assert "sk-" not in blob
        assert "Bearer" not in blob
        assert "Authorization" not in blob
