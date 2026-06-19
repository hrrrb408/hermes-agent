"""Phase 3H Dev-only Sandbox Proof Skeleton — Orchestrator (Block 2).

The single dev-only entry point that ties the guards + policy + audit into a
**proof evaluation**. A proof takes a static descriptor id + metadata, a mock
operation name, requested capabilities / paths / network targets / secret
names, and a kill-switch flag, and returns a :class:`SandboxProofResult`
recording what was allowed and (far more often) denied.

This is a **skeleton**, not a runtime:

  - It never executes a plugin, never loads a plugin, never dynamic-imports.
  - It never performs a network call, never reads a real secret.
  - It introduces **no** HTTP route and is **not** imported by the FastAPI app.
  - It references the Phase 3D static descriptor registry **read-only** (for
    descriptor-only enforcement); it never invokes loader / runtime code.

The result's evidence flags are frozen ``False``: a proof requires no route
change, no production access, no external network, no real secret, no runtime
execution. This is the dev-only skeleton's central invariant.

Phase: 3H — Dev-only Sandbox Proof Skeleton
Status: implemented (skeleton). NOT a real runtime. No plugin execution, no
        dynamic loading, no external network, no real secret, no new route.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Mapping

from hermes_cli.dev_web_sandbox_audit import build_sandbox_audit_record
from hermes_cli.dev_web_sandbox_guards import (
    evaluate_filesystem_path,
    evaluate_network_target,
    evaluate_secret_request,
    redact_sandbox_payload,
)
from hermes_cli.dev_web_sandbox_policy import (
    CapabilityDecision,
    CapabilityEvaluationContext,
    DescriptorDecision,
    KillSwitchDecision,
    evaluate_capability,
    evaluate_descriptor,
    evaluate_kill_switch,
)

SANDBOX_PROOF_VERSION = "phase-3h-sandbox-proof-skeleton-v1"
SANDBOX_PROOF_AUDIT_SOURCE = "dev_web_sandbox_proof"

#: Frozen evidence-flag names the result carries (all must be False).
RESULT_EVIDENCE_FLAGS: tuple[str, ...] = (
    "route_change_required",
    "production_access_required",
    "external_network_required",
    "real_secret_required",
    "runtime_execution_required",
)

#: Maximum number of requested items per category (caps / paths / targets /
#: secrets). Oversized input → denied (``oversized_input``).
MAX_REQUEST_ITEMS_PER_CATEGORY = 64


@dataclass(frozen=True)
class FilesystemRequest:
    """One filesystem access a proof wants to make."""

    path: str
    allow_write: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return {"path": self.path, "allowWrite": self.allow_write}


@dataclass(frozen=True)
class SandboxProofRequest:
    """Input model for a dev-only sandbox proof evaluation.

    Carries only static / mock / proof-level inputs. **Never** carries
    executable plugin code, a Python module / import path, a shell command, an
    external URL to fetch, a real API key, a provider credential, a production
    path, or a live provider request — if any such field is smuggled into
    ``descriptor_metadata`` or ``safe_metadata``, the descriptor / redaction
    guards deny it.
    """

    descriptor_id: str = ""
    descriptor_metadata: Mapping[str, Any] | None = None
    mock_operation: str = ""
    requested_capabilities: tuple[str, ...] = ()
    requested_filesystem_paths: tuple[FilesystemRequest, ...] = ()
    requested_network_targets: tuple[str, ...] = ()
    requested_secret_names: tuple[str, ...] = ()
    kill_switch_active: bool = False
    allowed_roots: tuple[str, ...] = ()
    capability_context: CapabilityEvaluationContext | None = None
    safe_metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        # Defensive-copy caller-supplied mutable mappings so post-construction
        # mutation of the caller's dict cannot change what the proof evaluates
        # (deep copy: descriptor / safe metadata may be arbitrarily nested).
        if self.descriptor_metadata is not None:
            object.__setattr__(
                self, "descriptor_metadata", copy.deepcopy(self.descriptor_metadata)
            )
        if self.safe_metadata is not None:
            object.__setattr__(
                self, "safe_metadata", copy.deepcopy(self.safe_metadata)
            )

    def to_safe_dict(self) -> dict[str, Any]:
        # The request itself is never returned raw by the proof; this helper
        # exists only for debug / test projections and is re-redacted upstream.
        return {
            "descriptorId": self.descriptor_id,
            "mockOperation": self.mock_operation,
            "requestedCapabilities": list(self.requested_capabilities),
            "requestedFilesystemPaths": [r.to_safe_dict() for r in self.requested_filesystem_paths],
            "requestedNetworkTargets": list(self.requested_network_targets),
            "requestedSecretNames": list(self.requested_secret_names),
            "killSwitchActive": self.kill_switch_active,
            "allowedRootsCount": len(self.allowed_roots),
            "redactionApplied": True,
        }


@dataclass(frozen=True)
class SandboxProofResult:
    """Output model for a dev-only sandbox proof evaluation."""

    allowed: bool
    denial_reasons: tuple[str, ...] = ()
    triggered_guards: tuple[str, ...] = ()
    route_change_required: bool = False
    production_access_required: bool = False
    external_network_required: bool = False
    real_secret_required: bool = False
    runtime_execution_required: bool = False
    kill_switch_decision: KillSwitchDecision | None = None
    descriptor_decision: DescriptorDecision | None = None
    capability_decisions: tuple[CapabilityDecision, ...] = ()
    audit_record: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Decouple the stored audit record from the builder's dict (and from any
        # later caller read of ``result.audit_record``) via a deep copy. The
        # result is frozen, so the field cannot be reassigned — but a mutable
        # dict could still be mutated in place; this snapshot isolates it.
        if self.audit_record:
            object.__setattr__(self, "audit_record", copy.deepcopy(self.audit_record))

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": SANDBOX_PROOF_VERSION,
            "allowed": self.allowed,
            "denialReasons": list(self.denial_reasons),
            "triggeredGuards": list(self.triggered_guards),
            "routeChangeRequired": self.route_change_required,
            "productionAccessRequired": self.production_access_required,
            "externalNetworkRequired": self.external_network_required,
            "realSecretRequired": self.real_secret_required,
            "runtimeExecutionRequired": self.runtime_execution_required,
            "killSwitch": self.kill_switch_decision.to_safe_dict() if self.kill_switch_decision else None,
            "descriptor": self.descriptor_decision.to_safe_dict() if self.descriptor_decision else None,
            "capabilities": [c.to_safe_dict() for c in self.capability_decisions],
            "audit": redact_sandbox_payload(copy.deepcopy(dict(self.audit_record))),
            "redactionApplied": True,
        }


def _oversized(request: SandboxProofRequest) -> str | None:
    """Return a denial reason if the request is oversized, else None."""
    if len(request.requested_capabilities) > MAX_REQUEST_ITEMS_PER_CATEGORY:
        return "oversized_input_capabilities"
    if len(request.requested_filesystem_paths) > MAX_REQUEST_ITEMS_PER_CATEGORY:
        return "oversized_input_filesystem_paths"
    if len(request.requested_network_targets) > MAX_REQUEST_ITEMS_PER_CATEGORY:
        return "oversized_input_network_targets"
    if len(request.requested_secret_names) > MAX_REQUEST_ITEMS_PER_CATEGORY:
        return "oversized_input_secret_names"
    return None


def evaluate_sandbox_proof(request: SandboxProofRequest) -> SandboxProofResult:
    """Evaluate a dev-only sandbox proof. Fail-closed default.

    Order (first denial short-circuits the ``allowed`` flag but evaluation
    continues so the audit record records every triggered guard):

      1. kill-switch active → fail closed.
      2. oversized input → denied.
      3. descriptor carries an execution surface → denied (descriptor-only).
      4. each requested capability → default-deny.
      5. each requested filesystem path → boundary guard.
      6. each requested network target → network deny guard.
      7. each requested secret name → secret deny guard.

    The result's evidence flags are frozen ``False``: a proof requires no
    route change / production access / external network / real secret / runtime
    execution.
    """
    reasons: list[str] = []
    guards: list[str] = []

    # 1. Kill switch.
    ks_decision = evaluate_kill_switch(request.kill_switch_active)
    if ks_decision.fail_closed:
        reasons.append("kill_switch_active")
        guards.append("kill_switch")

    # 2. Oversized input.
    oversized = _oversized(request)
    if oversized is not None:
        reasons.append(oversized)
        guards.append("input_size")

    # 3. Descriptor-only enforcement.
    descriptor_decision: DescriptorDecision | None = None
    if request.descriptor_metadata is not None:
        descriptor_decision = evaluate_descriptor(request.descriptor_metadata)
        if not descriptor_decision.allowed:
            for reason in descriptor_decision.reasons:
                reasons.append(reason)
            guards.append("descriptor_only")

    # 4. Capabilities.
    cap_context = request.capability_context or CapabilityEvaluationContext()
    cap_decisions: list[CapabilityDecision] = []
    for capability in request.requested_capabilities:
        decision = evaluate_capability(capability, context=cap_context)
        cap_decisions.append(decision)
        if not decision.allowed:
            reasons.extend(decision.reasons)
            guards.append(f"capability:{capability}")

    # 5. Filesystem paths.
    for fs_request in request.requested_filesystem_paths:
        fs_decision = evaluate_filesystem_path(
            fs_request.path,
            allowed_roots=request.allowed_roots,
            allow_write=fs_request.allow_write,
        )
        if not fs_decision.allowed:
            reasons.extend(fs_decision.reasons)
            guards.append("filesystem_boundary")

    # 6. Network targets.
    for target in request.requested_network_targets:
        net_decision = evaluate_network_target(target, capability_requested=True)
        if not net_decision.allowed:
            reasons.extend(net_decision.reasons)
            guards.append("network_deny")

    # 7. Secret names.
    for secret_name in request.requested_secret_names:
        secret_decision = evaluate_secret_request(secret_name)
        if not secret_decision.allowed:
            reasons.extend(secret_decision.reasons)
            guards.append("secret_unavailable")

    allowed = len(reasons) == 0

    audit_record = build_sandbox_audit_record(
        decision="allowed" if allowed else "denied",
        reasons=reasons,
        triggered_guards=guards,
        requested_capabilities=list(request.requested_capabilities),
        descriptor_id=request.descriptor_id,
        kill_switch_active=ks_decision.active,
        safe_metadata=request.safe_metadata,
    )

    return SandboxProofResult(
        allowed=allowed,
        denial_reasons=tuple(reasons),
        triggered_guards=tuple(guards),
        route_change_required=False,
        production_access_required=False,
        external_network_required=False,
        real_secret_required=False,
        runtime_execution_required=False,
        kill_switch_decision=ks_decision,
        descriptor_decision=descriptor_decision,
        capability_decisions=tuple(cap_decisions),
        audit_record=audit_record,
    )


def is_sandbox_proof_result_safe(result: SandboxProofResult | Mapping[str, Any]) -> bool:
    """True iff a proof result is value-free and requires no escalation.

    Accepts a :class:`SandboxProofResult` or its safe-dict form. Asserts the
    frozen evidence flags are all ``False`` and that the audit record is safe.
    """
    if isinstance(result, SandboxProofResult):
        for flag in RESULT_EVIDENCE_FLAGS:
            if getattr(result, flag) is not False:
                return False
        from hermes_cli.dev_web_sandbox_audit import is_audit_record_safe

        return is_audit_record_safe(result.audit_record)
    if isinstance(result, Mapping):
        mapping = {
            "route_change_required": "routeChangeRequired",
            "production_access_required": "productionAccessRequired",
            "external_network_required": "externalNetworkRequired",
            "real_secret_required": "realSecretRequired",
            "runtime_execution_required": "runtimeExecutionRequired",
        }
        for attr, key in mapping.items():
            if result.get(key) is not False:
                return False
        from hermes_cli.dev_web_sandbox_audit import is_audit_record_safe

        return is_audit_record_safe(result.get("audit", {}))
    return False


__all__ = [
    "SANDBOX_PROOF_VERSION",
    "SANDBOX_PROOF_AUDIT_SOURCE",
    "RESULT_EVIDENCE_FLAGS",
    "MAX_REQUEST_ITEMS_PER_CATEGORY",
    "FilesystemRequest",
    "SandboxProofRequest",
    "SandboxProofResult",
    "evaluate_sandbox_proof",
    "is_sandbox_proof_result_safe",
]
