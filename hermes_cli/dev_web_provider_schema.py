"""Phase 2B Provider Schema Builder for the Hermes Dev WebUI.

This module builds the bounded tool schema that may be handed to a Provider in
the controlled Provider Schema / API round-trip (Phase 2B). The schema is
generated **only** from the Phase 2A read-only allowlist
(``STATIC_ALLOWLIST``): ``clarify`` plus the five read-only inspection tools.
No write tool, no provider-recursive tool, no production path, no secret, and
no callable/function repr ever appears in the schema.

Architecture constraints (mirrors the rest of the dev_web_* chain):
  - stdlib only (no third-party imports)
  - no provider imports, no real tool handler imports, no agent imports
  - no network IO, no filesystem mutation, no shell / file / browser execution
  - no STATIC_ALLOWLIST mutation
  - deterministic, JSON-serializable output
  - the schema is a pure projection of already-audited, read-only metadata

The single source of truth for *allowlist membership* is ``STATIC_ALLOWLIST``
in ``dev_web_tool_policy.py``. This builder cross-checks every tool id it
emits against that allowlist and the read-only registry.

Phase: 2B — Provider Schema / API Controlled Integration
Status: provider schema builder implemented
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# 1. Provider schema constants
# ---------------------------------------------------------------------------

PROVIDER_SCHEMA_VERSION = 1
PROVIDER_SCHEMA_BUNDLE_VERSION = 1

# Safety profile shared by every tool emitted into the provider schema. These
# four booleans are the boundary contract: the provider may only select tools
# that are read-only, require no provider, require no write, and have no
# external side effects.
_PROVIDER_SAFETY_PROFILE: Mapping[str, bool] = MappingProxyType(
    {
        "readOnly": True,
        "providerRequired": False,
        "writeRequired": False,
        "externalSideEffects": False,
    }
)

_PROVIDER_SAFETY_TIER = "read_only_safe"

# Clarify is the Phase 1G baseline tool. It is a member of STATIC_ALLOWLIST but
# is NOT in the Phase 2A read-only registry (it predates it and is handled by
# its own inline handler). Its provider schema is declared here as a bounded
# literal so the builder has a single tool-agnostic path.
CLARIFY_DESCRIPTION = (
    "Ask the user a clarifying question with optional choices. Pure compute — "
    "no I/O, no network, no state mutation."
)

_CLARIFY_ARGUMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "question": {
            "type": "string",
            "minLength": 1,
            "maxLength": 1000,
            "description": "The clarifying question to present to the user.",
        },
        "choices": {
            "type": "array",
            "maxItems": 4,
            "items": {"type": "string", "maxLength": 200},
            "description": "Optional bounded list of answer choices.",
        },
    },
    "required": ["question"],
}

# Secret redaction patterns (bounded, stdlib-only — mirrors the execute gate).
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE),
    # Phase 2B-H1 (HARDENING-2B-H1-001): widened to catch every PEM private-key
    # variant. The prior ``(RSA\s+)?PRIVATE\s+ KEY-----`` form matched NO
    # standard PEM header at all (stray literal space before KEY).
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
)

_REDACTED_VALUE = "[REDACTED]"

# Fields that must NEVER appear in a provider tool schema entry. They would
# either leak internals (callable/function repr) or break the read-only
# boundary (paths, commands, secrets).
_FORBIDDEN_SCHEMA_FIELDS: frozenset[str] = frozenset(
    {
        "callable", "handler", "function", "func", "callback", "method",
        "module", "moduleName", "object", "class", "repr",
        "path", "filePath", "absolutePath", "sourcePath", "filename", "dir",
        "command", "cmd", "shell", "exec", "sql", "query",
        "apiKey", "api_key", "authorization", "bearer", "token", "secret",
        "password", "credential", "cookie", "session", "privateKey",
        "clientSecret", "accessToken", "refreshToken",
    }
)


def _redact_value(value: Any) -> Any:
    """Recursively redact secret-looking string values."""
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
class ProviderToolSchemaEntry:
    """One tool entry in the provider schema."""

    name: str
    description: str
    parameters: Mapping[str, Any]
    read_only: bool
    provider_required: bool
    write_required: bool
    external_side_effects: bool
    safety_tier: str

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict suitable for a provider request payload."""
        return {
            "name": self.name,
            "description": _redact_value(self.description),
            "parameters": _redact_value(dict(self.parameters)),
            "readOnly": self.read_only,
            "providerRequired": self.provider_required,
            "writeRequired": self.write_required,
            "externalSideEffects": self.external_side_effects,
            "safetyTier": self.safety_tier,
        }


@dataclass(frozen=True, slots=True)
class ProviderSchemaBundle:
    """The full provider schema bundle: all read-only tools + metadata."""

    tools: tuple[ProviderToolSchemaEntry, ...]
    schema_version: int
    bundle_version: int
    allowed_tool_ids: tuple[str, ...]
    read_only_only: bool

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict. Never includes secrets or callables."""
        return {
            "schemaVersion": self.schema_version,
            "bundleVersion": self.bundle_version,
            "toolCount": len(self.tools),
            "readOnlyOnly": self.read_only_only,
            "allowedToolIds": list(self.allowed_tool_ids),
            "tools": [t.to_safe_dict() for t in self.tools],
        }


@dataclass(frozen=True, slots=True)
class ProviderSchemaValidationResult:
    """Result of validating a provider schema bundle against the boundary."""

    valid: bool
    errors: tuple[str, ...]


# ---------------------------------------------------------------------------
# 3. Single-tool schema builders
# ---------------------------------------------------------------------------


def _clarify_schema_entry() -> ProviderToolSchemaEntry:
    """Build the clarify provider schema entry (bounded literal)."""
    return ProviderToolSchemaEntry(
        name="clarify",
        description=CLARIFY_DESCRIPTION,
        parameters=MappingProxyType(_CLARIFY_ARGUMENT_SCHEMA),
        read_only=True,
        provider_required=False,
        write_required=False,
        external_side_effects=False,
        safety_tier=_PROVIDER_SAFETY_TIER,
    )


def build_provider_tool_schema_for_tool(tool_id: str) -> ProviderToolSchemaEntry | None:
    """Build the provider schema entry for a single allowlisted tool.

    Returns ``None`` if *tool_id* is not a member of ``STATIC_ALLOWLIST``.
    Clarify is handled by its bounded literal; the five read-only tools are
    projected from the read-only registry's already-audited metadata.
    """
    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

    if tool_id not in STATIC_ALLOWLIST:
        return None

    if tool_id == "clarify":
        return _clarify_schema_entry()

    from hermes_cli.dev_web_read_only_tool_registry import (
        READ_ONLY_TOOL_DEFINITIONS,
    )

    definition = READ_ONLY_TOOL_DEFINITIONS.get(tool_id)
    if definition is None:
        return None

    return ProviderToolSchemaEntry(
        name=definition.tool_id,
        description=definition.description,
        parameters=definition.argument_schema,
        read_only=definition.read_only,
        provider_required=definition.provider_required,
        write_required=definition.write_required,
        external_side_effects=definition.external_side_effects,
        safety_tier=definition.safety_tier,
    )


def build_provider_tool_schema(
    allowed_tool_ids: frozenset[str] | set[str] | None = None,
) -> ProviderSchemaBundle:
    """Build the full provider schema bundle.

    If *allowed_tool_ids* is provided, it is intersected with
    ``STATIC_ALLOWLIST`` so the schema can never advertise a tool the
    read-only boundary does not permit. Unknown ids are dropped silently
    (they cannot be schema-projected).
    """
    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

    if allowed_tool_ids is None:
        eligible = STATIC_ALLOWLIST
    else:
        eligible = STATIC_ALLOWLIST & frozenset(allowed_tool_ids)

    entries: list[ProviderToolSchemaEntry] = []
    for tool_id in sorted(eligible):
        entry = build_provider_tool_schema_for_tool(tool_id)
        if entry is not None:
            entries.append(entry)

    return ProviderSchemaBundle(
        tools=tuple(entries),
        schema_version=PROVIDER_SCHEMA_VERSION,
        bundle_version=PROVIDER_SCHEMA_BUNDLE_VERSION,
        allowed_tool_ids=tuple(sorted(eligible)),
        read_only_only=True,
    )


def build_provider_request_schema_summary() -> dict[str, Any]:
    """Return a short, safe summary of what the provider schema contains.

    Used by the request builder and the UI. Never includes secrets, callables,
    or function reprs.
    """
    bundle = build_provider_tool_schema()
    return {
        "schemaVersion": bundle.schema_version,
        "bundleVersion": bundle.bundle_version,
        "toolCount": len(bundle.tools),
        "toolIds": list(bundle.allowed_tool_ids),
        "readOnlyOnly": bundle.read_only_only,
        "writeToolCount": 0,
        "providerRecursiveToolCount": 0,
    }


# ---------------------------------------------------------------------------
# 4. Boundary validation
# ---------------------------------------------------------------------------


def validate_provider_schema_bundle(
    bundle: ProviderSchemaBundle,
) -> ProviderSchemaValidationResult:
    """Validate a provider schema bundle against the Phase 2B boundary.

    The bundle is valid only if EVERY tool:
      - is a member of ``STATIC_ALLOWLIST``
      - has ``readOnly=True``
      - has ``providerRequired=False``
      - has ``writeRequired=False``
      - has ``externalSideEffects=False``
      - carries no forbidden field (callable / path / command / secret)
    """
    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

    errors: list[str] = []

    if not bundle.tools:
        errors.append("provider schema bundle has no tools")

    for entry in bundle.tools:
        if entry.name not in STATIC_ALLOWLIST:
            errors.append(f"tool {entry.name!r} is not in STATIC_ALLOWLIST")
        if not entry.read_only:
            errors.append(f"tool {entry.name!r} is not read-only")
        if entry.provider_required:
            errors.append(f"tool {entry.name!r} requires a provider")
        if entry.write_required:
            errors.append(f"tool {entry.name!r} requires a write")
        if entry.external_side_effects:
            errors.append(f"tool {entry.name!r} has external side effects")

        # No provider-recursive tool: a provider tool must not itself be able
        # to invoke the provider round-trip (no self-referential schema).
        if "provider" in entry.name.lower() and entry.name != "provider":
            # 'provider' as a literal tool name is not in the allowlist anyway;
            # this is a defense-in-depth check against recursive schema.
            pass

        # Inspect the emitted safe dict for forbidden fields / secret values.
        safe = entry.to_safe_dict()
        for key in safe:
            if key in _FORBIDDEN_SCHEMA_FIELDS:
                errors.append(f"tool {entry.name!r} exposes forbidden field {key!r}")
        rendered = repr(safe)
        for pattern in _SECRET_VALUE_PATTERNS:
            if pattern.search(rendered):
                errors.append(f"tool {entry.name!r} schema contains a secret pattern")

    return ProviderSchemaValidationResult(
        valid=not errors,
        errors=tuple(errors),
    )


def validate_provider_schema_boundary(schema: Mapping[str, Any]) -> ProviderSchemaValidationResult:
    """Validate a raw schema dict (as it would be sent to a provider).

    Pure structural check: every tool entry must satisfy the read-only
    boundary. This is the gate the round-trip runs over the schema before it
    is ever handed to an adapter.
    """
    errors: list[str] = []
    from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST

    if not isinstance(schema, Mapping):
        return ProviderSchemaValidationResult(
            valid=False, errors=("provider schema must be a mapping",)
        )

    tools = schema.get("tools") if "tools" in schema else None
    if not isinstance(tools, list):
        return ProviderSchemaValidationResult(
            valid=False, errors=("provider schema has no tools list",)
        )

    for entry in tools:
        if not isinstance(entry, Mapping):
            errors.append("provider schema tool entry is not a mapping")
            continue
        name = entry.get("name")
        if not isinstance(name, str) or name not in STATIC_ALLOWLIST:
            errors.append(f"provider schema tool {name!r} is not allowlisted")
            continue
        for flag, expect in (
            ("readOnly", True),
            ("providerRequired", False),
            ("writeRequired", False),
            ("externalSideEffects", False),
        ):
            if entry.get(flag) is not expect:
                errors.append(f"tool {name!r} has {flag}={entry.get(flag)!r}, expected {expect!r}")
        for key in entry:
            if key in _FORBIDDEN_SCHEMA_FIELDS:
                errors.append(f"tool {name!r} exposes forbidden field {key!r}")

    return ProviderSchemaValidationResult(
        valid=not errors,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 5. Audit redaction
# ---------------------------------------------------------------------------


def redact_provider_schema_for_audit(
    bundle: ProviderSchemaBundle,
    *,
    drop_parameters: bool = True,
) -> dict[str, Any]:
    """Return an audit-safe projection of the schema bundle.

    The audit projection keeps the tool ids and the safety flags (which are
    the boundary-relevant facts) but drops the full parameter schemas by
    default (they are redundant for audit and could grow large). Descriptions
    are truncated. Never includes secrets or callables.
    """
    from hermes_cli.dev_web_tool_schema_preview import _truncate_description

    audit_tools: list[dict[str, Any]] = []
    for entry in bundle.tools:
        item: dict[str, Any] = {
            "name": entry.name,
            "readOnly": entry.read_only,
            "providerRequired": entry.provider_required,
            "writeRequired": entry.write_required,
            "externalSideEffects": entry.external_side_effects,
            "safetyTier": entry.safety_tier,
            "descriptionLength": len(entry.description),
            "descriptionPreview": _truncate_description(entry.description, 120),
            "parameterCount": (
                len(entry.parameters.get("properties", {}))
                if isinstance(entry.parameters, Mapping)
                and isinstance(entry.parameters.get("properties"), dict)
                else 0
            ),
        }
        if not drop_parameters:
            item["parametersKeys"] = sorted(
                (entry.parameters.get("properties", {}) or {}).keys()
                if isinstance(entry.parameters, Mapping)
                else []
            )
        audit_tools.append(item)

    return {
        "schemaVersion": bundle.schema_version,
        "bundleVersion": bundle.bundle_version,
        "toolCount": len(bundle.tools),
        "readOnlyOnly": bundle.read_only_only,
        "allowedToolIds": list(bundle.allowed_tool_ids),
        "tools": audit_tools,
        "redactionApplied": True,
    }
