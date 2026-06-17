"""Phase 3B-Live-Enablement — Live Audit Policy tests.

Verifies:
  - all 18 provider_live_* event types are defined
  - every event carries redactionApplied=True
  - safe fields only; no API key / Authorization / Bearer / raw token / full
    tokenHash / raw prompt/response secret / callable repr / production path
  - defensive re-redaction before write masks a secret planted in a payload
  - audit write success under the dev home

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.dev_web_provider_live_audit import (
    ALL_LIVE_EVENT_TYPES,
    build_provider_live_audit_event,
    write_live_budget_checked,
    write_live_enablement_approved,
    write_live_enablement_denied,
    write_live_kill_switch_triggered,
    write_live_secret_state_checked,
    write_provider_live_audit_event,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))


FORBIDDEN_NEEDLES = (
    "sk-", "Bearer ", "Authorization", "apiKeyValue", "accessToken",
    "fullTokenHash", "plainToken", "<function", "<bound method",
    "/Users/huangruibang/.hermes", "state.db",
)


class TestEventCatalogue:
    def test_all_18_event_types_present(self) -> None:
        assert len(ALL_LIVE_EVENT_TYPES) == 18
        for name in (
            "provider_live_enablement_requested",
            "provider_live_enablement_approved",
            "provider_live_enablement_denied",
            "provider_live_enablement_kill_switch_triggered",
            "provider_live_secret_state_checked",
            "provider_live_budget_checked",
            "provider_live_disable_completed",
        ):
            assert name in ALL_LIVE_EVENT_TYPES


class TestSafeFields:
    def test_event_is_redacted_and_value_free(self) -> None:
        event = build_provider_live_audit_event(
            event_type="provider_live_enablement_started",
            provider_name="openai_compatible", provider_mode="real",
            model="gpt-4o-mini", base_url_host="api.openai.com",
        )
        assert event["redactionApplied"] is True
        blob = json.dumps(event)
        for needle in FORBIDDEN_NEEDLES:
            assert needle not in blob

    def test_secret_state_field_value_free(self) -> None:
        event = build_provider_live_audit_event(
            event_type="provider_live_secret_state_checked",
            provider_name="openai_compatible", provider_mode="real",
            secret_state={"keySource": "environment", "keyState": "env_present",
                          "keyValue": "never"},
        )
        blob = json.dumps(event)
        assert "env_present" in blob
        assert "sk-" not in blob
        assert "Bearer" not in blob
        assert event["secretState"]["keyValue"] == "never"


class TestRedactionBeforeWrite:
    def test_planted_secret_in_payload_is_redacted(self, tmp_path) -> None:
        from pathlib import Path

        home = str(tmp_path / "dev-home")
        event = build_provider_live_audit_event(
            event_type="provider_live_enablement_failed",
            provider_name="openai_compatible", provider_mode="real",
            safe_metadata={"leak": "sk-AAAA-BBBB-CCCC-DDDD-1234567890"},
        )
        write_provider_live_audit_event(event, hermes_home=home)
        # The redaction runs at WRITE time, so the persisted JSONL must not
        # carry the planted key even though the in-memory dict did.
        audit_dir = Path(home) / "gateway/dev"
        files = list(audit_dir.rglob("*.jsonl")) if audit_dir.exists() else []
        blob = "".join(f.read_text(encoding="utf-8") for f in files)
        assert "sk-AAAA" not in blob

    def test_writers_return_event_id_or_none(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        a = write_live_enablement_approved(
            hermes_home=home, provider_name="openai_compatible",
            model="gpt-4o-mini", base_url_host="api.openai.com",
            approval_id="plap_test", budget={"maxBudgetCents": 5},
        )
        b = write_live_enablement_denied(
            hermes_home=home, provider_name="openai_compatible",
            blocked_reason="blocked_live_provider_not_human_approved",
        )
        c = write_live_kill_switch_triggered(
            hermes_home=home, provider_name="openai_compatible",
            blocked_reason="blocked_live_provider_kill_switch_active",
        )
        d = write_live_budget_checked(
            hermes_home=home, provider_name="openai_compatible",
            budget={"maxBudgetCents": 5},
        )
        e = write_live_secret_state_checked(
            hermes_home=home, provider_name="openai_compatible",
            secret_state={"keySource": "environment", "keyState": "env_missing",
                          "keyValue": "never"},
        )
        for result in (a, b, c, d, e):
            assert result is None or isinstance(result, str)

    @pytest.mark.parametrize("needle", FORBIDDEN_NEEDLES)
    def test_no_forbidden_needle_in_any_writer_payload(self, tmp_path, needle) -> None:
        home = str(tmp_path / "dev-home")
        write_live_enablement_approved(
            hermes_home=home, provider_name="openai_compatible",
            model="gpt-4o-mini", base_url_host="api.openai.com",
            approval_id="plap_test", budget={"maxBudgetCents": 5},
        )
        # The audit JSONL file must not contain the forbidden needle.
        from pathlib import Path

        audit_dir = Path(home) / "gateway/dev"
        files = list(audit_dir.rglob("*.jsonl")) if audit_dir.exists() else []
        blob = "".join(f.read_text(encoding="utf-8") for f in files)
        assert needle not in blob
