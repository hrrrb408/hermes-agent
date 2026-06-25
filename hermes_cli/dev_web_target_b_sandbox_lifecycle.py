"""Phase 4C — Target B sandbox worker lifecycle approval (pure stdlib, fail-closed).

Layer 5 of the Phase 4C Target B authorization package. Defines the **sandbox
worker lifecycle approval model**: the worker model, the start / stop / restart
policies, the resource limits, the filesystem / network / secret / logging /
crash / kill-switch policies, and the approval result that gates whether a
sandbox worker may be started for Target B.

The lifecycle is **not approved** by default. No worker is ever started, no
process is ever spawned, no Docker is ever run, no shell is ever executed, and
the production gateway is never touched. The approval result keeps:

  - ``lifecycle_approved = False``
  - ``worker_start_allowed = False``
  - ``process_spawn_allowed = False``
  - ``network_allowed = False``
  - ``filesystem_write_allowed = False``
  - ``secrets_allowed = False``

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no Docker, no shell, no dynamic import, no eval / exec, no production
access, and no production gateway interaction (PID 28428 is referenced only as a
do-not-touch target).

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_target_b_authorization_common import (
    TARGET_B_AUTHORIZATION_NO_GO,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
)

# ---------------------------------------------------------------------------
# 1. The sandbox lifecycle schema (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SandboxResourceLimits:
    """The frozen resource limits for a sandbox worker. All zero by default."""

    max_cpu_seconds: int
    max_memory_mb: int
    max_wall_seconds: int
    max_filesystem_read_bytes: int
    max_filesystem_write_bytes: int
    max_network_bytes: int
    max_processes: int


@dataclass(frozen=True, slots=True)
class SandboxIsolationPolicy:
    """The frozen isolation policy for a sandbox worker. All deny by default."""

    filesystem_write_allowed: bool
    network_allowed: bool
    process_spawn_allowed: bool
    secrets_allowed: bool
    host_mount_allowed: bool
    privileged_allowed: bool


@dataclass(frozen=True, slots=True)
class SandboxWorkerLifecyclePlan:
    """A frozen sandbox worker lifecycle plan. Not approved by default."""

    worker_model: str
    start_policy: str
    stop_policy: str
    restart_policy: str
    resource_limits: SandboxResourceLimits
    isolation_policy: SandboxIsolationPolicy
    logging_policy: str
    crash_policy: str
    kill_switch_policy: str
    reviewer_approval_id: str
    approved: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "workerModel": self.worker_model,
                "startPolicy": self.start_policy,
                "stopPolicy": self.stop_policy,
                "restartPolicy": self.restart_policy,
                "resourceLimits": {
                    "maxCpuSeconds": self.resource_limits.max_cpu_seconds,
                    "maxMemoryMb": self.resource_limits.max_memory_mb,
                    "maxWallSeconds": self.resource_limits.max_wall_seconds,
                    "maxFilesystemReadBytes": self.resource_limits.max_filesystem_read_bytes,
                    "maxFilesystemWriteBytes": self.resource_limits.max_filesystem_write_bytes,
                    "maxNetworkBytes": self.resource_limits.max_network_bytes,
                    "maxProcesses": self.resource_limits.max_processes,
                },
                "isolationPolicy": {
                    "filesystemWriteAllowed": self.isolation_policy.filesystem_write_allowed,
                    "networkAllowed": self.isolation_policy.network_allowed,
                    "processSpawnAllowed": self.isolation_policy.process_spawn_allowed,
                    "secretsAllowed": self.isolation_policy.secrets_allowed,
                    "hostMountAllowed": self.isolation_policy.host_mount_allowed,
                    "privilegedAllowed": self.isolation_policy.privileged_allowed,
                },
                "loggingPolicy": self.logging_policy,
                "crashPolicy": self.crash_policy,
                "killSwitchPolicy": self.kill_switch_policy,
                "reviewerApprovalId": self.reviewer_approval_id,
                "approved": self.approved,
            }
        )


@dataclass(frozen=True, slots=True)
class SandboxLifecycleApprovalResult:
    """The frozen result of evaluating a sandbox lifecycle plan. Defaults denied."""

    lifecycle_approved: bool
    worker_start_allowed: bool
    process_spawn_allowed: bool
    network_allowed: bool
    filesystem_write_allowed: bool
    secrets_allowed: bool
    kill_switch_armed: bool
    production_gateway_untouched: bool
    production_authorization: str
    reason: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "lifecycleApproved": self.lifecycle_approved,
                "workerStartAllowed": self.worker_start_allowed,
                "processSpawnAllowed": self.process_spawn_allowed,
                "networkAllowed": self.network_allowed,
                "filesystemWriteAllowed": self.filesystem_write_allowed,
                "secretsAllowed": self.secrets_allowed,
                "killSwitchArmed": self.kill_switch_armed,
                "productionGatewayUntouched": self.production_gateway_untouched,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


@dataclass(frozen=True, slots=True)
class SandboxLifecycleReport:
    """The frozen aggregate sandbox-lifecycle authorization report."""

    lifecycle_approved: bool
    worker_start_allowed: bool
    process_spawn_allowed: bool
    network_allowed: bool
    filesystem_write_allowed: bool
    secrets_allowed: bool
    production_gateway_untouched: bool
    production_authorization: str
    reason: str


# ---------------------------------------------------------------------------
# 2. The frozen default plan + validation
# ---------------------------------------------------------------------------


#: The frozen default resource limits (all zero).
DEFAULT_RESOURCE_LIMITS: SandboxResourceLimits = SandboxResourceLimits(
    max_cpu_seconds=0,
    max_memory_mb=0,
    max_wall_seconds=0,
    max_filesystem_read_bytes=0,
    max_filesystem_write_bytes=0,
    max_network_bytes=0,
    max_processes=0,
)

#: The frozen default isolation policy (all deny).
DEFAULT_ISOLATION_POLICY: SandboxIsolationPolicy = SandboxIsolationPolicy(
    filesystem_write_allowed=False,
    network_allowed=False,
    process_spawn_allowed=False,
    secrets_allowed=False,
    host_mount_allowed=False,
    privileged_allowed=False,
)


def build_sandbox_lifecycle_plan() -> SandboxWorkerLifecyclePlan:
    """Build the frozen default sandbox worker lifecycle plan (not approved)."""
    return SandboxWorkerLifecyclePlan(
        worker_model="disabled",
        start_policy="never",
        stop_policy="never_started",
        restart_policy="never",
        resource_limits=DEFAULT_RESOURCE_LIMITS,
        isolation_policy=DEFAULT_ISOLATION_POLICY,
        logging_policy="redacted_in_memory_only",
        crash_policy="no_worker_running",
        kill_switch_policy="design_ready_only",
        reviewer_approval_id="",
        approved=False,
    )


def validate_sandbox_lifecycle_plan(plan: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate a sandbox lifecycle plan's shape + safety. Returns ``(ok, reasons)``.

    A plan is invalid if it would allow host mounts, privileged mode, network,
    process spawn, filesystem write, or secrets without a reviewer approval, or
    if it is missing a kill-switch policy.
    """
    if not isinstance(plan, SandboxWorkerLifecyclePlan):
        return False, ("plan_not_a_lifecycle_plan",)
    reasons: list[str] = []
    if plan.isolation_policy.host_mount_allowed:
        reasons.append("host_mount_not_allowed")
    if plan.isolation_policy.privileged_allowed:
        reasons.append("privileged_not_allowed")
    if plan.isolation_policy.network_allowed and not plan.reviewer_approval_id:
        reasons.append("network_requires_reviewer_approval")
    if plan.isolation_policy.process_spawn_allowed and not plan.reviewer_approval_id:
        reasons.append("process_spawn_requires_reviewer_approval")
    if plan.isolation_policy.filesystem_write_allowed and not plan.reviewer_approval_id:
        reasons.append("filesystem_write_requires_reviewer_approval")
    if plan.isolation_policy.secrets_allowed:
        reasons.append("secrets_never_allowed")
    if not plan.kill_switch_policy:
        reasons.append("kill_switch_policy_required")
    if not plan.reviewer_approval_id:
        reasons.append("reviewer_approval_required")
    # A plan is safety-valid iff it has no safety violation. Note: this says
    # nothing about whether the plan is *approved* for production — that is the
    # job of :func:`evaluate_sandbox_lifecycle_approval`, which always denies.
    return (len(reasons) == 0), tuple(reasons)


def evaluate_sandbox_lifecycle_approval(
    plan: Any = None,
    untrusted_metadata: Any = None,
) -> SandboxLifecycleApprovalResult:
    """Evaluate the sandbox worker lifecycle approval gate. Always denied today.

    *untrusted_metadata* is inspected only to report ignored bypass keys. The
    production gateway (PID 28428) is referenced only as a do-not-touch target —
    it is never signaled, read, or touched.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    active = plan if isinstance(plan, SandboxWorkerLifecyclePlan) else build_sandbox_lifecycle_plan()
    # Approval requires an explicit, reviewed plan — the default plan is never
    # approved, and no metadata flag can flip it.
    approved = False
    return SandboxLifecycleApprovalResult(
        lifecycle_approved=approved,
        worker_start_allowed=False,
        process_spawn_allowed=active.isolation_policy.process_spawn_allowed and approved,
        network_allowed=active.isolation_policy.network_allowed and approved,
        filesystem_write_allowed=active.isolation_policy.filesystem_write_allowed and approved,
        secrets_allowed=False,
        kill_switch_armed=False,
        production_gateway_untouched=True,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="sandbox_lifecycle_not_approved",
        ignored_metadata_keys=ignored,
    )


def build_sandbox_lifecycle_report() -> SandboxLifecycleReport:
    """Build the frozen aggregate sandbox-lifecycle authorization report.

    The lifecycle is not approved; no worker starts; no process spawns; no
    network / filesystem write / secrets; the production gateway is untouched.
    Production authorization stays NO-GO. Pure and deterministic.
    """
    return SandboxLifecycleReport(
        lifecycle_approved=False,
        worker_start_allowed=False,
        process_spawn_allowed=False,
        network_allowed=False,
        filesystem_write_allowed=False,
        secrets_allowed=False,
        production_gateway_untouched=True,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="sandbox_lifecycle_not_approved",
    )


def assert_sandbox_lifecycle_not_approved() -> None:
    """Re-affirm the sandbox lifecycle is not approved. Pure."""
    report = build_sandbox_lifecycle_report()
    assert report.lifecycle_approved is False
    assert report.worker_start_allowed is False
    assert report.process_spawn_allowed is False
    assert report.network_allowed is False
    assert report.filesystem_write_allowed is False
    assert report.secrets_allowed is False
    assert report.production_gateway_untouched is True
    assert report.production_authorization == TARGET_B_AUTHORIZATION_NO_GO
    plan = build_sandbox_lifecycle_plan()
    assert plan.approved is False
    result = evaluate_sandbox_lifecycle_approval(plan, {"sandbox_bypass": "true"})
    assert result.lifecycle_approved is False
    assert "sandbox_bypass" in result.ignored_metadata_keys


__all__ = [
    # schema
    "SandboxResourceLimits",
    "SandboxIsolationPolicy",
    "SandboxWorkerLifecyclePlan",
    "SandboxLifecycleApprovalResult",
    "SandboxLifecycleReport",
    # defaults
    "DEFAULT_RESOURCE_LIMITS",
    "DEFAULT_ISOLATION_POLICY",
    # validation
    "build_sandbox_lifecycle_plan",
    "validate_sandbox_lifecycle_plan",
    "evaluate_sandbox_lifecycle_approval",
    "build_sandbox_lifecycle_report",
    # boundary
    "assert_sandbox_lifecycle_not_approved",
]
