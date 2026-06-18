"""Phase 3C-H1 — /status CapabilityRegistry API / Route Governance Hardening.

Hardens ``CAP-STATUS-API-3C-H1-001`` (Lens 10).

The Capability Registry is exposed ONLY through the existing ``GET /status``
response under ``data.capabilityRegistry``. This test proves:

  - the block exists and is value-free (no secret / callable / shell / SQL /
    production path / plugin path / dynamic import path),
  - the frozen policy flags hold (dynamicLoadingAllowed /
    remoteRegistryAllowed / marketplaceAllowed / productionAllowed = false;
    devOnly = true; redactionApplied = true),
  - route governance is unchanged: OpenAPI path count is the frozen baseline
    and NO new capability HTTP route was introduced.

Phase: 3C-H1 — Static Capability Registry Hardening
Status: implemented
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_capability_registry import ROUTE_GOVERNANCE_EXPECTED

#: Frozen route-governance baseline (OpenAPI paths / runtime / GET / write / dry-run / execute).
EXPECTED_OPENAPI_PATHS = 34

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
    "/Users/huangruibang/.hermes",
    "state.db",
)


def _client(tmp_path: Path) -> TestClient:
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    return TestClient(create_dev_web_api_app(cfg))


def _status(client: TestClient) -> dict:
    resp = client.get("/api/dev/v1/status")
    assert resp.status_code == 200
    return resp.json()["data"]["capabilityRegistry"]


def _openapi_paths(client: TestClient) -> dict:
    # FastAPI serves OpenAPI at /openapi.json (the app is not prefix-mounted).
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    return resp.json().get("paths", {})


class TestStatusBlockPresent:
    def test_capability_registry_block_exists(self, tmp_path: Path) -> None:
        cr = _status(_client(tmp_path))
        assert cr is not None
        assert cr["registryVersion"] == "phase3c-static-v1"

    def test_capability_count_is_46(self, tmp_path: Path) -> None:
        cr = _status(_client(tmp_path))
        assert cr["capabilityCount"] == 46

    def test_counts_partition_total(self, tmp_path: Path) -> None:
        cr = _status(_client(tmp_path))
        total = (
            cr["enabledCount"]
            + cr["disabledCount"]
            + cr["blockedCount"]
            + cr["plannedCount"]
            + cr["deprecatedCount"]
        )
        assert total == cr["capabilityCount"]

    def test_route_governance_baseline_surfaces(self, tmp_path: Path) -> None:
        cr = _status(_client(tmp_path))
        assert cr["routeGovernanceExpected"] == ROUTE_GOVERNANCE_EXPECTED == "34/34/5/0/1/1"


class TestFrozenPolicyFlags:
    def test_no_dynamic_remote_marketplace_production(self, tmp_path: Path) -> None:
        cr = _status(_client(tmp_path))
        assert cr["dynamicLoadingAllowed"] is False
        assert cr["remoteRegistryAllowed"] is False
        assert cr["marketplaceAllowed"] is False
        assert cr["productionAllowed"] is False
        assert cr["devOnly"] is True
        assert cr["redactionApplied"] is True

    def test_validation_passed(self, tmp_path: Path) -> None:
        cr = _status(_client(tmp_path))
        assert cr["validation"]["valid"] is True
        assert cr["validation"]["errorCount"] == 0
        assert cr["status"] == "enabled"
        assert cr["loaded"] is True


class TestStatusBlockNoLeak:
    def test_status_block_value_free(self, tmp_path: Path) -> None:
        cr = _status(_client(tmp_path))
        blob = json.dumps(cr)
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob, f"forbidden token {token!r} in /status capabilityRegistry"

    def test_status_block_no_capability_secret_or_callable(self, tmp_path: Path) -> None:
        cr = _status(_client(tmp_path))
        blob = json.dumps(cr)
        for token in ("<function", "<bound method", "sk-", "Bearer "):
            assert token not in blob

    def test_full_status_data_no_capability_route_leak(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        data = client.get("/api/dev/v1/status").json()["data"]
        blob = json.dumps(data.get("capabilityRegistry", {}))
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob


class TestRouteGovernanceUnchanged:
    def test_openapi_path_count_frozen(self, tmp_path: Path) -> None:
        paths = _openapi_paths(_client(tmp_path))
        assert len(paths) == EXPECTED_OPENAPI_PATHS

    def test_no_capability_http_route(self, tmp_path: Path) -> None:
        paths = _openapi_paths(_client(tmp_path))
        for path in paths:
            assert "capabilit" not in path.lower(), f"new capability route: {path}"

    def test_no_registry_http_route(self, tmp_path: Path) -> None:
        paths = _openapi_paths(_client(tmp_path))
        for path in paths:
            assert not path.lower().endswith("/registry"), f"new registry route: {path}"
            assert "/capability-registry" not in path.lower()
