"""Phase 4B — Target B runtime orchestrator (pure stdlib, fail-closed).

Layer 9 of the Phase 4B Target B engineering path. Defines the **runtime
orchestrator**: it composes the package, signature, permission, sandbox,
approval, and execution-policy layers into a single prepare / execute /
dry-run surface.

The orchestrator is **deny-by-default**:

  - :func:`prepare_plugin_execution` returns a *preview only* — no plugin is
    loaded, imported, or executed;
  - :func:`execute_plugin_gated` returns a *denied* result unconditionally — no
    plugin is executed, no subprocess is spawned, no network is opened, no
    secret is read, no filesystem write occurs;
  - :func:`dry_run_plugin_execution_policy` evaluates the policy without side
    effects and explains why execution is denied.

A future branch — when **every** gate passes and a real authorization exists —
would perform the actual execution. That branch is explicitly **not
implemented** in this task: no such authorization exists today, so it is left as
a documented, unreachable placeholder.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no real secret read, no production access.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_target_b_audit import build_denied_execution_audit
from hermes_cli.dev_web_target_b_common import (
    TARGET_B_DISABLED_REASON,
    TARGET_B_NO_GO,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
)
from hermes_cli.dev_web_target_b_execution_policy import (
    ExecutionPolicyReport,
    build_execution_policy_report,
    evaluate_target_b_execution_policy,
)
from hermes_cli.dev_web_target_b_package import (
    PluginPackageDescriptor,
    validate_plugin_package_without_loading,
)
from hermes_cli.dev_web_target_b_sandbox import (
    SandboxExecutionRequest,
    deny_sandbox_execution,
)

# ---------------------------------------------------------------------------
# 1. Execution request / preview / result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PluginExecutionRequest:
    """A request to execute a plugin. Carries untrusted metadata only.

    The ``descriptor`` is a validated-shape package descriptor projection; it is
    never loaded, imported, or executed.
    """

    descriptor: PluginPackageDescriptor
    entrypoint: str
    untrusted_metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RuntimeExecutionPreview:
    """A read-only preview of what a (denied) execution would entail.

    Pure projection — no plugin is loaded, imported, or executed.
    """

    prepared: bool
    package_valid: bool
    package_trusted: bool
    policy_allowed: bool
    execution_preview_only: bool
    reasons: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "prepared": self.prepared,
                "packageValid": self.package_valid,
                "packageTrusted": self.package_trusted,
                "policyAllowed": self.policy_allowed,
                "executionPreviewOnly": self.execution_preview_only,
                "reasons": list(self.reasons),
            }
        )


@dataclass(frozen=True, slots=True)
class PluginExecutionResult:
    """The frozen result of :func:`execute_plugin_gated`. Always denied."""

    executed: bool
    allowed: bool
    prepared: bool
    denied_audit_event_id: str
    reason: str
    production_authorization: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "executed": self.executed,
                "allowed": self.allowed,
                "prepared": self.prepared,
                "deniedAuditEventId": self.denied_audit_event_id,
                "reason": self.reason,
                "productionAuthorization": self.production_authorization,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


# ---------------------------------------------------------------------------
# 2. prepare / dry-run / execute
# ---------------------------------------------------------------------------


def prepare_plugin_execution(
    request: Any,
    untrusted_metadata: Any = None,
) -> RuntimeExecutionPreview:
    """Prepare a plugin execution — returns a *preview only*.

    Validates the package descriptor's shape (never loads it) and evaluates the
    execution policy. The preview is ``prepared=True`` (the request was
    understood) but ``execution_preview_only=True`` — nothing is executed.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    reasons: list[str] = []
    package_valid = False
    package_trusted = False
    if not isinstance(request, PluginExecutionRequest):
        reasons.append("request_not_a_plugin_execution_request")
    else:
        validation = validate_plugin_package_without_loading(
            request.descriptor.to_raw_descriptor()
        )
        package_valid = validation.valid
        package_trusted = validation.trusted  # always False
        if not package_valid:
            reasons.append("package_shape_invalid")
    policy = evaluate_target_b_execution_policy(untrusted_metadata=untrusted_metadata)
    if not policy.allowed:
        reasons.extend(policy.reasons)
    return RuntimeExecutionPreview(
        prepared=True,  # the request was understood
        package_valid=package_valid,
        package_trusted=package_trusted,
        policy_allowed=policy.allowed,
        execution_preview_only=True,
        reasons=tuple(reasons) + ignored,
    )


def dry_run_plugin_execution_policy(
    request: Any = None,
    untrusted_metadata: Any = None,
) -> ExecutionPolicyReport:
    """Evaluate the execution policy without side effects. Always denied today.

    A dry run never executes, never imports, never spawns, never opens the
    network, and never reads a secret. It returns the policy report explaining
    why execution is denied.
    """
    # Touch the request shape so a smuggler's metadata is observed; the answer
    # is unchanged.
    if isinstance(request, PluginExecutionRequest):
        detect_target_b_untrusted_metadata(request.untrusted_metadata)
    return evaluate_target_b_execution_policy(untrusted_metadata=untrusted_metadata)


def execute_plugin_gated(
    request: Any,
    untrusted_metadata: Any = None,
) -> PluginExecutionResult:
    """Execute a plugin under the gate. Always denied today.

    No plugin is executed, no subprocess is spawned, no network is opened, no
    secret is read, and no filesystem write occurs. A denied-execution audit
    event is built (in-memory only). If every gate passed and a real
    authorization existed, a future branch would perform the execution — that
    branch is **not implemented** here because no such authorization exists.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    audit = build_denied_execution_audit(
        event_id="target-b-runtime-execution-denied",
        layer="runtime",
        reason=TARGET_B_DISABLED_REASON,
        payload={"requestType": type(request).__name__ if request is not None else "none"},
    )
    policy = evaluate_target_b_execution_policy(untrusted_metadata=untrusted_metadata)
    return PluginExecutionResult(
        executed=False,
        allowed=False,
        prepared=isinstance(request, PluginExecutionRequest),
        denied_audit_event_id=audit.event_id,
        reason=TARGET_B_DISABLED_REASON,
        production_authorization=TARGET_B_NO_GO,
        ignored_metadata_keys=ignored,
    )


def build_runtime_execution_preview(
    descriptor: Any = None,
    untrusted_metadata: Any = None,
) -> RuntimeExecutionPreview:
    """Build a standalone runtime execution preview. Preview only — no execution."""
    if isinstance(descriptor, PluginPackageDescriptor):
        request = PluginExecutionRequest(
            descriptor=descriptor,
            entrypoint="preview (not executed)",
            untrusted_metadata=untrusted_metadata if isinstance(untrusted_metadata, Mapping) else {},
        )
        return prepare_plugin_execution(request, untrusted_metadata=untrusted_metadata)
    return prepare_plugin_execution(descriptor, untrusted_metadata=untrusted_metadata)


def build_denied_runtime_audit(
    untrusted_metadata: Any = None,
) -> str:
    """Build a denied-execution audit event id (in-memory only). Pure."""
    detect_target_b_untrusted_metadata(untrusted_metadata)
    event = build_denied_execution_audit(
        event_id="target-b-runtime-denied",
        layer="runtime",
        reason=TARGET_B_DISABLED_REASON,
    )
    return event.event_id


@dataclass(frozen=True, slots=True)
class RuntimeReadinessReport:
    """The frozen aggregate runtime readiness report."""

    runtime_enabled: bool
    execution_allowed: bool
    prepared_preview_only: bool
    production_authorization: str
    policy: ExecutionPolicyReport

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "runtimeEnabled": self.runtime_enabled,
                "executionAllowed": self.execution_allowed,
                "preparedPreviewOnly": self.prepared_preview_only,
                "productionAuthorization": self.production_authorization,
                "policy": self.policy.to_safe_dict(),
            }
        )


def build_runtime_readiness_report() -> RuntimeReadinessReport:
    """Build the frozen aggregate runtime report. Runtime disabled / preview only."""
    policy = build_execution_policy_report()
    return RuntimeReadinessReport(
        runtime_enabled=False,
        execution_allowed=False,
        prepared_preview_only=True,
        production_authorization=TARGET_B_NO_GO,
        policy=policy,
    )


def assert_runtime_layer_disabled() -> None:
    """Re-affirm the runtime layer disabled invariants. Pure."""
    policy = build_execution_policy_report()
    assert policy.allowed is False
    report = build_runtime_readiness_report()
    assert report.runtime_enabled is False
    assert report.execution_allowed is False
    assert report.production_authorization == TARGET_B_NO_GO
    # deny_sandbox_execution is imported to prove the orchestrator composes the
    # disabled sandbox; it never spawns.
    denied = deny_sandbox_execution({"force": "true"})
    assert denied.executed is False


__all__ = [
    # request / preview / result
    "PluginExecutionRequest",
    "RuntimeExecutionPreview",
    "PluginExecutionResult",
    # orchestrator
    "prepare_plugin_execution",
    "dry_run_plugin_execution_policy",
    "execute_plugin_gated",
    "build_runtime_execution_preview",
    "build_denied_runtime_audit",
    # report
    "RuntimeReadinessReport",
    "build_runtime_readiness_report",
    # boundary
    "assert_runtime_layer_disabled",
]
