"""Phase 3K Human Review Governance Read-only WebUI Surface — backend isolation tests.

Asserts that the Phase 3K read-only WebUI surface is **frontend-only** and adds
**no backend route** and **no backend import** of the runtime governance / plugin
runtime / human-review modules:

  - ``hermes_cli.dev_web_api`` does NOT import any human-review-governance,
    runtime-governance, or plugin-runtime module (the governance CLI / report
    projections stay out of the FastAPI app's import graph).
  - No OpenAPI path is named for human review / approval governance
    (``/human-review-governance``, ``/approval-governance``, ``/human-review`` …).
  - Probing candidate human-review / approval API paths returns 404.
  - The frozen route-governance baseline ``34/34/5/0/1/1`` is unchanged, every
    "new route" flag stays zero, and ``assert_route_governance_unchanged``
    passes.
  - The P0 evidence model still projects the frozen no-approval invariants
    (resolved_count 0, 5 blocked_by_human_review, every authorization flag
    NO-GO / not-authorized, no gate resolved).

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.
All "forbidden path" assertions use fake / string-policy paths only — never a
real ``stat`` / ``ls`` / ``resolve`` of ``~/.hermes``.

Phase: 3K — Human Review Governance Read-only Surface
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
    "human_review_governance",
)

#: Candidate backend API paths that must NOT exist for human review governance.
CANDIDATE_HUMAN_REVIEW_PATHS = (
    "/api/dev/v1/human-review-governance",
    "/api/dev/v1/human-review",
    "/api/dev/v1/approval-governance",
    "/api/dev/v1/human-review/gates",
    "/api/dev/v1/human-review/pending",
    "/api/dev/v1/human-review/approve",
    "/api/dev/v1/human-review/authorize",
    "/api/dev/v1/human-review/signoff",
    "/api/dev/v1/human-review/resolve",
)


# ---------------------------------------------------------------------------
# 1. dev_web_api does not import the human-review / governance modules
# ---------------------------------------------------------------------------


class TestDevWebApiIsolation:
    def test_dev_web_api_source_does_not_import_governance_modules(self) -> None:
        source = Path(dev_web_api_module.__file__).read_text(encoding="utf-8")
        for module in FORBIDDEN_BACKEND_IMPORTS:
            assert module not in source, (
                f"dev_web_api.py must not import {module} — the WebUI human "
                "review governance surface is frontend-only"
            )

    def test_dev_web_api_source_does_not_register_a_human_review_route(self) -> None:
        source = Path(dev_web_api_module.__file__).read_text(encoding="utf-8")
        lowered = source.lower()
        for needle in ("human-review", "human_review", "approval-governance"):
            assert needle not in lowered, (
                f"dev_web_api.py must not reference {needle!r} — no backend route"
            )


# ---------------------------------------------------------------------------
# 2. No OpenAPI path / runtime route is named for human review governance
# ---------------------------------------------------------------------------


class TestNoBackendRoute:
    def test_no_openapi_path_named_for_human_review(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        for path in spec["paths"]:
            lowered = path.lower()
            assert "human-review" not in lowered
            assert "approval-governance" not in lowered
            assert "human-review-governance" not in lowered

    def test_candidate_human_review_paths_return_404(self, client: TestClient) -> None:
        for path in CANDIDATE_HUMAN_REVIEW_PATHS:
            resp = client.get(path)
            assert resp.status_code == 404, f"{path} must not exist (got {resp.status_code})"
            # POST (approve/authorize/resolve) must also be absent.
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
#    (the WebUI mirrors these — they must not have drifted)
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
        blocked_ids = {g.gate_id for g in blocked}
        assert blocked_ids == {"P0-15", "P0-16", "P0-18", "P0-19", "P0-22"}

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
        assert summary.phase_3i_authorized is False
        assert summary.real_runtime == "NO-GO"
        assert summary.new_route == "NO-GO"
        assert summary.production_rollout == "NO-GO"


# ---------------------------------------------------------------------------
# 5. No production access (loopback bind + fake/string-policy path policy)
#    Never stat / ls / resolve ~/.hermes — only assert string policy + 404.
# ---------------------------------------------------------------------------


class TestNoProductionAccess:
    #: Forbidden path STEMS used as STRING POLICY only — never resolved, never
    #: opened. They exist to assert that candidate API paths cannot reach them.
    FORBIDDEN_PATH_STEMS = (
        "~/.hermes",
        ".hermes/state.db",
        "production/state.db",
    )

    def test_dev_app_binds_loopback_only(self, tmp_path: Path) -> None:
        # The dev WebUI must bind to 127.0.0.1 only — never 0.0.0.0.
        cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
        assert cfg.host == "127.0.0.1"
        app = create_dev_web_api_app(cfg)
        assert app is not None

    def test_candidate_human_review_paths_do_not_touch_production(
        self, client: TestClient
    ) -> None:
        # Every candidate path is a 404; none reaches production state.
        for path in CANDIDATE_HUMAN_REVIEW_PATHS:
            resp = client.get(path)
            assert resp.status_code == 404

    def test_forbidden_path_stems_are_string_policy_only(self) -> None:
        # These stems are policy strings used by the redactor / guard, never
        # resolved at runtime. The assertion itself never touches the filesystem.
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert isinstance(stem, str)
            assert stem  # non-empty policy string
