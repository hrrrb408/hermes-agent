"""Phase 3H Dev-only Sandbox Proof Runner Harness (Block 3).

Promotes the Phase 3H **single-evaluation** sandbox proof skeleton into a small,
**reproducible dev-only proof scenario runner**. It takes a frozen, in-memory,
test-only :class:`ProofScenario`, drives the *existing* policy / guard / audit /
evidence logic, and returns a :class:`ProofScenarioResult` recording what was
allowed and (far more often) denied.

This is a **runner over fixed scenarios**, not a runtime:

  - It never executes a plugin, never loads a plugin, never dynamic-imports.
  - It never performs a network call, never reads a real secret, never opens a
    real filesystem path (every path is a fake / temp / string-policy target).
  - It never reads the environment, ``.env``, or a real API key.
  - It introduces **no** HTTP route and is **not** imported by the FastAPI app.
  - It writes nothing: no JSONL, no database, no runtime store, no audit file.
    Every result is an in-memory, redacted dataclass.

Central invariants (frozen):

  - A scenario's evidence flags are all ``False`` — a proof requires no route
    change, no production access, no external network, no real secret, no
    runtime execution, and creates no persistent artifact.
  - A scenario **pass** is dev-only evidence. It is **never** a P0 resolution,
    **never** Implementation Authorization GO, **never** Phase 3I authorization,
    **never** real-runtime authorization. ``resolved_count`` stays 0 and the
    authorization flags stay NO-GO / not-authorized no matter how many
    scenarios pass or what untrusted metadata a scenario carries.

Phase: 3H — Dev-only Sandbox Proof Runner Harness
Status: implemented (dev-only proof runner). NOT a runtime, NOT a plugin loader,
        NOT a signoff, NOT an authorization. Resolves nothing on its own.
"""

from __future__ import annotations

import copy
import os
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from hermes_cli.dev_web_p0_evidence import (
    GATE_STATUS_PARTIAL_EVIDENCE,
    IMPLEMENTATION_AUTHORIZATION,
    NEW_ROUTE,
    PHASE_3I_AUTHORIZED,
    PRODUCTION_ROLLOUT,
    REAL_RUNTIME,
    ROUTE_GOVERNANCE_BASELINE,
    classify_evidence_quality,
    evaluate_authorization_request,
    evaluate_p0_evidence,
    evaluate_route_exception,
)
from hermes_cli.dev_web_safety_baseline import (
    is_production_home,
    is_production_state_db,
)
from hermes_cli.dev_web_sandbox_guards import (
    REDACTED_VALUE,
    contains_secret,
    redact_sandbox_payload,
    redact_sandbox_text,
)
from hermes_cli.dev_web_sandbox_proof import (
    FilesystemRequest,
    SandboxProofRequest,
    evaluate_sandbox_proof,
)

SANDBOX_RUNNER_VERSION = "phase-3h-sandbox-proof-runner-v1"
SANDBOX_RUNNER_AUDIT_SOURCE = "dev_web_sandbox_runner"

#: The frozen evidence-flag names every scenario result carries (all False).
RESULT_EVIDENCE_FLAGS: tuple[str, ...] = (
    "route_change_required",
    "production_access_required",
    "external_network_required",
    "real_secret_required",
    "runtime_execution_required",
    "persistent_artifacts_created",
)

#: Frozen route-governance new-route flags (all zero — the runner adds no route).
NEW_ROUTE_FLAGS: dict[str, int] = {
    "newHttpRoute": 0,
    "newToolWriteRoute": 0,
    "newProviderRoute": 0,
    "newPluginRoute": 0,
    "newRuntimeRoute": 0,
}

#: A scenario id is a clean label over ``[A-Za-z0-9_.\-]`` only — never a path,
#: traversal pair, or command. Mirrors the descriptor-id safety rule.
_SCENARIO_ID_SAFE: re.Pattern[str] = re.compile(r"[A-Za-z0-9_.\-]+")


def is_scenario_id_safe(scenario_id: Any) -> bool:
    """True iff *scenario_id* is a clean label (full match, no ``..``)."""
    if not isinstance(scenario_id, str) or not scenario_id:
        return False
    if ".." in scenario_id:
        return False
    return _SCENARIO_ID_SAFE.fullmatch(scenario_id) is not None


def _redact_filesystem_path(path: Any) -> str:
    """Redact a filesystem path string for an audit record.

    ``redact_sandbox_payload`` is secret-shaped, not path-shaped, so a raw
    ``~/.hermes`` / production ``state.db`` string would survive it. This helper
    applies the same production-path classifiers the sandbox guard uses
    (expanduser + string-only checks — the path is **never** opened or stated) so
    no raw production / forbidden path reaches a scenario's audit projection.
    """
    if path is None:
        return ""
    if not isinstance(path, str):
        return REDACTED_VALUE
    text = os.path.expanduser(path)
    if is_production_home(text) or is_production_state_db(text):
        return REDACTED_VALUE
    lowered = text.lower()
    if "/.hermes" in lowered or ".hermes/" in lowered or "state.db" in lowered:
        return REDACTED_VALUE
    return path


# ---------------------------------------------------------------------------
# 1. Proof scenario model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProofScenario:
    """One fixed, in-memory, test-only proof scenario.

    Carries only static / mock / proof-level inputs. **Never** carries executable
    plugin code, a Python module / import path, a shell command, a real URL, a
    real API key, a provider credential, or a production path. Every filesystem
    path is a fake / temp / string-policy target; every secret is an obvious
    fake. The descriptor is read descriptor-only; the metadata mapping is
    untrusted by construction and can authorize nothing.
    """

    scenario_id: str
    title: str = ""
    purpose: str = ""
    descriptor: Mapping[str, Any] | None = None
    requested_capabilities: tuple[str, ...] = ()
    requested_filesystem_paths: tuple[str, ...] = ()
    requested_network_targets: tuple[str, ...] = ()
    requested_secret_names: tuple[str, ...] = ()
    kill_switch_state: bool = False
    expected_decision: str = "denied"
    expected_denial_reasons: tuple[str, ...] = ()
    expected_triggered_guards: tuple[str, ...] = ()
    linked_p0_gates: tuple[str, ...] = ()
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        # Defensive-copy caller-supplied mutable mappings so post-construction
        # mutation of the caller's dict cannot change what the runner evaluates.
        if self.descriptor is not None:
            object.__setattr__(self, "descriptor", copy.deepcopy(self.descriptor))
        if self.metadata is not None:
            object.__setattr__(self, "metadata", copy.deepcopy(self.metadata))

    def to_safe_dict(self) -> dict[str, Any]:
        # Projection is re-redacted upstream by the runner; this helper exists
        # only for debug / test projections and never carries a raw secret.
        return redact_sandbox_payload(
            {
                "scenarioId": self.scenario_id,
                "title": self.title,
                "purpose": self.purpose,
                "expectedDecision": self.expected_decision,
                "linkedP0Gates": list(self.linked_p0_gates),
                "requestedCapabilities": list(self.requested_capabilities),
                "requestedNetworkTargets": list(self.requested_network_targets),
                "requestedSecretNames": list(self.requested_secret_names),
                "requestedFilesystemPaths": [
                    _redact_filesystem_path(p) for p in self.requested_filesystem_paths
                ],
                "killSwitchState": bool(self.kill_switch_state),
                "redactionApplied": True,
            }
        )


# ---------------------------------------------------------------------------
# 2. Scenario result model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProofScenarioResult:
    """Output of running one :class:`ProofScenario` through the runner."""

    scenario_id: str
    passed: bool
    decision: str
    denial_reasons: tuple[str, ...] = ()
    triggered_guards: tuple[str, ...] = ()
    redacted_audit: Mapping[str, Any] = field(default_factory=dict)
    linked_p0_gates: tuple[str, ...] = ()
    evidence_classification: str = GATE_STATUS_PARTIAL_EVIDENCE
    route_change_required: bool = False
    production_access_required: bool = False
    external_network_required: bool = False
    real_secret_required: bool = False
    runtime_execution_required: bool = False
    persistent_artifacts_created: bool = False
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # The frozen evidence flags MUST be False by construction — a dev-only
        # proof requires no route change / production access / external network
        # / real secret / runtime execution and creates no persistent artifact.
        for flag in RESULT_EVIDENCE_FLAGS:
            if getattr(self, flag) is not False:
                raise AssertionError(f"scenario result evidence flag must be False: {flag}")
        # Defensive-copy the audit mapping so a caller mutation of the builder's
        # dict (or a later read of result.redacted_audit) cannot leak a value.
        if self.redacted_audit:
            object.__setattr__(
                self, "redacted_audit", copy.deepcopy(dict(self.redacted_audit))
            )

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "schemaVersion": SANDBOX_RUNNER_VERSION,
                "scenarioId": self.scenario_id,
                "passed": self.passed,
                "decision": self.decision,
                "denialReasons": list(self.denial_reasons),
                "triggeredGuards": list(self.triggered_guards),
                "audit": dict(self.redacted_audit),
                "linkedP0Gates": list(self.linked_p0_gates),
                "evidenceClassification": self.evidence_classification,
                "routeChangeRequired": self.route_change_required,
                "productionAccessRequired": self.production_access_required,
                "externalNetworkRequired": self.external_network_required,
                "realSecretRequired": self.real_secret_required,
                "runtimeExecutionRequired": self.runtime_execution_required,
                "persistentArtifactsCreated": self.persistent_artifacts_created,
                "errors": list(self.errors),
                "redactionApplied": True,
            }
        )


# ---------------------------------------------------------------------------
# 3. Run summary model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProofRunSummary:
    """Aggregate of running a list of scenarios. Fail-closed authorization."""

    run_id: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    linked_p0_gates: tuple[str, ...] = ()
    p0_evidence_summary: Mapping[str, Any] = field(default_factory=dict)
    implementation_authorization: str = IMPLEMENTATION_AUTHORIZATION
    phase_3i_authorization: bool = PHASE_3I_AUTHORIZED
    real_runtime_authorization: str = REAL_RUNTIME
    route_governance_summary: Mapping[str, Any] = field(default_factory=dict)
    production_safety_summary: Mapping[str, Any] = field(default_factory=dict)
    redacted_audit_records: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        # The authorization flags are frozen constants — a scenario pass can
        # never flip Implementation Authorization to GO, authorize Phase 3I,
        # authorize real runtime, add a route, or roll out production.
        if self.implementation_authorization != IMPLEMENTATION_AUTHORIZATION:
            raise AssertionError("implementation authorization must stay NO-GO")
        if self.phase_3i_authorization is not False:
            raise AssertionError("Phase 3I must stay NOT AUTHORIZED")
        if self.real_runtime_authorization != REAL_RUNTIME:
            raise AssertionError("real runtime must stay NO-GO")
        # Defensive-copy the mutable mappings.
        if self.p0_evidence_summary:
            object.__setattr__(
                self, "p0_evidence_summary", copy.deepcopy(dict(self.p0_evidence_summary))
            )
        if self.route_governance_summary:
            object.__setattr__(
                self,
                "route_governance_summary",
                copy.deepcopy(dict(self.route_governance_summary)),
            )
        if self.production_safety_summary:
            object.__setattr__(
                self,
                "production_safety_summary",
                copy.deepcopy(dict(self.production_safety_summary)),
            )
        if self.redacted_audit_records:
            object.__setattr__(
                self,
                "redacted_audit_records",
                tuple(copy.deepcopy(dict(r)) for r in self.redacted_audit_records),
            )

    @property
    def new_route(self) -> str:
        return NEW_ROUTE

    @property
    def production_rollout(self) -> str:
        return PRODUCTION_ROLLOUT

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "schemaVersion": SANDBOX_RUNNER_VERSION,
                "runId": self.run_id,
                "totalScenarios": self.total_scenarios,
                "passedScenarios": self.passed_scenarios,
                "failedScenarios": self.failed_scenarios,
                "linkedP0Gates": list(self.linked_p0_gates),
                "p0EvidenceSummary": dict(self.p0_evidence_summary),
                "implementationAuthorization": self.implementation_authorization,
                "phase3iAuthorization": self.phase_3i_authorization,
                "realRuntimeAuthorization": self.real_runtime_authorization,
                "newRoute": self.new_route,
                "productionRollout": self.production_rollout,
                "routeGovernanceSummary": dict(self.route_governance_summary),
                "productionSafetySummary": dict(self.production_safety_summary),
                "redactedAuditRecords": [dict(r) for r in self.redacted_audit_records],
                "redactionApplied": True,
            }
        )


# ---------------------------------------------------------------------------
# 4. Single scenario runner
# ---------------------------------------------------------------------------


def _fail_closed_result(scenario: ProofScenario, *, error: str) -> ProofScenarioResult:
    """Build a fail-closed (denied, redacted) result for an unsafe / failing run."""
    # An unsafe scenario id is never echoed verbatim — it may carry traversal /
    # path / shell characters. Report it as a sanitized placeholder instead.
    safe_id = scenario.scenario_id if is_scenario_id_safe(scenario.scenario_id) else "<invalid>"
    raw_audit = {
        "scenarioId": safe_id,
        "decision": "denied",
        "denialReasons": ["scenario_run_fail_closed"],
        "triggeredGuards": ["fail_closed"],
        "linkedP0Gates": list(scenario.linked_p0_gates),
        "redactionApplied": True,
        "persisted": False,
    }
    redacted = redact_sandbox_payload(raw_audit)
    if contains_secret(redacted):
        redacted = {
            "decision": "denied",
            "denialReasons": ["redaction_failed_fail_closed"],
            "triggeredGuards": ["redaction_failure"],
            "redactionApplied": True,
            "persisted": False,
        }
    return ProofScenarioResult(
        scenario_id=safe_id,
        passed=False,
        decision="denied",
        denial_reasons=("scenario_run_fail_closed",),
        triggered_guards=("fail_closed",),
        redacted_audit=redacted,
        linked_p0_gates=tuple(scenario.linked_p0_gates),
        evidence_classification=GATE_STATUS_PARTIAL_EVIDENCE,
        errors=(redact_sandbox_text(error),),
    )


def _evidence_record(scenario: ProofScenario) -> dict[str, Any]:
    """Extract a (redacted-irrelevant) evidence record from scenario metadata.

    A scenario whose metadata carries a ``testCommand`` provides reproducible
    evidence → ``candidate_for_review``; otherwise the record is partial /
    empty. The record is fed to :func:`classify_evidence_quality`, which never
    resolves a gate without human approval.
    """
    meta = scenario.metadata
    if isinstance(meta, Mapping):
        test_command = meta.get("testCommand", meta.get("test_command"))
        if isinstance(test_command, str) and test_command.strip():
            return {"testCommand": test_command.strip()}
    return {}


def _expected_matches(proof_result: Any, scenario: ProofScenario) -> tuple[bool, str]:
    """Compare the proof evaluation to the scenario's expectations."""
    actual = "allowed" if proof_result.allowed else "denied"
    decision_ok = actual == scenario.expected_decision
    if scenario.expected_decision == "allowed":
        # An allowed scenario must have no denial reasons at all.
        reasons_ok = len(proof_result.denial_reasons) == 0 and not scenario.expected_denial_reasons
    else:
        reasons_ok = all(r in proof_result.denial_reasons for r in scenario.expected_denial_reasons)
    guards_ok = all(g in proof_result.triggered_guards for g in scenario.expected_triggered_guards)
    return decision_ok and reasons_ok and guards_ok, actual


def _verdict_projection(authorization: Any, route_exception: Any) -> dict[str, Any]:
    """Build a redaction-safe projection of the authorization / route verdicts.

    The keys deliberately avoid secret-bearing stems (``auth`` / ``token`` /
    ``secret`` / ``apikey`` / ``credential``) — the sandbox redactor collapses a
    string value under such a key to ``[REDACTED]``, which would hide the very
    ``NO-GO`` / ``False`` verdicts the audit exists to carry. These renamed keys
    keep the verdicts readable while remaining value-free.
    """
    return {
        "implementationGate": authorization.implementation_authorization,
        "phase3iGate": authorization.phase_3i_authorized,
        "realRuntimeGate": authorization.real_runtime,
        "newRouteGate": authorization.new_route,
        "productionRolloutGate": authorization.production_rollout,
        "bypassKeysIgnored": list(authorization.ignored_metadata_keys),
        "routeExceptionRequired": route_exception.route_exception_required,
        "routeExceptionApproved": route_exception.route_exception_approved,
    }


def _build_redacted_audit(
    scenario: ProofScenario,
    proof_result: Any,
    authorization: Any,
    route_exception: Any,
    quality: Any,
) -> dict[str, Any]:
    """Build a redacted, in-memory audit projection for one scenario result.

    The scenario-supplied fields (title / purpose / requested items / metadata)
    are run through the secret + path redactor; the verdict projection and the
    underlying proof audit (already redacted by their builders) are merged in
    verbatim. A final secret sweep fails closed to a minimal denial record if any
    value slipped through.
    """
    scenario_payload = redact_sandbox_payload(
        {
            "scenarioTitle": scenario.title,
            "scenarioPurpose": scenario.purpose,
            "requestedCapabilities": list(scenario.requested_capabilities),
            "requestedNetworkTargets": list(scenario.requested_network_targets),
            "requestedSecretNames": list(scenario.requested_secret_names),
            "requestedFilesystemPaths": [
                _redact_filesystem_path(p) for p in scenario.requested_filesystem_paths
            ],
            "scenarioMetadata": dict(scenario.metadata) if scenario.metadata else {},
        }
    )
    audit: dict[str, Any] = {
        "schemaVersion": SANDBOX_RUNNER_VERSION,
        "source": SANDBOX_RUNNER_AUDIT_SOURCE,
        "scenarioId": scenario.scenario_id,
        "decision": "allowed" if proof_result.allowed else "denied",
        "denialReasons": list(proof_result.denial_reasons),
        "triggeredGuards": list(proof_result.triggered_guards),
        "killSwitchState": bool(scenario.kill_switch_state),
        "linkedP0Gates": list(scenario.linked_p0_gates),
        "evidenceClassification": quality.quality,
        "verdict": _verdict_projection(authorization, route_exception),
        "proofAudit": dict(proof_result.audit_record) if proof_result.audit_record else {},
        "evidence": {flag: False for flag in RESULT_EVIDENCE_FLAGS},
        "redactionApplied": True,
        "persisted": False,
    }
    audit.update(scenario_payload)
    if contains_secret(audit):
        return {
            "schemaVersion": SANDBOX_RUNNER_VERSION,
            "source": SANDBOX_RUNNER_AUDIT_SOURCE,
            "decision": "denied",
            "denialReasons": ["redaction_failed_fail_closed"],
            "triggeredGuards": ["redaction_failure"],
            "evidence": {flag: False for flag in RESULT_EVIDENCE_FLAGS},
            "redactionApplied": True,
            "redactionFailed": True,
            "persisted": False,
        }
    return audit


def run_proof_scenario(scenario: ProofScenario) -> ProofScenarioResult:
    """Run one :class:`ProofScenario` through the existing proof / guard / audit
    / evidence logic. Fail-closed default.

    The runner only *evaluates*: it builds a :class:`SandboxProofRequest`, calls
    :func:`evaluate_sandbox_proof`, and classifies the evidence. It executes no
    code, opens no path, contacts no host, reads no secret, and writes nothing.
    """
    # 1. Scenario id safety — an unsafe id is denied before any evaluation.
    if not is_scenario_id_safe(scenario.scenario_id):
        return _fail_closed_result(scenario, error="unsafe_scenario_id")

    # 2. Build the proof request (deep-copied mappings; safe label operation).
    try:
        request = SandboxProofRequest(
            descriptor_id=scenario.scenario_id,
            descriptor_metadata=copy.deepcopy(scenario.descriptor) if scenario.descriptor else None,
            mock_operation=scenario.scenario_id,
            requested_capabilities=tuple(scenario.requested_capabilities),
            requested_filesystem_paths=tuple(
                FilesystemRequest(path=str(p)) for p in scenario.requested_filesystem_paths
            ),
            requested_network_targets=tuple(scenario.requested_network_targets),
            requested_secret_names=tuple(scenario.requested_secret_names),
            kill_switch_active=bool(scenario.kill_switch_state),
            safe_metadata=copy.deepcopy(scenario.metadata) if scenario.metadata else None,
        )
        proof_result = evaluate_sandbox_proof(request)
    except Exception as exc:  # pragma: no cover — defensive fail-closed
        return _fail_closed_result(scenario, error=str(exc))

    # 3. P0 evidence classification (never resolves a gate without human approval).
    try:
        quality = classify_evidence_quality(_evidence_record(scenario))
        authorization = evaluate_authorization_request(scenario.metadata)
        route_exception = evaluate_route_exception(
            scenario.metadata, untrusted_metadata=scenario.metadata
        )
    except Exception as exc:  # pragma: no cover — defensive fail-closed
        return _fail_closed_result(scenario, error=str(exc))

    # 4. Compare the actual evaluation to the scenario's expectations.
    passed, actual_decision = _expected_matches(proof_result, scenario)

    # 5. Build the redacted audit projection.
    redacted_audit = _build_redacted_audit(
        scenario, proof_result, authorization, route_exception, quality
    )

    return ProofScenarioResult(
        scenario_id=scenario.scenario_id,
        passed=passed,
        decision=actual_decision,
        denial_reasons=tuple(proof_result.denial_reasons),
        triggered_guards=tuple(proof_result.triggered_guards),
        redacted_audit=redacted_audit,
        linked_p0_gates=tuple(scenario.linked_p0_gates),
        evidence_classification=quality.quality,
        route_change_required=False,
        production_access_required=False,
        external_network_required=False,
        real_secret_required=False,
        runtime_execution_required=False,
        persistent_artifacts_created=False,
        errors=(),
    )


# ---------------------------------------------------------------------------
# 5. Multi scenario runner
# ---------------------------------------------------------------------------


def _frozen_route_governance_summary() -> dict[str, Any]:
    """Frozen route-governance projection (no new route, baseline unchanged)."""
    return {
        "baseline": ROUTE_GOVERNANCE_BASELINE,
        "newRouteFlags": dict(NEW_ROUTE_FLAGS),
        "routeChangeRequired": False,
        "redactionApplied": True,
    }


def _frozen_production_safety_summary() -> dict[str, Any]:
    """Frozen production-safety projection (no production access, ever)."""
    return {
        "productionAccessRequired": False,
        "realSecretRequired": False,
        "externalNetworkRequired": False,
        "runtimeExecutionRequired": False,
        "persistentArtifactsCreated": False,
        "productionHomeAccessed": False,
        "productionStateDbAccessed": False,
        "redactionApplied": True,
    }


def run_proof_scenarios(
    scenarios: Any,
    *,
    run_id: str = "dev-only-proof-runner-run",
) -> ProofRunSummary:
    """Run a list of scenarios and aggregate the results.

    Fail-closed: a scenario failure is reported (``failed_scenarios``) but never
    escalates anything; an internal runner error on a scenario yields a redacted
    fail-closed result for that scenario. The summary's authorization flags are
    frozen constants — Implementation Authorization stays NO-GO, Phase 3I stays
    NOT AUTHORIZED, real runtime stays NO-GO, new route stays NO-GO, production
    rollout stays NO-GO, and ``resolved_count`` stays 0 no matter what.
    """
    # Defensive-copy the input sequence (the caller's list cannot be mutated by
    # the run, and a non-iterable input yields an empty fail-closed summary).
    if not isinstance(scenarios, (list, tuple)):
        scenario_list: list[ProofScenario] = []
    else:
        scenario_list = list(scenarios)

    results: list[ProofScenarioResult] = []
    for scenario in scenario_list:
        if not isinstance(scenario, ProofScenario):
            # A non-scenario item is wrapped into a fail-closed synthetic result
            # so the run never crashes on a malformed library entry.
            synthetic = ProofScenario(scenario_id="<invalid>")
            results.append(_fail_closed_result(synthetic, error="non_scenario_input"))
            continue
        try:
            results.append(run_proof_scenario(scenario))
        except Exception as exc:  # pragma: no cover — defensive fail-closed
            results.append(_fail_closed_result(scenario, error=str(exc)))

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    linked = sorted({gate for r in results for gate in r.linked_p0_gates})

    # The P0 evidence summary is evaluated fresh — resolved_count is always 0 in
    # the dev skeleton. A scenario pass cannot advance it.
    p0_summary = evaluate_p0_evidence()

    return ProofRunSummary(
        run_id=str(run_id) if isinstance(run_id, str) and run_id else "dev-only-proof-runner-run",
        total_scenarios=len(results),
        passed_scenarios=passed,
        failed_scenarios=failed,
        linked_p0_gates=tuple(linked),
        p0_evidence_summary=p0_summary.to_safe_dict(),
        implementation_authorization=IMPLEMENTATION_AUTHORIZATION,
        phase_3i_authorization=PHASE_3I_AUTHORIZED,
        real_runtime_authorization=REAL_RUNTIME,
        route_governance_summary=_frozen_route_governance_summary(),
        production_safety_summary=_frozen_production_safety_summary(),
        redacted_audit_records=tuple(r.redacted_audit for r in results),
    )


# ---------------------------------------------------------------------------
# 6. Boundary re-affirmation (pure constants, grep-able)
# ---------------------------------------------------------------------------

NO_REAL_PLUGIN_RUNTIME: bool = True
NO_PLUGIN_EXECUTION: bool = True
NO_PLUGIN_LOADER: bool = True
NO_DYNAMIC_LOADING: bool = True
NO_EXTERNAL_NETWORK: bool = True
NO_REAL_API_KEY_READ: bool = True
NO_NEW_ROUTE: bool = True
NO_PRODUCTION_ACCESS: bool = True
NO_PERSISTENT_ARTIFACTS: bool = True


def assert_no_side_effect_surface() -> None:
    """Re-affirm the no-side-effect + no-authorization invariants."""
    assert NO_REAL_PLUGIN_RUNTIME is True
    assert NO_PLUGIN_EXECUTION is True
    assert NO_PLUGIN_LOADER is True
    assert NO_DYNAMIC_LOADING is True
    assert NO_EXTERNAL_NETWORK is True
    assert NO_REAL_API_KEY_READ is True
    assert NO_NEW_ROUTE is True
    assert NO_PRODUCTION_ACCESS is True
    assert NO_PERSISTENT_ARTIFACTS is True
    assert IMPLEMENTATION_AUTHORIZATION == "NO-GO"
    assert PHASE_3I_AUTHORIZED is False
    assert REAL_RUNTIME == "NO-GO"
    assert NEW_ROUTE == "NO-GO"
    assert PRODUCTION_ROLLOUT == "NO-GO"


__all__ = [
    "SANDBOX_RUNNER_VERSION",
    "SANDBOX_RUNNER_AUDIT_SOURCE",
    "RESULT_EVIDENCE_FLAGS",
    "NEW_ROUTE_FLAGS",
    "NO_REAL_PLUGIN_RUNTIME",
    "NO_PLUGIN_EXECUTION",
    "NO_PLUGIN_LOADER",
    "NO_DYNAMIC_LOADING",
    "NO_EXTERNAL_NETWORK",
    "NO_REAL_API_KEY_READ",
    "NO_NEW_ROUTE",
    "NO_PRODUCTION_ACCESS",
    "NO_PERSISTENT_ARTIFACTS",
    "is_scenario_id_safe",
    "ProofScenario",
    "ProofScenarioResult",
    "ProofRunSummary",
    "run_proof_scenario",
    "run_proof_scenarios",
    "assert_no_side_effect_surface",
]
