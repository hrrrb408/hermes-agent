"""Phase 2D — Audit integration tests.

Verifies the dual-write bridge flows each legacy audit kind into the durable
store, and that the query engine + Audit Viewer readback path can find them:
dry-run, pre-execution, post-execution, provider, write, rollback,
confirmation.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hermes_cli.dev_web_audit_bridge import bridge_legacy_audit_to_store
from hermes_cli.dev_web_audit_query import build_audit_query, query_audit_events
from hermes_cli.dev_web_audit_store import get_audit_store_meta


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return str(home)


def _query_one(dev_home, **filters):
    res = query_audit_events(
        build_audit_query(limit=10, **filters), hermes_home=dev_home
    )
    assert res.success, res.error_message
    return res


class TestDryRunIntegration:
    def test_dry_run_flows_to_store(self, dev_home):
        from hermes_cli.dev_web_tool_dry_run_audit import (
            build_dry_run_audit_event,
            write_dry_run_audit_event,
        )

        class FR:
            def to_safe_dict(self):
                return {
                    "canonicalName": "clarify", "exists": True, "riskTier": "P0",
                    "decision": "would_block", "reasonCodes": [],
                    "policyNotes": [], "redactedArgumentsPreview": {},
                    "forbiddenFields": ["api_key"], "missingRequiredFields": [],
                    "executionAllowed": False, "dispatchAllowed": False,
                    "providerSchemaAllowed": False, "auditWritten": False,
                }

        ev = build_dry_run_audit_event(dry_run_result=FR(), request_id="r1")
        write_dry_run_audit_event(ev, hermes_home=dev_home)
        res = _query_one(dev_home, audit_kind="dry_run")
        assert len(res.items) == 1
        assert res.items[0]["toolId"] == "clarify"


class TestPreExecutionIntegration:
    def test_pre_execution_flows_to_store(self, dev_home):
        from hermes_cli.dev_web_tool_pre_execution_audit import (
            write_pre_execution_audit_event,
        )

        pkg = {
            "preExecutionAuditId": "pea-1",
            "executeRequestId": "exe-1",
            "canonicalName": "clarify",
            "createdAt": "2026-06-15T00:00:00+00:00",
        }
        write_pre_execution_audit_event(audit_package=pkg, hermes_home=dev_home)
        res = _query_one(dev_home, audit_kind="pre_execution")
        assert len(res.items) == 1
        assert res.items[0]["preExecutionAuditId"] == "pea-1"


class TestPostExecutionIntegration:
    def test_post_execution_flows_to_store(self, dev_home):
        from hermes_cli.dev_web_tool_post_execution_audit import (
            write_post_execution_audit_event,
        )

        pkg = {
            "postExecutionAuditId": "pexa-1",
            "executeRequestId": "exe-1",
            "canonicalName": "clarify",
            "executionStatus": "completed",
            "eventType": "clarify_execution_completed",
            "sideEffectFlags": {
                "providerSchemaSent": False,
                "providerApiCalled": False,
                "externalSideEffects": False,
            },
            "resultSummary": {"toolResultType": "clarify", "messageLength": 5},
            "createdAt": "2026-06-15T00:00:00+00:00",
        }
        write_post_execution_audit_event(audit_package=pkg, hermes_home=dev_home)
        res = _query_one(dev_home, audit_kind="post_execution")
        assert len(res.items) == 1
        assert res.items[0]["postExecutionAuditId"] == "pexa-1"
        assert res.items[0]["providerApiCalled"] is False
        assert res.items[0]["providerSchemaSent"] is False
        assert res.items[0]["externalSideEffects"] is False


class TestProviderIntegration:
    def test_provider_flows_to_store(self, dev_home):
        from hermes_cli.dev_web_provider_audit import (
            build_provider_audit_event,
            write_provider_audit_event,
        )

        ev = build_provider_audit_event(
            event_type="provider_request",
            provider_request_id="pr-1",
            provider_response_id=None,
            provider_mode="fake",
            payload={"ok": True},
        )
        write_provider_audit_event(ev, hermes_home=dev_home)
        res = _query_one(dev_home, audit_kind="provider")
        assert len(res.items) == 1
        assert res.items[0]["providerMode"] == "fake"


class TestWriteIntegration:
    def test_write_flows_to_store(self, dev_home, monkeypatch):
        monkeypatch.setenv("HERMES_TOOL_WRITE_EXECUTION_ENABLED", "1")
        from hermes_cli.dev_web_write_plan import emit_write_audit

        emit_write_audit(
            event_type="write_preview",
            hermes_home=dev_home,
            tool_id="dev_sandbox_file_write",
            write_plan_id="wp-1",
            write_preview_id="wprev-1",
            rollback_id=None,
            operation="write",
            target_relative_path="a.md",
            status="preview",
            blocked_reason=None,
        )
        res = _query_one(dev_home, audit_kind="write")
        assert len(res.items) == 1
        assert res.items[0]["writePlanId"] == "wp-1"
        assert res.items[0]["writeRequired"] is True


class TestRollbackIntegration:
    def test_rollback_flows_to_store(self, dev_home):
        # The dual-write hook in mark_rollback_executed calls the bridge with a
        # rollback legacy payload; exercise that exact mapping here.
        bridge_legacy_audit_to_store(
            {
                "eventId": "rb-evt-1",
                "rollbackId": "rblk_1",
                "executionId": "exe-1",
                "eventType": "rollback_executed",
                "status": "completed",
                "toolId": "dev_sandbox_file_write",
                "writePlanId": "wp-1",
                "confirmationTokenId": "ctok_1",
                "executedSteps": 2,
            },
            audit_kind="rollback",
            hermes_home=dev_home,
        )
        res = _query_one(dev_home, audit_kind="rollback")
        assert len(res.items) == 1
        assert res.items[0]["rollbackId"] == "rblk_1"
        assert res.items[0]["writeRequired"] is True


class TestConfirmationIntegration:
    def test_confirmation_flows_to_store(self, dev_home):
        bridge_legacy_audit_to_store(
            {
                "tokenId": "ctok_2",
                "eventType": "confirmation_token_used",
                "status": "used",
                "used": True,
                "toolId": "dev_sandbox_file_write",
                "writePlanId": "wp-2",
            },
            audit_kind="confirmation",
            hermes_home=dev_home,
        )
        res = _query_one(dev_home, audit_kind="confirmation")
        assert len(res.items) == 1
        assert res.items[0]["confirmationTokenId"] == "ctok_2"
        assert res.items[0]["writeRequired"] is True


class TestBridgeDirect:
    def test_bridge_writes_each_kind(self, dev_home):
        for kind, legacy in (
            ("dry_run", {"eventId": "d1", "canonicalName": "clarify", "decision": "would_block"}),
            ("pre_execution", {"preExecutionAuditId": "p1", "canonicalName": "clarify"}),
            ("post_execution", {"postExecutionAuditId": "x1", "canonicalName": "clarify"}),
            ("provider", {"eventId": "pv1", "providerMode": "fake"}),
            ("write", {"eventId": "w1", "toolId": "dev_sandbox_file_write"}),
            ("rollback", {"eventId": "rb1", "rollbackId": "rb1"}),
            ("confirmation", {"tokenId": "c1"}),
        ):
            r = bridge_legacy_audit_to_store(legacy, audit_kind=kind, hermes_home=dev_home)
            assert r is not None and r.written, kind
        meta, _ = get_audit_store_meta(dev_home)
        assert meta.event_count == 7

    def test_bridge_never_raises_on_bad_input(self, dev_home):
        assert bridge_legacy_audit_to_store(None, audit_kind="dry_run", hermes_home=dev_home) is None
        assert bridge_legacy_audit_to_store({}, audit_kind="bogus", hermes_home=dev_home) is None


class TestCrossKindQuery:
    def test_query_all_kinds_together(self, dev_home):
        for kind, legacy in (
            ("dry_run", {"eventId": "d1", "canonicalName": "clarify"}),
            ("provider", {"eventId": "p1", "providerMode": "fake"}),
            ("write", {"eventId": "w1", "toolId": "dev_sandbox_file_write"}),
        ):
            bridge_legacy_audit_to_store(legacy, audit_kind=kind, hermes_home=dev_home)
        # No auditKind filter → returns all.
        res = _query_one(dev_home)
        assert len(res.items) == 3
        kinds = {i["auditKind"] for i in res.items}
        assert kinds == {"dry_run", "provider", "write"}
