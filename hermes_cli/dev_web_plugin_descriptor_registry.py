"""Phase 3D Plugin Descriptor Registry — loader, validation, read model.

Loads the static manifest
(:mod:`hermes_cli.dev_web_plugin_descriptor_manifest`), validates it against
the frozen schema + capability-binding + permission-inheritance + trust policy,
and exposes a **read-only** descriptor-registry summary + per-descriptor safe
records.

Hard guarantees (frozen, see docs/webui/phase-3d-*.md):

  - The registry **describes** future plugin descriptors; it never authorizes
    execution, grants permission, creates an approval / confirmation / dry-run
    / route, or introduces an execution path.
  - No plugin runtime. No plugin loader. No dynamic loading (no ``importlib`` /
    ``__import__`` / path-based load / directory scan). No local plugin
    directory loading. No remote registry / marketplace / external plugin
    fetch. No provider-generated plugin. No LLM-generated plugin install.
  - Validation fails closed: if the manifest is invalid, the registry status
    is ``validation_failed`` and invalid entries are blocked (never exposed as
    enabled / visible-executable).
  - The read model never returns a forbidden field (API key, Authorization,
    Bearer token, raw secret, callable repr, shell command, SQL statement,
    production path, local plugin path, dynamic import path, external URL,
    download URL, install command).
  - Frozen policy flags are constants: ``pluginRuntimeImplemented = False``,
    ``pluginLoaderImplemented = False``, ``dynamicLoadingAllowed = False``,
    ``localPluginDirectoryLoadingAllowed = False``,
    ``remoteRegistryAllowed = False``, ``marketplaceAllowed = False``,
    ``externalPluginFetchAllowed = False``,
    ``providerGeneratedPluginAllowed = False``,
    ``llmGeneratedPluginInstallAllowed = False``,
    ``pluginExecutionAllowed = False``, ``newRouteIntroduced = False``,
    ``productionAllowed = False``, ``devOnly = True``,
    ``redactionApplied = True``.

This module is stdlib-only and has no side effects on import.

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
Status: implemented. No plugin runtime execution, no plugin loader execution.
"""

from __future__ import annotations

from typing import Any

from hermes_cli.dev_web_plugin_descriptor_manifest import (
    MANIFEST_VERSION,
    get_static_manifest,
)
from hermes_cli.dev_web_plugin_descriptor_policy import (
    build_capability_index,
    check_descriptor_policy,
)
from hermes_cli.dev_web_plugin_descriptor_schema import (
    ALLOWED_FIELDS,
    FORBIDDEN_FIELDS,
    PluginDescriptorValidationReport,
    PluginDescriptorValidationError,
    REQUIRED_FIELDS,
    is_forbidden_field_present,
    is_valid_bool,
    is_valid_permission_class,
    is_valid_plugin_execution_mode,
    is_valid_plugin_id,
    is_valid_plugin_source,
    is_valid_plugin_status,
    is_valid_plugin_trust_level,
)

#: Frozen route-governance baseline surfaced by the registry summary. Unchanged
#: by Phase 3D — no new HTTP route is introduced.
ROUTE_GOVERNANCE_EXPECTED = "34/34/5/0/1/1"

#: Frozen policy flags for the first version. These are constants, not state.
PLUGIN_RUNTIME_IMPLEMENTED: bool = False
PLUGIN_LOADER_IMPLEMENTED: bool = False
DYNAMIC_LOADING_ALLOWED: bool = False
LOCAL_PLUGIN_DIRECTORY_LOADING_ALLOWED: bool = False
REMOTE_REGISTRY_ALLOWED: bool = False
MARKETPLACE_ALLOWED: bool = False
EXTERNAL_PLUGIN_FETCH_ALLOWED: bool = False
PROVIDER_GENERATED_PLUGIN_ALLOWED: bool = False
LLM_GENERATED_PLUGIN_INSTALL_ALLOWED: bool = False
PLUGIN_EXECUTION_ALLOWED: bool = False
NEW_ROUTE_INTRODUCED: bool = False
DEV_ONLY: bool = True
PRODUCTION_ALLOWED: bool = False

#: The fields the read model exposes for a descriptor detail.
DETAIL_FIELDS: tuple[str, ...] = (
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
)

#: Fields that must be scalar strings when present (never a nested dict/list).
SCALAR_STRING_FIELDS: tuple[str, ...] = (
    "displayName",
    "description",
    "version",
    "owner",
    "blockedReason",
    "metadataSchema",
)

#: The list field (capabilityBindings) — must be a list/tuple of scalar strings.
LIST_STRING_FIELDS: tuple[str, ...] = ("capabilityBindings",)


# ---------------------------------------------------------------------------
# 1. Validation
# ---------------------------------------------------------------------------


def _validate_entry(entry: Any, index: dict[str, str]) -> list[PluginDescriptorValidationError]:
    """Validate a single manifest entry (schema + policy). Never raises."""
    if not isinstance(entry, dict):
        return [PluginDescriptorValidationError("<unknown>", "entry", "entry is not a dict")]

    pid = str(entry.get("pluginId", "<unknown>"))
    errors: list[PluginDescriptorValidationError] = []

    def _err(field_name: str, reason: str) -> None:
        errors.append(PluginDescriptorValidationError(pid, field_name, reason))

    # Forbidden fields → reject the entry outright (fail closed).
    forbidden = is_forbidden_field_present(entry)
    if forbidden is not None:
        _err(forbidden, f"forbidden field present: {forbidden}")
        return errors

    # Required fields.
    for required in REQUIRED_FIELDS:
        if required not in entry or entry[required] is None:
            _err(required, f"missing required field: {required}")

    # pluginId format + stability.
    if "pluginId" in entry and not is_valid_plugin_id(entry["pluginId"]):
        _err("pluginId", "pluginId must be a stable dot-delimited id")

    # Enum validity.
    if "trustLevel" in entry and not is_valid_plugin_trust_level(entry["trustLevel"]):
        _err("trustLevel", "invalid trustLevel")
    if "status" in entry and not is_valid_plugin_status(entry["status"]):
        _err("status", "invalid status")
    if "executionMode" in entry and not is_valid_plugin_execution_mode(entry["executionMode"]):
        _err("executionMode", "invalid executionMode")
    if "source" in entry and not is_valid_plugin_source(entry["source"]):
        _err("source", "invalid source")
    if "permissionClass" in entry and not is_valid_permission_class(entry["permissionClass"]):
        _err("permissionClass", "invalid permissionClass")

    # Boolean fields.
    for bool_field in (
        "requiresApproval",
        "requiresDryRun",
        "requiresConfirmation",
        "requiresAudit",
        "requiresBudget",
        "requiresKillSwitch",
        "devOnly",
        "productionAllowed",
        "disabledByDefault",
    ):
        if bool_field in entry and entry[bool_field] is not None and not is_valid_bool(entry[bool_field]):
            _err(bool_field, f"{bool_field} must be a boolean")

    # Scalar-string fields must never carry a nested dict/list value.
    for scalar_field in SCALAR_STRING_FIELDS:
        if scalar_field in entry and entry[scalar_field] is not None:
            if not isinstance(entry[scalar_field], str):
                _err(scalar_field, f"{scalar_field} must be a string scalar (no nested structure)")

    # capabilityBindings must be a list/tuple of scalar strings (no nested
    # structure that could smuggle content past the read model).
    bindings = entry.get("capabilityBindings")
    if bindings is not None:
        if not isinstance(bindings, (list, tuple)):
            _err("capabilityBindings", "capabilityBindings must be a list")
        else:
            for item in bindings:
                if not isinstance(item, str):
                    _err("capabilityBindings", "capabilityBindings must contain only string ids")

    # First-version invariants.
    if entry.get("devOnly") is not True:
        _err("devOnly", "devOnly must be true in the first version")
    if entry.get("productionAllowed") is True:
        _err("productionAllowed", "productionAllowed must be false in the first version")
    if entry.get("disabledByDefault") is not True:
        _err("disabledByDefault", "disabledByDefault must be true in the first version")

    # blocked descriptors need a reason.
    if entry.get("status") == "blocked" and not entry.get("blockedReason"):
        _err("blockedReason", "status=blocked requires a blockedReason")

    # Unknown allowed-field whitelist: a manifest entry may only carry fields
    # from the allowed set (no extra keys that smuggle in an execution surface).
    for key in entry:
        if key not in ALLOWED_FIELDS:
            _err(key, f"unknown field: {key}")

    # Policy composition checks (capability binding + inheritance + trust).
    errors.extend(check_descriptor_policy(entry, index))

    return errors


def validate_manifest(entries: Any) -> PluginDescriptorValidationReport:
    """Validate a manifest (list/tuple of entries). Returns a report.

    Fail-closed semantics: ``valid`` is ``True`` only when every entry passes
    schema + policy + uniqueness.
    """
    errors: list[PluginDescriptorValidationError] = []
    warnings: list[PluginDescriptorValidationError] = []

    index = build_capability_index()

    if not isinstance(entries, (list, tuple)):
        return PluginDescriptorValidationReport(
            valid=False,
            error_count=1,
            errors=[PluginDescriptorValidationError("<root>", "manifest", "manifest is not a list/tuple")],
        )

    seen_ids: dict[str, int] = {}
    permission_counts: dict[str, int] = {}
    trust_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    exec_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    bound_capability_count = 0

    for entry in entries:
        entry_errors = _validate_entry(entry, index)
        errors.extend(entry_errors)

        if isinstance(entry, dict):
            pid = str(entry.get("pluginId", ""))
            if pid:
                seen_ids[pid] = seen_ids.get(pid, 0) + 1
            pc = entry.get("permissionClass")
            if isinstance(pc, str):
                permission_counts[pc] = permission_counts.get(pc, 0) + 1
            tl = entry.get("trustLevel")
            if isinstance(tl, str):
                trust_counts[tl] = trust_counts.get(tl, 0) + 1
            st = entry.get("status")
            if isinstance(st, str):
                status_counts[st] = status_counts.get(st, 0) + 1
            em = entry.get("executionMode")
            if isinstance(em, str):
                exec_counts[em] = exec_counts.get(em, 0) + 1
            src = entry.get("source")
            if isinstance(src, str):
                source_counts[src] = source_counts.get(src, 0) + 1
            bindings = entry.get("capabilityBindings")
            if isinstance(bindings, (list, tuple)):
                bound_capability_count += len(bindings)

    # pluginId uniqueness.
    for pid, count in seen_ids.items():
        if count > 1:
            errors.append(
                PluginDescriptorValidationError(pid, "pluginId", f"duplicate pluginId ({count} occurrences)")
            )

    visible_count = status_counts.get("visible", 0)
    disabled_count = status_counts.get("disabled", 0)
    blocked_count = status_counts.get("blocked", 0)

    return PluginDescriptorValidationReport(
        valid=(len(errors) == 0),
        error_count=len(errors),
        warning_count=len(warnings),
        descriptor_count=len(entries) if isinstance(entries, (list, tuple)) else 0,
        visible_count=visible_count,
        disabled_count=disabled_count,
        blocked_count=blocked_count,
        bound_capability_count=bound_capability_count,
        permission_class_counts=permission_counts,
        trust_level_counts=trust_counts,
        status_counts=status_counts,
        execution_mode_counts=exec_counts,
        source_counts=source_counts,
        errors=errors,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# 2. Read model
# ---------------------------------------------------------------------------


def _safe_detail(entry: dict[str, Any]) -> dict[str, Any]:
    """Build the safe read-only detail dict for a single descriptor.

    Only carries :data:`DETAIL_FIELDS`. A defensive second guard drops any
    forbidden field that slipped through (they can never be present after
    validation, but defense in depth). ``capabilityBindings`` is normalized to
    a tuple of strings.
    """
    detail: dict[str, Any] = {"redactionApplied": True}
    for field_name in DETAIL_FIELDS:
        if field_name in FORBIDDEN_FIELDS:
            continue
        if field_name in entry:
            value = entry[field_name]
            if field_name == "capabilityBindings" and isinstance(value, (list, tuple)):
                detail[field_name] = tuple(str(v) for v in value if isinstance(v, str))
            else:
                detail[field_name] = value
    return detail


def list_descriptor_details(entries: Any) -> list[dict[str, Any]]:
    """Return the safe detail list for every entry (deterministic order).

    Invalid entries (those carrying a forbidden field) are blocked out — their
    detail is reduced to a blocked record so the read model never exposes an
    execution surface even if a caller feeds an unvalidated manifest.
    """
    details: list[dict[str, Any]] = []
    if not isinstance(entries, (list, tuple)):
        return details
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if is_forbidden_field_present(entry) is not None:
            details.append(
                {
                    "pluginId": str(entry.get("pluginId", "<blocked>")),
                    "status": "blocked",
                    "blockedReason": "forbidden_field_present_validation_failed",
                    "redactionApplied": True,
                }
            )
            continue
        details.append(_safe_detail(entry))
    return details


def get_descriptor_detail(entries: Any, plugin_id: str) -> dict[str, Any] | None:
    """Return the safe detail for one ``plugin_id``, or ``None`` if absent."""
    if not isinstance(plugin_id, str) or not plugin_id:
        return None
    if not isinstance(entries, (list, tuple)):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get("pluginId") == plugin_id:
            if is_forbidden_field_present(entry) is not None:
                return {
                    "pluginId": plugin_id,
                    "status": "blocked",
                    "blockedReason": "forbidden_field_present_validation_failed",
                    "redactionApplied": True,
                }
            return _safe_detail(entry)
    return None


def build_registry_summary(report: PluginDescriptorValidationReport | None = None) -> dict[str, Any]:
    """Build the read-only descriptor-registry summary surfaced under ``/status``.

    The summary is value-free: no secret, no path, no callable repr. Frozen
    policy flags are constants. ``report`` may be ``None`` (loads + validates
    the static manifest on demand).
    """
    if report is None:
        report = validate_manifest(get_static_manifest())

    if report.valid:
        registry_status = "enabled"
    else:
        # Fail closed: never expose an invalid registry as healthy/enabled.
        registry_status = "validation_failed"

    return {
        "status": registry_status,
        "registryVersion": MANIFEST_VERSION,
        "descriptorCount": report.descriptor_count,
        "visibleCount": report.visible_count,
        "disabledCount": report.disabled_count,
        "blockedCount": report.blocked_count,
        "devOnly": DEV_ONLY,
        "productionAllowed": PRODUCTION_ALLOWED,
        "pluginRuntimeImplemented": PLUGIN_RUNTIME_IMPLEMENTED,
        "pluginLoaderImplemented": PLUGIN_LOADER_IMPLEMENTED,
        "dynamicLoadingAllowed": DYNAMIC_LOADING_ALLOWED,
        "localPluginDirectoryLoadingAllowed": LOCAL_PLUGIN_DIRECTORY_LOADING_ALLOWED,
        "remoteRegistryAllowed": REMOTE_REGISTRY_ALLOWED,
        "marketplaceAllowed": MARKETPLACE_ALLOWED,
        "externalPluginFetchAllowed": EXTERNAL_PLUGIN_FETCH_ALLOWED,
        "providerGeneratedPluginAllowed": PROVIDER_GENERATED_PLUGIN_ALLOWED,
        "llmGeneratedPluginInstallAllowed": LLM_GENERATED_PLUGIN_INSTALL_ALLOWED,
        "pluginExecutionAllowed": PLUGIN_EXECUTION_ALLOWED,
        "newRouteIntroduced": NEW_ROUTE_INTRODUCED,
        "routeGovernanceExpected": ROUTE_GOVERNANCE_EXPECTED,
        "validation": {
            "valid": report.valid,
            "errorCount": report.error_count,
            "warningCount": report.warning_count,
        },
        "redactionApplied": True,
    }


def get_plugin_descriptor_status_block() -> dict[str, Any]:
    """Load + validate the static manifest and return the ``/status`` block.

    This is the single entry point used by the ``/status`` response. It never
    raises — a load/validation failure is surfaced as
    ``status=validation_failed`` so ``/status`` itself never fails because of
    the descriptor registry.
    """
    try:
        report = validate_manifest(get_static_manifest())
        return build_registry_summary(report)
    except Exception:  # pragma: no cover — defensive; never fail /status
        return {
            "status": "validation_failed",
            "registryVersion": MANIFEST_VERSION,
            "descriptorCount": 0,
            "visibleCount": 0,
            "disabledCount": 0,
            "blockedCount": 0,
            "devOnly": DEV_ONLY,
            "productionAllowed": PRODUCTION_ALLOWED,
            "pluginRuntimeImplemented": PLUGIN_RUNTIME_IMPLEMENTED,
            "pluginLoaderImplemented": PLUGIN_LOADER_IMPLEMENTED,
            "dynamicLoadingAllowed": DYNAMIC_LOADING_ALLOWED,
            "localPluginDirectoryLoadingAllowed": LOCAL_PLUGIN_DIRECTORY_LOADING_ALLOWED,
            "remoteRegistryAllowed": REMOTE_REGISTRY_ALLOWED,
            "marketplaceAllowed": MARKETPLACE_ALLOWED,
            "externalPluginFetchAllowed": EXTERNAL_PLUGIN_FETCH_ALLOWED,
            "providerGeneratedPluginAllowed": PROVIDER_GENERATED_PLUGIN_ALLOWED,
            "llmGeneratedPluginInstallAllowed": LLM_GENERATED_PLUGIN_INSTALL_ALLOWED,
            "pluginExecutionAllowed": PLUGIN_EXECUTION_ALLOWED,
            "newRouteIntroduced": NEW_ROUTE_INTRODUCED,
            "routeGovernanceExpected": ROUTE_GOVERNANCE_EXPECTED,
            "validation": {"valid": False, "errorCount": 1, "warningCount": 0},
            "redactionApplied": True,
        }


def assert_no_plugin_runtime() -> None:
    """Re-affirm the no-plugin-runtime invariants.

    A pure assertion helper (no side effects). Raises :class:`AssertionError`
    if any frozen flag drifted. Used by tests + the no-runtime audit breadcrumb.
    """
    assert PLUGIN_RUNTIME_IMPLEMENTED is False
    assert PLUGIN_LOADER_IMPLEMENTED is False
    assert DYNAMIC_LOADING_ALLOWED is False
    assert LOCAL_PLUGIN_DIRECTORY_LOADING_ALLOWED is False
    assert REMOTE_REGISTRY_ALLOWED is False
    assert MARKETPLACE_ALLOWED is False
    assert EXTERNAL_PLUGIN_FETCH_ALLOWED is False
    assert PROVIDER_GENERATED_PLUGIN_ALLOWED is False
    assert LLM_GENERATED_PLUGIN_INSTALL_ALLOWED is False
    assert PLUGIN_EXECUTION_ALLOWED is False
    assert NEW_ROUTE_INTRODUCED is False
    assert DEV_ONLY is True
    assert PRODUCTION_ALLOWED is False


__all__ = [
    "ROUTE_GOVERNANCE_EXPECTED",
    "PLUGIN_RUNTIME_IMPLEMENTED",
    "PLUGIN_LOADER_IMPLEMENTED",
    "DYNAMIC_LOADING_ALLOWED",
    "LOCAL_PLUGIN_DIRECTORY_LOADING_ALLOWED",
    "REMOTE_REGISTRY_ALLOWED",
    "MARKETPLACE_ALLOWED",
    "EXTERNAL_PLUGIN_FETCH_ALLOWED",
    "PROVIDER_GENERATED_PLUGIN_ALLOWED",
    "LLM_GENERATED_PLUGIN_INSTALL_ALLOWED",
    "PLUGIN_EXECUTION_ALLOWED",
    "NEW_ROUTE_INTRODUCED",
    "DEV_ONLY",
    "PRODUCTION_ALLOWED",
    "DETAIL_FIELDS",
    "SCALAR_STRING_FIELDS",
    "LIST_STRING_FIELDS",
    "validate_manifest",
    "list_descriptor_details",
    "get_descriptor_detail",
    "build_registry_summary",
    "get_plugin_descriptor_status_block",
    "assert_no_plugin_runtime",
]
