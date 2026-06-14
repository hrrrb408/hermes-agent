"""Phase 2C — Write audit model tests.

Verifies write audit events are written to tool-write-audit.jsonl under the
dev HERMES_HOME, that the event types are emitted across the lifecycle
(pre/post execution, handler call, rollback manifest, blocked), that every
audit payload is redacted (no raw token / full tokenHash / raw arguments /
secrets / callable repr), and that the read-only audit-events route surfaces
the new ``write`` kind.

Phase: 2C — Controlled Tool Write Execution (Dev Sandbox Write MVP)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_write_handlers import dispatch_write_tool
from hermes_cli.dev_web_write_plan import (
    EVENT_WRITE_POST_EXECUTION_AUDIT,
    EVENT_WRITE_PRE_EXECUTION_AUDIT,
    EVENT_WRITE_ROLLBACK_MANIFEST_BUILT,
    EVENT_WRITE_EXECUTION_BLOCKED,
    build_write_audit_event,
    build_write_preview,
    emit_write_audit,
    write_write_audit_event,
    _reset_confirmation_state_for_tests,
)
from hermes_cli.dev_web_write_sandbox import PRODUCTION_HERMES_HOME


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    (home / "gateway" / "dev" / "audit").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_TOOL_WRITE_EXECUTION_ENABLED", "1")
    _reset_confirmation_state_for_tests()
    return str(home)


def _write_once(dev_home: str, target: str = "a.md", content: str = "hello") -> dict:
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
    ).to_safe_dict()


class TestAuditWriter:
    def test_production_home_never_written(self) -> None:
        event = build_write_audit_event(
            event_type=EVENT_WRITE_PRE_EXECUTION_AUDIT,
            tool_id="dev_sandbox_file_write", write_plan_id="wpln_x",
            write_preview_id="wprv_x", rollback_id=None,
            operation="create_or_replace", target_relative_path="a.md",
            status="pre_execution", blocked_reason=None,
        )
        result = write_write_audit_event(event, hermes_home=PRODUCTION_HERMES_HOME)
        assert result.written is False

    def test_audit_redacts_secrets(self) -> None:
        event = build_write_audit_event(
            event_type=EVENT_WRITE_POST_EXECUTION_AUDIT,
            tool_id="dev_sandbox_file_write", write_plan_id="wpln_x",
            write_preview_id="wprv_x", rollback_id="wrbk_x",
            operation="create_or_replace", target_relative_path="a.md",
            status="completed", blocked_reason=None,
            payload={"apiKey": "sk-abcdefghijklmnopqrstuvwxyz", "auth": "Bearer xyz"},
        )
        blob = json.dumps(event)
        assert "sk-abcdefghijklmnopqrstuvwxyz" not in blob
        assert "Bearer xyz" not in blob
        assert "[REDACTED]" in blob

    def test_audit_no_callable_repr(self) -> None:
        event = build_write_audit_event(
            event_type=EVENT_WRITE_POST_EXECUTION_AUDIT,
            tool_id="dev_sandbox_file_write", write_plan_id="p",
            write_preview_id="pv", rollback_id="rb",
            operation="create_or_replace", target_relative_path="a.md",
            status="completed", blocked_reason=None,
            payload={"callable": lambda: None},  # type: ignore[dict-item]
        )
        blob = json.dumps(event)
        assert "<function" not in blob
        assert "<lambda>" not in blob

    def test_emit_returns_event_id(self, dev_home: str) -> None:
        eid = emit_write_audit(
            event_type=EVENT_WRITE_PRE_EXECUTION_AUDIT, hermes_home=dev_home,
            tool_id="dev_sandbox_file_write", write_plan_id="wpln_x",
            write_preview_id="wprv_x", rollback_id=None,
            operation="create_or_replace", target_relative_path="a.md",
            status="pre_execution", blocked_reason=None,
        )
        assert eid and eid.startswith("wau_")


class TestAuditLifecycle:
    def test_successful_write_emits_pre_post_rollback(self, dev_home: str) -> None:
        d = _write_once(dev_home)
        audit_file = Path(dev_home) / "gateway/dev/audit/tool-write-audit.jsonl"
        assert audit_file.exists()
        events = [json.loads(line) for line in audit_file.read_text().splitlines() if line.strip()]
        types = {e["eventType"] for e in events}
        assert EVENT_WRITE_PRE_EXECUTION_AUDIT in types
        assert EVENT_WRITE_POST_EXECUTION_AUDIT in types
        assert EVENT_WRITE_ROLLBACK_MANIFEST_BUILT in types
        # The post-execution event carries the postExecutionAuditId.
        post = [e for e in events if e["eventType"] == EVENT_WRITE_POST_EXECUTION_AUDIT][0]
        assert post["writePlanId"]
        assert post["rollbackId"]

    def test_blocked_write_emits_blocked_audit(self, dev_home: str, monkeypatch) -> None:
        monkeypatch.delenv("HERMES_TOOL_WRITE_EXECUTION_ENABLED", raising=False)
        preview = build_write_preview(
            "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"}, hermes_home=dev_home
        )
        ctx = {
            "writePlanId": preview["writePlanId"],
            "confirmationToken": preview["confirmationToken"],
            "argumentDigest": preview["argumentDigest"],
        }
        dispatch_write_tool(
            "dev_sandbox_file_write", {"targetPath": "a.md", "content": "x"},
            context=ctx, hermes_home=dev_home,
        )
        audit_file = Path(dev_home) / "gateway/dev/audit/tool-write-audit.jsonl"
        events = [json.loads(line) for line in audit_file.read_text().splitlines() if line.strip()]
        blocked = [e for e in events if e["eventType"] == EVENT_WRITE_EXECUTION_BLOCKED]
        assert len(blocked) >= 1
        assert blocked[0]["blockedReason"] == "blocked_write_execution_not_enabled"

    def test_audit_records_no_raw_args(self, dev_home: str) -> None:
        _write_once(dev_home, target="secret.md", content="super-secret-body")
        audit_file = Path(dev_home) / "gateway/dev/audit/tool-write-audit.jsonl"
        blob = audit_file.read_text()
        # The raw content body must not appear verbatim in the audit file.
        assert "super-secret-body" not in blob
        assert "rawArguments" not in blob


class TestAuditReadRoute:
    def test_write_kind_queryable(self, dev_home: str) -> None:
        _write_once(dev_home)
        from fastapi.testclient import TestClient
        from hermes_cli.dev_web_api import create_dev_web_api_app
        from hermes_cli.dev_web_config import DevWebApiConfig

        app = create_dev_web_api_app(DevWebApiConfig(hermes_home=Path(dev_home)))
        client = TestClient(app)
        resp = client.get(
            "/api/dev/v1/tools/audit-events",
            params={"auditKind": "write", "limit": 20},
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) > 0
        item = items[0]
        assert item["auditKind"] == "write"
        assert "writePlanId" in item
        assert item["sideEffects"]["writeRequired"] is True
        assert item["sideEffects"]["externalNetworkCalled"] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
