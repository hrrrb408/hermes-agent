"""Phase 2C-H1 — Rollback manifest store tests.

Verifies the manifest store: save/load/list/mark_executed, rollbackId path
traversal is blocked, tampered manifests are rejected, and the store lives
under the dev HERMES_HOME (never repo / ~/.hermes / production).

Phase: 2C-H1 — Write Execution Hardening
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_write_rollback import (
    RESTORE_MODE_DELETE_CREATED_FILE,
    RESTORE_MODE_RESTORE_PREVIOUS_CONTENT,
    build_rollback_manifest,
)
from hermes_cli.dev_web_write_rollback_store import (
    PRODUCTION_HERMES_HOME,
    ROLLBACK_DIR_RELATIVE,
    is_valid_rollback_id,
    list_rollback_manifests,
    load_rollback_manifest,
    mark_rollback_executed,
    redact_rollback_manifest_for_audit,
    save_rollback_manifest,
    validate_rollback_manifest_for_execution,
)


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return str(home)


def _manifest(restore_mode=RESTORE_MODE_DELETE_CREATED_FILE, before=None):
    return build_rollback_manifest(
        operation="create_or_replace",
        target_relative_path="notes/a.md",
        before_content=before,
        after_content="created",
        after_hash="a" * 64,
    )


class TestRollbackIdValidation:
    @pytest.mark.parametrize("rid", ["../escape", "/abs", "a/b", "wrbk_x", "wrbk_", "wrbk_GGGG", "a..b"])
    def test_invalid_rollback_id(self, rid: str) -> None:
        assert is_valid_rollback_id(rid) is False

    def test_valid_rollback_id(self) -> None:
        assert is_valid_rollback_id("wrbk_" + "0" * 24) is True


class TestSaveLoad:
    def test_save_then_load(self, dev_home: str) -> None:
        m = _manifest()
        rid = save_rollback_manifest(
            m, before_content=None, write_execution_id="wexe_1", write_plan_id="wpln_1",
            post_execution_audit_id="wau_1", hermes_home=dev_home,
        )
        assert rid == m.rollback_id
        data = load_rollback_manifest(rid, hermes_home=dev_home)
        assert data is not None
        assert data["rollbackId"] == rid
        assert data["restoreMode"] == RESTORE_MODE_DELETE_CREATED_FILE
        assert data["executed"] is False
        # Stored under the dev home rollback dir.
        manifest_file = Path(dev_home) / ROLLBACK_DIR_RELATIVE / f"{rid}.json"
        assert manifest_file.exists()

    def test_before_content_stored_for_restore(self, dev_home: str) -> None:
        m = _manifest(restore_mode=RESTORE_MODE_RESTORE_PREVIOUS_CONTENT, before="old")
        rid = save_rollback_manifest(
            m, before_content="old", write_execution_id="wexe_1", write_plan_id="wpln_1",
            post_execution_audit_id="wau_1", hermes_home=dev_home,
        )
        data = load_rollback_manifest(rid, hermes_home=dev_home)
        assert data["beforeContent"] == "old"

    def test_save_rejects_invalid_rollback_id(self, dev_home: str) -> None:
        m = _manifest()
        # Tamper the rollbackId to something invalid.
        bad = m.to_dict()
        bad["rollbackId"] = "../escape"
        rid = save_rollback_manifest(
            bad, before_content=None, write_execution_id="x", write_plan_id="x",
            post_execution_audit_id="x", hermes_home=dev_home,
        )
        assert rid is None

    def test_production_home_rejected(self) -> None:
        m = _manifest()
        rid = save_rollback_manifest(
            m, before_content=None, write_execution_id="x", write_plan_id="x",
            post_execution_audit_id="x", hermes_home=PRODUCTION_HERMES_HOME,
        )
        assert rid is None


class TestList:
    def test_list_returns_safe_summaries(self, dev_home: str) -> None:
        m = _manifest()
        save_rollback_manifest(
            m, before_content=None, write_execution_id="x", write_plan_id="x",
            post_execution_audit_id="x", hermes_home=dev_home,
        )
        items = list_rollback_manifests(hermes_home=dev_home)
        assert len(items) == 1
        # beforeContent / canonicalTargetPath must NOT appear in the summary.
        assert "beforeContent" not in items[0]
        assert "canonicalTargetPath" not in items[0]
        assert items[0]["rollbackId"] == m.rollback_id


class TestMarkExecuted:
    def test_mark_executed_persists(self, dev_home: str) -> None:
        m = _manifest()
        rid = save_rollback_manifest(
            m, before_content=None, write_execution_id="x", write_plan_id="x",
            post_execution_audit_id="x", hermes_home=dev_home,
        )
        ok = mark_rollback_executed(rid, execution_id="rbexe_1", hermes_home=dev_home)
        assert ok is True
        data = load_rollback_manifest(rid, hermes_home=dev_home)
        assert data["executed"] is True
        assert data["executionId"] == "rbexe_1"


class TestValidation:
    def test_valid_manifest_passes(self, dev_home: str) -> None:
        m = _manifest()
        rid = save_rollback_manifest(
            m, before_content=None, write_execution_id="x", write_plan_id="x",
            post_execution_audit_id="x", hermes_home=dev_home,
        )
        data = load_rollback_manifest(rid, hermes_home=dev_home)
        ok, errors = validate_rollback_manifest_for_execution(data)
        assert ok, errors

    def test_tampered_manifest_rejected(self, dev_home: str) -> None:
        m = _manifest(restore_mode=RESTORE_MODE_RESTORE_PREVIOUS_CONTENT, before="old")
        rid = save_rollback_manifest(
            m, before_content="old", write_execution_id="x", write_plan_id="x",
            post_execution_audit_id="x", hermes_home=dev_home,
        )
        data = load_rollback_manifest(rid, hermes_home=dev_home)
        # Tamper: drop beforeContent -> restore mode needs it.
        data["beforeContent"] = None
        ok, errors = validate_rollback_manifest_for_execution(data)
        assert ok is False

    def test_redaction_drops_before_content(self, dev_home: str) -> None:
        m = _manifest(restore_mode=RESTORE_MODE_RESTORE_PREVIOUS_CONTENT, before="secret-body")
        rid = save_rollback_manifest(
            m, before_content="secret-body", write_execution_id="x", write_plan_id="x",
            post_execution_audit_id="x", hermes_home=dev_home,
        )
        data = load_rollback_manifest(rid, hermes_home=dev_home)
        safe = redact_rollback_manifest_for_audit(data)
        assert "beforeContent" not in safe
        assert "secret-body" not in json.dumps(safe)
        assert safe["redactionApplied"] is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
