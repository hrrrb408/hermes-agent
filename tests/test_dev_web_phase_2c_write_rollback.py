"""Phase 2C — Write rollback manifest tests.

Verifies rollback manifests are built correctly for newly-created files
(delete_created_file) and replaced files (restore_previous_content), that the
restore preview is bounded and redacted, and that validation + audit redaction
hold. Automatic rollback *execution* is deferred to Phase 2C-H1 / Phase 2D.

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
"""

from __future__ import annotations

import pytest

from hermes_cli.dev_web_write_rollback import (
    RESTORE_MODE_DELETE_CREATED_FILE,
    RESTORE_MODE_RESTORE_PREVIOUS_CONTENT,
    RollbackManifest,
    build_rollback_manifest,
    redact_rollback_manifest_for_audit,
    validate_rollback_manifest,
)
from hermes_cli.dev_web_write_sandbox import compute_sha256_text


class TestRollbackManifest:
    def test_new_file_delete_mode(self) -> None:
        manifest = build_rollback_manifest(
            operation="create_or_replace",
            target_relative_path="notes/new.md",
            before_content=None,
            after_content="created",
            after_hash=compute_sha256_text("created"),
        )
        assert isinstance(manifest, RollbackManifest)
        assert manifest.before_exists is False
        assert manifest.restore_mode == RESTORE_MODE_DELETE_CREATED_FILE
        assert "delete" in manifest.restore_preview.lower()
        assert manifest.rollback_id.startswith("wrbk_")
        assert manifest.after_hash == compute_sha256_text("created")

    def test_replace_restore_mode(self) -> None:
        manifest = build_rollback_manifest(
            operation="create_or_replace",
            target_relative_path="notes/existing.md",
            before_content="old",
            after_content="new",
            after_hash=compute_sha256_text("new"),
        )
        assert manifest.before_exists is True
        assert manifest.before_hash == compute_sha256_text("old")
        assert manifest.restore_mode == RESTORE_MODE_RESTORE_PREVIOUS_CONTENT
        assert "restore" in manifest.restore_preview.lower()

    def test_append_restore_mode(self) -> None:
        manifest = build_rollback_manifest(
            operation="append",
            target_relative_path="log.md",
            before_content="line1\n",
            after_content="line1\nline2\n",
            after_hash=compute_sha256_text("line1\nline2\n"),
        )
        assert manifest.restore_mode == RESTORE_MODE_RESTORE_PREVIOUS_CONTENT

    def test_manifest_to_dict_roundtrip(self) -> None:
        manifest = build_rollback_manifest(
            operation="create_or_replace",
            target_relative_path="a.md",
            before_content=None,
            after_content="x",
            after_hash=compute_sha256_text("x"),
        )
        d = manifest.to_dict()
        assert d["rollbackId"] == manifest.rollback_id
        assert d["restoreMode"] == RESTORE_MODE_DELETE_CREATED_FILE


class TestRollbackValidation:
    def test_valid_manifest_passes(self) -> None:
        manifest = build_rollback_manifest(
            operation="create_or_replace",
            target_relative_path="a.md",
            before_content=None,
            after_content="x",
            after_hash=compute_sha256_text("x"),
        )
        ok, errors = validate_rollback_manifest(manifest)
        assert ok, errors

    def test_missing_field_rejected(self) -> None:
        ok, errors = validate_rollback_manifest({"rollbackId": "x"})
        assert ok is False
        assert errors

    def test_invalid_restore_mode_rejected(self) -> None:
        manifest = build_rollback_manifest(
            operation="create_or_replace",
            target_relative_path="a.md",
            before_content=None,
            after_content="x",
            after_hash=compute_sha256_text("x"),
        )
        # Mutate via a raw dict to inject an invalid mode.
        bad = manifest.to_dict()
        bad["restoreMode"] = "nuke_everything"
        ok, errors = validate_rollback_manifest(bad)
        assert ok is False


class TestRollbackRedaction:
    def test_redaction_strips_secrets(self) -> None:
        manifest = build_rollback_manifest(
            operation="create_or_replace",
            target_relative_path="notes/leak.md",
            before_content=None,
            after_content="sk-abcdefghijklmnopqrstuvwxyz",
            after_hash="h",
        )
        safe = redact_rollback_manifest_for_audit(manifest)
        blob = repr(safe)
        assert "sk-abcdefghijklmnopqrstuvwxyz" not in blob
        assert safe["redactionApplied"] is True

    def test_redaction_carries_hashes(self) -> None:
        manifest = build_rollback_manifest(
            operation="create_or_replace",
            target_relative_path="a.md",
            before_content="old",
            after_content="new",
            after_hash=compute_sha256_text("new"),
        )
        safe = redact_rollback_manifest_for_audit(manifest)
        assert safe["beforeHash"] == compute_sha256_text("old")
        assert safe["afterHash"] == compute_sha256_text("new")
        assert safe["restoreMode"] == RESTORE_MODE_RESTORE_PREVIOUS_CONTENT


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
