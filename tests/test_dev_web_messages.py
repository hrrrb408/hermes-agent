"""Tests for the Hermes Dev Web API Phase 0C-04 message endpoints.

Covers:
- Message list with pagination and anchor filters
- Role normalization and content safety
- Sensitive field exclusion (reasoning, codex_*, etc.)
- Read-only guarantee (no database writes)
- Database unavailability
- Tool call display safety
- Content type handling (plain text, structured, empty, unsupported)
- Request ID and error model consistency
- OpenAPI route boundary
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_message_service import (
    DevMessageQueryService,
    MessageSessionNotFoundError,
    MessageStoreUnavailableError,
    _normalize_role,
    _sanitize_text,
    _transform_content,
    _transform_message,
    _transform_tool_calls,
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
    archived: int = 0,
) -> None:
    """Insert a session row into the test database."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT OR REPLACE INTO sessions
           (id, source, title, model, message_count, tool_call_count,
            started_at, archived)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id, source, title, model, message_count, tool_call_count,
            started_at or time.time(), archived,
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
    tool_calls: str | None = None,
    tool_name: str | None = None,
    tool_call_id: str | None = None,
    reasoning: str | None = None,
    reasoning_content: str | None = None,
    codex_reasoning_items: str | None = None,
    token_count: int | None = None,
    finish_reason: str | None = None,
    active: int = 1,
) -> None:
    """Insert a message row into the test database with all optional fields."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT INTO messages
           (session_id, role, content, timestamp, tool_calls, tool_name,
            tool_call_id, reasoning, reasoning_content, codex_reasoning_items,
            token_count, finish_reason, active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id, role, content, timestamp or time.time(),
            tool_calls, tool_name, tool_call_id,
            reasoning, reasoning_content, codex_reasoning_items,
            token_count, finish_reason, active,
        ),
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
def seeded_message_client(db_path):
    """TestClient with sessions and messages for message tests."""
    now = time.time()

    # Session 1: multiple messages with various roles
    _insert_session(
        db_path, "msg-session-001", source="cli",
        title="Message test session", model="deepseek-chat",
        message_count=0, started_at=now - 3600,
    )
    _insert_message(
        db_path, "msg-session-001", role="user",
        content="Hello, can you help me?",
        timestamp=now - 3500,
    )
    _insert_message(
        db_path, "msg-session-001", role="assistant",
        content="Of course! How can I assist you today?",
        timestamp=now - 3400,
        token_count=42, finish_reason="stop",
    )
    _insert_message(
        db_path, "msg-session-001", role="tool",
        content="Tool execution result",
        timestamp=now - 3300,
        tool_name="search_files", tool_call_id="call_001",
    )
    _insert_message(
        db_path, "msg-session-001", role="system",
        content="System message content",
        timestamp=now - 3600,
    )

    # Session 2: empty (no messages)
    _insert_session(
        db_path, "msg-session-002", source="cli",
        title="Empty session", started_at=now - 1800,
    )

    # Session 3: messages with sensitive data in internal fields
    _insert_session(
        db_path, "msg-session-003", source="cli",
        title="Sensitive data session", started_at=now - 900,
    )
    _insert_message(
        db_path, "msg-session-003", role="assistant",
        content="Normal response text",
        timestamp=now - 800,
        reasoning="SECRET_REASONING_TOKEN in reasoning field",
        reasoning_content="SECRET_REASONING_CONTENT data",
        codex_reasoning_items='{"items": "SECRET_CODEX_TOKEN"}',
    )
    _insert_message(
        db_path, "msg-session-003", role="assistant",
        content="Response with tool calls",
        timestamp=now - 700,
        tool_calls=json.dumps([{
            "id": "call_secret_123",
            "type": "function",
            "function": {
                "name": "search_files",
                "arguments": json.dumps({"pattern": "test_query"}),
            },
        }]),
    )

    config = DevWebApiConfig(hermes_home=db_path.parent)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ── Message List Basics ──


class TestMessageListBasics:
    """Basic message retrieval and structure validation."""

    def test_messages_returned_for_valid_session(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-001/messages"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "items" in body["data"]
        assert "page" in body["data"]
        assert "meta" in body
        items = body["data"]["items"]
        assert len(items) == 4  # 4 messages (user, assistant, tool, system)

    def test_message_item_structure(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-001/messages"
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]

        # Find user message
        user_msg = next(m for m in items if m["role"] == "user")
        assert "id" in user_msg
        assert user_msg["role"] == "user"
        assert "content" in user_msg
        assert "timestamp" in user_msg

    def test_messages_ordered_by_id_asc(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-001/messages"
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        ids = [m["id"] for m in items]
        assert ids == sorted(ids)

    def test_empty_session_returns_empty_items(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-002/messages"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["items"] == []
        assert body["data"]["page"]["total"] == 0
        assert body["data"]["page"]["hasMore"] is False

    def test_nonexistent_session_returns_404(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/nonexistent-session/messages"
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "SESSION_NOT_FOUND"

    def test_response_has_request_id(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-001/messages"
        )
        assert resp.status_code == 200
        assert "requestId" in resp.json()["meta"]
        assert len(resp.json()["meta"]["requestId"]) > 0


# ── Pagination ──


class TestMessagePagination:
    """Pagination parameters and response metadata."""

    def test_default_limit(self, db_path):
        _insert_session(db_path, "pag-session", message_count=0)
        for i in range(5):
            _insert_message(db_path, "pag-session", content=f"Msg {i}")

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get("/api/dev/v1/sessions/pag-session/messages")
        assert resp.status_code == 200
        page = resp.json()["data"]["page"]
        assert page["limit"] == 50
        assert page["offset"] == 0
        assert page["total"] == 5
        assert page["hasMore"] is False

    def test_custom_limit(self, db_path):
        _insert_session(db_path, "lim-session", message_count=0)
        for i in range(10):
            _insert_message(db_path, "lim-session", content=f"Msg {i}")

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get("/api/dev/v1/sessions/lim-session/messages?limit=3")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        page = resp.json()["data"]["page"]
        assert len(items) == 3
        assert page["limit"] == 3
        assert page["total"] == 10
        assert page["hasMore"] is True

    def test_offset_pagination(self, db_path):
        _insert_session(db_path, "off-session", message_count=0)
        for i in range(8):
            _insert_message(db_path, "off-session", content=f"Msg {i}")

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get(
            "/api/dev/v1/sessions/off-session/messages?limit=3&offset=6"
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 2  # only 2 remaining
        page = resp.json()["data"]["page"]
        assert page["offset"] == 6
        assert page["hasMore"] is False

    def test_limit_exceeds_max_clamped(self, db_path):
        _insert_session(db_path, "max-session", message_count=0)
        _insert_message(db_path, "max-session", content="Test")

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get(
            "/api/dev/v1/sessions/max-session/messages?limit=200"
        )
        assert resp.status_code == 422  # FastAPI validation rejects > 100

    def test_zero_limit_rejected(self, db_path):
        _insert_session(db_path, "zero-lim", message_count=0)

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get(
            "/api/dev/v1/sessions/zero-lim/messages?limit=0"
        )
        assert resp.status_code == 422

    def test_negative_offset_rejected(self, db_path):
        _insert_session(db_path, "neg-off", message_count=0)

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get(
            "/api/dev/v1/sessions/neg-off/messages?offset=-1"
        )
        assert resp.status_code == 422


# ── Anchor-based pagination ──


class TestAnchorPagination:
    """before/after anchor-based message filtering."""

    def test_before_anchor(self, db_path):
        _insert_session(db_path, "anchor-sess", message_count=0)
        for i in range(5):
            _insert_message(db_path, "anchor-sess", content=f"Msg {i}")

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        # Get all messages first to find an ID
        all_resp = client.get(
            "/api/dev/v1/sessions/anchor-sess/messages"
        )
        items = all_resp.json()["data"]["items"]
        mid_id = items[2]["id"]

        # Get messages before this ID
        resp = client.get(
            f"/api/dev/v1/sessions/anchor-sess/messages?before={mid_id}"
        )
        assert resp.status_code == 200
        result_items = resp.json()["data"]["items"]
        for item in result_items:
            assert item["id"] < mid_id

    def test_after_anchor(self, db_path):
        _insert_session(db_path, "after-sess", message_count=0)
        for i in range(5):
            _insert_message(db_path, "after-sess", content=f"Msg {i}")

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        all_resp = client.get(
            "/api/dev/v1/sessions/after-sess/messages"
        )
        items = all_resp.json()["data"]["items"]
        mid_id = items[2]["id"]

        resp = client.get(
            f"/api/dev/v1/sessions/after-sess/messages?after={mid_id}"
        )
        assert resp.status_code == 200
        result_items = resp.json()["data"]["items"]
        for item in result_items:
            assert item["id"] > mid_id

    def test_messages_before_and_after_counts(self, db_path):
        _insert_session(db_path, "count-sess", message_count=0)
        for i in range(10):
            _insert_message(db_path, "count-sess", content=f"Msg {i}")

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        all_resp = client.get(
            "/api/dev/v1/sessions/count-sess/messages"
        )
        items = all_resp.json()["data"]["items"]
        mid_id = items[4]["id"]

        resp = client.get(
            f"/api/dev/v1/sessions/count-sess/messages?before={mid_id}"
        )
        page = resp.json()["data"]["page"]
        assert page["messagesBefore"] is not None

        resp2 = client.get(
            f"/api/dev/v1/sessions/count-sess/messages?after={mid_id}"
        )
        page2 = resp2.json()["data"]["page"]
        assert page2["messagesAfter"] is not None


# ── Role normalization ──


class TestRoleNormalization:
    """Role mapping and normalization tests."""

    def test_user_role(self):
        assert _normalize_role("user") == "user"

    def test_assistant_role(self):
        assert _normalize_role("assistant") == "assistant"

    def test_tool_role(self):
        assert _normalize_role("tool") == "tool"

    def test_system_role(self):
        assert _normalize_role("system") == "system"

    def test_null_role(self):
        assert _normalize_role(None) == "unknown"

    def test_empty_role(self):
        assert _normalize_role("") == "unknown"

    def test_unknown_role(self):
        assert _normalize_role("custom_agent") == "unknown"

    def test_case_insensitive(self):
        assert _normalize_role("User") == "user"
        assert _normalize_role("ASSISTANT") == "assistant"
        assert _normalize_role("  tool  ") == "tool"

    def test_api_unknown_role_handled(self, db_path):
        _insert_session(db_path, "role-sess", message_count=0)
        # Insert message directly with unusual role
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("role-sess", "custom_agent", "test content", time.time()),
        )
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
            ("role-sess",),
        )
        conn.commit()
        conn.close()

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get("/api/dev/v1/sessions/role-sess/messages")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["role"] == "unknown"


# ── Content handling ──


class TestContentHandling:
    """Content type and safety handling."""

    def test_plain_text_content(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-001/messages"
        )
        items = resp.json()["data"]["items"]
        user_msg = next(m for m in items if m["role"] == "user")
        assert user_msg["content"]["type"] == "text"
        assert "Hello, can you help me?" in user_msg["content"]["text"]

    def test_empty_content(self, db_path):
        _insert_session(db_path, "empty-content-sess", message_count=0)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("empty-content-sess", "user", "", time.time()),
        )
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
            ("empty-content-sess",),
        )
        conn.commit()
        conn.close()

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get(
            "/api/dev/v1/sessions/empty-content-sess/messages"
        )
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["content"]["type"] == "empty"

    def test_null_content(self, db_path):
        _insert_session(db_path, "null-content-sess", message_count=0)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("null-content-sess", "user", None, time.time()),
        )
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
            ("null-content-sess",),
        )
        conn.commit()
        conn.close()

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get(
            "/api/dev/v1/sessions/null-content-sess/messages"
        )
        items = resp.json()["data"]["items"]
        assert items[0]["content"]["type"] == "empty"

    def test_multiline_text_preserved(self, db_path):
        _insert_session(db_path, "multi-sess", message_count=0)
        _insert_message(
            db_path, "multi-sess", content="Line 1\nLine 2\nLine 3"
        )

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get("/api/dev/v1/sessions/multi-sess/messages")
        items = resp.json()["data"]["items"]
        assert "Line 1\nLine 2\nLine 3" in items[0]["content"]["text"]

    def test_code_block_text(self, db_path):
        _insert_session(db_path, "code-sess", message_count=0)
        _insert_message(
            db_path, "code-sess",
            content="Here is code:\n```python\nprint('hello')\n```\nDone.",
        )

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get("/api/dev/v1/sessions/code-sess/messages")
        items = resp.json()["data"]["items"]
        assert "print('hello')" in items[0]["content"]["text"]

    def test_control_characters_removed(self):
        text, _ = _sanitize_text("Hello\x00\x01\x02World")
        assert "\x00" not in text
        assert "\x01" not in text
        assert "Hello" in text
        assert "World" in text

    def test_unicode_preserved(self, db_path):
        _insert_session(db_path, "unicode-sess", message_count=0)
        _insert_message(
            db_path, "unicode-sess",
            content="你好世界 🌍 café naïve",
        )

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get("/api/dev/v1/sessions/unicode-sess/messages")
        items = resp.json()["data"]["items"]
        assert "你好世界" in items[0]["content"]["text"]
        assert "🌍" in items[0]["content"]["text"]

    def test_long_text_truncated(self):
        long_text = "A" * 100_000
        text, truncated = _sanitize_text(long_text, max_chars=50_000)
        assert truncated is True
        assert len(text) == 50_000


# ── Structured content (\x00json:) ──


class TestStructuredContent:
    """Handling of \x00json: prefixed content."""

    def test_json_content_with_text_parts(self, db_path):
        """Test that structured content with text parts is extracted."""
        _insert_session(db_path, "struct-sess", message_count=0)
        # Insert \x00json: content manually
        structured = json.dumps([
            {"type": "text", "text": "Hello from structured"},
        ])
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("struct-sess", "user", "\x00json:" + structured, time.time()),
        )
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
            ("struct-sess",),
        )
        conn.commit()
        conn.close()

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get("/api/dev/v1/sessions/struct-sess/messages")
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["content"]["type"] == "text"
        assert "Hello from structured" in items[0]["content"]["text"]

    def test_json_content_with_no_text_parts_returns_unsupported(self, db_path):
        """Test that structured content without text parts is unsupported."""
        _insert_session(db_path, "no-text-sess", message_count=0)
        structured = json.dumps([
            {"type": "image_url", "url": "https://example.com/img.png"},
        ])
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("no-text-sess", "user", "\x00json:" + structured, time.time()),
        )
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
            ("no-text-sess",),
        )
        conn.commit()
        conn.close()

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get("/api/dev/v1/sessions/no-text-sess/messages")
        items = resp.json()["data"]["items"]
        assert items[0]["content"]["type"] == "unsupported"

    def test_invalid_json_content_handled(self, db_path):
        """Invalid JSON after \x00json: prefix should not crash."""
        _insert_session(db_path, "bad-json-sess", message_count=0)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("bad-json-sess", "user", "\x00json:{invalid", time.time()),
        )
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
            ("bad-json-sess",),
        )
        conn.commit()
        conn.close()

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get("/api/dev/v1/sessions/bad-json-sess/messages")
        # Should not crash — SessionDB._decode_content returns the raw string
        # for unparseable JSON, so it will be treated as text
        assert resp.status_code == 200


# ── Tool calls ──


class TestToolCalls:
    """Tool call display safety."""

    def test_tool_calls_in_assistant_message(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-003/messages"
        )
        items = resp.json()["data"]["items"]
        tc_msg = next(
            m for m in items
            if m.get("toolCalls") and len(m["toolCalls"]) > 0
        )
        assert tc_msg["toolCalls"][0]["type"] == "function"
        assert tc_msg["toolCalls"][0]["function"]["name"] == "search_files"
        # Arguments should be present but truncated if long
        assert "arguments" in tc_msg["toolCalls"][0]["function"]

    def test_tool_call_arguments_truncated(self):
        long_args = "A" * 500
        result = _transform_tool_calls([{
            "id": "call_1",
            "type": "function",
            "function": {"name": "test_tool", "arguments": long_args},
        }])
        assert result is not None
        assert len(result[0]["function"]["arguments"]) == 200

    def test_tool_message_has_tool_name(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-001/messages"
        )
        items = resp.json()["data"]["items"]
        tool_msg = next(m for m in items if m["role"] == "tool")
        assert tool_msg.get("toolName") == "search_files"
        assert tool_msg.get("toolCallId") == "call_001"

    def test_empty_tool_calls_returns_none(self):
        result = _transform_tool_calls(None)
        assert result is None

    def test_empty_list_tool_calls_returns_none(self):
        result = _transform_tool_calls([])
        assert result is None


# ── Sensitive field exclusion ──


class TestSensitiveFieldExclusion:
    """Verify sensitive fields are never returned."""

    SENSITIVE_VALUES = [
        "SECRET_REASONING_TOKEN",
        "SECRET_REASONING_CONTENT",
        "SECRET_CODEX_TOKEN",
        "SECRET_TOOL_ARG_TOKEN",
    ]

    SENSITIVE_FIELD_NAMES = [
        "reasoning",
        "reasoning_content",
        "reasoning_details",
        "codex_reasoning_items",
        "codex_message_items",
        "observed",
        "active",
        "platform_message_id",
    ]

    def test_sensitive_values_excluded(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-003/messages"
        )
        text = resp.text
        for secret in self.SENSITIVE_VALUES:
            assert secret not in text, (
                f"Sensitive value '{secret}' found in message response"
            )

    def test_sensitive_field_names_excluded(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-003/messages"
        )
        text = resp.text.lower()
        # Check field names aren't present as JSON keys
        for field in self.SENSITIVE_FIELD_NAMES:
            assert f'"{field}"' not in resp.text.lower(), (
                f"Sensitive field '{field}' found in message response"
            )

    def test_dto_whitelist_only(self):
        """Unit test: _transform_message only includes known safe fields."""
        row = {
            "id": 1,
            "role": "assistant",
            "content": "Hello",
            "timestamp": time.time(),
            "reasoning": "secret reasoning",
            "reasoning_content": "secret reasoning content",
            "codex_reasoning_items": "secret codex",
            "codex_message_items": "secret codex msg",
            "observed": 1,
            "active": 1,
            "platform_message_id": "platform_123",
            "tool_calls": None,
            "tool_name": None,
            "tool_call_id": None,
            "token_count": None,
            "finish_reason": None,
        }
        dto = _transform_message(row)
        # Must not contain sensitive keys
        assert "reasoning" not in dto
        assert "reasoning_content" not in dto
        assert "codex_reasoning_items" not in dto
        assert "codex_message_items" not in dto
        assert "observed" not in dto
        assert "active" not in dto
        assert "platform_message_id" not in dto


# ── Read-only guarantee ──


class TestReadOnlyGuarantee:
    """Verify that message API never writes to the database."""

    def test_messages_do_not_modify_db(self, db_path):
        _insert_session(db_path, "ro-msg-sess", message_count=0)
        _insert_message(db_path, "ro-msg-sess", content="Readonly check")

        before_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()
        before_size = db_path.stat().st_size

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))
        client.get("/api/dev/v1/sessions/ro-msg-sess/messages")

        after_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()
        after_size = db_path.stat().st_size
        assert before_hash == after_hash, "Database was modified!"
        assert before_size == after_size, "Database size changed!"

    def test_no_wal_or_journal_created(self, db_path):
        _insert_session(db_path, "wal-msg-sess", message_count=0)
        _insert_message(db_path, "wal-msg-sess", content="WAL check")
        parent = db_path.parent

        config = DevWebApiConfig(hermes_home=parent)
        client = TestClient(create_dev_web_api_app(config))
        client.get("/api/dev/v1/sessions/wal-msg-sess/messages")

        assert not (parent / "state.db-wal").exists()
        assert not (parent / "state.db-shm").exists()
        assert not (parent / "state.db-journal").exists()

    def test_message_count_unchanged_after_query(self, db_path):
        _insert_session(db_path, "count-sess", message_count=0)
        for i in range(5):
            _insert_message(db_path, "count-sess", content=f"Msg {i}")

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        # Check message count before
        conn = sqlite3.connect(str(db_path))
        before = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?",
            ("count-sess",),
        ).fetchone()[0]
        conn.close()

        client.get("/api/dev/v1/sessions/count-sess/messages")

        conn = sqlite3.connect(str(db_path))
        after = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?",
            ("count-sess",),
        ).fetchone()[0]
        conn.close()

        assert before == after == 5


# ── Database unavailability ──


class TestDatabaseUnavailability:
    """Test behavior when the database is unavailable."""

    def test_missing_database_returns_503(self, tmp_path):
        config = DevWebApiConfig(hermes_home=tmp_path)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions/any-session/messages")
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "SESSION_STORE_UNAVAILABLE"

    def test_database_is_directory_returns_503(self, tmp_path):
        db_dir = tmp_path / "state.db"
        db_dir.mkdir()
        config = DevWebApiConfig(hermes_home=tmp_path)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions/any-session/messages")
        assert resp.status_code == 503

    def test_error_does_not_leak_paths(self, tmp_path):
        config = DevWebApiConfig(hermes_home=tmp_path)
        client = TestClient(create_dev_web_api_app(config))
        resp = client.get("/api/dev/v1/sessions/any-session/messages")
        text = resp.text.lower()
        assert str(tmp_path).lower() not in text
        assert "traceback" not in text
        assert "state.db" not in text
        assert "sqlite" not in text


# ── Parameter safety ──


class TestParameterSafety:
    """Test input parameter validation and injection prevention."""

    def test_session_id_too_long(self, client_with_db):
        long_id = "a" * 300
        resp = client_with_db.get(
            f"/api/dev/v1/sessions/{long_id}/messages"
        )
        assert resp.status_code == 400

    def test_session_id_with_control_chars(self, client_with_db):
        # URL with control chars won't even make it past HTTP parsing,
        # so test with URL-encoded control character
        resp = client_with_db.get(
            "/api/dev/v1/sessions/test%00id/messages"
        )
        # FastAPI may accept it and pass to route; the service should reject
        # or return 404 — either way it must not crash
        assert resp.status_code in (400, 404, 422)

    def test_session_id_sql_injection(self, client_with_db):
        resp = client_with_db.get(
            "/api/dev/v1/sessions/' OR '1'='1/messages"
        )
        # Should return 404 (not found), not 200 with data
        assert resp.status_code in (400, 404)


# ── Optional message fields ──


class TestOptionalFields:
    """Verify optional fields like tokenCount, finishReason."""

    def test_assistant_message_has_optional_fields(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-001/messages"
        )
        items = resp.json()["data"]["items"]
        assistant_msg = next(m for m in items if m["role"] == "assistant")
        assert assistant_msg.get("tokenCount") == 42
        assert assistant_msg.get("finishReason") == "stop"

    def test_user_message_no_optional_fields(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-001/messages"
        )
        items = resp.json()["data"]["items"]
        user_msg = next(m for m in items if m["role"] == "user")
        assert user_msg.get("tokenCount") is None
        assert user_msg.get("finishReason") is None


# ── Inactive messages ──


class TestInactiveMessages:
    """Verify soft-deleted (inactive) messages are excluded."""

    def test_inactive_messages_excluded(self, db_path):
        _insert_session(db_path, "inactive-sess", message_count=0)
        _insert_message(
            db_path, "inactive-sess", content="Active message", active=1,
        )
        _insert_message(
            db_path, "inactive-sess", content="Inactive message", active=0,
        )

        config = DevWebApiConfig(hermes_home=db_path.parent)
        client = TestClient(create_dev_web_api_app(config))

        resp = client.get("/api/dev/v1/sessions/inactive-sess/messages")
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["content"]["text"] == "Active message"


# ── OpenAPI route boundary ──


class TestOpenAPIRouteBoundary:
    """Verify the runtime OpenAPI spec has correct routes."""

    def test_runtime_openapi_has_messages_route(self, client_with_db):
        resp = client_with_db.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        paths = spec.get("paths", {})
        # Must have messages route
        msg_key = None
        for key in paths:
            if "messages" in key:
                msg_key = key
                break
        assert msg_key is not None, "Messages route not found in OpenAPI"
        # Must be GET only
        assert "get" in paths[msg_key]
        assert "post" not in paths[msg_key]
        assert "put" not in paths[msg_key]
        assert "delete" not in paths[msg_key]

    def test_no_forbidden_routes(self, client_with_db):
        """Phase 0C-05: reviews, send, upload, delete routes are absent."""
        resp = client_with_db.get("/openapi.json")
        spec = resp.json()
        paths = spec.get("paths", {})
        path_strs = " ".join(paths.keys()).lower()
        assert "/reviews" not in path_strs
        assert "/send" not in path_strs
        assert "/upload" not in path_strs
        assert "/delete" not in path_strs

    def test_business_routes_count(self, client_with_db):
        """Phase 0C-05: runtime should have exactly 11 business routes."""
        resp = client_with_db.get("/openapi.json")
        spec = resp.json()
        paths = spec.get("paths", {})
        business = [p for p in paths if p.startswith("/api/dev/v1")]
        assert len(business) == 11, (
            f"Expected 11 business routes, got {len(business)}: {business}"
        )


# ── Request ID ──


class TestMessageRequestId:
    """Request ID consistency for message endpoints."""

    def test_client_request_id_echoed(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-001/messages",
            headers={"X-Request-ID": "test-msg-rid-123"},
        )
        assert resp.headers.get("x-request-id") == "test-msg-rid-123"

    def test_auto_generated_request_id(self, seeded_message_client):
        resp = seeded_message_client.get(
            "/api/dev/v1/sessions/msg-session-001/messages"
        )
        rid = resp.json()["meta"]["requestId"]
        assert len(rid) > 0


# ── No write routes ──


class TestNoWriteRoutes:
    """Verify no write methods exist on the messages endpoint."""

    def test_post_messages_rejected(self, client_with_db):
        resp = client_with_db.post(
            "/api/dev/v1/sessions/test/messages", json={}
        )
        assert resp.status_code == 405

    def test_delete_messages_rejected(self, client_with_db):
        resp = client_with_db.delete(
            "/api/dev/v1/sessions/test/messages"
        )
        assert resp.status_code == 405

    def test_put_messages_rejected(self, client_with_db):
        resp = client_with_db.put(
            "/api/dev/v1/sessions/test/messages", json={}
        )
        assert resp.status_code == 405


# ── CORS ──


class TestMessageCORS:
    """CORS headers on message endpoint."""

    def test_cors_preflight(self, client_with_db):
        resp = client_with_db.options(
            "/api/dev/v1/sessions/test/messages",
            headers={
                "Origin": "http://127.0.0.1:5180",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers

    def test_cors_disallows_other_origin(self, client_with_db):
        resp = client_with_db.get(
            "/api/dev/v1/sessions/test/messages",
            headers={"Origin": "http://evil.com"},
        )
        assert "access-control-allow-origin" not in resp.headers
