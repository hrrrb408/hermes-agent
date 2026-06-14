"""Phase 2A Read-only Tool Registry for the Hermes Dev WebUI.

This module is the single metadata source for the five Phase 2A read-only
inspection tools that the Dev WebUI exposes through the controlled-execution
chain (dry-run -> confirmation token -> digest verification -> pre-execution
audit -> handler lookup -> dispatch planning -> handler call -> post-execution
audit).

The five tools are Dev-WebUI-local read-only *inspection* surfaces. They are
NOT registered Hermes agent tools (``tools/registry.py``) and are NOT in the
production tool dispatch path. They mirror the bounded-reimplementation
pattern already used for the ``clarify`` handler in
``dev_web_tool_handler_call.py``: each tool is a bounded, deterministic,
side-effect-free pure function that inspects only dev-local, in-process state.

The single source of truth for *allowlist membership* remains
``STATIC_ALLOWLIST`` in ``dev_web_tool_policy.py``. This registry layer adds
the rich per-tool metadata (display name, argument schema, safety tier) that
the policy inventory's ``ToolPolicyEntry`` does not carry. This registry
cross-checks its tool ids against ``STATIC_ALLOWLIST`` at import time so the
two representations cannot silently drift.

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider imports, no real tool handler imports, no agent imports
  - no network IO, no filesystem mutation, no shell / file / browser execution
  - no STATIC_ALLOWLIST mutation
  - argument validation is strict-whitelist (rejects unknown keys, secret
    stems, path values, shell values, regex, glob)
  - deterministic, JSON-serializable output

Phase: 2A — Real Tool Execution MVP (Read-only Multi-tool Execution)
Status: read-only registry implemented
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# 1. Single-source re-export of the allowlist (DO NOT duplicate)
# ---------------------------------------------------------------------------
#
# ``STATIC_ALLOWLIST`` is defined ONCE in ``dev_web_tool_policy.py`` and is the
# authoritative permission boundary. This registry re-exports it so callers have
# a single import surface, but there is exactly one definition in the codebase.

from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST  # noqa: E402


# ---------------------------------------------------------------------------
# 2. Read-only tool definition record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReadOnlyToolDefinition:
    """Immutable metadata record for one Phase 2A read-only tool.

    All Phase 2A read-only tools share the same invariant safety profile:

      - ``read_only`` is True
      - ``external_side_effects`` is False
      - ``provider_required`` is False
      - ``write_required`` is False
      - ``requires_confirmation`` is True (they flow through the full
        controlled-execution chain, including the confirmation token)
    """

    tool_id: str
    display_name: str
    description: str
    category: str
    safety_tier: str
    read_only: bool
    external_side_effects: bool
    provider_required: bool
    write_required: bool
    requires_confirmation: bool
    argument_schema: Mapping[str, Any]
    result_schema: Mapping[str, Any]
    audit_redaction_policy: str
    enabled_in_phase: str


# ---------------------------------------------------------------------------
# 3. Argument validation primitives (strict whitelist)
# ---------------------------------------------------------------------------

# Maximum bounds for string filters — generous for inspection but bounded to
# prevent abuse. Path traversal, shell, SQL, glob, regex from user input are
# never accepted.
_MAX_FILTER_STRING_LENGTH = 128
_MAX_EVENT_TYPE_LENGTH = 80
_MAX_STATUS_LENGTH = 64
_DEFAULT_AUDIT_LIMIT = 20
_MAX_AUDIT_LIMIT = 100

# Forbidden argument key stems — these never appear in any read-only tool's
# accepted argument set. Mirrors the redaction stems used across the chain.
_FORBIDDEN_ARG_STEMS: frozenset[str] = frozenset(
    {
        "apikey", "api_key", "authorization", "auth", "bearer", "token",
        "secret", "password", "passwd", "credential", "cookie", "session",
        "privatekey", "private_key", "clientsecret", "client_secret",
        "accesstoken", "access_token", "refresh_token", "access_key",
        "path", "filepath", "filename", "file", "dir", "directory",
        "command", "cmd", "shell", "exec", "script", "sql", "query",
        "regex", "pattern", "glob",
    }
)


def _is_forbidden_key(key: str) -> bool:
    """Return True if *key* matches a forbidden argument stem."""
    if not isinstance(key, str):
        return True
    normalized = key.strip().lower().replace("-", "").replace("_", "")
    return normalized in _FORBIDDEN_ARG_STEMS or any(
        stem in normalized for stem in ("token", "secret", "password", "key", "auth")
    )


def _as_bool(value: Any) -> bool | None:
    """Coerce *value* to bool strictly. Returns None on invalid input."""
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "on"):
            return True
        if lowered in ("false", "0", "no", "off", ""):
            return False
    return None


def _as_bounded_int(value: Any, *, minimum: int, maximum: int) -> int | None:
    """Coerce *value* to a bounded int. Returns None on invalid input."""
    if isinstance(value, bool):  # bool is an int subclass — reject explicitly
        return None
    if isinstance(value, int):
        if minimum <= value <= maximum:
            return value
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            parsed = int(stripped)
        except ValueError:
            return None
        if minimum <= parsed <= maximum:
            return parsed
    return None


def _as_bounded_string(value: Any, *, max_length: int) -> str | None:
    """Coerce *value* to a bounded, stripped string. None on invalid input."""
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if len(stripped) > max_length:
            return None
        # Reject anything that looks like a path / shell / secret.
        if _contains_unsafe_fragment(stripped):
            return None
        return stripped
    return None


def _contains_unsafe_fragment(value: str) -> bool:
    """Reject strings that resemble paths, shell, or secret material."""
    if not value:
        return False
    # Path traversal / absolute paths / home references
    if value.startswith(("/", "~", "\\")):
        return True
    if ".." in value:
        return True
    if value.startswith("file://"):
        return True
    # Shell metacharacters
    if any(ch in value for ch in ("|", ";", "`", "$", ">", "<", "&", "\n", "\r")):
        return True
    # Secret patterns
    lowered = value.lower()
    if "bearer " in lowered or lowered.startswith("sk-"):
        return True
    return False


# ---------------------------------------------------------------------------
# 4. Per-tool argument specifications
# ---------------------------------------------------------------------------
#
# Each spec lists the accepted argument keys, their coercion helper, default,
# and a short human note. Anything not in the spec is rejected as unknown.

_ARG_ERROR_UNKNOWN_TOOL = "READ_ONLY_ARG_UNKNOWN_TOOL"
_ARG_ERROR_NON_DICT = "READ_ONLY_ARG_NON_DICT"
_ARG_ERROR_UNKNOWN_KEY = "READ_ONLY_ARG_UNKNOWN_KEY"
_ARG_ERROR_FORBIDDEN_KEY = "READ_ONLY_ARG_FORBIDDEN_KEY"
_ARG_ERROR_INVALID_VALUE = "READ_ONLY_ARG_INVALID_VALUE"


def _spec_bool(key: str, default: bool) -> dict[str, Any]:
    return {"key": key, "kind": "bool", "default": default}


def _spec_int(key: str, minimum: int, maximum: int, default: int) -> dict[str, Any]:
    return {"key": key, "kind": "int", "min": minimum, "max": maximum, "default": default}


def _spec_str(key: str, max_length: int) -> dict[str, Any]:
    return {"key": key, "kind": "str", "max": max_length}


# Per-tool accepted-argument tables. Order is stable for documentation.
_TOOL_ARGUMENT_SPECS: Mapping[str, tuple[dict[str, Any], ...]] = MappingProxyType(
    {
        "tool_policy_read": (
            _spec_bool("includeDisabled", default=False),
        ),
        "route_governance_read": (
            _spec_bool("includeDetails", default=False),
        ),
        "audit_events_read": (
            _spec_int("limit", 1, _MAX_AUDIT_LIMIT, _DEFAULT_AUDIT_LIMIT),
            _spec_str("eventType", _MAX_EVENT_TYPE_LENGTH),
            _spec_str("toolId", _MAX_FILTER_STRING_LENGTH),
            _spec_str("status", _MAX_STATUS_LENGTH),
            _spec_str("correlationId", _MAX_FILTER_STRING_LENGTH),
        ),
        "dev_environment_read": (
            _spec_bool("includePorts", default=True),
            _spec_bool("includeProductionGatewayReadOnlyCheck", default=True),
        ),
        "release_status_read": (
            _spec_bool("includePhaseTimeline", default=False),
            _spec_bool("includeP2Backlog", default=False),
        ),
    }
)


# ---------------------------------------------------------------------------
# 5. Read-only tool definitions
# ---------------------------------------------------------------------------

_BOOL_ARG_SCHEMA_COMMON = {
    "type": "object",
    "additionalProperties": False,
}

_READ_ONLY_SAFETY_TIER = "read_only_safe"
_AUDIT_REDACTION = (
    "stores redactedArgumentsPreview only; never raw token, full tokenHash, "
    "raw arguments, secrets, or callable/function repr"
)


def _json_schema(properties: dict[str, Any], required: tuple[str, ...] = ()) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
    }
    if required:
        schema["required"] = list(required)
    return schema


_TOOL_POLICY_READ_ARGUMENTS = _json_schema(
    {
        "includeDisabled": {
            "type": "boolean",
            "default": False,
            "description": "Include disabled/denied tool categories in the summary.",
        }
    }
)

_ROUTE_GOVERNANCE_READ_ARGUMENTS = _json_schema(
    {
        "includeDetails": {
            "type": "boolean",
            "default": False,
            "description": "Include per-route detail in the governance summary.",
        }
    }
)

_AUDIT_EVENTS_READ_ARGUMENTS = _json_schema(
    {
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": _MAX_AUDIT_LIMIT,
            "default": _DEFAULT_AUDIT_LIMIT,
        },
        "eventType": {"type": "string", "maxLength": _MAX_EVENT_TYPE_LENGTH},
        "toolId": {"type": "string", "maxLength": _MAX_FILTER_STRING_LENGTH},
        "status": {"type": "string", "maxLength": _MAX_STATUS_LENGTH},
        "correlationId": {"type": "string", "maxLength": _MAX_FILTER_STRING_LENGTH},
    }
)

_DEV_ENVIRONMENT_READ_ARGUMENTS = _json_schema(
    {
        "includePorts": {
            "type": "boolean",
            "default": True,
            "description": "Include read-only port checks (lsof) for 5180/5181.",
        },
        "includeProductionGatewayReadOnlyCheck": {
            "type": "boolean",
            "default": True,
            "description": "Include read-only production gateway PID/count observation.",
        },
    }
)

_RELEASE_STATUS_READ_ARGUMENTS = _json_schema(
    {
        "includePhaseTimeline": {"type": "boolean", "default": False},
        "includeP2Backlog": {"type": "boolean", "default": False},
    }
)


_READ_ONLY_TOOL_DEFINITIONS_RAW: dict[str, ReadOnlyToolDefinition] = {
    "tool_policy_read": ReadOnlyToolDefinition(
        tool_id="tool_policy_read",
        display_name="Tool Policy Read",
        description=(
            "Return the current tool-execution policy: the static allowlist, "
            "the read-only candidate tools, disabled/denied categories, route "
            "counts, and the Phase 2A safety boundaries."
        ),
        category="policy",
        safety_tier=_READ_ONLY_SAFETY_TIER,
        read_only=True,
        external_side_effects=False,
        provider_required=False,
        write_required=False,
        requires_confirmation=True,
        argument_schema=_TOOL_POLICY_READ_ARGUMENTS,
        result_schema=_json_schema(
            {
                "staticAllowlist": {"type": "array", "items": {"type": "string"}},
                "candidateAllowlist": {"type": "array", "items": {"type": "string"}},
                "staticAllowlistSize": {"type": "integer"},
                "readOnly": {"type": "boolean"},
                "providerRequired": {"type": "boolean"},
                "writeRequired": {"type": "boolean"},
                "externalSideEffects": {"type": "boolean"},
            }
        ),
        audit_redaction_policy=_AUDIT_REDACTION,
        enabled_in_phase="2A",
    ),
    "route_governance_read": ReadOnlyToolDefinition(
        tool_id="route_governance_read",
        display_name="Route Governance Read",
        description=(
            "Return the current OpenAPI/runtime/tool route governance summary "
            "(OpenAPI paths, runtime routes, tool GET / write / dry-run / "
            "execution route counts, and the static allowlist)."
        ),
        category="governance",
        safety_tier=_READ_ONLY_SAFETY_TIER,
        read_only=True,
        external_side_effects=False,
        provider_required=False,
        write_required=False,
        requires_confirmation=True,
        argument_schema=_ROUTE_GOVERNANCE_READ_ARGUMENTS,
        result_schema=_json_schema(
            {
                "openApiPaths": {"type": "integer"},
                "runtimeRoutes": {"type": "integer"},
                "toolGetRoutes": {"type": "integer"},
                "toolWriteRoutes": {"type": "integer"},
                "toolDryRunRoutes": {"type": "integer"},
                "toolExecutionRoutes": {"type": "integer"},
                "staticAllowlist": {"type": "array", "items": {"type": "string"}},
            }
        ),
        audit_redaction_policy=_AUDIT_REDACTION,
        enabled_in_phase="2A",
    ),
    "audit_events_read": ReadOnlyToolDefinition(
        tool_id="audit_events_read",
        display_name="Audit Events Read",
        description=(
            "Query the dev environment audit-event summary with safe filters "
            "(limit, eventType, toolId, status, correlationId). Reads only the "
            "dev JSONL audit stores; never production state.db or ~/.hermes."
        ),
        category="audit",
        safety_tier=_READ_ONLY_SAFETY_TIER,
        read_only=True,
        external_side_effects=False,
        provider_required=False,
        write_required=False,
        requires_confirmation=True,
        argument_schema=_AUDIT_EVENTS_READ_ARGUMENTS,
        result_schema=_json_schema(
            {
                "items": {"type": "array"},
                "count": {"type": "integer"},
                "hasMore": {"type": "boolean"},
                "filtersApplied": {"type": "object"},
                "redactionApplied": {"type": "boolean"},
            }
        ),
        audit_redaction_policy=_AUDIT_REDACTION,
        enabled_in_phase="2A",
    ),
    "dev_environment_read": ReadOnlyToolDefinition(
        tool_id="dev_environment_read",
        display_name="Dev Environment Read",
        description=(
            "Return the dev environment health summary: HERMES_HOME, dev "
            "gateway status, ports 5180/5181, and a read-only production "
            "gateway PID/count observation. Never accesses ~/.hermes or "
            "production state.db; never stops/restarts/signals the gateway."
        ),
        category="environment",
        safety_tier=_READ_ONLY_SAFETY_TIER,
        read_only=True,
        external_side_effects=False,
        provider_required=False,
        write_required=False,
        requires_confirmation=True,
        argument_schema=_DEV_ENVIRONMENT_READ_ARGUMENTS,
        result_schema=_json_schema(
            {
                "hermesHome": {"type": "string"},
                "isDevHome": {"type": "boolean"},
                "devGatewayStatus": {"type": "string"},
                "port5180": {"type": "string"},
                "port5181": {"type": "string"},
                "productionGatewayPidExpected": {"type": "integer"},
                "productionGatewayPidObserved": {"type": ["integer", "null"]},
                "productionGatewayProcessCount": {"type": "integer"},
                "productionSafetyStatus": {"type": "string"},
            }
        ),
        audit_redaction_policy=_AUDIT_REDACTION,
        enabled_in_phase="2A",
    ),
    "release_status_read": ReadOnlyToolDefinition(
        tool_id="release_status_read",
        display_name="Release Status Read",
        description=(
            "Return the docs/webui release-status summary: Phase 1G sealed, "
            "Phase 2 unlocked, Phase 2A status, the known P2 backlog, and the "
            "next recommended phase. Reads only repo-local docs/webui files."
        ),
        category="release",
        safety_tier=_READ_ONLY_SAFETY_TIER,
        read_only=True,
        external_side_effects=False,
        provider_required=False,
        write_required=False,
        requires_confirmation=True,
        argument_schema=_RELEASE_STATUS_READ_ARGUMENTS,
        result_schema=_json_schema(
            {
                "phase1gStatus": {"type": "string"},
                "phase2Status": {"type": "string"},
                "phase2aStatus": {"type": "string"},
                "finalSealId": {"type": "string"},
                "phase2UnlockId": {"type": "string"},
                "nextRecommendedPhase": {"type": "string"},
            }
        ),
        audit_redaction_policy=_AUDIT_REDACTION,
        enabled_in_phase="2A",
    ),
}

READ_ONLY_TOOL_DEFINITIONS: Mapping[str, ReadOnlyToolDefinition] = MappingProxyType(
    _READ_ONLY_TOOL_DEFINITIONS_RAW
)

# The Phase 2A read-only tool ids (excludes clarify, which is the Phase 1G
# baseline handled separately by the inline clarify handler).
PHASE_2A_READ_ONLY_TOOL_IDS: frozenset[str] = frozenset(
    _READ_ONLY_TOOL_DEFINITIONS_RAW.keys()
)


# ---------------------------------------------------------------------------
# 6. Consistency guard — the registry must agree with STATIC_ALLOWLIST
# ---------------------------------------------------------------------------


def _verify_registry_consistency() -> None:
    """Cross-check the registry against ``STATIC_ALLOWLIST`` at import.

    The five Phase 2A read-only tools MUST all be members of
    ``STATIC_ALLOWLIST`` (otherwise they could not pass the allowlist gate in
    the controlled-execution chain). Raise ``RuntimeError`` on drift so the
    mismatch is impossible to miss at import time.
    """
    errors: list[str] = []

    missing_from_allowlist = PHASE_2A_READ_ONLY_TOOL_IDS - STATIC_ALLOWLIST
    if missing_from_allowlist:
        errors.append(
            f"Phase 2A read-only tools missing from STATIC_ALLOWLIST: "
            f"{sorted(missing_from_allowlist)}"
        )

    for definition in READ_ONLY_TOOL_DEFINITIONS.values():
        if not definition.read_only:
            errors.append(f"Tool {definition.tool_id} is not read-only")
        if definition.external_side_effects:
            errors.append(f"Tool {definition.tool_id} has external side effects")
        if definition.provider_required:
            errors.append(f"Tool {definition.tool_id} requires a provider")
        if definition.write_required:
            errors.append(f"Tool {definition.tool_id} requires a write")
        if not definition.requires_confirmation:
            errors.append(f"Tool {definition.tool_id} does not require confirmation")
        if definition.tool_id not in _TOOL_ARGUMENT_SPECS:
            errors.append(f"Tool {definition.tool_id} has no argument spec")
        if definition.tool_id not in PHASE_2A_READ_ONLY_TOOL_IDS:
            errors.append(f"Tool {definition.tool_id} not in id set")

    if len(PHASE_2A_READ_ONLY_TOOL_IDS) != 5:
        errors.append(
            f"Expected exactly 5 Phase 2A read-only tools, got "
            f"{len(PHASE_2A_READ_ONLY_TOOL_IDS)}"
        )

    if errors:
        raise RuntimeError(
            "Phase 2A read-only registry consistency check failed:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


_verify_registry_consistency()


# ---------------------------------------------------------------------------
# 7. Public query / validation functions
# ---------------------------------------------------------------------------


def get_read_only_tool_definition(tool_id: str) -> ReadOnlyToolDefinition | None:
    """Return the read-only tool definition for *tool_id*, or ``None``."""
    return READ_ONLY_TOOL_DEFINITIONS.get(tool_id)


def list_read_only_tool_definitions() -> tuple[ReadOnlyToolDefinition, ...]:
    """Return all Phase 2A read-only tool definitions, sorted by tool id."""
    return tuple(sorted(READ_ONLY_TOOL_DEFINITIONS.values(), key=lambda d: d.tool_id))


def is_phase_2a_read_only_tool(tool_id: str) -> bool:
    """Return ``True`` if *tool_id* is a Phase 2A read-only tool."""
    return tool_id in PHASE_2A_READ_ONLY_TOOL_IDS


def _coerce_one(spec: dict[str, Any], value: Any) -> tuple[Any, str | None]:
    """Coerce a single argument value per *spec*. Returns (value, error_code)."""
    kind = spec["kind"]
    if kind == "bool":
        if value is None:
            return spec["default"], None
        coerced = _as_bool(value)
        if coerced is None:
            return None, _ARG_ERROR_INVALID_VALUE
        return coerced, None
    if kind == "int":
        if value is None:
            return spec["default"], None
        coerced = _as_bounded_int(value, minimum=spec["min"], maximum=spec["max"])
        if coerced is None:
            return None, _ARG_ERROR_INVALID_VALUE
        return coerced, None
    if kind == "str":
        if value is None:
            return None, None  # optional string
        coerced = _as_bounded_string(value, max_length=spec["max"])
        if coerced is None:
            return None, _ARG_ERROR_INVALID_VALUE
        return coerced, None
    return None, _ARG_ERROR_INVALID_VALUE


def validate_read_only_tool_arguments(
    tool_id: str,
    arguments: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], str | None]:
    """Validate and normalize *arguments* for *tool_id*.

    Returns ``(normalized_arguments, error_code)``. ``error_code`` is ``None``
    on success. Normalization applies defaults, drops unknown keys, and rejects
    forbidden/unsafe values.

    This is a strict whitelist: any key not in the tool's accepted set, any key
    matching a forbidden stem, or any value resembling a path / shell / secret
    is rejected.
    """
    if tool_id not in PHASE_2A_READ_ONLY_TOOL_IDS:
        return {}, _ARG_ERROR_UNKNOWN_TOOL

    if arguments is None:
        arguments_in: Mapping[str, Any] = {}
    elif isinstance(arguments, Mapping):
        arguments_in = arguments
    else:
        return {}, _ARG_ERROR_NON_DICT

    specs = _TOOL_ARGUMENT_SPECS[tool_id]
    accepted_keys = {spec["key"] for spec in specs}

    normalized: dict[str, Any] = {}

    for raw_key, raw_value in arguments_in.items():
        if not isinstance(raw_key, str):
            return {}, _ARG_ERROR_UNKNOWN_KEY
        if _is_forbidden_key(raw_key):
            return {}, _ARG_ERROR_FORBIDDEN_KEY
        if raw_key not in accepted_keys:
            return {}, _ARG_ERROR_UNKNOWN_KEY
        spec = next(s for s in specs if s["key"] == raw_key)
        coerced, err = _coerce_one(spec, raw_value)
        if err is not None:
            return {}, err
        if coerced is not None:
            normalized[raw_key] = coerced

    # Apply defaults for accepted keys that were not supplied.
    for spec in specs:
        key = spec["key"]
        if key not in normalized and spec["kind"] in ("bool", "int"):
            normalized[key] = spec["default"]

    return normalized, None


def normalize_read_only_tool_arguments(
    tool_id: str,
    arguments: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return the normalized argument dict for *tool_id*.

    Always returns a dict populated with the tool's accepted-key defaults so a
    handler never receives untrusted values and always has usable inputs.
    Invalid / unsafe input is reduced to a safe default-only dict.
    """
    normalized, _err = validate_read_only_tool_arguments(tool_id, arguments)
    if not normalized:
        # Validation rejected the input — populate the default-only dict so the
        # handler still receives a safe, usable argument set.
        normalized = {}
        for spec in _TOOL_ARGUMENT_SPECS.get(tool_id, ()):
            if spec["kind"] in ("bool", "int"):
                normalized[spec["key"]] = spec["default"]
    return normalized
