"""Schema Preview Read-Only Service for the Hermes Dev WebUI.

Pure-computation query service that reads from the static tool policy module
and combines it with an injectable schema source to produce ToolSchemaPreview
DTOs.  All queries are side-effect-free.

Architecture constraints:
  - stdlib only (no third-party imports)
  - import side effects = 0 (beyond importing static policy constants)
  - no file IO, no network IO, no environment reads
  - no provider imports, no tool handler imports, no runtime DB access
  - no memory access, no review queue access
  - dependency-injected schema source
  - stable sorting by canonicalName
  - JSON-safe output
  - explicit not-found and unavailable handling

Phase: 1G-03-02 — Schema Preview Read-Only Service
Status: Read-only service layer (no API, no OpenAPI, no frontend)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from hermes_cli.dev_web_tool_policy import (
    RISK_RANK,
    TOOL_POLICY_INVENTORY,
    ToolPolicyEntry,
    get_tool_policy,
)
from hermes_cli.dev_web_tool_schema_preview import (
    REASON_UNAVAILABLE_SCHEMA_SOURCE_ERROR,
    REDACTION_STATUS_UNAVAILABLE,
    ToolSchemaPreview,
    build_schema_preview,
)


# ---------------------------------------------------------------------------
# 1. Schema source abstraction
# ---------------------------------------------------------------------------

SchemaSourceCallable = Callable[[str], Mapping[str, Any] | None]
"""Callable that takes a canonical tool name and returns its JSON Schema dict
or ``None`` if the schema is unavailable."""


# ---------------------------------------------------------------------------
# 2. Default empty schema source
# ---------------------------------------------------------------------------


def _empty_schema_source(canonical_name: str) -> Mapping[str, Any] | None:
    """Default schema source that returns ``None`` for all tools.

    This ensures no real tool handler is ever imported or called.
    """
    return None


# ---------------------------------------------------------------------------
# 3. Lookup result model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolSchemaPreviewLookupResult:
    """Result of a single tool schema preview lookup.

    Attributes:
        found: Whether the canonical_name exists in the policy inventory.
        preview: The ToolSchemaPreview if found, otherwise None.
        reason_code: Service-level result code:
            ``"NOT_FOUND"`` — canonical_name not in inventory.
            ``"FOUND"`` — canonical_name found (preview may still be unavailable).
    """

    found: bool
    preview: ToolSchemaPreview | None
    reason_code: str

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""
        return {
            "found": self.found,
            "preview": self.preview.to_safe_dict() if self.preview is not None else None,
            "reasonCode": self.reason_code,
        }


# ---------------------------------------------------------------------------
# 4. Catalog model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolSchemaPreviewCatalog:
    """Result of a catalog-level schema preview query.

    Attributes:
        total_count: Total number of tools in the policy inventory.
        available_count: Number of tools with ``schemaPreviewAvailable = True``.
        unavailable_count: Number of tools with ``schemaPreviewAvailable = False``.
        items: All ToolSchemaPreview DTOs, sorted by canonicalName.
    """

    total_count: int
    available_count: int
    unavailable_count: int
    items: tuple[ToolSchemaPreview, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""
        return {
            "totalCount": self.total_count,
            "availableCount": self.available_count,
            "unavailableCount": self.unavailable_count,
            "items": [item.to_safe_dict() for item in self.items],
        }


# ---------------------------------------------------------------------------
# 5. Internal helpers
# ---------------------------------------------------------------------------


def _build_preview_for_entry(
    entry: ToolPolicyEntry,
    schema_source: SchemaSourceCallable,
) -> ToolSchemaPreview:
    """Build a :class:`ToolSchemaPreview` for a single policy entry.

    Catches exceptions raised by the schema source and converts them to
    unavailable results with ``UNAVAILABLE_SCHEMA_SOURCE_ERROR`` reason code.
    """
    schema: Mapping[str, Any] | None = None
    source_error = False

    try:
        schema = schema_source(entry.canonical_name)
    except Exception:
        source_error = True

    if source_error:
        return ToolSchemaPreview(
            canonical_name=entry.canonical_name,
            risk=entry.primary_risk.value,
            risk_rank=RISK_RANK[entry.primary_risk],
            capabilities=tuple(sorted(c.value for c in entry.capabilities)),
            schema_preview_available=False,
            reason_code=REASON_UNAVAILABLE_SCHEMA_SOURCE_ERROR,
            unavailable_reason="Schema source raised an error.",
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


# ---------------------------------------------------------------------------
# 6. Public API
# ---------------------------------------------------------------------------


def list_schema_previews(
    schema_source: SchemaSourceCallable | None = None,
) -> ToolSchemaPreviewCatalog:
    """List schema previews for all 71 tools in the policy inventory.

    Args:
        schema_source: Callable that takes a canonical tool name and returns
            its JSON Schema dict or ``None``.  Defaults to an empty source
            (all tools have ``schemaPreviewAvailable = False`` due to empty
            schema).

    Returns:
        :class:`ToolSchemaPreviewCatalog` with items sorted by
        ``canonicalName`` (ascending, stable).
    """
    if schema_source is None:
        schema_source = _empty_schema_source

    entries = sorted(
        TOOL_POLICY_INVENTORY.values(),
        key=lambda e: e.canonical_name,
    )

    items: list[ToolSchemaPreview] = []
    available_count = 0
    unavailable_count = 0

    for entry in entries:
        preview = _build_preview_for_entry(entry, schema_source)
        items.append(preview)
        if preview.schema_preview_available:
            available_count += 1
        else:
            unavailable_count += 1

    return ToolSchemaPreviewCatalog(
        total_count=len(items),
        available_count=available_count,
        unavailable_count=unavailable_count,
        items=tuple(items),
    )


def get_schema_preview(
    canonical_name: str,
    schema_source: SchemaSourceCallable | None = None,
) -> ToolSchemaPreviewLookupResult:
    """Look up a single tool's schema preview by canonical name.

    **Exact match only.**  No fuzzy matching, no case folding, no alias
    resolution.

    Args:
        canonical_name: Exact tool canonical name.
        schema_source: Callable that takes a canonical tool name and returns
            its JSON Schema dict or ``None``.  Defaults to empty source.

    Returns:
        :class:`ToolSchemaPreviewLookupResult` with:

        - ``found=True``, ``reasonCode="FOUND"`` when the tool exists in the
          inventory (inner *preview* may still show
          ``schemaPreviewAvailable = False``).
        - ``found=False``, ``reasonCode="NOT_FOUND"`` when the tool does not
          exist in the inventory.
    """
    if schema_source is None:
        schema_source = _empty_schema_source

    entry = get_tool_policy(canonical_name)

    if entry is None:
        return ToolSchemaPreviewLookupResult(
            found=False,
            preview=None,
            reason_code="NOT_FOUND",
        )

    preview = _build_preview_for_entry(entry, schema_source)

    return ToolSchemaPreviewLookupResult(
        found=True,
        preview=preview,
        reason_code="FOUND",
    )
