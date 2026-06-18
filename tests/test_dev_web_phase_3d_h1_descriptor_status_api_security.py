"""Phase 3D-H1 — /status pluginDescriptorRegistry API / route governance.

Hardens Lens 10: the ``pluginDescriptorRegistry`` block surfaced under ``/status``
is read-only and value-free, carries every frozen policy flag set to its locked
value, surfaces the validation summary + descriptor counts, leaks no forbidden
token, and the route-governance baseline is unchanged (OpenAPI + runtime
business routes stay at 34; no plugin / descriptor HTTP route; Tool GET=5 /
write=0 / dry-run=1 / execution=1).

Phase: 3D-H1 — Static Plugin Descriptor Registry Hardening
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_plugin_descriptor_registry import get_plugin_descriptor_status_block

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
)

_FROZEN_FALSE_FLAGS = (
    "pluginRuntimeImplemented",
    "pluginLoaderImplemented",
    "dynamicLoadingAllowed",
    "localPluginDirectoryLoadingAllowed",
    "remoteRegistryAllowed",
    "marketplaceAllowed",
    "externalPluginFetchAllowed",
    "providerGeneratedPluginAllowed",
    "llmGeneratedPluginInstallAllowed",
    "pluginExecutionAllowed",
    "newRouteIntroduced",
    "productionAllowed",
)


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    app = create_dev_web_api_app(cfg)
    return TestClient(app)


def _status_block(client: TestClient) -> dict:
    return client.get("/api/dev/v1/status").json()["data"]["pluginDescriptorRegistry"]


class TestStatusBlockPresent:
    def test_status_includes_plugin_descriptor_registry(self, client: TestClient) -> None:
        block = _status_block(client)
        assert block is not None
        assert isinstance(block, dict)

    def test_status_block_matches_direct_accessor(self, client: TestClient) -> None:
        # The /status block must equal the registry's own accessor (no drift).
        assert _status_block(client) == get_plugin_descriptor_status_block()


class TestFrozenFlags:
    @pytest.mark.parametrize("flag", _FROZEN_FALSE_FLAGS)
    def test_flag_is_false(self, client: TestClient, flag: str) -> None:
        assert _status_block(client)[flag] is False

    def test_dev_only_is_true(self, client: TestClient) -> None:
        assert _status_block(client)["devOnly"] is True

    def test_redaction_applied_is_true(self, client: TestClient) -> None:
        assert _status_block(client)["redactionApplied"] is True

    def test_status_is_enabled(self, client: TestClient) -> None:
        block = _status_block(client)
        assert block["status"] == "enabled"


class TestValidationSummaryAndCounts:
    def test_validation_summary_present(self, client: TestClient) -> None:
        validation = _status_block(client)["validation"]
        assert validation["valid"] is True
        assert validation["errorCount"] == 0

    def test_descriptor_counts_present(self, client: TestClient) -> None:
        block = _status_block(client)
        assert block["descriptorCount"] == 12
        assert block["visibleCount"] == 3
        assert block["disabledCount"] == 4
        assert block["blockedCount"] == 5

    def test_route_governance_expected_string(self, client: TestClient) -> None:
        assert _status_block(client)["routeGovernanceExpected"] == "34/34/5/0/1/1"


class TestNoLeak:
    def test_status_block_value_free(self, client: TestClient) -> None:
        blob = json.dumps(_status_block(client))
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob
        assert "/Users/huangruibang/.hermes" not in blob
        assert "state.db" not in blob
        assert "OPENAI_API_KEY" not in blob

    def test_full_status_response_value_free(self, client: TestClient) -> None:
        blob = json.dumps(client.get("/api/dev/v1/status").json())
        assert "OPENAI_API_KEY" not in blob
        assert "sk-" not in blob


class TestRouteGovernance:
    def test_openapi_path_count_unchanged(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        # Frozen baseline: 34 OpenAPI business paths. Phase 3D-H1 adds none.
        assert len(paths) == 34

    def test_no_plugin_descriptor_route_introduced(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        for path in spec.get("paths", {}):
            lower = path.lower()
            assert "descriptor" not in lower
            assert "/plugin" not in lower

    def test_runtime_business_routes_unchanged(self, client: TestClient) -> None:
        app = create_dev_web_api_app(
            DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=Path("/tmp/_h1_unused"))
        )
        runtime = {
            getattr(r, "path", "")
            for r in app.routes
            if getattr(r, "path", "").startswith("/api/dev/v1/")
        }
        assert len(runtime) == 34
