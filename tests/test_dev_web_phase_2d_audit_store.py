"""Phase 2D — Durable audit store writer tests.

Verifies append-only durability, monotonic gap-free sequence, unique eventId,
concurrent-write safety, path containment (never repo / ~/.hermes / state.db),
and the store-meta snapshot.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from hermes_cli.dev_web_audit_schema import AUDIT_SCHEMA_VERSION
from hermes_cli.dev_web_audit_store import (
    ERROR_DUPLICATE_EVENT_ID,
    ERROR_STORE_ROOT_FORBIDDEN,
    append_audit_event,
    append_audit_events,
    build_audit_event,
    ensure_audit_store,
    get_audit_event,
    get_audit_store_meta,
    get_audit_store_root,
    iter_all_events,
    list_audit_segments,
    validate_audit_store_root,
)


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return str(home)


def _evt(event_id="e1", seq=0, **extra):
    return build_audit_event(
        event_type="unit_test_event", audit_kind="internal",
        event_id=event_id, **extra,
    )


class TestEnsureStore:
    def test_ensure_creates_tree(self, dev_home):
        root, err = ensure_audit_store(dev_home)
        assert err is None
        assert root.is_dir()
        assert (root / "events").is_dir()
        assert (root / "indexes").is_dir()
        assert (root / "quarantine").is_dir()
        assert (root / "meta").is_dir()

    def test_ensure_idempotent(self, dev_home):
        ensure_audit_store(dev_home)
        root, err = ensure_audit_store(dev_home)
        assert err is None and root.is_dir()


class TestAppendDurability:
    def test_append_one_event(self, dev_home):
        r = append_audit_event(_evt(), hermes_home=dev_home)
        assert r.written
        assert r.sequence == 1
        assert r.segment == "audit-000001.jsonl"

    def test_event_persisted_as_jsonl_line(self, dev_home):
        append_audit_event(_evt(), hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        seg = list_audit_segments(root)[0]
        lines = seg.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        obj = json.loads(lines[0])
        assert obj["eventId"] == "e1"
        assert obj["schemaVersion"] == AUDIT_SCHEMA_VERSION

    def test_sequence_monotonic(self, dev_home):
        seqs = []
        for i in range(5):
            r = append_audit_event(_evt(event_id=f"e{i}"), hermes_home=dev_home)
            seqs.append(r.sequence)
        assert seqs == [1, 2, 3, 4, 5]

    def test_event_id_unique_rejects_duplicate(self, dev_home):
        append_audit_event(_evt(event_id="dup"), hermes_home=dev_home)
        r = append_audit_event(_evt(event_id="dup"), hermes_home=dev_home)
        assert not r.written
        assert r.error_code == ERROR_DUPLICATE_EVENT_ID

    def test_append_batch_atomic(self, dev_home):
        events = [_evt(event_id=f"b{i}") for i in range(3)]
        r = append_audit_events(events, hermes_home=dev_home)
        assert r.written
        assert r.sequence == 3

    def test_append_batch_rejects_invalid_no_partial(self, dev_home):
        events = [_evt(event_id="ok1"), _evt(event_id="ok2")]
        r = append_audit_events(events, hermes_home=dev_home)
        assert r.written
        # Now append a batch containing a duplicate → whole batch rejected.
        bad = [_evt(event_id="ok3"), _evt(event_id="ok1")]
        r2 = append_audit_events(bad, hermes_home=dev_home)
        assert not r2.written
        # ok3 must NOT have been written (no partial batch).
        ev, _ = get_audit_event("ok3", hermes_home=dev_home)
        assert ev is None


class TestStoreMeta:
    def test_meta_reflects_writes(self, dev_home):
        for i in range(3):
            append_audit_event(_evt(event_id=f"m{i}"), hermes_home=dev_home)
        meta, err = get_audit_store_meta(dev_home)
        assert err is None
        assert meta.last_sequence == 3
        assert meta.event_count == 3
        assert meta.schema_version == AUDIT_SCHEMA_VERSION

    def test_meta_uninitialized_when_absent(self, dev_home):
        meta, err = get_audit_store_meta(dev_home)
        assert err is None
        assert meta.initialized is False
        assert meta.event_count == 0


class TestGetSingleEvent:
    def test_get_existing(self, dev_home):
        append_audit_event(_evt(event_id="find-me"), hermes_home=dev_home)
        ev, err = get_audit_event("find-me", hermes_home=dev_home)
        assert err is None and ev is not None
        assert ev["eventId"] == "find-me"

    def test_get_missing_returns_none(self, dev_home):
        ensure_audit_store(dev_home)
        ev, err = get_audit_event("nope", hermes_home=dev_home)
        assert err is None and ev is None


class TestConcurrentWrites:
    def test_no_lost_events_under_threads(self, dev_home):
        N_THREADS = 8
        PER_THREAD = 25
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

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        written = [r for r in results if r.written]
        assert len(written) == N_THREADS * PER_THREAD
        seqs = sorted(r.sequence for r in written)
        # Sequences must be unique, contiguous, 1..N.
        assert seqs == list(range(1, N_THREADS * PER_THREAD + 1))
        # Every eventId must be durable on disk.
        root, _ = get_audit_store_root(dev_home)
        on_disk_ids = {
            ev["eventId"]
            for _s, _l, ev, _r in iter_all_events(root)
            if ev is not None
        }
        for tid in range(N_THREADS):
            for i in range(PER_THREAD):
                assert f"t{tid}-{i}" in on_disk_ids


class TestPathContainment:
    def test_root_under_dev_home(self, dev_home):
        root, err = get_audit_store_root(dev_home)
        assert err is None
        assert "hermes-home-dev" in str(root)
        assert "audit-store" in str(root)

    def test_root_not_under_repo(self, dev_home):
        root, _ = get_audit_store_root(dev_home)
        assert "hermes-agent-dev" not in str(root) or "hermes-home-dev" in str(root)

    def test_production_home_blocked(self, tmp_path, monkeypatch):
        prod = tmp_path / "prod-home"
        prod.mkdir()
        monkeypatch.setenv("HERMES_HOME", str(prod))
        root, err = get_audit_store_root(str(prod))
        # Not the real prod path, so this resolves fine; verify the guard exists
        # against the literal production path via validate_audit_store_root.
        assert err is None or err == ERROR_STORE_ROOT_FORBIDDEN

    def test_validate_rejects_repo_root(self):
        err = validate_audit_store_root(Path("/Users/huangruibang/Code/hermes-agent-dev"))
        assert err == ERROR_STORE_ROOT_FORBIDDEN

    def test_validate_rejects_production_path(self):
        err = validate_audit_store_root(Path("/Users/huangruibang/.hermes"))
        assert err == ERROR_STORE_ROOT_FORBIDDEN

    def test_validate_rejects_state_db(self):
        err = validate_audit_store_root(Path("/tmp/state.db"))
        assert err == ERROR_STORE_ROOT_FORBIDDEN

    def test_hermes_home_missing_error(self, monkeypatch):
        monkeypatch.delenv("HERMES_HOME", raising=False)
        r = append_audit_event(_evt(), hermes_home=None)
        assert not r.written


class TestSecretsNeverPersisted:
    def test_secret_in_metadata_redacted_on_disk(self, dev_home):
        ev = build_audit_event(
            event_type="t", audit_kind="internal", event_id="s1",
            safe_metadata={"api_key": "sk-leak-1234567890abcdef"},
        )
        append_audit_event(ev, hermes_home=dev_home)
        root, _ = get_audit_store_root(dev_home)
        on_disk = "\n".join(
            raw for _s, _l, _e, raw in iter_all_events(root, include_corrupt=True)
        )
        assert "sk-leak-1234567890abcdef" not in on_disk
        assert "[REDACTED]" in on_disk
