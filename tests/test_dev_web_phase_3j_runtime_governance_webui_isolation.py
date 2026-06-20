"""Phase 3J Runtime Governance Read-only WebUI Surface — backend isolation tests.

Asserts that the Phase 3J read-only WebUI surface is **frontend-only** and adds
**no backend route** and **no backend import** of the runtime governance /
plugin runtime modules:

  - ``hermes_cli.dev_web_api`` does NOT import any runtime-governance or
    plugin-runtime module (the governance CLI / report projections stay out of
    the FastAPI app's import graph).
  - No OpenAPI path is named for runtime governance (``/runtime-governance``,
    ``/dev-runtime``, ``/plugins/runtime-governance`` …).
  - Probing candidate runtime-governance API paths returns 404.
  - The frozen route-governance baseline ``34/34/5/0/1/1`` is unchanged, every
    "new route" flag stays zero, and ``assert_route_governance_unchanged``
    passes.
  - The runtime governance report projections still project the frozen
    no-side-effect / no-authorization invariants (resolved_count 0, every
    authorization flag NO-GO / not-authorized, every side effect False).

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 3J — Runtime Governance Read-only WebUI Surface
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli import dev_web_api as dev_web_api_module
from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_runtime_governance import (
    assert_no_side_effect_surface,
    authorization_projection,
    build_runtime_p0_report,
    list_runtime_descriptors,
    side_effect_projection,
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


#: Modules that the read-only WebUI surface must NOT pull into the backend app.
FORBIDDEN_BACKEND_IMPORTS = (
    "dev_web_runtime_governance",
    "dev_web_runtime_governance_cli",
    "dev_web_plugin_runtime",
    "dev_web_plugin_runtime_binding",
    "dev_web_fixture_plugins",
)

#: Candidate backend API paths that must NOT exist for runtime governance.
CANDIDATE_RUNTIME_PATHS = (
    "/api/dev/v1/runtime-governance",
    "/api/dev/v1/runtime/governance",
    "/api/dev/v1/dev-runtime",
    "/api/dev/v1/plugins/runtime-governance",
    "/api/dev/v1/runtime-governance/descriptors",
    "/api/dev/v1/runtime-governance/p0-report",
)


# ---------------------------------------------------------------------------
# 1. dev_web_api does not import the runtime governance / plugin runtime modules
# ---------------------------------------------------------------------------


class TestDevWebApiIsolation:
    def test_dev_web_api_source_does_not_import_governance_modules(self) -> None:
        source = Path(dev_web_api_module.__file__).read_text(encoding="utf-8")
        for module in FORBIDDEN_BACKEND_IMPORTS:
            assert module not in source, (
                f"dev_web_api.py must not import {module} — the WebUI runtime "
                "governance surface is frontend-only"
            )

    def test_dev_web_api_source_does_not_register_a_runtime_governance_route(self) -> None:
        source = Path(dev_web_api_module.__file__).read_text(encoding="utf-8")
        lowered = source.lower()
        for needle in ("runtime-governance", "runtime_governance", "dev-runtime"):
            assert needle not in lowered, (
                f"dev_web_api.py must not reference {needle!r} — no backend route"
            )


# ---------------------------------------------------------------------------
# 2. No OpenAPI path / runtime route is named for runtime governance
# ---------------------------------------------------------------------------


class TestNoBackendRoute:
    def test_no_openapi_path_named_for_runtime_governance(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        for path in spec["paths"]:
            lowered = path.lower()
            assert "runtime-governance" not in lowered
            assert "dev-runtime" not in lowered
            assert "plugins/runtime" not in lowered

    def test_candidate_runtime_paths_return_404(self, client: TestClient) -> None:
        for path in CANDIDATE_RUNTIME_PATHS:
            resp = client.get(path)
            assert resp.status_code == 404, f"{path} must not exist (got {resp.status_code})"


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
# 4. The governance projections still freeze the no-side-effect / no-authz
#    invariants (the WebUI mirrors these — they must not have drifted)
# ---------------------------------------------------------------------------


class TestGovernanceProjectionsFrozen:
    def test_side_effect_projection_is_all_false(self) -> None:
        flags = side_effect_projection()
        assert flags and all(v is False for v in flags.values())
        # assert_no_side_effect_surface re-affirms every frozen boundary flag.
        asserted = assert_no_side_effect_surface()
        assert asserted == flags

    def test_authorization_projection_is_all_no_go(self) -> None:
        authz = authorization_projection()
        for key, value in authz.items():
            if key == "realApiKeyRead":
                assert value is False
            else:
                assert value in {"NO-GO", "NOT_AUTHORIZED"}, (key, value)

    def test_p0_report_resolved_count_is_zero(self) -> None:
        report = build_runtime_p0_report()
        assert report["resolvedCount"] == 0
        assert report["totalGates"] == 24
        # The top-level *Authorization key is deliberately redacted by the
        # conservative redactor (its key name carries an authorization stem);
        # the report surfaces the verdict via the value-preserving *Gate keys
        # in the dedicated authorization block.
        assert report["implementationAuthorization"] == "[REDACTED]"
        authz = report["authorization"]
        assert authz["implementationGate"] == "NO-GO"
        assert authz["phase3iProductionGate"] == "NOT_AUTHORIZED"
        assert authz["productionRuntimeGate"] == "NO-GO"
        assert authz["newRouteGate"] == "NO-GO"
        assert authz["productionRolloutGate"] == "NO-GO"
        # The non-secret-stem top-level verdicts survive redaction.
        assert report["realRuntime"] == "NO-GO"
        assert report["newRoute"] == "NO-GO"
        assert report["productionRollout"] == "NO-GO"

    def test_descriptor_list_reports_six_reviewed_fixtures_none_executable(self) -> None:
        listing = list_runtime_descriptors()
        assert listing["count"] == 6
        assert listing["anyExecutable"] is False
        assert listing["anyRemote"] is False
        assert listing["anyMarketplace"] is False
        assert listing["anyProduction"] is False
        assert listing["anyRouteChange"] is False
        for entry in listing["descriptors"]:
            assert entry["devOnly"] is True
            assert entry["fixtureOnly"] is True
            assert entry["reviewedFixture"] is True
            assert entry["executable"] is False
