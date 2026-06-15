"""Phase 2D — Audit query engine + cursor pagination tests.

Verifies cursor next/previous semantics, offset backward compatibility,
filters (eventType / toolId / status / auditKind / providerMode /
writeRequired), safe search, cursor tamper/mismatch rejection, and
limit bounds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.dev_web_audit_query import (
    BLOCKED_CURSOR_INVALID,
    BLOCKED_CURSOR_QUERY_MISMATCH,
    BLOCKED_LIMIT_TOO_LARGE,
    BLOCKED_QUERY_INVALID,
    AuditCursor,
    AuditQuery,
    build_audit_query,
    decode_audit_cursor,
    encode_audit_cursor,
    query_audit_events,
)
from hermes_cli.dev_web_audit_store import append_audit_event, build_audit_event


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return str(home)


def _seed(dev_home, n=5):
    for i in range(n):
        append_audit_event(
            build_audit_event(
                event_type="evt_A" if i % 2 == 0 else "evt_B",
                audit_kind="internal", event_id=f"e{i}",
                tool_id="clarify" if i % 2 == 0 else "read_file",
                status="ok" if i % 2 == 0 else "blocked",
                source="internal", provider_mode="fake",
                read_only=True, write_required=False,
                summary={"note": f"item-{i}"},
            ),
            hermes_home=dev_home,
        )


class TestCursorCodec:
    def test_encode_decode_roundtrip(self):
        c = AuditCursor(42, "desc", "abc123", "2026-06-15T00:00:00+00:00")
        token = encode_audit_cursor(c)
        back = decode_audit_cursor(token)
        assert back is not None
        assert back.last_sequence == 42
        assert back.direction == "desc"
        assert back.query_hash == "abc123"

    def test_decode_garbage_returns_none(self):
        assert decode_audit_cursor("!!!not-base64!!!") is None

    def test_decode_tampered_returns_none(self):
        assert decode_audit_cursor("eyJ2IjogMn0") is None

    def test_decode_wrong_version_returns_none(self):
        assert decode_audit_cursor("eyJ2IjogMn0") is None

    def test_decode_none_or_empty(self):
        assert decode_audit_cursor(None) is None  # type: ignore[arg-type]
        assert decode_audit_cursor("") is None


class TestCursorPagination:
    def test_desc_first_page(self, dev_home):
        _seed(dev_home, 5)
        q = build_audit_query(audit_kind="internal", limit=2)
        res = query_audit_events(q, hermes_home=dev_home)
        assert res.success
        assert len(res.items) == 2
        assert res.has_more is True
        # Newest first → seqs 5, 4.
        assert [i["sequence"] for i in res.items] == [5, 4]

    def test_cursor_next_page(self, dev_home):
        _seed(dev_home, 5)
        res1 = query_audit_events(
            build_audit_query(audit_kind="internal", limit=2), hermes_home=dev_home
        )
        res2 = query_audit_events(
            build_audit_query(
                audit_kind="internal", limit=2, cursor=res1.next_cursor
            ),
            hermes_home=dev_home,
        )
        assert [i["sequence"] for i in res2.items] == [3, 2]

    def test_cursor_third_page_exhausts(self, dev_home):
        _seed(dev_home, 5)
        r1 = query_audit_events(build_audit_query(audit_kind="internal", limit=2), hermes_home=dev_home)
        r2 = query_audit_events(build_audit_query(audit_kind="internal", limit=2, cursor=r1.next_cursor), hermes_home=dev_home)
        r3 = query_audit_events(build_audit_query(audit_kind="internal", limit=2, cursor=r2.next_cursor), hermes_home=dev_home)
        assert [i["sequence"] for i in r3.items] == [1]
        assert r3.has_more is False
        assert r3.next_cursor is None

    def test_asc_order(self, dev_home):
        _seed(dev_home, 3)
        res = query_audit_events(
            build_audit_query(audit_kind="internal", limit=10, order="asc"),
            hermes_home=dev_home,
        )
        assert [i["sequence"] for i in res.items] == [1, 2, 3]


class TestOffsetBackwardCompat:
    def test_integer_offset_cursor_accepted(self, dev_home):
        _seed(dev_home, 5)
        res = query_audit_events(
            build_audit_query(audit_kind="internal", limit=2, cursor="2"),
            hermes_home=dev_home,
        )
        assert res.success
        # Offset 2 into desc-ordered [5,4,3,2,1] → [3, 2].
        assert [i["sequence"] for i in res.items] == [3, 2]


class TestFilters:
    def test_filter_event_type(self, dev_home):
        _seed(dev_home, 4)
        res = query_audit_events(
            build_audit_query(event_type="evt_A", limit=10), hermes_home=dev_home
        )
        assert all(i["eventType"] == "evt_A" for i in res.items)
        assert len(res.items) == 2

    def test_filter_tool_id(self, dev_home):
        _seed(dev_home, 4)
        res = query_audit_events(
            build_audit_query(tool_id="read_file", limit=10), hermes_home=dev_home
        )
        assert all(i["toolId"] == "read_file" for i in res.items)

    def test_filter_status(self, dev_home):
        _seed(dev_home, 4)
        res = query_audit_events(
            build_audit_query(status="blocked", limit=10), hermes_home=dev_home
        )
        assert all(i["status"] == "blocked" for i in res.items)

    def test_filter_audit_kind(self, dev_home):
        _seed(dev_home, 3)
        res = query_audit_events(
            build_audit_query(audit_kind="internal", limit=10), hermes_home=dev_home
        )
        assert len(res.items) == 3

    def test_filter_provider_mode(self, dev_home):
        _seed(dev_home, 3)
        res = query_audit_events(
            build_audit_query(provider_mode="fake", limit=10), hermes_home=dev_home
        )
        assert len(res.items) == 3

    def test_filter_write_required(self, dev_home):
        _seed(dev_home, 3)
        res = query_audit_events(
            build_audit_query(write_required=False, limit=10), hermes_home=dev_home
        )
        assert len(res.items) == 3

    def test_filter_read_only(self, dev_home):
        _seed(dev_home, 3)
        res = query_audit_events(
            build_audit_query(read_only=True, limit=10), hermes_home=dev_home
        )
        assert len(res.items) == 3


class TestSearch:
    def test_search_matches_summary(self, dev_home):
        _seed(dev_home, 5)
        res = query_audit_events(
            build_audit_query(search="item-2", limit=10), hermes_home=dev_home
        )
        assert len(res.items) == 1
        assert res.items[0]["sequence"] == 3  # e2 → item-2

    def test_search_no_match(self, dev_home):
        _seed(dev_home, 3)
        res = query_audit_events(
            build_audit_query(search="zzz-not-present", limit=10), hermes_home=dev_home
        )
        assert res.success and len(res.items) == 0


class TestCursorMismatch:
    def test_cursor_query_mismatch_blocked(self, dev_home):
        _seed(dev_home, 5)
        r1 = query_audit_events(
            build_audit_query(event_type="evt_A", limit=1), hermes_home=dev_home
        )
        # Reuse cursor but change the filter → mismatch.
        r2 = query_audit_events(
            build_audit_query(event_type="evt_B", limit=1, cursor=r1.next_cursor),
            hermes_home=dev_home,
        )
        assert not r2.success
        assert r2.error_code == BLOCKED_CURSOR_QUERY_MISMATCH

    def test_cursor_invalid_blocked(self, dev_home):
        _seed(dev_home, 3)
        # search param forces store mode; cursor is garbage.
        r = query_audit_events(
            build_audit_query(search="x", cursor="!!garbage!!"), hermes_home=dev_home
        )
        assert not r.success
        assert r.error_code == BLOCKED_CURSOR_INVALID


class TestLimitBounds:
    def test_limit_too_large_blocked(self, dev_home):
        _seed(dev_home, 3)
        r = query_audit_events(
            AuditQuery(limit=99999, search="x"), hermes_home=dev_home
        )
        assert not r.success
        assert r.error_code == BLOCKED_LIMIT_TOO_LARGE

    def test_negative_limit_blocked(self, dev_home):
        r = query_audit_events(
            AuditQuery(limit=-1, search="x"), hermes_home=dev_home
        )
        assert not r.success
        assert r.error_code == BLOCKED_QUERY_INVALID


class TestInvalidQuery:
    def test_bad_order_blocked(self, dev_home):
        r = query_audit_events(
            AuditQuery(limit=10, order="sideways", search="x"), hermes_home=dev_home
        )
        assert not r.success and r.error_code == BLOCKED_QUERY_INVALID

    def test_bad_date_blocked(self, dev_home):
        r = query_audit_events(
            AuditQuery(limit=10, from_created_at="yesterday", search="x"),
            hermes_home=dev_home,
        )
        assert not r.success and r.error_code == BLOCKED_QUERY_INVALID

    def test_unsafe_search_blocked(self, dev_home):
        r = query_audit_events(
            AuditQuery(limit=10, search="bad\x00ctrl"), hermes_home=dev_home
        )
        assert not r.success and r.error_code == BLOCKED_QUERY_INVALID


class TestStoreAndIndexStatus:
    def test_result_carries_store_and_index_status(self, dev_home):
        _seed(dev_home, 2)
        res = query_audit_events(
            build_audit_query(audit_kind="internal", limit=10), hermes_home=dev_home
        )
        assert "schemaVersion" in res.store_status
        assert "segmentCount" in res.store_status
        assert "present" in res.index_status
        assert res.schema_version == "audit_schema_v2"

    def test_include_summary_false(self, dev_home):
        _seed(dev_home, 1)
        res = query_audit_events(
            build_audit_query(audit_kind="internal", limit=10, include_summary=False),
            hermes_home=dev_home,
        )
        assert "summary" not in res.items[0]
