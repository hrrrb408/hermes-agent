"""Phase 3E–3H Remaining P0 Gate Reduction tests.

Drives the fail-closed P0 evidence aggregator
(:mod:`hermes_cli.dev_web_p0_evidence`) and proves the conservative invariants
that the remaining 9 governance-only gates (P0-05 / 15 / 16 / 17 / 18 / 19 /
21 / 22 / 23) require:

  - the 24-gate registry is intact and ``resolved_count`` is **always 0**;
  - no request metadata, reviewer-like string, route-exception flag, production
    flag, or real-runtime flag can flip Implementation Authorization to GO or
    authorize Phase 3I;
  - a human approval cannot be faked — not via :func:`create_human_approval`
    with a smuggled token, and not by constructing
    :class:`HumanApprovalRecord` directly;
  - supply-chain provenance denies every untrusted source and trusts nothing
    for execution;
  - a route-governance exception is detected but never auto-approved;
  - rollback / incident readiness is partial at best, rejects production paths,
    and rejects a fake owner;
  - evidence without a test command is partial, evidence with one is
    candidate-for-review, and nothing resolves without human approval;
  - evidence summaries redact secrets and production paths;
  - the new module is pure stdlib with no dynamic loading / network / shell /
    file I/O, and is not imported by the FastAPI app;
  - route governance stays ``34/34/5/0/1/1`` and no new route appears.

Boundary: this test never touches ``~/.hermes`` (no stat / ls / read / open /
resolve), never opens production ``state.db``, never signals the production
gateway, never starts a gateway / dashboard, never networks, never reads a real
secret, and introduces no new route. Every secret value is an obvious fake;
every path is a fake / temp / string-policy target.

Phase: 3E–3H — Remaining P0 Gate Reduction
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli import dev_web_p0_evidence as p0_mod
from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_p0_evidence import (
    ALL_GATE_STATUSES,
    ALLOWED_SOURCE_TYPES,
    GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW,
    GATE_STATUS_CANDIDATE_FOR_REVIEW,
    GATE_STATUS_PARTIAL_EVIDENCE,
    GATE_STATUS_RESOLVED,
    GATES,
    HumanApprovalRecord,
    PROVENANCE_REASONS,
    REMAINING_GATE_IDS,
    RouteExceptionDecision,
    assert_no_side_effect_surface,
    classify_evidence_quality,
    classify_plugin_source,
    create_human_approval,
    detect_untrusted_metadata,
    evaluate_authorization_request,
    evaluate_p0_evidence,
    evaluate_provenance_integrity,
    evaluate_rollback_readiness,
    evaluate_route_exception,
    is_approval_valid,
)
from hermes_cli.dev_web_safety_baseline import (
    ROUTE_GOVERNANCE_EXPECTED,
    assert_route_governance_unchanged,
    route_governance_counts,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

FAKE_SK = "sk-abcd1234efgh5678"
FAKE_PROD_PATH = "/Users/huangruibang/.hermes/state.db"


@pytest.fixture()
def app(tmp_path: Path):
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return create_dev_web_api_app(cfg)


def _src(module) -> str:
    return Path(inspect.getsourcefile(module)).read_text(encoding="utf-8")


# ===========================================================================
# 1. P0 aggregator / evidence classification
# ===========================================================================


class TestP0Aggregator:
    def test_no_side_effect_surface(self) -> None:
        assert_no_side_effect_surface()  # must not raise

    def test_registry_has_exactly_24_unique_gates(self) -> None:
        ids = [g.gate_id for g in GATES]
        assert len(GATES) == 24
        assert len(set(ids)) == 24
        for i in range(1, 25):
            assert f"P0-{i:02d}" in ids

    def test_all_classifications_are_valid_statuses(self) -> None:
        for gate in GATES:
            assert gate.classification in ALL_GATE_STATUSES

    def test_no_gate_starts_resolved(self) -> None:
        assert all(not g.is_resolved() for g in GATES)

    def test_summary_counts(self) -> None:
        summary = evaluate_p0_evidence()
        assert summary.total_gates == 24
        assert summary.resolved_count == 0
        assert summary.unresolved_count == 24
        # 4 of the remaining 9 advanced to partial evidence (P0-05/17/21/23);
        # 5 stay blocked by human review (P0-15/16/18/19/22).
        assert summary.partial_evidence_count == 19
        assert summary.blocked_by_human_review_count == 5
        assert summary.governance_only_count == 0
        assert summary.no_evidence_count == 0
        assert summary.candidate_for_review_count == 0

    def test_remaining_9_all_represented_and_unresolved(self) -> None:
        summary = evaluate_p0_evidence()
        by_id = {g.gate_id: g for g in summary.gates}
        for gate_id in REMAINING_GATE_IDS:
            assert gate_id in by_id
            assert by_id[gate_id].classification != GATE_STATUS_RESOLVED
            assert by_id[gate_id].requires_human_approval is True

    def test_remaining_9_classification_split(self) -> None:
        summary = evaluate_p0_evidence()
        by_id = {g.gate_id: g for g in summary.gates}
        partial = {gid for gid in REMAINING_GATE_IDS if by_id[gid].classification == GATE_STATUS_PARTIAL_EVIDENCE}
        blocked = {gid for gid in REMAINING_GATE_IDS if by_id[gid].classification == GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW}
        assert partial == {"P0-05", "P0-17", "P0-21", "P0-23"}
        assert blocked == {"P0-15", "P0-16", "P0-18", "P0-19", "P0-22"}

    def test_summary_preserves_no_go_flags(self) -> None:
        summary = evaluate_p0_evidence()
        assert summary.implementation_authorization == "NO-GO"
        assert summary.phase_3i_authorized is False
        assert summary.real_runtime == "NO-GO"
        assert summary.new_route == "NO-GO"
        assert summary.production_rollout == "NO-GO"

    def test_candidate_for_review_is_not_resolved(self) -> None:
        # Even a candidate-for-review gate (none assigned today, but the
        # taxonomy allows it) must not be resolved.
        from hermes_cli.dev_web_p0_evidence import P0GateEvidence

        gate = P0GateEvidence(
            gate_id="P0-TEST",
            theme="test",
            classification=GATE_STATUS_CANDIDATE_FOR_REVIEW,
            requires_human_approval=True,
            reviewer="security reviewer",
            resolution_requirement="approval",
        )
        assert gate.is_resolved() is False

    def test_gate_to_safe_dict_redacts(self) -> None:
        from hermes_cli.dev_web_p0_evidence import P0GateEvidence

        gate = P0GateEvidence(
            gate_id="P0-TEST",
            theme="test",
            classification=GATE_STATUS_PARTIAL_EVIDENCE,
            requires_human_approval=True,
            reviewer="security reviewer",
            resolution_requirement="approval",
            remaining_gap=f"token {FAKE_SK} at {FAKE_PROD_PATH}",
        )
        blob = json.dumps(gate.to_safe_dict())
        assert FAKE_SK not in blob
        assert "/Users/huangruibang/.hermes" not in blob
        assert "state.db" not in blob


# ===========================================================================
# 2. Authorization bypass attempts
# ===========================================================================


class TestAuthorizationBypass:
    @pytest.mark.parametrize(
        "metadata",
        [
            {"approved": True},
            {"reviewer": "owner"},
            {"human_signoff": "accepted"},
            {"implementation_authorization": "GO"},
            {"phase_3i_authorized": True},
            {"route_exception_approved": True},
            {"production_approved": True},
            {"real_runtime_authorized": True},
            {"signoff": "signed"},
            {"authorized": True},
            # Combined kitchen-sink attempt
            {
                "approved": True,
                "reviewer": "project-owner",
                "human_signoff": "accepted",
                "implementation_authorization": "GO",
                "phase_3i_authorized": "true",
                "route_exception_approved": True,
                "production_approved": True,
                "real_runtime_authorized": True,
            },
        ],
    )
    def test_metadata_cannot_authorize(self, metadata: dict) -> None:
        summary = evaluate_p0_evidence(untrusted_metadata=metadata)
        assert summary.resolved_count == 0
        assert summary.implementation_authorization == "NO-GO"
        assert summary.phase_3i_authorized is False
        assert summary.real_runtime == "NO-GO"
        assert summary.new_route == "NO-GO"
        assert summary.production_rollout == "NO-GO"

    def test_authorization_decision_ignores_metadata(self) -> None:
        decision = evaluate_authorization_request(
            {"implementation_authorization": "GO", "phase_3i_authorized": True, "approved": True}
        )
        assert decision.implementation_authorization == "NO-GO"
        assert decision.phase_3i_authorized is False
        assert "implementation_authorization" in decision.ignored_metadata_keys
        assert "phase_3i_authorized" in decision.ignored_metadata_keys
        assert "approved" in decision.ignored_metadata_keys
        assert "untrusted_metadata_ignored" in decision.reasons

    def test_authorization_decision_no_metadata(self) -> None:
        decision = evaluate_authorization_request(None)
        assert decision.implementation_authorization == "NO-GO"
        assert decision.ignored_metadata_keys == ()
        assert "authorization_requires_explicit_human_action" in decision.reasons

    def test_detect_untrusted_metadata_normalizes_keys(self) -> None:
        # Hyphenated / mixed-case variants are also detected.
        found = detect_untrusted_metadata({"route-exception-approved": True, "Real-Runtime-Authorized": True})
        assert "route-exception-approved" in found
        assert "Real-Runtime-Authorized" in found


# ===========================================================================
# 3. Human approval cannot be faked
# ===========================================================================


class TestHumanApprovalUnforgeable:
    @pytest.mark.parametrize(
        "token",
        [None, "approved", "true", "GO", "signoff", "owner", "trust_token", "", "phase_3i_authorized"],
    )
    def test_create_human_approval_never_valid(self, token) -> None:
        record = create_human_approval("P0-15", "owner", "approved", trust_token=token)
        assert is_approval_valid(record) is False
        assert record.is_valid() is False

    def test_direct_construction_forgery_blocked(self) -> None:
        # A caller cannot forge validity by building the dataclass directly.
        forged = HumanApprovalRecord(
            gate_id="P0-15", reviewer="owner", decision="approved", signature="forged-signature"
        )
        assert is_approval_valid(forged) is False
        empty = HumanApprovalRecord(gate_id="P0-15", reviewer="owner", decision="approved")
        assert is_approval_valid(empty) is False

    def test_forged_approval_does_not_resolve_gate(self) -> None:
        forged = HumanApprovalRecord(
            gate_id="P0-15", reviewer="owner", decision="approved", signature="anything"
        )
        smuggled = create_human_approval("P0-22", "owner", "approved", trust_token="approved")
        summary = evaluate_p0_evidence(approvals=[forged, smuggled])
        assert summary.resolved_count == 0
        by_id = {g.gate_id: g for g in summary.gates}
        assert by_id["P0-15"].classification == GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW
        assert by_id["P0-22"].classification == GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW

    def test_approval_record_redacts_signature_and_secrets(self) -> None:
        record = create_human_approval("P0-15", f"reviewer-{FAKE_SK}", "approved")
        blob = json.dumps(record.to_safe_dict())
        # The signature field is never exposed; smuggled secrets are redacted.
        assert "signature" not in record.to_safe_dict()
        assert FAKE_SK not in blob
        assert record.to_safe_dict()["valid"] is False


# ===========================================================================
# 4. Supply-chain provenance
# ===========================================================================


class TestSupplyChainProvenance:
    def test_descriptor_only_readable_as_metadata_only(self) -> None:
        for src_type in ALLOWED_SOURCE_TYPES:
            decision = classify_plugin_source({"sourceType": src_type})
            assert decision.metadata_readable is True
            assert decision.execution_trusted is False
            assert decision.reasons == ()

    @pytest.mark.parametrize(
        "source_type",
        [
            "remote_registry",
            "marketplace",
            "external_fetch",
            "external_download",
            "provider_generated",
            "llm_generated",
            "ai_generated",
            "generated",
            "unreviewed_local_executable",
            "local_executable",
            "unknown",
        ],
    )
    def test_untrusted_source_denied(self, source_type: str) -> None:
        decision = classify_plugin_source({"sourceType": source_type})
        assert decision.metadata_readable is False
        assert decision.execution_trusted is False
        assert decision.reasons  # a specific denial reason
        for reason in decision.reasons:
            assert reason in PROVENANCE_REASONS

    def test_unknown_non_mapping_denied(self) -> None:
        decision = classify_plugin_source("not a mapping")  # type: ignore[arg-type]
        assert decision.metadata_readable is False
        assert decision.execution_trusted is False
        assert "provenance_unknown_source" in decision.reasons

    def test_source_with_executable_field_denied_even_if_descriptor_only(self) -> None:
        decision = classify_plugin_source({"sourceType": "descriptor_only", "entrypoint": "main:run"})
        assert decision.metadata_readable is False
        assert "executable_field_denied" in decision.reasons

    def test_case_insensitive_source_type(self) -> None:
        decision = classify_plugin_source({"sourceType": "Marketplace"})
        assert decision.metadata_readable is False
        assert "marketplace_denied" in decision.reasons

    def test_no_source_type_is_unknown_denied(self) -> None:
        decision = classify_plugin_source({"origin": ""})
        assert decision.metadata_readable is False

    def test_integrity_requirements_missing_stays_unresolved(self) -> None:
        decision = evaluate_provenance_integrity({"sourceType": "descriptor_only"})
        assert decision.requirements_present is False
        assert decision.verified is False
        assert "integrity_requirements_missing" in decision.reasons

    def test_integrity_requirements_present_not_verified(self) -> None:
        decision = evaluate_provenance_integrity({"sourceType": "descriptor_only", "checksum": "deadbeef", "signature": "sig"})
        assert decision.requirements_present is True
        assert decision.verified is False  # never auto-verified
        assert "integrity_requirements_present_not_verified" in decision.reasons


# ===========================================================================
# 5. Route exception gap
# ===========================================================================


class TestRouteExceptionGap:
    def test_route_change_detected_and_required(self) -> None:
        decision = evaluate_route_exception({"newRoute": "/api/dev/v1/sandbox"})
        assert decision.route_change_detected is True
        assert decision.route_exception_required is True
        assert decision.route_exception_approved is False
        assert "route_exception_requires_human_route_governance_approval" in decision.reasons

    def test_no_change_no_exception(self) -> None:
        decision = evaluate_route_exception({})  # type: ignore[arg-type]
        # empty mapping → no change requested
        assert decision.route_change_detected is False
        assert decision.route_exception_approved is False

    def test_metadata_cannot_approve_route_exception(self) -> None:
        decision = evaluate_route_exception(
            {"newRoute": "/api/dev/v1/sandbox"},
            untrusted_metadata={"route_exception_approved": True, "approved": True, "reviewer": "owner"},
        )
        assert decision.route_exception_approved is False
        assert "route_exception_approved" in decision.ignored_metadata_keys
        assert "approved" in decision.ignored_metadata_keys

    def test_openapi_routes_unchanged(self, app) -> None:
        # The evaluator must not have added any route to the real app.
        counts = route_governance_counts(app)
        assert counts == {
            "openApiPaths": 34,
            "runtimeRoutes": 34,
            "toolGetRoutes": 5,
            "toolWriteRoutes": 0,
            "toolDryRunRoutes": 1,
            "toolExecutionRoutes": 1,
        }
        assert_route_governance_unchanged(app)

    def test_no_sandbox_or_p0_route_exposed(self, app) -> None:
        client = TestClient(app)
        spec = client.get("/openapi.json").json()
        for path in spec["paths"]:
            lower = path.lower()
            assert "/sandbox" not in lower
            assert "/p0" not in lower
            assert "/evidence" not in lower


# ===========================================================================
# 6. Rollback / incident readiness gap
# ===========================================================================


class TestRollbackIncidentGap:
    def test_temp_targets_and_real_owner_partial_not_ready(self) -> None:
        decision = evaluate_rollback_readiness(
            {"cleanupTargets": ["/tmp/rollback/a.json", "/tmp/rollback/b.json"], "incidentOwner": "release-engineering"}
        )
        assert decision.cleanup_targets_safe is True
        assert decision.production_path_present is False
        assert decision.incident_owner_present is True
        # Still NOT ready — human/operator approval required.
        assert decision.ready is False
        assert "rollback_requires_human_operator_approval" in decision.reasons

    def test_production_path_in_targets_denied(self) -> None:
        # Fake production path only — never the real one.
        decision = evaluate_rollback_readiness(
            {"cleanupTargets": [FAKE_PROD_PATH], "incidentOwner": "release-engineering"}
        )
        assert decision.production_path_present is True
        assert decision.cleanup_targets_safe is False
        assert decision.ready is False
        assert "production_path_in_cleanup_targets" in decision.reasons

    def test_missing_incident_owner_unresolved(self) -> None:
        decision = evaluate_rollback_readiness({"cleanupTargets": ["/tmp/x.json"], "incidentOwner": ""})
        assert decision.incident_owner_present is False
        assert decision.ready is False
        assert "incident_owner_missing_or_fake" in decision.reasons

    @pytest.mark.parametrize("owner", ["approved", "true", "owner", "admin", "auto", "system", "me", "1"])
    def test_fake_owner_does_not_authorize(self, owner: str) -> None:
        decision = evaluate_rollback_readiness({"cleanupTargets": ["/tmp/x.json"], "incidentOwner": owner})
        assert decision.incident_owner_present is False
        assert decision.ready is False

    def test_non_temp_absolute_target_unsafe(self) -> None:
        decision = evaluate_rollback_readiness(
            {"cleanupTargets": ["/etc/important_config.json"], "incidentOwner": "release-engineering"}
        )
        assert decision.cleanup_targets_safe is False
        assert decision.ready is False

    def test_missing_plan_denied(self) -> None:
        decision = evaluate_rollback_readiness(None)  # type: ignore[arg-type]
        assert decision.ready is False
        assert "rollback_plan_missing" in decision.reasons

    def test_no_persistent_artifacts_verifier_uses_temp_only(self, tmp_path: Path) -> None:
        # The evaluator itself creates nothing; running it repeatedly in a temp
        # tree must leave no runtime-store artifacts behind.
        from hermes_cli.dev_web_safety_baseline import find_runtime_store_artifacts

        for plan in (
            {"cleanupTargets": [str(tmp_path / "a.json")], "incidentOwner": "release-engineering"},
            {"cleanupTargets": [FAKE_PROD_PATH], "incidentOwner": "owner"},
        ):
            evaluate_rollback_readiness(plan)
        assert find_runtime_store_artifacts(tmp_path) == []


# ===========================================================================
# 7. Evidence reproducibility
# ===========================================================================


class TestEvidenceReproducibility:
    def test_no_test_command_is_partial(self) -> None:
        decision = classify_evidence_quality({"description": "some evidence"})
        assert decision.quality == "partial"
        assert decision.reproducible is False
        assert decision.has_test_command is False
        assert decision.resolvable_without_human is False

    def test_with_test_command_is_candidate_not_resolved(self) -> None:
        decision = classify_evidence_quality({"testCommand": "pytest tests/test_dev_web_phase_3e_h_remaining_p0_reduction.py -q"})
        assert decision.quality == "candidate_for_review"
        assert decision.reproducible is True
        assert decision.has_test_command is True
        assert decision.resolvable_without_human is False

    def test_empty_record_is_no_evidence(self) -> None:
        decision = classify_evidence_quality({})
        assert decision.quality == "no_evidence"

    def test_non_mapping_is_no_evidence(self) -> None:
        decision = classify_evidence_quality("not a mapping")  # type: ignore[arg-type]
        assert decision.quality == "no_evidence"

    def test_summary_redacts_secrets_and_production_paths(self) -> None:
        # A summary built normally must carry no raw secret / production path.
        summary = evaluate_p0_evidence(untrusted_metadata={"apikey": FAKE_SK, "path": FAKE_PROD_PATH})
        blob = json.dumps(summary.to_safe_dict())
        assert FAKE_SK not in blob
        assert "/Users/huangruibang/.hermes" not in blob
        assert "state.db" not in blob
        # The smuggled apikey is detected + ignored (it is a bypass-shaped key).
        assert "apikey" in summary.ignored_metadata_keys


# ===========================================================================
# 8. Source-boundary + dev-web API isolation
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


def test_p0_module_source_has_no_forbidden_surface() -> None:
    src = _src(p0_mod)
    for token in _STRICT_FORBIDDEN_TOKENS:
        assert token not in src, f"dev_web_p0_evidence: forbidden token {token!r}"


def test_p0_module_does_no_file_io() -> None:
    # Pure evaluators only — no filesystem access of any kind.
    src = _src(p0_mod)
    for token in ("open(", "Path(", "os.stat", "os.listdir", "os.walk", "os.read", ".read_text(", ".write("):
        assert token not in src, f"dev_web_p0_evidence: file-IO token {token!r}"


def test_p0_module_references_production_only_as_denial_target() -> None:
    src = _src(p0_mod)
    # The production home is referenced only conceptually in policy text /
    # markers — never opened. No literal production path is read.
    for forbidden in ("open('/Users", "read_text('/Users", "stat('/Users"):
        assert forbidden not in src


def test_no_dev_web_module_imports_p0_evidence() -> None:
    sandbox_family = {
        "dev_web_p0_evidence",
        "dev_web_sandbox_proof",
        "dev_web_sandbox_guards",
        "dev_web_sandbox_policy",
        "dev_web_sandbox_audit",
        "dev_web_safety_baseline",
        "dev_web_sandbox_runner",
        "dev_web_sandbox_scenarios",
    }
    candidates = sorted((REPO_ROOT / "hermes_cli").glob("dev_web_*.py"))
    for path in candidates:
        if path.stem in sandbox_family:
            continue
        src = path.read_text(encoding="utf-8")
        assert "dev_web_p0_evidence" not in src, f"{path.name} imports dev_web_p0_evidence"


def test_p0_evidence_not_wired_into_fastapi_app() -> None:
    api_src = (REPO_ROOT / "hermes_cli" / "dev_web_api.py").read_text(encoding="utf-8")
    assert "dev_web_p0_evidence" not in api_src


# ===========================================================================
# 9. Route governance unchanged (regression)
# ===========================================================================


class TestRouteGovernanceUnchanged:
    def test_formatted_baseline(self, app) -> None:
        from hermes_cli.dev_web_safety_baseline import format_route_governance

        assert format_route_governance(route_governance_counts(app)) == ROUTE_GOVERNANCE_EXPECTED

    def test_new_route_flags_all_zero(self) -> None:
        from hermes_cli.dev_web_safety_baseline import route_governance_new_route_flags

        flags = route_governance_new_route_flags()
        assert all(v == 0 for v in flags.values())


# ===========================================================================
# 10. Adversarial-bypass regressions (each locks a confirmed bypass closed)
# ===========================================================================


class TestAdversarialBypassRegressions:
    @pytest.mark.parametrize(
        "exec_key",
        [
            "subprocess", "spawn", "code", "run", "eval", "python", "src",
            "runtime", "fork", "loader", "program", "node", "process",
            "sourceCode", "dockerImage", "script", "entrypoint", "command",
            "source", "file", "path", "main", "app",
        ],
    )
    def test_provenance_exec_field_denied_on_allowed_type(self, exec_key: str) -> None:
        # Regression: an allowed source type carrying an executable-ish field
        # must be denied metadata readability (was leaking via incomplete stem set).
        decision = classify_plugin_source({"sourceType": "descriptor_only", exec_key: "x"})
        assert decision.metadata_readable is False
        assert "executable_field_denied" in decision.reasons

    @pytest.mark.parametrize(
        "benign_key",
        [
            "sourceType", "source_type", "origin", "name", "version", "status",
            "description", "author", "category", "platforms", "profileName",
            "homepage", "license", "displayName",
        ],
    )
    def test_provenance_benign_field_preserved(self, benign_key: str) -> None:
        # Token-exact matching must NOT trip on benign keys whose substrings
        # resemble stems (description ⊃ script, profile ⊃ file).
        if benign_key in ("sourceType", "source_type", "origin"):
            source = {benign_key: "descriptor_only"}
        else:
            source = {"sourceType": "descriptor_only", benign_key: "benign-value"}
        decision = classify_plugin_source(source)
        assert decision.metadata_readable is True, benign_key
        assert decision.execution_trusted is False

    @pytest.mark.parametrize(
        "requested",
        [
            "Add a new POST route /admin/exec to the OpenAPI surface",
            "register endpoint /x",
            ["POST", "/api/new"],
            ("add_route", "/x"),
            {"action": "create route", "path": "/y"},
        ],
    )
    def test_route_change_detected_in_any_shape(self, requested) -> None:
        # Regression: a route change described as a string/list/tuple (not a
        # mapping with known keys) must still be detected.
        decision = evaluate_route_exception(requested)
        assert decision.route_change_detected is True
        assert decision.route_exception_required is True
        assert decision.route_exception_approved is False

    def test_empty_route_request_not_detected(self) -> None:
        assert evaluate_route_exception("").route_change_detected is False
        assert evaluate_route_exception({}).route_change_detected is False

    @pytest.mark.parametrize(
        "owner",
        [
            "approved-by-ai", "ai-approver", "claude", "gpt-bot", "null",
            "none", "placeholder", "TBD", "N/A", "default", "unknown",
            "anonymous", "confirmed", "yes", "system", "automated",
        ],
    )
    def test_fake_owner_siblings_rejected(self, owner: str) -> None:
        # Regression: token-based fake-owner detection catches placeholder /
        # affirmative / AI-attributed siblings the exact denylist missed.
        decision = evaluate_rollback_readiness({"cleanupTargets": ["/tmp/x"], "incidentOwner": owner})
        assert decision.incident_owner_present is False
        assert decision.ready is False

    @pytest.mark.parametrize("owner", ["release-engineering", "aidan", "oncall-payments", "sre-platform"])
    def test_real_owner_accepted(self, owner: str) -> None:
        decision = evaluate_rollback_readiness({"cleanupTargets": ["/tmp/x"], "incidentOwner": owner})
        assert decision.incident_owner_present is True
        # Ready still False — human/operator approval required regardless.
        assert decision.ready is False

    def test_production_home_constant_not_resolved(self) -> None:
        # Regression: PRODUCTION_HERMES_HOME must NOT call .resolve() —
        # resolving stats the forbidden production directory at import time,
        # which would violate the "no ~/.hermes access (not even metadata)" rule.
        from hermes_cli import dev_web_safety_baseline as baseline

        src = _src(baseline)
        assert 'PRODUCTION_HERMES_HOME: Path = Path("/Users/huangruibang/.hermes").resolve()' not in src
        # The value is the literal path (string-only denial target).
        assert str(baseline.PRODUCTION_HERMES_HOME) == "/Users/huangruibang/.hermes"

    def test_importing_p0_evidence_does_not_touch_production_home(self) -> None:
        # Functional guard: a fresh re-import of the safety baseline (which the
        # p0_evidence import chain pulls in) must issue no stat/lstat/realpath
        # against the production directory.
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
            from hermes_cli import dev_web_safety_baseline as baseline

            importlib.reload(baseline)
        finally:
            os.lstat = real_lstat
            os.stat = real_stat
            posixpath.realpath = real_realpath
            os.path.realpath = real_realpath
        prod_touches = [p for p in touched if "/Users/huangruibang/.hermes" in p]
        assert prod_touches == [], f"production home touched on import: {prod_touches}"
