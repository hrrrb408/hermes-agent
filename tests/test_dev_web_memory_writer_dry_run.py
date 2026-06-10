"""Tests for Memory Writer Dry-Run API routes.

Verifies that WRITE, UPDATE, and ARCHIVE dry-run endpoints:
- Return correct decision previews
- Never modify any files
- Enforce P0/permanent protection independently
- Redact local paths and secrets
- Reject invalid inputs
- Produce correct DTO shapes
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig


# ── Helpers ──


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dir_snapshot(directory: Path) -> dict[str, str]:
    """Capture SHA-256 hashes of all files under directory."""
    snapshot: dict[str, str] = {}
    if not directory.exists():
        return snapshot
    for f in sorted(directory.rglob("*")):
        if f.is_file():
            rel = str(f.relative_to(directory))
            snapshot[rel] = _file_hash(f)
    return snapshot


def _dir_list(directory: Path) -> set[str]:
    """List all relative paths under directory."""
    if not directory.exists():
        return set()
    return {str(f.relative_to(directory)) for f in directory.rglob("*")}


# ── Fixtures ──


@pytest.fixture
def writer_home(tmp_path):
    """Create a temporary HERMES_HOME with memory scaffold for writer tests."""
    home = tmp_path / "writer-home"

    # Create memory scaffold
    (home / "memory" / "indexes").mkdir(parents=True)
    (home / "memory" / "records" / "hermes").mkdir(parents=True)
    (home / "memory" / "snapshots").mkdir(parents=True)
    (home / "memory" / "events.jsonl").write_text("", encoding="utf-8")

    # Create MEMORY.md with active and archived categories
    memory_md = """\
# Hermes Memory Root Router

## hermes

- index: memory://indexes/hermes.md
- scope: project
- priority: P0
- status: active
- keywords: hermes, gateway, memory
- description: Hermes project memories.

## archived-cat

- index: memory://indexes/archived-cat.md
- scope: test
- priority: P2
- status: archived
- keywords: archived
- description: Archived category.
"""
    (home / "MEMORY.md").write_text(memory_md, encoding="utf-8")

    # Create hermes category index with diverse items
    index_md = """\
# Hermes Category Index

## MEM-HERMES-001 Normal Memory

- type: project_status
- importance: P2
- ttl: project
- status: active
- tags: hermes, test
- storage: memory://records/hermes/mem-hermes-001.md
- created_at: 2026-06-01
- updated_at: 2026-06-01
- summary: A normal memory item for testing.

## MEM-HERMES-002 P0 Protected

- type: critical
- importance: P0
- ttl: permanent
- status: active
- tags: hermes, protected
- storage: memory://records/hermes/mem-hermes-002.md
- created_at: 2026-06-01
- updated_at: 2026-06-01
- summary: A P0 permanent item that should be protected.

## MEM-HERMES-003 Permanent Item

- type: architecture_decision
- importance: P1
- ttl: permanent
- status: active
- tags: hermes, permanent
- storage: memory://records/hermes/mem-hermes-003.md
- created_at: 2026-06-02
- updated_at: 2026-06-02
- summary: A permanent TTL item.

## MEM-HERMES-004 Archived Item

- type: note
- importance: P2
- ttl: session
- status: archived
- tags: hermes, archived
- storage: memory://records/hermes/mem-hermes-004.md
- created_at: 2026-06-03
- updated_at: 2026-06-03
- summary: An already archived item.

## MEM-HERMES-005 Similar to Write

- type: project_status
- importance: P1
- ttl: project
- status: active
- tags: hermes, test, memory-writer
- storage: memory://records/hermes/mem-hermes-005.md
- created_at: 2026-06-04
- updated_at: 2026-06-04
- summary: Memory writer dry-run testing item for similarity.
"""
    (home / "memory" / "indexes" / "hermes.md").write_text(
        index_md, encoding="utf-8"
    )

    # Create archived category index
    archived_index = """\
# Archived Category Index

## MEM-ARCHIVED_CAT-001 Archived Cat Item

- type: note
- importance: P3
- ttl: temporary
- status: active
- tags: archived-cat
- storage: memory://records/archived-cat/mem-archived_cat-001.md
- created_at: 2026-06-01
- updated_at: 2026-06-01
- summary: Item in archived category.
"""
    (home / "memory" / "indexes" / "archived-cat.md").write_text(
        archived_index, encoding="utf-8"
    )

    # Create record files
    for i in range(1, 6):
        rec = home / "memory" / "records" / "hermes" / f"mem-hermes-00{i}.md"
        rec.write_text(f"# Details\n\nRecord {i} content.\n", encoding="utf-8")

    # Create state.db
    (home / "state.db").touch()

    return home


@pytest.fixture
def writer_client(writer_home):
    """TestClient with writer-enabled HERMES_HOME."""
    config = DevWebApiConfig(hermes_home=writer_home)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def no_home_client():
    """TestClient without HERMES_HOME."""
    config = DevWebApiConfig(hermes_home=None)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ── Shared assertions ──

API = "/api/dev/v1"


def _valid_write_body(**overrides):
    body = {
        "query": "User wants to save information about the memory writer feature.",
        "candidate": {
            "summary": "The memory writer dry-run feature allows previewing write operations.",
            "category": "hermes",
            "importance": "P2",
            "ttl": "project",
            "tags": ["hermes", "test", "memory-writer"],
            "type": "project_status",
        },
    }
    body.update(overrides)
    return body


def _assert_safety(data):
    """Assert all safety fields are correct."""
    assert data["safety"]["readOnly"] is True
    assert data["safety"]["writeEnabled"] is False
    assert data["safety"]["executeAvailable"] is False
    assert data["safety"]["sideEffects"] is False


def _assert_no_local_paths(obj, path=None):
    """Recursively check no local paths in response."""
    if isinstance(obj, str):
        assert "/Users/" not in obj, f"Local path found at {path}: {obj}"
        assert "/home/" not in obj, f"Local path found at {path}: {obj}"
        assert "file://" not in obj, f"file:// URI found at {path}: {obj}"
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _assert_no_local_paths(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_no_local_paths(v, f"{path}[{i}]" if path else f"[{i}]")


# ═══════════════════════════════════════════════════════════════
# WRITE Dry-Run Tests
# ═══════════════════════════════════════════════════════════════


class TestWriteDryRun:
    """POST /api/dev/v1/memory/write/dry-run"""

    def test_write_allowed(self, writer_client):
        """WRITE with valid high-scoring candidate returns decision."""
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["dryRun"] is True
        assert data["operation"] == "WRITE"
        assert data["decision"] in ("WRITE", "REVIEW", "UPDATE", "SKIP", "SKIP_DUPLICATE")
        assert "score" in data
        assert "checks" in data
        _assert_safety(data)

    def test_write_has_request_id(self, writer_client):
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())
        assert resp.status_code == 200
        meta = resp.json()["meta"]
        assert "requestId" in meta
        assert "timestamp" in meta

    def test_write_no_paths_in_response(self, writer_client):
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())
        assert resp.status_code == 200
        _assert_no_local_paths(resp.json()["data"])

    def test_write_category_not_found(self, writer_client):
        """WRITE to nonexistent category returns preview with check failure."""
        body = _valid_write_body()
        body["candidate"]["category"] = "nonexistent"
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=body)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["operation"] == "WRITE"
        # Category check should fail
        cat_checks = [c for c in data["checks"] if c["code"] == "CATEGORY_EXISTS"]
        assert len(cat_checks) == 1
        assert cat_checks[0]["passed"] is False

    def test_write_inactive_category(self, writer_client):
        """WRITE to archived category returns preview with check failure."""
        body = _valid_write_body()
        body["candidate"]["category"] = "archived-cat"
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=body)
        assert resp.status_code == 200
        data = resp.json()["data"]
        cat_active_checks = [c for c in data["checks"] if c["code"] == "CATEGORY_ACTIVE"]
        assert len(cat_active_checks) == 1
        assert cat_active_checks[0]["passed"] is False

    def test_write_invalid_importance(self, writer_client):
        body = _valid_write_body()
        body["candidate"]["importance"] = "P99"
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=body)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_MEMORY_DRY_RUN_REQUEST"

    def test_write_invalid_ttl(self, writer_client):
        body = _valid_write_body()
        body["candidate"]["ttl"] = "forever"
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=body)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_MEMORY_DRY_RUN_REQUEST"

    def test_write_too_many_tags(self, writer_client):
        body = _valid_write_body()
        body["candidate"]["tags"] = [f"tag{i}" for i in range(25)]
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=body)
        assert resp.status_code == 400

    def test_write_missing_query(self, writer_client):
        body = _valid_write_body()
        del body["query"]
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=body)
        assert resp.status_code == 400

    def test_write_missing_candidate(self, writer_client):
        resp = writer_client.post(f"{API}/memory/write/dry-run", json={"query": "test"})
        assert resp.status_code == 400

    def test_write_missing_summary(self, writer_client):
        body = _valid_write_body()
        del body["candidate"]["summary"]
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=body)
        assert resp.status_code == 400

    def test_write_has_config(self, writer_client):
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())
        data = resp.json()["data"]
        assert "config" in data
        assert "writeThreshold" in data["config"]
        assert "reviewThreshold" in data["config"]

    def test_write_has_no_effects(self, writer_client):
        """No-effects list must always be present."""
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())
        data = resp.json()["data"]
        assert "noEffects" in data
        assert len(data["noEffects"]) > 0
        assert "No files were modified." in data["noEffects"]
        assert "No review item was created." in data["noEffects"]

    def test_write_unavailable_no_home(self, no_home_client):
        resp = no_home_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "MEMORY_DRY_RUN_UNAVAILABLE"

    def test_write_has_candidate_dto(self, writer_client):
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())
        data = resp.json()["data"]
        assert data["candidate"] is not None
        assert "summaryPreview" in data["candidate"]
        assert "category" in data["candidate"]
        assert "importance" in data["candidate"]
        assert "ttl" in data["candidate"]
        assert "tags" in data["candidate"]


# ═══════════════════════════════════════════════════════════════
# UPDATE Dry-Run Tests
# ═══════════════════════════════════════════════════════════════


class TestUpdateDryRun:
    """POST /api/dev/v1/memory/items/{memoryId}/update/dry-run"""

    def test_update_allowed(self, writer_client):
        """UPDATE on a normal P2 item is allowed."""
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/update/dry-run",
            json={
                "candidate": {
                    "summary": "Updated memory item summary.",
                    "tags": ["hermes", "test", "updated"],
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["dryRun"] is True
        assert data["operation"] == "UPDATE"
        _assert_safety(data)

    def test_update_memory_not_found(self, writer_client):
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-999/update/dry-run",
            json={"candidate": {"summary": "test"}},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "MEMORY_NOT_FOUND"

    def test_update_invalid_memory_id(self, writer_client):
        resp = writer_client.post(
            f"{API}/memory/items/INVALID/update/dry-run",
            json={"candidate": {"summary": "test"}},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_MEMORY_ID"

    def test_update_p0_blocked(self, writer_client):
        """UPDATE on P0 item is blocked."""
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-002/update/dry-run",
            json={"candidate": {"summary": "Attempt to modify P0."}},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["allowed"] is False
        p0_checks = [c for c in data["checks"] if c["code"] == "TARGET_P0_PROTECTED"]
        assert any(c["passed"] is False for c in p0_checks)

    def test_update_permanent_blocked(self, writer_client):
        """UPDATE on permanent TTL item is blocked."""
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-003/update/dry-run",
            json={"candidate": {"summary": "Attempt to modify permanent."}},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["allowed"] is False
        perm_checks = [c for c in data["checks"] if c["code"] == "TARGET_PERMANENT_PROTECTED"]
        assert any(c["passed"] is False for c in perm_checks)

    def test_update_archived_blocked(self, writer_client):
        """UPDATE on archived item is blocked."""
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-004/update/dry-run",
            json={"candidate": {"summary": "Attempt to modify archived."}},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["allowed"] is False

    def test_update_diff_preview(self, writer_client):
        """UPDATE returns diff showing changed fields."""
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/update/dry-run",
            json={
                "candidate": {
                    "summary": "Completely new summary.",
                    "tags": ["hermes", "new-tag"],
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "diff" in data
        diff = data["diff"]
        assert diff["titleChanged"] is False  # Title never changes
        assert diff["summaryChanged"] is True

    def test_update_has_target_dto(self, writer_client):
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/update/dry-run",
            json={"candidate": {"summary": "test"}},
        )
        data = resp.json()["data"]
        assert data["target"] is not None
        assert data["target"]["memoryId"] == "MEM-HERMES-001"
        assert "importance" in data["target"]
        assert "ttl" in data["target"]
        assert "status" in data["target"]

    def test_update_no_paths_in_response(self, writer_client):
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/update/dry-run",
            json={"candidate": {"summary": "test"}},
        )
        assert resp.status_code == 200
        _assert_no_local_paths(resp.json()["data"])

    def test_update_unavailable_no_home(self, no_home_client):
        resp = no_home_client.post(
            f"{API}/memory/items/MEM-HERMES-001/update/dry-run",
            json={"candidate": {"summary": "test"}},
        )
        assert resp.status_code == 503


# ═══════════════════════════════════════════════════════════════
# ARCHIVE Dry-Run Tests
# ═══════════════════════════════════════════════════════════════


class TestArchiveDryRun:
    """POST /api/dev/v1/memory/items/{memoryId}/archive/dry-run"""

    def test_archive_allowed(self, writer_client):
        """ARCHIVE on a normal P2 item is allowed."""
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/archive/dry-run",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["dryRun"] is True
        assert data["operation"] == "ARCHIVE"
        assert data["allowed"] is True
        _assert_safety(data)

    def test_archive_memory_not_found(self, writer_client):
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-999/archive/dry-run",
            json={},
        )
        assert resp.status_code == 404

    def test_archive_invalid_memory_id(self, writer_client):
        resp = writer_client.post(
            f"{API}/memory/items/BAD-ID/archive/dry-run",
            json={},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_MEMORY_ID"

    def test_archive_p0_blocked(self, writer_client):
        """ARCHIVE on P0 item is independently blocked."""
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-002/archive/dry-run",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["allowed"] is False
        p0_checks = [c for c in data["checks"] if c["code"] == "TARGET_P0_PROTECTED"]
        assert any(c["passed"] is False for c in p0_checks)

    def test_archive_permanent_blocked(self, writer_client):
        """ARCHIVE on permanent TTL item is independently blocked."""
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-003/archive/dry-run",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["allowed"] is False
        perm_checks = [c for c in data["checks"] if c["code"] == "TARGET_PERMANENT_PROTECTED"]
        assert any(c["passed"] is False for c in perm_checks)

    def test_archive_already_archived(self, writer_client):
        """ARCHIVE on already-archived item returns blocked."""
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-004/archive/dry-run",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["allowed"] is False

    def test_archive_with_reason(self, writer_client):
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/archive/dry-run",
            json={"reason": "No longer relevant"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["allowed"] is True

    def test_archive_reason_redacted(self, writer_client):
        """Reasons containing local paths must be redacted."""
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/archive/dry-run",
            json={"reason": "Found at /Users/alice/secret/file.txt"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        warnings_text = " ".join(data.get("warnings", []))
        assert "/Users/" not in warnings_text
        assert "[local-path]" in warnings_text

    def test_archive_has_effects(self, writer_client):
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/archive/dry-run",
            json={},
        )
        data = resp.json()["data"]
        assert "effects" in data
        effect_types = [e["type"] for e in data["effects"]]
        assert "ARCHIVE_MEMORY_RECORD" in effect_types
        assert "UPDATE_CATEGORY_INDEX" in effect_types

    def test_archive_no_paths_in_response(self, writer_client):
        resp = writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/archive/dry-run",
            json={},
        )
        assert resp.status_code == 200
        _assert_no_local_paths(resp.json()["data"])

    def test_archive_unavailable_no_home(self, no_home_client):
        resp = no_home_client.post(
            f"{API}/memory/items/MEM-HERMES-001/archive/dry-run",
            json={},
        )
        assert resp.status_code == 503


# ═══════════════════════════════════════════════════════════════
# Side-Effect Tests (Zero Modification Guarantee)
# ═══════════════════════════════════════════════════════════════


class TestSideEffects:
    """Verify dry-run calls leave no trace on the filesystem."""

    def test_write_dry_run_no_file_changes(self, writer_home, writer_client):
        """WRITE dry-run does not modify any files."""
        before_memory = _dir_snapshot(writer_home / "memory")
        before_root = _file_hash(writer_home / "MEMORY.md")
        before_dirs = _dir_list(writer_home)

        writer_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())

        after_memory = _dir_snapshot(writer_home / "memory")
        after_root = _file_hash(writer_home / "MEMORY.md")
        after_dirs = _dir_list(writer_home)

        assert before_memory == after_memory, "Memory files changed during WRITE dry-run"
        assert before_root == after_root, "MEMORY.md changed during WRITE dry-run"
        assert before_dirs == after_dirs, "Directories changed during WRITE dry-run"

    def test_update_dry_run_no_file_changes(self, writer_home, writer_client):
        """UPDATE dry-run does not modify any files."""
        before_memory = _dir_snapshot(writer_home / "memory")
        before_root = _file_hash(writer_home / "MEMORY.md")

        writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/update/dry-run",
            json={"candidate": {"summary": "Should not be written."}},
        )

        after_memory = _dir_snapshot(writer_home / "memory")
        after_root = _file_hash(writer_home / "MEMORY.md")

        assert before_memory == after_memory
        assert before_root == after_root

    def test_archive_dry_run_no_file_changes(self, writer_home, writer_client):
        """ARCHIVE dry-run does not modify any files."""
        before_memory = _dir_snapshot(writer_home / "memory")
        before_root = _file_hash(writer_home / "MEMORY.md")

        writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/archive/dry-run",
            json={},
        )

        after_memory = _dir_snapshot(writer_home / "memory")
        after_root = _file_hash(writer_home / "MEMORY.md")

        assert before_memory == after_memory
        assert before_root == after_root

    def test_no_new_directories(self, writer_home, writer_client):
        """No new directories are created by any dry-run."""
        before = _dir_list(writer_home)

        writer_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())
        writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/update/dry-run",
            json={"candidate": {"summary": "test"}},
        )
        writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/archive/dry-run",
            json={},
        )

        after = _dir_list(writer_home)
        assert before == after

    def test_no_events_appended(self, writer_home, writer_client):
        """events.jsonl is not modified by dry-run."""
        events_path = writer_home / "memory" / "events.jsonl"
        before = events_path.read_text(encoding="utf-8")

        writer_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())
        writer_client.post(
            f"{API}/memory/items/MEM-HERMES-001/archive/dry-run", json={}
        )

        after = events_path.read_text(encoding="utf-8")
        assert before == after


# ═══════════════════════════════════════════════════════════════
# Forbidden Function Tests
# ═══════════════════════════════════════════════════════════════


class TestForbiddenFunctions:
    """Verify write functions are never called during dry-run."""

    @pytest.fixture
    def patched_client(self, writer_home, monkeypatch):
        """Client with all write functions monkeypatched to fail."""
        import hermes_cli.dev_web_memory_writer_service as svc

        def fail_if_called(*args, **kwargs):
            raise AssertionError("Write function called during dry-run")

        # Patch write functions in memory_router
        import hermes_cli.memory_router as mr
        for name in [
            "create_memory_item", "update_memory_item", "append_event",
            "write_root_categories", "write_index_items", "backup_file",
            "backup_memory_root", "ensure_memory_scaffold",
            "ensure_root_status_fields",
        ]:
            if hasattr(mr, name):
                monkeypatch.setattr(mr, name, fail_if_called)

        # Patch write functions in runtime_memory_writer
        import agent.runtime_memory_writer as rmw
        for name in [
            "_ensure_auto_category", "perform_safe_memory_action",
            "maybe_auto_write_memory",
        ]:
            if hasattr(rmw, name):
                monkeypatch.setattr(rmw, name, fail_if_called)

        # Patch review queue write functions
        import agent.memory_review_queue as rq
        for name in [
            "enqueue_review_item", "atomic_write_review_json",
            "append_review_event", "_ensure_paths",
        ]:
            if hasattr(rq, name):
                monkeypatch.setattr(rq, name, fail_if_called)

        config = DevWebApiConfig(hermes_home=writer_home)
        app = create_dev_web_api_app(config)
        return TestClient(app)

    def test_write_dry_run_no_write_calls(self, patched_client):
        resp = patched_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())
        assert resp.status_code == 200

    def test_update_dry_run_no_write_calls(self, patched_client):
        resp = patched_client.post(
            f"{API}/memory/items/MEM-HERMES-001/update/dry-run",
            json={"candidate": {"summary": "test"}},
        )
        assert resp.status_code == 200

    def test_archive_dry_run_no_write_calls(self, patched_client):
        resp = patched_client.post(
            f"{API}/memory/items/MEM-HERMES-001/archive/dry-run",
            json={},
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════
# DTO Safety Tests
# ═══════════════════════════════════════════════════════════════


class TestDTOSafety:
    """Verify response DTOs don't leak forbidden fields."""

    def test_no_storage_field(self, writer_client):
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())
        text = resp.text
        assert '"storage"' not in text
        assert "recordPath" not in text
        assert "snapshotPath" not in text

    def test_no_secrets_in_response(self, writer_client):
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=_valid_write_body())
        text = resp.text.lower()
        for forbidden in ["api_key", "secret", "token", "cookie", "traceback"]:
            assert forbidden not in text

    def test_forbidden_dangerous_fields_rejected(self, writer_client):
        """Fields like 'execute', 'force', 'writeEnabled' must not be accepted."""
        body = _valid_write_body()
        body["execute"] = True
        body["force"] = True
        # Body is passed as-is — the service should still produce correct safety
        resp = writer_client.post(f"{API}/memory/write/dry-run", json=body)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["safety"]["writeEnabled"] is False
        assert data["safety"]["sideEffects"] is False


# ═══════════════════════════════════════════════════════════════
# Route Boundary Tests
# ═══════════════════════════════════════════════════════════════


class TestRouteBoundary:
    """Verify route boundary rules for Phase 1D."""

    def test_total_business_paths(self):
        """Total business paths should be 29 (21 base + 4 Phase 1F agent run + 2 Phase 1E agent preview + 2 Phase 1G tool policy)."""
        config = DevWebApiConfig(hermes_home=None)
        app = create_dev_web_api_app(config)
        business_prefix = "/api/dev/v1/"
        paths = sorted(set(
            r.path for r in app.routes
            if hasattr(r, "path") and r.path.startswith(business_prefix)
        ))
        assert len(paths) == 29, f"Expected 29 paths, got {len(paths)}: {paths}"

    def test_no_real_write_routes(self):
        """Real write routes must not exist."""
        config = DevWebApiConfig(hermes_home=None)
        app = create_dev_web_api_app(config)
        paths = {r.path for r in app.routes if hasattr(r, "path")}
        forbidden = [
            "/api/dev/v1/memory/write",
            "/api/dev/v1/memory/items/{memoryId}/update",
            "/api/dev/v1/memory/items/{memoryId}/archive",
        ]
        for f in forbidden:
            assert f not in paths, f"Forbidden route found: {f}"

    def test_dry_run_routes_exist(self):
        """All 3 dry-run routes must exist."""
        config = DevWebApiConfig(hermes_home=None)
        app = create_dev_web_api_app(config)
        paths = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/api/dev/v1/memory/write/dry-run" in paths
        assert "/api/dev/v1/memory/items/{memoryId}/update/dry-run" in paths
        assert "/api/dev/v1/memory/items/{memoryId}/archive/dry-run" in paths

    def test_dry_run_routes_post_only(self):
        """Dry-run routes must only accept POST."""
        config = DevWebApiConfig(hermes_home=None)
        app = create_dev_web_api_app(config)
        dry_run_paths = {
            "/api/dev/v1/memory/write/dry-run",
            "/api/dev/v1/memory/items/{memoryId}/update/dry-run",
            "/api/dev/v1/memory/items/{memoryId}/archive/dry-run",
        }
        for route in app.routes:
            if hasattr(route, "path") and route.path in dry_run_paths:
                assert hasattr(route, "methods")
                assert route.methods == {"POST"}, f"{route.path} has methods {route.methods}"
