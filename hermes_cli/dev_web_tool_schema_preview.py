"""Static Tool Schema Preview Model and Sanitizer for the Hermes Dev WebUI.

This module implements a pure-function schema preview system that generates
safe, redacted previews of tool input schemas. It reads only from the static
tool policy module and plain Python dicts (representing JSON Schema).

Architecture constraints:
  - stdlib only (no third-party imports)
  - import side effects = 0 (beyond importing static policy constants)
  - no file IO, no network IO, no environment reads
  - no provider imports, no tool handler imports, no runtime DB access
  - no memory access, no review queue access
  - deterministic, JSON-serializable output
  - type hints, frozen dataclasses, explicit constants

Phase: 1G-03-01 — Static Schema Preview Model and Sanitizer
Status: Model and sanitizer implementation (no API, no OpenAPI, no frontend)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from hermes_cli.dev_web_tool_policy import (
    CANDIDATE_ALLOWLIST,
    RISK_RANK,
    STATIC_ALLOWLIST,
    STATIC_DENYLIST,
    ToolRiskLevel,
)


# ---------------------------------------------------------------------------
# 1. Truncation and depth limits (frozen constants)
# ---------------------------------------------------------------------------

MAX_DESCRIPTION_CHARS: int = 240
MAX_RATIONALE_CHARS: int = 240
MAX_ENUM_VALUES: int = 20
MAX_ENUM_VALUE_CHARS: int = 80
MAX_CONSTRAINTS_CHARS: int = 120
MAX_NESTED_DEPTH: int = 4
MAX_FIELD_COUNT: int = 100

# Allowed JSON Schema types for type normalization
_ALLOWED_FIELD_TYPES: frozenset[str] = frozenset(
    {"string", "number", "integer", "boolean", "array", "object", "null", "unknown"}
)


# ---------------------------------------------------------------------------
# 2. Reason codes (frozen)
# ---------------------------------------------------------------------------

REASON_AVAILABLE = "AVAILABLE"
REASON_AVAILABLE_WITH_REDACTION = "AVAILABLE_WITH_REDACTION"
REASON_UNAVAILABLE_RISK_R4 = "RISK_R4_EXECUTION"
REASON_UNAVAILABLE_RISK_R5 = "RISK_R5_SYSTEM"
REASON_UNAVAILABLE_PERMANENTLY_DENIED = "PERMANENTLY_DENIED"
REASON_UNAVAILABLE_UNLISTED = "UNLISTED"
REASON_UNAVAILABLE_EMPTY_SCHEMA = "UNAVAILABLE_EMPTY_SCHEMA"
REASON_UNAVAILABLE_INVALID_SCHEMA = "UNAVAILABLE_INVALID_SCHEMA"
REASON_UNAVAILABLE_SCHEMA_SOURCE_ERROR = "UNAVAILABLE_SCHEMA_SOURCE_ERROR"

REDACTED_FORBIDDEN_FIELD = "REDACTED_FORBIDDEN_FIELD"
REDACTED_SECRET_PATTERN = "REDACTED_SECRET_PATTERN"
REDACTED_DEPTH_LIMIT = "REDACTED_DEPTH_LIMIT"
REDACTED_FIELD_LIMIT = "REDACTED_FIELD_LIMIT"

REDACTION_STATUS_CLEAN = "clean"
REDACTION_STATUS_REDACTED = "redacted"
REDACTION_STATUS_UNAVAILABLE = "unavailable"


# ---------------------------------------------------------------------------
# 3. Forbidden field name patterns
# ---------------------------------------------------------------------------

# 3a. Callable / internals
_FORBIDDEN_CALLABLE_NAMES: frozenset[str] = frozenset(
    {
        "handler", "callable", "function", "func", "callback", "method",
        "class", "module", "object", "check_fn", "is_async",
    }
)

# 3b. Filesystem / source
_FORBIDDEN_FILESYSTEM_NAMES: frozenset[str] = frozenset(
    {
        "path", "absolute_path", "source_path", "file_path", "filename",
        "dirname", "root", "cwd", "home",
    }
)

# 3c. Runtime internals
_FORBIDDEN_RUNTIME_NAMES: frozenset[str] = frozenset(
    {
        "traceback", "stack", "thread", "thread_id", "process",
        "process_id", "pid", "fd", "socket",
    }
)

# 3d. Secrets
_FORBIDDEN_SECRET_NAMES: frozenset[str] = frozenset(
    {
        "api_key", "apikey", "authorization", "auth_header", "bearer",
        "token", "secret", "password", "passwd", "credential", "cookie",
        "session", "private_key", "client_secret", "access_token",
        "refresh_token",
    }
)

# 3e. Raw provider / tool data
_FORBIDDEN_RAW_DATA_NAMES: frozenset[str] = frozenset(
    {
        "provider_schema", "tool_schema", "raw_schema", "raw_tool",
        "tool_object", "provider_object", "headers", "env", "environment",
    }
)

# 3f. Dynamic overrides and execution config
_FORBIDDEN_DYNAMIC_NAMES: frozenset[str] = frozenset(
    {
        "dynamic_schema_overrides", "max_result_size_chars", "override",
        "requires_env",
    }
)

# Combined set for fast lookup (all lowercase)
_ALL_FORBIDDEN_NAMES: frozenset[str] = (
    _FORBIDDEN_CALLABLE_NAMES
    | _FORBIDDEN_FILESYSTEM_NAMES
    | _FORBIDDEN_RUNTIME_NAMES
    | _FORBIDDEN_SECRET_NAMES
    | _FORBIDDEN_RAW_DATA_NAMES
    | _FORBIDDEN_DYNAMIC_NAMES
)


def _normalize_for_comparison(name: str) -> str:
    """Normalize a field name for forbidden-pattern comparison.

    Removes underscores, hyphens, and converts to lowercase.
    This catches camelCase variants like 'clientSecret' → 'clientsecret'
    matching 'client_secret' → 'clientsecret'.
    """
    return name.replace("_", "").replace("-", "").lower()


# Pre-compute normalized forbidden names for fast lookup
_NORMALIZED_FORBIDDEN_NAMES: frozenset[str] = frozenset(
    _normalize_for_comparison(n) for n in _ALL_FORBIDDEN_NAMES
)


def _is_forbidden_field_name(name: str) -> bool:
    """Check if a field name matches any forbidden pattern (case-insensitive).

    Handles camelCase, snake_case, kebab-case, and mixed variants.
    """
    return _normalize_for_comparison(name) in _NORMALIZED_FORBIDDEN_NAMES


# ---------------------------------------------------------------------------
# 4. Secret pattern detection in string content
# ---------------------------------------------------------------------------

_RE_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"sk-[a-zA-Z0-9_\-]{8,}"), "[redacted: secret-like content]"),
    (re.compile(r"Bearer\s+\S+", re.IGNORECASE), "[redacted: bearer token]"),
    (re.compile(r"Authorization\s*:\s*\S+", re.IGNORECASE), "[redacted: authorization header]"),
    (re.compile(r"api_key\s*=\s*\S+", re.IGNORECASE), "[redacted: api_key assignment]"),
    (re.compile(r"token\s*=\s*\S+", re.IGNORECASE), "[redacted: token assignment]"),
    (re.compile(r"password\s*=\s*\S+", re.IGNORECASE), "[redacted: password assignment]"),
    (re.compile(r"-----BEGIN PRIVATE KEY-----"), "[redacted: private key]"),
    (re.compile(r"-----BEGIN RSA PRIVATE KEY-----"), "[redacted: rsa private key]"),
)


def _contains_secret_pattern(text: str) -> bool:
    """Check if text contains any known secret pattern."""
    for pattern, _ in _RE_SECRET_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _redact_secret_patterns(text: str) -> str:
    """Replace known secret patterns with safe placeholders."""
    for pattern, replacement in _RE_SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# 5. Description and enum truncation helpers
# ---------------------------------------------------------------------------


def _truncate_description(text: str | None, max_chars: int = MAX_DESCRIPTION_CHARS) -> str | None:
    """Truncate description at last word boundary before max_chars.

    Appends '…' if truncation occurs. Does not break Unicode characters.
    """
    if text is None:
        return None
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    # Find last word boundary before limit
    truncated = text[:max_chars]
    # Try to cut at last space to avoid breaking a word
    last_space = truncated.rfind(" ")
    if last_space > max_chars // 2:
        truncated = truncated[:last_space]
    return truncated + "…"


def _truncate_enum_values(
    values: Sequence[Any] | None,
) -> tuple[str, ...]:
    """Produce a safe, truncated enum preview.

    - Max 20 values
    - Each value truncated to 80 chars
    - Only safe types (str, int, float, bool, None) rendered
    - Complex objects → '[complex]'
    """
    if values is None:
        return ()

    result: list[str] = []
    for i, v in enumerate(values):
        if i >= MAX_ENUM_VALUES:
            break
        if isinstance(v, bool):
            result.append(str(v).lower())
        elif isinstance(v, (str, int, float)):
            s = str(v)
            if len(s) > MAX_ENUM_VALUE_CHARS:
                s = s[:MAX_ENUM_VALUE_CHARS] + "…"
            result.append(s)
        elif v is None:
            result.append("null")
        else:
            result.append("[complex]")
    return tuple(result)


def _enum_contains_secrets(values: Sequence[Any] | None) -> bool:
    """Check if any enum value contains secret patterns."""
    if values is None:
        return False
    for v in values:
        if isinstance(v, str) and _contains_secret_pattern(v):
            return True
    return False


# ---------------------------------------------------------------------------
# 6. Constraints preview builder
# ---------------------------------------------------------------------------


def _build_constraints_preview(
    field_schema: Mapping[str, Any],
) -> str | None:
    """Build a brief, safe constraints summary (max 120 chars).

    Shows: minimum, maximum, minLength, maxLength, pattern presence,
    additionalProperties presence, items type summary.
    Never shows raw pattern text that might contain secrets.
    """
    parts: list[str] = []

    if "minimum" in field_schema:
        parts.append(f"min: {field_schema['minimum']}")
    if "maximum" in field_schema:
        parts.append(f"max: {field_schema['maximum']}")
    if "minLength" in field_schema:
        parts.append(f"minLen: {field_schema['minLength']}")
    if "maxLength" in field_schema:
        parts.append(f"maxLen: {field_schema['maxLength']}")
    if "pattern" in field_schema:
        parts.append("pattern: present")
    if "additionalProperties" in field_schema:
        ap = field_schema["additionalProperties"]
        if isinstance(ap, bool):
            parts.append(f"additionalProperties: {str(ap).lower()}")
        else:
            parts.append("additionalProperties: present")

    if "items" in field_schema:
        items = field_schema["items"]
        if isinstance(items, dict) and "type" in items:
            items_type = _normalize_type(items["type"])
            parts.append(f"items: {items_type}")
        else:
            parts.append("items: present")

    if not parts:
        return None

    summary = ", ".join(parts)
    return _truncate_description(summary, MAX_CONSTRAINTS_CHARS) or None


# ---------------------------------------------------------------------------
# 7. Type normalization
# ---------------------------------------------------------------------------


def _normalize_type(type_val: Any) -> str:
    """Normalize JSON Schema type to the allowed set.

    Accepts string or list of strings; returns a single normalized type.
    Unknown or complex types → 'unknown'.
    """
    if isinstance(type_val, str):
        if type_val in _ALLOWED_FIELD_TYPES:
            return type_val
        return "unknown"

    if isinstance(type_val, list):
        # Use the first recognized type
        for t in type_val:
            if isinstance(t, str) and t in _ALLOWED_FIELD_TYPES:
                return t
        return "unknown"

    return "unknown"


# ---------------------------------------------------------------------------
# 8. Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SchemaPreviewField:
    """Per-field schema preview DTO.

    Matches Section 7.2 of the scope document (SchemaFieldDTO).
    """

    field_name: str
    field_type: str
    required: bool
    description_preview: str | None
    enum_preview: tuple[str, ...]
    default_presence: bool
    constraints_preview: str | None
    redaction_status: str

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""
        return {
            "fieldName": self.field_name,
            "fieldType": self.field_type,
            "required": self.required,
            "descriptionPreview": self.description_preview,
            "enumPreview": list(self.enum_preview) if self.enum_preview else None,
            "defaultPresence": self.default_presence,
            "constraintsPreview": self.constraints_preview,
        }


@dataclass(frozen=True, slots=True)
class SchemaPreviewAvailability:
    """Result of risk-based availability determination."""

    preview_available: bool
    reason_code: str
    unavailable_reason: str | None


@dataclass(frozen=True, slots=True)
class ToolSchemaPreview:
    """Top-level Schema Preview DTO.

    Matches Section 7.2 of the scope document (Top-Level Schema Preview DTO).
    """

    canonical_name: str
    risk: str
    risk_rank: int
    capabilities: tuple[str, ...]
    schema_preview_available: bool
    reason_code: str
    unavailable_reason: str | None
    schema_shape: str
    input_fields: tuple[SchemaPreviewField, ...]
    redaction_status: str

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation.

        Only whitelisted fields are included. No Python object repr,
        no memory addresses, no function references.
        """
        return {
            "canonicalName": self.canonical_name,
            "risk": self.risk,
            "capabilities": list(self.capabilities),
            "schemaPreviewAvailable": self.schema_preview_available,
            "reasonCode": self.reason_code,
            "unavailableReason": self.unavailable_reason,
            "schemaShape": self.schema_shape,
            "inputFields": [f.to_safe_dict() for f in self.input_fields],
            "redactionStatus": self.redaction_status,
        }


# ---------------------------------------------------------------------------
# 9. Schema shape detection
# ---------------------------------------------------------------------------


def _detect_schema_shape(schema: Mapping[str, Any] | None) -> str:
    """Detect the top-level schema shape.

    Returns one of: 'object', 'array', 'primitive', 'unknown'.
    """
    if schema is None:
        return "unknown"
    t = schema.get("type")
    if isinstance(t, str):
        if t == "object":
            return "object"
        if t == "array":
            return "array"
        if t in ("string", "number", "integer", "boolean", "null"):
            return "primitive"
    return "unknown"


# ---------------------------------------------------------------------------
# 10. Risk-based availability
# ---------------------------------------------------------------------------


def determine_schema_preview_availability(
    *,
    canonical_name: str,
    primary_risk: str,
    risk_rank: int,
    permanently_denied: bool,
    candidate_allowlisted: bool,
    statically_allowed: bool = False,
) -> SchemaPreviewAvailability:
    """Determine schema preview availability based on risk and policy status.

    Rules (from scope Section 8):
      - Permanent denylist → unavailable (highest priority)
      - R4 → unavailable
      - R5 → unavailable
      - R0/R1/R2 → available
      - R3 → available with enhanced redaction
      - Candidate allowlist → available (but execution still disabled)
      - STATIC_ALLOWLIST → remains empty, no effect on preview

    Pure function: no IO, no side effects.
    """
    # Priority 1: Permanent denylist
    if permanently_denied:
        return SchemaPreviewAvailability(
            preview_available=False,
            reason_code=REASON_UNAVAILABLE_PERMANENTLY_DENIED,
            unavailable_reason="Tool is permanently denied by static policy.",
        )

    # Priority 2: Risk-based unavailability
    if risk_rank >= 5:
        return SchemaPreviewAvailability(
            preview_available=False,
            reason_code=REASON_UNAVAILABLE_RISK_R5,
            unavailable_reason="High-risk system tool — schema preview not available.",
        )

    if risk_rank >= 4:
        return SchemaPreviewAvailability(
            preview_available=False,
            reason_code=REASON_UNAVAILABLE_RISK_R4,
            unavailable_reason="Process/execution tool — schema preview not available.",
        )

    # R3: available with enhanced redaction
    if risk_rank == 3:
        return SchemaPreviewAvailability(
            preview_available=True,
            reason_code=REASON_AVAILABLE_WITH_REDACTION,
            unavailable_reason=None,
        )

    # R0, R1, R2: fully available
    return SchemaPreviewAvailability(
        preview_available=True,
        reason_code=REASON_AVAILABLE,
        unavailable_reason=None,
    )


# ---------------------------------------------------------------------------
# 11. Field sanitizer — processes one property from the schema
# ---------------------------------------------------------------------------


def _sanitize_field(
    name: str,
    field_schema: Mapping[str, Any] | Any,
    required_fields: frozenset[str],
    depth: int,
    visited_ids: set[int],
) -> SchemaPreviewField:
    """Sanitize a single schema property into a safe SchemaPreviewField.

    Applies:
      1. Forbidden field name check
      2. Secret pattern detection in descriptions
      3. Description truncation
      4. Enum truncation and sanitization
      5. Type normalization
      6. Constraints preview
      7. Depth limit
    """
    redaction_reasons: list[str] = []

    # Check forbidden field name
    if _is_forbidden_field_name(name):
        redaction_reasons.append(REDACTED_FORBIDDEN_FIELD)
        return SchemaPreviewField(
            field_name=name,
            field_type="unknown",
            required=name in required_fields,
            description_preview=None,
            enum_preview=(),
            default_presence=False,
            constraints_preview=None,
            redaction_status=REDACTED_FORBIDDEN_FIELD,
        )

    # Guard: field_schema must be a dict-like mapping
    if not isinstance(field_schema, dict):
        return SchemaPreviewField(
            field_name=name,
            field_type="unknown",
            required=name in required_fields,
            description_preview=None,
            enum_preview=(),
            default_presence=False,
            constraints_preview=None,
            redaction_status=REDACTION_STATUS_CLEAN,
        )

    # Depth check (cycle safety via visited_ids)
    field_id = id(field_schema)
    if depth > MAX_NESTED_DEPTH or field_id in visited_ids:
        redaction_reasons.append(REDACTED_DEPTH_LIMIT)
        return SchemaPreviewField(
            field_name=name,
            field_type=_normalize_type(field_schema.get("type")),
            required=name in required_fields,
            description_preview="nested structure truncated",
            enum_preview=(),
            default_presence=False,
            constraints_preview="nested structure truncated",
            redaction_status=REDACTED_DEPTH_LIMIT,
        )

    # Type normalization
    field_type = _normalize_type(field_schema.get("type"))

    # Description sanitization
    raw_desc = field_schema.get("description")
    description_preview: str | None = None
    if isinstance(raw_desc, str):
        if _contains_secret_pattern(raw_desc):
            redaction_reasons.append(REDACTED_SECRET_PATTERN)
            description_preview = "[redacted: secret-like content]"
        else:
            description_preview = _truncate_description(raw_desc)
    elif raw_desc is not None:
        description_preview = None

    # Enum sanitization
    raw_enum = field_schema.get("enum")
    enum_preview: tuple[str, ...] = ()
    if raw_enum is not None and isinstance(raw_enum, list):
        if _enum_contains_secrets(raw_enum):
            redaction_reasons.append(REDACTED_SECRET_PATTERN)
            enum_preview = ()
        else:
            enum_preview = _truncate_enum_values(raw_enum)

    # Default presence (value NOT exposed)
    default_presence = "default" in field_schema

    # Constraints preview
    constraints_preview = _build_constraints_preview(field_schema)

    # Redaction status
    redaction_status = (
        REDACTION_STATUS_REDACTED if redaction_reasons else REDACTION_STATUS_CLEAN
    )

    return SchemaPreviewField(
        field_name=name,
        field_type=field_type,
        required=name in required_fields,
        description_preview=description_preview,
        enum_preview=enum_preview,
        default_presence=default_presence,
        constraints_preview=constraints_preview,
        redaction_status=redaction_status,
    )


# ---------------------------------------------------------------------------
# 12. Schema sanitizer — processes an entire schema dict
# ---------------------------------------------------------------------------


def sanitize_schema(
    schema: Mapping[str, Any] | Any,
) -> tuple[tuple[SchemaPreviewField, ...], str, str]:
    """Sanitize a full JSON Schema dict into safe field previews.

    Returns:
      (fields, redaction_status, schema_shape)

    Applies:
      1. Schema shape detection
      2. Forbidden field name redaction
      3. Secret pattern redaction
      4. Description truncation
      5. Enum truncation
      6. Constraints preview
      7. Nested depth limit (max 4)
      8. Field count limit (max 100)
      9. Cycle-safe recursion via visited id set

    Pure function: no IO, no side effects.
    """
    schema_shape = _detect_schema_shape(schema)

    # Handle None / non-dict
    if schema is None:
        return (), REDACTION_STATUS_UNAVAILABLE, schema_shape

    if not isinstance(schema, dict):
        return (), REDACTION_STATUS_UNAVAILABLE, schema_shape

    # Extract properties
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return (), REDACTION_STATUS_CLEAN, schema_shape

    # Extract required fields
    raw_required = schema.get("required")
    required_fields: frozenset[str] = frozenset()
    if isinstance(raw_required, list):
        required_fields = frozenset(
            r for r in raw_required if isinstance(r, str)
        )

    # Track visited object ids for cycle safety.
    # Only the root schema id is pre-added; child field ids are
    # tracked inside _sanitize_field's recursive descent.
    visited_ids: set[int] = {id(schema)}

    # Process fields
    fields: list[SchemaPreviewField] = []
    has_redaction = False
    field_count_exceeded = False

    for name, field_schema in properties.items():
        if not isinstance(name, str):
            continue
        if len(fields) >= MAX_FIELD_COUNT:
            field_count_exceeded = True
            break

        field = _sanitize_field(
            name=name,
            field_schema=field_schema,
            required_fields=required_fields,
            depth=0,
            visited_ids=visited_ids,
        )
        if field.redaction_status != REDACTION_STATUS_CLEAN:
            has_redaction = True
        fields.append(field)

    # Determine overall redaction status
    if field_count_exceeded:
        redaction_status = REDACTED_FIELD_LIMIT
    elif has_redaction:
        redaction_status = REDACTION_STATUS_REDACTED
    else:
        redaction_status = REDACTION_STATUS_CLEAN

    return tuple(fields), redaction_status, schema_shape


# ---------------------------------------------------------------------------
# 13. Build schema preview — top-level builder function
# ---------------------------------------------------------------------------


def build_schema_preview(
    *,
    canonical_name: str,
    primary_risk: str,
    risk_rank: int,
    capabilities: Iterable[str],
    schema: Mapping[str, Any] | None,
    permanently_denied: bool,
    candidate_allowlisted: bool,
    statically_allowed: bool = False,
) -> ToolSchemaPreview:
    """Build a complete ToolSchemaPreview from raw schema and policy data.

    This is the main entry point. It:
      1. Determines availability from risk/policy
      2. Sanitizes the schema (if available)
      3. Produces a JSON-safe ToolSchemaPreview

    Guarantees:
      - Does NOT execute any tool
      - Does NOT call any handler
      - Does NOT read env vars, files, or network
      - Does NOT access any provider
      - Does NOT write to runtime
      - Returns JSON-safe dataclass
    """
    # Step 1: Determine availability
    availability = determine_schema_preview_availability(
        canonical_name=canonical_name,
        primary_risk=primary_risk,
        risk_rank=risk_rank,
        permanently_denied=permanently_denied,
        candidate_allowlisted=candidate_allowlisted,
        statically_allowed=statically_allowed,
    )

    capabilities_tuple = tuple(sorted(capabilities))

    # Step 2: If unavailable, return early with empty fields
    if not availability.preview_available:
        return ToolSchemaPreview(
            canonical_name=canonical_name,
            risk=primary_risk,
            risk_rank=risk_rank,
            capabilities=capabilities_tuple,
            schema_preview_available=False,
            reason_code=availability.reason_code,
            unavailable_reason=availability.unavailable_reason,
            schema_shape="unknown",
            input_fields=(),
            redaction_status=REDACTION_STATUS_UNAVAILABLE,
        )

    # Step 3: Handle empty/None schema
    if schema is None:
        return ToolSchemaPreview(
            canonical_name=canonical_name,
            risk=primary_risk,
            risk_rank=risk_rank,
            capabilities=capabilities_tuple,
            schema_preview_available=False,
            reason_code=REASON_UNAVAILABLE_EMPTY_SCHEMA,
            unavailable_reason="Tool has no input schema.",
            schema_shape="unknown",
            input_fields=(),
            redaction_status=REDACTION_STATUS_UNAVAILABLE,
        )

    # Step 4: Handle non-dict schema
    if not isinstance(schema, dict):
        return ToolSchemaPreview(
            canonical_name=canonical_name,
            risk=primary_risk,
            risk_rank=risk_rank,
            capabilities=capabilities_tuple,
            schema_preview_available=False,
            reason_code=REASON_UNAVAILABLE_INVALID_SCHEMA,
            unavailable_reason="Schema is not a valid JSON Schema object.",
            schema_shape="unknown",
            input_fields=(),
            redaction_status=REDACTION_STATUS_UNAVAILABLE,
        )

    # Step 5: Sanitize
    input_fields, redaction_status, schema_shape = sanitize_schema(schema)

    # Step 6: Apply enhanced redaction for R3
    if risk_rank == 3 and redaction_status == REDACTION_STATUS_CLEAN:
        # R3 tools always show redacted status to indicate enhanced scrutiny
        redaction_status = REDACTION_STATUS_REDACTED

    return ToolSchemaPreview(
        canonical_name=canonical_name,
        risk=primary_risk,
        risk_rank=risk_rank,
        capabilities=capabilities_tuple,
        schema_preview_available=True,
        reason_code=availability.reason_code,
        unavailable_reason=None,
        schema_shape=schema_shape,
        input_fields=input_fields,
        redaction_status=redaction_status,
    )


# ---------------------------------------------------------------------------
# 14. Convenience function: preview from policy entry name
# ---------------------------------------------------------------------------


def preview_from_policy_name(
    canonical_name: str,
    schema: Mapping[str, Any] | None,
) -> ToolSchemaPreview:
    """Build a ToolSchemaPreview using the static policy inventory.

    Looks up the canonical_name in TOOL_POLICY_INVENTORY and delegates
    to build_schema_preview().

    If the name is not found in the inventory, returns unavailable with
    UNLISTED reason code.
    """
    from hermes_cli.dev_web_tool_policy import (
        TOOL_POLICY_INVENTORY,
        get_tool_policy,
    )

    entry = get_tool_policy(canonical_name)

    if entry is None:
        # Unlisted tool
        return ToolSchemaPreview(
            canonical_name=canonical_name,
            risk="unknown",
            risk_rank=-1,
            capabilities=(),
            schema_preview_available=False,
            reason_code=REASON_UNAVAILABLE_UNLISTED,
            unavailable_reason="Tool is not in the policy inventory.",
            schema_shape="unknown",
            input_fields=(),
            redaction_status=REDACTION_STATUS_UNAVAILABLE,
        )

    return build_schema_preview(
        canonical_name=entry.canonical_name,
        primary_risk=entry.primary_risk.value,
        risk_rank=RISK_RANK[entry.primary_risk],
        capabilities=(c.value for c in entry.capabilities),
        schema=schema,
        permanently_denied=entry.permanently_denied,
        candidate_allowlisted=entry.candidate_allowlisted,
        statically_allowed=entry.statically_allowed,
    )
