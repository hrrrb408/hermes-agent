"""Phase 2B — Provider Request Builder tests.

Verifies disabled / fake / real mode gating, allowedToolIds bounding, and
audit redaction. Real mode is blocked unless fully enabled (and never
auto-enabled in tests).

Phase: 2B — Provider Schema / API Controlled Integration
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_request import (
    BLOCKED_PROVIDER_REAL_MODE_NOT_ENABLED,
    build_provider_request,
    normalize_provider_mode,
    redact_provider_request_for_audit,
    validate_provider_request_boundary,
)
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST


@pytest.fixture(autouse=True)
def _clean_provider_env(monkeypatch):
    # Ensure real mode is never accidentally enabled in these tests.
    for var in (
        "HERMES_PROVIDER_API_ENABLED", "HERMES_PROVIDER_MODE",
        "HERMES_PROVIDER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


class TestProviderRequestModes:
    def test_disabled_mode_sends_no_schema(self) -> None:
        req = build_provider_request("hello", "disabled")
        assert req.provider_mode == "disabled"
        assert req.provider_schema_sent is False
        assert req.provider_api_called is False
        assert req.external_network_called is False
        assert req.tools == ()
        assert req.blocked is False

    def test_fake_mode_sends_schema_and_calls_fake_adapter(self) -> None:
        req = build_provider_request("check route governance", "fake")
        assert req.provider_mode == "fake"
        assert req.provider_schema_sent is True
        assert req.provider_api_called is True
        assert req.external_network_called is False
        assert len(req.tools) == 6
        assert req.fake_model_name is not None
        assert req.model_name is None

    def test_real_mode_blocked_without_enable_env(self) -> None:
        req = build_provider_request("x", "real")
        assert req.provider_mode == "real"
        assert req.blocked is True
        assert req.blocked_reason == BLOCKED_PROVIDER_REAL_MODE_NOT_ENABLED
        assert req.provider_schema_sent is False
        assert req.provider_api_called is False
        assert req.external_network_called is False

    def test_real_mode_blocked_without_api_key(self, monkeypatch) -> None:
        monkeypatch.setenv("HERMES_PROVIDER_API_ENABLED", "1")
        monkeypatch.setenv("HERMES_PROVIDER_MODE", "real")
        monkeypatch.setenv("HERMES_HOME", "/tmp/dev-home")
        # No provider key set → blocked.
        req = build_provider_request("x", "real")
        assert req.blocked is True
        assert req.blocked_reason == "blocked_provider_api_key_missing"

    def test_unknown_mode_normalizes_to_disabled(self) -> None:
        req = build_provider_request("x", "bogus")
        assert req.provider_mode == "disabled"


class TestProviderRequestAllowedTools:
    def test_allowed_tool_ids_bounded_to_allowlist(self) -> None:
        req = build_provider_request(
            "x", "fake",
            allowed_tool_ids=frozenset({"route_governance_read", "write_file"}),
        )
        assert set(req.allowed_tool_ids) == {"route_governance_read"}
        # Schema only carries the allowlisted subset.
        assert {t["name"] for t in req.tools} == {"route_governance_read"}

    def test_allowed_tool_ids_default_full_allowlist(self) -> None:
        req = build_provider_request("x", "fake")
        assert set(req.allowed_tool_ids) == set(STATIC_ALLOWLIST)


class TestProviderRequestBoundaryValidation:
    def test_fake_request_valid(self) -> None:
        req = build_provider_request("check route governance", "fake")
        result = validate_provider_request_boundary(req)
        assert result.valid, result.errors

    def test_normalize_provider_mode(self) -> None:
        assert normalize_provider_mode("FAKE") == "fake"
        assert normalize_provider_mode(None) == "disabled"
        assert normalize_provider_mode(123) == "disabled"  # type: ignore[arg-type]


class TestProviderRequestRedaction:
    def test_redaction_strips_secret_patterns(self, monkeypatch) -> None:
        # Inject a secret-looking message and confirm it is redacted.
        monkeypatch.setenv("HERMES_HOME", "/tmp/dev-home")
        req = build_provider_request("my key is sk-abcdefghijklmnopqrstuvwxyz", "fake")
        audit = redact_provider_request_for_audit(req)
        rendered = repr(audit)
        assert "sk-abcdefghijklmnopqrstuvwxyz" not in rendered
        assert "[REDACTED]" in rendered

    def test_redaction_never_carries_full_message(self) -> None:
        long_msg = "x" * 4000
        req = build_provider_request(long_msg, "fake")
        audit = redact_provider_request_for_audit(req)
        assert "userMessagePreview" in audit
        # The preview is bounded; the full 4000-char message is not in the audit.
        assert len(audit["userMessagePreview"]) <= 200
