"""Phase 2C-H1 — Rollback execution tests.

Verifies the full controlled rollback chain: delete_created_file and
restore_previous_content both work inside the sandbox; current-hash mismatch,
already-executed, tamper, symlink escape, and outside-sandbox are blocked;
enablement, confirmation, and digest gates are enforced.

Phase: 2C-H1 — Write Execution Hardening
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hermes_cli.dev_web_write_handlers import dispatch_rollback_tool, dispatch_write_tool
from hermes_cli.dev_web_write_plan import build_write_preview, _reset_confirmation_state_for_tests
from hermes_cli.dev_web_write_rollback import build_rollback_execution_preview


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_TOOL_WRITE_EXECUTION_ENABLED", "1")
    _reset_confirmation_state_for_tests()
    return str(home)


def _write(dev_home: str, target: str, content: str) -> str:
    """Write a file via the controlled chain and return its rollbackId."""
    preview = build_write_preview(
        "dev_sandbox_file_write", {"targetPath": target, "content": content}, hermes_home=dev_home
    )
    assert preview["blocked"] is False
    ctx = {
        "writePlanId": preview["writePlanId"],
        "confirmationToken": preview["confirmationToken"],
        "argumentDigest": preview["argumentDigest"],
    }
    result = dispatch_write_tool(
        "dev_sandbox_file_write", {"targetPath": target, "content": content},
        context=ctx, hermes_home=dev_home,
    )
    assert result.to_safe_dict()["status"] == "completed"
    return result.to_safe_dict()["rollbackId"]


def _rollback(dev_home: str, rollback_id: str, *, token: str | None = None, digest: str | None = None):
    preview = build_rollback_execution_preview(rollback_id, hermes_home=dev_home)
    ctx = {
        "confirmationToken": token if token is not None else preview["confirmationToken"],
        "argumentDigest": digest if digest is not None else preview["argumentDigest"],
    }
    return dispatch_rollback_tool(rollback_id, context=ctx, hermes_home=dev_home)


class TestRollbackPreview:
    def test_preview_for_delete_created(self, dev_home: str) -> None:
        rid = _write(dev_home, "notes/a.md", "created")
        preview = build_rollback_execution_preview(rid, hermes_home=dev_home)
        assert preview["blocked"] is False
        assert preview["restoreMode"] == "delete_created_file"
        assert preview["confirmationToken"]
        assert preview["currentHash"] == preview["afterHash"]

    def test_preview_not_found(self, dev_home: str) -> None:
        preview = build_rollback_execution_preview("wrbk_" + "0" * 24, hermes_home=dev_home)
        assert preview["blocked"] is True
        assert preview["blockedReason"] == "blocked_rollback_manifest_not_found"


class TestDeleteCreatedRollback:
    def test_delete_created_file(self, dev_home: str) -> None:
        target = Path(dev_home) / "gateway/dev/tool-write-sandbox/notes/a.md"
        rid = _write(dev_home, "notes/a.md", "created")
        assert target.exists()
        result = _rollback(dev_home, rid)
        d = result.to_safe_dict()
        assert d["status"] == "completed"
        assert d["restoreMode"] == "delete_created_file"
        assert d["finalHash"] is None
        assert d["postExecutionAuditId"]
        assert target.exists() is False  # file deleted


class TestRestorePreviousRollback:
    def test_restore_previous_content(self, dev_home: str) -> None:
        # Create original, then replace it.
        _write(dev_home, "p.md", "original")
        rid = _write(dev_home, "p.md", "REPLACED")
        target = Path(dev_home) / "gateway/dev/tool-write-sandbox/p.md"
        assert target.read_text(encoding="utf-8") == "REPLACED"
        result = _rollback(dev_home, rid)
        d = result.to_safe_dict()
        assert d["status"] == "completed"
        assert d["restoreMode"] == "restore_previous_content"
        assert target.read_text(encoding="utf-8") == "original"


class TestBlockedCases:
    def test_current_hash_mismatch_blocked(self, dev_home: str) -> None:
        rid = _write(dev_home, "h.md", "v1")
        # Mutate the file out from under the rollback.
        target = Path(dev_home) / "gateway/dev/tool-write-sandbox/h.md"
        target.write_text("MUTATED", encoding="utf-8")
        result = _rollback(dev_home, rid)
        assert result.to_safe_dict()["blockedReason"] == "blocked_rollback_current_hash_mismatch"

    def test_already_executed_blocked(self, dev_home: str) -> None:
        rid = _write(dev_home, "e.md", "x")
        r1 = _rollback(dev_home, rid)
        assert r1.to_safe_dict()["status"] == "completed"
        # Replay → manifest already executed.
        r2 = _rollback(dev_home, rid)
        assert r2.to_safe_dict()["blockedReason"] == "blocked_rollback_already_executed"

    def test_write_disabled_blocked(self, dev_home: str, monkeypatch) -> None:
        rid = _write(dev_home, "d.md", "x")
        monkeypatch.delenv("HERMES_TOOL_WRITE_EXECUTION_ENABLED", raising=False)
        result = _rollback(dev_home, rid)
        assert result.to_safe_dict()["blockedReason"] == "blocked_rollback_write_not_enabled"

    def test_missing_confirmation_blocked(self, dev_home: str) -> None:
        rid = _write(dev_home, "c.md", "x")
        preview = build_rollback_execution_preview(rid, hermes_home=dev_home)
        result = dispatch_rollback_tool(
            rid, context={"confirmationToken": None, "argumentDigest": preview["argumentDigest"]},
            hermes_home=dev_home,
        )
        assert result.to_safe_dict()["blockedReason"] == "blocked_rollback_confirmation_required"

    def test_digest_mismatch_blocked(self, dev_home: str) -> None:
        rid = _write(dev_home, "dg.md", "x")
        preview = build_rollback_execution_preview(rid, hermes_home=dev_home)
        result = dispatch_rollback_tool(
            rid,
            context={"confirmationToken": preview["confirmationToken"], "argumentDigest": "0" * 64},
            hermes_home=dev_home,
        )
        assert result.to_safe_dict()["blockedReason"] == "blocked_rollback_digest_mismatch"

    def test_symlink_escape_blocked(self, dev_home: str) -> None:
        rid = _write(dev_home, "sym.md", "x")
        # Replace the sandbox target with a symlink escaping the sandbox. The
        # outside file holds the SAME content ("x") so the current-hash check
        # would pass — the symlink-escape check must block before any delete.
        target = Path(dev_home) / "gateway/dev/tool-write-sandbox/sym.md"
        target.unlink()
        outside = Path(dev_home).parent / "escape-target.txt"
        outside.write_text("x", encoding="utf-8")
        try:
            os.symlink(outside, target)
        except OSError:
            pytest.skip("symlink not supported")
        result = _rollback(dev_home, rid)
        assert result.to_safe_dict()["status"] == "blocked"
        # The escaped file must NOT have been deleted by the rollback.
        assert outside.exists()
        assert outside.read_text(encoding="utf-8") == "x"


class TestSandboxOnly:
    def test_rollback_target_must_be_in_sandbox(self, dev_home: str) -> None:
        # A manifest whose targetRelativePath is traversal is rejected at the
        # sandbox validation stage. Build a manifest store entry manually with
        # a traversal target via save.
        from hermes_cli.dev_web_write_rollback import build_rollback_manifest
        from hermes_cli.dev_web_write_rollback_store import save_rollback_manifest

        m = build_rollback_manifest(
            operation="create_or_replace", target_relative_path="../escape.md",
            before_content=None, after_content="x", after_hash="x",
        )
        # Patch the rollbackId to be valid-shaped but keep the traversal target.
        rid = save_rollback_manifest(
            m, before_content=None, write_execution_id="x", write_plan_id="x",
            post_execution_audit_id="x", hermes_home=dev_home,
        )
        preview = build_rollback_execution_preview(rid, hermes_home=dev_home)
        assert preview["blocked"] is True
        assert preview["blockedReason"] in (
            "blocked_rollback_target_escape", "blocked_rollback_current_hash_mismatch",
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
