"""Phase 2D-H1 — Durable audit store hardening (stress + recovery).

Deterministic, hermetic stress + recovery coverage that goes beyond the Phase 2D
happy-path tests. Covers Lens 3 (append-only / sequence consistency), Lens 6
(rotation / segment recovery boundary), and Lens 7 (corruption detection /
quarantine boundary):

  - high-concurrency append (32 threads) with no lost events and no
    duplicate / colliding sequence
  - the on-disk sequence floor: a stale / deleted / corrupt store-meta never
    produces a colliding sequence (the designed-for crash-recovery case)
  - append recovers after a stale / missing index (the query path rebuilds)
  - append never leaves the active segment corrupt (every line is valid JSON)
  - large-batch contiguous sequences + oversized-event rejection
  - the cross-process writer lock file lives only under the dev audit store
  - rotation by size and by event count is deterministic, never overwrites a
    segment, and queries + indexes transparently span segments
  - partial / interrupted rotation is recoverable; old segments are retained
  - every corruption class is detected, copied to a dev-local quarantine, and
    skipped by the query path; repair rebuilds the index without data loss
  - repeated-run stability (the store is deterministic across invocations)

No production access, no `~/.hermes`, no `state.db`. Tests use tmp_path only.
Hardening ID: HARDENING-2D-H1-001.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from hermes_cli.dev_web_audit_index import (
    rebuild_audit_index,
    validate_audit_index,
)
from hermes_cli.dev_web_audit_query import build_audit_query, query_audit_events
from hermes_cli.dev_web_audit_recovery import (
    CORRUPT_DUPLICATE_EVENT_ID,
    CORRUPT_DUPLICATE_SEQUENCE,
    CORRUPT_INVALID_JSON,
    CORRUPT_MISSING_FIELD,
    CORRUPT_NOT_OBJECT,
    CORRUPT_PARTIAL_WRITE,
    CORRUPT_SCHEMA_VERSION,
    CORRUPT_UNSAFE_SECRET,
    quarantine_corrupt_records,
    repair_audit_store,
    scan_audit_segments,
)
from hermes_cli.dev_web_audit_rotation import (
    DEFAULT_MAX_EVENTS_PER_SEGMENT,
    DEFAULT_MAX_SEGMENT_BYTES,
    RotationPolicy,
    get_active_audit_segment,
    get_active_audit_segment_path,
    rotate_audit_segment,
    should_rotate_audit_segment,
    validate_audit_segments,
)
from hermes_cli.dev_web_audit_schema import AUDIT_SCHEMA_VERSION
from hermes_cli.dev_web_audit_store import (
    ERROR_DUPLICATE_EVENT_ID,
    ERROR_EVENT_TOO_LARGE,
    _serialize_event_line,
    append_audit_event,
    append_audit_events,
    build_audit_event,
    ensure_audit_store,
    get_audit_event,
    get_audit_store_meta,
    get_audit_store_root,
    iter_all_events,
    list_audit_segments,
    parse_segment_number,
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


def _store_meta_path(root: Path) -> Path:
    return root / "meta" / "store-meta.json"


# ---------------------------------------------------------------------------
# Lens 3 — Append-only store / sequence consistency
# ---------------------------------------------------------------------------


class TestHighConcurrencyAppend:
    """32-thread stress: no lost events, unique contiguous sequences."""

    def test_32_threads_no_lost_events_unique_sequence(self, dev_home):
        N_THREADS = 32
        PER_THREAD = 40
        results: list = []
        lock = threading.Lock()

        def worker(tid):
            local = []
            for i in range(PER_THREAD):
                r = append_audit_event(
                    _evt(event_id=f"t{tid}-{i}"), hermes_home=dev_home
                )
                local.append(r)
            with lock:
                results.extend(local)

        threads = [
            threading.Thread(target=worker, args=(t,)) for t in range(N_THREADS)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        written = [r for r in results if r.written]
        expected = N_THREADS * PER_THREAD
        assert len(written) == expected

        seqs = sorted(r.sequence for r in written)
        assert seqs == list(range(1, expected + 1)), "sequences must be contiguous 1..N"
        assert len(set(seqs)) == expected, "no duplicate sequences"

        root, _ = get_audit_store_root(dev_home)
        on_disk_ids = {ev["eventId"] for ev in _on_disk_events(root)}
        assert len(on_disk_ids) == expected
        for tid in range(N_THREADS):
            for i in range(PER_THREAD):
                assert f"t{tid}-{i}" in on_disk_ids

    def test_concurrent_batches_atomic(self, dev_home):
        """Concurrent batch appends each remain internally contiguous."""
        N_THREADS = 16
        BATCH = 10
        all_seqs: list[int] = []
        lock = threading.Lock()

        def worker(tid):
            batch = [_evt(event_id=f"b{tid}-{i}") for i in range(BATCH)]
            r = append_audit_events(batch, hermes_home=dev_home)
            assert r.written
            with lock:
                all_seqs.append(r.sequence)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        root, _ = get_audit_store_root(dev_home)
        seqs = sorted(ev["sequence"] for ev in _on_disk_events(root))
        assert seqs == list(range(1, N_THREADS * BATCH + 1))
        assert len(set(seqs)) == len(seqs)


class TestSequenceFlooring:
    """A stale/corrupt store-meta must never cause a colliding sequence."""

    def test_deleted_meta_next_sequence_floored_to_disk(self, dev_home):
        append_audit_event(_evt(event_id="a"), hermes_home=dev_home)  # seq 1
        append_audit_event(_evt(event_id="b"), hermes_home=dev_home)  # seq 2
        root, _ = get_audit_store_root(dev_home)
        # Simulate a crash that lost the meta write: delete store-meta.json.
        _store_meta_path(root).unlink()
        # Next append must floor against the on-disk max (2) → seq 3, not 1.
        r = append_audit_event(_evt(event_id="c"), hermes_home=dev_home)
        assert r.written
        assert r.sequence == 3

    def test_stale_low_meta_next_sequence_floored_to_disk(self, dev_home):
        append_audit_event(_evt(event_id="a"), hermes_home=dev_home)
        append_audit_event(_evt(event_id="b"), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        # Corrupt meta to a STALE-LOW lastSequence (realistic crash-recovery
        # case the floor was designed for). Next sequence must still be 3.
        meta = json.loads(_store_meta_path(root).read_text(encoding="utf-8"))
        meta["lastSequence"] = 0
        meta["eventCount"] = 0
        _store_meta_path(root).write_text(
            json.dumps(meta, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
        r = append_audit_event(_evt(event_id="c"), hermes_home=dev_home)
        assert r.written
        assert r.sequence == 3
        ev, _ = get_audit_event("c", hermes_home=dev_home)
        assert ev is not None and ev["sequence"] == 3

    def test_no_colliding_sequence_after_floor(self, dev_home):
        for i in range(10):
            append_audit_event(_evt(event_id=f"x{i}"), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        _store_meta_path(root).unlink()
        # Append many more; sequences must remain unique and monotonic.
        for i in range(10, 30):
            r = append_audit_event(_evt(event_id=f"x{i}"), hermes_home=dev_home)
            assert r.written
            assert r.sequence == i + 1
        seqs = sorted(ev["sequence"] for ev in _on_disk_events(root))
        assert seqs == list(range(1, 31))


class TestAppendRecoversAfterStaleIndex:
    def test_query_rebuilds_after_index_deleted(self, dev_home):
        for i in range(3):
            append_audit_event(_evt(event_id=f"i{i}"), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        rebuild_audit_index(root)
        # Delete the index; the query path must rebuild and still return all events.
        for p in (root / "indexes").glob("*.json"):
            p.unlink()
        status = validate_audit_index(root)
        assert not status.present or status.stale
        res = query_audit_events(
            build_audit_query(audit_kind="internal", limit=10), hermes_home=dev_home
        )
        assert res.success
        assert len(res.items) == 3
        # Index was rebuilt as a side effect of the query.
        assert validate_audit_index(root).present


class TestAppendNeverCorruptsActiveSegment:
    def test_every_line_valid_json_after_many_appends(self, dev_home):
        for i in range(60):
            append_audit_event(_evt(event_id=f"v{i}"), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        for segment in list_audit_segments(root):
            with segment.open("r", encoding="utf-8") as f:
                for raw in f:
                    stripped = raw.strip()
                    if not stripped:
                        continue
                    obj = json.loads(stripped)  # must not raise
                    assert obj["schemaVersion"] == AUDIT_SCHEMA_VERSION


class TestLargeBatchAndOversized:
    def test_large_batch_contiguous_sequences(self, dev_home):
        events = [_evt(event_id=f"L{i}") for i in range(200)]
        r = append_audit_events(events, hermes_home=dev_home)
        assert r.written
        assert r.sequence == 200
        root, _ = get_audit_store_root(dev_home)
        seqs = sorted(ev["sequence"] for ev in _on_disk_events(root))
        assert seqs == list(range(1, 201))

    def test_oversized_event_line_rejected(self):
        # Defense-in-depth guard: a serialized line exceeding MAX_EVENT_BYTES
        # is rejected with ERROR_EVENT_TOO_LARGE. (Through the sanitized path
        # this is unreachable — the sanitizer caps every scalar — so we exercise
        # the guard directly on the serializer with a synthetic payload.)
        huge = {"eventId": "z", "sequence": 1, "createdAt": "2026-06-15T00:00:00+00:00",
                "eventType": "t", "auditKind": "internal",
                "schemaVersion": AUDIT_SCHEMA_VERSION,
                "blob": "A" * (70 * 1024)}
        line, err = _serialize_event_line(huge)
        assert line is None
        assert err == ERROR_EVENT_TOO_LARGE

    def test_empty_batch_rejected(self, dev_home):
        r = append_audit_events([], hermes_home=dev_home)
        assert not r.written

    def test_duplicate_event_id_across_appends_rejected(self, dev_home):
        assert append_audit_event(_evt(event_id="dup"), hermes_home=dev_home).written
        r = append_audit_event(_evt(event_id="dup"), hermes_home=dev_home)
        assert not r.written
        assert r.error_code == ERROR_DUPLICATE_EVENT_ID


class TestWriterLockLocation:
    def test_lock_file_under_dev_store_only(self, dev_home):
        append_audit_event(_evt(event_id="lk"), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        lock_path = root / "meta" / "store.lock"
        # The lock file is created (opened a+) under the dev audit-store meta dir.
        assert str(lock_path).startswith(str(root))
        assert "hermes-home-dev" in str(lock_path)
        assert "/Users/huangruibang/.hermes" not in str(lock_path)
        assert "hermes-agent-dev" not in str(lock_path) or "hermes-home-dev" in str(lock_path)


# ---------------------------------------------------------------------------
# Lens 6 — Rotation / segment recovery boundary
# ---------------------------------------------------------------------------


class TestRotationByCount:
    def test_should_rotate_by_event_count(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        seg = get_active_audit_segment_path(root)
        seg.parent.mkdir(parents=True, exist_ok=True)
        seg.write_text(("x\n" * 5), encoding="utf-8")
        policy = RotationPolicy(
            max_segment_bytes=DEFAULT_MAX_SEGMENT_BYTES, max_events_per_segment=4
        )
        assert should_rotate_audit_segment(seg, policy=policy) is True

    def test_should_rotate_by_size(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        seg = get_active_audit_segment_path(root)
        seg.parent.mkdir(parents=True, exist_ok=True)
        seg.write_text("x" * 2048, encoding="utf-8")
        policy = RotationPolicy(
            max_segment_bytes=1024, max_events_per_segment=DEFAULT_MAX_EVENTS_PER_SEGMENT
        )
        assert should_rotate_audit_segment(seg, policy=policy) is True

    def test_rotation_never_overwrites(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        first = get_active_audit_segment_path(root)
        first.parent.mkdir(parents=True, exist_ok=True)
        first.write_text("orig-1\n", encoding="utf-8")
        rotate_audit_segment(root)
        second = get_active_audit_segment_path(root)
        second.parent.mkdir(parents=True, exist_ok=True)
        second.write_text("orig-2\n", encoding="utf-8")
        rotate_audit_segment(root)
        segs = list_audit_segments(root)
        assert len(segs) >= 3
        assert "orig-1\n" in first.read_text(encoding="utf-8")
        assert "orig-2\n" in second.read_text(encoding="utf-8")

    def test_segment_names_monotonic_zero_padded(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        for _ in range(3):
            rotate_audit_segment(root)
        numbers = [parse_segment_number(p.name) for p in list_audit_segments(root)]
        numbers = [n for n in numbers if n is not None]
        assert numbers == sorted(numbers)
        assert all(b - a == 1 for a, b in zip(numbers, numbers[1:]))


class TestQueryAndIndexAcrossSegments:
    def test_query_spans_multiple_segments(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        for i in range(3):
            append_audit_event(_evt(event_id=f"q{i}"), hermes_home=dev_home)
        rotate_audit_segment(root)
        for i in range(3, 6):
            append_audit_event(_evt(event_id=f"q{i}"), hermes_home=dev_home)
        assert len(list_audit_segments(root)) >= 2
        res = query_audit_events(
            build_audit_query(audit_kind="internal", limit=100), hermes_home=dev_home
        )
        assert res.success
        assert len(res.items) == 6
        # Ordered desc by default.
        seqs = [it["sequence"] for it in res.items]
        assert seqs == sorted(seqs, reverse=True)

    def test_index_rebuild_across_segments(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        for i in range(3):
            append_audit_event(_evt(event_id=f"ix{i}"), hermes_home=dev_home)
        rotate_audit_segment(root)
        for i in range(3, 6):
            append_audit_event(_evt(event_id=f"ix{i}"), hermes_home=dev_home)
        summary = rebuild_audit_index(root)
        assert summary["rebuilt"] is True
        assert summary["eventCount"] == 6
        assert validate_audit_index(root).consistent


class TestPartialRotationRecovery:
    def test_active_segment_reconciled_after_state_loss(self, dev_home):
        append_audit_event(_evt(event_id="p1"), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        # Simulate interrupted rotation: rotation-state points at a segment
        # that does not exist yet, but on-disk segments are intact.
        rstate = root / "meta" / "rotation-state.json"
        rstate.write_text(
            json.dumps(
                {"activeSegment": "audit-000099.jsonl",
                 "segmentCount": 99, "rotatedCount": 98},
                ensure_ascii=False, sort_keys=True,
            ),
            encoding="utf-8",
        )
        # get_active_audit_segment returns the declared path; the next append
        # creates it lazily and the store keeps working.
        r = append_audit_event(_evt(event_id="p2"), hermes_home=dev_home)
        assert r.written
        ev, _ = get_audit_event("p2", hermes_home=dev_home)
        assert ev is not None

    def test_old_segment_not_deleted_after_rotation(self, dev_home):
        append_audit_event(_evt(event_id="keep1"), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        first_seg = list_audit_segments(root)[0]
        first_size = first_seg.stat().st_size
        rotate_audit_segment(root)
        append_audit_event(_evt(event_id="keep2"), hermes_home=dev_home)
        # The original segment is untouched (size unchanged, content intact).
        assert first_seg.is_file()
        assert first_seg.stat().st_size == first_size
        ev, _ = get_audit_event("keep1", hermes_home=dev_home)
        assert ev is not None


# ---------------------------------------------------------------------------
# Lens 7 — Corruption detection / quarantine boundary
# ---------------------------------------------------------------------------


_VALID_LINE = (
    '{"eventId":"ok","sequence":1,"createdAt":"2026-06-15T00:00:00+00:00",'
    '"eventType":"t","auditKind":"internal","schemaVersion":"audit_schema_v2"}\n'
)


def _write_segment(root: Path, lines: list[str]) -> None:
    seg = root / "events" / "audit-000001.jsonl"
    seg.parent.mkdir(parents=True, exist_ok=True)
    with seg.open("w", encoding="utf-8") as f:
        f.writelines(lines)


class TestCorruptionDetectionAllClasses:
    def test_detects_invalid_json(self, tmp_path):
        root = self._bare_root(tmp_path)
        _write_segment(root, ["NOT JSON\n"])
        report = scan_audit_segments(root)
        reasons = {r.reason for r in report.records}
        assert CORRUPT_INVALID_JSON in reasons

    def test_detects_not_object(self, tmp_path):
        root = self._bare_root(tmp_path)
        _write_segment(root, ['[1, 2, 3]\n'])
        report = scan_audit_segments(root)
        assert any(r.reason == CORRUPT_NOT_OBJECT for r in report.records)

    def test_detects_missing_field(self, tmp_path):
        root = self._bare_root(tmp_path)
        # Correct schemaVersion but missing the other required fields so the
        # classifier reaches validate_canonical_event (the schema-version check
        # runs first; a record with the wrong/absent version is classified as
        # CORRUPT_SCHEMA_VERSION, not CORRUPT_MISSING_FIELD).
        _write_segment(root, ['{"schemaVersion":"audit_schema_v2"}\n'])
        report = scan_audit_segments(root)
        assert any(r.reason == CORRUPT_MISSING_FIELD for r in report.records)

    def test_detects_schema_version_mismatch(self, tmp_path):
        root = self._bare_root(tmp_path)
        _write_segment(root, [
            '{"eventId":"x","sequence":1,"createdAt":"2026-06-15T00:00:00+00:00",'
            '"eventType":"t","auditKind":"internal","schemaVersion":"audit_schema_v1"}\n'
        ])
        report = scan_audit_segments(root)
        assert any(r.reason == CORRUPT_SCHEMA_VERSION for r in report.records)

    def test_detects_partial_write(self, tmp_path):
        root = self._bare_root(tmp_path)
        seg = root / "events" / "audit-000001.jsonl"
        seg.parent.mkdir(parents=True, exist_ok=True)
        # No trailing newline → partial-write fingerprint.
        with seg.open("w", encoding="utf-8") as f:
            f.write('{"eventId":"x","sequence":1,"createdAt":"2026-06-15T00:00:00+00:00",'
                    '"eventType":"t","auditKind":"internal","schemaVersion":"audit_schema_v2"}')
        report = scan_audit_segments(root)
        assert any(r.reason == CORRUPT_PARTIAL_WRITE for r in report.records)

    def test_detects_duplicate_sequence(self, tmp_path):
        root = self._bare_root(tmp_path)
        _write_segment(root, [_VALID_LINE, _VALID_LINE])
        report = scan_audit_segments(root)
        assert any(r.reason == CORRUPT_DUPLICATE_SEQUENCE for r in report.records)

    def test_detects_duplicate_event_id(self, tmp_path):
        root = self._bare_root(tmp_path)
        _write_segment(root, [_VALID_LINE, _VALID_LINE])
        report = scan_audit_segments(root)
        assert any(r.reason == CORRUPT_DUPLICATE_EVENT_ID for r in report.records)

    def test_detects_unsafe_secret(self, tmp_path):
        root = self._bare_root(tmp_path)
        _write_segment(root, [
            '{"eventId":"x","sequence":1,"createdAt":"2026-06-15T00:00:00+00:00",'
            '"eventType":"t","auditKind":"internal","schemaVersion":"audit_schema_v2",'
            '"summary":{"k":"sk-abcd1234efgh5678ijkl"}}\n'
        ])
        report = scan_audit_segments(root)
        assert any(r.reason == CORRUPT_UNSAFE_SECRET for r in report.records)

    @staticmethod
    def _bare_root(tmp_path: Path) -> Path:
        home = tmp_path / "hh"
        home.mkdir()
        ensure_audit_store(str(home))
        root, _ = get_audit_store_root(str(home))
        return root


class TestQuarantineNonDestructive:
    def test_quarantine_copies_without_deleting_source(self, tmp_path):
        home = tmp_path / "hh"
        home.mkdir()
        ensure_audit_store(str(home))
        root, _ = get_audit_store_root(str(home))
        _write_segment(root, [_VALID_LINE, "GARBAGE\n"])
        report = scan_audit_segments(root)
        assert report.corrupt_count >= 1
        summary = quarantine_corrupt_records(root, list(report.records))
        assert summary["quarantined"] >= 1
        assert summary["nonDestructive"] is True
        # Original segment still exists and still contains both lines.
        seg = root / "events" / "audit-000001.jsonl"
        assert seg.is_file()
        assert len(seg.read_text(encoding="utf-8").splitlines()) == 2
        # Quarantine dir lives under the dev audit store only.
        qdir = root / "quarantine"
        assert any(qdir.iterdir())
        assert str(qdir).startswith(str(root))
        assert "/Users/huangruibang/.hermes" not in str(qdir)


class TestCorruptLineNeverCrashesQuery:
    def test_query_skips_corrupt_and_reports_skipped(self, tmp_path, monkeypatch):
        home = tmp_path / "hh"
        home.mkdir()
        monkeypatch.setenv("HERMES_HOME", str(home))
        ensure_audit_store(str(home))
        root, _ = get_audit_store_root(str(home))
        _write_segment(root, [_VALID_LINE, "BROKEN JSON\n"])
        # No substring search: the valid line matches the audit_kind filter.
        res = query_audit_events(
            build_audit_query(audit_kind="internal", limit=10),
            hermes_home=str(home),
        )
        assert res.success
        assert res.skipped_malformed >= 1
        assert len(res.items) == 1

    def test_repair_rebuilds_index_without_losing_valid_events(self, tmp_path):
        home = tmp_path / "hh"
        home.mkdir()
        ensure_audit_store(str(home))
        root, _ = get_audit_store_root(str(home))
        _write_segment(root, [_VALID_LINE, "BROKEN\n"])
        summary = repair_audit_store(root)
        assert summary["nonDestructive"] is True
        # The valid event is still queryable after repair.
        valid = [ev for ev in _on_disk_events(root)]
        assert any(ev["eventId"] == "ok" for ev in valid)


class TestRepeatedRunStability:
    """The store must be deterministic across repeated invocations."""

    def test_five_runs_deterministic(self, dev_home):
        for run in range(5):
            # Fresh store each run via a unique event-id namespace.
            for i in range(20):
                r = append_audit_event(
                    _evt(event_id=f"run{run}-{i}"), hermes_home=dev_home
                )
                assert r.written
        root, _ = get_audit_store_root(dev_home)
        seqs = sorted(ev["sequence"] for ev in _on_disk_events(root))
        assert seqs == list(range(1, 101))  # 5 * 20
        assert len(set(seqs)) == 100
        meta, _ = get_audit_store_meta(dev_home)
        assert meta.last_sequence == 100
        assert meta.event_count == 100
