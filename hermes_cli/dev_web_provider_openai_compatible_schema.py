"""Phase 3B OpenAI-compatible Wire Schema (Request / Response mapping).

Maps the controlled Phase 3B request envelope to the OpenAI chat-completions
wire shape and normalizes the wire response back to a bounded, structured form.
The raw wire payload is **never** returned; only the normalized content +
structured tool calls + bounded usage leave this module.

Phase: 3B — Real Provider Read-only Controlled Integration
Status: OpenAI-compatible wire schema implemented
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass
class OpenAIChatRequest:
    """The OpenAI chat-completions request payload (built from the envelope)."""

    model: str
    messages: tuple[dict[str, Any], ...]
    max_tokens: int
    temperature: float
    tools: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    tool_choice: str = "auto"

    @classmethod
    def from_real_request(cls, request, *, model: str) -> "OpenAIChatRequest":
        """Build the wire payload from a ``ProviderRealRequest``.

        Tool definitions come from the read-only allowlist only.
        """
        messages = tuple({"role": m.role, "content": m.content} for m in request.messages)
        tools = tuple(_tool_definition(name) for name in request.tool_allowlist)
        tool_choice = "auto" if tools else "none"
        return cls(
            model=model,
            messages=messages,
            max_tokens=int(request.max_tokens),
            temperature=float(request.temperature),
            tools=tools,
            tool_choice=tool_choice,
        )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": list(self.messages),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        if self.tools:
            payload["tools"] = list(self.tools)
            payload["tool_choice"] = self.tool_choice
        return payload


# Minimal JSON-Schema-ish parameter schemas for the read-only allowlist tools.
# These describe the bounded args the provider may pass; validation happens in
# the policy layer (allowlist membership) and the controlled execution chain.
_TOOL_PARAM_SCHEMAS: dict[str, dict[str, Any]] = {
    "clarify": {"type": "object", "properties": {"question": {"type": "string"}}},
    "tool_policy_read": {"type": "object", "properties": {"includeDisabled": {"type": "boolean"}}},
    "route_governance_read": {"type": "object", "properties": {"includeDetails": {"type": "boolean"}}},
    "audit_events_read": {"type": "object", "properties": {"limit": {"type": "integer"}}},
    "dev_environment_read": {"type": "object", "properties": {}},
    "release_status_read": {"type": "object", "properties": {"includePhaseTimeline": {"type": "boolean"}}},
}


def _tool_definition(name: str) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Read-only inspection tool: {name}.",
            "parameters": dict(_TOOL_PARAM_SCHEMAS.get(name, {"type": "object", "properties": {}})),
        },
    }


@dataclass(frozen=True)
class OpenAIChatResponse:
    """The normalized OpenAI chat-completions response (bounded)."""

    content: str
    tool_calls: tuple[dict[str, Any], ...]  # {id, name, arguments(dict)}
    usage: dict[str, int]
    finish_reason: str


def parse_openai_chat_response(payload: Mapping[str, Any]) -> OpenAIChatResponse:
    """Normalize an OpenAI chat-completions JSON payload.

    Raises ``ValueError`` on a schema mismatch (the adapter maps that to
    ``blocked_provider_schema_mismatch``). Malformed JSON is caught earlier by
    the adapter.
    """
    if not isinstance(payload, Mapping):
        raise ValueError("response is not an object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        # A usage-only or empty response is acceptable as a no-content answer.
        usage = _parse_usage(payload.get("usage"))
        return OpenAIChatResponse(
            content="", tool_calls=(), usage=usage, finish_reason="stop",
        )
    first = choices[0]
    if not isinstance(first, Mapping):
        raise ValueError("choice is not an object")
    message = first.get("message")
    content = ""
    raw_calls: list[dict[str, Any]] = []
    if isinstance(message, Mapping):
        raw_content = message.get("content")
        if isinstance(raw_content, str):
            content = raw_content
        calls = message.get("tool_calls")
        if isinstance(calls, list):
            for call in calls:
                parsed_call = _parse_tool_call(call)
                if parsed_call is not None:
                    raw_calls.append(parsed_call)
    finish_reason = first.get("finish_reason") if isinstance(first.get("finish_reason"), str) else "stop"
    usage = _parse_usage(payload.get("usage"))
    return OpenAIChatResponse(
        content=content, tool_calls=tuple(raw_calls), usage=usage, finish_reason=finish_reason,
    )


def _parse_tool_call(call: Any) -> dict[str, Any] | None:
    if not isinstance(call, Mapping):
        return None
    call_id = call.get("id")
    function = call.get("function")
    if not isinstance(function, Mapping):
        return None
    name = function.get("name")
    raw_args = function.get("arguments")
    if not isinstance(name, str) or not name.strip():
        return None
    arguments = _parse_arguments(raw_args)
    return {"id": str(call_id) if call_id is not None else "", "name": name, "arguments": arguments}


def _parse_arguments(raw_args: Any) -> dict[str, Any]:
    """Parse tool-call arguments to a JSON-native dict.

    OpenAI sends arguments as a JSON STRING. We parse it defensively; on any
    failure we return an empty dict (the policy layer still validates the tool
    id against the allowlist). Never ``eval`` / ``exec``.
    """
    if isinstance(raw_args, Mapping):
        return {k: v for k, v in raw_args.items()}
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
        except ValueError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def _parse_usage(usage: Any) -> dict[str, int]:
    if not isinstance(usage, Mapping):
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _as_int(key: str) -> int:
        val = usage.get(key)
        if isinstance(val, bool) or not isinstance(val, int):
            return 0
        return max(0, val)

    prompt = _as_int("prompt_tokens")
    completion = _as_int("completion_tokens")
    total = _as_int("total_tokens")
    if total == 0:
        total = prompt + completion
    return {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": total}


__all__ = [
    "OpenAIChatRequest",
    "OpenAIChatResponse",
    "parse_openai_chat_response",
]
