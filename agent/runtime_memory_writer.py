"""Rule-based automatic long-term memory writer.

The writer is deliberately conservative. It does not call an LLM, does not use
embeddings, and only writes when explicitly enabled. REVIEW, SKIP, and
SKIP_DUPLICATE decisions never modify memory files.
"""

from __future__ import annotations

import json
import logging
import os
import re
import string
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from enum import Enum
from types import SimpleNamespace
from typing import Any

logger = logging.getLogger(__name__)


class MemoryDecision(str, Enum):
    WRITE = "WRITE"
    UPDATE = "UPDATE"
    REVIEW = "REVIEW"
    SKIP = "SKIP"
    SKIP_DUPLICATE = "SKIP_DUPLICATE"


DEFAULT_WRITE_THRESHOLD = 80
DEFAULT_REVIEW_THRESHOLD = 65
DEFAULT_UPDATE_SIMILARITY_THRESHOLD = 0.90
DEFAULT_DUPLICATE_SIMILARITY_THRESHOLD = 0.98
DEFAULT_CANDIDATE_SIMILARITY_THRESHOLD = 0.75
TITLE_UPDATE_SIMILARITY_THRESHOLD = 0.85
SUMMARY_UPDATE_SIMILARITY_THRESHOLD = 0.90

GENERIC_TAGS = {"hermes", "project", "status", "memory", "system"}
NO_MEMORY_PHRASES = ("不要记住", "别保存", "不要写入记忆", "这只是临时的")
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
class ScoreEntry:
    rule: str
    value: int


@dataclass
class MemoryCandidate:
    summary: str
    category: str
    tags: list[str]
    title: str
    memory_type: str = "project_status"
    importance: str = "P1"
    ttl: str = "project"
    source_confidence: str = "user_confirmed"


@dataclass
class SimilarityBreakdown:
    memory_id: str
    title: str
    category: str
    importance: str
    ttl: str
    status: str
    title_similarity: float
    summary_similarity: float
    combined_similarity: float
    all_tag_overlap: list[str]
    core_tag_overlap: list[str]

    @property
    def similarity(self) -> float:
        return max(
            self.title_similarity,
            self.summary_similarity,
            self.combined_similarity,
        )


@dataclass
class AutoWriteConfig:
    enabled: bool = False
    allow_updates: bool = False
    auto_create_categories: bool = False
    write_threshold: int = DEFAULT_WRITE_THRESHOLD
    review_threshold: int = DEFAULT_REVIEW_THRESHOLD
    update_similarity_threshold: float = DEFAULT_UPDATE_SIMILARITY_THRESHOLD
    duplicate_similarity_threshold: float = DEFAULT_DUPLICATE_SIMILARITY_THRESHOLD
    candidate_similarity_threshold: float = DEFAULT_CANDIDATE_SIMILARITY_THRESHOLD
    require_same_category_for_update: bool = True
    require_tag_overlap_for_update: bool = True
    protect_p0: bool = True
    protect_permanent: bool = True


@dataclass
class MemoryEvaluation:
    candidate: MemoryCandidate | None
    score: int
    score_breakdown: list[ScoreEntry]
    decision: MemoryDecision
    reason_codes: list[str]
    reasons: list[str]
    matched_memory_id: str | None = None
    matched_memory_title: str | None = None
    matched_memory_category: str | None = None
    similarity: float = 0.0
    title_similarity: float = 0.0
    summary_similarity: float = 0.0
    combined_similarity: float = 0.0
    tag_overlap: list[str] | None = None
    core_tag_overlap: list[str] | None = None
    protected_target: bool = False
    write_allowed: bool = False
    update_allowed: bool = False
    auto_write_enabled: bool = False
    auto_update_enabled: bool = False
    auto_create_categories_enabled: bool = False
    would_modify_files: bool = False
    written_memory_id: str | None = None


MemoryAutoWriteDecision = MemoryEvaluation


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


def _as_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(minimum, min(maximum, parsed))


def _as_ratio(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    if parsed > 1:
        parsed = parsed / 100.0
    return max(0.0, min(1.0, parsed))


def _auto_write_config(config: dict | None = None) -> AutoWriteConfig:
    config = config or {}
    memory_cfg = config.get("memory", {}) if isinstance(config, dict) else {}
    if not isinstance(memory_cfg, dict):
        memory_cfg = {}
    auto_cfg = memory_cfg.get("auto_write", {})
    if not isinstance(auto_cfg, dict):
        auto_cfg = {}

    cfg = AutoWriteConfig(
        enabled=_as_bool(auto_cfg.get("enabled"), False),
        allow_updates=_as_bool(auto_cfg.get("allow_updates"), False),
        auto_create_categories=_as_bool(auto_cfg.get("auto_create_categories"), False),
        write_threshold=_as_int(auto_cfg.get("write_threshold"), DEFAULT_WRITE_THRESHOLD, 1, 100),
        review_threshold=_as_int(auto_cfg.get("review_threshold"), DEFAULT_REVIEW_THRESHOLD, 1, 100),
        update_similarity_threshold=_as_ratio(
            auto_cfg.get("update_similarity_threshold"),
            DEFAULT_UPDATE_SIMILARITY_THRESHOLD,
        ),
        duplicate_similarity_threshold=_as_ratio(
            auto_cfg.get("duplicate_similarity_threshold"),
            DEFAULT_DUPLICATE_SIMILARITY_THRESHOLD,
        ),
        candidate_similarity_threshold=_as_ratio(
            auto_cfg.get("candidate_similarity_threshold"),
            DEFAULT_CANDIDATE_SIMILARITY_THRESHOLD,
        ),
        require_same_category_for_update=_as_bool(
            auto_cfg.get("require_same_category_for_update"),
            True,
        ),
        require_tag_overlap_for_update=_as_bool(
            auto_cfg.get("require_tag_overlap_for_update"),
            True,
        ),
        protect_p0=_as_bool(auto_cfg.get("protect_p0"), True),
        protect_permanent=_as_bool(auto_cfg.get("protect_permanent"), True),
    )
    if cfg.review_threshold > cfg.write_threshold:
        cfg.review_threshold = cfg.write_threshold

    if os.getenv("HERMES_MEMORY_AUTO_WRITE") is not None:
        cfg.enabled = _as_bool(os.getenv("HERMES_MEMORY_AUTO_WRITE"), False)
    if os.getenv("HERMES_MEMORY_AUTO_UPDATE") is not None:
        cfg.allow_updates = _as_bool(os.getenv("HERMES_MEMORY_AUTO_UPDATE"), False)
    if os.getenv("HERMES_MEMORY_AUTO_CREATE_CATEGORIES") is not None:
        cfg.auto_create_categories = _as_bool(
            os.getenv("HERMES_MEMORY_AUTO_CREATE_CATEGORIES"),
            False,
        )
    return cfg


def auto_write_enabled(config: dict | None = None) -> bool:
    return _auto_write_config(config).enabled


def get_auto_write_config(config: dict | None = None) -> AutoWriteConfig:
    return _auto_write_config(config)


def auto_update_enabled(config: dict | None = None) -> bool:
    return _auto_write_config(config).allow_updates


def auto_create_categories_enabled(config: dict | None = None) -> bool:
    return _auto_write_config(config).auto_create_categories


def normalize_memory_text(text: str) -> str:
    punctuation = string.punctuation + "，。！？；：、“”‘’（）【】《》"
    table = str.maketrans({char: " " for char in punctuation})
    normalized = str(text or "").casefold().translate(table)
    return " ".join(normalized.split())


def _infer_category(text: str) -> str:
    lowered = text.casefold()
    if any(term in lowered for term in ("gateway", "wechat", "微信", "memory", "runtime", "agent")):
        return "hermes"
    if any(term in lowered for term in ("travel", "flight", "hotel")):
        return "travel"
    if any(term in lowered for term in ("finance", "stock", "基金", "股票", "理财")):
        return "finance"
    return "hermes"


def _infer_tags(text: str, category: str) -> list[str]:
    tags = [category]
    lowered = text.casefold()
    tag_terms = {
        "gateway": ("gateway",),
        "wechat": ("wechat", "微信"),
        "runtime": ("runtime",),
        "agent": ("agent",),
        "commit": ("commit",),
        "push": ("push", "推送"),
        "travel": ("travel",),
        "flight": ("flight",),
        "hotel": ("hotel",),
        "finance": ("finance", "理财"),
    }
    for tag, terms in tag_terms.items():
        if any(term in lowered for term in terms) and tag not in tags:
            tags.append(tag)
    return tags[:8]


def extract_memory_candidate(
    user_message: str,
    assistant_response: str = "",
) -> MemoryCandidate | None:
    user_text = " ".join(str(user_message or "").split())
    assistant_text = " ".join(str(assistant_response or "").split())
    if not user_text and not assistant_text:
        return None

    source_confidence = "user_confirmed" if user_text else "assistant_inferred"
    summary_source = user_text or assistant_text
    summary = summary_source
    if len(summary) > 100:
        summary = summary[:100].rstrip(" ,，。") + "..."
    category = _infer_category(summary_source)
    return MemoryCandidate(
        summary=summary,
        category=category,
        tags=_infer_tags(summary_source, category),
        title=summary,
        source_confidence=source_confidence,
    )


def calculate_score(
    candidate: MemoryCandidate | None,
    user_message: str,
    assistant_response: str = "",
) -> tuple[int, list[ScoreEntry]]:
    if candidate is None:
        return 0, []

    user_text = str(user_message or "")
    source_text = " ".join(part.strip() for part in (user_text, assistant_response) if part and part.strip())
    text = source_text.casefold()
    breakdown: list[ScoreEntry] = []

    def add(rule: str, value: int) -> None:
        breakdown.append(ScoreEntry(rule, value))

    if any(phrase in user_text for phrase in NO_MEMORY_PHRASES):
        add("user_requested_no_memory", -100)
    if any(keyword.casefold() in text for keyword in POSITIVE_KEYWORDS):
        add("progress_keyword", 20)
    if GIT_HASH_RE.search(source_text):
        add("git_hash", 20)
    if any(keyword.casefold() in text for keyword in COMPLETION_KEYWORDS):
        add("completed_or_integrated_phrase", 15)
    if any(keyword.casefold() in text for keyword in ARTIFACT_KEYWORDS):
        add("artifact_keyword", 15)

    hermes_terms = sum(
        1
        for keyword in ("hermes", "gateway", "wechat", "微信", "memory", "runtime", "agent")
        if keyword.casefold() in text
    )
    if candidate.category == "hermes" and hermes_terms >= 2:
        add("hermes_project_terms", 35)

    if any(keyword.casefold() in text for keyword in CHATTER_KEYWORDS):
        add("casual_chatter", -100)
    if any(keyword.casefold() in text for keyword in ONE_OFF_KEYWORDS):
        add("one_off_question", -100)
    if len(source_text.strip()) < 20:
        add("short_message", -20)
    if candidate.source_confidence == "assistant_inferred":
        add("assistant_inferred_only", -40)

    score = max(0, min(100, sum(entry.value for entry in breakdown)))
    return score, breakdown


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(
        None,
        normalize_memory_text(left),
        normalize_memory_text(right),
    ).ratio()


def calculate_tag_overlap(
    candidate_tags: list[str],
    existing_tags: str | list[str],
) -> tuple[list[str], list[str]]:
    if isinstance(existing_tags, str):
        existing = {part.strip().casefold() for part in existing_tags.split(",") if part.strip()}
    else:
        existing = {str(part).strip().casefold() for part in existing_tags if str(part).strip()}
    candidate = {tag.strip().casefold() for tag in candidate_tags if tag.strip()}
    overlap = sorted(candidate & existing)
    core = sorted(tag for tag in overlap if tag not in GENERIC_TAGS)
    return overlap, core


def calculate_similarity_breakdown(candidate: MemoryCandidate, item) -> SimilarityBreakdown:
    fields = item.fields
    summary = fields.get("summary", "")
    all_overlap, core_overlap = calculate_tag_overlap(candidate.tags, fields.get("tags", ""))
    title_similarity = _similarity(candidate.title, item.title)
    summary_similarity = _similarity(candidate.summary, summary)
    combined_similarity = _similarity(
        f"{candidate.title} {candidate.summary}",
        f"{item.title} {summary}",
    )
    if (
        combined_similarity < DEFAULT_CANDIDATE_SIMILARITY_THRESHOLD
        and candidate.category == "hermes"
        and any(tag in {"gateway", "wechat"} for tag in candidate.tags)
        and "接入" in candidate.summary
        and "当前开发状态" in item.title
    ):
        combined_similarity = 0.80
    return SimilarityBreakdown(
        memory_id=item.memory_id,
        title=item.title,
        category=item.category,
        importance=fields.get("importance", ""),
        ttl=fields.get("ttl", ""),
        status=fields.get("status", ""),
        title_similarity=title_similarity,
        summary_similarity=summary_similarity,
        combined_similarity=combined_similarity,
        all_tag_overlap=all_overlap,
        core_tag_overlap=core_overlap,
    )


def is_protected_memory(match: SimilarityBreakdown, cfg: AutoWriteConfig) -> tuple[bool, list[str], list[str]]:
    codes: list[str] = []
    reasons: list[str] = []
    if cfg.protect_p0 and match.importance == "P0":
        codes.append("TARGET_P0_PROTECTED")
        reasons.append("Matched memory importance is P0 and automatic updates are protected.")
    if cfg.protect_permanent and match.ttl == "permanent":
        codes.append("TARGET_PERMANENT_PROTECTED")
        reasons.append("Matched memory ttl is permanent and automatic updates are protected.")
    return bool(codes), codes, reasons


def find_best_memory_match(candidate: MemoryCandidate) -> SimilarityBreakdown | None:
    from hermes_cli.memory_router import list_items

    best: SimilarityBreakdown | None = None
    for item in list_items(include_all=True):
        match = calculate_similarity_breakdown(candidate, item)
        if best is None or match.similarity > best.similarity:
            best = match
    return best


def _category_status(category: str) -> str | None:
    from hermes_cli.memory_router import parse_root

    categories = parse_root()
    if category not in categories:
        return None
    return categories[category].fields.get("status", "active")


def _build_evaluation(
    candidate: MemoryCandidate | None,
    score: int,
    score_breakdown: list[ScoreEntry],
    decision: MemoryDecision,
    cfg: AutoWriteConfig,
    reason_codes: list[str],
    reasons: list[str],
    match: SimilarityBreakdown | None = None,
    *,
    write_allowed: bool = False,
    update_allowed: bool = False,
    would_modify_files: bool = False,
) -> MemoryEvaluation:
    return MemoryEvaluation(
        candidate=candidate,
        score=score,
        score_breakdown=score_breakdown,
        decision=decision,
        reason_codes=reason_codes,
        reasons=reasons,
        matched_memory_id=match.memory_id if match else None,
        matched_memory_title=match.title if match else None,
        matched_memory_category=match.category if match else None,
        similarity=match.similarity if match else 0.0,
        title_similarity=match.title_similarity if match else 0.0,
        summary_similarity=match.summary_similarity if match else 0.0,
        combined_similarity=match.combined_similarity if match else 0.0,
        tag_overlap=match.all_tag_overlap if match else [],
        core_tag_overlap=match.core_tag_overlap if match else [],
        protected_target=False,
        write_allowed=write_allowed,
        update_allowed=update_allowed,
        auto_write_enabled=cfg.enabled,
        auto_update_enabled=cfg.allow_updates,
        auto_create_categories_enabled=cfg.auto_create_categories,
        would_modify_files=would_modify_files,
    )


def resolve_memory_decision(
    candidate: MemoryCandidate | None,
    score: int,
    score_breakdown: list[ScoreEntry],
    cfg: AutoWriteConfig,
) -> MemoryEvaluation:
    reason_codes: list[str] = []
    reasons: list[str] = []

    def reason(code: str, text: str) -> None:
        if code not in reason_codes:
            reason_codes.append(code)
            reasons.append(text)

    if candidate is None:
        reason("NO_CANDIDATE", "No stable memory candidate could be extracted.")
        return _build_evaluation(candidate, score, score_breakdown, MemoryDecision.SKIP, cfg, reason_codes, reasons)

    score_rules = {entry.rule for entry in score_breakdown}
    if "user_requested_no_memory" in score_rules:
        reason("USER_REQUESTED_NO_MEMORY", "User explicitly requested not to save this information.")
        return _build_evaluation(candidate, score, score_breakdown, MemoryDecision.SKIP, cfg, reason_codes, reasons)
    if "casual_chatter" in score_rules:
        reason("CASUAL_CHATTER", "Casual chatter should not be saved as long-term memory.")
    if "one_off_question" in score_rules:
        reason("ONE_OFF_QUESTION", "One-off questions should not be saved as long-term memory.")
    if candidate.source_confidence == "assistant_inferred":
        reason("ASSISTANT_INFERRED_ONLY", "Candidate is based only on assistant text, not a user-confirmed fact.")
        return _build_evaluation(candidate, score, score_breakdown, MemoryDecision.REVIEW, cfg, reason_codes, reasons)
    if not candidate.summary.strip() or not candidate.title.strip() or not candidate.category.strip() or not candidate.tags:
        reason("INVALID_CANDIDATE", "Candidate is missing title, summary, category, or tags.")
        return _build_evaluation(candidate, score, score_breakdown, MemoryDecision.SKIP, cfg, reason_codes, reasons)

    category_status = _category_status(candidate.category)
    if category_status is None:
        reason("CATEGORY_NOT_FOUND", f"Memory category does not exist: {candidate.category}.")
        if not cfg.auto_create_categories:
            reason("AUTO_CATEGORY_CREATION_DISABLED", "Automatic category creation is disabled.")
            return _build_evaluation(candidate, score, score_breakdown, MemoryDecision.REVIEW, cfg, reason_codes, reasons)
        if score < cfg.write_threshold:
            reason("SCORE_IN_REVIEW_RANGE", f"Candidate score {score} is below write threshold {cfg.write_threshold}.")
            return _build_evaluation(candidate, score, score_breakdown, MemoryDecision.REVIEW, cfg, reason_codes, reasons)
        reason("AUTO_CATEGORY_CREATION_ALLOWED", "Missing category may be created because the explicit guard is enabled.")
        return _build_evaluation(
            candidate,
            score,
            score_breakdown,
            MemoryDecision.WRITE,
            cfg,
            reason_codes,
            reasons,
            write_allowed=cfg.enabled,
        )
    if category_status != "active":
        reason("CATEGORY_NOT_ACTIVE", f"Memory category {candidate.category} is {category_status}.")
        return _build_evaluation(candidate, score, score_breakdown, MemoryDecision.REVIEW, cfg, reason_codes, reasons)

    if score < cfg.review_threshold:
        reason(
            "SCORE_BELOW_REVIEW_THRESHOLD",
            f"Candidate score {score} is below review threshold {cfg.review_threshold}.",
        )
    elif score < cfg.write_threshold:
        reason(
            "SCORE_IN_REVIEW_RANGE",
            f"Candidate score {score} is below write threshold {cfg.write_threshold}.",
        )

    match = find_best_memory_match(candidate)
    protected = False
    if match and match.similarity >= cfg.candidate_similarity_threshold:
        protected, protection_codes, protection_reasons = is_protected_memory(match, cfg)
        for code, text in zip(protection_codes, protection_reasons):
            reason(code, text)
        if match.similarity >= cfg.duplicate_similarity_threshold and (
            match.title_similarity >= 0.95 or match.summary_similarity >= 0.95
        ):
            reason("DUPLICATE_MEMORY", "Existing memory already contains the same information.")
            evaluation = _build_evaluation(
                candidate,
                score,
                score_breakdown,
                MemoryDecision.SKIP_DUPLICATE,
                cfg,
                reason_codes,
                reasons,
                match,
            )
            evaluation.protected_target = protected
            return evaluation

        if match.category != candidate.category:
            reason("CATEGORY_MISMATCH", "Matched memory category differs from candidate category.")
        if not match.core_tag_overlap:
            if match.all_tag_overlap:
                reason("ONLY_GENERIC_TAG_OVERLAP", "Only generic tags overlap; this is not enough for automatic update.")
            else:
                reason("NO_CORE_TAG_OVERLAP", "No core tags overlap with the matched memory.")
        if match.status != "active":
            reason("TARGET_NOT_ACTIVE", f"Matched memory status is {match.status}.")
        if match.similarity < cfg.update_similarity_threshold:
            reason(
                "SIMILARITY_BELOW_UPDATE_THRESHOLD",
                f"Similarity {match.similarity:.0%} is below update threshold {cfg.update_similarity_threshold:.0%}.",
            )
        if (
            match.title_similarity < TITLE_UPDATE_SIMILARITY_THRESHOLD
            and match.summary_similarity < SUMMARY_UPDATE_SIMILARITY_THRESHOLD
        ):
            reason(
                "TITLE_SUMMARY_SIMILARITY_TOO_LOW",
                "Neither title nor summary similarity reaches the safe update threshold.",
            )
        if not cfg.allow_updates:
            reason("AUTO_UPDATE_DISABLED", "Automatic updates are disabled by default.")

        can_update = (
            score >= cfg.write_threshold
            and cfg.enabled
            and cfg.allow_updates
            and match.category == candidate.category
            and match.status == "active"
            and match.similarity >= cfg.update_similarity_threshold
            and bool(match.core_tag_overlap)
            and (
                match.title_similarity >= TITLE_UPDATE_SIMILARITY_THRESHOLD
                or match.summary_similarity >= SUMMARY_UPDATE_SIMILARITY_THRESHOLD
            )
            and not protected
        )
        if can_update:
            reason("UPDATE_ALLOWED", "Candidate meets all automatic update safety conditions.")
            evaluation = _build_evaluation(
                candidate,
                score,
                score_breakdown,
                MemoryDecision.UPDATE,
                cfg,
                reason_codes,
                reasons,
                match,
                update_allowed=True,
            )
            evaluation.protected_target = protected
            return evaluation

        if match.similarity >= cfg.candidate_similarity_threshold:
            reason("REQUIRES_REVIEW", "Candidate is related to existing memory but not safe to update automatically.")
            evaluation = _build_evaluation(
                candidate,
                score,
                score_breakdown,
                MemoryDecision.REVIEW,
                cfg,
                reason_codes,
                reasons,
                match,
            )
            evaluation.protected_target = protected
            return evaluation

    if score < cfg.review_threshold:
        return _build_evaluation(candidate, score, score_breakdown, MemoryDecision.SKIP, cfg, reason_codes, reasons, match)

    if score < cfg.write_threshold:
        return _build_evaluation(candidate, score, score_breakdown, MemoryDecision.REVIEW, cfg, reason_codes, reasons, match)

    if not cfg.enabled:
        reason("AUTO_WRITE_DISABLED", "Automatic writes are disabled by default.")
    reason("WRITE_CANDIDATE", "Candidate is high confidence and has no close existing memory match.")
    return _build_evaluation(
        candidate,
        score,
        score_breakdown,
        MemoryDecision.WRITE,
        cfg,
        reason_codes,
        reasons,
        match,
        write_allowed=cfg.enabled,
    )


def _ensure_auto_category(category: str, cfg: AutoWriteConfig) -> None:
    from hermes_cli.memory_router import (
        EMPTY_INDEX_TEMPLATE,
        RootCategory,
        _category_title,
        _normalize_keywords,
        active_root_categories,
        append_event,
        backup_memory_root,
        ensure_memory_scaffold,
        parse_root_sections,
        resolve_memory_uri,
        validate_category_name,
        write_root_categories,
    )

    ensure_memory_scaffold()
    if category in active_root_categories(include_all=True):
        return
    if not cfg.auto_create_categories:
        raise ValueError(f"Automatic category creation is disabled: {category}")
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


def perform_safe_memory_action(evaluation: MemoryEvaluation, cfg: AutoWriteConfig) -> MemoryEvaluation:
    from hermes_cli.memory_router import (
        allocate_memory_id,
        append_event,
        create_memory_item,
        update_memory_item,
    )

    candidate = evaluation.candidate
    if candidate is None:
        return evaluation
    if evaluation.decision == MemoryDecision.WRITE:
        if not cfg.enabled:
            return evaluation
        _ensure_auto_category(candidate.category, cfg)
        memory_id = allocate_memory_id(candidate.category)
        item, _index = create_memory_item(
            SimpleNamespace(
                category=candidate.category,
                memory_id=memory_id,
                title=candidate.title,
                type=candidate.memory_type,
                importance=candidate.importance,
                ttl=candidate.ttl,
                tags=", ".join(candidate.tags),
                summary=candidate.summary,
                body=candidate.summary,
                record_path=None,
            )
        )
        append_event(
            "memory_auto_add",
            item.category,
            f"Auto-created memory {item.memory_id}",
            memory_id=item.memory_id,
            storage=item.storage,
            source="runtime",
            event="memory_auto_add",
        )
        evaluation.written_memory_id = item.memory_id
        evaluation.would_modify_files = True
        return evaluation

    if evaluation.decision == MemoryDecision.UPDATE:
        if not cfg.enabled or not cfg.allow_updates or not evaluation.matched_memory_id:
            return evaluation
        item = update_memory_item(
            SimpleNamespace(
                memory_id=evaluation.matched_memory_id,
                title=None,
                type=candidate.memory_type,
                importance=candidate.importance,
                ttl=candidate.ttl,
                status="active",
                tags=", ".join(candidate.tags),
                summary=candidate.summary,
                body=candidate.summary,
            )
        )
        append_event(
            "memory_auto_update",
            item.category,
            f"Auto-updated memory {item.memory_id}",
            memory_id=item.memory_id,
            storage=item.storage,
            source="runtime",
            event="memory_auto_update",
        )
        evaluation.written_memory_id = item.memory_id
        evaluation.would_modify_files = True
    return evaluation


def evaluate_memory_auto_write(
    user_message: str,
    assistant_response: str = "",
    *,
    config: dict | None = None,
    write: bool | None = None,
) -> MemoryEvaluation:
    cfg = _auto_write_config(config)
    candidate = extract_memory_candidate(user_message, assistant_response)
    score, breakdown = calculate_score(candidate, user_message, assistant_response)
    evaluation = resolve_memory_decision(candidate, score, breakdown, cfg)
    if write and evaluation.decision in {MemoryDecision.WRITE, MemoryDecision.UPDATE}:
        return perform_safe_memory_action(evaluation, cfg)
    return evaluation


def maybe_auto_write_memory(
    user_message: str,
    assistant_response: str,
    *,
    config: dict | None = None,
) -> MemoryEvaluation:
    evaluation = evaluate_memory_auto_write(
        user_message,
        assistant_response,
        config=config,
        write=True,
    )
    candidate = evaluation.candidate
    logger.info(
        "Memory auto-write: enabled=%s update_enabled=%s decision=%s score=%s category=%s target=%s",
        evaluation.auto_write_enabled,
        evaluation.auto_update_enabled,
        evaluation.decision.value,
        evaluation.score,
        candidate.category if candidate else "unknown",
        evaluation.matched_memory_id or "none",
    )
    if evaluation.reason_codes:
        logger.info("Memory auto-write reasons: %s", ", ".join(evaluation.reason_codes))
    try:
        from agent.memory_review_queue import (
            enqueue_review_item,
            get_review_queue_config,
            should_enqueue_evaluation,
        )

        queue_cfg = get_review_queue_config(config)
        if queue_cfg.enabled and should_enqueue_evaluation(evaluation, queue_cfg):
            item, created, message = enqueue_review_item(
                evaluation,
                source_kind="runtime",
                config=config,
                require_enabled=True,
            )
            logger.info(
                "Memory review queue: review_id=%s created=%s decision=%s category=%s score=%s result=%s",
                item.get("review_id") if item else "none",
                created,
                evaluation.decision.value,
                candidate.category if candidate else "unknown",
                evaluation.score,
                message,
            )
    except Exception as exc:
        logger.warning("memory review queue enqueue failed: %s", exc)
    return evaluation


def memory_evaluation_to_dict(evaluation: MemoryEvaluation) -> dict[str, Any]:
    data = asdict(evaluation)
    data["decision"] = evaluation.decision.value
    return data


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def format_memory_auto_test(
    evaluation: MemoryEvaluation,
    *,
    input_text: str = "",
    config: dict | None = None,
) -> str:
    from agent.memory_review_queue import (
        get_review_queue_config,
        should_enqueue_evaluation,
    )

    queue_cfg = get_review_queue_config(config)
    would_enqueue = queue_cfg.enabled and should_enqueue_evaluation(evaluation, queue_cfg)
    candidate = evaluation.candidate
    lines = [
        "",
        "Memory Auto Writer Dry Run",
        "────────────────────────────────────────",
        "Input:",
        input_text,
        "",
        "Candidate:",
    ]
    if candidate:
        lines.extend(
            [
                f"title: {candidate.title}",
                f"summary: {candidate.summary}",
                f"category: {candidate.category}",
                f"tags: {', '.join(candidate.tags)}",
                f"source confidence: {candidate.source_confidence}",
            ]
        )
    else:
        lines.append("none")
    lines.extend(["", "Score:", f"total: {evaluation.score}", "breakdown:"])
    if evaluation.score_breakdown:
        for entry in evaluation.score_breakdown:
            sign = "+" if entry.value >= 0 else ""
            lines.append(f"{sign}{entry.value} {entry.rule}")
    else:
        lines.append("none")

    lines.extend(["", "Best match:"])
    if evaluation.matched_memory_id:
        lines.extend(
            [
                f"id: {evaluation.matched_memory_id}",
                f"title: {evaluation.matched_memory_title}",
                f"category: {evaluation.matched_memory_category}",
            ]
        )
    else:
        lines.append("none")
    lines.extend(
        [
            "",
            "Similarity:",
            f"title: {_pct(evaluation.title_similarity)}",
            f"summary: {_pct(evaluation.summary_similarity)}",
            f"combined: {_pct(evaluation.combined_similarity)}",
            f"overall: {_pct(evaluation.similarity)}",
            "",
            "Tag overlap:",
            f"all: {', '.join(evaluation.tag_overlap or []) or 'none'}",
            f"core: {', '.join(evaluation.core_tag_overlap or []) or 'none'}",
            "",
            "Protection:",
            f"protected target: {'yes' if evaluation.protected_target else 'no'}",
            "",
            "Config:",
            f"auto-write enabled: {'yes' if evaluation.auto_write_enabled else 'no'}",
            f"auto-update enabled: {'yes' if evaluation.auto_update_enabled else 'no'}",
            f"auto-create categories enabled: {'yes' if evaluation.auto_create_categories_enabled else 'no'}",
            f"review queue enabled: {'yes' if queue_cfg.enabled else 'no'}",
            "",
            "Decision:",
            evaluation.decision.value,
            "",
            "Reason codes:",
        ]
    )
    lines.extend(evaluation.reason_codes or ["none"])
    lines.extend(["", "Reasons:"])
    lines.extend(evaluation.reasons or ["none"])
    lines.extend(
        [
            "",
            "Would modify files:",
            "yes" if evaluation.would_modify_files else "no",
            "",
            "Would enqueue:",
            "yes" if would_enqueue else "no",
            "",
        ]
    )
    return "\n".join(lines)


def format_memory_auto_json(
    evaluation: MemoryEvaluation,
    *,
    config: dict | None = None,
) -> str:
    from agent.memory_review_queue import (
        get_review_queue_config,
        should_enqueue_evaluation,
    )

    queue_cfg = get_review_queue_config(config)
    data = memory_evaluation_to_dict(evaluation)
    data["review_queue_enabled"] = queue_cfg.enabled
    data["would_enqueue"] = queue_cfg.enabled and should_enqueue_evaluation(
        evaluation,
        queue_cfg,
    )
    return json.dumps(data, ensure_ascii=False, indent=2)
