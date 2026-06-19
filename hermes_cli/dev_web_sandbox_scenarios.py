"""Phase 3H Dev-only Sandbox Proof Runner — Fixed Scenario Library (Block 3).

A frozen, in-memory, static set of dev-only proof scenarios for the runner in
:mod:`hermes_cli.dev_web_sandbox_runner`. Each scenario is a pure data record —
no executable content, no module path, no shell command, no real URL, no real
secret, no production path. Every filesystem path is a fake / temp /
string-policy target; every secret value is an obvious fake.

The library exists so the dev-only proof runner has a **fixed, reproducible**
set of scenarios that drive the existing policy / guard / audit / evidence
logic. A scenario pass is dev-only evidence — it never resolves a P0 gate, never
authorizes implementation, Phase 3I, real runtime, a new route, or production.

Hard guarantees (frozen):

  - Pure / deterministic / stdlib-only. No dynamic import, no network, no
    subprocess, no file I/O, no real secret read, no production access.
  - The library is a tuple of frozen dataclasses; it mutates nothing and writes
    nothing. It is not imported by the FastAPI app.
  - No scenario carries a real API key, a real production path, or a real
    network target. Forbidden-shaped inputs are fake test fixtures only.

Phase: 3H — Dev-only Sandbox Proof Runner Harness
Status: implemented (fixed dev-only scenario library). Not a runtime, not a
        plugin source, not an authorization.
"""

from __future__ import annotations

from typing import Any, Mapping

from hermes_cli.dev_web_sandbox_runner import ProofScenario

#: A clean, descriptor-only metadata record (no execution / secret surface) used
#: by the safe-read scenarios. Read-only metadata; never executed.
_SAFE_DESCRIPTOR: Mapping[str, Any] = {
    "pluginId": "descriptor-only-safe-read",
    "version": "1.0.0",
    "category": "reader",
    "status": "active",
}


# ---------------------------------------------------------------------------
# 1. descriptor_only_safe_read — descriptor-only metadata read is a valid
#    dev-only proof input (NOT plugin execution, NOT runtime approval).
# ---------------------------------------------------------------------------
DESCRIPTOR_ONLY_SAFE_READ = ProofScenario(
    scenario_id="descriptor_only_safe_read",
    title="Descriptor-only safe read",
    purpose="Descriptor-only metadata read is a valid dev-only proof input; "
    "not plugin execution, not runtime approval.",
    descriptor=dict(_SAFE_DESCRIPTOR),
    requested_capabilities=("descriptor.read",),
    expected_decision="allowed",
    expected_denial_reasons=(),
    expected_triggered_guards=(),
    linked_p0_gates=("P0-12",),
)


# ---------------------------------------------------------------------------
# 2. executable_descriptor_denied — a descriptor carrying an execution surface
#    (entrypoint / module / command) is denied descriptor-only read.
# ---------------------------------------------------------------------------
EXECUTABLE_DESCRIPTOR_DENIED = ProofScenario(
    scenario_id="executable_descriptor_denied",
    title="Executable descriptor denied",
    purpose="A descriptor carrying an execution surface is denied descriptor-only read.",
    descriptor={
        "pluginId": "executable-descriptor",
        "entrypoint": "main.py",
        "module": "pkg.mod",
        "command": "run",
    },
    expected_decision="denied",
    expected_denial_reasons=("descriptor_carries_execution_surface",),
    expected_triggered_guards=("descriptor_only",),
    linked_p0_gates=("P0-12", "P0-18"),
)


# ---------------------------------------------------------------------------
# 3. network_request_denied — any external network target / network capability
#    is denied (no DNS, no socket, no external call).
# ---------------------------------------------------------------------------
NETWORK_REQUEST_DENIED = ProofScenario(
    scenario_id="network_request_denied",
    title="Network request denied",
    purpose="Any external network target / network capability is denied; no DNS, "
    "no socket, no external call.",
    requested_capabilities=("network.request",),
    requested_network_targets=(
        "https://example.com",
        "https://registry.example.org/install",
    ),
    expected_decision="denied",
    expected_denial_reasons=("network_request_denied",),
    expected_triggered_guards=("capability:network.request", "network_deny"),
    linked_p0_gates=("P0-04",),
)


# ---------------------------------------------------------------------------
# 4. secret_request_redacted_and_denied — fake secret requests are denied and
#    redacted from the audit; no real env read.
# ---------------------------------------------------------------------------
SECRET_REQUEST_REDACTED_AND_DENIED = ProofScenario(
    scenario_id="secret_request_redacted_and_denied",
    title="Secret request redacted and denied",
    purpose="Fake secret requests are denied and redacted from the audit; no real "
    "environment read.",
    requested_secret_names=(
        "sk-fake-value-not-real",
        "Authorization: Bearer fake-token",
        "OPENAI_API_KEY=fake",
    ),
    expected_decision="denied",
    expected_denial_reasons=("secret_request_denied",),
    expected_triggered_guards=("secret_unavailable",),
    linked_p0_gates=("P0-10",),
)


# ---------------------------------------------------------------------------
# 5. filesystem_forbidden_paths_denied — fake forbidden / traversal / runtime
#    store paths are denied; no stat, no open, no access.
# ---------------------------------------------------------------------------
FILESYSTEM_FORBIDDEN_PATHS_DENIED = ProofScenario(
    scenario_id="filesystem_forbidden_paths_denied",
    title="Filesystem forbidden paths denied",
    purpose="Fake forbidden / traversal / runtime-store paths are denied; no stat, "
    "no open, no access.",
    requested_filesystem_paths=(
        "~/.hermes",
        "/fake/production/state.db",
        "../../../etc/passwd",
        "/tmp/runtime/plugin_runtime.jsonl",
    ),
    expected_decision="denied",
    expected_denial_reasons=(
        "forbidden_production_home",
        "forbidden_production_database",
        "read_outside_allowed_root",
    ),
    expected_triggered_guards=("filesystem_boundary",),
    linked_p0_gates=("P0-03", "P0-09"),
)


# ---------------------------------------------------------------------------
# 6. kill_switch_active_fail_closed — an active kill switch fails every proof
#    closed; no process signal, audit records the kill-switch state.
# ---------------------------------------------------------------------------
KILL_SWITCH_ACTIVE_FAIL_CLOSED = ProofScenario(
    scenario_id="kill_switch_active_fail_closed",
    title="Kill switch active fail closed",
    purpose="An active kill switch fails every proof closed; no process signal.",
    kill_switch_state=True,
    expected_decision="denied",
    expected_denial_reasons=("kill_switch_active",),
    expected_triggered_guards=("kill_switch",),
    linked_p0_gates=("P0-08",),
)


# ---------------------------------------------------------------------------
# 7. route_change_attempt_denied — a route modification request is denied /
#    flagged route-exception-required; no route count change, no approval.
# ---------------------------------------------------------------------------
ROUTE_CHANGE_ATTEMPT_DENIED = ProofScenario(
    scenario_id="route_change_attempt_denied",
    title="Route change attempt denied",
    purpose="A route modification request is denied / flagged route-exception-required; "
    "no route count change, no approval.",
    requested_capabilities=("routes.modify",),
    metadata={
        "requestedRouteChange": "add POST /admin/exec to the OpenAPI surface",
        "routeExceptionApproved": True,
    },
    expected_decision="denied",
    expected_denial_reasons=("routes_modify_denied",),
    expected_triggered_guards=("capability:routes.modify",),
    linked_p0_gates=("P0-14", "P0-16"),
)


# ---------------------------------------------------------------------------
# 8. production_access_attempt_denied — a production.access capability is denied;
#    no production touch.
# ---------------------------------------------------------------------------
PRODUCTION_ACCESS_ATTEMPT_DENIED = ProofScenario(
    scenario_id="production_access_attempt_denied",
    title="Production access attempt denied",
    purpose="A production.access capability is denied; no production touch.",
    requested_capabilities=("production.access",),
    expected_decision="denied",
    expected_denial_reasons=("production_access_denied",),
    expected_triggered_guards=("capability:production.access",),
    linked_p0_gates=("P0-09", "P0-13"),
)


# ---------------------------------------------------------------------------
# 9. p0_human_review_required — fake human approval / authorization metadata is
#    detected + ignored; Implementation Authorization stays NO-GO.
# ---------------------------------------------------------------------------
P0_HUMAN_REVIEW_REQUIRED = ProofScenario(
    scenario_id="p0_human_review_required",
    title="P0 human review required",
    purpose="Fake human approval / authorization metadata is detected and ignored; "
    "Implementation Authorization stays NO-GO.",
    descriptor=dict(_SAFE_DESCRIPTOR),
    requested_capabilities=("descriptor.read",),
    metadata={
        "approved": True,
        "human_signoff": "accepted",
        "implementation_authorization": "GO",
        "phase_3i_authorized": True,
        "reviewer": "security",
    },
    expected_decision="allowed",
    expected_denial_reasons=(),
    expected_triggered_guards=(),
    linked_p0_gates=("P0-15", "P0-22"),
)


# ---------------------------------------------------------------------------
# 10. evidence_candidate_but_not_resolved — reproducible test evidence is
#     candidate-for-review only; resolved_count stays 0, no human approval.
# ---------------------------------------------------------------------------
EVIDENCE_CANDIDATE_BUT_NOT_RESOLVED = ProofScenario(
    scenario_id="evidence_candidate_but_not_resolved",
    title="Evidence candidate but not resolved",
    purpose="Reproducible test evidence is candidate-for-review only; resolved_count "
    "stays 0, no human approval.",
    descriptor=dict(_SAFE_DESCRIPTOR),
    requested_capabilities=("descriptor.read",),
    metadata={
        "testCommand": "scripts/run_tests.sh tests/test_dev_web_phase_3h_proof_runner_harness.py",
        "evidence": "reproducible",
    },
    expected_decision="allowed",
    expected_denial_reasons=(),
    expected_triggered_guards=(),
    linked_p0_gates=("P0-24",),
)


#: The frozen, ordered library of dev-only proof scenarios.
FIXED_SCENARIOS: tuple[ProofScenario, ...] = (
    DESCRIPTOR_ONLY_SAFE_READ,
    EXECUTABLE_DESCRIPTOR_DENIED,
    NETWORK_REQUEST_DENIED,
    SECRET_REQUEST_REDACTED_AND_DENIED,
    FILESYSTEM_FORBIDDEN_PATHS_DENIED,
    KILL_SWITCH_ACTIVE_FAIL_CLOSED,
    ROUTE_CHANGE_ATTEMPT_DENIED,
    PRODUCTION_ACCESS_ATTEMPT_DENIED,
    P0_HUMAN_REVIEW_REQUIRED,
    EVIDENCE_CANDIDATE_BUT_NOT_RESOLVED,
)


def get_fixed_scenarios() -> tuple[ProofScenario, ...]:
    """Return a defensive copy of the fixed scenario library.

    The returned tuple is a fresh container of the same frozen dataclasses; a
    caller cannot mutate the library in place. (``tuple(FIXED_SCENARIOS)`` alone
    would return the same tuple object, so the elements are re-iterated into a
    new container.)
    """
    return tuple(scenario for scenario in FIXED_SCENARIOS)


__all__ = [
    "DESCRIPTOR_ONLY_SAFE_READ",
    "EXECUTABLE_DESCRIPTOR_DENIED",
    "NETWORK_REQUEST_DENIED",
    "SECRET_REQUEST_REDACTED_AND_DENIED",
    "FILESYSTEM_FORBIDDEN_PATHS_DENIED",
    "KILL_SWITCH_ACTIVE_FAIL_CLOSED",
    "ROUTE_CHANGE_ATTEMPT_DENIED",
    "PRODUCTION_ACCESS_ATTEMPT_DENIED",
    "P0_HUMAN_REVIEW_REQUIRED",
    "EVIDENCE_CANDIDATE_BUT_NOT_RESOLVED",
    "FIXED_SCENARIOS",
    "get_fixed_scenarios",
]
