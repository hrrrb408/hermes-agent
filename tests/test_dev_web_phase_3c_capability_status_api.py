"""Phase 3C — Capability Registry /status integration tests.

Verifies the ``capabilityRegistry`` block is present under ``/status`` data,
carries the frozen policy flags, is value-free (no leak), and that no new HTTP
route was introduced (runtime business routes stay at 34).

Phase: 3C — Static dev-only Capability Registry
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app, DevWebApiConfig
from hermes_cli.dev_web_capability_registry import (
    get_registry_status_block,
    list_capability_details,
)
from hermes_cli.dev_web_capability_registry_manifest import get_static_manifest

_FORBIDDEN_TOKENS = (
    "apiKey",
    "Authorization",
    "Bearer",
    "shellCommand",
    "pythonImportPath",
    "externalUrl",
    "downloadUrl",
    "pluginPackage",
    "dynamicModule",
    "evalCode",
    "execCode",
    "sqlStatement",
    "productionPath",
    "callable",
    "secret",
)


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    app = create_dev_web_api_app(cfg)
    return TestClient(app)


class TestStatusBlock:
    def test_status_includes_capability_registry(self, client: TestClient) -> None:
        resp = client.get("/api/dev/v1/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "capabilityRegistry" in data
        cr = data["capabilityRegistry"]
        assert cr["status"] in {"enabled", "validation_failed"}
        assert cr["registryVersion"] == "phase3c-static-v1"
        assert cr["capabilityCount"] == len(get_static_manifest())

    def test_frozen_policy_flags(self, client: TestClient) -> None:
        cr = client.get("/api/dev/v1/status").json()["data"]["capabilityRegistry"]
        assert cr["devOnly"] is True
        assert cr["productionAllowed"] is False
        assert cr["dynamicLoadingAllowed"] is False
        assert cr["remoteRegistryAllowed"] is False
        assert cr["marketplaceAllowed"] is False
        assert cr["redactionApplied"] is True

    def test_route_governance_string(self, client: TestClient) -> None:
        cr = client.get("/api/dev/v1/status").json()["data"]["capabilityRegistry"]
        assert cr["routeGovernanceExpected"] == "34/34/5/0/1/1"

    def test_validation_block(self, client: TestClient) -> None:
        cr = client.get("/api/dev/v1/status").json()["data"]["capabilityRegistry"]
        v = cr["validation"]
        assert v["valid"] is True
        assert v["errorCount"] == 0

    def test_counts_present(self, client: TestClient) -> None:
        cr = client.get("/api/dev/v1/status").json()["data"]["capabilityRegistry"]
        for key in (
            "enabledCount",
            "disabledCount",
            "blockedCount",
            "plannedCount",
            "deprecatedCount",
            "permissionClassCounts",
            "trustLevelCounts",
            "categoryCounts",
        ):
            assert key in cr
        assert cr["enabledCount"] + cr["disabledCount"] + cr["blockedCount"] <= cr["capabilityCount"]


class TestNoLeak:
    def test_status_block_no_forbidden_tokens(self, client: TestClient) -> None:
        cr = client.get("/api/dev/v1/status").json()["data"]["capabilityRegistry"]
        blob = json.dumps(cr)
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob, f"forbidden token {token!r} leaked into capabilityRegistry"

    def test_detail_list_no_forbidden_tokens(self) -> None:
        blob = json.dumps(list_capability_details(get_static_manifest()))
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob, f"forbidden token {token!r} leaked into a detail"

    def test_get_registry_status_block_no_leak(self) -> None:
        blob = json.dumps(get_registry_status_block())
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob


class TestRouteGovernance:
    def test_runtime_business_routes_unchanged(self, client: TestClient) -> None:
        app = client.app
        paths = {
            getattr(r, "path", None)
            for r in app.routes
            if getattr(r, "path", "").startswith("/api/dev/v1/")
        }
        # Frozen baseline: 34 business paths under the API prefix.
        assert len(paths) == 34

    def test_no_capability_specific_route(self, client: TestClient) -> None:
        paths = {getattr(r, "path", "") for r in client.app.routes}
        assert not any("capability" in p.lower() for p in paths), (
            "Phase 3C must not introduce a capability HTTP route"
        )

    def test_status_route_is_get_only(self, client: TestClient) -> None:
        route = next(r for r in client.app.routes if getattr(r, "path", "") == "/api/dev/v1/status")
        methods = {m.lower() for m in getattr(route, "methods", set())}
        assert methods == {"get"}
