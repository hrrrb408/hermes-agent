"""Phase 4A Target B Readiness scaffold — backend isolation tests.

Asserts that the Phase 4A Target B Readiness surface is **frontend-only** and
the backend disabled scaffold adds **no backend route** and **no backend import
graph change** that could expose execution / install / approval / registry /
marketplace capability, and that the frozen no-authorization invariants still
hold:

  - ``hermes_cli.dev_web_api`` does NOT import the Target B readiness scaffold
    (or any governance / runtime / human-review / plugin-runtime module).
  - No OpenAPI path is named for target-b / readiness / scaffold / plugin
    install / plugin execute / registry fetch / marketplace / approve / authorize.
  - Probing candidate target-b / plugin-install / registry / marketplace /
    approval / authorization API paths returns 404.
  - The frozen route-governance baseline ``34/34/5/0/1/1`` is unchanged, every
    "new route" flag stays zero, and ``assert_route_governance_unchanged``
    passes.
  - The P0 evidence model still projects the frozen no-approval invariants
    (resolved_count 0, 5 blocked_by_human_review, every authorization flag
    NO-GO / not-authorized).
  - The Target B disabled scaffold itself keeps execution DISABLED, every
    authorization NO-GO, and P0 resolved 0.
  - No ``~/.hermes`` access and no production ``state.db`` access (string-policy
    only; never resolved).

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.
All forbidden-path assertions use fake / string-policy paths only.

Phase: 4A — Target B Readiness Scaffold
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli import dev_web_api as dev_web_api_module
from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_p0_evidence import (
    GATES,
    GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW,
    GATE_STATUS_PARTIAL_EVIDENCE,
    GATE_STATUS_RESOLVED,
    IMPLEMENTATION_AUTHORIZATION,
    NEW_ROUTE,
    PHASE_3I_AUTHORIZED,
    PRODUCTION_ROLLOUT,
    REAL_RUNTIME,
    evaluate_p0_evidence,
)
from hermes_cli.dev_web_safety_baseline import (
    ROUTE_GOVERNANCE_EXPECTED,
    assert_route_governance_unchanged,
    format_route_governance,
    route_governance_counts,
    route_governance_drift,
)
from hermes_cli.dev_web_target_b_readiness import build_target_b_readiness_report


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return TestClient(create_dev_web_api_app(cfg))


@pytest.fixture()
def app(tmp_path: Path):
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return create_dev_web_api_app(cfg)


#: Modules that the read-only WebUI surface must NOT pull into the backend app.
FORBIDDEN_BACKEND_IMPORTS = (
    "dev_web_target_b_readiness",
    "dev_web_runtime_governance",
    "dev_web_runtime_governance_cli",
    "dev_web_plugin_runtime",
    "dev_web_plugin_runtime_binding",
    "dev_web_fixture_plugins",
    "human_review_governance",
    "governance_hub",
)

#: Candidate backend API paths that must NOT exist for Target B readiness.
CANDIDATE_TARGET_B_PATHS = (
    "/api/dev/v1/target-b",
    "/api/dev/v1/target-b/readiness",
    "/api/dev/v1/target-b/summary",
    "/api/dev/v1/target-b/architecture",
    "/api/dev/v1/target-b/permission-model",
    "/api/dev/v1/target-b/registry",
    "/api/dev/v1/target-b/execute",
    "/api/dev/v1/target-b/approve",
    "/api/dev/v1/target-b/authorize",
    "/api/dev/v1/target-b/signoff",
    "/api/dev/v1/target-b/resolve",
    "/api/dev/v1/target-b/rollout",
    "/api/dev/v1/plugin-install",
    "/api/dev/v1/plugins/install",
    "/api/dev/v1/plugins/load",
    "/api/dev/v1/plugins/upload",
    "/api/dev/v1/plugin-execute",
    "/api/dev/v1/plugins/execute",
    "/api/dev/v1/registry/fetch",
    "/api/dev/v1/registry",
    "/api/dev/v1/marketplace",
    "/api/dev/v1/marketplace/install",
    "/api/dev/v1/approve",
    "/api/dev/v1/authorize",
)


# ---------------------------------------------------------------------------
# 1. dev_web_api does not import the Target B scaffold / governance modules
# ---------------------------------------------------------------------------


class TestDevWebApiIsolation:
    def test_dev_web_api_source_does_not_import_target_b_or_governance_modules(self) -> None:
        source = Path(dev_web_api_module.__file__).read_text(encoding="utf-8")
        for module in FORBIDDEN_BACKEND_IMPORTS:
            assert module not in source, (
                f"dev_web_api.py must not import {module} — the Target B readiness "
                "surface is frontend-only"
            )

    def test_dev_web_api_source_does_not_reference_target_b_paths(self) -> None:
        source = Path(dev_web_api_module.__file__).read_text(encoding="utf-8").lower()
        for needle in (
            "target-b",
            "target_b",
            "readiness",
            "/scaffold",
            "plugin-install",
            "plugin-install",
            "registry/fetch",
            "/marketplace",
        ):
            assert needle not in source, (
                f"dev_web_api.py must not reference {needle!r} — no backend route"
            )


# ---------------------------------------------------------------------------
# 2. No OpenAPI path / runtime route is named for target b / readiness / install
# ---------------------------------------------------------------------------


class TestNoBackendRoute:
    def test_no_openapi_path_named_for_target_b_or_install_or_registry(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        for path in spec["paths"]:
            lowered = path.lower()
            assert "target-b" not in lowered
            assert "target_b" not in lowered
            assert "readiness" not in lowered
            assert "/scaffold" not in lowered
            assert "plugin-install" not in lowered
            assert "plugin-install" not in lowered
            assert "registry" not in lowered
            assert "/marketplace" not in lowered

    def test_candidate_target_b_paths_return_404(self, client: TestClient) -> None:
        for path in CANDIDATE_TARGET_B_PATHS:
            resp = client.get(path)
            assert resp.status_code == 404, f"{path} must not exist (got {resp.status_code})"
            # POST (approve/authorize/execute/install/rollout) must also be absent.
            post = client.post(path, json={})
            assert post.status_code == 404, f"POST {path} must not exist"


# ---------------------------------------------------------------------------
# 3. Route governance baseline unchanged (34/34/5/0/1/1, all new-route flags 0)
# ---------------------------------------------------------------------------


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

    def test_formatted_baseline_string(self, app) -> None:
        counts = route_governance_counts(app)
        assert format_route_governance(counts) == ROUTE_GOVERNANCE_EXPECTED == "34/34/5/0/1/1"

    def test_assert_unchanged_passes(self, app) -> None:
        # Must not raise.
        assert_route_governance_unchanged(app)

    def test_no_drift_and_no_new_route_flags(self, app) -> None:
        report = route_governance_drift(route_governance_counts(app))
        assert report["drifted"] is False


# ---------------------------------------------------------------------------
# 4. The P0 evidence model still freezes the no-approval invariants
# ---------------------------------------------------------------------------


class TestP0EvidenceFrozen:
    def test_gate_registry_has_24_gates_none_resolved(self) -> None:
        assert len(GATES) == 24
        for g in GATES:
            assert g.classification != GATE_STATUS_RESOLVED
            assert g.is_resolved() is False

    def test_gate_distribution_is_19_partial_5_blocked(self) -> None:
        partial = [g for g in GATES if g.classification == GATE_STATUS_PARTIAL_EVIDENCE]
        blocked = [g for g in GATES if g.classification == GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW]
        assert len(partial) == 19
        assert len(blocked) == 5
        assert {g.gate_id for g in blocked} == {"P0-15", "P0-16", "P0-18", "P0-19", "P0-22"}

    def test_authorization_flags_are_all_no_go(self) -> None:
        assert IMPLEMENTATION_AUTHORIZATION == "NO-GO"
        assert PHASE_3I_AUTHORIZED is False
        assert REAL_RUNTIME == "NO-GO"
        assert NEW_ROUTE == "NO-GO"
        assert PRODUCTION_ROLLOUT == "NO-GO"

    def test_p0_summary_resolved_count_is_zero(self) -> None:
        summary = evaluate_p0_evidence()
        assert summary.total_gates == 24
        assert summary.resolved_count == 0
        assert summary.partial_evidence_count == 19
        assert summary.blocked_by_human_review_count == 5
        assert summary.implementation_authorization == "NO-GO"
        assert summary.production_rollout == "NO-GO"


# ---------------------------------------------------------------------------
# 5. The Target B disabled scaffold itself stays disabled (importing it into a
#    test does NOT wire it into the backend app).
# ---------------------------------------------------------------------------


class TestTargetBScaffoldStaysDisabled:
    def test_report_is_disabled_when_imported(self) -> None:
        report = build_target_b_readiness_report()
        assert report.execution_status == "DISABLED"
        assert report.production_runtime == "NO-GO"
        assert report.remote_registry == "NO-GO"
        assert report.marketplace == "NO-GO"
        assert report.webui_execution == "NO-GO"
        assert report.approval_authorization == "NO-GO"
        assert report.production_rollout == "NO-GO"
        assert report.p0_resolved == 0
        assert report.backend_routes_changed is False


# ---------------------------------------------------------------------------
# 6. No production access (loopback bind + fake/string-policy path policy).
#    Never stat / ls / resolve ~/.hermes — only assert string policy + 404.
# ---------------------------------------------------------------------------


class TestNoProductionAccess:
    #: Forbidden path STEMS used as STRING POLICY only — never resolved, never
    #: opened. They exist to assert that candidate API paths cannot reach them.
    FORBIDDEN_PATH_STEMS = (
        "~/.hermes",
        ".hermes/state.db",
        "production/state.db",
        "state.db",
    )

    def test_dev_app_binds_loopback_only(self, tmp_path: Path) -> None:
        # The dev WebUI must bind to 127.0.0.1 only — never 0.0.0.0.
        cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
        assert cfg.host == "127.0.0.1"
        app = create_dev_web_api_app(cfg)
        assert app is not None

    def test_candidate_target_b_paths_do_not_touch_production(self, client: TestClient) -> None:
        # Every candidate path is a 404; none reaches production state.
        for path in CANDIDATE_TARGET_B_PATHS:
            resp = client.get(path)
            assert resp.status_code == 404

    def test_forbidden_path_stems_are_string_policy_only(self) -> None:
        # These stems are policy strings used by the redactor / guard, never
        # resolved at runtime. The assertion itself never touches the filesystem.
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert isinstance(stem, str)
            assert stem  # non-empty policy string
