"""Phase 3B-H1 — provider_real_* Audit No-leak HARDENING (Lens 8).

Deterministic, adversarial verification that every provider_real_* audit event:

  - is one of the frozen event types
  - carries the value-free safeMetadata (apiKeySource / apiKeyPresent /
    apiKeySourceDetail / allowlistedBaseUrl(host) / modelName / adapterName)
  - NEVER carries an API key, Authorization header, raw token, full tokenHash,
    raw arguments, raw prompt/response body, callable repr, or production path
  - write failure never enables execution / never leaks

The audit writers are exercised against the dev HERMES_HOME only (temp dir);
~/.hermes and production state.db are never touched.

Phase: 3B-H1 — Provider Boundary Hardening
Provider Audit Security ID: PROVIDER-AUDIT-3B-H1-001
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_provider_config import load_provider_real_config
from hermes_cli.dev_web_provider_real_audit import (
    EVENT_REAL_BUDGET_BLOCKED,
    EVENT_REAL_RATE_LIMIT_BLOCKED,
    EVENT_REAL_REQUEST_BLOCKED,
    EVENT_REAL_REQUEST_COMPLETED,
    EVENT_REAL_REQUEST_FAILED,
    EVENT_REAL_REQUEST_PREVIEWED,
    EVENT_REAL_REQUEST_STARTED,
    EVENT_REAL_RESPONSE_REDACTED,
    EVENT_REAL_TOOL_CALL_BLOCKED,
    EVENT_REAL_TOOL_CALL_COMPLETED,
    EVENT_REAL_TOOL_CALL_REQUESTED,
    build_provider_real_audit_event,
    write_provider_real_audit_event,
)

_FROZEN_EVENTS = {
    EVENT_REAL_REQUEST_PREVIEWED, EVENT_REAL_REQUEST_BLOCKED,
    EVENT_REAL_REQUEST_STARTED, EVENT_REAL_REQUEST_COMPLETED,
    EVENT_REAL_REQUEST_FAILED, EVENT_REAL_RESPONSE_REDACTED,
    EVENT_REAL_TOOL_CALL_REQUESTED, EVENT_REAL_TOOL_CALL_BLOCKED,
    EVENT_REAL_TOOL_CALL_COMPLETED, EVENT_REAL_BUDGET_BLOCKED,
    EVENT_REAL_RATE_LIMIT_BLOCKED,
}

_AUDIT_LEAKS = (
    "sk-", "Bearer ", "Authorization:", "accessToken", "refresh_token",
    "client_secret", "rawPrompt", "rawResponse", "rawArguments", "fullTokenHash",
    "tokenSecret", "plainToken", "fileContent", "/Users/huangruibang/.hermes",
    "state.db", "<function", "<bound method", "object at 0x",
)

_PROVIDER_ENVS = (
    "HERMES_PROVIDER_MODE", "HERMES_PROVIDER_API_ENABLED", "HERMES_PROVIDER_BASE_URL",
    "HERMES_PROVIDER_MODEL",
)
_KEY_ENVS = (
    "HERMES_PROVIDER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY",
    "ZAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "dev-home"))
    for env in _PROVIDER_ENVS:
        monkeypatch.delenv(env, raising=False)
    for env in _KEY_ENVS:
        monkeypatch.delenv(env, raising=False)


def _cfg():
    return load_provider_real_config()


def _audit_path(home: str) -> Path:
    return Path(home) / "gateway" / "dev" / "audit" / "provider-roundtrip-audit.jsonl"


def _read_audit_blob(home: str) -> str:
    path = _audit_path(home)
    assert path.exists(), f"audit file not written: {path}"
    return path.read_text(encoding="utf-8")


# ===========================================================================
# Lens 8 — frozen event catalogue
# ===========================================================================


class TestFrozenEventCatalogue:
    def test_all_eleven_events_exist(self) -> None:
        # The frozen catalogue has exactly 11 provider_real_* event types.
        assert len(_FROZEN_EVENTS) == 11

    def test_every_event_is_prefixed_provider_real(self) -> None:
        for event in _FROZEN_EVENTS:
            assert event.startswith("provider_real_")

    @pytest.mark.parametrize("event", sorted(_FROZEN_EVENTS))
    def test_each_event_can_be_built(self, event: str) -> None:
        ev = build_provider_real_audit_event(
            event_type=event, request_id="preq_abc", response_id="prsp_def",
            provider_name="openai_compatible", provider_mode="real",
        )
        assert ev["eventType"] == event
        assert ev["redactionApplied"] is True


# ===========================================================================
# Lens 8 — event envelope never carries a secret
# ===========================================================================


class TestWrittenEventNoSecret:
    @pytest.mark.parametrize("event", sorted(_FROZEN_EVENTS))
    def test_written_event_no_leak(self, event: str, tmp_path) -> None:
        # The build event is an internal intermediate; the WRITE boundary is
        # where redaction is enforced. Adversarially inject secret carriers and
        # assert the WRITTEN audit line carries none.
        home = str(tmp_path / "dev-home")
        ev = build_provider_real_audit_event(
            event_type=event, request_id="preq_abc", response_id="prsp_def",
            provider_name="openai_compatible", provider_mode="real",
            payload={"api_key": "sk-injectedkey-1234567890", "auth": "Bearer xyz"},
            safe_metadata={"apiKeySource": "env", "apiKeyPresent": True,
                           "apiKeySourceDetail": "env_present"},
        )
        write_provider_real_audit_event(ev, hermes_home=home)
        blob = _read_audit_blob(home)
        for needle in _AUDIT_LEAKS:
            assert needle not in blob, f"{event} leaked {needle}"

    def test_safe_metadata_is_value_free(self) -> None:
        ev = build_provider_real_audit_event(
            event_type=EVENT_REAL_REQUEST_STARTED, request_id="r", response_id=None,
            provider_name="openai_compatible", provider_mode="real",
            safe_metadata={
                "apiKeySource": "env", "apiKeyPresent": True,
                "apiKeySourceDetail": "env_present",
                "allowlistedBaseUrl": "api.openai.com", "modelName": "gpt-4o-mini",
                "adapterName": "openai_compatible", "externalNetworkCalled": True,
            },
        )
        meta = ev["safeMetadata"]
        assert meta["apiKeySource"] == "env"
        assert meta["apiKeySourceDetail"] == "env_present"
        blob = json.dumps(meta)
        for needle in ("sk-", "Bearer ", "Authorization"):
            assert needle not in blob

    def test_non_json_payload_value_collapses_at_write(self, tmp_path) -> None:
        def fn() -> None:  # pragma: no cover
            pass

        home = str(tmp_path / "dev-home")
        ev = build_provider_real_audit_event(
            event_type=EVENT_REAL_REQUEST_PREVIEWED, request_id="r", response_id=None,
            provider_name="openai_compatible", provider_mode="real",
            payload={"handler": fn, "obj": object()},
        )
        write_provider_real_audit_event(ev, hermes_home=home)
        blob = _read_audit_blob(home)
        for needle in ("<function", "<bound method", "object at 0x"):
            assert needle not in blob


# ===========================================================================
# Lens 8 — written audit file never carries a secret
# ===========================================================================


class TestWrittenAuditNoLeak:
    def test_written_event_redacts_secret_payload(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        ev = build_provider_real_audit_event(
            event_type=EVENT_REAL_REQUEST_BLOCKED, request_id="r", response_id=None,
            provider_name="openai_compatible", provider_mode="real",
            blocked_reason="blocked_provider_secret_detected",
            payload={"api_key": "sk-writtenkey-1234567890", "leaked": "Bearer abc.def.ghi"},
        )
        write_provider_real_audit_event(ev, hermes_home=home)
        blob = _read_audit_blob(home)
        assert "sk-writtenkey" not in blob
        assert "abc.def.ghi" not in blob
        assert "[REDACTED]" in blob
        assert "blocked_provider_secret_detected" in blob

    def test_production_home_write_returns_none(self) -> None:
        ev = build_provider_real_audit_event(
            event_type=EVENT_REAL_REQUEST_PREVIEWED, request_id="r", response_id=None,
            provider_name="openai_compatible", provider_mode="real",
        )
        # Writing to ~/.hermes is refused; the result is None and no leak occurs.
        result = write_provider_real_audit_event(ev, hermes_home="/Users/huangruibang/.hermes")
        assert result is None

    def test_every_written_event_carries_redaction_flag(self, tmp_path) -> None:
        home = str(tmp_path / "dev-home")
        for event in sorted(_FROZEN_EVENTS):
            ev = build_provider_real_audit_event(
                event_type=event, request_id="r", response_id="s",
                provider_name="openai_compatible", provider_mode="real",
            )
            write_provider_real_audit_event(ev, hermes_home=home)
        blob = _read_audit_blob(home)
        # Every written line must carry redactionApplied=true and no secret.
        for line in blob.strip().splitlines():
            entry = json.loads(line)
            assert entry["redactionApplied"] is True
            line_blob = json.dumps(entry)
            for needle in _AUDIT_LEAKS:
                assert needle not in line_blob, f"{entry['eventType']} leaked {needle}"
