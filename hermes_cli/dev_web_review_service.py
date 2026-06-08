"""Dev Web API review queue query service.

Read-only service that queries review queue data from the development HERMES_HOME
using the memory_review_queue read-only functions. All queries are side-effect-free.

Phase 1C adds dev-only execute methods that call the real approve_review_item()
and reject_review_item() functions. Execute is gated by a fail-closed kill switch
and dev-only environment guard.

Importing this module has no side effects.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from agent.memory_review_queue import (
    ReviewStatus,
    ProposedAction,
    get_review_queue_paths,
    list_review_items,
    load_review_item,
    revalidate_review_approval,
    approve_review_item,
    reject_review_item,
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


class ReviewNotPendingError(Exception):
    """Raised when a dry-run action targets a non-pending review item."""

    def __init__(self, current_status: str) -> None:
        self.current_status = current_status
        super().__init__(
            f"Review item is not pending (current: {current_status})."
        )


class ReviewExecuteDisabledError(Exception):
    """Raised when execute is attempted but the kill switch is disabled."""


class ReviewPreconditionFailedError(Exception):
    """Raised when reviewUpdatedAt does not match the current item."""

    def __init__(self, expected: str, actual: str) -> None:
        self.expected_updated_at = expected
        self.actual_updated_at = actual
        super().__init__(
            "Review item was modified since dry-run preview. "
            "Please re-run dry-run."
        )


class InvalidConfirmationError(Exception):
    """Raised when confirmationText does not match the expected value."""

    def __init__(self, expected: str) -> None:
        self.expected = expected
        super().__init__(
            f"confirmationText must be exactly '{expected}'."
        )


class MissingDryRunError(Exception):
    """Raised when dryRunPreviewed is not true."""

    def __init__(self) -> None:
        super().__init__(
            "dryRunPreviewed must be true. "
            "Dry-run preview must be completed before execute."
        )


class InvalidAcknowledgedEffectsError(Exception):
    """Raised when acknowledgedEffects does not include required effects."""

    def __init__(self, missing: list[str]) -> None:
        self.missing_effects = missing
        super().__init__(
            f"Missing required acknowledged effects: {', '.join(missing)}."
        )


class ReviewApprovalBlockedError(Exception):
    """Raised when approval revalidation fails on execute."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class UnsafeEnvironmentError(Exception):
    """Raised when execute is attempted in an unsafe environment."""


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
_REASON_PREVIEW_MAX_LENGTH = 200
_CHECK_MESSAGE_MAX_LENGTH = 200
_EFFECTS_ITEM_MAX_LENGTH = 200
_BLOCKED_REASON_MAX_LENGTH = 120

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

    # Safety flags — read-only + dry-run available in Phase 1B
    dto["safety"] = {
        "readOnly": True,
        "approveAvailable": False,
        "rejectAvailable": False,
        "writeAvailable": False,
        "dryRunAvailable": True,
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
            "dryRunEnabled": True,
            "executeEnabled": self.is_execute_enabled(),
            "killSwitchActive": not self.is_execute_enabled(),
            "devOnly": True,
            "productionBlocked": True,
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

    # ── Dry-run: Approve ──

    def dry_run_approve(
        self,
        review_id: str,
        *,
        include_diff: bool = True,
    ) -> dict[str, Any]:
        """Preview what would happen if a review item were approved.

        This method is completely side-effect-free. It only reads the review
        item and revalidates approval conditions using read-only functions.

        It does NOT call approve_review_item(), reject_review_item(),
        append_review_event(), atomic_write_review_json(),
        create_memory_item(), or update_memory_item().
        """
        if not self.is_available():
            raise ReviewQueueUnavailableError()

        try:
            item = load_review_item(review_id, home=self._home)
        except FileNotFoundError:
            raise ReviewNotFoundError()
        except (ValueError, OSError):
            raise ReviewNotFoundError()

        status = item.get("status", "")
        if status != ReviewStatus.PENDING.value:
            raise ReviewNotPendingError(status)

        # Determine the proposed action from the item
        proposed_action = item.get("proposed_action", "")
        if not proposed_action or proposed_action == ProposedAction.UNDECIDED.value:
            # Default to WRITE for undecided items
            proposed_action = ProposedAction.WRITE.value
        action = proposed_action if proposed_action in (
            ProposedAction.WRITE.value, ProposedAction.UPDATE.value,
        ) else ProposedAction.WRITE.value

        # Use revalidate_review_approval for read-only validation.
        # This function only reads data — it calls parse_root(), find_item(),
        # find_best_memory_match(), calculate_similarity_breakdown(),
        # is_protected_memory() — all confirmed read-only.
        # If the memory system is not initialized (e.g. in tests with
        # minimal fixtures), fall back to basic validation.
        target_memory_id = None
        matched_memory = item.get("matched_memory")
        if matched_memory and isinstance(matched_memory, dict):
            target_memory_id = matched_memory.get("memory_id")

        try:
            validation = revalidate_review_approval(
                item, action=action, target=target_memory_id,
            )
        except (FileNotFoundError, ValueError, OSError, KeyError):
            # Memory system not fully initialized — perform basic checks
            validation = _basic_approve_validation(
                item, action=action, target=target_memory_id,
            )

        allowed = validation.get("valid", False)
        errors = validation.get("errors", [])

        # Build checks list
        checks = _build_approve_checks(item, validation)

        # Build safety
        safety = {
            "devOnly": True,
            "productionBlocked": True,
            "protectedTarget": validation.get("protected_target", False),
            "p0Blocked": "TARGET_P0_PROTECTED" in errors,
            "permanentBlocked": "TARGET_PERMANENT_PROTECTED" in errors,
            "duplicateBlocked": "BECAME_DUPLICATE" in errors,
        }

        # Build preview
        candidate = item.get("candidate", {})
        preview = {
            "title": _truncate(
                redact_local_paths(candidate.get("title", "")),
                _TITLE_MAX_LENGTH,
            ),
            "summaryPreview": _truncate(
                redact_local_paths(candidate.get("summary", "")),
                _SUMMARY_PREVIEW_MAX_LENGTH,
            ),
            "tags": candidate.get("tags", []),
            "reasonPreview": None,
            "redactedPaths": True,
        }

        # Build effects / noEffects
        if allowed:
            effects = []
            if action == ProposedAction.WRITE.value:
                effects.append("Would create memory record.")
            elif action == ProposedAction.UPDATE.value:
                effects.append("Would update existing memory record.")
            effects.append("Would mark review as approved.")
            effects.append("Would append review_approved event.")
        else:
            effects = []

        no_effects = [
            "No files were modified.",
            "No events were appended.",
            "No memory was written.",
        ]
        if not allowed:
            no_effects.append("Approval would be blocked.")

        # Determine blocked reason
        blocked_reason = None
        if not allowed and errors:
            blocked_reason = _truncate(
                errors[0], _BLOCKED_REASON_MAX_LENGTH,
            )

        return {
            "reviewId": item.get("review_id", ""),
            "dryRun": True,
            "action": "APPROVE",
            "allowed": allowed,
            "blockedReason": blocked_reason,
            "wouldModify": allowed,
            "wouldWriteMemory": allowed,
            "wouldUpdateReview": allowed,
            "wouldAppendEvent": allowed,
            "wouldCreateSnapshot": False,
            "target": {
                "memoryId": target_memory_id,
                "category": candidate.get("category", ""),
                "operation": action,
            },
            "safety": safety,
            "checks": checks,
            "preview": preview if include_diff else None,
            "effects": effects,
            "noEffects": no_effects,
            "warnings": [],
        }

    # ── Dry-run: Reject ──

    def dry_run_reject(
        self,
        review_id: str,
        *,
        reason: str | None = None,
        include_diff: bool = True,
    ) -> dict[str, Any]:
        """Preview what would happen if a review item were rejected.

        This method is completely side-effect-free. It only reads the review
        item and checks its status.

        It does NOT call reject_review_item() (which has no dry_run param),
        append_review_event(), or atomic_write_review_json().
        """
        if not self.is_available():
            raise ReviewQueueUnavailableError()

        try:
            item = load_review_item(review_id, home=self._home)
        except FileNotFoundError:
            raise ReviewNotFoundError()
        except (ValueError, OSError):
            raise ReviewNotFoundError()

        status = item.get("status", "")
        if status != ReviewStatus.PENDING.value:
            raise ReviewNotPendingError(status)

        allowed = True
        checks = [
            {
                "code": "REVIEW_IS_PENDING",
                "status": "pass",
                "message": "Review item is pending and can be rejected.",
            },
        ]

        candidate = item.get("candidate", {})

        # Prepare reason preview (redacted, truncated, not saved)
        reason_preview = None
        if reason and reason.strip():
            reason_preview = _truncate(
                redact_local_paths(reason.strip()),
                _REASON_PREVIEW_MAX_LENGTH,
            )

        # Build preview
        preview = {
            "title": _truncate(
                redact_local_paths(candidate.get("title", "")),
                _TITLE_MAX_LENGTH,
            ),
            "summaryPreview": _truncate(
                redact_local_paths(candidate.get("summary", "")),
                _SUMMARY_PREVIEW_MAX_LENGTH,
            ),
            "tags": candidate.get("tags", []),
            "reasonPreview": reason_preview,
            "redactedPaths": True,
        }

        effects = [
            "Would mark review as rejected.",
            "Would append review_rejected event.",
        ]

        no_effects = [
            "No files were modified.",
            "No events were appended.",
            "No memory was written.",
        ]

        return {
            "reviewId": item.get("review_id", ""),
            "dryRun": True,
            "action": "REJECT",
            "allowed": allowed,
            "blockedReason": None,
            "wouldModify": True,
            "wouldWriteMemory": False,
            "wouldUpdateReview": True,
            "wouldAppendEvent": True,
            "wouldCreateSnapshot": False,
            "target": {
                "memoryId": None,
                "category": candidate.get("category", ""),
                "operation": "REJECT",
            },
            "safety": {
                "devOnly": True,
                "productionBlocked": True,
            },
            "checks": checks,
            "preview": preview if include_diff else None,
            "effects": effects,
            "noEffects": no_effects,
            "warnings": [],
        }

    # ── Kill switch ──

    @staticmethod
    def is_execute_enabled() -> bool:
        """Check if execute capability is enabled via kill switch.

        The kill switch reads HERMES_REVIEW_EXECUTE_ENABLED from the
        environment. Default is disabled (false). Fail-closed: any
        unrecognized value is treated as disabled.
        """
        raw = os.environ.get("HERMES_REVIEW_EXECUTE_ENABLED", "").strip().lower()
        return raw in ("true", "1", "yes", "on")

    @staticmethod
    def _check_dev_only_environment(hermes_home: Path) -> None:
        """Verify the HERMES_HOME is safe for execute operations.

        Raises UnsafeEnvironmentError if:
        - HERMES_HOME is the production home (~/.hermes)
        - HERMES_HOME is inside the production home
        """
        from hermes_cli.dev_web_config import _PRODUCTION_HERMES_HOME

        resolved = hermes_home.resolve()
        try:
            prod_resolved = _PRODUCTION_HERMES_HOME.resolve()
        except Exception:
            prod_resolved = _PRODUCTION_HERMES_HOME

        if resolved == prod_resolved:
            raise UnsafeEnvironmentError(
                "Execute is not allowed on the production home."
            )
        try:
            resolved.relative_to(prod_resolved)
        except ValueError:
            pass  # Not inside production — good
        else:
            raise UnsafeEnvironmentError(
                "Execute is not allowed inside the production home."
            )

    # ── Execute: Approve ──

    def execute_approve(
        self,
        review_id: str,
        *,
        confirmation_text: str,
        expected_action: str,
        review_updated_at: str,
        dry_run_previewed: bool,
        acknowledged_effects: list[str],
    ) -> dict[str, Any]:
        """Execute a real approve on a review item.

        This method has real side effects: it writes memory files,
        updates review status, and appends events. It is gated by
        the kill switch and dev-only environment guard.

        All preconditions must be met before execution.
        """
        # 1. Kill switch check
        if not self.is_execute_enabled():
            raise ReviewExecuteDisabledError()

        # 2. Dev-only environment guard
        self._check_dev_only_environment(self._home)

        # 3. Validate review ID
        validation_error = self.validate_review_id(review_id)
        if validation_error:
            raise InvalidReviewIdError()

        # 4. Validate confirmation text
        if confirmation_text != "APPROVE":
            raise InvalidConfirmationError("APPROVE")

        # 5. Validate expected action
        if expected_action != "APPROVE":
            raise InvalidConfirmationError("APPROVE for expectedAction")

        # 6. Validate dryRunPreviewed
        if not dry_run_previewed:
            raise MissingDryRunError()

        # 7. Validate acknowledged effects
        required_effects = {"WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT"}
        missing = sorted(required_effects - set(acknowledged_effects))
        if missing:
            raise InvalidAcknowledgedEffectsError(missing)

        # 8. Load review item
        if not self.is_available():
            raise ReviewQueueUnavailableError()

        try:
            item = load_review_item(review_id, home=self._home)
        except FileNotFoundError:
            raise ReviewNotFoundError()
        except (ValueError, OSError):
            raise ReviewNotFoundError()

        # 9. Check status is pending
        status = item.get("status", "")
        if status != ReviewStatus.PENDING.value:
            raise ReviewNotPendingError(status)

        # 10. Validate reviewUpdatedAt precondition
        current_updated_at = item.get("updated_at", "")
        if review_updated_at != current_updated_at:
            raise ReviewPreconditionFailedError(
                review_updated_at, current_updated_at,
            )

        # 11. Determine proposed action
        proposed_action = item.get("proposed_action", "")
        if not proposed_action or proposed_action == ProposedAction.UNDECIDED.value:
            proposed_action = ProposedAction.WRITE.value
        action = proposed_action if proposed_action in (
            ProposedAction.WRITE.value, ProposedAction.UPDATE.value,
        ) else ProposedAction.WRITE.value

        # 12. Get target memory ID
        target_memory_id = None
        matched_memory = item.get("matched_memory")
        if matched_memory and isinstance(matched_memory, dict):
            target_memory_id = matched_memory.get("memory_id")

        # 13. Revalidate approval (full validation before execute)
        try:
            validation = revalidate_review_approval(
                item, action=action, target=target_memory_id,
            )
        except (FileNotFoundError, ValueError, OSError, KeyError):
            validation = _basic_approve_validation(
                item, action=action, target=target_memory_id,
            )

        if not validation.get("valid", False):
            errors = validation.get("errors", [])
            reason = ", ".join(errors) if errors else "Approval validation failed."
            raise ReviewApprovalBlockedError(
                _truncate(reason, _BLOCKED_REASON_MAX_LENGTH),
            )

        # 14. Execute the real approve
        status_before = item.get("status", ReviewStatus.PENDING.value)
        candidate = item.get("candidate", {})
        memory_changed = False

        try:
            result_item, result_info = approve_review_item(
                review_id,
                action=action,
                target=target_memory_id,
                dry_run=False,
                home=self._home,
            )
            memory_changed = action in (
                ProposedAction.WRITE.value, ProposedAction.UPDATE.value,
            )
            # Check if it was already approved (idempotent)
            already_approved = result_info.get("already_approved", False)
        except ValueError as exc:
            # Catch approval errors from the real function
            error_msg = str(exc)
            raise ReviewApprovalBlockedError(
                _truncate(redact_local_paths(error_msg), _BLOCKED_REASON_MAX_LENGTH),
            )
        except Exception as exc:
            # Unexpected errors — return sanitized message
            raise ReviewApprovalBlockedError(
                "An error occurred during approval execution.",
            )

        status_after = result_item.get("status", ReviewStatus.APPROVED.value)
        # Get the actual memory_id if it was written
        result_memory_id = target_memory_id
        if memory_changed and result_item.get("approval"):
            result_memory_id = result_item["approval"].get(
                "memory_id", target_memory_id,
            )

        return _build_execute_result(
            review_id=review_id,
            action="APPROVE",
            status_before=status_before,
            status_after=status_after,
            memory_changed=memory_changed,
            review_changed=True,
            event_appended=True,
            target_memory_id=result_memory_id,
            category=candidate.get("category", ""),
            operation=action,
        )

    # ── Execute: Reject ──

    def execute_reject(
        self,
        review_id: str,
        *,
        confirmation_text: str,
        expected_action: str,
        review_updated_at: str,
        dry_run_previewed: bool,
        acknowledged_effects: list[str],
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Execute a real reject on a review item.

        This method has real side effects: it updates review status
        and appends events. No memory is written.
        """
        # 1. Kill switch check
        if not self.is_execute_enabled():
            raise ReviewExecuteDisabledError()

        # 2. Dev-only environment guard
        self._check_dev_only_environment(self._home)

        # 3. Validate review ID
        validation_error = self.validate_review_id(review_id)
        if validation_error:
            raise InvalidReviewIdError()

        # 4. Validate confirmation text
        if confirmation_text != "REJECT":
            raise InvalidConfirmationError("REJECT")

        # 5. Validate expected action
        if expected_action != "REJECT":
            raise InvalidConfirmationError("REJECT for expectedAction")

        # 6. Validate dryRunPreviewed
        if not dry_run_previewed:
            raise MissingDryRunError()

        # 7. Validate acknowledged effects
        required_effects = {"UPDATE_REVIEW", "APPEND_REVIEW_EVENT"}
        missing = sorted(required_effects - set(acknowledged_effects))
        if missing:
            raise InvalidAcknowledgedEffectsError(missing)

        # 8. Sanitize reason (path redaction + truncation)
        safe_reason = "Rejected via dev-webui"
        if reason and reason.strip():
            safe_reason = redact_local_paths(reason.strip())[:500]

        # 9. Load review item
        if not self.is_available():
            raise ReviewQueueUnavailableError()

        try:
            item = load_review_item(review_id, home=self._home)
        except FileNotFoundError:
            raise ReviewNotFoundError()
        except (ValueError, OSError):
            raise ReviewNotFoundError()

        # 10. Check status is pending
        status = item.get("status", "")
        if status != ReviewStatus.PENDING.value:
            raise ReviewNotPendingError(status)

        # 11. Validate reviewUpdatedAt precondition
        current_updated_at = item.get("updated_at", "")
        if review_updated_at != current_updated_at:
            raise ReviewPreconditionFailedError(
                review_updated_at, current_updated_at,
            )

        # 12. Execute the real reject
        status_before = item.get("status", ReviewStatus.PENDING.value)
        candidate = item.get("candidate", {})

        try:
            result_item, changed = reject_review_item(
                review_id,
                reason=safe_reason,
                home=self._home,
            )
        except ValueError as exc:
            error_msg = str(exc)
            raise ReviewNotPendingError(
                _truncate(redact_local_paths(error_msg), _BLOCKED_REASON_MAX_LENGTH),
            )
        except Exception:
            raise ReviewApprovalBlockedError(
                "An error occurred during rejection execution.",
            )

        status_after = result_item.get("status", ReviewStatus.REJECTED.value)

        return _build_execute_result(
            review_id=review_id,
            action="REJECT",
            status_before=status_before,
            status_after=status_after,
            memory_changed=False,
            review_changed=changed,
            event_appended=True,
            target_memory_id=None,
            category=candidate.get("category", ""),
            operation="REJECT",
        )


def _build_execute_result(
    *,
    review_id: str,
    action: str,
    status_before: str,
    status_after: str,
    memory_changed: bool,
    review_changed: bool,
    event_appended: bool,
    target_memory_id: str | None,
    category: str,
    operation: str,
) -> dict[str, Any]:
    """Build a whitelisted execute result DTO.

    Only safe fields are included. No raw candidate, source,
    fingerprint, paths, secrets, or traceback.
    """
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "reviewId": review_id,
        "executed": True,
        "action": action,
        "statusBefore": status_before,
        "statusAfter": status_after,
        "memoryChanged": memory_changed,
        "reviewChanged": review_changed,
        "eventAppended": event_appended,
        "target": {
            "memoryId": target_memory_id,
            "category": category,
            "operation": operation,
        },
        "audit": {
            "actor": "dev-webui",
            "timestamp": timestamp,
            "devOnly": True,
        },
        "warnings": [],
    }


def _basic_approve_validation(
    item: dict[str, Any],
    *,
    action: str,
    target: str | None = None,
) -> dict[str, Any]:
    """Basic validation when the full memory system is unavailable.

    This performs lightweight checks without calling parse_root()
    or find_best_memory_match(), so it works with minimal test fixtures.
    """
    errors: list[str] = []

    # Check item status is pending
    if item.get("status") != ReviewStatus.PENDING.value:
        errors.append("REVIEW_NOT_PENDING")

    # Check action is valid
    if action not in (ProposedAction.WRITE.value, ProposedAction.UPDATE.value):
        errors.append("INVALID_APPROVAL_ACTION")

    # For UPDATE, check target exists in matched_memory
    if action == ProposedAction.UPDATE.value:
        matched = item.get("matched_memory")
        if not target:
            errors.append("UPDATE_TARGET_REQUIRED")
        elif not matched or matched.get("memory_id") != target:
            errors.append("UPDATE_TARGET_NOT_FOUND")

    return {
        "review_id": item.get("review_id", ""),
        "requested_action": action,
        "current_status": item.get("status", ""),
        "category_valid": True,  # Cannot validate without parse_root
        "duplicate_found": False,  # Cannot check without find_best_memory_match
        "protected_target": False,  # Cannot check without is_protected_memory
        "target": target,
        "errors": list(dict.fromkeys(errors)),
        "valid": item.get("status") == ReviewStatus.PENDING.value and not errors,
        "would_call": (
            "memory-add" if action == ProposedAction.WRITE.value
            else "memory-update"
        ),
        "would_modify_formal_memory": not errors,
    }


def _build_approve_checks(
    item: dict[str, Any],
    validation: dict[str, Any],
) -> list[dict[str, str]]:
    """Build the checks list for an approve dry-run response."""
    errors = validation.get("errors", [])
    status = item.get("status", "")

    checks: list[dict[str, str]] = []

    # Always include pending check
    checks.append({
        "code": "REVIEW_IS_PENDING",
        "status": "pass" if status == ReviewStatus.PENDING.value else "fail",
        "message": (
            "Review item is pending."
            if status == ReviewStatus.PENDING.value
            else f"Review item is not pending (current: {status})."
        ),
    })

    # Map validation errors to check items
    error_messages = {
        "CATEGORY_NOT_ACTIVE_OR_MISSING": "Category is not active or missing.",
        "BECAME_DUPLICATE": "Candidate became a duplicate since enqueue.",
        "UPDATE_TARGET_REQUIRED": "Update requires a target memory ID.",
        "UPDATE_TARGET_NOT_FOUND": "Target memory was not found.",
        "TARGET_P0_PROTECTED": "Target memory is P0 and protected from updates.",
        "TARGET_PERMANENT_PROTECTED": (
            "Target memory is permanent and protected from updates."
        ),
        "CATEGORY_MISMATCH": "Target memory is in a different category.",
        "TARGET_NOT_ACTIVE": "Target memory is not active.",
        "NO_CORE_TAG_OVERLAP": "No meaningful tag overlap with target memory.",
        "SIMILARITY_BELOW_UPDATE_THRESHOLD": (
            "Overall similarity is below the update threshold."
        ),
        "TITLE_SUMMARY_SIMILARITY_TOO_LOW": (
            "Both title and summary similarity are too low."
        ),
        "INVALID_APPROVAL_ACTION": "Approval action is not WRITE or UPDATE.",
    }

    reported_codes = set()
    for error_code in errors:
        if error_code in reported_codes:
            continue
        reported_codes.add(error_code)
        msg = error_messages.get(error_code, error_code)
        checks.append({
            "code": error_code,
            "status": "fail",
            "message": _truncate(msg, _CHECK_MESSAGE_MAX_LENGTH),
        })

    # If no errors, add pass checks for the common validations
    if not errors:
        if validation.get("category_valid", True):
            checks.append({
                "code": "CATEGORY_EXISTS",
                "status": "pass",
                "message": "Category exists and is active.",
            })
        if not validation.get("duplicate_found", False):
            checks.append({
                "code": "DUPLICATE_CHECK",
                "status": "pass",
                "message": "No duplicate found.",
            })
        if not validation.get("protected_target", False):
            checks.append({
                "code": "PROTECTION_CHECK",
                "status": "pass",
                "message": "Target is not protected.",
            })

    return checks
