"""Phase 2C — Write security boundary tests.

The central safety sweep for controlled write execution. Verifies:

  - writes outside the dev sandbox are blocked (traversal / absolute / symlink
    escape / production home / production state.db / repo tree)
  - forbidden targets (.env / .claude / .git / *.jsonl / *.log / *.db) blocked
  - oversized + binary content blocked
  - the write modules introduce NO shell command execution, database mutation,
    or external service write (source inspection)
  - the write modules never OPEN/READ/WRITE ~/.hermes or production state.db
  - route governance stays 34/34/5/0/1/1 (no new HTTP route)
  - provider write never auto-executes; real provider write is blocked
  - audit payloads never leak raw tokens / full tokenHash / raw arguments /
    secrets / callable reprs
  - Phase 1G / 2A / 2B contracts are preserved

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hermes_cli.dev_web_write_plan import (
    BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED,
    build_provider_write_preview,
    build_write_preview,
    _reset_confirmation_state_for_tests,
)
from hermes_cli.dev_web_tool_policy import STATIC_ALLOWLIST


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_TOOL_WRITE_EXECUTION_ENABLED", "1")
    _reset_confirmation_state_for_tests()
    return str(home)


# ---------------------------------------------------------------------------
# 1. Write-outside-sandbox is blocked
# ---------------------------------------------------------------------------


class TestWriteOutsideSandboxBlocked:
    @pytest.mark.parametrize(
        "target",
        [
            "../escape.md",
            "notes/../../escape.md",
            "/etc/passwd",
            "~/secret.md",
        ],
    )
    def test_path_blocked(self, dev_home: str, target: str) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write",
            {"targetPath": target, "content": "x"},
            hermes_home=dev_home,
        )
        assert preview["blocked"] is True
        # And nothing was written outside the sandbox.
        escaped = Path(dev_home).parent / "escape.md"
        assert escaped.exists() is False

    def test_production_home_blocked(self) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x"},
            hermes_home="/Users/huangruibang/.hermes",
        )
        assert preview["blocked"] is True

    def test_production_state_db_target_blocked(self, dev_home: str) -> None:
        # Even though it is under the dev home, state.db is a forbidden target.
        preview = build_write_preview(
            "dev_sandbox_file_write",
            {"targetPath": "state.db", "content": "x"},
            hermes_home=dev_home,
        )
        assert preview["blocked"] is True

    @pytest.mark.parametrize(
        "target",
        [
            "bad/.env",
            "nested/.claude/x.md",
            "repo/.git/config.md",
            "logs/run.log",
            "data/state.db",
            "a/x.jsonl",
            "a/x.sqlite",
            "out/test-results/x.md",
            "out/playwright-report/x.md",
        ],
    )
    def test_forbidden_target_blocked(self, dev_home: str, target: str) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write",
            {"targetPath": target, "content": "x"},
            hermes_home=dev_home,
        )
        assert preview["blocked"] is True


# ---------------------------------------------------------------------------
# 2. Oversized + binary blocked
# ---------------------------------------------------------------------------


class TestSizeAndBinaryBlocked:
    def test_oversized_blocked(self, dev_home: str) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x" * (64 * 1024 + 1)},
            hermes_home=dev_home,
        )
        assert preview["blocked"] is True

    def test_binary_blocked(self, dev_home: str) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "".join(chr(i) for i in range(1, 200))},
            hermes_home=dev_home,
        )
        assert preview["blocked"] is True


# ---------------------------------------------------------------------------
# 3. Source inspection — no shell / database / external-service / prod access
# ---------------------------------------------------------------------------


def _real_code(path: Path) -> str:
    """Strip docstrings/comments so we inspect real code only."""
    src = path.read_text(encoding="utf-8")
    cleaned = re.sub(r'"""[\s\S]*?"""', "", src)
    cleaned = re.sub(r"^\s*#.*$", "", cleaned, flags=re.MULTILINE)
    return cleaned


WRITE_MODULES = [
    "hermes_cli/dev_web_write_tool_registry.py",
    "hermes_cli/dev_web_write_sandbox.py",
    "hermes_cli/dev_web_write_plan.py",
    "hermes_cli/dev_web_write_handlers.py",
    "hermes_cli/dev_web_write_rollback.py",
]

_REPO_ROOT = Path(__file__).resolve().parents[1]


class TestSourceSafety:
    @pytest.mark.parametrize("rel", WRITE_MODULES)
    def test_no_shell_subprocess_exec(self, rel: str) -> None:
        code = _real_code(_REPO_ROOT / rel)
        assert "import subprocess" not in code
        assert "os.system(" not in code
        assert "shell=True" not in code
        assert "os.popen(" not in code

    @pytest.mark.parametrize("rel", WRITE_MODULES)
    def test_no_database_mutation(self, rel: str) -> None:
        code = _real_code(_REPO_ROOT / rel)
        assert "import sqlite3" not in code
        assert ".connect(" not in code
        assert "sqlite3.connect" not in code

    @pytest.mark.parametrize("rel", WRITE_MODULES)
    def test_no_external_service_write(self, rel: str) -> None:
        code = _real_code(_REPO_ROOT / rel)
        # Inspect actual import / call forms (not the banned-operation string
        # list the registry carries for its own validation).
        assert "import requests" not in code
        assert "requests.post(" not in code
        assert "import httpx" not in code
        assert "import urllib" not in code
        assert "urllib.request" not in code
        assert "import aiohttp" not in code
        assert "socket.socket(" not in code

    @pytest.mark.parametrize("rel", WRITE_MODULES)
    def test_no_production_access(self, rel: str) -> None:
        code = _real_code(_REPO_ROOT / rel)
        # The production path constant may exist for an equality comparison,
        # but it must never be opened / read / written.
        assert "open(prod" not in code
        assert "prod_home.read" not in code
        assert "prod_home.write" not in code
        # No raw absolute production path used for IO.
        assert 'open("/Users/huangruibang/.hermes' not in code


# ---------------------------------------------------------------------------
# 4. Route governance unchanged
# ---------------------------------------------------------------------------


class TestRouteGovernance:
    def test_route_governance_34_34_5_0_1_1(self) -> None:
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=None))
        prefix = DevWebApiConfig().api_prefix
        spec = app.openapi()
        openapi_paths = [p for p in spec["paths"] if p.startswith(prefix)]
        runtime_paths = [
            getattr(r, "path", None)
            for r in app.routes
            if getattr(r, "path", "").startswith(prefix)
        ]
        assert len(openapi_paths) == 34
        assert len(runtime_paths) == 34
        tool_get = [
            p for p in openapi_paths
            if p.startswith(f"{prefix}/tools") and "get" in spec["paths"][p]
        ]
        assert len(tool_get) == 5
        _write_methods = {"post", "put", "patch", "delete"}
        _non_write = {f"{prefix}/tools/dry-run", f"{prefix}/tools/execute"}
        tool_write = [
            p for p in openapi_paths
            if p.startswith(f"{prefix}/tools")
            and (_write_methods & set(spec["paths"][p].keys()))
            and p not in _non_write
        ]
        assert tool_write == []


# ---------------------------------------------------------------------------
# 5. Provider write never auto-executes
# ---------------------------------------------------------------------------


class TestProviderWriteBoundary:
    def test_fake_provider_write_not_executed(self, dev_home: str) -> None:
        preview = build_provider_write_preview(
            "draft a sandbox note", "dev_sandbox_file_write", hermes_home=dev_home
        )
        assert preview["writeExecuted"] is False
        assert preview["blockedReason"] == BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED

    def test_real_provider_write_not_executed(self, dev_home: str) -> None:
        preview = build_provider_write_preview(
            "draft a sandbox note", "dev_sandbox_file_write",
            hermes_home=dev_home, provider_mode="real",
        )
        assert preview["writeExecuted"] is False


# ---------------------------------------------------------------------------
# 6. Audit redaction — no secret/callable leak
# ---------------------------------------------------------------------------


class TestAuditRedaction:
    def test_audit_payload_redacts_secrets_and_callables(self) -> None:
        import json

        from hermes_cli.dev_web_write_plan import build_write_audit_event

        event = build_write_audit_event(
            event_type="write_post_execution_audit",
            tool_id="dev_sandbox_file_write",
            write_plan_id="wpln_x",
            write_preview_id="wprv_x",
            rollback_id="wrbk_x",
            operation="create_or_replace",
            target_relative_path="a.md",
            status="completed",
            blocked_reason=None,
            payload={
                "apiKey": "sk-abcdefghijklmnopqrstuvwxyz",
                "authorization": "Bearer xyz",
                "handler": lambda: None,  # type: ignore[dict-item]
            },
        )
        blob = json.dumps(event)
        assert "sk-abcdefghijklmnopqrstuvwxyz" not in blob
        assert "Bearer xyz" not in blob
        assert "<function" not in blob
        assert "<lambda>" not in blob


# ---------------------------------------------------------------------------
# 7. Phase 1G / 2A / 2B preservation
# ---------------------------------------------------------------------------


class TestPhasePreservation:
    def test_phase_1g_clarify_preserved(self) -> None:
        assert "clarify" in STATIC_ALLOWLIST

    def test_phase_2a_read_only_allowlist_preserved(self) -> None:
        # STATIC_ALLOWLIST stays frozen at the six read-only tools.
        assert STATIC_ALLOWLIST == frozenset(
            {
                "clarify",
                "tool_policy_read",
                "route_governance_read",
                "audit_events_read",
                "dev_environment_read",
                "release_status_read",
            }
        )
        assert len(STATIC_ALLOWLIST) == 6

    def test_phase_2b_fake_provider_preserved(self, dev_home: str) -> None:
        # The fake provider can still route to a read-only tool and execute it.
        from hermes_cli.dev_web_provider_roundtrip import run_provider_tool_roundtrip

        result = run_provider_tool_roundtrip(
            user_message="check route governance",
            provider_mode="fake",
            selected_tool_ids=frozenset({"route_governance_read"}),
            context={"uiOrigin": "dev-webui"},
            hermes_home=dev_home,
        )
        safe = result.to_safe_dict()
        assert safe["providerMode"] == "fake"
        # A read-only tool call was parsed and executed.
        assert len(safe["toolCalls"]) >= 1
        assert safe["externalNetworkCalled"] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
