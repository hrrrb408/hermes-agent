"""Phase 2C — Write plan / preview tests.

Verifies the dry-run plan computes correct before/after hashes, diff and
rollback previews, argument digest stability, precise blocked reasons, that the
preview issues a confirmation token, and that building a plan/preview NEVER
writes a file.

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.dev_web_write_plan import (
    BLOCKED_WRITE_ABSOLUTE_PATH,
    BLOCKED_WRITE_BINARY_CONTENT,
    BLOCKED_WRITE_CONTENT_TOO_LARGE,
    BLOCKED_WRITE_FORBIDDEN_PATH,
    BLOCKED_WRITE_MISSING_ROLLBACK_PLAN,
    BLOCKED_WRITE_PATCH_NO_UNIQUE_MATCH,
    BLOCKED_WRITE_PATH_TRAVERSAL,
    BLOCKED_WRITE_TOOL_NOT_SUPPORTED,
    build_write_plan,
    build_write_preview,
    compute_argument_digest,
    issue_write_confirmation_token,
    redact_write_plan_for_audit,
    validate_write_plan,
    verify_write_confirmation_token,
    _reset_confirmation_state_for_tests,
)
from hermes_cli.dev_web_write_sandbox import compute_sha256_text


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    _reset_confirmation_state_for_tests()
    return str(home)


class TestPlanBuilding:
    def test_plan_for_new_file(self, dev_home: str) -> None:
        plan = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "notes/a.md", "content": "hello"},
            hermes_home=dev_home,
        )
        assert plan.blocked is False
        assert plan.before_exists is False
        assert plan.before_hash is None
        assert plan.after_hash == compute_sha256_text("hello")
        assert plan.content_digest == compute_sha256_text("hello")
        assert plan.operation == "create_or_replace"
        assert plan.rollback_preview  # non-empty
        assert plan.argument_digest == compute_argument_digest(
            "dev_sandbox_file_write", {"targetPath": "notes/a.md", "content": "hello", "mode": "create_or_replace"}
        )

    def test_plan_for_replace(self, dev_home: str) -> None:
        # Seed the file first.
        plan1 = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "notes/a.md", "content": "old"},
            hermes_home=dev_home,
        )
        from hermes_cli.dev_web_write_handlers import dispatch_write_tool  # noqa
        # Actually write via dispatch to seed state (enablement on).
        import os

        os.environ["HERMES_TOOL_WRITE_EXECUTION_ENABLED"] = "1"
        ctx = {
            "writePlanId": plan1.write_plan_id,
            "confirmationToken": issue_write_confirmation_token(plan1.write_plan_id, plan1.argument_digest),
            "argumentDigest": plan1.argument_digest,
        }
        dispatch_write_tool(
            "dev_sandbox_file_write",
            {"targetPath": "notes/a.md", "content": "old"},
            context=ctx, hermes_home=dev_home,
        )
        del os.environ["HERMES_TOOL_WRITE_EXECUTION_ENABLED"]

        # Now a plan to replace should see before_exists True.
        plan2 = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "notes/a.md", "content": "new"},
            hermes_home=dev_home,
        )
        assert plan2.blocked is False
        assert plan2.before_exists is True
        assert plan2.before_hash == compute_sha256_text("old")
        assert plan2.after_hash == compute_sha256_text("new")

    def test_plan_append(self, dev_home: str) -> None:
        plan = build_write_plan(
            "dev_sandbox_file_append",
            {"targetPath": "log.md", "content": "line"},
            hermes_home=dev_home,
        )
        assert plan.blocked is False
        assert plan.operation == "append"

    def test_plan_patch_no_match_blocked(self, dev_home: str) -> None:
        # File does not exist -> patch blocked.
        plan = build_write_plan(
            "dev_sandbox_file_patch",
            {"targetPath": "p.md", "search": "x", "replace": "y"},
            hermes_home=dev_home,
        )
        assert plan.blocked is True
        assert plan.blocked_reason == BLOCKED_WRITE_PATCH_NO_UNIQUE_MATCH

    def test_plan_readback(self, dev_home: str) -> None:
        plan = build_write_plan(
            "dev_sandbox_file_readback",
            {"targetPath": "rb.md"},
            hermes_home=dev_home,
        )
        assert plan.blocked is False
        assert plan.operation == "readback"

    def test_plan_unknown_tool_blocked(self, dev_home: str) -> None:
        plan = build_write_plan("not_a_tool", {"targetPath": "a.md"}, hermes_home=dev_home)
        assert plan.blocked is True
        assert plan.blocked_reason == BLOCKED_WRITE_TOOL_NOT_SUPPORTED


class TestPlanBlockedReasons:
    def test_traversal_blocked(self, dev_home: str) -> None:
        plan = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "../escape.md", "content": "x"},
            hermes_home=dev_home,
        )
        assert plan.blocked is True
        assert plan.blocked_reason == BLOCKED_WRITE_PATH_TRAVERSAL

    def test_absolute_blocked(self, dev_home: str) -> None:
        plan = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "/etc/passwd", "content": "x"},
            hermes_home=dev_home,
        )
        assert plan.blocked is True
        assert plan.blocked_reason == BLOCKED_WRITE_ABSOLUTE_PATH

    def test_forbidden_env_blocked(self, dev_home: str) -> None:
        plan = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "bad/.env", "content": "x"},
            hermes_home=dev_home,
        )
        assert plan.blocked is True
        assert plan.blocked_reason == BLOCKED_WRITE_FORBIDDEN_PATH

    def test_forbidden_db_blocked(self, dev_home: str) -> None:
        plan = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "a/state.db", "content": "x"},
            hermes_home=dev_home,
        )
        assert plan.blocked is True
        assert plan.blocked_reason == BLOCKED_WRITE_FORBIDDEN_PATH

    def test_forbidden_jsonl_blocked(self, dev_home: str) -> None:
        plan = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "a/x.jsonl", "content": "x"},
            hermes_home=dev_home,
        )
        assert plan.blocked is True
        assert plan.blocked_reason == BLOCKED_WRITE_FORBIDDEN_PATH

    def test_binary_content_blocked(self, dev_home: str) -> None:
        binary = "".join(chr(i) for i in range(1, 200))
        plan = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": binary},
            hermes_home=dev_home,
        )
        assert plan.blocked is True
        assert plan.blocked_reason == BLOCKED_WRITE_BINARY_CONTENT

    def test_content_too_large_blocked(self, dev_home: str) -> None:
        plan = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x" * (64 * 1024 + 1)},
            hermes_home=dev_home,
        )
        assert plan.blocked is True
        assert plan.blocked_reason == BLOCKED_WRITE_CONTENT_TOO_LARGE

    def test_production_home_blocked(self) -> None:
        plan = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x"},
            hermes_home="/Users/huangruibang/.hermes",
        )
        assert plan.blocked is True
        assert plan.blocked_reason == BLOCKED_WRITE_FORBIDDEN_PATH


class TestPlanValidation:
    def test_valid_plan_passes(self, dev_home: str) -> None:
        plan = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x"},
            hermes_home=dev_home,
        )
        ok, errors = validate_write_plan(plan)
        assert ok, errors

    def test_redaction_excludes_raw_args(self, dev_home: str) -> None:
        plan = build_write_plan(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "sensitive-content"},
            hermes_home=dev_home,
        )
        safe = redact_write_plan_for_audit(plan)
        blob = repr(safe)
        assert "canonicalTargetPath" not in safe
        assert "normalizedArgs" not in safe
        # The full raw content must not appear as a raw-arguments field.
        assert "rawArguments" not in blob
        assert "argumentsPreview" not in blob


class TestPreviewNoWrite:
    def test_preview_does_not_write_file(self, dev_home: str) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write",
            {"targetPath": "notes/never.md", "content": "x"},
            hermes_home=dev_home,
        )
        assert preview["blocked"] is False
        assert preview["confirmationToken"]
        target = Path(dev_home) / "gateway/dev/tool-write-sandbox/notes/never.md"
        assert target.exists() is False

    def test_preview_issues_token_bound_to_plan(self, dev_home: str) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x"},
            hermes_home=dev_home,
        )
        ok, err = verify_write_confirmation_token(
            preview["confirmationToken"],
            preview["writePlanId"],
            preview["argumentDigest"],
            consume=False,
        )
        assert ok is True and err is None

    def test_preview_token_rejects_wrong_digest(self, dev_home: str) -> None:
        preview = build_write_preview(
            "dev_sandbox_file_write",
            {"targetPath": "a.md", "content": "x"},
            hermes_home=dev_home,
        )
        ok, _ = verify_write_confirmation_token(
            preview["confirmationToken"],
            preview["writePlanId"],
            "0" * 64,
            consume=False,
        )
        assert ok is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
