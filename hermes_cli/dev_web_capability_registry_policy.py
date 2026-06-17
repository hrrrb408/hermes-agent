"""Phase 3C Capability Registry — Policy (composition / consistency checks).

Enforces the **frozen composition rules** between ``permissionClass``,
``trustLevel``, ``status``, and the runtime gate flags. These checks confirm
that the registry only *describes* capabilities — it never grants execution.

A capability may be ``enabled`` only when, per the frozen taxonomy:

  - ``trustLevel ∈ {BUILTIN_VERIFIED, DEV_STATIC_MANIFEST}`` **and**
  - ``permissionClass ∈ {READ_ONLY, WRITE_PREVIEW, WRITE_CONFIRM,
    ROLLBACK_CONFIRM, LIVE_PROVIDER_GATED}`` **and**
  - every runtime gate it declares holds.

A capability with a forbidden trust / permission class is always ``disabled``
or ``blocked``. ``EXPERIMENTAL_DISABLED`` capabilities are always ``disabled``
or ``planned``. No first-version capability has ``productionAllowed = True``.

Additional gate-coherence rules:
  - ``WRITE_CONFIRM`` requires ``requiresDryRun`` + ``requiresConfirmation``
    + ``requiresAudit``.
  - ``ROLLBACK_CONFIRM`` requires ``requiresConfirmation`` + ``requiresAudit``.
  - ``LIVE_PROVIDER_GATED`` requires ``requiresApproval`` + ``requiresBudget``
    + ``requiresKillSwitch`` + ``requiresAudit``.
  - ``READ_ONLY`` must not declare ``confirmed_execute`` / ``manual_live``
    execution (a read-only capability cannot require a write execution gate).

This module is stdlib-only and has no side effects.

Phase: 3C — Static dev-only Capability Registry
Status: implemented
"""

from __future__ import annotations

from typing import Any

from hermes_cli.dev_web_capability_registry_schema import (
    CapabilityValidationError,
    FORBIDDEN_PERMISSION_CLASSES,
    FORBIDDEN_TRUST_LEVELS,
    is_terminal_forbidden,
)


def _err(entry: dict[str, Any], field_name: str, reason: str) -> CapabilityValidationError:
    return CapabilityValidationError(
        capability_id=str(entry.get("capabilityId", "<unknown>")),
        field=field_name,
        reason=reason,
    )


def check_capability_policy(entry: dict[str, Any]) -> list[CapabilityValidationError]:
    """Return policy violations for a single manifest entry.

    Pure / deterministic. Never raises. The caller (registry loader) aggregates
    these into a :class:`ValidationReport`.
    """
    if not isinstance(entry, dict):
        return [CapabilityValidationError("<unknown>", "entry", "entry is not a dict")]

    cid = str(entry.get("capabilityId", "<unknown>"))
    errors: list[CapabilityValidationError] = []

    permission_class = entry.get("permissionClass")
    trust_level = entry.get("trustLevel")
    status = entry.get("status")

    # ── Forbidden trust / permission classes must be non-executable ───────
    if isinstance(permission_class, str) and permission_class in FORBIDDEN_PERMISSION_CLASSES:
        if status not in ("disabled", "blocked"):
            errors.append(
                _err(entry, "status", f"permissionClass={permission_class} must be disabled or blocked")
            )
    if isinstance(trust_level, str) and trust_level in FORBIDDEN_TRUST_LEVELS:
        if status not in ("disabled", "blocked"):
            errors.append(
                _err(entry, "status", f"trustLevel={trust_level} must be disabled or blocked")
            )
    if trust_level == "EXPERIMENTAL_DISABLED":
        if status not in ("disabled", "planned", "blocked"):
            errors.append(
                _err(entry, "status", "trustLevel=EXPERIMENTAL_DISABLED must be disabled/planned/blocked")
            )

    # ── Enabled only for the verified/dev trust + non-forbidden class ─────
    if status == "enabled":
        if trust_level not in ("BUILTIN_VERIFIED", "DEV_STATIC_MANIFEST"):
            errors.append(
                _err(entry, "trustLevel", f"status=enabled requires a verified trust level (got {trust_level})")
            )
        if isinstance(permission_class, str) and is_terminal_forbidden(permission_class):
            errors.append(
                _err(entry, "permissionClass", f"status=enabled cannot use forbidden class {permission_class}")
            )

    # ── productionAllowed must be False in the first version ──────────────
    if entry.get("productionAllowed") is True:
        errors.append(_err(entry, "productionAllowed", "must be false in the first version"))

    # ── devOnly must be True in the first version ─────────────────────────
    if entry.get("devOnly") is not True:
        errors.append(_err(entry, "devOnly", "must be true in the first version"))

    # ── blocked capabilities must carry a blockedReason ───────────────────
    if status == "blocked" and not entry.get("blockedReason"):
        errors.append(_err(entry, "blockedReason", "status=blocked requires a blockedReason"))

    # ── Gate-coherence rules ──────────────────────────────────────────────
    if permission_class == "WRITE_CONFIRM":
        if entry.get("requiresDryRun") is not True:
            errors.append(_err(entry, "requiresDryRun", "WRITE_CONFIRM requires a dry-run gate"))
        if entry.get("requiresConfirmation") is not True:
            errors.append(_err(entry, "requiresConfirmation", "WRITE_CONFIRM requires a confirmation gate"))
        if entry.get("requiresAudit") is not True:
            errors.append(_err(entry, "requiresAudit", "WRITE_CONFIRM requires an audit gate"))

    if permission_class == "ROLLBACK_CONFIRM":
        if entry.get("requiresConfirmation") is not True:
            errors.append(_err(entry, "requiresConfirmation", "ROLLBACK_CONFIRM requires a confirmation gate"))
        if entry.get("requiresAudit") is not True:
            errors.append(_err(entry, "requiresAudit", "ROLLBACK_CONFIRM requires an audit gate"))

    if permission_class == "LIVE_PROVIDER_GATED":
        if entry.get("requiresApproval") is not True:
            errors.append(_err(entry, "requiresApproval", "LIVE_PROVIDER_GATED requires an approval gate"))
        if entry.get("requiresBudget") is not True:
            errors.append(_err(entry, "requiresBudget", "LIVE_PROVIDER_GATED requires a budget gate"))
        if entry.get("requiresKillSwitch") is not True:
            errors.append(_err(entry, "requiresKillSwitch", "LIVE_PROVIDER_GATED requires a kill-switch gate"))
        if entry.get("requiresAudit") is not True:
            errors.append(_err(entry, "requiresAudit", "LIVE_PROVIDER_GATED requires an audit gate"))

    # ── READ_ONLY must not declare a write execution gate ─────────────────
    if permission_class == "READ_ONLY":
        execution_mode = entry.get("executionMode")
        if execution_mode in ("confirmed_execute", "manual_live"):
            errors.append(
                _err(entry, "executionMode", f"READ_ONLY cannot use executionMode={execution_mode}")
            )

    return errors


__all__ = ["check_capability_policy"]
