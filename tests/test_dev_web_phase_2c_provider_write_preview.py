"""Phase 2C — Provider write preview tests.

Verifies that a (fake) provider may *suggest* a Phase 2C write tool, that the
system generates a write PREVIEW for it, and that it NEVER auto-executes. Real
provider write execution remains blocked. The provider write preview reuses
the existing ``/tools/execute`` route (mode ``provider_roundtrip``) — no new
route is added.

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.dev_web_write_plan import (
    BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED,
    build_provider_write_preview,
    _reset_confirmation_state_for_tests,
)


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_TOOL_WRITE_EXECUTION_ENABLED", "1")
    _reset_confirmation_state_for_tests()
    return str(home)


class TestProviderWritePreview:
    def test_preview_generated_not_executed(self, dev_home: str) -> None:
        preview = build_provider_write_preview(
            "draft a sandbox note please", "dev_sandbox_file_write", hermes_home=dev_home
        )
        assert preview["providerSuggested"] is True
        assert preview["providerToolCallParsed"] is True
        assert preview["writePreviewGenerated"] is True
        assert preview["writeExecuted"] is False
        assert preview["requiresUserConfirmation"] is True
        assert preview["blockedReason"] == BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED

    def test_preview_does_not_write_file(self, dev_home: str) -> None:
        build_provider_write_preview(
            "draft another note", "dev_sandbox_file_write", hermes_home=dev_home
        )
        sandbox = Path(dev_home) / "gateway/dev/tool-write-sandbox"
        if sandbox.exists():
            files = list(sandbox.rglob("*.md"))
            assert files == [], "provider write preview must not create any file"

    def test_preview_carries_plan_and_token(self, dev_home: str) -> None:
        preview = build_provider_write_preview(
            "draft a note", "dev_sandbox_file_write", hermes_home=dev_home
        )
        assert preview["writePlanId"]
        assert preview["confirmationToken"]
        assert preview["argumentDigest"]
        assert preview["targetRelativePath"].endswith(".md")


class TestProviderWriteApi:
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
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "blocked"
        assert data["writeExecuted"] is False
        assert data["writePreviewGenerated"] is True
        assert data["blockedReason"] == BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED
        assert "writePreview" in data
        assert data["externalNetworkCalled"] is False

    def test_api_provider_write_no_file_written(self, dev_home: str) -> None:
        from fastapi.testclient import TestClient
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=Path(dev_home)))
        client = TestClient(app)
        client.post(
            "/api/dev/v1/tools/execute",
            json={
                "mode": "provider_roundtrip",
                "providerMode": "fake",
                "message": "draft a sandbox note please",
                "allowedToolIds": ["dev_sandbox_file_write"],
                "providerWriteMode": "preview_only",
            },
        )
        sandbox = Path(dev_home) / "gateway/dev/tool-write-sandbox"
        if sandbox.exists():
            assert list(sandbox.rglob("*.md")) == []

    def test_real_provider_write_blocked(self, dev_home: str) -> None:
        # Real provider mode is never wired for writes in Phase 2C.
        preview = build_provider_write_preview(
            "draft a note", "dev_sandbox_file_write",
            hermes_home=dev_home, provider_mode="real",
        )
        assert preview["writeExecuted"] is False
        assert preview["providerMode"] == "real"
        assert preview["blockedReason"] == BLOCKED_WRITE_PROVIDER_AUTO_EXECUTE_DENIED


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
