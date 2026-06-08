"""Tests for dev-check WebUI governance checks (Phase 0E-05).

Covers:
- _webui_check_gitignore: paths ignored vs not ignored
- _webui_check_openapi: path count, allowed routes, forbidden routes
- Integration: cmd_dev_check output includes WebUI section
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

import pytest
import yaml

from hermes_cli.main import _webui_check_gitignore, _webui_check_openapi


# ── Fixtures ──────────────────────────────────────────────────────────


class CheckCollector:
    """Collects (status, label, value) tuples for assertion."""

    def __init__(self) -> None:
        self.checks: list[tuple[str, str, str]] = []

    def __call__(self, status: str, label: str, value: str) -> None:
        self.checks.append((status, label, value))

    def labels(self) -> list[str]:
        return [label for _, label, _ in self.checks]

    def by_label(self, label: str) -> tuple[str, str, str] | None:
        for check in self.checks:
            if check[1] == label:
                return check
        return None

    def statuses_for(self, label: str) -> list[str]:
        return [s for s, l, _ in self.checks if l == label]


def _make_gitignore_fn(ignored_paths: set[str]):
    """Create a git_value_fn stub that simulates git check-ignore."""

    def git_value_fn(*git_args: str) -> tuple[str, int]:
        if git_args[:2] == ("check-ignore", "-v"):
            target = git_args[2] if len(git_args) > 2 else ""
            if target in ignored_paths:
                return (f".gitignore:1:... {target}", 0)
            return ("", 1)
        return ("", 1)

    return git_value_fn


# ── _webui_check_gitignore tests ──────────────────────────────────────


class TestWebuiCheckGitignore:
    def test_all_paths_ignored(self) -> None:
        col = CheckCollector()
        git_fn = _make_gitignore_fn({"apps/hermes-dev-webui/dist/index.html"})
        _webui_check_gitignore(col, git_fn, "Build artifacts", ["apps/hermes-dev-webui/dist/index.html"])
        assert col.by_label("Build artifacts") == ("PASS", "Build artifacts", "ignored")

    def test_path_not_ignored(self) -> None:
        col = CheckCollector()
        git_fn = _make_gitignore_fn(set())  # nothing ignored
        _webui_check_gitignore(col, git_fn, "Build artifacts", ["apps/hermes-dev-webui/dist/index.html"])
        assert col.by_label("Build artifacts") == ("FAIL", "Build artifacts", "not ignored")

    def test_multiple_paths_one_missing(self) -> None:
        col = CheckCollector()
        git_fn = _make_gitignore_fn({"a"})  # only "a" ignored, not "b"
        _webui_check_gitignore(col, git_fn, "Test label", ["a", "b"])
        assert col.by_label("Test label") == ("FAIL", "Test label", "not ignored")

    def test_multiple_paths_all_ignored(self) -> None:
        col = CheckCollector()
        git_fn = _make_gitignore_fn({"a", "b", "c"})
        _webui_check_gitignore(col, git_fn, "Test label", ["a", "b", "c"])
        assert col.by_label("Test label") == ("PASS", "Test label", "ignored")


# ── _webui_check_openapi tests ────────────────────────────────────────


def _write_openapi(tmp_path: Path, spec: dict[str, Any]) -> Path:
    """Write a YAML spec and return the path."""
    p = tmp_path / "openapi.yaml"
    p.write_text(yaml.dump(spec, default_flow_style=False), encoding="utf-8")
    return p


def _minimal_valid_spec() -> dict[str, Any]:
    """Return a valid 11-path OpenAPI spec matching the Dev WebUI contract."""
    paths: dict[str, Any] = {
        "/status": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/files/status": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/sessions": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/sessions/{sessionId}": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/sessions/{sessionId}/messages": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/memory/status": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/memory/categories": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/memory/items": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/memory/items/{memoryId}": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/context/preview": {"post": {"responses": {"200": {"description": "ok"}}}},
        "/agent/status": {"get": {"responses": {"200": {"description": "ok"}}}},
    }
    return {"openapi": "3.1.0", "info": {"title": "test", "version": "1.0"}, "paths": paths}


class TestWebuiCheckOpenapi:
    def test_valid_11_paths(self, tmp_path: Path) -> None:
        spec = _minimal_valid_spec()
        p = _write_openapi(tmp_path, spec)
        col = CheckCollector()
        _webui_check_openapi(col, p)
        assert col.by_label("OpenAPI paths") == ("PASS", "OpenAPI paths", "11")
        assert col.by_label("OpenAPI routes") == ("PASS", "OpenAPI routes", "all present")
        assert col.by_label("Forbidden routes") == ("PASS", "Forbidden routes", "absent")

    def test_wrong_path_count(self, tmp_path: Path) -> None:
        spec = _minimal_valid_spec()
        # Remove one path to get 10
        del spec["paths"]["/agent/status"]
        p = _write_openapi(tmp_path, spec)
        col = CheckCollector()
        _webui_check_openapi(col, p)
        assert col.by_label("OpenAPI paths") == ("FAIL", "OpenAPI paths", "10")
        # Also should report missing route
        route_check = col.by_label("OpenAPI routes")
        assert route_check is not None
        assert route_check[0] == "FAIL"
        assert "agent/status" in route_check[2]

    def test_missing_route(self, tmp_path: Path) -> None:
        spec = _minimal_valid_spec()
        # Replace a required route with an extra one
        del spec["paths"]["/sessions"]
        spec["paths"]["/extra"] = {"get": {"responses": {"200": {"description": "ok"}}}}
        p = _write_openapi(tmp_path, spec)
        col = CheckCollector()
        _webui_check_openapi(col, p)
        route_check = col.by_label("OpenAPI routes")
        assert route_check is not None
        assert route_check[0] == "FAIL"
        assert "/sessions" in route_check[2]

    def test_forbidden_route_reviews(self, tmp_path: Path) -> None:
        spec = _minimal_valid_spec()
        spec["paths"]["/reviews"] = {"get": {"responses": {"200": {"description": "ok"}}}}
        p = _write_openapi(tmp_path, spec)
        col = CheckCollector()
        _webui_check_openapi(col, p)
        forbidden_check = col.by_label("Forbidden routes")
        assert forbidden_check is not None
        assert forbidden_check[0] == "FAIL"
        assert "/reviews" in forbidden_check[2]

    def test_forbidden_route_agent_run(self, tmp_path: Path) -> None:
        spec = _minimal_valid_spec()
        spec["paths"]["/agent/run"] = {"post": {"responses": {"200": {"description": "ok"}}}}
        p = _write_openapi(tmp_path, spec)
        col = CheckCollector()
        _webui_check_openapi(col, p)
        forbidden_check = col.by_label("Forbidden routes")
        assert forbidden_check is not None
        assert forbidden_check[0] == "FAIL"
        assert "/agent/run" in forbidden_check[2]

    def test_forbidden_route_tools(self, tmp_path: Path) -> None:
        spec = _minimal_valid_spec()
        spec["paths"]["/tools/execute"] = {"post": {"responses": {"200": {"description": "ok"}}}}
        p = _write_openapi(tmp_path, spec)
        col = CheckCollector()
        _webui_check_openapi(col, p)
        forbidden_check = col.by_label("Forbidden routes")
        assert forbidden_check is not None
        assert forbidden_check[0] == "FAIL"
        assert "/tools" in forbidden_check[2]

    def test_forbidden_route_files_upload(self, tmp_path: Path) -> None:
        spec = _minimal_valid_spec()
        spec["paths"]["/files/upload"] = {"post": {"responses": {"200": {"description": "ok"}}}}
        p = _write_openapi(tmp_path, spec)
        col = CheckCollector()
        _webui_check_openapi(col, p)
        forbidden_check = col.by_label("Forbidden routes")
        assert forbidden_check is not None
        assert forbidden_check[0] == "FAIL"
        assert "/files/upload" in forbidden_check[2]

    def test_extra_method_on_allowed_route(self, tmp_path: Path) -> None:
        spec = _minimal_valid_spec()
        # Add DELETE to sessions (should be GET-only)
        spec["paths"]["/sessions"]["delete"] = {"responses": {"200": {"description": "ok"}}}
        p = _write_openapi(tmp_path, spec)
        col = CheckCollector()
        _webui_check_openapi(col, p)
        forbidden_check = col.by_label("Forbidden routes")
        assert forbidden_check is not None
        assert forbidden_check[0] == "FAIL"
        assert "delete" in forbidden_check[2].lower()

    def test_post_on_wrong_route(self, tmp_path: Path) -> None:
        spec = _minimal_valid_spec()
        # Add POST to /sessions (should be GET-only)
        spec["paths"]["/sessions"]["post"] = {"responses": {"200": {"description": "ok"}}}
        p = _write_openapi(tmp_path, spec)
        col = CheckCollector()
        _webui_check_openapi(col, p)
        forbidden_check = col.by_label("Forbidden routes")
        assert forbidden_check is not None
        assert forbidden_check[0] == "FAIL"
        assert "post" in forbidden_check[2].lower()

    def test_context_preview_post_allowed(self, tmp_path: Path) -> None:
        """POST /context/preview is the only allowed POST — must not be flagged."""
        spec = _minimal_valid_spec()
        p = _write_openapi(tmp_path, spec)
        col = CheckCollector()
        _webui_check_openapi(col, p)
        assert col.by_label("Forbidden routes") == ("PASS", "Forbidden routes", "absent")

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("{{invalid yaml::", encoding="utf-8")
        col = CheckCollector()
        # Should raise, caught by the caller in cmd_dev_check
        with pytest.raises(Exception):
            _webui_check_openapi(col, p)

    def test_12_paths(self, tmp_path: Path) -> None:
        spec = _minimal_valid_spec()
        spec["paths"]["/extra"] = {"get": {"responses": {"200": {"description": "ok"}}}}
        p = _write_openapi(tmp_path, spec)
        col = CheckCollector()
        _webui_check_openapi(col, p)
        assert col.by_label("OpenAPI paths") == ("FAIL", "OpenAPI paths", "12")

    def test_11_paths_all_present_forbidden_absent(self, tmp_path: Path) -> None:
        """The real OpenAPI file should pass all checks."""
        real_openapi = Path("docs/webui/openapi/dev-web-api-v1.yaml")
        if not real_openapi.is_file():
            pytest.skip("OpenAPI file not found (running outside repo root)")
        col = CheckCollector()
        _webui_check_openapi(col, real_openapi)
        assert col.by_label("OpenAPI paths") == ("PASS", "OpenAPI paths", "11")
        assert col.by_label("OpenAPI routes") == ("PASS", "OpenAPI routes", "all present")
        assert col.by_label("Forbidden routes") == ("PASS", "Forbidden routes", "absent")


# ── Integration: dev-check output includes WebUI section ──────────────


class TestDevCheckWebuiIntegration:
    """Verify that cmd_dev_check produces WebUI governance output.

    These tests run the actual dev-check and assert on the output.
    They are integration tests that require the full dev environment.
    """

    @pytest.mark.integration
    def test_dev_check_includes_webui_app(self) -> None:
        """dev-check output should include WebUI app check."""
        import subprocess

        result = subprocess.run(
            ["python", "-m", "hermes_cli.main", "dev-check"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        output = result.stdout
        assert "WebUI app:" in output
        assert "PASS" in output.split("WebUI app:")[0].split("\n")[-1]

    @pytest.mark.integration
    def test_dev_check_includes_openapi(self) -> None:
        """dev-check output should include OpenAPI checks."""
        import subprocess

        result = subprocess.run(
            ["python", "-m", "hermes_cli.main", "dev-check"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        output = result.stdout
        assert "OpenAPI paths:" in output
        assert "OpenAPI routes:" in output
        assert "Forbidden routes:" in output

    @pytest.mark.integration
    def test_dev_check_includes_artifact_checks(self) -> None:
        """dev-check output should include build artifact and visual-review checks."""
        import subprocess

        result = subprocess.run(
            ["python", "-m", "hermes_cli.main", "dev-check"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        output = result.stdout
        assert "Build artifacts:" in output
        assert "Visual review:" in output
        assert "Playwright artifacts:" in output

    @pytest.mark.integration
    def test_dev_check_includes_smoke_runner(self) -> None:
        """dev-check output should include smoke runner check."""
        import subprocess

        result = subprocess.run(
            ["python", "-m", "hermes_cli.main", "dev-check"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        output = result.stdout
        assert "Smoke runner:" in output
        assert "Smoke script:" in output

    @pytest.mark.integration
    def test_dev_check_no_service_startup(self) -> None:
        """dev-check must complete quickly (no service startup)."""
        import subprocess
        import time

        start = time.monotonic()
        subprocess.run(
            ["python", "-m", "hermes_cli.main", "dev-check"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        elapsed = time.monotonic() - start
        # Should complete in well under 10 seconds if no services started
        assert elapsed < 10, f"dev-check took {elapsed:.1f}s — may have started a service"
