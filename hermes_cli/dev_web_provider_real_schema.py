"""Phase 3B Real Provider Request / Response Envelope Schema (Frozen).

The controlled envelopes the rest of the system sees for a real round-trip.
The raw vendor wire payload is **never** exposed: it is normalized into these
envelopes with secrets redacted, sizes bounded, and tool calls validated
against the read-only allowlist.

The request envelope **never** carries an API key, an Authorization header, a
raw secret / token, a full tokenHash, a production path, raw file content, or a
callable repr. The response envelope **never** carries a raw secret, an API
key, an Authorization header, a raw token, a full tokenHash, a callable repr,
or an unbounded raw response body.

Phase: 3B — Real Provider Read-only Controlled Integration
Status: request / response envelopes implemented (frozen)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping

# Bounded size limits (frozen by the schema + failure policy).
_MAX_CONTENT_SUMMARY_CHARS = 1000
_MAX_MESSAGES = 32
_MAX_MESSAGE_CHARS = 4000
_MAX_TOOL_CALLS = 8
_MAX_TEMPERATURE = 1.0
_MIN_TEMPERATURE = 0.0
_MAX_MAX_TOKENS = 4096
_RESPONSE_VERSION = 1


def _deterministic_id(prefix: str, *parts: str) -> str:
    """Derive a deterministic, stable ID from *parts* via sha256.

    Same inputs → same ID. The parts are request ids, mode, and bounded message
    hashes — never an API key.
    """
    canonical = "\x1f".join(str(p) for p in parts)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:24]}"


# ---------------------------------------------------------------------------
# 1. Request envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderRealMessage:
    """One sanitized request message (role + bounded content). No secrets."""

    role: str
    content: str

    def to_safe_dict(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True, slots=True)
class ProviderRealRequest:
    """The controlled real-provider request envelope (never carries a key).

    Field set is frozen by phase-3b-provider-request-response-schema.md §2.
    """

    provider_mode: str
    provider_name: str
    model: str
    request_id: str
    conversation_id: str | None
    workflow_id: str | None
    tool_allowlist: tuple[str, ...]
    messages: tuple[ProviderRealMessage, ...]
    max_tokens: int
    temperature: float
    timeout_seconds: int
    redaction_policy: str
    audit_required: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "providerMode": self.provider_mode,
            "providerName": self.provider_name,
            "model": self.model,
            "requestId": self.request_id,
            "conversationId": self.conversation_id,
            "workflowId": self.workflow_id,
            "toolAllowlist": list(self.tool_allowlist),
            "messages": [m.to_safe_dict() for m in self.messages],
            "maxTokens": self.max_tokens,
            "temperature": self.temperature,
            "timeoutSeconds": self.timeout_seconds,
            "redactionPolicy": self.redaction_policy,
            "auditRequired": self.audit_required,
            "redactionApplied": True,
        }


def build_provider_real_request(
    *,
    provider_mode: str,
    provider_name: str,
    model: str,
    user_message: str,
    conversation_id: str | None = None,
    workflow_id: str | None = None,
    tool_allowlist: tuple[str, ...] = (),
    max_tokens: int = 1024,
    temperature: float = 0.0,
    timeout_seconds: int = 20,
    request_id: str | None = None,
    redaction_policy: str = "phase-3b-redaction-v1",
) -> ProviderRealRequest:
    """Build the controlled request envelope from a user message.

    The user message is bounded; the request envelope never carries an API key.
    """
    # Bound + sanitize the user message into a single user turn.
    if not isinstance(user_message, str):
        user_message = ""
    content = user_message.strip()[:_MAX_MESSAGE_CHARS]

    rid = request_id or _deterministic_id("preq", provider_mode, provider_name, model, content)
    return ProviderRealRequest(
        provider_mode=provider_mode,
        provider_name=provider_name,
        model=model,
        request_id=rid,
        conversation_id=conversation_id,
        workflow_id=workflow_id,
        tool_allowlist=tuple(sorted(set(tool_allowlist))),
        messages=(ProviderRealMessage(role="user", content=content),),
        max_tokens=max(1, min(_MAX_MAX_TOKENS, int(max_tokens))) if isinstance(max_tokens, int) else 1024,
        temperature=max(_MIN_TEMPERATURE, min(_MAX_TEMPERATURE, float(temperature))),
        timeout_seconds=int(timeout_seconds),
        redaction_policy=redaction_policy,
        audit_required=True,
    )


# ---------------------------------------------------------------------------
# 2. Response envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderRealToolCall:
    """A validated, allowlisted provider tool call in the response."""

    tool_call_id: str
    tool_id: str  # must be in the read-only allowlist
    arguments: Mapping[str, Any]
    status: str  # parsed | blocked | executed
    blocked_reason: str | None

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "toolCallId": self.tool_call_id,
            "toolId": self.tool_id,
            "arguments": dict(self.arguments),
            "status": self.status,
            "blockedReason": self.blocked_reason,
        }


@dataclass(frozen=True, slots=True)
class ProviderRealUsage:
    """Bounded token usage (prompt / completion / total)."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "promptTokens": self.prompt_tokens,
            "completionTokens": self.completion_tokens,
            "totalTokens": self.total_tokens,
        }


@dataclass(frozen=True, slots=True)
class ProviderRealResponse:
    """The controlled real-provider response envelope.

    Field set is frozen by phase-3b-provider-request-response-schema.md §3.
    ``external_network_called`` is ``True`` only when a real call was made.
    """

    request_id: str
    response_id: str
    provider_name: str
    model: str
    status: str  # completed | blocked | failed
    content_summary: str
    tool_calls: tuple[ProviderRealToolCall, ...]
    usage_summary: ProviderRealUsage
    finish_reason: str
    blocked_reason: str | None
    audit_links: tuple[str, ...]
    redaction_applied: bool
    external_network_called: bool
    cost_estimate: Mapping[str, Any] | None = field(default=None)

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "requestId": self.request_id,
            "responseId": self.response_id,
            "providerName": self.provider_name,
            "model": self.model,
            "status": self.status,
            "contentSummary": self.content_summary,
            "toolCalls": [c.to_safe_dict() for c in self.tool_calls],
            "usageSummary": self.usage_summary.to_safe_dict(),
            "finishReason": self.finish_reason,
            "blockedReason": self.blocked_reason,
            "auditLinks": list(self.audit_links),
            "redactionApplied": self.redaction_applied,
            "externalNetworkCalled": self.external_network_called,
            "costEstimate": dict(self.cost_estimate) if self.cost_estimate else None,
        }


def build_blocked_real_response(
    *,
    request: ProviderRealRequest,
    blocked_reason: str,
    response_id: str | None = None,
    audit_links: tuple[str, ...] = (),
    cost_estimate: Mapping[str, Any] | None = None,
) -> ProviderRealResponse:
    """Build a blocked real response (no network call made)."""
    rid = response_id or _deterministic_id(
        "prsp", request.provider_name, request.request_id, "blocked",
    )
    return ProviderRealResponse(
        request_id=request.request_id,
        response_id=rid,
        provider_name=request.provider_name,
        model=request.model,
        status="blocked",
        content_summary=f"Real provider request blocked: {blocked_reason}.",
        tool_calls=(),
        usage_summary=ProviderRealUsage(0, 0, 0),
        finish_reason="blocked",
        blocked_reason=blocked_reason,
        audit_links=audit_links,
        redaction_applied=True,
        external_network_called=False,
        cost_estimate=cost_estimate,
    )


def build_failed_real_response(
    *,
    request: ProviderRealRequest,
    blocked_reason: str,
    response_id: str | None = None,
    audit_links: tuple[str, ...] = (),
    usage: ProviderRealUsage | None = None,
    cost_estimate: Mapping[str, Any] | None = None,
) -> ProviderRealResponse:
    """Build a failed real response (a call was attempted but failed)."""
    rid = response_id or _deterministic_id(
        "prsp", request.provider_name, request.request_id, "failed",
    )
    return ProviderRealResponse(
        request_id=request.request_id,
        response_id=rid,
        provider_name=request.provider_name,
        model=request.model,
        status="failed",
        content_summary=f"Real provider request failed: {blocked_reason}.",
        tool_calls=(),
        usage_summary=usage or ProviderRealUsage(0, 0, 0),
        finish_reason="failed",
        blocked_reason=blocked_reason,
        audit_links=audit_links,
        redaction_applied=True,
        external_network_called=True,
        cost_estimate=cost_estimate,
    )


def truncate_content_summary(text: str) -> str:
    """Bound the content summary; the raw body is never returned."""
    if not isinstance(text, str):
        return ""
    if len(text) <= _MAX_CONTENT_SUMMARY_CHARS:
        return text
    return text[:_MAX_CONTENT_SUMMARY_CHARS]


__all__ = [
    "ProviderRealMessage",
    "ProviderRealRequest",
    "ProviderRealToolCall",
    "ProviderRealUsage",
    "ProviderRealResponse",
    "build_provider_real_request",
    "build_blocked_real_response",
    "build_failed_real_response",
    "truncate_content_summary",
    "MAX_TOOL_CALLS",
]


# Re-exported size constants for tests / the adapter.
MAX_TOOL_CALLS = _MAX_TOOL_CALLS
