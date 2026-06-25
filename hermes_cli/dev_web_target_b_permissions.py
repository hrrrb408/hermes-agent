"""Phase 4B — Target B permission / capability model (pure stdlib, fail-closed).

Layer 4 of the Phase 4B Target B engineering path. Defines the **plugin
permission model** (15 permissions) and the **capability declaration model**.

Every permission is **denied by default** — ``DENIED_BY_DEFAULT``. None is
granted, no matter what renders or what untrusted metadata a request carries.
Dangerous permissions (filesystem.write, network.*, secrets.read,
provider.write, database.write, process.spawn, runtime.execute, plugin.install,
marketplace.fetch) are denied unconditionally. ``ui.render`` is a future
display-only capability that **cannot execute**; ``tool.invoke`` is denied
unless a dev-fixture mode flag (also denied here) is set.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no real secret read, no production access.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_target_b_common import (
    TARGET_B_PERMISSION_DENIED,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
)

# ---------------------------------------------------------------------------
# 1. Frozen permission taxonomy (15 permissions — every one denied by default)
# ---------------------------------------------------------------------------

#: The permission taxonomy: ``(key, label, risk)``. Risk is documentation only;
#: it never grants the permission.
_PERMISSION_TAXONOMY: tuple[tuple[str, str, str], ...] = (
    ("filesystem.read", "Filesystem read", "high"),
    ("filesystem.write", "Filesystem write", "critical"),
    ("network.http", "Network HTTP", "critical"),
    ("network.registry", "Network registry", "critical"),
    ("secrets.read", "Secrets read", "critical"),
    ("provider.read", "Provider read", "medium"),
    ("provider.write", "Provider write", "critical"),
    ("ui.render", "UI render (display only)", "medium"),
    ("tool.invoke", "Tool invoke", "critical"),
    ("database.read", "Database read", "high"),
    ("database.write", "Database write", "critical"),
    ("process.spawn", "Process spawn", "critical"),
    ("runtime.execute", "Runtime execute", "critical"),
    ("plugin.install", "Plugin install", "critical"),
    ("marketplace.fetch", "Marketplace fetch", "critical"),
)

#: Permissions that are dangerous and denied unconditionally (never grantable
#: in the dev skeleton, no matter what).
_DANGEROUS_PERMISSIONS: frozenset[str] = frozenset(
    {
        "filesystem.write",
        "network.http",
        "network.registry",
        "secrets.read",
        "provider.write",
        "tool.invoke",
        "database.write",
        "process.spawn",
        "runtime.execute",
        "plugin.install",
        "marketplace.fetch",
    }
)

#: Read-only permissions that *could* be conceptually granted in a future
#: hardened runtime — but stay denied by default here.
_READ_ONLY_PERMISSIONS: frozenset[str] = frozenset(
    {
        "filesystem.read",
        "provider.read",
        "database.read",
    }
)

#: Display-only capability permissions — never executable.
_DISPLAY_PERMISSIONS: frozenset[str] = frozenset({"ui.render"})

#: All known permission keys.
PERMISSION_KEYS: tuple[str, ...] = tuple(row[0] for row in _PERMISSION_TAXONOMY)
_PERMISSION_KEY_SET: frozenset[str] = frozenset(PERMISSION_KEYS)


@dataclass(frozen=True, slots=True)
class PermissionEntry:
    """One permission in the plugin permission model — always denied."""

    key: str
    label: str
    risk: str
    current_status: str
    grantable: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "key": self.key,
                "label": self.label,
                "risk": self.risk,
                "currentStatus": self.current_status,
                "grantable": self.grantable,
            }
        )


def _build_permission_entries() -> tuple[PermissionEntry, ...]:
    return tuple(
        PermissionEntry(
            key=key,
            label=label,
            risk=risk,
            current_status=TARGET_B_PERMISSION_DENIED,
            # No permission is grantable in the dev skeleton.
            grantable=False,
        )
        for key, label, risk in _PERMISSION_TAXONOMY
    )


#: The frozen permission model. Immutable; every permission denied by default.
PERMISSION_MODEL: tuple[PermissionEntry, ...] = _build_permission_entries()

assert len(PERMISSION_MODEL) == 15, "permission model must contain exactly 15 permissions"
assert all(p.current_status == TARGET_B_PERMISSION_DENIED for p in PERMISSION_MODEL)
assert all(p.grantable is False for p in PERMISSION_MODEL)


# ---------------------------------------------------------------------------
# 2. Frozen capability declaration model (metadata only — grants nothing)
# ---------------------------------------------------------------------------

#: The capability declaration taxonomy: ``(key, label, executable)``. Every
#: capability is non-executable metadata.
_CAPABILITY_TAXONOMY: tuple[tuple[str, str, bool], ...] = (
    ("display.surface", "Display surface", False),
    ("display.toolbar", "Display toolbar", False),
    ("display.status", "Display status", False),
    ("read.descriptor", "Read descriptor", False),
    ("read.capability", "Read capability", False),
    ("event.emit.readonly", "Emit read-only event", False),
)

CAPABILITY_KEYS: tuple[str, ...] = tuple(row[0] for row in _CAPABILITY_TAXONOMY)
_CAPABILITY_KEY_SET: frozenset[str] = frozenset(CAPABILITY_KEYS)


@dataclass(frozen=True, slots=True)
class CapabilityEntry:
    """One capability declaration — metadata only, never executable."""

    key: str
    label: str
    executable: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "key": self.key,
                "label": self.label,
                "executable": self.executable,
            }
        )


def _build_capability_entries() -> tuple[CapabilityEntry, ...]:
    return tuple(
        CapabilityEntry(key=key, label=label, executable=executable)
        for key, label, executable in _CAPABILITY_TAXONOMY
    )


#: The frozen capability model. Immutable; every capability non-executable.
CAPABILITY_MODEL: tuple[CapabilityEntry, ...] = _build_capability_entries()

assert len(CAPABILITY_MODEL) == 6
assert all(not c.executable for c in CAPABILITY_MODEL)


# ---------------------------------------------------------------------------
# 3. Permission / capability request evaluation (deny by default)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    """The frozen result of a permission request. Always denied."""

    permission: str
    granted: bool
    current_status: str
    reason: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "permission": self.permission,
                "granted": self.granted,
                "currentStatus": self.current_status,
                "reason": self.reason,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


@dataclass(frozen=True, slots=True)
class CapabilityDecision:
    """The frozen result of a capability declaration evaluation."""

    capability: str
    recognized: bool
    executable: bool
    granted: bool
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "capability": self.capability,
                "recognized": self.recognized,
                "executable": self.executable,
                "granted": self.granted,
                "reason": self.reason,
            }
        )


def evaluate_permission_request(
    permission: Any,
    untrusted_metadata: Any = None,
    *,
    dev_fixture_mode: bool = False,
) -> PermissionDecision:
    """Evaluate a permission request. Always denied.

    Dangerous permissions are denied unconditionally. Read-only / display
    permissions are denied by default and only a future, hardened runtime with
    a real policy could grant them — and even then, only when
    ``dev_fixture_mode`` is True for the single ``tool.invoke`` permission under
    a reviewed fixture allowlist. In the dev skeleton, ``dev_fixture_mode`` is
    always passed False, so every request is denied.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    if not isinstance(permission, str) or permission not in _PERMISSION_KEY_SET:
        return PermissionDecision(
            permission=permission if isinstance(permission, str) else "<invalid>",
            granted=False,
            current_status=TARGET_B_PERMISSION_DENIED,
            reason="permission_unknown",
            ignored_metadata_keys=ignored,
        )
    # tool.invoke is the only permission with a (still-disabled) dev-fixture
    # path. Even with dev_fixture_mode=True it is NOT granted here — granting
    # requires the fixture runtime, not this model. We record the intent.
    if permission == "tool.invoke" and dev_fixture_mode:
        return PermissionDecision(
            permission=permission,
            granted=False,  # fixture mode is not an authorization
            current_status=TARGET_B_PERMISSION_DENIED,
            reason="tool_invoke_fixture_mode_not_authorized",
            ignored_metadata_keys=ignored,
        )
    if permission in _DANGEROUS_PERMISSIONS:
        return PermissionDecision(
            permission=permission,
            granted=False,
            current_status=TARGET_B_PERMISSION_DENIED,
            reason="dangerous_permission_denied",
            ignored_metadata_keys=ignored,
        )
    if permission in _DISPLAY_PERMISSIONS:
        return PermissionDecision(
            permission=permission,
            granted=False,
            current_status=TARGET_B_PERMISSION_DENIED,
            reason="display_only_capability_not_executable",
            ignored_metadata_keys=ignored,
        )
    return PermissionDecision(
        permission=permission,
        granted=False,
        current_status=TARGET_B_PERMISSION_DENIED,
        reason="read_permission_denied_by_default",
        ignored_metadata_keys=ignored,
    )


def deny_disallowed_permissions(declared: Any) -> tuple[str, ...]:
    """Return the disallowed permissions in *declared*.

    Any permission outside the taxonomy, or any dangerous permission, is
    reported as disallowed. Pure inspection — never grants anything.
    """
    if not isinstance(declared, (list, tuple)):
        return ()
    disallowed: list[str] = []
    for p in declared:
        if not isinstance(p, str) or p not in _PERMISSION_KEY_SET:
            disallowed.append(p if isinstance(p, str) else "<invalid>")
        elif p in _DANGEROUS_PERMISSIONS:
            disallowed.append(p)
    return tuple(disallowed)


def build_permission_matrix() -> tuple[PermissionEntry, ...]:
    """Return a defensive copy of the frozen permission matrix."""
    return tuple(
        PermissionEntry(
            key=p.key,
            label=p.label,
            risk=p.risk,
            current_status=p.current_status,
            grantable=p.grantable,
        )
        for p in PERMISSION_MODEL
    )


def evaluate_capability_declaration(capability: Any) -> CapabilityDecision:
    """Evaluate a capability declaration. Metadata only — never executable."""
    if not isinstance(capability, str) or capability not in _CAPABILITY_KEY_SET:
        return CapabilityDecision(
            capability=capability if isinstance(capability, str) else "<invalid>",
            recognized=False,
            executable=False,
            granted=False,
            reason="capability_unknown",
        )
    entry = next(c for c in CAPABILITY_MODEL if c.key == capability)
    return CapabilityDecision(
        capability=capability,
        recognized=True,
        executable=entry.executable,  # always False
        granted=False,
        reason="capability_metadata_only_not_executable",
    )


@dataclass(frozen=True, slots=True)
class PermissionModelReport:
    """The frozen aggregate permission-model readiness report."""

    default_disposition: str
    any_granted: bool
    dangerous_permissions_denied: bool
    permission_count: int
    capability_count: int

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "defaultDisposition": self.default_disposition,
                "anyGranted": self.any_granted,
                "dangerousPermissionsDenied": self.dangerous_permissions_denied,
                "permissionCount": self.permission_count,
                "capabilityCount": self.capability_count,
            }
        )


def build_permission_model_report() -> PermissionModelReport:
    """Build the frozen aggregate permission-model report. Pure / deterministic."""
    return PermissionModelReport(
        default_disposition=TARGET_B_PERMISSION_DENIED,
        any_granted=False,
        dangerous_permissions_denied=True,
        permission_count=len(PERMISSION_MODEL),
        capability_count=len(CAPABILITY_MODEL),
    )


def assert_permission_layer_disabled() -> None:
    """Re-affirm the permission layer disabled invariants. Pure."""
    assert len(PERMISSION_MODEL) == 15
    for p in PERMISSION_MODEL:
        assert p.current_status == TARGET_B_PERMISSION_DENIED
        assert p.grantable is False
    for perm in PERMISSION_KEYS:
        decision = evaluate_permission_request(perm)
        assert decision.granted is False
    report = build_permission_model_report()
    assert report.any_granted is False
    assert report.dangerous_permissions_denied is True


__all__ = [
    # taxonomy
    "PERMISSION_KEYS",
    "CAPABILITY_KEYS",
    "PERMISSION_MODEL",
    "CAPABILITY_MODEL",
    # models
    "PermissionEntry",
    "CapabilityEntry",
    "PermissionDecision",
    "CapabilityDecision",
    "PermissionModelReport",
    # evaluation
    "evaluate_permission_request",
    "deny_disallowed_permissions",
    "build_permission_matrix",
    "evaluate_capability_declaration",
    "build_permission_model_report",
    # boundary
    "assert_permission_layer_disabled",
]
