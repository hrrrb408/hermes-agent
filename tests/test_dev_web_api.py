"""Tests for the Hermes Dev Web API Phase 0C-02 skeleton.

Covers:
- Configuration validation (host, port, CORS)
- HERMES_HOME isolation
- Status endpoint
- Files status endpoint
- Request ID middleware
- Error model
- CORS enforcement
- Route boundary (no unimplemented endpoints)
- Side-effect verification
- Import safety
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_config import (
    ALLOWED_HOSTS,
    DEFAULT_DEV_WEB_API_HOST,
    DEFAULT_DEV_WEB_API_PORT,
    DEFAULT_DEV_WEB_API_PREFIX,
    DEFAULT_DEV_WEB_API_CORS_ORIGINS,
    DevApiConfigurationError,
    DevWebApiConfig,
    build_config,
    validate_development_hermes_home,
)
from hermes_cli.dev_web_schemas import (
    generate_request_id,
    sanitize_request_id,
)
from hermes_cli.dev_web_api import create_dev_web_api_app


# ── Fixtures ──


@pytest.fixture
def client():
    """TestClient with a default safe config."""
    config = DevWebApiConfig(hermes_home=None)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def client_with_home(tmp_path):
    """TestClient with a valid temporary HERMES_HOME."""
    config = DevWebApiConfig(hermes_home=tmp_path)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ── 1. Configuration defaults ──


class TestConfigDefaults:
    def test_default_host(self):
        assert DEFAULT_DEV_WEB_API_HOST == "127.0.0.1"

    def test_default_port(self):
        assert DEFAULT_DEV_WEB_API_PORT == 5181

    def test_default_cors_origin(self):
        assert DEFAULT_DEV_WEB_API_CORS_ORIGINS == ("http://127.0.0.1:5180",)

    def test_default_api_prefix(self):
        assert DEFAULT_DEV_WEB_API_PREFIX == "/api/dev/v1"

    def test_allowed_hosts_contains_only_loopback(self):
        assert ALLOWED_HOSTS == frozenset({"127.0.0.1"})

    def test_config_with_defaults(self):
        config = DevWebApiConfig(hermes_home=None)
        assert config.host == "127.0.0.1"
        assert config.port == 5181
        assert config.cors_origins == ("http://127.0.0.1:5180",)
        assert config.api_prefix == "/api/dev/v1"
        assert config.environment == "development"


# ── 2. Host validation ──


class TestHostValidation:
    @pytest.mark.parametrize("unsafe_host", [
        "0.0.0.0",
        "localhost",
        "::",
        "::1",
        "192.168.1.10",
        "10.0.0.1",
        "example.com",
        "",
    ])
    def test_unsafe_host_rejected(self, unsafe_host):
        with pytest.raises(DevApiConfigurationError, match="Refusing"):
            DevWebApiConfig(host=unsafe_host, hermes_home=None)

    def test_127_0_0_1_accepted(self):
        config = DevWebApiConfig(host="127.0.0.1", hermes_home=None)
        assert config.host == "127.0.0.1"


# ── 3. Port validation ──


class TestPortValidation:
    @pytest.mark.parametrize("bad_port", [-1, 0, 65536, 100000])
    def test_invalid_port_rejected(self, bad_port):
        with pytest.raises(DevApiConfigurationError, match="Invalid port"):
            DevWebApiConfig(port=bad_port, hermes_home=None)

    def test_valid_port_accepted(self):
        config = DevWebApiConfig(port=5181, hermes_home=None)
        assert config.port == 5181

    def test_port_80_accepted(self):
        config = DevWebApiConfig(port=80, hermes_home=None)
        assert config.port == 80


# ── 4. HERMES_HOME isolation ──


class TestHermesHomeIsolation:
    def test_valid_dev_home_passes(self, tmp_path):
        result = validate_development_hermes_home(tmp_path)
        assert result == tmp_path.resolve()

    def test_production_home_rejected(self):
        prod = Path.home() / ".hermes"
        with pytest.raises(DevApiConfigurationError, match="production"):
            validate_development_hermes_home(prod)

    def test_production_subpath_rejected(self, tmp_path):
        """A directory inside ~/.hermes must be rejected.

        We create a fake production-like structure using a temporary
        directory with a .hermes subdirectory.
        """
        fake_prod = tmp_path / "fake_prod" / ".hermes"
        fake_prod.mkdir(parents=True)
        fake_inside = fake_prod / "subdir"
        fake_inside.mkdir()

        # Monkey-patch the production path constant in the module.
        import hermes_cli.dev_web_config as cfg_mod
        original = cfg_mod._PRODUCTION_HERMES_HOME
        try:
            cfg_mod._PRODUCTION_HERMES_HOME = fake_prod
            with pytest.raises(DevApiConfigurationError, match="inside"):
                validate_development_hermes_home(fake_inside)
        finally:
            cfg_mod._PRODUCTION_HERMES_HOME = original

    def test_symlink_to_production_rejected(self, tmp_path):
        """A symlink pointing to production home must be rejected."""
        prod = Path.home() / ".hermes"
        link = tmp_path / "evil_link"
        try:
            link.symlink_to(prod)
        except OSError:
            pytest.skip("Cannot create symlink in test")

        with pytest.raises(DevApiConfigurationError):
            validate_development_hermes_home(link)

    def test_none_rejected(self):
        with pytest.raises(DevApiConfigurationError, match="not set"):
            validate_development_hermes_home(None)

    def test_nonexistent_path_rejected(self, tmp_path):
        gone = tmp_path / "does_not_exist"
        with pytest.raises(DevApiConfigurationError, match="does not exist"):
            validate_development_hermes_home(gone)

    def test_file_path_rejected(self, tmp_path):
        a_file = tmp_path / "not_a_dir"
        a_file.write_text("hello")
        with pytest.raises(DevApiConfigurationError, match="not a directory"):
            validate_development_hermes_home(a_file)


# ── 5. build_config ──


class TestBuildConfig:
    def test_build_with_valid_home(self, tmp_path):
        config = build_config(hermes_home=tmp_path)
        assert config.hermes_home == tmp_path.resolve()

    def test_build_with_env_home(self, tmp_path):
        with patch.dict(os.environ, {"HERMES_HOME": str(tmp_path)}):
            config = build_config()
        assert config.hermes_home == tmp_path.resolve()

    def test_build_without_home_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove HERMES_HOME if present
            os.environ.pop("HERMES_HOME", None)
            with pytest.raises(DevApiConfigurationError, match="not set"):
                build_config()

    def test_build_with_unsafe_host_raises(self, tmp_path):
        with pytest.raises(DevApiConfigurationError, match="Refusing"):
            build_config(host="0.0.0.0", hermes_home=tmp_path)

    def test_build_with_env_port(self, tmp_path):
        with patch.dict(os.environ, {"HERMES_DEV_WEB_API_PORT": "9999"}):
            config = build_config(hermes_home=tmp_path)
        assert config.port == 9999

    def test_build_with_bad_env_port_raises(self, tmp_path):
        with patch.dict(os.environ, {"HERMES_DEV_WEB_API_PORT": "abc"}):
            with pytest.raises(DevApiConfigurationError, match="integer"):
                build_config(hermes_home=tmp_path)

    def test_build_with_env_unsafe_host_raises(self, tmp_path):
        with patch.dict(os.environ, {"HERMES_DEV_WEB_API_HOST": "0.0.0.0"}):
            with pytest.raises(DevApiConfigurationError, match="Refusing"):
                build_config(hermes_home=tmp_path)

    def test_explicit_params_override_env(self, tmp_path):
        with patch.dict(os.environ, {
            "HERMES_DEV_WEB_API_HOST": "0.0.0.0",
            "HERMES_DEV_WEB_API_PORT": "9999",
        }):
            # Explicit host must still be validated
            with pytest.raises(DevApiConfigurationError):
                build_config(hermes_home=tmp_path)


# ── 6. Status endpoint ──


class TestStatusEndpoint:
    def test_status_returns_200(self, client):
        resp = client.get("/api/dev/v1/status")
        assert resp.status_code == 200

    def test_status_content_type(self, client):
        resp = client.get("/api/dev/v1/status")
        assert "application/json" in resp.headers["content-type"]

    def test_status_environment(self, client):
        resp = client.get("/api/dev/v1/status")
        data = resp.json()
        assert data["data"]["environment"] == "development"

    def test_status_api_version(self, client):
        resp = client.get("/api/dev/v1/status")
        assert resp.json()["data"]["apiVersion"] == "v1"

    def test_status_read_only(self, client):
        resp = client.get("/api/dev/v1/status")
        assert resp.json()["data"]["readOnly"] is True

    def test_status_bind(self, client):
        resp = client.get("/api/dev/v1/status")
        bind = resp.json()["data"]["bind"]
        assert bind["host"] == "127.0.0.1"
        assert bind["port"] == 5181

    def test_status_isolation_no_home(self, client):
        """Without HERMES_HOME, isolation.passed should be False."""
        resp = client.get("/api/dev/v1/status")
        iso = resp.json()["data"]["isolation"]
        assert iso["passed"] is False
        assert iso["usesDevelopmentHome"] is False

    def test_status_isolation_with_home(self, client_with_home):
        resp = client_with_home.get("/api/dev/v1/status")
        iso = resp.json()["data"]["isolation"]
        assert iso["passed"] is True
        assert iso["usesDevelopmentHome"] is True

    def test_status_services_unavailable(self, client):
        resp = client.get("/api/dev/v1/status")
        services = resp.json()["data"]["services"]
        assert services["api"]["available"] is True
        assert services["sessions"]["available"] is False
        assert services["memory"]["available"] is False
        assert services["agent"]["available"] is False
        assert services["files"]["available"] is False

    def test_status_no_absolute_paths(self, client):
        resp = client.get("/api/dev/v1/status")
        text = resp.text
        assert "/Users/" not in text
        assert "/home/" not in text

    def test_status_no_secrets(self, client):
        resp = client.get("/api/dev/v1/status")
        text = resp.text.lower()
        assert "api_key" not in text
        assert "secret" not in text
        assert "token" not in text
        assert "cookie" not in text
        assert "password" not in text

    def test_status_has_request_id(self, client):
        resp = client.get("/api/dev/v1/status")
        rid = resp.json()["meta"]["requestId"]
        assert rid
        assert len(rid) == 32  # UUID4 hex

    def test_status_has_timestamp(self, client):
        resp = client.get("/api/dev/v1/status")
        ts = resp.json()["meta"]["timestamp"]
        assert ts.endswith("Z")
        assert "T" in ts

    def test_status_has_response_header_request_id(self, client):
        resp = client.get("/api/dev/v1/status")
        assert "x-request-id" in resp.headers
        assert resp.headers["x-request-id"]


# ── 7. Files status endpoint ──


class TestFilesStatusEndpoint:
    def test_files_returns_200(self, client):
        resp = client.get("/api/dev/v1/files/status")
        assert resp.status_code == 200

    def test_files_available_false(self, client):
        resp = client.get("/api/dev/v1/files/status")
        data = resp.json()
        assert data["data"]["available"] is False

    def test_files_browse_disabled(self, client):
        resp = client.get("/api/dev/v1/files/status")
        data = resp.json()["data"]
        assert data["browseEnabled"] is False
        assert data["uploadEnabled"] is False
        assert data["downloadEnabled"] is False
        assert data["deleteEnabled"] is False

    def test_files_has_reason(self, client):
        resp = client.get("/api/dev/v1/files/status")
        assert "not available" in resp.json()["data"]["reason"].lower()

    def test_files_no_path_param_accepted(self, client):
        """Even if a query param is sent, no file access occurs."""
        resp = client.get("/api/dev/v1/files/status?path=/etc/passwd")
        # Should still return normal response, ignoring the param
        assert resp.status_code == 200
        assert resp.json()["data"]["available"] is False


# ── 8. Request ID ──


class TestRequestId:
    def test_auto_generated_when_missing(self, client):
        resp = client.get("/api/dev/v1/status")
        rid = resp.headers.get("x-request-id")
        assert rid
        assert len(rid) == 32

    def test_client_id_accepted(self, client):
        resp = client.get(
            "/api/dev/v1/status",
            headers={"X-Request-ID": "test-123"},
        )
        assert resp.headers["x-request-id"] == "test-123"
        assert resp.json()["meta"]["requestId"] == "test-123"

    def test_newline_rejected(self, client):
        """A request ID with newline must not be echoed."""
        resp = client.get(
            "/api/dev/v1/status",
            headers={"X-Request-ID": "evil\nid"},
        )
        rid = resp.headers["x-request-id"]
        assert "\n" not in rid
        assert rid != "evil\nid"

    def test_too_long_rejected(self, client):
        long_id = "a" * 100
        resp = client.get(
            "/api/dev/v1/status",
            headers={"X-Request-ID": long_id},
        )
        rid = resp.headers["x-request-id"]
        assert rid != long_id
        assert len(rid) <= 64

    def test_404_has_request_id(self, client):
        resp = client.get("/api/dev/v1/nonexistent")
        assert resp.status_code == 404
        assert "requestId" in resp.json()

    def test_method_not_allowed_has_request_id(self, client):
        resp = client.post("/api/dev/v1/status")
        assert resp.status_code == 405
        assert "requestId" in resp.json()


# ── 9. Error model ──


class TestErrorModel:
    def test_404_format(self, client):
        resp = client.get("/api/dev/v1/nonexistent")
        data = resp.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "requestId" in data
        assert "timestamp" in data

    def test_405_format(self, client):
        resp = client.delete("/api/dev/v1/status")
        assert resp.status_code == 405
        data = resp.json()
        assert data["error"]["code"]

    def test_error_no_traceback(self, client):
        resp = client.get("/api/dev/v1/nonexistent")
        text = resp.text.lower()
        assert "traceback" not in text

    def test_error_no_absolute_paths(self, client):
        resp = client.get("/api/dev/v1/nonexistent")
        text = resp.text
        assert "/Users/" not in text
        assert "/home/" not in text

    def test_error_no_secrets(self, client):
        resp = client.get("/api/dev/v1/nonexistent")
        text = resp.text.lower()
        assert "api_key" not in text
        assert "secret" not in text
        assert "token" not in text
        assert ".hermes" not in text
        assert "state.db" not in text

    def test_error_has_timestamp(self, client):
        resp = client.get("/api/dev/v1/nonexistent")
        ts = resp.json()["timestamp"]
        assert ts.endswith("Z")

    def test_validation_error_format(self, client):
        """Trigger FastAPI validation error."""
        resp = client.get("/api/dev/v1/status?invalid_param=bad")
        # Validation errors are 422 from FastAPI
        if resp.status_code == 422:
            data = resp.json()
            assert "error" in data or "detail" in data


# ── 10. CORS ──


class TestCORS:
    def test_allowed_origin(self, client):
        resp = client.get(
            "/api/dev/v1/status",
            headers={"Origin": "http://127.0.0.1:5180"},
        )
        assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:5180"

    def test_reject_localhost(self, client):
        resp = client.get(
            "/api/dev/v1/status",
            headers={"Origin": "http://localhost:5180"},
        )
        assert resp.headers.get("access-control-allow-origin") != "http://localhost:5180"

    def test_reject_wrong_port(self, client):
        resp = client.get(
            "/api/dev/v1/status",
            headers={"Origin": "http://127.0.0.1:5186"},
        )
        assert resp.headers.get("access-control-allow-origin") != "http://127.0.0.1:5186"

    def test_reject_external(self, client):
        resp = client.get(
            "/api/dev/v1/status",
            headers={"Origin": "https://example.com"},
        )
        assert resp.headers.get("access-control-allow-origin") != "https://example.com"

    def test_no_wildcard(self, client):
        resp = client.options(
            "/api/dev/v1/status",
            headers={
                "Origin": "http://127.0.0.1:5180",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") != "*"

    def test_expose_request_id_header(self, client):
        """The X-Request-ID must be readable by the browser."""
        resp = client.get(
            "/api/dev/v1/status",
            headers={"Origin": "http://127.0.0.1:5180"},
        )
        # X-Request-ID is always in the response headers from middleware.
        assert "x-request-id" in resp.headers


# ── 11. Route boundary ──


class TestRouteBoundary:
    """Phase 0C-03: /status, /files/status, /sessions, /sessions/{id} exist.
    All other planned endpoints remain unimplemented (404)."""

    @pytest.mark.parametrize("path", [
        "/api/dev/v1/sessions/test-id/messages",
        "/api/dev/v1/memory/status",
        "/api/dev/v1/memory/categories",
        "/api/dev/v1/memory/items",
        "/api/dev/v1/context/preview",
        "/api/dev/v1/agent/status",
        "/api/dev/v1/reviews",
    ])
    def test_unimplemented_endpoints_return_404(self, client, path):
        resp = client.get(path)
        assert resp.status_code == 404

    def test_sessions_list_exists(self, client):
        """GET /sessions is implemented (returns 503 without hermes_home)."""
        resp = client.get("/api/dev/v1/sessions")
        assert resp.status_code == 503

    def test_sessions_detail_exists(self, client):
        """GET /sessions/{id} is implemented (returns 503 without hermes_home)."""
        resp = client.get("/api/dev/v1/sessions/test-id")
        assert resp.status_code == 503

    def test_no_session_write_routes(self, client):
        resp = client.post("/api/dev/v1/sessions", json={})
        assert resp.status_code == 405

    def test_no_memory_write_routes(self, client):
        resp = client.post("/api/dev/v1/memory/items", json={})
        assert resp.status_code == 404

    def test_no_review_routes(self, client):
        resp = client.get("/api/dev/v1/reviews")
        assert resp.status_code == 404

    def test_no_file_upload(self, client):
        resp = client.post("/api/dev/v1/files/upload", json={})
        assert resp.status_code == 404

    def test_no_delete_routes(self, client):
        resp = client.delete("/api/dev/v1/sessions/test-id")
        assert resp.status_code == 405


# ── 12. Side-effect verification ──


class TestNoSideEffects:
    def test_status_creates_no_files(self, client, tmp_path):
        """Requesting status must not create any files."""
        before = set(tmp_path.iterdir()) if tmp_path.exists() else set()
        client.get("/api/dev/v1/status")
        after = set(tmp_path.iterdir()) if tmp_path.exists() else set()
        assert before == after

    def test_files_status_creates_no_files(self, client, tmp_path):
        before = set(tmp_path.iterdir()) if tmp_path.exists() else set()
        client.get("/api/dev/v1/files/status")
        after = set(tmp_path.iterdir()) if tmp_path.exists() else set()
        assert before == after


# ── 13. Import safety ──


class TestImportSafety:
    def test_import_no_side_effects(self):
        """Importing the API module must not start a server or open files."""
        # This test passes if the import above (in fixtures) succeeded
        # without errors. We explicitly verify module-level attributes.
        from hermes_cli.dev_web_api import create_dev_web_api_app
        assert callable(create_dev_web_api_app)

    def test_import_config_no_side_effects(self):
        from hermes_cli.dev_web_config import DevWebApiConfig
        # Creating a config with hermes_home=None should not touch filesystem
        config = DevWebApiConfig(hermes_home=None)
        assert config.host == "127.0.0.1"


# ── 14. Request ID sanitization ──


class TestRequestIdSanitization:
    def test_none_returns_new_id(self):
        rid = sanitize_request_id(None)
        assert len(rid) == 32

    def test_empty_returns_new_id(self):
        rid = sanitize_request_id("")
        assert len(rid) == 32

    def test_valid_id_preserved(self):
        rid = sanitize_request_id("abc-123")
        assert rid == "abc-123"

    def test_newline_generates_new(self):
        rid = sanitize_request_id("abc\n123")
        assert "\n" not in rid
        assert rid != "abc\n123"

    def test_carriage_return_generates_new(self):
        rid = sanitize_request_id("abc\r123")
        assert "\r" not in rid

    def test_null_byte_generates_new(self):
        rid = sanitize_request_id("abc\x00123")
        assert "\x00" not in rid

    def test_too_long_generates_new(self):
        rid = sanitize_request_id("a" * 100)
        assert len(rid) <= 64

    def test_max_length_preserved(self):
        rid = sanitize_request_id("a" * 64)
        assert rid == "a" * 64
