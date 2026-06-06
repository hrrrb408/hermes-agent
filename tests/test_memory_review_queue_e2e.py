"""End-to-end tests for Memory Review Queue approval in an isolated home."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.memory_review_queue import (
    ReviewStatus,
    approve_review_item,
    enqueue_review_item,
    load_review_item,
    reject_review_item,
)
from agent.runtime_memory_writer import (
    MemoryCandidate,
    MemoryDecision,
    MemoryEvaluation,
    ScoreEntry,
)
from hermes_cli.memory_router import (
    MemoryItem,
    create_memory_item,
    find_item,
    list_items,
    parse_index,
    parse_root_sections,
    validate_memory,
    write_root_categories,
)
from hermes_constants import get_hermes_home


ROOT = """# Hermes Memory Root Router

## hermes

- index: memory://indexes/hermes.md
- scope: project
- priority: P0
- status: active
- keywords: hermes, gateway, memory, runtime, review
- description: Hermes project development memories.

## projects

- index: memory://indexes/projects.md
- scope: project
- priority: P1
- status: active
- keywords: project, development
- description: General project memories.
"""

INDEX_HEADER = """# Hermes Memory Index

This file stores category-level memory indexes for Hermes project memories.
"""

EXISTING_ITEMS = [
    MemoryItem(
        memory_id="MEM-HERMES-010",
        title="Hermes Review Queue Initial Implementation",
        category="hermes",
        fields={
            "type": "project_progress",
            "importance": "P1",
            "ttl": "project",
            "status": "active",
            "tags": "hermes, review-queue, approval, workflow",
            "storage": "memory://records/projects/hermes/existing-update-target.md",
            "created_at": "2026-06-01",
            "updated_at": "2026-06-01",
            "summary": "Hermes review queue supports pending candidate storage and manual approval workflow.",
        },
    ),
    MemoryItem(
        memory_id="MEM-HERMES-011",
        title="Hermes Protected P0 Architecture",
        category="hermes",
        fields={
            "type": "architecture_decision",
            "importance": "P0",
            "ttl": "project",
            "status": "active",
            "tags": "hermes, protected-p0, architecture",
            "storage": "memory://records/projects/hermes/protected-p0.md",
            "created_at": "2026-06-01",
            "updated_at": "2026-06-01",
            "summary": "Hermes protected P0 architecture remains stable and requires explicit manual changes.",
        },
    ),
    MemoryItem(
        memory_id="MEM-HERMES-012",
        title="Hermes Protected Permanent Architecture",
        category="hermes",
        fields={
            "type": "architecture_decision",
            "importance": "P1",
            "ttl": "permanent",
            "status": "active",
            "tags": "hermes, protected-permanent, architecture",
            "storage": "memory://records/projects/hermes/protected-permanent.md",
            "created_at": "2026-06-01",
            "updated_at": "2026-06-01",
            "summary": "Hermes protected permanent architecture remains stable and requires explicit manual changes.",
        },
    ),
]


def _render_index(items: list[MemoryItem]) -> str:
    parts = [INDEX_HEADER.rstrip()]
    for item in items:
        fields = item.fields
        parts.extend(
            [
                "",
                f"## {item.memory_id} {item.title}",
                "",
                f"- type: {fields['type']}",
                f"- importance: {fields['importance']}",
                f"- ttl: {fields['ttl']}",
                f"- status: {fields['status']}",
                f"- tags: {fields['tags']}",
                f"- storage: {fields['storage']}",
                f"- created_at: {fields['created_at']}",
                f"- updated_at: {fields['updated_at']}",
                f"- summary: {fields['summary']}",
            ]
        )
    return "\n".join(parts) + "\n"


def _render_record(item: MemoryItem) -> str:
    fields = item.fields
    return f"""# {item.memory_id} {item.title}

## Summary

{fields['summary']}

## Details

{fields['summary']}

## Metadata

- category: {item.category}
- type: {fields['type']}
- importance: {fields['importance']}
- ttl: {fields['ttl']}
- status: {fields['status']}
- tags: {fields['tags']}
- created_at: {fields['created_at']}
- updated_at: {fields['updated_at']}
"""


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "hermes-review-e2e"
    for name in (
        "HERMES_MEMORY_AUTO_WRITE",
        "HERMES_MEMORY_AUTO_UPDATE",
        "HERMES_MEMORY_REVIEW_QUEUE",
        "HERMES_MEMORY_AUTO_CREATE_CATEGORIES",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HERMES_HOME", str(home))
    for name in (
        "memory/indexes",
        "memory/records/projects/hermes",
        "memory/snapshots",
        "memory/reviews/items",
        "sessions",
    ):
        (home / name).mkdir(parents=True, exist_ok=True)
    (home / "MEMORY.md").write_text(ROOT, encoding="utf-8")
    (home / "memory/indexes/hermes.md").write_text(
        _render_index(EXISTING_ITEMS),
        encoding="utf-8",
    )
    (home / "memory/indexes/projects.md").write_text(
        "# Projects Memory Index\n",
        encoding="utf-8",
    )
    for item in EXISTING_ITEMS:
        relative = item.fields["storage"].removeprefix("memory://")
        (home / "memory" / relative).write_text(_render_record(item), encoding="utf-8")
    (home / "memory/events.jsonl").write_text("", encoding="utf-8")
    (home / "memory/reviews/events.jsonl").write_text("", encoding="utf-8")
    (home / "config.yaml").write_text(
        "memory:\n  auto_write:\n    enabled: false\n  review_queue:\n    enabled: false\n",
        encoding="utf-8",
    )

    assert get_hermes_home().resolve() == home.resolve()
    assert home.resolve() != Path("/Users/huangruibang/Code/hermes-home-dev").resolve()
    assert validate_memory(home).ok
    return home


def _evaluation(
    candidate: MemoryCandidate,
    *,
    decision: MemoryDecision = MemoryDecision.REVIEW,
    matched: MemoryItem | None = None,
) -> MemoryEvaluation:
    return MemoryEvaluation(
        candidate=candidate,
        score=90,
        score_breakdown=[ScoreEntry("e2e_fixture", 90)],
        decision=decision,
        reason_codes=["E2E_REVIEW_REQUIRED"],
        reasons=["Created by isolated E2E fixture."],
        matched_memory_id=matched.memory_id if matched else None,
        matched_memory_title=matched.title if matched else None,
        matched_memory_category=matched.category if matched else None,
        similarity=0.95 if matched else 0.0,
        title_similarity=0.95 if matched else 0.0,
        summary_similarity=0.95 if matched else 0.0,
        combined_similarity=0.95 if matched else 0.0,
        tag_overlap=["hermes", "review-queue", "approval"] if matched else [],
        core_tag_overlap=["review-queue", "approval"] if matched else [],
        protected_target=False,
    )


def _enqueue(
    home: Path,
    candidate: MemoryCandidate,
    *,
    decision: MemoryDecision = MemoryDecision.REVIEW,
    matched: MemoryItem | None = None,
) -> str:
    item, created, _message = enqueue_review_item(
        _evaluation(candidate, decision=decision, matched=matched),
        home=home,
        require_enabled=False,
    )
    assert item is not None and created
    return item["review_id"]


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _formal_hash(home: Path) -> str:
    digest = hashlib.sha256()
    paths = [home / "MEMORY.md", home / "memory/events.jsonl"]
    paths.extend(sorted((home / "memory/indexes").rglob("*.md")))
    paths.extend(sorted((home / "memory/records").rglob("*.md")))
    for path in paths:
        digest.update(str(path.relative_to(home)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_candidate() -> MemoryCandidate:
    return MemoryCandidate(
        title="Hermes Review Queue End-to-End Approval Completed",
        summary="Hermes completed isolated end-to-end approval validation for the memory review queue.",
        category="hermes",
        tags=["hermes", "review-queue", "e2e", "approval"],
        memory_type="project_progress",
        importance="P1",
        ttl="project",
    )


def _update_candidate() -> MemoryCandidate:
    return MemoryCandidate(
        title="Hermes Review Queue Initial Implementation",
        summary="Hermes review queue supports pending candidate storage and manual approval workflow with safe rejection.",
        category="hermes",
        tags=["hermes", "review-queue", "approval", "workflow", "rejection"],
        memory_type="project_progress",
        importance="P1",
        ttl="project",
    )


def test_real_write_approval_and_idempotency(isolated_home: Path) -> None:
    review_id = _enqueue(
        isolated_home,
        _write_candidate(),
        decision=MemoryDecision.WRITE,
    )
    before_events = len(_read_jsonl(isolated_home / "memory/events.jsonl"))

    approved, validation = approve_review_item(
        review_id,
        action="write",
        dry_run=False,
        home=isolated_home,
    )

    assert validation["valid"]
    assert approved["status"] == "approved"
    assert approved["approval"]["action"] == "WRITE"
    assert approved["approval"]["memory_id"] == "MEM-HERMES-013"
    created = find_item("MEM-HERMES-013", isolated_home)
    assert created is not None
    assert created.title == _write_candidate().title
    record = isolated_home / "memory/records/projects/hermes/mem-hermes-013.md"
    assert record.exists()
    assert _write_candidate().title in record.read_text(encoding="utf-8")
    assert _write_candidate().summary in record.read_text(encoding="utf-8")
    assert len(_read_jsonl(isolated_home / "memory/events.jsonl")) == before_events + 1
    assert _read_jsonl(isolated_home / "memory/events.jsonl")[-1]["action"] == "memory_create"
    review_events = _read_jsonl(isolated_home / "memory/reviews/events.jsonl")
    assert review_events[-1]["event"] == "review_approved"
    assert review_events[-1]["memory_id"] == "MEM-HERMES-013"
    assert validate_memory(isolated_home).ok
    assert any(item.memory_id == "MEM-HERMES-013" for item in list_items(isolated_home, include_all=True))

    counts = (
        len(parse_index("hermes", isolated_home)),
        len(list((isolated_home / "memory/records/projects/hermes").glob("*.md"))),
        len(_read_jsonl(isolated_home / "memory/events.jsonl")),
    )
    again, second = approve_review_item(
        review_id,
        action="write",
        dry_run=False,
        home=isolated_home,
    )
    assert second["already_approved"]
    assert again["approval"]["memory_id"] == "MEM-HERMES-013"
    assert counts == (
        len(parse_index("hermes", isolated_home)),
        len(list((isolated_home / "memory/records/projects/hermes").glob("*.md"))),
        len(_read_jsonl(isolated_home / "memory/events.jsonl")),
    )


def test_real_update_approval_and_idempotency(isolated_home: Path) -> None:
    target = find_item("MEM-HERMES-010", isolated_home)
    assert target is not None
    review_id = _enqueue(isolated_home, _update_candidate(), matched=target)
    snapshots_before = len(list((isolated_home / "memory/snapshots").iterdir()))

    approved, validation = approve_review_item(
        review_id,
        action="update",
        target="MEM-HERMES-010",
        dry_run=False,
        home=isolated_home,
    )

    assert validation["valid"]
    assert approved["approval"] == {
        "approved_at": approved["approval"]["approved_at"],
        "action": "UPDATE",
        "memory_id": "MEM-HERMES-010",
    }
    updated = find_item("MEM-HERMES-010", isolated_home)
    assert updated is not None
    assert updated.fields["summary"] == _update_candidate().summary
    assert "rejection" in updated.fields["tags"]
    assert updated.fields["updated_at"] != "2026-06-01"
    assert len([item for item in parse_index("hermes", isolated_home) if item.memory_id == "MEM-HERMES-010"]) == 1
    record = isolated_home / "memory/records/projects/hermes/existing-update-target.md"
    assert _update_candidate().summary in record.read_text(encoding="utf-8")
    assert len(list((isolated_home / "memory/snapshots").iterdir())) > snapshots_before
    assert _read_jsonl(isolated_home / "memory/events.jsonl")[-1]["action"] == "memory_update"
    assert validate_memory(isolated_home).ok

    stable = (
        record.read_text(encoding="utf-8"),
        len(list((isolated_home / "memory/snapshots").iterdir())),
        len(_read_jsonl(isolated_home / "memory/events.jsonl")),
    )
    again, second = approve_review_item(
        review_id,
        action="update",
        target="MEM-HERMES-010",
        dry_run=False,
        home=isolated_home,
    )
    assert second["already_approved"]
    assert again["approval"]["memory_id"] == "MEM-HERMES-010"
    assert stable == (
        record.read_text(encoding="utf-8"),
        len(list((isolated_home / "memory/snapshots").iterdir())),
        len(_read_jsonl(isolated_home / "memory/events.jsonl")),
    )


@pytest.mark.parametrize(
    ("target_id", "reason"),
    [
        ("MEM-HERMES-011", "TARGET_P0_PROTECTED"),
        ("MEM-HERMES-012", "TARGET_PERMANENT_PROTECTED"),
        ("MEM-HERMES-999", "UPDATE_TARGET_NOT_FOUND"),
    ],
)
def test_protected_or_missing_update_stays_pending(
    isolated_home: Path,
    target_id: str,
    reason: str,
) -> None:
    target = find_item(target_id, isolated_home)
    candidate = MemoryCandidate(
        title=target.title if target else "Missing target",
        summary=target.fields["summary"] if target else "Missing target update",
        category="hermes",
        tags=(target.fields["tags"].split(", ") if target else ["hermes", "review-queue"]),
        memory_type="project_progress",
        importance="P1",
        ttl="project",
    )
    review_id = _enqueue(isolated_home, candidate, matched=target)
    before = _formal_hash(isolated_home)

    with pytest.raises(ValueError, match=reason):
        approve_review_item(
            review_id,
            action="update",
            target=target_id,
            home=isolated_home,
        )

    item = load_review_item(review_id, home=isolated_home)
    assert item["status"] == "pending"
    assert item["approval"] is None
    assert reason in item["last_error"]
    assert _formal_hash(isolated_home) == before
    assert _read_jsonl(isolated_home / "memory/reviews/events.jsonl")[-1]["event"] == "review_approval_failed"
    assert validate_memory(isolated_home).ok


def test_archived_category_and_became_duplicate(isolated_home: Path) -> None:
    archived_review = _enqueue(isolated_home, _write_candidate())
    categories = parse_root_sections(isolated_home)
    categories[0].fields["status"] = "archived"
    write_root_categories(categories, isolated_home)
    before = _formal_hash(isolated_home)
    with pytest.raises(ValueError, match="CATEGORY_NOT_ACTIVE_OR_MISSING"):
        approve_review_item(
            archived_review,
            action="write",
            home=isolated_home,
        )
    assert load_review_item(archived_review, home=isolated_home)["status"] == "pending"
    assert _formal_hash(isolated_home) == before

    categories[0].fields["status"] = "active"
    write_root_categories(categories, isolated_home)
    duplicate_candidate = MemoryCandidate(
        title="Future duplicate",
        summary="Future duplicate formal memory",
        category="hermes",
        tags=["hermes", "review-queue", "duplicate"],
        memory_type="project_progress",
        importance="P1",
        ttl="project",
    )
    duplicate_review = _enqueue(isolated_home, duplicate_candidate)
    create_memory_item(
        SimpleNamespace(
            category="hermes",
            memory_id="MEM-HERMES-013",
            title=duplicate_candidate.title,
            type=duplicate_candidate.memory_type,
            importance=duplicate_candidate.importance,
            ttl=duplicate_candidate.ttl,
            tags=", ".join(duplicate_candidate.tags),
            summary=duplicate_candidate.summary,
            body=duplicate_candidate.summary,
            record_path=None,
        )
    )
    count_before = len(parse_index("hermes", isolated_home))
    with pytest.raises(ValueError, match="BECAME_DUPLICATE"):
        approve_review_item(
            duplicate_review,
            action="write",
            home=isolated_home,
        )
    duplicate_item = load_review_item(duplicate_review, home=isolated_home)
    assert duplicate_item["status"] == "rejected"
    assert duplicate_item["rejection"]["reason"] == "became_duplicate"
    assert len(parse_index("hermes", isolated_home)) == count_before


def test_formal_write_failure_rolls_back_review_state(
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review_id = _enqueue(isolated_home, _write_candidate())
    before = _formal_hash(isolated_home)

    def fail_create(_args):
        raise RuntimeError("simulated create failure")

    monkeypatch.setattr("hermes_cli.memory_router.create_memory_item", fail_create)
    with pytest.raises(RuntimeError, match="simulated create failure"):
        approve_review_item(review_id, action="write", home=isolated_home)

    item = load_review_item(review_id, home=isolated_home)
    assert item["status"] == "pending"
    assert item["approval"] is None
    assert "simulated create failure" in item["last_error"]
    assert _formal_hash(isolated_home) == before
    assert _read_jsonl(isolated_home / "memory/reviews/events.jsonl")[-1]["event"] == "review_approval_failed"


def test_rejected_state_and_dry_runs_do_not_modify(isolated_home: Path) -> None:
    write_review = _enqueue(isolated_home, _write_candidate())
    target = find_item("MEM-HERMES-010", isolated_home)
    assert target is not None
    update_review = _enqueue(isolated_home, _update_candidate(), matched=target)
    before = _formal_hash(isolated_home)
    review_events_before = len(_read_jsonl(isolated_home / "memory/reviews/events.jsonl"))

    write_item, write_validation = approve_review_item(
        write_review,
        action="write",
        dry_run=True,
        home=isolated_home,
    )
    update_item, update_validation = approve_review_item(
        update_review,
        action="update",
        target="MEM-HERMES-010",
        dry_run=True,
        home=isolated_home,
    )
    assert write_item["status"] == update_item["status"] == "pending"
    assert write_validation["valid"] and update_validation["valid"]
    assert _formal_hash(isolated_home) == before
    assert len(_read_jsonl(isolated_home / "memory/reviews/events.jsonl")) == review_events_before

    rejected, changed = reject_review_item(
        write_review,
        "not durable",
        home=isolated_home,
    )
    assert changed and rejected["status"] == "rejected"
    after_reject = _formal_hash(isolated_home)
    with pytest.raises(ValueError, match="not pending"):
        approve_review_item(write_review, action="write", home=isolated_home)
    assert _formal_hash(isolated_home) == after_reject


def test_review_and_formal_events_are_valid_json(isolated_home: Path) -> None:
    review_id = _enqueue(isolated_home, _write_candidate(), decision=MemoryDecision.WRITE)
    approve_review_item(review_id, action="write", home=isolated_home)

    for event in _read_jsonl(isolated_home / "memory/reviews/events.jsonl"):
        assert event["time"]
        assert event["event"]
        assert event["review_id"]
        serialized = json.dumps(event).lower()
        assert "api_key" not in serialized
        assert "cookie" not in serialized
        assert "assistant_response" not in serialized
        if event["event"] == "review_approved":
            assert event["action"] == "WRITE"
            assert event["memory_id"] == "MEM-HERMES-013"

    formal_events = _read_jsonl(isolated_home / "memory/events.jsonl")
    assert formal_events[-1]["action"] == "memory_create"
    assert formal_events[-1]["memory_id"] == "MEM-HERMES-013"
    assert formal_events[-1]["category"] == "hermes"


def test_concurrent_write_approval_creates_one_memory(isolated_home: Path) -> None:
    review_id = _enqueue(
        isolated_home,
        _write_candidate(),
        decision=MemoryDecision.WRITE,
    )
    results: list[tuple[dict, dict]] = []
    errors: list[Exception] = []

    def approve() -> None:
        try:
            results.append(
                approve_review_item(
                    review_id,
                    action="write",
                    home=isolated_home,
                )
            )
        except Exception as exc:  # pragma: no cover - assertion reports details
            errors.append(exc)

    threads = [threading.Thread(target=approve) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    assert len(results) == 2
    assert sum(1 for _item, result in results if result.get("already_approved")) == 1
    assert len([item for item in parse_index("hermes", isolated_home) if item.memory_id == "MEM-HERMES-013"]) == 1
    assert len(
        [
            event
            for event in _read_jsonl(isolated_home / "memory/events.jsonl")
            if event.get("action") == "memory_create"
        ]
    ) == 1
    assert validate_memory(isolated_home).ok
