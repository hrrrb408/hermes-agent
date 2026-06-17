"""Phase 3C Capability Registry — loader, validation, read model.

Loads the static manifest (:mod:`hermes_cli.dev_web_capability_registry_manifest`),
validates it against the frozen schema + policy, and exposes a **read-only**
registry summary + per-capability safe records.

Hard guarantees (frozen):

  - The registry **describes** capabilities; it never authorizes execution.
  - No dynamic loading. No ``importlib`` / path-based load / remote fetch /
    marketplace. The loader only reads the static, in-process manifest.
  - Validation fails closed: if the manifest is invalid, the registry status
    is ``validation_failed`` and invalid entries are blocked (never exposed as
    enabled).
  - The read model never returns a forbidden field (API key, Authorization,
    Bearer, secret, callable repr, shell command, SQL statement, production
    path, local plugin path, dynamic import path, external URL).
  - Frozen policy flags are constant: ``devOnly = True``,
    ``productionAllowed = False``, ``dynamicLoadingAllowed = False``,
    ``remoteRegistryAllowed = False``, ``marketplaceAllowed = False``,
    ``redactionApplied = True``.

This module is stdlib-only and has no side effects on import.

Phase: 3C — Static dev-only Capability Registry
Status: implemented
"""

from __future__ import annotations

from typing import Any

from hermes_cli.dev_web_capability_registry_manifest import (
    MANIFEST_VERSION,
    get_static_manifest,
)
from hermes_cli.dev_web_capability_registry_policy import check_capability_policy
from hermes_cli.dev_web_capability_registry_schema import (
    ALLOWED_FIELDS,
    CapabilityValidationError,
    FORBIDDEN_FIELDS,
    REQUIRED_FIELDS,
    ValidationReport,
    is_forbidden_field_present,
    is_valid_bool,
    is_valid_capability_id,
    is_valid_category,
    is_valid_execution_mode,
    is_valid_permission_class,
    is_valid_route_exposure,
    is_valid_source,
    is_valid_status,
    is_valid_trust_level,
)

#: Frozen route-governance baseline surfaced by the registry summary.
ROUTE_GOVERNANCE_EXPECTED = "34/34/5/0/1/1"

#: Frozen policy flags for the first version. These are constants, not state.
DYNAMIC_LOADING_ALLOWED: bool = False
REMOTE_REGISTRY_ALLOWED: bool = False
MARKETPLACE_ALLOWED: bool = False
DEV_ONLY: bool = True
PRODUCTION_ALLOWED: bool = False

#: The fields the read model exposes for a capability detail.
DETAIL_FIELDS: tuple[str, ...] = (
    "capabilityId",
    "displayName",
    "description",
    "category",
    "status",
    "permissionClass",
    "trustLevel",
    "executionMode",
    "routeExposure",
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
    "toolBinding",
    "providerBinding",
    "workflowBinding",
    "auditEventPrefix",
    "metadataSchema",
)


# ---------------------------------------------------------------------------
# 1. Validation
# ---------------------------------------------------------------------------


def _validate_entry(entry: Any) -> list[CapabilityValidationError]:
    """Validate a single manifest entry (schema + policy). Never raises."""
    if not isinstance(entry, dict):
        return [CapabilityValidationError("<unknown>", "entry", "entry is not a dict")]

    cid = str(entry.get("capabilityId", "<unknown>"))
    errors: list[CapabilityValidationError] = []

    def _err(field_name: str, reason: str) -> None:
        errors.append(CapabilityValidationError(cid, field_name, reason))

    # Forbidden fields → reject the entry outright (fail closed).
    forbidden = is_forbidden_field_present(entry)
    if forbidden is not None:
        _err(forbidden, f"forbidden field present: {forbidden}")
        return errors

    # Required fields.
    for required in REQUIRED_FIELDS:
        if required not in entry or entry[required] is None:
            _err(required, f"missing required field: {required}")

    # capabilityId format + stability.
    if "capabilityId" in entry and not is_valid_capability_id(entry["capabilityId"]):
        _err("capabilityId", "capabilityId must be a stable dot-delimited id")

    # Enum validity.
    if "category" in entry and not is_valid_category(entry["category"]):
        _err("category", "invalid category")
    if "status" in entry and not is_valid_status(entry["status"]):
        _err("status", "invalid status")
    if "permissionClass" in entry and not is_valid_permission_class(entry["permissionClass"]):
        _err("permissionClass", "invalid permissionClass")
    if "trustLevel" in entry and not is_valid_trust_level(entry["trustLevel"]):
        _err("trustLevel", "invalid trustLevel")
    if "executionMode" in entry and not is_valid_execution_mode(entry["executionMode"]):
        _err("executionMode", "invalid executionMode")
    if "routeExposure" in entry and not is_valid_route_exposure(entry["routeExposure"]):
        _err("routeExposure", "invalid routeExposure")
    if "source" in entry and not is_valid_source(entry["source"]):
        _err("source", "invalid source")

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

    # First-version invariants.
    if entry.get("devOnly") is not True:
        _err("devOnly", "devOnly must be true in the first version")
    if entry.get("productionAllowed") is True:
        _err("productionAllowed", "productionAllowed must be false in the first version")

    # blocked capabilities need a reason.
    if entry.get("status") == "blocked" and not entry.get("blockedReason"):
        _err("blockedReason", "status=blocked requires a blockedReason")

    # Unknown allowed-field whitelist: a manifest entry may only carry fields
    # from the allowed set (no extra keys that smuggle in an execution surface).
    for key in entry:
        if key not in ALLOWED_FIELDS:
            _err(key, f"unknown field: {key}")

    # Policy composition checks.
    errors.extend(check_capability_policy(entry))

    return errors


def validate_manifest(entries: Any) -> ValidationReport:
    """Validate a manifest (list/tuple of entries). Returns a report.

    Fail-closed semantics: ``valid`` is ``True`` only when every entry passes
    schema + policy + uniqueness.
    """
    errors: list[CapabilityValidationError] = []
    warnings: list[CapabilityValidationError] = []

    if not isinstance(entries, (list, tuple)):
        return ValidationReport(
            valid=False,
            error_count=1,
            errors=[CapabilityValidationError("<root>", "manifest", "manifest is not a list/tuple")],
        )

    seen_ids: dict[str, int] = {}
    permission_counts: dict[str, int] = {}
    trust_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    blocked_count = 0

    for entry in entries:
        entry_errors = _validate_entry(entry)
        errors.extend(entry_errors)

        if isinstance(entry, dict):
            cid = str(entry.get("capabilityId", ""))
            if cid:
                seen_ids[cid] = seen_ids.get(cid, 0) + 1
            pc = entry.get("permissionClass")
            if isinstance(pc, str):
                permission_counts[pc] = permission_counts.get(pc, 0) + 1
            tl = entry.get("trustLevel")
            if isinstance(tl, str):
                trust_counts[tl] = trust_counts.get(tl, 0) + 1
            cat = entry.get("category")
            if isinstance(cat, str):
                category_counts[cat] = category_counts.get(cat, 0) + 1
            st = entry.get("status")
            if isinstance(st, str):
                status_counts[st] = status_counts.get(st, 0) + 1
                if st == "blocked":
                    blocked_count += 1

    # capabilityId uniqueness.
    for cid, count in seen_ids.items():
        if count > 1:
            errors.append(
                CapabilityValidationError(cid, "capabilityId", f"duplicate capabilityId ({count} occurrences)")
            )

    return ValidationReport(
        valid=(len(errors) == 0),
        error_count=len(errors),
        warning_count=len(warnings),
        blocked_count=blocked_count,
        capability_count=len(entries) if isinstance(entries, (list, tuple)) else 0,
        permission_class_counts=permission_counts,
        trust_level_counts=trust_counts,
        category_counts=category_counts,
        status_counts=status_counts,
        errors=errors,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# 2. Read model
# ---------------------------------------------------------------------------


def _safe_detail(entry: dict[str, Any]) -> dict[str, Any]:
    """Build the safe read-only detail dict for a single capability.

    Only carries :data:`DETAIL_FIELDS`. A defensive second guard drops any
    forbidden field that slipped through (they can never be present after
    validation, but defense in depth).
    """
    detail: dict[str, Any] = {"redactionApplied": True}
    for field_name in DETAIL_FIELDS:
        if field_name in FORBIDDEN_FIELDS:
            continue
        if field_name in entry:
            detail[field_name] = entry[field_name]
    return detail


def list_capability_details(entries: Any) -> list[dict[str, Any]]:
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
                    "capabilityId": str(entry.get("capabilityId", "<blocked>")),
                    "status": "blocked",
                    "blockedReason": "forbidden_field_present_validation_failed",
                    "redactionApplied": True,
                }
            )
            continue
        details.append(_safe_detail(entry))
    return details


def get_capability_detail(entries: Any, capability_id: str) -> dict[str, Any] | None:
    """Return the safe detail for one ``capability_id``, or ``None`` if absent."""
    if not isinstance(capability_id, str) or not capability_id:
        return None
    if not isinstance(entries, (list, tuple)):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get("capabilityId") == capability_id:
            if is_forbidden_field_present(entry) is not None:
                return {
                    "capabilityId": capability_id,
                    "status": "blocked",
                    "blockedReason": "forbidden_field_present_validation_failed",
                    "redactionApplied": True,
                }
            return _safe_detail(entry)
    return None


def build_registry_summary(report: ValidationReport | None = None) -> dict[str, Any]:
    """Build the read-only registry summary surfaced under ``/status``.

    The summary is value-free: no secret, no path, no callable repr. Frozen
    policy flags are constants. ``report`` may be ``None`` (loads + validates
    the static manifest on demand).
    """
    if report is None:
        report = validate_manifest(get_static_manifest())

    enabled = report.status_counts.get("enabled", 0)
    disabled = report.status_counts.get("disabled", 0)
    blocked = report.status_counts.get("blocked", 0)
    planned = report.status_counts.get("planned", 0)
    deprecated = report.status_counts.get("deprecated", 0)

    if report.valid:
        registry_status = "enabled"
    else:
        # Fail closed: never expose an invalid registry as healthy/enabled.
        registry_status = "validation_failed"

    return {
        "status": registry_status,
        "registryVersion": MANIFEST_VERSION,
        "loaded": report.valid,
        "validationPassed": report.valid,
        "capabilityCount": report.capability_count,
        "enabledCount": enabled,
        "disabledCount": disabled,
        "blockedCount": blocked,
        "plannedCount": planned,
        "deprecatedCount": deprecated,
        "permissionClassCounts": dict(report.permission_class_counts),
        "trustLevelCounts": dict(report.trust_level_counts),
        "categoryCounts": dict(report.category_counts),
        "devOnly": DEV_ONLY,
        "productionAllowed": PRODUCTION_ALLOWED,
        "dynamicLoadingAllowed": DYNAMIC_LOADING_ALLOWED,
        "remoteRegistryAllowed": REMOTE_REGISTRY_ALLOWED,
        "marketplaceAllowed": MARKETPLACE_ALLOWED,
        "routeGovernanceExpected": ROUTE_GOVERNANCE_EXPECTED,
        "validation": {
            "valid": report.valid,
            "errorCount": report.error_count,
            "warningCount": report.warning_count,
        },
        "redactionApplied": True,
    }


def get_registry_status_block() -> dict[str, Any]:
    """Load + validate the static manifest and return the ``/status`` block.

    This is the single entry point used by the ``/status`` response. It never
    raises — a load/validation failure is surfaced as ``status=validation_failed``
    so ``/status`` itself never fails because of the registry.
    """
    try:
        report = validate_manifest(get_static_manifest())
        return build_registry_summary(report)
    except Exception:  # pragma: no cover — defensive; never fail /status
        return {
            "status": "validation_failed",
            "registryVersion": MANIFEST_VERSION,
            "loaded": False,
            "validationPassed": False,
            "capabilityCount": 0,
            "enabledCount": 0,
            "disabledCount": 0,
            "blockedCount": 0,
            "plannedCount": 0,
            "deprecatedCount": 0,
            "permissionClassCounts": {},
            "trustLevelCounts": {},
            "categoryCounts": {},
            "devOnly": DEV_ONLY,
            "productionAllowed": PRODUCTION_ALLOWED,
            "dynamicLoadingAllowed": DYNAMIC_LOADING_ALLOWED,
            "remoteRegistryAllowed": REMOTE_REGISTRY_ALLOWED,
            "marketplaceAllowed": MARKETPLACE_ALLOWED,
            "routeGovernanceExpected": ROUTE_GOVERNANCE_EXPECTED,
            "validation": {"valid": False, "errorCount": 1, "warningCount": 0},
            "redactionApplied": True,
        }


def assert_no_dynamic_loading() -> None:
    """Re-affirm the no-dynamic-loading invariants.

    A pure assertion helper (no side effects). Raises :class:`AssertionError`
    if any frozen flag drifted. Used by tests + the no-dynamic-loading audit
    breadcrumb.
    """
    assert DYNAMIC_LOADING_ALLOWED is False
    assert REMOTE_REGISTRY_ALLOWED is False
    assert MARKETPLACE_ALLOWED is False
    assert DEV_ONLY is True
    assert PRODUCTION_ALLOWED is False


__all__ = [
    "ROUTE_GOVERNANCE_EXPECTED",
    "DYNAMIC_LOADING_ALLOWED",
    "REMOTE_REGISTRY_ALLOWED",
    "MARKETPLACE_ALLOWED",
    "DEV_ONLY",
    "PRODUCTION_ALLOWED",
    "DETAIL_FIELDS",
    "validate_manifest",
    "list_capability_details",
    "get_capability_detail",
    "build_registry_summary",
    "get_registry_status_block",
    "assert_no_dynamic_loading",
]
