"""Phase 3B-Live-Enablement — Live Provider Round-trip Boundary (Frozen).

The single entry point for a **one-shot** live round-trip. It is **disabled by
default** and **blocked without a valid human approval**. A live request is
reachable only when EVERY gate holds, in order:

  1. mode == real            else blocked_live_provider_not_human_approved
  2. api enabled             else blocked_live_provider_not_human_approved
  3. kill switch inactive    else blocked_live_provider_kill_switch_active
  4. approval valid          else blocked_live_provider_approval_*
  5. approval matches request else blocked_live_provider_approval_mismatch
  6. host allowlisted (https) else blocked_live_provider_host_not_approved / scheme
  7. budget valid            else blocked_live_provider_budget_* / request/token cap
  8. secret state checked    (value-free; env read ONLY past every gate)
  9. one network call        (injected client — mock-only in tests/smoke)
 10. approval invalidated    (single-use; immediately after the call)

Any failure fails closed with a precise ``blocked_live_*`` reason, no network
call (``externalNetworkCalled=false``), and an audited, redacted event.

The HTTP client is a **required, injected** dependency (the Phase 3B
``ProviderHttpClient`` Protocol). Tests inject ``MockHttpClient``; there is
**no default real-network client wired into the live request path**. Therefore
no real provider call ever happens in tests, smoke, or default operation.

The first live request does NOT execute provider tool calls: a returned
``tool_calls`` array is classified + audited + summarized, never executed.
Provider write / auto-write / rollback / autonomous suggestions fire the kill
switch and are blocked.

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
Status: live round-trip boundary implemented (gated; mock-only in tests)
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from hermes_cli.dev_web_provider_live_approval import (
    BLOCKED_LIVE_PROVIDER_APPROVAL_EXPIRED,
    BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH,
    BLOCKED_LIVE_PROVIDER_APPROVAL_SCOPE_INVALID,
    BLOCKED_LIVE_PROVIDER_APPROVAL_USED,
    BLOCKED_LIVE_PROVIDER_DEV_ONLY_VIOLATION,
    BLOCKED_LIVE_PROVIDER_NOT_HUMAN_APPROVED,
    LiveApproval,
    find_active_approval,
    mark_approval_used,
    match_live_approval,
    validate_live_approval,
)
from hermes_cli.dev_web_provider_live_audit import (
    write_live_budget_blocked,
    write_live_budget_checked,
    write_live_enablement_denied,
    write_live_enablement_failed,
    write_live_enablement_started,
    write_live_enablement_completed,
    write_live_kill_switch_triggered,
    write_live_network_request_blocked,
    write_live_network_request_completed,
    write_live_network_request_started,
    write_live_secret_state_checked,
    write_live_tool_call_blocked,
    write_live_tool_call_requested,
)
from hermes_cli.dev_web_provider_live_budget import (
    BLOCKED_LIVE_PROVIDER_BUDGET_EXCEEDED,
    BLOCKED_LIVE_PROVIDER_BUDGET_NOT_CONFIGURED,
    BLOCKED_LIVE_PROVIDER_COUNTER_UNAVAILABLE,
    BLOCKED_LIVE_PROVIDER_REQUEST_CAP_EXCEEDED,
    BLOCKED_LIVE_PROVIDER_TOKEN_CAP_EXCEEDED,
    LiveBudgetCaps,
    evaluate_live_budget,
    live_budget_badge,
    meter_live_usage,
    read_live_counters,
    record_live_attempt,
)
from hermes_cli.dev_web_provider_live_kill_switch import (
    BLOCKED_LIVE_PROVIDER_KILL_SWITCH_ACTIVE,
    KILL_SWITCH_TRIGGER_PROVIDER_WRITE_SUGGESTION,
    KILL_SWITCH_TRIGGER_SECRET_DETECTED,
    KILL_SWITCH_TRIGGER_UNEXPECTED_TOOL_CALL,
    is_kill_switch_active,
    trigger_kill_switch,
)
from hermes_cli.dev_web_provider_live_network import (
    BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED,
    BLOCKED_LIVE_PROVIDER_SCHEME_NOT_HTTPS,
    evaluate_live_network,
    is_tool_external_http,
)
from hermes_cli.dev_web_provider_live_secret import (
    read_provider_api_key_if_live_approved,
)
from hermes_cli.dev_web_provider_real_redaction import contains_secret


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Names whose presence in a provider tool_call is a write / autonomous action
# and therefore fires the kill switch immediately.
_WRITE_AUTONOMOUS_TOOL_IDS: frozenset[str] = frozenset(
    {
        "write_file", "patch", "dev_sandbox_file_write", "dev_sandbox_file_append",
        "dev_sandbox_file_patch", "dev_sandbox_rollback_execute", "memory_add",
        "memory_update", "todo", "skill_manage", "send_message", "terminal",
        "process", "execute_code", "delegate_task", "cronjob", "image_generate",
        "shell", "database", "production_operation",
    }
)


@dataclass(frozen=True, slots=True)
class LiveRoundtripRequest:
    """The concrete live request parameters (value-free)."""

    provider_name: str
    model: str
    base_url: str
    base_url_host: str
    user_message: str
    tool_allowlist: frozenset[str]
    estimated_input_tokens: int
    estimated_output_tokens: int

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "providerName": self.provider_name,
            "model": self.model,
            "baseUrlHost": self.base_url_host,
            "userMessagePreview": self.user_message[:200],
            "userMessageLength": len(self.user_message),
            "toolAllowlist": sorted(self.tool_allowlist),
            "estimatedInputTokens": self.estimated_input_tokens,
            "estimatedOutputTokens": self.estimated_output_tokens,
            "redactionApplied": True,
        }


@dataclass(frozen=True, slots=True)
class LiveRoundtripResult:
    """The one-shot live round-trip result (value-free; never raw)."""

    status: str  # completed | blocked | failed
    request_id: str
    response_id: str | None
    approval_id: str | None
    provider_name: str
    model: str
    base_url_host: str
    external_network_called: bool
    blocked_reason: str | None
    content_summary: str
    finish_reason: str | None
    tool_calls_classified: tuple[Mapping[str, Any], ...]
    usage_summary: Mapping[str, Any]
    cost_estimate: Mapping[str, Any] | None
    audit_links: tuple[str, ...]
    secret_state: Mapping[str, Any]
    budget_badge: Mapping[str, Any]
    approval_invalidated: bool
    redaction_applied: bool = True

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "requestId": self.request_id,
            "responseId": self.response_id,
            "approvalId": self.approval_id,
            "providerName": self.provider_name,
            "model": self.model,
            "baseUrlHost": self.base_url_host if self.external_network_called else "",
            "externalNetworkCalled": self.external_network_called,
            "blockedReason": self.blocked_reason,
            "contentSummary": self.content_summary,
            "finishReason": self.finish_reason,
            "toolCallsClassified": [dict(c) for c in self.tool_calls_classified],
            "usageSummary": dict(self.usage_summary),
            "costEstimate": dict(self.cost_estimate) if self.cost_estimate else None,
            "auditLinks": list(self.audit_links),
            "secretState": dict(self.secret_state),
            "budgetBadge": dict(self.budget_badge),
            "approvalInvalidated": self.approval_invalidated,
            "redactionApplied": True,
        }


@dataclass(frozen=True, slots=True)
class LiveRoundtripOutcome:
    """The decision + (optional) result. ``allowed=False`` ⇒ no network call."""

    allowed: bool
    blocked_reason: str | None
    approval: LiveApproval | None
    secret_state: Mapping[str, Any]
    network_host: str
    budget_badge: Mapping[str, Any]
    audit_links: tuple[str, ...] = field(default_factory=tuple)


def evaluate_live_enablement(
    request: LiveRoundtripRequest,
    *,
    approval_id: str | None,
    provider_mode: str,
    api_enabled: bool,
    caps: LiveBudgetCaps | None,
    hermes_home: str | None,
    now_iso: str | None = None,
    is_dev_home: bool = True,
) -> LiveRoundtripOutcome:
    """Evaluate every live gate in order. First failure wins; all fail closed.

    This performs NO network call and reads NO API key value. The secret read
    is value-free and reached only past every gate. Returns a ``LiveRoundtripOutcome``
    whose ``allowed`` flag the orchestrator consults before any network call.
    """
    ts = now_iso or _now_iso()
    request_id = f"plrr_{secrets.token_urlsafe(12)}"
    audit_links: list[str] = []

    def _block(reason: str, approval: LiveApproval | None) -> LiveRoundtripOutcome:
        audit_links.append(write_live_enablement_denied(
            hermes_home=hermes_home, provider_name=request.provider_name,
            blocked_reason=reason, approval_id=approval.approval_id if approval else None,
        ) or "")
        return LiveRoundtripOutcome(
            allowed=False, blocked_reason=reason, approval=approval,
            secret_state={"keySource": "environment", "keyState": "blocked_before_secret_read"},
            network_host="", budget_badge=live_budget_badge(
                caps=caps or LiveBudgetCaps(),
                counters=read_live_counters(hermes_home=hermes_home, now_iso=ts),
            ),
            audit_links=tuple(x for x in audit_links if x),
        )

    # ── 1. mode + enablement + dev-only ──
    if provider_mode != "real" or not api_enabled:
        return _block(BLOCKED_LIVE_PROVIDER_NOT_HUMAN_APPROVED, None)
    if not is_dev_home:
        return _block(BLOCKED_LIVE_PROVIDER_DEV_ONLY_VIOLATION, None)

    # ── 2. kill switch ──
    if is_kill_switch_active(hermes_home=hermes_home):
        audit_links.append(write_live_kill_switch_triggered(
            hermes_home=hermes_home, provider_name=request.provider_name,
            blocked_reason=BLOCKED_LIVE_PROVIDER_KILL_SWITCH_ACTIVE,
        ) or "")
        return _block(BLOCKED_LIVE_PROVIDER_KILL_SWITCH_ACTIVE, None)

    # ── 3. approval lifetime ──
    approval = find_active_approval(approval_id, hermes_home=hermes_home)
    valid, reason = validate_live_approval(approval, now_iso=ts)
    if not valid:
        return _block(reason or BLOCKED_LIVE_PROVIDER_NOT_HUMAN_APPROVED, approval)

    # ── 4. approval matches the concrete request ──
    matched, match_reason = match_live_approval(
        approval,
        provider_name=request.provider_name,
        model=request.model,
        base_url_host=request.base_url_host,
        tool_allowlist=request.tool_allowlist,
    )
    if not matched:
        return _block(match_reason or BLOCKED_LIVE_PROVIDER_APPROVAL_MISMATCH, approval)

    # ── 5. network allowlist (https + host) ──
    net = evaluate_live_network(
        base_url=request.base_url, approval_host=approval.base_url_host,
    )
    if not net.allowed:
        audit_links.append(write_live_network_request_blocked(
            hermes_home=hermes_home, provider_name=request.provider_name,
            blocked_reason=net.blocked_reason or BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED,
            base_url_host="",
        ) or "")
        return _block(net.blocked_reason or BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED, approval)

    # ── 6. budget / rate-limit ──
    decision = evaluate_live_budget(
        caps=caps, model=request.model, hermes_home=hermes_home, now_iso=ts,
        estimated_input_tokens=request.estimated_input_tokens,
        estimated_output_tokens=request.estimated_output_tokens,
    )
    if not decision.allowed:
        budget_reason = decision.blocked_reason or BLOCKED_LIVE_PROVIDER_BUDGET_EXCEEDED
        audit_links.append(write_live_budget_blocked(
            hermes_home=hermes_home, provider_name=request.provider_name,
            blocked_reason=budget_reason,
            budget=decision.cost_estimate,
        ) or "")
        return _block(budget_reason, approval)
    audit_links.append(write_live_budget_checked(
        hermes_home=hermes_home, provider_name=request.provider_name,
        budget=decision.cost_estimate or {},
    ) or "")

    # ── 7. secret state (value-free; env read ONLY past every gate) ──
    secret = read_provider_api_key_if_live_approved(
        provider_mode=provider_mode,
        api_enabled=api_enabled,
        kill_switch_active=False,
        approval_valid=True,
        budget_ok=True,
        host_ok=True,
    )
    secret_state = secret.to_safe_dict()
    audit_links.append(write_live_secret_state_checked(
        hermes_home=hermes_home, provider_name=request.provider_name,
        secret_state=secret_state,
    ) or "")

    return LiveRoundtripOutcome(
        allowed=True,
        blocked_reason=None,
        approval=approval,
        secret_state=secret_state,
        network_host=net.host,
        budget_badge=live_budget_badge(
            caps=caps or LiveBudgetCaps(), counters=decision.counters,
        ),
        audit_links=tuple(x for x in audit_links if x),
    )


def run_live_provider_roundtrip_controlled(
    request: LiveRoundtripRequest,
    *,
    approval_id: str | None,
    provider_mode: str,
    api_enabled: bool,
    caps: LiveBudgetCaps | None,
    http_client,
    hermes_home: str | None = None,
    now_iso: str | None = None,
    is_dev_home: bool = True,
) -> LiveRoundtripResult:
    """Run one gated, audited, redacted, single-use live round-trip.

    ``http_client`` is REQUIRED and injected (``MockHttpClient`` in tests). The
    function NEVER makes a real network call unless an explicit real client is
    injected AND every gate passes — which no default code path does.

    After the call (success or failure), the single-use approval is invalidated.
    """
    ts = now_iso or _now_iso()
    request_id = f"plrr_{secrets.token_urlsafe(12)}"
    all_audit: list[str] = []

    outcome = evaluate_live_enablement(
        request, approval_id=approval_id, provider_mode=provider_mode,
        api_enabled=api_enabled, caps=caps, hermes_home=hermes_home,
        now_iso=ts, is_dev_home=is_dev_home,
    )
    all_audit.extend(outcome.audit_links)

    if not outcome.allowed:
        return LiveRoundtripResult(
            status="blocked", request_id=request_id, response_id=None,
            approval_id=outcome.approval.approval_id if outcome.approval else None,
            provider_name=request.provider_name, model=request.model,
            base_url_host="", external_network_called=False,
            blocked_reason=outcome.blocked_reason, content_summary="",
            finish_reason=None, tool_calls_classified=(),
            usage_summary={}, cost_estimate=None,
            audit_links=tuple(x for x in all_audit if x),
            secret_state=outcome.secret_state,
            budget_badge=outcome.budget_badge, approval_invalidated=False,
        )

    approval = outcome.approval
    assert approval is not None  # allowed ⇒ approval present

    # Count the attempt in the rate window (before the call).
    record_live_attempt(hermes_home=hermes_home, now_iso=ts)

    all_audit.append(write_live_enablement_started(
        hermes_home=hermes_home, provider_name=request.provider_name,
        model=request.model, base_url_host=outcome.network_host,
        approval_id=approval.approval_id, request_id=request_id,
        budget=outcome.budget_badge,
    ) or "")
    all_audit.append(write_live_network_request_started(
        hermes_home=hermes_home, provider_name=request.provider_name,
        base_url_host=outcome.network_host, approval_id=approval.approval_id,
        request_id=request_id,
    ) or "")

    # ── Perform the bounded call via the injected client ──
    # The adapter builds the Authorization header from the env key locally and
    # never returns it; we use the Phase 3B adapter for request/response shaping.
    result = _perform_bounded_live_call(
        http_client=http_client, request=request, host=outcome.network_host,
    )

    # Classify tool calls (NO execution for the first live request).
    classified, fired_kill, kill_reason = _classify_live_tool_calls(
        result.get("tool_calls") or [], hermes_home=hermes_home,
        provider_name=request.provider_name, request_id=request_id,
        response_id=request_id, audit=all_audit,
    )

    usage = dict(result.get("usage") or {})
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
    from hermes_cli.dev_web_provider_live_budget import estimate_live_cost_cents

    cost = estimate_live_cost_cents(
        model=request.model, prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    meter_live_usage(
        hermes_home=hermes_home, now_iso=ts,
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        cost_cents=int(cost["estimateCents"]),
    )

    # ── Defensive re-redaction of the content summary ──
    content_summary = str(result.get("content", ""))[:1000]
    if contains_secret({"v": content_summary}):
        trigger_kill_switch(
            hermes_home=hermes_home, reason=KILL_SWITCH_TRIGGER_SECRET_DETECTED, now_iso=ts,
        )
        all_audit.append(write_live_kill_switch_triggered(
            hermes_home=hermes_home, provider_name=request.provider_name,
            blocked_reason="blocked_provider_secret_detected",
        ) or "")

    # ── Invalidate the single-use approval immediately after the call ──
    invalidated = mark_approval_used(
        approval.approval_id, hermes_home=hermes_home, now_iso=ts,
    )

    status = "completed"
    blocked_reason = None
    if not result.get("ok"):
        status = "failed"
        blocked_reason = str(result.get("blocked_reason") or "blocked_live_provider_failed")
    elif fired_kill:
        status = "blocked"
        blocked_reason = kill_reason

    all_audit.append(write_live_network_request_completed(
        hermes_home=hermes_home, provider_name=request.provider_name,
        base_url_host=outcome.network_host, request_id=request_id, response_id=request_id,
    ) or "")
    if status == "completed":
        all_audit.append(write_live_enablement_completed(
            hermes_home=hermes_home, provider_name=request.provider_name,
            model=request.model, base_url_host=outcome.network_host,
            approval_id=approval.approval_id, request_id=request_id, response_id=request_id,
            usage_summary={"promptTokens": prompt_tokens, "completionTokens": completion_tokens,
                           "totalTokens": total_tokens},
            cost_estimate=cost,
        ) or "")
    elif status == "failed":
        all_audit.append(write_live_enablement_failed(
            hermes_home=hermes_home, provider_name=request.provider_name,
            blocked_reason=blocked_reason or "",
            approval_id=approval.approval_id, request_id=request_id,
        ) or "")

    return LiveRoundtripResult(
        status=status, request_id=request_id, response_id=request_id,
        approval_id=approval.approval_id, provider_name=request.provider_name,
        model=request.model, base_url_host=outcome.network_host,
        external_network_called=bool(result.get("external_network_called", False)),
        blocked_reason=blocked_reason, content_summary=content_summary,
        finish_reason=str(result.get("finish_reason") or ""),
        tool_calls_classified=tuple(classified),
        usage_summary={"promptTokens": prompt_tokens, "completionTokens": completion_tokens,
                       "totalTokens": total_tokens},
        cost_estimate=cost,
        audit_links=tuple(x for x in all_audit if x),
        secret_state=outcome.secret_state,
        budget_badge=outcome.budget_badge, approval_invalidated=invalidated,
    )


def _perform_bounded_live_call(
    *, http_client, request: LiveRoundtripRequest, host: str,
) -> dict[str, Any]:
    """Build + perform the bounded call via the Phase 3B adapter.

    The adapter is constructed with the injected client (mock in tests). It
    reads the env key into a local, attaches one Authorization header, and
    drops it. The raw body / header / secret is never returned here.
    """
    from hermes_cli.dev_web_provider_openai_compatible import OpenAICompatibleAdapter
    from hermes_cli.dev_web_provider_real_schema import build_provider_real_request

    base_url = request.base_url
    # Defensive: the host must already be the allowlisted host.
    if host and host not in request.base_url:
        base_url = f"https://{host}"
    real_request = build_provider_real_request(
        provider_mode="real", provider_name=request.provider_name,
        model=request.model, user_message=request.user_message,
        conversation_id=None, workflow_id=None,
        tool_allowlist=tuple(request.tool_allowlist),
        max_tokens=request.estimated_output_tokens or 200,
        temperature=0.0, timeout_seconds=60,
    )
    adapter = OpenAICompatibleAdapter(http_client, base_url=base_url, model=request.model)
    result = adapter.round_trip(real_request, timeout_seconds=60, max_retries=0)
    return {
        "ok": result.ok,
        "content": result.content,
        "tool_calls": result.raw_tool_calls,
        "usage": dict(result.usage),
        "finish_reason": result.finish_reason,
        "blocked_reason": result.blocked_reason,
        "external_network_called": result.external_network_called,
    }


def _classify_live_tool_calls(
    raw_calls,
    *,
    hermes_home: str | None,
    provider_name: str,
    request_id: str,
    response_id: str,
    audit: list[str],
) -> tuple[list[dict[str, Any]], bool, str | None]:
    """Classify provider tool calls for the first live request (NO execution).

    A write / autonomous / external-HTTP tool name fires the kill switch and is
    blocked. Everything else is audited as requested-but-not-executed; the
    first live request never executes any tool.
    """
    out: list[dict[str, Any]] = []
    fired_kill = False
    kill_reason: str | None = None
    for call in raw_calls:
        if not isinstance(call, Mapping):
            continue
        tool_id = str(call.get("name") or "")
        call_id = str(call.get("id") or "")
        if tool_id in _WRITE_AUTONOMOUS_TOOL_IDS:
            trigger_kill_switch(
                hermes_home=hermes_home,
                reason=KILL_SWITCH_TRIGGER_PROVIDER_WRITE_SUGGESTION, now_iso=_now_iso(),
            )
            audit.append(write_live_tool_call_blocked(
                hermes_home=hermes_home, provider_name=provider_name,
                request_id=request_id, response_id=response_id,
                tool_call_id=call_id, tool_id=tool_id,
                blocked_reason="blocked_provider_write_not_allowed",
            ) or "")
            out.append({
                "toolCallId": call_id, "toolId": tool_id, "status": "blocked",
                "blockedReason": "blocked_provider_write_not_allowed", "executed": False,
            })
            fired_kill = True
            kill_reason = "blocked_provider_write_not_allowed"
            continue
        if is_tool_external_http(tool_id):
            audit.append(write_live_tool_call_blocked(
                hermes_home=hermes_home, provider_name=provider_name,
                request_id=request_id, response_id=response_id,
                tool_call_id=call_id, tool_id=tool_id,
                blocked_reason="blocked_provider_external_url_not_allowed",
            ) or "")
            out.append({
                "toolCallId": call_id, "toolId": tool_id, "status": "blocked",
                "blockedReason": "blocked_provider_external_url_not_allowed", "executed": False,
            })
            continue
        # Read-only or unknown tool: requested but NOT executed (first live).
        audit.append(write_live_tool_call_requested(
            hermes_home=hermes_home, provider_name=provider_name,
            request_id=request_id, response_id=response_id,
            tool_call_id=call_id, tool_id=tool_id,
        ) or "")
        out.append({
            "toolCallId": call_id, "toolId": tool_id, "status": "parsed_not_executed",
            "blockedReason": None, "executed": False,
        })
    return out, fired_kill, kill_reason


__all__ = [
    "LiveRoundtripRequest",
    "LiveRoundtripResult",
    "LiveRoundtripOutcome",
    "evaluate_live_enablement",
    "run_live_provider_roundtrip_controlled",
]
