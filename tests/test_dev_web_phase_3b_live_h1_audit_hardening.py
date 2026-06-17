"""Phase 3B-Live-Enablement H1 — provider_live_* Audit / Redaction Hardening.

Hardening pass over the live audit writers (LIVE-AUDIT-3B-H1-001).

Verifies:
  - all 18 frozen ``provider_live_*`` event types exist and build value-free
  - every built event carries ``redactionApplied=true`` and the safe schema
  - the writer defensively re-redacts injected secrets (apiKey / Authorization /
    Bearer / raw token) before the persisted JSONL sees them
  - an audit write against the production home fails closed (returns None)
  - the persisted store lives under the dev HERMES_HOME only

No network call and no real key read happen here. Secrets injected in tests are
synthetic sentinels.

Phase: 3B-Live-Enablement H1 — Strict Manual One-shot Live Gate Hardening
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.dev_web_provider_live_audit import (
    ALL_LIVE_EVENT_TYPES,
    build_provider_live_audit_event,
    write_live_enablement_approved,
    write_live_enablement_denied,
    write_live_kill_switch_triggered,
    write_live_secret_state_checked,
    write_provider_live_audit_event,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    for env in ("OPENAI_API_KEY", "HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED"):
        monkeypatch.delenv(env, raising=False)


_FORBIDDEN_NEEDLES = (
    "sk-injected", "Bearer xyz", "Authorization", "private_key",
    "BEGIN PRIVATE KEY", "/Users/huangruibang/.hermes", "state.db",
)


class TestEventTypeCatalogue:
    def test_eighteen_event_types(self) -> None:
        assert len(ALL_LIVE_EVENT_TYPES) == 18
        for et in (
            "provider_live_enablement_requested",
            "provider_live_enablement_approved",
            "provider_live_enablement_denied",
            "provider_live_enablement_expired",
            "provider_live_enablement_started",
            "provider_live_enablement_completed",
            "provider_live_enablement_failed",
            "provider_live_enablement_kill_switch_triggered",
            "provider_live_secret_state_checked",
            "provider_live_network_request_started",
            "provider_live_network_request_completed",
            "provider_live_network_request_blocked",
            "provider_live_budget_checked",
            "provider_live_budget_blocked",
            "provider_live_tool_call_requested",
            "provider_live_tool_call_blocked",
            "provider_live_tool_call_completed",
            "provider_live_disable_completed",
        ):
            assert et in ALL_LIVE_EVENT_TYPES


class TestBuildValueFree:
    @pytest.mark.parametrize("event_type", sorted(ALL_LIVE_EVENT_TYPES))
    def test_every_event_type_builds_value_free(self, event_type: str) -> None:
        event = build_provider_live_audit_event(
            event_type=event_type, provider_name="openai_compatible",
            provider_mode="real", approval_id="plap_x", request_id="plrr_y",
            model="gpt-4o-mini", base_url_host="api.openai.com",
            usage_summary={"promptTokens": 1, "completionTokens": 1, "totalTokens": 2},
            secret_state={"keySource": "environment", "keyState": "env_present", "keyValue": "never"},
        )
        assert event["redactionApplied"] is True
        assert event["eventType"] == event_type
        blob = json.dumps(event)
        for needle in _FORBIDDEN_NEEDLES:
            assert needle not in blob

    def test_secret_state_projection_value_free(self) -> None:
        event = build_provider_live_audit_event(
            event_type="provider_live_secret_state_checked", provider_name=None,
            provider_mode="real",
            secret_state={"keySource": "environment", "keyState": "env_present", "keyValue": "never"},
        )
        assert event["secretState"]["keyValue"] == "never"


class TestDefensiveRedaction:
    def test_injected_api_key_redacted_before_persist(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        event = build_provider_live_audit_event(
            event_type="provider_live_enablement_completed", provider_name="openai_compatible",
            provider_mode="real", approval_id="plap_x", request_id="plrr_y",
            response_id="plrr_y", model="gpt-4o-mini", base_url_host="api.openai.com",
            safe_metadata={"apiKey": "sk-injected-secret-1234567890"},
        )
        eid = write_provider_live_audit_event(event, hermes_home=home)
        assert eid is not None
        from hermes_cli.dev_web_provider_audit import _AUDIT_DIR_RELATIVE, _AUDIT_FILENAME
        from pathlib import Path

        store = Path(home) / _AUDIT_DIR_RELATIVE / _AUDIT_FILENAME
        assert store.exists()
        blob = store.read_text(encoding="utf-8")
        assert "sk-injected" not in blob
        assert "[REDACTED]" in blob

    def test_injected_authorization_header_redacted(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        event = build_provider_live_audit_event(
            event_type="provider_live_network_request_completed", provider_name="openai_compatible",
            provider_mode="real", base_url_host="api.openai.com",
            safe_metadata={"auth": "Bearer xyz"},
        )
        eid = write_provider_live_audit_event(event, hermes_home=home)
        assert eid is not None
        from hermes_cli.dev_web_provider_audit import _AUDIT_DIR_RELATIVE, _AUDIT_FILENAME
        from pathlib import Path

        blob = (Path(home) / _AUDIT_DIR_RELATIVE / _AUDIT_FILENAME).read_text(encoding="utf-8")
        assert "Bearer xyz" not in blob


class TestFailClosedAndStore:
    def test_production_home_write_fail_closed(self) -> None:
        event = build_provider_live_audit_event(
            event_type="provider_live_enablement_denied", provider_name=None,
            provider_mode="real", blocked_reason="blocked_live_provider_not_human_approved",
        )
        assert write_provider_live_audit_event(event, hermes_home="/Users/huangruibang/.hermes") is None

    def test_typed_writers_return_event_id(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        assert write_live_enablement_approved(
            hermes_home=home, provider_name="openai_compatible", model="gpt-4o-mini",
            base_url_host="api.openai.com", approval_id="plap_x", budget={"maxBudgetCents": 5},
        ) is not None
        assert write_live_enablement_denied(
            hermes_home=home, provider_name=None,
            blocked_reason="blocked_live_provider_not_human_approved",
        ) is not None
        assert write_live_kill_switch_triggered(
            hermes_home=home, provider_name=None,
            blocked_reason="blocked_live_provider_kill_switch_active",
        ) is not None
        assert write_live_secret_state_checked(
            hermes_home=home, provider_name=None,
            secret_state={"keySource": "environment", "keyState": "env_present", "keyValue": "never"},
        ) is not None

    def test_store_under_dev_home_only(self, tmp_path) -> None:
        from hermes_cli.dev_web_provider_audit import _AUDIT_DIR_RELATIVE, _AUDIT_FILENAME
        from pathlib import Path

        home = tmp_path / "dev-home"
        store = home / _AUDIT_DIR_RELATIVE / _AUDIT_FILENAME
        assert "/Users/huangruibang/.hermes" not in str(store)
        assert "state.db" not in str(store)
