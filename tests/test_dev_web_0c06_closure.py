"""Phase 0C-06 closure tests for route boundaries and error hardening.

Covers:
- Comprehensive forbidden route verification
- Error response leakage across all HTTP status codes
- Method enforcement on all business endpoints
- Context preview edge cases
- No Mock fallback verification
- Unified error envelope across all paths

Phase 1A note:
  Three read-only Review Queue GET routes were added in Phase 1A.
  The path count increased from 11 to 14. Review GET routes are
  now allowed; review write routes (approve/reject/enqueue/POST/PATCH/DELETE)
  remain forbidden.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig

API = "/api/dev/v1"


@pytest.fixture
def client():
    """TestClient without HERMES_HOME."""
    config = DevWebApiConfig(hermes_home=None)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def client_with_home(tmp_path):
    """TestClient with a minimal HERMES_HOME including MEMORY.md."""
    home = tmp_path / "hermes-home"
    home.mkdir()
    (home / "state.db").touch()
    (home / "memory" / "indexes").mkdir(parents=True)
    (home / "memory" / "records").mkdir(parents=True)
    (home / "memory" / "snapshots").mkdir(parents=True)
    (home / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    # Minimal MEMORY.md so memory service reports available
    (home / "MEMORY.md").write_text(
        "# Memory Root\n\n## test\n\n- index: memory://indexes/test.md\n"
        "- scope: test\n- priority: P1\n- status: active\n- keywords: test\n"
        "- description: Test category.\n",
        encoding="utf-8",
    )
    (home / "memory" / "indexes" / "test.md").write_text(
        "# Test Index\n", encoding="utf-8"
    )
    config = DevWebApiConfig(hermes_home=home)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ── Forbidden Routes: comprehensive 404 ──


class TestForbiddenRoutes:
    """Verify all disallowed business routes return 404.

    Phase 1B: Review Queue dry-run POST routes (approve/dry-run, reject/dry-run)
    are now allowed. Review execute routes (approve, reject without /dry-run)
    and enqueue remain forbidden.
    """

    @pytest.mark.parametrize("path", [
        # Review execute sub-paths remain forbidden (no /dry-run)
        "/api/dev/v1/reviews/MR-001/approve",
        "/api/dev/v1/reviews/MR-001/reject",
        # Agent execution
        "/api/dev/v1/agent/run",
        "/api/dev/v1/agent/messages",
        # Tool execution
        "/api/dev/v1/tools",
        "/api/dev/v1/tools/run",
        # File modification
        "/api/dev/v1/files/upload",
        "/api/dev/v1/files/delete",
        # Memory write
        "/api/dev/v1/memory/write",
        "/api/dev/v1/memory/items/test-id/delete",
        "/api/dev/v1/memory/items/test-id/update",
        "/api/dev/v1/memory/categories/add",
    ])
    def test_forbidden_routes_404(self, client, path):
        resp = client.get(path)
        assert resp.status_code == 404, f"{path} should be 404, got {resp.status_code}"

    @pytest.mark.parametrize("method,path", [
        # Review write execute routes — must remain forbidden (no /dry-run)
        ("POST", "/api/dev/v1/reviews"),
        ("POST", "/api/dev/v1/reviews/MR-test/approve"),
        ("POST", "/api/dev/v1/reviews/MR-test/reject"),
        ("POST", "/api/dev/v1/reviews/enqueue"),
        ("PATCH", "/api/dev/v1/reviews/MR-test"),
        # Memory write
        ("POST", "/api/dev/v1/memory/items"),
        ("PATCH", "/api/dev/v1/memory/items/test-id"),
        ("POST", "/api/dev/v1/memory/categories"),
        ("PATCH", "/api/dev/v1/memory/categories/test"),
        # Agent / tools execution
        ("POST", "/api/dev/v1/agent/run"),
        ("POST", "/api/dev/v1/tools/run"),
        # Session / message write
        ("POST", "/api/dev/v1/sessions"),
        ("PATCH", "/api/dev/v1/sessions/test-id"),
        ("POST", "/api/dev/v1/sessions/test-id/messages"),
        ("POST", "/api/dev/v1/messages"),
        # File write
        ("POST", "/api/dev/v1/files/upload"),
    ])
    def test_write_methods_not_allowed(self, client, method, path):
        fn = getattr(client, method.lower())
        resp = fn(path, json={})
        assert resp.status_code in (404, 405), (
            f"{method} {path} should be 404/405, got {resp.status_code}"
        )

    @pytest.mark.parametrize("path", [
        "/api/dev/v1/reviews/MR-test",
        "/api/dev/v1/memory/items/test-id",
        "/api/dev/v1/sessions/test-id",
        "/api/dev/v1/files/test",
    ])
    def test_delete_not_allowed(self, client, path):
        resp = client.delete(path)
        assert resp.status_code in (404, 405), (
            f"DELETE {path} should be 404/405, got {resp.status_code}"
        )

    def test_file_browse_by_path_not_allowed(self, client):
        resp = client.get("/api/dev/v1/files?path=/Users/test")
        assert resp.status_code in (404, 422, 200)
        # If 200, it must be the files/status endpoint, not browse
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("data", {}).get("browseEnabled") is False


# ── Method enforcement ──


class TestMethodEnforcement:
    """Verify GET-only endpoints reject POST/PUT/PATCH/DELETE."""

    GET_ONLY_ENDPOINTS = [
        f"{API}/status",
        f"{API}/files/status",
        f"{API}/sessions",
        f"{API}/sessions/test-id",
        f"{API}/sessions/test-id/messages",
        f"{API}/memory/status",
        f"{API}/memory/categories",
        f"{API}/memory/items",
        f"{API}/memory/items/TEST-001",
        f"{API}/agent/status",
        # Phase 1A: Review Queue read-only GET routes
        f"{API}/reviews/status",
        f"{API}/reviews",
        f"{API}/reviews/MR-001",
    ]

    @pytest.mark.parametrize("endpoint", GET_ONLY_ENDPOINTS)
    def test_post_rejected(self, client, endpoint):
        resp = client.post(endpoint, json={})
        assert resp.status_code in (404, 405)

    @pytest.mark.parametrize("endpoint", GET_ONLY_ENDPOINTS)
    def test_put_rejected(self, client, endpoint):
        resp = client.put(endpoint, json={})
        assert resp.status_code in (404, 405)

    @pytest.mark.parametrize("endpoint", GET_ONLY_ENDPOINTS)
    def test_patch_rejected(self, client, endpoint):
        resp = client.patch(endpoint, json={})
        assert resp.status_code in (404, 405)


# ── Error response leakage ──


class TestErrorResponseLeakage:
    """Verify error responses never leak sensitive data."""

    # Collect error responses from various endpoints
    ERROR_RESPONSES_PARAMS = [
        # 404
        ("GET", f"{API}/nonexistent"),
        # Reviews: now a valid route, returns 503 when service unavailable
        ("GET", f"{API}/reviews"),
        # 405
        ("POST", f"{API}/status"),
        ("DELETE", f"{API}/status"),
    ]

    @pytest.mark.parametrize("method,path", ERROR_RESPONSES_PARAMS)
    def test_no_traceback_in_errors(self, client, method, path):
        fn = getattr(client, method.lower())
        resp = fn(path)
        text = resp.text.lower()
        assert "traceback" not in text
        assert "exception" not in text

    @pytest.mark.parametrize("method,path", ERROR_RESPONSES_PARAMS)
    def test_no_paths_in_errors(self, client, method, path):
        fn = getattr(client, method.lower())
        resp = fn(path)
        text = resp.text
        assert "/Users/" not in text
        assert "/home/" not in text
        assert "file://" not in text
        assert ".hermes" not in text

    @pytest.mark.parametrize("method,path", ERROR_RESPONSES_PARAMS)
    def test_no_secrets_in_errors(self, client, method, path):
        fn = getattr(client, method.lower())
        resp = fn(path)
        text = resp.text.lower()
        assert "api_key" not in text
        assert "secret" not in text
        assert "token" not in text
        assert "cookie" not in text
        assert "base_url" not in text
        assert "state.db" not in text

    def test_503_no_leakage(self, client):
        """503 from missing services must not leak internals."""
        resp = client.get(f"{API}/sessions")
        if resp.status_code == 503:
            text = resp.text.lower()
            assert "traceback" not in text
            assert "sqlite" not in text
            assert "operationalerror" not in text

    def test_context_preview_invalid_json_safe(self, client_with_home):
        """Invalid JSON body must not leak internals."""
        resp = client_with_home.post(
            f"{API}/context/preview",
            content=b"not json at all",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400
        text = resp.text.lower()
        assert "traceback" not in text
        assert "/Users/" not in text

    def test_422_validation_safe(self, client):
        """FastAPI validation errors must not leak implementation details."""
        resp = client.get(f"{API}/sessions?limit=0")
        if resp.status_code == 422:
            text = resp.text.lower()
            assert "traceback" not in text
            assert "/Users/" not in text


# ── Context preview edge cases ──


class TestContextPreviewEdgeCases:
    """Context preview edge cases with safe error handling."""

    def test_null_query(self, client_with_home):
        resp = client_with_home.post(
            f"{API}/context/preview",
            json={"query": None},
        )
        assert resp.status_code == 400

    def test_query_with_script_tags(self, client_with_home):
        """Script injection in query is echoed back safely as text.

        The API echoes the query string back in the response. This is safe
        because the frontend uses Vue {{ }} templates (text interpolation)
        and never v-html. The script tags are rendered as literal text.
        """
        resp = client_with_home.post(
            f"{API}/context/preview",
            json={"query": "<script>alert(1)</script>"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        # Query is echoed back as plain text — frontend renders it as text
        assert data["query"] == "<script>alert(1)</script>"
        # No actual execution — sideEffects remains false
        assert data["sideEffects"] is False

    def test_options_with_negative_values(self, client_with_home):
        resp = client_with_home.post(
            f"{API}/context/preview",
            json={"query": "test", "options": {"maxCategories": -1}},
        )
        assert resp.status_code == 200
        # Should use safe default
        assert resp.json()["data"]["limits"]["maxCategories"] == 3

    def test_options_with_extremely_large_values(self, client_with_home):
        resp = client_with_home.post(
            f"{API}/context/preview",
            json={"query": "test", "options": {"maxCategories": 999999}},
        )
        assert resp.status_code == 200
        # Should clamp to max
        assert resp.json()["data"]["limits"]["maxCategories"] == 10

    def test_extra_body_fields_ignored(self, client_with_home):
        resp = client_with_home.post(
            f"{API}/context/preview",
            json={
                "query": "test",
                "extraField": "ignored",
                "malicious": {"runAgent": True},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["sideEffects"] is False


# ── Unified error envelope ──


class TestUnifiedErrorEnvelope:
    """All error responses must use the unified envelope."""

    @pytest.mark.parametrize("method,path,expected_status", [
        ("GET", f"{API}/nonexistent", 404),
        ("DELETE", f"{API}/status", 405),
        ("POST", f"{API}/status", 405),
    ])
    def test_error_has_envelope(self, client, method, path, expected_status):
        fn = getattr(client, method.lower())
        resp = fn(path)
        assert resp.status_code == expected_status
        data = resp.json()
        # Must have error object with code and message
        assert "error" in data or "detail" in data
        if "error" in data:
            assert "code" in data["error"]
            assert "message" in data["error"]
        # Must have requestId
        assert "requestId" in data or "request_id" in data.get("meta", {})

    def test_503_has_envelope(self, client):
        resp = client.get(f"{API}/sessions")
        if resp.status_code == 503:
            data = resp.json()
            assert "error" in data
            assert "code" in data["error"]


# ── No Mock fallback ──


class TestNoMockFallback:
    """Verify the API never returns mock data."""

    def test_status_not_mock(self, client):
        resp = client.get(f"{API}/status")
        data = resp.json()["data"]
        assert data["environment"] == "development"
        assert data["status"] == "ok"
        assert data["readOnly"] is True

    def test_files_status_not_mock(self, client):
        resp = client.get(f"{API}/files/status")
        data = resp.json()["data"]
        assert data["available"] is False
        assert data["readOnly"] is True
        # No fake browse capability
        assert data["browseEnabled"] is False

    def test_agent_status_not_mock(self, client):
        resp = client.get(f"{API}/agent/status")
        data = resp.json()["data"]
        # Without HERMES_HOME, available should be False
        assert data["available"] is False
        assert data["readOnly"] is True
        assert data["runtime"]["toolExecutionEnabled"] is False
        assert data["runtime"]["messageSendEnabled"] is False

    def test_memory_status_not_mock(self, client):
        resp = client.get(f"{API}/memory/status")
        data = resp.json()["data"]
        # Without HERMES_HOME, available should be False
        assert data["available"] is False
        assert data["exposedCapabilities"]["write"] is False
        assert data["exposedCapabilities"]["review"] is False


# ── OpenAPI contract ──


class TestOpenAPIContract:
    """Verify static and runtime OpenAPI consistency."""

    def test_business_paths_count(self, client):
        """Phase 1B: 16 implemented business paths (11 + 3 review + 2 dry-run)."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        assert len(paths) == 16

    def test_post_routes(self, client):
        """Phase 1B: 3 POST routes (context/preview + 2 review dry-run)."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        post_routes = []
        for path, methods in spec["paths"].items():
            if "post" in methods and path.startswith("/api/dev/v1/"):
                post_routes.append(path)
        assert len(post_routes) == 3
        assert "/api/dev/v1/context/preview" in post_routes
        assert "/api/dev/v1/reviews/{reviewId}/approve/dry-run" in post_routes
        assert "/api/dev/v1/reviews/{reviewId}/reject/dry-run" in post_routes

    def test_no_write_schemas(self, client):
        resp = client.get("/openapi.json")
        spec = resp.json()
        text = json.dumps(spec).lower()
        assert "write_memory" not in text
        assert "create_session" not in text
        assert "run_agent" not in text
        assert "execute_tool" not in text

    def test_record_preview_described(self, client):
        """Verify recordPreview field exists in the static OpenAPI spec."""
        # Runtime spec uses dict returns without inline schemas,
        # but the static YAML has the description with redaction note.
        # Verify the static file has it.
        import pathlib
        static_yaml = pathlib.Path(
            "docs/webui/openapi/dev-web-api-v1.yaml"
        )
        if static_yaml.exists():
            text = static_yaml.read_text(encoding="utf-8")
            assert "redact" in text.lower() or "[local-path]" in text


# ── Read-only guarantee across all endpoints ──


class TestReadOnlyGuarantee:
    """Verify all endpoints are truly read-only."""

    def test_all_get_endpoints_return_safe_data(self, client_with_home):
        """All GET endpoints must return safe data regardless of status."""
        endpoints = [
            f"{API}/status",
            f"{API}/files/status",
            f"{API}/sessions",
            f"{API}/memory/status",
            f"{API}/agent/status",
            f"{API}/memory/categories",
            f"{API}/memory/items",
        ]
        for url in endpoints:
            resp = client_with_home.get(url)
            assert resp.status_code in (200, 503), f"{url} returned {resp.status_code}"
            body = json.dumps(resp.json())
            # No paths
            assert "/Users/" not in body, f"Path leak in {url}"
            assert "/home/" not in body, f"Path leak in {url}"
            assert "file://" not in body, f"file:// leak in {url}"
            # No secrets
            lower = body.lower()
            assert "api_key" not in lower, f"Secret leak in {url}"
            assert '"secret"' not in lower, f"Secret leak in {url}"
            assert "base_url" not in lower, f"Secret leak in {url}"

    def test_memory_endpoints_no_storage_uri(self, client_with_home):
        """Memory endpoints must not expose storage URIs."""
        for url in [f"{API}/memory/status", f"{API}/memory/categories", f"{API}/memory/items"]:
            resp = client_with_home.get(url)
            if resp.status_code == 200:
                body = json.dumps(resp.json())
                assert "memory://" not in body, f"memory:// in {url}"
                assert "storage" not in body.lower() or '"writestorage"' not in body.lower()
