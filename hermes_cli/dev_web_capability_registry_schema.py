"""Phase 3C Capability Registry — Schema (frozen taxonomies + validation).

This module defines the **capability model** for the static, dev-only
Capability Registry. It is intentionally a *descriptive* schema: it describes
capabilities, it never loads code, never imports a plugin, never shells out,
never fetches a remote manifest, and never carries a secret.

Frozen design (see docs/webui/phase-3c-*.md):

  - The registry **describes**; it does **not authorize.** A ``permissionClass``
    is a label, not a runtime grant.
  - Every capability in the first version has ``devOnly = True`` and
    ``productionAllowed = False``.
  - No capability record may carry a forbidden field. A forbidden field would
    convert a descriptive registry into an execution surface (dynamic code
    load, shell, SQL mutation, network fetch, or secret carriage).

This module is stdlib-only and has **no side effects** on import.

Phase: 3C — Static dev-only Capability Registry
Status: implemented (static manifest, validation, read model)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 1. Enumerations (frozen taxonomies)
# ---------------------------------------------------------------------------

#: Capability categories.
CATEGORIES: frozenset[str] = frozenset(
    {
        "tool",
        "provider",
        "workflow",
        "sandbox",
        "audit",
        "registry",
        "system",
    }
)

#: Capability lifecycle statuses.
CAPABILITY_STATUSES: frozenset[str] = frozenset(
    {"enabled", "disabled", "blocked", "planned", "deprecated"}
)

#: Permission classes (least → most privileged; the three ``*_FORBIDDEN``
#: classes are terminal and never executable in the first version).
PERMISSION_CLASSES: frozenset[str] = frozenset(
    {
        "READ_ONLY",
        "WRITE_PREVIEW",
        "WRITE_CONFIRM",
        "ROLLBACK_CONFIRM",
        "LIVE_PROVIDER_GATED",
        "ADMIN_FORBIDDEN",
        "EXTERNAL_FORBIDDEN",
        "PRODUCTION_FORBIDDEN",
    }
)

#: Terminal (forbidden) permission classes — always non-executable.
FORBIDDEN_PERMISSION_CLASSES: frozenset[str] = frozenset(
    {"ADMIN_FORBIDDEN", "EXTERNAL_FORBIDDEN", "PRODUCTION_FORBIDDEN"}
)

#: Trust levels.
TRUST_LEVELS: frozenset[str] = frozenset(
    {
        "BUILTIN_VERIFIED",
        "DEV_STATIC_MANIFEST",
        "EXPERIMENTAL_DISABLED",
        "EXTERNAL_FORBIDDEN",
        "UNKNOWN_FORBIDDEN",
    }
)

#: Trust levels that may never be executable in the first version.
FORBIDDEN_TRUST_LEVELS: frozenset[str] = frozenset(
    {"EXTERNAL_FORBIDDEN", "UNKNOWN_FORBIDDEN"}
)

#: Execution modes.
EXECUTION_MODES: frozenset[str] = frozenset(
    {"none", "read_only", "dry_run", "confirmed_execute", "manual_live"}
)

#: Route exposure policies.
ROUTE_EXPOSURES: frozenset[str] = frozenset(
    {"existing_route_only", "no_route", "forbidden_new_route"}
)

#: Allowed ``source`` values for a capability record.
ALLOWED_SOURCES: frozenset[str] = frozenset(
    {"builtin", "static_manifest", "provider_boundary", "workflow_boundary"}
)

#: Executable statuses (a capability may only be ``enabled`` here).
EXECUTABLE_STATUSES: frozenset[str] = frozenset({"enabled"})

#: Non-executable statuses.
NON_EXECUTABLE_STATUSES: frozenset[str] = frozenset(
    {"disabled", "blocked", "planned", "deprecated"}
)


# ---------------------------------------------------------------------------
# 2. Allowed / forbidden manifest fields
# ---------------------------------------------------------------------------

#: The maximum field set a capability record may carry. The static manifest
#: supplies a subset of these; the read model never returns more.
ALLOWED_FIELDS: tuple[str, ...] = (
    "capabilityId",
    "displayName",
    "description",
    "category",
    "version",
    "owner",
    "source",
    "status",
    "permissionClass",
    "trustLevel",
    "executionMode",
    "routeExposure",
    "toolBinding",
    "providerBinding",
    "workflowBinding",
    "requiresApproval",
    "requiresDryRun",
    "requiresConfirmation",
    "requiresAudit",
    "requiresBudget",
    "requiresKillSwitch",
    "devOnly",
    "productionAllowed",
    "disabledByDefault",
    "blockedReason",
    "auditEventPrefix",
    "metadataSchema",
    "createdAt",
    "updatedAt",
)

#: Required manifest fields (validation fails closed if any are missing).
REQUIRED_FIELDS: tuple[str, ...] = (
    "capabilityId",
    "category",
    "permissionClass",
    "trustLevel",
    "status",
)

#: Fields a capability record / manifest entry **must never** carry. Each one
#: would convert a descriptive registry into an execution surface. Validation
#: rejects the entire manifest if any forbidden field is present — it is never
#: silently dropped.
FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "pythonImportPath",
        "callable",
        "shellCommand",
        "externalUrl",
        "downloadUrl",
        "pluginPackage",
        "dynamicModule",
        "evalCode",
        "execCode",
        "sqlStatement",
        "productionPath",
        "apiKey",
        "Authorization",
        "secret",
    }
)

#: Stable ``capabilityId`` format: dot-delimited tokens, lower-snake segments,
#: e.g. ``tool.read.route_governance_read``.
_CAPABILITY_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")

#: Maximum scalar string length (mirrors the audit store bound).
MAX_SCALAR_LENGTH = 2048


# ---------------------------------------------------------------------------
# 3. Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CapabilityValidationError:
    """A single validation error against a manifest entry."""

    capability_id: str
    field: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "capabilityId": self.capability_id,
            "field": self.field,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ValidationReport:
    """Aggregate result of validating a manifest."""

    valid: bool
    error_count: int = 0
    warning_count: int = 0
    blocked_count: int = 0
    capability_count: int = 0
    permission_class_counts: dict[str, int] = field(default_factory=dict)
    trust_level_counts: dict[str, int] = field(default_factory=dict)
    category_counts: dict[str, int] = field(default_factory=dict)
    status_counts: dict[str, int] = field(default_factory=dict)
    errors: list[CapabilityValidationError] = field(default_factory=list)
    warnings: list[CapabilityValidationError] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errorCount": self.error_count,
            "warningCount": self.warning_count,
            "blockedCount": self.blocked_count,
            "capabilityCount": self.capability_count,
            "permissionClassCounts": dict(self.permission_class_counts),
            "trustLevelCounts": dict(self.trust_level_counts),
            "categoryCounts": dict(self.category_counts),
            "statusCounts": dict(self.status_counts),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }


# ---------------------------------------------------------------------------
# 4. Validation helpers
# ---------------------------------------------------------------------------


def is_valid_category(value: Any) -> bool:
    return isinstance(value, str) and value in CATEGORIES


def is_valid_status(value: Any) -> bool:
    return isinstance(value, str) and value in CAPABILITY_STATUSES


def is_valid_permission_class(value: Any) -> bool:
    return isinstance(value, str) and value in PERMISSION_CLASSES


def is_valid_trust_level(value: Any) -> bool:
    return isinstance(value, str) and value in TRUST_LEVELS


def is_valid_execution_mode(value: Any) -> bool:
    return isinstance(value, str) and value in EXECUTION_MODES


def is_valid_route_exposure(value: Any) -> bool:
    return isinstance(value, str) and value in ROUTE_EXPOSURES


def is_valid_source(value: Any) -> bool:
    return isinstance(value, str) and value in ALLOWED_SOURCES


def is_valid_capability_id(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) > MAX_SCALAR_LENGTH:
        return False
    return bool(_CAPABILITY_ID_RE.match(value))


def is_valid_bool(value: Any) -> bool:
    return isinstance(value, bool)


def is_forbidden_field_present(entry: Any) -> str | None:
    """Return the first forbidden field present on ``entry``, else ``None``."""
    if not isinstance(entry, dict):
        return None
    for key in entry:
        if key in FORBIDDEN_FIELDS:
            return key
    return None


def is_terminal_forbidden(permission_class: str) -> bool:
    """True if the permission class is a terminal forbidden class."""
    return permission_class in FORBIDDEN_PERMISSION_CLASSES


def is_executable_status(status: str) -> bool:
    return status in EXECUTABLE_STATUSES


__all__ = [
    "CATEGORIES",
    "CAPABILITY_STATUSES",
    "PERMISSION_CLASSES",
    "FORBIDDEN_PERMISSION_CLASSES",
    "TRUST_LEVELS",
    "FORBIDDEN_TRUST_LEVELS",
    "EXECUTION_MODES",
    "ROUTE_EXPOSURES",
    "ALLOWED_SOURCES",
    "EXECUTABLE_STATUSES",
    "NON_EXECUTABLE_STATUSES",
    "ALLOWED_FIELDS",
    "REQUIRED_FIELDS",
    "FORBIDDEN_FIELDS",
    "MAX_SCALAR_LENGTH",
    "CapabilityValidationError",
    "ValidationReport",
    "is_valid_category",
    "is_valid_status",
    "is_valid_permission_class",
    "is_valid_trust_level",
    "is_valid_execution_mode",
    "is_valid_route_exposure",
    "is_valid_source",
    "is_valid_capability_id",
    "is_valid_bool",
    "is_forbidden_field_present",
    "is_terminal_forbidden",
    "is_executable_status",
]
