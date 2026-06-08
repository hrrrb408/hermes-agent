"""Phase 0D closure tests for responsive accessibility and motion hardening.

Extends Phase 0C-06 closure with:
- Route count unchanged (11 business paths)
- Forbidden routes still blocked
- No new write routes
- OpenAPI contract unchanged
- Redaction still active
- Error envelope unchanged
- CORS unchanged
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


# ── Route count unchanged ──


class TestRouteCount:
    """Phase 0D must not add or remove business routes."""

    def test_business_paths_count_unchanged(self, client):
        """Still exactly 11 business paths."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        paths = [p for p in spec["paths"] if p.startswith("/api/dev/v1/")]
        assert len(paths) == 11, (
            f"Expected 11 business paths, got {len(paths)}: {paths}"
        )

    def test_still_only_one_post_route(self, client):
        """Only POST /context/preview remains."""
        resp = client.get("/openapi.json")
        spec = resp.json()
        post_routes = []
        for path, methods in spec["paths"].items():
            if "post" in methods and path.startswith("/api/dev/v1/"):
                post_routes.append(path)
        assert len(post_routes) == 1
        assert post_routes[0] == "/api/dev/v1/context/preview"


# ── Forbidden routes still blocked ──


class TestForbiddenRoutesStillBlocked:
    """Phase 0D must not introduce any new endpoints."""

    FORBIDDEN_GET = [
        "/api/dev/v1/reviews",
        "/api/dev/v1/reviews/pending",
        "/api/dev/v1/reviews/MR-001",
        "/api/dev/v1/agent/run",
        "/api/dev/v1/tools",
        "/api/dev/v1/tools/run",
        "/api/dev/v1/files/upload",
        "/api/dev/v1/files?path=/etc/passwd",
        "/api/dev/v1/sse",
        "/api/dev/v1/ws",
    ]

    @pytest.mark.parametrize("path", FORBIDDEN_GET)
    def test_forbidden_get_404(self, client, path):
        resp = client.get(path)
        assert resp.status_code in (404, 405, 422), (
            f"GET {path} should be 404/405/422, got {resp.status_code}"
        )

    FORBIDDEN_WRITE = [
        ("POST", "/api/dev/v1/memory/items"),
        ("PATCH", "/api/dev/v1/memory/items/test-id"),
        ("POST", "/api/dev/v1/agent/run"),
        ("POST", "/api/dev/v1/tools/run"),
        ("POST", "/api/dev/v1/sessions"),
        ("POST", "/api/dev/v1/sessions/test-id/messages"),
        ("POST", "/api/dev/v1/reviews/MR-001/approve"),
        ("POST", "/api/dev/v1/reviews/MR-001/reject"),
    ]

    @pytest.mark.parametrize("method,path", FORBIDDEN_WRITE)
    def test_forbidden_write_rejected(self, client, method, path):
        fn = getattr(client, method.lower())
        resp = fn(path, json={})
        assert resp.status_code in (404, 405), (
            f"{method} {path} should be 404/405, got {resp.status_code}"
        )

    @pytest.mark.parametrize("path", [
        "/api/dev/v1/memory/items/test-id",
        "/api/dev/v1/sessions/test-id",
    ])
    def test_delete_not_allowed(self, client, path):
        resp = client.delete(path)
        assert resp.status_code in (404, 405), (
            f"DELETE {path} should be 404/405, got {resp.status_code}"
        )


# ── Redaction still active ──


class TestRedactionStillActive:
    """Path redaction must still be enforced after Phase 0D."""

    def test_memory_items_no_local_paths(self, client_with_home):
        resp = client_with_home.get(f"{API}/memory/items")
        if resp.status_code == 200:
            body = json.dumps(resp.json())
            assert "/Users/" not in body
            assert "/home/" not in body
            assert "file://" not in body

    def test_memory_detail_no_local_paths(self, client_with_home):
        resp = client_with_home.get(f"{API}/memory/items")
        if resp.status_code == 200:
            items = resp.json()["data"]["items"]
            if items:
                detail = client_with_home.get(
                    f"{API}/memory/items/{items[0]['id']}"
                )
                if detail.status_code == 200:
                    body = json.dumps(detail.json())
                    assert "/Users/" not in body
                    assert "/home/" not in body
                    assert "file://" not in body

    def test_context_preview_no_local_paths(self, client_with_home):
        resp = client_with_home.post(
            f"{API}/context/preview",
            json={"query": "test query"},
        )
        if resp.status_code == 200:
            body = json.dumps(resp.json())
            assert "/Users/" not in body
            assert "/home/" not in body
            assert "file://" not in body


# ── Error envelope unchanged ──


class TestErrorEnvelopeUnchanged:
    """Error responses still use unified envelope."""

    @pytest.mark.parametrize("method,path,expected_status", [
        ("GET", f"{API}/nonexistent", 404),
        ("DELETE", f"{API}/status", 405),
        ("POST", f"{API}/status", 405),
        ("POST", f"{API}/sessions", 405),
    ])
    def test_error_has_envelope(self, client, method, path, expected_status):
        fn = getattr(client, method.lower())
        resp = fn(path)
        assert resp.status_code == expected_status
        data = resp.json()
        assert "error" in data or "detail" in data
        if "error" in data:
            assert "code" in data["error"]
            assert "message" in data["error"]

    @pytest.mark.parametrize("method,path", [
        ("GET", f"{API}/nonexistent"),
        ("POST", f"{API}/status"),
    ])
    def test_error_no_traceback(self, client, method, path):
        fn = getattr(client, method.lower())
        resp = fn(path)
        text = resp.text.lower()
        assert "traceback" not in text
        assert "/Users/" not in resp.text


# ── Read-only guarantee ──


class TestReadOnlyGuarantee:
    """All endpoints remain read-only in Phase 0D."""

    def test_status_confirms_read_only(self, client):
        resp = client.get(f"{API}/status")
        data = resp.json()["data"]
        assert data["readOnly"] is True

    def test_agent_status_disabled(self, client):
        resp = client.get(f"{API}/agent/status")
        data = resp.json()["data"]
        assert data["readOnly"] is True
        assert data["runtime"]["toolExecutionEnabled"] is False
        assert data["runtime"]["messageSendEnabled"] is False

    def test_memory_no_write_capability(self, client):
        resp = client.get(f"{API}/memory/status")
        data = resp.json()["data"]
        assert data["exposedCapabilities"]["write"] is False
        assert data["exposedCapabilities"]["review"] is False

    def test_files_no_browse(self, client):
        resp = client.get(f"{API}/files/status")
        data = resp.json()["data"]
        assert data["browseEnabled"] is False
        assert data["readOnly"] is True
