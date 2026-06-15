"""Phase 2C-H1 — Rollback audit tests.

Verifies rollback lifecycle audit events are written to tool-write-audit.jsonl
(pre/post execution, handler call, manifest-marked-executed, blocked), that
confirmation token ids are recorded without their secret, and that no raw
token secret / before content leaks into the audit file.

Phase: 2C-H1 — Write Execution Hardening
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_write_handlers import dispatch_rollback_tool, dispatch_write_tool
from hermes_cli.dev_web_write_plan import (
    EVENT_ROLLBACK_HANDLER_CALLED,
    EVENT_ROLLBACK_MANIFEST_MARKED_EXECUTED,
    EVENT_ROLLBACK_POST_EXECUTION_AUDIT,
    EVENT_ROLLBACK_PRE_EXECUTION_AUDIT,
    build_write_preview,
    _reset_confirmation_state_for_tests,
)
from hermes_cli.dev_web_write_rollback import build_rollback_execution_preview


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_TOOL_WRITE_EXECUTION_ENABLED", "1")
    _reset_confirmation_state_for_tests()
    return str(home)


def _audit_events(dev_home: str) -> list[dict]:
    af = Path(dev_home) / "gateway/dev/audit/tool-write-audit.jsonl"
    if not af.exists():
        return []
    return [json.loads(line) for line in af.read_text().splitlines() if line.strip()]


def _write(dev_home: str, target: str, content: str) -> str:
    preview = build_write_preview(
        "dev_sandbox_file_write", {"targetPath": target, "content": content}, hermes_home=dev_home
    )
    ctx = {
        "writePlanId": preview["writePlanId"],
        "confirmationToken": preview["confirmationToken"],
        "argumentDigest": preview["argumentDigest"],
    }
    return dispatch_write_tool(
        "dev_sandbox_file_write", {"targetPath": target, "content": content},
        context=ctx, hermes_home=dev_home,
    ).to_safe_dict()["rollbackId"]


class TestRollbackAudit:
    def test_rollback_emits_lifecycle_events(self, dev_home: str) -> None:
        rid = _write(dev_home, "notes/a.md", "created")
        preview = build_rollback_execution_preview(rid, hermes_home=dev_home)
        dispatch_rollback_tool(
            rid,
            context={"confirmationToken": preview["confirmationToken"], "argumentDigest": preview["argumentDigest"]},
            hermes_home=dev_home,
        )
        events = _audit_events(dev_home)
        types = {e["eventType"] for e in events}
        assert EVENT_ROLLBACK_PRE_EXECUTION_AUDIT in types
        assert EVENT_ROLLBACK_HANDLER_CALLED in types
        assert EVENT_ROLLBACK_POST_EXECUTION_AUDIT in types
        assert EVENT_ROLLBACK_MANIFEST_MARKED_EXECUTED in types

    def test_rollback_audit_carries_ids(self, dev_home: str) -> None:
        rid = _write(dev_home, "notes/b.md", "created")
        preview = build_rollback_execution_preview(rid, hermes_home=dev_home)
        dispatch_rollback_tool(
            rid,
            context={"confirmationToken": preview["confirmationToken"], "argumentDigest": preview["argumentDigest"]},
            hermes_home=dev_home,
        )
        events = _audit_events(dev_home)
        post = [e for e in events if e["eventType"] == EVENT_ROLLBACK_POST_EXECUTION_AUDIT][0]
        assert post["rollbackId"] == rid
        assert post["writeRequired"] is True
        assert post["externalSideEffects"] is False
        assert post["redactionApplied"] is True

    def test_audit_no_token_secret_or_before_content(self, dev_home: str) -> None:
        # Restore rollback stores beforeContent internally.
        _write(dev_home, "p.md", "secret-before-content")
        rid = _write(dev_home, "p.md", "REPLACED")
        preview = build_rollback_execution_preview(rid, hermes_home=dev_home)
        dispatch_rollback_tool(
            rid,
            context={"confirmationToken": preview["confirmationToken"], "argumentDigest": preview["argumentDigest"]},
            hermes_home=dev_home,
        )
        blob = json.dumps(_audit_events(dev_home))
        assert "secret-before-content" not in blob
        # The token secret (the part after the dot) must not appear.
        secret = preview["confirmationToken"].split(".", 1)[1]
        assert secret not in blob

    def test_blocked_rollback_emits_blocked_event(self, dev_home: str, monkeypatch) -> None:
        rid = _write(dev_home, "x.md", "x")
        monkeypatch.delenv("HERMES_TOOL_WRITE_EXECUTION_ENABLED", raising=False)
        dispatch_rollback_tool(rid, context={"confirmationToken": "x", "argumentDigest": "x"}, hermes_home=dev_home)
        events = _audit_events(dev_home)
        blocked = [e for e in events if e["eventType"] == "rollback_execution_blocked"]
        assert len(blocked) >= 1
        assert blocked[-1]["blockedReason"] == "blocked_rollback_write_not_enabled"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
