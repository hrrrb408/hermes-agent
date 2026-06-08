"""Dev Web API review queue query service.

Read-only service that queries review queue data from the development HERMES_HOME
using the memory_review_queue read-only functions. All queries are side-effect-free.

Importing this module has no side effects.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agent.memory_review_queue import (
    ReviewStatus,
    ProposedAction,
    get_review_queue_paths,
    list_review_items,
    load_review_item,
    REVIEW_ID_RE,
)
from hermes_cli.dev_web_memory_service import redact_local_paths


# ── Custom exceptions ──


class ReviewQueueUnavailableError(Exception):
    """Raised when the review queue storage is not available."""


class ReviewNotFoundError(Exception):
    """Raised when a requested review item does not exist."""


class InvalidReviewIdError(Exception):
    """Raised when a review ID is malformed."""


class InvalidReviewQueryError(Exception):
    """Raised when review query parameters are invalid."""


# ── Constants ──

# Maximum review ID length for API input validation
_MAX_REVIEW_ID_LENGTH = 256

# Safe characters for review ID
_SAFE_REVIEW_ID_RE = re.compile(r"^[A-Za-z0-9._:\-]+$")

# Text truncation limits
_TITLE_MAX_LENGTH = 120
_SUMMARY_PREVIEW_MAX_LENGTH = 120
_SUMMARY_MAX_LENGTH = 300
_LAST_ERROR_MAX_LENGTH = 200

# Pagination limits
_MIN_LIMIT = 1
_MAX_LIMIT = 100
_DEFAULT_LIMIT = 30

# Allowed filter values
_VALID_STATUSES = frozenset(s.value for s in ReviewStatus) | {"all"}
_VALID_DECISIONS = frozenset({
    "WRITE", "UPDATE", "REVIEW", "SKIP",
    "SKIP_DUPLICATE", "UNDECIDED", "all",
})
_VALID_ORDERS = frozenset({"created_desc", "updated_desc"})

# Safe list-item fields (DTO whitelist for list responses)
_SAFE_LIST_FIELDS = frozenset({
    "review_id", "status", "original_decision", "proposed_action",
    "occurrence_count", "created_at", "updated_at",
})

# Fields that come from nested objects and need safe extraction
_CANDIDATE_SAFE_FIELDS = frozenset({
    "title", "category", "tags", "type",
})

_EVALUATION_SAFE_FIELDS = frozenset({
    "score", "reason_codes",
})


# ── DTO transformers (explicit whitelist) ──


def _truncate(text: str, max_length: int) -> str:
    """Truncate text to max_length with ellipsis indicator."""
    if not text:
        return text
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def _transform_review_list_dto(item: dict[str, Any]) -> dict[str, Any]:
    """Transform a review item into a safe list-item DTO.

    Only whitelisted fields are included. No fingerprint, source,
    raw candidate, evaluation details, approval/rejection objects,
    or internal paths.
    """
    candidate = item.get("candidate", {})
    evaluation = item.get("evaluation", {})

    # Extract target memory ID from matched_memory
    matched_memory = item.get("matched_memory")
    target_memory_id = (
        matched_memory.get("memory_id") if matched_memory else None
    )

    # Extract protected_target from evaluation
    protected_target = evaluation.get("protected_target", False)

    return {
        "reviewId": item.get("review_id", ""),
        "status": item.get("status", ""),
        "decision": item.get("original_decision", ""),
        "proposedAction": item.get("proposed_action", ""),
        "category": candidate.get("category", ""),
        "title": _truncate(candidate.get("title", ""), _TITLE_MAX_LENGTH),
        "summaryPreview": _truncate(
            candidate.get("summary", ""), _SUMMARY_PREVIEW_MAX_LENGTH
        ),
        "tags": candidate.get("tags", []),
        "score": evaluation.get("score", 0),
        "reasonCodes": evaluation.get("reason_codes", []),
        "targetMemoryId": target_memory_id,
        "protectedTarget": protected_target,
        "occurrenceCount": item.get("occurrence_count", 1),
        "createdAt": item.get("created_at", ""),
        "updatedAt": item.get("updated_at", ""),
    }


def _transform_review_detail_dto(item: dict[str, Any]) -> dict[str, Any]:
    """Transform a review item into a safe detail DTO.

    Includes all list fields plus summary, score breakdown,
    similarity, target, and safety information.
    """
    candidate = item.get("candidate", {})
    evaluation = item.get("evaluation", {})
    matched_memory = item.get("matched_memory")

    # Base list DTO fields
    dto = _transform_review_list_dto(item)

    # Detail-only additions
    dto["summary"] = _truncate(
        redact_local_paths(candidate.get("summary", "")),
        _SUMMARY_MAX_LENGTH,
    )

    # Score breakdown (safe: just rule name and value)
    raw_breakdown = evaluation.get("score_breakdown", [])
    dto["scoreBreakdown"] = [
        {"rule": entry.get("rule", ""), "value": entry.get("value", 0)}
        for entry in raw_breakdown
    ]

    # Similarity scores
    dto["similarity"] = {
        "title": evaluation.get("title_similarity", 0),
        "summary": evaluation.get("summary_similarity", 0),
        "combined": evaluation.get("combined_similarity", 0),
        "overall": evaluation.get("similarity", 0),
    }

    # Target information (safe)
    target_memory_id = (
        matched_memory.get("memory_id") if matched_memory else None
    )
    dto["target"] = {
        "memoryId": target_memory_id,
        "title": (
            _truncate(matched_memory.get("title", ""), _TITLE_MAX_LENGTH)
            if matched_memory else None
        ),
        "category": (
            matched_memory.get("category")
            if matched_memory else None
        ),
        "protected": evaluation.get("protected_target", False),
    }

    # Timestamps
    dto["timestamps"] = {
        "createdAt": item.get("created_at", ""),
        "updatedAt": item.get("updated_at", ""),
        "lastSeenAt": item.get("last_seen_at", ""),
        "reviewedAt": None,
    }

    # Extract reviewedAt from approval or rejection
    approval = item.get("approval")
    rejection = item.get("rejection")
    if approval and isinstance(approval, dict):
        dto["timestamps"]["reviewedAt"] = approval.get("approved_at")
    elif rejection and isinstance(rejection, dict):
        dto["timestamps"]["reviewedAt"] = rejection.get("rejected_at")

    # Error information (redacted and truncated)
    last_error = item.get("last_error")
    dto["errors"] = {
        "lastError": (
            _truncate(redact_local_paths(str(last_error)), _LAST_ERROR_MAX_LENGTH)
            if last_error else None
        ),
    }

    # Safety flags — always read-only in Phase 1A
    dto["safety"] = {
        "readOnly": True,
        "approveAvailable": False,
        "rejectAvailable": False,
        "writeAvailable": False,
        "dryRunAvailable": False,
    }

    return dto


def _redact_path(path: Path) -> str:
    """Redact a Path for display in API responses.

    Shows only the relative portion under hermes_home.
    """
    text = str(path)
    return redact_local_paths(text)


# ── Review query service ──


class DevReviewQueryService:
    """Read-only review queue query service for the Dev Web API.

    All operations use the memory_review_queue read-only functions with
    explicit home parameter. No writes, no LLM calls, no approval,
    no rejection, no enqueue.
    """

    def __init__(self, hermes_home: Path) -> None:
        self._home = hermes_home

    def is_available(self) -> bool:
        """Check whether the review queue storage is available."""
        try:
            paths = get_review_queue_paths(self._home)
            return paths.root.exists()
        except Exception:
            return False

    # ── Status ──

    def get_status(self) -> dict[str, Any]:
        """Get review queue status.

        Returns a DTO dict with availability, counts, and safety flags.
        Never returns raw file paths.
        """
        available = self.is_available()

        # Count items by status
        counts = {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "failed": 0,
            "total": 0,
        }

        redacted_path = ""
        storage_available = False

        if available:
            try:
                paths = get_review_queue_paths(self._home)
                storage_available = paths.items.exists()

                # Redact the path for display
                home_str = str(self._home)
                raw_path = str(paths.root)
                if raw_path.startswith(home_str):
                    redacted_path = "[dev-home]" + raw_path[len(home_str):]
                else:
                    redacted_path = redact_local_paths(raw_path)

                # Count items
                result = list_review_items(
                    include_all=True,
                    limit=10000,
                    home=self._home,
                )
                for item in result.items:
                    status = item.get("status", "")
                    if status in counts:
                        counts[status] += 1
                    counts["total"] += 1
            except Exception:
                storage_available = False

        return {
            "available": available and storage_available,
            "readOnly": True,
            "queueEnabled": False,
            "writeEnabled": False,
            "approveEnabled": False,
            "rejectEnabled": False,
            "enqueueEnabled": False,
            "counts": counts,
            "storage": {
                "available": storage_available,
                "redactedPath": redacted_path,
            },
        }

    # ── List ──

    def list_reviews(
        self,
        *,
        status: str | None = None,
        decision: str | None = None,
        category: str | None = None,
        query: str | None = None,
        limit: int = _DEFAULT_LIMIT,
        offset: int = 0,
        order: str = "updated_desc",
    ) -> dict[str, Any]:
        """List review items with optional filtering and pagination.

        Returns a dict with 'items' (list of DTOs) and 'page' (pagination).
        Never returns fingerprint, source, raw candidate, or evaluation details.
        """
        if not self.is_available():
            raise ReviewQueueUnavailableError()

        # Validate parameters
        if limit < _MIN_LIMIT or limit > _MAX_LIMIT:
            raise InvalidReviewQueryError(
                f"Limit must be between {_MIN_LIMIT} and {_MAX_LIMIT}."
            )
        if offset < 0:
            raise InvalidReviewQueryError("Offset must be non-negative.")
        if order not in _VALID_ORDERS:
            raise InvalidReviewQueryError(
                f"Order must be one of: {', '.join(sorted(_VALID_ORDERS))}."
            )
        if status is not None and status not in _VALID_STATUSES:
            raise InvalidReviewQueryError(
                f"Status must be one of: {', '.join(sorted(_VALID_STATUSES))}."
            )
        if decision is not None and decision not in _VALID_DECISIONS:
            raise InvalidReviewQueryError(
                f"Decision must be one of: {', '.join(sorted(_VALID_DECISIONS))}."
            )

        # Fetch all items (list_review_items is the only read-only lister)
        include_all = status == "all" or status is None
        result = list_review_items(
            status=None if include_all else status,
            include_all=True,  # Always fetch all, filter ourselves
            limit=10000,
            home=self._home,
        )

        items = result.items

        # Filter by status
        if status is not None and status != "all":
            items = [i for i in items if i.get("status") == status]

        # Filter by decision (original_decision)
        if decision is not None and decision != "all":
            items = [
                i for i in items
                if i.get("original_decision") == decision
            ]

        # Filter by category
        if category and category.strip():
            cat_lower = category.strip().lower()
            items = [
                i for i in items
                if i.get("candidate", {}).get("category", "").lower() == cat_lower
            ]

        # Filter by query (search title and summary)
        if query and query.strip():
            terms = query.strip().lower().split()
            filtered = []
            for item in items:
                candidate = item.get("candidate", {})
                title = candidate.get("title", "").lower()
                summary = candidate.get("summary", "").lower()
                text = f"{title} {summary}"
                if all(term in text for term in terms):
                    filtered.append(item)
            items = filtered

        # Sort
        if order == "created_desc":
            items.sort(
                key=lambda i: i.get("created_at", ""),
                reverse=True,
            )
        else:  # updated_desc
            items.sort(
                key=lambda i: i.get("updated_at", ""),
                reverse=True,
            )

        total = len(items)
        page_items = items[offset:offset + limit]

        return {
            "items": [_transform_review_list_dto(item) for item in page_items],
            "page": {
                "limit": limit,
                "offset": offset,
                "total": total,
                "hasMore": (offset + limit) < total,
            },
        }

    # ── Detail ──

    def get_review_detail(self, review_id: str) -> dict[str, Any]:
        """Get a single review item's detail by ID.

        Returns a detail DTO with safety information.
        Never returns fingerprint, source, raw evaluation details,
        approval/rejection objects, or internal paths.
        """
        if not self.is_available():
            raise ReviewQueueUnavailableError()

        try:
            item = load_review_item(review_id, home=self._home)
        except FileNotFoundError:
            raise ReviewNotFoundError()
        except (ValueError, OSError):
            raise ReviewNotFoundError()

        return _transform_review_detail_dto(item)

    # ── Validation helpers ──

    @staticmethod
    def validate_review_id(review_id: str) -> str | None:
        """Validate a review ID string.

        Returns None if valid, or an error description string if invalid.
        """
        if not review_id:
            return "Review ID is required."
        if len(review_id) > _MAX_REVIEW_ID_LENGTH:
            return "Review ID is too long."
        if not _SAFE_REVIEW_ID_RE.match(review_id):
            return "Review ID contains invalid characters."
        if not REVIEW_ID_RE.match(review_id):
            return "Review ID format is invalid."
        # Extra safety: no path separators
        if "/" in review_id or "\\" in review_id or ".." in review_id:
            return "Review ID contains path separators."
        return None
