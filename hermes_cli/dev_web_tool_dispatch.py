"""Tool Dispatch Planning for the Hermes Dev WebUI Tool Execute Gate.

This module implements minimal safe dispatch plan / dispatch envelope
construction for the execute gate stack.  It builds a side-effect-free,
metadata-only dispatch plan for an already-verified, allowlisted,
handler-resolved ``canonicalName``.

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider imports, no tool handler imports, no agent imports
  - no dispatch runtime imports, no toolsets execution
  - no network IO, no filesystem mutation, no runtime state mutation
  - no STATIC_ALLOWLIST mutation
  - deterministic, JSON-serializable output
  - never stores raw confirmationToken
  - never stores full tokenHash
  - never stores raw arguments
  - never stores secrets
  - never calls handler / dispatch runtime / provider
  - dispatch plan success does NOT imply a Tool Handler call
  - dispatch plan existence is NOT permission
  - handler descriptor is NOT permission
  - STATIC_ALLOWLIST remains the permission boundary
  - Tool Handler call remains disabled

Phase: 1G-04-28 — Dispatch Minimal Implementation
Status: Safe dispatch plan / envelope implemented, execute still blocked-only
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

DISPATCH_ID_PREFIX = "dsp_"
DISPATCH_SCHEMA_VERSION = 1
DISPATCH_PLAN_VERSION = 1

DISPATCH_STATUS_PLANNED = "planned"
DISPATCH_STATUS_BLOCKED = "blocked"
DISPATCH_ROUTING_MODE = "metadata_only"

# Final block boundary after a successful dispatch plan build.
# Tool Handler call is still disabled; this is the project-approved final
# block decision for the dispatch phase.
FINAL_BLOCK_TOOL_HANDLER_CALL_NOT_ENABLED = "blocked_tool_handler_call_not_enabled"

# ID random bytes
_ID_RANDOM_BYTES = 16  # 128 bits of randomness


# ---------------------------------------------------------------------------
# 2. Error codes / decisions
# ---------------------------------------------------------------------------

ERROR_DISPATCH_NOT_ENABLED = "dispatch_not_enabled"
ERROR_DISPATCH_UNAVAILABLE = "dispatch_unavailable"
ERROR_DISPATCH_PLAN_UNAVAILABLE = "dispatch_plan_unavailable"
ERROR_DISPATCH_PLAN_INVALID = "dispatch_plan_invalid"
ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISSING = "dispatch_handler_descriptor_missing"
ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH = "dispatch_handler_descriptor_mismatch"
ERROR_DISPATCH_NOT_ALLOWLISTED = "dispatch_not_allowlisted"
ERROR_DISPATCH_POLICY_MISMATCH = "dispatch_policy_mismatch"
ERROR_DISPATCH_SIDE_EFFECT_RISK = "dispatch_side_effect_risk"
ERROR_DISPATCH_REGISTRY_MISMATCH = "dispatch_registry_mismatch"
ERROR_DISPATCH_WRITTEN_BUT_TOOL_HANDLER_CALL_NOT_ENABLED = (
    "dispatch_written_but_tool_handler_call_not_enabled"
)
ERROR_TOOL_HANDLER_CALL_NOT_ENABLED = "tool_handler_call_not_enabled"

DECISION_BLOCKED_DISPATCH_NOT_ENABLED = "blocked_dispatch_not_enabled"
DECISION_BLOCKED_DISPATCH_UNAVAILABLE = "blocked_dispatch_unavailable"
DECISION_BLOCKED_DISPATCH_PLAN_UNAVAILABLE = "blocked_dispatch_plan_unavailable"
DECISION_BLOCKED_DISPATCH_PLAN_INVALID = "blocked_dispatch_plan_invalid"
DECISION_BLOCKED_DISPATCH_HANDLER_DESCRIPTOR_MISSING = (
    "blocked_dispatch_handler_descriptor_missing"
)
DECISION_BLOCKED_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH = (
    "blocked_dispatch_handler_descriptor_mismatch"
)
DECISION_BLOCKED_DISPATCH_NOT_ALLOWLISTED = "blocked_dispatch_not_allowlisted"
DECISION_BLOCKED_DISPATCH_POLICY_MISMATCH = "blocked_dispatch_policy_mismatch"
DECISION_BLOCKED_DISPATCH_SIDE_EFFECT_RISK = "blocked_dispatch_side_effect_risk"
DECISION_BLOCKED_DISPATCH_REGISTRY_MISMATCH = "blocked_dispatch_registry_mismatch"
DECISION_BLOCKED_TOOL_HANDLER_CALL_NOT_ENABLED = (
    "blocked_tool_handler_call_not_enabled"
)

# Gate constants
GATE_DISPATCH = "dispatch"
GATE_DISPATCH_PLAN = "dispatch_plan"
GATE_DISPATCH_PLAN_SOURCE = "dispatch_plan_source"
GATE_DISPATCH_CANONICAL_NAME = "dispatch_canonical_name"
GATE_DISPATCH_REGISTRY = "dispatch_registry"
GATE_DISPATCH_POLICY = "dispatch_policy"
GATE_DISPATCH_ALLOWLIST = "dispatch_allowlist"
GATE_DISPATCH_PLAN_VALIDATION = "dispatch_plan_validation"
GATE_DISPATCH_ID = "dispatch_id"
GATE_TOOL_HANDLER_CALL = "tool_handler_call"


# ---------------------------------------------------------------------------
# 3. Required dispatch plan fields
# ---------------------------------------------------------------------------

_REQUIRED_DISPATCH_PLAN_FIELDS: frozenset[str] = frozenset(
    {
        "canonicalName",
        "handlerLookupId",
        "handlerId",
        "registryKey",
        "routingMode",
        "dispatchAllowed",
        "toolHandlerCallAllowed",
        "executionAllowed",
        "providerSchemaAllowed",
        "sideEffectFreeDispatch",
    }
)


# ---------------------------------------------------------------------------
# 4. Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DispatchPlan:
    """Immutable safe dispatch plan.

    Contains metadata only — no callable references, no secrets, no raw
    arguments, no raw token, no full tokenHash, no provider credentials,
    no Provider Schema payload.
    """

    canonical_name: str
    handler_lookup_id: str
    handler_id: str
    registry_key: str
    routing_mode: str
    dispatch_allowed: bool
    tool_handler_call_allowed: bool
    execution_allowed: bool
    provider_schema_allowed: bool
    side_effect_free_dispatch: bool
    dispatch_plan_version: int
    toolset_name: str | None = None
    category: str | None = None
    risk_tier: str | None = None
    policy_version: str | None = None
    handler_descriptor_version: int | None = None

    def to_safe_dict(self) -> dict[str, Any]:
        """Convert to a JSON-safe dict containing safe metadata only."""
        plan: dict[str, Any] = {
            "canonicalName": self.canonical_name,
            "handlerLookupId": self.handler_lookup_id,
            "handlerId": self.handler_id,
            "registryKey": self.registry_key,
            "routingMode": self.routing_mode,
            "dispatchAllowed": self.dispatch_allowed,
            "toolHandlerCallAllowed": self.tool_handler_call_allowed,
            "executionAllowed": self.execution_allowed,
            "providerSchemaAllowed": self.provider_schema_allowed,
            "sideEffectFreeDispatch": self.side_effect_free_dispatch,
            "dispatchPlanVersion": self.dispatch_plan_version,
        }
        if self.toolset_name is not None:
            plan["toolsetName"] = self.toolset_name
        if self.category is not None:
            plan["category"] = self.category
        if self.risk_tier is not None:
            plan["riskTier"] = self.risk_tier
        if self.policy_version is not None:
            plan["policyVersion"] = self.policy_version
        if self.handler_descriptor_version is not None:
            plan["handlerDescriptorVersion"] = self.handler_descriptor_version
        return plan


@dataclass(frozen=True, slots=True)
class DispatchResult:
    """Immutable result of dispatch plan construction.

    When ``built`` is True, ``dispatch_plan`` contains the safe plan and the
    final block boundary remains ``blocked_tool_handler_call_not_enabled``
    — no Tool Handler call, no execution, no Provider Schema, no Provider API.
    """

    built: bool
    dispatch_status: str
    dispatch_id: str | None
    dispatch_plan: dict[str, Any] | None
    error_code: str | None
    decision: str | None
    gate: str | None
    final_block: str
    created_at: str | None = None
    side_effect_flags: dict[str, bool] = field(default_factory=dict)
    safe_summary: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 5. Internal helpers
# ---------------------------------------------------------------------------


def _dispatch_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def generate_dispatch_id() -> str:
    """Generate a unique dispatch correlation ID.

    Format: ``dsp_`` + base64url-safe random string.
    The ID is not an authorization credential — it is correlation-only.
    It never contains raw token, full tokenHash, raw arguments, or secrets.
    """
    return f"{DISPATCH_ID_PREFIX}{secrets.token_urlsafe(_ID_RANDOM_BYTES)}"


def _build_side_effect_flags() -> dict[str, bool]:
    """Build side-effect flags — all always false."""
    return {
        "executionAllowed": False,
        "dispatchAllowed": False,
        "providerSchemaAllowed": False,
        "toolHandlerCalled": False,
        "providerApiCalled": False,
        "executionStarted": False,
    }


def _fail_closed(
    *,
    error_code: str,
    decision: str,
    gate: str,
    created_at: str | None = None,
    side_effect_flags: dict[str, bool] | None = None,
) -> DispatchResult:
    """Return a fail-closed dispatch result — never an unhandled exception."""
    return DispatchResult(
        built=False,
        dispatch_status=DISPATCH_STATUS_BLOCKED,
        dispatch_id=None,
        dispatch_plan=None,
        error_code=error_code,
        decision=decision,
        gate=gate,
        final_block=FINAL_BLOCK_TOOL_HANDLER_CALL_NOT_ENABLED,
        created_at=created_at,
        side_effect_flags=side_effect_flags or _build_side_effect_flags(),
        safe_summary={},
    )


# ---------------------------------------------------------------------------
# 6. Dispatch plan validation
# ---------------------------------------------------------------------------


def validate_dispatch_plan(
    plan: dict[str, Any],
    *,
    expected_canonical_name: str | None = None,
    expected_handler_lookup_id: str | None = None,
    expected_registry_key: str | None = None,
) -> str | None:
    """Validate a dispatch plan for safety.

    Returns an error_code if validation fails, None if the plan is valid.

    Checks:
      - ``plan`` is a dict
      - All required fields present and non-None
      - ``canonicalName`` is a non-empty string
      - ``routingMode`` is ``metadata_only``
      - ``canonicalName`` matches expected (if provided)
      - ``handlerLookupId`` matches expected (if provided)
      - ``registryKey`` matches expected (if provided)
      - All side-effect flags are safe (false / side-effect-free true)
    """
    if not isinstance(plan, dict):
        return ERROR_DISPATCH_PLAN_INVALID

    # Required fields present and non-None
    for key in sorted(_REQUIRED_DISPATCH_PLAN_FIELDS):
        if key not in plan or plan[key] is None:
            return ERROR_DISPATCH_PLAN_INVALID

    # canonicalName non-empty string
    canonical_name = plan.get("canonicalName")
    if not isinstance(canonical_name, str) or not canonical_name.strip():
        return ERROR_DISPATCH_PLAN_INVALID

    # routingMode must be metadata-only
    if plan.get("routingMode") != DISPATCH_ROUTING_MODE:
        return ERROR_DISPATCH_PLAN_INVALID

    # handlerId / registryKey non-empty strings
    handler_id = plan.get("handlerId")
    if not isinstance(handler_id, str) or not handler_id.strip():
        return ERROR_DISPATCH_PLAN_INVALID
    registry_key = plan.get("registryKey")
    if not isinstance(registry_key, str) or not registry_key.strip():
        return ERROR_DISPATCH_PLAN_INVALID
    handler_lookup_id = plan.get("handlerLookupId")
    if not isinstance(handler_lookup_id, str) or not handler_lookup_id.strip():
        return ERROR_DISPATCH_PLAN_INVALID

    # Consistency against expected values (if provided)
    if expected_canonical_name is not None and canonical_name != expected_canonical_name:
        return ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH
    if (
        expected_handler_lookup_id is not None
        and handler_lookup_id != expected_handler_lookup_id
    ):
        return ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH
    if expected_registry_key is not None and registry_key != expected_registry_key:
        return ERROR_DISPATCH_REGISTRY_MISMATCH

    # Side-effect flags must be safe
    if plan.get("dispatchAllowed") is not False:
        return ERROR_DISPATCH_SIDE_EFFECT_RISK
    if plan.get("toolHandlerCallAllowed") is not False:
        return ERROR_DISPATCH_SIDE_EFFECT_RISK
    if plan.get("executionAllowed") is not False:
        return ERROR_DISPATCH_SIDE_EFFECT_RISK
    if plan.get("providerSchemaAllowed") is not False:
        return ERROR_DISPATCH_SIDE_EFFECT_RISK
    if plan.get("sideEffectFreeDispatch") is not True:
        return ERROR_DISPATCH_SIDE_EFFECT_RISK

    return None


# ---------------------------------------------------------------------------
# 7. Safe dispatch summary
# ---------------------------------------------------------------------------


def safe_dispatch_summary(
    *,
    dispatch_id: str | None,
    dispatch_status: str,
    canonical_name: str | None = None,
) -> dict[str, Any]:
    """Build a safe summary from a dispatch result.

    Never exposes raw token, full tokenHash, raw arguments, callable object,
    function repr, provider credentials, secrets, or authorization headers.
    """
    summary: dict[str, Any] = {
        "dispatchId": dispatch_id,
        "dispatchStatus": dispatch_status,
    }
    if canonical_name is not None:
        summary["canonicalName"] = canonical_name
    return summary


# ---------------------------------------------------------------------------
# 8. Dispatch plan builder
# ---------------------------------------------------------------------------


def build_dispatch_plan(
    *,
    canonical_name: str,
    handler_lookup_id: str | None,
    handler_descriptor: dict[str, Any] | None,
    allowlist: frozenset[str] | None = None,
    risk_tier: str | None = None,
    policy_version: str | None = None,
    toolset_name: str | None = None,
    category: str | None = None,
    handler_descriptor_version: int | None = None,
) -> DispatchResult:
    """Build a safe dispatch plan / dispatch envelope.

    This function constructs side-effect-free routing metadata only. It does
    NOT:
      - Import any handler module
      - Instantiate any handler
      - Call any callable
      - Invoke the dispatch runtime
      - Access ~/.hermes
      - Read production state.db
      - Read provider keys
      - Store raw confirmationToken
      - Store full tokenHash
      - Store raw arguments
      - Store secrets

    Dispatch plan success is NOT Tool Handler call permission. Tool Handler
    call remains disabled. After a successful build, execute still blocks at
    ``blocked_tool_handler_call_not_enabled``.

    Args:
        canonical_name: The allowlisted canonical tool name.
        handler_lookup_id: Correlation ID from a successful handler lookup.
        handler_descriptor: Safe handler descriptor from handler lookup.
        allowlist: The STATIC_ALLOWLIST to check against. If None, the
            built-in STATIC_ALLOWLIST is used.
        risk_tier: Expected risk tier for policy consistency.
        policy_version: Optional policy version metadata.
        toolset_name: Optional toolset name metadata.
        category: Optional category metadata.
        handler_descriptor_version: Optional handler descriptor version.

    Returns:
        DispatchResult with the safe dispatch plan or a fail-closed result.
    """
    side_effect_flags = _build_side_effect_flags()
    now = _dispatch_now()
    created_at = now.isoformat()

    # Gate 57: Dispatch enable gate — dispatch planning is enabled in this
    # phase (metadata-only). Tool Handler call remains disabled.

    # Gate 58: Handler lookup result available — handlerLookupId present
    if not isinstance(handler_lookup_id, str) or not handler_lookup_id.strip():
        return _fail_closed(
            error_code=ERROR_DISPATCH_PLAN_UNAVAILABLE,
            decision=DECISION_BLOCKED_DISPATCH_PLAN_UNAVAILABLE,
            gate=GATE_DISPATCH_PLAN,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )

    # canonicalName must be a non-empty string
    if not isinstance(canonical_name, str) or not canonical_name.strip():
        return _fail_closed(
            error_code=ERROR_DISPATCH_PLAN_INVALID,
            decision=DECISION_BLOCKED_DISPATCH_PLAN_INVALID,
            gate=GATE_DISPATCH_CANONICAL_NAME,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )

    # Gate 59: Dispatch plan source available — handler descriptor present
    if handler_descriptor is None or not isinstance(handler_descriptor, dict):
        return _fail_closed(
            error_code=ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISSING,
            decision=DECISION_BLOCKED_DISPATCH_HANDLER_DESCRIPTOR_MISSING,
            gate=GATE_DISPATCH_PLAN_SOURCE,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )

    # Gate 63 (allowlist): canonicalName must be allowlisted.
    # Dispatch plan existence is NOT permission; STATIC_ALLOWLIST is.
    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

    effective_allowlist = allowlist if allowlist is not None else STATIC_ALLOWLIST
    if canonical_name not in effective_allowlist:
        return _fail_closed(
            error_code=ERROR_DISPATCH_NOT_ALLOWLISTED,
            decision=DECISION_BLOCKED_DISPATCH_NOT_ALLOWLISTED,
            gate=GATE_DISPATCH_ALLOWLIST,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )

    # Extract safe handler descriptor fields
    desc_canonical = handler_descriptor.get("canonicalName")
    handler_id = handler_descriptor.get("handlerId")
    registry_key = handler_descriptor.get("registryKey")
    desc_risk_tier = handler_descriptor.get("riskTier")

    # Gate 61: Validate canonicalName consistency
    if not isinstance(desc_canonical, str) or desc_canonical != canonical_name:
        return _fail_closed(
            error_code=ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH,
            decision=DECISION_BLOCKED_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH,
            gate=GATE_DISPATCH_CANONICAL_NAME,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )

    # handlerId must be a non-empty string
    if not isinstance(handler_id, str) or not handler_id.strip():
        return _fail_closed(
            error_code=ERROR_DISPATCH_PLAN_INVALID,
            decision=DECISION_BLOCKED_DISPATCH_PLAN_INVALID,
            gate=GATE_DISPATCH_PLAN_SOURCE,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )

    # Gate 62: Validate handler descriptor registry consistency.
    # For builtin allowlisted tools, registryKey equals canonicalName.
    if not isinstance(registry_key, str) or not registry_key.strip():
        return _fail_closed(
            error_code=ERROR_DISPATCH_REGISTRY_MISMATCH,
            decision=DECISION_BLOCKED_DISPATCH_REGISTRY_MISMATCH,
            gate=GATE_DISPATCH_REGISTRY,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )
    if registry_key != canonical_name:
        return _fail_closed(
            error_code=ERROR_DISPATCH_REGISTRY_MISMATCH,
            decision=DECISION_BLOCKED_DISPATCH_REGISTRY_MISMATCH,
            gate=GATE_DISPATCH_REGISTRY,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )

    # Gate 63 (policy): risk tier consistency
    if not isinstance(desc_risk_tier, str) or not desc_risk_tier.strip():
        return _fail_closed(
            error_code=ERROR_DISPATCH_POLICY_MISMATCH,
            decision=DECISION_BLOCKED_DISPATCH_POLICY_MISMATCH,
            gate=GATE_DISPATCH_POLICY,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )
    if risk_tier is not None and desc_risk_tier != risk_tier:
        return _fail_closed(
            error_code=ERROR_DISPATCH_POLICY_MISMATCH,
            decision=DECISION_BLOCKED_DISPATCH_POLICY_MISMATCH,
            gate=GATE_DISPATCH_POLICY,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )

    # Gate 64: Side-effect-free metadata only — enforce descriptor side-effect
    # flags are safe. Dispatch planning must never inherit execution permission
    # from the handler descriptor.
    if handler_descriptor.get("dispatchAllowed") is not False:
        return _fail_closed(
            error_code=ERROR_DISPATCH_SIDE_EFFECT_RISK,
            decision=DECISION_BLOCKED_DISPATCH_SIDE_EFFECT_RISK,
            gate=GATE_DISPATCH_PLAN_VALIDATION,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )
    if handler_descriptor.get("executionAllowed") is not False:
        return _fail_closed(
            error_code=ERROR_DISPATCH_SIDE_EFFECT_RISK,
            decision=DECISION_BLOCKED_DISPATCH_SIDE_EFFECT_RISK,
            gate=GATE_DISPATCH_PLAN_VALIDATION,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )
    if handler_descriptor.get("providerSchemaAllowed") is not False:
        return _fail_closed(
            error_code=ERROR_DISPATCH_SIDE_EFFECT_RISK,
            decision=DECISION_BLOCKED_DISPATCH_SIDE_EFFECT_RISK,
            gate=GATE_DISPATCH_PLAN_VALIDATION,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )

    # Build the DispatchPlan (metadata-only, side-effect-free)
    plan = DispatchPlan(
        canonical_name=canonical_name,
        handler_lookup_id=handler_lookup_id,
        handler_id=handler_id,
        registry_key=registry_key,
        routing_mode=DISPATCH_ROUTING_MODE,
        dispatch_allowed=False,
        tool_handler_call_allowed=False,
        execution_allowed=False,
        provider_schema_allowed=False,
        side_effect_free_dispatch=True,
        dispatch_plan_version=DISPATCH_PLAN_VERSION,
        toolset_name=toolset_name,
        category=category,
        risk_tier=desc_risk_tier,
        policy_version=policy_version,
        handler_descriptor_version=handler_descriptor_version,
    )
    plan_dict = plan.to_safe_dict()

    # Validate the built plan against its declared fields
    validation_error = validate_dispatch_plan(
        plan_dict,
        expected_canonical_name=canonical_name,
        expected_handler_lookup_id=handler_lookup_id,
        expected_registry_key=registry_key,
    )
    if validation_error is not None:
        if validation_error == ERROR_DISPATCH_REGISTRY_MISMATCH:
            decision = DECISION_BLOCKED_DISPATCH_REGISTRY_MISMATCH
        elif validation_error == ERROR_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH:
            decision = DECISION_BLOCKED_DISPATCH_HANDLER_DESCRIPTOR_MISMATCH
        elif validation_error == ERROR_DISPATCH_SIDE_EFFECT_RISK:
            decision = DECISION_BLOCKED_DISPATCH_SIDE_EFFECT_RISK
        else:
            decision = DECISION_BLOCKED_DISPATCH_PLAN_INVALID
        return _fail_closed(
            error_code=validation_error,
            decision=decision,
            gate=GATE_DISPATCH_PLAN_VALIDATION,
            created_at=created_at,
            side_effect_flags=side_effect_flags,
        )

    # Gate 65: dispatchId generated (correlation-only, not a credential)
    dispatch_id = generate_dispatch_id()

    # Gate 66: Dispatch safe response fields available
    safe_summary = safe_dispatch_summary(
        dispatch_id=dispatch_id,
        dispatch_status=DISPATCH_STATUS_PLANNED,
        canonical_name=canonical_name,
    )

    # Gate 67: Block because Tool Handler call is not enabled.
    # Gate 68: Tool Handler still not called.
    # Gate 69: Execution still disabled.
    return DispatchResult(
        built=True,
        dispatch_status=DISPATCH_STATUS_PLANNED,
        dispatch_id=dispatch_id,
        dispatch_plan=plan_dict,
        error_code=ERROR_DISPATCH_WRITTEN_BUT_TOOL_HANDLER_CALL_NOT_ENABLED,
        decision=DECISION_BLOCKED_TOOL_HANDLER_CALL_NOT_ENABLED,
        gate=GATE_TOOL_HANDLER_CALL,
        final_block=FINAL_BLOCK_TOOL_HANDLER_CALL_NOT_ENABLED,
        created_at=created_at,
        side_effect_flags=side_effect_flags,
        safe_summary=safe_summary,
    )


# ``create_dispatch_plan`` is a public alias for ``build_dispatch_plan``.
# It exists so callers can express intent ("create a dispatch plan") without
# coupling to the internal builder name.
def create_dispatch_plan(
    *,
    canonical_name: str,
    handler_lookup_id: str | None,
    handler_descriptor: dict[str, Any] | None,
    allowlist: frozenset[str] | None = None,
    risk_tier: str | None = None,
    policy_version: str | None = None,
    toolset_name: str | None = None,
    category: str | None = None,
    handler_descriptor_version: int | None = None,
) -> DispatchResult:
    """Create a safe dispatch plan (alias for :func:`build_dispatch_plan`)."""
    return build_dispatch_plan(
        canonical_name=canonical_name,
        handler_lookup_id=handler_lookup_id,
        handler_descriptor=handler_descriptor,
        allowlist=allowlist,
        risk_tier=risk_tier,
        policy_version=policy_version,
        toolset_name=toolset_name,
        category=category,
        handler_descriptor_version=handler_descriptor_version,
    )
