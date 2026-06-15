"""Phase 2C Write Tool Registry for the Hermes Dev WebUI.

This module is the single metadata source for the four Phase 2C controlled
write tools that may operate inside the **dev sandbox** (a directory under the
dev ``HERMES_HOME``). It mirrors the bounded-reimplementation pattern used by
the Phase 2A read-only registry (``dev_web_read_only_tool_registry.py``), but
inverts the safety profile: every write tool is ``readOnly=False``,
``writeRequired=True``, ``localSideEffects=True``, requires explicit write
enablement, requires confirmation, and requires a rollback plan.

Architecture constraints:
  - stdlib only (no third-party imports)
  - no provider imports, no agent imports, no tool-dispatch imports
  - no network IO, no filesystem mutation (this registry is pure metadata)
  - no STATIC_ALLOWLIST mutation — the Phase 2A read-only allowlist in
    ``dev_web_tool_policy.py`` stays frozen at exactly six read-only tools.
    Write tools live in a SEPARATE allowlist (``STATIC_WRITE_ALLOWLIST``).
  - argument validation is strict: only the documented keys are accepted,
    secret / shell / command stems are rejected, but a *sandbox-relative*
    ``targetPath`` and UTF-8 ``content`` are legitimate write inputs.
  - deterministic, JSON-serializable metadata

The write tools are Dev-WebUI-local bounded handlers (NOT registered Hermes
agent tools, NOT in the production tool dispatch path). They only ever write
inside the dev sandbox root (see ``dev_web_write_sandbox.py``).

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
Status: write registry implemented
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# 1. Allowlists
# ---------------------------------------------------------------------------
#
# The Phase 2A read-only allowlist is the SINGLE source of truth for read-only
# membership and is re-exported here for a unified view. It is NOT modified by
# this module. Write tools have their own separate allowlist.

from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST as STATIC_READ_ONLY_ALLOWLIST  # noqa: E402,F401


# The four Phase 2C controlled write tools. Each writes ONLY inside the dev
# sandbox root under the dev HERMES_HOME.
STATIC_WRITE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "dev_sandbox_file_write",
        "dev_sandbox_file_append",
        "dev_sandbox_file_patch",
        "dev_sandbox_file_readback",
    }
)

PHASE_2C_WRITE_TOOL_IDS: frozenset[str] = frozenset(STATIC_WRITE_ALLOWLIST)

# Phase 2C-H1: the rollback execution tool lives in its OWN allowlist, separate
# from the four file-write tools (clean token-scope separation; the file-write
# registry assertions stay frozen at four). Rollback execution loads a stored
# manifest rather than taking file-write arguments, so it has its own flow.
STATIC_ROLLBACK_TOOL_IDS: frozenset[str] = frozenset({"dev_sandbox_rollback_execute"})
PHASE_2C_H1_ROLLBACK_TOOL_IDS: frozenset[str] = frozenset(STATIC_ROLLBACK_TOOL_IDS)


def is_phase_2c_h1_rollback_tool(tool_id: str) -> bool:
    """Return ``True`` if *tool_id* is the Phase 2C-H1 rollback execution tool."""
    return tool_id in PHASE_2C_H1_ROLLBACK_TOOL_IDS


# Derived unified executable view (read-only ∪ file-write ∪ rollback). This is
# a NEW name and does NOT overwrite the frozen STATIC_ALLOWLIST.
UNIFIED_EXECUTABLE_ALLOWLIST: frozenset[str] = frozenset(
    STATIC_READ_ONLY_ALLOWLIST | STATIC_WRITE_ALLOWLIST | STATIC_ROLLBACK_TOOL_IDS
)


# ---------------------------------------------------------------------------
# 2. Write tool definition record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WriteToolDefinition:
    """Immutable metadata record for one Phase 2C write tool.

    All Phase 2C write tools share the same invariant safety profile:

      - ``read_only`` is False
      - ``write_required`` is True
      - ``external_side_effects`` is False
      - ``provider_required`` is False
      - ``local_side_effects`` is True
      - ``requires_confirmation`` is True
      - ``requires_write_enablement`` is True
      - ``requires_rollback_plan`` is True
      - ``side_effect_scope`` is the dev sandbox filesystem
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
    local_side_effects: bool
    side_effect_scope: str
    requires_confirmation: bool
    requires_write_enablement: bool
    requires_rollback_plan: bool
    argument_schema: Mapping[str, Any]
    result_schema: Mapping[str, Any]
    audit_redaction_policy: str
    enabled_in_phase: str


# ---------------------------------------------------------------------------
# 3. Argument validation primitives (write-specific)
# ---------------------------------------------------------------------------
#
# Unlike the read-only registry, write tools legitimately accept a
# sandbox-relative ``targetPath`` and UTF-8 ``content``. We still reject every
# secret / shell / command / database stem and reject path values that look
# absolute, traversal-bearing, or shell-like.

_MAX_TARGET_PATH_LENGTH = 256
# Generous structural cap. The authoritative single-write limit (64 KiB) is
# enforced by the sandbox so the plan can report the precise
# blocked_write_content_too_large reason.
_MAX_CONTENT_BYTES = 256 * 1024  # 256 KiB structural ceiling
_MAX_PATCH_FRAGMENT_LENGTH = 32 * 1024  # 32 KiB for search / replace fragments
_MAX_MODE_LENGTH = 32

# Argument keys that are NEVER accepted by any write tool.
_FORBIDDEN_WRITE_ARG_STEMS: frozenset[str] = frozenset(
    {
        "apikey", "api_key", "authorization", "auth", "bearer", "token",
        "secret", "password", "passwd", "credential", "cookie", "session",
        "privatekey", "private_key", "clientsecret", "client_secret",
        "accesstoken", "access_token", "refresh_token", "access_key",
        "command", "cmd", "shell", "exec", "script", "sql", "query",
        "database", "dbpath", "url", "endpoint", "host", "port",
    }
)


def _is_forbidden_write_key(key: str) -> bool:
    """Return True if *key* matches a forbidden write-argument stem."""
    if not isinstance(key, str):
        return True
    normalized = key.strip().lower().replace("-", "").replace("_", "")
    if normalized in _FORBIDDEN_WRITE_ARG_STEMS:
        return True
    return any(
        stem in normalized
        for stem in (
            "token", "secret", "password", "apikey", "privatekey", "credential",
            "authorization",
        )
    )


# Accepted write-argument keys (the legitimate inputs). These are NOT in the
# forbidden stem set.
_ACCEPTED_WRITE_ARG_KEYS: frozenset[str] = frozenset(
    {"targetpath", "content", "mode", "search", "replace"}
)


def _path_value_is_safe_relative(value: str) -> bool:
    """Return True if *value* is a non-empty, sandbox-relative path string.

    Rejects: absolute paths, home references, traversal, backslashes,
    shell metacharacters, file:// schemes, NUL bytes, control chars.
    """
    if not isinstance(value, str) or not value:
        return False
    if value.startswith(("/", "~", "\\")):
        return False
    if "\x00" in value:
        return False
    # Disallow any backslash segment separator escape.
    if "\\" in value:
        return False
    # Disallow traversal segments anywhere.
    parts = value.replace("\\", "/").split("/")
    for part in parts:
        if part == "..":
            return False
    if value.startswith("file://"):
        return False
    # Reject embedded shell metacharacters in the path.
    if any(ch in value for ch in ("|", ";", "`", "$", ">", "<", "&", "\n", "\r")):
        return False
    # Reject leading whitespace.
    if value != value.strip():
        return False
    return True


def _string_value_is_safe_text(value: str) -> bool:
    """Return True if *value* is acceptable UTF-8 text content (no NUL)."""
    if not isinstance(value, str):
        return False
    if "\x00" in value:
        return False
    return True


def _is_binary_text(value: str) -> bool:
    """Detect likely-binary content: NUL byte or any C0 control char (other
    than ``\\n`` / ``\\r`` / ``\\t``) in the first 1024 characters."""
    if not value:
        return False
    if "\x00" in value:
        return True
    sample = value[:1024]
    return any(ord(ch) < 32 and ch not in "\n\r\t" for ch in sample)


_ARG_ERROR_UNKNOWN_TOOL = "WRITE_ARG_UNKNOWN_TOOL"
_ARG_ERROR_NON_DICT = "WRITE_ARG_NON_DICT"
_ARG_ERROR_UNKNOWN_KEY = "WRITE_ARG_UNKNOWN_KEY"
_ARG_ERROR_FORBIDDEN_KEY = "WRITE_ARG_FORBIDDEN_KEY"
_ARG_ERROR_INVALID_VALUE = "WRITE_ARG_INVALID_VALUE"
_ARG_ERROR_MISSING_REQUIRED = "WRITE_ARG_MISSING_REQUIRED"
_ARG_ERROR_BINARY_CONTENT = "WRITE_ARG_BINARY_CONTENT"


def _json_schema(properties: dict[str, Any], required: tuple[str, ...] = ()) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
    }
    if required:
        schema["required"] = list(required)
    return schema


# ---------------------------------------------------------------------------
# 4. Per-tool argument specifications + JSON schemas
# ---------------------------------------------------------------------------

_TARGET_PATH_SCHEMA = {
    "type": "string",
    "maxLength": _MAX_TARGET_PATH_LENGTH,
    "description": "Sandbox-relative target path (no absolute paths, no .. traversal).",
}
_CONTENT_SCHEMA = {
    "type": "string",
    "maxLength": _MAX_CONTENT_BYTES,
    "description": "UTF-8 text content to write/append.",
}
_SEARCH_SCHEMA = {
    "type": "string",
    "maxLength": _MAX_PATCH_FRAGMENT_LENGTH,
    "description": "Exact substring to find for a controlled patch.",
}
_REPLACE_SCHEMA = {
    "type": "string",
    "maxLength": _MAX_PATCH_FRAGMENT_LENGTH,
    "description": "Replacement substring for a controlled patch.",
}
_MODE_SCHEMA = {
    "type": "string",
    "enum": ["create_or_replace"],
    "default": "create_or_replace",
    "description": "Write mode. Phase 2C supports create_or_replace only.",
}


_DEV_SANDBOX_FILE_WRITE_ARGUMENTS = _json_schema(
    {
        "targetPath": _TARGET_PATH_SCHEMA,
        "content": _CONTENT_SCHEMA,
        "mode": _MODE_SCHEMA,
    },
    required=("targetPath", "content"),
)

_DEV_SANDBOX_FILE_APPEND_ARGUMENTS = _json_schema(
    {
        "targetPath": _TARGET_PATH_SCHEMA,
        "content": _CONTENT_SCHEMA,
    },
    required=("targetPath", "content"),
)

_DEV_SANDBOX_FILE_PATCH_ARGUMENTS = _json_schema(
    {
        "targetPath": _TARGET_PATH_SCHEMA,
        "search": _SEARCH_SCHEMA,
        "replace": _REPLACE_SCHEMA,
    },
    required=("targetPath", "search", "replace"),
)

_DEV_SANDBOX_FILE_READBACK_ARGUMENTS = _json_schema(
    {
        "targetPath": _TARGET_PATH_SCHEMA,
    },
    required=("targetPath",),
)


# Per-tool accepted-argument specs. Each entry: key, required, kind.
_TOOL_ARGUMENT_SPECS: Mapping[str, tuple[dict[str, Any], ...]] = MappingProxyType(
    {
        "dev_sandbox_file_write": (
            {"key": "targetPath", "required": True, "kind": "target_path"},
            {"key": "content", "required": True, "kind": "content"},
            {"key": "mode", "required": False, "kind": "mode"},
        ),
        "dev_sandbox_file_append": (
            {"key": "targetPath", "required": True, "kind": "target_path"},
            {"key": "content", "required": True, "kind": "content"},
        ),
        "dev_sandbox_file_patch": (
            {"key": "targetPath", "required": True, "kind": "target_path"},
            {"key": "search", "required": True, "kind": "patch_fragment"},
            {"key": "replace", "required": True, "kind": "patch_fragment"},
        ),
        "dev_sandbox_file_readback": (
            {"key": "targetPath", "required": True, "kind": "target_path"},
        ),
    }
)


# ---------------------------------------------------------------------------
# 5. Write tool definitions
# ---------------------------------------------------------------------------

_WRITE_SAFETY_TIER = "dev_sandbox_write"
_SIDE_EFFECT_SCOPE = "dev_sandbox_filesystem"
_AUDIT_REDACTION = (
    "stores a redacted argument summary (targetPath + contentDigest + lengths) "
    "only; never raw token, full tokenHash, raw arguments, full file content, "
    "secrets, or callable/function repr"
)


_WRITE_TOOL_DEFINITIONS_RAW: dict[str, WriteToolDefinition] = {
    "dev_sandbox_file_write": WriteToolDefinition(
        tool_id="dev_sandbox_file_write",
        display_name="Dev Sandbox File Write",
        description=(
            "Create or replace a UTF-8 text file inside the dev sandbox root "
            "under the dev HERMES_HOME. Requires write enablement, dry-run "
            "preview, confirmation, digest verification, and a rollback plan. "
            "Never writes outside the sandbox, never touches ~/.hermes or "
            "production state.db."
        ),
        category="write",
        safety_tier=_WRITE_SAFETY_TIER,
        read_only=False,
        external_side_effects=False,
        provider_required=False,
        write_required=True,
        local_side_effects=True,
        side_effect_scope=_SIDE_EFFECT_SCOPE,
        requires_confirmation=True,
        requires_write_enablement=True,
        requires_rollback_plan=True,
        argument_schema=_DEV_SANDBOX_FILE_WRITE_ARGUMENTS,
        result_schema=_json_schema(
            {
                "operation": {"type": "string"},
                "targetRelativePath": {"type": "string"},
                "beforeExists": {"type": "boolean"},
                "beforeHash": {"type": ["string", "null"]},
                "afterHash": {"type": "string"},
                "bytesWritten": {"type": "integer"},
                "rollbackAvailable": {"type": "boolean"},
            }
        ),
        audit_redaction_policy=_AUDIT_REDACTION,
        enabled_in_phase="2C",
    ),
    "dev_sandbox_file_append": WriteToolDefinition(
        tool_id="dev_sandbox_file_append",
        display_name="Dev Sandbox File Append",
        description=(
            "Append UTF-8 text to a file inside the dev sandbox root (creating "
            "it if absent). Same safety constraints as the write tool."
        ),
        category="write",
        safety_tier=_WRITE_SAFETY_TIER,
        read_only=False,
        external_side_effects=False,
        provider_required=False,
        write_required=True,
        local_side_effects=True,
        side_effect_scope=_SIDE_EFFECT_SCOPE,
        requires_confirmation=True,
        requires_write_enablement=True,
        requires_rollback_plan=True,
        argument_schema=_DEV_SANDBOX_FILE_APPEND_ARGUMENTS,
        result_schema=_json_schema(
            {
                "operation": {"type": "string"},
                "targetRelativePath": {"type": "string"},
                "beforeExists": {"type": "boolean"},
                "beforeHash": {"type": ["string", "null"]},
                "afterHash": {"type": "string"},
                "bytesWritten": {"type": "integer"},
                "rollbackAvailable": {"type": "boolean"},
            }
        ),
        audit_redaction_policy=_AUDIT_REDACTION,
        enabled_in_phase="2C",
    ),
    "dev_sandbox_file_patch": WriteToolDefinition(
        tool_id="dev_sandbox_file_patch",
        display_name="Dev Sandbox File Patch",
        description=(
            "Apply a controlled find-and-replace patch to an existing UTF-8 "
            "text file inside the dev sandbox root. The search fragment must "
            "match exactly once. Same safety constraints as the write tool."
        ),
        category="write",
        safety_tier=_WRITE_SAFETY_TIER,
        read_only=False,
        external_side_effects=False,
        provider_required=False,
        write_required=True,
        local_side_effects=True,
        side_effect_scope=_SIDE_EFFECT_SCOPE,
        requires_confirmation=True,
        requires_write_enablement=True,
        requires_rollback_plan=True,
        argument_schema=_DEV_SANDBOX_FILE_PATCH_ARGUMENTS,
        result_schema=_json_schema(
            {
                "operation": {"type": "string"},
                "targetRelativePath": {"type": "string"},
                "beforeExists": {"type": "boolean"},
                "beforeHash": {"type": ["string", "null"]},
                "afterHash": {"type": "string"},
                "linesChanged": {"type": "integer"},
                "rollbackAvailable": {"type": "boolean"},
            }
        ),
        audit_redaction_policy=_AUDIT_REDACTION,
        enabled_in_phase="2C",
    ),
    "dev_sandbox_file_readback": WriteToolDefinition(
        tool_id="dev_sandbox_file_readback",
        display_name="Dev Sandbox File Readback",
        description=(
            "Read back a content summary and a bounded snippet of a file inside "
            "the dev sandbox root, to verify a prior write. Belongs to the write "
            "workflow but performs a read-only inspection of sandbox state."
        ),
        category="write",
        safety_tier=_WRITE_SAFETY_TIER,
        read_only=False,
        external_side_effects=False,
        provider_required=False,
        write_required=True,
        local_side_effects=True,
        side_effect_scope=_SIDE_EFFECT_SCOPE,
        requires_confirmation=True,
        requires_write_enablement=True,
        requires_rollback_plan=True,
        argument_schema=_DEV_SANDBOX_FILE_READBACK_ARGUMENTS,
        result_schema=_json_schema(
            {
                "operation": {"type": "string"},
                "targetRelativePath": {"type": "string"},
                "exists": {"type": "boolean"},
                "contentHash": {"type": ["string", "null"]},
                "sizeBytes": {"type": "integer"},
                "snippet": {"type": "string"},
            }
        ),
        audit_redaction_policy=_AUDIT_REDACTION,
        enabled_in_phase="2C",
    ),
}

WRITE_TOOL_DEFINITIONS: Mapping[str, WriteToolDefinition] = MappingProxyType(
    _WRITE_TOOL_DEFINITIONS_RAW
)


# ---------------------------------------------------------------------------
# 6. Consistency guard — runs at import time
# ---------------------------------------------------------------------------


def _verify_write_registry_consistency() -> None:
    """Cross-check the write registry invariants at import time.

    Write tools MUST NOT collide with the read-only allowlist, must carry the
    write safety profile, and must not overlap any production tool name.
    """
    from hermes_cli.dev_web_tool_policy import STATIC_DENYLIST, TOOL_POLICY_INVENTORY

    errors: list[str] = []

    if len(PHASE_2C_WRITE_TOOL_IDS) != 4:
        errors.append(
            f"Expected exactly 4 Phase 2C write tools, got "
            f"{len(PHASE_2C_WRITE_TOOL_IDS)}"
        )

    # Write tools must not be in the read-only allowlist (separate registries).
    overlap_read_only = STATIC_WRITE_ALLOWLIST & STATIC_READ_ONLY_ALLOWLIST
    if overlap_read_only:
        errors.append(
            f"Write tools must not be in the read-only allowlist: "
            f"{sorted(overlap_read_only)}"
        )

    # Write tools must not collide with any production inventory name.
    collide_production = STATIC_WRITE_ALLOWLIST & set(TOOL_POLICY_INVENTORY.keys())
    if collide_production:
        errors.append(
            f"Write tool ids must not collide with production tools: "
            f"{sorted(collide_production)}"
        )

    # Write tools must not be on the denylist.
    on_deny = STATIC_WRITE_ALLOWLIST & STATIC_DENYLIST
    if on_deny:
        errors.append(f"Write tools must not be on the denylist: {sorted(on_deny)}")

    # Phase 2C-H1: rollback tool must be disjoint from read-only + file-write +
    # production inventory + denylist.
    if len(PHASE_2C_H1_ROLLBACK_TOOL_IDS) != 1:
        errors.append(
            f"Expected exactly 1 Phase 2C-H1 rollback tool, got "
            f"{len(PHASE_2C_H1_ROLLBACK_TOOL_IDS)}"
        )
    rb_overlap = STATIC_ROLLBACK_TOOL_IDS & (STATIC_READ_ONLY_ALLOWLIST | STATIC_WRITE_ALLOWLIST)
    if rb_overlap:
        errors.append(f"Rollback tool must be disjoint: {sorted(rb_overlap)}")
    rb_collide = STATIC_ROLLBACK_TOOL_IDS & set(TOOL_POLICY_INVENTORY.keys())
    if rb_collide:
        errors.append(f"Rollback tool collides with production: {sorted(rb_collide)}")
    rb_deny = STATIC_ROLLBACK_TOOL_IDS & STATIC_DENYLIST
    if rb_deny:
        errors.append(f"Rollback tool must not be on denylist: {sorted(rb_deny)}")

    for definition in WRITE_TOOL_DEFINITIONS.values():
        tid = definition.tool_id
        if definition.read_only:
            errors.append(f"Write tool {tid} must be readOnly=False")
        if not definition.write_required:
            errors.append(f"Write tool {tid} must be writeRequired=True")
        if definition.external_side_effects:
            errors.append(f"Write tool {tid} must have externalSideEffects=False")
        if not definition.local_side_effects:
            errors.append(f"Write tool {tid} must have localSideEffects=True")
        if definition.provider_required:
            errors.append(f"Write tool {tid} must have providerRequired=False")
        if not definition.requires_confirmation:
            errors.append(f"Write tool {tid} must require confirmation")
        if not definition.requires_write_enablement:
            errors.append(f"Write tool {tid} must require write enablement")
        if not definition.requires_rollback_plan:
            errors.append(f"Write tool {tid} must require a rollback plan")
        if definition.safety_tier != _WRITE_SAFETY_TIER:
            errors.append(f"Write tool {tid} has wrong safety tier")
        if definition.category != "write":
            errors.append(f"Write tool {tid} has wrong category")
        if definition.enabled_in_phase != "2C":
            errors.append(f"Write tool {tid} has wrong phase")
        if tid not in _TOOL_ARGUMENT_SPECS:
            errors.append(f"Write tool {tid} has no argument spec")

    if errors:
        raise RuntimeError(
            "Phase 2C write registry consistency check failed:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


_verify_write_registry_consistency()


# ---------------------------------------------------------------------------
# 7. Public query / validation functions
# ---------------------------------------------------------------------------


def get_write_tool_definition(tool_id: str) -> WriteToolDefinition | None:
    """Return the write tool definition for *tool_id*, or ``None``."""
    return WRITE_TOOL_DEFINITIONS.get(tool_id)


def list_write_tool_definitions() -> tuple[WriteToolDefinition, ...]:
    """Return all Phase 2C write tool definitions, sorted by tool id."""
    return tuple(sorted(WRITE_TOOL_DEFINITIONS.values(), key=lambda d: d.tool_id))


def is_phase_2c_write_tool(tool_id: str) -> bool:
    """Return ``True`` if *tool_id* is a Phase 2C write tool."""
    return tool_id in PHASE_2C_WRITE_TOOL_IDS


def validate_write_tool_definition(tool: WriteToolDefinition) -> tuple[bool, tuple[str, ...]]:
    """Validate a single write tool definition record.

    Returns ``(valid, errors)``. Used by import-time consistency and by tests.
    """
    errors: list[str] = []
    if tool.read_only:
        errors.append("write tool cannot be readOnly=True")
    if not tool.write_required:
        errors.append("write tool must be writeRequired=True")
    if tool.external_side_effects:
        errors.append("write tool must have externalSideEffects=False")
    if not tool.local_side_effects:
        errors.append("write tool must have localSideEffects=True")
    if tool.provider_required:
        errors.append("write tool must have providerRequired=False")
    if not tool.requires_confirmation:
        errors.append("write tool must require confirmation")
    if not tool.requires_write_enablement:
        errors.append("write tool must require write enablement")
    if not tool.requires_rollback_plan:
        errors.append("write tool must require a rollback plan")
    # Reject any shell / database / external-service operation in the schema.
    schema_blob = repr(tool.argument_schema).lower()
    for banned in ("subprocess", "os.system", "sqlite", "delete from", "requests.post", "httpx", "urllib"):
        if banned in schema_blob:
            errors.append(f"write tool schema references banned operation: {banned}")
    return (len(errors) == 0, tuple(errors))


def _coerce_write_value(spec: dict[str, Any], value: Any) -> tuple[Any, str | None]:
    """Coerce one write-argument value per *spec*. Returns (value, error_code).

    For ``target_path`` the registry performs STRUCTURAL validation only (str,
    length bound, no NUL). Path-safety classification (traversal / absolute /
    symlink escape / forbidden target / file type) is delegated to
    :mod:`dev_web_write_sandbox`, which produces precise blocked reasons.
    """
    kind = spec["kind"]
    if kind == "target_path":
        if not isinstance(value, str) or not value.strip():
            return None, _ARG_ERROR_INVALID_VALUE
        if len(value) > _MAX_TARGET_PATH_LENGTH:
            return None, _ARG_ERROR_INVALID_VALUE
        if "\x00" in value:
            return None, _ARG_ERROR_INVALID_VALUE
        return value, None
    if kind == "content":
        if not isinstance(value, str):
            return None, _ARG_ERROR_INVALID_VALUE
        if len(value.encode("utf-8")) > _MAX_CONTENT_BYTES:
            return None, _ARG_ERROR_INVALID_VALUE
        if not _string_value_is_safe_text(value):
            return None, _ARG_ERROR_INVALID_VALUE
        if _is_binary_text(value):
            return None, _ARG_ERROR_BINARY_CONTENT
        return value, None
    if kind == "patch_fragment":
        if not isinstance(value, str):
            return None, _ARG_ERROR_INVALID_VALUE
        if len(value.encode("utf-8")) > _MAX_PATCH_FRAGMENT_LENGTH:
            return None, _ARG_ERROR_INVALID_VALUE
        if not _string_value_is_safe_text(value):
            return None, _ARG_ERROR_INVALID_VALUE
        return value, None
    if kind == "mode":
        if not isinstance(value, str):
            return None, _ARG_ERROR_INVALID_VALUE
        if len(value) > _MAX_MODE_LENGTH:
            return None, _ARG_ERROR_INVALID_VALUE
        if value not in ("create_or_replace",):
            return None, _ARG_ERROR_INVALID_VALUE
        return value, None
    return None, _ARG_ERROR_INVALID_VALUE


def validate_write_tool_arguments(
    tool_id: str,
    arguments: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], str | None]:
    """Validate and normalize *arguments* for write *tool_id*.

    Returns ``(normalized_arguments, error_code)``. ``error_code`` is ``None``
    on success. Strict whitelist: any unknown/forbidden key or unsafe value is
    rejected. Required keys must be present.
    """
    if tool_id not in PHASE_2C_WRITE_TOOL_IDS:
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
        if _is_forbidden_write_key(raw_key):
            return {}, _ARG_ERROR_FORBIDDEN_KEY
        if raw_key not in accepted_keys:
            return {}, _ARG_ERROR_UNKNOWN_KEY
        spec = next(s for s in specs if s["key"] == raw_key)
        coerced, err = _coerce_write_value(spec, raw_value)
        if err is not None:
            return {}, err
        normalized[raw_key] = coerced

    # Apply required-key presence checks.
    for spec in specs:
        key = spec["key"]
        if spec.get("required") and key not in normalized:
            return {}, _ARG_ERROR_MISSING_REQUIRED

    # Apply defaults for optional keys.
    for spec in specs:
        key = spec["key"]
        if key not in normalized and spec["kind"] == "mode":
            normalized[key] = "create_or_replace"

    return normalized, None


def normalize_write_tool_arguments(
    tool_id: str,
    arguments: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return the normalized argument dict for write *tool_id*.

    Always returns a dict. Invalid / unsafe input returns an empty dict (the
    caller / plan builder treats an empty dict as a validation failure and
    blocks the write).
    """
    normalized, err = validate_write_tool_arguments(tool_id, arguments)
    if err is not None:
        return {}
    return normalized
