"""Phase 3H Dev-only Sandbox Proof Runner Harness tests.

Drives the dev-only proof runner (:mod:`hermes_cli.dev_web_sandbox_runner`) and
the fixed scenario library (:mod:`hermes_cli.dev_web_sandbox_scenarios`) and
proves the conservative invariants the runner must hold:

  - the scenario model is immutable / defensive-copied, and an unsafe scenario
    id is denied before evaluation;
  - every fixed scenario evaluates to its expected decision / reasons / guards;
  - every result's evidence flags are frozen ``False`` (no route change, no
    production access, no external network, no real secret, no runtime
    execution, no persistent artifact) and the audit is fully redacted;
  - a scenario pass is dev-only evidence — it never resolves a P0 gate
    (``resolved_count`` stays 0) and never authorizes implementation / Phase 3I
    / real runtime / new route / production rollout;
  - fake human-approval / authorization metadata smuggled into a scenario is
    detected and ignored — Implementation Authorization stays NO-GO;
  - the runner modules are pure stdlib with no dynamic loading / network / shell
    / subprocess / file I/O / real secret read, are not imported by the FastAPI
    app, add no route, never touch ``~/.hermes`` or production ``state.db``.

Boundary: this test never touches ``~/.hermes`` (no stat / ls / read / open /
resolve), never opens production ``state.db``, never signals the production
gateway, never starts a gateway / dashboard, never networks, never reads a real
secret, and introduces no new route. Every secret value is an obvious fake;
every path is a fake / temp / string-policy target.

Phase: 3H — Dev-only Sandbox Proof Runner Harness
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli import dev_web_sandbox_runner as runner_mod
from hermes_cli import dev_web_sandbox_scenarios as scenarios_mod
from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_p0_evidence import (
    GATE_STATUS_CANDIDATE_FOR_REVIEW,
    GATE_STATUS_NO_EVIDENCE,
    GATE_STATUS_RESOLVED,
)
from hermes_cli.dev_web_safety_baseline import (
    ROUTE_GOVERNANCE_EXPECTED,
    assert_route_governance_unchanged,
    route_governance_counts,
)
from hermes_cli.dev_web_sandbox_runner import (
    NEW_ROUTE_FLAGS,
    ProofRunSummary,
    ProofScenario,
    ProofScenarioResult,
    assert_no_side_effect_surface,
    is_scenario_id_safe,
    run_proof_scenario,
    run_proof_scenarios,
)
from hermes_cli.dev_web_sandbox_scenarios import (
    DESCRIPTOR_ONLY_SAFE_READ,
    EVIDENCE_CANDIDATE_BUT_NOT_RESOLVED,
    EXECUTABLE_DESCRIPTOR_DENIED,
    FILESYSTEM_FORBIDDEN_PATHS_DENIED,
    FIXED_SCENARIOS,
    KILL_SWITCH_ACTIVE_FAIL_CLOSED,
    NETWORK_REQUEST_DENIED,
    P0_HUMAN_REVIEW_REQUIRED,
    PRODUCTION_ACCESS_ATTEMPT_DENIED,
    ROUTE_CHANGE_ATTEMPT_DENIED,
    SECRET_REQUEST_REDACTED_AND_DENIED,
    get_fixed_scenarios,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

FAKE_SK = "sk-abcd1234efgh5678notreal"
FAKE_PROD_PATH = "/Users/huangruibang/.hermes/state.db"


@pytest.fixture()
def app(tmp_path: Path):
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return create_dev_web_api_app(cfg)


def _src(module) -> str:
    return Path(inspect.getsourcefile(module)).read_text(encoding="utf-8")


def _safe_summary() -> ProofRunSummary:
    return run_proof_scenarios(get_fixed_scenarios())


# ===========================================================================
# 1. Scenario model safety
# ===========================================================================


class TestScenarioModelSafety:
    def test_no_side_effect_surface(self) -> None:
        assert_no_side_effect_surface()  # must not raise

    def test_scenario_id_safe_helper(self) -> None:
        assert is_scenario_id_safe("descriptor_only_safe_read") is True
        assert is_scenario_id_safe("a-b_c.d") is True

    @pytest.mark.parametrize(
        "bad_id",
        [
            "",
            "has space",
            "has/slash",
            "has..traversal",
            "has;shell",
            "has|pipe",
            "rel/../../etc",
            123,
            None,
            "unicode-é",
        ],
    )
    def test_unsafe_scenario_id_is_not_safe(self, bad_id) -> None:
        assert is_scenario_id_safe(bad_id) is False

    def test_unsafe_scenario_id_denied(self) -> None:
        scenario = ProofScenario(
            scenario_id="bad/../id",
            expected_decision="allowed",
        )
        result = run_proof_scenario(scenario)
        assert result.passed is False
        assert result.decision == "denied"
        assert result.persistent_artifacts_created is False
        # The unsafe id itself must not be echoed verbatim into the audit.
        blob = json.dumps(result.to_safe_dict(), default=str)
        assert "bad/../id" not in blob

    def test_scenario_is_frozen(self) -> None:
        scenario = ProofScenario(scenario_id="freeze-test")
        with pytest.raises(Exception):
            scenario.scenario_id = "mutated"  # type: ignore[misc]

    def test_descriptor_metadata_defensive_copied(self) -> None:
        original = {"pluginId": "copied-descriptor", "v": 1}
        scenario = ProofScenario(scenario_id="copy-test", descriptor=original)
        original["v"] = 999  # mutate the caller's dict
        original["injected"] = True
        assert scenario.descriptor == {"pluginId": "copied-descriptor", "v": 1}

    def test_scenario_metadata_defensive_copied(self) -> None:
        original = {"approved": True}
        scenario = ProofScenario(scenario_id="copy-meta-test", metadata=original)
        original["approved"] = False
        original["extra"] = "x"
        assert scenario.metadata == {"approved": True}

    def test_metadata_cannot_authorize_implementation(self) -> None:
        scenario = ProofScenario(
            scenario_id="authz-bypass",
            descriptor={"pluginId": "authz-bypass"},
            requested_capabilities=("descriptor.read",),
            metadata={
                "approved": True,
                "implementation_authorization": "GO",
                "human_signoff": "accepted",
            },
        )
        result = run_proof_scenario(scenario)
        summary = run_proof_scenarios([scenario])
        assert summary.implementation_authorization == "NO-GO"
        # The audit records the bypass keys were detected + ignored, and the
        # verdict stays NO-GO.
        verdict = result.redacted_audit.get("verdict", {})
        assert verdict["implementationGate"] == "NO-GO"
        assert "approved" in verdict["bypassKeysIgnored"]
        assert "implementation_authorization" in verdict["bypassKeysIgnored"]

    def test_metadata_cannot_authorize_phase_3i(self) -> None:
        scenario = ProofScenario(
            scenario_id="phase3i-bypass",
            metadata={"phase_3i_authorized": True},
        )
        summary = run_proof_scenarios([scenario])
        assert summary.phase_3i_authorization is False

    def test_metadata_cannot_authorize_production_or_route(self) -> None:
        scenario = ProofScenario(
            scenario_id="prod-route-bypass",
            metadata={
                "production_approved": True,
                "route_exception_approved": True,
                "real_runtime_authorized": True,
            },
        )
        summary = run_proof_scenarios([scenario])
        assert summary.implementation_authorization == "NO-GO"
        assert summary.phase_3i_authorization is False
        assert summary.real_runtime_authorization == "NO-GO"
        assert summary.new_route == "NO-GO"
        assert summary.production_rollout == "NO-GO"

    def test_fake_secrets_redacted_from_scenario_output(self) -> None:
        scenario = ProofScenario(
            scenario_id="secret-redact",
            requested_secret_names=(FAKE_SK, "Authorization: Bearer fake-token"),
        )
        result = run_proof_scenario(scenario)
        blob = json.dumps(result.to_safe_dict(), default=str)
        assert FAKE_SK not in blob
        assert "Bearer fake-token" not in blob


# ===========================================================================
# 2. Fixed scenario library
# ===========================================================================


class TestFixedScenarioLibrary:
    def test_library_has_expected_scenario_count(self) -> None:
        # 10 baseline scenarios + 12 Phase 3H adversarial-hardening scenarios.
        assert len(FIXED_SCENARIOS) == 22

    def test_all_scenario_ids_safe_and_unique(self) -> None:
        ids = [s.scenario_id for s in FIXED_SCENARIOS]
        assert all(is_scenario_id_safe(sid) for sid in ids)
        assert len(set(ids)) == len(ids)

    def test_get_fixed_scenarios_returns_defensive_copy(self) -> None:
        first = get_fixed_scenarios()
        second = get_fixed_scenarios()
        assert first == second
        assert first is not FIXED_SCENARIOS  # fresh container
        # Library contents are immutable regardless.
        assert len(FIXED_SCENARIOS) == 22

    def test_no_scenario_carries_real_secret_or_production_path(self) -> None:
        for scenario in FIXED_SCENARIOS:
            blob = json.dumps(scenario.to_safe_dict(), default=str)
            assert FAKE_SK not in blob
            assert "/Users/huangruibang/.hermes" not in blob
            assert "state.db" not in blob


# ===========================================================================
# 3. Single scenario runner — each fixed scenario
# ===========================================================================

_FIXED_SCENARIO_IDS = [s.scenario_id for s in FIXED_SCENARIOS]


@pytest.mark.parametrize("scenario", list(FIXED_SCENARIOS), ids=_FIXED_SCENARIO_IDS)
def test_fixed_scenario_evaluates_as_expected(scenario: ProofScenario) -> None:
    result = run_proof_scenario(scenario)
    assert result.scenario_id == scenario.scenario_id
    assert result.passed is True, (
        f"{scenario.scenario_id} expected {scenario.expected_decision}, "
        f"got decision={result.decision} reasons={result.denial_reasons} "
        f"guards={result.triggered_guards}"
    )
    assert result.decision == scenario.expected_decision
    # Every evidence flag is frozen False.
    assert result.route_change_required is False
    assert result.production_access_required is False
    assert result.external_network_required is False
    assert result.real_secret_required is False
    assert result.runtime_execution_required is False
    assert result.persistent_artifacts_created is False
    assert result.errors == ()
    assert result.linked_p0_gates == scenario.linked_p0_gates


class TestSingleScenarioRunner:
    def test_descriptor_only_safe_read_allowed(self) -> None:
        result = run_proof_scenario(DESCRIPTOR_ONLY_SAFE_READ)
        assert result.decision == "allowed"
        assert result.passed is True
        assert result.runtime_execution_required is False

    def test_executable_descriptor_denied(self) -> None:
        result = run_proof_scenario(EXECUTABLE_DESCRIPTOR_DENIED)
        assert result.decision == "denied"
        assert "descriptor_carries_execution_surface" in result.denial_reasons
        assert "descriptor_only" in result.triggered_guards

    def test_network_request_denied(self) -> None:
        result = run_proof_scenario(NETWORK_REQUEST_DENIED)
        assert result.decision == "denied"
        assert "network_request_denied" in result.denial_reasons
        assert result.external_network_required is False

    def test_secret_request_redacted_and_denied(self) -> None:
        result = run_proof_scenario(SECRET_REQUEST_REDACTED_AND_DENIED)
        assert result.decision == "denied"
        assert "secret_request_denied" in result.denial_reasons
        assert "secret_unavailable" in result.triggered_guards
        assert result.real_secret_required is False
        blob = json.dumps(result.to_safe_dict(), default=str)
        assert "sk-fake-value-not-real" not in blob

    def test_filesystem_forbidden_paths_denied(self) -> None:
        result = run_proof_scenario(FILESYSTEM_FORBIDDEN_PATHS_DENIED)
        assert result.decision == "denied"
        assert "forbidden_production_home" in result.denial_reasons
        assert "forbidden_production_database" in result.denial_reasons
        assert "filesystem_boundary" in result.triggered_guards
        assert result.production_access_required is False
        blob = json.dumps(result.to_safe_dict(), default=str)
        assert "/Users/huangruibang/.hermes" not in blob
        assert "~/.hermes" not in blob
        assert "state.db" not in blob

    def test_kill_switch_active_fail_closed(self) -> None:
        result = run_proof_scenario(KILL_SWITCH_ACTIVE_FAIL_CLOSED)
        assert result.decision == "denied"
        assert "kill_switch_active" in result.denial_reasons
        assert "kill_switch" in result.triggered_guards

    def test_route_change_attempt_denied(self) -> None:
        result = run_proof_scenario(ROUTE_CHANGE_ATTEMPT_DENIED)
        assert result.decision == "denied"
        assert "routes_modify_denied" in result.denial_reasons
        assert result.route_change_required is False
        # The route-exception metadata was detected but never approved.
        verdict = json.dumps(result.redacted_audit.get("verdict", {}), default=str)
        assert '"routeExceptionRequired": true' in verdict
        assert '"routeExceptionApproved": false' in verdict

    def test_production_access_attempt_denied(self) -> None:
        result = run_proof_scenario(PRODUCTION_ACCESS_ATTEMPT_DENIED)
        assert result.decision == "denied"
        assert "production_access_denied" in result.denial_reasons
        assert result.production_access_required is False

    def test_p0_human_review_required_ignored(self) -> None:
        result = run_proof_scenario(P0_HUMAN_REVIEW_REQUIRED)
        assert result.decision == "allowed"
        # Authorization stays NO-GO even though the proof-level read was allowed.
        # The verdict projection uses redaction-safe keys (the word "authorization"
        # contains "auth", which the redactor would otherwise collapse).
        verdict = json.dumps(result.redacted_audit.get("verdict", {}), default=str)
        assert '"implementationGate": "NO-GO"' in verdict
        assert '"phase3iGate": false' in verdict

    def test_evidence_candidate_but_not_resolved(self) -> None:
        result = run_proof_scenario(EVIDENCE_CANDIDATE_BUT_NOT_RESOLVED)
        assert result.decision == "allowed"
        assert result.evidence_classification == GATE_STATUS_CANDIDATE_FOR_REVIEW
        assert result.evidence_classification != GATE_STATUS_RESOLVED


# ===========================================================================
# 4. Multi scenario runner
# ===========================================================================


class TestMultiScenarioRunner:
    def test_runs_all_fixed_scenarios(self) -> None:
        summary = _safe_summary()
        assert summary.total_scenarios == 22
        assert summary.passed_scenarios == 22
        assert summary.failed_scenarios == 0

    def test_summary_has_linked_p0_gates(self) -> None:
        summary = _safe_summary()
        assert "P0-12" in summary.linked_p0_gates
        assert "P0-24" in summary.linked_p0_gates
        assert summary.linked_p0_gates == tuple(sorted(summary.linked_p0_gates))

    def test_failed_scenario_summary_fail_closed(self) -> None:
        bad = ProofScenario(scenario_id="bad/../id")
        summary = run_proof_scenarios([bad])
        assert summary.total_scenarios == 1
        assert summary.failed_scenarios == 1
        assert summary.passed_scenarios == 0
        # Failure does not escalate anything.
        assert summary.implementation_authorization == "NO-GO"

    def test_non_scenario_input_fail_closed(self) -> None:
        summary = run_proof_scenarios(["not-a-scenario", 42])  # type: ignore[list-item]
        assert summary.total_scenarios == 2
        assert summary.failed_scenarios == 2

    def test_non_iterable_input_is_empty_summary(self) -> None:
        summary = run_proof_scenarios(None)  # type: ignore[arg-type]
        assert summary.total_scenarios == 0
        assert summary.passed_scenarios == 0
        assert summary.implementation_authorization == "NO-GO"

    def test_errors_redacted_in_fail_closed_result(self) -> None:
        bad = ProofScenario(scenario_id="bad/../id")
        result = run_proof_scenario(bad)
        for err in result.errors:
            assert "bad/../id" not in err

    def test_no_persistent_artifacts(self, tmp_path: Path) -> None:
        from hermes_cli.dev_web_safety_baseline import find_runtime_store_artifacts

        _safe_summary()
        # The runner writes nothing to disk; a temp dir stays empty of artifacts.
        assert find_runtime_store_artifacts(tmp_path) == []

    def test_summary_evidence_flags_all_false(self) -> None:
        summary = _safe_summary()
        for record in summary.redacted_audit_records:
            evidence = record.get("evidence", {})
            assert all(v is False for v in evidence.values())

    def test_summary_redacts_secrets_and_production_paths(self) -> None:
        summary = _safe_summary()
        blob = json.dumps(summary.to_safe_dict(), default=str)
        assert FAKE_SK not in blob
        assert "/Users/huangruibang/.hermes" not in blob
        assert "state.db" not in blob

    def test_summary_defensive_copies_audit_records(self) -> None:
        # The summary deep-copies the audit records it receives, so mutating the
        # builder's dict after construction cannot leak into the summary.
        record = {"decision": "denied", "nested": {"k": "v"}}
        summary = ProofRunSummary(
            run_id="t",
            total_scenarios=1,
            passed_scenarios=0,
            failed_scenarios=1,
            redacted_audit_records=(record,),
        )
        record["injected"] = True
        record["nested"]["k"] = "mutated"
        stored = summary.redacted_audit_records[0]
        assert "injected" not in stored
        assert stored["nested"]["k"] == "v"

    def test_run_id_passthrough(self) -> None:
        summary = run_proof_scenarios(get_fixed_scenarios(), run_id="custom-run-id")
        assert summary.run_id == "custom-run-id"


# ===========================================================================
# 5. P0 integration — no authorization escalation
# ===========================================================================


class TestP0Integration:
    def test_p0_summary_resolved_count_is_zero(self) -> None:
        summary = _safe_summary()
        assert summary.p0_evidence_summary["resolvedCount"] == 0
        assert summary.p0_evidence_summary["totalGates"] == 24

    def test_passing_scenarios_do_not_resolve_p0(self) -> None:
        # Even a fully-passing run resolves no gate.
        summary = _safe_summary()
        assert summary.passed_scenarios == 22
        assert summary.p0_evidence_summary["resolvedCount"] == 0

    def test_candidate_evidence_is_not_resolved(self) -> None:
        result = run_proof_scenario(EVIDENCE_CANDIDATE_BUT_NOT_RESOLVED)
        assert result.evidence_classification == GATE_STATUS_CANDIDATE_FOR_REVIEW
        summary = _safe_summary()
        assert summary.p0_evidence_summary["resolvedCount"] == 0
        # candidate_for_review count may be > 0, but resolved stays 0.
        assert summary.p0_evidence_summary["resolvedCount"] == 0

    def test_implementation_authorization_stays_no_go(self) -> None:
        summary = _safe_summary()
        assert summary.implementation_authorization == "NO-GO"

    def test_phase_3i_stays_not_authorized(self) -> None:
        summary = _safe_summary()
        assert summary.phase_3i_authorization is False

    def test_real_runtime_stays_no_go(self) -> None:
        summary = _safe_summary()
        assert summary.real_runtime_authorization == "NO-GO"

    def test_new_route_stays_no_go(self) -> None:
        summary = _safe_summary()
        assert summary.new_route == "NO-GO"
        assert summary.production_rollout == "NO-GO"

    def test_fake_human_approval_cannot_override_authorization(self) -> None:
        scenario = ProofScenario(
            scenario_id="fake-signoff",
            metadata={
                "approved": True,
                "human_signoff": "accepted",
                "implementation_authorization": "GO",
                "phase_3i_authorized": True,
                "reviewer": "project owner",
                "signoff": True,
            },
        )
        summary = run_proof_scenarios([scenario])
        assert summary.implementation_authorization == "NO-GO"
        assert summary.phase_3i_authorization is False
        assert summary.p0_evidence_summary["resolvedCount"] == 0

    def test_linking_gate_does_not_resolve_it(self) -> None:
        # A scenario may link many gates; linking is traceability, not resolution.
        scenario = ProofScenario(
            scenario_id="linked-gates",
            descriptor={"pluginId": "linked"},
            requested_capabilities=("descriptor.read",),
            linked_p0_gates=("P0-01", "P0-02", "P0-15", "P0-22"),
        )
        summary = run_proof_scenarios([scenario])
        assert set(scenario.linked_p0_gates).issubset(set(summary.linked_p0_gates))
        assert summary.p0_evidence_summary["resolvedCount"] == 0


# ===========================================================================
# 6. Source boundary + dev-web API isolation
# ===========================================================================

_STRICT_FORBIDDEN_TOKENS = (
    "import importlib",
    "importlib.import_module",
    "__import__(",
    "eval(",
    "exec(",
    "os.system",
    "shell=True",
    "import subprocess",
    "subprocess.run",
    "subprocess.Popen",
    "import requests",
    "import httpx",
    "import aiohttp",
    "socket.socket",
    "urllib.request",
    "os.kill",
    "signal.signal",
)

_FILE_IO_TOKENS = (
    "open(",
    "Path(",
    "os.stat",
    "os.listdir",
    "os.walk",
    "os.read",
    ".read_text(",
    ".write(",
    ".write_text(",
)


def test_runner_source_has_no_forbidden_surface() -> None:
    src = _src(runner_mod)
    for token in _STRICT_FORBIDDEN_TOKENS:
        assert token not in src, f"dev_web_sandbox_runner: forbidden token {token!r}"


def test_scenarios_source_has_no_forbidden_surface() -> None:
    src = _src(scenarios_mod)
    for token in _STRICT_FORBIDDEN_TOKENS:
        assert token not in src, f"dev_web_sandbox_scenarios: forbidden token {token!r}"


def test_runner_source_does_no_file_io() -> None:
    src = _src(runner_mod)
    for token in _FILE_IO_TOKENS:
        assert token not in src, f"dev_web_sandbox_runner: file-IO token {token!r}"


def test_scenarios_source_does_no_file_io() -> None:
    src = _src(scenarios_mod)
    for token in _FILE_IO_TOKENS:
        assert token not in src, f"dev_web_sandbox_scenarios: file-IO token {token!r}"


def test_runner_references_production_only_as_denial_target() -> None:
    src = _src(runner_mod)
    for forbidden in ("open('/Users", "read_text('/Users", "stat('/Users", "expanduser('~/.hermes"):
        assert forbidden not in src


def test_runner_not_imported_by_dev_web_api() -> None:
    api_src = (REPO_ROOT / "hermes_cli" / "dev_web_api.py").read_text(encoding="utf-8")
    assert "dev_web_sandbox_runner" not in api_src
    assert "dev_web_sandbox_scenarios" not in api_src


def test_runner_not_wired_into_fastapi_app(app) -> None:
    api_src = (REPO_ROOT / "hermes_cli" / "dev_web_api.py").read_text(encoding="utf-8")
    for mod in ("dev_web_sandbox_runner", "dev_web_sandbox_scenarios"):
        assert mod not in api_src, f"dev_web_api.py references {mod}"


def test_no_dev_web_module_outside_family_imports_runner() -> None:
    family = {
        "dev_web_sandbox_runner",
        "dev_web_sandbox_scenarios",
        "dev_web_sandbox_proof",
        "dev_web_sandbox_guards",
        "dev_web_sandbox_policy",
        "dev_web_sandbox_audit",
        "dev_web_safety_baseline",
        "dev_web_p0_evidence",
    }
    candidates = sorted((REPO_ROOT / "hermes_cli").glob("dev_web_*.py"))
    for path in candidates:
        if path.stem in family:
            continue
        src = path.read_text(encoding="utf-8")
        assert "dev_web_sandbox_runner" not in src, f"{path.name} imports dev_web_sandbox_runner"
        assert "dev_web_sandbox_scenarios" not in src, f"{path.name} imports dev_web_sandbox_scenarios"


# ===========================================================================
# 7. Route governance unchanged
# ===========================================================================


class TestRouteGovernanceUnchanged:
    def test_counts_match_frozen_baseline(self, app) -> None:
        counts = route_governance_counts(app)
        assert counts == {
            "openApiPaths": 34,
            "runtimeRoutes": 34,
            "toolGetRoutes": 5,
            "toolWriteRoutes": 0,
            "toolDryRunRoutes": 1,
            "toolExecutionRoutes": 1,
        }

    def test_assert_unchanged(self, app) -> None:
        counts = assert_route_governance_unchanged(app)
        assert counts["openApiPaths"] == 34

    def test_new_route_flags_all_zero(self) -> None:
        assert all(v == 0 for v in NEW_ROUTE_FLAGS.values())

    def test_summary_route_governance_unchanged(self) -> None:
        summary = _safe_summary()
        assert summary.route_governance_summary["baseline"] == ROUTE_GOVERNANCE_EXPECTED
        assert summary.route_governance_summary["routeChangeRequired"] is False
        assert all(v == 0 for v in summary.route_governance_summary["newRouteFlags"].values())

    def test_no_runner_route_exposed(self, app) -> None:
        client = TestClient(app)
        # No sandbox / runner / scenario route exists.
        for path in ("/api/dev/v1/sandbox/proof/run", "/api/dev/v1/proof-runner", "/api/dev/v1/scenarios"):
            response = client.get(path)
            assert response.status_code == 404, f"{path} should not exist"


# ===========================================================================
# 8. Production safety — no ~/.hermes access (including metadata)
# ===========================================================================


class TestProductionSafety:
    def test_production_home_constant_not_resolved_in_runner_chain(self) -> None:
        # The runner imports safety_baseline; PRODUCTION_HERMES_HOME must not be
        # .resolve()'d (which would stat the forbidden directory at import time).
        from hermes_cli import dev_web_safety_baseline as baseline

        src = _src(baseline)
        assert 'PRODUCTION_HERMES_HOME: Path = Path("/Users/huangruibang/.hermes").resolve()' not in src
        assert str(baseline.PRODUCTION_HERMES_HOME) == "/Users/huangruibang/.hermes"

    def test_importing_runner_does_not_touch_production_home(self) -> None:
        # Functional guard: reloading the runner (and its import chain) must
        # issue no stat / lstat / realpath against the production directory.
        import importlib
        import os
        import posixpath

        touched: list[str] = []
        real_lstat, real_stat, real_realpath = os.lstat, os.stat, posixpath.realpath
        os.lstat = lambda p, *a, **k: (touched.append(str(p)), real_lstat(p, *a, **k))[1]
        os.stat = lambda p, *a, **k: (touched.append(str(p)), real_stat(p, *a, **k))[1]
        posixpath.realpath = lambda p, *a, **k: (touched.append(str(p)), real_realpath(p, *a, **k))[1]
        os.path.realpath = posixpath.realpath
        try:
            importlib.reload(runner_mod)
            importlib.reload(scenarios_mod)
        finally:
            os.lstat = real_lstat
            os.stat = real_stat
            posixpath.realpath = real_realpath
            os.path.realpath = real_realpath
        prod_touches = [p for p in touched if "/Users/huangruibang/.hermes" in p]
        assert prod_touches == [], f"production home touched on import: {prod_touches}"

    def test_running_scenarios_does_not_touch_production_home(self) -> None:
        # Running the full library must issue no stat / lstat / realpath against
        # the production directory (every path is a fake / string-policy target).
        import os
        import posixpath

        touched: list[str] = []
        real_lstat, real_stat, real_realpath = os.lstat, os.stat, posixpath.realpath
        os.lstat = lambda p, *a, **k: (touched.append(str(p)), real_lstat(p, *a, **k))[1]
        os.stat = lambda p, *a, **k: (touched.append(str(p)), real_stat(p, *a, **k))[1]
        posixpath.realpath = lambda p, *a, **k: (touched.append(str(p)), real_realpath(p, *a, **k))[1]
        os.path.realpath = posixpath.realpath
        try:
            _safe_summary()
        finally:
            os.lstat = real_lstat
            os.stat = real_stat
            posixpath.realpath = real_realpath
            os.path.realpath = real_realpath
        prod_touches = [p for p in touched if "/Users/huangruibang/.hermes" in p]
        assert prod_touches == [], f"production home touched during run: {prod_touches}"

    def test_production_safety_summary_all_false(self) -> None:
        summary = _safe_summary()
        safety = summary.production_safety_summary
        assert safety["productionAccessRequired"] is False
        assert safety["realSecretRequired"] is False
        assert safety["externalNetworkRequired"] is False
        assert safety["runtimeExecutionRequired"] is False
        assert safety["persistentArtifactsCreated"] is False
        assert safety["productionHomeAccessed"] is False
        assert safety["productionStateDbAccessed"] is False


# ===========================================================================
# 9. Result model invariants
# ===========================================================================


class TestResultModelInvariants:
    def test_result_evidence_flag_must_be_false(self) -> None:
        # A result constructed with a True evidence flag is rejected.
        with pytest.raises(AssertionError):
            ProofScenarioResult(
                scenario_id="x",
                passed=False,
                decision="denied",
                runtime_execution_required=True,
            )

    def test_result_redacted_audit_defensive_copied(self) -> None:
        # The result deep-copies the audit dict it is built from, so mutating the
        # builder's dict after construction cannot leak into the result.
        builder_audit = {"decision": "denied", "nested": {"k": "v"}}
        result = ProofScenarioResult(
            scenario_id="copy-test",
            passed=False,
            decision="denied",
            redacted_audit=builder_audit,
        )
        builder_audit["injected"] = True
        builder_audit["nested"]["k"] = "mutated"
        assert "injected" not in result.redacted_audit
        assert result.redacted_audit["nested"]["k"] == "v"

    def test_result_to_safe_dict_redacts(self) -> None:
        result = run_proof_scenario(SECRET_REQUEST_REDACTED_AND_DENIED)
        blob = json.dumps(result.to_safe_dict(), default=str)
        assert "sk-fake-value-not-real" not in blob
        assert "Bearer fake-token" not in blob
        assert result.to_safe_dict()["redactionApplied"] is True
