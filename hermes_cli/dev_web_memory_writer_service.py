"""Dev Web API Memory Writer Dry-Run Service.

Pure-computation preview service for Memory WRITE, UPDATE, and ARCHIVE
operations. This service ONLY reads existing Memory data and returns a
preview of what *would* happen. No files are modified, no events are
appended, no Review Queue items are enqueued.

Safety guarantees enforced at the service layer:
- Never calls create_memory_item, update_memory_item, append_event,
  write_root_categories, write_index_items, backup_file,
  backup_memory_root, ensure_memory_scaffold, _ensure_auto_category,
  perform_safe_memory_action, maybe_auto_write_memory,
  enqueue_review_item, or any other write function.
- Never creates directories, lock files, snapshots, or Review items.
- All responses have dryRun=True, readOnly=True, writeEnabled=False,
  executeAvailable=False, sideEffects=False.

IMPORTANT: This service does NOT use find_best_memory_match(),
resolve_memory_decision(), _category_status(), or get_auto_write_config()
because those functions use get_hermes_home() defaults that resolve to
the production home. Instead, all read operations explicitly pass
home=self._home and decision logic is reimplemented locally.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from agent.runtime_memory_writer import (
    AutoWriteConfig,
    MemoryCandidate,
    MemoryDecision,
    ScoreEntry,
    SimilarityBreakdown,
    calculate_score,
    calculate_similarity_breakdown,
    calculate_tag_overlap,
    is_protected_memory,
    normalize_memory_text,
)
from hermes_cli.memory_router import (
    CATEGORY_NAME_RE,
    MEMORY_ID_RE,
    VALID_IMPORTANCE,
    VALID_TTL,
    find_item,
    list_items,
    parse_root,
)

logger = logging.getLogger(__name__)

# ── Truncation limits ──

_MAX_TITLE_PREVIEW = 120
_MAX_SUMMARY_PREVIEW = 300
_MAX_BLOCKED_REASON = 200
_MAX_CHECK_MESSAGE = 200
_MAX_EFFECT_DESCRIPTION = 200
_MAX_WARNING = 200
_MAX_PROTECTION_REASON = 200
_MAX_ARCHIVE_REASON = 500
_MAX_TAG_LENGTH = 50
_MAX_TAGS_COUNT = 20
_MAX_QUERY_LENGTH = 2000
_MAX_CANDIDATE_SUMMARY = 1000
_MAX_CANDIDATE_TITLE = 120
_MAX_CANDIDATE_TYPE = 50
_MAX_CATEGORY_LENGTH = 100

# ── Threshold defaults (must match AutoWriteConfig defaults) ──

_DEFAULT_WRITE_THRESHOLD = 80
_DEFAULT_REVIEW_THRESHOLD = 65
_DEFAULT_UPDATE_SIMILARITY_THRESHOLD = 0.90
_DEFAULT_DUPLICATE_SIMILARITY_THRESHOLD = 0.98
_DEFAULT_CANDIDATE_SIMILARITY_THRESHOLD = 0.75
_TITLE_UPDATE_SIMILARITY_THRESHOLD = 0.85
_SUMMARY_UPDATE_SIMILARITY_THRESHOLD = 0.90

# ── Path redaction ──

_LOCAL_PATH_RE = re.compile(
    r"(?:"
    r"/Users/[^\s,;)\]}'\"]+"
    r"|/home/[^\s,;)\]}'\"]+"
    r"|C:\\[^\s,;)\]}'\"]+"
    r"|file://[^\s,;)\]}'\"]+"
    r")"
)


def redact_local_paths(text: str) -> str:
    """Redact local filesystem paths and file:// URIs from text."""
    if not text:
        return text
    return _LOCAL_PATH_RE.sub(
        lambda m: (
            "[file-uri-redacted]" if m.group(0).startswith("file://")
            else "[local-path]"
        ),
        text,
    )


def _truncate(text: str, limit: int) -> str:
    """Truncate text to limit with ellipsis indicator."""
    if not text or len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


# ── Exceptions ──


class MemoryWriterDryRunUnavailableError(Exception):
    """Memory system not available for dry-run."""


class MemoryWriterTargetNotFoundError(Exception):
    """Target memory item not found."""


class MemoryWriterInvalidIdError(Exception):
    """Invalid memory ID format."""


class MemoryWriterInvalidRequestError(Exception):
    """Invalid dry-run request payload."""


# ── Local match helper ──


def _find_best_match_local(
    candidate: MemoryCandidate, home: Path
) -> SimilarityBreakdown | None:
    """Find best matching memory item using explicit home path.

    This replaces find_best_memory_match() which uses default get_hermes_home().
    """
    all_items = list_items(home=home, include_all=True)
    if not all_items:
        return None
    best: SimilarityBreakdown | None = None
    for item in all_items:
        breakdown = calculate_similarity_breakdown(candidate, item)
        if best is None or breakdown.similarity > best.similarity:
            best = breakdown
    return best


# ── Service ──


class DevMemoryWriterDryRunService:
    """Read-only dry-run preview for Memory Writer operations.

    Only reads existing Memory data and produces decision previews.
    Never modifies any file or enqueues any Review item.
    """

    def __init__(self, hermes_home: Path) -> None:
        self._home = hermes_home

    def is_available(self) -> bool:
        """Check if the Memory system is available."""
        try:
            root = self._home / "MEMORY.md"
            return root.exists()
        except Exception:
            return False

    # ── WRITE Dry-Run ──

    def dry_run_write(
        self,
        *,
        query: str,
        candidate: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Preview a WRITE operation. No side effects."""
        self._ensure_available()
        opts = options or {}

        # Validate inputs
        self._validate_write_request(query, candidate)

        # Read current state with explicit home
        root_categories = parse_root(home=self._home)

        # Build MemoryCandidate
        mc = self._build_candidate(candidate, query)

        # Calculate score (pure computation)
        score, score_breakdown = calculate_score(mc, query)

        # Get config with defaults (no file I/O)
        cfg = AutoWriteConfig()

        # Find best match using local implementation with explicit home
        best_match = _find_best_match_local(mc, self._home)

        # Determine category status locally
        cat_status = None
        if mc.category in root_categories:
            cat_data = root_categories[mc.category]
            cat_status = cat_data.fields.get("status", "active") if hasattr(cat_data, "fields") else "active"

        # Resolve decision locally (instead of using resolve_memory_decision
        # which calls find_best_memory_match without home parameter)
        decision, decision_reasons = self._resolve_write_decision(
            mc, score, score_breakdown, cfg, best_match, cat_status
        )

        # Build checks
        checks = self._build_write_checks(mc, root_categories, cat_status)

        # Build effects
        effects, no_effects = self._build_write_effects(
            decision, mc, root_categories, cfg
        )

        # Build similarity preview
        similarity = self._build_similarity_preview(best_match)

        # Determine if review would be enqueued
        would_enqueue_review = decision == MemoryDecision.REVIEW

        return self._build_response(
            operation="WRITE",
            decision=decision,
            decision_reasons=decision_reasons,
            candidate=mc,
            target=None,
            checks=checks,
            effects=effects,
            no_effects=no_effects,
            similarity=similarity,
            score=score,
            score_breakdown=score_breakdown,
            cfg=cfg,
            would_enqueue_review=would_enqueue_review,
            include_similarity=opts.get("includeSimilarity", True),
            include_effects=opts.get("includeEffects", True),
        )

    # ── UPDATE Dry-Run ──

    def dry_run_update(
        self,
        memory_id: str,
        *,
        candidate: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Preview an UPDATE operation. No side effects."""
        self._ensure_available()
        opts = options or {}

        # Validate memory ID
        self._validate_memory_id(memory_id)

        # Find target using explicit home
        target = find_item(memory_id, home=self._home)
        if target is None:
            raise MemoryWriterTargetNotFoundError(
                f"Memory item '{memory_id}' not found."
            )

        # Check archived
        target_status = target.fields.get("status", "active")
        if target_status == "archived":
            return self._build_blocked_response(
                operation="UPDATE",
                memory_id=memory_id,
                target=target,
                blocked_reason="Target memory is archived and cannot be updated.",
                decision_override="SKIP",
                check_code="MEMORY_ALREADY_ARCHIVED",
            )

        # Protection checks (independent, not relying on core archive path)
        cfg = AutoWriteConfig()
        protection = self._check_target_protection(target, cfg)
        if protection:
            return self._build_blocked_response(
                operation="UPDATE",
                memory_id=memory_id,
                target=target,
                blocked_reason=protection["reason"],
                decision_override="SKIP",
                check_code=protection["code"],
            )

        # Validate candidate
        self._validate_update_candidate(candidate)

        # Build candidate for similarity
        mc = self._build_update_candidate(target, candidate)

        # Calculate score (pure computation)
        query = candidate.get("summary", "")
        score, score_breakdown = calculate_score(mc, query)

        # Find best match (for similarity display)
        best_match = _find_best_match_local(mc, self._home)

        # Resolve decision locally
        decision, decision_reasons = self._resolve_update_decision(
            mc, score, score_breakdown, cfg, best_match, target
        )

        # Build diff
        diff = self._build_update_diff(target, candidate)

        # Build checks
        checks = self._build_update_checks(target, candidate)

        # Build effects
        effects, no_effects = self._build_update_effects(decision, target)

        # Build similarity
        similarity = self._build_similarity_preview(best_match)

        return self._build_response(
            operation="UPDATE",
            decision=decision,
            decision_reasons=decision_reasons,
            candidate=mc,
            target=target,
            checks=checks,
            effects=effects,
            no_effects=no_effects,
            similarity=similarity,
            score=score,
            score_breakdown=score_breakdown,
            cfg=cfg,
            diff=diff,
            include_similarity=opts.get("includeSimilarity", True),
            include_effects=opts.get("includeEffects", True),
            include_diff=opts.get("includeDiff", True),
        )

    # ── ARCHIVE Dry-Run ──

    def dry_run_archive(
        self,
        memory_id: str,
        *,
        reason: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Preview an ARCHIVE operation. No side effects."""
        self._ensure_available()
        opts = options or {}

        # Validate memory ID
        self._validate_memory_id(memory_id)

        # Validate reason
        if reason is not None:
            reason = _truncate(reason, _MAX_ARCHIVE_REASON)

        # Find target using explicit home
        target = find_item(memory_id, home=self._home)
        if target is None:
            raise MemoryWriterTargetNotFoundError(
                f"Memory item '{memory_id}' not found."
            )

        # Check already archived
        target_status = target.fields.get("status", "active")
        if target_status == "archived":
            return self._build_blocked_response(
                operation="ARCHIVE",
                memory_id=memory_id,
                target=target,
                blocked_reason="Target memory is already archived.",
                decision_override="SKIP",
                check_code="MEMORY_ALREADY_ARCHIVED",
            )

        # Independent P0/permanent protection
        cfg = AutoWriteConfig()
        protection = self._check_target_protection(target, cfg)
        if protection:
            return self._build_blocked_response(
                operation="ARCHIVE",
                memory_id=memory_id,
                target=target,
                blocked_reason=protection["reason"],
                decision_override="SKIP",
                check_code=protection["code"],
            )

        # Build checks
        checks = self._build_archive_checks(target, reason)

        # Build effects
        effects, no_effects = self._build_archive_effects(target)

        # ARCHIVE is allowed
        return self._build_response(
            operation="ARCHIVE",
            decision=MemoryDecision.WRITE,  # placeholder, overridden
            decision_reasons=[],
            candidate=None,
            target=target,
            checks=checks,
            effects=effects,
            no_effects=no_effects,
            similarity=None,
            score=None,
            score_breakdown=None,
            cfg=cfg,
            decision_override="ARCHIVE",
            allowed=True,
            archive_reason=redact_local_paths(reason) if reason else None,
        )

    # ── Local decision resolvers ──

    @staticmethod
    def _resolve_write_decision(
        candidate: MemoryCandidate,
        score: int,
        score_breakdown: list[ScoreEntry],
        cfg: AutoWriteConfig,
        best_match: SimilarityBreakdown | None,
        cat_status: str | None,
    ) -> tuple[MemoryDecision, list[str]]:
        """Resolve WRITE decision locally without calling resolve_memory_decision."""
        reasons: list[str] = []
        score_rules = {entry.rule for entry in score_breakdown}

        # Invalid candidate
        if not candidate.summary.strip() or not candidate.title.strip() or not candidate.tags:
            reasons.append("Candidate is missing required fields.")
            return MemoryDecision.SKIP, reasons

        # Category not found
        if cat_status is None:
            if cfg.auto_create_categories and score >= cfg.write_threshold:
                reasons.append("Category would be auto-created.")
                return MemoryDecision.WRITE, reasons
            reasons.append("Category does not exist.")
            return MemoryDecision.REVIEW, reasons

        # Category not active
        if cat_status != "active":
            reasons.append(f"Category is {cat_status}.")
            return MemoryDecision.REVIEW, reasons

        # Score too low
        if score < cfg.review_threshold:
            reasons.append(f"Score {score} is below review threshold {cfg.review_threshold}.")
            return MemoryDecision.SKIP, reasons

        # Score in review range
        if score < cfg.write_threshold:
            reasons.append(f"Score {score} is below write threshold {cfg.write_threshold}.")
            if best_match and best_match.similarity >= cfg.candidate_similarity_threshold:
                return MemoryDecision.REVIEW, reasons
            return MemoryDecision.REVIEW, reasons

        # High score — check for duplicates and updates
        if best_match and best_match.similarity >= cfg.candidate_similarity_threshold:
            # Duplicate check
            if (best_match.similarity >= cfg.duplicate_similarity_threshold
                    and (best_match.title_similarity >= 0.95
                         or best_match.summary_similarity >= 0.95)):
                reasons.append("Exact duplicate of existing memory.")
                return MemoryDecision.SKIP_DUPLICATE, reasons

            # Update check
            if (best_match.similarity >= cfg.update_similarity_threshold
                    and best_match.category == candidate.category
                    and best_match.core_tag_overlap
                    and best_match.status == "active"):
                protected, _, _ = is_protected_memory(best_match, cfg)
                if not protected:
                    reasons.append("Similar enough to update existing memory.")
                    return MemoryDecision.UPDATE, reasons

            # Not safe for auto-update → REVIEW
            reasons.append("Similar match found but not safe for auto-update.")
            return MemoryDecision.REVIEW, reasons

        # No match or low similarity — WRITE
        reasons.append("No conflicting match found.")
        return MemoryDecision.WRITE, reasons

    @staticmethod
    def _resolve_update_decision(
        candidate: MemoryCandidate,
        score: int,
        score_breakdown: list[ScoreEntry],
        cfg: AutoWriteConfig,
        best_match: SimilarityBreakdown | None,
        target: Any,
    ) -> tuple[MemoryDecision, list[str]]:
        """Resolve UPDATE decision locally."""
        reasons: list[str] = []

        # If there's a close match that qualifies for UPDATE
        if best_match and best_match.similarity >= cfg.candidate_similarity_threshold:
            if (best_match.similarity >= cfg.duplicate_similarity_threshold
                    and (best_match.title_similarity >= 0.95
                         or best_match.summary_similarity >= 0.95)):
                reasons.append("Content is nearly identical — would be a duplicate.")
                return MemoryDecision.SKIP_DUPLICATE, reasons

            if best_match.similarity >= cfg.update_similarity_threshold:
                reasons.append("Similar enough for update.")
                return MemoryDecision.UPDATE, reasons

            reasons.append("Similar but below update threshold.")
            return MemoryDecision.REVIEW, reasons

        # For direct target update, if no close match, UPDATE is reasonable
        reasons.append("Direct target update.")
        return MemoryDecision.UPDATE, reasons

    # ── Validation helpers ──

    def _ensure_available(self) -> None:
        if not self.is_available():
            raise MemoryWriterDryRunUnavailableError(
                "Memory system is not available."
            )

    @staticmethod
    def _validate_memory_id(memory_id: str) -> None:
        if not memory_id or not isinstance(memory_id, str):
            raise MemoryWriterInvalidIdError("Memory ID is required.")
        if not MEMORY_ID_RE.match(memory_id):
            raise MemoryWriterInvalidIdError(
                f"Invalid memory ID format: '{_truncate(memory_id, 50)}'."
            )

    @staticmethod
    def _validate_write_request(query: str, candidate: dict[str, Any]) -> None:
        if not query or not isinstance(query, str):
            raise MemoryWriterInvalidRequestError("query is required.")
        if len(query) > _MAX_QUERY_LENGTH:
            raise MemoryWriterInvalidRequestError(
                f"query exceeds {_MAX_QUERY_LENGTH} characters."
            )
        if not candidate or not isinstance(candidate, dict):
            raise MemoryWriterInvalidRequestError("candidate is required.")

        summary = candidate.get("summary")
        if not summary or not isinstance(summary, str):
            raise MemoryWriterInvalidRequestError("candidate.summary is required.")
        if len(summary) > _MAX_CANDIDATE_SUMMARY:
            raise MemoryWriterInvalidRequestError(
                f"candidate.summary exceeds {_MAX_CANDIDATE_SUMMARY} characters."
            )

        category = candidate.get("category")
        if not category or not isinstance(category, str):
            raise MemoryWriterInvalidRequestError("candidate.category is required.")
        if len(category) > _MAX_CATEGORY_LENGTH:
            raise MemoryWriterInvalidRequestError(
                f"candidate.category exceeds {_MAX_CATEGORY_LENGTH} characters."
            )
        if not CATEGORY_NAME_RE.match(category):
            raise MemoryWriterInvalidRequestError(
                f"candidate.category has invalid format: '{_truncate(category, 30)}'."
            )

        importance = candidate.get("importance")
        if not importance or not isinstance(importance, str):
            raise MemoryWriterInvalidRequestError("candidate.importance is required.")
        if importance not in VALID_IMPORTANCE:
            raise MemoryWriterInvalidRequestError(
                f"candidate.importance must be one of {sorted(VALID_IMPORTANCE)}."
            )

        ttl = candidate.get("ttl")
        if not ttl or not isinstance(ttl, str):
            raise MemoryWriterInvalidRequestError("candidate.ttl is required.")
        if ttl not in VALID_TTL:
            raise MemoryWriterInvalidRequestError(
                f"candidate.ttl must be one of {sorted(VALID_TTL)}."
            )

        tags = candidate.get("tags")
        if not tags or not isinstance(tags, list):
            raise MemoryWriterInvalidRequestError("candidate.tags is required.")
        if len(tags) > _MAX_TAGS_COUNT:
            raise MemoryWriterInvalidRequestError(
                f"candidate.tags exceeds {_MAX_TAGS_COUNT} items."
            )
        for tag in tags:
            if not isinstance(tag, str):
                raise MemoryWriterInvalidRequestError(
                    "candidate.tags must contain only strings."
                )
            if len(tag) > _MAX_TAG_LENGTH:
                raise MemoryWriterInvalidRequestError(
                    f"Tag exceeds {_MAX_TAG_LENGTH} characters: '{_truncate(tag, 20)}'."
                )

        title = candidate.get("title")
        if title is not None and isinstance(title, str) and len(title) > _MAX_CANDIDATE_TITLE:
            raise MemoryWriterInvalidRequestError(
                f"candidate.title exceeds {_MAX_CANDIDATE_TITLE} characters."
            )

        ctype = candidate.get("type")
        if ctype is not None and isinstance(ctype, str) and len(ctype) > _MAX_CANDIDATE_TYPE:
            raise MemoryWriterInvalidRequestError(
                f"candidate.type exceeds {_MAX_CANDIDATE_TYPE} characters."
            )

        source_confidence = candidate.get("sourceConfidence")
        if source_confidence is not None and source_confidence not in (
            "user_confirmed",
            "assistant_inferred",
        ):
            raise MemoryWriterInvalidRequestError(
                "candidate.sourceConfidence must be 'user_confirmed' or 'assistant_inferred'."
            )

    @staticmethod
    def _validate_update_candidate(candidate: dict[str, Any]) -> None:
        if not candidate or not isinstance(candidate, dict):
            raise MemoryWriterInvalidRequestError("candidate is required.")

        summary = candidate.get("summary")
        if not summary or not isinstance(summary, str):
            raise MemoryWriterInvalidRequestError("candidate.summary is required.")
        if len(summary) > _MAX_CANDIDATE_SUMMARY:
            raise MemoryWriterInvalidRequestError(
                f"candidate.summary exceeds {_MAX_CANDIDATE_SUMMARY} characters."
            )

        importance = candidate.get("importance")
        if importance is not None and importance not in VALID_IMPORTANCE:
            raise MemoryWriterInvalidRequestError(
                f"candidate.importance must be one of {sorted(VALID_IMPORTANCE)}."
            )

        ttl = candidate.get("ttl")
        if ttl is not None and ttl not in VALID_TTL:
            raise MemoryWriterInvalidRequestError(
                f"candidate.ttl must be one of {sorted(VALID_TTL)}."
            )

        tags = candidate.get("tags")
        if tags is not None:
            if not isinstance(tags, list):
                raise MemoryWriterInvalidRequestError("candidate.tags must be a list.")
            if len(tags) > _MAX_TAGS_COUNT:
                raise MemoryWriterInvalidRequestError(
                    f"candidate.tags exceeds {_MAX_TAGS_COUNT} items."
                )
            for tag in tags:
                if not isinstance(tag, str):
                    raise MemoryWriterInvalidRequestError(
                        "candidate.tags must contain only strings."
                    )
                if len(tag) > _MAX_TAG_LENGTH:
                    raise MemoryWriterInvalidRequestError(
                        f"Tag exceeds {_MAX_TAG_LENGTH} characters."
                    )

    # ── Candidate builders ──

    @staticmethod
    def _build_candidate(candidate: dict[str, Any], query: str) -> MemoryCandidate:
        summary = candidate["summary"]
        title = candidate.get("title") or summary[:100]
        return MemoryCandidate(
            summary=summary,
            category=candidate["category"],
            tags=candidate["tags"],
            title=title[:_MAX_CANDIDATE_TITLE],
            memory_type=candidate.get("type", "project_status"),
            importance=candidate["importance"],
            ttl=candidate["ttl"],
            source_confidence=candidate.get("sourceConfidence", "user_confirmed"),
        )

    @staticmethod
    def _build_update_candidate(
        target: Any, candidate: dict[str, Any]
    ) -> MemoryCandidate:
        old_fields = target.fields
        summary = candidate.get("summary", old_fields.get("summary", ""))
        tags = candidate.get("tags", old_fields.get("tags", "").split(", "))
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        title = target.title  # Title is NOT updated
        return MemoryCandidate(
            summary=summary,
            category=target.category,
            tags=tags,
            title=title,
            memory_type=candidate.get("type", old_fields.get("type", "project_status")),
            importance=candidate.get("importance", old_fields.get("importance", "P1")),
            ttl=candidate.get("ttl", old_fields.get("ttl", "project")),
            source_confidence="user_confirmed",
        )

    # ── Protection checks ──

    @staticmethod
    def _check_target_protection(
        target: Any, cfg: AutoWriteConfig
    ) -> dict[str, str] | None:
        """Check P0 and permanent protection independently."""
        importance = target.fields.get("importance", "")
        ttl = target.fields.get("ttl", "")

        if cfg.protect_p0 and importance == "P0":
            return {
                "code": "MEMORY_P0_PROTECTED",
                "reason": "Target memory importance is P0 and is protected from modification.",
            }
        if cfg.protect_permanent and ttl == "permanent":
            return {
                "code": "MEMORY_PERMANENT_PROTECTED",
                "reason": "Target memory TTL is permanent and is protected from modification.",
            }
        return None

    # ── Check builders ──

    def _build_write_checks(
        self, candidate: MemoryCandidate, root_categories: dict[str, Any],
        cat_status: str | None,
    ) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        cat_name = candidate.category

        if cat_name in root_categories:
            checks.append({
                "code": "CATEGORY_EXISTS",
                "passed": True,
                "message": redact_local_paths(
                    _truncate(f"Category '{cat_name}' exists.", _MAX_CHECK_MESSAGE)
                ),
            })
            if cat_status == "active":
                checks.append({
                    "code": "CATEGORY_ACTIVE",
                    "passed": True,
                    "message": f"Category '{cat_name}' is active.",
                })
            else:
                checks.append({
                    "code": "CATEGORY_ACTIVE",
                    "passed": False,
                    "message": _truncate(
                        f"Category '{cat_name}' is not active (status: {cat_status}).",
                        _MAX_CHECK_MESSAGE,
                    ),
                })
        else:
            checks.append({
                "code": "CATEGORY_EXISTS",
                "passed": False,
                "message": _truncate(
                    f"Category '{cat_name}' does not exist.", _MAX_CHECK_MESSAGE
                ),
            })

        checks.append({
            "code": "IMPORTANCE_VALID",
            "passed": candidate.importance in VALID_IMPORTANCE,
            "message": f"Importance '{candidate.importance}' is valid.",
        })
        checks.append({
            "code": "TTL_VALID",
            "passed": candidate.ttl in VALID_TTL,
            "message": f"TTL '{candidate.ttl}' is valid.",
        })
        checks.append({
            "code": "SOURCE_CONFIDENCE",
            "passed": candidate.source_confidence == "user_confirmed",
            "message": (
                "Source confidence is 'user_confirmed'."
                if candidate.source_confidence == "user_confirmed"
                else "Source confidence is 'assistant_inferred' — score may be reduced."
            ),
        })
        return checks

    @staticmethod
    def _build_update_checks(
        target: Any, candidate: dict[str, Any]
    ) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []

        importance = candidate.get("importance")
        if importance is not None:
            checks.append({
                "code": "IMPORTANCE_VALID",
                "passed": importance in VALID_IMPORTANCE,
                "message": f"Importance '{importance}' is valid.",
            })

        ttl = candidate.get("ttl")
        if ttl is not None:
            checks.append({
                "code": "TTL_VALID",
                "passed": ttl in VALID_TTL,
                "message": f"TTL '{ttl}' is valid.",
            })

        target_importance = target.fields.get("importance", "")
        target_ttl = target.fields.get("ttl", "")
        checks.append({
            "code": "TARGET_P0_PROTECTED",
            "passed": target_importance != "P0",
            "message": (
                "Target memory is not P0 protected."
                if target_importance != "P0"
                else "Target memory importance is P0 and is protected."
            ),
        })
        checks.append({
            "code": "TARGET_PERMANENT_PROTECTED",
            "passed": target_ttl != "permanent",
            "message": (
                "Target memory is not permanent protected."
                if target_ttl != "permanent"
                else "Target memory TTL is permanent and is protected."
            ),
        })
        return checks

    @staticmethod
    def _build_archive_checks(
        target: Any, reason: str | None
    ) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []

        importance = target.fields.get("importance", "")
        checks.append({
            "code": "TARGET_P0_PROTECTED",
            "passed": importance != "P0",
            "message": (
                "Target memory is not P0 protected."
                if importance != "P0"
                else "Target memory importance is P0 and cannot be archived."
            ),
        })

        ttl = target.fields.get("ttl", "")
        checks.append({
            "code": "TARGET_PERMANENT_PROTECTED",
            "passed": ttl != "permanent",
            "message": (
                "Target memory is not permanent protected."
                if ttl != "permanent"
                else "Target memory TTL is permanent and cannot be archived."
            ),
        })

        status = target.fields.get("status", "active")
        checks.append({
            "code": "TARGET_NOT_ARCHIVED",
            "passed": status != "archived",
            "message": (
                "Target memory is not archived."
                if status != "archived"
                else "Target memory is already archived."
            ),
        })
        return checks

    # ── Effect builders ──

    @staticmethod
    def _build_write_effects(
        decision: MemoryDecision,
        candidate: MemoryCandidate,
        root_categories: dict[str, Any],
        cfg: AutoWriteConfig,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        effects: list[dict[str, Any]] = []
        no_effects = [
            "No files were modified.",
            "No memory event was appended.",
            "No snapshot was created.",
            "No review item was created.",
        ]

        if decision == MemoryDecision.WRITE:
            effects.append({"type": "CREATE_MEMORY_RECORD", "wouldOccur": True, "description": "A new memory record would be created."})
            effects.append({"type": "UPDATE_CATEGORY_INDEX", "wouldOccur": True, "description": "The category index would be updated."})
            effects.append({"type": "APPEND_MEMORY_EVENT", "wouldOccur": True, "description": "A memory_create event would be appended."})
            effects.append({"type": "CREATE_INDEX_SNAPSHOT", "wouldOccur": True, "description": "A backup of the category index would be created."})
            if candidate.category not in root_categories:
                effects.append({"type": "CREATE_CATEGORY", "wouldOccur": cfg.auto_create_categories, "description": "A new category would be auto-created." if cfg.auto_create_categories else "Category auto-creation is disabled."})
        elif decision == MemoryDecision.REVIEW:
            effects.append({"type": "ENQUEUE_REVIEW", "wouldOccur": True, "description": "A Review Queue item would be enqueued."})
        elif decision == MemoryDecision.UPDATE:
            effects.append({"type": "UPDATE_MEMORY_RECORD", "wouldOccur": True, "description": "An existing memory record would be updated."})
            effects.append({"type": "UPDATE_CATEGORY_INDEX", "wouldOccur": True, "description": "The category index would be updated."})
            effects.append({"type": "APPEND_MEMORY_EVENT", "wouldOccur": True, "description": "A memory_update event would be appended."})
        elif decision in (MemoryDecision.SKIP, MemoryDecision.SKIP_DUPLICATE):
            effects.append({"type": "NO_OPERATION", "wouldOccur": True, "description": "No modifications would occur."})

        return effects, no_effects

    @staticmethod
    def _build_update_effects(
        decision: MemoryDecision, target: Any
    ) -> tuple[list[dict[str, Any]], list[str]]:
        effects: list[dict[str, Any]] = []
        no_effects = [
            "No files were modified.",
            "No memory event was appended.",
            "No snapshot was created.",
            "No review item was created.",
        ]

        if decision == MemoryDecision.UPDATE:
            effects.append({"type": "UPDATE_MEMORY_RECORD", "wouldOccur": True, "description": "The memory record would be updated."})
            effects.append({"type": "UPDATE_CATEGORY_INDEX", "wouldOccur": True, "description": "The category index would be updated."})
            effects.append({"type": "APPEND_MEMORY_EVENT", "wouldOccur": True, "description": "A memory_update event would be appended."})
            effects.append({"type": "CREATE_INDEX_SNAPSHOT", "wouldOccur": True, "description": "A backup of the category index would be created."})
            effects.append({"type": "CREATE_RECORD_SNAPSHOT", "wouldOccur": True, "description": "A backup of the memory record would be created."})
        elif decision == MemoryDecision.REVIEW:
            effects.append({"type": "ENQUEUE_REVIEW", "wouldOccur": True, "description": "A Review Queue item would be enqueued."})
        else:
            effects.append({"type": "NO_OPERATION", "wouldOccur": True, "description": "No modifications would occur."})

        return effects, no_effects

    @staticmethod
    def _build_archive_effects(target: Any) -> tuple[list[dict[str, Any]], list[str]]:
        effects: list[dict[str, Any]] = [
            {"type": "ARCHIVE_MEMORY_RECORD", "wouldOccur": True, "description": "The memory record status would change to archived."},
            {"type": "UPDATE_CATEGORY_INDEX", "wouldOccur": True, "description": "The category index would be updated."},
            {"type": "APPEND_MEMORY_EVENT", "wouldOccur": True, "description": "A memory_archive event would be appended."},
            {"type": "CREATE_INDEX_SNAPSHOT", "wouldOccur": True, "description": "A backup of the category index would be created."},
            {"type": "CREATE_RECORD_SNAPSHOT", "wouldOccur": True, "description": "A backup of the memory record would be created."},
        ]
        no_effects = [
            "No files were modified.",
            "No memory event was appended.",
            "No snapshot was created.",
            "No review item was created.",
        ]
        return effects, no_effects

    # ── Similarity preview ──

    @staticmethod
    def _build_similarity_preview(
        best_match: SimilarityBreakdown | None,
    ) -> dict[str, Any] | None:
        if best_match is None:
            return None
        return {
            "title": round(best_match.title_similarity, 4),
            "summary": round(best_match.summary_similarity, 4),
            "combined": round(best_match.combined_similarity, 4),
            "overall": round(best_match.similarity, 4),
            "tagOverlap": best_match.all_tag_overlap,
            "coreTagOverlap": best_match.core_tag_overlap,
            "matchedMemoryId": best_match.memory_id,
            "matchedMemoryTitle": redact_local_paths(
                _truncate(best_match.title, _MAX_TITLE_PREVIEW)
            ),
        }

    # ── Update diff ──

    @staticmethod
    def _build_update_diff(target: Any, candidate: dict[str, Any]) -> dict[str, Any]:
        old_fields = target.fields
        old_tags = [t.strip() for t in old_fields.get("tags", "").split(",") if t.strip()]
        new_tags = candidate.get("tags", old_tags)
        if isinstance(new_tags, str):
            new_tags = [t.strip() for t in new_tags.split(",") if t.strip()]

        new_summary = candidate.get("summary", old_fields.get("summary", ""))
        new_importance = candidate.get("importance", old_fields.get("importance", ""))
        new_ttl = candidate.get("ttl", old_fields.get("ttl", ""))

        return {
            "titleChanged": False,
            "summaryChanged": new_summary != old_fields.get("summary", ""),
            "importanceChanged": new_importance != old_fields.get("importance", ""),
            "ttlChanged": new_ttl != old_fields.get("ttl", ""),
            "tagsAdded": sorted(set(new_tags) - set(old_tags)),
            "tagsRemoved": sorted(set(old_tags) - set(new_tags)),
        }

    # ── Response builders ──

    def _build_response(
        self,
        *,
        operation: str,
        decision: MemoryDecision,
        decision_reasons: list[str],
        candidate: MemoryCandidate | None,
        target: Any | None,
        checks: list[dict[str, Any]],
        effects: list[dict[str, Any]],
        no_effects: list[str],
        similarity: dict[str, Any] | None,
        score: int | None,
        score_breakdown: list[ScoreEntry] | None,
        cfg: AutoWriteConfig,
        would_enqueue_review: bool = False,
        diff: dict[str, Any] | None = None,
        decision_override: str | None = None,
        allowed: bool | None = None,
        include_similarity: bool = True,
        include_effects: bool = True,
        include_diff: bool = False,
        archive_reason: str | None = None,
    ) -> dict[str, Any]:
        decision_str = decision_override or decision.value

        if allowed is not None:
            is_allowed = allowed
        else:
            is_allowed = decision in (
                MemoryDecision.WRITE,
                MemoryDecision.UPDATE,
                MemoryDecision.REVIEW,
            ) or decision_override in ("ARCHIVE",)

        blocked_reason = None
        if not is_allowed:
            if decision_reasons:
                blocked_reason = _truncate(
                    redact_local_paths(decision_reasons[0]), _MAX_BLOCKED_REASON
                )
            else:
                blocked_reason = "Operation would be skipped."

        target_dto = self._build_target_dto(target)
        candidate_dto = self._build_candidate_dto(candidate)

        score_dto = None
        if score is not None and score_breakdown is not None:
            score_dto = {
                "total": score,
                "breakdown": [{"rule": e.rule, "value": e.value} for e in score_breakdown],
            }

        config_dto = {
            "autoWriteEnabled": cfg.enabled,
            "autoUpdateEnabled": cfg.allow_updates,
            "autoCreateCategories": cfg.auto_create_categories,
            "writeThreshold": cfg.write_threshold,
            "reviewThreshold": cfg.review_threshold,
            "updateSimilarityThreshold": cfg.update_similarity_threshold,
            "duplicateSimilarityThreshold": cfg.duplicate_similarity_threshold,
            "candidateSimilarityThreshold": cfg.candidate_similarity_threshold,
        }

        warnings: list[str] = []
        if would_enqueue_review:
            warnings.append("Decision is REVIEW — a review item would be enqueued if executed.")
        if archive_reason:
            warnings.append(_truncate(redact_local_paths(f"Archive reason: {archive_reason}"), _MAX_WARNING))

        data: dict[str, Any] = {
            "dryRun": True,
            "operation": operation,
            "allowed": is_allowed,
            "blockedReason": blocked_reason,
            "decision": decision_str,
            "wouldModify": is_allowed and decision_str not in ("SKIP", "SKIP_DUPLICATE"),
            "wouldEnqueueReview": would_enqueue_review,
            "target": target_dto,
            "candidate": candidate_dto,
        }

        if score_dto is not None:
            data["score"] = score_dto
        if include_similarity and similarity is not None:
            data["similarity"] = similarity
        if include_diff and diff is not None:
            data["diff"] = diff

        data["checks"] = checks
        if include_effects:
            data["effects"] = effects
            data["noEffects"] = no_effects

        data["safety"] = {
            "readOnly": True,
            "writeEnabled": False,
            "executeAvailable": False,
            "sideEffects": False,
        }
        data["config"] = config_dto
        data["warnings"] = [_truncate(redact_local_paths(w), _MAX_WARNING) for w in warnings]

        return {"data": data}

    def _build_blocked_response(
        self,
        *,
        operation: str,
        memory_id: str,
        target: Any,
        blocked_reason: str,
        decision_override: str,
        check_code: str,
    ) -> dict[str, Any]:
        """Build a response for blocked operations."""
        checks: list[dict[str, Any]] = []

        if check_code in ("MEMORY_P0_PROTECTED", "MEMORY_PERMANENT_PROTECTED"):
            importance = target.fields.get("importance", "")
            ttl = target.fields.get("ttl", "")
            checks.append({"code": "TARGET_P0_PROTECTED", "passed": importance != "P0", "message": "Target memory is not P0 protected." if importance != "P0" else "Target memory importance is P0 and is protected."})
            checks.append({"code": "TARGET_PERMANENT_PROTECTED", "passed": ttl != "permanent", "message": "Target memory is not permanent protected." if ttl != "permanent" else "Target memory TTL is permanent and is protected."})
        elif check_code == "MEMORY_ALREADY_ARCHIVED":
            checks.append({"code": "TARGET_NOT_ARCHIVED", "passed": False, "message": "Target memory is already archived."})

        return self._build_response(
            operation=operation,
            decision=MemoryDecision.SKIP,
            decision_reasons=[blocked_reason],
            candidate=None,
            target=target,
            checks=checks,
            effects=[{"type": "NO_OPERATION", "wouldOccur": True, "description": "No modifications would occur."}],
            no_effects=["No files were modified.", "No memory event was appended.", "No snapshot was created.", "No review item was created."],
            similarity=None,
            score=None,
            score_breakdown=None,
            cfg=AutoWriteConfig(),
            decision_override=decision_override,
            allowed=False,
        )

    @staticmethod
    def _build_target_dto(target: Any | None) -> dict[str, Any] | None:
        if target is None:
            return None
        fields = target.fields
        return {
            "memoryId": target.memory_id,
            "title": redact_local_paths(_truncate(target.title, _MAX_TITLE_PREVIEW)),
            "category": target.category,
            "importance": fields.get("importance", ""),
            "ttl": fields.get("ttl", ""),
            "status": fields.get("status", ""),
            "protected": False,
            "protectionReason": None,
        }

    @staticmethod
    def _build_candidate_dto(candidate: MemoryCandidate | None) -> dict[str, Any] | None:
        if candidate is None:
            return None
        return {
            "titlePreview": redact_local_paths(_truncate(candidate.title, _MAX_TITLE_PREVIEW)),
            "summaryPreview": redact_local_paths(_truncate(candidate.summary, _MAX_SUMMARY_PREVIEW)),
            "category": candidate.category,
            "type": candidate.memory_type,
            "importance": candidate.importance,
            "ttl": candidate.ttl,
            "tags": candidate.tags,
        }
