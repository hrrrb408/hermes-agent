"""Phase 2B Provider Adapters for the Hermes Dev WebUI.

Two adapters implement the controlled Provider boundary:

  - ``FakeProviderAdapter``: deterministic, offline. Maps a user message to a
    bounded read-only tool call (or a clarify call) WITHOUT any network
    access, API key, ~/.hermes access, shell, or file write. Used by tests,
    smoke, and local verification. ``providerMode=fake``,
    ``providerApiCalled=true``, ``externalNetworkCalled=false``.

  - ``RealProviderAdapter``: the controlled framework for a real external
    Provider API. It is BLOCKED by default. Even when fully enabled it does
    not perform a real network call in Phase 2B (the concrete vendor call is
    deferred). It never prints / logs / audits an API key. ``providerMode=real``.

Architecture constraints (mirrors the rest of the chain):
  - stdlib only (no third-party imports — no httpx, no requests, no openai)
  - no ~/.hermes access, no production state.db access, no shell, no file write
  - never reads a provider API key into a response or log
  - deterministic IDs (derived from input via sha256) so the fake provider is
    reproducible across runs
  - the fake adapter only ever selects tools that are in the request's
    allowed_tool_ids AND in STATIC_ALLOWLIST

Phase: 2B — Provider Schema / API Controlled Integration
Status: provider adapters implemented (fake deterministic; real blocked)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from hermes_cli.dev_web_provider_request import (
    BLOCKED_PROVIDER_API_KEY_MISSING,
    BLOCKED_PROVIDER_REAL_MODE_NOT_ENABLED,
    ProviderRequest,
    PROVIDER_MODE_FAKE,
    PROVIDER_MODE_REAL,
    _evaluate_real_mode_eligibility,
)


# ---------------------------------------------------------------------------
# 1. Response models
# ---------------------------------------------------------------------------

FINISH_REASON_TOOL_CALLS = "tool_calls"
FINISH_REASON_STOP = "stop"
FINISH_REASON_BLOCKED = "blocked"

# P2: the concrete real-vendor network call is not wired in Phase 2B.
BLOCKED_REAL_PROVIDER_NOT_WIRED = "blocked_real_provider_not_wired_in_phase_2b"


@dataclass(frozen=True, slots=True)
class ProviderToolCall:
    """A single provider-emitted tool call (validated later by the round-trip)."""

    id: str
    name: str
    arguments: Mapping[str, Any]

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": dict(self.arguments),
        }


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    """The adapter response envelope."""

    provider_response_id: str
    provider_mode: str
    provider_api_called: bool
    external_network_called: bool
    assistant_message: str
    tool_calls: tuple[ProviderToolCall, ...]
    finish_reason: str
    blocked: bool
    blocked_reason: str | None

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "providerResponseId": self.provider_response_id,
            "providerMode": self.provider_mode,
            "providerApiCalled": self.provider_api_called,
            "externalNetworkCalled": self.external_network_called,
            "assistantMessage": self.assistant_message,
            "toolCalls": [c.to_safe_dict() for c in self.tool_calls],
            "finishReason": self.finish_reason,
            "blocked": self.blocked,
            "blockedReason": self.blocked_reason,
        }


# ---------------------------------------------------------------------------
# 2. Deterministic ID derivation
# ---------------------------------------------------------------------------


def _deterministic_id(prefix: str, *parts: str) -> str:
    """Derive a deterministic, stable ID from *parts* via sha256.

    Same inputs → same ID. Never contains secrets (the parts are tool names,
    modes, and bounded message hashes — never API keys).
    """
    canonical = "\x1f".join(str(p) for p in parts)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:24]}"


# ---------------------------------------------------------------------------
# 3. ProviderAdapter base
# ---------------------------------------------------------------------------


class ProviderAdapter:
    """Base adapter contract."""

    mode: str = ""

    def invoke(
        self,
        request: ProviderRequest,
        *,
        tool_results: Mapping[str, Any] | None = None,
    ) -> ProviderResponse:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 4. FakeProviderAdapter — deterministic, offline
# ---------------------------------------------------------------------------

# Keyword → (tool_id, arguments). Order matters: first match wins. Each route
# is also gated by allowlist membership at invoke time. Arguments are bounded,
# allowlisted-only values that pass the read-only registry validator.
_FAKE_TOOL_ROUTES: tuple[tuple[tuple[str, ...], str, Mapping[str, Any]], ...] = (
    (("tool policy", "polic"), "tool_policy_read", {"includeDisabled": True}),
    (("route governance", "route"), "route_governance_read", {"includeDetails": True}),
    (("audit events", "audit"), "audit_events_read", {"limit": 5}),
    (("dev environment", "environment"), "dev_environment_read", {}),
    (("release status", "release"), "release_status_read", {"includePhaseTimeline": True}),
)

_CLARIFY_KEYWORDS: tuple[str, ...] = ("clarif", "ask", "question")


class FakeProviderAdapter(ProviderAdapter):
    """Deterministic, offline fake provider.

    First turn (``tool_results`` is None): map the user message to at most one
    bounded read-only tool call (or a clarify call). Second turn
    (``tool_results`` provided): emit a deterministic final answer that
    summarizes the executed tool results.
    """

    mode = PROVIDER_MODE_FAKE

    def invoke(
        self,
        request: ProviderRequest,
        *,
        tool_results: Mapping[str, Any] | None = None,
    ) -> ProviderResponse:
        message = request.user_message or ""
        lowered = message.lower()
        allowed = frozenset(request.allowed_tool_ids)

        if tool_results is not None:
            return self._finalize(request, tool_results)

        # Deterministic per MESSAGE (not per random request id) so the fake
        # provider is reproducible across runs for the same input.
        response_id = _deterministic_id("prsp", PROVIDER_MODE_FAKE, message)

        # Route to a read-only tool if a keyword matches and the tool is allowed.
        for keywords, tool_id, arguments in _FAKE_TOOL_ROUTES:
            if tool_id in allowed and any(kw in lowered for kw in keywords):
                call = ProviderToolCall(
                    id=_deterministic_id("ptc", response_id, tool_id),
                    name=tool_id,
                    arguments=dict(arguments),
                )
                return ProviderResponse(
                    provider_response_id=response_id,
                    provider_mode=PROVIDER_MODE_FAKE,
                    provider_api_called=True,
                    external_network_called=False,
                    assistant_message=self._assistant_for_tool(tool_id),
                    tool_calls=(call,),
                    finish_reason=FINISH_REASON_TOOL_CALLS,
                    blocked=False,
                    blocked_reason=None,
                )

        # Clarify route.
        if "clarify" in allowed and any(kw in lowered for kw in _CLARIFY_KEYWORDS):
            question = message.strip() or "Could you clarify what you need?"
            call = ProviderToolCall(
                id=_deterministic_id("ptc", response_id, "clarify"),
                name="clarify",
                arguments={"question": question[:1000]},
            )
            return ProviderResponse(
                provider_response_id=response_id,
                provider_mode=PROVIDER_MODE_FAKE,
                provider_api_called=True,
                external_network_called=False,
                assistant_message="Asking the user to clarify.",
                tool_calls=(call,),
                finish_reason=FINISH_REASON_TOOL_CALLS,
                blocked=False,
                blocked_reason=None,
            )

        # No tool selected — return a direct answer.
        return ProviderResponse(
            provider_response_id=response_id,
            provider_mode=PROVIDER_MODE_FAKE,
            provider_api_called=True,
            external_network_called=False,
            assistant_message=(
                "No read-only tool matched this request. "
                "Phase 2B supports tool_policy_read, route_governance_read, "
                "audit_events_read, dev_environment_read, release_status_read, "
                "and clarify only."
            ),
            tool_calls=(),
            finish_reason=FINISH_REASON_STOP,
            blocked=False,
            blocked_reason=None,
        )

    @staticmethod
    def _assistant_for_tool(tool_id: str) -> str:
        return {
            "tool_policy_read": "I will read the current tool-execution policy.",
            "route_governance_read": "I will read the route-governance summary.",
            "audit_events_read": "I will read recent audit events.",
            "dev_environment_read": "I will read the dev environment health summary.",
            "release_status_read": "I will read the release-status summary.",
        }.get(tool_id, "I will run a read-only inspection.")

    def _finalize(
        self, request: ProviderRequest, tool_results: Mapping[str, Any]
    ) -> ProviderResponse:
        """Produce a deterministic final answer summarizing the tool results."""
        response_id = _deterministic_id(
            "prsp", PROVIDER_MODE_FAKE, request.user_message, "finalize",
        )
        executed = tool_results.get("executedToolIds", [])
        blocked = tool_results.get("blockedToolIds", [])
        parts: list[str] = ["Provider round-trip completed (fake provider)."]
        if executed:
            parts.append(f"Executed read-only tool(s): {', '.join(executed)}.")
        if blocked:
            parts.append(f"Blocked tool call(s): {', '.join(blocked)}.")
        parts.append("No external network was called.")
        return ProviderResponse(
            provider_response_id=response_id,
            provider_mode=PROVIDER_MODE_FAKE,
            provider_api_called=True,
            external_network_called=False,
            assistant_message=" ".join(parts),
            tool_calls=(),
            finish_reason=FINISH_REASON_STOP,
            blocked=False,
            blocked_reason=None,
        )


# ---------------------------------------------------------------------------
# 5. RealProviderAdapter — blocked framework (no real network call in 2B)
# ---------------------------------------------------------------------------


class RealProviderAdapter(ProviderAdapter):
    """Controlled framework for a real external Provider API.

    Phase 2B policy: BLOCKED. Even when every enablement condition holds, the
    concrete vendor network call is NOT wired (deferred — see Phase 2B P2
    backlog). This adapter therefore never performs a real external call in
    Phase 2B and never reads an API key into a response or log.
    """

    mode = PROVIDER_MODE_REAL

    def invoke(
        self,
        request: ProviderRequest,
        *,
        tool_results: Mapping[str, Any] | None = None,
    ) -> ProviderResponse:
        response_id = _deterministic_id(
            "prsp", PROVIDER_MODE_REAL, request.provider_request_id,
        )

        # Defense-in-depth eligibility re-check (the request builder already
        # gated real mode). If anything is missing, block with the reason.
        eligible, reason = _evaluate_real_mode_eligibility(production_gate_override=None)
        if not eligible:
            return self._blocked(response_id, reason or BLOCKED_PROVIDER_REAL_MODE_NOT_ENABLED)

        # Eligible but the concrete vendor call is not wired in Phase 2B.
        return self._blocked(response_id, BLOCKED_REAL_PROVIDER_NOT_WIRED)

    @staticmethod
    def _blocked(response_id: str, reason: str) -> ProviderResponse:
        return ProviderResponse(
            provider_response_id=response_id,
            provider_mode=PROVIDER_MODE_REAL,
            provider_api_called=False,
            external_network_called=False,
            assistant_message=f"Real provider call blocked: {reason}.",
            tool_calls=(),
            finish_reason=FINISH_REASON_BLOCKED,
            blocked=True,
            blocked_reason=reason,
        )


# ---------------------------------------------------------------------------
# 6. Adapter factory
# ---------------------------------------------------------------------------


def get_provider_adapter(provider_mode: str) -> ProviderAdapter:
    """Return the adapter for *provider_mode*.

    Unknown / disabled modes return the fake adapter is NOT correct — disabled
    means no provider at all. The round-trip orchestrator handles ``disabled``
    before reaching an adapter. Here we map fake→fake, real→real, and anything
    else (including disabled) to the real-adapter-blocked surface so a stray
    call still fails closed.
    """
    if provider_mode == PROVIDER_MODE_FAKE:
        return FakeProviderAdapter()
    if provider_mode == PROVIDER_MODE_REAL:
        return RealProviderAdapter()
    return RealProviderAdapter()


__all__ = [
    "ProviderAdapter",
    "FakeProviderAdapter",
    "RealProviderAdapter",
    "ProviderToolCall",
    "ProviderResponse",
    "get_provider_adapter",
    "FINISH_REASON_TOOL_CALLS",
    "FINISH_REASON_STOP",
    "FINISH_REASON_BLOCKED",
    "BLOCKED_REAL_PROVIDER_NOT_WIRED",
]
