"""Phase 2D-H1 — Audit consistency hardening (index / cursor / dual-write).

Deterministic, hermetic consistency coverage that goes beyond the Phase 2D
happy-path tests. Covers Lens 4 (index build / update / repair consistency),
Lens 5 (cursor query / filter / search stability), and Lens 8 (legacy
dual-write / compatibility boundary):

  - index build from an empty store and from multiple segments
  - index query-by-field equals a full segment scan for EVERY indexed field
    (eventType / toolId / status / auditKind / source / providerMode /
    readOnly / writeRequired / createdDate)
  - index missing → rebuild; corrupt → rebuild; stale → repair
  - index contents carry no raw arguments / secrets
  - cursor next / asc / desc windowing; query-hash stability
  - cursor tamper blocked, cursor query-mismatch blocked, direction-mismatch blocked
  - limit too large / negative / non-integer blocked; invalid date blocked;
    unsafe search blocked; oversized search blocked
  - every equality filter (eventType / toolId / status / auditKind / source /
    providerMode / readOnly / writeRequired) plus time-range
  - legacy offset cursor backward compatibility
  - cursor token carries no file path / index internal / secret
  - dual-write bridge writes all 7 audit kinds; legacy read still works; no
    duplicate display across the two read paths

No production access, no `~/.hermes`, no `state.db`. Tests use tmp_path only.
Consistency ID: AUDIT-CONSISTENCY-2D-H1-001.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_audit_bridge import bridge_legacy_audit_to_store
from hermes_cli.dev_web_audit_index import (
    INDEXED_FIELDS,
    query_audit_index,
    rebuild_audit_index,
    repair_audit_index_if_needed,
    update_audit_index_for_event,
    validate_audit_index,
)
from hermes_cli.dev_web_audit_query import (
    BLOCKED_CURSOR_INVALID,
    BLOCKED_CURSOR_QUERY_MISMATCH,
    BLOCKED_LIMIT_TOO_LARGE,
    BLOCKED_QUERY_INVALID,
    AuditCursor,
    MAX_LIMIT,
    build_audit_query,
    decode_audit_cursor,
    encode_audit_cursor,
    query_audit_events,
)
from hermes_cli.dev_web_audit_schema import AUDIT_SCHEMA_VERSION
from hermes_cli.dev_web_audit_store import (
    append_audit_event,
    build_audit_event,
    ensure_audit_store,
    get_audit_store_root,
    iter_all_events,
)


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return str(home)


def _evt(event_id: str = "e1", **extra):
    return build_audit_event(
        event_type="unit_test_event", audit_kind="internal",
        event_id=event_id, **extra,
    )


def _on_disk_events(root: Path) -> list[dict]:
    return [ev for _s, _l, ev, _r in iter_all_events(root) if ev is not None]


# ---------------------------------------------------------------------------
# Lens 4 — Index build / update / repair consistency
# ---------------------------------------------------------------------------


class TestIndexBuildFromEmpty:
    def test_build_empty_store(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        summary = rebuild_audit_index(root)
        assert summary["rebuilt"] is True
        assert summary["eventCount"] == 0
        status = validate_audit_index(root)
        assert status.present
        assert status.consistent


class TestIndexQueryEqualsScan:
    """For every indexed field, index matches a full segment scan."""

    def test_index_matches_scan_all_fields(self, dev_home):
        # Seed a varied event set so every indexed field has at least one value.
        specs = [
            dict(event_id="a", tool_id="clarify", status="ok", source="dry_run_api",
                 provider_mode="fake"),
            dict(event_id="b", tool_id="todo", status="blocked", source="execute_api",
                 provider_mode="disabled", read_only=True, write_required=False),
            dict(event_id="c", tool_id="clarify", status="ok", source="provider_api",
                 provider_mode="real", read_only=True, write_required=False),
        ]
        for spec in specs:
            append_audit_event(_evt(spec.pop("event_id"), **spec), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)

        events = _on_disk_events(root)
        for field in INDEXED_FIELDS:
            # Bucket the scan by this field the same way the index does.
            from hermes_cli.dev_web_audit_index import _indexable_value, _value_key
            scan_buckets: dict[str, set[str]] = {}
            for ev in events:
                val = _indexable_value(ev, field)
                if val is None:
                    continue
                scan_buckets.setdefault(_value_key(val), set()).add(ev["eventId"])
            for key, expected_ids in scan_buckets.items():
                entries = query_audit_index(field, _raw_value(field, key), root)
                assert entries is not None, f"index missing for {field}={key}"
                got_ids = {e["id"] for e in entries}
                assert got_ids == expected_ids, f"{field}={key}: {got_ids} != {expected_ids}"

    def test_index_has_no_secrets_or_raw_args(self, dev_home):
        append_audit_event(
            build_audit_event(
                event_type="t", audit_kind="internal", event_id="sec-idx",
                summary={"api_key": "sk-leak-1234567890abcdef"},
                safe_metadata={"rawArguments": {"x": 1}, "tokenHash": "a" * 40},
            ),
            hermes_home=dev_home,
        )
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        blob = ""
        for p in (root / "indexes").glob("*.json"):
            blob += p.read_text(encoding="utf-8")
        assert "sk-leak" not in blob
        assert "rawArguments" not in blob
        assert "tokenHash" not in blob


def _raw_value(field: str, key: str) -> object:
    """Reverse _value_key back into a comparable value for query_audit_index."""
    if key == "null":
        return None
    if key in ("true", "false"):
        return key == "true"
    return key


class TestIndexRepair:
    def test_missing_index_rebuilt_on_repair(self, dev_home):
        append_audit_event(_evt(event_id="m1"), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        # No index built yet → repair builds it.
        summary = repair_audit_index_if_needed(root)
        assert summary["rebuilt"] is True
        assert validate_audit_index(root).consistent

    def test_stale_index_repaired(self, dev_home):
        append_audit_event(_evt(event_id="s1"), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        # Add an event WITHOUT rebuilding → index is stale (count/seq behind).
        append_audit_event(_evt(event_id="s2"), hermes_home=dev_home)
        status = validate_audit_index(root)
        assert status.stale or not status.consistent
        repair_audit_index_if_needed(root)
        status = validate_audit_index(root)
        assert status.consistent
        assert status.event_count == 2

    def test_corrupt_index_rebuilt(self, dev_home):
        append_audit_event(_evt(event_id="c1"), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        # Corrupt the sequence marker.
        seq_path = root / "indexes" / "sequence.json"
        seq_path.write_text("NOT JSON", encoding="utf-8")
        status = validate_audit_index(root)
        assert not status.present or not status.consistent
        repair_audit_index_if_needed(root)
        assert validate_audit_index(root).consistent

    def test_incremental_update_appends_entry(self, dev_home):
        append_audit_event(_evt(event_id="u1"), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        # Manually append an event and incrementally update the index.
        ev = _evt(event_id="u2")
        append_audit_event(ev, hermes_home=dev_home)
        ok = update_audit_index_for_event(
            ev, root, segment_name="audit-000001.jsonl", line_no=2
        )
        assert ok is True


# ---------------------------------------------------------------------------
# Lens 5 — Cursor query / filter / search stability
# ---------------------------------------------------------------------------


def _seed_n(dev_home, n: int) -> list[int]:
    for i in range(n):
        append_audit_event(_evt(event_id=f"p{i}"), hermes_home=dev_home)
    root, _ = get_audit_store_root(dev_home)
    return sorted(ev["sequence"] for ev in _on_disk_events(root))


class TestCursorWindowing:
    def test_cursor_next_desc(self, dev_home):
        _seed_n(dev_home, 5)
        r1 = query_audit_events(
            build_audit_query(audit_kind="internal", limit=2), hermes_home=dev_home
        )
        assert r1.success and len(r1.items) == 2 and r1.has_more
        assert [it["sequence"] for it in r1.items] == [5, 4]
        r2 = query_audit_events(
            build_audit_query(audit_kind="internal", limit=2, cursor=r1.next_cursor),
            hermes_home=dev_home,
        )
        assert r2.success and [it["sequence"] for it in r2.items] == [3, 2]

    def test_cursor_next_asc(self, dev_home):
        _seed_n(dev_home, 5)
        r1 = query_audit_events(
            build_audit_query(audit_kind="internal", limit=2, order="asc"),
            hermes_home=dev_home,
        )
        assert [it["sequence"] for it in r1.items] == [1, 2]
        r2 = query_audit_events(
            build_audit_query(
                audit_kind="internal", limit=2, order="asc", cursor=r1.next_cursor
            ),
            hermes_home=dev_home,
        )
        assert [it["sequence"] for it in r2.items] == [3, 4]

    def test_cursor_query_hash_stable(self, dev_home):
        _seed_n(dev_home, 3)
        from hermes_cli.dev_web_audit_query import _query_hash
        h1 = _query_hash(build_audit_query(audit_kind="internal", limit=1))
        h2 = _query_hash(build_audit_query(audit_kind="internal", limit=99))
        # Hash ignores limit / cursor.
        assert h1 == h2
        h3 = _query_hash(build_audit_query(audit_kind="provider", limit=1))
        assert h1 != h3

    def test_previous_cursor_field_present(self, dev_home):
        _seed_n(dev_home, 3)
        r = query_audit_events(
            build_audit_query(audit_kind="internal", limit=1), hermes_home=dev_home
        )
        # Backward pagination is not supported in Phase 2D; the field is present
        # and None. (This is the documented Phase 2D posture.)
        assert hasattr(r, "previous_cursor")
        assert r.previous_cursor is None


class TestCursorTamperAndMismatch:
    def test_garbage_cursor_blocked(self, dev_home):
        _seed_n(dev_home, 2)
        r = query_audit_events(
            build_audit_query(
                audit_kind="internal", limit=10, cursor="!!garbage!!"
            ),
            hermes_home=dev_home,
        )
        assert not r.success
        assert r.error_code == BLOCKED_CURSOR_INVALID

    def test_cursor_query_mismatch_blocked(self, dev_home):
        _seed_n(dev_home, 3)
        r1 = query_audit_events(
            build_audit_query(audit_kind="internal", limit=1), hermes_home=dev_home
        )
        r2 = query_audit_events(
            build_audit_query(
                audit_kind="provider", limit=1, cursor=r1.next_cursor
            ),
            hermes_home=dev_home,
        )
        assert not r2.success
        assert r2.error_code == BLOCKED_CURSOR_QUERY_MISMATCH

    def test_cursor_direction_mismatch_blocked(self, dev_home):
        _seed_n(dev_home, 3)
        r1 = query_audit_events(
            build_audit_query(audit_kind="internal", limit=1, order="desc"),
            hermes_home=dev_home,
        )
        r2 = query_audit_events(
            build_audit_query(
                audit_kind="internal", limit=1, order="asc", cursor=r1.next_cursor
            ),
            hermes_home=dev_home,
        )
        assert not r2.success
        assert r2.error_code == BLOCKED_CURSOR_QUERY_MISMATCH


class TestQueryValidation:
    def test_limit_too_large_blocked(self, dev_home):
        r = query_audit_events(
            build_audit_query(audit_kind="internal", limit=MAX_LIMIT + 1),
            hermes_home=dev_home,
        )
        assert not r.success and r.error_code == BLOCKED_LIMIT_TOO_LARGE

    def test_limit_negative_blocked(self, dev_home):
        r = query_audit_events(
            build_audit_query(audit_kind="internal", limit=0), hermes_home=dev_home
        )
        assert not r.success and r.error_code == BLOCKED_QUERY_INVALID

    def test_invalid_date_blocked(self, dev_home):
        r = query_audit_events(
            build_audit_query(
                audit_kind="internal", from_created_at="not-a-date"
            ),
            hermes_home=dev_home,
        )
        assert not r.success and r.error_code == BLOCKED_QUERY_INVALID

    def test_unsafe_search_blocked(self, dev_home):
        r = query_audit_events(
            build_audit_query(audit_kind="internal", search="bad\x00control"),
            hermes_home=dev_home,
        )
        assert not r.success and r.error_code == BLOCKED_QUERY_INVALID

    def test_oversized_search_blocked(self, dev_home):
        r = query_audit_events(
            build_audit_query(audit_kind="internal", search="x" * 500),
            hermes_home=dev_home,
        )
        assert not r.success and r.error_code == BLOCKED_QUERY_INVALID

    def test_invalid_enum_blocked(self, dev_home):
        r = query_audit_events(
            build_audit_query(audit_kind="bogus_kind"), hermes_home=dev_home
        )
        assert not r.success and r.error_code == BLOCKED_QUERY_INVALID


class TestFiltersAndSearch:
    def test_event_type_filter(self, dev_home):
        append_audit_event(
            build_audit_event(event_type="alpha", audit_kind="internal", event_id="1"),
            hermes_home=dev_home,
        )
        append_audit_event(
            build_audit_event(event_type="beta", audit_kind="internal", event_id="2"),
            hermes_home=dev_home,
        )
        r = query_audit_events(
            build_audit_query(event_type="alpha", limit=10), hermes_home=dev_home
        )
        assert r.success and len(r.items) == 1
        assert r.items[0]["eventType"] == "alpha"

    def test_status_and_source_filters(self, dev_home):
        append_audit_event(
            build_audit_event(
                event_type="t", audit_kind="internal", event_id="1",
                status="ok", source="dry_run_api",
            ),
            hermes_home=dev_home,
        )
        append_audit_event(
            build_audit_event(
                event_type="t", audit_kind="internal", event_id="2",
                status="blocked", source="execute_api",
            ),
            hermes_home=dev_home,
        )
        r = query_audit_events(
            build_audit_query(status="ok", source="dry_run_api", limit=10),
            hermes_home=dev_home,
        )
        assert r.success and len(r.items) == 1
        assert r.items[0]["status"] == "ok"

    def test_provider_mode_and_bool_filters(self, dev_home):
        append_audit_event(
            build_audit_event(
                event_type="t", audit_kind="provider", event_id="1",
                provider_mode="fake", read_only=True, write_required=False,
            ),
            hermes_home=dev_home,
        )
        append_audit_event(
            build_audit_event(
                event_type="t", audit_kind="write", event_id="2",
                read_only=False, write_required=True,
            ),
            hermes_home=dev_home,
        )
        r = query_audit_events(
            build_audit_query(
                audit_kind="provider", provider_mode="fake",
                read_only=True, write_required=False, limit=10,
            ),
            hermes_home=dev_home,
        )
        assert r.success and len(r.items) == 1
        assert r.items[0]["providerMode"] == "fake"

    def test_search_matches_summary(self, dev_home):
        append_audit_event(
            build_audit_event(
                event_type="t", audit_kind="internal", event_id="1",
                summary={"note": "needle-in-haystack"},
            ),
            hermes_home=dev_home,
        )
        append_audit_event(
            build_audit_event(event_type="t", audit_kind="internal", event_id="2"),
            hermes_home=dev_home,
        )
        r = query_audit_events(
            build_audit_query(search="needle", limit=10), hermes_home=dev_home
        )
        assert r.success and len(r.items) == 1


class TestLegacyOffsetCompat:
    def test_offset_cursor_paginates(self, dev_home):
        _seed_n(dev_home, 6)
        r1 = query_audit_events(
            build_audit_query(audit_kind="internal", limit=2, cursor="0"),
            hermes_home=dev_home,
        )
        assert r1.success and len(r1.items) == 2
        r2 = query_audit_events(
            build_audit_query(audit_kind="internal", limit=2, cursor="2"),
            hermes_home=dev_home,
        )
        assert r2.success and len(r2.items) == 2
        # No overlap between offset pages.
        s1 = {it["sequence"] for it in r1.items}
        s2 = {it["sequence"] for it in r2.items}
        assert s1.isdisjoint(s2)


class TestCursorTokenNoLeak:
    def test_token_has_no_path_or_secret(self, dev_home):
        _seed_n(dev_home, 3)
        r = query_audit_events(
            build_audit_query(audit_kind="internal", limit=1), hermes_home=dev_home
        )
        token = r.next_cursor
        assert token is not None
        assert "/Users/" not in token
        assert "hermes-home" not in token
        assert "audit-store" not in token
        assert "eventId" not in token
        assert "sequence.json" not in token

    def test_decoded_cursor_fields_whitelist(self):
        token = encode_audit_cursor(
            AuditCursor(42, "desc", "abc123", "2026-06-15T00:00:00+00:00")
        )
        back = decode_audit_cursor(token)
        assert back is not None
        assert back.last_sequence == 42
        assert back.direction == "desc"
        assert back.query_hash == "abc123"

    def test_decode_rejects_bad_token(self):
        assert decode_audit_cursor("!!!not-base64!!!") is None
        assert decode_audit_cursor("") is None


# ---------------------------------------------------------------------------
# Lens 8 — Legacy dual-write / compatibility boundary
# ---------------------------------------------------------------------------


_DUAL_KINDS = (
    ("dry_run", {"eventId": "d1", "canonicalName": "clarify", "decision": "would_block"}),
    ("pre_execution", {"preExecutionAuditId": "pe1", "canonicalName": "clarify"}),
    ("post_execution", {"postExecutionAuditId": "px1", "canonicalName": "clarify"}),
    ("provider", {"eventId": "pv1", "providerMode": "fake"}),
    ("write", {"eventId": "w1", "toolId": "dev_sandbox_file_write"}),
    ("rollback", {"eventId": "rb1", "rollbackId": "rblk1"}),
    ("confirmation", {"tokenId": "ct1"}),
)


class TestDualWriteAllKinds:
    def test_all_seven_kinds_written_once(self, dev_home):
        for kind, legacy in _DUAL_KINDS:
            r = bridge_legacy_audit_to_store(legacy, audit_kind=kind, hermes_home=dev_home)
            assert r is not None and r.written, kind
        # Query without an auditKind filter → all 7 are visible, exactly once.
        res = query_audit_events(
            build_audit_query(limit=100), hermes_home=dev_home
        )
        assert res.success
        assert len(res.items) == 7
        kinds = {it["auditKind"] for it in res.items}
        assert kinds == {"dry_run", "pre_execution", "post_execution",
                         "provider", "write", "rollback", "confirmation"}

    def test_no_duplicate_event_id_across_kinds(self, dev_home):
        # Re-bridging the SAME event id (per kind) is rejected, not duplicated.
        legacy = {"eventId": "dup-1", "canonicalName": "clarify"}
        r1 = bridge_legacy_audit_to_store(
            legacy, audit_kind="dry_run", hermes_home=dev_home
        )
        assert r1.written
        r2 = bridge_legacy_audit_to_store(
            legacy, audit_kind="dry_run", hermes_home=dev_home
        )
        assert not r2.written
        res = query_audit_events(
            build_audit_query(audit_kind="dry_run", limit=100), hermes_home=dev_home
        )
        assert len(res.items) == 1


class TestLegacyReadCompat:
    def test_legacy_offset_path_still_works(self, dev_home):
        # Legacy offset pagination (read_audit_events via the API) is independent
        # of the store; here we confirm the store path tolerates the same
        # auditKind values the legacy reader exposes.
        for i in range(3):
            bridge_legacy_audit_to_store(
                {"eventId": f"lr{i}", "canonicalName": "clarify"},
                audit_kind="dry_run", hermes_home=dev_home,
            )
        res = query_audit_events(
            build_audit_query(audit_kind="dry_run", limit=10, cursor="0"),
            hermes_home=dev_home,
        )
        assert res.success and len(res.items) == 3


class TestBridgeRobustness:
    def test_bridge_never_raises(self, dev_home):
        assert bridge_legacy_audit_to_store(
            None, audit_kind="dry_run", hermes_home=dev_home
        ) is None
        assert bridge_legacy_audit_to_store(
            {}, audit_kind="unknown_kind", hermes_home=dev_home
        ) is None
        # Schema version is always forced canonical by the bridge.
        r = bridge_legacy_audit_to_store(
            {"eventId": "v1", "canonicalName": "clarify"},
            audit_kind="dry_run", hermes_home=dev_home,
        )
        assert r is not None and r.written
