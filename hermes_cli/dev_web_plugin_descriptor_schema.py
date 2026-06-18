"""Phase 3D Plugin Descriptor Registry — Schema (frozen taxonomies + validation).

This module defines the **plugin descriptor model** for the static, dev-only
Plugin Descriptor Registry. It is intentionally a *descriptive* schema: it
describes future plugin descriptors, it never loads code, never imports a
plugin, never shells out, never fetches a remote manifest, never reads a local
plugin directory, and never carries a secret.

Hard guarantees (frozen, see docs/webui/phase-3d-*.md):

  - The registry **describes** future plugin descriptors; it does **not**
    authorize execution, does **not** grant permission, does **not** create an
    approval / confirmation / dry-run / route / execution path.
  - Every descriptor in the first version has ``devOnly = True``,
    ``productionAllowed = False`` and ``disabledByDefault = True``.
  - A descriptor **binds only** to existing Phase 3C Capability Registry
    capabilityIds (validated in the policy module). It never introduces a new
    capabilityId or a new permission class.
  - No descriptor may carry a forbidden field. A forbidden field would convert
    a descriptive registry into an execution surface (dynamic code load, shell,
    SQL mutation, network fetch, secret carriage, install hook, …). Validation
    is recursive and fail-closed.

This module is stdlib-only and has **no side effects** on import.

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
Status: implemented (static manifest, validation, read model). No plugin
        runtime, no plugin loader, no dynamic loading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 1. Enumerations (frozen taxonomies)
# ---------------------------------------------------------------------------

#: Plugin trust levels. The ``*_forbidden`` levels are terminal: a descriptor
#: with one of them must be ``blocked`` and is never executable.
PLUGIN_TRUST_LEVELS: frozenset[str] = frozenset(
    {
        "trusted_builtin_code",
        "trusted_static_descriptor",
        "dev_reviewed_descriptor",
        "experimental_disabled_descriptor",
        "external_forbidden",
        "unknown_forbidden",
        "production_forbidden",
    }
)

#: Trust levels that are terminal / forbidden — always non-executable.
FORBIDDEN_PLUGIN_TRUST_LEVELS: frozenset[str] = frozenset(
    {"external_forbidden", "unknown_forbidden", "production_forbidden"}
)

#: Trust levels that may be exposed as a visible descriptor-only record.
VISIBLE_TRUST_LEVELS: frozenset[str] = frozenset(
    {"trusted_builtin_code", "trusted_static_descriptor"}
)

#: Plugin lifecycle statuses.
PLUGIN_STATUSES: frozenset[str] = frozenset(
    {"planned", "declared", "validated", "visible", "disabled", "blocked", "deprecated", "removed"}
)

#: Statuses that represent a non-executable descriptor (no runtime lifecycle).
#: The first version never carries an executable lifecycle status such as
#: ``installed`` / ``loaded`` / ``executing`` — those do not exist in the
#: taxonomy because there is no plugin runtime.
NON_EXECUTABLE_PLUGIN_STATUSES: frozenset[str] = frozenset(
    {"planned", "declared", "validated", "visible", "disabled", "blocked", "deprecated", "removed"}
)

#: Plugin execution modes. All four are descriptor-level only — **none** of
#: them represents runtime execution. The first version has no plugin runtime,
#: so a descriptor can never be in an executable mode.
PLUGIN_EXECUTION_MODES: frozenset[str] = frozenset(
    {"none", "descriptor_only", "read_only_descriptor", "disabled_runtime"}
)

#: Plugin descriptor ``source`` values.
PLUGIN_SOURCES: frozenset[str] = frozenset(
    {
        "builtin_static",
        "tracked_static_descriptor",
        "dev_reviewed_descriptor",
        "experimental_disabled",
        "external_forbidden",
        "unknown_forbidden",
        "production_forbidden",
    }
)

#: Permission classes — shared with the Phase 3C Capability Registry. A
#: descriptor inherits the most-restrictive class among its bound capabilities
#: and may never declare a less-restrictive class (escalation is rejected).
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

#: Permission restrictiveness ordering — most restrictive first. Used to
#: compute the inherited (most-restrictive) permission class among a
#: descriptor's bound capabilities and to reject permission escalation.
#: Higher index in this tuple == more restrictive (more locked-down).
PERMISSION_RESTRICTIVENESS_ORDER: tuple[str, ...] = (
    "READ_ONLY",            # 0 — least restrictive (minimal privilege)
    "WRITE_PREVIEW",        # 1
    "WRITE_CONFIRM",        # 2
    "ROLLBACK_CONFIRM",     # 3
    "LIVE_PROVIDER_GATED",  # 4
    "ADMIN_FORBIDDEN",      # 5
    "EXTERNAL_FORBIDDEN",   # 6
    "PRODUCTION_FORBIDDEN",  # 7 — most restrictive (terminal block)
)

#: Map permission class → restrictiveness rank (higher == more restrictive).
PERMISSION_RESTRICTIVENESS_RANK: dict[str, int] = {
    cls: rank for rank, cls in enumerate(PERMISSION_RESTRICTIVENESS_ORDER)
}


def permission_rank(permission_class: Any) -> int:
    """Return the restrictiveness rank of a permission class (higher = stricter).

    Unknown classes rank ``-1`` (less restrictive than anything, so any real
    class is considered at-least-as-restrictive — callers must validate class
    membership separately).
    """
    if isinstance(permission_class, str) and permission_class in PERMISSION_RESTRICTIVENESS_RANK:
        return PERMISSION_RESTRICTIVENESS_RANK[permission_class]
    return -1


def most_restrictive_permission(classes: Any) -> str | None:
    """Return the most-restrictive permission class among ``classes``.

    ``classes`` is any iterable of permission-class strings. Returns ``None``
    for an empty / invalid input. The most-restrictive class is the one with
    the **highest** restrictiveness rank.
    """
    best: str | None = None
    best_rank = -2
    for cls in classes or ():
        rank = permission_rank(cls)
        if rank > best_rank:
            best_rank = rank
            best = cls if isinstance(cls, str) and cls in PERMISSION_RESTRICTIVENESS_RANK else best
    return best


# ---------------------------------------------------------------------------
# 2. Allowed / forbidden manifest fields
# ---------------------------------------------------------------------------

#: The maximum field set a plugin descriptor may carry. The static manifest
#: supplies a subset of these; the read model never returns more.
ALLOWED_FIELDS: tuple[str, ...] = (
    "pluginId",
    "displayName",
    "description",
    "version",
    "owner",
    "source",
    "trustLevel",
    "status",
    "capabilityBindings",
    "permissionClass",
    "executionMode",
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
    "metadataSchema",
    "createdAt",
    "updatedAt",
)

#: Required manifest fields (validation fails closed if any are missing).
REQUIRED_FIELDS: tuple[str, ...] = (
    "pluginId",
    "displayName",
    "source",
    "trustLevel",
    "status",
    "capabilityBindings",
    "permissionClass",
    "executionMode",
    "devOnly",
    "productionAllowed",
    "disabledByDefault",
)

#: Fields a plugin descriptor / manifest entry **must never** carry. Each one
#: would convert a descriptive registry into an execution surface. This set is
#: the union of the canonical forbidden names and their alias / casing
#: variants; validation rejects the entire manifest if any forbidden field is
#: present at any depth — it is never silently dropped.
FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        # Canonical execution-surface names
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
        "localPath",
        "remoteUrl",
        "installCommand",
        "postInstallHook",
        "preExecutionHook",
        "arbitraryArgs",
        # Alias / casing / snake_case variants
        "authorization",
        "AUTHORIZATION",
        "bearer",
        "Bearer",
        "api_key",
        "secretValue",
        "token",
        "accessToken",
        "callable_repr",
        "shell_command",
        "sql",
        "production_path",
        "dynamic_import",
        "importPath",
        "modulePath",
        "external_url",
        "download_url",
        "install_command",
        "post_install_hook",
        "pre_execution_hook",
    }
)

#: Stable ``pluginId`` format: dot-delimited tokens, lower-snake segments,
#: e.g. ``plugin.descriptor.registry_status``.
_PLUGIN_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")

#: Stable ``capabilityId`` format (Phase 3C): dot-delimited lower-snake tokens.
_CAPABILITY_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")

#: Maximum scalar string length (mirrors the audit store bound).
MAX_SCALAR_LENGTH = 2048


# ---------------------------------------------------------------------------
# 3. Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PluginDescriptorValidationError:
    """A single validation error against a manifest entry."""

    plugin_id: str
    field: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "pluginId": self.plugin_id,
            "field": self.field,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PluginDescriptorValidationReport:
    """Aggregate result of validating a descriptor manifest."""

    valid: bool
    error_count: int = 0
    warning_count: int = 0
    descriptor_count: int = 0
    visible_count: int = 0
    disabled_count: int = 0
    blocked_count: int = 0
    bound_capability_count: int = 0
    permission_class_counts: dict[str, int] = field(default_factory=dict)
    trust_level_counts: dict[str, int] = field(default_factory=dict)
    status_counts: dict[str, int] = field(default_factory=dict)
    execution_mode_counts: dict[str, int] = field(default_factory=dict)
    source_counts: dict[str, int] = field(default_factory=dict)
    errors: list[PluginDescriptorValidationError] = field(default_factory=list)
    warnings: list[PluginDescriptorValidationError] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errorCount": self.error_count,
            "warningCount": self.warning_count,
            "descriptorCount": self.descriptor_count,
            "visibleCount": self.visible_count,
            "disabledCount": self.disabled_count,
            "blockedCount": self.blocked_count,
            "boundCapabilityCount": self.bound_capability_count,
            "permissionClassCounts": dict(self.permission_class_counts),
            "trustLevelCounts": dict(self.trust_level_counts),
            "statusCounts": dict(self.status_counts),
            "executionModeCounts": dict(self.execution_mode_counts),
            "sourceCounts": dict(self.source_counts),
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }


# ---------------------------------------------------------------------------
# 4. Validation helpers
# ---------------------------------------------------------------------------


def is_valid_plugin_trust_level(value: Any) -> bool:
    return isinstance(value, str) and value in PLUGIN_TRUST_LEVELS


def is_valid_plugin_status(value: Any) -> bool:
    return isinstance(value, str) and value in PLUGIN_STATUSES


def is_valid_plugin_execution_mode(value: Any) -> bool:
    return isinstance(value, str) and value in PLUGIN_EXECUTION_MODES


def is_valid_plugin_source(value: Any) -> bool:
    return isinstance(value, str) and value in PLUGIN_SOURCES


def is_valid_permission_class(value: Any) -> bool:
    return isinstance(value, str) and value in PERMISSION_CLASSES


def is_terminal_forbidden_permission(value: Any) -> bool:
    return isinstance(value, str) and value in FORBIDDEN_PERMISSION_CLASSES


def is_valid_plugin_id(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) > MAX_SCALAR_LENGTH:
        return False
    return bool(_PLUGIN_ID_RE.match(value))


def is_valid_capability_id(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) > MAX_SCALAR_LENGTH:
        return False
    return bool(_CAPABILITY_ID_RE.match(value))


def is_valid_bool(value: Any) -> bool:
    return isinstance(value, bool)


def is_executable_execution_mode(value: Any) -> bool:
    """True if an execution mode represents runtime execution.

    The plugin-descriptor taxonomy has **no** executable mode, so this always
    returns ``False``. It exists as an explicit, grep-able guard so a future
    taxonomy change cannot silently introduce an executable mode.
    """
    # No value in PLUGIN_EXECUTION_MODES is executable in the first version.
    return False


def _scan_for_forbidden(node: Any) -> str | None:
    """Return the first forbidden key found anywhere in ``node`` (recursive).

    Pre-order, depth-first traversal that checks every dict key — at the top
    level and inside any nested dict / list / tuple value — so a forbidden
    field cannot be smuggled inside an allowed field's nested value (e.g.
    inside a ``metadataSchema`` dict). Returns the first forbidden key found,
    else ``None``. Never raises.
    """
    if isinstance(node, dict):
        for key in node:
            if key in FORBIDDEN_FIELDS:
                return str(key)
        for value in node.values():
            found = _scan_for_forbidden(value)
            if found is not None:
                return found
    elif isinstance(node, (list, tuple)):
        for item in node:
            found = _scan_for_forbidden(item)
            if found is not None:
                return found
    return None


def is_forbidden_field_present(entry: Any) -> str | None:
    """Return the first forbidden field present anywhere in ``entry``, else ``None``.

    The scan is **recursive**: it walks top-level keys AND any nested dict /
    list / tuple structure, so a forbidden field (``shellCommand``,
    ``Authorization``, ``secret``, ``installCommand``, …) hidden inside an
    allowed field's value — e.g. ``{"metadataSchema": {"shellCommand": "rm -rf"}}``
    — is detected and treated as a fail-closed validation error, never exposed
    by the read model. Non-dict input returns ``None`` (a non-dict entry is
    reported by the caller's type check, not here).
    """
    if not isinstance(entry, dict):
        return None
    return _scan_for_forbidden(entry)


__all__ = [
    "PLUGIN_TRUST_LEVELS",
    "FORBIDDEN_PLUGIN_TRUST_LEVELS",
    "VISIBLE_TRUST_LEVELS",
    "PLUGIN_STATUSES",
    "NON_EXECUTABLE_PLUGIN_STATUSES",
    "PLUGIN_EXECUTION_MODES",
    "PLUGIN_SOURCES",
    "PERMISSION_CLASSES",
    "FORBIDDEN_PERMISSION_CLASSES",
    "PERMISSION_RESTRICTIVENESS_ORDER",
    "PERMISSION_RESTRICTIVENESS_RANK",
    "ALLOWED_FIELDS",
    "REQUIRED_FIELDS",
    "FORBIDDEN_FIELDS",
    "MAX_SCALAR_LENGTH",
    "PluginDescriptorValidationError",
    "PluginDescriptorValidationReport",
    "permission_rank",
    "most_restrictive_permission",
    "is_valid_plugin_trust_level",
    "is_valid_plugin_status",
    "is_valid_plugin_execution_mode",
    "is_valid_plugin_source",
    "is_valid_permission_class",
    "is_terminal_forbidden_permission",
    "is_valid_plugin_id",
    "is_valid_capability_id",
    "is_valid_bool",
    "is_executable_execution_mode",
    "_scan_for_forbidden",
    "is_forbidden_field_present",
]
