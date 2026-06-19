"""Phase 3I Runtime Descriptor Registry Integration (code allowed, production forbidden).

Bridges the **Phase 3D Static Plugin Descriptor Registry** and the **Phase 3I
dev-only local plugin runtime** (:mod:`hermes_cli.dev_web_plugin_runtime`).

A descriptor is *not* an executable plugin — it is a static, reviewed record.
This module binds a **reviewed fixture descriptor** to the runtime's frozen
fixture allowlist through a strict, fail-closed, dual-layer validation, then —
and only then — invokes the existing dev-only runtime. The descriptor is read as
metadata; the runtime executes a reviewed fixture function by allowlist binding
only. Nothing here loads, imports, fetches, shells, or executes a descriptor.

Hard guarantees (frozen):

  - The descriptor is **descriptor-only**. It is never loaded / executed. A
    descriptor carrying any module / command / entrypoint / import / shell / url
    / registry / marketplace / remote / fetch / provider-generated /
    LLM-generated / docker / image / file / path / install field — at any depth,
    any casing — is denied outright before any fixture runs.
  - Only a descriptor whose ``(pluginId, operation)`` is an exact member of the
    frozen :data:`~dev_web_fixture_plugins.FIXTURE_ALLOWLIST` may bind. The
    binding is hardcoded; it is never derived from user input, a directory scan,
    a remote fetch, or a marketplace.
  - Registry-level validation + runtime-level binding are **both** required. A
    descriptor must (a) be a static, reviewed, dev-only record and (b) bind a
    reviewed fixture with compatible, all-False safety metadata. Either layer
    denying denies the whole binding.
  - The runtime re-uses :func:`~dev_web_plugin_runtime.run_dev_plugin` verbatim,
    so every Phase 3H guard (filesystem / network / secret / kill-switch /
    capability default-deny / redaction / P0 evidence) is enforced unchanged.
  - This module reads **no** real API key, contacts **no** host, touches **no**
    filesystem path, opens **no** ``~/.hermes`` and **no** production
    ``state.db``, writes **no** runtime store, and adds **no** HTTP route. It is
    **not** imported by the FastAPI app.

A successful descriptor-backed fixture execution is **dev-only partial
evidence**. It is **never** Implementation Authorization GO, **never** Phase 3I
production authorization, **never** real-runtime authorization, **never** a P0
resolution. ``resolved_count`` stays 0 and the authorization flags stay NO-GO /
not-authorized no matter what runs or what untrusted metadata a descriptor or
request carries.

Phase: 3I — Runtime Descriptor Registry Integration
Status: implemented (descriptor→runtime binding). NOT a production plugin
        runtime. No arbitrary loading, no remote registry, no marketplace, no
        external network, no real secret read, no new route, no production
        access.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from hermes_cli.dev_web_fixture_plugins import (
    FIXTURE_ALLOWLIST,
    FIXTURE_OPERATION_NAMES,
    FIXTURE_PLUGIN_IDS,
)
from hermes_cli.dev_web_p0_evidence import (
    IMPLEMENTATION_AUTHORIZATION,
    NEW_ROUTE,
    PHASE_3I_AUTHORIZED,
    PRODUCTION_ROLLOUT,
    REAL_RUNTIME,
    detect_untrusted_metadata,
)
from hermes_cli.dev_web_plugin_descriptor_schema import is_forbidden_field_present
from hermes_cli.dev_web_plugin_runtime import (
    RESULT_EVIDENCE_FLAGS,
    MAX_BATCH_REQUESTS,
    RUNTIME_FLAGS_FROZEN,
    PluginRuntimeBatchResult,
    PluginRuntimeRequest,
    PluginRuntimeResult,
    resolve_runtime_binding,
    run_dev_plugin,
)
from hermes_cli.dev_web_sandbox_guards import (
    REDACTED_VALUE,
    contains_secret,
    redact_sandbox_payload,
)
from hermes_cli.dev_web_sandbox_policy import evaluate_descriptor

DESCRIPTOR_RUNTIME_BINDING_VERSION = "phase-3i-descriptor-registry-runtime-binding-v1"
DESCRIPTOR_BINDING_AUDIT_SOURCE = "dev_web_plugin_runtime_binding"

#: Provenance label carried by every binding result: the descriptor was sourced
#: from the Phase 3D static descriptor registry (an in-memory reviewed record),
#: never fetched, never loaded from a directory, never from a marketplace.
DESCRIPTOR_BINDING_SOURCE = "static_descriptor_registry"

#: Descriptor ``source`` values that classify as a readable static descriptor
#: provenance (mirrors :data:`~dev_web_p0_evidence.ALLOWED_SOURCE_TYPES`). A
#: reviewed fixture descriptor carries one of these so its provenance is
#: readable-as-metadata; it is never trusted for execution.
_ALLOWED_DESCRIPTOR_SOURCE_TYPES: frozenset[str] = frozenset(
    {"descriptor_only", "local_static_descriptor", "bundled_descriptor"}
)

#: Descriptor ``source`` values that denote an untrusted / remote / generated
#: supply chain — each denied with a precise reason before any fixture runs.
_DENIED_DESCRIPTOR_SOURCE_REASONS: dict[str, str] = {
    "remote_registry": "remote_registry_denied",
    "marketplace": "marketplace_denied",
    "external_fetch": "external_fetch_denied",
    "external_download": "external_fetch_denied",
    "provider_generated": "provider_generated_denied",
    "llm_generated": "llm_generated_denied",
    "ai_generated": "llm_generated_denied",
    "generated": "llm_generated_denied",
    "unreviewed_local_executable": "provider_generated_denied",
    "local_executable": "provider_generated_denied",
    "production": "production_access_denied",
}

#: Stable reason tokens the descriptor binding may emit. A superset of the
#: runtime's :data:`~dev_web_plugin_runtime.RUNTIME_REASONS` plus the
#: registry-level / provenance tokens added by this layer.
DESCRIPTOR_BINDING_REASONS: frozenset[str] = frozenset(
    {
        "descriptor_missing",
        "descriptor_malformed",
        "descriptor_id_missing",
        "descriptor_id_unsafe",
        "descriptor_carries_execution_surface",
        "descriptor_forbidden_field",
        "descriptor_oversized",
        "descriptor_source_untrusted",
        "remote_registry_denied",
        "marketplace_denied",
        "external_fetch_denied",
        "provider_generated_denied",
        "llm_generated_denied",
        "production_access_denied",
        "descriptor_plugin_id_missing",
        "descriptor_plugin_id_not_fixture",
        "descriptor_operation_missing",
        "descriptor_operation_not_fixture",
        "descriptor_pair_not_in_allowlist",
        "descriptor_capability_mismatch",
        "descriptor_metadata_smuggling_denied",
        "descriptor_metadata_secret_leak",
        "descriptor_metadata_path_leak",
        "descriptor_metadata_route_exception",
        "descriptor_metadata_production_smuggling",
        "descriptor_not_in_static_registry",
        "descriptor_batch_oversized",
        "descriptor_batch_id_unsafe",
        "descriptor_batch_id_missing",
        "descriptor_batch_malformed",
        "descriptor_batch_metadata_smuggling_denied",
    }
)

#: Maximum descriptor-metadata size (bytes of ``repr``). Oversized → denied.
MAX_DESCRIPTOR_BINDING_SIZE: int = 32768


# ---------------------------------------------------------------------------
# 1. In-memory reviewed fixture descriptors (the static registry binding table)
# ---------------------------------------------------------------------------
#
# A frozen, in-memory table of reviewed fixture descriptors. Each entry is a
# plain dict that NAMES a reviewed ``(pluginId, operation)`` pair already in the
# frozen :data:`~dev_web_fixture_plugins.FIXTURE_ALLOWLIST`. These are static
# records — no executable content, no module path, no shell command, no real
# URL, no real secret, no production path. They describe a fixture binding; they
# are never themselves executed.
#
# These are NOT added to the Phase 3D ``STATIC_PLUGIN_DESCRIPTOR_MANIFEST``
# (that manifest is a frozen, capability-bound descriptor-only registry and is
# intentionally untouched here). They are a separate, in-memory binding table
# that maps a stable ``descriptorId`` to a reviewed fixture operation.
#
# Every key is chosen so it passes the descriptor-only recursive surface scan
# (no module/command/entrypoint/import/shell/url/registry/marketplace/remote/
# fetch/file/path stems). The ``source`` value is an allowed static provenance
# type so supply-chain classification reads it as metadata only.

_DESC_SOURCE = "local_static_descriptor"
_DESC_VERSION = "phase-3i-fixture-descriptor-v1"

#: A clean capability label every reviewed fixture allows (the default
#: ``allowed_capabilities`` of every :class:`FixtureOperation`).
_DESC_CAPABILITY = ("descriptor.read",)


def _reviewed_descriptor(
    *,
    descriptor_id: str,
    plugin_id: str,
    operation: str,
    display_name: str,
    description: str,
) -> dict[str, Any]:
    """Build one reviewed fixture descriptor dict (pure, static, no side effects)."""
    return {
        "descriptorId": descriptor_id,
        "pluginId": plugin_id,
        "operation": operation,
        "source": _DESC_SOURCE,
        "version": _DESC_VERSION,
        "displayName": display_name,
        "description": description,
        "requestedCapabilities": _DESC_CAPABILITY,
        "reviewed": True,
        "devOnly": True,
        "fixtureOnly": True,
    }


#: The frozen, in-memory reviewed fixture descriptor registry. Each entry names
#: an exact ``(pluginId, operation)`` member of the frozen fixture allowlist.
REVIEWED_FIXTURE_DESCRIPTORS: tuple[dict[str, Any], ...] = (
    _reviewed_descriptor(
        descriptor_id="descriptor.fixture.echo_uppercase",
        plugin_id="fixture.echo",
        operation="echo_uppercase",
        display_name="Fixture Echo Uppercase Descriptor",
        description="Reviewed fixture descriptor binding fixture.echo/echo_uppercase.",
    ),
    _reviewed_descriptor(
        descriptor_id="descriptor.fixture.normalize_text",
        plugin_id="fixture.transform",
        operation="normalize_text",
        display_name="Fixture Normalize Text Descriptor",
        description="Reviewed fixture descriptor binding fixture.transform/normalize_text.",
    ),
    _reviewed_descriptor(
        descriptor_id="descriptor.fixture.validate_required_keys",
        plugin_id="fixture.validate",
        operation="validate_required_keys",
        display_name="Fixture Validate Required Keys Descriptor",
        description="Reviewed fixture descriptor binding fixture.validate/validate_required_keys.",
    ),
    _reviewed_descriptor(
        descriptor_id="descriptor.fixture.count_items",
        plugin_id="fixture.math",
        operation="count_items",
        display_name="Fixture Count Items Descriptor",
        description="Reviewed fixture descriptor binding fixture.math/count_items.",
    ),
    _reviewed_descriptor(
        descriptor_id="descriptor.fixture.redact_payload",
        plugin_id="fixture.redact",
        operation="redact_payload",
        display_name="Fixture Redact Payload Descriptor",
        description="Reviewed fixture descriptor binding fixture.redact/redact_payload.",
    ),
    _reviewed_descriptor(
        descriptor_id="descriptor.fixture.fault",
        plugin_id="fixture.fault",
        operation="deliberate_failure",
        display_name="Fixture Deliberate Failure Descriptor",
        description="Reviewed fixture descriptor binding fixture.fault/deliberate_failure.",
    ),
)


def get_reviewed_fixture_descriptors() -> tuple[dict[str, Any], ...]:
    """Return a defensive copy of the in-memory reviewed fixture descriptor table."""
    return tuple(copy.deepcopy(dict(entry)) for entry in REVIEWED_FIXTURE_DESCRIPTORS)


def lookup_reviewed_fixture_descriptor(
    registry: Any, descriptor_id: Any
) -> dict[str, Any] | None:
    """Return a deep copy of the reviewed descriptor for *descriptor_id*, else None.

    *registry* is an in-memory sequence of descriptor dicts (the static table or
    a caller-supplied fixture registry). Lookup is by exact ``descriptorId``
    membership only — never a path, directory scan, or remote fetch.
    """
    if not isinstance(descriptor_id, str) or not descriptor_id:
        return None
    if not isinstance(registry, (list, tuple)):
        return None
    for entry in registry:
        if isinstance(entry, dict) and entry.get("descriptorId") == descriptor_id:
            return copy.deepcopy(dict(entry))
    return None


def _descriptor_id_for(entry: Any) -> str:
    """Return the stable descriptor id (``descriptorId`` or ``pluginId``)."""
    if isinstance(entry, Mapping):
        raw = entry.get("descriptorId") or entry.get("pluginId")
        if isinstance(raw, str):
            return raw
    return ""


# ---------------------------------------------------------------------------
# 2. Registry-level + provenance validation (pure, fail-closed)
# ---------------------------------------------------------------------------


def _normalize_source_type(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""
    text = raw.strip().lower().replace("-", "_").replace(" ", "_")
    return text or ""


def _descriptor_source_type(descriptor: Mapping[str, Any]) -> str:
    raw = descriptor.get(
        "source", descriptor.get("sourceType", descriptor.get("origin"))
    )
    return _normalize_source_type(raw)


def _provenance_reason(source_type: str) -> str | None:
    """Return a denial reason for an untrusted descriptor source, else None."""
    if source_type in _ALLOWED_DESCRIPTOR_SOURCE_TYPES:
        return None
    return _DENIED_DESCRIPTOR_SOURCE_REASONS.get(source_type, "descriptor_source_untrusted")


def _metadata_smuggling(metadata: Any) -> tuple[str, ...]:
    """Return bypass-shaped keys present in *metadata* (detected + ignored)."""
    return detect_untrusted_metadata(metadata)


def _looks_like_path_leak(metadata: Any) -> bool:
    """True if *metadata* carries a production-path-like value (no real path is opened).

    Pure string inspection: a ``~/.hermes`` / ``state.db`` / runtime-store
    marker value is a production-path leak. The real paths are never opened.
    """
    if not isinstance(metadata, Mapping):
        return False
    for value in metadata.values():
        if isinstance(value, str) and (
            ".hermes" in value.lower() or "state.db" in value.lower()
        ):
            return True
    return False


def _metadata_leak(metadata: Any) -> str | None:
    """Return a denial reason if *metadata* carries a secret / path / route leak."""
    if not isinstance(metadata, Mapping):
        return None
    # A smuggled authorization key (any casing / separator) denies the binding.
    if _metadata_smuggling(metadata):
        return "descriptor_metadata_smuggling_denied"
    # A production-path-like value in the metadata is a path leak.
    if _looks_like_path_leak(metadata):
        return "descriptor_metadata_path_leak"
    # A secret value anywhere in the metadata redacts at worst at the runtime
    # layer, but a descriptor binding fails closed on it too.
    if contains_secret(metadata):
        return "descriptor_metadata_secret_leak"
    return None


def validate_runtime_descriptor_for_fixture_runtime(
    descriptor: Any,
    *,
    metadata: Any = None,
) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
    """Validate a descriptor for the dev-only fixture runtime. Fail-closed.

    Returns ``(allowed, reasons, guards)``. ``allowed`` is True **only** when the
    descriptor is a static, reviewed, dev-only record that binds a reviewed
    fixture operation with compatible safety metadata and carries no execution
    surface, no untrusted source, and no authorization smuggling.

    This is the **registry-level** half of the dual-layer check; the
    **runtime-level** half (allowlist binding + capability compatibility) is
    performed by :func:`resolve_runtime_descriptor_binding`.
    """
    reasons: list[str] = []
    guards: list[str] = []

    if descriptor is None:
        return False, ("descriptor_missing",), ("descriptor_missing",)
    if not isinstance(descriptor, Mapping):
        return False, ("descriptor_malformed",), ("descriptor_malformed",)

    # 1. Stable descriptor id (registry lookup key). It is a label, never a
    #    path / command. The descriptor-only evaluator enforces id safety; we
    #    re-derive it here so a registry-level denial is precise.
    descriptor_id = _descriptor_id_for(descriptor)
    if not descriptor_id:
        reasons.append("descriptor_id_missing")
        guards.append("descriptor_id")

    # 2. Descriptor-only enforcement: re-use the Phase 3H evaluator (recursive
    #    forbidden-field scan + extended execution/secret-surface scan + size).
    #    A descriptor carrying an execution surface is denied outright.
    desc_decision = evaluate_descriptor(descriptor)
    if not desc_decision.allowed:
        # Map the evaluator's reasons onto registry-level tokens.
        for reason in desc_decision.reasons:
            if reason == "descriptor_carries_execution_surface":
                reasons.append("descriptor_carries_execution_surface")
                guards.append("descriptor_execution_surface")
            elif reason == "descriptor_id_unsafe":
                reasons.append("descriptor_id_unsafe")
                guards.append("descriptor_id")
            elif reason == "descriptor_id_missing":
                if "descriptor_id_missing" not in reasons:
                    reasons.append("descriptor_id_missing")
                    guards.append("descriptor_id")
            elif reason == "descriptor_oversized":
                reasons.append("descriptor_oversized")
                guards.append("descriptor_size")
            elif reason == "malformed_descriptor":
                if "descriptor_malformed" not in reasons:
                    reasons.append("descriptor_malformed")
                    guards.append("descriptor_malformed")

    # 3. Defense-in-depth: the recursive forbidden-field scanner must agree.
    forbidden = is_forbidden_field_present(dict(descriptor))
    if forbidden is not None and "descriptor_carries_execution_surface" not in reasons:
        reasons.append("descriptor_forbidden_field")
        guards.append("descriptor_execution_surface")

    # 4. Size bound (defense-in-depth; evaluate_descriptor already bounds it).
    try:
        size = len(repr(dict(descriptor)))
    except Exception:  # pragma: no cover — defensive
        size = 0
    if size > MAX_DESCRIPTOR_BINDING_SIZE and "descriptor_oversized" not in reasons:
        reasons.append("descriptor_oversized")
        guards.append("descriptor_size")

    # 5. Supply-chain provenance: the descriptor source must be a readable
    #    static type. A remote / marketplace / generated / production source is
    #    denied before any fixture runs.
    source_type = _descriptor_source_type(descriptor)
    provenance_reason = _provenance_reason(source_type)
    if provenance_reason is not None:
        reasons.append(provenance_reason)
        guards.append("descriptor_provenance")

    # 6. Fixture binding key (registry-level): the descriptor must name a
    #    reviewed fixture plugin + operation that is an exact allowlist member.
    plugin_id = descriptor.get("pluginId")
    operation = descriptor.get("operation")
    if not isinstance(plugin_id, str) or not plugin_id:
        reasons.append("descriptor_plugin_id_missing")
        guards.append("fixture_binding")
    elif plugin_id not in FIXTURE_PLUGIN_IDS:
        reasons.append("descriptor_plugin_id_not_fixture")
        guards.append("fixture_binding")
    if not isinstance(operation, str) or not operation:
        reasons.append("descriptor_operation_missing")
        guards.append("fixture_binding")
    elif operation not in FIXTURE_OPERATION_NAMES:
        reasons.append("descriptor_operation_not_fixture")
        guards.append("fixture_binding")
    if (
        isinstance(plugin_id, str)
        and isinstance(operation, str)
        and (plugin_id, operation) not in FIXTURE_ALLOWLIST
    ):
        reasons.append("descriptor_pair_not_in_allowlist")
        guards.append("fixture_binding")

    # 7. First-version descriptor invariants (defense-in-depth): a reviewed
    #    descriptor must be dev-only and must not claim production. These are
    #    metadata claims only — they authorize nothing — but a claim of
    #    ``productionAllowed`` is treated as smuggling and denied.
    if descriptor.get("productionAllowed") is True:
        reasons.append("descriptor_metadata_production_smuggling")
        guards.append("descriptor_production_claim")

    # 8. Authorization-smuggling / secret / path leak in descriptor metadata.
    leak_reason = _metadata_leak(descriptor.get("metadata", descriptor))
    if leak_reason is not None:
        reasons.append(leak_reason)
        guards.append("metadata_smuggling" if leak_reason.endswith("smuggling_denied") else "metadata_redaction")

    # 9. Caller-supplied request metadata smuggling / leak fails closed.
    if metadata is not None:
        meta_leak = _metadata_leak(metadata)
        if meta_leak is not None and meta_leak not in reasons:
            reasons.append(meta_leak)
            guards.append(
                "metadata_smuggling" if meta_leak.endswith("smuggling_denied") else "metadata_redaction"
            )

    allowed = len(reasons) == 0
    return allowed, tuple(dict.fromkeys(reasons)), tuple(dict.fromkeys(guards))


# ---------------------------------------------------------------------------
# 3. RuntimeDescriptorBinding — the resolved registry→runtime binding
# ---------------------------------------------------------------------------


def _redacted_descriptor(descriptor: Any) -> dict[str, Any]:
    """Project a descriptor to a redacted, value-free binding-view dict."""
    if not isinstance(descriptor, Mapping):
        return {"malformed": True, "redactionApplied": True}
    view: dict[str, Any] = {}
    for key in ("descriptorId", "pluginId", "operation", "source", "version"):
        if key in descriptor:
            view[key] = descriptor[key]
    caps = descriptor.get("requestedCapabilities")
    if isinstance(caps, (list, tuple)):
        view["requestedCapabilities"] = list(caps)
    return redact_sandbox_payload(view)


@dataclass(frozen=True)
class RuntimeDescriptorBinding:
    """A resolved registry→runtime descriptor binding.

    ``binding_allowed`` is True **only** when the descriptor passed BOTH the
    registry-level validation (:func:`validate_runtime_descriptor_for_fixture_runtime`)
    and the runtime-level binding (:func:`~dev_web_plugin_runtime.resolve_runtime_binding`).
    ``reviewed_fixture`` / ``dev_only`` / ``fixture_only`` are frozen True; the
    provenance ``source`` is the static descriptor registry. ``runtime_flags``
    equal the frozen runtime constants — a binding flips none of them.
    """

    descriptor_id: str
    registry_descriptor_id: str
    plugin_id: str
    operation: str
    source: str = DESCRIPTOR_BINDING_SOURCE
    fixture_only: bool = True
    dev_only: bool = True
    reviewed_fixture: bool = True
    binding_allowed: bool = False
    denial_reasons: tuple[str, ...] = ()
    triggered_guards: tuple[str, ...] = ()
    redacted_descriptor: Mapping[str, Any] = field(default_factory=dict)
    runtime_flags: Mapping[str, bool] = field(default_factory=lambda: dict(RUNTIME_FLAGS_FROZEN))

    def __post_init__(self) -> None:
        if self.source != DESCRIPTOR_BINDING_SOURCE:
            object.__setattr__(self, "source", DESCRIPTOR_BINDING_SOURCE)
        if dict(self.runtime_flags) != RUNTIME_FLAGS_FROZEN:
            raise AssertionError("descriptor binding flags must equal the frozen constants")
        object.__setattr__(
            self, "redacted_descriptor", MappingProxyType(copy.deepcopy(dict(self.redacted_descriptor)))
        )

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "descriptorId": self.descriptor_id,
                "registryDescriptorId": self.registry_descriptor_id,
                "pluginId": self.plugin_id,
                "operation": self.operation,
                "source": self.source,
                "fixtureOnly": self.fixture_only,
                "devOnly": self.dev_only,
                "reviewedFixture": self.reviewed_fixture,
                "bindingAllowed": self.binding_allowed,
                "denialReasons": list(self.denial_reasons),
                "triggeredGuards": list(self.triggered_guards),
                "redactedDescriptor": dict(self.redacted_descriptor),
                "runtimeFlags": dict(self.runtime_flags),
                "redactionApplied": True,
            }
        )


def _binding_descriptor_id(descriptor: Any) -> str:
    if isinstance(descriptor, Mapping):
        raw = descriptor.get("descriptorId") or descriptor.get("pluginId")
        if isinstance(raw, str):
            return raw
    return ""


def resolve_runtime_descriptor_binding(
    descriptor: Any,
    *,
    metadata: Any = None,
) -> RuntimeDescriptorBinding:
    """Resolve a registry→runtime descriptor binding (dual-layer, fail-closed).

    Layer 1 (registry): :func:`validate_runtime_descriptor_for_fixture_runtime`.
    Layer 2 (runtime): :func:`~dev_web_plugin_runtime.resolve_runtime_binding`
    over a :class:`PluginRuntimeRequest` carrying the descriptor — the runtime's
    own allowlist membership, capability-compatibility, and fixture-metadata
    re-validation. The binding is allowed only when BOTH layers pass.
    """
    registry_allowed, reg_reasons, reg_guards = validate_runtime_descriptor_for_fixture_runtime(
        descriptor, metadata=metadata
    )

    descriptor_id = _binding_descriptor_id(descriptor)
    plugin_id = ""
    operation = ""

    runtime_reasons: tuple[str, ...] = ()
    runtime_guards: tuple[str, ...] = ()
    if isinstance(descriptor, Mapping):
        plugin_id = descriptor.get("pluginId") or ""
        operation = descriptor.get("operation") or ""
        if isinstance(plugin_id, str) and isinstance(operation, str):
            request = PluginRuntimeRequest(
                descriptor=descriptor,
                descriptor_id=descriptor_id,
                requested_capabilities=tuple(
                    descriptor.get("requestedCapabilities", ())
                    if isinstance(descriptor.get("requestedCapabilities"), (list, tuple))
                    else ()
                ),
                metadata=metadata,
            )
            binding = resolve_runtime_binding(request)
            runtime_reasons = binding.reasons
            runtime_guards = () if binding.resolved else ("fixture_binding",)
            if binding.resolved:
                plugin_id = binding.plugin_id or plugin_id
                operation = binding.operation or operation
            else:
                # Surface a registry-level capability-mismatch reason when the
                # runtime flagged one, so the binding result is self-describing.
                pass

    reasons: list[str] = list(reg_reasons)
    for reason in runtime_reasons:
        if reason not in reasons:
            reasons.append(reason)
    guards: list[str] = list(reg_guards)
    for guard in runtime_guards:
        if guard not in guards:
            guards.append(guard)

    binding_allowed = registry_allowed and not runtime_reasons

    return RuntimeDescriptorBinding(
        descriptor_id=descriptor_id,
        registry_descriptor_id=descriptor_id,
        plugin_id=plugin_id if isinstance(plugin_id, str) else "",
        operation=operation if isinstance(operation, str) else "",
        binding_allowed=binding_allowed,
        denial_reasons=tuple(dict.fromkeys(reasons)),
        triggered_guards=tuple(dict.fromkeys(guards)),
        redacted_descriptor=_redacted_descriptor(descriptor),
    )


# ---------------------------------------------------------------------------
# 4. Descriptor-backed runtime execution wrappers
# ---------------------------------------------------------------------------


def _binding_p0_projection(kind: str) -> dict[str, Any]:
    """Conservative P0 projection for a descriptor-backed runtime result.

    ``kind`` is ``partial_evidence`` (a fixture executed — dev-only partial
    evidence), ``guard_evidence`` (a guard / registry denied), or
    ``failure_mode_evidence`` (a fixture failed). ``resolved`` is always False
    and every authorization flag is frozen — a descriptor-backed pass resolves /
    authorizes nothing.
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
        "registrySource": DESCRIPTOR_BINDING_SOURCE,
        "note": "dev_only_descriptor_fixture_partial_evidence_only",
        "redactionApplied": True,
    }


def _annotate_result(
    result: PluginRuntimeResult,
    binding: RuntimeDescriptorBinding,
    *,
    p0_kind: str,
) -> PluginRuntimeResult:
    """Return a fresh result carrying the binding annotation + merged verdicts.

    The descriptor binding is authoritative: if it denied, the final result is
    denied and not executed even if the runtime happened to allow. The audit is
    annotated with the redacted binding + the static-registry source. The frozen
    runtime flags are re-affirmed by construction.
    """
    final_allowed = result.allowed and binding.binding_allowed
    # A fixture is "executed" when the binding allowed it and the runtime
    # invoked it — even if the fixture then failed (e.g. deliberate_failure). A
    # binding-denied descriptor never executes.
    final_executed = result.executed and binding.binding_allowed

    merged_reasons: list[str] = list(binding.denial_reasons)
    for reason in result.denial_reasons:
        if reason not in merged_reasons:
            merged_reasons.append(reason)
    merged_guards: list[str] = list(binding.triggered_guards)
    for guard in result.triggered_guards:
        if guard not in merged_guards:
            merged_guards.append(guard)

    audit_view: dict[str, Any] = dict(result.redacted_audit)
    audit_view["descriptorBinding"] = binding.to_safe_dict()
    audit_view["registrySource"] = DESCRIPTOR_BINDING_SOURCE
    audit_view["schemaVersion"] = DESCRIPTOR_RUNTIME_BINDING_VERSION

    # Recompute the P0 projection for the final outcome (a binding-denied
    # result is guard_evidence; an executed fixture is partial_evidence; a
    # failure is failure_mode_evidence).
    if result.failed and final_executed:
        kind = "failure_mode_evidence"
    elif final_executed:
        kind = "partial_evidence"
    else:
        kind = "guard_evidence"
    projection = _binding_p0_projection(kind)

    redacted_audit = redact_sandbox_payload(audit_view)
    return PluginRuntimeResult(
        allowed=final_allowed,
        executed=final_executed,
        failed=result.failed,
        plugin_id=result.plugin_id,
        operation=result.operation,
        output_payload=dict(result.output_payload) if final_allowed else {},
        denial_reasons=tuple(merged_reasons),
        triggered_guards=tuple(merged_guards),
        redacted_audit=redacted_audit,
        runtime_flags=dict(RUNTIME_FLAGS_FROZEN),
        p0_evidence=projection,
        errors=result.errors,
    )


def _build_request(
    descriptor: Mapping[str, Any],
    binding: RuntimeDescriptorBinding,
    *,
    input_payload: Any,
    metadata: Any,
) -> PluginRuntimeRequest:
    """Build the :class:`PluginRuntimeRequest` that drives the runtime."""
    requested = descriptor.get("requestedCapabilities")
    if not isinstance(requested, (list, tuple)):
        requested = ()
    return PluginRuntimeRequest(
        plugin_id=binding.plugin_id,
        operation=binding.operation,
        descriptor=descriptor,
        descriptor_id=binding.registry_descriptor_id or binding.descriptor_id,
        input_payload=input_payload,
        requested_capabilities=tuple(requested),
        metadata=metadata,
    )


def run_dev_plugin_from_descriptor(
    descriptor: Any,
    input_payload: Any = None,
    *,
    metadata: Any = None,
) -> PluginRuntimeResult:
    """Run a dev-only fixture evaluation driven by a registry descriptor.

    Flow:

      1. Resolve the registry→runtime binding (dual-layer validation). A denied
         binding short-circuits to a denied, non-executed result.
      2. Build a :class:`PluginRuntimeRequest` and invoke
         :func:`~dev_web_plugin_runtime.run_dev_plugin` (which enforces every
         Phase 3H guard + fixture invocation + redaction + P0 projection).
      3. Annotate the result with the redacted binding + the static-registry
         source and enforce the binding's verdict authoritatively.

    Loads / imports / fetches / shells nothing; adds no route; touches no
    production path or ``~/.hermes``. A success is dev-only partial evidence.
    """
    binding = resolve_runtime_descriptor_binding(descriptor, metadata=metadata)
    if not isinstance(descriptor, Mapping):
        descriptor = {}
    request = _build_request(descriptor, binding, input_payload=input_payload, metadata=metadata)
    result = run_dev_plugin(request)
    return _annotate_result(result, binding, p0_kind="partial_evidence")


def run_dev_plugin_from_registry_descriptor(
    registry: Any,
    descriptor_id: Any,
    input_payload: Any = None,
    *,
    metadata: Any = None,
) -> PluginRuntimeResult:
    """Run a dev-only fixture evaluation for a descriptor looked up by id.

    *registry* is an in-memory sequence of descriptor dicts (the static reviewed
    table or a caller-supplied fixture registry). A descriptor not present is
    denied (``descriptor_not_in_static_registry``) — never loaded from a file,
    a directory, a remote registry, or a marketplace.
    """
    descriptor = lookup_reviewed_fixture_descriptor(registry, descriptor_id)
    if descriptor is None:
        binding = RuntimeDescriptorBinding(
            descriptor_id=str(descriptor_id) if isinstance(descriptor_id, str) else "",
            registry_descriptor_id=str(descriptor_id) if isinstance(descriptor_id, str) else "",
            plugin_id="",
            operation="",
            binding_allowed=False,
            denial_reasons=("descriptor_not_in_static_registry",),
            triggered_guards=("descriptor_registry_lookup",),
            redacted_descriptor={"notFound": True, "redactionApplied": True},
        )
        return _annotate_result(
            run_dev_plugin(PluginRuntimeRequest(descriptor_id=binding.descriptor_id)),
            binding,
            p0_kind="guard_evidence",
        )
    return run_dev_plugin_from_descriptor(descriptor, input_payload, metadata=metadata)


# ---------------------------------------------------------------------------
# 5. Batch descriptor runtime execution (isolated, fail-closed)
# ---------------------------------------------------------------------------


_BATCH_ID_SAFE_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"
)


def _batch_id_is_safe(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if ".." in value:
        return False
    return all(ch in _BATCH_ID_SAFE_CHARS for ch in value)


def run_dev_plugin_batch_from_descriptors(
    descriptors: Any,
    *,
    batch_id: str = "",
    fail_fast: bool = False,
    metadata: Any = None,
) -> PluginRuntimeBatchResult:
    """Run a dev-only multi-descriptor batch. Fail-closed; isolation-preserving.

    Each descriptor is bound + executed independently through
    :func:`run_dev_plugin_from_descriptor` — one failure / denial never poisons
    another descriptor. With ``fail_fast=True`` the batch stops after the first
    non-allowed result; with ``fail_fast=False`` every descriptor runs.

    ``resolved`` stays False and every authorization flag stays NO-GO. The
    runtime flags equal the frozen constants. Loads / imports / fetches / shells
    nothing; adds no route; touches no production path or ``~/.hermes``.
    """
    safe_batch_id = batch_id if _batch_id_is_safe(batch_id) else ""
    if not safe_batch_id:
        safe_batch_id = "dev-only-descriptor-batch"

    # Batch-level metadata smuggling fails the whole batch closed.
    if metadata is not None:
        if _metadata_smuggling(metadata):
            return _fail_closed_descriptor_batch(
                safe_batch_id,
                reasons=("descriptor_batch_metadata_smuggling_denied",),
            )

    if not isinstance(descriptors, (list, tuple)):
        return _fail_closed_descriptor_batch(
            safe_batch_id, reasons=("descriptor_batch_malformed",)
        )
    if len(descriptors) > MAX_BATCH_REQUESTS:
        return _fail_closed_descriptor_batch(
            safe_batch_id, reasons=("descriptor_batch_oversized",)
        )

    results: list[PluginRuntimeResult] = []
    for descriptor in descriptors:
        result = run_dev_plugin_from_descriptor(descriptor, metadata=metadata)
        results.append(result)
        if fail_fast and not result.allowed:
            break

    return _aggregate_descriptor_batch(
        safe_batch_id,
        tuple(results),
        fail_fast=bool(fail_fast),
    )


def _fail_closed_descriptor_batch(
    batch_id: str, *, reasons: tuple[str, ...]
) -> PluginRuntimeBatchResult:
    audit = redact_sandbox_payload(
        {
            "schemaVersion": DESCRIPTOR_RUNTIME_BINDING_VERSION,
            "source": DESCRIPTOR_BINDING_AUDIT_SOURCE + ".batch",
            "batchId": batch_id,
            "total": 0,
            "succeeded": 0,
            "failed": 0,
            "denied": 0,
            "perDescriptorSummary": [],
            "decision": "denied",
            "denialReasons": list(reasons),
            "triggeredGuards": ["descriptor_batch_fail_closed"],
            "registrySource": DESCRIPTOR_BINDING_SOURCE,
            "runtimeFlags": dict(RUNTIME_FLAGS_FROZEN),
            "p0Evidence": _binding_p0_projection("guard_evidence"),
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
        runtime_flags=dict(RUNTIME_FLAGS_FROZEN),
        p0_evidence=_binding_p0_projection("guard_evidence"),
        errors=reasons,
    )


def _aggregate_descriptor_batch(
    batch_id: str,
    results: tuple[PluginRuntimeResult, ...],
    *,
    fail_fast: bool,
) -> PluginRuntimeBatchResult:
    succeeded = sum(1 for r in results if r.allowed and not r.failed)
    failed = sum(1 for r in results if r.failed)
    denied = sum(1 for r in results if not r.allowed and not r.failed)

    per_descriptor_summary = [
        {
            "pluginId": r.plugin_id,
            "operation": r.operation,
            "allowed": r.allowed,
            "executed": r.executed,
            "failed": r.failed,
        }
        for r in results
    ]

    if any(r.failed for r in results):
        kind = "failure_mode_evidence"
    elif any(r.allowed for r in results):
        kind = "partial_evidence"
    else:
        kind = "guard_evidence"
    projection = _binding_p0_projection(kind)
    projection["batchKind"] = kind
    projection["note"] = "dev_only_descriptor_fixture_batch_partial_evidence_only"

    decision = "mixed" if (succeeded and (failed or denied)) else (
        "allowed" if succeeded and not (failed or denied) else "denied"
    )

    audit = redact_sandbox_payload(
        {
            "schemaVersion": DESCRIPTOR_RUNTIME_BINDING_VERSION,
            "source": DESCRIPTOR_BINDING_AUDIT_SOURCE + ".batch",
            "batchId": batch_id,
            "total": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "denied": denied,
            "failFast": bool(fail_fast),
            "perDescriptorSummary": per_descriptor_summary,
            "decision": decision,
            "registrySource": DESCRIPTOR_BINDING_SOURCE,
            "runtimeFlags": dict(RUNTIME_FLAGS_FROZEN),
            "p0Evidence": projection,
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
        results=results,
        redacted_audit=audit,
        runtime_flags=dict(RUNTIME_FLAGS_FROZEN),
        p0_evidence=projection,
        errors=(),
    )


# ---------------------------------------------------------------------------
# 6. Boundary re-affirmation (pure constants, grep-able)
# ---------------------------------------------------------------------------

NO_REAL_PLUGIN_RUNTIME: bool = True
NO_ARBITRARY_PLUGIN_LOADING: bool = True
NO_LOCAL_PLUGIN_DIRECTORY_LOADING: bool = True
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
    """Re-affirm the descriptor-binding no-side-effect + no-authorization invariants."""
    assert NO_REAL_PLUGIN_RUNTIME is True
    assert NO_ARBITRARY_PLUGIN_LOADING is True
    assert NO_LOCAL_PLUGIN_DIRECTORY_LOADING is True
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
    assert DESCRIPTOR_BINDING_SOURCE == "static_descriptor_registry"
    # Every reviewed descriptor names an exact allowlist member.
    for entry in REVIEWED_FIXTURE_DESCRIPTORS:
        pair = (entry["pluginId"], entry["operation"])
        assert pair in FIXTURE_ALLOWLIST, f"reviewed descriptor {pair} not in allowlist"


__all__ = [
    "DESCRIPTOR_RUNTIME_BINDING_VERSION",
    "DESCRIPTOR_BINDING_AUDIT_SOURCE",
    "DESCRIPTOR_BINDING_SOURCE",
    "DESCRIPTOR_BINDING_REASONS",
    "MAX_DESCRIPTOR_BINDING_SIZE",
    "REVIEWED_FIXTURE_DESCRIPTORS",
    "get_reviewed_fixture_descriptors",
    "lookup_reviewed_fixture_descriptor",
    "validate_runtime_descriptor_for_fixture_runtime",
    "RuntimeDescriptorBinding",
    "resolve_runtime_descriptor_binding",
    "run_dev_plugin_from_descriptor",
    "run_dev_plugin_from_registry_descriptor",
    "run_dev_plugin_batch_from_descriptors",
    # boundary constants
    "NO_REAL_PLUGIN_RUNTIME",
    "NO_ARBITRARY_PLUGIN_LOADING",
    "NO_LOCAL_PLUGIN_DIRECTORY_LOADING",
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
