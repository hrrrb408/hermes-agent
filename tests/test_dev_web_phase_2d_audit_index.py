"""Phase 2D — Audit index tests.

Verifies index build, incremental update, rebuild-when-missing,
repair-when-stale, and equality queries — plus that the index never
persists secrets / raw arguments.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_audit_index import (
    INDEXED_FIELDS,
    query_audit_index,
    rebuild_audit_index,
    update_audit_index_for_event,
    validate_audit_index,
    repair_audit_index_if_needed,
    load_audit_index,
)
from hermes_cli.dev_web_audit_store import (
    append_audit_event,
    build_audit_event,
    ensure_audit_store,
    get_audit_store_root,
)


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return str(home)


def _seed(dev_home, n=3):
    for i in range(n):
        append_audit_event(
            build_audit_event(
                event_type="evt_A" if i % 2 == 0 else "evt_B",
                audit_kind="internal", event_id=f"e{i}",
                tool_id="clarify" if i % 2 == 0 else "read_file",
                status="ok", source="internal",
                read_only=True, write_required=False,
            ),
            hermes_home=dev_home,
        )


class TestIndexBuild:
    def test_build_returns_summary(self, dev_home):
        _seed(dev_home, 4)
        root, _ = get_audit_store_root(dev_home)
        summary = rebuild_audit_index(root)
        assert summary["rebuilt"]
        assert summary["eventCount"] == 4
        assert summary["lastSequence"] == 4
        assert "eventType" in summary["fields"]

    def test_build_creates_field_files(self, dev_home):
        _seed(dev_home, 2)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        for field in ("eventType", "toolId", "status", "auditKind"):
            assert (root / "indexes" / f"by-{field.replace('_','-')}.json").is_file()

    def test_indexed_fields_cover_required_filters(self):
        for f in ("eventType", "toolId", "status", "auditKind", "source",
                  "providerMode", "readOnly", "writeRequired", "createdDate"):
            assert f in INDEXED_FIELDS


class TestIndexQuery:
    def test_query_event_type(self, dev_home):
        _seed(dev_home, 4)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        entries = query_audit_index("eventType", "evt_A", root)
        assert entries is not None
        assert len(entries) == 2  # e0, e2

    def test_query_tool_id(self, dev_home):
        _seed(dev_home, 4)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        entries = query_audit_index("toolId", "clarify", root)
        assert entries is not None and len(entries) == 2

    def test_query_missing_field_returns_none(self, dev_home):
        _seed(dev_home, 2)
        root, _ = get_audit_store_root(dev_home)
        # No build → index missing.
        assert query_audit_index("eventType", "evt_A", root) is None

    def test_query_unknown_field_returns_none(self, dev_home):
        root, _ = get_audit_store_root(dev_home)
        ensure_audit_store(dev_home)
        assert query_audit_index("bogusField", "x", root) is None

    def test_query_empty_match_returns_empty_list(self, dev_home):
        _seed(dev_home, 2)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        entries = query_audit_index("eventType", "nonexistent", root)
        assert entries == []


class TestIndexUpdate:
    def test_update_advances_sequence(self, dev_home):
        _seed(dev_home, 2)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        before = validate_audit_index(root)
        ok = update_audit_index_for_event(
            {"eventId": "new1", "sequence": 3, "eventType": "evt_A",
             "auditKind": "internal", "createdAt": "2026-06-15T00:00:00+00:00",
             "schemaVersion": "audit_schema_v2"},
            root, segment_name="audit-000001.jsonl", line_no=99,
        )
        assert ok
        after = validate_audit_index(root)
        assert after.last_sequence == 3
        assert after.event_count == before.event_count + 1

    def test_update_when_missing_index_returns_false(self, dev_home):
        root, _ = get_audit_store_root(dev_home)
        ok = update_audit_index_for_event(
            {"eventId": "x", "sequence": 1, "auditKind": "internal"},
            root, segment_name="audit-000001.jsonl", line_no=1,
        )
        assert ok is False


class TestIndexRebuildAndRepair:
    def test_rebuild_when_missing(self, dev_home):
        _seed(dev_home, 3)
        root, _ = get_audit_store_root(dev_home)
        status = validate_audit_index(root)
        assert status.present is False
        summary = repair_audit_index_if_needed(root)
        assert summary["rebuilt"]
        status2 = validate_audit_index(root)
        assert status2.present and status2.consistent

    def test_repair_when_stale(self, dev_home):
        _seed(dev_home, 3)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        # Append one more event WITHOUT updating the index → stale.
        append_audit_event(
            build_audit_event(event_type="evt_A", audit_kind="internal", event_id="e99"),
            hermes_home=dev_home,
        )
        status = validate_audit_index(root)
        assert not status.consistent
        summary = repair_audit_index_if_needed(root)
        assert summary["rebuilt"]
        status2 = validate_audit_index(root)
        assert status2.consistent
        assert status2.event_count == 4

    def test_repair_when_corrupt(self, dev_home):
        _seed(dev_home, 2)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        # Corrupt the sequence marker.
        seq_path = root / "indexes" / "sequence.json"
        seq_path.write_text("{not valid json", encoding="utf-8")
        status = validate_audit_index(root)
        assert status.present is False
        repair_audit_index_if_needed(root)
        status2 = validate_audit_index(root)
        assert status2.consistent


class TestIndexNeverPersistsSecrets:
    def test_no_secret_in_index_files(self, dev_home):
        append_audit_event(
            build_audit_event(
                event_type="evt_A", audit_kind="internal", event_id="sec1",
                safe_metadata={"api_key": "sk-leak-1234567890abcdef"},
            ),
            hermes_home=dev_home,
        )
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        blob = ""
        for p in (root / "indexes").iterdir():
            blob += p.read_text(encoding="utf-8")
        assert "sk-leak-1234567890abcdef" not in blob
        assert "api_key" not in blob.lower()

    def test_load_index_safe(self, dev_home):
        _seed(dev_home, 1)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        view = load_audit_index(root)
        assert view["present"] is True
        assert view["schemaVersion"] == "audit_schema_v2"
