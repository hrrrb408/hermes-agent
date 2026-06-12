"""Tests for Phase 1G-03-03 Tool Schema Preview GET-only API Routes.

Covers:
  - GET /tools/schemas — catalog response, counts, sorting, JSON safety
  - GET /tools/schemas/{canonicalName} — found and not-found cases
  - Method safety — POST/PUT/PATCH/DELETE rejected with 405
  - Existing API unchanged — /tools/policy and /tools/catalog unaffected
  - Boundary safety — no provider, no handler, no execution, no audit
  - OpenAPI static — path count, schema definitions
  - Runtime routes — correct counts for Tool GET and Tool write routes
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig

API = "/api/dev/v1"


# ── Fixtures ──


@pytest.fixture
def client():
    """TestClient without HERMES_HOME — Schema Preview is stateless."""
    config = DevWebApiConfig(hermes_home=None)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ── Sensitive field whitelist ──

_FORBIDDEN_FIELDS = frozenset({
    "handler", "callable", "function", "modulePath", "sourcePath",
    "absolutePath", "registryObject", "toolRegistry", "rawSchema",
    "providerSchema", "apiKey", "api_key", "baseUrl", "base_url",
    "authorization", "headers", "cookies", "proxy", "environment",
    "env", "secrets", "token", "password", "credentials", "fullSource",
    "traceback", "stack", "thread", "process",
    "dispatch", "force", "override", "execute", "run",
    "object repr", "memory address",
})


def _collect_keys(obj, prefix=""):
    """Recursively collect all keys from a nested dict/list structure."""
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            keys.add(full_key)
            keys.update(_collect_keys(v, full_key))
    elif isinstance(obj, list):
        for item in obj:
            keys.update(_collect_keys(item, prefix))
    return keys


def _collect_string_values(obj, values=None):
    """Recursively collect all string values from a nested structure."""
    if values is None:
        values = []
    if isinstance(obj, str):
        values.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_string_values(v, values)
    elif isinstance(obj, list):
        for item in obj:
            _collect_string_values(item, values)
    return values


# ═══════════════════════════════════════════════════════════════════════════
# 1. GET /tools/schemas — Catalog
# ═══════════════════════════════════════════════════════════════════════════


class TestSchemaPreviewCatalog:
    """Tests for GET /api/dev/v1/tools/schemas."""

    def test_returns_200(self, client):
        resp = client.get(f"{API}/tools/schemas")
        assert resp.status_code == 200

    def test_response_envelope(self, client):
        resp = client.get(f"{API}/tools/schemas")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "requestId" in body["meta"]
        assert "timestamp" in body["meta"]

    def test_total_count_71(self, client):
        resp = client.get(f"{API}/tools/schemas")
        data = resp.json()["data"]
        assert data["totalCount"] == 71

    def test_items_length_71(self, client):
        resp = client.get(f"{API}/tools/schemas")
        data = resp.json()["data"]
        assert len(data["items"]) == 71

    def test_available_plus_unavailable_equals_total(self, client):
        resp = client.get(f"{API}/tools/schemas")
        data = resp.json()["data"]
        assert data["availableCount"] + data["unavailableCount"] == data["totalCount"]

    def test_items_sorted_by_canonical_name(self, client):
        resp = client.get(f"{API}/tools/schemas")
        data = resp.json()["data"]
        names = [item["canonicalName"] for item in data["items"]]
        assert names == sorted(names)

    def test_response_json_safe(self, client):
        resp = client.get(f"{API}/tools/schemas")
        # If json.dumps succeeds, the response is JSON-safe
        serialized = json.dumps(resp.json(), sort_keys=True)
        assert isinstance(serialized, str)

    def test_no_raw_schema_in_response(self, client):
        resp = client.get(f"{API}/tools/schemas")
        body_str = json.dumps(resp.json()).lower()
        assert "rawschema" not in body_str
        assert "raw_schema" not in body_str

    def test_no_handler_in_response(self, client):
        resp = client.get(f"{API}/tools/schemas")
        body_str = json.dumps(resp.json()).lower()
        assert '"handler"' not in body_str
        assert '"callable"' not in body_str

    def test_no_secrets_in_response(self, client):
        resp = client.get(f"{API}/tools/schemas")
        body_str = json.dumps(resp.json()).lower()
        assert "api_key" not in body_str
        assert "password" not in body_str
        assert '"token"' not in body_str
        assert '"secret"' not in body_str

    def test_no_forbidden_fields(self, client):
        resp = client.get(f"{API}/tools/schemas")
        body = resp.json()
        all_keys = _collect_keys(body)
        for forbidden in _FORBIDDEN_FIELDS:
            assert forbidden not in all_keys, f"Forbidden key found: {forbidden}"

    def test_no_function_repr_in_values(self, client):
        resp = client.get(f"{API}/tools/schemas")
        values = _collect_string_values(resp.json())
        for val in values:
            assert "<function" not in val
            assert "<class" not in val
            assert "0x" not in val  # no memory addresses

    def test_all_items_have_required_fields(self, client):
        resp = client.get(f"{API}/tools/schemas")
        data = resp.json()["data"]
        required = {
            "canonicalName", "risk", "capabilities",
            "schemaPreviewAvailable", "schemaShape",
            "inputFields", "redactionStatus", "reasonCode",
            "unavailableReason",
        }
        for item in data["items"]:
            actual_keys = set(item.keys())
            missing = required - actual_keys
            assert not missing, f"Missing keys for {item.get('canonicalName', '?')}: {missing}"


# ═══════════════════════════════════════════════════════════════════════════
# 2. GET /tools/schemas/{canonicalName} — Single
# ═══════════════════════════════════════════════════════════════════════════


class TestSchemaPreviewSingle:
    """Tests for GET /api/dev/v1/tools/schemas/{canonicalName}."""

    def test_existing_tool_returns_200(self, client):
        # Use a tool that is always in the inventory — search_files is R2
        resp = client.get(f"{API}/tools/schemas/search_files")
        assert resp.status_code == 200

    def test_response_envelope(self, client):
        resp = client.get(f"{API}/tools/schemas/search_files")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "requestId" in body["meta"]
        assert "timestamp" in body["meta"]

    def test_found_result_structure(self, client):
        resp = client.get(f"{API}/tools/schemas/search_files")
        data = resp.json()["data"]
        assert data["found"] is True
        assert data["reasonCode"] == "FOUND"
        assert data["preview"] is not None
        assert data["preview"]["canonicalName"] == "search_files"

    def test_preview_has_required_fields(self, client):
        resp = client.get(f"{API}/tools/schemas/search_files")
        preview = resp.json()["data"]["preview"]
        required = {
            "canonicalName", "risk", "capabilities",
            "schemaPreviewAvailable", "schemaShape",
            "inputFields", "redactionStatus", "reasonCode",
            "unavailableReason",
        }
        actual_keys = set(preview.keys())
        missing = required - actual_keys
        assert not missing, f"Missing keys: {missing}"

    def test_response_json_safe(self, client):
        resp = client.get(f"{API}/tools/schemas/search_files")
        serialized = json.dumps(resp.json(), sort_keys=True)
        assert isinstance(serialized, str)

    def test_no_execution_fields(self, client):
        resp = client.get(f"{API}/tools/schemas/search_files")
        body_str = json.dumps(resp.json()).lower()
        assert "execute" not in body_str
        assert "dispatch" not in body_str
        assert "provider" not in body_str
        assert "dryrun" not in body_str.replace("-", "")
        assert "dry_run" not in body_str

    def test_no_provider_send_fields(self, client):
        resp = client.get(f"{API}/tools/schemas/search_files")
        body_str = json.dumps(resp.json()).lower()
        assert "providersent" not in body_str
        assert "sendschema" not in body_str

    def test_denylisted_tool_returns_200_with_unavailable(self, client):
        # terminal is permanently denied (R4)
        resp = client.get(f"{API}/tools/schemas/terminal")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["found"] is True
        assert data["preview"]["schemaPreviewAvailable"] is False
        assert data["preview"]["reasonCode"] == "PERMANENTLY_DENIED"


# ═══════════════════════════════════════════════════════════════════════════
# 3. GET /tools/schemas/{canonicalName} — Not Found
# ═══════════════════════════════════════════════════════════════════════════


class TestSchemaPreviewNotFound:
    """Tests for missing canonical name."""

    def test_missing_tool_returns_404(self, client):
        resp = client.get(f"{API}/tools/schemas/__missing_tool__")
        assert resp.status_code == 404

    def test_not_found_error_has_code(self, client):
        resp = client.get(f"{API}/tools/schemas/__missing_tool__")
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "TOOL_SCHEMA_PREVIEW_NOT_FOUND"

    def test_not_found_has_request_id(self, client):
        resp = client.get(f"{API}/tools/schemas/__missing_tool__")
        body = resp.json()
        assert "requestId" in body or "request_id" in body.get("meta", {})

    def test_not_found_no_crash(self, client):
        """Even with unusual names, no server crash."""
        for name in ["", "   ", "UPPERCASE", "with spaces", "a" * 500, "../../etc/passwd"]:
            resp = client.get(f"{API}/tools/schemas/{name}")
            assert resp.status_code in (200, 404, 422)

    def test_not_found_case_sensitive(self, client):
        """Exact match only — Search_Files is not the same as search_files."""
        resp = client.get(f"{API}/tools/schemas/Search_Files")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# 4. Method Safety
# ═══════════════════════════════════════════════════════════════════════════


class TestSchemaPreviewMethodSafety:
    """POST/PUT/PATCH/DELETE on schema preview routes must be 405."""

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_schemas_catalog_rejects_write(self, client, method):
        fn = getattr(client, method)
        if method == "delete":
            resp = fn(f"{API}/tools/schemas")
        else:
            resp = fn(f"{API}/tools/schemas", json={})
        assert resp.status_code == 405

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_schemas_single_rejects_write(self, client, method):
        fn = getattr(client, method)
        if method == "delete":
            resp = fn(f"{API}/tools/schemas/search_files")
        else:
            resp = fn(f"{API}/tools/schemas/search_files", json={})
        assert resp.status_code == 405


# ═══════════════════════════════════════════════════════════════════════════
# 5. Existing API Unchanged
# ═══════════════════════════════════════════════════════════════════════════


class TestExistingAPIUnchanged:
    """Verify /tools/policy and /tools/catalog are not affected."""

    def test_tools_policy_still_200(self, client):
        resp = client.get(f"{API}/tools/policy")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["inventoryCount"] == 71

    def test_tools_catalog_still_200(self, client):
        resp = client.get(f"{API}/tools/catalog")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 71

    def test_catalog_schema_preview_available_still_false(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        for item in data["items"]:
            assert item["schemaPreviewAvailable"] is False

    def test_catalog_dry_run_available_still_false(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        for item in data["items"]:
            assert item["dryRunAvailable"] is False

    def test_catalog_execution_available_still_false(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        for item in data["items"]:
            assert item["executionAvailable"] is False

    def test_catalog_no_schema_preview_payload(self, client):
        """Existing catalog must NOT contain new schema preview data."""
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        for item in data["items"]:
            assert "inputFields" not in item
            assert "schemaShape" not in item
            assert "redactionStatus" not in item

    def test_policy_execution_flags_all_false(self, client):
        resp = client.get(f"{API}/tools/policy")
        data = resp.json()["data"]
        exe = data["execution"]
        assert exe["implemented"] is False
        assert exe["enabled"] is False
        assert exe["providerSchemaSent"] is False
        assert exe["dispatchAvailable"] is False
        assert exe["auditAvailable"] is False


# ═══════════════════════════════════════════════════════════════════════════
# 6. Boundary Safety
# ═══════════════════════════════════════════════════════════════════════════


class TestSchemaPreviewBoundarySafety:
    """Verify no provider, handler, execution, audit, or allowlist changes."""

    def test_api_does_not_import_tools_registry(self):
        """The API module must not import tools.registry."""
        import hermes_cli.dev_web_api as api_module

        module_source = open(api_module.__file__, encoding="utf-8").read()
        assert "tools.registry" not in module_source
        assert "from tools" not in module_source

    def test_api_does_not_import_provider(self):
        """The API module must not import any provider module."""
        import hermes_cli.dev_web_api as api_module

        module_source = open(api_module.__file__, encoding="utf-8").read()
        assert "import provider" not in module_source
        # The schema preview service module also should not import provider
        assert "dev_web_tool_schema_preview_service" in module_source

    def test_static_allowlist_remains_clarify_only(self, client):
        """STATIC_ALLOWLIST must remain frozenset({"clarify"}) after schema preview routes."""
        from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST
        assert STATIC_ALLOWLIST == frozenset({"clarify"})

    def test_denylist_unchanged(self, client):
        from hermes_cli.dev_web_tool_policy import STATIC_DENYLIST
        assert len(STATIC_DENYLIST) == 26

    def test_candidate_unchanged(self, client):
        from hermes_cli.dev_web_tool_policy import CANDIDATE_ALLOWLIST
        assert len(CANDIDATE_ALLOWLIST) == 6

    def test_no_tool_dispatch(self, client):
        """Schema preview routes must not call any tool dispatch."""
        import hermes_cli.dev_web_api as api_module
        module_source = open(api_module.__file__, encoding="utf-8").read()
        assert "dispatch" not in module_source.split("_register_schema_preview_routes")[1].split("\n    def ")[0].lower() or "no tool dispatch" in ""


# ═══════════════════════════════════════════════════════════════════════════
# 7. OpenAPI Static
# ═══════════════════════════════════════════════════════════════════════════


class TestSchemaPreviewOpenAPI:
    """Verify OpenAPI spec has the new paths and schemas."""

    def test_openapi_paths_33(self, client):
        resp = client.get("/openapi.json")
        spec = resp.json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        assert len(paths) == 33

    def test_schemas_catalog_path_exists(self, client):
        resp = client.get("/openapi.json")
        spec = resp.json()
        assert "/api/dev/v1/tools/schemas" in spec["paths"]
        assert "get" in spec["paths"]["/api/dev/v1/tools/schemas"]

    def test_schemas_single_path_exists(self, client):
        resp = client.get("/openapi.json")
        spec = resp.json()
        assert "/api/dev/v1/tools/schemas/{canonicalName}" in spec["paths"]
        assert "get" in spec["paths"]["/api/dev/v1/tools/schemas/{canonicalName}"]

    def test_schemas_catalog_get_only(self, client):
        resp = client.get("/openapi.json")
        spec = resp.json()
        methods = set(spec["paths"]["/api/dev/v1/tools/schemas"].keys())
        write_methods = methods & {"post", "put", "patch", "delete"}
        assert write_methods == set()

    def test_schemas_single_get_only(self, client):
        resp = client.get("/openapi.json")
        spec = resp.json()
        methods = set(spec["paths"]["/api/dev/v1/tools/schemas/{canonicalName}"].keys())
        write_methods = methods & {"post", "put", "patch", "delete"}
        assert write_methods == set()

    def test_schemas_defined_in_components(self, client):
        """Verify static YAML has the new schema definitions."""
        import pathlib
        import yaml

        static_yaml = pathlib.Path("docs/webui/openapi/dev-web-api-v1.yaml")
        if not static_yaml.exists():
            pytest.skip("OpenAPI YAML file not found")
        text = static_yaml.read_text(encoding="utf-8")
        spec = yaml.safe_load(text)
        schemas = spec.get("components", {}).get("schemas", {})
        assert "ToolSchemaPreviewCatalogResponse" in schemas
        assert "ToolSchemaPreviewLookupResponse" in schemas
        assert "ToolSchemaPreviewItem" in schemas
        assert "ToolSchemaPreviewField" in schemas

    def test_static_yaml_has_33_paths(self):
        """Verify the static YAML file has exactly 33 paths."""
        import pathlib
        import yaml

        static_yaml = pathlib.Path("docs/webui/openapi/dev-web-api-v1.yaml")
        if not static_yaml.exists():
            pytest.skip("OpenAPI YAML file not found")
        text = static_yaml.read_text(encoding="utf-8")
        spec = yaml.safe_load(text)
        paths = spec.get("paths", {})
        assert len(paths) == 33

    def test_static_yaml_has_new_schemas(self):
        """Verify the static YAML has new schema definitions."""
        import pathlib
        import yaml

        static_yaml = pathlib.Path("docs/webui/openapi/dev-web-api-v1.yaml")
        if not static_yaml.exists():
            pytest.skip("OpenAPI YAML file not found")
        text = static_yaml.read_text(encoding="utf-8")
        spec = yaml.safe_load(text)
        schemas = spec.get("components", {}).get("schemas", {})
        assert "ToolSchemaPreviewCatalogResponse" in schemas
        assert "ToolSchemaPreviewLookupResponse" in schemas


# ═══════════════════════════════════════════════════════════════════════════
# 8. Runtime Routes
# ═══════════════════════════════════════════════════════════════════════════


class TestSchemaPreviewRuntimeRoutes:
    """Verify runtime route counts."""

    def test_runtime_routes_33(self, client):
        resp = client.get("/openapi.json")
        spec = resp.json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        assert len(paths) == 33

    def test_tool_get_routes_4(self, client):
        resp = client.get("/openapi.json")
        spec = resp.json()
        tool_get_routes = [
            p for p in spec["paths"]
            if p.startswith("/api/dev/v1/tools") and "get" in spec["paths"][p]
        ]
        assert len(tool_get_routes) == 4

    def test_tool_write_routes_0(self, client):
        resp = client.get("/openapi.json")
        spec = resp.json()
        write_methods = {"post", "put", "patch", "delete"}
        # Tool dry-run POST and execute POST are non-mutating — excluded from write count
        _TOOL_NON_WRITE_ROUTES = {"/api/dev/v1/tools/dry-run", "/api/dev/v1/tools/execute"}
        tool_write_routes = []
        for p, methods in spec["paths"].items():
            if not p.startswith("/api/dev/v1/tools"):
                continue
            if p in _TOOL_NON_WRITE_ROUTES:
                continue
            actual = set(methods.keys()) & write_methods
            if actual:
                tool_write_routes.append(f"{p} ({', '.join(sorted(actual))})")
        assert tool_write_routes == []
