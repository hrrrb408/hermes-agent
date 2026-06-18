"""Phase 3D Plugin Descriptor Registry — Policy (binding / inheritance / trust).

Enforces the **frozen composition rules** that bind a plugin descriptor to the
Phase 3C Capability Registry. These checks confirm that the registry only
*describes* future plugin descriptors — it never grants permission, never
creates a capability, never creates an approval / confirmation / dry-run /
route, and never introduces an execution path.

Frozen rules (see docs/webui/phase-3d-*.md):

  - A descriptor **must** bind at least one existing Phase 3C capabilityId. It
    never introduces a new capabilityId.
  - A descriptor inherits the **most-restrictive** permission class among its
    bound capabilities. A descriptor may **never** declare a less-restrictive
    class than the inherited one — that is permission escalation and is
    rejected fail-closed.
  - A descriptor may never introduce a new permission class.
  - Trust + status coherence:
      * ``visible`` requires a verified trust level
        (``trusted_builtin_code`` / ``trusted_static_descriptor``);
      * a forbidden trust level (``external_forbidden`` /
        ``unknown_forbidden`` / ``production_forbidden``) **must** be
        ``blocked``;
      * a descriptor binding a forbidden capability (terminal permission class)
        must be ``blocked`` (it can never be marked visible / executable).
  - A descriptor bound to a terminal-forbidden capability cannot be marked
    ``visible``.
  - First-version invariants: ``devOnly = True``, ``productionAllowed = False``,
    ``disabledByDefault = True``.
  - Trust self-upgrade is rejected: a descriptor binding forbidden
    capabilities may not carry a verified trust level.

This module is stdlib-only. It imports the Phase 3C Capability Registry
**read-only** to build a capability index; it performs no side effect.

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
Status: implemented. No plugin runtime, no plugin loader, no dynamic loading.
"""

from __future__ import annotations

from typing import Any

from hermes_cli.dev_web_plugin_descriptor_schema import (
    FORBIDDEN_PERMISSION_CLASSES,
    FORBIDDEN_PLUGIN_TRUST_LEVELS,
    PLUGIN_EXECUTION_MODES,
    PLUGIN_SOURCES,
    PLUGIN_STATUSES,
    PLUGIN_TRUST_LEVELS,
    VISIBLE_TRUST_LEVELS,
    PluginDescriptorValidationError,
    is_terminal_forbidden_permission,
    is_valid_capability_id,
    is_valid_permission_class,
    is_valid_plugin_execution_mode,
    is_valid_plugin_id,
    is_valid_plugin_source,
    is_valid_plugin_status,
    is_valid_plugin_trust_level,
    most_restrictive_permission,
    permission_rank,
)


def _err(plugin_id: str, field_name: str, reason: str) -> PluginDescriptorValidationError:
    return PluginDescriptorValidationError(plugin_id=plugin_id, field=field_name, reason=reason)


# ---------------------------------------------------------------------------
# Phase 3C capability index (read-only binding target)
# ---------------------------------------------------------------------------

#: Cached {capabilityId: permissionClass} view of the validated Phase 3C
#: Capability Registry. Built lazily and read-only. A descriptor's
#: ``capabilityBindings`` must reference keys present here.
_capability_index_cache: dict[str, str] | None = None


def build_capability_index() -> dict[str, str]:
    """Return a ``{capabilityId: permissionClass}`` view of Phase 3C.

    Reads the validated Phase 3C Capability Registry manifest. Deterministic
    and read-only — no side effect, no dynamic loading. The result is cached
    for the process lifetime (the manifest is frozen). On any failure the
    function returns an empty dict, which causes every binding to be rejected
    (fail-closed: a descriptor may never bind to an unknown capability).
    """
    global _capability_index_cache
    if _capability_index_cache is not None:
        return _capability_index_cache
    index: dict[str, str] = {}
    try:
        from hermes_cli.dev_web_capability_registry_manifest import get_static_manifest

        for entry in get_static_manifest():
            if not isinstance(entry, dict):
                continue
            cid = entry.get("capabilityId")
            pc = entry.get("permissionClass")
            if isinstance(cid, str) and isinstance(pc, str) and pc:
                index[cid] = pc
    except Exception:  # pragma: no cover — defensive; fail-closed
        index = {}
    _capability_index_cache = index
    return index


def reset_capability_index_cache() -> None:
    """Clear the cached capability index (test hook only)."""
    global _capability_index_cache
    _capability_index_cache = None


def inherited_permission_class(capability_bindings: Any, index: dict[str, str] | None = None) -> str | None:
    """Return the most-restrictive permission class among bound capabilities.

    Returns ``None`` if the binding list is empty / contains an unknown id /
    contains a non-string. The caller treats ``None`` as a binding failure.
    """
    if index is None:
        index = build_capability_index()
    if not isinstance(capability_bindings, (list, tuple)) or not capability_bindings:
        return None
    classes: list[str] = []
    for cid in capability_bindings:
        if not isinstance(cid, str) or cid not in index:
            return None
        classes.append(index[cid])
    return most_restrictive_permission(classes)


# ---------------------------------------------------------------------------
# Per-entry policy checks
# ---------------------------------------------------------------------------


def check_descriptor_policy(entry: dict[str, Any], index: dict[str, str] | None = None) -> list[PluginDescriptorValidationError]:
    """Return policy violations for a single descriptor entry.

    Pure / deterministic. Never raises. The caller (registry loader) aggregates
    these into a :class:`PluginDescriptorValidationReport`. ``index`` is the
    Phase 3C capability index (built on demand if omitted).
    """
    if not isinstance(entry, dict):
        return [_err("<unknown>", "entry", "entry is not a dict")]

    if index is None:
        index = build_capability_index()

    pid = str(entry.get("pluginId", "<unknown>"))
    errors: list[PluginDescriptorValidationError] = []

    trust_level = entry.get("trustLevel")
    status = entry.get("status")
    permission_class = entry.get("permissionClass")
    bindings = entry.get("capabilityBindings")

    # ── capabilityBindings must be a non-empty list of existing capability ids ──
    if not isinstance(bindings, (list, tuple)) or not bindings:
        errors.append(_err(pid, "capabilityBindings", "capabilityBindings must be a non-empty list"))
        bindings_classes: list[str] = []
        inherited: str | None = None
    else:
        bindings_classes = []
        binding_ok = True
        for cid in bindings:
            if not isinstance(cid, str) or not is_valid_capability_id(cid):
                errors.append(_err(pid, "capabilityBindings", f"invalid capabilityId format: {cid!r}"))
                binding_ok = False
                continue
            if cid not in index:
                errors.append(_err(pid, "capabilityBindings", f"capabilityId does not exist in Phase 3C registry: {cid}"))
                binding_ok = False
                continue
            bindings_classes.append(index[cid])
        inherited = most_restrictive_permission(bindings_classes) if binding_ok and bindings_classes else None

    # ── Permission inheritance: declared must be at least as restrictive as inherited ──
    if inherited is not None and isinstance(permission_class, str) and is_valid_permission_class(permission_class):
        declared_rank = permission_rank(permission_class)
        inherited_rank = permission_rank(inherited)
        if declared_rank < inherited_rank:
            errors.append(
                _err(
                    pid,
                    "permissionClass",
                    f"permission escalation: declared {permission_class} (rank {declared_rank}) is less "
                    f"restrictive than inherited {inherited} (rank {inherited_rank})",
                )
            )

    # ── A descriptor binding a terminal-forbidden capability cannot be visible ──
    if inherited is not None and is_terminal_forbidden_permission(inherited):
        if status != "blocked":
            errors.append(
                _err(
                    pid,
                    "status",
                    f"descriptor bound to forbidden capability ({inherited}) must be blocked",
                )
            )
        # Trust self-upgrade: a descriptor bound to forbidden capabilities may
        # not carry a verified trust level.
        if isinstance(trust_level, str) and trust_level in VISIBLE_TRUST_LEVELS:
            errors.append(
                _err(
                    pid,
                    "trustLevel",
                    f"descriptor bound to forbidden capability may not carry verified trust level {trust_level}",
                )
            )

    # ── Trust / status coherence ───────────────────────────────────────────────
    if status == "visible":
        if not (isinstance(trust_level, str) and trust_level in VISIBLE_TRUST_LEVELS):
            errors.append(
                _err(pid, "trustLevel", f"status=visible requires a verified trust level (got {trust_level})")
            )
    if isinstance(trust_level, str) and trust_level in FORBIDDEN_PLUGIN_TRUST_LEVELS:
        if status != "blocked":
            errors.append(
                _err(pid, "status", f"trustLevel={trust_level} must be blocked")
            )
    if trust_level == "experimental_disabled_descriptor":
        if status not in ("disabled", "blocked", "planned"):
            errors.append(
                _err(pid, "status", "trustLevel=experimental_disabled_descriptor must be disabled/planned/blocked")
            )

    # ── Forbidden permission classes must be non-executable ────────────────────
    if isinstance(permission_class, str) and permission_class in FORBIDDEN_PERMISSION_CLASSES:
        if status not in ("disabled", "blocked"):
            errors.append(
                _err(pid, "status", f"permissionClass={permission_class} must be disabled or blocked")
            )

    # ── First-version invariants ───────────────────────────────────────────────
    if entry.get("productionAllowed") is True:
        errors.append(_err(pid, "productionAllowed", "must be false in the first version"))
    if entry.get("devOnly") is not True:
        errors.append(_err(pid, "devOnly", "must be true in the first version"))
    if entry.get("disabledByDefault") is not True:
        errors.append(_err(pid, "disabledByDefault", "must be true in the first version"))

    # ── blocked descriptors must carry a blockedReason ──────────────────────────
    if status == "blocked" and not entry.get("blockedReason"):
        errors.append(_err(pid, "blockedReason", "status=blocked requires a blockedReason"))

    # ── An execution surface may never be present in an executable mode ────────
    # The taxonomy has no executable mode; this is a defense-in-depth assertion.
    if isinstance(entry.get("executionMode"), str) and entry.get("executionMode") not in PLUGIN_EXECUTION_MODES:
        errors.append(_err(pid, "executionMode", "invalid executionMode"))

    return errors


__all__ = [
    "build_capability_index",
    "reset_capability_index_cache",
    "inherited_permission_class",
    "check_descriptor_policy",
    "permission_rank",
    "most_restrictive_permission",
]
