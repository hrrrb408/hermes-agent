"""Phase 2B Provider Round-trip Orchestrator for the Hermes Dev WebUI.

This module orchestrates the controlled Provider Schema / API round-trip:

  1. build the provider schema (Phase 2A read-only tools only)
  2. build the controlled provider request (disabled / fake / real)
  3. audit the schema + request
  4. if the request is blocked (e.g. real mode not enabled) → return blocked
  5. invoke the provider adapter (fake by default)
  6. audit the provider response
  7. parse + validate every emitted tool call against the allowlist
  8. for each valid tool call, run it through the EXISTING controlled
     execution chain (dry-run → digest → confirmation token → pre-execution
     audit → handler lookup → dispatch → handler call → post-execution audit)
  9. audit each tool call + tool result
 10. feed the tool results back to the fake provider for a final answer
 11. audit the final response
 12. return a unified result envelope

Critical invariants:
  - Provider-requested tool calls NEVER bypass the controlled execution chain.
  - Only allowlisted, read-only, side-effect-free tools may be executed.
  - Unknown / write-like / provider-recursive / malformed calls are blocked.
  - Fake provider round-trips may use internal confirmation (read-only only);
    real provider round-trips are blocked at preview in Phase 2B.
  - No API key is ever logged, audited, or returned.

Phase: 2B — Provider Schema / API Controlled Integration
Status: provider round-trip orchestrator implemented
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from hermes_cli.dev_web_provider_adapter import (
    FINISH_REASON_BLOCKED,
    ProviderResponse,
    ProviderToolCall,
    get_provider_adapter,
)
from hermes_cli.dev_web_provider_audit import (
    write_provider_final_response_audit,
    write_provider_request_audit,
    write_provider_response_audit,
    write_provider_schema_audit,
    write_provider_tool_call_audit,
    write_provider_tool_result_audit,
)
from hermes_cli.dev_web_provider_request import (
    ProviderRequest,
    PROVIDER_MODE_DISABLED,
    PROVIDER_MODE_FAKE,
    build_provider_request,
    normalize_provider_mode,
    redact_provider_request_for_audit,
)
from hermes_cli.dev_web_provider_schema import (
    build_provider_request_schema_summary,
    build_provider_tool_schema,
    redact_provider_schema_for_audit,
    validate_provider_schema_bundle,
)


# ---------------------------------------------------------------------------
# 1. Constants + validation
# ---------------------------------------------------------------------------

# Tool call validation outcomes.
TOOL_CALL_VALID = "valid"
TOOL_CALL_BLOCKED_UNKNOWN_TOOL = "blocked_unknown_tool"
TOOL_CALL_BLOCKED_WRITE_LIKE = "blocked_write_like_tool"
TOOL_CALL_BLOCKED_PROVIDER_RECURSIVE = "blocked_provider_recursive_tool"
TOOL_CALL_BLOCKED_MALFORMED_ARGS = "blocked_malformed_arguments"
TOOL_CALL_BLOCKED_NOT_ALLOWLISTED = "blocked_not_allowlisted"

# Names that look like write tools (defense-in-depth — they are not in the
# allowlist anyway, but the provider is untrusted input).
_WRITE_LIKE_NAMES: frozenset[str] = frozenset(
    {
        "write_file", "patch", "memory", "todo", "skill_manage",
        "send_message", "terminal", "process", "execute_code", "delegate_task",
        "cronjob", "image_generate", "text_to_speech", "video_generate",
    }
)

_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
)


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        for pattern in _SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                return "[REDACTED]"
        return value
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


@dataclass(frozen=True, slots=True)
class ParsedToolCall:
    """A parsed + validated provider tool call."""

    id: str
    name: str
    arguments: Mapping[str, Any]
    status: str  # TOOL_CALL_VALID or a blocked_* code
    blocked_reason: str | None

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": _redact_value(dict(self.arguments)),
            "status": self.status,
            "blockedReason": self.blocked_reason,
        }


def validate_provider_tool_call(
    raw_call: Mapping[str, Any] | ProviderToolCall,
    *,
    allowlist: frozenset[str],
) -> ParsedToolCall:
    """Validate a single provider tool call against the boundary.

    Checks (in order):
      - well-formed id / name / arguments
      - name is in the allowlist (not unknown, not non-allowlisted)
      - name is not a write-like tool
      - name is not a provider-recursive tool
      - arguments are JSON-serializable and free of secret patterns
    """
    if isinstance(raw_call, ProviderToolCall):
        call_id = raw_call.id
        name = raw_call.name
        arguments = dict(raw_call.arguments)
    elif isinstance(raw_call, Mapping):
        call_id = raw_call.get("id")
        name = raw_call.get("name")
        arguments = raw_call.get("arguments", {})
    else:
        return ParsedToolCall(
            id="", name="", arguments={},
            status=TOOL_CALL_BLOCKED_MALFORMED_ARGS,
            blocked_reason="tool call is not a mapping",
        )

    if not isinstance(call_id, str) or not call_id.strip():
        return ParsedToolCall(
            id="", name=str(name) if name else "", arguments={},
            status=TOOL_CALL_BLOCKED_MALFORMED_ARGS,
            blocked_reason="tool call id missing",
        )
    if not isinstance(name, str) or not name.strip():
        return ParsedToolCall(
            id=call_id, name="", arguments={},
            status=TOOL_CALL_BLOCKED_MALFORMED_ARGS,
            blocked_reason="tool call name missing",
        )
    if not isinstance(arguments, Mapping):
        return ParsedToolCall(
            id=call_id, name=name, arguments={},
            status=TOOL_CALL_BLOCKED_MALFORMED_ARGS,
            blocked_reason="arguments are not an object",
        )

    # JSON-serializable + bounded?
    try:
        rendered = json.dumps(arguments, ensure_ascii=False)
    except (TypeError, ValueError):
        return ParsedToolCall(
            id=call_id, name=name, arguments={},
            status=TOOL_CALL_BLOCKED_MALFORMED_ARGS,
            blocked_reason="arguments are not JSON-serializable",
        )
    if len(rendered) > 32 * 1024:
        return ParsedToolCall(
            id=call_id, name=name, arguments={},
            status=TOOL_CALL_BLOCKED_MALFORMED_ARGS,
            blocked_reason="arguments exceed size limit",
        )
    for pattern in _SECRET_VALUE_PATTERNS:
        if pattern.search(rendered):
            return ParsedToolCall(
                id=call_id, name=name, arguments={},
                status=TOOL_CALL_BLOCKED_MALFORMED_ARGS,
                blocked_reason="arguments contain a secret pattern",
            )

    # Allowlist gate (the authoritative boundary).
    if name not in allowlist:
        if name in _WRITE_LIKE_NAMES:
            return ParsedToolCall(
                id=call_id, name=name, arguments=dict(arguments),
                status=TOOL_CALL_BLOCKED_WRITE_LIKE,
                blocked_reason=f"write-like tool {name!r} is not permitted",
            )
        return ParsedToolCall(
            id=call_id, name=name, arguments=dict(arguments),
            status=TOOL_CALL_BLOCKED_NOT_ALLOWLISTED,
            blocked_reason=f"tool {name!r} is not on the read-only allowlist",
        )

    # Provider-recursive guard: a provider tool must not invoke the provider
    # round-trip itself.
    if "provider" in name.lower() and name not in allowlist:
        return ParsedToolCall(
            id=call_id, name=name, arguments=dict(arguments),
            status=TOOL_CALL_BLOCKED_PROVIDER_RECURSIVE,
            blocked_reason="provider-recursive tool call blocked",
        )

    return ParsedToolCall(
        id=call_id, name=name, arguments=dict(arguments),
        status=TOOL_CALL_VALID, blocked_reason=None,
    )


def parse_provider_tool_calls(
    response: ProviderResponse,
    *,
    allowlist: frozenset[str],
) -> tuple[ParsedToolCall, ...]:
    """Parse + validate every tool call in a provider response."""
    parsed: list[ParsedToolCall] = []
    for call in response.tool_calls:
        parsed.append(validate_provider_tool_call(call, allowlist=allowlist))
    return tuple(parsed)


# ---------------------------------------------------------------------------
# 2. Controlled-chain execution of one provider tool call
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def execute_provider_tool_call_via_controlled_chain(
    parsed: ParsedToolCall,
    *,
    hermes_home: str | None,
    provider_request_id: str,
    provider_response_id: str,
    sequence: int,
) -> dict[str, Any]:
    """Run one validated provider tool call through the full controlled chain.

    Reuses the Phase 1G/2A chain end-to-end:
      dry-run → digest → dry-run audit write → confirmation token →
      pre-execution audit → handler lookup → dispatch → handler call →
      post-execution audit.

    Returns a safe dict describing the executed (or blocked) tool call. The
    controlled chain enforces all kill-switch, allowlist, digest, and audit
    gates; this function only wires the inputs.
    """
    from hermes_cli.dev_web_tool_dry_run import dry_run_tool_policy
    from hermes_cli.dev_web_tool_dry_run_audit import (
        build_dry_run_audit_event,
        write_dry_run_audit_event,
    )
    from hermes_cli.dev_web_tool_execute import evaluate_tool_execute_request
    from hermes_cli.dev_web_tool_execute_confirmation import issue_confirmation_token
    from hermes_cli.dev_web_tool_execute_digest import (
        DIGEST_ALGORITHM,
        DIGEST_PACKAGE_VERSION,
        CANONICALIZATION_VERSION,
        build_dry_run_decision_digest_package,
    )
    from hermes_cli.dev_web_tool_execute_preflight import (
        DryRunHistoricalLookupResult,
        _DRY_RUN_TTL_SECONDS,
    )

    tool_id = parsed.name
    arguments = dict(parsed.arguments)
    request_id = f"prqs-{provider_request_id}-tc{sequence}-{tool_id}"

    # 1. Dry-run evaluation (pure).
    dry = dry_run_tool_policy(tool_id, arguments)
    if dry.decision != "would_allow":
        return {
            "toolCallId": parsed.id,
            "toolId": tool_id,
            "status": "blocked",
            "blockedReason": f"dry_run_decision_{dry.decision}",
            "executed": False,
            "executeResult": None,
        }

    risk_tier = dry.risk_tier

    # 2. Build the dry-run audit event (digest computed consistently below).
    event = build_dry_run_audit_event(
        dry_run_result=dry,
        source_context="provider_roundtrip",
        ui_origin="dev-webui",
        request_id=request_id,
        duration_ms=0,
        result_status="ok",
        dry_run_decision_digest=None,
        digest_algorithm=None,
        digest_package_version=None,
        canonicalization_version=None,
    )

    # 3. Compute the digest from the real event id + timestamp (mirrors the
    #    Dev API dry-run handler so the execute-derived digest matches).
    created_at = event.get("timestamp")
    expires_at = None
    if isinstance(created_at, str) and created_at:
        try:
            expires_at = (
                datetime.fromisoformat(created_at) + timedelta(seconds=_DRY_RUN_TTL_SECONDS)
            ).isoformat()
        except ValueError:
            expires_at = None

    digest_pkg = build_dry_run_decision_digest_package(
        dry_run_request_id=request_id,
        canonical_name=tool_id,
        risk_tier=risk_tier,
        policy_decision=dry.decision,
        allowlisted=True,
        audit_written=True,
        audit_event_id=event.get("eventId"),
        arguments=arguments,
        created_at=created_at,
        expires_at=expires_at,
    )
    digest = digest_pkg.digest if digest_pkg.success else None
    event["dryRunDecisionDigest"] = digest
    event["digestAlgorithm"] = DIGEST_ALGORITHM if digest_pkg.success else None
    event["digestPackageVersion"] = DIGEST_PACKAGE_VERSION if digest_pkg.success else None
    event["canonicalizationVersion"] = CANONICALIZATION_VERSION if digest_pkg.success else None

    # 4. Write the dry-run audit event (containment-guarded; never ~/.hermes).
    write_result = write_dry_run_audit_event(event, hermes_home=hermes_home)
    if not write_result.written:
        return {
            "toolCallId": parsed.id,
            "toolId": tool_id,
            "status": "blocked",
            "blockedReason": "dry_run_audit_write_failed",
            "executed": False,
            "executeResult": None,
        }
    audit_event_id = write_result.event_id

    # 5. Issue the confirmation token (internal confirmation; read-only only).
    record = DryRunHistoricalLookupResult(
        found=True,
        error_code=None,
        dry_run_request_id=request_id,
        canonical_name=tool_id,
        decision=dry.decision,
        risk_tier=risk_tier,
        policy_version=None,
        arguments_digest=None,
        dry_run_decision_digest=digest,
        audit_written=True,
        audit_event_id=audit_event_id,
        created_at=created_at,
        expires_at=expires_at,
        lookup_source="provider_roundtrip",
        redaction_status="none",
        safe_summary={},
    )
    token = issue_confirmation_token(
        hermes_home=hermes_home,
        dry_run_record=record,
        canonical_name=tool_id,
        risk_tier=risk_tier,
        dry_run_request_id=request_id,
        dry_run_decision_digest=digest,
        now=_now_utc(),
    )
    if not token.issued or not token.raw_token:
        return {
            "toolCallId": parsed.id,
            "toolId": tool_id,
            "status": "blocked",
            "blockedReason": f"confirmation_{token.error_code}",
            "executed": False,
            "executeResult": None,
        }

    # 6. Run the full execute gate (digest / pre-audit / dispatch / handler /
    #    post-audit). The kill-switch gates must be enabled by the caller.
    exec_result = evaluate_tool_execute_request(
        canonical_name=tool_id,
        arguments_preview=arguments,
        dry_run_request_id=request_id,
        dry_run_decision_digest=digest,
        confirmation_token=token.raw_token,
        request_id=f"exec-prqs-{provider_request_id}-tc{sequence}",
        hermes_home=hermes_home,
    )
    safe = exec_result.to_safe_dict()

    executed = bool(safe.get("executionCompleted"))
    return {
        "toolCallId": parsed.id,
        "toolId": tool_id,
        "status": "executed" if executed else "blocked",
        "blockedReason": None if executed else (safe.get("errorCode") or "execution_blocked"),
        "executed": executed,
        "executeResult": safe,
        "internalConfirmation": True,
        "readOnlyOnly": True,
        "providerRequestId": provider_request_id,
        "providerResponseId": provider_response_id,
    }


# ---------------------------------------------------------------------------
# 3. Unified result envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderRoundtripResult:
    status: str  # "completed" | "blocked"
    provider_mode: str
    provider_request_id: str
    provider_response_id: str | None
    provider_schema_sent: bool
    provider_api_called: bool
    external_network_called: bool
    read_only_only: bool
    tool_calls: tuple[dict[str, Any], ...]
    tool_results: tuple[dict[str, Any], ...]
    final_answer: str
    provider_audit_ids: tuple[str, ...]
    blocked_reason: str | None
    schema_summary: Mapping[str, Any] = field(default_factory=dict)

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "mode": "provider_roundtrip",
            "providerMode": self.provider_mode,
            "providerRequestId": self.provider_request_id,
            "providerResponseId": self.provider_response_id,
            "providerSchemaSent": self.provider_schema_sent,
            "providerApiCalled": self.provider_api_called,
            "externalNetworkCalled": self.external_network_called,
            "readOnlyOnly": self.read_only_only,
            "toolWriteDisabled": True,
            "toolCalls": list(self.tool_calls),
            "toolResults": list(self.tool_results),
            "finalAnswer": self.final_answer,
            "providerAuditIds": list(self.provider_audit_ids),
            "blockedReason": self.blocked_reason,
            "schemaSummary": dict(self.schema_summary),
        }


# ---------------------------------------------------------------------------
# 4. Top-level orchestrator
# ---------------------------------------------------------------------------


def run_provider_tool_roundtrip(
    user_message: str,
    provider_mode: str,
    *,
    selected_tool_ids: frozenset[str] | set[str] | None = None,
    context: Mapping[str, Any] | None = None,
    hermes_home: str | None = None,
    production_gate_override: bool | None = None,
) -> ProviderRoundtripResult:
    """Run the full controlled Provider round-trip.

    See module docstring for the step order. Default *provider_mode* is
    ``disabled``; tests / smoke pass ``fake``. Real mode is blocked unless
    fully enabled and is never auto-executed in Phase 2B.
    """
    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

    mode = normalize_provider_mode(provider_mode)
    audit_ids: list[str] = []

    # ── Step 1–2: schema + request ──
    bundle = build_provider_tool_schema(selected_tool_ids)
    schema_validation = validate_provider_schema_bundle(bundle)
    # The bundle is generated from the allowlist, so it is always valid;
    # a failure here would indicate a code regression. We still surface it.
    if not schema_validation.valid:
        return ProviderRoundtripResult(
            status="blocked",
            provider_mode=mode,
            provider_request_id="",
            provider_response_id=None,
            provider_schema_sent=False,
            provider_api_called=False,
            external_network_called=False,
            read_only_only=True,
            tool_calls=(),
            tool_results=(),
            final_answer="Provider schema failed boundary validation.",
            provider_audit_ids=tuple(audit_ids),
            blocked_reason="provider_schema_boundary_violation",
        )

    request = build_provider_request(
        user_message=user_message,
        provider_mode=mode,
        include_tool_schema=True,
        allowed_tool_ids=selected_tool_ids,
        context=context,
        production_gate_override=production_gate_override,
    )

    schema_summary = build_provider_request_schema_summary()

    # ── Step 3: audit schema + request ──
    audit_ids.append(write_provider_schema_audit(
        hermes_home=hermes_home,
        provider_request_id=request.provider_request_id,
        provider_mode=mode,
        schema_summary=redact_provider_schema_for_audit(bundle),
    ) or "")
    audit_ids.append(write_provider_request_audit(
        hermes_home=hermes_home,
        provider_request_id=request.provider_request_id,
        provider_mode=mode,
        request_summary=redact_provider_request_for_audit(request),
    ) or "")

    # ── Step 4: blocked request (e.g. real mode not enabled) ──
    if request.blocked or mode == PROVIDER_MODE_DISABLED:
        blocked_reason = request.blocked_reason
        if mode == PROVIDER_MODE_DISABLED:
            blocked_reason = "provider_mode_disabled"
        return ProviderRoundtripResult(
            status="blocked",
            provider_mode=mode,
            provider_request_id=request.provider_request_id,
            provider_response_id=None,
            provider_schema_sent=request.provider_schema_sent,
            provider_api_called=False,
            external_network_called=False,
            read_only_only=True,
            tool_calls=(),
            tool_results=(),
            final_answer=(
                "Provider mode is disabled or blocked. "
                "Phase 2A manual tool execution remains available."
            ),
            provider_audit_ids=tuple(x for x in audit_ids if x),
            blocked_reason=blocked_reason,
            schema_summary=schema_summary,
        )

    # ── Step 5: invoke the adapter ──
    adapter = get_provider_adapter(mode)
    response: ProviderResponse = adapter.invoke(request)

    # ── Step 6: audit the response ──
    audit_ids.append(write_provider_response_audit(
        hermes_home=hermes_home,
        provider_request_id=request.provider_request_id,
        provider_response_id=response.provider_response_id,
        provider_mode=mode,
        response_summary={
            "finishReason": response.finish_reason,
            "toolCallCount": len(response.tool_calls),
            "toolCallNames": [c.name for c in response.tool_calls],
            "blocked": response.blocked,
            "blockedReason": response.blocked_reason,
            "assistantMessagePreview": response.assistant_message[:160],
        },
    ) or "")

    # Adapter-level block (e.g. real provider not wired).
    if response.blocked:
        return ProviderRoundtripResult(
            status="blocked",
            provider_mode=mode,
            provider_request_id=request.provider_request_id,
            provider_response_id=response.provider_response_id,
            provider_schema_sent=request.provider_schema_sent,
            provider_api_called=False,
            external_network_called=False,
            read_only_only=True,
            tool_calls=(),
            tool_results=(),
            final_answer=response.assistant_message,
            provider_audit_ids=tuple(x for x in audit_ids if x),
            blocked_reason=response.blocked_reason,
            schema_summary=schema_summary,
        )

    # ── Step 7: parse + validate tool calls ──
    allowlist = STATIC_ALLOWLIST
    parsed_calls = parse_provider_tool_calls(response, allowlist=allowlist)

    tool_calls_view: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    executed_ids: list[str] = []
    blocked_ids: list[str] = []

    for sequence, parsed in enumerate(parsed_calls):
        # Audit the parsed call (valid or blocked).
        audit_ids.append(write_provider_tool_call_audit(
            hermes_home=hermes_home,
            provider_request_id=request.provider_request_id,
            provider_response_id=response.provider_response_id,
            provider_mode=mode,
            tool_call_id=parsed.id,
            tool_id=parsed.name,
            status=parsed.status if parsed.status == TOOL_CALL_VALID else "blocked",
            blocked_reason=parsed.blocked_reason,
            summary={"argumentsKeys": sorted(parsed.arguments.keys())},
        ) or "")

        tool_calls_view.append(parsed.to_safe_dict())

        if parsed.status != TOOL_CALL_VALID:
            blocked_ids.append(parsed.name)
            tool_results.append({
                "toolCallId": parsed.id,
                "toolId": parsed.name,
                "status": "blocked",
                "blockedReason": parsed.blocked_reason,
                "executed": False,
            })
            continue

        # ── Step 8: execute via the existing controlled chain ──
        result = execute_provider_tool_call_via_controlled_chain(
            parsed,
            hermes_home=hermes_home,
            provider_request_id=request.provider_request_id,
            provider_response_id=response.provider_response_id,
            sequence=sequence,
        )

        # Audit the tool result.
        audit_ids.append(write_provider_tool_result_audit(
            hermes_home=hermes_home,
            provider_request_id=request.provider_request_id,
            provider_response_id=response.provider_response_id,
            provider_mode=mode,
            tool_call_id=parsed.id,
            tool_id=parsed.name,
            result_summary={
                "status": result["status"],
                "executed": result["executed"],
                "blockedReason": result.get("blockedReason"),
                "readOnlyOnly": True,
            },
        ) or "")

        if result["executed"]:
            executed_ids.append(parsed.name)
        else:
            blocked_ids.append(parsed.name)
        tool_results.append(result)

    # ── Step 9–10: feed tool results to the fake provider for a final answer ──
    final_answer = response.assistant_message
    final_response_id = response.provider_response_id
    if mode == PROVIDER_MODE_FAKE:
        finalize_response = adapter.invoke(
            request,
            tool_results={
                "executedToolIds": executed_ids,
                "blockedToolIds": blocked_ids,
            },
        )
        final_answer = finalize_response.assistant_message
        final_response_id = finalize_response.provider_response_id

    # ── Step 11: audit the final response ──
    audit_ids.append(write_provider_final_response_audit(
        hermes_home=hermes_home,
        provider_request_id=request.provider_request_id,
        provider_response_id=final_response_id,
        provider_mode=mode,
        final_summary={
            "executedToolIds": executed_ids,
            "blockedToolIds": blocked_ids,
            "finalAnswerPreview": final_answer[:160],
            "readOnlyOnly": True,
        },
    ) or "")

    status = "completed" if not blocked_ids else "blocked"
    return ProviderRoundtripResult(
        status=status,
        provider_mode=mode,
        provider_request_id=request.provider_request_id,
        provider_response_id=final_response_id,
        provider_schema_sent=request.provider_schema_sent,
        provider_api_called=request.provider_api_called,
        external_network_called=request.external_network_called,
        read_only_only=True,
        tool_calls=tuple(tool_calls_view),
        tool_results=tuple(tool_results),
        final_answer=final_answer,
        provider_audit_ids=tuple(x for x in audit_ids if x),
        blocked_reason=(f"blocked_tool_calls:{','.join(blocked_ids)}" if blocked_ids else None),
        schema_summary=schema_summary,
    )


def build_provider_final_response(
    result: ProviderRoundtripResult,
) -> dict[str, Any]:
    """Return the final-answer envelope for the API/UI."""
    return result.to_safe_dict()
