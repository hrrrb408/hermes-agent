"""Tests for the Hermes Dev Web API Memory, Context, and Agent endpoints.

Covers Phase 0C-05:
- Memory status, categories, items, item detail
- Context preview (POST)
- Agent status
- Read-only guarantees
- No file path leakage
- No secrets leakage
- DTO whitelist enforcement
- Side-effect verification
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig

API = "/api/dev/v1"


# ── Fixtures ──


@pytest.fixture
def memory_home(tmp_path):
    """Create a temporary HERMES_HOME with memory scaffold and test data."""
    home = tmp_path / "hermes-home"

    # Create memory scaffold
    (home / "memory" / "indexes").mkdir(parents=True)
    (home / "memory" / "records" / "test-cat").mkdir(parents=True)
    (home / "memory" / "snapshots").mkdir(parents=True)
    (home / "memory" / "events.jsonl").write_text("", encoding="utf-8")

    # Create MEMORY.md
    memory_md = """\
# Hermes Memory Root Router

## test-cat

- index: memory://indexes/test-cat.md
- scope: test
- priority: P0
- status: active
- keywords: test, memory, unit
- description: A test category for unit tests.

## archived-cat

- index: memory://indexes/archived-cat.md
- scope: test
- priority: P2
- status: archived
- keywords: archived, test
- description: An archived test category.
"""
    (home / "MEMORY.md").write_text(memory_md, encoding="utf-8")

    # Create category index
    index_md = """\
# Test Category Index

## MEM-TEST_CAT-001 Test Memory Alpha

- type: project_status
- importance: P0
- ttl: project
- status: active
- tags: test, alpha
- storage: memory://records/test-cat/mem-test_cat-001.md
- created_at: 2026-06-01
- updated_at: 2026-06-01
- summary: A test memory item for validation.

## MEM-TEST_CAT-002 Test Memory Beta

- type: architecture_decision
- importance: P1
- ttl: permanent
- status: active
- tags: test, beta
- storage: memory://records/test-cat/mem-test_cat-002.md
- created_at: 2026-06-02
- updated_at: 2026-06-02
- summary: Another test memory item.

## MEM-TEST_CAT-003 Archived Memory

- type: feature_design
- importance: P2
- ttl: session
- status: archived
- tags: test, archived
- storage: memory://records/test-cat/mem-test_cat-003.md
- created_at: 2026-06-01
- updated_at: 2026-06-01
- summary: An archived memory item.
"""
    (home / "memory" / "indexes" / "test-cat.md").write_text(
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
- storage: memory://records/test-cat/mem-archived_cat-001.md
- created_at: 2026-06-01
- updated_at: 2026-06-01
- summary: Item in archived category.
"""
    (home / "memory" / "indexes" / "archived-cat.md").write_text(
        archived_index, encoding="utf-8"
    )

    # Create record files
    record_1 = "# Details\n\nFull record content for alpha.\n"
    (home / "memory" / "records" / "test-cat" / "mem-test_cat-001.md").write_text(
        record_1, encoding="utf-8"
    )
    record_2 = (
        "# Status\n\n"
        "Source at /Users/huangruibang/Code/hermes-agent-dev.\n"
        "Config file:///Users/alice/private.txt.\n"
        "Linux path /home/bob/.ssh/id_rsa.\n"
        "See also memory://records/projects/hermes/hermes.md\n"
        "Visit https://example.com for info.\n"
    )
    (home / "memory" / "records" / "test-cat" / "mem-test_cat-002.md").write_text(
        record_2, encoding="utf-8"
    )

    # Create state.db for session compatibility
    (home / "state.db").touch()

    return home


@pytest.fixture
def memory_client(memory_home):
    """TestClient with memory-enabled HERMES_HOME."""
    config = DevWebApiConfig(hermes_home=memory_home)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def no_home_client():
    """TestClient without HERMES_HOME."""
    config = DevWebApiConfig(hermes_home=None)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def empty_home_client(tmp_path):
    """TestClient with an empty HERMES_HOME (no MEMORY.md)."""
    home = tmp_path / "empty-home"
    home.mkdir()
    (home / "state.db").touch()
    config = DevWebApiConfig(hermes_home=home)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ── Helper ──


def _file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file for read-only verification."""
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── Memory Status ──


class TestMemoryStatus:
    def test_memory_status_available(self, memory_client):
        resp = memory_client.get(f"{API}/memory/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["available"] is True
        assert data["readOnly"] is True
        assert data["rootCategories"]["total"] >= 1
        assert data["rootCategories"]["active"] >= 1
        assert data["memories"]["total"] >= 2
        assert data["memories"]["active"] >= 2
        assert data["exposedCapabilities"]["read"] is True
        assert data["exposedCapabilities"]["write"] is False
        assert data["exposedCapabilities"]["review"] is False

    def test_memory_status_unavailable_no_home(self, no_home_client):
        resp = no_home_client.get(f"{API}/memory/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["available"] is False
        assert data["capabilities"]["contextLoader"] is False

    def test_memory_status_unavailable_empty_home(self, empty_home_client):
        resp = empty_home_client.get(f"{API}/memory/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["available"] is False

    def test_memory_status_has_request_id(self, memory_client):
        resp = memory_client.get(f"{API}/memory/status")
        meta = resp.json()["meta"]
        assert "requestId" in meta
        assert len(meta["requestId"]) > 0

    def test_memory_status_no_paths(self, memory_client):
        resp = memory_client.get(f"{API}/memory/status")
        body = json.dumps(resp.json())
        assert "memory://" not in body
        assert "indexes/" not in body
        assert "records/" not in body


# ── Memory Categories ──


class TestMemoryCategories:
    def test_list_categories(self, memory_client):
        resp = memory_client.get(f"{API}/memory/categories")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        items = data["items"]
        # Should only show active categories by default
        for item in items:
            assert item["status"] == "active"

    def test_list_categories_include_archived(self, memory_client):
        resp = memory_client.get(f"{API}/memory/categories?includeArchived=true")
        assert resp.status_code == 200
        data = resp.json()["data"]
        statuses = {item["status"] for item in data["items"]}
        assert "archived" in statuses

    def test_category_has_memory_count(self, memory_client):
        resp = memory_client.get(f"{API}/memory/categories")
        items = resp.json()["data"]["items"]
        test_cat = next(i for i in items if i["key"] == "test-cat")
        assert test_cat["memoryCount"] == 3
        assert test_cat["activeMemoryCount"] == 2

    def test_category_fields_whitelist(self, memory_client):
        resp = memory_client.get(f"{API}/memory/categories")
        items = resp.json()["data"]["items"]
        for item in items:
            # Allowed fields
            assert "key" in item
            assert "title" in item
            assert "description" in item
            assert "priority" in item
            assert "keywords" in item
            assert "status" in item
            # Forbidden fields
            assert "index" not in item
            assert "storage" not in item
            assert "path" not in item

    def test_categories_no_paths(self, memory_client):
        resp = memory_client.get(f"{API}/memory/categories")
        body = json.dumps(resp.json())
        assert "memory://" not in body

    def test_categories_unavailable_no_home(self, no_home_client):
        resp = no_home_client.get(f"{API}/memory/categories")
        assert resp.status_code == 503
        error = resp.json()["error"]
        assert error["code"] == "MEMORY_UNAVAILABLE"


# ── Memory Items ──


class TestMemoryItems:
    def test_list_items(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) >= 2
        assert data["page"]["total"] >= 2

    def test_list_items_exclude_archived_default(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items")
        items = resp.json()["data"]["items"]
        for item in items:
            assert item["status"] == "active"

    def test_list_items_include_archived(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items?includeArchived=true")
        items = resp.json()["data"]["items"]
        statuses = {i["status"] for i in items}
        assert "archived" in statuses

    def test_list_items_category_filter(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items?category=test-cat")
        items = resp.json()["data"]["items"]
        assert len(items) >= 2
        for item in items:
            assert item["category"] == "test-cat"

    def test_list_items_query_filter(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items?query=alpha")
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        assert any("Alpha" in i["title"] for i in items)

    def test_list_items_pagination(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items?limit=1&offset=0")
        data = resp.json()["data"]
        assert len(data["items"]) == 1
        assert data["page"]["hasMore"] is True

    def test_item_fields_whitelist(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items")
        items = resp.json()["data"]["items"]
        for item in items:
            assert "id" in item
            assert "category" in item
            assert "title" in item
            assert "summary" in item
            assert "tags" in item
            assert "type" in item
            assert "importance" in item
            assert "status" in item
            assert "updatedAt" in item
            # Forbidden fields
            assert "storage" not in item
            assert "path" not in item

    def test_items_no_storage_uri(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items")
        body = json.dumps(resp.json())
        assert "memory://" not in body

    def test_items_unavailable_no_home(self, no_home_client):
        resp = no_home_client.get(f"{API}/memory/items")
        assert resp.status_code == 503


# ── Memory Item Detail ──


class TestMemoryItemDetail:
    def test_get_item_detail(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items/MEM-TEST_CAT-001")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == "MEM-TEST_CAT-001"
        assert data["title"] == "Test Memory Alpha"
        assert data["summary"] == "A test memory item for validation."
        assert data["category"] == "test-cat"
        assert data["type"] == "project_status"
        assert data["importance"] == "P0"
        assert data["status"] == "active"
        assert "recordPreview" in data

    def test_get_item_detail_has_record_preview(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items/MEM-TEST_CAT-001")
        data = resp.json()["data"]
        assert data["recordPreview"] is not None
        assert "Full record content for alpha" in data["recordPreview"]
        assert data["truncated"] is False

    def test_get_item_not_found(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items/MEM-TEST_CAT-999")
        assert resp.status_code == 404
        error = resp.json()["error"]
        assert error["code"] == "MEMORY_NOT_FOUND"

    def test_get_item_invalid_id(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items/invalid-id")
        assert resp.status_code == 400
        error = resp.json()["error"]
        assert error["code"] == "INVALID_MEMORY_ID"

    def test_get_item_empty_id(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items/")
        # This should hit the list endpoint, not detail
        assert resp.status_code == 200

    def test_item_detail_no_storage_uri(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items/MEM-TEST_CAT-001")
        body = json.dumps(resp.json())
        assert "memory://" not in body

    def test_item_detail_no_path(self, memory_client):
        resp = memory_client.get(f"{API}/memory/items/MEM-TEST_CAT-001")
        body = json.dumps(resp.json()).lower()
        assert "records/" not in body
        assert "indexes/" not in body


# ── Context Preview ──


class TestContextPreview:
    def test_preview_basic(self, memory_client):
        resp = memory_client.post(
            f"{API}/context/preview",
            json={"query": "test alpha"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["query"] == "test alpha"
        assert data["sideEffects"] is False
        assert isinstance(data["matchedCategories"], list)
        assert isinstance(data["memories"], list)
        assert "limits" in data

    def test_preview_with_scores(self, memory_client):
        resp = memory_client.post(
            f"{API}/context/preview",
            json={
                "query": "test memory alpha",
                "options": {"showScores": True},
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        for cat in data["matchedCategories"]:
            assert "score" in cat
            assert isinstance(cat["score"], int)

    def test_preview_with_custom_limits(self, memory_client):
        resp = memory_client.post(
            f"{API}/context/preview",
            json={
                "query": "test",
                "options": {
                    "maxCategories": 1,
                    "maxMemories": 2,
                    "maxRecordChars": 100,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["limits"]["maxCategories"] == 1
        assert data["limits"]["maxMemories"] == 2
        assert data["limits"]["maxRecordChars"] == 100
        assert len(data["matchedCategories"]) <= 1

    def test_preview_empty_query(self, memory_client):
        resp = memory_client.post(
            f"{API}/context/preview",
            json={"query": ""},
        )
        assert resp.status_code == 400

    def test_preview_missing_query(self, memory_client):
        resp = memory_client.post(
            f"{API}/context/preview",
            json={},
        )
        assert resp.status_code == 400

    def test_preview_long_query_rejected(self, memory_client):
        resp = memory_client.post(
            f"{API}/context/preview",
            json={"query": "x" * 1001},
        )
        assert resp.status_code == 400

    def test_preview_non_string_query(self, memory_client):
        resp = memory_client.post(
            f"{API}/context/preview",
            json={"query": 12345},
        )
        assert resp.status_code == 400

    def test_preview_invalid_body(self, memory_client):
        resp = memory_client.post(
            f"{API}/context/preview",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400

    def test_preview_side_effects_false(self, memory_client):
        resp = memory_client.post(
            f"{API}/context/preview",
            json={"query": "test"},
        )
        assert resp.json()["data"]["sideEffects"] is False

    def test_preview_no_prompt_leakage(self, memory_client):
        resp = memory_client.post(
            f"{API}/context/preview",
            json={"query": "test"},
        )
        body = json.dumps(resp.json()).lower()
        assert "system prompt" not in body
        assert "api_key" not in body
        assert "base_url" not in body

    def test_preview_unavailable_no_home(self, no_home_client):
        resp = no_home_client.post(
            f"{API}/context/preview",
            json={"query": "test"},
        )
        assert resp.status_code == 503

    def test_preview_memory_items_have_scores(self, memory_client):
        resp = memory_client.post(
            f"{API}/context/preview",
            json={
                "query": "test alpha",
                "options": {"showScores": True},
            },
        )
        data = resp.json()["data"]
        for mem in data["memories"]:
            assert "score" in mem
            assert mem["score"] > 0


# ── Agent Status ──


class TestAgentStatus:
    def test_agent_status_available(self, memory_client):
        resp = memory_client.get(f"{API}/agent/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["available"] is True
        assert data["readOnly"] is True

    def test_agent_status_runtime_flags(self, memory_client):
        resp = memory_client.get(f"{API}/agent/status")
        runtime = resp.json()["data"]["runtime"]
        assert runtime["messageSendEnabled"] is False
        assert runtime["streamingEnabled"] is False
        assert runtime["toolExecutionEnabled"] is False
        assert runtime["entry"] == "conversation_loop"

    def test_agent_status_memory_flags(self, memory_client):
        resp = memory_client.get(f"{API}/agent/status")
        memory = resp.json()["data"]["memory"]
        assert "enabled" in memory
        assert "contextLoaderEnabled" in memory
        assert memory["autoWriteEnabled"] is False
        assert memory["reviewQueueEnabled"] is False

    def test_agent_status_model_safe(self, memory_client):
        resp = memory_client.get(f"{API}/agent/status")
        model = resp.json()["data"]["model"]
        assert "configured" in model
        assert "provider" in model
        assert "name" in model

    def test_agent_status_no_secrets(self, memory_client):
        resp = memory_client.get(f"{API}/agent/status")
        body = json.dumps(resp.json()).lower()
        assert "api_key" not in body
        assert "base_url" not in body
        assert "secret" not in body
        assert "token" not in body
        assert "credential" not in body

    def test_agent_status_no_system_prompt(self, memory_client):
        resp = memory_client.get(f"{API}/agent/status")
        body = json.dumps(resp.json()).lower()
        assert "system_prompt" not in body
        assert "full_config" not in body

    def test_agent_status_unavailable_no_home(self, no_home_client):
        resp = no_home_client.get(f"{API}/agent/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["available"] is False

    def test_agent_status_has_request_id(self, memory_client):
        resp = memory_client.get(f"{API}/agent/status")
        meta = resp.json()["meta"]
        assert "requestId" in meta


# ── Read-only Verification ──


class TestReadOnlyGuarantees:
    def test_memory_files_unchanged_after_status(self, memory_client, memory_home):
        """Verify memory files are unchanged after /memory/status."""
        before = {}
        for path in (memory_home / "memory" / "indexes").rglob("*.md"):
            before[str(path)] = _file_hash(path)
        before[str(memory_home / "MEMORY.md")] = _file_hash(
            memory_home / "MEMORY.md"
        )
        before[str(memory_home / "memory" / "events.jsonl")] = _file_hash(
            memory_home / "memory" / "events.jsonl"
        )

        memory_client.get(f"{API}/memory/status")
        memory_client.get(f"{API}/memory/categories")
        memory_client.get(f"{API}/memory/items")
        memory_client.get(f"{API}/memory/items/MEM-TEST_CAT-001")

        after = {}
        for path in (memory_home / "memory" / "indexes").rglob("*.md"):
            after[str(path)] = _file_hash(path)
        after[str(memory_home / "MEMORY.md")] = _file_hash(
            memory_home / "MEMORY.md"
        )
        after[str(memory_home / "memory" / "events.jsonl")] = _file_hash(
            memory_home / "memory" / "events.jsonl"
        )

        assert before == after

    def test_memory_files_unchanged_after_context_preview(
        self, memory_client, memory_home
    ):
        """Verify no files are written during context preview."""
        events_before = _file_hash(memory_home / "memory" / "events.jsonl")
        memory_md_before = _file_hash(memory_home / "MEMORY.md")

        memory_client.post(
            f"{API}/context/preview",
            json={"query": "test alpha memory"},
        )

        assert _file_hash(memory_home / "memory" / "events.jsonl") == events_before
        assert _file_hash(memory_home / "MEMORY.md") == memory_md_before

    def test_no_new_events_after_api_calls(self, memory_client, memory_home):
        """Verify events.jsonl is not appended to."""
        events_path = memory_home / "memory" / "events.jsonl"
        lines_before = events_path.read_text(encoding="utf-8").strip().splitlines()

        memory_client.get(f"{API}/memory/status")
        memory_client.get(f"{API}/memory/categories")
        memory_client.get(f"{API}/memory/items")
        memory_client.post(
            f"{API}/context/preview",
            json={"query": "test"},
        )

        lines_after = events_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines_after) == len(lines_before)


# ── Route Boundary ──


class TestRouteBoundary:
    def test_total_business_routes(self, memory_client):
        """Verify runtime OpenAPI has exactly 27 business paths."""
        resp = memory_client.get("/openapi.json")
        spec = resp.json()
        paths = [
            p for p in spec["paths"]
            if p.startswith("/api/dev/v1/")
        ]
        assert len(paths) == 27
        # Phase 1E: verify agent preview routes exist
        assert "/api/dev/v1/agent/prompt/preview" in paths
        assert "/api/dev/v1/agent/run/dry-run" in paths
        # Phase 1F: verify agent run routes exist
        assert "/api/dev/v1/agent/runs" in paths
        assert "/api/dev/v1/agent/runs/{runId}" in paths
        assert "/api/dev/v1/agent/runs/{runId}/events" in paths
        assert "/api/dev/v1/agent/runs/{runId}/cancel" in paths

    def test_no_real_write_memory_routes(self, memory_client):
        """Verify no real (non-dry-run) memory write routes exist."""
        resp = memory_client.get("/openapi.json")
        spec = resp.json()
        for path, methods in spec["paths"].items():
            if "/memory" in path:
                for method in methods:
                    if method.lower() == "post":
                        assert path.endswith("/dry-run"), (
                            f"Found non-dry-run POST method {method} on {path}"
                        )

    def test_no_review_write_routes(self, memory_client):
        """Verify no real (non-dry-run, non-execute) review write routes exist."""
        resp = memory_client.get("/openapi.json")
        spec = resp.json()
        for path in spec["paths"]:
            if "/reviews" in path:
                # Only dry-run and execute routes are allowed
                assert "dry-run" in path or "execute" in path or spec["paths"][path].get("get"), (
                    f"Unexpected review route: {path}"
                )

    def test_no_agent_write_routes(self, memory_client):
        """Verify no real agent execution routes exist (only safe preview + run routes)."""
        allowed_agent_post_routes = {
            "/api/dev/v1/agent/prompt/preview",
            "/api/dev/v1/agent/run/dry-run",
            "/api/dev/v1/agent/runs",
            "/api/dev/v1/agent/runs/{runId}/cancel",
        }
        # Routes that must NOT exist at all (any method)
        forbidden_agent_routes = {
            "/api/dev/v1/agent/run",
            "/api/dev/v1/agent/run/",
            "/api/dev/v1/agent/stream",
            "/api/dev/v1/agent/tools",
        }
        # Routes that exist as GET but must NOT have POST
        no_post_routes = {
            "/api/dev/v1/sessions/{sessionId}/messages",
            "/api/dev/v1/agent/runs/{runId}",
            "/api/dev/v1/agent/runs/{runId}/events",
        }
        resp = memory_client.get("/openapi.json")
        spec = resp.json()
        # Verify safe routes exist
        for route in allowed_agent_post_routes:
            assert route in spec["paths"], f"Expected safe route {route} missing"
        # Verify real execution routes do NOT exist at all
        for route in forbidden_agent_routes:
            assert route not in spec["paths"], (
                f"Forbidden agent route {route} found"
            )
        # Verify read-only routes do NOT have POST method
        for route in no_post_routes:
            if route in spec["paths"]:
                assert "post" not in spec["paths"][route], (
                    f"POST method found on read-only route {route}"
                )
        # Verify all agent POST routes are in the allowed set
        for path, methods in spec["paths"].items():
            if "/agent" in path and "post" in methods:
                assert path in allowed_agent_post_routes, (
                    f"Agent POST route {path} not in allowed set"
                )

    def test_post_routes_are_safe(self, memory_client):
        """Verify all POST routes are safe (dry-run, preview, execute, or agent run with confirmation)."""
        resp = memory_client.get("/openapi.json")
        spec = resp.json()
        post_routes = []
        for path, methods in spec["paths"].items():
            if "post" in methods and path.startswith("/api/dev/v1/"):
                post_routes.append(path)
        # 12 POST routes: context/preview, 2 review dry-runs, 2 review executes,
        # 3 memory writer dry-runs, agent prompt preview, agent run dry-run,
        # agent runs (create), agent runs cancel
        assert len(post_routes) == 12
        # Verify Phase 1E safe POST routes
        assert "/api/dev/v1/agent/prompt/preview" in post_routes
        assert "/api/dev/v1/agent/run/dry-run" in post_routes
        # Verify Phase 1F agent run POST routes
        assert "/api/dev/v1/agent/runs" in post_routes
        assert "/api/dev/v1/agent/runs/{runId}/cancel" in post_routes
        for route in post_routes:
            assert any(kw in route for kw in ("preview", "dry-run", "execute", "runs", "cancel")), (
                f"POST route {route} is not a safe preview/dry-run/execute/run route"
            )

    def test_404_for_unknown_routes(self, memory_client):
        assert memory_client.get(f"{API}/memory/write").status_code == 404
        assert memory_client.get(f"{API}/agent/run").status_code == 404
        assert memory_client.get(f"{API}/tools").status_code == 404
        assert memory_client.get(f"{API}/memory/items/test/delete").status_code == 404


# ── Status Integration ──


class TestStatusIntegration:
    def test_status_reflects_memory_available(self, memory_client):
        resp = memory_client.get(f"{API}/status")
        services = resp.json()["data"]["services"]
        assert services["memory"]["available"] is True

    def test_status_reflects_agent_available(self, memory_client):
        resp = memory_client.get(f"{API}/status")
        services = resp.json()["data"]["services"]
        assert services["agent"]["available"] is True

    def test_status_reflects_memory_unavailable(self, empty_home_client):
        resp = empty_home_client.get(f"{API}/status")
        services = resp.json()["data"]["services"]
        assert services["memory"]["available"] is False


# ── Path Redaction ──


class TestRedactLocalPaths:
    """Unit tests for the redact_local_paths() pure function."""

    def test_import(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        assert callable(redact_local_paths)

    def test_macos_users_path(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        result = redact_local_paths("Source at /Users/huangruibang/Code/hermes-agent-dev.")
        assert "/Users/" not in result
        assert "[local-path]" in result
        assert "Source at" in result

    def test_macos_other_user(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        result = redact_local_paths("Path /Users/alice/project/secret.txt here.")
        assert "/Users/alice" not in result
        assert "secret.txt" not in result
        assert "[local-path]" in result

    def test_linux_home_path(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        result = redact_local_paths("Key at /home/bob/.ssh/id_rsa.")
        assert "/home/bob" not in result
        assert "id_rsa" not in result
        assert "[local-path]" in result

    def test_file_uri(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        result = redact_local_paths("Config file:///Users/alice/private.txt.")
        assert "file:///" not in result
        assert "private.txt" not in result
        assert "[file-uri-redacted]" in result

    def test_file_uri_with_host(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        result = redact_local_paths("file://localhost/Users/alice/secret.")
        assert "file://" not in result
        assert "[file-uri-redacted]" in result

    def test_preserves_memory_uri(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        text = "See memory://records/projects/hermes/hermes.md for details."
        result = redact_local_paths(text)
        assert "memory://" in result
        assert "memory://records/projects/hermes/hermes.md" in result

    def test_preserves_https_url(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        text = "Visit https://example.com/path for info."
        result = redact_local_paths(text)
        assert "https://example.com/path" in result

    def test_preserves_http_url(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        text = "Server at http://localhost:3000/api."
        result = redact_local_paths(text)
        assert "http://localhost:3000/api" in result

    def test_empty_string(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        assert redact_local_paths("") == ""

    def test_no_paths(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        text = "Plain text without any paths."
        assert redact_local_paths(text) == text

    def test_windows_path(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        result = redact_local_paths("Located at C:\\Users\\alice\\secret.txt.")
        assert "C:\\Users\\alice" not in result
        assert "[local-path]" in result

    def test_multiple_paths_in_one_text(self):
        from hermes_cli.dev_web_memory_service import redact_local_paths
        text = (
            "Dev source /Users/huangruibang/Code/hermes-agent-dev, "
            "prod data /Users/huangruibang/.hermes, "
            "linux /home/bob/.ssh/id_rsa."
        )
        result = redact_local_paths(text)
        assert "/Users/" not in result
        assert "/home/" not in result
        assert result.count("[local-path]") >= 3


class TestPathRedactionInAPI:
    """Integration tests verifying path redaction in API responses."""

    def test_item_detail_no_local_paths(self, memory_client):
        """Verify recordPreview does not contain local absolute paths."""
        resp = memory_client.get(f"{API}/memory/items/MEM-TEST_CAT-002")
        assert resp.status_code == 200
        body = json.dumps(resp.json())
        # No local absolute paths
        assert "/Users/" not in body
        assert "/home/" not in body
        assert "file://" not in body
        assert "secret.txt" not in body
        assert "id_rsa" not in body
        assert "private.txt" not in body

    def test_item_detail_has_redaction_markers(self, memory_client):
        """Verify redaction markers appear where paths were."""
        resp = memory_client.get(f"{API}/memory/items/MEM-TEST_CAT-002")
        assert resp.status_code == 200
        data = resp.json()["data"]
        preview = data.get("recordPreview", "")
        assert "[local-path]" in preview
        assert "[file-uri-redacted]" in preview

    def test_item_detail_preserves_memory_uri(self, memory_client):
        """Verify memory:// references are preserved in recordPreview."""
        resp = memory_client.get(f"{API}/memory/items/MEM-TEST_CAT-002")
        assert resp.status_code == 200
        data = resp.json()["data"]
        preview = data.get("recordPreview", "")
        assert "memory://" in preview

    def test_item_detail_preserves_https(self, memory_client):
        """Verify https:// URLs are preserved in recordPreview."""
        resp = memory_client.get(f"{API}/memory/items/MEM-TEST_CAT-002")
        assert resp.status_code == 200
        data = resp.json()["data"]
        preview = data.get("recordPreview", "")
        assert "https://example.com" in preview

    def test_all_memory_endpoints_no_paths(self, memory_client):
        """Verify no endpoint returns local absolute paths."""
        endpoints = [
            (f"{API}/memory/status", "get"),
            (f"{API}/memory/categories", "get"),
            (f"{API}/memory/items", "get"),
            (f"{API}/memory/items/MEM-TEST_CAT-001", "get"),
            (f"{API}/memory/items/MEM-TEST_CAT-002", "get"),
        ]
        for url, method in endpoints:
            resp = memory_client.get(url)
            assert resp.status_code == 200, f"{url} returned {resp.status_code}"
            body = json.dumps(resp.json())
            assert "/Users/" not in body, f"Found /Users/ in {url}"
            assert "/home/" not in body, f"Found /home/ in {url}"
            assert "file://" not in body, f"Found file:// in {url}"
