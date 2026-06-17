"""Phase 3B-Live-Enablement H1 — Kill Switch / Disable / Re-enable Hardening.

Hardening pass over the live kill switch (LIVE-KILL-3B-H1-001).

Verifies: inactive by default; the 14 frozen triggers; unknown-reason
normalization; an active switch blocks (reported via the boundary, not here);
clearing the switch is NOT an approval (the switch only arms/disarms); a corrupt
store defaults to inactive (fail-open on read, still gated by the other layers);
and the store is dev-only (never ~/.hermes, never state.db, never committed).

No network call and no real key read happen here.

Phase: 3B-Live-Enablement H1 — Strict Manual One-shot Live Gate Hardening
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.dev_web_provider_live_kill_switch import (
    KILL_SWITCH_TRIGGER_MANUAL,
    KILL_SWITCH_TRIGGERS,
    clear_kill_switch,
    is_kill_switch_active,
    read_kill_switch,
    trigger_kill_switch,
)

_NOW = "2026-06-17T10:00:00+00:00"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    for env in ("OPENAI_API_KEY", "HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED"):
        monkeypatch.delenv(env, raising=False)


class TestDefault:
    def test_inactive_by_default(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        assert read_kill_switch(hermes_home=home).active is False
        assert is_kill_switch_active(hermes_home=home) is False

    def test_fourteen_triggers(self) -> None:
        assert len(KILL_SWITCH_TRIGGERS) == 14
        for t in (
            "manual_operator_trigger", "budget_exceeded", "rate_limit_exceeded",
            "secret_detected", "response_too_large", "malformed_unsafe_response",
            "off_allowlist_redirect", "route_governance_drift",
            "production_gateway_pid_drift", "audit_write_failure",
            "unexpected_provider_tool_call", "provider_write_autonomous_suggestion",
            "smoke_failure", "manual_abort",
        ):
            assert t in KILL_SWITCH_TRIGGERS


class TestTriggerAndNormalize:
    def test_trigger_arms_switch(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        assert trigger_kill_switch(hermes_home=home, reason="secret_detected", now_iso=_NOW) is True
        st = read_kill_switch(hermes_home=home)
        assert st.active is True
        assert st.triggered_by == "secret_detected"
        assert st.triggered_at == _NOW

    def test_unknown_reason_normalized_to_manual(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        assert trigger_kill_switch(hermes_home=home, reason="bogus", now_iso=_NOW) is True
        assert read_kill_switch(hermes_home=home).triggered_by == KILL_SWITCH_TRIGGER_MANUAL

    def test_state_value_free(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        trigger_kill_switch(hermes_home=home, reason="secret_detected", now_iso=_NOW)
        blob = json.dumps(read_kill_switch(hermes_home=home).to_safe_dict())
        for needle in ("sk-", "Bearer ", "Authorization", "/Users/huangruibang/.hermes", "state.db"):
            assert needle not in blob


class TestClearNotApproval:
    def test_clear_disarms_switch(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        trigger_kill_switch(hermes_home=home, reason="manual_operator_trigger", now_iso=_NOW)
        assert clear_kill_switch(hermes_home=home) is True
        st = read_kill_switch(hermes_home=home)
        assert st.active is False
        assert st.triggered_by == ""
        assert st.triggered_at == ""

    def test_clear_does_not_grant_approval(self, tmp_path) -> None:
        # The kill switch module has no notion of "approval" — clearing only
        # disarms. Re-enabling a live request still needs a fresh approval from
        # the approval module. Here we assert clearing leaves no armed state and
        # no approval is implicit.
        home = str(tmp_path / "dev-home")
        trigger_kill_switch(hermes_home=home, reason="budget_exceeded", now_iso=_NOW)
        clear_kill_switch(hermes_home=home)
        from hermes_cli.dev_web_provider_live_approval import list_approvals

        assert is_kill_switch_active(hermes_home=home) is False
        assert list_approvals(hermes_home=home) == []


class TestFailSafeAndDevOnly:
    def test_corrupt_store_defaults_inactive(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        from hermes_cli.dev_web_provider_live_kill_switch import _resolve_store_path

        path, err = _resolve_store_path(home)
        assert err is None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not-json{", encoding="utf-8")
        # A corrupt read fail-OPENS to inactive (still gated by other layers).
        assert read_kill_switch(hermes_home=home).active is False

    def test_production_home_refused(self) -> None:
        # Triggering against the production home fails closed (returns False).
        assert trigger_kill_switch(
            hermes_home="/Users/huangruibang/.hermes", reason="manual_operator_trigger", now_iso=_NOW,
        ) is False
        assert read_kill_switch(hermes_home="/Users/huangruibang/.hermes").active is False

    def test_store_under_dev_home_only(self, tmp_path) -> None:
        from hermes_cli.dev_web_provider_live_kill_switch import _resolve_store_path

        home = tmp_path / "dev-home"
        path, err = _resolve_store_path(str(home))
        assert err is None
        assert "/Users/huangruibang/.hermes" not in str(path)
        assert "state.db" not in str(path)
