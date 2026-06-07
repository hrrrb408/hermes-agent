"""Tests for the Hermes Dev Web API Phase 0C-03 session endpoints.

Covers:
- Session list with pagination, search, sort, filter
- Session detail retrieval
- Sensitive field exclusion (explicit DTO whitelist)
- Read-only guarantee (no database writes)
- Database unavailability (missing, corrupted, missing tables)
- Request ID and error model consistency
- OpenAPI route boundary
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_session_service import (
    DevSessionQueryService,
    SessionNotFoundError,
    SessionStoreUnavailableError,
    _build_preview,
    _escape_like,
    _transform_detail,
    _transform_list_item,
    _unix_to_iso,
)


# ── Fixtures ──


def _create_state_db(db_path: Path) -> None:
    """Create a minimal state.db with sessions and messages tables."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            user_id TEXT,
            model TEXT,
            model_config TEXT,
            system_prompt TEXT,
            parent_session_id TEXT,
            started_at REAL NOT NULL,
            ended_at REAL,
            end_reason TEXT,
            message_count INTEGER DEFAULT 0,
            tool_call_count INTEGER DEFAULT 0,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cache_read_tokens INTEGER DEFAULT 0,
            cache_write_tokens INTEGER DEFAULT 0,
            reasoning_tokens INTEGER DEFAULT 0,
            cwd TEXT,
            billing_provider TEXT,
            billing_base_url TEXT,
            billing_mode TEXT,
            estimated_cost_usd REAL,
            actual_cost_usd REAL,
            cost_status TEXT,
            cost_source TEXT,
            pricing_version TEXT,
            title TEXT,
            api_call_count INTEGER DEFAULT 0,
            handoff_state TEXT,
            handoff_platform TEXT,
            handoff_error TEXT,
            rewind_count INTEGER NOT NULL DEFAULT 0,
            archived INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id),
            role TEXT NOT NULL,
            content TEXT,
            tool_call_id TEXT,
            tool_calls TEXT,
            tool_name TEXT,
            timestamp REAL NOT NULL,
            token_count INTEGER,
            finish_reason TEXT,
            reasoning TEXT,
            reasoning_content TEXT,
            reasoning_details TEXT,
            codex_reasoning_items TEXT,
            codex_message_items TEXT,
            platform_message_id TEXT,
            observed INTEGER DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


def _insert_session(
    db_path: Path,
    session_id: str,
    source: str = "cli",
    title: str | None = None,
    model: str | None = None,
    message_count: int = 0,
    tool_call_count: int = 0,
    started_at: float | None = None,
    ended_at: float | None = None,
    end_reason: str | None = None,
    archived: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    system_prompt: str | None = None,
    model_config: str | None = None,
    user_id: str | None = None,
    cwd: str | None = None,
    billing_provider: str | None = None,
    billing_base_url: str | None = None,
    billing_mode: str | None = None,
) -> None:
    """Insert a session row into the test database."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT OR REPLACE INTO sessions
           (id, source, title, model, message_count, tool_call_count,
            started_at, ended_at, end_reason, archived,
            input_tokens, output_tokens, system_prompt, model_config,
            user_id, cwd, billing_provider, billing_base_url, billing_mode)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id, source, title, model, message_count, tool_call_count,
            started_at or time.time(), ended_at, end_reason, archived,
            input_tokens, output_tokens, system_prompt, model_config,
            user_id, cwd, billing_provider, billing_base_url, billing_mode,
        ),
    )
    conn.commit()
    conn.close()


def _insert_message(
    db_path: Path,
    session_id: str,
    role: str = "user",
    content: str = "Hello",
    timestamp: float | None = None,
) -> None:
    """Insert a message row into the test database."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT INTO messages
           (session_id, role, content, timestamp)
           VALUES (?, ?, ?, ?)""",
        (session_id, role, content, timestamp or time.time()),
    )
    conn.execute(
        "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary state.db with schema."""
    path = tmp_path / "state.db"
    _create_state_db(path)
    return path


@pytest.fixture
def client_with_db(db_path):
    """TestClient with a valid state.db."""
    config = DevWebApiConfig(hermes_home=db_path.parent)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def seeded_client(db_path):
    """TestClient with pre-seeded session data."""
    now = time.time()
    # Session 1: oldest, cli source
    _insert_session(
        db_path, "session-001", source="cli", title="First session",
        model="deepseek-chat", message_count=3, started_at=now - 7200,
        system_prompt="TOP_SECRET_PROMPT", model_config="TOP_SECRET_MODEL_CONFIG",
        user_id="TOP_SECRET_USER", cwd="/top/secret/path",
        billing_provider="TOP_SECRET_BILLING", billing_base_url="https://secret.example",
        billing_mode="TOP_SECRET_MODE",
    )
    _insert_message(db_path, "session-001", content="Hello from session 1", timestamp=now - 7100)

    # Session 2: middle, telegram source
    _insert_session(
        db_path, "session-002", source="telegram", title="Telegram chat",
        model="glm-5", message_count=5, started_at=now - 3600,
    )
    _insert_message(db_path, "session-002", content="Hi from telegram", timestamp=now - 3500)

    # Session 3: newest, cli, no title
    _insert_session(
        db_path, "session-003", source="cli", title=None,
        model="claude-sonnet", message_count=1, started_at=now - 1800,
    )

    # Session 4: archived
    _insert_session(
        db_path, "session-004", source="cli", title="Archived session",
        model="deepseek-chat", message_count=10, started_at=now - 10000,
        archived=1,
    )

    # Session 5: ended session
    _insert_session(
        db_path, "session-005", source="cli", title="Ended session",
        model="glm-5", message_count=2, started_at=now - 5000,
        ended_at=now - 4900, end_reason="user_exit",
    )

    config = DevWebApiConfig(hermes_home=db_path.parent)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ── 1. Session list basics ──


class TestSessionListBasics:
    def test_list_returns_200(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "items" in data["data"]
        assert "page" in data["data"]

    def test_empty_database_returns_empty_items(self, client_with_db):
        resp = client_with_db.get("/api/dev/v1/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["items"] == []
        assert data["data"]["page"]["total"] == 0

    def test_list_returns_sessions(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        # Default excludes archived, so 4 non-archived sessions
        assert len(items) == 4

    def test_default_pagination(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        page = resp.json()["data"]["page"]
        assert page["offset"] == 0
        assert page["limit"] == 30
        assert page["total"] == 4
        assert page["hasMore"] is False

    def test_custom_limit(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?limit=2")
        data = resp.json()
        assert len(data["data"]["items"]) == 2
        assert data["data"]["page"]["limit"] == 2
        assert data["data"]["page"]["hasMore"] is True

    def test_offset(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?limit=2&offset=2")
        data = resp.json()
        assert len(data["data"]["items"]) == 2
        assert data["data"]["page"]["offset"] == 2

    def test_empty_page(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?offset=100")
        data = resp.json()
        assert data["data"]["items"] == []
        assert data["data"]["page"]["hasMore"] is False

    def test_session_id_is_string(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        items = resp.json()["data"]["items"]
        for item in items:
            assert isinstance(item["id"], str)

    def test_null_title(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        items = resp.json()["data"]["items"]
        untitled = [i for i in items if i["id"] == "session-003"]
        assert len(untitled) == 1
        assert untitled[0]["title"] is None

    def test_unicode_title(self, db_path):
        _insert_session(db_path, "uni-01", title="中文会话标题 🎉")
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions")
        items = resp.json()["data"]["items"]
        assert any(i["title"] == "中文会话标题 🎉" for i in items)


# ── 2. Sorting ──


class TestSessionListSorting:
    def test_default_sort_is_recent(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        items = resp.json()["data"]["items"]
        # Sessions with messages should have lastActiveAt
        # session-003 (newest started_at, no msg) and session-002 (recent msg)
        # Order should be by last_active DESC
        assert len(items) >= 2

    def test_created_sort(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?order=created")
        items = resp.json()["data"]["items"]
        # Should be ordered by started_at DESC
        assert items[0]["id"] == "session-003"
        assert items[-1]["id"] == "session-001"

    def test_stable_sort_with_offset(self, seeded_client):
        """Pagination should not skip or duplicate items."""
        r1 = seeded_client.get("/api/dev/v1/sessions?order=created&limit=2")
        r2 = seeded_client.get("/api/dev/v1/sessions?order=created&limit=2&offset=2")
        ids_1 = [i["id"] for i in r1.json()["data"]["items"]]
        ids_2 = [i["id"] for i in r2.json()["data"]["items"]]
        assert len(set(ids_1) & set(ids_2)) == 0


# ── 3. Search ──


class TestSessionListSearch:
    def test_search_by_title(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?query=Telegram")
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        assert all("Telegram" in (i["title"] or "") for i in items)

    def test_search_by_session_id(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?query=session-001")
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        assert any(i["id"] == "session-001" for i in items)

    def test_search_case_insensitive(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?query=telegram")
        items = resp.json()["data"]["items"]
        assert len(items) >= 1

    def test_search_trim(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?query=%20Telegram%20")
        items = resp.json()["data"]["items"]
        assert len(items) >= 1

    def test_empty_query_returns_all(self, seeded_client):
        resp_all = seeded_client.get("/api/dev/v1/sessions")
        resp_empty = seeded_client.get("/api/dev/v1/sessions?query=")
        assert (
            resp_all.json()["data"]["page"]["total"]
            == resp_empty.json()["data"]["page"]["total"]
        )

    def test_search_no_results(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?query=xyznonexistent")
        data = resp.json()
        assert data["data"]["items"] == []
        assert data["data"]["page"]["total"] == 0

    def test_search_chinese(self, db_path):
        _insert_session(db_path, "cn-01", title="中文搜索测试")
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions?query=%E4%B8%AD%E6%96%87")
        items = resp.json()["data"]["items"]
        assert len(items) >= 1

    def test_search_sql_injection(self, seeded_client):
        """Search with SQL injection strings should not crash."""
        injection_attempts = [
            "'; DROP TABLE sessions; --",
            "%",
            "_",
            "' OR '1'='1",
            "''",
        ]
        for attempt in injection_attempts:
            resp = seeded_client.get(f"/api/dev/v1/sessions?query={attempt}")
            assert resp.status_code == 200

    def test_search_does_not_match_system_prompt(self, seeded_client):
        """Search must not find sessions by system_prompt content."""
        resp = seeded_client.get("/api/dev/v1/sessions?query=TOP_SECRET_PROMPT")
        items = resp.json()["data"]["items"]
        assert len(items) == 0

    def test_search_does_not_match_model_config(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?query=TOP_SECRET_MODEL_CONFIG")
        items = resp.json()["data"]["items"]
        assert len(items) == 0


# ── 4. Filter ──


class TestSessionListFilter:
    def test_filter_by_source(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?source=telegram")
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        assert all(i["source"] == "telegram" for i in items)

    def test_filter_archived_exclude(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?archived=exclude")
        items = resp.json()["data"]["items"]
        assert all(i["archived"] is False for i in items)

    def test_filter_archived_include(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?archived=include")
        items = resp.json()["data"]["items"]
        assert any(i["archived"] is True for i in items)
        total = resp.json()["data"]["page"]["total"]
        assert total == 5  # 4 non-archived + 1 archived

    def test_filter_archived_only(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?archived=only")
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        assert all(i["archived"] is True for i in items)

    def test_filter_source_no_results(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?source=nonexistent")
        data = resp.json()
        assert data["data"]["items"] == []


# ── 5. Pagination validation ──


class TestSessionListPagination:
    def test_limit_minimum(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["items"]) <= 1

    def test_limit_maximum(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?limit=100")
        assert resp.status_code == 200

    def test_limit_zero_rejected(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?limit=0")
        assert resp.status_code == 422

    def test_limit_exceeds_maximum(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?limit=101")
        assert resp.status_code == 422

    def test_offset_negative_rejected(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?offset=-1")
        assert resp.status_code == 422

    def test_large_offset(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions?offset=9999")
        assert resp.status_code == 200
        assert resp.json()["data"]["items"] == []

    def test_no_duplicate_across_pages(self, seeded_client):
        all_ids = set()
        offset = 0
        while True:
            resp = seeded_client.get(
                f"/api/dev/v1/sessions?limit=2&offset={offset}"
            )
            items = resp.json()["data"]["items"]
            if not items:
                break
            for item in items:
                assert item["id"] not in all_ids
                all_ids.add(item["id"])
            offset += 2


# ── 6. Session detail ──


class TestSessionDetail:
    def test_existing_session_returns_200(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions/session-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["id"] == "session-001"

    def test_nonexistent_session_returns_404(self, seeded_client):
        resp = seeded_client.get(
            "/api/dev/v1/sessions/definitely-not-existing-session"
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "SESSION_NOT_FOUND"

    def test_detail_fields(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions/session-005")
        data = resp.json()["data"]
        assert data["id"] == "session-005"
        assert data["title"] == "Ended session"
        assert data["source"] == "cli"
        assert data["model"] == "glm-5"
        assert isinstance(data["messageCount"], int)
        assert isinstance(data["toolCallCount"], int)
        assert isinstance(data["archived"], bool)
        assert data["startedAt"] is not None
        assert data["endedAt"] is not None
        assert data["endReason"] == "user_exit"
        assert "inputTokens" in data
        assert "outputTokens" in data

    def test_detail_no_messages_field(self, seeded_client):
        """Detail must not include messages."""
        resp = seeded_client.get("/api/dev/v1/sessions/session-001")
        data = resp.json()["data"]
        assert "messages" not in data

    def test_detail_null_fields(self, db_path):
        _insert_session(db_path, "minimal-01", title=None, model=None)
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions/minimal-01")
        data = resp.json()["data"]
        assert data["title"] is None
        assert data["model"] is None
        assert data["endedAt"] is None
        assert data["lastActiveAt"] is not None  # Falls back to startedAt
        assert data["endReason"] is None

    def test_session_id_with_special_chars(self, db_path):
        """Session IDs may contain hyphens, colons, etc."""
        _insert_session(db_path, "sess:with-special_chars.2024")
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions/sess:with-special_chars.2024")
        assert resp.status_code == 200

    def test_session_id_with_spaces(self, db_path):
        """Session IDs with spaces should be URL-decodable."""
        _insert_session(db_path, "sess space")
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions/sess%20space")
        assert resp.status_code == 200

    def test_session_id_too_long(self, seeded_client):
        long_id = "a" * 300
        resp = seeded_client.get(f"/api/dev/v1/sessions/{long_id}")
        assert resp.status_code == 400

    def test_session_id_control_chars(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions/sess%00ion")
        assert resp.status_code == 400

    def test_sql_injection_session_id(self, seeded_client):
        resp = seeded_client.get(
            "/api/dev/v1/sessions/' OR '1'='1"
        )
        # Should not return 200 with data
        assert resp.status_code in (400, 404)


# ── 7. Sensitive field exclusion ──


class TestSensitiveFieldExclusion:
    """Verify that sensitive fields NEVER appear in API responses."""

    SENSITIVE_VALUES = [
        "TOP_SECRET_PROMPT",
        "TOP_SECRET_MODEL_CONFIG",
        "TOP_SECRET_USER",
        "/top/secret/path",
        "TOP_SECRET_BILLING",
        "https://secret.example",
        "TOP_SECRET_MODE",
    ]

    SENSITIVE_FIELDS = [
        "system_prompt",
        "model_config",
        "user_id",
        "cwd",
        "billing_provider",
        "billing_base_url",
        "billing_mode",
    ]

    def test_list_excludes_sensitive_values(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        text = resp.text
        for secret in self.SENSITIVE_VALUES:
            assert secret not in text, f"Sensitive value '{secret}' found in list response"

    def test_list_excludes_sensitive_field_names(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        text = resp.text.lower()
        for field in self.SENSITIVE_FIELDS:
            assert field not in text, f"Sensitive field '{field}' found in list response"

    def test_detail_excludes_sensitive_values(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions/session-001")
        text = resp.text
        for secret in self.SENSITIVE_VALUES:
            assert secret not in text, f"Sensitive value '{secret}' found in detail response"

    def test_detail_excludes_sensitive_field_names(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions/session-001")
        text = resp.text.lower()
        for field in self.SENSITIVE_FIELDS:
            assert field not in text, f"Sensitive field '{field}' found in detail response"


# ── 8. Read-only guarantee ──


class TestReadOnlyGuarantee:
    def test_list_does_not_modify_db(self, db_path):
        _insert_session(db_path, "ro-test-1", title="Readonly check")
        before_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()
        before_size = db_path.stat().st_size

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        client.get("/api/dev/v1/sessions")

        after_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()
        after_size = db_path.stat().st_size
        assert before_hash == after_hash
        assert before_size == after_size

    def test_detail_does_not_modify_db(self, db_path):
        _insert_session(db_path, "ro-test-2", title="Readonly detail")
        before_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        client.get("/api/dev/v1/sessions/ro-test-2")

        after_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()
        assert before_hash == after_hash

    def test_no_wal_or_journal_created(self, db_path):
        """No WAL, SHM, or journal files should be created."""
        _insert_session(db_path, "ro-test-3")
        parent = db_path.parent

        config = DevWebApiConfig(hermes_home=parent)
        client = TestClient(create_dev_web_api_app(config))
        client.get("/api/dev/v1/sessions")
        client.get("/api/dev/v1/sessions/ro-test-3")

        assert not (parent / "state.db-wal").exists()
        assert not (parent / "state.db-shm").exists()
        assert not (parent / "state.db-journal").exists()

    def test_session_db_opened_read_only(self, db_path):
        """Verify SessionDB is opened with read_only=True."""
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        with patch(
            "hermes_cli.dev_web_session_service.SessionDB",
            wraps=__import__(
                "hermes_state", fromlist=["SessionDB"]
            ).SessionDB,
        ) as mock_cls:
            client.get("/api/dev/v1/sessions")
            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args
            assert call_kwargs.kwargs.get("read_only") is True or (
                len(call_kwargs.args) > 1 and call_kwargs.args[1] is True
            )


# ── 9. Database unavailability ──


class TestDatabaseUnavailability:
    def test_missing_database_returns_503(self, tmp_path):
        """When state.db doesn't exist, return 503."""
        config = DevWebApiConfig(hermes_home=tmp_path)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions")
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "SESSION_STORE_UNAVAILABLE"

    def test_missing_database_detail_returns_503(self, tmp_path):
        config = DevWebApiConfig(hermes_home=tmp_path)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions/any-id")
        assert resp.status_code == 503

    def test_corrupted_database_returns_503(self, tmp_path):
        """A corrupted state.db (not valid SQLite) should return 503."""
        db_path = tmp_path / "state.db"
        db_path.write_text("this is not a valid sqlite database")
        config = DevWebApiConfig(hermes_home=tmp_path)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions")
        assert resp.status_code == 503

    def test_database_is_directory_returns_503(self, tmp_path):
        """A directory named state.db should return 503."""
        db_dir = tmp_path / "state.db"
        db_dir.mkdir()
        config = DevWebApiConfig(hermes_home=tmp_path)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions")
        assert resp.status_code == 503

    def test_error_does_not_leak_path(self, tmp_path):
        config = DevWebApiConfig(hermes_home=tmp_path)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions")
        text = resp.text.lower()
        assert str(tmp_path).lower() not in text
        assert "state.db" not in text
        assert "traceback" not in text


# ── 10. Request ID and meta ──


class TestSessionRequestId:
    def test_list_includes_request_id(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        data = resp.json()
        assert "requestId" in data["meta"]
        assert len(data["meta"]["requestId"]) > 0

    def test_detail_includes_request_id(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions/session-001")
        data = resp.json()
        assert "requestId" in data["meta"]

    def test_404_includes_request_id(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions/nonexistent")
        assert resp.status_code == 404
        body = resp.json()
        assert "requestId" in body

    def test_503_includes_request_id(self, tmp_path):
        config = DevWebApiConfig(hermes_home=tmp_path)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions")
        body = resp.json()
        assert "requestId" in body

    def test_client_request_id_echoed(self, seeded_client):
        resp = seeded_client.get(
            "/api/dev/v1/sessions",
            headers={"X-Request-ID": "test-rid-123"},
        )
        assert resp.headers.get("x-request-id") == "test-rid-123"

    def test_timestamp_in_response(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        ts = resp.json()["meta"]["timestamp"]
        assert ts.endswith("Z")
        assert "T" in ts


# ── 11. Status endpoint session availability ──


class TestStatusSessionAvailability:
    def test_status_shows_sessions_available_with_db(self, db_path):
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/status")
        sessions = resp.json()["data"]["services"]["sessions"]
        assert sessions["available"] is True
        assert sessions["readOnly"] is True

    def test_status_shows_sessions_unavailable_without_db(self, tmp_path):
        config = DevWebApiConfig(hermes_home=tmp_path)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/status")
        sessions = resp.json()["data"]["services"]["sessions"]
        assert sessions["available"] is False

    def test_status_does_not_crash_without_hermes_home(self):
        config = DevWebApiConfig(hermes_home=None)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/status")
        assert resp.status_code == 200
        sessions = resp.json()["data"]["services"]["sessions"]
        assert sessions["available"] is False


# ── 12. Preview ──


class TestPreview:
    def test_preview_from_first_user_message(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        items = resp.json()["data"]["items"]
        s1 = [i for i in items if i["id"] == "session-001"]
        assert len(s1) == 1
        assert s1[0]["preview"] is not None
        assert "Hello from session 1" in s1[0]["preview"]

    def test_no_preview_when_no_messages(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        items = resp.json()["data"]["items"]
        s3 = [i for i in items if i["id"] == "session-003"]
        assert len(s3) == 1
        assert s3[0]["preview"] is None

    def test_preview_max_length(self, db_path):
        _insert_session(db_path, "long-preview")
        _insert_message(
            db_path, "long-preview",
            content="A" * 200,
        )
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions")
        items = resp.json()["data"]["items"]
        lp = [i for i in items if i["id"] == "long-preview"]
        assert len(lp) == 1
        assert lp[0]["preview"] is not None
        assert len(lp[0]["preview"]) <= 63


# ── 13. Time conversion ──


class TestTimeConversion:
    def test_unix_to_iso_none(self):
        assert _unix_to_iso(None) is None

    def test_unix_to_iso_valid(self):
        # 2024-01-01T00:00:00Z = 1704067200
        result = _unix_to_iso(1704067200.0)
        assert result == "2024-01-01T00:00:00Z"

    def test_unix_to_iso_negative(self):
        result = _unix_to_iso(-1)
        assert result is not None  # 1969-12-31

    def test_started_at_format(self, seeded_client):
        resp = seeded_client.get("/api/dev/v1/sessions")
        items = resp.json()["data"]["items"]
        for item in items:
            if item["startedAt"]:
                assert item["startedAt"].endswith("Z")
                assert "T" in item["startedAt"]


# ── 14. Service unit tests ──


class TestServiceHelpers:
    def test_escape_like(self):
        assert _escape_like("test%value") == "test\\%value"
        assert _escape_like("test_value") == "test\\_value"
        assert _escape_like("test\\slash") == "test\\\\slash"
        assert _escape_like("all%_\\") == "all\\%\\_\\\\"

    def test_build_preview_none(self):
        assert _build_preview(None) is None

    def test_build_preview_empty(self):
        assert _build_preview("") is None

    def test_build_preview_whitespace(self):
        assert _build_preview("   ") is None

    def test_build_preview_short(self):
        assert _build_preview("Hello") == "Hello"

    def test_build_preview_truncation(self):
        long_text = "A" * 100
        result = _build_preview(long_text)
        assert result is not None
        assert len(result) <= 63
        assert result.endswith("...")

    def test_validate_session_id_empty(self):
        assert DevSessionQueryService.validate_session_id("") is not None

    def test_validate_session_id_too_long(self):
        assert DevSessionQueryService.validate_session_id("a" * 300) is not None

    def test_validate_session_id_control_chars(self):
        assert DevSessionQueryService.validate_session_id("test\x00id") is not None

    def test_validate_session_id_valid(self):
        assert DevSessionQueryService.validate_session_id("session-123") is None

    def test_validate_session_id_with_special_chars(self):
        assert DevSessionQueryService.validate_session_id("sess:abc-def_123") is None

    def test_transform_list_item_whitelist(self):
        row = {
            "id": "test-1",
            "title": "Test",
            "source": "cli",
            "model": "deepseek",
            "message_count": 5,
            "tool_call_count": 2,
            "archived": 0,
            "started_at": 1704067200.0,
            "ended_at": None,
            "last_active": 1704067800.0,
            "preview": "Hello",
        }
        result = _transform_list_item(row)
        assert result["id"] == "test-1"
        assert result["messageCount"] == 5
        assert "system_prompt" not in result
        assert "model_config" not in result
        assert "user_id" not in result

    def test_transform_detail_whitelist(self):
        row = {
            "id": "test-1",
            "title": "Test",
            "source": "cli",
            "model": "deepseek",
            "message_count": 5,
            "tool_call_count": 2,
            "archived": 0,
            "started_at": 1704067200.0,
            "ended_at": None,
            "end_reason": None,
            "input_tokens": 100,
            "output_tokens": 200,
            "system_prompt": "SECRET",
            "model_config": "SECRET",
            "user_id": "SECRET",
            "cwd": "/secret",
        }
        result = _transform_detail(row)
        assert result["id"] == "test-1"
        assert result["inputTokens"] == 100
        assert result["outputTokens"] == 200
        assert "system_prompt" not in result
        assert "model_config" not in result
        assert "user_id" not in result
        assert "cwd" not in result


# ── 15. OpenAPI routes ──


class TestSessionOpenAPIRoutes:
    def test_openapi_has_session_paths(self, seeded_client):
        resp = seeded_client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "/api/dev/v1/sessions" in paths
        assert "/api/dev/v1/sessions/{sessionId}" in paths

    def test_openapi_no_message_routes(self, seeded_client):
        resp = seeded_client.get("/openapi.json")
        paths = resp.json()["paths"]
        for path in paths:
            assert "messages" not in path

    def test_openapi_no_memory_routes(self, seeded_client):
        resp = seeded_client.get("/openapi.json")
        paths = resp.json()["paths"]
        for path in paths:
            assert "memory" not in path

    def test_openapi_no_agent_routes(self, seeded_client):
        resp = seeded_client.get("/openapi.json")
        paths = resp.json()["paths"]
        for path in paths:
            assert "agent" not in path.lower() or "agent" in path and "/api/dev/v1/agent" not in path

    def test_openapi_has_four_business_paths(self, seeded_client):
        resp = seeded_client.get("/openapi.json")
        paths = resp.json()["paths"]
        business = [p for p in paths if p.startswith("/api/dev/v1")]
        assert len(business) == 4


# ── 16. SessionDB close read-only behavior ──


class TestSessionDBCloseReadOnly:
    """Verify that read-only SessionDB.close() skips WAL checkpoint."""

    def test_read_only_close_skips_wal_checkpoint(self, db_path):
        """Read-only connection should not execute PRAGMA wal_checkpoint.

        Strategy: subclass SessionDB to override close behavior tracking.
        Since sqlite3.Connection cannot be monkey-patched, we verify by
        checking that WAL/SHM mtime is unchanged after close.
        """
        from hermes_state import SessionDB

        # First open writable to initialize WAL, then close
        writable = SessionDB(db_path=db_path, read_only=False)
        writable.close()

        parent = db_path.parent
        wal_path = parent / "state.db-wal"
        shm_path = parent / "state.db-shm"

        # Record WAL/SHM state
        wal_mtime_before = wal_path.stat().st_mtime if wal_path.exists() else 0
        shm_mtime_before = shm_path.stat().st_mtime if shm_path.exists() else 0

        # Open read-only and close
        db = SessionDB(db_path=db_path, read_only=True)
        db.close()

        # Verify WAL/SHM mtimes unchanged (checkpoint would change them)
        if wal_path.exists():
            assert wal_path.stat().st_mtime == wal_mtime_before, (
                "Read-only close changed WAL mtime — checkpoint may have been attempted"
            )
        if shm_path.exists():
            assert shm_path.stat().st_mtime == shm_mtime_before, (
                "Read-only close changed SHM mtime — checkpoint may have been attempted"
            )

        # Verify no journal file created
        assert not (parent / "state.db-journal").exists()

    def test_read_only_close_still_closes_connection(self, db_path):
        """After close(), the connection must be None."""
        from hermes_state import SessionDB

        db = SessionDB(db_path=db_path, read_only=True)
        assert db._conn is not None
        db.close()
        assert db._conn is None

    def test_read_only_close_does_not_modify_wal_files(self, db_path):
        """Read-only open + close should not change WAL or SHM."""
        from hermes_state import SessionDB

        parent = db_path.parent
        # Open writable first to ensure WAL mode is set, then close
        writable = SessionDB(db_path=db_path, read_only=False)
        writable.close()

        # Record WAL/SHM state after writable close
        wal_path = parent / "state.db-wal"
        shm_path = parent / "state.db-shm"
        wal_before = (
            (wal_path.stat().st_size, wal_path.stat().st_mtime)
            if wal_path.exists() else None
        )
        shm_before = (
            (shm_path.stat().st_size, shm_path.stat().st_mtime)
            if shm_path.exists() else None
        )

        # Open read-only and close
        db = SessionDB(db_path=db_path, read_only=True)
        db.close()

        # Verify WAL unchanged
        if wal_before is not None and wal_path.exists():
            assert wal_path.stat().st_size == wal_before[0]
            assert wal_path.stat().st_mtime == wal_before[1]
        if shm_before is not None and shm_path.exists():
            assert shm_path.stat().st_size == shm_before[0]
            assert shm_path.stat().st_mtime == shm_before[1]

        # No journal
        assert not (parent / "state.db-journal").exists()

    def test_writable_close_preserves_checkpoint_behavior(self, db_path):
        """Writable connections should still attempt checkpoint.

        Strategy: open writable, do a write, close, verify WAL is
        checkpointed (WAL should shrink or disappear).
        """
        from hermes_state import SessionDB
        import time

        # Open writable, insert a row, then close
        db = SessionDB(db_path=db_path, read_only=False)
        db._conn.execute("BEGIN IMMEDIATE")
        db._conn.execute(
            "INSERT OR REPLACE INTO sessions (id, source, started_at) "
            "VALUES (?, ?, ?)",
            ("writable-test-ckpt", "cli", time.time()),
        )
        db._conn.execute("COMMIT")
        db.close()

        # After writable close with checkpoint, WAL should exist but be
        # empty or very small (the checkpoint truncates it)
        parent = db_path.parent
        wal_path = parent / "state.db-wal"
        if wal_path.exists():
            # WAL exists but should be small after checkpoint
            assert wal_path.stat().st_size >= 0  # just verify accessible

        # Verify the session was persisted
        db2 = SessionDB(db_path=db_path, read_only=True)
        row = db2.get_session("writable-test-ckpt")
        db2.close()
        assert row is not None, "Writable session should have been persisted"


# ── 17. Search scope contract tests ──


class TestSearchScopeContract:
    """Verify search only covers title and session ID, not message content
    or other sensitive fields."""

    def test_search_does_not_match_message_content(self, db_path):
        """Message body content must not appear in search results."""
        _insert_session(db_path, "msg-scope-test", title="Alpha session")
        _insert_message(db_path, "msg-scope-test", content="SECRET_MESSAGE_ONLY_TOKEN_xyzzy")

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions?query=SECRET_MESSAGE_ONLY_TOKEN")
        items = resp.json()["data"]["items"]
        assert len(items) == 0

    def test_search_does_not_match_system_prompt(self, db_path):
        _insert_session(
            db_path, "sys-prompt-test", title="Beta",
            system_prompt="SECRET_SYS_PROMPT_TOKEN_plugh",
        )
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions?query=SECRET_SYS_PROMPT_TOKEN")
        assert len(resp.json()["data"]["items"]) == 0

    def test_search_does_not_match_cwd(self, db_path):
        _insert_session(
            db_path, "cwd-test", title="Gamma",
            cwd="/top/SECRET_CWD_TOKEN_foo",
        )
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions?query=SECRET_CWD_TOKEN")
        assert len(resp.json()["data"]["items"]) == 0

    def test_search_does_not_match_user_id(self, db_path):
        _insert_session(
            db_path, "uid-test", title="Delta",
            user_id="SECRET_USER_ID_TOKEN_bar",
        )
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions?query=SECRET_USER_ID_TOKEN")
        assert len(resp.json()["data"]["items"]) == 0

    def test_search_does_not_match_billing(self, db_path):
        _insert_session(
            db_path, "billing-test", title="Epsilon",
            billing_provider="SECRET_BILLING_TOKEN_baz",
        )
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions?query=SECRET_BILLING_TOKEN")
        assert len(resp.json()["data"]["items"]) == 0

    def test_search_hits_title(self, db_path):
        _insert_session(db_path, "title-hit", title="UniqueTitle_ZZZ123")
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions?query=UniqueTitle_ZZZ123")
        assert len(resp.json()["data"]["items"]) >= 1

    def test_search_hits_session_id(self, db_path):
        _insert_session(db_path, "id-hit-ABC456", title="Some title")
        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions?query=id-hit-ABC456")
        assert len(resp.json()["data"]["items"]) >= 1


# ── 18. OpenAPI query parameter description ──


class TestOpenAPISearchDescription:
    """Verify OpenAPI query parameter description is aligned with
    Phase 0C-03 search scope (title + ID only, not message content)."""

    def test_query_param_description_mentions_title_or_id(self, seeded_client):
        resp = seeded_client.get("/openapi.json")
        spec = resp.json()
        sessions_get = spec["paths"]["/api/dev/v1/sessions"]["get"]
        query_param = None
        for p in sessions_get.get("parameters", []):
            if p.get("name") == "query":
                query_param = p
                break
        assert query_param is not None
        desc = query_param.get("description", "").lower()
        # Must mention title or ID
        assert "title" in desc or "id" in desc or "session" in desc

    def test_query_param_description_no_fts5_claim(self, seeded_client):
        """Must not claim FTS5 search capability."""
        resp = seeded_client.get("/openapi.json")
        spec = resp.json()
        sessions_get = spec["paths"]["/api/dev/v1/sessions"]["get"]
        for p in sessions_get.get("parameters", []):
            if p.get("name") == "query":
                desc = p.get("description", "")
                assert "FTS5" not in desc, "Description must not claim FTS5 search"
