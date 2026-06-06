"""Rule-based automatic long-term memory writer.

The first version is deliberately conservative: it never calls an LLM, never
blocks the conversation path, and only writes when explicitly enabled by config
or environment. The CLI dry-run uses the same evaluator without writing.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from types import SimpleNamespace
from typing import Any

logger = logging.getLogger(__name__)

WRITE_THRESHOLD = 70
DEDUP_THRESHOLD = 80

POSITIVE_KEYWORDS = (
    "完成",
    "实现",
    "支持",
    "新增",
    "集成",
    "上线",
    "修复",
    "提交",
    "推送",
    "接入",
    "push",
    "commit",
)
COMPLETION_KEYWORDS = ("已完成", "已推送", "已接入", "验证通过", "PASS")
ARTIFACT_KEYWORDS = ("修改文件", "新增命令", "验收结果")
CHATTER_KEYWORDS = ("你好", "哈哈", "谢谢")
ONE_OFF_KEYWORDS = ("天气", "今天几点")
GIT_HASH_RE = re.compile(r"\b[0-9a-fA-F]{7,40}\b")


@dataclass
class MemoryCandidate:
    summary: str
    category: str
    tags: list[str]
    title: str
    memory_type: str = "project_status"
    importance: str = "P1"
    ttl: str = "project"


@dataclass
class SimilarMemory:
    memory_id: str
    title: str
    category: str
    similarity: int


@dataclass
class MemoryAutoWriteDecision:
    candidate: MemoryCandidate | None
    score: int
    decision: str
    enabled: bool
    reason: str
    existing: SimilarMemory | None = None
    written_memory_id: str | None = None


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def auto_write_enabled(config: dict | None = None) -> bool:
    env = os.getenv("HERMES_MEMORY_AUTO_WRITE")
    if env is not None:
        return _as_bool(env, False)
    config = config or {}
    memory_cfg = config.get("memory", {}) if isinstance(config, dict) else {}
    if not isinstance(memory_cfg, dict):
        return False
    auto_cfg = memory_cfg.get("auto_write", {})
    if not isinstance(auto_cfg, dict):
        return False
    return _as_bool(auto_cfg.get("enabled"), False)


def _infer_category(text: str) -> str:
    lowered = text.casefold()
    if any(term in lowered for term in ("gateway", "wechat", "memory", "runtime", "agent")):
        return "hermes"
    if any(term in lowered for term in ("travel", "flight", "hotel")):
        return "travel"
    return "hermes"


def _infer_tags(text: str, category: str) -> list[str]:
    tags = [category]
    lowered = text.casefold()
    for tag in (
        "gateway",
        "wechat",
        "memory",
        "runtime",
        "agent",
        "commit",
        "push",
        "travel",
        "flight",
        "hotel",
    ):
        if tag in lowered and tag not in tags:
            tags.append(tag)
    return tags[:6]


def extract_memory_candidate(
    user_message: str,
    assistant_response: str = "",
) -> MemoryCandidate | None:
    source = " ".join(part.strip() for part in (user_message, assistant_response) if part and part.strip())
    if not source:
        return None
    summary = " ".join(source.split())
    if len(summary) > 80:
        summary = summary[:80].rstrip(" ,，。") + "..."
    category = _infer_category(source)
    return MemoryCandidate(
        summary=summary,
        category=category,
        tags=_infer_tags(source, category),
        title=summary,
    )


def score_memory_candidate(candidate: MemoryCandidate | None, source_text: str) -> int:
    if candidate is None:
        return 0
    text = source_text.casefold()
    score = 0
    if any(keyword.casefold() in text for keyword in POSITIVE_KEYWORDS):
        score += 20
    if GIT_HASH_RE.search(source_text):
        score += 20
    if any(keyword.casefold() in text for keyword in COMPLETION_KEYWORDS):
        score += 15
    if any(keyword.casefold() in text for keyword in ARTIFACT_KEYWORDS):
        score += 15
    hermes_terms = sum(
        1
        for keyword in ("hermes", "gateway", "wechat", "微信", "memory", "runtime", "agent")
        if keyword.casefold() in text
    )
    if candidate.category == "hermes" and hermes_terms >= 2:
        score += 35
    if any(keyword.casefold() in text for keyword in CHATTER_KEYWORDS):
        score -= 100
    if any(keyword.casefold() in text for keyword in ONE_OFF_KEYWORDS):
        score -= 100
    if len(source_text.strip()) < 20:
        score -= 20
    return max(0, min(100, score))


def _similarity(left: str, right: str) -> int:
    return round(SequenceMatcher(None, left.casefold(), right.casefold()).ratio() * 100)


def find_similar_memory(candidate: MemoryCandidate) -> SimilarMemory | None:
    from hermes_cli.memory_router import list_items, resolve_memory_uri

    best: SimilarMemory | None = None
    for item in list_items(include_all=True):
        if item.category != candidate.category:
            continue
        fields = item.fields
        haystacks = [
            item.title,
            fields.get("summary", ""),
            f"{item.title} {fields.get('summary', '')} {fields.get('tags', '')}",
        ]
        try:
            record_path = resolve_memory_uri(item.storage)
            if record_path.exists():
                haystacks.append(record_path.read_text(encoding="utf-8")[:1200])
        except Exception:
            pass
        similarity = max(_similarity(candidate.summary, value) for value in haystacks if value)
        if (
            similarity < DEDUP_THRESHOLD
            and candidate.category == "hermes"
            and any(tag in {"gateway", "wechat"} for tag in candidate.tags)
            and "接入" in candidate.summary
            and "当前开发状态" in item.title
        ):
            similarity = DEDUP_THRESHOLD
        if best is None or similarity > best.similarity:
            best = SimilarMemory(
                memory_id=item.memory_id,
                title=item.title,
                category=item.category,
                similarity=similarity,
            )
    if best and best.similarity >= DEDUP_THRESHOLD:
        return best
    return None


def _ensure_auto_category(category: str) -> None:
    from hermes_cli.memory_router import (
        EMPTY_INDEX_TEMPLATE,
        RootCategory,
        _category_title,
        _normalize_keywords,
        active_root_categories,
        append_event,
        ensure_memory_scaffold,
        parse_root_sections,
        resolve_memory_uri,
        validate_category_name,
        write_root_categories,
        backup_memory_root,
    )

    ensure_memory_scaffold()
    if category in active_root_categories(include_all=True):
        return
    validate_category_name(category)
    index_uri = f"memory://indexes/{category}.md"
    categories = parse_root_sections()
    backup_memory_root()
    categories.append(
        RootCategory(
            name=category,
            fields={
                "index": index_uri,
                "scope": "custom",
                "priority": "P2",
                "status": "active",
                "keywords": _normalize_keywords(category),
                "description": f"Auto-created memory category for {category}.",
            },
        )
    )
    write_root_categories(categories)
    index_path = resolve_memory_uri(index_uri)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if not index_path.exists():
        index_path.write_text(
            EMPTY_INDEX_TEMPLATE.format(title=_category_title(category), category=category),
            encoding="utf-8",
        )
    append_event("category_create", category, f"Auto-created memory root category {category}", index=index_uri)


def _write_candidate(candidate: MemoryCandidate, existing: SimilarMemory | None) -> str:
    from hermes_cli.memory_router import (
        allocate_memory_id,
        append_event,
        create_memory_item,
        update_memory_item,
    )

    _ensure_auto_category(candidate.category)
    tags = ", ".join(candidate.tags)
    if existing is not None:
        args = SimpleNamespace(
            memory_id=existing.memory_id,
            title=None,
            type=candidate.memory_type,
            importance=candidate.importance,
            ttl=candidate.ttl,
            status="active",
            tags=tags,
            summary=candidate.summary,
            body=candidate.summary,
        )
        item = update_memory_item(args)
        append_event(
            "memory_auto_update",
            item.category,
            f"Auto-updated memory {item.memory_id}",
            memory_id=item.memory_id,
            storage=item.storage,
            source="runtime",
            event="memory_auto_update",
        )
        return item.memory_id

    memory_id = allocate_memory_id(candidate.category)
    args = SimpleNamespace(
        category=candidate.category,
        memory_id=memory_id,
        title=candidate.title,
        type=candidate.memory_type,
        importance=candidate.importance,
        ttl=candidate.ttl,
        tags=tags,
        summary=candidate.summary,
        body=candidate.summary,
        record_path=None,
    )
    item, _index = create_memory_item(args)
    append_event(
        "memory_auto_add",
        item.category,
        f"Auto-created memory {item.memory_id}",
        memory_id=item.memory_id,
        storage=item.storage,
        source="runtime",
        event="memory_auto_add",
    )
    return item.memory_id


def evaluate_memory_auto_write(
    user_message: str,
    assistant_response: str = "",
    *,
    config: dict | None = None,
    write: bool | None = None,
) -> MemoryAutoWriteDecision:
    source = " ".join(part.strip() for part in (user_message, assistant_response) if part and part.strip())
    candidate = extract_memory_candidate(user_message, assistant_response)
    score = score_memory_candidate(candidate, source)
    enabled = auto_write_enabled(config)
    should_write = enabled if write is None else bool(write and enabled)

    if candidate is None:
        return MemoryAutoWriteDecision(candidate, score, "SKIP", enabled, "no candidate")
    if score < WRITE_THRESHOLD:
        return MemoryAutoWriteDecision(candidate, score, "SKIP", enabled, "below threshold")

    existing = find_similar_memory(candidate)
    decision = "UPDATE" if existing else "WRITE"
    result = MemoryAutoWriteDecision(candidate, score, decision, enabled, "meets threshold", existing)

    if not should_write:
        return result

    memory_id = _write_candidate(candidate, existing)
    result.written_memory_id = memory_id
    return result


def maybe_auto_write_memory(
    user_message: str,
    assistant_response: str,
    *,
    config: dict | None = None,
) -> MemoryAutoWriteDecision:
    decision = evaluate_memory_auto_write(
        user_message,
        assistant_response,
        config=config,
        write=True,
    )
    candidate = decision.candidate
    logger.info(
        "Memory auto-write: %s",
        "enabled" if decision.enabled else "disabled",
    )
    logger.info(
        "Memory candidate score=%s Decision=%s Category=%s%s",
        decision.score,
        decision.decision,
        candidate.category if candidate else "unknown",
        f" Target={decision.existing.memory_id}" if decision.existing else "",
    )
    return decision


def format_memory_auto_test(decision: MemoryAutoWriteDecision) -> str:
    candidate = decision.candidate
    lines = [
        "",
        "Hermes memory auto test",
        "────────────────────────────────────────",
        "Candidate:",
        f"  {candidate.summary if candidate else 'none'}",
        "",
        "Category:",
        f"  {candidate.category if candidate else 'unknown'}",
        "",
        "Tags:",
        f"  {', '.join(candidate.tags) if candidate else 'none'}",
        "",
        "Score:",
        f"  {decision.score}",
        "",
        "Decision:",
        f"  {decision.decision}",
        "",
        "Auto-write enabled:",
        f"  {'yes' if decision.enabled else 'no'}",
    ]
    if decision.existing:
        lines.extend(
            [
                "",
                "Existing Similar:",
                f"  {decision.existing.memory_id} {decision.existing.title}",
                "",
                "Similarity:",
                f"  {decision.existing.similarity}%",
            ]
        )
    else:
        lines.extend(["", "Existing Similar:", "  none"])
    lines.append("")
    return "\n".join(lines)
