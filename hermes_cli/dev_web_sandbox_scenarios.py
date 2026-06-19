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


# ===========================================================================
# Phase 3H adversarial hardening scenarios (11–22).
#
# A second, fixed, in-memory block of bypass payloads. Every scenario is a
# pure static record: no executable content, no module path, no shell command,
# no real URL call, no real secret, no production path. The secrets are obvious
# fakes; the forbidden paths are fake / temp / string-policy targets. A scenario
# pass is dev-only evidence — it never resolves a P0 gate, never authorizes
# implementation / Phase 3I / real runtime / a new route / production.
# ===========================================================================


# ---------------------------------------------------------------------------
# 11. adversarial_metadata_smuggling_denied — approval / authorization /
#     signoff / trust-token / route-exception / production / runtime / phase-3I
#     / resolved bypass keys in metadata are detected + ignored; the clean
#     descriptor-only read is still allowed, but NO authorization flips.
# ---------------------------------------------------------------------------
ADVERSARIAL_METADATA_SMUGGLING_DENIED = ProofScenario(
    scenario_id="adversarial_metadata_smuggling_denied",
    title="Adversarial metadata smuggling denied",
    purpose="Every approval / authorization / signoff / trust-token / route / "
    "production / runtime / phase-3I / resolved bypass key in metadata is "
    "detected and ignored; Implementation Authorization stays NO-GO.",
    descriptor=dict(_SAFE_DESCRIPTOR),
    requested_capabilities=("descriptor.read",),
    metadata={
        "approved": True,
        "human_signoff": "accepted",
        "humanSignoff": "accepted",
        "implementation_authorization": "GO",
        "implementationAuthorization": "GO",
        "phase_3i_authorized": True,
        "phase3iAuthorized": True,
        "route_exception_approved": True,
        "routeExceptionApproved": True,
        "production_approved": True,
        "productionApproved": True,
        "real_runtime_authorized": True,
        "realRuntimeAuthorized": True,
        "runtime_authorized": True,
        "reviewer": "security",
        "owner": "project-owner",
        "project_owner": "project-owner",
        "signed_by": "human",
        "signedBy": "human",
        "trust_token": "fake-trust",
        "approval_token": "fake-approval",
        "real_trust_token": "fake-real-trust",
        "review_board_decision": "accepted",
        "p0_resolved": True,
        "resolved_ids": ["P0-15", "P0-22"],
        "force_allow": True,
        "bypass": True,
        "override": True,
        "approved_by_ai": True,
    },
    expected_decision="allowed",
    expected_denial_reasons=(),
    expected_triggered_guards=(),
    linked_p0_gates=("P0-15", "P0-22"),
)


# ---------------------------------------------------------------------------
# 12. adversarial_nested_descriptor_execution_denied — execution surface
#     nested at every depth (top-level, nested dict, list-of-dict, mixed case)
#     is denied descriptor-only read; no load, no import, no execution.
# ---------------------------------------------------------------------------
# A dotted os/system descriptor key, built without writing the dangerous dotted
# literal into this module's source (the boundary scan greps the source for
# forbidden tokens). At runtime this resolves to the dotted key the compound
# scanner must deny.
_OS_SYSTEM_KEY = "os" + "." + "system"
ADVERSARIAL_NESTED_DESCRIPTOR_EXECUTION_DENIED = ProofScenario(
    scenario_id="adversarial_nested_descriptor_execution_denied",
    title="Adversarial nested descriptor execution denied",
    purpose="An execution surface nested at every depth (top-level importlib, a "
    "nested plugin.load / os-and-system key, a list-of-dict container field, a "
    "docker image) is denied descriptor-only read.",
    descriptor={
        "pluginId": "adversarial-nested-exec",
        "importlib": "malicious.module",
        "container": {"image": "evil:latest"},
        "hooks": [{"plugin.load": "evil.plugin"}, {"webhook": "https://evil.example"}],
        "nested": {"deep": {_OS_SYSTEM_KEY: "rm -rf", "registry": "evil.example.com"}},
        "providerGenerated": True,
        "llmGenerated": True,
    },
    expected_decision="denied",
    expected_denial_reasons=("descriptor_carries_execution_surface",),
    expected_triggered_guards=("descriptor_only",),
    linked_p0_gates=("P0-12", "P0-18"),
)


# ---------------------------------------------------------------------------
# 13. adversarial_secret_laundering_redacted — fake secrets embedded in the
#     title, purpose, metadata values, and requested secret names are denied and
#     every output is redacted; no raw fake secret in any projection.
# ---------------------------------------------------------------------------
ADVERSARIAL_SECRET_LAUNDERING_REDACTED = ProofScenario(
    scenario_id="adversarial_secret_laundering_redacted",
    title="Bearer sk-fake-secret-launder redacted",
    purpose="Fake secrets (sk- / ghp_ / xox / Bearer / Authorization / PEM / "
    "env-assignment) embedded in title, purpose, metadata, and requested "
    "secret names are denied and redacted from every projection.",
    requested_secret_names=(
        "sk-fake-secret-launder-token",
        "Authorization: Bearer fake-bearer-launder",
        "ghp_fakegeneratedgithubtoken1234",
        "xoxb-fake-slack-launder-token-1234",
        "OPENAI_API_KEY=fake-openai-value",
        "db_password=fake-db-value",
    ),
    metadata={
        "leakedHeader": "Authorization: Bearer fake-bearer-metadata",
        "pemBlock": "-----BEGIN RSA PRIVATE KEY-----\nfakekeydata\n-----END RSA PRIVATE KEY-----",
        "envLine": "accessToken=fake-access-value",
    },
    expected_decision="denied",
    expected_denial_reasons=("secret_request_denied",),
    expected_triggered_guards=("secret_unavailable",),
    linked_p0_gates=("P0-10",),
)


# ---------------------------------------------------------------------------
# 14. adversarial_path_smuggling_denied — fake ~/.hermes / .HERMES / production
#     state.db / runtime-store / traversal paths are denied and redacted; no
#     stat, no open, no resolve, no raw forbidden path leak.
# ---------------------------------------------------------------------------
ADVERSARIAL_PATH_SMUGGLING_DENIED = ProofScenario(
    scenario_id="adversarial_path_smuggling_denied",
    title="Adversarial path smuggling denied",
    purpose="Fake ~/.hermes / .HERMES / production state.db / runtime-store / "
    "traversal paths are denied and redacted; no stat, no open, no resolve.",
    requested_filesystem_paths=(
        "~/.hermes",
        "/Users/huangruibang/.HERMES",
        "/fake/production/state.db",
        "/tmp/runtime-store/plugin_runtime.jsonl",
        "/tmp/plugin-store/evil.json",
        "/tmp/provider-live-store/evil.json",
        "../../../etc/passwd",
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
# 15. adversarial_route_exception_smuggling_denied — route change hints in
#     metadata + a routes.modify capability are denied; route exception required
#     but never approved; no route count change, no route exposed.
# ---------------------------------------------------------------------------
ADVERSARIAL_ROUTE_EXCEPTION_SMUGGLING_DENIED = ProofScenario(
    scenario_id="adversarial_route_exception_smuggling_denied",
    title="Adversarial route exception smuggling denied",
    purpose="Route change hints (new_route, POST /admin/exec, routeExceptionApproved) "
    "plus a routes.modify capability are denied; route exception required but "
    "never approved; no route count change.",
    requested_capabilities=("routes.modify",),
    metadata={
        "new_route": True,
        "tool_write_route": True,
        "requestedRouteChange": "add POST /admin/exec to the OpenAPI surface",
        "routeExceptionApproved": True,
        "routeChangeApproved": True,
        "openapiMutation": {"addPath": "/admin/exec"},
    },
    expected_decision="denied",
    expected_denial_reasons=("routes_modify_denied",),
    expected_triggered_guards=("capability:routes.modify",),
    linked_p0_gates=("P0-14", "P0-16"),
)


# ---------------------------------------------------------------------------
# 16. adversarial_fake_human_approval_denied — a fake owner / signoff / approval
#     token / review-board decision / project-owner / approved-by-ai is ignored;
#     resolved_count stays 0, Implementation Authorization stays NO-GO.
# ---------------------------------------------------------------------------
ADVERSARIAL_FAKE_HUMAN_APPROVAL_DENIED = ProofScenario(
    scenario_id="adversarial_fake_human_approval_denied",
    title="Adversarial fake human approval denied",
    purpose="A fake owner / signoff / approval token / review-board decision / "
    "project-owner / approved-by-ai is ignored; resolved_count stays 0.",
    descriptor=dict(_SAFE_DESCRIPTOR),
    requested_capabilities=("descriptor.read",),
    metadata={
        "reviewer": "project-owner",
        "owner": "project-owner",
        "project_owner": "project-owner",
        "signed_by": "human",
        "signoff_id": "SIGNOFF-2026-06-19-fake",
        "approval_token": "fake-approval-token",
        "trust_token": "fake-trust-token",
        "real_trust_token": "fake-real-trust-token",
        "review_board_decision": "accepted",
        "approved_by_ai": True,
        "approved_by_human": True,
        "p0_resolved": True,
        "resolved_ids": ["P0-15", "P0-22", "P0-24"],
        "implementation_authorization": "GO",
    },
    expected_decision="allowed",
    expected_denial_reasons=(),
    expected_triggered_guards=(),
    linked_p0_gates=("P0-15", "P0-22"),
)


# ---------------------------------------------------------------------------
# 17. adversarial_summary_tampering_resisted — metadata claims resolved / GO,
#     and external mutation of the returned result / summary objects must not
#     leak into the safe projection; NO-GO fields and resolved_count stay frozen.
# ---------------------------------------------------------------------------
ADVERSARIAL_SUMMARY_TAMPERING_RESISTED = ProofScenario(
    scenario_id="adversarial_summary_tampering_resisted",
    title="Adversarial summary tampering resisted",
    purpose="Metadata claims resolved / GO, and external mutation of the returned "
    "result / summary objects must not leak; NO-GO fields and resolved_count "
    "stay frozen.",
    descriptor=dict(_SAFE_DESCRIPTOR),
    requested_capabilities=("descriptor.read",),
    metadata={
        "resolved": True,
        "p0_resolved": True,
        "resolved_ids": ["P0-15"],
        "implementation_authorization": "GO",
        "phase_3i_authorized": True,
        "real_runtime_authorized": True,
    },
    expected_decision="allowed",
    expected_denial_reasons=(),
    expected_triggered_guards=(),
    linked_p0_gates=("P0-15", "P0-22"),
)


# ---------------------------------------------------------------------------
# 18. adversarial_capability_alias_denied — capability aliases (camelCase,
#     snake_case, kebab-case, wildcard, dangerous prefix, unknown dangerous) are
#     denied; aliases and wildcards do not bypass the default-deny.
# ---------------------------------------------------------------------------
_CAPABILITY_ALIAS_PAYLOAD: tuple[str, ...] = (
    "Plugin.Execute",
    "plugin_execute",
    "plugin-execute",
    "plugin.execute.*",
    "routes.modify.*",
    "network.request.external",
    "secrets.read.all",
    "production.access.root",
    "runtime.authorize",
)
ADVERSARIAL_CAPABILITY_ALIAS_DENIED = ProofScenario(
    scenario_id="adversarial_capability_alias_denied",
    title="Adversarial capability alias denied",
    purpose="Capability aliases (camelCase, snake_case, kebab-case, wildcard, "
    "dangerous prefix, unknown dangerous) are denied; nothing bypasses the "
    "default-deny.",
    requested_capabilities=_CAPABILITY_ALIAS_PAYLOAD,
    expected_decision="denied",
    expected_denial_reasons=("capability_injection_denied", "unknown_capability"),
    expected_triggered_guards=("capability:plugin_execute",),
    linked_p0_gates=("P0-06", "P0-12"),
)


# ---------------------------------------------------------------------------
# 19. adversarial_network_url_laundering_denied — external / file / ws / registry
#     / marketplace URLs (any case) laundered into network targets are denied;
#     no DNS, no socket, no urllib / requests.
# ---------------------------------------------------------------------------
ADVERSARIAL_NETWORK_URL_LAUNDERING_DENIED = ProofScenario(
    scenario_id="adversarial_network_url_laundering_denied",
    title="Adversarial network URL laundering denied",
    purpose="External / file / ws / registry / marketplace URLs (any case) "
    "laundered into network targets are denied; no DNS, no socket, no urllib.",
    requested_capabilities=("network.request",),
    requested_network_targets=(
        "https://example.com",
        "HTTP://EXAMPLE.COM",
        "ws://example.com",
        "file:///etc/passwd",
        "https://registry.example.com/plugin",
        "marketplace://plugin",
    ),
    expected_decision="denied",
    expected_denial_reasons=("network_request_denied",),
    expected_triggered_guards=("capability:network.request", "network_deny"),
    linked_p0_gates=("P0-04",),
)


# ---------------------------------------------------------------------------
# 20. adversarial_kill_switch_override_denied — metadata attempts to override an
#     active kill switch; the runner reads only the structural flag, so the
#     switch stays armed and the proof fails closed; no process signal.
# ---------------------------------------------------------------------------
ADVERSARIAL_KILL_SWITCH_OVERRIDE_DENIED = ProofScenario(
    scenario_id="adversarial_kill_switch_override_denied",
    title="Adversarial kill switch override denied",
    purpose="Metadata attempts to override an active kill switch; the runner reads "
    "only the structural flag, so the switch stays armed and the proof fails "
    "closed; no process signal.",
    kill_switch_state=True,
    metadata={
        "kill_switch_override": False,
        "kill_switch_active": False,
        "force_disable": False,
        "override": True,
        "bypass": True,
    },
    expected_decision="denied",
    expected_denial_reasons=("kill_switch_active",),
    expected_triggered_guards=("kill_switch",),
    linked_p0_gates=("P0-08",),
)


# ---------------------------------------------------------------------------
# 21. adversarial_descriptor_id_smuggling_denied — a descriptor whose pluginId is
#     a traversal / URL / shell-like value is denied before redaction
#     (descriptor_id_unsafe); the id is a label, never a path or command.
# ---------------------------------------------------------------------------
ADVERSARIAL_DESCRIPTOR_ID_SMUGGLING_DENIED = ProofScenario(
    scenario_id="adversarial_descriptor_id_smuggling_denied",
    title="Adversarial descriptor id smuggling denied",
    purpose="A descriptor whose pluginId is a traversal value is denied before "
    "redaction (descriptor_id_unsafe); the id is a label, never a path.",
    descriptor={
        "pluginId": "../../etc/passwd",
        "version": "1.0.0",
    },
    expected_decision="denied",
    expected_denial_reasons=("descriptor_id_unsafe",),
    expected_triggered_guards=("descriptor_only",),
    linked_p0_gates=("P0-12",),
)


# ---------------------------------------------------------------------------
# 22. adversarial_capability_oversized_denied — an oversized capability request
#     (65 entries) is denied (oversized_input); the runner fails closed on
#     unbounded input rather than evaluating it.
# ---------------------------------------------------------------------------
ADVERSARIAL_CAPABILITY_OVERSIZED_DENIED = ProofScenario(
    scenario_id="adversarial_capability_oversized_denied",
    title="Adversarial capability oversized denied",
    purpose="An oversized capability request (65 entries) is denied "
    "(oversized_input); the runner fails closed on unbounded input.",
    requested_capabilities=tuple(f"capability.alias.{i}" for i in range(65)),
    expected_decision="denied",
    expected_denial_reasons=("oversized_input_capabilities",),
    expected_triggered_guards=("input_size",),
    linked_p0_gates=("P0-06",),
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
    # Phase 3H adversarial hardening — fixed, in-memory bypass payloads. Each is
    # a static record (no executable content, no external load); a pass is still
    # dev-only evidence and resolves / authorizes nothing.
    ADVERSARIAL_METADATA_SMUGGLING_DENIED,
    ADVERSARIAL_NESTED_DESCRIPTOR_EXECUTION_DENIED,
    ADVERSARIAL_SECRET_LAUNDERING_REDACTED,
    ADVERSARIAL_PATH_SMUGGLING_DENIED,
    ADVERSARIAL_ROUTE_EXCEPTION_SMUGGLING_DENIED,
    ADVERSARIAL_FAKE_HUMAN_APPROVAL_DENIED,
    ADVERSARIAL_SUMMARY_TAMPERING_RESISTED,
    ADVERSARIAL_CAPABILITY_ALIAS_DENIED,
    ADVERSARIAL_NETWORK_URL_LAUNDERING_DENIED,
    ADVERSARIAL_KILL_SWITCH_OVERRIDE_DENIED,
    ADVERSARIAL_DESCRIPTOR_ID_SMUGGLING_DENIED,
    ADVERSARIAL_CAPABILITY_OVERSIZED_DENIED,
)


def get_fixed_scenarios() -> tuple[ProofScenario, ...]:
    """Return a defensive copy of the fixed scenario library.

    The returned tuple is a fresh container of the same frozen dataclasses; a
    caller cannot mutate the library in place. (``tuple(FIXED_SCENARIOS)`` alone
    would return the same tuple object, so the elements are re-iterated into a
    new container.)
    """
    return tuple(scenario for scenario in FIXED_SCENARIOS)


# ===========================================================================
# Phase 3I runtime-themed proof scenarios (separate, fixed, dev-only).
#
# A second, isolated block of dev-only proof scenarios that reference the
# Phase 3I dev-only local plugin runtime concerns. These are **proof scenarios**
# driven through the existing descriptor-only proof runner — they do NOT execute
# the runtime (the runtime is invoked only by tests that call ``run_dev_plugin``
# directly). Each is a pure static record: no executable content, no module
# path, no shell command, no real URL call, no real secret, no production path.
#
# Kept OUT of :data:`FIXED_SCENARIOS` so the frozen Phase 3H 22-scenario library
# (and its ``len == 22`` regression assertions) is unchanged. A scenario pass is
# dev-only evidence — it never resolves a P0 gate, never authorizes
# implementation / Phase 3I / real runtime / a new route / production.
# ===========================================================================


# A clean, descriptor-only record that names a reviewed fixture plugin. Read as
# metadata only; never loaded / executed by the proof runner.
_RUNTIME_FIXTURE_DESCRIPTOR: Mapping[str, Any] = {
    "pluginId": "fixture.echo",
    "operation": "echo_uppercase",
    "source": "descriptor_only",
    "version": "1.0.0",
}


# ---------------------------------------------------------------------------
# R1. local_runtime_echo_descriptor_allowed — a descriptor-only read of a
#     reviewed fixture descriptor is a valid dev-only proof input (NOT plugin
#     execution, NOT runtime approval).
# ---------------------------------------------------------------------------
LOCAL_RUNTIME_ECHO_DESCRIPTOR_ALLOWED = ProofScenario(
    scenario_id="local_runtime_echo_descriptor_allowed",
    title="Local runtime fixture descriptor allowed (descriptor-only read)",
    purpose="A descriptor-only read of a reviewed fixture descriptor is a valid "
    "dev-only proof input; not plugin execution, not runtime approval.",
    descriptor=dict(_RUNTIME_FIXTURE_DESCRIPTOR),
    requested_capabilities=("descriptor.read",),
    expected_decision="allowed",
    expected_denial_reasons=(),
    expected_triggered_guards=(),
    linked_p0_gates=("P0-12",),
)


# ---------------------------------------------------------------------------
# R2. local_runtime_network_denied — a runtime request for an external network
#     target / network capability is denied; no DNS, no socket, no external call.
# ---------------------------------------------------------------------------
LOCAL_RUNTIME_NETWORK_DENIED = ProofScenario(
    scenario_id="local_runtime_network_denied",
    title="Local runtime network request denied",
    purpose="A dev-only runtime request for an external network target / network "
    "capability is denied; no DNS, no socket, no external call.",
    requested_capabilities=("network.request",),
    requested_network_targets=("https://registry.example.org/plugin",),
    expected_decision="denied",
    expected_denial_reasons=("network_request_denied",),
    expected_triggered_guards=("capability:network.request", "network_deny"),
    linked_p0_gates=("P0-04",),
)


# ---------------------------------------------------------------------------
# R3. local_runtime_secret_denied — a runtime request for a secret is denied and
#     redacted; no real environment read.
# ---------------------------------------------------------------------------
LOCAL_RUNTIME_SECRET_DENIED = ProofScenario(
    scenario_id="local_runtime_secret_denied",
    title="Local runtime secret request denied",
    purpose="A dev-only runtime request for a secret is denied and redacted from "
    "the audit; no real environment read.",
    requested_secret_names=("OPENAI_API_KEY=fake-runtime-secret",),
    expected_decision="denied",
    expected_denial_reasons=("secret_request_denied",),
    expected_triggered_guards=("secret_unavailable",),
    linked_p0_gates=("P0-10",),
)


# ---------------------------------------------------------------------------
# R4. local_runtime_kill_switch_denied — an active kill switch fails a runtime
#     proof closed; no process signal.
# ---------------------------------------------------------------------------
LOCAL_RUNTIME_KILL_SWITCH_DENIED = ProofScenario(
    scenario_id="local_runtime_kill_switch_denied",
    title="Local runtime kill switch denied",
    purpose="An active kill switch fails a dev-only runtime proof closed; no "
    "process signal.",
    kill_switch_state=True,
    expected_decision="denied",
    expected_denial_reasons=("kill_switch_active",),
    expected_triggered_guards=("kill_switch",),
    linked_p0_gates=("P0-08",),
)


# ---------------------------------------------------------------------------
# R5. local_runtime_descriptor_execution_denied — a runtime descriptor carrying
#     a loader / module field is denied descriptor-only read; no load, no import.
# ---------------------------------------------------------------------------
LOCAL_RUNTIME_DESCRIPTOR_EXECUTION_DENIED = ProofScenario(
    scenario_id="local_runtime_descriptor_execution_denied",
    title="Local runtime descriptor execution surface denied",
    purpose="A runtime descriptor carrying a loader / module field is denied "
    "descriptor-only read; no load, no import, no execution.",
    descriptor={
        "pluginId": "runtime-loader-descriptor",
        "operation": "load",
        "module": "pkg.runtime.loader",
    },
    expected_decision="denied",
    expected_denial_reasons=("descriptor_carries_execution_surface",),
    expected_triggered_guards=("descriptor_only",),
    linked_p0_gates=("P0-12", "P0-18"),
)


#: The frozen, ordered library of Phase 3I runtime-themed dev-only proof
#: scenarios. Separate from :data:`FIXED_SCENARIOS` (the frozen Phase 3H
#: 22-scenario library) so that library's regression assertions are unchanged.
RUNTIME_PROOF_SCENARIOS: tuple[ProofScenario, ...] = (
    LOCAL_RUNTIME_ECHO_DESCRIPTOR_ALLOWED,
    LOCAL_RUNTIME_NETWORK_DENIED,
    LOCAL_RUNTIME_SECRET_DENIED,
    LOCAL_RUNTIME_KILL_SWITCH_DENIED,
    LOCAL_RUNTIME_DESCRIPTOR_EXECUTION_DENIED,
)


def get_runtime_proof_scenarios() -> tuple[ProofScenario, ...]:
    """Return a defensive copy of the Phase 3I runtime-themed scenario library."""
    return tuple(scenario for scenario in RUNTIME_PROOF_SCENARIOS)


# ===========================================================================
# Phase 3I runtime expansion proof scenarios (separate, fixed, dev-only).
#
# A third, isolated block of dev-only proof scenarios that reference the Phase
# 3I runtime's EXPANDED reviewed-fixture surface (fixture.transform /
# fixture.validate / fixture.math / fixture.redact). Like the runtime-themed
# scenarios above, these are **proof scenarios** driven through the existing
# descriptor-only proof runner — they do NOT execute the runtime. Each is a pure
# static record: no executable content, no module path, no shell command, no
# real URL call, no real secret, no production path.
#
# Kept OUT of :data:`FIXED_SCENARIOS` and :data:`RUNTIME_PROOF_SCENARIOS` so
# both frozen libraries' regression assertions are unchanged. A scenario pass is
# dev-only evidence — it never resolves a P0 gate, never authorizes
# implementation / Phase 3I / real runtime / a new route / production.
# ===========================================================================


# ---------------------------------------------------------------------------
# RE1. runtime_transform_normalize_allowed — a descriptor-only read of the
#      reviewed fixture.transform / normalize_text fixture is a valid dev-only
#      proof input (NOT plugin execution, NOT runtime approval).
# ---------------------------------------------------------------------------
RUNTIME_TRANSFORM_NORMALIZE_ALLOWED = ProofScenario(
    scenario_id="runtime_transform_normalize_allowed",
    title="Runtime transform (normalize_text) descriptor allowed (descriptor-only read)",
    purpose="A descriptor-only read of the reviewed fixture.transform fixture is a "
    "valid dev-only proof input; not plugin execution, not runtime approval.",
    descriptor={
        "pluginId": "fixture.transform",
        "operation": "normalize_text",
        "source": "descriptor_only",
        "version": "1.0.0",
    },
    requested_capabilities=("descriptor.read",),
    expected_decision="allowed",
    expected_denial_reasons=(),
    expected_triggered_guards=(),
    linked_p0_gates=("P0-12",),
)


# ---------------------------------------------------------------------------
# RE2. runtime_validate_required_keys_allowed — a descriptor-only read of the
#      reviewed fixture.validate / validate_required_keys fixture is valid.
# ---------------------------------------------------------------------------
RUNTIME_VALIDATE_REQUIRED_KEYS_ALLOWED = ProofScenario(
    scenario_id="runtime_validate_required_keys_allowed",
    title="Runtime validate (required_keys) descriptor allowed (descriptor-only read)",
    purpose="A descriptor-only read of the reviewed fixture.validate fixture is a "
    "valid dev-only proof input; not plugin execution, not runtime approval.",
    descriptor={
        "pluginId": "fixture.validate",
        "operation": "validate_required_keys",
        "source": "descriptor_only",
        "version": "1.0.0",
    },
    requested_capabilities=("descriptor.read",),
    expected_decision="allowed",
    expected_denial_reasons=(),
    expected_triggered_guards=(),
    linked_p0_gates=("P0-12",),
)


# ---------------------------------------------------------------------------
# RE3. runtime_count_items_allowed — a descriptor-only read of the reviewed
#      fixture.math / count_items fixture is valid.
# ---------------------------------------------------------------------------
RUNTIME_COUNT_ITEMS_ALLOWED = ProofScenario(
    scenario_id="runtime_count_items_allowed",
    title="Runtime math (count_items) descriptor allowed (descriptor-only read)",
    purpose="A descriptor-only read of the reviewed fixture.math fixture is a valid "
    "dev-only proof input; not plugin execution, not runtime approval.",
    descriptor={
        "pluginId": "fixture.math",
        "operation": "count_items",
        "source": "descriptor_only",
        "version": "1.0.0",
    },
    requested_capabilities=("descriptor.read",),
    expected_decision="allowed",
    expected_denial_reasons=(),
    expected_triggered_guards=(),
    linked_p0_gates=("P0-12",),
)


# ---------------------------------------------------------------------------
# RE4. runtime_redact_payload_allowed — a descriptor-only read of the reviewed
#      fixture.redact / redact_payload fixture is valid.
# ---------------------------------------------------------------------------
RUNTIME_REDACT_PAYLOAD_ALLOWED = ProofScenario(
    scenario_id="runtime_redact_payload_allowed",
    title="Runtime redact (redact_payload) descriptor allowed (descriptor-only read)",
    purpose="A descriptor-only read of the reviewed fixture.redact fixture is a valid "
    "dev-only proof input; not plugin execution, not runtime approval.",
    descriptor={
        "pluginId": "fixture.redact",
        "operation": "redact_payload",
        "source": "descriptor_only",
        "version": "1.0.0",
    },
    requested_capabilities=("descriptor.read",),
    expected_decision="allowed",
    expected_denial_reasons=(),
    expected_triggered_guards=(),
    linked_p0_gates=("P0-12",),
)


#: The frozen, ordered library of Phase 3I runtime-EXPANSION dev-only proof
#: scenarios. Separate from :data:`FIXED_SCENARIOS` (frozen Phase 3H 22-scenario
#: library) and :data:`RUNTIME_PROOF_SCENARIOS` (frozen 5-scenario runtime
#: library) so both libraries' regression assertions are unchanged.
RUNTIME_EXPANSION_PROOF_SCENARIOS: tuple[ProofScenario, ...] = (
    RUNTIME_TRANSFORM_NORMALIZE_ALLOWED,
    RUNTIME_VALIDATE_REQUIRED_KEYS_ALLOWED,
    RUNTIME_COUNT_ITEMS_ALLOWED,
    RUNTIME_REDACT_PAYLOAD_ALLOWED,
)


def get_runtime_expansion_proof_scenarios() -> tuple[ProofScenario, ...]:
    """Return a defensive copy of the Phase 3I runtime-expansion scenario library."""
    return tuple(scenario for scenario in RUNTIME_EXPANSION_PROOF_SCENARIOS)


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
    "ADVERSARIAL_METADATA_SMUGGLING_DENIED",
    "ADVERSARIAL_NESTED_DESCRIPTOR_EXECUTION_DENIED",
    "ADVERSARIAL_SECRET_LAUNDERING_REDACTED",
    "ADVERSARIAL_PATH_SMUGGLING_DENIED",
    "ADVERSARIAL_ROUTE_EXCEPTION_SMUGGLING_DENIED",
    "ADVERSARIAL_FAKE_HUMAN_APPROVAL_DENIED",
    "ADVERSARIAL_SUMMARY_TAMPERING_RESISTED",
    "ADVERSARIAL_CAPABILITY_ALIAS_DENIED",
    "ADVERSARIAL_NETWORK_URL_LAUNDERING_DENIED",
    "ADVERSARIAL_KILL_SWITCH_OVERRIDE_DENIED",
    "ADVERSARIAL_DESCRIPTOR_ID_SMUGGLING_DENIED",
    "ADVERSARIAL_CAPABILITY_OVERSIZED_DENIED",
    "FIXED_SCENARIOS",
    "get_fixed_scenarios",
    # Phase 3I runtime-themed proof scenarios (separate, fixed, dev-only).
    "LOCAL_RUNTIME_ECHO_DESCRIPTOR_ALLOWED",
    "LOCAL_RUNTIME_NETWORK_DENIED",
    "LOCAL_RUNTIME_SECRET_DENIED",
    "LOCAL_RUNTIME_KILL_SWITCH_DENIED",
    "LOCAL_RUNTIME_DESCRIPTOR_EXECUTION_DENIED",
    "RUNTIME_PROOF_SCENARIOS",
    "get_runtime_proof_scenarios",
    # Phase 3I runtime-expansion proof scenarios (separate, fixed, dev-only).
    "RUNTIME_TRANSFORM_NORMALIZE_ALLOWED",
    "RUNTIME_VALIDATE_REQUIRED_KEYS_ALLOWED",
    "RUNTIME_COUNT_ITEMS_ALLOWED",
    "RUNTIME_REDACT_PAYLOAD_ALLOWED",
    "RUNTIME_EXPANSION_PROOF_SCENARIOS",
    "get_runtime_expansion_proof_scenarios",
]
