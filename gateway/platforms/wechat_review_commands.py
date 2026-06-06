"""Read-only Memory Review Queue commands for the development WeChat gateway."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.memory_review_queue import (
    REVIEW_ID_RE,
    list_review_items,
    load_review_item,
)

logger = logging.getLogger(__name__)

MAX_WECHAT_REVIEW_OUTPUT = 2000
DEFAULT_LIST_LIMIT = 5
MAX_LIST_LIMIT = 10
READ_ONLY_ACTIONS = {"status", "list", "show", "help"}
FORBIDDEN_ACTIONS = {
    "approve",
    "reject",
    "write",
    "update",
    "delete",
    "clear",
    "clear-all",
    "archive",
}
COMMAND_RE = re.compile(r"^/memory-review(?:\s+(.*))?$", re.IGNORECASE)


@dataclass(frozen=True)
class WechatReviewCommand:
    action: str
    review_id: str | None = None
    limit: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class WechatReviewCommandResult:
    handled: bool
    response: str | None = None
    error_code: str | None = None


def _truncate(value: Any, limit: int) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[: max(0, limit - len(" [truncated]"))] + " [truncated]"


def _bounded_output(text: str) -> str:
    if len(text) <= MAX_WECHAT_REVIEW_OUTPUT:
        return text
    suffix = "\n[output truncated]"
    return text[: MAX_WECHAT_REVIEW_OUTPUT - len(suffix)] + suffix


def _log_command_result(
    command: WechatReviewCommand,
    *,
    result: str,
    pending_count: int | None = None,
) -> None:
    logger.info(
        "Dev wechat review command: action=%s authorized=yes result=%s "
        "pending_count=%s review_id=%s",
        command.action,
        result,
        pending_count if pending_count is not None else "-",
        command.review_id or "-",
    )


def parse_wechat_review_command(text: str) -> WechatReviewCommand | None:
    match = COMMAND_RE.fullmatch(str(text or "").strip())
    if not match:
        return None
    raw_args = (match.group(1) or "").strip()
    if not raw_args:
        return WechatReviewCommand(action="help")
    parts = raw_args.split()
    action = parts[0].casefold()
    args = parts[1:]

    if action == "status":
        return (
            WechatReviewCommand(action=action)
            if not args
            else WechatReviewCommand(action=action, error="INVALID_ARGUMENTS")
        )
    if action == "help":
        return (
            WechatReviewCommand(action=action)
            if not args
            else WechatReviewCommand(action=action, error="INVALID_ARGUMENTS")
        )
    if action == "list":
        if len(args) > 1:
            return WechatReviewCommand(action=action, error="INVALID_LIST_LIMIT")
        if not args:
            return WechatReviewCommand(action=action, limit=DEFAULT_LIST_LIMIT)
        try:
            limit = int(args[0])
        except ValueError:
            return WechatReviewCommand(action=action, error="INVALID_LIST_LIMIT")
        if not 1 <= limit <= MAX_LIST_LIMIT:
            return WechatReviewCommand(action=action, error="INVALID_LIST_LIMIT")
        return WechatReviewCommand(action=action, limit=limit)
    if action == "show":
        if len(args) != 1:
            return WechatReviewCommand(action=action, error="INVALID_ARGUMENTS")
        review_id = args[0]
        if not REVIEW_ID_RE.fullmatch(review_id):
            return WechatReviewCommand(action=action, error="INVALID_REVIEW_ID")
        return WechatReviewCommand(action=action, review_id=review_id)
    if action in FORBIDDEN_ACTIONS:
        return WechatReviewCommand(action=action, error="WRITE_COMMAND_FORBIDDEN")
    return WechatReviewCommand(action=action, error="UNKNOWN_COMMAND")


def format_review_help() -> str:
    return "\n".join(
        [
            "Memory Review Queue 只读命令",
            "────────────────────",
            "/memory-review status",
            "/memory-review list",
            "/memory-review list 1-10",
            "/memory-review show <review_id>",
            "/memory-review help",
            "",
            "微信端不支持 approve、reject、write、update、delete 或 clear。",
        ]
    )


def format_review_status(
    *,
    pilot_enabled: bool,
    pilot_safety: str,
    pending_count: int,
    max_pending: int,
) -> str:
    return "\n".join(
        [
            "Memory Review Queue",
            "────────────────────",
            f"Pilot: {'enabled' if pilot_enabled else 'disabled'}",
            f"Safety: {pilot_safety if pilot_enabled else 'disabled'}",
            f"Pending: {pending_count}",
            f"Max pending: {max_pending}",
            "Auto write: disabled",
            "Auto update: disabled",
            "Auto category creation: disabled",
        ]
    )


def format_review_list(items: list[dict[str, Any]], warnings: list[str]) -> str:
    if not items:
        lines = ["暂无待审核记忆。"]
    else:
        lines = [f"待审核记忆：{len(items)} 条"]
        for index, item in enumerate(items, start=1):
            candidate = item.get("candidate") or {}
            evaluation = item.get("evaluation") or {}
            reasons = list(evaluation.get("reason_codes") or [])[:4]
            lines.extend(
                [
                    "",
                    f"{index}. {item.get('review_id', 'unknown')}",
                    f"   category: {_truncate(candidate.get('category'), 60)}",
                    f"   score: {evaluation.get('score', 'unknown')}",
                    f"   action: {item.get('proposed_action', 'unknown')}",
                    f"   occurrences: {item.get('occurrence_count', 0)}",
                    f"   created_at: {item.get('created_at', 'unknown')}",
                    f"   reasons: {', '.join(reasons) or 'none'}",
                ]
            )
        lines.extend(["", "查看详情：", "/memory-review show <review_id>"])
    if warnings:
        lines.extend(["", "部分 Review Item 无法读取。"])
    return _bounded_output("\n".join(lines))


def format_review_detail(item: dict[str, Any]) -> str:
    candidate = item.get("candidate") or {}
    evaluation = item.get("evaluation") or {}
    matched = item.get("matched_memory") or {}
    tags = list(candidate.get("tags") or [])[:20]
    reasons = list(evaluation.get("reason_codes") or [])[:10]
    core_tags = list(evaluation.get("core_tag_overlap") or [])[:20]
    lines = [
        "Memory Review Item",
        "────────────────────",
        f"review_id: {item.get('review_id', 'unknown')}",
        f"status: {item.get('status', 'unknown')}",
        f"created_at: {item.get('created_at', 'unknown')}",
        f"updated_at: {item.get('updated_at', 'unknown')}",
        f"last_seen_at: {item.get('last_seen_at', 'unknown')}",
        f"occurrence_count: {item.get('occurrence_count', 0)}",
        "",
        f"title: {_truncate(candidate.get('title'), 120)}",
        f"summary: {_truncate(candidate.get('summary'), 500)}",
        f"category: {_truncate(candidate.get('category'), 60)}",
        f"tags: {_truncate(', '.join(str(tag) for tag in tags), 300)}",
        f"type: {_truncate(candidate.get('type'), 60)}",
        f"importance: {_truncate(candidate.get('importance'), 20)}",
        f"ttl: {_truncate(candidate.get('ttl'), 30)}",
        "",
        f"score: {evaluation.get('score', 'unknown')}",
        f"original decision: {item.get('original_decision', 'unknown')}",
        f"proposed action: {item.get('proposed_action', 'unknown')}",
        f"reason codes: {_truncate(', '.join(str(code) for code in reasons), 400)}",
        f"matched memory: {matched.get('memory_id') or 'none'}",
        f"title similarity: {evaluation.get('title_similarity', 0)}",
        f"summary similarity: {evaluation.get('summary_similarity', 0)}",
        f"combined similarity: {evaluation.get('combined_similarity', 0)}",
        f"core tag overlap: {_truncate(', '.join(str(tag) for tag in core_tags), 300)}",
        f"protected target: {'yes' if evaluation.get('protected_target') else 'no'}",
    ]
    return _bounded_output("\n".join(lines))


def handle_wechat_review_command(
    text: str,
    *,
    hermes_home: Path,
    pilot_enabled: bool,
    pilot_safety: str,
    max_pending: int,
) -> WechatReviewCommandResult:
    command = parse_wechat_review_command(text)
    if command is None:
        return WechatReviewCommandResult(handled=False)

    if command.error == "WRITE_COMMAND_FORBIDDEN":
        _log_command_result(command, result="forbidden")
        response = (
            "该操作不能通过微信执行。\n"
            "请在终端中使用人工审核命令，并优先使用 "
            "memory-review-approve --dry-run。"
        )
        return WechatReviewCommandResult(True, response, command.error)
    if command.error == "INVALID_REVIEW_ID":
        _log_command_result(command, result="invalid")
        return WechatReviewCommandResult(True, "Invalid review ID.", command.error)
    if command.error:
        _log_command_result(command, result="invalid")
        return WechatReviewCommandResult(True, format_review_help(), command.error)
    if not pilot_enabled or pilot_safety != "PASS":
        _log_command_result(command, result="pilot_disabled")
        return WechatReviewCommandResult(
            True,
            "Memory Review Queue Pilot 未启用。\n"
            "请使用开发版 Gateway 的 --memory-review-queue 参数启动。",
            "PILOT_DISABLED",
        )

    try:
        if command.action == "help":
            response = format_review_help()
            result = "success"
            pending_count = None
        elif command.action == "status":
            pending = list_review_items(
                status="pending",
                limit=10000,
                home=hermes_home,
            )
            pending_count = len(pending.items)
            response = format_review_status(
                pilot_enabled=True,
                pilot_safety=pilot_safety,
                pending_count=pending_count,
                max_pending=max_pending,
            )
            result = "success"
        elif command.action == "list":
            reviews = list_review_items(
                status="pending",
                limit=command.limit or DEFAULT_LIST_LIMIT,
                home=hermes_home,
            )
            pending_count = len(reviews.items)
            response = format_review_list(reviews.items, reviews.warnings)
            result = "success"
        elif command.action == "show":
            pending_count = None
            try:
                item = load_review_item(command.review_id or "", home=hermes_home)
            except FileNotFoundError:
                response = "Review item not found."
                result = "not_found"
            else:
                response = format_review_detail(item)
                result = "success"
        else:
            return WechatReviewCommandResult(
                True,
                format_review_help(),
                "UNKNOWN_COMMAND",
            )
    except Exception as exc:
        logger.warning(
            "Dev wechat review command: action=%s authorized=yes result=error "
            "error=%s",
            command.action,
            type(exc).__name__,
        )
        return WechatReviewCommandResult(
            True,
            "暂时无法读取审核队列，请稍后重试。",
            "QUEUE_READ_FAILED",
        )

    _log_command_result(command, result=result, pending_count=pending_count)
    return WechatReviewCommandResult(True, _bounded_output(response))
