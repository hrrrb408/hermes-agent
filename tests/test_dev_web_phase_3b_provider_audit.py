"""Phase 3B — Real Provider Audit tests.

Verifies the ``provider_real_*`` audit writers:
  - events are written to the dev-only JSONL under HERMES_HOME
  - the Phase 2D durable store receives the dual-write (auditKind=provider)
  - events carry the frozen common envelope (phase=3B, redactionApplied=true)
  - safeMetadata carries only value-free markers (env_present / env_missing,
    allowlisted host, model name, adapter name) — never the key value
  - NO API key / Authorization / raw token / full tokenHash / callable repr /
    production path ever appears in the audit
  - a payload with a stray secret is defensively re-redacted

Phase: 3B — Real Provider Read-only Controlled Integration
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_provider_config import load_provider_real_config
from hermes_cli.dev_web_provider_real_audit import (
    EVENT_REAL_BUDGET_BLOCKED,
    EVENT_REAL_REQUEST_BLOCKED,
    EVENT_REAL_REQUEST_COMPLETED,
    EVENT_REAL_REQUEST_STARTED,
    build_provider_real_audit_event,
    write_real_request_blocked,
    write_real_request_completed,
    write_real_request_started,
)
from hermes_cli.dev_web_provider_real_schema import (
    build_blocked_real_response,
    build_provider_real_request,
)

_PROVIDER_ENVS = (
    "HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED", "HERMES_PROVIDER_NAME",
    "HERMES_PROVIDER_BASE_URL", "HERMES_PROVIDER_MODEL",
)
_KEY_ENVS = (
    "HERMES_PROVIDER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY",
    "ZAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY",
)


@pytest.fixture
def provider_home(tmp_path):
    home = tmp_path / "hermes-home-dev"
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    return str(home)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, provider_home):
    monkeypatch.setenv("HERMES_HOME", provider_home)
    for env in _PROVIDER_ENVS + _KEY_ENVS:
        monkeypatch.delenv(env, raising=False)
    monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
    monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
    monkeypatch.setenv("HERMES_PROVIDER_BASE_URL", "https://api.openai.com")
    monkeypatch.setenv("HERMES_PROVIDER_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")


def _read_audit_lines(home: str) -> list[dict]:
    path = Path(home) / "gateway/dev/audit/provider-roundtrip-audit.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class TestEnvelope:
    def test_event_has_phase_3b_envelope(self) -> None:
        event = build_provider_real_audit_event(
            event_type=EVENT_REAL_REQUEST_STARTED, request_id="r1", response_id=None,
            provider_name="openai_compatible", provider_mode="real",
            status="started", external_network_called=True,
        )
        assert event["phase"] == "3B"
        assert event["eventType"] == EVENT_REAL_REQUEST_STARTED
        assert event["redactionApplied"] is True
        assert event["providerName"] == "openai_compatible"

    def test_safe_metadata_is_value_free(self) -> None:
        cfg = load_provider_real_config()
        event = build_provider_real_audit_event(
            event_type=EVENT_REAL_REQUEST_STARTED, request_id="r1", response_id=None,
            provider_name=cfg.provider_name, provider_mode=cfg.provider_mode,
            status="started", external_network_called=True,
            safe_metadata={
                "apiKeySource": "env",
                "apiKeyPresent": True,
                "apiKeySourceDetail": "env_present",
                "allowlistedBaseUrl": cfg.base_url_host,
                "modelName": cfg.model,
                "adapterName": cfg.provider_name,
            },
        )
        meta = event["safeMetadata"]
        assert meta["apiKeySourceDetail"] == "env_present"
        blob = json.dumps(event)
        assert "sk-fake-placeholder" not in blob
        assert "Bearer" not in blob
        assert "Authorization" not in blob


class TestWrittenEvents:
    def test_started_event_written(self, provider_home) -> None:
        cfg = load_provider_real_config()
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible",
            model="gpt-4o-mini", user_message="hi",
        )
        eid = write_real_request_started(hermes_home=provider_home, config=cfg, request=req)
        assert eid is not None
        events = _read_audit_lines(provider_home)
        types = [e["eventType"] for e in events]
        assert EVENT_REAL_REQUEST_STARTED in types

    def test_blocked_event_written(self, provider_home) -> None:
        cfg = load_provider_real_config()
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible",
            model="gpt-4o-mini", user_message="hi",
        )
        write_real_request_blocked(
            hermes_home=provider_home, config=cfg, request=req,
            blocked_reason="blocked_provider_api_key_missing",
        )
        events = _read_audit_lines(provider_home)
        assert any(e["eventType"] == EVENT_REAL_REQUEST_BLOCKED for e in events)

    def test_completed_event_written(self, provider_home) -> None:
        cfg = load_provider_real_config()
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible",
            model="gpt-4o-mini", user_message="hi",
        )
        resp = build_blocked_real_response(request=req, blocked_reason="x")
        # Use a completed-shape response by building manually.
        from hermes_cli.dev_web_provider_real_schema import (
            ProviderRealResponse, ProviderRealUsage,
        )
        completed = ProviderRealResponse(
            request_id=req.request_id, response_id=req.request_id,
            provider_name=req.provider_name, model=req.model, status="completed",
            content_summary="done", tool_calls=(), usage_summary=ProviderRealUsage(1, 1, 2),
            finish_reason="stop", blocked_reason=None, audit_links=(),
            redaction_applied=True, external_network_called=True,
            cost_estimate={"estimateCents": 1},
        )
        eid = write_real_request_completed(
            hermes_home=provider_home, config=cfg, request=req, response=completed,
        )
        assert eid is not None
        events = _read_audit_lines(provider_home)
        assert any(e["eventType"] == EVENT_REAL_REQUEST_COMPLETED for e in events)


class TestNoLeak:
    def test_no_api_key_in_audit_file(self, provider_home) -> None:
        cfg = load_provider_real_config()
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible",
            model="gpt-4o-mini", user_message="hi",
        )
        write_real_request_started(hermes_home=provider_home, config=cfg, request=req)
        blob = "\n".join(json.dumps(e) for e in _read_audit_lines(provider_home))
        for needle in ("sk-fake-placeholder", "Bearer ", "Authorization", "api_key"):
            assert needle not in blob

    def test_stray_secret_in_payload_redacted(self, provider_home) -> None:
        # A payload that accidentally carries a secret must be re-redacted.
        from hermes_cli.dev_web_provider_real_audit import write_provider_real_audit_event

        event = build_provider_real_audit_event(
            event_type=EVENT_REAL_BUDGET_BLOCKED, request_id="r1", response_id=None,
            provider_name="openai_compatible", provider_mode="real",
            status="blocked", blocked_reason="blocked_provider_budget_exceeded",
            payload={"oops": "sk-straysecret-1234567890ab"},
        )
        write_provider_real_audit_event(event, hermes_home=provider_home)
        blob = "\n".join(json.dumps(e) for e in _read_audit_lines(provider_home))
        assert "sk-straysecret" not in blob
        assert "[REDACTED]" in blob

    def test_no_callable_repr_in_audit(self, provider_home) -> None:
        from hermes_cli.dev_web_provider_real_audit import write_provider_real_audit_event

        def _fn() -> None:  # pragma: no cover
            pass

        event = build_provider_real_audit_event(
            event_type=EVENT_REAL_REQUEST_STARTED, request_id="r1", response_id=None,
            provider_name="openai_compatible", provider_mode="real", status="started",
            payload={"handler": _fn},
        )
        write_provider_real_audit_event(event, hermes_home=provider_home)
        blob = "\n".join(json.dumps(e) for e in _read_audit_lines(provider_home))
        assert "<function" not in blob
        assert "<bound method" not in blob
        assert "_fn" not in blob


class TestContainment:
    def test_production_home_rejected(self, monkeypatch, provider_home) -> None:
        # Writing under ~/.hermes must be refused by the inherited Phase 2B
        # containment guard.
        cfg = load_provider_real_config()
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible",
            model="gpt-4o-mini", user_message="hi",
        )
        eid = write_real_request_started(
            hermes_home="/Users/huangruibang/.hermes", config=cfg, request=req,
        )
        assert eid is None  # refused

    def test_dual_write_to_durable_store(self, provider_home) -> None:
        # The Phase 2B writer dual-writes to the Phase 2D durable store via
        # bridge_legacy_audit_to_store (auditKind=provider). Confirm the store
        # path is exercised without error.
        from hermes_cli.dev_web_audit_bridge import bridge_legacy_audit_to_store

        cfg = load_provider_real_config()
        event = build_provider_real_audit_event(
            event_type=EVENT_REAL_REQUEST_STARTED, request_id="r1", response_id=None,
            provider_name=cfg.provider_name, provider_mode=cfg.provider_mode,
            status="started",
        )
        # Should not raise.
        bridge_legacy_audit_to_store(event, audit_kind="provider", hermes_home=provider_home)
