"""Phase 3I Runtime Governance — report projections (code allowed, production forbidden).

Pure, side-effect-free report projections that expose the **already-implemented**
Phase 3I dev-only descriptor-backed fixture runtime to a developer-facing CLI /
internal command surface. This module **adds no capability** — it only projects
the reviewed-fixture descriptor registry, the registry→runtime binding, the
descriptor-backed fixture execution, the descriptor-backed batch execution, the
redacted audit, and the P0 evidence summary as JSON-safe, deterministic,
redacted dicts.

A descriptor is *not* an executable plugin — it is a static, reviewed record.
Every projection here reads descriptors as **metadata only** and, when a fixture
runs, delegates to the existing dev-only runtime
(:mod:`hermes_cli.dev_web_plugin_runtime_binding`) which executes a reviewed
fixture function by allowlist binding only.

Hard guarantees (frozen, grep-able via :data:`NO_*` + :func:`assert_no_side_effect_surface`):

  - **reviewed-fixture-descriptor only.** The only descriptors reachable are the
    frozen, in-memory :data:`~dev_web_plugin_runtime_binding.REVIEWED_FIXTURE_DESCRIPTORS`.
    No arbitrary plugin loading, no local plugin directory loading, no remote
    registry, no marketplace, no external plugin fetch, no provider-generated /
    LLM-generated plugin install.
  - **No real plugin runtime / no real runtime execution surface.** A fixture
    runs only through the reviewed-fixture allowlist binding.
  - **No real API key read, no external network, no new HTTP route.** This module
    is **not** imported by the FastAPI app (:mod:`hermes_cli.dev_web_api`).
  - **No ``~/.hermes`` access and no production ``state.db`` access** — not even
    metadata-only ``stat`` / ``ls`` / ``resolve``. Production is referenced only
    as a denial-target string inside the existing guards.
  - **No runtime store write / no audit persistence.** Every report is built
    in-memory and is ``persisted: False``.

A successful descriptor-backed fixture execution (single or batch) is **dev-only
partial evidence**. It is **never** Implementation Authorization GO, **never**
Phase 3I production authorization, **never** real-runtime authorization, **never**
a P0 resolution. ``resolved_count`` stays 0 and every authorization flag stays
NO-GO / not-authorized no matter what runs or what untrusted metadata a request
carries.

Phase: 3I — Runtime Governance CLI (report projections)
Status: implemented (read-only projections over the existing dev-only runtime).
        NOT a production plugin runtime. No arbitrary loading, no remote
        registry, no marketplace, no external network, no real secret read, no
        new route, no production access.
"""

from __future__ import annotations

from typing import Any, Mapping

from hermes_cli.dev_web_p0_evidence import (
    IMPLEMENTATION_AUTHORIZATION,
    NEW_ROUTE,
    PHASE_3I_AUTHORIZED,
    PRODUCTION_ROLLOUT,
    REAL_RUNTIME,
    evaluate_p0_evidence,
)
from hermes_cli.dev_web_plugin_runtime import (
    RESULT_EVIDENCE_FLAGS,
    RUNTIME_FLAGS_FROZEN,
    PluginRuntimeResult,
)
from hermes_cli.dev_web_plugin_runtime_binding import (
    DESCRIPTOR_BINDING_SOURCE,
    REVIEWED_FIXTURE_DESCRIPTORS,
    get_reviewed_fixture_descriptors,
    lookup_reviewed_fixture_descriptor,
    resolve_runtime_descriptor_binding,
    run_dev_plugin_batch_from_descriptors,
    run_dev_plugin_from_registry_descriptor,
)
from hermes_cli.dev_web_sandbox_guards import redact_sandbox_payload

#: Schema + audit-source labels carried by every governance report.
GOVERNANCE_VERSION = "phase-3i-runtime-governance-v1"
GOVERNANCE_AUDIT_SOURCE = "dev_web_runtime_governance"

#: Authorization label projected for the Phase 3I production gate. The frozen
#: constant is a bool (``False``); the CLI/report surface renders the string.
_PHASE_3I_AUTHORIZATION_LABEL = "NOT_AUTHORIZED" if not PHASE_3I_AUTHORIZED else "AUTHORIZED"


# ---------------------------------------------------------------------------
# 0. Boundary re-affirmation (pure constants, grep-able)
# ---------------------------------------------------------------------------

#: Frozen boundary flags. Every projection is a read-only view over the existing
#: dev-only runtime; this module adds none of the forbidden surfaces.
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
NO_PRODUCTION_STATE_DB_ACCESS: bool = True
NO_RUNTIME_STORE_WRITE: bool = True
NO_AUDIT_PERSISTENCE: bool = True
NO_FILE_READ: bool = True
NO_FILE_WRITE: bool = True


#: The frozen side-effect surface projected by every CLI envelope. Every value
#: is a plain bool (never a string), so the conservative redactor — which only
#: masks a value under a secret-bearing *key* when the value is a non-empty
#: *string* — leaves every ``False`` intact and the invariant stays visible. A
#: governance pass performs none of these actions no matter what runs or what
#: untrusted metadata a request carries; the block cannot be overridden.
_SIDE_EFFECT_FIELDS: tuple[str, ...] = (
    "productionAccess",
    "externalNetwork",
    "realSecretRead",
    "routeChange",
    "runtimeStoreWrite",
    "auditStoreWrite",
    "arbitraryPluginLoad",
    "localPluginDirectoryRead",
    "remotePluginFetch",
    "marketplaceAccess",
    "inputFileRead",
    "outputFileWrite",
)


def side_effect_projection() -> dict[str, bool]:
    """The frozen all-False side-effect surface appended to every CLI envelope.

    Every value is ``not <frozen NO_* flag>``: with every boundary flag frozen
    ``True`` today, every value resolves to ``False`` — and if a future editor
    flipped a flag to ``False`` (allowing the action), the corresponding side
    effect would surface as ``True`` rather than stay hidden. A descriptor-backed
    fixture pass (single or batch) performs none of these actions: it touches no
    production path, no network, no real secret, adds no route, writes no runtime
    / audit store, loads / fetches / scans no plugin source, and reads / writes
    no file. The values are plain bools, so the conservative redactor (which only
    masks a value under a secret-bearing key when the value is a non-empty
    *string*) leaves every ``False`` intact.
    """
    return {
        "productionAccess": not NO_PRODUCTION_ACCESS,
        "externalNetwork": not NO_EXTERNAL_NETWORK,
        "realSecretRead": not NO_REAL_API_KEY_READ,
        "routeChange": not NO_NEW_ROUTE,
        "runtimeStoreWrite": not NO_RUNTIME_STORE_WRITE,
        "auditStoreWrite": not NO_AUDIT_PERSISTENCE,
        "arbitraryPluginLoad": not NO_ARBITRARY_PLUGIN_LOADING,
        "localPluginDirectoryRead": not NO_LOCAL_PLUGIN_DIRECTORY_LOADING,
        "remotePluginFetch": not NO_REMOTE_REGISTRY,
        "marketplaceAccess": not NO_MARKETPLACE,
        "inputFileRead": not NO_FILE_READ,
        "outputFileWrite": not NO_FILE_WRITE,
    }


def assert_no_side_effect_surface() -> dict[str, bool]:
    """Re-affirm the governance no-side-effect + no-authorization invariants.

    Returns the frozen :func:`side_effect_projection` so a caller can both
    assert (this call raises if any frozen boundary flag drifted) and use the
    resulting all-False block directly. The CLI re-affirms this on every
    invocation and projects the returned block into every envelope.
    """
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
    assert NO_PRODUCTION_STATE_DB_ACCESS is True
    assert NO_RUNTIME_STORE_WRITE is True
    assert NO_AUDIT_PERSISTENCE is True
    assert NO_FILE_READ is True
    assert NO_FILE_WRITE is True
    return side_effect_projection()


# ---------------------------------------------------------------------------
# 1. Frozen authorization + P0 projection helpers
# ---------------------------------------------------------------------------


def authorization_projection() -> dict[str, Any]:
    """The frozen authorization block appended to every CLI report.

    Every flag is derived from the frozen Phase 3I / P0 constants so the block
    can never drift to GO / authorized by accident. A descriptor-backed fixture
    pass authorizes nothing.

    The verdict keys mirror the value-preserving ``*Gate`` names used by the P0
    projection (:func:`_p0_projection`): a key whose name carries a secret stem
    (e.g. ``*Authorization`` / ``*ApiKey``) would have its value collapsed to
    ``[REDACTED]`` by :func:`~dev_web_sandbox_guards.redact_sandbox_payload`,
    which would hide the very NO-GO / not-authorized signal this block exists to
    surface. The ``*Gate`` keys preserve their string values while remaining
    grep-able and consistent with the rest of the runtime's authorization
    vocabulary.

    The block surfaces every authorization dimension the governance boundary
    freezes: implementation / Phase 3I production / production runtime / new
    route / production rollout verdicts (``*Gate`` strings), plus the explicit
    supply-chain / network verdicts (``arbitraryPluginLoading``,
    ``localPluginDirectoryLoading``, ``remoteRegistry``, ``marketplace``,
    ``externalNetwork``, ``newRoute``, ``productionRollout``). The real-API-key
    dimension is projected as ``realApiKeyRead: False`` — a key whose name carries
    the ``apikey`` stem would be masked with any string value, so a plain bool
    keeps the "no real key read" signal visible.
    """
    return {
        "implementationGate": IMPLEMENTATION_AUTHORIZATION,
        "phase3iProductionGate": _PHASE_3I_AUTHORIZATION_LABEL,
        "productionRuntimeGate": REAL_RUNTIME,
        "newRouteGate": NEW_ROUTE,
        "productionRolloutGate": PRODUCTION_ROLLOUT,
        # Explicit supply-chain / network / rollout verdicts (safe key names —
        # none carries a secret stem, so the "NO-GO" string survives redaction).
        "arbitraryPluginLoading": "NO-GO",
        "localPluginDirectoryLoading": "NO-GO",
        "remoteRegistry": "NO-GO",
        "marketplace": "NO-GO",
        "externalNetwork": "NO-GO",
        "newRoute": NEW_ROUTE,
        "productionRollout": PRODUCTION_ROLLOUT,
        # The real-API-key dimension as a bool: a key with the "apikey" stem +
        # a string value would be redacted, so a plain False keeps it visible.
        "realApiKeyRead": not NO_REAL_API_KEY_READ,
    }


def _p0_projection(kind: str) -> dict[str, Any]:
    """Conservative P0 projection for a descriptor-backed governance result.

    ``kind`` is ``partial_evidence`` (a fixture executed — dev-only partial
    evidence), ``guard_evidence`` (a guard / registry denied), or
    ``failure_mode_evidence`` (a fixture failed). ``resolved`` is always False
    and every authorization flag is frozen — a governance pass resolves /
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


# ---------------------------------------------------------------------------
# 2. list — reviewed fixture descriptors (no execution)
# ---------------------------------------------------------------------------


def list_runtime_descriptors() -> dict[str, Any]:
    """Project the frozen reviewed-fixture descriptor registry (no execution).

    Each descriptor is rendered as a value-free metadata view: it is a static,
    reviewed, dev-only, fixture-only record that carries **no** execution
    surface (``executable`` False), is **not** remote / marketplace / production,
    and requests **no** route change. No fixture runs; nothing is loaded.
    """
    entries = get_reviewed_fixture_descriptors()
    descriptors: list[dict[str, Any]] = []
    for entry in entries:
        descriptors.append(
            {
                "descriptorId": entry.get("descriptorId", ""),
                "pluginId": entry.get("pluginId", ""),
                "operation": entry.get("operation", ""),
                "source": DESCRIPTOR_BINDING_SOURCE,
                "version": entry.get("version", ""),
                "devOnly": True,
                "fixtureOnly": True,
                "reviewedFixture": True,
                "executable": False,
                "remote": False,
                "marketplace": False,
                "production": False,
                "routeChange": False,
                "redactionApplied": True,
            }
        )
    return redact_sandbox_payload(
        {
            "schemaVersion": GOVERNANCE_VERSION,
            "source": GOVERNANCE_AUDIT_SOURCE + ".list",
            "descriptors": descriptors,
            "count": len(descriptors),
            "allDevOnly": True,
            "allFixtureOnly": True,
            "allReviewedFixture": True,
            "anyExecutable": False,
            "anyRemote": False,
            "anyMarketplace": False,
            "anyProduction": False,
            "anyRouteChange": False,
            "registrySource": DESCRIPTOR_BINDING_SOURCE,
            "redactionApplied": True,
        }
    )


# ---------------------------------------------------------------------------
# 3. show — registry→runtime binding inspection (no execution)
# ---------------------------------------------------------------------------


def show_runtime_descriptor_binding(
    descriptor_id: Any, *, metadata: Any = None
) -> dict[str, Any]:
    """Project the registry→runtime binding for *descriptor_id* (no execution).

    Looks the id up in the frozen reviewed registry (membership only — never a
    path / directory scan / remote fetch) and resolves the dual-layer binding
    through :func:`~dev_web_plugin_runtime_binding.resolve_runtime_descriptor_binding`,
    which validates but **does not execute**. An unknown / unsafe id projects a
    denied binding (``bindingAllowed`` False).
    """
    descriptor = (
        lookup_reviewed_fixture_descriptor(REVIEWED_FIXTURE_DESCRIPTORS, descriptor_id)
        if isinstance(descriptor_id, str)
        else None
    )
    if descriptor is None:
        return redact_sandbox_payload(
            {
                "schemaVersion": GOVERNANCE_VERSION,
                "source": GOVERNANCE_AUDIT_SOURCE + ".binding",
                "descriptorId": descriptor_id if isinstance(descriptor_id, str) else "",
                "registryDescriptorId": descriptor_id if isinstance(descriptor_id, str) else "",
                "pluginId": "",
                "operation": "",
                "source": DESCRIPTOR_BINDING_SOURCE,
                "fixtureOnly": True,
                "devOnly": True,
                "reviewedFixture": True,
                "bindingAllowed": False,
                "denialReasons": ["descriptor_not_in_static_registry"],
                "triggeredGuards": ["descriptor_registry_lookup"],
                "redactedDescriptor": {"notFound": True, "redactionApplied": True},
                "runtimeFlags": dict(RUNTIME_FLAGS_FROZEN),
                "p0Projection": _p0_projection("guard_evidence"),
                "redactionApplied": True,
            }
        )

    binding = resolve_runtime_descriptor_binding(descriptor, metadata=metadata)
    view = binding.to_safe_dict()
    kind = "partial_evidence" if binding.binding_allowed else "guard_evidence"
    view["schemaVersion"] = GOVERNANCE_VERSION
    view["source"] = GOVERNANCE_AUDIT_SOURCE + ".binding"
    view["p0Projection"] = _p0_projection(kind)
    view["runtimeFlags"] = dict(RUNTIME_FLAGS_FROZEN)
    view["redactionApplied"] = True
    return redact_sandbox_payload(view)


# ---------------------------------------------------------------------------
# 4. run — descriptor-backed fixture execution (single)
# ---------------------------------------------------------------------------


def run_runtime_descriptor(
    descriptor_id: Any,
    input_payload: Any = None,
    *,
    metadata: Any = None,
) -> dict[str, Any]:
    """Run a reviewed-fixture descriptor (looked up by id) and project the result.

    Delegates to
    :func:`~dev_web_plugin_runtime_binding.run_dev_plugin_from_registry_descriptor`,
    which performs the dual-layer binding + the existing dev-only fixture
    execution (every Phase 3H guard + redaction + P0 projection enforced
    unchanged). A denied / unknown id runs nothing (``executed`` False).
    """
    result = run_dev_plugin_from_registry_descriptor(
        REVIEWED_FIXTURE_DESCRIPTORS,
        descriptor_id,
        input_payload,
        metadata=metadata,
    )
    return _project_run_result(descriptor_id, result)


def _project_run_result(descriptor_id: Any, result: PluginRuntimeResult) -> dict[str, Any]:
    """Render a single :class:`PluginRuntimeResult` as a JSON-safe report."""
    return redact_sandbox_payload(
        {
            "schemaVersion": GOVERNANCE_VERSION,
            "source": GOVERNANCE_AUDIT_SOURCE + ".run",
            "descriptorId": descriptor_id if isinstance(descriptor_id, str) else "",
            "allowed": result.allowed,
            "executed": result.executed,
            "failed": result.failed,
            "pluginId": result.plugin_id,
            "operation": result.operation,
            "outputPayload": dict(result.output_payload),
            "denialReasons": list(result.denial_reasons),
            "triggeredGuards": list(result.triggered_guards),
            "redactedAudit": dict(result.redacted_audit),
            "runtimeFlags": dict(result.runtime_flags),
            "p0Evidence": dict(result.p0_evidence),
            "sideEffects": side_effect_projection(),
            "errors": list(result.errors),
            "registrySource": DESCRIPTOR_BINDING_SOURCE,
            "redactionApplied": True,
            "persisted": False,
        }
    )


# ---------------------------------------------------------------------------
# 5. batch — descriptor-backed fixture execution (multi, isolated, fail-closed)
# ---------------------------------------------------------------------------


def run_runtime_descriptor_batch(
    items: Any,
    *,
    fail_fast: bool = False,
    metadata: Any = None,
) -> dict[str, Any]:
    """Run a multi-descriptor batch. Fail-closed; isolation-preserving.

    *items* is a sequence of mappings each carrying ``descriptor_id`` (required)
    and an optional ``input`` object. Each item is bound + executed independently
    through the per-descriptor run path — one failure / denial never poisons
    another item. With ``fail_fast=True`` the batch stops after the first
    non-allowed result; with ``fail_fast=False`` every item runs. Order is
    preserved and the per-item results appear in input order.

    When **no** item carries an explicit ``input`` and **every** id resolves to a
    reviewed descriptor, the batch delegates to the canonical
    :func:`~dev_web_plugin_runtime_binding.run_dev_plugin_batch_from_descriptors`
    (the same path the Phase 3I integration tests exercise). Otherwise each item
    is run individually so per-item input is honored and unknown ids are reported
    as denied rather than dropped.

    ``resolved`` stays False and every authorization flag stays NO-GO. The
    runtime flags equal the frozen constants. Loads / imports / fetches / shells
    nothing; adds no route; touches no production path or ``~/.hermes``.
    """
    parsed = _parse_batch_items_internal(items)

    resolved: list[dict[str, Any] | None] = []
    for desc_id, _input in parsed:
        resolved.append(
            lookup_reviewed_fixture_descriptor(REVIEWED_FIXTURE_DESCRIPTORS, desc_id)
            if isinstance(desc_id, str)
            else None
        )

    has_missing = any(desc is None for desc in resolved)
    has_input = any(input_payload is not None for _id, input_payload in parsed)

    per_item: list[tuple[str, PluginRuntimeResult]] = []

    if not has_missing and not has_input:
        # Canonical descriptors-only batch: reuse the existing batch machinery.
        descriptors = [desc for desc in resolved if desc is not None]
        batch = run_dev_plugin_batch_from_descriptors(
            descriptors, fail_fast=fail_fast, metadata=metadata
        )
        for desc_id, result in zip([pid for pid, _ in parsed], batch.results):
            per_item.append((desc_id, result))
    else:
        # Per-item path: honor per-item input and report unknown ids as denied.
        for (desc_id, input_payload), _desc in zip(parsed, resolved):
            result = run_dev_plugin_from_registry_descriptor(
                REVIEWED_FIXTURE_DESCRIPTORS,
                desc_id,
                input_payload,
                metadata=metadata,
            )
            per_item.append((desc_id if isinstance(desc_id, str) else "", result))
            if fail_fast and not result.allowed:
                break

    return _build_batch_report(per_item, fail_fast=bool(fail_fast))


def _parse_batch_items_internal(items: Any) -> list[tuple[Any, Any]]:
    """Coerce raw *items* into a list of ``(descriptor_id, input_or_None)``.

    Performs no execution and no size policy here — the CLI layer enforces the
    bounded size policy before calling :func:`run_runtime_descriptor_batch`. This
    helper only normalizes the shape so the projection is robust to a caller that
    supplies already-parsed items (e.g. a direct module caller in tests).
    """
    parsed: list[tuple[Any, Any]] = []
    if not isinstance(items, (list, tuple)):
        return parsed
    for item in items:
        if isinstance(item, Mapping):
            parsed.append((item.get("descriptor_id"), item.get("input")))
        else:
            parsed.append((None, None))
    return parsed


def _build_batch_report(
    per_item: list[tuple[str, PluginRuntimeResult]], *, fail_fast: bool
) -> dict[str, Any]:
    """Aggregate per-item results into a JSON-safe, redacted batch report."""
    safe_results: list[dict[str, Any]] = []
    per_descriptor_summary: list[dict[str, Any]] = []
    succeeded = failed = denied = 0
    for desc_id, result in per_item:
        view = _project_run_result(desc_id, result)
        safe_results.append(view)
        per_descriptor_summary.append(
            {
                "descriptorId": desc_id,
                "pluginId": result.plugin_id,
                "operation": result.operation,
                "allowed": result.allowed,
                "executed": result.executed,
                "failed": result.failed,
            }
        )
        if result.allowed and not result.failed:
            succeeded += 1
        elif result.failed:
            failed += 1
        else:
            denied += 1
    total = len(per_item)

    if any(result.failed for _id, result in per_item):
        kind = "failure_mode_evidence"
    elif any(result.allowed for _id, result in per_item):
        kind = "partial_evidence"
    else:
        kind = "guard_evidence"
    projection = _p0_projection(kind)
    projection["batchKind"] = kind
    projection["note"] = "dev_only_descriptor_fixture_batch_partial_evidence_only"

    audit = redact_sandbox_payload(
        {
            "schemaVersion": GOVERNANCE_VERSION,
            "source": GOVERNANCE_AUDIT_SOURCE + ".batch",
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "denied": denied,
            "failFast": bool(fail_fast),
            "perDescriptorSummary": per_descriptor_summary,
            "registrySource": DESCRIPTOR_BINDING_SOURCE,
            "runtimeFlags": dict(RUNTIME_FLAGS_FROZEN),
            "p0Evidence": projection,
            "evidence": {flag: False for flag in RESULT_EVIDENCE_FLAGS},
            "redactionApplied": True,
            "persisted": False,
        }
    )
    return redact_sandbox_payload(
        {
            "schemaVersion": GOVERNANCE_VERSION,
            "source": GOVERNANCE_AUDIT_SOURCE + ".batch",
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "denied": denied,
            "failFast": bool(fail_fast),
            "results": safe_results,
            "redactedAudit": audit,
            "runtimeFlags": dict(RUNTIME_FLAGS_FROZEN),
            "p0Evidence": projection,
            "registrySource": DESCRIPTOR_BINDING_SOURCE,
            "redactionApplied": True,
            "persisted": False,
        }
    )


# ---------------------------------------------------------------------------
# 6. audit — redacted audit projection from a run / batch report
# ---------------------------------------------------------------------------


def build_runtime_audit_report(result_report: Any) -> dict[str, Any]:
    """Project the redacted audit from a run or batch report (no re-execution).

    *result_report* is a dict produced by :func:`run_runtime_descriptor` or
    :func:`run_runtime_descriptor_batch`. The audit + P0 evidence are projected
    value-free; nothing runs again. The report surfaces the descriptor id,
    plugin id, operation, verdict, denial reasons, triggered guards, the redacted
    audit, the P0 evidence, the frozen authorization block, and the all-False
    side-effect surface — every value redacted, nothing persisted.
    """
    if not isinstance(result_report, Mapping):
        return redact_sandbox_payload(
            {
                "schemaVersion": GOVERNANCE_VERSION,
                "source": GOVERNANCE_AUDIT_SOURCE + ".audit",
                "malformed": True,
                "sideEffects": side_effect_projection(),
                "authorization": authorization_projection(),
                "redactionApplied": True,
                "persisted": False,
            }
        )
    audit = result_report.get("redactedAudit") or result_report.get("audit")
    p0 = result_report.get("p0Evidence") or result_report.get("p0Projection")
    reasons = result_report.get("denialReasons")
    guards = result_report.get("triggeredGuards")
    return redact_sandbox_payload(
        {
            "schemaVersion": GOVERNANCE_VERSION,
            "source": GOVERNANCE_AUDIT_SOURCE + ".audit",
            "descriptorId": result_report.get("descriptorId", ""),
            "pluginId": result_report.get("pluginId", ""),
            "operation": result_report.get("operation", ""),
            "allowed": result_report.get("allowed"),
            "executed": result_report.get("executed"),
            "failed": result_report.get("failed"),
            "denialReasons": list(reasons) if isinstance(reasons, (list, tuple)) else [],
            "triggeredGuards": list(guards) if isinstance(guards, (list, tuple)) else [],
            "redactedAudit": dict(audit) if isinstance(audit, Mapping) else {},
            "p0Evidence": dict(p0) if isinstance(p0, Mapping) else {},
            "sideEffects": side_effect_projection(),
            "authorization": authorization_projection(),
            "redactionApplied": True,
            "persisted": False,
        }
    )


# ---------------------------------------------------------------------------
# 7. p0-report — P0 evidence projection summary
# ---------------------------------------------------------------------------


def build_runtime_p0_report(*, untrusted_metadata: Any = None) -> dict[str, Any]:
    """Project the conservative P0 evidence summary for the dev-only runtime.

    Delegates to :func:`~dev_web_p0_evidence.evaluate_p0_evidence`.
    ``resolved_count`` is always 0 (no valid human approval is possible in the
    dev skeleton) and every authorization flag is frozen NO-GO / not-authorized.
    *untrusted_metadata* is inspected only to report ignored bypass keys; it
    cannot change any classification or flag.
    """
    summary = evaluate_p0_evidence(untrusted_metadata=untrusted_metadata)
    view = summary.to_safe_dict()
    view["schemaVersion"] = GOVERNANCE_VERSION
    view["source"] = GOVERNANCE_AUDIT_SOURCE + ".p0"
    view["authorization"] = authorization_projection()
    view["redactionApplied"] = True
    return redact_sandbox_payload(dict(view))


__all__ = [
    "GOVERNANCE_VERSION",
    "GOVERNANCE_AUDIT_SOURCE",
    "assert_no_side_effect_surface",
    "authorization_projection",
    "side_effect_projection",
    "list_runtime_descriptors",
    "show_runtime_descriptor_binding",
    "run_runtime_descriptor",
    "run_runtime_descriptor_batch",
    "build_runtime_audit_report",
    "build_runtime_p0_report",
]
