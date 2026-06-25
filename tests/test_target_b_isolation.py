"""Phase 4B — Target B End-to-End Implementation backend isolation tests.

Asserts that the Phase 4B Target B implementation surface is **frontend-only**
and the gated backend layers add **no backend route** and **no backend import
graph change** that could expose execution / install / approval / registry /
marketplace / runtime capability, and that the frozen gated invariants still
hold:

  - ``hermes_cli.dev_web_api`` does NOT import any Phase 4B target_b_* module
    (or any governance / runtime / human-review / plugin-runtime module);
  - No OpenAPI path is named for target-b implementation / runtime / execute /
    plugin-install / registry / marketplace / approve / authorize;
  - Probing candidate target-b-implementation / plugin-execute / runtime /
    approval / authorization API paths returns 404;
  - The frozen route-governance baseline ``34/34/5/0/1/1`` is unchanged, every
    "new route" flag stays zero, and ``assert_route_governance_unchanged``
    passes;
  - The aggregate Target B implementation report keeps execution DISABLED,
    every authorization NO-GO, P0 resolved 0, and backend_routes_changed False;
  - No ``~/.hermes`` access and no production ``state.db`` access (string-policy
    only; never resolved).

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli import dev_web_api as dev_web_api_module
from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_target_b_report import build_target_b_implementation_report
from hermes_cli.dev_web_safety_baseline import (
    ROUTE_GOVERNANCE_EXPECTED,
    assert_route_governance_unchanged,
    format_route_governance,
    route_governance_counts,
    route_governance_drift,
)


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return TestClient(create_dev_web_api_app(cfg))


@pytest.fixture()
def app(tmp_path: Path):
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return create_dev_web_api_app(cfg)


#: Phase 4B modules that the read-only WebUI surface must NOT pull into the app.
PHASE4B_MODULES = (
    "dev_web_target_b_common",
    "dev_web_target_b_package",
    "dev_web_target_b_signature",
    "dev_web_target_b_permissions",
    "dev_web_target_b_registry",
    "dev_web_target_b_sandbox",
    "dev_web_target_b_approval",
    "dev_web_target_b_execution_policy",
    "dev_web_target_b_runtime",
    "dev_web_target_b_audit",
    "dev_web_target_b_rollback",
    "dev_web_target_b_report",
)

#: Other governance / runtime modules that must also stay out of dev_web_api.
OTHER_FORBIDDEN_BACKEND_IMPORTS = (
    "dev_web_target_b_readiness",
    "dev_web_runtime_governance",
    "dev_web_runtime_governance_cli",
    "dev_web_plugin_runtime",
    "dev_web_plugin_runtime_binding",
    "dev_web_fixture_plugins",
    "human_review_governance",
    "governance_hub",
)

#: Candidate backend API paths that must NOT exist for the Phase 4B surface.
CANDIDATE_PHASE4B_PATHS = (
    "/api/dev/v1/target-b-implementation",
    "/api/dev/v1/target-b/runtime",
    "/api/dev/v1/target-b/execute",
    "/api/dev/v1/target-b/prepare",
    "/api/dev/v1/target-b/dry-run",
    "/api/dev/v1/target-b/signature/verify",
    "/api/dev/v1/target-b/sandbox/execute",
    "/api/dev/v1/target-b/approval",
    "/api/dev/v1/target-b/approve",
    "/api/dev/v1/target-b/authorize",
    "/api/dev/v1/target-b/rollout",
    "/api/dev/v1/target-b/rollback",
    "/api/dev/v1/plugin-install",
    "/api/dev/v1/plugins/load",
    "/api/dev/v1/plugins/execute",
    "/api/dev/v1/registry/fetch",
    "/api/dev/v1/marketplace",
    "/api/dev/v1/marketplace/install",
    "/api/dev/v1/approve",
    "/api/dev/v1/authorize",
)


# ---------------------------------------------------------------------------
# 1. dev_web_api does not import any Phase 4B target_b module
# ---------------------------------------------------------------------------


class TestDevWebApiIsolation:
    def test_dev_web_api_source_does_not_import_phase4b_modules(self) -> None:
        source = Path(dev_web_api_module.__file__).read_text(encoding="utf-8")
        for module in PHASE4B_MODULES + OTHER_FORBIDDEN_BACKEND_IMPORTS:
            assert module not in source, (
                f"dev_web_api.py must not import {module} — the Phase 4B Target B "
                "implementation surface is frontend-only"
            )

    def test_dev_web_api_source_does_not_reference_phase4b_paths(self) -> None:
        source = Path(dev_web_api_module.__file__).read_text(encoding="utf-8").lower()
        for needle in (
            "target-b-implementation",
            "target_b_implementation",
            "target-b/runtime",
            "/plugin-execute",
            "plugin-install",
            "registry/fetch",
            "/marketplace",
            "signature/verify",
            "sandbox/execute",
        ):
            assert needle not in source, (
                f"dev_web_api.py must not reference {needle!r} — no backend route"
            )


# ---------------------------------------------------------------------------
# 2. No OpenAPI path / runtime route is named for the Phase 4B surface
# ---------------------------------------------------------------------------


class TestNoBackendRoute:
    def test_no_openapi_path_named_for_phase4b_surface(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        for path in spec["paths"]:
            lowered = path.lower()
            # Phase-4B-specific path roots must not exist. (The pre-existing
            # review-approve /execute and /dry-run routes are part of the frozen
            # 34/34/5/0/1/1 baseline and are NOT Phase 4B routes — they are
            # covered by the candidate-path 404 test below.)
            assert "target-b-implementation" not in lowered
            assert "target_b_implementation" not in lowered
            assert "target-b/runtime" not in lowered
            assert "plugin-install" not in lowered
            assert "plugin-execute" not in lowered
            assert "plugins/execute" not in lowered
            assert "plugins/load" not in lowered
            assert "plugins/install" not in lowered
            assert "registry/fetch" not in lowered
            assert "/marketplace" not in lowered
            assert "signature/verify" not in lowered
            assert "sandbox/execute" not in lowered

    def test_candidate_phase4b_paths_return_404(self, client: TestClient) -> None:
        for path in CANDIDATE_PHASE4B_PATHS:
            resp = client.get(path)
            assert resp.status_code == 404, f"{path} must not exist (got {resp.status_code})"
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
        assert_route_governance_unchanged(app)

    def test_no_drift_and_no_new_route_flags(self, app) -> None:
        report = route_governance_drift(route_governance_counts(app))
        assert report["drifted"] is False


# ---------------------------------------------------------------------------
# 4. The aggregate Target B implementation report stays gated
# ---------------------------------------------------------------------------


class TestReportStaysGated:
    def test_report_every_verdict_no_go_and_p0_zero(self) -> None:
        report = build_target_b_implementation_report()
        assert report.implementation_status == "SCAFFOLD_READY"
        assert report.execution_status == "DISABLED"
        for verdict in (
            report.production_runtime,
            report.arbitrary_plugin_loading,
            report.remote_registry,
            report.marketplace,
            report.webui_execution,
            report.approval_authorization,
            report.production_rollout,
        ):
            assert verdict == "NO-GO"
        assert report.p0_total == 24
        assert report.p0_resolved == 0
        assert report.p0_partial_evidence == 19
        assert report.p0_pending_human_review == 5
        assert set(report.pending_human_review_gates) == {"P0-15", "P0-16", "P0-18", "P0-19", "P0-22"}
        assert report.route_governance_baseline == "34/34/5/0/1/1"
        assert report.backend_routes_changed is False
        assert len(report.implementation_layers) == 12
        for layer in report.implementation_layers:
            assert layer.enabled is False
            assert layer.execution_capable is False
            assert layer.network_capable is False
            assert layer.production_capable is False

    def test_report_never_states_a_positive_authorization(self) -> None:
        text = str(build_target_b_implementation_report().to_safe_dict()).lower()
        for marker in (
            "production_runtime_go=true",
            "target_b_authorized=true",
            "implementation_authorization=go",
            "production rollout approved",
            "approved_by_ai=true",
        ):
            assert marker not in text

    def test_report_is_deterministic(self) -> None:
        a = build_target_b_implementation_report().to_safe_dict()
        b = build_target_b_implementation_report().to_safe_dict()
        assert a == b


# ---------------------------------------------------------------------------
# 5. No production access (loopback bind + fake/string-policy path policy).
#    Never stat / ls / resolve ~/.hermes — only assert string policy + 404.
# ---------------------------------------------------------------------------


class TestNoProductionAccess:
    FORBIDDEN_PATH_STEMS = (
        "~/.hermes",
        ".hermes/state.db",
        "production/state.db",
        "state.db",
    )

    def test_dev_app_binds_loopback_only(self, tmp_path: Path) -> None:
        cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
        assert cfg.host == "127.0.0.1"
        app = create_dev_web_api_app(cfg)
        assert app is not None

    def test_candidate_phase4b_paths_do_not_touch_production(self, client: TestClient) -> None:
        for path in CANDIDATE_PHASE4B_PATHS:
            resp = client.get(path)
            assert resp.status_code == 404

    def test_forbidden_path_stems_are_string_policy_only(self) -> None:
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert isinstance(stem, str)
            assert stem
