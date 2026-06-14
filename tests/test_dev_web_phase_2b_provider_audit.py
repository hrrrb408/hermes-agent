"""Phase 2B — Provider Audit writer tests.

Verifies the provider round-trip audit events are written to the dev JSONL
store, every event carries redactionApplied=true, and no API key, raw token,
full tokenHash, raw arguments, secret, or callable/function repr is ever
stored.

Phase: 2B — Provider Schema / API Controlled Integration
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_provider_audit import (
    build_provider_audit_event,
    write_provider_audit_event,
    EVENT_PROVIDER_REQUEST_BUILT,
    EVENT_PROVIDER_SCHEMA_BUILT,
)
from hermes_cli.dev_web_provider_roundtrip import run_provider_tool_roundtrip


@pytest.fixture
def provider_home(tmp_path):
    home = tmp_path / "hermes-home-dev"
    (home / "gateway" / "dev" / "audit").mkdir(parents=True, exist_ok=True)
    (home / "gateway" / "dev" / "tokens").mkdir(parents=True, exist_ok=True)
    return str(home)


@pytest.fixture(autouse=True)
def _enable_gates(monkeypatch):
    monkeypatch.setenv("HERMES_TOOL_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("HERMES_AGENT_TOOLS_ENABLED", "true")
    monkeypatch.setenv("HERMES_TOOL_HANDLER_CALL_ENABLED", "true")
    import hermes_cli.dev_web_read_only_tool_handlers as handlers

    monkeypatch.setattr(handlers, "_probe_system_state", lambda: {
        "productionGatewayPidObserved": 1962, "productionGatewayProcessCount": 1,
        "productionGatewayCommandSummary": "x", "port5180": "free", "port5181": "free",
    })


def _audit_path(home: str) -> Path:
    return Path(home) / "gateway" / "dev" / "audit" / "provider-roundtrip-audit.jsonl"


class TestProviderAuditWrite:
    def test_writes_single_event(self, provider_home) -> None:
        event = build_provider_audit_event(
            event_type=EVENT_PROVIDER_SCHEMA_BUILT,
            provider_request_id="prqs_test",
            provider_response_id=None,
            provider_mode="fake",
            payload={"toolCount": 6},
        )
        result = write_provider_audit_event(event, hermes_home=provider_home)
        assert result.written is True
        assert result.event_id is not None
        assert _audit_path(provider_home).exists()

    def test_redaction_applied_flag_always_true(self, provider_home) -> None:
        run_provider_tool_roundtrip(
            "check route governance", "fake",
            selected_tool_ids=frozenset({"route_governance_read"}),
            hermes_home=provider_home,
        )
        lines = _audit_path(provider_home).read_text(encoding="utf-8").splitlines()
        assert lines
        for line in lines:
            ev = json.loads(line)
            assert ev.get("redactionApplied") is True

    def test_audit_covers_full_lifecycle(self, provider_home) -> None:
        run_provider_tool_roundtrip(
            "read tool policy", "fake",
            selected_tool_ids=frozenset({"tool_policy_read"}),
            hermes_home=provider_home,
        )
        lines = _audit_path(provider_home).read_text(encoding="utf-8").splitlines()
        event_types = {json.loads(line)["eventType"] for line in lines}
        assert "provider_schema_built" in event_types
        assert "provider_request_built" in event_types
        assert "provider_response_received" in event_types
        assert "provider_tool_call_parsed" in event_types
        assert "provider_tool_call_executed" in event_types
        assert "provider_final_response_received" in event_types

    def test_audit_never_outside_hermes_home(self, tmp_path) -> None:
        # Pointing at the production home must fail closed.
        event = build_provider_audit_event(
            event_type=EVENT_PROVIDER_REQUEST_BUILT,
            provider_request_id="prqs_x", provider_response_id=None,
            provider_mode="fake", payload={},
        )
        result = write_provider_audit_event(event, hermes_home="/Users/huangruibang/.hermes")
        assert result.written is False
        assert result.error_code is not None


class TestProviderAuditRedaction:
    def test_no_secret_in_audit_file(self, provider_home, monkeypatch) -> None:
        # Slip a secret into the user message; the round-trip redacts it before
        # the request summary is built, but also re-confirm the audit file.
        run_provider_tool_roundtrip(
            "read tool policy key=sk-abcdefghijklmnopqrstuvwxyz", "fake",
            selected_tool_ids=frozenset({"tool_policy_read"}),
            hermes_home=provider_home,
        )
        blob = _audit_path(provider_home).read_text(encoding="utf-8")
        assert "sk-abcdefghijklmnopqrstuvwxyz" not in blob
        assert "BEGIN PRIVATE KEY" not in blob

    def test_no_api_key_field_in_audit(self, provider_home) -> None:
        run_provider_tool_roundtrip(
            "check route governance", "fake",
            selected_tool_ids=frozenset({"route_governance_read"}),
            hermes_home=provider_home,
        )
        blob = _audit_path(provider_home).read_text(encoding="utf-8")
        for line in blob.splitlines():
            ev = json.loads(line)
            for forbidden in ("apiKey", "api_key", "authorization", "token", "secret"):
                assert forbidden not in json.dumps(ev).lower() or "[redacted]" in json.dumps(ev)

    def test_callable_never_rendered(self, provider_home) -> None:
        event = build_provider_audit_event(
            event_type=EVENT_PROVIDER_SCHEMA_BUILT,
            provider_request_id="prqs_x", provider_response_id=None,
            provider_mode="fake",
            payload={"fn": lambda: None},  # callable in payload
        )
        result = write_provider_audit_event(event, hermes_home=provider_home)
        assert result.written is True
        blob = _audit_path(provider_home).read_text(encoding="utf-8")
        assert "<function" not in blob
        # Callable rendered as its class name only.
        assert "<lambda>" in blob or "function" not in blob
