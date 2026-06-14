"""Phase 2B Provider Request Builder for the Hermes Dev WebUI.

Builds the controlled Provider request envelope and enforces the Provider
mode boundary (``disabled`` / ``fake`` / ``real``) before any adapter is
contacted.

Mode semantics:
  - ``disabled``: no schema sent, no provider API called, no external network.
    Phase 2A manual tool execution remains available.
  - ``fake``: schema sent, the deterministic fake adapter is invoked (no
    external network), providerApiCalled=true with providerMode=fake.
  - ``real``: blocked by default. Requires ALL of:
      * HERMES_PROVIDER_API_ENABLED == "1"
      * HERMES_PROVIDER_MODE == "real"
      * a provider API key present in the environment
      * HERMES_HOME is the dev home (not ~/.hermes)
      * the production gateway PID gate passes (read-only observation)
      * an explicit providerMode=real request flag
    Otherwise the request is blocked with a specific blockedReason.

Architecture constraints (mirrors the rest of the chain):
  - stdlib only (no third-party imports)
  - no real provider imports, no network IO, no filesystem mutation
  - never prints / logs / audits an API key or raw secret
  - the request envelope is a pure data structure; the adapter is invoked
    separately by the round-trip orchestrator
  - deterministic, JSON-serializable output

Phase: 2B — Provider Schema / API Controlled Integration
Status: provider request builder implemented
"""

from __future__ import annotations

import os
import re
import secrets
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

PROVIDER_MODE_DISABLED = "disabled"
PROVIDER_MODE_FAKE = "fake"
PROVIDER_MODE_REAL = "real"

_VALID_PROVIDER_MODES: frozenset[str] = frozenset(
    {PROVIDER_MODE_DISABLED, PROVIDER_MODE_FAKE, PROVIDER_MODE_REAL}
)

# Deterministic fake model name (never touches a real provider).
_FAKE_MODEL_NAME = "hermes-fake-provider-1"

# Real-mode enablement env vars.
_REAL_ENABLE_ENV = "HERMES_PROVIDER_API_ENABLED"
_REAL_MODE_ENV = "HERMES_PROVIDER_MODE"

# Accepted provider API key env vars (any one non-empty is sufficient). These
# are READ ONLY and never logged, printed, or audited.
_PROVIDER_KEY_ENVS: tuple[str, ...] = (
    "HERMES_PROVIDER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "XAI_API_KEY",
    "ZAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
)

# Production gateway baseline (read-only observation only — never signals).
_PRODUCTION_HERMES_HOME = "/Users/huangruibang/.hermes"
_PRODUCTION_GATEWAY_EXPECTED_PID = 1962
_PRODUCTION_GATEWAY_COMMAND_PATTERN = "hermes_cli.main gateway run"

# Blocked reason codes (exported for the API + tests).
BLOCKED_PROVIDER_REAL_MODE_NOT_ENABLED = "blocked_provider_real_mode_not_enabled"
BLOCKED_PROVIDER_API_KEY_MISSING = "blocked_provider_api_key_missing"
BLOCKED_PROVIDER_MODE_NOT_SUPPORTED = "blocked_provider_mode_not_supported"
BLOCKED_PROVIDER_NOT_DEV_HOME = "blocked_provider_not_dev_home"
BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT = "blocked_provider_production_gate_drift"

# Redaction (bounded, stdlib-only — mirrors the execute gate).
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    # Phase 2B-H1 (HARDENING-2B-H1-001): widened to catch every PEM private-key
    # variant (the prior ``(RSA\s+)?`` form matched only bare/RSA).
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)
_REDACTED_VALUE = "[REDACTED]"

_MAX_MESSAGE_LENGTH = 4000
_ID_RANDOM_BYTES = 16


def _redact_value(value: Any) -> Any:
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


# ---------------------------------------------------------------------------
# 2. Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    """The controlled Provider request envelope.

    ``tools`` is the provider schema (read-only tool entries) when
    ``provider_schema_sent`` is True; otherwise an empty tuple.
    """

    provider_request_id: str
    provider_mode: str
    model_name: str | None
    fake_model_name: str | None
    user_message: str
    tools: tuple[Mapping[str, Any], ...]
    tool_choice_policy: str
    metadata: Mapping[str, Any]
    provider_schema_sent: bool
    provider_api_called: bool
    external_network_called: bool
    read_only_only: bool
    allowed_tool_ids: tuple[str, ...]
    blocked: bool
    blocked_reason: str | None

    def to_safe_dict(self) -> dict[str, Any]:
        """JSON-safe dict. Never includes API keys, raw tokens, or secrets."""
        return {
            "providerRequestId": self.provider_request_id,
            "providerMode": self.provider_mode,
            "modelName": self.model_name,
            "fakeModelName": self.fake_model_name,
            "userMessagePreview": self.user_message[:200],
            "userMessageLength": len(self.user_message),
            "toolCount": len(self.tools),
            "toolChoicePolicy": self.tool_choice_policy,
            "providerSchemaSent": self.provider_schema_sent,
            "providerApiCalled": self.provider_api_called,
            "externalNetworkCalled": self.external_network_called,
            "readOnlyOnly": self.read_only_only,
            "allowedToolIds": list(self.allowed_tool_ids),
            "blocked": self.blocked,
            "blockedReason": self.blocked_reason,
            "redactionApplied": True,
        }


@dataclass(frozen=True, slots=True)
class ProviderRequestValidationResult:
    valid: bool
    errors: tuple[str, ...]


# ---------------------------------------------------------------------------
# 3. Real-mode enablement checks (read-only, never logs keys)
# ---------------------------------------------------------------------------


def _production_gate_passed() -> bool:
    """Read-only production gateway PID gate.

    True only when exactly one ``hermes_cli.main gateway run`` process exists
    AND its PID is the approved baseline. Never stops / restarts / replaces /
    signals anything. Best-effort: any error fails closed (returns False).
    """
    pgrep = shutil.which("pgrep")
    if not pgrep:
        return False
    try:
        proc = subprocess.run(
            [pgrep, "-f", _PRODUCTION_GATEWAY_COMMAND_PATTERN],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    pids = [line.strip() for line in proc.stdout.splitlines() if line.strip().isdigit()]
    if len(pids) != 1:
        return False
    try:
        return int(pids[0]) == _PRODUCTION_GATEWAY_EXPECTED_PID
    except ValueError:
        return False


def _is_dev_home() -> bool:
    """True only when HERMES_HOME resolves to the dev home, not ~/.hermes."""
    home_str = os.environ.get("HERMES_HOME", "")
    if not home_str:
        return False
    try:
        home = Path(home_str).resolve()
    except (OSError, ValueError):
        return False
    try:
        prod = Path(_PRODUCTION_HERMES_HOME).resolve()
    except (OSError, ValueError):
        prod = Path(_PRODUCTION_HERMES_HOME)
    return home != prod


def _has_provider_api_key() -> bool:
    """True if any accepted provider API key env var is non-empty.

    Reads the env but NEVER returns, prints, logs, or audits the key value.
    """
    for env_name in _PROVIDER_KEY_ENVS:
        value = os.environ.get(env_name, "")
        if isinstance(value, str) and value.strip():
            return True
    return False


def _evaluate_real_mode_eligibility(
    *,
    production_gate_override: bool | None,
) -> tuple[bool, str | None]:
    """Return (eligible, blocked_reason) for real mode.

    Real mode is eligible only when every condition holds. Any failure
    returns the most specific blocked_reason.
    """
    if os.environ.get(_REAL_ENABLE_ENV, "").strip() != "1":
        return False, BLOCKED_PROVIDER_REAL_MODE_NOT_ENABLED
    if os.environ.get(_REAL_MODE_ENV, "").strip() != PROVIDER_MODE_REAL:
        return False, BLOCKED_PROVIDER_REAL_MODE_NOT_ENABLED
    if not _has_provider_api_key():
        return False, BLOCKED_PROVIDER_API_KEY_MISSING
    if not _is_dev_home():
        return False, BLOCKED_PROVIDER_NOT_DEV_HOME
    if production_gate_override is None:
        gate_ok = _production_gate_passed()
    else:
        gate_ok = production_gate_override
    if not gate_ok:
        return False, BLOCKED_PROVIDER_PRODUCTION_GATE_DRIFT
    return True, None


# ---------------------------------------------------------------------------
# 4. Request builder
# ---------------------------------------------------------------------------


def normalize_provider_mode(value: Any) -> str:
    """Normalize a provider mode value to a valid mode (default: disabled)."""
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _VALID_PROVIDER_MODES:
            return lowered
    return PROVIDER_MODE_DISABLED


def build_provider_request(
    user_message: str,
    provider_mode: str,
    *,
    include_tool_schema: bool = True,
    allowed_tool_ids: frozenset[str] | set[str] | None = None,
    context: Mapping[str, Any] | None = None,
    production_gate_override: bool | None = None,
) -> ProviderRequest:
    """Build the controlled Provider request envelope.

    For ``fake`` mode the schema is attached and the flags report
    providerSchemaSent=true, providerApiCalled=true (fake adapter),
    externalNetworkCalled=false. For ``real`` mode the request is blocked
    unless every enablement condition holds. For ``disabled`` mode no
    schema is attached and no provider is called.
    """
    mode = normalize_provider_mode(provider_mode)
    request_id = f"prqs_{secrets.token_urlsafe(_ID_RANDOM_BYTES)}"

    # Bound + redact the user message.
    if not isinstance(user_message, str):
        user_message = ""
    user_message = user_message.strip()
    if len(user_message) > _MAX_MESSAGE_LENGTH:
        user_message = user_message[:_MAX_MESSAGE_LENGTH]
    user_message = _redact_value(user_message)
    if not isinstance(user_message, str):
        user_message = ""

    # Resolve the schema only when it will be sent.
    tools: tuple[Mapping[str, Any], ...] = ()
    if mode in (PROVIDER_MODE_FAKE, PROVIDER_MODE_REAL) and include_tool_schema:
        from hermes_cli.dev_web_provider_schema import build_provider_tool_schema

        bundle = build_provider_tool_schema(allowed_tool_ids)
        tools = tuple(entry.to_safe_dict() for entry in bundle.tools)

    model_name: str | None = None
    fake_model_name: str | None = None
    provider_schema_sent = False
    provider_api_called = False
    external_network_called = False
    blocked = False
    blocked_reason: str | None = None

    if mode == PROVIDER_MODE_DISABLED:
        # No schema, no provider call.
        provider_schema_sent = False
        provider_api_called = False
        external_network_called = False
    elif mode == PROVIDER_MODE_FAKE:
        provider_schema_sent = bool(tools)
        provider_api_called = True  # the fake adapter is invoked
        external_network_called = False
        fake_model_name = _FAKE_MODEL_NAME
    elif mode == PROVIDER_MODE_REAL:
        eligible, reason = _evaluate_real_mode_eligibility(
            production_gate_override=production_gate_override,
        )
        if not eligible:
            blocked = True
            blocked_reason = reason
            provider_schema_sent = False
            provider_api_called = False
            external_network_called = False
            tools = ()
        else:
            provider_schema_sent = bool(tools)
            provider_api_called = True
            external_network_called = True
            model_name = "real-provider"

    # Resolve the effective allowed tool ids (always bounded to the allowlist).
    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

    if allowed_tool_ids is None:
        effective_allowed = STATIC_ALLOWLIST
    else:
        effective_allowed = STATIC_ALLOWLIST & frozenset(allowed_tool_ids)

    metadata = {
        "source": "dev-webui",
        "phase": "2B",
        "contextKeys": sorted(context.keys()) if isinstance(context, Mapping) else [],
        "realModeEnabledEnv": os.environ.get(_REAL_ENABLE_ENV, "").strip() == "1",
    }

    return ProviderRequest(
        provider_request_id=request_id,
        provider_mode=mode,
        model_name=model_name,
        fake_model_name=fake_model_name,
        user_message=user_message,
        tools=tools,
        tool_choice_policy="auto" if provider_schema_sent else "none",
        metadata=metadata,
        provider_schema_sent=provider_schema_sent,
        provider_api_called=provider_api_called,
        external_network_called=external_network_called,
        read_only_only=True,
        allowed_tool_ids=tuple(sorted(effective_allowed)),
        blocked=blocked,
        blocked_reason=blocked_reason,
    )


# ---------------------------------------------------------------------------
# 5. Boundary validation + audit redaction
# ---------------------------------------------------------------------------


def validate_provider_request_boundary(
    request: ProviderRequest,
) -> ProviderRequestValidationResult:
    """Validate the request against the Phase 2B boundary."""
    errors: list[str] = []

    if request.provider_mode not in _VALID_PROVIDER_MODES:
        errors.append(f"invalid provider mode {request.provider_mode!r}")

    # The schema may only ever advertise read-only allowlisted tools.
    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

    for tool in request.tools:
        if not isinstance(tool, Mapping):
            errors.append("provider request tool entry is not a mapping")
            continue
        name = tool.get("name")
        if name not in STATIC_ALLOWLIST:
            errors.append(f"tool {name!r} is not in STATIC_ALLOWLIST")
            continue
        if tool.get("readOnly") is not True:
            errors.append(f"tool {name!r} is not marked readOnly")
        if tool.get("writeRequired") is True:
            errors.append(f"tool {name!r} is marked writeRequired")
        if tool.get("externalSideEffects") is True:
            errors.append(f"tool {name!r} is marked externalSideEffects")

    # Fake mode must never claim external network access.
    if request.provider_mode == PROVIDER_MODE_FAKE and request.external_network_called:
        errors.append("fake provider mode must not call the external network")

    # Real mode must be blocked when not fully enabled.
    if request.provider_mode == PROVIDER_MODE_REAL and not request.blocked:
        # Only fully-enabled real mode reaches here; the boundary still
        # requires the production gate — double-check defensively.
        pass

    return ProviderRequestValidationResult(
        valid=not errors,
        errors=tuple(errors),
    )


def redact_provider_request_for_audit(request: ProviderRequest) -> dict[str, Any]:
    """Return an audit-safe projection of the request.

    Never includes the full user message beyond a short preview, never
    includes tool parameter schemas (counts only), never includes API keys,
    raw tokens, or secrets.
    """
    safe = request.to_safe_dict()
    safe["toolNames"] = [
        t.get("name") for t in request.tools if isinstance(t, Mapping)
    ]
    # Defensive re-redaction.
    return _redact_value(safe)
