"""Persistent review queue for automatic memory candidates."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

from hermes_constants import get_hermes_home
from utils import atomic_json_write

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class ProposedAction(str, Enum):
    WRITE = "WRITE"
    UPDATE = "UPDATE"
    UNDECIDED = "UNDECIDED"


@dataclass
class ReviewQueueConfig:
    enabled: bool = False
    path: str = "memory/reviews"
    enqueue_review: bool = True
    enqueue_blocked_write: bool = True
    enqueue_blocked_update: bool = True
    max_pending: int = 500
    exact_dedup: bool = True


@dataclass
class ReviewQueuePaths:
    root: Path
    items: Path
    events: Path
    lock: Path


@dataclass
class ReviewListResult:
    items: list[dict[str, Any]]
    warnings: list[str]


@dataclass
class MemoryReviewItem:
    review_id: str
    status: str
    created_at: str
    updated_at: str
    last_seen_at: str
    occurrence_count: int
    fingerprint: str
    source: dict[str, Any]
    original_decision: str
    proposed_action: str
    candidate: dict[str, Any]
    evaluation: dict[str, Any]
    matched_memory: dict[str, Any] | None
    approval: dict[str, Any] | None
    rejection: dict[str, Any] | None
    last_error: str | None
    version: int = 1


REVIEW_ID_RE = re.compile(r"^MR-\d{8}T\d{6}-[0-9a-f]{8}$")


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(minimum, min(maximum, parsed))


def get_review_queue_config(config: dict | None = None) -> ReviewQueueConfig:
    config = config or {}
    memory_cfg = config.get("memory", {}) if isinstance(config, dict) else {}
    if not isinstance(memory_cfg, dict):
        memory_cfg = {}
    raw = memory_cfg.get("review_queue", {})
    if not isinstance(raw, dict):
        raw = {}
    cfg = ReviewQueueConfig(
        enabled=_as_bool(raw.get("enabled"), False),
        path=str(raw.get("path") or "memory/reviews"),
        enqueue_review=_as_bool(raw.get("enqueue_review"), True),
        enqueue_blocked_write=_as_bool(raw.get("enqueue_blocked_write"), True),
        enqueue_blocked_update=_as_bool(raw.get("enqueue_blocked_update"), True),
        max_pending=_as_int(raw.get("max_pending"), 500, 1, 10000),
        exact_dedup=_as_bool(raw.get("exact_dedup"), True),
    )
    if os.getenv("HERMES_MEMORY_REVIEW_QUEUE") is not None:
        cfg.enabled = _as_bool(os.getenv("HERMES_MEMORY_REVIEW_QUEUE"), False)
    if os.getenv("HERMES_MEMORY_REVIEW_MAX_PENDING") is not None:
        cfg.max_pending = _as_int(
            os.getenv("HERMES_MEMORY_REVIEW_MAX_PENDING"),
            cfg.max_pending,
            1,
            10000,
        )
    return cfg


def get_review_queue_paths(
    home: Path | None = None,
    config: dict | None = None,
) -> ReviewQueuePaths:
    home = (home or get_hermes_home()).resolve()
    cfg = get_review_queue_config(config)
    relative = Path(cfg.path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe review queue path: {cfg.path}")
    root = (home / relative).resolve()
    expected = (home / "memory" / "reviews").resolve()
    if root != expected:
        raise ValueError("Review queue path must be HERMES_HOME/memory/reviews")
    return ReviewQueuePaths(
        root=root,
        items=root / "items",
        events=root / "events.jsonl",
        lock=root / ".queue.lock",
    )


def _ensure_paths(paths: ReviewQueuePaths) -> None:
    paths.items.mkdir(parents=True, exist_ok=True)
    paths.events.touch(exist_ok=True)


@contextmanager
def review_queue_lock(paths: ReviewQueuePaths) -> Iterator[None]:
    _ensure_paths(paths)
    with paths.lock.open("a+", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write_review_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_json_write(path, payload, indent=2, mode=0o600)


def append_review_event(paths: ReviewQueuePaths, event: str, **fields: Any) -> None:
    _ensure_paths(paths)
    payload = {"time": _now(), "event": event, **fields}
    with paths.events.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def fingerprint_memory_candidate(candidate: Any) -> str:
    from agent.runtime_memory_writer import normalize_memory_text

    parts = [
        normalize_memory_text(candidate.category),
        normalize_memory_text(candidate.title),
        normalize_memory_text(candidate.summary),
        ",".join(sorted(normalize_memory_text(tag) for tag in candidate.tags)),
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def generate_review_id(fingerprint: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"MR-{stamp}-{fingerprint[:8]}"


def _item_path(paths: ReviewQueuePaths, review_id: str) -> Path:
    if not REVIEW_ID_RE.match(review_id):
        raise ValueError(f"Invalid review id: {review_id}")
    path = (paths.items / f"{review_id}.json").resolve()
    path.relative_to(paths.items.resolve())
    return path


def _evaluation_payload(evaluation: Any) -> dict[str, Any]:
    return {
        "score": evaluation.score,
        "score_breakdown": [asdict(entry) for entry in evaluation.score_breakdown],
        "reason_codes": list(evaluation.reason_codes),
        "reasons": list(evaluation.reasons),
        "title_similarity": evaluation.title_similarity,
        "summary_similarity": evaluation.summary_similarity,
        "combined_similarity": evaluation.combined_similarity,
        "similarity": evaluation.similarity,
        "tag_overlap": list(evaluation.tag_overlap or []),
        "core_tag_overlap": list(evaluation.core_tag_overlap or []),
        "protected_target": evaluation.protected_target,
    }


def proposed_action_for(evaluation: Any) -> ProposedAction:
    from agent.runtime_memory_writer import MemoryDecision

    if evaluation.decision == MemoryDecision.WRITE:
        return ProposedAction.WRITE
    if evaluation.decision == MemoryDecision.UPDATE:
        return ProposedAction.UPDATE
    if evaluation.matched_memory_id:
        return ProposedAction.UNDECIDED
    return ProposedAction.WRITE


def should_enqueue_evaluation(evaluation: Any, cfg: ReviewQueueConfig) -> bool:
    from agent.runtime_memory_writer import MemoryDecision

    if evaluation.decision in {MemoryDecision.SKIP, MemoryDecision.SKIP_DUPLICATE}:
        return False
    if evaluation.decision == MemoryDecision.REVIEW:
        return cfg.enqueue_review
    if evaluation.decision == MemoryDecision.WRITE:
        return cfg.enqueue_blocked_write and not evaluation.would_modify_files
    if evaluation.decision == MemoryDecision.UPDATE:
        return cfg.enqueue_blocked_update and not evaluation.would_modify_files
    return False


def list_review_items(
    *,
    status: str | None = ReviewStatus.PENDING.value,
    include_all: bool = False,
    limit: int = 50,
    home: Path | None = None,
    config: dict | None = None,
) -> ReviewListResult:
    paths = get_review_queue_paths(home, config)
    if not paths.items.exists():
        return ReviewListResult([], [])
    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    for path in sorted(paths.items.glob("MR-*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            validate_review_item(payload)
        except Exception as exc:
            warnings.append(f"{path.name}: {exc}")
            continue
        if not include_all and status and payload.get("status") != status:
            continue
        items.append(payload)
    items.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return ReviewListResult(items[: max(1, limit)], warnings)


def validate_review_item(payload: dict[str, Any]) -> None:
    if not REVIEW_ID_RE.match(str(payload.get("review_id", ""))):
        raise ValueError("invalid review_id")
    if payload.get("status") not in {status.value for status in ReviewStatus}:
        raise ValueError("invalid status")
    if not payload.get("fingerprint"):
        raise ValueError("missing fingerprint")
    candidate = payload.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("missing candidate")
    for field in ("summary", "category", "tags", "title"):
        if not candidate.get(field):
            raise ValueError(f"candidate missing {field}")
    if payload.get("status") == ReviewStatus.APPROVED.value and not payload.get("approval"):
        raise ValueError("approved item missing approval")
    if payload.get("status") == ReviewStatus.REJECTED.value and not payload.get("rejection"):
        raise ValueError("rejected item missing rejection")


def load_review_item(
    review_id: str,
    *,
    home: Path | None = None,
    config: dict | None = None,
) -> dict[str, Any]:
    paths = get_review_queue_paths(home, config)
    path = _item_path(paths, review_id)
    if not path.exists():
        raise FileNotFoundError(f"Review item not found: {review_id}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_review_item(payload)
    return payload


def enqueue_review_item(
    evaluation: Any,
    *,
    source_kind: str = "runtime",
    channel: str = "",
    session_id_hash: str | None = None,
    message_id: str | None = None,
    home: Path | None = None,
    config: dict | None = None,
    require_enabled: bool = True,
) -> tuple[dict[str, Any] | None, bool, str]:
    cfg = get_review_queue_config(config)
    if require_enabled and not cfg.enabled:
        return None, False, "Review queue is disabled."
    if evaluation.candidate is None or not should_enqueue_evaluation(evaluation, cfg):
        return None, False, "Evaluation does not require review."
    paths = get_review_queue_paths(home, config)
    fingerprint = fingerprint_memory_candidate(evaluation.candidate)
    now = _now()

    with review_queue_lock(paths):
        current = list_review_items(include_all=True, limit=10000, home=home, config=config)
        if cfg.exact_dedup:
            for item in current.items:
                if item.get("status") == ReviewStatus.PENDING.value and item.get("fingerprint") == fingerprint:
                    item["occurrence_count"] = int(item.get("occurrence_count", 1)) + 1
                    item["last_seen_at"] = now
                    item["updated_at"] = now
                    item["evaluation"] = _evaluation_payload(evaluation)
                    atomic_write_review_json(_item_path(paths, item["review_id"]), item)
                    append_review_event(
                        paths,
                        "review_duplicate_seen",
                        review_id=item["review_id"],
                        occurrence_count=item["occurrence_count"],
                    )
                    return item, False, "Existing pending review updated."
        pending_count = sum(
            1 for item in current.items if item.get("status") == ReviewStatus.PENDING.value
        )
        if pending_count >= cfg.max_pending:
            return None, False, "Review queue is full."

        review_id = generate_review_id(fingerprint)
        while _item_path(paths, review_id).exists():
            fingerprint = hashlib.sha256((fingerprint + now).encode("utf-8")).hexdigest()
            review_id = generate_review_id(fingerprint)
        candidate = evaluation.candidate
        review_item = MemoryReviewItem(
            review_id=review_id,
            status=ReviewStatus.PENDING.value,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
            occurrence_count=1,
            fingerprint=fingerprint,
            source={
                "kind": source_kind,
                "channel": channel,
                "session_id_hash": session_id_hash,
                "message_id": message_id,
            },
            original_decision=evaluation.decision.value,
            proposed_action=proposed_action_for(evaluation).value,
            candidate={
                "summary": candidate.summary,
                "category": candidate.category,
                "tags": list(candidate.tags),
                "title": candidate.title,
                "type": candidate.memory_type,
                "importance": candidate.importance,
                "ttl": candidate.ttl,
                "source_confidence": candidate.source_confidence,
            },
            evaluation=_evaluation_payload(evaluation),
            matched_memory={
                "memory_id": evaluation.matched_memory_id,
                "title": evaluation.matched_memory_title,
                "category": evaluation.matched_memory_category,
            } if evaluation.matched_memory_id else None,
            approval=None,
            rejection=None,
            last_error=None,
        )
        payload = asdict(review_item)
        atomic_write_review_json(_item_path(paths, review_id), payload)
        append_review_event(
            paths,
            "review_created",
            review_id=review_id,
            decision=evaluation.decision.value,
            proposed_action=payload["proposed_action"],
            fingerprint=fingerprint,
        )
        return payload, True, "Review created."


def reject_review_item(
    review_id: str,
    reason: str,
    *,
    home: Path | None = None,
    config: dict | None = None,
) -> tuple[dict[str, Any], bool]:
    if not reason.strip():
        raise ValueError("Rejection reason is required")
    paths = get_review_queue_paths(home, config)
    with review_queue_lock(paths):
        item = load_review_item(review_id, home=home, config=config)
        if item["status"] == ReviewStatus.REJECTED.value:
            return item, False
        if item["status"] == ReviewStatus.APPROVED.value:
            raise ValueError("Approved review item cannot be rejected")
        if item["status"] != ReviewStatus.PENDING.value:
            raise ValueError(f"Review item is not pending: {item['status']}")
        now = _now()
        item["status"] = ReviewStatus.REJECTED.value
        item["updated_at"] = now
        item["rejection"] = {"rejected_at": now, "reason": reason.strip()}
        atomic_write_review_json(_item_path(paths, review_id), item)
        append_review_event(
            paths,
            "review_rejected",
            review_id=review_id,
            reason=reason.strip(),
        )
        return item, True


def _candidate_from_item(item: dict[str, Any]):
    from agent.runtime_memory_writer import MemoryCandidate

    candidate = item["candidate"]
    return MemoryCandidate(
        summary=candidate["summary"],
        category=candidate["category"],
        tags=list(candidate["tags"]),
        title=candidate["title"],
        memory_type=candidate.get("type", "project_status"),
        importance=candidate.get("importance", "P1"),
        ttl=candidate.get("ttl", "project"),
        source_confidence=candidate.get("source_confidence", "user_confirmed"),
    )


def revalidate_review_approval(
    item: dict[str, Any],
    *,
    action: str,
    target: str | None = None,
) -> dict[str, Any]:
    from agent.runtime_memory_writer import (
        DEFAULT_DUPLICATE_SIMILARITY_THRESHOLD,
        DEFAULT_UPDATE_SIMILARITY_THRESHOLD,
        SUMMARY_UPDATE_SIMILARITY_THRESHOLD,
        TITLE_UPDATE_SIMILARITY_THRESHOLD,
        calculate_similarity_breakdown,
        find_best_memory_match,
        is_protected_memory,
        AutoWriteConfig,
    )
    from hermes_cli.memory_router import find_item, parse_root

    candidate = _candidate_from_item(item)
    categories = parse_root()
    errors: list[str] = []
    category = categories.get(candidate.category)
    category_valid = bool(category and category.fields.get("status", "active") == "active")
    if not category_valid:
        errors.append("CATEGORY_NOT_ACTIVE_OR_MISSING")

    duplicate = find_best_memory_match(candidate)
    duplicate_found = bool(
        duplicate
        and duplicate.similarity >= DEFAULT_DUPLICATE_SIMILARITY_THRESHOLD
        and (
            duplicate.title_similarity >= 0.95
            or duplicate.summary_similarity >= 0.95
        )
    )

    protected = False
    match = None
    if action == ProposedAction.UPDATE.value:
        if not target:
            errors.append("UPDATE_TARGET_REQUIRED")
        else:
            target_item = find_item(target)
            if target_item is None:
                errors.append("UPDATE_TARGET_NOT_FOUND")
            else:
                match = calculate_similarity_breakdown(candidate, target_item)
                protected, codes, _reasons = is_protected_memory(match, AutoWriteConfig())
                errors.extend(codes)
                if match.category != candidate.category:
                    errors.append("CATEGORY_MISMATCH")
                if match.status != "active":
                    errors.append("TARGET_NOT_ACTIVE")
                if not match.core_tag_overlap:
                    errors.append("NO_CORE_TAG_OVERLAP")
                if match.similarity < DEFAULT_UPDATE_SIMILARITY_THRESHOLD:
                    errors.append("SIMILARITY_BELOW_UPDATE_THRESHOLD")
                if (
                    match.title_similarity < TITLE_UPDATE_SIMILARITY_THRESHOLD
                    and match.summary_similarity < SUMMARY_UPDATE_SIMILARITY_THRESHOLD
                ):
                    errors.append("TITLE_SUMMARY_SIMILARITY_TOO_LOW")
    elif action == ProposedAction.WRITE.value:
        if duplicate_found:
            errors.append("BECAME_DUPLICATE")
    else:
        errors.append("INVALID_APPROVAL_ACTION")

    return {
        "review_id": item["review_id"],
        "requested_action": action,
        "current_status": item["status"],
        "category_valid": category_valid,
        "duplicate_found": duplicate_found,
        "protected_target": protected,
        "target": target,
        "errors": list(dict.fromkeys(errors)),
        "valid": item["status"] == ReviewStatus.PENDING.value and not errors,
        "would_call": "memory-add" if action == ProposedAction.WRITE.value else "memory-update",
        "would_modify_formal_memory": not errors,
    }


def approve_review_item(
    review_id: str,
    *,
    action: str,
    target: str | None = None,
    dry_run: bool = False,
    home: Path | None = None,
    config: dict | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    action = action.upper()
    paths = get_review_queue_paths(home, config)
    if dry_run:
        item = load_review_item(review_id, home=home, config=config)
        return item, revalidate_review_approval(item, action=action, target=target)

    with review_queue_lock(paths):
        item = load_review_item(review_id, home=home, config=config)
        if item["status"] == ReviewStatus.APPROVED.value:
            return item, {"valid": True, "already_approved": True}
        if item["status"] != ReviewStatus.PENDING.value:
            raise ValueError(f"Review item is not pending: {item['status']}")
        validation = revalidate_review_approval(item, action=action, target=target)
        if not validation["valid"]:
            error = ", ".join(validation["errors"])
            item["last_error"] = error
            item["updated_at"] = _now()
            atomic_write_review_json(_item_path(paths, review_id), item)
            append_review_event(
                paths,
                "review_approval_failed",
                review_id=review_id,
                error=error,
            )
            raise ValueError(error)

        from hermes_cli.memory_router import (
            allocate_memory_id,
            create_memory_item,
            update_memory_item,
        )

        candidate = _candidate_from_item(item)
        if action == ProposedAction.WRITE.value:
            memory_id = allocate_memory_id(candidate.category)
            memory, _index = create_memory_item(
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
        else:
            memory = update_memory_item(
                SimpleNamespace(
                    memory_id=target,
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
        now = _now()
        item["status"] = ReviewStatus.APPROVED.value
        item["updated_at"] = now
        item["approval"] = {
            "approved_at": now,
            "action": action,
            "memory_id": memory.memory_id,
        }
        item["last_error"] = None
        atomic_write_review_json(_item_path(paths, review_id), item)
        append_review_event(
            paths,
            "review_approved",
            review_id=review_id,
            action=action,
            memory_id=memory.memory_id,
        )
        return item, validation


def get_review_queue_summary(
    *,
    home: Path | None = None,
    config: dict | None = None,
) -> dict[str, Any]:
    cfg = get_review_queue_config(config)
    paths = get_review_queue_paths(home, config)
    result = list_review_items(include_all=True, limit=10000, home=home, config=config)
    pending = sum(1 for item in result.items if item.get("status") == "pending")
    return {
        "available": True,
        "enabled": cfg.enabled,
        "path": paths.root,
        "initialized": paths.root.exists(),
        "pending": pending,
        "max_pending": cfg.max_pending,
        "exact_dedup": cfg.exact_dedup,
        "warnings": result.warnings,
    }


def format_review_item(item: dict[str, Any]) -> str:
    candidate = item["candidate"]
    evaluation = item["evaluation"]
    lines = [
        "Memory Review Item",
        "────────────────────────────────────────",
        f"Review ID: {item['review_id']}",
        f"Status: {item['status']}",
        f"Created: {item['created_at']}",
        f"Updated: {item['updated_at']}",
        f"Last seen: {item['last_seen_at']}",
        f"Occurrences: {item['occurrence_count']}",
        f"Original decision: {item['original_decision']}",
        f"Proposed action: {item['proposed_action']}",
        "",
        "Candidate:",
        f"title: {candidate['title']}",
        f"summary: {candidate['summary']}",
        f"category: {candidate['category']}",
        f"tags: {', '.join(candidate['tags'])}",
        "",
        "Evaluation:",
        f"score: {evaluation['score']}",
        f"title similarity: {evaluation['title_similarity']:.0%}",
        f"summary similarity: {evaluation['summary_similarity']:.0%}",
        f"combined similarity: {evaluation['combined_similarity']:.0%}",
        f"tag overlap: {', '.join(evaluation['tag_overlap']) or 'none'}",
        f"core tag overlap: {', '.join(evaluation['core_tag_overlap']) or 'none'}",
        f"protected target: {'yes' if evaluation['protected_target'] else 'no'}",
        "reason codes:",
        *[f"- {code}" for code in evaluation["reason_codes"]],
    ]
    if item.get("matched_memory"):
        lines.extend(
            [
                "",
                "Matched memory:",
                f"id: {item['matched_memory']['memory_id']}",
                f"title: {item['matched_memory']['title']}",
                f"category: {item['matched_memory']['category']}",
            ]
        )
    if item.get("approval"):
        lines.extend(["", "Approval:", json.dumps(item["approval"], ensure_ascii=False)])
    if item.get("rejection"):
        lines.extend(["", "Rejection:", json.dumps(item["rejection"], ensure_ascii=False)])
    return "\n".join(lines) + "\n"


def cmd_memory_review_list(args) -> None:
    status = None if args.all else args.status
    result = list_review_items(
        status=status,
        include_all=args.all,
        limit=args.limit,
    )
    if args.format == "json":
        print(json.dumps({"items": result.items, "warnings": result.warnings}, ensure_ascii=False, indent=2))
        return
    if not result.items:
        print("No pending memory reviews." if not args.all and status == "pending" else "No memory reviews.")
    else:
        print()
        print("Memory Review Queue")
        print("────────────────────────────────────────")
        print(f"Items: {len(result.items)}")
        for item in result.items:
            candidate = item["candidate"]
            print()
            print(item["review_id"])
            print(f"status: {item['status']}")
            print(f"action: {item['proposed_action']}")
            print(f"score: {item['evaluation']['score']}")
            print(f"category: {candidate['category']}")
            print(f"title: {candidate['title']}")
            print(f"occurrences: {item['occurrence_count']}")
            matched = item.get("matched_memory") or {}
            print(f"matched: {matched.get('memory_id') or 'none'}")
            print(f"reasons: {', '.join(item['evaluation']['reason_codes'])}")
    for warning in result.warnings:
        print(f"WARN {warning}", file=sys.stderr)


def cmd_memory_review_show(args) -> None:
    try:
        item = load_review_item(args.review_id)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        sys.exit(1)
    if args.format == "json":
        print(json.dumps(item, ensure_ascii=False, indent=2))
    else:
        print(format_review_item(item))


def cmd_memory_review_enqueue(args) -> None:
    from agent.runtime_memory_writer import evaluate_memory_auto_write
    from hermes_cli.config import load_config_readonly

    config = load_config_readonly()
    evaluation = evaluate_memory_auto_write(args.message, config=config, write=False)
    if args.dry_run:
        result = {
            "decision": evaluation.decision.value,
            "would_enqueue": should_enqueue_evaluation(
                evaluation,
                get_review_queue_config(config),
            ),
            "reason_codes": evaluation.reason_codes,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else "\n".join(
            [
                "Memory Review Enqueue Dry Run",
                f"Decision: {result['decision']}",
                f"Would enqueue: {'yes' if result['would_enqueue'] else 'no'}",
                f"Reason codes: {', '.join(result['reason_codes'])}",
            ]
        ))
        return
    item, created, message = enqueue_review_item(
        evaluation,
        source_kind=args.source,
        config=config,
        require_enabled=False,
    )
    result = {
        "decision": evaluation.decision.value,
        "enqueued": item is not None,
        "created": created,
        "review_id": item.get("review_id") if item else None,
        "message": message,
        "reason_codes": evaluation.reason_codes,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.format == "json" else "\n".join(
        [
            f"Decision: {result['decision']}",
            f"Enqueued: {'yes' if result['enqueued'] else 'no'}",
            f"Review ID: {result['review_id'] or 'none'}",
            f"Result: {message}",
        ]
    ))


def cmd_memory_review_reject(args) -> None:
    try:
        item, changed = reject_review_item(args.review_id, args.reason)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        sys.exit(1)
    if not changed:
        print("Review item already rejected.")
    print("Memory review rejected")
    print(f"review_id: {item['review_id']}")
    print(f"status: {item['status']}")
    print(f"reason: {item['rejection']['reason']}")


def cmd_memory_review_approve(args) -> None:
    try:
        item, validation = approve_review_item(
            args.review_id,
            action=args.action,
            target=args.target,
            dry_run=args.dry_run,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        sys.exit(1)
    if args.dry_run:
        print("Approval Dry Run")
        print("────────────────────────────────────────")
        print(f"Review ID: {item['review_id']}")
        print(f"Requested action: {args.action.upper()}")
        print(f"Current status: {item['status']}")
        print(f"Category valid: {'yes' if validation['category_valid'] else 'no'}")
        print(f"Duplicate found: {'yes' if validation['duplicate_found'] else 'no'}")
        print(f"Protected target: {'yes' if validation['protected_target'] else 'no'}")
        print(f"Errors: {', '.join(validation['errors']) or 'none'}")
        print(f"Would call: {validation['would_call']}")
        print(f"Would modify formal memory: {'yes' if validation['would_modify_formal_memory'] else 'no'}")
        print("Dry-run performed: yes")
        print("Files modified: no")
        return
    if validation.get("already_approved"):
        print("Review item already approved.")
    print("Memory review approved")
    print(f"review_id: {item['review_id']}")
    print(f"status: {item['status']}")
    print(f"memory_id: {(item.get('approval') or {}).get('memory_id', '')}")
