"""Phase 3B — Real Provider Request / Response Schema tests.

Verifies the frozen envelopes:
  - request envelope includes the frozen field set
  - request envelope NEVER carries apiKey / Authorization / raw secret / token /
    full tokenHash / production path / raw file content / callable repr
  - response envelope includes the frozen field set
  - response envelope NEVER carries a raw secret / API key / Authorization /
    raw token / full tokenHash / callable repr / unbounded raw body
  - sizes are bounded (content summary, message length, max tokens, temperature)
  - blocked / failed response builders set externalNetworkCalled correctly

Phase: 3B — Real Provider Read-only Controlled Integration
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_provider_real_schema import (
    ProviderRealMessage,
    ProviderRealResponse,
    ProviderRealUsage,
    build_blocked_real_response,
    build_failed_real_response,
    build_provider_real_request,
    truncate_content_summary,
)

_FORBIDDEN_FIELDS = (
    "apiKey", "api_key", "authorization", "Authorization", "bearer", "token",
    "tokenHash", "rawPrompt", "rawResponse", "callable", "productionPath",
)


def _make_request(**kwargs):
    base = dict(
        provider_mode="real", provider_name="openai_compatible", model="gpt-4o-mini",
        user_message="check route governance",
    )
    base.update(kwargs)
    return build_provider_real_request(**base)


class TestRequestEnvelope:
    def test_request_includes_frozen_fields(self) -> None:
        d = _make_request().to_safe_dict()
        for key in (
            "providerMode", "providerName", "model", "requestId", "conversationId",
            "workflowId", "toolAllowlist", "messages", "maxTokens", "temperature",
            "timeoutSeconds", "redactionPolicy", "auditRequired", "redactionApplied",
        ):
            assert key in d, f"missing frozen field {key}"

    def test_request_excludes_forbidden_fields(self) -> None:
        d = _make_request().to_safe_dict()
        for field in _FORBIDDEN_FIELDS:
            assert field not in d, f"forbidden field {field} present in request"

    def test_request_never_carries_an_api_key(self) -> None:
        # Even when the user message contains a secret-looking value, the
        # envelope is the controlled surface — the builder bounds the message
        # but the REQUEST audit/preview is separately redacted. Here we assert
        # the envelope has no dedicated secret field.
        d = _make_request(user_message="x").to_safe_dict()
        assert "apiKey" not in d
        assert d.get("auditRequired") is True

    def test_message_length_is_bounded(self) -> None:
        req = _make_request(user_message="A" * 10000)
        assert len(req.messages[0].content) <= 4000

    def test_max_tokens_clamped(self) -> None:
        req = _make_request(max_tokens=999_999)
        assert req.max_tokens <= 4096

    def test_temperature_clamped(self) -> None:
        req = _make_request(temperature=5.0)
        assert 0.0 <= req.temperature <= 1.0
        req2 = _make_request(temperature=-1.0)
        assert req2.temperature >= 0.0

    def test_request_id_is_deterministic(self) -> None:
        r1 = _make_request(user_message="same message")
        r2 = _make_request(user_message="same message")
        assert r1.request_id == r2.request_id


class TestResponseEnvelope:
    def test_response_includes_frozen_fields(self) -> None:
        req = _make_request()
        resp = build_blocked_real_response(request=req, blocked_reason="blocked_provider_real_not_enabled")
        d = resp.to_safe_dict()
        for key in (
            "requestId", "responseId", "providerName", "model", "status",
            "contentSummary", "toolCalls", "usageSummary", "finishReason",
            "blockedReason", "auditLinks", "redactionApplied", "externalNetworkCalled",
            "costEstimate",
        ):
            assert key in d, f"missing frozen field {key}"

    def test_blocked_response_no_network(self) -> None:
        req = _make_request()
        resp = build_blocked_real_response(request=req, blocked_reason="blocked_provider_api_key_missing")
        d = resp.to_safe_dict()
        assert d["status"] == "blocked"
        assert d["externalNetworkCalled"] is False
        assert d["blockedReason"] == "blocked_provider_api_key_missing"

    def test_failed_response_marks_network(self) -> None:
        req = _make_request()
        resp = build_failed_real_response(
            request=req, blocked_reason="blocked_provider_network_unavailable",
            usage=ProviderRealUsage(5, 0, 5),
        )
        d = resp.to_safe_dict()
        assert d["status"] == "failed"
        assert d["externalNetworkCalled"] is True
        assert d["usageSummary"]["totalTokens"] == 5

    def test_response_excludes_forbidden_fields(self) -> None:
        req = _make_request()
        resp = build_blocked_real_response(request=req, blocked_reason="x")
        d = resp.to_safe_dict()
        for field in _FORBIDDEN_FIELDS:
            assert field not in d

    def test_usage_summary_shape(self) -> None:
        u = ProviderRealUsage(10, 5, 15)
        d = u.to_safe_dict()
        assert d == {"promptTokens": 10, "completionTokens": 5, "totalTokens": 15}

    def test_content_summary_truncated(self) -> None:
        long = "Z" * 5000
        truncated = truncate_content_summary(long)
        assert len(truncated) <= 1000

    def test_usage_field_not_treated_as_secret(self) -> None:
        # totalTokens / promptTokens / completionTokens are safe counts; the
        # schema must surface them as integers (not redact them).
        u = ProviderRealUsage(100, 200, 300)
        assert u.to_safe_dict()["totalTokens"] == 300
