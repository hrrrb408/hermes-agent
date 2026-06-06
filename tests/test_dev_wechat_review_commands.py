"""Tests for dev-only WeChat Memory Review Queue read-only commands."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from agent.memory_review_queue import (
    enqueue_review_item,
    get_review_queue_paths,
    reject_review_item,
)
from agent.runtime_memory_writer import (
    MemoryCandidate,
    MemoryDecision,
    MemoryEvaluation,
    ScoreEntry,
)
from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.platforms.base import MessageEvent
from gateway.platforms.wechat_review_commands import (
    MAX_WECHAT_REVIEW_OUTPUT,
    WechatReviewCommandResult,
    handle_wechat_review_command,
    parse_wechat_review_command,
)
from gateway.session import SessionSource
from hermes_cli.memory_router import ensure_memory_scaffold, validate_memory


@pytest.fixture
def review_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "wechat-review-home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    ensure_memory_scaffold(home)
    assert home.resolve() == (tmp_path / "wechat-review-home").resolve()
    assert home.resolve() != Path("/Users/huangruibang/Code/hermes-home-dev").resolve()
    assert validate_memory(home).ok
    return home


def _evaluation(index: int, *, long: bool = False) -> MemoryEvaluation:
    suffix = f"{index:03d}"
    summary = (
        ("候选摘要" * 500)
        if long
        else f"Hermes dev WeChat review candidate {suffix}"
    )
    candidate = MemoryCandidate(
        title=("候选标题" * 100) if long else f"Review candidate {suffix}",
        summary=summary,
        category="hermes",
        tags=[f"tag-{value}" for value in range(30)] if long else ["hermes", "review"],
        memory_type="project_progress",
        importance="P1",
        ttl="project",
    )
    return MemoryEvaluation(
        candidate=candidate,
        score=90 - index,
        score_breakdown=[ScoreEntry("read_only_test", 90)],
        decision=MemoryDecision.REVIEW,
        reason_codes=(
            [f"REASON_{value}_{'X' * 80}" for value in range(20)]
            if long
            else ["SCORE_IN_REVIEW_RANGE"]
        ),
        reasons=["Read-only test."],
        title_similarity=0.81,
        summary_similarity=0.82,
        combined_similarity=0.83,
        core_tag_overlap=["review", "wechat"],
        protected_target=False,
    )


def _enqueue(home: Path, index: int, *, long: bool = False) -> dict[str, Any]:
    item, created, _message = enqueue_review_item(
        _evaluation(index, long=long),
        home=home,
        require_enabled=False,
    )
    assert item is not None and created
    return item


def _handle(home: Path, text: str, *, enabled: bool = True):
    return handle_wechat_review_command(
        text,
        hermes_home=home,
        pilot_enabled=enabled,
        pilot_safety="PASS" if enabled else "disabled",
        max_pending=20,
    )


def _tree_hash(home: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in home.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(home)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


@pytest.mark.parametrize(
    ("text", "action", "limit"),
    [
        ("/memory-review status", "status", None),
        ("/memory-review list", "list", 5),
        ("/memory-review list 10", "list", 10),
        (
            "/memory-review show MR-20260606T120530-a1b2c3d4",
            "show",
            None,
        ),
        ("/memory-review help", "help", None),
        ("  /MEMORY-REVIEW LIST 1  ", "list", 1),
    ],
)
def test_command_parser(text: str, action: str, limit: int | None) -> None:
    command = parse_wechat_review_command(text)
    assert command is not None
    assert command.action == action
    assert command.limit == limit


@pytest.mark.parametrize(
    "text",
    [
        "Hermes memory review status",
        "请执行 /memory-review list",
        "prefix /memory-review status",
        "/memory-reviewer list",
    ],
)
def test_normal_messages_are_not_commands(text: str) -> None:
    assert parse_wechat_review_command(text) is None


def test_pilot_disabled_is_handled_without_queue_access(
    review_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "gateway.platforms.wechat_review_commands.list_review_items",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("queue read")),
    )
    result = _handle(review_home, "/memory-review list", enabled=False)
    assert result.handled
    assert "Pilot 未启用" in result.response


def test_status_has_safe_fields_without_absolute_paths(review_home: Path) -> None:
    _enqueue(review_home, 1)
    _enqueue(review_home, 2)
    result = _handle(review_home, "/memory-review status")
    assert result.handled
    assert "Pilot: enabled" in result.response
    assert "Safety: PASS" in result.response
    assert "Pending: 2" in result.response
    assert "Max pending: 20" in result.response
    assert "Auto write: disabled" in result.response
    assert str(review_home) not in result.response


def test_empty_list_is_readable(review_home: Path) -> None:
    result = _handle(review_home, "/memory-review list")
    assert result.response == "暂无待审核记忆。"


def test_list_only_pending_newest_first(review_home: Path) -> None:
    pending = [_enqueue(review_home, index) for index in range(1, 4)]
    rejected = _enqueue(review_home, 4)
    reject_review_item(rejected["review_id"], "test", home=review_home)
    approved = _enqueue(review_home, 5)
    approved_path = (
        get_review_queue_paths(review_home).items / f"{approved['review_id']}.json"
    )
    approved_payload = json.loads(approved_path.read_text(encoding="utf-8"))
    approved_payload["status"] = "approved"
    approved_payload["approval"] = {
        "approved_at": approved_payload["updated_at"],
        "action": "WRITE",
        "memory_id": "MEM-HERMES-999",
    }
    approved_path.write_text(json.dumps(approved_payload), encoding="utf-8")

    result = _handle(review_home, "/memory-review list")
    assert "待审核记忆：3 条" in result.response
    for item in pending:
        assert item["review_id"] in result.response
    assert rejected["review_id"] not in result.response
    assert approved["review_id"] not in result.response


def test_list_limits_and_invalid_limits(review_home: Path) -> None:
    for index in range(12):
        _enqueue(review_home, index)
    assert "Pending: 12" in _handle(
        review_home,
        "/memory-review status",
    ).response
    assert _handle(review_home, "/memory-review list").response.count("\n1.") == 1
    assert _handle(review_home, "/memory-review list").response.count("\n") > 5
    assert _handle(review_home, "/memory-review list 1").response.startswith(
        "待审核记忆：1 条"
    )
    assert _handle(review_home, "/memory-review list 10").response.startswith(
        "待审核记忆：10 条"
    )
    for value in ("0", "11", "-1", "abc", "1 extra"):
        result = _handle(review_home, f"/memory-review list {value}")
        assert result.error_code == "INVALID_LIST_LIMIT"
        assert "/memory-review list 1-10" in result.response


def test_show_uses_whitelist_and_review_fields(review_home: Path) -> None:
    item = _enqueue(review_home, 1)
    path = get_review_queue_paths(review_home).items / f"{item['review_id']}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(
        {
            "api_key": "secret-api-key",
            "token": "secret-token",
            "cookie": "secret-cookie",
            "prompt": "secret-prompt",
            "assistant_response": "secret-assistant",
            "original_message": "secret-user-message",
        }
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = _handle(review_home, f"/memory-review show {item['review_id']}")
    assert item["review_id"] in result.response
    assert "Review candidate 001" in result.response
    assert "score: 89" in result.response
    assert "title similarity: 0.81" in result.response
    for secret in (
        "secret-api-key",
        "secret-token",
        "secret-cookie",
        "secret-prompt",
        "secret-assistant",
        "secret-user-message",
    ):
        assert secret not in result.response


@pytest.mark.parametrize(
    "review_id",
    ["../../MEMORY.md", "/etc/passwd", "../items/test.json", "invalid-id"],
)
def test_show_rejects_invalid_review_ids(
    review_home: Path,
    review_id: str,
) -> None:
    result = _handle(review_home, f"/memory-review show {review_id}")
    assert result.response == "Invalid review ID."
    assert result.error_code == "INVALID_REVIEW_ID"


def test_show_missing_and_corrupt_items(review_home: Path) -> None:
    missing = _handle(
        review_home,
        "/memory-review show MR-20260606T120530-ffffffff",
    )
    assert missing.response == "Review item not found."

    good = _enqueue(review_home, 1)
    paths = get_review_queue_paths(review_home)
    (paths.items / "MR-20260606T120530-deadbeef.json").write_text(
        "{broken",
        encoding="utf-8",
    )
    listed = _handle(review_home, "/memory-review list")
    assert good["review_id"] in listed.response
    assert "部分 Review Item 无法读取" in listed.response


@pytest.mark.parametrize(
    "action",
    ["approve MR-1", "reject MR-1", "write", "update", "delete MR-1", "clear"],
)
def test_write_commands_are_forbidden(review_home: Path, action: str) -> None:
    before = _tree_hash(review_home)
    result = _handle(review_home, f"/memory-review {action}")
    assert result.handled
    assert "不能通过微信执行" in result.response
    assert result.error_code == "WRITE_COMMAND_FORBIDDEN"
    assert _tree_hash(review_home) == before


def test_commands_are_fully_read_only(review_home: Path) -> None:
    item = _enqueue(review_home, 1)
    before = _tree_hash(review_home)
    for command in (
        "/memory-review status",
        "/memory-review list",
        f"/memory-review show {item['review_id']}",
        "/memory-review help",
        "/memory-review list 0",
    ):
        assert _handle(review_home, command).handled
        assert _tree_hash(review_home) == before


def test_long_show_output_is_bounded_and_unicode_safe(review_home: Path) -> None:
    item = _enqueue(review_home, 1, long=True)
    result = _handle(review_home, f"/memory-review show {item['review_id']}")
    assert len(result.response) <= MAX_WECHAT_REVIEW_OUTPUT
    assert "[truncated]" in result.response
    assert "候选" in result.response


def test_queue_read_failure_isolated(
    review_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        "gateway.platforms.wechat_review_commands.list_review_items",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("read failure")),
    )
    result = _handle(review_home, "/memory-review list")
    assert result.handled
    assert result.error_code == "QUEUE_READ_FAILED"
    assert "暂时无法读取审核队列" in result.response
    assert "read failure" not in result.response
    assert "result=error" in caplog.text


def _weixin_event(text: str, *, chat_type: str = "dm") -> MessageEvent:
    return MessageEvent(
        text=text,
        source=SessionSource(
            platform=Platform.WEIXIN,
            user_id="test-user",
            chat_id="test-chat",
            user_name="test-user",
            chat_type=chat_type,
        ),
        message_id="message-1",
    )


def _runner(*, authorized: bool):
    from gateway.run import GatewayRunner

    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(
        platforms={
            Platform.WEIXIN: PlatformConfig(
                enabled=True,
                token="test",
                extra={
                    "dev_wechat_review_commands": True,
                    "dev_review_pilot_enabled": True,
                    "dev_review_pilot_safety": "PASS",
                    "dev_review_max_pending": 20,
                },
            )
        }
    )
    runner._is_user_authorized = lambda _source: authorized
    runner.adapters = {}
    runner._handle_message_with_agent = AsyncMock(
        side_effect=AssertionError("review command reached Agent Runtime")
    )
    return runner


@pytest.mark.asyncio
async def test_gateway_dispatch_runs_review_handler_after_authorization(
    review_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", lambda *_a, **_k: [])
    runner = _runner(authorized=True)
    result = await runner._handle_message(_weixin_event("/memory-review status"))
    assert "Memory Review Queue" in result
    runner._handle_message_with_agent.assert_not_called()


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_reach_review_handler(
    review_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", lambda *_a, **_k: [])
    monkeypatch.setattr(
        "gateway.platforms.wechat_review_commands.handle_wechat_review_command",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("unauthorized review handler call")
        ),
    )
    runner = _runner(authorized=False)
    result = await runner._handle_message(
        _weixin_event("/memory-review list", chat_type="group")
    )
    assert result is None


def test_normal_message_returns_unhandled(review_home: Path) -> None:
    result = _handle(review_home, "Hermes 记忆系统现在做到哪了")
    assert result == WechatReviewCommandResult(handled=False)
