"""Phase 3A — Workflow audit bridge tests.

Verifies workflow breadcrumb events are written to the Phase 2D durable store,
are sanitized (no raw args / tokens / hashes / secrets / callables), preserve
audit links, and are discoverable by the audit query engine.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_audit_query import build_audit_query, query_audit_events
from hermes_cli.dev_web_audit_store import get_audit_store_root
from hermes_cli.dev_web_workflow_audit import (
    audit_link_from_result,
    redact_workflow_audit_payload,
    write_workflow_audit_event,
)
from hermes_cli.dev_web_workflow_schema import (
    EVENT_WORKFLOW_PLAN_CREATED,
    EVENT_WORKFLOW_STEP_COMPLETED,
    WorkflowAuditLink,
)


@pytest.fixture
def dev_home(tmp_path: Path) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return str(home)


class TestAuditWrite:
    def test_event_written_and_linked(self, dev_home: str) -> None:
        r = write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_PLAN_CREATED,
            workflow_id="wf_x", workflow_plan_id="wfp_x",
            status="ok", hermes_home=dev_home,
        )
        assert r.written
        assert r.event_id
        link = audit_link_from_result(r)
        assert link is not None
        assert isinstance(link, WorkflowAuditLink)

    def test_completed_event_carries_step_metadata(self, dev_home: str) -> None:
        r = write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_STEP_COMPLETED,
            workflow_id="wf_x", workflow_execution_id="wfx_x", workflow_step_id="wfs_x",
            step_type="read_only_tool", tool_id="dev_environment_read",
            write_preview_id="wpv_x", rollback_id=None, status="completed",
            hermes_home=dev_home,
        )
        assert r.written

    def test_audit_event_sanitized(self, dev_home: str) -> None:
        r = write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_PLAN_CREATED,
            workflow_id="wf_x",
            summary={"note": "sk-" + "a" * 20, "rawArguments": {"secret": "x"}},
            safe_metadata={"apiKey": "k"},
            hermes_home=dev_home,
        )
        assert r.written
        # Inspect the on-disk segment for the secret / forbidden carriers.
        root, _err = get_audit_store_root(dev_home)
        blob = ""
        for segment in root.glob("**/audit-*.jsonl"):
            blob += segment.read_text(encoding="utf-8")
        assert "sk-" + "a" * 20 not in blob
        assert "[REDACTED]" in blob
        assert "apiKey" not in blob
        assert "rawArguments" not in blob

    def test_payload_redaction(self) -> None:
        out = redact_workflow_audit_payload({"a": "sk-" + "b" * 20, "ok": "safe"})
        assert out["a"] == "[REDACTED]"
        assert out["ok"] == "safe"
        assert redact_workflow_audit_payload(None) == {}

    def test_workflow_events_queryable(self, dev_home: str) -> None:
        write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_PLAN_CREATED, workflow_id="wf_x",
            status="ok", hermes_home=dev_home,
        )
        q = build_audit_query(limit=50, cursor=None, order="desc",
                              event_type=EVENT_WORKFLOW_PLAN_CREATED,
                              audit_kind="internal", include_summary=True)
        result = query_audit_events(q, hermes_home=dev_home)
        assert result.success
        assert any(e.get("eventType") == EVENT_WORKFLOW_PLAN_CREATED for e in result.items)

    def test_audit_link_no_callable_repr(self, dev_home: str) -> None:
        r = write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_PLAN_CREATED, workflow_id="wf_x",
            summary={"obj": object()}, hermes_home=dev_home,
        )
        assert r.written
        root, _err = get_audit_store_root(dev_home)
        for segment in root.glob("**/audit-*.jsonl"):
            text = segment.read_text(encoding="utf-8")
            assert "object at 0x" not in text
            assert "<function" not in text
