"""Phase 3C — Capability Registry security / no-leak boundary tests.

Verifies the end-to-end no-leak closure: the read model (summary + every
detail) never surfaces a secret, callable repr, shell command, SQL statement,
production path, local plugin path, dynamic import path, or external URL; and
the registry never performs a network call, never reads ``~/.hermes``, and
never reads a production ``state.db``.

Phase: 3C — Static dev-only Capability Registry
"""

from __future__ import annotations

import inspect
import importlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app, DevWebApiConfig
from hermes_cli.dev_web_capability_registry import (
    build_registry_summary,
    get_capability_detail,
    get_registry_status_block,
    list_capability_details,
)
from hermes_cli.dev_web_capability_registry_manifest import get_static_manifest

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


def _no_leak(blob: str) -> None:
    for token in _FORBIDDEN_TOKENS:
        assert token not in blob, f"forbidden token {token!r} leaked"


class TestReadModelNoLeak:
    def test_summary_no_leak(self) -> None:
        _no_leak(json.dumps(build_registry_summary()))

    def test_status_block_no_leak(self) -> None:
        _no_leak(json.dumps(get_registry_status_block()))

    def test_all_details_no_leak(self) -> None:
        _no_leak(json.dumps(list_capability_details(get_static_manifest())))

    def test_each_detail_no_leak(self) -> None:
        for entry in get_static_manifest():
            detail = get_capability_detail(get_static_manifest(), entry["capabilityId"])
            assert detail is not None
            _no_leak(json.dumps(detail))

    def test_forbidden_capability_detail_blocked(self) -> None:
        d = get_capability_detail(get_static_manifest(), "capability.forbidden.shell")
        assert d is not None
        assert d["status"] == "blocked"
        assert d["permissionClass"] == "ADMIN_FORBIDDEN"
        # No shell payload surfaces.
        _no_leak(json.dumps(d))

    def test_live_capability_listed_not_executed(self) -> None:
        d = get_capability_detail(get_static_manifest(), "provider.live_manual_one_shot")
        assert d is not None
        assert d["permissionClass"] == "LIVE_PROVIDER_GATED"
        assert d["status"] == "disabled"
        assert d["executionMode"] == "manual_live"
        assert d["requiresBudget"] is True
        assert d["requiresKillSwitch"] is True


class TestNoNetworkNoProductionAccess:
    @staticmethod
    def _client(tmp_path: Path) -> TestClient:
        cfg = DevWebApiConfig(host="127.0.0.1", port=5181, hermes_home=tmp_path / "dev-home")
        return TestClient(create_dev_web_api_app(cfg))

    def test_registry_modules_no_network_imports(self) -> None:
        import ast
        for module_name in (
            "hermes_cli.dev_web_capability_registry",
            "hermes_cli.dev_web_capability_registry_manifest",
            "hermes_cli.dev_web_capability_registry_audit",
        ):
            mod = importlib.import_module(module_name)
            src_path = Path(inspect.getsourcefile(mod))  # type: ignore[arg-type]
            tree = ast.parse(src_path.read_text(encoding="utf-8"))
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split(".")[0])
            for forbidden in ("requests", "httpx", "urllib", "aiohttp", "http", "socket"):
                assert forbidden not in imports, f"{module_name} must not import {forbidden!r}"

    def test_status_response_no_production_path(self, tmp_path: Path) -> None:
        client = self._client(tmp_path)
        blob = json.dumps(client.get("/api/dev/v1/status").json()["data"]["capabilityRegistry"])
        assert "/Users/huangruibang/.hermes" not in blob
        assert "state.db" not in blob

    def test_read_only_default(self, tmp_path: Path) -> None:
        client = self._client(tmp_path)
        data = client.get("/api/dev/v1/status").json()["data"]
        assert data["readOnly"] is True


class TestFailClosed:
    def test_invalid_manifest_summary_marks_validation_failed(self) -> None:
        from hermes_cli.dev_web_capability_registry import validate_manifest

        bad = list(get_static_manifest())[0].copy()
        bad["pythonImportPath"] = "evil"
        report = validate_manifest([bad])
        summary = build_registry_summary(report)
        assert summary["status"] == "validation_failed"
        assert summary["validationPassed"] is False

    def test_invalid_entry_blocked_in_detail_list(self) -> None:
        bad = list(get_static_manifest())[0].copy()
        bad["capabilityId"] = "tool.read.bad_detail"
        bad["shellCommand"] = "rm -rf /"
        details = list_capability_details([bad])
        assert details[0]["status"] == "blocked"
        _no_leak(json.dumps(details))
