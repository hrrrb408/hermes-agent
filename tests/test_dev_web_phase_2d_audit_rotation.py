"""Phase 2D — Audit rotation policy tests.

Verifies rotation by size and by event count, monotonic segment naming,
querying across rotated segments, durable rotation state, and that rotation
never overwrites or deletes existing segments.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.dev_web_audit_rotation import (
    DEFAULT_MAX_EVENTS_PER_SEGMENT,
    DEFAULT_MAX_SEGMENT_BYTES,
    RotationPolicy,
    get_active_audit_segment_path,
    get_active_audit_segment_number,
    list_audit_segments_rotation,
    load_rotation_state,
    rotate_audit_segment,
    should_rotate_audit_segment,
    validate_audit_segments,
)
from hermes_cli.dev_web_audit_store import (
    append_audit_event,
    build_audit_event,
    ensure_audit_store,
    get_audit_store_root,
    list_audit_segments,
)


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return str(home)


def _evt(i):
    return build_audit_event(
        event_type="rot", audit_kind="internal", event_id=f"r{i}",
    )


class TestShouldRotate:
    def test_no_rotation_when_empty(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        seg = get_active_audit_segment_path(root)
        assert should_rotate_audit_segment(seg) is False

    def test_rotation_by_event_count(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        seg = get_active_audit_segment_path(root)
        seg.parent.mkdir(parents=True, exist_ok=True)
        seg.write_text(("x\n" * 5), encoding="utf-8")
        policy = RotationPolicy(max_segment_bytes=1024 * 1024, max_events_per_segment=4)
        assert should_rotate_audit_segment(seg, policy=policy) is True

    def test_rotation_by_size(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        seg = get_active_audit_segment_path(root)
        seg.parent.mkdir(parents=True, exist_ok=True)
        seg.write_text("x" * 2048, encoding="utf-8")
        policy = RotationPolicy(max_segment_bytes=1024, max_events_per_segment=10000)
        assert should_rotate_audit_segment(seg, policy=policy) is True


class TestRotateExecution:
    def test_rotate_creates_new_segment(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        seg = get_active_audit_segment_path(root)
        seg.parent.mkdir(parents=True, exist_ok=True)
        seg.write_text("seed\n", encoding="utf-8")
        new_seg, rotated = rotate_audit_segment(root)
        assert rotated is True
        assert new_seg.name == "audit-000002.jsonl"
        assert new_seg.exists()
        # Old segment preserved.
        assert seg.exists()

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
        # Three distinct segments, originals intact.
        segs = list_audit_segments(root)
        assert len(segs) >= 3
        assert "orig-1\n" in first.read_text(encoding="utf-8")
        assert "orig-2\n" in second.read_text(encoding="utf-8")

    def test_segment_numbers_monotonic(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        for _ in range(3):
            seg = get_active_audit_segment_path(root)
            seg.parent.mkdir(parents=True, exist_ok=True)
            seg.write_text("x\n", encoding="utf-8")
            rotate_audit_segment(root)
        from hermes_cli.dev_web_audit_store import list_audit_segment_numbers
        nums = list_audit_segment_numbers(root)
        assert nums == sorted(nums)


class TestRotationState:
    def test_state_durable(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        seg = get_active_audit_segment_path(root)
        seg.parent.mkdir(parents=True, exist_ok=True)
        seg.write_text("x\n", encoding="utf-8")
        rotate_audit_segment(root)
        state = load_rotation_state(root)
        assert state["activeSegment"] == "audit-000002.jsonl"
        assert state["rotatedCount"] >= 1

    def test_validate_segments(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        seg = get_active_audit_segment_path(root)
        seg.parent.mkdir(parents=True, exist_ok=True)
        seg.write_text("x\n", encoding="utf-8")
        rotate_audit_segment(root)
        info = validate_audit_segments(root)
        assert info["segmentCount"] >= 2
        assert info["monotonic"] is True


class TestQueryAcrossSegments:
    def test_append_continues_after_rotation(self, dev_home):
        ensure_audit_store(dev_home)
        # Force rotation by count by writing 3 then rotating.
        for i in range(3):
            append_audit_event(_evt(i), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        rotate_audit_segment(root)
        # New events land in segment 2.
        for i in range(3, 6):
            append_audit_event(_evt(i), hermes_home=dev_home)
        segs = list_audit_segments(root)
        assert len(segs) >= 2
        # All 6 events are durable across both segments.
        from hermes_cli.dev_web_audit_store import iter_all_events
        ids = {
            ev["eventId"]
            for _s, _l, ev, _r in iter_all_events(root)
            if ev is not None
        }
        for i in range(6):
            assert f"r{i}" in ids


class TestPolicyValidation:
    def test_policy_defaults(self):
        p = RotationPolicy()
        assert p.max_segment_bytes == DEFAULT_MAX_SEGMENT_BYTES
        assert p.max_events_per_segment == DEFAULT_MAX_EVENTS_PER_SEGMENT

    def test_policy_rejects_tiny_size(self):
        p = RotationPolicy(max_segment_bytes=10)
        assert p.validate() is not None

    def test_get_active_segment_number_default(self, dev_home):
        root, _ = ensure_audit_store(dev_home)
        assert get_active_audit_segment_number(root) == 1
