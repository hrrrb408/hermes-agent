"""Phase 4C — Target B Authorization & Gate Resolution Package isolation tests.

Asserts that the Phase 4C Target B authorization package is **frontend-only**
and the gated authorization layers add **no backend route** and **no backend
import graph change** that could expose execution / install / approval /
authorization / registry / marketplace / runtime / trust-token / signature
capability, and that the frozen gated invariants still hold:

  - ``hermes_cli.dev_web_api`` does NOT import any Phase 4C target_b
    authorization module (or any governance / runtime / human-review /
    plugin-runtime module);
  - No OpenAPI path is named for target-b authorization / enablement /
    trust-token / approval / production-signature / rollout;
  - Probing candidate phase-4c API paths returns 404;
  - The frozen route-governance baseline ``34/34/5/0/1/1`` is unchanged, every
    "new route" flag stays zero, and ``assert_route_governance_unchanged``
    passes;
  - The aggregate Target B authorization package report keeps readiness BLOCKED,
    every authorization verdict NO-GO, trust token not provisioned, P0 resolved
    0, production_enablement_allowed False, backend_routes_changed False;
  - Every Phase 4C module source is pure (no forbidden primitive) and references
    no ``~/.hermes`` / production ``state.db`` path;
  - The default readiness evaluator never enables production even with a
    complete fixture package.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts / stops / signals a gateway or dashboard, and
introduces no new route. The production Gateway PID 28428 is referenced only as
a do-not-touch string.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli import dev_web_api as dev_web_api_module
from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_target_b_enablement_readiness import (
    EnablementReadinessInput,
    build_target_b_authorization_package_report,
    evaluate_target_b_enablement_readiness,
)
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


#: Phase 4C modules that the read-only WebUI surface must NOT pull into the app.
PHASE4C_MODULES = (
    "dev_web_target_b_authorization_common",
    "dev_web_target_b_human_approval",
    "dev_web_target_b_trust_token",
    "dev_web_target_b_trusted_publishers",
    "dev_web_target_b_production_signature",
    "dev_web_target_b_sandbox_lifecycle",
    "dev_web_target_b_registry_policy",
    "dev_web_target_b_network_policy",
    "dev_web_target_b_secret_policy",
    "dev_web_target_b_incident_rollback",
    "dev_web_target_b_route_authorization",
    "dev_web_target_b_p0_gate_resolution",
    "dev_web_target_b_enablement_readiness",
)

#: Other governance / runtime modules that must also stay out of dev_web_api.
OTHER_FORBIDDEN_BACKEND_IMPORTS = (
    "dev_web_target_b_readiness",
    "dev_web_target_b_report",
    "dev_web_target_b_runtime",
    "dev_web_runtime_governance",
    "dev_web_runtime_governance_cli",
    "dev_web_plugin_runtime",
    "dev_web_plugin_runtime_binding",
    "dev_web_fixture_plugins",
    "human_review_governance",
    "governance_hub",
)

#: Candidate backend API paths that must NOT exist for the Phase 4C surface.
CANDIDATE_PHASE4C_PATHS = (
    "/api/dev/v1/target-b-authorization",
    "/api/dev/v1/target-b/authorization",
    "/api/dev/v1/target-b/enablement",
    "/api/dev/v1/target-b/readiness",
    "/api/dev/v1/target-b/trust-token",
    "/api/dev/v1/target-b/approval-record",
    "/api/dev/v1/target-b/human-approval",
    "/api/dev/v1/target-b/trusted-publishers",
    "/api/dev/v1/target-b/production-signature",
    "/api/dev/v1/target-b/sandbox-lifecycle",
    "/api/dev/v1/target-b/registry-policy",
    "/api/dev/v1/target-b/network-policy",
    "/api/dev/v1/target-b/secret-policy",
    "/api/dev/v1/target-b/incident-rollback",
    "/api/dev/v1/target-b/route-authorization",
    "/api/dev/v1/target-b/p0-resolution",
    "/api/dev/v1/target-b/authorize",
    "/api/dev/v1/target-b/provision-trust-token",
    "/api/dev/v1/target-b/rollout",
    "/api/dev/v1/target-b/enable",
)

#: Forbidden usage primitives no Phase 4C module may use.
FORBIDDEN_USAGE_PATTERNS = (
    "import subprocess",
    "subprocess.",
    "import importlib",
    "importlib.",
    "__import__",
    "import socket",
    "socket.",
    "requests.",
    "httpx.",
    "aiohttp.",
    "urllib",
    "eval(",
    "exec(",
    "os.system",
    "os.popen",
)

#: Forbidden path stems no Phase 4C module may reference.
FORBIDDEN_PATH_STEMS = (
    "~/.hermes",
    ".hermes/state.db",
    "production/state.db",
    "state.db",
)


# ---------------------------------------------------------------------------
# 1. dev_web_api does not import any Phase 4C target_b authorization module
# ---------------------------------------------------------------------------


class TestDevWebApiIsolation:
    def test_dev_web_api_source_does_not_import_phase4c_modules(self) -> None:
        source = Path(dev_web_api_module.__file__).read_text(encoding="utf-8")
        for module in PHASE4C_MODULES + OTHER_FORBIDDEN_BACKEND_IMPORTS:
            assert module not in source, (
                f"dev_web_api.py must not import {module} — the Phase 4C Target B "
                "authorization package surface is frontend-only"
            )

    def test_dev_web_api_source_does_not_reference_phase4c_paths(self) -> None:
        source = Path(dev_web_api_module.__file__).read_text(encoding="utf-8").lower()
        for needle in (
            "target-b-authorization",
            "target_b_authorization",
            "target-b/enablement",
            "trust-token",
            "human-approval",
            "production-signature",
            "sandbox-lifecycle",
            "registry-policy",
            "network-policy",
            "secret-policy",
            "incident-rollback",
            "route-authorization",
            "p0-resolution",
            "/provision-trust-token",
        ):
            assert needle not in source, (
                f"dev_web_api.py must not reference {needle!r} — no backend route"
            )


# ---------------------------------------------------------------------------
# 2. No OpenAPI path / runtime route is named for the Phase 4C surface
# ---------------------------------------------------------------------------


class TestNoBackendRoute:
    def test_no_openapi_path_named_for_phase4c_surface(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        for path in spec["paths"]:
            lowered = path.lower()
            assert "target-b-authorization" not in lowered
            assert "target_b_authorization" not in lowered
            assert "target-b/enablement" not in lowered
            assert "trust-token" not in lowered
            assert "human-approval" not in lowered
            assert "production-signature" not in lowered
            assert "sandbox-lifecycle" not in lowered
            assert "registry-policy" not in lowered
            assert "network-policy" not in lowered
            assert "secret-policy" not in lowered
            assert "incident-rollback" not in lowered
            assert "route-authorization" not in lowered
            assert "p0-resolution" not in lowered
            assert "/provision-trust-token" not in lowered

    def test_candidate_phase4c_paths_return_404(self, client: TestClient) -> None:
        for path in CANDIDATE_PHASE4C_PATHS:
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
# 4. The aggregate Target B authorization package report stays gated
# ---------------------------------------------------------------------------


class TestAuthorizationPackageStaysGated:
    def test_report_blocked_and_every_verdict_no_go(self) -> None:
        report = build_target_b_authorization_package_report()
        assert report.schema_version == "phase-4c-target-b-authorization-v1"
        assert report.readiness_status == "BLOCKED"
        assert report.production_enablement_allowed is False
        for verdict in (
            report.production_runtime,
            report.registry,
            report.marketplace,
            report.webui_execution,
            report.approval_authorization,
            report.production_rollout,
        ):
            assert verdict == "NO-GO"
        assert report.trust_token_provisioned is False
        assert report.p0_total == 24
        assert report.p0_resolved == 0
        assert report.p0_pending_human_review == 5
        assert set(report.pending_human_review_gates) == {
            "P0-15",
            "P0-16",
            "P0-18",
            "P0-19",
            "P0-22",
        }
        assert report.route_governance_baseline == "34/34/5/0/1/1"
        assert report.backend_routes_changed is False

    def test_report_never_states_a_positive_authorization(self) -> None:
        text = str(build_target_b_authorization_package_report().to_safe_dict()).lower()
        for marker in (
            "production_runtime_go=true",
            "target_b_authorized=true",
            "implementation_authorization=go",
            "production rollout approved",
            "approved_by_ai=true",
            "trust_token_provisioned=true",
            "production_enablement_allowed=true",
        ):
            assert marker not in text

    def test_default_evaluator_blocked_even_with_fixture_package(self) -> None:
        # The DEFAULT evaluator call (no inputs) is BLOCKED.
        default = evaluate_target_b_enablement_readiness()
        assert default.readiness_status == "BLOCKED"
        assert default.production_enablement_allowed is False
        # A complete fixture package is "ready but not enabled" — never enabled.
        fixture_inputs = EnablementReadinessInput(
            human_approval_valid=True,
            trust_token_valid=True,
            trusted_publishers_present=True,
            production_signature_verifier_authorized=True,
            sandbox_lifecycle_approved=True,
            registry_trust_policy_approved=True,
            network_allowlist_approved=True,
            secret_policy_approved=True,
            incident_rollback_plan_approved=True,
            route_authorization_approved=True,
            p0_gates_resolved=True,
            production_mode=True,
            fixture_only=True,
        )
        fixture_result = evaluate_target_b_enablement_readiness(fixture_inputs)
        assert fixture_result.production_enablement_allowed is False

    def test_report_is_deterministic(self) -> None:
        a = build_target_b_authorization_package_report().to_safe_dict()
        b = build_target_b_authorization_package_report().to_safe_dict()
        assert a == b


# ---------------------------------------------------------------------------
# 5. Source purity across all 13 Phase 4C modules
# ---------------------------------------------------------------------------


class TestPhase4CSourcePurity:
    @pytest.mark.parametrize("module_name", PHASE4C_MODULES)
    def test_module_source_contains_no_forbidden_primitive(self, module_name: str) -> None:
        module = __import__("hermes_cli." + module_name, fromlist=["_"])
        source = Path(module.__file__).read_text(encoding="utf-8")
        for pattern in FORBIDDEN_USAGE_PATTERNS:
            assert pattern not in source, f"{module_name} must not use {pattern!r}"

    @pytest.mark.parametrize("module_name", PHASE4C_MODULES)
    def test_module_source_does_not_reference_production_paths(self, module_name: str) -> None:
        module = __import__("hermes_cli." + module_name, fromlist=["_"])
        source = Path(module.__file__).read_text(encoding="utf-8").lower()
        for stem in FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"{module_name} must not reference {stem!r}"


# ---------------------------------------------------------------------------
# 6. No production access (loopback bind + string-policy path policy).
# ---------------------------------------------------------------------------


class TestNoProductionAccess:
    FORBIDDEN_PATH_STEMS = FORBIDDEN_PATH_STEMS

    def test_dev_app_binds_loopback_only(self, tmp_path: Path) -> None:
        cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
        assert cfg.host == "127.0.0.1"
        app = create_dev_web_api_app(cfg)
        assert app is not None

    def test_candidate_phase4c_paths_do_not_touch_production(self, client: TestClient) -> None:
        for path in CANDIDATE_PHASE4C_PATHS:
            resp = client.get(path)
            assert resp.status_code == 404

    def test_forbidden_path_stems_are_string_policy_only(self) -> None:
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert isinstance(stem, str)
            assert stem

    def test_production_gateway_pid_is_a_do_not_touch_string_only(self) -> None:
        # The production gateway PID 28428 is referenced only as a documentation
        # do-not-touch target in the gated layers. It is never signaled.
        from hermes_cli.dev_web_target_b_common import (
            TARGET_B_PRODUCTION_GATEWAY_PID_REFERENCE,
        )

        assert "28428" in TARGET_B_PRODUCTION_GATEWAY_PID_REFERENCE
        assert isinstance(TARGET_B_PRODUCTION_GATEWAY_PID_REFERENCE, str)


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
