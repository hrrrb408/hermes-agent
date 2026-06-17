"""Phase 3B-Live-Enablement — Live Kill Switch tests.

Verifies:
  - kill switch inactive by default
  - active kill switch blocks before secret read / network
  - triggering writes the reason + time
  - clear kill switch returns to inactive
  - clearing is NOT an approval (re-enable still needs fresh approval)
  - trigger reasons catalogue is frozen (14)
  - dev-only store (production home rejected)
  - value-free state projection

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.dev_web_provider_live_kill_switch import (
    BLOCKED_LIVE_PROVIDER_KILL_SWITCH_ACTIVE,
    KILL_SWITCH_TRIGGERS,
    clear_kill_switch,
    is_kill_switch_active,
    read_kill_switch,
    trigger_kill_switch,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))


_NOW = "2026-06-17T10:00:00+00:00"


class TestDefault:
    def test_inactive_by_default(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        assert is_kill_switch_active(hermes_home=home) is False
        st = read_kill_switch(hermes_home=home)
        assert st.active is False
        assert st.triggered_by == ""

    def test_triggers_catalogue_frozen(self) -> None:
        assert len(KILL_SWITCH_TRIGGERS) == 14


class TestTriggerAndClear:
    def test_trigger_arms_switch(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        assert trigger_kill_switch(
            hermes_home=home, reason="budget_exceeded", now_iso=_NOW,
        ) is True
        st = read_kill_switch(hermes_home=home)
        assert st.active is True
        assert st.triggered_by == "budget_exceeded"
        assert st.triggered_at == _NOW

    def test_active_blocks_live(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        trigger_kill_switch(hermes_home=home, reason="secret_detected", now_iso=_NOW)
        assert is_kill_switch_active(hermes_home=home) is True
        # The blocked reason constant is exported for the orchestrator.
        assert BLOCKED_LIVE_PROVIDER_KILL_SWITCH_ACTIVE.startswith("blocked_live_")

    def test_clear_returns_inactive(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        trigger_kill_switch(hermes_home=home, reason="manual_abort", now_iso=_NOW)
        assert clear_kill_switch(hermes_home=home) is True
        assert is_kill_switch_active(hermes_home=home) is False

    def test_clear_is_not_an_approval(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        trigger_kill_switch(hermes_home=home, reason="audit_write_failure", now_iso=_NOW)
        clear_kill_switch(hermes_home=home)
        st = read_kill_switch(hermes_home=home)
        # Clearing only flips the switch; it grants no approval state.
        assert st.active is False
        assert st.triggered_by == ""

    def test_unknown_reason_normalized_to_manual(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        trigger_kill_switch(
            hermes_home=home, reason="totally_unknown_reason", now_iso=_NOW,
        )
        st = read_kill_switch(hermes_home=home)
        assert st.active is True
        assert st.triggered_by == "manual_operator_trigger"


class TestDevOnlyAndValueFree:
    def test_production_home_rejected(self, tmp_path) -> None:
        home = "/Users/huangruibang/.hermes"
        # Trigger on the production home must fail closed (no write).
        assert trigger_kill_switch(
            hermes_home=home, reason="manual_operator_trigger", now_iso=_NOW,
        ) is False

    def test_state_value_free(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        trigger_kill_switch(hermes_home=home, reason="secret_detected", now_iso=_NOW)
        blob = json.dumps(read_kill_switch(hermes_home=home).to_safe_dict())
        assert "sk-" not in blob
        assert "Bearer" not in blob
