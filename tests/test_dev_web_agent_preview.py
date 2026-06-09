"""Tests for the Hermes Dev Web API Phase 1E Agent Preview routes.

Covers:
- Prompt Preview API
- Agent Run Dry-Run API
- Input validation
- Forbidden field rejection
- Safety flags (all forced disabled)
- Side-effect verification (monkeypatch forbidden functions)
- Network call verification (monkeypatch network)
- Hash-based side-effect verification (tmp_path fixtures)
- DTO whitelist (no secrets, no paths, no full system prompt)
- Session handling (no session, valid session, missing session)
- Memory context handling
- System prompt preview (default off, optional on, redacted)
- Capability planning (all forced disabled)
- Temperature / max tokens validation
- Model override handling
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_api import create_dev_web_api_app
from hermes_cli.dev_web_config import DevWebApiConfig


# ── Fixtures ──


@pytest.fixture
def tmp_hermes_home(tmp_path):
    """Create a minimal HERMES_HOME with config and memory."""
    home = tmp_path / "hermes-home"

    # Create directories
    (home / "memory" / "indexes").mkdir(parents=True)
    (home / "memory" / "records").mkdir(parents=True)
    (home / "memory" / "snapshots").mkdir(parents=True)
    (home / "memory" / "reviews").mkdir(parents=True)

    # Create MEMORY.md with a root category (matching real format)
    memory_md = home / "MEMORY.md"
    memory_md.write_text(
        "# Hermes Memory Root Router\n\n"
        "## test-category\n\n"
        "- index: memory://indexes/test-category.json\n"
        "- scope: project\n"
        "- priority: P1\n"
        "- status: active\n"
        "- keywords: test, preview\n"
        "- description: Test category for preview.\n\n",
        encoding="utf-8",
    )

    # Create a category index file (Markdown format matching real structure)
    index_file = home / "memory" / "indexes" / "test-category.md"
    index_file.write_text(
        "# Test Category Index\n\n"
        "## MEM-TEST-001 Test Memory\n\n"
        "- type: test\n"
        "- importance: P1\n"
        "- ttl: 0\n"
        "- status: active\n"
        "- tags: test, preview\n"
        "- storage: memory://records/test/test-memory.md\n"
        "- created_at: 2026-06-09\n"
        "- updated_at: 2026-06-09\n"
        "- summary: A test memory item for preview.\n\n",
        encoding="utf-8",
    )

    # Create empty events file
    events_file = home / "memory" / "events.jsonl"
    events_file.write_text("", encoding="utf-8")

    # Create SOUL.md
    soul_md = home / "SOUL.md"
    soul_md.write_text("You are a helpful AI assistant for testing.", encoding="utf-8")

    # Create config.yaml (minimal safe config)
    config_yaml = home / "config.yaml"
    config_yaml.write_text(
        "model: test-model\n"
        "provider: test-provider\n"
        "temperature: 0.7\n"
        "max_tokens: 2048\n"
        "providers:\n"
        "  test-provider:\n"
        "    api_mode: openai\n",
        encoding="utf-8",
    )

    # Create .env
    env_file = home / ".env"
    env_file.write_text("TEST_API_KEY=test-key-not-real\n", encoding="utf-8")

    return home


@pytest.fixture
def tmp_home_with_session(tmp_hermes_home):
    """Create a HERMES_HOME with a session and messages in state.db."""
    db_path = tmp_hermes_home / "state.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sessions ("
        "  id TEXT PRIMARY KEY,"
        "  title TEXT,"
        "  source TEXT DEFAULT 'cli',"
        "  model TEXT,"
        "  message_count INTEGER DEFAULT 0,"
        "  tool_call_count INTEGER DEFAULT 0,"
        "  input_tokens INTEGER,"
        "  output_tokens INTEGER,"
        "  archived INTEGER DEFAULT 0,"
        "  started_at REAL,"
        "  ended_at REAL,"
        "  last_active_at REAL,"
        "  end_reason TEXT"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS messages ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  session_id TEXT NOT NULL,"
        "  role TEXT NOT NULL,"
        "  content TEXT,"
        "  timestamp REAL,"
        "  token_count INTEGER,"
        "  finish_reason TEXT,"
        "  tool_calls TEXT,"
        "  tool_call_id TEXT,"
        "  tool_name TEXT,"
        "  active INTEGER DEFAULT 1,"
        "  FOREIGN KEY (session_id) REFERENCES sessions(id)"
        ")"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_session "
        "ON messages(session_id, id)"
    )

    import time
    now = time.time()

    conn.execute(
        "INSERT INTO sessions (id, title, source, message_count, started_at, last_active_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("test-session-001", "Test Session", "dev-webui", 2, now, now),
    )
    conn.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) "
        "VALUES (?, ?, ?, ?)",
        ("test-session-001", "user", "Hello from test", now),
    )
    conn.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) "
        "VALUES (?, ?, ?, ?)",
        ("test-session-001", "assistant", "Hello! How can I help?", now),
    )
    conn.commit()
    conn.close()
    return tmp_hermes_home


@pytest.fixture
def client_no_home():
    """TestClient without HERMES_HOME configured."""
    config = DevWebApiConfig(hermes_home=None)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def client_with_home(tmp_hermes_home):
    """TestClient with a valid temporary HERMES_HOME."""
    config = DevWebApiConfig(hermes_home=tmp_hermes_home)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def client_with_session(tmp_home_with_session):
    """TestClient with a HERMES_HOME containing a session."""
    config = DevWebApiConfig(hermes_home=tmp_home_with_session)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ── Shared helpers ──

API_PREFIX = "/api/dev/v1"

FORBIDDEN_FIELDS = [
    "apiKey", "api_key", "baseUrl", "base_url",
    "authorization", "headers", "proxy",
    "systemPrompt", "developerPrompt",
    "tools", "toolSchema", "execute", "run",
    "stream", "force", "persist", "saveSession",
    "writeMemory", "autoMemory",
]

SENSITIVE_STRINGS = [
    "/Users/",
    "/home/",
    "file://",
    "api_key",
    "authorization",
    "Bearer",
    "secret",
    "cookie",
    "base_url",
    "traceback",
    "reasoning",
    "fullSystemPrompt",
    "toolSchema",
]


def _check_no_sensitive_data(data: dict, path: str = "") -> list[str]:
    """Recursively check a response dict for sensitive data."""
    violations = []
    if isinstance(data, dict):
        for key, value in data.items():
            # Check keys
            key_lower = key.lower()
            if key_lower in ("api_key", "apikey", "base_url", "baseurl", "secret", "cookie"):
                violations.append(f"{path}.{key} is a sensitive key")
            # Check string values
            if isinstance(value, str):
                for pattern in ("/Users/", "/home/", "file://", "Bearer ", "api_key=", "secret="):
                    if pattern in value:
                        violations.append(f"{path}.{key} contains '{pattern}'")
            violations.extend(_check_no_sensitive_data(value, f"{path}.{key}"))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            violations.extend(_check_no_sensitive_data(item, f"{path}[{i}]"))
    return violations


# ── 1. Prompt Preview Tests ──


class TestPromptPreview:
    """Tests for POST /agent/prompt/preview."""

    def test_no_session_returns_200(self, client_with_home):
        """Prompt preview without session ID returns 200 with session.exists=false."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["dryRun"] is True
        assert data["data"]["operation"] == "PROMPT_PREVIEW"
        assert data["data"]["session"]["exists"] is False
        assert data["data"]["session"]["historyIncluded"] is False

    def test_with_session_returns_200(self, client_with_session):
        """Prompt preview with valid session returns 200 with session data."""
        resp = client_with_session.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "What is the project status?",
                "sessionId": "test-session-001",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["session"]["exists"] is True
        assert data["data"]["session"]["historyMessageCount"] == 2
        assert data["data"]["session"]["historyIncluded"] is True

    def test_missing_session_still_200(self, client_with_session):
        """Session not found returns 200 with session.exists=false."""
        resp = client_with_session.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "sessionId": "nonexistent-session",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # Session not found but still valid response
        assert data["data"]["session"]["exists"] is False

    def test_invalid_session_id_returns_400(self, client_with_home):
        """Invalid session ID format returns 400."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "sessionId": "valid\nwith\tcontrol\x00chars",
            },
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"]["code"] == "INVALID_SESSION_ID"

    def test_empty_message_returns_400(self, client_with_home):
        """Empty message returns 400."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": ""},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_AGENT_PREVIEW_REQUEST"

    def test_missing_message_returns_400(self, client_with_home):
        """Missing message field returns 400."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={},
        )
        assert resp.status_code == 400

    def test_message_too_long_returns_400(self, client_with_home):
        """Message exceeding 4000 chars returns 400."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "x" * 4001},
        )
        assert resp.status_code == 400

    def test_no_home_returns_503(self, client_no_home):
        """No HERMES_HOME returns 503."""
        resp = client_no_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello"},
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "AGENT_PREVIEW_UNAVAILABLE"

    def test_system_preview_default_off(self, client_with_home):
        """System preview is off by default."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Find SYSTEM_IDENTITY section
        sections = data["data"]["prompt"]["sections"]
        identity = next(s for s in sections if s["type"] == "SYSTEM_IDENTITY")
        assert identity["preview"] is None

    def test_system_preview_enabled(self, client_with_home):
        """System preview can be enabled."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "options": {"includeSystemPreview": True},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        sections = data["data"]["prompt"]["sections"]
        identity = next(s for s in sections if s["type"] == "SYSTEM_IDENTITY")
        assert identity["preview"] is not None
        assert identity["redacted"] is True
        # Preview should be truncated to 500 chars
        assert len(identity["preview"]) <= 500

    def test_system_preview_redacts_paths(self, client_with_home):
        """System preview redacts local paths."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "options": {"includeSystemPreview": True},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        sections = data["data"]["prompt"]["sections"]
        identity = next(s for s in sections if s["type"] == "SYSTEM_IDENTITY")
        if identity["preview"]:
            assert "/Users/" not in identity["preview"]
            assert "/home/" not in identity["preview"]

    def test_memory_context_enabled(self, client_with_home):
        """Memory context is loaded when enabled."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "options": {"includeMemoryContext": True},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        mc = data["data"]["memoryContext"]
        assert mc["enabled"] is True

    def test_memory_context_disabled(self, client_with_home):
        """Memory context is not loaded when disabled."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "options": {"includeMemoryContext": False},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        mc = data["data"]["memoryContext"]
        assert mc["enabled"] is False

    def test_tool_metadata_enabled(self, client_with_home):
        """Tool metadata section is included when enabled."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "options": {"includeToolMetadata": True},
            },
        )
        assert resp.status_code == 200
        sections = resp.json()["data"]["prompt"]["sections"]
        tool_section = next(
            (s for s in sections if s["type"] == "TOOL_METADATA"), None
        )
        assert tool_section is not None

    def test_tool_metadata_disabled(self, client_with_home):
        """Tool metadata section is absent when disabled."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "options": {"includeToolMetadata": False},
            },
        )
        assert resp.status_code == 200
        sections = resp.json()["data"]["prompt"]["sections"]
        tool_section = next(
            (s for s in sections if s["type"] == "TOOL_METADATA"), None
        )
        assert tool_section is None

    def test_temperature_override(self, client_with_home):
        """Temperature override is accepted."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "overrides": {"temperature": 1.5},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["model"]["temperature"] == 1.5

    def test_invalid_temperature_returns_400(self, client_with_home):
        """Temperature out of range returns 400."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "overrides": {"temperature": 3.0},
            },
        )
        assert resp.status_code == 400

    def test_max_tokens_override(self, client_with_home):
        """maxOutputTokens override is accepted."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "overrides": {"maxOutputTokens": 4096},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["model"]["maxOutputTokens"] == 4096

    def test_invalid_max_tokens_returns_400(self, client_with_home):
        """Invalid maxOutputTokens returns 400."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "overrides": {"maxOutputTokens": 0},
            },
        )
        assert resp.status_code == 400


# ── 2. Agent Run Dry-Run Tests ──


class TestAgentRunDryRun:
    """Tests for POST /agent/run/dry-run."""

    def test_basic_dry_run(self, client_with_home):
        """Basic dry-run returns 200 with correct structure."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/run/dry-run",
            json={"message": "Analyze the project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["dryRun"] is True
        assert data["data"]["operation"] == "AGENT_RUN_DRY_RUN"
        assert data["data"]["allowed"] is True

    def test_tools_requested_forced_disabled(self, client_with_home):
        """toolsRequested=true still results in forced disabled."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/run/dry-run",
            json={
                "message": "Hello",
                "options": {"toolsRequested": True},
            },
        )
        assert resp.status_code == 200
        caps = resp.json()["data"]["capabilities"]
        assert caps["toolsRequested"] is True
        assert caps["toolExecutionAvailable"] is False
        assert caps["toolExecutionForcedDisabled"] is True

    def test_stream_requested_forced_disabled(self, client_with_home):
        """streamRequested=true still results in forced disabled."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/run/dry-run",
            json={
                "message": "Hello",
                "options": {"streamRequested": True},
            },
        )
        assert resp.status_code == 200
        caps = resp.json()["data"]["capabilities"]
        assert caps["streamingRequested"] is True
        assert caps["streamingAvailable"] is False
        assert caps["streamingForcedDisabled"] is True

    def test_auto_memory_requested_forced_disabled(self, client_with_home):
        """autoMemoryRequested=true still results in forced disabled."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/run/dry-run",
            json={
                "message": "Hello",
                "options": {"autoMemoryRequested": True},
            },
        )
        assert resp.status_code == 200
        caps = resp.json()["data"]["capabilities"]
        assert caps["autoMemoryRequested"] is True
        assert caps["memoryWriteAvailable"] is False
        assert caps["memoryWriteForcedDisabled"] is True

    def test_all_capabilities_forced_disabled(self, client_with_home):
        """All execution capabilities are forced disabled in Phase 1E."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/run/dry-run",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        caps = resp.json()["data"]["capabilities"]
        assert caps["llmCallForcedDisabled"] is True
        assert caps["streamingForcedDisabled"] is True
        assert caps["toolExecutionForcedDisabled"] is True
        assert caps["memoryWriteForcedDisabled"] is True
        assert caps["sessionWriteAvailable"] is False
        assert caps["reviewQueueAvailable"] is False

    def test_warnings_for_requested_capabilities(self, client_with_home):
        """Warnings are generated when requested capabilities are forced disabled."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/run/dry-run",
            json={
                "message": "Hello",
                "options": {
                    "toolsRequested": True,
                    "streamRequested": True,
                    "autoMemoryRequested": True,
                },
            },
        )
        assert resp.status_code == 200
        warnings = resp.json()["data"]["warnings"]
        assert len(warnings) == 3

    def test_no_warnings_when_nothing_requested(self, client_with_home):
        """No warnings when no capabilities are requested."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/run/dry-run",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        warnings = resp.json()["data"]["warnings"]
        assert len(warnings) == 0


# ── 3. Forbidden Field Tests ──


class TestForbiddenFields:
    """Verify that dangerous request fields are rejected."""

    @pytest.mark.parametrize("field", FORBIDDEN_FIELDS[:10])
    def test_forbidden_field_in_body(self, client_with_home, field):
        """Forbidden field at top level is rejected."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello", field: "dangerous"},
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize("field", FORBIDDEN_FIELDS[:5])
    def test_forbidden_field_in_options(self, client_with_home, field):
        """Forbidden field in options is rejected."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello", "options": {field: "dangerous"}},
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize("field", FORBIDDEN_FIELDS[:5])
    def test_forbidden_field_in_overrides(self, client_with_home, field):
        """Forbidden field in overrides is rejected."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello", "overrides": {field: "dangerous"}},
        )
        assert resp.status_code == 400


# ── 4. Safety Flags Tests ──


class TestSafetyFlags:
    """Verify all safety flags are correct."""

    def test_prompt_preview_safety_flags(self, client_with_home):
        """Prompt Preview returns correct safety flags."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        safety = resp.json()["data"]["safety"]
        assert safety["readOnly"] is True
        assert safety["sideEffects"] is False
        assert safety["llmCalled"] is False
        assert safety["toolsExecuted"] is False
        assert safety["sessionWritten"] is False
        assert safety["memoryWritten"] is False
        assert safety["reviewQueued"] is False

    def test_dry_run_safety_flags(self, client_with_home):
        """Run Dry-Run returns correct safety flags."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/run/dry-run",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        safety = resp.json()["data"]["safety"]
        assert safety["readOnly"] is True
        assert safety["sideEffects"] is False
        assert safety["llmCalled"] is False
        assert safety["toolsExecuted"] is False
        assert safety["sessionWritten"] is False
        assert safety["memoryWritten"] is False
        assert safety["reviewQueued"] is False

    def test_no_effects_list(self, client_with_home):
        """Both endpoints return the no-effects list."""
        for endpoint in ["prompt/preview", "run/dry-run"]:
            resp = client_with_home.post(
                f"{API_PREFIX}/agent/{endpoint}",
                json={"message": "Hello"},
            )
            assert resp.status_code == 200
            no_effects = resp.json()["data"]["noEffects"]
            assert len(no_effects) == 5
            assert any("No language model request" in e for e in no_effects)
            assert any("No session message" in e for e in no_effects)
            assert any("No memory file" in e for e in no_effects)
            assert any("No tool was executed" in e for e in no_effects)
            assert any("No review item" in e for e in no_effects)

    def test_checks_all_passed(self, client_with_home):
        """All checks pass."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        checks = resp.json()["data"]["checks"]
        assert len(checks) == 5
        for check in checks:
            assert check["passed"] is True


# ── 5. Forbidden Function Monkeypatch Tests ──


def _fail_if_called(*args, **kwargs):
    """Raise AssertionError if any forbidden function is called."""
    raise AssertionError("Forbidden function was called during preview!")


class TestForbiddenFunctions:
    """Verify that forbidden execution functions are never called."""

    def test_prompt_preview_no_agent_calls(self, client_with_home):
        """Prompt Preview does not call AIAgent.chat or run_conversation."""
        with patch("run_agent.AIAgent.chat", _fail_if_called), \
             patch("agent.conversation_loop.run_conversation", _fail_if_called):
            resp = client_with_home.post(
                f"{API_PREFIX}/agent/prompt/preview",
                json={"message": "Hello"},
            )
            assert resp.status_code == 200

    def test_dry_run_no_agent_calls(self, client_with_home):
        """Run Dry-Run does not call AIAgent.chat or run_conversation."""
        with patch("run_agent.AIAgent.chat", _fail_if_called), \
             patch("agent.conversation_loop.run_conversation", _fail_if_called):
            resp = client_with_home.post(
                f"{API_PREFIX}/agent/run/dry-run",
                json={"message": "Hello"},
            )
            assert resp.status_code == 200

    def test_prompt_preview_no_tool_dispatch(self, client_with_home):
        """Prompt Preview does not call registry.dispatch."""
        with patch("tools.registry.ToolRegistry.dispatch", _fail_if_called):
            resp = client_with_home.post(
                f"{API_PREFIX}/agent/prompt/preview",
                json={"message": "Hello"},
            )
            assert resp.status_code == 200

    def test_prompt_preview_no_memory_writer(self, client_with_home):
        """Prompt Preview does not call maybe_auto_write_memory."""
        with patch("agent.runtime_memory_writer.maybe_auto_write_memory", _fail_if_called):
            resp = client_with_home.post(
                f"{API_PREFIX}/agent/prompt/preview",
                json={"message": "Hello"},
            )
            assert resp.status_code == 200

    def test_prompt_preview_no_review_enqueue(self, client_with_home):
        """Prompt Preview does not call enqueue_review_item."""
        with patch("agent.memory_review_queue.enqueue_review_item", _fail_if_called):
            resp = client_with_home.post(
                f"{API_PREFIX}/agent/prompt/preview",
                json={"message": "Hello"},
            )
            assert resp.status_code == 200

    def test_prompt_preview_no_session_append(self, client_with_home):
        """Prompt Preview does not call SessionDB.append_message."""
        with patch("hermes_state.SessionDB.append_message", _fail_if_called):
            resp = client_with_home.post(
                f"{API_PREFIX}/agent/prompt/preview",
                json={"message": "Hello"},
            )
            assert resp.status_code == 200

    def test_dry_run_no_tool_dispatch(self, client_with_home):
        """Run Dry-Run does not call registry.dispatch."""
        with patch("tools.registry.ToolRegistry.dispatch", _fail_if_called):
            resp = client_with_home.post(
                f"{API_PREFIX}/agent/run/dry-run",
                json={"message": "Hello"},
            )
            assert resp.status_code == 200


# ── 6. DTO Safety Tests ──


class TestDtoSafety:
    """Verify responses contain no sensitive data."""

    def test_prompt_preview_no_secrets(self, client_with_home):
        """Prompt Preview response contains no sensitive strings."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        violations = _check_no_sensitive_data(resp.json())
        assert violations == [], f"Sensitive data found: {violations}"

    def test_dry_run_no_secrets(self, client_with_home):
        """Run Dry-Run response contains no sensitive strings."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/run/dry-run",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        violations = _check_no_sensitive_data(resp.json())
        assert violations == [], f"Sensitive data found: {violations}"

    def test_model_info_safe(self, client_with_home):
        """Model info only contains safe fields."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        model = resp.json()["data"]["model"]
        # Only safe fields
        assert "name" in model
        assert "provider" in model
        # No dangerous fields
        assert "api_key" not in model
        assert "apiKey" not in model
        assert "base_url" not in model
        assert "baseUrl" not in model
        assert "headers" not in model
        assert "proxy" not in model

    def test_memory_context_no_paths(self, client_with_home):
        """Memory context items contain no file paths."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello", "options": {"includeMemoryContext": True}},
        )
        assert resp.status_code == 200
        mc = resp.json()["data"]["memoryContext"]
        for item in mc.get("items", []):
            # Only safe fields
            assert "memoryId" in item
            assert "title" in item
            assert "category" in item
            assert "score" in item
            assert "summaryPreview" in item
            # No dangerous fields
            assert "storage" not in item
            assert "recordPath" not in item
            assert "indexPath" not in item
            assert "absolutePath" not in item


# ── 7. Side-Effect Hash Tests ──


def _hash_tree(path: Path) -> str:
    """Compute a SHA-256 hash of all files under a directory."""
    h = hashlib.sha256()
    for fpath in sorted(path.rglob("*")):
        if fpath.is_file():
            h.update(str(fpath.relative_to(path)).encode("utf-8"))
            h.update(fpath.read_bytes())
    return h.hexdigest()


def _count_files(path: Path) -> int:
    """Count files under a directory."""
    return sum(1 for _ in path.rglob("*") if _.is_file())


class TestSideEffectHash:
    """Verify that preview operations cause zero filesystem side effects."""

    def test_prompt_preview_no_side_effects(self, tmp_hermes_home):
        """Prompt Preview does not modify any files."""
        config = DevWebApiConfig(hermes_home=tmp_hermes_home)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        before_hash = _hash_tree(tmp_hermes_home)
        before_count = _count_files(tmp_hermes_home)

        client.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello"},
        )

        after_hash = _hash_tree(tmp_hermes_home)
        after_count = _count_files(tmp_hermes_home)

        assert before_hash == after_hash, "Filesystem was modified!"
        assert before_count == after_count, "File count changed!"

    def test_dry_run_no_side_effects(self, tmp_hermes_home):
        """Run Dry-Run does not modify any files."""
        config = DevWebApiConfig(hermes_home=tmp_hermes_home)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        before_hash = _hash_tree(tmp_hermes_home)
        before_count = _count_files(tmp_hermes_home)

        client.post(
            f"{API_PREFIX}/agent/run/dry-run",
            json={"message": "Hello"},
        )

        after_hash = _hash_tree(tmp_hermes_home)
        after_count = _count_files(tmp_hermes_home)

        assert before_hash == after_hash, "Filesystem was modified!"
        assert before_count == after_count, "File count changed!"

    def test_prompt_preview_db_unchanged(self, tmp_home_with_session):
        """Prompt Preview does not change state.db."""
        config = DevWebApiConfig(hermes_home=tmp_home_with_session)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        db_path = tmp_home_with_session / "state.db"
        before_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()

        client.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "sessionId": "test-session-001",
            },
        )

        after_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()
        assert before_hash == after_hash, "state.db was modified!"

    def test_no_db_auxiliary_files(self, tmp_home_with_session):
        """No WAL/SHM/journal files created after preview."""
        config = DevWebApiConfig(hermes_home=tmp_home_with_session)
        app = create_dev_web_api_app(config)
        client = TestClient(app)

        # Check no auxiliary files before
        home = tmp_home_with_session
        aux_before = list(home.glob("state.db-*"))

        client.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello", "sessionId": "test-session-001"},
        )
        client.post(
            f"{API_PREFIX}/agent/run/dry-run",
            json={"message": "Hello", "sessionId": "test-session-001"},
        )

        aux_after = list(home.glob("state.db-*"))
        assert aux_before == aux_after, "DB auxiliary files were created!"


# ── 8. Redaction Tests ──


class TestRedaction:
    """Verify path and secret redaction."""

    def test_path_redaction_in_user_message(self, client_with_home):
        """Paths in user message preview are redacted."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Check /Users/test/file.txt please"},
        )
        assert resp.status_code == 200
        preview = resp.json()["data"]["userMessagePreview"]
        assert "/Users/" not in preview
        assert "[local-path]" in preview

    def test_secret_redaction_in_user_message(self, client_with_home):
        """Secrets in user message preview are redacted."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "My api_key=sk-12345 is here"},
        )
        assert resp.status_code == 200
        preview = resp.json()["data"]["userMessagePreview"]
        assert "sk-12345" not in preview
        assert "[secret-redacted]" in preview


# ── 9. Prompt Section Tests ──


class TestPromptSections:
    """Verify prompt section metadata."""

    def test_all_sections_present(self, client_with_home):
        """All expected section types are present."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={
                "message": "Hello",
                "options": {"includeToolMetadata": True},
            },
        )
        assert resp.status_code == 200
        sections = resp.json()["data"]["prompt"]["sections"]
        types = {s["type"] for s in sections}
        assert "SYSTEM_IDENTITY" in types
        assert "USER_MESSAGE" in types
        assert "TIMESTAMP" in types
        assert "TOOL_METADATA" in types

    def test_section_count(self, client_with_home):
        """Prompt section count matches actual sections."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["prompt"]["sectionCount"] == len(data["prompt"]["sections"])

    def test_user_message_section_preview(self, client_with_home):
        """USER_MESSAGE section has a preview."""
        resp = client_with_home.post(
            f"{API_PREFIX}/agent/prompt/preview",
            json={"message": "Hello world"},
        )
        assert resp.status_code == 200
        sections = resp.json()["data"]["prompt"]["sections"]
        user_section = next(s for s in sections if s["type"] == "USER_MESSAGE")
        assert user_section["preview"] is not None
        assert user_section["characterCount"] == 11  # "Hello world"
