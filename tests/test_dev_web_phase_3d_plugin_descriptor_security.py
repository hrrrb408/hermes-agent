"""Phase 3D — Plugin Descriptor Registry security / boundary tests.

Verifies the registry cannot grant permission, cannot create an approval /
confirmation / dry-run / route / execution path, the read model never leaks a
forbidden value, no production home / state.db access is referenced, and the
route-governance baseline is preserved (OpenAPI + runtime business routes stay
at 34).

Phase: 3D — Static dev-only Plugin Descriptor Registry (skeleton)
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli import dev_web_plugin_descriptor_registry as registry_mod
from hermes_cli.dev_web_api import DevWebApiConfig, create_dev_web_api_app
from hermes_cli.dev_web_plugin_descriptor_registry import (
    get_plugin_descriptor_status_block,
    list_descriptor_details,
)
from hermes_cli.dev_web_plugin_descriptor_manifest import get_static_manifest

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


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
    app = create_dev_web_api_app(cfg)
    return TestClient(app)


class TestNonGrant:
    def test_registry_module_has_no_permission_granting_api(self) -> None:
        for forbidden_attr in (
            "grant_permission",
            "approve",
            "create_approval",
            "create_confirmation_token",
            "create_dry_run",
            "create_route",
            "execute",
            "load_plugin",
            "install_plugin",
            "enable_plugin",
        ):
            assert not hasattr(registry_mod, forbidden_attr), f"unexpected grant API: {forbidden_attr}"

    def test_descriptors_do_not_grant_permission(self) -> None:
        # A descriptor is descriptive; permissionClass is a label inherited from
        # bound capabilities, never a grant. No descriptor carries a field that
        # would grant anything.
        for entry in get_static_manifest():
            assert entry["devOnly"] is True
            assert entry["productionAllowed"] is False
            assert entry["disabledByDefault"] is True
            assert entry["executionMode"] == "descriptor_only"


class TestReadModelNoLeak:
    def test_status_block_value_free(self) -> None:
        blob = json_blob(get_plugin_descriptor_status_block())
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob
        assert "/Users/huangruibang/.hermes" not in blob
        assert "state.db" not in blob

    def test_detail_list_value_free(self) -> None:
        blob = json_blob(list_descriptor_details(get_static_manifest()))
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob

    def test_endpoint_status_value_free(self, client: TestClient) -> None:
        blob = json_blob(client.get("/api/dev/v1/status").json()["data"]["pluginDescriptorRegistry"])
        for token in _FORBIDDEN_TOKENS:
            assert token not in blob
        assert "OPENAI_API_KEY" not in blob


class TestRouteGovernancePreserved:
    def test_openapi_path_count_unchanged(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        # The frozen baseline: 34 OpenAPI business paths. Phase 3D adds none.
        assert len(paths) == 34

    def test_no_plugin_descriptor_route_introduced(self, client: TestClient) -> None:
        spec = client.get("/openapi.json").json()
        for path in spec.get("paths", {}):
            lower = path.lower()
            assert "descriptor" not in lower
            assert "/plugin" not in lower


class TestNoProductionAccess:
    def test_source_references_no_production_home(self) -> None:
        src = Path(inspect.getsourcefile(registry_mod)).read_text(encoding="utf-8")
        assert "/Users/huangruibang/.hermes" not in src
        assert "state.db" not in src

    def test_bindings_only_reference_phase_3c_static_ids(self) -> None:
        # Security: every binding must be a known Phase 3C capabilityId (no
        # arbitrary / production path smuggled in as a "binding").
        from hermes_cli.dev_web_capability_registry_manifest import get_static_manifest as cap_manifest

        valid = {e["capabilityId"] for e in cap_manifest()}
        for entry in get_static_manifest():
            for cid in entry["capabilityBindings"]:
                assert cid in valid


def json_blob(obj: object) -> str:
    import json

    return json.dumps(obj)
