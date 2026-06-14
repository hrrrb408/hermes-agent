"""Tool Handler Call for the Hermes Dev WebUI Tool Execute Gate.

This module implements the clarify-only minimal controlled Tool Handler call
for the execute gate stack.  It builds a safe handler-call plan from the
already-verified allowlisted handler descriptor and side-effect-free dispatch
plan, invokes a bounded, deterministic, side-effect-free clarify handler, and
returns a safe handler-call result envelope.

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider imports, no real tool handler imports, no agent imports
  - no dispatch runtime imports, no toolsets execution
  - no network IO, no filesystem mutation, no shell / file / browser execution
  - no STATIC_ALLOWLIST mutation
  - deterministic, JSON-serializable output
  - never stores raw confirmationToken
  - never stores full tokenHash
  - never stores raw arguments (only safe-normalized clarify fields)
  - never stores secrets
  - never calls the dispatch runtime / provider
  - handler call is DEFAULT DISABLED — only an explicit dev gate enables it
  - clarify-only — non-clarify canonicalName never invokes a handler
  - dispatch plan existence is NOT handler-call permission
  - handler descriptor is NOT handler-call permission
  - STATIC_ALLOWLIST remains the permission boundary

The clarify handler implemented here is a bounded, safe, deterministic
re-implementation of the clarify tool's *contract* (present a clarifying
question with optional choices) adapted for the non-interactive controlled
backend.  It does NOT import ``tools/`` (which would trigger registry side
effects and require a blocking platform callback).  This matches the handler
descriptor's declared ``moduleName`` of ``builtin.safe_metadata_only``.

Phase: 1G-04-29 — Clarify-only Handler Call + Post-execution Audit
Status: clarify-only controlled handler call implemented, default-disabled
"""

from __future__ import annotations

import os
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

HANDLER_CALL_ID_PREFIX = "thc_"
HANDLER_CALL_SCHEMA_VERSION = 1
HANDLER_CALL_PLAN_VERSION = 1

HANDLER_CALL_STATUS_COMPLETED = "completed"
HANDLER_CALL_STATUS_BLOCKED = "blocked"

EXECUTION_STATUS_COMPLETED = "completed"
EXECUTION_STATUS_BLOCKED = "blocked"

CLARIFY_TOOL_TYPE = "clarify"
CLARIFY_MAX_CHOICES = 4  # mirrors tools/clarify_tool.py MAX_CHOICES

# Explicit dev gate env var. Default unset → handler call disabled.
HANDLER_CALL_GATE_ENV = "HERMES_TOOL_HANDLER_CALL_ENABLED"

# ID random bytes
_ID_RANDOM_BYTES = 16  # 128 bits of randomness


# ---------------------------------------------------------------------------
# 2. Error codes / decisions
# ---------------------------------------------------------------------------

ERROR_HANDLER_CALL_NOT_ENABLED = "tool_handler_call_not_enabled"
ERROR_HANDLER_CALL_UNAVAILABLE = "handler_call_unavailable"
ERROR_HANDLER_CALL_NOT_CLARIFY = "handler_call_not_clarify"
ERROR_HANDLER_CALL_DISPATCH_PLAN_MISSING = "handler_call_dispatch_plan_missing"
ERROR_HANDLER_CALL_HANDLER_DESCRIPTOR_MISSING = (
    "handler_call_handler_descriptor_missing"
)
ERROR_HANDLER_CALL_PLAN_INVALID = "handler_call_plan_invalid"
ERROR_HANDLER_CALL_CANONICAL_NAME_MISMATCH = "handler_call_canonical_name_mismatch"
ERROR_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH = "handler_call_handler_lookup_mismatch"
ERROR_HANDLER_CALL_REGISTRY_MISMATCH = "handler_call_registry_mismatch"
ERROR_HANDLER_CALL_SIDE_EFFECT_RISK = "handler_call_side_effect_risk"
ERROR_HANDLER_CALL_PROVIDER_NOT_DISABLED = "handler_call_provider_not_disabled"
ERROR_HANDLER_CALL_FAILED = "handler_call_failed"

DECISION_BLOCKED_TOOL_HANDLER_CALL_NOT_ENABLED = (
    "blocked_tool_handler_call_not_enabled"
)
DECISION_BLOCKED_HANDLER_CALL_UNAVAILABLE = "blocked_handler_call_unavailable"
DECISION_BLOCKED_HANDLER_CALL_NOT_CLARIFY = "blocked_handler_call_not_clarify"
DECISION_BLOCKED_HANDLER_CALL_DISPATCH_PLAN_MISSING = (
    "blocked_handler_call_dispatch_plan_missing"
)
DECISION_BLOCKED_HANDLER_CALL_HANDLER_DESCRIPTOR_MISSING = (
    "blocked_handler_call_handler_descriptor_missing"
)
DECISION_BLOCKED_HANDLER_CALL_PLAN_INVALID = "blocked_handler_call_plan_invalid"
DECISION_BLOCKED_HANDLER_CALL_CANONICAL_NAME_MISMATCH = (
    "blocked_handler_call_canonical_name_mismatch"
)
DECISION_BLOCKED_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH = (
    "blocked_handler_call_handler_lookup_mismatch"
)
DECISION_BLOCKED_HANDLER_CALL_REGISTRY_MISMATCH = (
    "blocked_handler_call_registry_mismatch"
)
DECISION_BLOCKED_HANDLER_CALL_SIDE_EFFECT_RISK = (
    "blocked_handler_call_side_effect_risk"
)
DECISION_BLOCKED_HANDLER_CALL_PROVIDER_NOT_DISABLED = (
    "blocked_handler_call_provider_not_disabled"
)
DECISION_BLOCKED_HANDLER_CALL_FAILED = "blocked_handler_call_failed"

# Gate constants
GATE_TOOL_HANDLER_CALL = "tool_handler_call"
GATE_HANDLER_CALL_ENABLE = "handler_call_enable"
GATE_HANDLER_CALL_CANONICAL_NAME = "handler_call_canonical_name"
GATE_HANDLER_CALL_DISPATCH_PLAN = "handler_call_dispatch_plan"
GATE_HANDLER_CALL_DESCRIPTOR = "handler_call_descriptor"
GATE_HANDLER_CALL_PLAN = "handler_call_plan"
GATE_HANDLER_CALL_PLAN_VALIDATION = "handler_call_plan_validation"
GATE_HANDLER_CALL_PROVIDER = "handler_call_provider"
GATE_HANDLER_CALL_ID = "handler_call_id"
GATE_HANDLER_CALL_INVOCATION = "handler_call_invocation"
GATE_HANDLER_CALL_NORMALIZATION = "handler_call_normalization"


# ---------------------------------------------------------------------------
# 3. Secret redaction (bounded, stdlib-only — mirrors execute gate)
# ---------------------------------------------------------------------------

_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
)

_FORBIDDEN_ARG_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "api_key", "apikey", "authorization", "auth_header", "bearer",
        "token", "secret", "password", "passwd", "credential", "cookie",
        "session", "private_key", "client_secret", "access_token",
        "refresh_token", "access_key",
    }
)

_NORMALIZED_FORBIDDEN_ARG_FIELDS: frozenset[str] = frozenset(
    n.replace("_", "").replace("-", "").lower()
    for n in _FORBIDDEN_ARG_FIELD_NAMES
)

_REDACTED_VALUE = "[REDACTED]"


def _redact_value(value: Any) -> Any:
    """Redact secret-looking string values recursively."""
    if isinstance(value, str):
        for pattern in _SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                return _REDACTED_VALUE
        return value
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


def _redact_clarify_arguments(arguments: dict[str, Any] | None) -> dict[str, Any]:
    """Build a safe-normalized clarify arguments dict.

    Only the ``question`` and ``choices`` clarify fields are extracted; every
    other field is dropped.  Secret-looking values are redacted.  Choices are
    bounded to CLARIFY_MAX_CHOICES.
    """
    safe: dict[str, Any] = {}
    if not isinstance(arguments, dict):
        return safe

    # question
    raw_question = arguments.get("question")
    if isinstance(raw_question, str):
        question = _redact_value(raw_question.strip())
        if isinstance(question, str) and question:
            safe["question"] = question

    # choices (optional list of strings, bounded)
    raw_choices = arguments.get("choices")
    if isinstance(raw_choices, list):
        cleaned: list[str] = []
        for choice in raw_choices[:CLARIFY_MAX_CHOICES]:
            if isinstance(choice, str):
                redacted_choice = _redact_value(choice.strip())
                if isinstance(redacted_choice, str) and redacted_choice:
                    cleaned.append(redacted_choice)
        if cleaned:
            safe["choices"] = cleaned

    return safe


def _redact_read_only_arguments(
    canonical_name: str,
    arguments: dict[str, Any] | None,
) -> dict[str, Any]:
    """Safe-normalize a read-only tool's arguments via the registry whitelist.

    Phase 2A read-only tools route their arguments through the read-only
    registry's strict-whitelist validator/normalizer, which drops unknown keys,
    rejects forbidden/secret/path/shell stems, applies defaults, and bounds
    values. The handler therefore never receives untrusted input.
    """
    from hermes_cli.dev_web_read_only_tool_registry import (
        normalize_read_only_tool_arguments,
    )

    return normalize_read_only_tool_arguments(canonical_name, arguments)


def _is_supported_controlled_tool(canonical_name: str) -> bool:
    """Return True for ``clarify`` OR a Phase 2A read-only tool.

    Lazy import keeps this module import-clean (the read-only registry imports
    the policy module, which is stdlib-only — no cycle, but lazy import matches
    the existing pattern used by ``lookup_handler_descriptor``).
    """
    if canonical_name == CLARIFY_TOOL_TYPE:
        return True
    try:
        from hermes_cli.dev_web_read_only_tool_registry import (
            is_phase_2a_read_only_tool,
        )

        return is_phase_2a_read_only_tool(canonical_name)
    except Exception:
        # If the registry cannot be imported, fail safe: only clarify is
        # supported. No read-only tool can reach execution.
        return False


# ---------------------------------------------------------------------------
# 4. Result / plan dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HandlerCallPlan:
    """Immutable safe handler-call plan.

    Contains only safe, deterministic metadata and the safe-normalized clarify
    arguments.  No callable references, no secrets, no raw token, no full
    tokenHash, no raw unredacted arguments, no provider credentials.
    """

    canonical_name: str
    handler_lookup_id: str
    dispatch_id: str
    handler_id: str
    registry_key: str
    execute_request_id: str | None
    pre_execution_audit_id: str | None
    normalized_arguments: dict[str, Any]
    handler_call_plan_version: int

    def to_safe_dict(self) -> dict[str, Any]:
        """Convert to a JSON-safe dict containing safe metadata only."""
        return {
            "canonicalName": self.canonical_name,
            "handlerLookupId": self.handler_lookup_id,
            "dispatchId": self.dispatch_id,
            "handlerId": self.handler_id,
            "registryKey": self.registry_key,
            "normalizedArguments": dict(self.normalized_arguments),
            "handlerCallPlanVersion": self.handler_call_plan_version,
        }


@dataclass(frozen=True, slots=True)
class HandlerCallResult:
    """Immutable result of a clarify-only handler call attempt.

    When ``called`` is True, the clarify handler was invoked under the explicit
    dev gate, the result was normalized, and a post-execution audit is required.
    When ``called`` is False, the handler was not invoked (default-disabled or
    a consistency gate failed) and ``decision``/``error_code`` describe the
    block.
    """

    called: bool
    handler_call_id: str | None
    handler_call_status: str
    execution_status: str
    canonical_name: str
    tool_result: dict[str, Any] | None
    side_effects: dict[str, bool]
    error_code: str | None
    decision: str | None
    gate: str | None
    safe_summary: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 5. Internal helpers
# ---------------------------------------------------------------------------


def _handler_call_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def generate_handler_call_id() -> str:
    """Generate a unique handler-call correlation ID.

    Format: ``thc_`` + base64url-safe random string.
    The ID is not an authorization credential — it is correlation-only.
    It never contains raw token, full tokenHash, raw arguments, or secrets.
    """
    return f"{HANDLER_CALL_ID_PREFIX}{secrets.token_urlsafe(_ID_RANDOM_BYTES)}"


def is_handler_call_enabled() -> bool:
    """Return True only when the explicit handler-call dev gate is set.

    Only exact lowercase ``"true"`` for ``HERMES_TOOL_HANDLER_CALL_ENABLED``
    enables the handler call.  Unset / empty / any other value disables it.
    Default (unset) → disabled → handler call blocked.
    """
    return os.environ.get(HANDLER_CALL_GATE_ENV, "").strip() == "true"


def _build_side_effect_flags(**overrides: bool) -> dict[str, bool]:
    """Build side-effect flags — all false unless explicitly overridden.

    Clarify is side-effect-free: no provider, no filesystem, no network,
    no external side effects.  The overrides are used only for the success
    envelope's handler-call / execution bookkeeping flags.
    """
    flags: dict[str, bool] = {
        "externalSideEffects": False,
        "providerSchemaSent": False,
        "providerApiCalled": False,
        "filesystemChanged": False,
        "networkCalled": False,
    }
    flags.update(overrides)
    return flags


def _fail_closed(
    *,
    error_code: str,
    decision: str,
    gate: str,
    canonical_name: str = CLARIFY_TOOL_TYPE,
) -> HandlerCallResult:
    """Return a fail-closed handler-call result — never an unhandled exception."""
    return HandlerCallResult(
        called=False,
        handler_call_id=None,
        handler_call_status=HANDLER_CALL_STATUS_BLOCKED,
        execution_status=EXECUTION_STATUS_BLOCKED,
        canonical_name=canonical_name,
        tool_result=None,
        side_effects=_build_side_effect_flags(),
        error_code=error_code,
        decision=decision,
        gate=gate,
        safe_summary={},
    )


# ---------------------------------------------------------------------------
# 6. Bounded clarify handler (deterministic, side-effect-free)
# ---------------------------------------------------------------------------


def _run_clarify_handler(plan: HandlerCallPlan) -> dict[str, Any]:
    """Invoke the bounded safe clarify handler.

    This is a deterministic, side-effect-free re-implementation of the clarify
    tool's contract for the non-interactive controlled backend.  It constructs
    the clarification request (question + optional choices) from the
    safe-normalized arguments WITHOUT:

      - importing tools/ (no registry side effects)
      - requiring a platform callback (no blocking)
      - any shell / file / network / browser execution
      - any provider call

    Returns the safe clarify tool result envelope:
      {"type": "clarify", "message": <question>, "questions": [...]}

    The clarify question text is required.  If absent, a safe default
    clarification message is produced (the handler call still completes — the
    execute gate has already validated the full chain).
    """
    args = plan.normalized_arguments
    question = args.get("question")
    if not isinstance(question, str) or not question.strip():
        # No explicit question supplied — produce a safe default clarification.
        # The handler call still completes; clarify is a no-side-effect request.
        question = "Clarification requested."

    choices = args.get("choices")
    questions: list[dict[str, Any]] = []
    if isinstance(choices, list):
        for idx, choice in enumerate(choices):
            if isinstance(choice, str) and choice.strip():
                questions.append({"id": idx, "label": choice})

    return {
        "type": CLARIFY_TOOL_TYPE,
        "message": question,
        "questions": questions,
    }


# ---------------------------------------------------------------------------
# 7. Handler-call plan validation
# ---------------------------------------------------------------------------


def validate_handler_call_plan(
    plan: HandlerCallPlan,
    *,
    expected_canonical_name: str | None = None,
    expected_handler_lookup_id: str | None = None,
    expected_registry_key: str | None = None,
) -> str | None:
    """Validate a handler-call plan for safety.

    Returns an error_code if validation fails, None if the plan is valid.
    """
    if not isinstance(plan, HandlerCallPlan):
        return ERROR_HANDLER_CALL_PLAN_INVALID

    # Phase 2A: support clarify OR Phase 2A read-only tools. Any other name
    # (e.g. read_file, a write tool, an unknown tool) is blocked here as a
    # defense-in-depth backstop. (The allowlist gate already rejected it.)
    if not _is_supported_controlled_tool(plan.canonical_name):
        return ERROR_HANDLER_CALL_NOT_CLARIFY
    if not isinstance(plan.handler_lookup_id, str) or not plan.handler_lookup_id.strip():
        return ERROR_HANDLER_CALL_PLAN_INVALID
    if not isinstance(plan.dispatch_id, str) or not plan.dispatch_id.strip():
        return ERROR_HANDLER_CALL_PLAN_INVALID
    if not isinstance(plan.handler_id, str) or not plan.handler_id.strip():
        return ERROR_HANDLER_CALL_PLAN_INVALID
    if not isinstance(plan.registry_key, str) or not plan.registry_key.strip():
        return ERROR_HANDLER_CALL_PLAN_INVALID
    if not isinstance(plan.normalized_arguments, dict):
        return ERROR_HANDLER_CALL_PLAN_INVALID

    if expected_canonical_name is not None and plan.canonical_name != expected_canonical_name:
        return ERROR_HANDLER_CALL_CANONICAL_NAME_MISMATCH
    if (
        expected_handler_lookup_id is not None
        and plan.handler_lookup_id != expected_handler_lookup_id
    ):
        return ERROR_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH
    if expected_registry_key is not None and plan.registry_key != expected_registry_key:
        return ERROR_HANDLER_CALL_REGISTRY_MISMATCH

    return None


# ---------------------------------------------------------------------------
# 8. Safe summary
# ---------------------------------------------------------------------------


def safe_handler_call_summary(
    *,
    handler_call_id: str | None,
    handler_call_status: str,
    execution_status: str,
    canonical_name: str | None = None,
) -> dict[str, Any]:
    """Build a safe summary from a handler-call result.

    Never exposes raw token, full tokenHash, raw arguments, callable object,
    function repr, provider credentials, secrets, or authorization headers.
    """
    summary: dict[str, Any] = {
        "handlerCallId": handler_call_id,
        "handlerCallStatus": handler_call_status,
        "executionStatus": execution_status,
    }
    if canonical_name is not None:
        summary["canonicalName"] = canonical_name
    return summary


# ---------------------------------------------------------------------------
# 9. Handler-call plan builder
# ---------------------------------------------------------------------------


def build_handler_call_plan(
    *,
    canonical_name: str,
    handler_descriptor: dict[str, Any] | None,
    dispatch_plan: dict[str, Any] | None,
    handler_lookup_id: str | None,
    dispatch_id: str | None,
    execute_request_id: str | None = None,
    pre_execution_audit_id: str | None = None,
    arguments: dict[str, Any] | None = None,
) -> HandlerCallPlan | tuple[None, str, str, str]:
    """Build a safe clarify-only handler-call plan.

    Returns either a :class:`HandlerCallPlan` or, on failure, a tuple
    ``(None, error_code, decision, gate)`` describing the blocking gate.

    This function constructs side-effect-free routing metadata only. It does
    NOT import any handler module, instantiate a handler, call a callable,
    invoke the dispatch runtime, access ~/.hermes, read production state.db,
    read provider keys, store raw confirmationToken, store full tokenHash,
    store raw unredacted arguments, or store secrets.
    """
    # Gate 72: Dispatch plan available
    if not isinstance(dispatch_plan, dict) or not dispatch_plan:
        return None, (
            ERROR_HANDLER_CALL_DISPATCH_PLAN_MISSING,
            DECISION_BLOCKED_HANDLER_CALL_DISPATCH_PLAN_MISSING,
            GATE_HANDLER_CALL_DISPATCH_PLAN,
        )

    # Gate 73: Handler descriptor available + dispatch plan consistency
    if not isinstance(handler_descriptor, dict) or not handler_descriptor:
        return None, (
            ERROR_HANDLER_CALL_HANDLER_DESCRIPTOR_MISSING,
            DECISION_BLOCKED_HANDLER_CALL_HANDLER_DESCRIPTOR_MISSING,
            GATE_HANDLER_CALL_DESCRIPTOR,
        )

    # canonicalName must be a supported controlled tool (clarify OR a Phase 2A
    # read-only tool). Defense-in-depth — the allowlist already gates this.
    if not _is_supported_controlled_tool(canonical_name):
        return None, (
            ERROR_HANDLER_CALL_NOT_CLARIFY,
            DECISION_BLOCKED_HANDLER_CALL_NOT_CLARIFY,
            GATE_HANDLER_CALL_CANONICAL_NAME,
        )

    desc_canonical = handler_descriptor.get("canonicalName")
    handler_id = handler_descriptor.get("handlerId")
    registry_key = handler_descriptor.get("registryKey")

    if not isinstance(desc_canonical, str) or desc_canonical != canonical_name:
        return None, (
            ERROR_HANDLER_CALL_CANONICAL_NAME_MISMATCH,
            DECISION_BLOCKED_HANDLER_CALL_CANONICAL_NAME_MISMATCH,
            GATE_HANDLER_CALL_CANONICAL_NAME,
        )
    if not isinstance(handler_id, str) or not handler_id.strip():
        return None, (
            ERROR_HANDLER_CALL_PLAN_INVALID,
            DECISION_BLOCKED_HANDLER_CALL_PLAN_INVALID,
            GATE_HANDLER_CALL_DESCRIPTOR,
        )
    if not isinstance(registry_key, str) or registry_key.strip() != canonical_name:
        return None, (
            ERROR_HANDLER_CALL_REGISTRY_MISMATCH,
            DECISION_BLOCKED_HANDLER_CALL_REGISTRY_MISMATCH,
            GATE_HANDLER_CALL_DESCRIPTOR,
        )

    # Dispatch plan must agree on canonicalName / handlerLookupId
    plan_canonical = dispatch_plan.get("canonicalName")
    plan_lookup_id = dispatch_plan.get("handlerLookupId")
    if plan_canonical != canonical_name:
        return None, (
            ERROR_HANDLER_CALL_CANONICAL_NAME_MISMATCH,
            DECISION_BLOCKED_HANDLER_CALL_CANONICAL_NAME_MISMATCH,
            GATE_HANDLER_CALL_DISPATCH_PLAN,
        )
    if not isinstance(handler_lookup_id, str) or not handler_lookup_id.strip():
        return None, (
            ERROR_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH,
            DECISION_BLOCKED_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH,
            GATE_HANDLER_CALL_DISPATCH_PLAN,
        )
    if plan_lookup_id != handler_lookup_id:
        return None, (
            ERROR_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH,
            DECISION_BLOCKED_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH,
            GATE_HANDLER_CALL_DISPATCH_PLAN,
        )
    if not isinstance(dispatch_id, str) or not dispatch_id.strip():
        return None, (
            ERROR_HANDLER_CALL_PLAN_INVALID,
            DECISION_BLOCKED_HANDLER_CALL_PLAN_INVALID,
            GATE_HANDLER_CALL_DISPATCH_PLAN,
        )

    # Gate 64 mirror: dispatch plan side-effect flags must remain safe.
    # The handler call must never inherit execution permission from the plan.
    if dispatch_plan.get("toolHandlerCallAllowed") is not False:
        return None, (
            ERROR_HANDLER_CALL_SIDE_EFFECT_RISK,
            DECISION_BLOCKED_HANDLER_CALL_SIDE_EFFECT_RISK,
            GATE_HANDLER_CALL_PLAN_VALIDATION,
        )
    if dispatch_plan.get("executionAllowed") is not False:
        return None, (
            ERROR_HANDLER_CALL_SIDE_EFFECT_RISK,
            DECISION_BLOCKED_HANDLER_CALL_SIDE_EFFECT_RISK,
            GATE_HANDLER_CALL_PLAN_VALIDATION,
        )
    if dispatch_plan.get("providerSchemaAllowed") is not False:
        return None, (
            ERROR_HANDLER_CALL_SIDE_EFFECT_RISK,
            DECISION_BLOCKED_HANDLER_CALL_SIDE_EFFECT_RISK,
            GATE_HANDLER_CALL_PLAN_VALIDATION,
        )
    if dispatch_plan.get("sideEffectFreeDispatch") is not True:
        return None, (
            ERROR_HANDLER_CALL_SIDE_EFFECT_RISK,
            DECISION_BLOCKED_HANDLER_CALL_SIDE_EFFECT_RISK,
            GATE_HANDLER_CALL_PLAN_VALIDATION,
        )

    # Safe-normalize the arguments. Clarify uses its own bounded normalizer
    # (question + choices only). Phase 2A read-only tools use the registry's
    # strict-whitelist normalizer (drops unknown keys, rejects secret/path/shell
    # stems, applies defaults, bounds values).
    if canonical_name == CLARIFY_TOOL_TYPE:
        normalized_arguments = _redact_clarify_arguments(arguments)
    else:
        normalized_arguments = _redact_read_only_arguments(canonical_name, arguments)

    plan = HandlerCallPlan(
        canonical_name=canonical_name,
        handler_lookup_id=handler_lookup_id,
        dispatch_id=dispatch_id,
        handler_id=handler_id,
        registry_key=registry_key,
        execute_request_id=execute_request_id,
        pre_execution_audit_id=pre_execution_audit_id,
        normalized_arguments=normalized_arguments,
        handler_call_plan_version=HANDLER_CALL_PLAN_VERSION,
    )

    # Validate the built plan
    validation_error = validate_handler_call_plan(
        plan,
        expected_canonical_name=canonical_name,
        expected_handler_lookup_id=handler_lookup_id,
        expected_registry_key=registry_key,
    )
    if validation_error is not None:
        if validation_error == ERROR_HANDLER_CALL_CANONICAL_NAME_MISMATCH:
            decision = DECISION_BLOCKED_HANDLER_CALL_CANONICAL_NAME_MISMATCH
        elif validation_error == ERROR_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH:
            decision = DECISION_BLOCKED_HANDLER_CALL_HANDLER_LOOKUP_MISMATCH
        elif validation_error == ERROR_HANDLER_CALL_REGISTRY_MISMATCH:
            decision = DECISION_BLOCKED_HANDLER_CALL_REGISTRY_MISMATCH
        elif validation_error == ERROR_HANDLER_CALL_NOT_CLARIFY:
            decision = DECISION_BLOCKED_HANDLER_CALL_NOT_CLARIFY
        else:
            decision = DECISION_BLOCKED_HANDLER_CALL_PLAN_INVALID
        return None, (validation_error, decision, GATE_HANDLER_CALL_PLAN_VALIDATION)

    return plan, (None, None, None)


# ---------------------------------------------------------------------------
# 10. Result normalization
# ---------------------------------------------------------------------------


def _normalize_read_only_handler_result(
    canonical_name: str,
    raw_tool_result: dict[str, Any],
) -> dict[str, Any]:
    """Normalize a Phase 2A read-only handler result into a safe envelope.

    The read-only handlers return ``{"type": <toolId>, "message": <summary>,
    "result": <structured>}``. The structured result is already redacted and
    size-bounded by ``dispatch_read_only_tool``; here we defensively re-redact
    the message and ensure a safe shape. Never exposes raw token, full
    tokenHash, raw arguments, callable/function repr, or secrets.
    """
    result = raw_tool_result.get("result")
    if not isinstance(result, dict):
        result = {}

    message = raw_tool_result.get("message")
    if not isinstance(message, str):
        message = "Read-only inspection completed."
    message = _redact_value(message)
    if not isinstance(message, str) or not message:
        message = "Read-only inspection completed."

    return {
        "type": canonical_name,
        "message": message,
        "result": _redact_value(result),
    }


def normalize_handler_result(
    *,
    handler_call_id: str,
    canonical_name: str,
    raw_tool_result: dict[str, Any],
) -> dict[str, Any]:
    """Normalize a handler result into a safe envelope.

    For clarify, the result is normalized to the clarify shape (message +
    questions). For a Phase 2A read-only tool, the structured result is
    preserved (already redacted and size-bounded by the dispatcher).

    Never exposes raw token, full tokenHash, raw unredacted arguments, callable
    object, function repr, provider credentials, secrets, or authorization
    headers. Re-redacts the message / question labels defensively.
    """
    if _is_supported_controlled_tool(canonical_name) and canonical_name != CLARIFY_TOOL_TYPE:
        return _normalize_read_only_handler_result(canonical_name, raw_tool_result)

    message = raw_tool_result.get("message")
    if not isinstance(message, str):
        message = "Clarification requested."
    message = _redact_value(message)
    if not isinstance(message, str) or not message:
        message = "Clarification requested."

    questions: list[dict[str, Any]] = []
    raw_questions = raw_tool_result.get("questions")
    if isinstance(raw_questions, list):
        for item in raw_questions:
            if isinstance(item, dict):
                label = item.get("label")
                if isinstance(label, str):
                    label = _redact_value(label)
                    if isinstance(label, str) and label:
                        questions.append({"id": item.get("id"), "label": label})

    return {
        "type": CLARIFY_TOOL_TYPE,
        "message": message,
        "questions": questions,
    }


# ---------------------------------------------------------------------------
# 11. Top-level entry point — attempt_clarify_handler_call
# ---------------------------------------------------------------------------


def attempt_clarify_handler_call(
    *,
    canonical_name: str,
    handler_descriptor: dict[str, Any] | None,
    dispatch_plan: dict[str, Any] | None,
    handler_lookup_id: str | None,
    dispatch_id: str | None,
    execute_request_id: str | None = None,
    pre_execution_audit_id: str | None = None,
    arguments: dict[str, Any] | None = None,
    hermes_home: str | None = None,
) -> HandlerCallResult:
    """Attempt a controlled handler call under the explicit dev gate.

    Phase 2A generalizes this from clarify-only to dispatch-by-name: clarify
    uses the inline bounded handler; Phase 2A read-only tools use
    ``dispatch_read_only_tool``. The function name is retained for stability
    of the call site and tests.

    Gate order:
      70. Tool handler call enable gate (HERMES_TOOL_HANDLER_CALL_ENABLED)
      71. canonicalName is a supported controlled tool (clarify OR read-only)
      72. Dispatch plan available
      73. Handler descriptor / dispatch plan consistency
      74. Handler call plan build
      75. Handler call plan validation
      76. Provider disabled invariant
      77. handlerCallId generated
      78. Handler invocation (clarify inline OR read-only dispatch)
      79. Handler result normalization

    Default (gate unset) → blocked (tool_handler_call_not_enabled), no handler
    invoked, no execution, no provider call.

    Explicit gate + supported tool + all consistency → completed, safe tool
    result, all external side-effect flags false.
    """
    # Gate 70: Tool handler call enable gate
    if not is_handler_call_enabled():
        return _fail_closed(
            error_code=ERROR_HANDLER_CALL_NOT_ENABLED,
            decision=DECISION_BLOCKED_TOOL_HANDLER_CALL_NOT_ENABLED,
            gate=GATE_HANDLER_CALL_ENABLE,
            canonical_name=canonical_name,
        )

    # Gate 71: supported controlled tool (clarify OR Phase 2A read-only).
    # Defense-in-depth — the allowlist gate already rejected non-members.
    if not _is_supported_controlled_tool(canonical_name):
        return _fail_closed(
            error_code=ERROR_HANDLER_CALL_NOT_CLARIFY,
            decision=DECISION_BLOCKED_HANDLER_CALL_NOT_CLARIFY,
            gate=GATE_HANDLER_CALL_CANONICAL_NAME,
            canonical_name=canonical_name,
        )

    # Gates 72–75: build + validate the handler call plan
    plan_or_err = build_handler_call_plan(
        canonical_name=canonical_name,
        handler_descriptor=handler_descriptor,
        dispatch_plan=dispatch_plan,
        handler_lookup_id=handler_lookup_id,
        dispatch_id=dispatch_id,
        execute_request_id=execute_request_id,
        pre_execution_audit_id=pre_execution_audit_id,
        arguments=arguments,
    )
    plan, err = plan_or_err
    if plan is None:
        error_code, decision, gate = err  # type: ignore[misc]
        return _fail_closed(
            error_code=error_code,
            decision=decision,
            gate=gate,
            canonical_name=canonical_name,
        )

    # Gate 76: Provider disabled invariant — clarify never sends Provider
    # Schema and never calls a Provider API. These flags must remain false.
    # (Defense-in-depth; the module never imports a provider.)

    # Gate 77: handlerCallId generated (correlation-only, not a credential)
    handler_call_id = generate_handler_call_id()

    # Gate 78: Handler invocation (bounded, deterministic, safe).
    # Clarify uses the inline bounded handler; Phase 2A read-only tools use
    # the bounded read-only dispatcher. Both are side-effect-free re-
    # implementations — neither imports tools/ (no production registry side
    # effects), neither calls a Provider, neither writes.
    try:
        if canonical_name == CLARIFY_TOOL_TYPE:
            raw_tool_result = _run_clarify_handler(plan)
        else:
            from hermes_cli.dev_web_read_only_tool_handlers import (
                dispatch_read_only_tool,
            )

            raw_tool_result = dispatch_read_only_tool(
                canonical_name,
                plan.normalized_arguments,
                hermes_home=hermes_home,
            )
    except Exception:
        # Any unexpected handler failure fails closed.
        return _fail_closed(
            error_code=ERROR_HANDLER_CALL_FAILED,
            decision=DECISION_BLOCKED_HANDLER_CALL_FAILED,
            gate=GATE_HANDLER_CALL_INVOCATION,
            canonical_name=canonical_name,
        )

    if not isinstance(raw_tool_result, dict):
        return _fail_closed(
            error_code=ERROR_HANDLER_CALL_FAILED,
            decision=DECISION_BLOCKED_HANDLER_CALL_FAILED,
            gate=GATE_HANDLER_CALL_INVOCATION,
            canonical_name=canonical_name,
        )

    # Gate 79: Handler result normalization
    try:
        tool_result = normalize_handler_result(
            handler_call_id=handler_call_id,
            canonical_name=canonical_name,
            raw_tool_result=raw_tool_result,
        )
    except Exception:
        return _fail_closed(
            error_code=ERROR_HANDLER_CALL_FAILED,
            decision=DECISION_BLOCKED_HANDLER_CALL_FAILED,
            gate=GATE_HANDLER_CALL_NORMALIZATION,
            canonical_name=canonical_name,
        )

    side_effects = _build_side_effect_flags()

    safe_summary = safe_handler_call_summary(
        handler_call_id=handler_call_id,
        handler_call_status=HANDLER_CALL_STATUS_COMPLETED,
        execution_status=EXECUTION_STATUS_COMPLETED,
        canonical_name=canonical_name,
    )

    return HandlerCallResult(
        called=True,
        handler_call_id=handler_call_id,
        handler_call_status=HANDLER_CALL_STATUS_COMPLETED,
        execution_status=EXECUTION_STATUS_COMPLETED,
        canonical_name=canonical_name,
        tool_result=tool_result,
        side_effects=side_effects,
        error_code=None,
        decision=None,
        gate=None,
        safe_summary=safe_summary,
    )
