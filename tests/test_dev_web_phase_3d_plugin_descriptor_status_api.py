"""Phase 3D — Plugin Descriptor Registry /status integration tests.

Verifies the ``pluginDescriptorRegistry`` block is present under ``/status``
data, carries every frozen policy flag, is value-free (no leak), asserts the
route-governance baseline is unchanged, and that no new HTTP route was
introduced (OpenAPI + runtime business routes stay at 34).

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest
from hermes_cli.dev_web_plugin_descriptor_registry import (
    get_plugin_descriptor_status_block,
    list_descriptor_details,
)

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
    "installCommand",
    "localPath",
    "remoteUrl",
    "bearer",
)


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    app = create_dev_web_api_app(cfg)
    return TestClient(app)


class TestStatusBlock:
    def test_status_includes_plugin_descriptor_registry(self, client: TestClient) -> None:
        resp = client.get("/api/dev/v1/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "pluginDescriptorRegistry" in data
        pdr = data["pluginDescriptorRegistry"]
        assert pdr["status"] in {"enabled", "validation_failed"}
        assert pdr["registryVersion"] == "phase3d-static-descriptor-v1"
        assert pdr["descriptorCount"] == len(get_static_manifest())

    def test_all_runtime_disabled_flags_false(self, client: TestClient) -> None:
        pdr = client.get("/api/dev/v1/status").json()["data"]["pluginDescriptorRegistry"]
        assert pdr["pluginRuntimeImplemented"] is False
        assert pdr["pluginLoaderImplemented"] is False
        assert pdr["dynamicLoadingAllowed"] is False
        assert pdr["localPluginDirectoryLoadingAllowed"] is False
        assert pdr["remoteRegistryAllowed"] is False
        assert pdr["marketplaceAllowed"] is False
        assert pdr["externalPluginFetchAllowed"] is False
        assert pdr["providerGeneratedPluginAllowed"] is False
        assert pdr["llmGeneratedPluginInstallAllowed"] is False
        assert pdr["pluginExecutionAllowed"] is False
        assert pdr["newRouteIntroduced"] is False
        assert pdr["productionAllowed"] is False
        assert pdr["devOnly"] is True
        assert pdr["redactionApplied"] is True

    def test_route_governance_baseline_unchanged(self, client: TestClient) -> None:
        pdr = client.get("/api/dev/v1/status").json()["data"]["pluginDescriptorRegistry"]
        assert pdr["routeGovernanceExpected"] == "34/34/5/0/1/1"

    def test_validation_passed(self, client: TestClient) -> None:
        pdr = client.get("/api/dev/v1/status").json()["data"]["pluginDescriptorRegistry"]
        assert pdr["validation"]["valid"] is True
        assert pdr["validation"]["errorCount"] == 0
        assert pdr["status"] == "enabled"

    def test_counts_partition_descriptors(self, client: TestClient) -> None:
        pdr = client.get("/api/dev/v1/status").json()["data"]["pluginDescriptorRegistry"]
        assert pdr["descriptorCount"] == 12
        assert pdr["visibleCount"] == 3
        assert pdr["disabledCount"] == 4
        assert pdr["blockedCount"] == 5


class TestStatusBlockNoLeak:
    def test_status_block_is_value_free(self, client: TestClient) -> None:
        pdr = client.get("/api/dev/v1/status").json()["data"]["pluginDescriptorRegistry"]
        blob = json_blob(pdr)
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob, f"forbidden token {token} in /status block"
        assert "/Users/huangruibang/.hermes" not in blob
        assert "state.db" not in blob

    def test_full_status_payload_no_plugin_secret_leak(self, client: TestClient) -> None:
        blob = json_blob(client.get("/api/dev/v1/status").json()["data"]["pluginDescriptorRegistry"])
        assert "OPENAI_API_KEY" not in blob
        assert "sk-" not in blob


class TestDirectBlockHelper:
    def test_get_block_helper_matches_endpoint(self, client: TestClient) -> None:
        direct = get_plugin_descriptor_status_block()
        via_api = client.get("/api/dev/v1/status").json()["data"]["pluginDescriptorRegistry"]
        assert direct == via_api

    def test_detail_list_safe(self) -> None:
        details = list_descriptor_details(get_static_manifest())
        blob = json_blob(details)
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob
        # capabilityBindings surfaced as plain ids (no execution surface).
        assert any("registry.capability_registry_status" in str(d) for d in details)


class TestNoNewRoute:
    def test_no_plugin_descriptor_http_route(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        # No new route introduced by Phase 3D (baseline 34 business paths).
        assert len(paths) == 34
        for path in paths:
            lower = path.lower()
            assert "descriptor" not in lower
            assert "/plugin" not in lower


def json_blob(obj: object) -> str:
    import json

    return json.dumps(obj)
