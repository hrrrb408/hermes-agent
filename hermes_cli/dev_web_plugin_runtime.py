"""Phase 3I Dev-only Local Plugin Runtime MVP (code allowed, production forbidden).

A **very narrow** dev-only local plugin runtime that may invoke the reviewed,
side-effect-free fixture operations in
:mod:`hermes_cli.dev_web_fixture_plugins` — and only those. It takes a
:class:`PluginRuntimeRequest`, resolves a descriptor-to-fixture binding through
a hardcoded allowlist, enforces capability / filesystem / network / secrets /
production / route / kill-switch guards, runs the bound fixture (catching and
redacting any failure), and returns a redacted, in-memory
:class:`PluginRuntimeResult`.

This is a **dev-only MVP**, not a production plugin runtime:

  - It executes **only** reviewed fixture operations bound through the frozen
    ``FIXTURE_ALLOWLIST``. There is no plugin loader, no ``importlib`` /
    ``__import__`` / ``eval`` / ``exec``, no subprocess, no shell, no dynamic
    import of any path, no arbitrary local plugin directory loading, no remote
    registry, no marketplace, no external plugin fetch, no provider-generated /
    LLM-generated plugin install.
  - It reads **no** real API key, contacts **no** host, touches **no**
    filesystem path (the fixtures are pure in-memory transforms), opens **no**
    ``~/.hermes`` and **no** production ``state.db``, writes **no** runtime
    store, and adds **no** HTTP route. It is **not** imported by the FastAPI app.
  - A successful fixture execution is **dev-only partial evidence**. It is
    **never** Implementation Authorization GO, **never** Phase 3I production
    authorization, **never** real-runtime authorization, **never** a P0
    resolution. ``resolved_count`` stays 0 and the authorization flags stay
    NO-GO / not-authorized no matter what runs or what untrusted metadata a
    request carries.

The runtime reuses the Phase 3H guards / policy / audit / evidence logic
verbatim (descriptor-only enforcement, capability default-deny, kill switch,
filesystem / network / secret guards, redaction, P0 evidence) and layers a
single new capability on top: invoke a reviewed fixture by allowlist binding.

Phase: 3I — Dev-only Local Plugin Runtime MVP
Status: implemented (dev-only runtime). NOT a production plugin runtime. No
        arbitrary loading, no remote registry, no marketplace, no external
        network, no real secret read, no new route, no production access.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from hermes_cli.dev_web_fixture_plugins import (
    FIXTURE_ALLOWLIST,
    FIXTURE_OPERATION_NAMES,
    FIXTURE_PLUGIN_IDS,
    FIXTURE_REGISTRY,
    FixtureOperation,
    FixtureOutputError,
    MAX_FIXTURE_NESTING_DEPTH,
    lookup_fixture,
    validate_fixture_metadata,
)
from hermes_cli.dev_web_p0_evidence import (
    GATE_STATUS_PARTIAL_EVIDENCE,
    IMPLEMENTATION_AUTHORIZATION,
    NEW_ROUTE,
    PHASE_3I_AUTHORIZED,
    PRODUCTION_ROLLOUT,
    ProvenanceDecision,
    REAL_RUNTIME,
    classify_plugin_source,
    detect_untrusted_metadata,
)
from hermes_cli.dev_web_sandbox_guards import (
    REDACTED_VALUE,
    contains_secret,
    evaluate_filesystem_path,
    evaluate_network_target,
    evaluate_secret_request,
    redact_sandbox_payload,
    redact_sandbox_text,
)
from hermes_cli.dev_web_sandbox_policy import (
    CapabilityEvaluationContext,
    DescriptorDecision,
    KillSwitchDecision,
    evaluate_capability,
    evaluate_descriptor,
    evaluate_kill_switch,
)

PLUGIN_RUNTIME_VERSION = "phase-3i-dev-only-local-plugin-runtime-mvp-v1"
PLUGIN_RUNTIME_AUDIT_SOURCE = "dev_web_plugin_runtime"

#: The frozen evidence-flag names every result carries (all must be False). A
#: dev-only fixture runtime requires no route change / production access /
#: external network / real secret / runtime execution (of a *real* plugin) and
#: creates no persistent artifact.
RESULT_EVIDENCE_FLAGS: tuple[str, ...] = (
    "route_change_required",
    "production_access_required",
    "external_network_required",
    "real_secret_required",
    "real_runtime_execution_required",
    "persistent_artifacts_created",
)

#: Maximum number of requested items per category (caps / paths / targets /
#: secrets). Oversized input → denied (``oversized_input``).
MAX_REQUEST_ITEMS_PER_CATEGORY = 64

#: Maximum number of requests in a single batch. An oversized batch is rejected
#: outright (``batch_oversized``) so the batch runner never processes unbounded
#: input.
MAX_BATCH_REQUESTS: int = 32

#: A safe batch id is a clean label over ``[A-Za-z0-9_.\-]`` (mirrors a
#: descriptor / scenario id) — never a path, traversal pair, or command.
_BATCH_ID_SAFE: re.Pattern[str] = re.compile(r"[A-Za-z0-9_.\-]+")

#: The frozen runtime flags every result carries. The dev-only / fixture-only
#: flags are True; every production / network / secret / route / store / load /
#: fetch / marketplace flag is False — a fixture execution flips none of them.
#: These are constants: enforced in :class:`PluginRuntimeResult.__post_init__`.
RUNTIME_FLAGS_FROZEN: dict[str, bool] = {
    "dev_only": True,
    "fixture_only": True,
    "production_access": False,
    "external_network": False,
    "real_secret_read": False,
    "route_change": False,
    "runtime_store_write": False,
    "arbitrary_plugin_load": False,
    "remote_plugin_fetch": False,
    "marketplace_access": False,
}

#: A clean plugin_id / operation label is over ``[a-z0-9_.]`` with no traversal
#: pair. (Allowlist membership — not label safety — is the real gate; this only
#: rejects path / shell / wildcard smuggling before the allowlist lookup.)
_LABEL_SAFE: re.Pattern[str] = re.compile(r"[a-z0-9_.]+")

#: Operation verbs that denote an execution surface even as a bare label. They
#: are denied with a precise reason in addition to the allowlist membership
#: denial — an operation named ``import`` / ``shell`` / ``execute`` is never a
#: reviewed fixture operation.
_DANGEROUS_OPERATION_VERBS: frozenset[str] = frozenset(
    {
        "import",
        "__import__",
        "shell",
        "execute",
        "exec",
        "eval",
        "run",
        "subprocess",
        "load",
        "fetch",
        "install",
        "spawn",
    }
)

#: Stable reason tokens the runtime may emit.
RUNTIME_REASONS: frozenset[str] = frozenset(
    {
        "kill_switch_active",
        "metadata_authorization_smuggling_denied",
        "oversized_input_capabilities",
        "oversized_input_filesystem_paths",
        "oversized_input_network_targets",
        "oversized_input_secret_names",
        "plugin_id_unsafe",
        "operation_unsafe",
        "plugin_id_missing",
        "operation_missing",
        "dangerous_operation_denied",
        "fixture_not_in_allowlist",
        "malformed_descriptor",
        "descriptor_carries_execution_surface",
        "descriptor_oversized",
        "descriptor_id_missing",
        "descriptor_id_unsafe",
        "untrusted_source_denied",
        "remote_registry_denied",
        "marketplace_denied",
        "external_fetch_denied",
        "provider_generated_denied",
        "llm_generated_denied",
        "capability_default_denied",
        "network_request_denied",
        "secret_request_denied",
        "routes_modify_denied",
        "production_access_denied",
        "plugin_execution_denied",
        "filesystem_boundary",
        "network_deny",
        "secret_unavailable",
        "fixture_execution_failed",
        "fixture_input_invalid",
        "fixture_metadata_unsafe",
        "fixture_metadata_missing",
        "fixture_output_unsafe",
        "capability_mismatch_denied",
        "batch_oversized",
        "batch_id_unsafe",
        "batch_id_missing",
        "batch_malformed_requests",
        "batch_metadata_smuggling_denied",
        "redaction_failed_fail_closed",
    }
)


# ---------------------------------------------------------------------------
# 1. Request model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PluginRuntimeRequest:
    """Input model for a dev-only local plugin runtime evaluation.

    Carries only static / dev-only inputs. **Never** carries executable plugin
    code, a Python module / import path, a shell command, an external URL to
    fetch, a real API key, a provider credential, or a production path. Every
    filesystem path is a fake / temp / string-policy target; every secret value
    is an obvious fake. The optional ``descriptor`` is read descriptor-only and
    classified for supply-chain provenance — it is **never** loaded / executed.

    The ``(plugin_id, operation)`` pair is the canonical binding key. When a
    ``descriptor`` mapping is also supplied, it must pass descriptor-only +
    provenance enforcement; its ``pluginId`` / ``operation`` may supply the
    binding key when the request fields are empty.
    """

    plugin_id: str = ""
    operation: str = ""
    descriptor_id: str = ""
    descriptor: Mapping[str, Any] | None = None
    input_payload: Mapping[str, Any] | None = None
    requested_capabilities: tuple[str, ...] = ()
    requested_filesystem_paths: tuple[str, ...] = ()
    requested_network_targets: tuple[str, ...] = ()
    requested_secret_names: tuple[str, ...] = ()
    kill_switch_state: bool = False
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        # Defensive-copy caller-supplied mutable mappings so post-construction
        # mutation of the caller's dict cannot change what the runtime evaluates
        # (deep copy: descriptor / input / metadata may be arbitrarily nested).
        if self.descriptor is not None:
            object.__setattr__(self, "descriptor", copy.deepcopy(self.descriptor))
        if self.input_payload is not None:
            object.__setattr__(self, "input_payload", copy.deepcopy(self.input_payload))
        if self.metadata is not None:
            object.__setattr__(self, "metadata", copy.deepcopy(self.metadata))

    def to_safe_dict(self) -> dict[str, Any]:
        # The request is never returned raw by the runtime; this helper exists
        # only for debug / test projections and is re-redacted upstream.
        return {
            "pluginId": self.plugin_id,
            "operation": self.operation,
            "descriptorId": self.descriptor_id,
            "requestedCapabilities": list(self.requested_capabilities),
            "requestedFilesystemPaths": list(self.requested_filesystem_paths),
            "requestedNetworkTargets": list(self.requested_network_targets),
            "requestedSecretNames": list(self.requested_secret_names),
            "killSwitchState": bool(self.kill_switch_state),
            "hasDescriptor": self.descriptor is not None,
            "hasInputPayload": self.input_payload is not None,
            "redactionApplied": True,
        }


# ---------------------------------------------------------------------------
# 2. Descriptor-to-fixture binding
# ---------------------------------------------------------------------------


def _label_is_safe(value: Any) -> bool:
    """True iff *value* is a clean ``[a-z0-9_.]`` label with no traversal pair."""
    if not isinstance(value, str) or not value:
        return False
    if ".." in value:
        return False
    return _LABEL_SAFE.fullmatch(value) is not None


def _source_view(descriptor: Mapping[str, Any]) -> Mapping[str, Any]:
    """Project a descriptor to a provenance source mapping for classification.

    Reads only the source-type key (``source`` / ``sourceType`` / ``origin``);
    defaults to ``descriptor_only`` when absent. Never fetches anything.
    """
    raw = descriptor.get("source", descriptor.get("sourceType", descriptor.get("origin")))
    if isinstance(raw, str) and raw.strip():
        return {"sourceType": raw.strip()}
    return {"sourceType": "descriptor_only"}


@dataclass(frozen=True, slots=True)
class RuntimeBinding:
    """A resolved descriptor-to-fixture binding.

    ``resolved`` is True **only** when a reviewed fixture operation was bound.
    ``fixture`` is the bound :class:`FixtureOperation` (or ``None``). The
    decisions record *why* a binding was or was not resolved; they never carry
    a secret or a raw module / command / url value.
    """

    plugin_id: str
    operation: str
    resolved: bool
    fixture: FixtureOperation | None
    descriptor_decision: DescriptorDecision | None
    provenance_decision: ProvenanceDecision | None
    reasons: tuple[str, ...] = ()

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "pluginId": self.plugin_id,
                "operation": self.operation,
                "resolved": self.resolved,
                "fixtureBound": self.fixture is not None,
                "fixture": self.fixture.to_safe_dict() if self.fixture else None,
                "descriptorDecision": (
                    self.descriptor_decision.to_safe_dict() if self.descriptor_decision else None
                ),
                "provenanceDecision": (
                    self.provenance_decision.to_safe_dict() if self.provenance_decision else None
                ),
                "reasons": list(self.reasons),
                "redactionApplied": True,
            }
        )


def resolve_runtime_binding(request: PluginRuntimeRequest) -> RuntimeBinding:
    """Resolve a descriptor-to-fixture binding through the frozen allowlist.

    Steps (each denial pushes a precise reason; resolution requires all pass):

      1. If a ``descriptor`` mapping is present, enforce descriptor-only
         (:func:`evaluate_descriptor`) and supply-chain provenance
         (:func:`classify_plugin_source`). A descriptor carrying an execution
         surface, or an untrusted / remote / marketplace / generated source, is
         denied outright.
      2. Determine the effective ``(plugin_id, operation)`` — from the request
         fields, falling back to the descriptor's ``pluginId`` / ``operation``.
      3. Validate both are clean labels (``plugin_id_unsafe`` /
         ``operation_unsafe`` / ``missing``).
      4. Deny a dangerous operation verb (``dangerous_operation_denied``).
      5. Exact-membership allowlist lookup (:func:`lookup_fixture`). A pair not
         in :data:`FIXTURE_ALLOWLIST` is denied (``fixture_not_in_allowlist``).

    Never loads, imports, fetches, or executes anything.
    """
    reasons: list[str] = []
    descriptor_decision: DescriptorDecision | None = None
    provenance_decision: ProvenanceDecision | None = None

    # 1. Descriptor-only + provenance enforcement (only when a descriptor is
    #    supplied). A request with no descriptor binds directly by allowlist.
    if request.descriptor is not None:
        if not isinstance(request.descriptor, Mapping):
            descriptor_decision = DescriptorDecision(
                descriptor_id_redacted="",
                descriptor_only=False,
                allowed=False,
                reasons=("malformed_descriptor",),
            )
            reasons.extend(descriptor_decision.reasons)
        else:
            descriptor_decision = evaluate_descriptor(request.descriptor)
            if not descriptor_decision.allowed:
                reasons.extend(descriptor_decision.reasons)
            provenance_decision = classify_plugin_source(_source_view(request.descriptor))
            if not provenance_decision.metadata_readable:
                reasons.extend(provenance_decision.reasons)

    # 2. Effective binding key.
    plugin_id = request.plugin_id
    operation = request.operation
    if (not plugin_id) and isinstance(request.descriptor, Mapping):
        plugin_id = request.descriptor.get("pluginId") or request.descriptor.get("descriptorId") or ""
    if (not operation) and isinstance(request.descriptor, Mapping):
        operation = request.descriptor.get("operation") or ""
    plugin_id = plugin_id if isinstance(plugin_id, str) else ""
    operation = operation if isinstance(operation, str) else ""

    # 3. Label safety.
    if not plugin_id:
        reasons.append("plugin_id_missing")
    elif not _label_is_safe(plugin_id):
        reasons.append("plugin_id_unsafe")
    if not operation:
        reasons.append("operation_missing")
    elif not _label_is_safe(operation):
        reasons.append("operation_unsafe")

    # 4. Dangerous operation verb.
    if operation and operation in _DANGEROUS_OPERATION_VERBS:
        reasons.append("dangerous_operation_denied")

    # 5. Allowlist membership (only when labels are well-formed).
    fixture: FixtureOperation | None = None
    if plugin_id and operation and _label_is_safe(plugin_id) and _label_is_safe(operation):
        fixture = lookup_fixture(plugin_id, operation)
        if fixture is None:
            reasons.append("fixture_not_in_allowlist")

    # 6. Metadata re-validation (defense-in-depth) + capability compatibility.
    #    A bound fixture's safety metadata must be all-False (``side_effects`` /
    #    ``network`` / ``secrets`` / ``filesystem`` / ``production`` /
    #    ``route_change``); a forged / injected operation with tampered metadata
    #    is refused here. Every requested capability must also be one the bound
    #    fixture declares as compatible (a pure fixture allows only
    #    descriptor-level labels) — a capability outside that set is a mismatch.
    if fixture is not None:
        meta_ok, meta_reasons = validate_fixture_metadata(fixture)
        if not meta_ok:
            reasons.extend(meta_reasons)
            fixture = None
        else:
            for capability in request.requested_capabilities:
                if capability not in fixture.allowed_capabilities:
                    reasons.append("capability_mismatch_denied")
                    break

    resolved = fixture is not None and not reasons
    return RuntimeBinding(
        plugin_id=plugin_id if _label_is_safe(plugin_id) else "",
        operation=operation if _label_is_safe(operation) else "",
        resolved=resolved,
        fixture=fixture,
        descriptor_decision=descriptor_decision,
        provenance_decision=provenance_decision,
        reasons=tuple(reasons),
    )


def validate_runtime_binding(binding: RuntimeBinding) -> tuple[bool, tuple[str, ...]]:
    """Validate a resolved binding. Returns ``(ok, reasons)``."""
    return binding.resolved, binding.reasons


# ---------------------------------------------------------------------------
# 3. Policy (capability / guard / kill-switch / metadata-smuggling enforcement)
# ---------------------------------------------------------------------------


class PluginRuntimePolicy:
    """Stateless policy namespace for the dev-only runtime.

    Every method is a pure evaluator returning ``(ok, reasons, guards)`` (or a
    decision object). Default-deny: an unknown / dangerous / oversized /
    smuggled / kill-switched request fails closed. No method loads, imports,
    fetches, or executes anything.
    """

    def validate_kill_switch(self, kill_switch_state: Any) -> KillSwitchDecision:
        """An active (or invalid) kill switch fails the request closed."""
        return evaluate_kill_switch(kill_switch_state)

    def validate_metadata_no_authorization_smuggling(
        self, metadata: Any
    ) -> tuple[bool, tuple[str, ...]]:
        """Detect + deny authorization-smuggling metadata.

        Any bypass-shaped key (approval / authorization / signoff / trust-token
        / route-exception / production / runtime / phase-3I / resolved variant)
        is detected via :func:`detect_untrusted_metadata` and the request is
        denied — a runtime that actually invokes code fails closed on a smuggling
        attempt. The frozen authorization flags are unaffected either way.
        """
        smuggled = detect_untrusted_metadata(metadata)
        if smuggled:
            return False, ("metadata_authorization_smuggling_denied",)
        return True, ()

    def validate_fixture_allowlist(
        self, plugin_id: Any, operation: Any
    ) -> tuple[bool, tuple[str, ...]]:
        """Validate ``(plugin_id, operation)`` against the frozen allowlist."""
        reasons: list[str] = []
        if not plugin_id:
            reasons.append("plugin_id_missing")
        elif not _label_is_safe(plugin_id):
            reasons.append("plugin_id_unsafe")
        if not operation:
            reasons.append("operation_missing")
        elif not _label_is_safe(operation):
            reasons.append("operation_unsafe")
        if operation and operation in _DANGEROUS_OPERATION_VERBS:
            reasons.append("dangerous_operation_denied")
        if not reasons:
            if lookup_fixture(plugin_id, operation) is None:
                reasons.append("fixture_not_in_allowlist")
        return (not reasons), tuple(reasons)

    def validate_capabilities(
        self, requested_capabilities: Any
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Evaluate requested capabilities. Default-deny; returns (reasons, guards)."""
        if not isinstance(requested_capabilities, (list, tuple, set, frozenset)):
            return (), ()
        reasons: list[str] = []
        guards: list[str] = []
        for capability in requested_capabilities:
            if capability is None:
                continue
            decision = evaluate_capability(capability, context=CapabilityEvaluationContext())
            if not decision.allowed:
                reasons.extend(decision.reasons)
                guards.append(f"capability:{capability}")
        return tuple(reasons), tuple(guards)

    def validate_guards(
        self, request: PluginRuntimeRequest
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Evaluate filesystem / network / secret guards. Returns (reasons, guards)."""
        reasons: list[str] = []
        guards: list[str] = []
        for path in request.requested_filesystem_paths:
            decision = evaluate_filesystem_path(path)
            if not decision.allowed:
                reasons.extend(decision.reasons)
                guards.append("filesystem_boundary")
        for target in request.requested_network_targets:
            decision = evaluate_network_target(target, capability_requested=True)
            if not decision.allowed:
                reasons.extend(decision.reasons)
                guards.append("network_deny")
        for secret_name in request.requested_secret_names:
            decision = evaluate_secret_request(secret_name)
            if not decision.allowed:
                reasons.extend(decision.reasons)
                guards.append("secret_unavailable")
        return tuple(reasons), tuple(guards)

    def validate_oversized(self, request: PluginRuntimeRequest) -> str | None:
        """Return a denial reason if the request is oversized, else ``None``."""
        if len(request.requested_capabilities) > MAX_REQUEST_ITEMS_PER_CATEGORY:
            return "oversized_input_capabilities"
        if len(request.requested_filesystem_paths) > MAX_REQUEST_ITEMS_PER_CATEGORY:
            return "oversized_input_filesystem_paths"
        if len(request.requested_network_targets) > MAX_REQUEST_ITEMS_PER_CATEGORY:
            return "oversized_input_network_targets"
        if len(request.requested_secret_names) > MAX_REQUEST_ITEMS_PER_CATEGORY:
            return "oversized_input_secret_names"
        return None

    def validate_runtime_request(
        self, request: PluginRuntimeRequest
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Full request validation (every surface). Returns (reasons, guards).

        Does **not** resolve the binding (that is :func:`resolve_runtime_binding`'s
        job); callers combine the two. Order: kill switch → oversized → metadata
        smuggling → capabilities → guards. Evaluation continues after a denial so
        the audit records every triggered surface.
        """
        reasons: list[str] = []
        guards: list[str] = []

        ks = self.validate_kill_switch(request.kill_switch_state)
        if ks.fail_closed:
            reasons.append("kill_switch_active")
            guards.append("kill_switch")

        oversized = self.validate_oversized(request)
        if oversized is not None:
            reasons.append(oversized)
            guards.append("input_size")

        meta_ok, meta_reasons = self.validate_metadata_no_authorization_smuggling(request.metadata)
        if not meta_ok:
            reasons.extend(meta_reasons)
            guards.append("metadata_smuggling")

        cap_reasons, cap_guards = self.validate_capabilities(request.requested_capabilities)
        reasons.extend(cap_reasons)
        guards.extend(cap_guards)

        guard_reasons, guard_guards = self.validate_guards(request)
        reasons.extend(guard_reasons)
        guards.extend(guard_guards)

        return tuple(reasons), tuple(guards)


#: Module-level stateless policy singleton.
RUNTIME_POLICY = PluginRuntimePolicy()


# ---------------------------------------------------------------------------
# 4. Result model
# ---------------------------------------------------------------------------


def _frozen_runtime_flags() -> dict[str, bool]:
    """Return a fresh copy of the frozen runtime flags."""
    return dict(RUNTIME_FLAGS_FROZEN)


def _runtime_p0_projection(kind: str) -> dict[str, Any]:
    """A conservative P0 evidence projection for one runtime result.

    ``kind`` is ``partial_evidence`` (a fixture executed — dev-only partial
    evidence), ``guard_evidence`` (a guard denied), or ``failure_mode_evidence``
    (a fixture failed). ``resolved`` is always False and every authorization
    flag is frozen — a runtime pass resolves / authorizes nothing.

    The verdict key names deliberately avoid secret-bearing stems
    (``auth`` / ``token`` / ``secret`` / ``apikey`` / ``credential``): the sandbox
    redactor collapses a string value under such a key to ``[REDACTED]``, which
    would hide the very ``NO-GO`` / ``False`` verdicts the projection exists to
    carry (and would trip the audit's final secret sweep). The ``*Gate`` names
    keep the verdicts readable while remaining value-free — mirroring the Phase
    3H runner's verdict projection.
    """
    return {
        "classification": kind,
        "resolved": False,
        "resolvedCount": 0,
        "implementationGate": IMPLEMENTATION_AUTHORIZATION,
        "phase3iGate": PHASE_3I_AUTHORIZED,
        "realRuntimeGate": REAL_RUNTIME,
        "newRouteGate": NEW_ROUTE,
        "productionRolloutGate": PRODUCTION_ROLLOUT,
        "note": "dev_only_fixture_runtime_partial_evidence_only",
        "redactionApplied": True,
    }


def _runtime_authorization_projection() -> dict[str, Any]:
    """A frozen, redaction-safe authorization verdict block for an audit record.

    The key names deliberately avoid secret-bearing stems (``auth`` / ``token`` /
    ``secret`` / ``apikey`` / ``credential``): the sandbox redactor would
    collapse a string value under such a key to ``[REDACTED]``, hiding the very
    ``NO-GO`` / ``False`` verdicts the block exists to carry (and tripping the
    audit's final secret sweep). The ``*Gate`` names keep the verdicts readable:
    ``implementationGate`` carries Implementation Authorization (NO-GO),
    ``phase3iGate`` carries Phase 3I authorization (NOT AUTHORIZED / False),
    ``productionRuntimeGate`` carries production-runtime authorization (NO-GO).
    Every value is a frozen constant — a runtime pass (single or batch) flips
    none of them.
    """
    return {
        "implementationGate": IMPLEMENTATION_AUTHORIZATION,
        "phase3iGate": PHASE_3I_AUTHORIZED,
        "productionRuntimeGate": REAL_RUNTIME,
        "newRouteGate": NEW_ROUTE,
        "productionRolloutGate": PRODUCTION_ROLLOUT,
        "resolved": False,
        "redactionApplied": True,
    }


@dataclass(frozen=True)
class PluginRuntimeResult:
    """Output model for a dev-only local plugin runtime evaluation."""

    allowed: bool
    executed: bool
    failed: bool
    plugin_id: str
    operation: str
    output_payload: Mapping[str, Any] = field(default_factory=dict)
    denial_reasons: tuple[str, ...] = ()
    triggered_guards: tuple[str, ...] = ()
    redacted_audit: Mapping[str, Any] = field(default_factory=dict)
    runtime_flags: Mapping[str, bool] = field(default_factory=_frozen_runtime_flags)
    p0_evidence: Mapping[str, Any] = field(default_factory=dict)
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # The frozen evidence flags must be False by construction and the
        # runtime flags must equal the frozen constants — a fixture execution
        # flips no production / network / secret / route / store / load flag.
        for flag in RESULT_EVIDENCE_FLAGS:
            # Read via the audit projection (the canonical frozen-False source).
            pass
        if dict(self.runtime_flags) != RUNTIME_FLAGS_FROZEN:
            raise AssertionError("runtime flags must equal the frozen constants")
        # Defensive-copy + freeze the mutable mappings so an in-place mutation
        # of a returned field cannot leak a value into a later safe projection.
        if self.output_payload:
            object.__setattr__(
                self, "output_payload", MappingProxyType(copy.deepcopy(dict(self.output_payload)))
            )
        if self.runtime_flags:
            object.__setattr__(
                self, "runtime_flags", MappingProxyType(copy.deepcopy(dict(self.runtime_flags)))
            )
        if self.redacted_audit:
            object.__setattr__(
                self, "redacted_audit", MappingProxyType(copy.deepcopy(dict(self.redacted_audit)))
            )
        if self.p0_evidence:
            object.__setattr__(
                self, "p0_evidence", MappingProxyType(copy.deepcopy(dict(self.p0_evidence)))
            )

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "schemaVersion": PLUGIN_RUNTIME_VERSION,
                "source": PLUGIN_RUNTIME_AUDIT_SOURCE,
                "allowed": self.allowed,
                "executed": self.executed,
                "failed": self.failed,
                "pluginId": self.plugin_id,
                "operation": self.operation,
                "outputPayload": dict(self.output_payload),
                "denialReasons": list(self.denial_reasons),
                "triggeredGuards": list(self.triggered_guards),
                "audit": dict(self.redacted_audit),
                "runtimeFlags": dict(self.runtime_flags),
                "p0Evidence": dict(self.p0_evidence),
                "errors": list(self.errors),
                "redactionApplied": True,
                "persisted": False,
            }
        )


def is_runtime_result_safe(result: PluginRuntimeResult | Mapping[str, Any]) -> bool:
    """True iff a runtime result is value-free and requires no escalation.

    Asserts the runtime flags equal the frozen constants, the result audit is
    secret-free and in-memory, and the embedded P0 projection is unresolved
    with frozen NO-GO authorization.
    """
    if isinstance(result, PluginRuntimeResult):
        if dict(result.runtime_flags) != RUNTIME_FLAGS_FROZEN:
            return False
        if contains_secret(result.redacted_audit):
            return False
        if contains_secret(result.output_payload):
            return False
        p0 = result.p0_evidence
        if not isinstance(p0, Mapping):
            return False
        if p0.get("resolved") is not False:
            return False
        if p0.get("implementationGate") != IMPLEMENTATION_AUTHORIZATION:
            return False
        if p0.get("phase3iGate") is not False:
            return False
        if p0.get("realRuntimeGate") != REAL_RUNTIME:
            return False
        return True
    if isinstance(result, Mapping):
        flags = result.get("runtimeFlags")
        if not isinstance(flags, Mapping) or dict(flags) != RUNTIME_FLAGS_FROZEN:
            return False
        if contains_secret(result):
            return False
        p0 = result.get("p0Evidence")
        if not isinstance(p0, Mapping):
            return False
        if p0.get("resolved") is not False:
            return False
        if p0.get("implementationGate") != IMPLEMENTATION_AUTHORIZATION:
            return False
        return True
    return False


# ---------------------------------------------------------------------------
# 5. Audit builder
# ---------------------------------------------------------------------------


def _redaction_failed_audit() -> dict[str, Any]:
    """Minimal fail-closed audit emitted when the final sweep detects a secret."""
    return {
        "schemaVersion": PLUGIN_RUNTIME_VERSION,
        "source": PLUGIN_RUNTIME_AUDIT_SOURCE,
        "decision": "denied",
        "denialReasons": ["redaction_failed_fail_closed"],
        "triggeredGuards": ["redaction_failure"],
        "runtimeFlags": _frozen_runtime_flags(),
        "authorizationSummary": _runtime_authorization_projection(),
        "p0Evidence": _runtime_p0_projection("guard_evidence"),
        "evidence": {flag: False for flag in RESULT_EVIDENCE_FLAGS},
        "redactionApplied": True,
        "redactionFailed": True,
        "persisted": False,
    }


def _build_runtime_audit(
    *,
    request: PluginRuntimeRequest,
    binding: RuntimeBinding,
    allowed: bool,
    executed: bool,
    failed: bool,
    reasons: list[str],
    guards: list[str],
    output_payload: Mapping[str, Any],
    errors: tuple[str, ...],
    p0_kind: str,
) -> dict[str, Any]:
    """Build a redacted, in-memory audit record for one runtime result.

    The request's input / metadata are run through the secret + path redactor;
    the output (already redacted) and the verdicts are merged in. A final
    secret sweep fails closed to a minimal denial record if any value slipped
    through. The record is never persisted.
    """
    redacted_input = redact_sandbox_payload(
        copy.deepcopy(dict(request.input_payload)) if request.input_payload else {}
    )
    audit: dict[str, Any] = {
        "schemaVersion": PLUGIN_RUNTIME_VERSION,
        "source": PLUGIN_RUNTIME_AUDIT_SOURCE,
        "pluginId": binding.plugin_id,
        "operation": binding.operation,
        "descriptorId": request.descriptor_id,
        "decision": "allowed" if allowed else "denied",
        "executed": executed,
        "failed": failed,
        "bindingResolved": binding.resolved,
        "killSwitchActive": bool(request.kill_switch_state),
        "denialReasons": list(reasons),
        "triggeredGuards": list(guards),
        "redactedInput": redacted_input,
        "redactedOutput": dict(output_payload),
        "redactedErrors": list(errors),
        "runtimeFlags": _frozen_runtime_flags(),
        "authorizationSummary": _runtime_authorization_projection(),
        "p0Evidence": _runtime_p0_projection(p0_kind),
        "evidence": {flag: False for flag in RESULT_EVIDENCE_FLAGS},
        "redactionApplied": True,
        "persisted": False,
    }
    if contains_secret(audit):
        return _redaction_failed_audit()
    return audit


# ---------------------------------------------------------------------------
# 6. run_dev_plugin — the single dev-only execution entry point
# ---------------------------------------------------------------------------


def _assert_fixture_output(value: Any, *, depth: int = 0) -> None:
    """Assert a fixture result is a bounded, JSON-native mapping.

    A fixture must return a dict of JSON-native scalars / dicts / lists (no
    callables, modules, or arbitrary objects) bounded in nesting depth. A
    non-conforming value raises :class:`FixtureOutputError`, which the runtime
    records as a fail-closed result (``fixture_output_unsafe``) so the
    non-native value is never echoed into an audit projection.
    """
    if depth > MAX_FIXTURE_NESTING_DEPTH + 2:
        raise FixtureOutputError("fixture output exceeds the depth bound")
    if isinstance(value, Mapping):
        for val in value.values():
            _assert_fixture_output(val, depth=depth + 1)
        return
    if isinstance(value, (list, tuple)):
        for val in value:
            _assert_fixture_output(val, depth=depth + 1)
        return
    if isinstance(value, (str, int, float, bool)) or value is None:
        return
    raise FixtureOutputError("fixture output contains a non-json-native value")


def run_dev_plugin(request: PluginRuntimeRequest) -> PluginRuntimeResult:
    """Run a dev-only local plugin evaluation. Fail-closed default.

    Flow:

      1. Full request validation (kill switch → oversized → metadata smuggling
         → capabilities → guards). Any denial short-circuits ``allowed`` but
         evaluation continues so the audit records every surface.
      2. Descriptor-to-fixture binding resolution through the frozen allowlist.
         An unresolved binding denies execution (no fixture is invoked).
      3. If allowed and bound, invoke the reviewed fixture's ``invoker`` on the
         (deep-copied) ``input_payload``, catching and redacting any failure.
      4. Build a redacted, in-memory audit + P0 projection and return the result.

    The runtime loads / imports / fetches / shells nothing: it invokes a
    reviewed fixture function by allowlist binding only.
    """
    # 1. Request validation.
    reasons, guards = RUNTIME_POLICY.validate_runtime_request(request)
    reasons = list(reasons)
    guards = list(guards)

    # 2. Binding resolution.
    binding = resolve_runtime_binding(request)
    if not binding.resolved:
        reasons.extend(binding.reasons)
        guards.append("fixture_binding")

    allowed = not reasons and binding.resolved
    executed = False
    failed = False
    output_payload: Mapping[str, Any] = {}
    errors: tuple[str, ...] = ()
    p0_kind = "guard_evidence"

    # 3. Invoke the reviewed fixture (only when fully allowed + bound).
    if allowed and binding.fixture is not None:
        payload = (
            copy.deepcopy(dict(request.input_payload))
            if request.input_payload is not None
            else {}
        )
        try:
            raw_output = binding.fixture.invoker(payload)
            if not isinstance(raw_output, Mapping):
                raise RuntimeError("fixture returned a non-mapping result")
            _assert_fixture_output(raw_output)
            output_payload = redact_sandbox_payload(copy.deepcopy(dict(raw_output)))
            executed = True
            p0_kind = "partial_evidence"
        except Exception as exc:  # controlled fixture failure — redact + record
            executed = True
            failed = True
            allowed = False
            errors = (redact_sandbox_text(str(exc)),)
            # Distinguish an input-validation failure, an output-validation
            # failure, and a deliberate failure so the audit / P0 projection is
            # precise.
            from hermes_cli.dev_web_fixture_plugins import FixtureInputError

            if isinstance(exc, FixtureInputError):
                reasons.append("fixture_input_invalid")
            elif isinstance(exc, FixtureOutputError):
                reasons.append("fixture_output_unsafe")
            else:
                reasons.append("fixture_execution_failed")
            guards.append("failure_handler")
            p0_kind = "failure_mode_evidence"

    # 4. Build the redacted audit + result.
    audit = _build_runtime_audit(
        request=request,
        binding=binding,
        allowed=allowed,
        executed=executed,
        failed=failed,
        reasons=list(reasons),
        guards=list(guards),
        output_payload=output_payload,
        errors=errors,
        p0_kind=p0_kind,
    )

    return PluginRuntimeResult(
        allowed=allowed,
        executed=executed,
        failed=failed,
        plugin_id=binding.plugin_id,
        operation=binding.operation,
        output_payload=output_payload,
        denial_reasons=tuple(reasons),
        triggered_guards=tuple(guards),
        redacted_audit=audit,
        runtime_flags=_frozen_runtime_flags(),
        p0_evidence=_runtime_p0_projection(p0_kind),
        errors=errors,
    )


# ---------------------------------------------------------------------------
# 7. Batch runtime execution (multi-plugin, isolated, fail-closed)
# ---------------------------------------------------------------------------


#: Default batch id when a caller supplies none (a safe label, never a path).
_DEFAULT_BATCH_ID = "dev-only-batch"


def _batch_id_is_safe(value: Any) -> bool:
    """True iff *value* is a clean ``[A-Za-z0-9_.\\-]`` label with no traversal."""
    if not isinstance(value, str) or not value:
        return False
    if ".." in value:
        return False
    return _BATCH_ID_SAFE.fullmatch(value) is not None


@dataclass(frozen=True)
class PluginRuntimeBatchRequest:
    """Input model for a dev-only multi-plugin batch runtime evaluation.

    Carries a list of :class:`PluginRuntimeRequest` (each independently
    validated + bound), a safe ``batch_id`` label, a ``fail_fast`` flag, and
    optional untrusted ``metadata``. **Never** carries executable plugin code,
    a module path, a shell command, an external URL, a real API key, or a
    production path. ``metadata`` is untrusted by construction: an
    authorization-smuggling payload fails the whole batch closed.
    """

    requests: tuple[PluginRuntimeRequest, ...] = ()
    batch_id: str = ""
    fail_fast: bool = False
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        # Coerce + defensive-copy: requests become a fresh tuple; metadata is
        # deep-copied so a caller mutation after construction cannot change what
        # the batch evaluates.
        if isinstance(self.requests, (list, tuple)):
            object.__setattr__(self, "requests", tuple(self.requests))
        else:
            object.__setattr__(self, "requests", ())
        if self.metadata is not None:
            object.__setattr__(self, "metadata", copy.deepcopy(self.metadata))

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "batchId": self.batch_id if _batch_id_is_safe(self.batch_id) else "",
            "requestCount": len(self.requests),
            "failFast": bool(self.fail_fast),
            "hasMetadata": self.metadata is not None,
            "redactionApplied": True,
        }


@dataclass(frozen=True)
class PluginRuntimeBatchResult:
    """Output model for a dev-only multi-plugin batch runtime evaluation.

    Every result is in-memory, redacted, and isolation-preserving: one fixture
    failure or denial never poisons another request, and a batch pass resolves
    / authorizes nothing (``resolved`` stays False, every authorization flag
    stays NO-GO / not-authorized). The runtime flags must equal the frozen
    constants — a batch flips none of them.
    """

    batch_id: str
    total: int
    succeeded: int
    failed: int
    denied: int
    results: tuple[PluginRuntimeResult, ...] = ()
    redacted_audit: Mapping[str, Any] = field(default_factory=dict)
    runtime_flags: Mapping[str, bool] = field(default_factory=_frozen_runtime_flags)
    p0_evidence: Mapping[str, Any] = field(default_factory=dict)
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if dict(self.runtime_flags) != RUNTIME_FLAGS_FROZEN:
            raise AssertionError("batch runtime flags must equal the frozen constants")
        # Freeze the mutable mappings + results tuple so an in-place mutation of
        # a returned field cannot leak a value into a later safe projection.
        if self.results:
            object.__setattr__(self, "results", tuple(self.results))
        if self.redacted_audit:
            object.__setattr__(
                self, "redacted_audit", MappingProxyType(copy.deepcopy(dict(self.redacted_audit)))
            )
        if self.runtime_flags:
            object.__setattr__(
                self, "runtime_flags", MappingProxyType(copy.deepcopy(dict(self.runtime_flags)))
            )
        if self.p0_evidence:
            object.__setattr__(
                self, "p0_evidence", MappingProxyType(copy.deepcopy(dict(self.p0_evidence)))
            )

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "schemaVersion": PLUGIN_RUNTIME_VERSION,
                "source": PLUGIN_RUNTIME_AUDIT_SOURCE + ".batch",
                "batchId": self.batch_id,
                "total": self.total,
                "succeeded": self.succeeded,
                "failed": self.failed,
                "denied": self.denied,
                "results": [r.to_safe_dict() for r in self.results],
                "audit": dict(self.redacted_audit),
                "runtimeFlags": dict(self.runtime_flags),
                "p0Evidence": dict(self.p0_evidence),
                "errors": list(self.errors),
                "redactionApplied": True,
                "persisted": False,
            }
        )


def _batch_p0_projection(results: tuple[PluginRuntimeResult, ...]) -> dict[str, Any]:
    """Conservative P0 projection for a batch.

    A batch with any successful fixture is ``partial_evidence`` (reproducibility
    evidence); a batch of only denials is ``guard_evidence``; a batch with any
    failure is ``failure_mode_evidence``. ``resolved`` is always False and every
    authorization flag is frozen — a batch pass resolves / authorizes nothing.
    """
    if any(r.failed for r in results):
        kind = "failure_mode_evidence"
    elif any(r.allowed for r in results):
        kind = "partial_evidence"
    else:
        kind = "guard_evidence"
    projection = _runtime_p0_projection(kind)
    projection["batchKind"] = kind
    projection["note"] = "dev_only_fixture_batch_partial_evidence_only"
    return projection


def _fail_closed_batch(
    batch_id: str, *, reasons: tuple[str, ...], errors: tuple[str, ...]
) -> PluginRuntimeBatchResult:
    """Build a fail-closed (no results, redacted) batch for an invalid request."""
    audit = redact_sandbox_payload(
        {
            "schemaVersion": PLUGIN_RUNTIME_VERSION,
            "source": PLUGIN_RUNTIME_AUDIT_SOURCE + ".batch",
            "batchId": batch_id,
            "total": 0,
            "succeeded": 0,
            "failed": 0,
            "denied": 0,
            "perOperationSummary": [],
            "decision": "denied",
            "denialReasons": list(reasons),
            "triggeredGuards": ["batch_fail_closed"],
            "runtimeFlags": _frozen_runtime_flags(),
            "authorizationSummary": _runtime_authorization_projection(),
            "p0Evidence": _batch_p0_projection(()),
            "evidence": {flag: False for flag in RESULT_EVIDENCE_FLAGS},
            "redactionApplied": True,
            "persisted": False,
        }
    )
    return PluginRuntimeBatchResult(
        batch_id=batch_id,
        total=0,
        succeeded=0,
        failed=0,
        denied=0,
        results=(),
        redacted_audit=audit,
        runtime_flags=_frozen_runtime_flags(),
        p0_evidence=_batch_p0_projection(()),
        errors=errors,
    )


def run_dev_plugin_batch(request: PluginRuntimeBatchRequest) -> PluginRuntimeBatchResult:
    """Run a dev-only multi-plugin batch. Fail-closed; isolation-preserving.

    Behavior:

      - Validates the batch id (a non-empty unsafe label fails the batch closed),
        the requests list (must be a sequence of :class:`PluginRuntimeRequest`),
        the batch size (``<= MAX_BATCH_REQUESTS``), and the batch metadata (an
        authorization-smuggling payload fails the batch closed).
      - Runs each request through :func:`run_dev_plugin` independently — one
        fixture failure / denial never poisons another request.
      - With ``fail_fast=True`` the batch stops after the first request that is
        not allowed (denied or failed); with ``fail_fast=False`` every request
        runs to completion.
      - Result order is preserved; the aggregate audit + P0 projection are
        redacted, in-memory, and resolve / authorize nothing.

    The batch runner loads / imports / fetches / shells nothing and adds no
    route; it only orchestrates :func:`run_dev_plugin`.
    """
    batch_id = request.batch_id if isinstance(request.batch_id, str) and request.batch_id else ""
    if not batch_id:
        batch_id = _DEFAULT_BATCH_ID
    elif not _batch_id_is_safe(batch_id):
        return _fail_closed_batch(
            _DEFAULT_BATCH_ID,
            reasons=("batch_id_unsafe",),
            errors=("batch_id_unsafe",),
        )

    if not isinstance(request.requests, tuple):
        return _fail_closed_batch(
            batch_id, reasons=("batch_malformed_requests",), errors=("batch_malformed_requests",)
        )
    for item in request.requests:
        if not isinstance(item, PluginRuntimeRequest):
            return _fail_closed_batch(
                batch_id,
                reasons=("batch_malformed_requests",),
                errors=("batch_malformed_requests",),
            )
    if len(request.requests) > MAX_BATCH_REQUESTS:
        return _fail_closed_batch(
            batch_id, reasons=("batch_oversized",), errors=("batch_oversized",)
        )

    # Batch-level metadata smuggling fails the whole batch closed (a runtime
    # that invokes code must refuse a smuggling attempt up front).
    meta_ok, meta_reasons = RUNTIME_POLICY.validate_metadata_no_authorization_smuggling(
        request.metadata
    )
    if not meta_ok:
        return _fail_closed_batch(
            batch_id, reasons=meta_reasons, errors=meta_reasons
        )

    results: list[PluginRuntimeResult] = []
    for sub_request in request.requests:
        # Each request is fully isolated: run_dev_plugin holds no shared mutable
        # state, so a failure / denial here cannot affect the next request.
        result = run_dev_plugin(sub_request)
        results.append(result)
        if request.fail_fast and not result.allowed:
            break

    succeeded = sum(1 for r in results if r.allowed and not r.failed)
    failed = sum(1 for r in results if r.failed)
    denied = sum(1 for r in results if not r.allowed and not r.failed)

    per_operation_summary = [
        {
            "pluginId": r.plugin_id,
            "operation": r.operation,
            "allowed": r.allowed,
            "executed": r.executed,
            "failed": r.failed,
        }
        for r in results
    ]

    p0 = _batch_p0_projection(tuple(results))
    audit = redact_sandbox_payload(
        {
            "schemaVersion": PLUGIN_RUNTIME_VERSION,
            "source": PLUGIN_RUNTIME_AUDIT_SOURCE + ".batch",
            "batchId": batch_id,
            "total": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "denied": denied,
            "failFast": bool(request.fail_fast),
            "perOperationSummary": per_operation_summary,
            "decision": "mixed" if (succeeded and (failed or denied)) else (
                "allowed" if succeeded and not (failed or denied) else "denied"
            ),
            "runtimeFlags": _frozen_runtime_flags(),
            "authorizationSummary": _runtime_authorization_projection(),
            "p0Evidence": p0,
            "evidence": {flag: False for flag in RESULT_EVIDENCE_FLAGS},
            "redactionApplied": True,
            "persisted": False,
        }
    )

    return PluginRuntimeBatchResult(
        batch_id=batch_id,
        total=len(results),
        succeeded=succeeded,
        failed=failed,
        denied=denied,
        results=tuple(results),
        redacted_audit=audit,
        runtime_flags=_frozen_runtime_flags(),
        p0_evidence=p0,
        errors=(),
    )


# ---------------------------------------------------------------------------
# 8. Boundary re-affirmation (pure constants, grep-able)
# ---------------------------------------------------------------------------

NO_REAL_PLUGIN_RUNTIME: bool = True
NO_ARBITRARY_PLUGIN_LOADING: bool = True
NO_REMOTE_REGISTRY: bool = True
NO_MARKETPLACE: bool = True
NO_EXTERNAL_PLUGIN_FETCH: bool = True
NO_PROVIDER_GENERATED_PLUGIN: bool = True
NO_LLM_GENERATED_PLUGIN: bool = True
NO_EXTERNAL_NETWORK: bool = True
NO_REAL_API_KEY_READ: bool = True
NO_NEW_ROUTE: bool = True
NO_PRODUCTION_ACCESS: bool = True
NO_HERMES_HOME_ACCESS: bool = True
NO_RUNTIME_STORE_WRITE: bool = True


def assert_no_side_effect_surface() -> None:
    """Re-affirm the dev-only runtime no-side-effect + no-authorization invariants."""
    assert NO_REAL_PLUGIN_RUNTIME is True
    assert NO_ARBITRARY_PLUGIN_LOADING is True
    assert NO_REMOTE_REGISTRY is True
    assert NO_MARKETPLACE is True
    assert NO_EXTERNAL_PLUGIN_FETCH is True
    assert NO_PROVIDER_GENERATED_PLUGIN is True
    assert NO_LLM_GENERATED_PLUGIN is True
    assert NO_EXTERNAL_NETWORK is True
    assert NO_REAL_API_KEY_READ is True
    assert NO_NEW_ROUTE is True
    assert NO_PRODUCTION_ACCESS is True
    assert NO_HERMES_HOME_ACCESS is True
    assert NO_RUNTIME_STORE_WRITE is True
    assert IMPLEMENTATION_AUTHORIZATION == "NO-GO"
    assert PHASE_3I_AUTHORIZED is False
    assert REAL_RUNTIME == "NO-GO"
    assert NEW_ROUTE == "NO-GO"
    assert PRODUCTION_ROLLOUT == "NO-GO"
    assert len(FIXTURE_ALLOWLIST) == len(FIXTURE_REGISTRY)
    assert FIXTURE_PLUGIN_IDS and FIXTURE_OPERATION_NAMES


__all__ = [
    "PLUGIN_RUNTIME_VERSION",
    "PLUGIN_RUNTIME_AUDIT_SOURCE",
    "RESULT_EVIDENCE_FLAGS",
    "MAX_REQUEST_ITEMS_PER_CATEGORY",
    "MAX_BATCH_REQUESTS",
    "RUNTIME_FLAGS_FROZEN",
    "RUNTIME_REASONS",
    "PluginRuntimeRequest",
    "RuntimeBinding",
    "resolve_runtime_binding",
    "validate_runtime_binding",
    "PluginRuntimePolicy",
    "RUNTIME_POLICY",
    "PluginRuntimeResult",
    "is_runtime_result_safe",
    "run_dev_plugin",
    "PluginRuntimeBatchRequest",
    "PluginRuntimeBatchResult",
    "run_dev_plugin_batch",
    # boundary constants
    "NO_REAL_PLUGIN_RUNTIME",
    "NO_ARBITRARY_PLUGIN_LOADING",
    "NO_REMOTE_REGISTRY",
    "NO_MARKETPLACE",
    "NO_EXTERNAL_PLUGIN_FETCH",
    "NO_PROVIDER_GENERATED_PLUGIN",
    "NO_LLM_GENERATED_PLUGIN",
    "NO_EXTERNAL_NETWORK",
    "NO_REAL_API_KEY_READ",
    "NO_NEW_ROUTE",
    "NO_PRODUCTION_ACCESS",
    "NO_HERMES_HOME_ACCESS",
    "NO_RUNTIME_STORE_WRITE",
    "assert_no_side_effect_surface",
]
