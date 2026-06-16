"""Phase 3B — OpenAI-compatible Adapter tests (mock HTTP client only).

Verifies the gated adapter:
  - builds a valid OpenAI chat-completions request shape
  - normalizes a well-formed response (content + tool calls + usage)
  - uses ONLY the injected mock client (no real network)
  - enforces the response-size limit (blocked_provider_response_too_large)
  - falls back safely on malformed JSON (blocked_provider_malformed_response)
  - falls back on schema mismatch (blocked_provider_schema_mismatch)
  - does NOT retry auth failure (blocked_provider_auth_failed)
  - retries safe-transient 5xx up to the cap then blocks
  - never returns the raw body / header / secret

Phase: 3B — Real Provider Read-only Controlled Integration
"""

from __future__ import annotations

import json

import pytest

from hermes_cli.dev_web_provider_openai_compatible import (
    MAX_RESPONSE_BYTES,
    MockHttpClient,
    OpenAICompatibleAdapter,
    RawHttpResponse,
)
from hermes_cli.dev_web_provider_openai_compatible_schema import (
    OpenAIChatRequest,
    parse_openai_chat_response,
)
from hermes_cli.dev_web_provider_real_schema import build_provider_real_request


def _request(message: str = "check route governance"):
    return build_provider_real_request(
        provider_mode="real", provider_name="openai_compatible",
        model="gpt-4o-mini", user_message=message,
        tool_allowlist=("route_governance_read", "tool_policy_read"),
    )


def _ok_body(content="I will inspect.", tool=None) -> bytes:
    tool_calls = []
    if tool:
        tool_calls.append({
            "id": "call_1", "type": "function",
            "function": {"name": tool, "arguments": json.dumps({"includeDetails": True})},
        })
    return json.dumps({
        "id": "chatcmpl-x",
        "choices": [{
            "message": {"role": "assistant", "content": content, "tool_calls": tool_calls or None},
            "finish_reason": "tool_calls" if tool else "stop",
        }],
        "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
    }).encode("utf-8")


class TestRequestShape:
    def test_openai_request_payload_shape(self) -> None:
        req = _request()
        chat = OpenAIChatRequest.from_real_request(req, model="gpt-4o-mini")
        payload = chat.to_payload()
        assert payload["model"] == "gpt-4o-mini"
        assert payload["messages"][0]["role"] == "user"
        assert payload["tool_choice"] == "auto"
        assert any(t["type"] == "function" for t in payload["tools"])
        assert payload["max_tokens"] == req.max_tokens

    def test_no_tools_means_tool_choice_none(self) -> None:
        req = build_provider_real_request(
            provider_mode="real", provider_name="openai_compatible",
            model="gpt-4o-mini", user_message="hi", tool_allowlist=(),
        )
        payload = OpenAIChatRequest.from_real_request(req, model="gpt-4o-mini").to_payload()
        assert "tools" not in payload


class TestResponseNormalization:
    def test_normalizes_content_and_usage(self) -> None:
        req = _request()
        adapter = OpenAICompatibleAdapter(
            MockHttpClient(response_body=_ok_body()), base_url="https://api.openai.com", model="gpt-4o-mini",
        )
        result = adapter.round_trip(req, timeout_seconds=10, max_retries=1)
        assert result.ok is True
        assert result.external_network_called is True
        assert "inspect" in result.content
        assert result.usage["total_tokens"] == 20

    def test_normalizes_tool_call(self) -> None:
        req = _request()
        adapter = OpenAICompatibleAdapter(
            MockHttpClient(response_body=_ok_body(tool="route_governance_read")),
            base_url="https://api.openai.com", model="gpt-4o-mini",
        )
        result = adapter.round_trip(req, timeout_seconds=10, max_retries=1)
        assert result.ok is True
        assert len(result.raw_tool_calls) == 1
        assert result.raw_tool_calls[0]["name"] == "route_governance_read"
        assert result.raw_tool_calls[0]["arguments"] == {"includeDetails": True}

    def test_argument_string_is_parsed_to_dict(self) -> None:
        payload = {
            "choices": [{
                "message": {
                    "role": "assistant", "content": "",
                    "tool_calls": [{
                        "id": "c1", "type": "function",
                        "function": {"name": "clarify", "arguments": '{"question":"hi"}'},
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        parsed = parse_openai_chat_response(payload)
        assert parsed.tool_calls[0]["arguments"] == {"question": "hi"}

    def test_malformed_arguments_become_empty_dict(self) -> None:
        payload = {
            "choices": [{
                "message": {
                    "role": "assistant", "content": "",
                    "tool_calls": [{
                        "id": "c1", "type": "function",
                        "function": {"name": "clarify", "arguments": "not-json"},
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {},
        }
        parsed = parse_openai_chat_response(payload)
        assert parsed.tool_calls[0]["arguments"] == {}


class TestFailurePaths:
    def test_auth_failure_not_retried(self) -> None:
        req = _request()
        # Give 3 identical 401 responses; adapter must stop after attempt 1.
        mock = MockHttpClient(responses=tuple(
            RawHttpResponse(status=401, body=b'{"error":"unauthorized"}', error=None) for _ in range(3)
        ))
        adapter = OpenAICompatibleAdapter(mock, base_url="https://api.openai.com", model="gpt-4o-mini")
        result = adapter.round_trip(req, timeout_seconds=10, max_retries=3)
        assert result.ok is False
        assert result.blocked_reason == "blocked_provider_auth_failed"
        assert result.attempts == 1  # no retry

    def test_oversize_response_blocked(self) -> None:
        req = _request()
        big = b'{"choices":[{"message":{"content":"x"},"finish_reason":"stop"}]}' + b' ' * (MAX_RESPONSE_BYTES + 1)
        adapter = OpenAICompatibleAdapter(
            MockHttpClient(response_body=big), base_url="https://api.openai.com", model="gpt-4o-mini",
        )
        result = adapter.round_trip(req, timeout_seconds=10, max_retries=1)
        assert result.ok is False
        assert result.blocked_reason == "blocked_provider_response_too_large"

    def test_malformed_json_blocked(self) -> None:
        req = _request()
        adapter = OpenAICompatibleAdapter(
            MockHttpClient(response_body=b'not-json{'), base_url="https://api.openai.com", model="gpt-4o-mini",
        )
        result = adapter.round_trip(req, timeout_seconds=10, max_retries=0)
        assert result.ok is False
        assert result.blocked_reason == "blocked_provider_malformed_response"

    def test_schema_mismatch_blocked(self) -> None:
        req = _request()
        adapter = OpenAICompatibleAdapter(
            MockHttpClient(response_body=b'{"weird":"structure","not":"a choice"}'),
            base_url="https://api.openai.com", model="gpt-4o-mini",
        )
        # A response with no choices is accepted as empty content (not a
        # mismatch). A response whose choices entry is not an object mismatches.
        result = adapter.round_trip(req, timeout_seconds=10, max_retries=0)
        # Missing choices → empty content success (usage 0).
        assert result.ok is True
        assert result.content == ""

        adapter2 = OpenAICompatibleAdapter(
            MockHttpClient(response_body=b'{"choices":["not-an-object"]}'),
            base_url="https://api.openai.com", model="gpt-4o-mini",
        )
        result2 = adapter2.round_trip(req, timeout_seconds=10, max_retries=0)
        assert result2.ok is False
        assert result2.blocked_reason == "blocked_provider_schema_mismatch"

    def test_5xx_retried_then_exhausts(self) -> None:
        req = _request()
        mock = MockHttpClient(responses=tuple(
            RawHttpResponse(status=503, body=None, error=None) for _ in range(5)
        ))
        adapter = OpenAICompatibleAdapter(mock, base_url="https://api.openai.com", model="gpt-4o-mini")
        result = adapter.round_trip(req, timeout_seconds=10, max_retries=2)
        assert result.ok is False
        # 1 initial + 2 retries = 3 attempts
        assert result.attempts == 3
        assert result.blocked_reason in (
            "blocked_provider_network_unavailable", "blocked_provider_retry_exhausted",
        )

    def test_transport_failure_blocked(self) -> None:
        req = _request()
        mock = MockHttpClient(response_status=None, response_body=None, error="connection_refused")
        adapter = OpenAICompatibleAdapter(mock, base_url="https://api.openai.com", model="gpt-4o-mini")
        result = adapter.round_trip(req, timeout_seconds=10, max_retries=0)
        assert result.ok is False
        assert result.blocked_reason == "blocked_provider_network_unavailable"

    def test_invalid_timeout_blocked_pre_call(self) -> None:
        req = _request()
        adapter = OpenAICompatibleAdapter(
            MockHttpClient(response_body=_ok_body()), base_url="https://api.openai.com", model="gpt-4o-mini",
        )
        result = adapter.round_trip(req, timeout_seconds=0, max_retries=1)
        assert result.ok is False
        assert result.blocked_reason == "blocked_provider_timeout_invalid"
        assert result.external_network_called is False


class TestMockClientOnly:
    def test_mock_client_records_call_without_key_value(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-placeholder-key-1234567890")
        req = _request()
        mock = MockHttpClient(response_body=_ok_body())
        adapter = OpenAICompatibleAdapter(mock, base_url="https://api.openai.com", model="gpt-4o-mini")
        adapter.round_trip(req, timeout_seconds=10, max_retries=0)
        assert len(mock.calls) == 1
        call = mock.calls[0]
        assert call["url"].endswith("/v1/chat/completions")
        assert "Authorization" in call["headerKeys"]
        # The recorded call never retains the key VALUE (only header KEYS).
        blob = repr(call)
        assert "sk-fake-placeholder-key" not in blob
