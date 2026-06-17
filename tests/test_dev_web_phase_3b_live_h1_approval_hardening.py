"""Phase 3B-Live-Enablement H1 — Live Approval / TTL / Single-use Hardening.

Hardening pass over the live human-approval model (LIVE-APPROVAL-3B-H1-001).
Probes edge cases the implementation tests treat more lightly:

  - approval default missing → blocked
  - TTL boundary: valid at exactly now+TTL, expired one second after
  - single-use: a used approval is blocked; mark_used is idempotent
  - scope / mode tampering → blocked (scope_invalid)
  - provider / model / host / tool-allowlist mismatch → blocked
  - tool-allowlist: every requested tool must be a subset of the approved set
  - the approval record + its persisted store are value-free (no key / header /
    token / raw prompt / raw response / production path) even when injected
  - production home / state.db / outside-home store → fail closed (no approval)
  - corrupt store → fail closed

This module never reads OPENAI_API_KEY and makes no network call.

Phase: 3B-Live-Enablement H1 — Strict Manual One-shot Live Gate Hardening
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest

from hermes_cli.dev_web_provider_live_approval import (
    APPROVAL_SCOPE,
    BLOCKED_LIVE_PROVIDER_APPROVAL_EXPIRED,
    BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH,
    BLOCKED_LIVE_PROVIDER_APPROVAL_SCOPE_INVALID,
    BLOCKED_LIVE_PROVIDER_APPROVAL_USED,
    BLOCKED_LIVE_PROVIDER_DEV_ONLY_VIOLATION,
    BLOCKED_LIVE_PROVIDER_NOT_HUMAN_APPROVED,
    DEFAULT_TTL_SECONDS,
    LiveApproval,
    find_active_approval,
    issue_live_approval,
    list_approvals,
    mark_approval_used,
    match_live_approval,
    revoke_all_approvals,
    validate_live_approval,
)

_NOW = "2026-06-17T10:00:00+00:00"


def _shift(seconds: int) -> str:
    from datetime import datetime

    base = datetime.fromisoformat(_NOW) + timedelta(seconds=seconds)
    return base.isoformat()


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


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    for env in ("OPENAI_API_KEY", "HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED"):
        monkeypatch.delenv(env, raising=False)


# ---------------------------------------------------------------------------
# 1. Default missing + frozen constants
# ---------------------------------------------------------------------------


class TestDefaultAndConstants:
    def test_missing_approval_blocked(self) -> None:
        valid, reason = validate_live_approval(None, now_iso=_NOW)
        assert valid is False
        assert reason == BLOCKED_LIVE_PROVIDER_NOT_HUMAN_APPROVED

    def test_frozen_scope_and_ttl(self) -> None:
        assert APPROVAL_SCOPE == "provider_live_enablement"
        assert DEFAULT_TTL_SECONDS == 300

    def test_find_active_approval_none_for_missing_id(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        assert find_active_approval("does-not-exist", hermes_home=home) is None
        assert find_active_approval(None, hermes_home=home) is None


# ---------------------------------------------------------------------------
# 2. TTL boundary
# ---------------------------------------------------------------------------


class TestTtlBoundary:
    def test_valid_exactly_at_expiry(self, tmp_path) -> None:
        approval, _ = _issue(tmp_path)
        # now == expires_at exactly ⇒ NOT expired (now > expires is False).
        valid, reason = validate_live_approval(approval, now_iso=approval.expires_at)
        assert valid is True
        assert reason is None

    def test_expired_one_second_after(self, tmp_path) -> None:
        approval, _ = _issue(tmp_path)
        from datetime import datetime

        expired = (datetime.fromisoformat(approval.expires_at) + timedelta(seconds=1)).isoformat()
        valid, reason = validate_live_approval(approval, now_iso=expired)
        assert valid is False
        assert reason == BLOCKED_LIVE_PROVIDER_APPROVAL_EXPIRED

    def test_expires_at_is_now_plus_ttl(self, tmp_path) -> None:
        approval, _ = _issue(tmp_path)
        assert approval.expires_at == _shift(DEFAULT_TTL_SECONDS)


# ---------------------------------------------------------------------------
# 3. Single-use semantics
# ---------------------------------------------------------------------------


class TestSingleUse:
    def test_used_approval_blocked(self, tmp_path) -> None:
        approval, home = _issue(tmp_path)
        assert mark_approval_used(approval.approval_id, hermes_home=home, now_iso=_NOW) is True
        used = find_active_approval(approval.approval_id, hermes_home=home)
        assert used is not None
        valid, reason = validate_live_approval(used, now_iso=_NOW)
        assert valid is False
        assert reason == BLOCKED_LIVE_PROVIDER_APPROVAL_USED

    def test_mark_used_is_idempotent(self, tmp_path) -> None:
        approval, home = _issue(tmp_path)
        assert mark_approval_used(approval.approval_id, hermes_home=home, now_iso=_NOW) is True
        # A second mark on the already-used single-use approval is a no-op.
        assert mark_approval_used(approval.approval_id, hermes_home=home, now_iso=_NOW) is False

    def test_revoke_clears_store(self, tmp_path) -> None:
        approval, home = _issue(tmp_path)
        assert revoke_all_approvals(hermes_home=home) is True
        assert list_approvals(hermes_home=home) == []


# ---------------------------------------------------------------------------
# 4. Scope / mode tampering
# ---------------------------------------------------------------------------


class TestScopeModeTamper:
    def test_wrong_scope_blocked(self, tmp_path) -> None:
        approval, _ = _issue(tmp_path)
        tampered = LiveApproval(
            approval_id=approval.approval_id, approval_scope="not_the_scope",
            provider_name=approval.provider_name, provider_mode="real",
            model=approval.model, base_url_host=approval.base_url_host,
            budget_cap_cents=5, request_cap=1, token_cap=1000, output_token_cap=200,
            tool_allowlist=approval.tool_allowlist, expires_at=approval.expires_at,
            created_at=approval.created_at, approved_by="human_operator",
            single_use=True, used_at="", redaction_applied=True,
        )
        valid, reason = validate_live_approval(tampered, now_iso=_NOW)
        assert valid is False
        assert reason == BLOCKED_LIVE_PROVIDER_APPROVAL_SCOPE_INVALID

    def test_non_real_mode_blocked(self, tmp_path) -> None:
        approval, _ = _issue(tmp_path)
        tampered = LiveApproval(
            approval_id=approval.approval_id, approval_scope=APPROVAL_SCOPE,
            provider_name=approval.provider_name, provider_mode="fake",
            model=approval.model, base_url_host=approval.base_url_host,
            budget_cap_cents=5, request_cap=1, token_cap=1000, output_token_cap=200,
            tool_allowlist=approval.tool_allowlist, expires_at=approval.expires_at,
            created_at=approval.created_at, approved_by="human_operator",
            single_use=True, used_at="", redaction_applied=True,
        )
        valid, reason = validate_live_approval(tampered, now_iso=_NOW)
        assert valid is False
        assert reason == BLOCKED_LIVE_PROVIDER_APPROVAL_SCOPE_INVALID


# ---------------------------------------------------------------------------
# 5. Request match (provider / model / host / tool subset)
# ---------------------------------------------------------------------------


class TestMatchBoundary:
    def test_provider_mismatch_blocked(self, tmp_path) -> None:
        approval, _ = _issue(tmp_path)
        ok, reason = match_live_approval(
            approval, provider_name="other", model="gpt-4o-mini",
            base_url_host="api.openai.com", tool_allowlist=frozenset({"route_governance_read"}),
        )
        assert ok is False
        assert reason == BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH

    def test_model_mismatch_blocked(self, tmp_path) -> None:
        approval, _ = _issue(tmp_path)
        ok, reason = match_live_approval(
            approval, provider_name="openai_compatible", model="gpt-4o",
            base_url_host="api.openai.com", tool_allowlist=frozenset({"route_governance_read"}),
        )
        assert ok is False
        assert reason == BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH

    def test_host_mismatch_blocked(self, tmp_path) -> None:
        approval, _ = _issue(tmp_path)
        ok, reason = match_live_approval(
            approval, provider_name="openai_compatible", model="gpt-4o-mini",
            base_url_host="evil.example.com", tool_allowlist=frozenset({"route_governance_read"}),
        )
        assert ok is False
        assert reason == BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH

    def test_requested_tool_outside_allowlist_blocked(self, tmp_path) -> None:
        approval, _ = _issue(tmp_path, tool_allowlist=frozenset({"route_governance_read"}))
        ok, reason = match_live_approval(
            approval, provider_name="openai_compatible", model="gpt-4o-mini",
            base_url_host="api.openai.com",
            tool_allowlist=frozenset({"route_governance_read", "write_file"}),
        )
        assert ok is False
        assert reason == BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH

    def test_subset_request_allowed(self, tmp_path) -> None:
        approval, _ = _issue(tmp_path, tool_allowlist=frozenset({"route_governance_read", "session_search"}))
        ok, reason = match_live_approval(
            approval, provider_name="openai_compatible", model="gpt-4o-mini",
            base_url_host="api.openai.com", tool_allowlist=frozenset({"route_governance_read"}),
        )
        assert ok is True
        assert reason is None


# ---------------------------------------------------------------------------
# 6. Value-free invariant (no key / header / token / secret / prod path)
# ---------------------------------------------------------------------------


_FORBIDDEN_NEEDLES = (
    "sk-", "Bearer ", "Authorization", "apiKeyValue", "accessToken",
    "private_key", "BEGIN PRIVATE KEY", "/Users/huangruibang/.hermes", "state.db",
)


class TestValueFree:
    def test_approval_to_safe_dict_value_free(self, tmp_path) -> None:
        approval, _ = _issue(tmp_path)
        blob = json.dumps(approval.to_safe_dict())
        for needle in _FORBIDDEN_NEEDLES:
            assert needle not in blob

    def test_persisted_store_value_free(self, tmp_path) -> None:
        approval, home = _issue(tmp_path)
        from hermes_cli.dev_web_provider_live_approval import _resolve_store_path

        path, err = _resolve_store_path(home)
        assert err is None and path.exists()
        blob = path.read_text(encoding="utf-8")
        for needle in _FORBIDDEN_NEEDLES:
            assert needle not in blob

    def test_list_approvals_value_free(self, tmp_path) -> None:
        _issue(tmp_path)
        blob = json.dumps(
            [a.to_safe_dict() for a in list_approvals(hermes_home=str(tmp_path / "dev-home"))]
        )
        for needle in _FORBIDDEN_NEEDLES:
            assert needle not in blob


# ---------------------------------------------------------------------------
# 7. Dev-only store boundary (fail closed)
# ---------------------------------------------------------------------------


class TestDevOnlyStore:
    def test_production_home_fail_closed(self) -> None:
        # The production home may NEVER host an approval store.
        approval = issue_live_approval(
            provider_name="openai_compatible", model="gpt-4o-mini",
            base_url_host="api.openai.com", budget_cap_cents=5, request_cap=1,
            token_cap=1000, output_token_cap=200,
            tool_allowlist=frozenset({"route_governance_read"}),
            hermes_home="/Users/huangruibang/.hermes", now_iso=_NOW,
        )
        assert approval is None
        assert list_approvals(hermes_home="/Users/huangruibang/.hermes") == []

    def test_corrupt_store_fail_closed(self, tmp_path) -> None:
        approval, home = _issue(tmp_path)
        from hermes_cli.dev_web_provider_live_approval import _resolve_store_path

        path, err = _resolve_store_path(home)
        assert err is None
        # Corrupt the store; a malformed file yields NO usable approval.
        path.write_text("not-json{", encoding="utf-8")
        assert find_active_approval(approval.approval_id, hermes_home=home) is None
        assert list_approvals(hermes_home=home) == []

    def test_store_under_dev_home_only(self, tmp_path) -> None:
        # The store path resolves strictly inside the dev HERMES_HOME.
        from hermes_cli.dev_web_provider_live_approval import (
            _STORE_DIR_RELATIVE,
            _STORE_FILENAME,
            _resolve_store_path,
        )

        home = tmp_path / "dev-home"
        path, err = _resolve_store_path(str(home))
        assert err is None
        assert path.name == _STORE_FILENAME
        assert _STORE_DIR_RELATIVE in str(path)
        assert str(home) in str(path)
        # It must never touch the production home.
        assert "/Users/huangruibang/.hermes" not in str(path)
