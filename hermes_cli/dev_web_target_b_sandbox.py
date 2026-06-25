"""Phase 4B — Target B sandbox broker layer (pure stdlib, fail-closed).

Layer 6 of the Phase 4B Target B engineering path. Defines the **sandbox
broker** interface, the **sandbox profile**, the **execution limits**, and the
**execution request/result** models.

The broker is **disabled by default**: ``broker_enabled=False``,
``execution_allowed=False``, ``process_spawn_allowed=False``,
``network_allowed=False``, ``filesystem_write_allowed=False``,
``secrets_allowed=False``. The broker **never** spawns a process, never opens a
shell, never touches Docker, never imports a plugin, and never performs a real
sandboxed execution. Every execution request returns a denied result.

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
    TARGET_B_NO_GO,
    TARGET_B_SANDBOX_DISABLED_REASON,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
)

# ---------------------------------------------------------------------------
# 1. Frozen sandbox profile + limits
# ---------------------------------------------------------------------------

#: Sandbox profile identifiers. The only profile is a *design-only* preview —
#: never an enforced production sandbox.
SANDBOX_PROFILE_DESIGN_ONLY: str = "design-only-preview"
SANDBOX_PROFILE_DISABLED: str = "disabled"

#: The frozen default sandbox profile.
DEFAULT_SANDBOX_PROFILE: str = SANDBOX_PROFILE_DISABLED


@dataclass(frozen=True, slots=True)
class SandboxLimits:
    """The frozen resource / capability limits a sandbox profile would enforce.

    Every limit is frozen at its most restrictive value (zero / False). The
    broker never enforces them — there is no sandbox process — but they document
    the intended boundary.
    """

    max_cpu_seconds: int
    max_memory_mb: int
    max_wall_seconds: int
    max_filesystem_read_bytes: int
    max_filesystem_write_bytes: int
    network_egress_allowed: bool
    process_spawn_allowed: bool
    secrets_allowed: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "maxCpuSeconds": self.max_cpu_seconds,
                "maxMemoryMb": self.max_memory_mb,
                "maxWallSeconds": self.max_wall_seconds,
                "maxFilesystemReadBytes": self.max_filesystem_read_bytes,
                "maxFilesystemWriteBytes": self.max_filesystem_write_bytes,
                "networkEgressAllowed": self.network_egress_allowed,
                "processSpawnAllowed": self.process_spawn_allowed,
                "secretsAllowed": self.secrets_allowed,
            }
        )


#: The frozen sandbox limits — every limit at its most restrictive value.
SANDBOX_LIMITS: SandboxLimits = SandboxLimits(
    max_cpu_seconds=0,
    max_memory_mb=0,
    max_wall_seconds=0,
    max_filesystem_read_bytes=0,
    max_filesystem_write_bytes=0,
    network_egress_allowed=False,
    process_spawn_allowed=False,
    secrets_allowed=False,
)


@dataclass(frozen=True, slots=True)
class SandboxProfile:
    """The frozen sandbox profile. Design-only / never enforced."""

    profile_id: str
    enabled: bool
    enforced: bool
    limits: SandboxLimits

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "profileId": self.profile_id,
                "enabled": self.enabled,
                "enforced": self.enforced,
                "limits": self.limits.to_safe_dict(),
            }
        )


def build_sandbox_profile() -> SandboxProfile:
    """Build the frozen, disabled sandbox profile."""
    return SandboxProfile(
        profile_id=SANDBOX_PROFILE_DESIGN_ONLY,
        enabled=False,
        enforced=False,
        limits=SandboxLimits(
            max_cpu_seconds=SANDBOX_LIMITS.max_cpu_seconds,
            max_memory_mb=SANDBOX_LIMITS.max_memory_mb,
            max_wall_seconds=SANDBOX_LIMITS.max_wall_seconds,
            max_filesystem_read_bytes=SANDBOX_LIMITS.max_filesystem_read_bytes,
            max_filesystem_write_bytes=SANDBOX_LIMITS.max_filesystem_write_bytes,
            network_egress_allowed=SANDBOX_LIMITS.network_egress_allowed,
            process_spawn_allowed=SANDBOX_LIMITS.process_spawn_allowed,
            secrets_allowed=SANDBOX_LIMITS.secrets_allowed,
        ),
    )


# ---------------------------------------------------------------------------
# 2. Execution request / result + the broker status
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SandboxExecutionRequest:
    """A sandbox execution request. Carries untrusted metadata only.

    No field is ever executed — the broker is disabled.
    """

    package_id: str
    entrypoint: str
    sandbox_profile: str
    untrusted_metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class SandboxExecutionResult:
    """The frozen result of a sandbox execution request. Always denied."""

    executed: bool
    allowed: bool
    process_spawned: bool
    network_used: bool
    filesystem_written: bool
    secrets_read: bool
    reason: str
    production_authorization: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "executed": self.executed,
                "allowed": self.allowed,
                "processSpawned": self.process_spawned,
                "networkUsed": self.network_used,
                "filesystemWritten": self.filesystem_written,
                "secretsRead": self.secrets_read,
                "reason": self.reason,
                "productionAuthorization": self.production_authorization,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


@dataclass(frozen=True, slots=True)
class SandboxBrokerStatus:
    """The frozen sandbox broker status. Disabled by default."""

    broker_enabled: bool
    execution_allowed: bool
    process_spawn_allowed: bool
    network_allowed: bool
    filesystem_write_allowed: bool
    secrets_allowed: bool
    profile: SandboxProfile

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "brokerEnabled": self.broker_enabled,
                "executionAllowed": self.execution_allowed,
                "processSpawnAllowed": self.process_spawn_allowed,
                "networkAllowed": self.network_allowed,
                "filesystemWriteAllowed": self.filesystem_write_allowed,
                "secretsAllowed": self.secrets_allowed,
                "profile": self.profile.to_safe_dict(),
            }
        )


def build_sandbox_broker_status() -> SandboxBrokerStatus:
    """Build the frozen, disabled sandbox broker status."""
    profile = build_sandbox_profile()
    return SandboxBrokerStatus(
        broker_enabled=False,
        execution_allowed=False,
        process_spawn_allowed=False,
        network_allowed=False,
        filesystem_write_allowed=False,
        secrets_allowed=False,
        profile=profile,
    )


def validate_sandbox_request(request: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate a sandbox request's *shape*. Never executes it.

    Returns ``(shape_ok, reasons)``. A request must be a
    :class:`SandboxExecutionRequest` with a non-empty package id and entrypoint.
    Shape validity **never** authorizes execution.
    """
    if not isinstance(request, SandboxExecutionRequest):
        return False, ("request_not_a_sandbox_execution_request",)
    reasons: list[str] = []
    if not isinstance(request.package_id, str) or not request.package_id.strip():
        reasons.append("package_id_missing")
    if not isinstance(request.entrypoint, str) or not request.entrypoint.strip():
        reasons.append("entrypoint_missing")
    return not reasons, tuple(reasons)


def deny_sandbox_execution(untrusted_metadata: Any = None) -> SandboxExecutionResult:
    """Deny a sandbox execution request. Always executed=False, allowed=False.

    No process is spawned, no network is opened, no filesystem write occurs, and
    no secret is read. *untrusted_metadata* is inspected only to report ignored
    keys.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    return SandboxExecutionResult(
        executed=False,
        allowed=False,
        process_spawned=False,
        network_used=False,
        filesystem_written=False,
        secrets_read=False,
        reason=TARGET_B_SANDBOX_DISABLED_REASON,
        production_authorization=TARGET_B_NO_GO,
        ignored_metadata_keys=ignored,
    )


def evaluate_sandbox_readiness() -> tuple[bool, tuple[str, ...]]:
    """Evaluate whether the sandbox broker is ready for production execution.

    Returns ``(ready, reasons)``. Always ``(False, reasons)`` — the broker is
    design-only, no worker lifecycle is approved, no production sandbox exists.
    """
    profile = build_sandbox_profile()
    reasons: list[str] = []
    if not profile.enabled:
        reasons.append("profile_not_enabled")
    if not profile.enforced:
        reasons.append("profile_not_enforced")
    if profile.limits.process_spawn_allowed:
        reasons.append("process_spawn_unexpectedly_allowed")
    if profile.limits.network_egress_allowed:
        reasons.append("network_unexpectedly_allowed")
    reasons.append("no_approved_worker_lifecycle")
    return False, tuple(reasons)


@dataclass(frozen=True, slots=True)
class SandboxBrokerReport:
    """The frozen aggregate sandbox-broker readiness report."""

    broker_enabled: bool
    execution_allowed: bool
    process_spawn_allowed: bool
    network_allowed: bool
    filesystem_write_allowed: bool
    secrets_allowed: bool
    production_authorization: str
    profile: SandboxProfile

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "brokerEnabled": self.broker_enabled,
                "executionAllowed": self.execution_allowed,
                "processSpawnAllowed": self.process_spawn_allowed,
                "networkAllowed": self.network_allowed,
                "filesystemWriteAllowed": self.filesystem_write_allowed,
                "secretsAllowed": self.secrets_allowed,
                "productionAuthorization": self.production_authorization,
                "profile": self.profile.to_safe_dict(),
            }
        )


def build_sandbox_broker_report() -> SandboxBrokerReport:
    """Build the frozen aggregate sandbox-broker report. Pure / deterministic."""
    status = build_sandbox_broker_status()
    return SandboxBrokerReport(
        broker_enabled=status.broker_enabled,
        execution_allowed=status.execution_allowed,
        process_spawn_allowed=status.process_spawn_allowed,
        network_allowed=status.network_allowed,
        filesystem_write_allowed=status.filesystem_write_allowed,
        secrets_allowed=status.secrets_allowed,
        production_authorization=TARGET_B_NO_GO,
        profile=status.profile,
    )


def assert_sandbox_layer_disabled() -> None:
    """Re-affirm the sandbox layer disabled invariants. Pure."""
    status = build_sandbox_broker_status()
    assert status.broker_enabled is False
    assert status.execution_allowed is False
    assert status.process_spawn_allowed is False
    assert status.network_allowed is False
    assert status.filesystem_write_allowed is False
    assert status.secrets_allowed is False
    ready, _reasons = evaluate_sandbox_readiness()
    assert ready is False
    report = build_sandbox_broker_report()
    assert report.broker_enabled is False
    assert report.production_authorization == TARGET_B_NO_GO


__all__ = [
    # profiles / limits
    "SANDBOX_PROFILE_DESIGN_ONLY",
    "SANDBOX_PROFILE_DISABLED",
    "DEFAULT_SANDBOX_PROFILE",
    "SandboxLimits",
    "SANDBOX_LIMITS",
    "SandboxProfile",
    "build_sandbox_profile",
    # request / result / status
    "SandboxExecutionRequest",
    "SandboxExecutionResult",
    "SandboxBrokerStatus",
    "build_sandbox_broker_status",
    "validate_sandbox_request",
    "deny_sandbox_execution",
    "evaluate_sandbox_readiness",
    # report
    "SandboxBrokerReport",
    "build_sandbox_broker_report",
    # boundary
    "assert_sandbox_layer_disabled",
]
