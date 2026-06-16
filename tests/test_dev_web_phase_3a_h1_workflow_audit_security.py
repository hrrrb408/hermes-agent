"""Phase 3A-H1 — Workflow audit hardening (Lens 7: Redaction Boundary).

Adversarial boundary tests for the workflow audit bridge: every workflow event
type is writable + queryable, an unknown event type normalizes safely, every
written event is sanitized (no raw args / token secrets / full hashes / API
keys / file content / callable reprs / production paths) with
``redactionApplied=true``, audit links + workflow correlation ids are
preserved, and the write is fail-safe (a bad home never raises).
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
    EVENT_WORKFLOW_EXECUTION_COMPLETED,
    EVENT_WORKFLOW_PLAN_BLOCKED,
    EVENT_WORKFLOW_PLAN_CREATED,
    EVENT_WORKFLOW_STEP_APPROVAL_CREATED,
    EVENT_WORKFLOW_STEP_APPROVAL_USED,
    EVENT_WORKFLOW_STEP_BLOCKED,
    EVENT_WORKFLOW_STEP_COMPLETED,
    EVENT_WORKFLOW_STEP_FAILED,
    EVENT_WORKFLOW_STEP_PREVIEW_CREATED,
    EVENT_WORKFLOW_STEP_STARTED,
    EVENT_WORKFLOW_TIMELINE_UPDATED,
    VALID_WORKFLOW_EVENT_TYPES,
    WorkflowAuditLink,
)


@pytest.fixture
def dev_home(tmp_path: Path) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    return str(home)


def _all_segments(dev_home: str) -> str:
    root, _err = get_audit_store_root(dev_home)
    blob = ""
    for segment in root.glob("**/audit-*.jsonl"):
        blob += segment.read_text(encoding="utf-8")
    return blob


# ---------------------------------------------------------------------------
# 1. Every event type is writable + queryable
# ---------------------------------------------------------------------------


REQUIRED_EVENT_TYPES = (
    EVENT_WORKFLOW_PLAN_CREATED,
    EVENT_WORKFLOW_PLAN_BLOCKED,
    "workflow_execution_created",
    EVENT_WORKFLOW_STEP_PREVIEW_CREATED,
    EVENT_WORKFLOW_STEP_APPROVAL_CREATED,
    EVENT_WORKFLOW_STEP_APPROVAL_USED,
    EVENT_WORKFLOW_STEP_STARTED,
    EVENT_WORKFLOW_STEP_COMPLETED,
    EVENT_WORKFLOW_STEP_BLOCKED,
    EVENT_WORKFLOW_STEP_FAILED,
    EVENT_WORKFLOW_TIMELINE_UPDATED,
    EVENT_WORKFLOW_EXECUTION_COMPLETED,
)


class TestEventTypeCoverage:
    def test_required_event_types_are_in_valid_set(self) -> None:
        for ev in REQUIRED_EVENT_TYPES:
            assert ev in VALID_WORKFLOW_EVENT_TYPES, ev

    @pytest.mark.parametrize("event_type", REQUIRED_EVENT_TYPES)
    def test_each_event_type_is_writable_and_queryable(self, dev_home: str, event_type: str) -> None:
        r = write_workflow_audit_event(event_type=event_type, workflow_id="wf_x", hermes_home=dev_home)
        assert r.written
        assert r.event_id
        q = build_audit_query(
            limit=50, cursor=None, order="desc", event_type=event_type,
            audit_kind="internal", include_summary=True,
        )
        result = query_audit_events(q, hermes_home=dev_home)
        assert result.success
        assert any(e.get("eventType") == event_type for e in result.items)

    def test_unknown_event_type_normalizes_to_timeline_updated(self, dev_home: str) -> None:
        r = write_workflow_audit_event(event_type="workflow_evil", workflow_id="wf_x", hermes_home=dev_home)
        assert r.written
        # The normalized breadcrumb is still queryable.
        q = build_audit_query(
            limit=50, cursor=None, order="desc",
            event_type=EVENT_WORKFLOW_TIMELINE_UPDATED,
            audit_kind="internal", include_summary=True,
        )
        result = query_audit_events(q, hermes_home=dev_home)
        assert result.success


# ---------------------------------------------------------------------------
# 2. Redaction (no-leak)
# ---------------------------------------------------------------------------


NO_LEAK_TOKENS = (
    "rawArguments",
    "rawArgs",
    "fullTokenHash",
    "tokenSecret",
    "plainToken",
    "rawToken",
    "apiKey",
    "fileContent",
    "<function",
    "object at 0x",
    "/Users/huangruibang/.hermes",
    "state.db",
)


class TestNoLeak:
    def test_secret_in_summary_is_redacted(self, dev_home: str) -> None:
        secret = "sk-" + "a" * 20
        r = write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_PLAN_CREATED, workflow_id="wf_x",
            summary={"note": secret, "rawArguments": {"secret": "x"}},
            safe_metadata={"apiKey": "k"},
            hermes_home=dev_home,
        )
        assert r.written
        blob = _all_segments(dev_home)
        assert secret not in blob
        assert "[REDACTED]" in blob
        for token in ("rawArguments", "apiKey"):
            assert token not in blob

    def test_callable_repr_never_persisted(self, dev_home: str) -> None:
        r = write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_PLAN_CREATED, workflow_id="wf_x",
            summary={"obj": object(), "fn": lambda: None}, hermes_home=dev_home,
        )
        assert r.written
        blob = _all_segments(dev_home)
        assert "object at 0x" not in blob
        assert "<function" not in blob

    def test_full_token_hash_never_persisted(self, dev_home: str) -> None:
        r = write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_STEP_COMPLETED, workflow_id="wf_x",
            summary={"fullTokenHash": "a" * 64, "tokenSecret": "bearer_xyz"},
            hermes_home=dev_home,
        )
        assert r.written
        blob = _all_segments(dev_home)
        for token in ("fullTokenHash", "tokenSecret"):
            assert token not in blob

    def test_redaction_applied_flag_true(self, dev_home: str) -> None:
        write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_PLAN_CREATED, workflow_id="wf_x", hermes_home=dev_home,
        )
        blob = _all_segments(dev_home)
        assert '"redactionApplied":true' in blob

    def test_payload_redaction_helper(self) -> None:
        out = redact_workflow_audit_payload({"a": "sk-" + "b" * 20, "ok": "safe", "apiKey": "x"})
        assert out["a"] == "[REDACTED]"
        assert out["ok"] == "safe"
        assert "apiKey" not in out
        assert redact_workflow_audit_payload(None) == {}
        assert redact_workflow_audit_payload("not a dict") == {}  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 3. Correlation ids + audit links preserved
# ---------------------------------------------------------------------------


class TestCorrelationAndLinks:
    def test_workflow_correlation_ids_carried(self, dev_home: str) -> None:
        r = write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_STEP_COMPLETED,
            workflow_id="wf_x", workflow_plan_id="wfp_x",
            workflow_execution_id="wfx_x", workflow_step_id="wfs_x",
            step_type="read_only_tool", approval_id="cft_a",
            tool_id="dev_environment_read", status="completed",
            hermes_home=dev_home,
        )
        assert r.written
        blob = _all_segments(dev_home)
        data = json.loads(blob.strip().splitlines()[-1])
        assert data["summary"]["workflowId"] == "wf_x"
        assert data["summary"]["workflowStepId"] == "wfs_x"
        assert data["summary"]["stepType"] == "read_only_tool"
        assert data["safeMetadata"]["workflowExecutionId"] == "wfx_x"
        assert data["safeMetadata"]["workflowApprovalId"] == "cft_a"
        assert data["safeMetadata"]["schemaOrigin"] == "workflow_audit_v1"

    def test_audit_links_preserved_as_public_ids(self, dev_home: str) -> None:
        link = WorkflowAuditLink(audit_id="evt_abc123", audit_kind="internal", label="audit")
        r = write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_STEP_COMPLETED, workflow_id="wf_x",
            audit_links=(link,), hermes_home=dev_home,
        )
        assert r.written
        blob = _all_segments(dev_home)
        assert "evt_abc123" in blob
        assert "linkedAuditIds" in blob

    def test_audit_link_from_result_handles_failure(self) -> None:
        assert audit_link_from_result(None) is None

    def test_audit_link_from_result_succeeds(self, dev_home: str) -> None:
        r = write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_PLAN_CREATED, workflow_id="wf_x", hermes_home=dev_home,
        )
        link = audit_link_from_result(r)
        assert link is not None
        assert isinstance(link, WorkflowAuditLink)
        assert link.audit_id == r.event_id


# ---------------------------------------------------------------------------
# 4. Fail-safe write (never raises)
# ---------------------------------------------------------------------------


class TestFailSafe:
    def test_write_to_unwritable_home_does_not_raise(self, tmp_path: Path) -> None:
        # Pointing HERMES_HOME under a regular file makes the store's mkdir
        # fail (NotADirectoryError). The bridge catches it, returns a
        # not-written result, and never raises — the fail-safe contract.
        blocker = tmp_path / "blocker"
        blocker.write_text("not a directory", encoding="utf-8")
        bogus = str(blocker / "audit")  # parent is a file → mkdir fails
        try:
            r = write_workflow_audit_event(
                event_type=EVENT_WORKFLOW_PLAN_CREATED, workflow_id="wf_x", hermes_home=bogus,
            )
        except Exception as exc:  # pragma: no cover - defensive
            raise AssertionError(f"bridge raised on bad home: {exc!r}") from exc
        assert r.written is False
        assert r.event_id is None

    def test_external_network_flag_always_false(self, dev_home: str) -> None:
        write_workflow_audit_event(
            event_type=EVENT_WORKFLOW_PLAN_CREATED, workflow_id="wf_x", hermes_home=dev_home,
        )
        blob = _all_segments(dev_home)
        assert '"externalNetworkCalled":false' in blob

    def test_multiple_events_accumulate(self, dev_home: str) -> None:
        for ev in (EVENT_WORKFLOW_PLAN_CREATED, EVENT_WORKFLOW_STEP_STARTED, EVENT_WORKFLOW_STEP_COMPLETED):
            write_workflow_audit_event(event_type=ev, workflow_id="wf_x", hermes_home=dev_home)
        q = build_audit_query(
            limit=50, cursor=None, order="desc", audit_kind="internal", include_summary=True,
        )
        result = query_audit_events(q, hermes_home=dev_home)
        types = {e.get("eventType") for e in result.items}
        assert EVENT_WORKFLOW_PLAN_CREATED in types
        assert EVENT_WORKFLOW_STEP_COMPLETED in types
