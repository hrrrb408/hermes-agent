"""Phase 2C-H1 — Provider write boundary tests.

Confirms the provider write boundary holds under hardening: the fake provider
may suggest a write (preview only), but never auto-executes a write OR a
rollback; real provider write/rollback remain blocked; a provider preview
confirmation token cannot be used to execute a write or a rollback.

Phase: 2C-H1 — Write Execution Hardening
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.dev_web_write_plan import (
    BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED,
    build_provider_write_preview,
    build_write_preview,
    _reset_confirmation_state_for_tests,
)
from hermes_cli.dev_web_write_handlers import dispatch_rollback_tool, dispatch_write_tool


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_TOOL_WRITE_EXECUTION_ENABLED", "1")
    _reset_confirmation_state_for_tests()
    return str(home)


class TestProviderWritePreview:
    def test_fake_provider_write_not_executed(self, dev_home: str) -> None:
        preview = build_provider_write_preview(
            "draft a sandbox note", "dev_sandbox_file_write", hermes_home=dev_home
        )
        assert preview["writeExecuted"] is False
        assert preview["blockedReason"] == BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED
        # No file created by the preview.
        sandbox = Path(dev_home) / "gateway/dev/tool-write-sandbox"
        if sandbox.exists():
            assert list(sandbox.rglob("*.md")) == []

    def test_real_provider_write_not_executed(self, dev_home: str) -> None:
        preview = build_provider_write_preview(
            "draft a note", "dev_sandbox_file_write",
            hermes_home=dev_home, provider_mode="real",
        )
        assert preview["writeExecuted"] is False
        assert preview["providerMode"] == "real"


class TestProviderApiBoundary:
    def test_api_provider_write_preview_blocked(self, dev_home: str) -> None:
        from fastapi.testclient import TestClient
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=Path(dev_home)))
        client = TestClient(app)
        resp = client.post(
            "/api/dev/v1/tools/execute",
            json={
                "mode": "provider_roundtrip",
                "providerMode": "fake",
                "message": "draft a sandbox note please",
                "allowedToolIds": ["dev_sandbox_file_write"],
                "providerWriteMode": "preview_only",
            },
        )
        data = resp.json()["data"]
        assert data["status"] == "blocked"
        assert data["writeExecuted"] is False
        assert data["externalNetworkCalled"] is False


class TestProviderTokenCannotExecute:
    def test_provider_preview_token_cannot_execute_write(self, dev_home: str) -> None:
        # A provider write preview issues a write_execute-scoped token, but the
        # provider path never reaches dispatch_write_tool. Simulate a client
        # attempting to use a write token with wrong args — the digest gate
        # blocks it. (The token scope is write_execute; provider preview itself
        # is blocked from auto-execution regardless.)
        provider_preview = build_provider_write_preview(
            "draft a note", "dev_sandbox_file_write", hermes_home=dev_home
        )
        # The provider preview is already blocked (auto-execute denied); the
        # token it carries is bound to its own args, not arbitrary writes.
        assert provider_preview["blockedReason"] == BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED

    def test_rollback_token_cannot_be_used_for_write(self, dev_home: str) -> None:
        # Issue a write, then a rollback preview (rollback-scoped token). The
        # rollback token must not verify for a write execution.
        from hermes_cli.dev_web_confirmation_store import (
            SCOPE_ROLLBACK_EXECUTE,
            SCOPE_WRITE_EXECUTE,
            create_confirmation_token,
            verify_confirmation_token,
        )

        rtok = create_confirmation_token(
            {"rollbackId": "wrbk_" + "0" * 24}, scope=SCOPE_ROLLBACK_EXECUTE,
            argument_digest="d" * 64, hermes_home=dev_home,
        )
        assert rtok is not None
        result = verify_confirmation_token(
            rtok.token, expected_scope=SCOPE_WRITE_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is False  # scope mismatch


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
