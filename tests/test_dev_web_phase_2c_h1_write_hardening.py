"""Phase 2C-H1 — Write hardening integration tests.

The hardening sweep: write tokens are file-backed and scope-isolated from
rollback tokens; the token + rollback stores never store secrets or access
production; route governance stays 34/34/5/0/1/1; Phase 1G/2A/2B/2C contracts
are preserved; and no new HTTP route is introduced.

Phase: 2C-H1 — Write Execution Hardening
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hermes_cli.dev_web_write_plan import (
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


class TestWriteTokenFileBacked:
    def test_write_preview_token_is_file_backed(self, dev_home: str) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"}, hermes_home=dev_home
        )
        token = preview["confirmationToken"]
        assert token and token.startswith("cft_")
        assert "." in token  # <tokenId>.<secret>
        # The token file exists under the dev home token store.
        token_id = token.split(".", 1)[0]
        token_file = Path(dev_home) / "gateway/dev/tool-confirmation-tokens" / f"{token_id}.json"
        assert token_file.exists()

    def test_token_scope_is_write_execute(self, dev_home: str) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"}, hermes_home=dev_home
        )
        assert preview["confirmationTokenScope"] == "write_execute"


class TestScopeCrossProtection:
    def test_write_token_cannot_rollback(self, dev_home: str) -> None:
        from hermes_cli.dev_web_confirmation_store import (
            SCOPE_ROLLBACK_EXECUTE,
            create_confirmation_token,
            verify_confirmation_token,
        )
        from hermes_cli.dev_web_write_handlers import dispatch_write_tool

        # Issue a write token, then try to use it in a rollback-scope verify.
        preview = build_write_preview(
            "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"}, hermes_home=dev_home
        )
        result = verify_confirmation_token(
            preview["confirmationToken"], expected_scope=SCOPE_ROLLBACK_EXECUTE,
            expected_digest=preview["argumentDigest"], hermes_home=dev_home,
        )
        assert result.verified is False

    def test_rollback_token_cannot_write(self, dev_home: str) -> None:
        from hermes_cli.dev_web_confirmation_store import (
            SCOPE_ROLLBACK_EXECUTE,
            SCOPE_WRITE_EXECUTE,
            create_confirmation_token,
            verify_confirmation_token,
        )

        rtok = create_confirmation_token(
            {"rollbackId": "wrbk_x"}, scope=SCOPE_ROLLBACK_EXECUTE,
            argument_digest="d" * 64, hermes_home=dev_home,
        )
        result = verify_confirmation_token(
            rtok.token, expected_scope=SCOPE_WRITE_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is False


class TestRouteGovernance:
    def test_route_governance_34_34_5_0_1_1(self) -> None:
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=None))
        prefix = DevWebApiConfig().api_prefix
        spec = app.openapi()
        op = [p for p in spec["paths"] if p.startswith(prefix)]
        rp = [getattr(r, "path", None) for r in app.routes if getattr(r, "path", "").startswith(prefix)]
        assert len(op) == 34
        assert len(rp) == 34
        tg = [p for p in op if p.startswith(f"{prefix}/tools") and "get" in spec["paths"][p]]
        assert len(tg) == 5
        wm = {"post", "put", "patch", "delete"}
        nw = {f"{prefix}/tools/dry-run", f"{prefix}/tools/execute"}
        tw = [p for p in op if p.startswith(f"{prefix}/tools") and (wm & set(spec["paths"][p].keys())) and p not in nw]
        assert tw == []


def _real_code(path: Path) -> str:
    src = path.read_text(encoding="utf-8")
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"^\s*#.*$", "", src, flags=re.MULTILINE)
    return src


_REPO = Path(__file__).resolve().parents[1]
HARDENING_MODULES = [
    "hermes_cli/dev_web_confirmation_store.py",
    "hermes_cli/dev_web_write_rollback_store.py",
    "hermes_cli/dev_web_write_rollback.py",
    "hermes_cli/dev_web_write_handlers.py",
]


class TestSourceSafety:
    @pytest.mark.parametrize("rel", HARDENING_MODULES)
    def test_no_shell_db_external(self, rel: str) -> None:
        code = _real_code(_REPO / rel)
        assert "import subprocess" not in code
        assert "import sqlite3" not in code
        assert "import requests" not in code
        assert "import httpx" not in code
        assert "import urllib" not in code
        assert "os.system(" not in code

    @pytest.mark.parametrize("rel", HARDENING_MODULES)
    def test_no_production_io(self, rel: str) -> None:
        code = _real_code(_REPO / rel)
        assert "open(prod" not in code
        assert ".connect(" not in code

    def test_token_store_never_stores_secret(self, dev_home: str, tmp_path: Path) -> None:
        # Inspect an actual stored token file: it must not contain a secret
        # field nor the plain secret value.
        import json
        from hermes_cli.dev_web_confirmation_store import (
            SCOPE_WRITE_EXECUTE,
            create_confirmation_token,
        )

        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WRITE_EXECUTE, argument_digest="d" * 64, hermes_home=dev_home
        )
        assert issue is not None
        secret = issue.token.split(".", 1)[1]
        token_file = Path(dev_home) / "gateway/dev/tool-confirmation-tokens" / f"{issue.tokenId}.json"
        data = json.loads(token_file.read_text(encoding="utf-8"))
        assert "secret" not in data
        assert "plainToken" not in data
        assert "tokenSecret" not in data
        blob = token_file.read_text(encoding="utf-8")
        assert secret not in blob


class TestPreservation:
    def test_phase_1g_clarify_preserved(self) -> None:
        assert "clarify" in STATIC_ALLOWLIST

    def test_phase_2a_read_only_preserved(self) -> None:
        assert STATIC_ALLOWLIST == frozenset(
            {"clarify", "tool_policy_read", "route_governance_read",
             "audit_events_read", "dev_environment_read", "release_status_read"}
        )

    def test_phase_2b_fake_provider_preserved(self, dev_home: str) -> None:
        from hermes_cli.dev_web_provider_roundtrip import run_provider_tool_roundtrip

        result = run_provider_tool_roundtrip(
            user_message="check route governance", provider_mode="fake",
            selected_tool_ids=frozenset({"route_governance_read"}),
            context={"uiOrigin": "dev-webui"}, hermes_home=dev_home,
        )
        safe = result.to_safe_dict()
        assert safe["providerMode"] == "fake"
        assert len(safe["toolCalls"]) >= 1
        assert safe["externalNetworkCalled"] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
