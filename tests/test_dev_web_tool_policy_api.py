"""Tests for Phase 1G-02B Tool Policy Read-Only API Routes.

Covers:
  - GET /tools/policy — status, counts, execution flags, safety, limits, DTO whitelist
  - GET /tools/catalog — default response, query params, pagination, sorting, errors
  - Error mapping — invalid params, dangerous params, error codes
  - Route boundary — only 2 GET routes, no write routes
  - Side effects — no state.db, memory, review changes
  - Service delegation — route only calls service, does not duplicate logic
  - Provider / Registry / Dispatch — none initialized during API calls
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_tool_policy_service import (
    DevToolPolicyQueryService,
    validate_catalog_query,
    InvalidToolPolicyQueryError,
    ToolPolicyQueryError,
)

API = "/api/dev/v1"


# ── Fixtures ──


@pytest.fixture
def client():
    """TestClient without HERMES_HOME — Tool Policy works without it."""
    config = DevWebApiConfig(hermes_home=None)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def client_with_home(tmp_path):
    """TestClient with a minimal HERMES_HOME for side-effect tests."""
    home = tmp_path / "hermes-home"
    home.mkdir()
    (home / "state.db").touch()
    (home / "memory" / "indexes").mkdir(parents=True)
    (home / "memory" / "records").mkdir(parents=True)
    (home / "memory" / "snapshots").mkdir(parents=True)
    (home / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (home / "MEMORY.md").write_text(
        "# Memory Root\n\n## test\n\n- index: memory://indexes/test.md\n"
        "- scope: test\n- priority: P1\n- status: active\n- keywords: test\n"
        "- description: test\n",
        encoding="utf-8",
    )
    config = DevWebApiConfig(hermes_home=home)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ── Sensitive field whitelist ──

_FORBIDDEN_FIELDS = frozenset({
    "handler", "callable", "function", "modulePath", "sourcePath",
    "absolutePath", "registryObject", "toolRegistry", "toolSchema",
    "providerSchema", "apiKey", "api_key", "baseUrl", "base_url",
    "authorization", "headers", "cookies", "proxy", "environment",
    "env", "secrets", "token", "password", "credentials", "fullSource",
    "fullRationale", "traceback", "stack", "thread", "process",
    "dispatch", "force", "override",
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


# ═══════════════════════════════════════════════════════════════════════════
# 1. GET /tools/policy
# ═══════════════════════════════════════════════════════════════════════════


class TestToolPolicyStatus:
    """Tests for GET /api/dev/v1/tools/policy."""

    def test_returns_200(self, client):
        resp = client.get(f"{API}/tools/policy")
        assert resp.status_code == 200

    def test_response_envelope(self, client):
        resp = client.get(f"{API}/tools/policy")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "requestId" in body["meta"]
        assert "timestamp" in body["meta"]

    def test_mode_is_default_deny(self, client):
        resp = client.get(f"{API}/tools/policy")
        data = resp.json()["data"]
        assert data["mode"] == "DEFAULT_DENY"

    def test_inventory_count_71(self, client):
        resp = client.get(f"{API}/tools/policy")
        data = resp.json()["data"]
        assert data["inventoryCount"] == 71

    def test_risk_counts(self, client):
        resp = client.get(f"{API}/tools/policy")
        data = resp.json()["data"]
        rc = data["riskCounts"]
        assert rc["R0"] == 1
        assert rc["R1"] == 5
        assert rc["R2"] == 19
        assert rc["R3"] == 26
        assert rc["R4"] == 17
        assert rc["R5"] == 3

    def test_permanent_denylist_count_26(self, client):
        resp = client.get(f"{API}/tools/policy")
        data = resp.json()["data"]
        assert data["permanentDenylistCount"] == 26

    def test_candidate_allowlist_count_6(self, client):
        resp = client.get(f"{API}/tools/policy")
        data = resp.json()["data"]
        assert data["candidateAllowlistCount"] == 6

    def test_enabled_allowlist_count_0(self, client):
        resp = client.get(f"{API}/tools/policy")
        data = resp.json()["data"]
        assert data["enabledAllowlistCount"] == 0

    def test_execution_flags_all_false(self, client):
        resp = client.get(f"{API}/tools/policy")
        data = resp.json()["data"]
        exe = data["execution"]
        assert exe["implemented"] is False
        assert exe["enabled"] is False
        assert exe["providerSchemaSent"] is False
        assert exe["dispatchAvailable"] is False
        assert exe["auditAvailable"] is False

    def test_safety_flags(self, client):
        resp = client.get(f"{API}/tools/policy")
        data = resp.json()["data"]
        safety = data["safety"]
        assert safety["readOnly"] is True
        assert safety["sideEffects"] is False
        assert safety["writeEnabled"] is False
        assert safety["executeAvailable"] is False
        assert safety["policyMutationAvailable"] is False

    def test_limits_present(self, client):
        resp = client.get(f"{API}/tools/policy")
        data = resp.json()["data"]
        limits = data["limits"]
        assert limits["maxArgumentPayloadBytes"] > 0
        assert limits["maxToolCallsPerRun"] > 0
        assert limits["maxToolTimeoutSeconds"] > 0
        assert limits["maxGlobalConcurrency"] > 0

    def test_no_sensitive_fields(self, client):
        resp = client.get(f"{API}/tools/policy")
        body = resp.json()
        all_keys = _collect_keys(body)
        for forbidden in _FORBIDDEN_FIELDS:
            assert forbidden not in all_keys, f"Forbidden key found: {forbidden}"


# ═══════════════════════════════════════════════════════════════════════════
# 2. GET /tools/catalog — Basic
# ═══════════════════════════════════════════════════════════════════════════


class TestToolCatalogBasic:
    """Tests for GET /api/dev/v1/tools/catalog basic response."""

    def test_returns_200(self, client):
        resp = client.get(f"{API}/tools/catalog")
        assert resp.status_code == 200

    def test_response_envelope(self, client):
        resp = client.get(f"{API}/tools/catalog")
        body = resp.json()
        assert "data" in body
        assert "meta" in body

    def test_total_71(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        assert data["total"] == 71

    def test_default_page_1(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        assert data["page"] == 1

    def test_default_page_size_25(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        assert data["pageSize"] == 25

    def test_items_count_25(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        assert len(data["items"]) == 25

    def test_total_pages(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        assert data["totalPages"] == 3  # ceil(71/25) = 3

    def test_summary(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        summary = data["summary"]
        assert summary["inventoryCount"] == 71
        assert summary["permanentDenylistCount"] == 26
        assert summary["candidateAllowlistCount"] == 6
        assert summary["enabledAllowlistCount"] == 0

    def test_safety(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        safety = data["safety"]
        assert safety["readOnly"] is True
        assert safety["sideEffects"] is False
        assert safety["executeAvailable"] is False

    def test_filters_default(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        filters = data["filters"]
        assert filters["q"] is None
        assert filters["risk"] is None
        assert filters["capability"] is None
        assert filters["policyStatus"] is None
        assert filters["sort"] == "nameAsc"

    def test_all_items_allowed_false(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        for item in data["items"]:
            assert item["allowed"] is False

    def test_all_items_execution_available_false(self, client):
        resp = client.get(f"{API}/tools/catalog")
        data = resp.json()["data"]
        for item in data["items"]:
            assert item["executionAvailable"] is False
            assert item["schemaPreviewAvailable"] is False
            assert item["dryRunAvailable"] is False

    def test_no_sensitive_fields(self, client):
        resp = client.get(f"{API}/tools/catalog")
        body = resp.json()
        all_keys = _collect_keys(body)
        for forbidden in _FORBIDDEN_FIELDS:
            assert forbidden not in all_keys, f"Forbidden key found: {forbidden}"


# ═══════════════════════════════════════════════════════════════════════════
# 3. GET /tools/catalog — Query Parameters
# ═══════════════════════════════════════════════════════════════════════════


class TestToolCatalogQuery:
    """Tests for catalog query parameters — search, filter, sort, pagination."""

    def test_search_q(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"q": "memory"})
        data = resp.json()["data"]
        assert data["total"] > 0
        for item in data["items"]:
            q_lower = "memory"
            assert (
                q_lower in item["canonicalName"].lower()
                or q_lower in item["rationalePreview"].lower()
            )

    def test_filter_risk(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"risk": "R0"})
        data = resp.json()["data"]
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["primaryRisk"] == "R0"

    def test_filter_capability(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"capability": "PURE_COMPUTE"}
        )
        data = resp.json()["data"]
        assert data["total"] >= 1
        for item in data["items"]:
            assert "PURE_COMPUTE" in item["capabilities"]

    def test_filter_policy_status(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"policyStatus": "PERMANENTLY_DENIED"}
        )
        data = resp.json()["data"]
        assert data["total"] == 26
        for item in data["items"]:
            assert item["policyStatus"] == "PERMANENTLY_DENIED"

    def test_combined_filters(self, client):
        resp = client.get(
            f"{API}/tools/catalog",
            params={"risk": "R3", "policyStatus": "PERMANENTLY_DENIED"},
        )
        data = resp.json()["data"]
        for item in data["items"]:
            assert item["primaryRisk"] == "R3"
            assert item["policyStatus"] == "PERMANENTLY_DENIED"

    def test_sort_name_asc(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"sort": "nameAsc"})
        data = resp.json()["data"]
        names = [item["canonicalName"] for item in data["items"]]
        assert names == sorted(names)

    def test_sort_name_desc(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"sort": "nameDesc"})
        data = resp.json()["data"]
        names = [item["canonicalName"] for item in data["items"]]
        assert names == sorted(names, reverse=True)

    def test_sort_risk_asc(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"sort": "riskAsc"})
        data = resp.json()["data"]
        assert data["total"] == 71

    def test_sort_risk_desc(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"sort": "riskDesc"})
        data = resp.json()["data"]
        assert data["total"] == 71

    def test_page_2(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"page": 2})
        data = resp.json()["data"]
        assert data["page"] == 2
        assert len(data["items"]) == 25

    def test_page_size_10(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"pageSize": 10}
        )
        data = resp.json()["data"]
        assert len(data["items"]) == 10
        assert data["total"] == 71

    def test_page_beyond_total_returns_empty_items(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"page": 999})
        data = resp.json()["data"]
        assert len(data["items"]) == 0
        assert data["total"] == 71

    def test_empty_search_returns_results(self, client):
        """Empty string search should return all results."""
        resp = client.get(f"{API}/tools/catalog", params={"q": ""})
        data = resp.json()["data"]
        assert data["total"] == 71

    def test_filters_reflect_active_params(self, client):
        resp = client.get(
            f"{API}/tools/catalog",
            params={"q": "file", "risk": "R1", "sort": "nameDesc"},
        )
        data = resp.json()["data"]
        filters = data["filters"]
        assert filters["q"] == "file"
        assert filters["risk"] == "R1"
        assert filters["sort"] == "nameDesc"


# ═══════════════════════════════════════════════════════════════════════════
# 4. Error Mapping
# ═══════════════════════════════════════════════════════════════════════════


class TestToolCatalogErrors:
    """Tests for error responses on invalid input."""

    def test_q_too_long_returns_error(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"q": "x" * 121}
        )
        assert resp.status_code == 422
        body = resp.json()
        # FastAPI Query(max_length) returns validation error
        assert "detail" in body

    def test_invalid_risk_returns_400(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"risk": "R6"})
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "INVALID_TOOL_RISK"

    def test_invalid_capability_returns_400(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"capability": "INVALID"}
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "INVALID_TOOL_CAPABILITY"

    def test_invalid_policy_status_returns_400(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"policyStatus": "INVALID"}
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "INVALID_TOOL_POLICY_STATUS"

    def test_invalid_sort_returns_400(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"sort": "invalidSort"}
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "INVALID_TOOL_SORT"

    def test_page_less_than_1_returns_400(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"page": 0})
        assert resp.status_code == 422  # FastAPI Query(ge=1) validation

    def test_page_size_less_than_1_returns_400(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"pageSize": 0})
        assert resp.status_code == 422

    def test_page_size_over_100_returns_400(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"pageSize": 101})
        assert resp.status_code == 422

    def test_dangerous_execute_param_returns_400(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"execute": "true"}
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "INVALID_TOOL_POLICY_QUERY"

    def test_dangerous_force_param_returns_400(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"force": "1"}
        )
        assert resp.status_code == 400

    def test_dangerous_dispatch_param_returns_400(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"dispatch": "yes"}
        )
        assert resp.status_code == 400

    def test_dangerous_enable_param_returns_400(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"enable": "true"}
        )
        assert resp.status_code == 400

    def test_dangerous_write_param_returns_400(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"write": "true"}
        )
        assert resp.status_code == 400

    def test_dangerous_override_param_returns_400(self, client):
        resp = client.get(
            f"{API}/tools/catalog", params={"override": "true"}
        )
        assert resp.status_code == 400

    def test_error_no_path_leakage(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"risk": "R6"})
        body = resp.json()
        body_str = str(body).lower()
        assert "/users/" not in body_str
        assert "traceback" not in body_str
        assert "exception" not in body_str

    def test_error_has_request_id_and_timestamp(self, client):
        resp = client.get(f"{API}/tools/catalog", params={"risk": "R6"})
        body = resp.json()
        assert "requestId" in body
        assert "timestamp" in body


# ═══════════════════════════════════════════════════════════════════════════
# 5. Route Boundary
# ═══════════════════════════════════════════════════════════════════════════


class TestToolPolicyRouteBoundary:
    """Verify only the 2 allowed Tool GET routes exist."""

    def test_get_tools_policy_exists(self, client):
        resp = client.get(f"{API}/tools/policy")
        assert resp.status_code == 200

    def test_get_tools_catalog_exists(self, client):
        resp = client.get(f"{API}/tools/catalog")
        assert resp.status_code == 200

    def test_post_tools_policy_not_allowed(self, client):
        resp = client.post(f"{API}/tools/policy")
        assert resp.status_code == 405

    def test_patch_tools_policy_not_allowed(self, client):
        resp = client.patch(f"{API}/tools/policy")
        assert resp.status_code == 405

    def test_put_tools_policy_not_allowed(self, client):
        resp = client.put(f"{API}/tools/policy")
        assert resp.status_code == 405

    def test_delete_tools_policy_not_allowed(self, client):
        resp = client.delete(f"{API}/tools/policy")
        assert resp.status_code == 405

    def test_post_tools_catalog_not_allowed(self, client):
        resp = client.post(f"{API}/tools/catalog")
        assert resp.status_code == 405

    def test_catalog_detail_not_exists(self, client):
        resp = client.get(f"{API}/tools/catalog/some_tool")
        assert resp.status_code == 404

    def test_schema_preview_not_exists(self, client):
        resp = client.post(f"{API}/tools/schema/preview")
        assert resp.status_code == 404

    def test_call_dry_run_not_exists(self, client):
        resp = client.post(f"{API}/tools/calls/dry-run")
        assert resp.status_code == 404

    def test_call_execute_not_exists(self, client):
        resp = client.post(f"{API}/tools/calls")
        assert resp.status_code == 404

    def test_call_status_not_exists(self, client):
        resp = client.get(f"{API}/tools/calls/call123")
        assert resp.status_code == 404

    def test_call_cancel_not_exists(self, client):
        resp = client.post(f"{API}/tools/calls/call123/cancel")
        assert resp.status_code == 404

    def test_total_tool_get_routes_is_4(self, client):
        """Verify exactly 4 tool GET routes via OpenAPI spec."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        tool_get_routes = [
            p for p in spec["paths"]
            if p.startswith("/api/dev/v1/tools") and "get" in spec["paths"][p]
        ]
        assert len(tool_get_routes) == 4

    def test_no_tool_write_routes(self, client):
        """Verify no tool POST/PUT/PATCH/DELETE routes exist (dry-run POST excluded)."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        write_methods = {"post", "put", "patch", "delete"}
        # Tool dry-run POST is non-mutating — excluded from write count
        _TOOL_DRY_RUN_ROUTES = {"/api/dev/v1/tools/dry-run"}
        tool_write_routes = []
        for p, methods in spec["paths"].items():
            if not p.startswith("/api/dev/v1/tools"):
                continue
            if p in _TOOL_DRY_RUN_ROUTES:
                continue
            actual = set(methods.keys()) & write_methods
            if actual:
                tool_write_routes.append(f"{p} ({', '.join(sorted(actual))})")
        assert tool_write_routes == []


# ═══════════════════════════════════════════════════════════════════════════
# 6. Side Effects
# ═══════════════════════════════════════════════════════════════════════════


class TestToolPolicySideEffects:
    """Verify GET tool policy routes produce zero persistent side effects."""

    def test_state_db_unchanged(self, client_with_home, tmp_path):
        home = tmp_path / "hermes-home"
        db_path = home / "state.db"
        before_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()

        client_with_home.get(f"{API}/tools/policy")
        client_with_home.get(f"{API}/tools/catalog")

        after_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()
        assert before_hash == after_hash

    def test_no_tool_audit_table(self, client_with_home, tmp_path):
        home = tmp_path / "hermes-home"
        db_path = home / "state.db"

        client_with_home.get(f"{API}/tools/policy")
        client_with_home.get(f"{API}/tools/catalog")

        conn = sqlite3.connect(str(db_path))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        conn.close()
        table_names = [t[0] for t in tables]
        assert "tool_execution_audit" not in table_names

    def test_memory_files_unchanged(self, client_with_home, tmp_path):
        home = tmp_path / "hermes-home"
        memory_md_before = hashlib.sha256(
            (home / "MEMORY.md").read_bytes()
        ).hexdigest()

        client_with_home.get(f"{API}/tools/policy")
        client_with_home.get(f"{API}/tools/catalog")

        memory_md_after = hashlib.sha256(
            (home / "MEMORY.md").read_bytes()
        ).hexdigest()
        assert memory_md_before == memory_md_after


# ═══════════════════════════════════════════════════════════════════════════
# 7. Service Delegation
# ═══════════════════════════════════════════════════════════════════════════


class TestToolPolicyServiceDelegation:
    """Verify routes delegate to service, do not duplicate logic."""

    def test_policy_calls_get_policy_status(self, client):
        # Get the actual service instance from the app
        app = client.app
        real_service = app.state.tool_policy_service
        with patch.object(
            type(real_service), "get_policy_status",
            wraps=real_service.get_policy_status,
        ) as spy:
            resp = client.get(f"{API}/tools/policy")
            assert resp.status_code == 200
            spy.assert_called_once()

    def test_catalog_calls_list_tool_catalog(self, client):
        app = client.app
        real_service = app.state.tool_policy_service
        with patch.object(
            type(real_service), "list_tool_catalog",
            wraps=real_service.list_tool_catalog,
        ) as spy:
            resp = client.get(f"{API}/tools/catalog")
            assert resp.status_code == 200
            spy.assert_called_once()

    def test_route_does_not_import_registry(self):
        """Verify the API module does not import tools.registry."""
        import hermes_cli.dev_web_api as api_module

        module_source = open(api_module.__file__, encoding="utf-8").read()
        assert "tools.registry" not in module_source
        assert "from tools" not in module_source


# ═══════════════════════════════════════════════════════════════════════════
# 8. OpenAPI / Runtime Consistency
# ═══════════════════════════════════════════════════════════════════════════


class TestToolPolicyOpenAPIConsistency:
    """Verify runtime routes match the static OpenAPI spec."""

    def test_runtime_has_32_business_paths(self, client):
        resp = client.get("/openapi.json")
        spec = resp.json()
        paths = [
            p for p in spec["paths"]
            if p.startswith("/api/dev/v1/")
        ]
        assert len(paths) == 32

    def test_tools_policy_in_runtime(self, client):
        resp = client.get("/openapi.json")
        spec = resp.json()
        assert "/api/dev/v1/tools/policy" in spec["paths"]
        assert "get" in spec["paths"]["/api/dev/v1/tools/policy"]

    def test_tools_catalog_in_runtime(self, client):
        resp = client.get("/openapi.json")
        spec = resp.json()
        assert "/api/dev/v1/tools/catalog" in spec["paths"]
        assert "get" in spec["paths"]["/api/dev/v1/tools/catalog"]
