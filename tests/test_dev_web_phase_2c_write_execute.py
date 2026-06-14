"""Phase 2C — Write execution (dispatch chain) tests.

Verifies the full controlled-write dispatch chain: write-enablement gate,
argument digest verification, confirmation token verification (missing /
wrong / single-use replay), the four handlers (write / append / patch /
readback), rollback manifest creation, pre/post execution audit ids, the
side-effect flags (no provider, no external network), and that the result
exposes no raw arguments or secrets.

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from hermes_cli.dev_web_write_handlers import dispatch_write_tool
from hermes_cli.dev_web_write_plan import (
    BLOCKED_WRITE_CONFIRMATION_REQUIRED,
    BLOCKED_WRITE_DIGEST_MISMATCH,
    BLOCKED_WRITE_EXECUTION_NOT_ENABLED,
    build_write_preview,
    issue_write_confirmation_token,
    _reset_confirmation_state_for_tests,
)
from hermes_cli.dev_web_write_sandbox import compute_sha256_text


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_TOOL_WRITE_EXECUTION_ENABLED", "1")
    _reset_confirmation_state_for_tests()
    return str(home)


def _preview_and_args(dev_home: str, tool_id: str, args: dict[str, Any]) -> dict[str, Any]:
    """Build a preview and return the execute context (writePlanId/digest/token)."""
    preview = build_write_preview(tool_id, args, hermes_home=dev_home)
    assert preview["blocked"] is False, preview
    return {
        "writePlanId": preview["writePlanId"],
        "confirmationToken": preview["confirmationToken"],
        "argumentDigest": preview["argumentDigest"],
    }


# ---------------------------------------------------------------------------
# 1. Enablement gate
# ---------------------------------------------------------------------------


class TestEnablementGate:
    def test_write_disabled_blocked(self, dev_home: str, monkeypatch) -> None:
        monkeypatch.delenv("HERMES_TOOL_WRITE_EXECUTION_ENABLED", raising=False)
        ctx = _preview_and_args(dev_home, "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"})
        result = dispatch_write_tool(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x"},
            context=ctx, hermes_home=dev_home,
        )
        d = result.to_safe_dict()
        assert d["status"] == "blocked"
        assert d["blockedReason"] == BLOCKED_WRITE_EXECUTION_NOT_ENABLED


# ---------------------------------------------------------------------------
# 2. Confirmation + digest gates
# ---------------------------------------------------------------------------


class TestConfirmationAndDigest:
    def test_missing_confirmation_blocked(self, dev_home: str) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"}, hermes_home=dev_home
        )
        ctx = {"writePlanId": preview["writePlanId"], "argumentDigest": preview["argumentDigest"]}
        result = dispatch_write_tool(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x"},
            context=ctx, hermes_home=dev_home,
        )
        assert result.to_safe_dict()["blockedReason"] == BLOCKED_WRITE_CONFIRMATION_REQUIRED

    def test_wrong_confirmation_blocked(self, dev_home: str) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"}, hermes_home=dev_home
        )
        ctx = {
            "writePlanId": preview["writePlanId"],
            "confirmationToken": "wctok_deadbeef" + "0" * 30,
            "argumentDigest": preview["argumentDigest"],
        }
        result = dispatch_write_tool(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x"},
            context=ctx, hermes_home=dev_home,
        )
        assert result.to_safe_dict()["blockedReason"] == BLOCKED_WRITE_CONFIRMATION_REQUIRED

    def test_digest_mismatch_blocked(self, dev_home: str) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"}, hermes_home=dev_home
        )
        ctx = {
            "writePlanId": preview["writePlanId"],
            "confirmationToken": issue_write_confirmation_token(
                preview["writePlanId"], "0" * 64
            ),
            "argumentDigest": "0" * 64,
        }
        result = dispatch_write_tool(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x"},
            context=ctx, hermes_home=dev_home,
        )
        assert result.to_safe_dict()["blockedReason"] == BLOCKED_WRITE_DIGEST_MISMATCH

    def test_token_single_use_replay_blocked(self, dev_home: str) -> None:
        ctx = _preview_and_args(dev_home, "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"})
        r1 = dispatch_write_tool(
            "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"},
            context=ctx, hermes_home=dev_home,
        )
        assert r1.to_safe_dict()["status"] == "completed"
        r2 = dispatch_write_tool(
            "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"},
            context=ctx, hermes_home=dev_home,
        )
        assert r2.to_safe_dict()["blockedReason"] == BLOCKED_WRITE_CONFIRMATION_REQUIRED


# ---------------------------------------------------------------------------
# 3. Successful execution of each tool
# ---------------------------------------------------------------------------


class TestSuccessfulExecution:
    def test_write_completes_with_rollback(self, dev_home: str) -> None:
        ctx = _preview_and_args(dev_home, "dev_sandbox_file_write", {"targetPath": "notes/a.md", "content": "hello"})
        result = dispatch_write_tool(
            "dev_sandbox_file_write", {"targetPath": "notes/a.md", "content": "hello"},
            context=ctx, hermes_home=dev_home,
        )
        d = result.to_safe_dict()
        assert d["status"] == "completed"
        assert d["bytesWritten"] == len("hello")
        assert d["rollbackAvailable"] is True
        assert d["rollbackId"]
        assert d["afterHash"] == compute_sha256_text("hello")
        assert d["preExecutionAuditId"]
        assert d["postExecutionAuditId"]
        # File actually written inside the sandbox.
        target = Path(dev_home) / "gateway/dev/tool-write-sandbox/notes/a.md"
        assert target.read_text(encoding="utf-8") == "hello"

    def test_append_completes(self, dev_home: str) -> None:
        # Seed with a write first.
        ctx0 = _preview_and_args(dev_home, "dev_sandbox_file_write", {"targetPath": "log.md", "content": "line1\n"})
        dispatch_write_tool("dev_sandbox_file_write", {"targetPath": "log.md", "content": "line1\n"}, context=ctx0, hermes_home=dev_home)
        ctx = _preview_and_args(dev_home, "dev_sandbox_file_append", {"targetPath": "log.md", "content": "line2\n"})
        result = dispatch_write_tool("dev_sandbox_file_append", {"targetPath": "log.md", "content": "line2\n"}, context=ctx, hermes_home=dev_home)
        assert result.to_safe_dict()["status"] == "completed"
        target = Path(dev_home) / "gateway/dev/tool-write-sandbox/log.md"
        assert target.read_text(encoding="utf-8") == "line1\nline2\n"

    def test_patch_completes(self, dev_home: str) -> None:
        ctx0 = _preview_and_args(dev_home, "dev_sandbox_file_write", {"targetPath": "p.md", "content": "alpha beta"})
        dispatch_write_tool("dev_sandbox_file_write", {"targetPath": "p.md", "content": "alpha beta"}, context=ctx0, hermes_home=dev_home)
        ctx = _preview_and_args(dev_home, "dev_sandbox_file_patch", {"targetPath": "p.md", "search": "beta", "replace": "gamma"})
        result = dispatch_write_tool("dev_sandbox_file_patch", {"targetPath": "p.md", "search": "beta", "replace": "gamma"}, context=ctx, hermes_home=dev_home)
        assert result.to_safe_dict()["status"] == "completed"
        target = Path(dev_home) / "gateway/dev/tool-write-sandbox/p.md"
        assert target.read_text(encoding="utf-8") == "alpha gamma"

    def test_readback_completes_no_rollback(self, dev_home: str) -> None:
        ctx0 = _preview_and_args(dev_home, "dev_sandbox_file_write", {"targetPath": "rb.md", "content": "data"})
        dispatch_write_tool("dev_sandbox_file_write", {"targetPath": "rb.md", "content": "data"}, context=ctx0, hermes_home=dev_home)
        ctx = _preview_and_args(dev_home, "dev_sandbox_file_readback", {"targetPath": "rb.md"})
        result = dispatch_write_tool("dev_sandbox_file_readback", {"targetPath": "rb.md"}, context=ctx, hermes_home=dev_home)
        d = result.to_safe_dict()
        assert d["status"] == "completed"
        assert d["rollbackAvailable"] is False
        assert d["rollbackId"] is None
        assert d["readback"]["exists"] is True
        assert d["readback"]["contentHash"] == compute_sha256_text("data")


# ---------------------------------------------------------------------------
# 4. Side-effect flags + no secret leak
# ---------------------------------------------------------------------------


class TestSideEffectsAndSafety:
    def test_no_external_side_effects(self, dev_home: str) -> None:
        ctx = _preview_and_args(dev_home, "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"})
        d = dispatch_write_tool(
            "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"},
            context=ctx, hermes_home=dev_home,
        ).to_safe_dict()
        assert d["externalSideEffects"] is False
        assert d["externalNetworkCalled"] is False
        assert d["providerApiCalled"] is False
        assert d["providerSchemaSent"] is False
        assert d["writeRequired"] is True
        assert d["localSideEffects"] is True
        assert d["readOnly"] is False

    def test_result_has_no_raw_args_or_secrets(self, dev_home: str) -> None:
        ctx = _preview_and_args(dev_home, "dev_sandbox_file_write", {"targetPath": "a.md", "content": "sensitive-body"})
        d = dispatch_write_tool(
            "dev_sandbox_file_write", {"targetPath": "a.md", "content": "sensitive-body"},
            context=ctx, hermes_home=dev_home,
        ).to_safe_dict()
        blob = repr(d)
        assert "rawArguments" not in blob
        assert "argumentsPreview" not in blob
        # No callable / function repr.
        assert "<function" not in blob
        assert "<bound method" not in blob

    def test_write_only_inside_sandbox(self, dev_home: str) -> None:
        # The target must resolve under the sandbox; a traversal target is
        # blocked at the plan stage even when enablement is on.
        preview = build_write_preview(
            "dev_sandbox_file_write",
            {"targetPath": "../escape.md", "content": "x"},
            hermes_home=dev_home,
        )
        assert preview["blocked"] is True
        ctx = {
            "writePlanId": preview["writePlanId"],
            "confirmationToken": "wctok_" + "0" * 40,
            "argumentDigest": preview["argumentDigest"],
        }
        result = dispatch_write_tool(
            "dev_sandbox_file_write",
            {"targetPath": "../escape.md", "content": "x"},
            context=ctx, hermes_home=dev_home,
        )
        assert result.to_safe_dict()["status"] == "blocked"
        # Nothing escaped outside the sandbox.
        escaped = Path(dev_home).parent / "escape.md"
        assert escaped.exists() is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
