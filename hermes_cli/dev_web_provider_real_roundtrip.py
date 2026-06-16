"""Phase 3B Real Provider Round-trip Orchestrator (Gated).

The single entry point for a real round-trip. It is **disabled by default**:
real mode is reachable only when EVERY eligibility condition holds (mode +
enablement + implemented provider + key present + dev home + production PID
gate + allowlisted base URL + allowlisted model + bounded timeout). Any failure
fails closed with a precise ``blocked_provider_*`` reason and **no network
call** (``externalNetworkCalled=false``).

The HTTP client is a **required, injected** dependency (a ``ProviderHttpClient``
Protocol). Tests inject ``MockHttpClient``; there is no default real-network
client wired into the live request path. Therefore **no real provider call ever
happens in tests, smoke, or default operation.**

The orchestrator reuses — unchanged — the Phase 2B sanitizer (redaction), the
Phase 2A ``STATIC_ALLOWLIST`` (read-only tool validation), the Phase 2B audit
writer + Phase 2D durable-store dual-write, and the Phase 3B policy / budget
modules. It does NOT execute provider tool calls (the controlled-chain
execution is a future, separately-authorized step); it classifies them.

Phase: 3B — Real Provider Read-only Controlled Integration
Status: real round-trip orchestrator implemented (gated; mock-only in tests)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from hermes_cli.dev_web_provider_config import (
    PROVIDER_MODE_REAL,
    load_provider_real_config,
)
from hermes_cli.dev_web_provider_openai_compatible import (
    OpenAICompatibleAdapter,
    ProviderHttpClient,
)
from hermes_cli.dev_web_provider_real_audit import (
    write_real_budget_blocked,
    write_real_rate_limit_blocked,
    write_real_request_blocked,
    write_real_request_completed,
    write_real_request_failed,
    write_real_request_previewed,
    write_real_request_started,
    write_real_response_redacted,
    write_real_tool_call_blocked,
    write_real_tool_call_requested,
)
from hermes_cli.dev_web_provider_real_budget import (
    BLOCKED_PROVIDER_BUDGET_EXCEEDED,
    BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED,
    estimate_cost_cents,
    evaluate_rate_and_budget,
    meter_usage,
    record_request_attempt,
)
from hermes_cli.dev_web_provider_real_policy import (
    BLOCKED_PROVIDER_SECRET_DETECTED,
    BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
    classify_provider_tool_call,
    evaluate_real_provider_gating,
    get_read_only_tool_allowlist,
)
from hermes_cli.dev_web_provider_real_redaction import (
    contains_secret,
    redact_real_response_for_audit,
)
from hermes_cli.dev_web_provider_real_schema import (
    ProviderRealRequest,
    ProviderRealResponse,
    ProviderRealToolCall,
    ProviderRealUsage,
    build_blocked_real_response,
    build_failed_real_response,
    build_provider_real_request,
    truncate_content_summary,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_real_request_from_message(
    user_message: str,
    *,
    config=None,
    conversation_id: str | None = None,
    workflow_id: str | None = None,
) -> ProviderRealRequest:
    """Build a real request envelope from a user message + config.

    The tool allowlist is the Phase 2A ``STATIC_ALLOWLIST`` (read-only only).
    """
    if config is None:
        config = load_provider_real_config()
    return build_provider_real_request(
        provider_mode=config.provider_mode,
        provider_name=config.provider_name,
        model=config.model,
        user_message=user_message,
        conversation_id=conversation_id,
        workflow_id=workflow_id,
        tool_allowlist=tuple(get_read_only_tool_allowlist()),
        max_tokens=config.max_tokens,
        temperature=0.0,
        timeout_seconds=config.timeout_seconds,
    )


def preview_real_request(
    request: ProviderRealRequest,
    *,
    hermes_home: str | None = None,
) -> dict[str, Any]:
    """Return a redacted request preview WITHOUT calling the provider.

    Audits ``provider_real_request_previewed``. The preview never carries an
    API key, Authorization header, raw secret, or callable repr.
    """
    config = load_provider_real_config()
    write_real_request_previewed(
        hermes_home=hermes_home, config=config, request=request,
        workflow_id=request.workflow_id,
    )
    safe = request.to_safe_dict()
    # Secret-detection: if the user message itself carried a secret, block.
    if contains_secret(safe):
        write_real_request_blocked(
            hermes_home=hermes_home, config=config, request=request,
            blocked_reason=BLOCKED_PROVIDER_SECRET_DETECTED,
            workflow_id=request.workflow_id,
        )
        return {
            "previewed": False,
            "blockedReason": BLOCKED_PROVIDER_SECRET_DETECTED,
            "redactionApplied": True,
        }
    return {"previewed": True, "request": safe, "redactionApplied": True}


def run_real_provider_roundtrip_controlled(
    request: ProviderRealRequest,
    *,
    http_client: ProviderHttpClient,
    hermes_home: str | None = None,
    production_gate_override: bool | None = None,
    now_iso: str | None = None,
) -> ProviderRealResponse:
    """Run one gated, audited, redacted real round-trip.

    ``http_client`` is REQUIRED and injected (``MockHttpClient`` in tests). The
    function NEVER makes a real network call unless an explicit real client is
    injected AND every gate passes — which no default code path does.
    """
    config = load_provider_real_config()
    ts = now_iso or _now_iso()
    audit_links: list[str] = []

    # ── 1. Enablement gating (no network call on any failure) ──
    eligible, blocked_reason = evaluate_real_provider_gating(
        config, production_gate_override=production_gate_override,
    )
    if not eligible:
        audit_links.append(write_real_request_blocked(
            hermes_home=hermes_home, config=config, request=request,
            blocked_reason=blocked_reason or BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
            workflow_id=request.workflow_id,
        ) or "")
        return build_blocked_real_response(
            request=request, blocked_reason=blocked_reason or "",
            audit_links=tuple(x for x in audit_links if x),
        )

    # ── 2. Secret-detection on the request (no network call) ──
    if contains_secret(request.to_safe_dict()):
        audit_links.append(write_real_request_blocked(
            hermes_home=hermes_home, config=config, request=request,
            blocked_reason=BLOCKED_PROVIDER_SECRET_DETECTED,
            workflow_id=request.workflow_id,
        ) or "")
        return build_blocked_real_response(
            request=request, blocked_reason=BLOCKED_PROVIDER_SECRET_DETECTED,
            audit_links=tuple(x for x in audit_links if x),
        )

    # ── 3. Rate-limit / budget evaluation (no network call) ──
    # Conservative estimate: bound by the per-request max_tokens.
    est_prompt = min(config.daily_token_cap, _estimate_prompt_tokens(request))
    est_completion = config.max_tokens
    decision = evaluate_rate_and_budget(
        config=config, now_iso=ts, hermes_home=hermes_home,
        estimated_prompt_tokens=est_prompt,
        estimated_completion_tokens=est_completion,
    )
    if not decision.allowed:
        if decision.blocked_reason == BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED:
            audit_links.append(write_real_rate_limit_blocked(
                hermes_home=hermes_home, config=config, request=request,
                blocked_reason=BLOCKED_PROVIDER_RATE_LIMIT_EXCEEDED,
                workflow_id=request.workflow_id,
            ) or "")
        else:
            audit_links.append(write_real_budget_blocked(
                hermes_home=hermes_home, config=config, request=request,
                blocked_reason=BLOCKED_PROVIDER_BUDGET_EXCEEDED,
                cost_estimate=decision.cost_estimate,
                workflow_id=request.workflow_id,
            ) or "")
        return build_blocked_real_response(
            request=request,
            blocked_reason=decision.blocked_reason or BLOCKED_PROVIDER_BUDGET_EXCEEDED,
            audit_links=tuple(x for x in audit_links if x),
            cost_estimate=decision.cost_estimate,
        )

    # ── 4. Count the attempt in the rate window (before the call) ──
    record_request_attempt(hermes_home=hermes_home, now_iso=ts)

    # ── 5. Audit start + perform the bounded call ──
    audit_links.append(write_real_request_started(
        hermes_home=hermes_home, config=config, request=request,
        workflow_id=request.workflow_id,
    ) or "")

    adapter = OpenAICompatibleAdapter(
        http_client, base_url=config.base_url, model=config.model,
    )
    result = adapter.round_trip(
        request, timeout_seconds=config.timeout_seconds, max_retries=config.max_retries,
    )

    # ── 6. Failure path ──
    if not result.ok:
        usage_map = dict(result.usage) if result.usage else {}
        cost = estimate_cost_cents(
            model=config.model,
            prompt_tokens=usage_map.get("prompt_tokens", 0),
            completion_tokens=usage_map.get("completion_tokens", 0),
        )
        # Meter any tokens that were actually billed before the failure.
        if usage_map.get("total_tokens", 0) > 0:
            meter_usage(
                hermes_home=hermes_home, now_iso=ts,
                prompt_tokens=usage_map.get("prompt_tokens", 0),
                completion_tokens=usage_map.get("completion_tokens", 0),
                cost_cents=int(cost["estimateCents"]),
            )
        audit_links.append(write_real_request_failed(
            hermes_home=hermes_home, config=config, request=request,
            blocked_reason=result.blocked_reason or "blocked_provider_request_failed",
            usage=usage_map, workflow_id=request.workflow_id,
        ) or "")
        return build_failed_real_response(
            request=request,
            blocked_reason=result.blocked_reason or "blocked_provider_request_failed",
            audit_links=tuple(x for x in audit_links if x),
            usage=ProviderRealUsage(
                usage_map.get("prompt_tokens", 0),
                usage_map.get("completion_tokens", 0),
                usage_map.get("total_tokens", 0),
            ),
            cost_estimate=cost,
        )

    # ── 7. Success: redact, classify tool calls, audit, meter ──
    audit_links.append(write_real_response_redacted(
        hermes_home=hermes_home, config=config, request=request,
        response_id=request.request_id, workflow_id=request.workflow_id,
    ) or "")

    tool_calls = _classify_tool_calls(
        result.raw_tool_calls, config=config, request=request,
        hermes_home=hermes_home, audit_links=audit_links,
    )

    usage_map = dict(result.usage) if result.usage else {}
    prompt_tokens = usage_map.get("prompt_tokens", 0)
    completion_tokens = usage_map.get("completion_tokens", 0)
    total_tokens = usage_map.get("total_tokens", prompt_tokens + completion_tokens)
    usage = ProviderRealUsage(prompt_tokens, completion_tokens, total_tokens)
    cost = estimate_cost_cents(
        model=config.model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
    )
    meter_usage(
        hermes_home=hermes_home, now_iso=ts,
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        cost_cents=int(cost["estimateCents"]),
    )

    # Build the normalized response through the redactor.
    raw_content = truncate_content_summary(result.content)
    response = ProviderRealResponse(
        request_id=request.request_id,
        response_id=request.request_id,  # derived id; provider id not exposed raw
        provider_name=request.provider_name,
        model=request.model,
        status="completed",
        content_summary=raw_content,
        tool_calls=tool_calls,
        usage_summary=usage,
        finish_reason=result.finish_reason,
        blocked_reason=None,
        audit_links=tuple(x for x in audit_links if x),
        redaction_applied=True,
        external_network_called=True,
        cost_estimate=cost,
    )
    # Defensive re-redaction of the whole projection (defense-in-depth).
    redacted = redact_real_response_for_audit(response.to_safe_dict())
    response = _rebuild_response_from_safe(response, redacted)

    audit_links.append(write_real_request_completed(
        hermes_home=hermes_home, config=config, request=request, response=response,
        workflow_id=request.workflow_id,
    ) or "")

    return response


def _estimate_prompt_tokens(request: ProviderRealRequest) -> int:
    """Conservative prompt-token estimate from the message content length."""
    total_chars = sum(len(m.content) for m in request.messages)
    # Rough 4 chars/token estimate, bounded by per-request max tokens.
    return min(8192, max(8, total_chars // 4))


def _classify_tool_calls(
    raw_calls: tuple[Mapping[str, Any], ...],
    *,
    config,
    request: ProviderRealRequest,
    hermes_home: str | None,
    audit_links: list[str],
) -> tuple[ProviderRealToolCall, ...]:
    """Classify provider tool calls against the read-only allowlist.

    Phase 3B does NOT execute them; valid calls are marked ``parsed`` and
    blocked calls get their precise reason. Execution through the controlled
    chain is a future, separately-authorized step.
    """
    out: list[ProviderRealToolCall] = []
    for call in raw_calls:
        if not isinstance(call, Mapping):
            continue
        tool_id = call.get("name")
        call_id = str(call.get("id") or "")
        arguments = call.get("arguments") if isinstance(call.get("arguments"), Mapping) else {}
        allowed, reason = classify_provider_tool_call(tool_id, arguments)
        if allowed:
            audit_links.append(write_real_tool_call_requested(
                hermes_home=hermes_home, config=config, request=request,
                response_id=request.request_id, tool_call_id=call_id, tool_id=str(tool_id),
                workflow_id=request.workflow_id,
            ) or "")
            out.append(ProviderRealToolCall(
                tool_call_id=call_id, tool_id=str(tool_id),
                arguments=dict(arguments), status="parsed", blocked_reason=None,
            ))
        else:
            audit_links.append(write_real_tool_call_blocked(
                hermes_home=hermes_home, config=config, request=request,
                response_id=request.request_id, tool_call_id=call_id, tool_id=str(tool_id),
                blocked_reason=reason or BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
                workflow_id=request.workflow_id,
            ) or "")
            out.append(ProviderRealToolCall(
                tool_call_id=call_id, tool_id=str(tool_id),
                arguments={}, status="blocked",
                blocked_reason=reason or BLOCKED_PROVIDER_TOOL_CALL_NOT_ALLOWED,
            ))
    return tuple(out)


def _rebuild_response_from_safe(
    response: ProviderRealResponse, safe: Mapping[str, Any],
) -> ProviderRealResponse:
    """Rebuild the response from its re-redacted projection (defense-in-depth).

    The redactor may have masked secret-bearing fields to ``[REDACTED]``; we
    carry the redacted projection forward so nothing secret survives.
    """
    content = safe.get("contentSummary", response.content_summary)
    if not isinstance(content, str):
        content = ""
    return ProviderRealResponse(
        request_id=response.request_id,
        response_id=response.response_id,
        provider_name=response.provider_name,
        model=response.model,
        status=response.status,
        content_summary=content,
        tool_calls=response.tool_calls,
        usage_summary=response.usage_summary,
        finish_reason=response.finish_reason,
        blocked_reason=response.blocked_reason,
        audit_links=response.audit_links,
        redaction_applied=True,
        external_network_called=response.external_network_called,
        cost_estimate=response.cost_estimate,
    )


__all__ = [
    "build_real_request_from_message",
    "preview_real_request",
    "run_real_provider_roundtrip_controlled",
]
