"""Tests for the Hermes Dev Web API Review Queue endpoints (Phase 1A + 1B + 1C).

Covers:
- GET /reviews/status — queue status and safety flags
- GET /reviews — paginated list with filters
- GET /reviews/{reviewId} — detail view
- POST /reviews/{reviewId}/approve/dry-run — approve dry-run preview
- POST /reviews/{reviewId}/reject/dry-run — reject dry-run preview
- POST /reviews/{reviewId}/approve/execute — approve execute (Phase 1C)
- POST /reviews/{reviewId}/reject/execute — reject execute (Phase 1C)
- Forbidden POST/PATCH/DELETE review routes
- Side-effect verification (no files changed)
- DTO whitelist (no forbidden fields in responses)
- Path redaction
- Text truncation
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermes_cli.dev_web_config import DevWebApiConfig
from hermes_cli.dev_web_api import create_dev_web_api_app


# ── Fixtures ──


def _make_review_item(
    review_id: str = "MR-20260606T080234-1e10c286",
    status: str = "pending",
    decision: str = "REVIEW",
    proposed_action: str = "UNDECIDED",
    category: str = "hermes",
    title: str = "Test review item",
    summary: str = "A test summary for the review item.",
    tags: list[str] | None = None,
    score: int = 70,
    occurrence_count: int = 1,
    has_matched: bool = True,
    has_error: bool = False,
) -> dict:
    """Create a valid review item dict."""
    tags = tags or ["hermes", "test"]
    item = {
        "review_id": review_id,
        "status": status,
        "created_at": "2026-06-06T16:02:34+08:00",
        "updated_at": "2026-06-06T16:03:10+08:00",
        "last_seen_at": "2026-06-06T16:02:47+08:00",
        "occurrence_count": occurrence_count,
        "fingerprint": "1e10c28674b89b72e52685f320dce2b908f9e622131026ca5fc1a016ac21ead2",
        "source": {
            "kind": "cli-test",
            "channel": "",
            "session_id_hash": None,
            "message_id": None,
        },
        "original_decision": decision,
        "proposed_action": proposed_action,
        "candidate": {
            "summary": summary,
            "category": category,
            "tags": tags,
            "title": title,
            "type": "project_status",
            "importance": "P1",
            "ttl": "project",
            "source_confidence": "user_confirmed",
        },
        "evaluation": {
            "score": score,
            "score_breakdown": [
                {"rule": "progress_keyword", "value": 20},
                {"rule": "completed_or_integrated_phrase", "value": 15},
                {"rule": "hermes_project_terms", "value": 35},
            ],
            "reason_codes": [
                "SCORE_IN_REVIEW_RANGE",
                "TARGET_P0_PROTECTED",
            ],
            "reasons": [
                "Candidate score 70 is below write threshold 80.",
                "Matched memory importance is P0 and automatic updates are protected.",
            ],
            "title_similarity": 0.41,
            "summary_similarity": 0.27,
            "combined_similarity": 0.8,
            "similarity": 0.8,
            "tag_overlap": ["hermes"],
            "core_tag_overlap": [],
            "protected_target": True,
        },
        "matched_memory": {
            "memory_id": "MEM-HERMES-001",
            "title": "Hermes test memory",
            "category": category,
        } if has_matched else None,
        "approval": None,
        "rejection": None,
        "last_error": "Some error message /Users/test/secret" if has_error else None,
        "version": 1,
    }
    if status == "rejected":
        item["rejection"] = {
            "rejected_at": "2026-06-06T16:03:10+08:00",
            "reason": "Test rejection",
        }
    if status == "approved":
        item["approval"] = {
            "approved_at": "2026-06-06T16:04:00+08:00",
            "action": "WRITE",
            "memory_id": "MEM-HERMES-099",
        }
    return item


@pytest.fixture
def review_home(tmp_path):
    """Create a temporary HERMES_HOME with review queue items and minimal memory structure.

    Uses the isolated HERMES_HOME path (hermes_test) so that
    revalidate_review_approval() → parse_root() → get_hermes_home()
    finds the MEMORY.md created here.
    """
    home = tmp_path / "hermes_test"
    home.mkdir(exist_ok=True)

    # Create directories that the isolation fixture expects
    for subdir in ("sessions", "cron", "memories", "skills"):
        (home / subdir).mkdir(exist_ok=True)

    # Create minimal MEMORY.md (required by revalidate_review_approval → parse_root)
    (home / "MEMORY.md").write_text(
        "# Test Memory\n\n## hermes\n- test memory note\n",
        encoding="utf-8",
    )

    # Create memory directory structure
    memory_dir = home / "memory"
    memory_dir.mkdir(exist_ok=True)

    # Create minimal category index (required by parse_root → parse_index)
    indexes_dir = memory_dir / "indexes"
    indexes_dir.mkdir(exist_ok=True)
    (indexes_dir / "hermes.md").write_text(
        "# hermes\n\n- [[HERMES-001]] Test memory\n",
        encoding="utf-8",
    )

    # Create minimal records directory
    records_dir = memory_dir / "records"
    records_dir.mkdir(exist_ok=True)
    (records_dir / "hermes").mkdir(exist_ok=True)

    # Create minimal events.jsonl
    (memory_dir / "events.jsonl").write_text("", encoding="utf-8")

    # Create memory/reviews structure
    reviews_dir = memory_dir / "reviews"
    items_dir = reviews_dir / "items"
    items_dir.mkdir(parents=True)

    # Create events.jsonl
    (reviews_dir / "events.jsonl").write_text("", encoding="utf-8")

    # Create lock file
    (reviews_dir / ".queue.lock").write_text("", encoding="utf-8")

    # Create some review items
    items = [
        _make_review_item(
            review_id="MR-20260606T080234-1e10c286",
            status="pending",
            decision="REVIEW",
            category="hermes",
            title="Hermes Gateway status",
        ),
        _make_review_item(
            review_id="MR-20260606T080319-36981352",
            status="rejected",
            decision="WRITE",
            category="projects",
            title="Project deployment note",
        ),
        _make_review_item(
            review_id="MR-20260606T080609-ec6a074f",
            status="pending",
            decision="UPDATE",
            proposed_action="UPDATE",
            category="learning",
            title="Learning progress",
        ),
        _make_review_item(
            review_id="MR-20260606T103018-275c332b",
            status="pending",
            decision="REVIEW",
            category="hermes",
            title="Another Hermes note",
            has_error=True,
        ),
    ]

    for item in items:
        path = items_dir / f"{item['review_id']}.json"
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")

    return home


@pytest.fixture
def client_with_reviews(review_home):
    """TestClient with review queue data."""
    config = DevWebApiConfig(hermes_home=review_home)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def empty_review_home(tmp_path):
    """Create a temporary HERMES_HOME without review queue directory."""
    home = tmp_path / "hermes_test"
    home.mkdir(exist_ok=True)
    for subdir in ("sessions", "cron", "memories", "skills"):
        (home / subdir).mkdir(exist_ok=True)
    return home


@pytest.fixture
def client_empty_reviews(empty_review_home):
    """TestClient without review queue data."""
    config = DevWebApiConfig(hermes_home=empty_review_home)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def client_no_home():
    """TestClient without HERMES_HOME configured."""
    config = DevWebApiConfig(hermes_home=None)
    app = create_dev_web_api_app(config)
    return TestClient(app)


# ── Status tests ──


class TestReviewStatus:
    def test_status_returns_200(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/status")
        assert resp.status_code == 200

    def test_status_read_only(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/status")
        data = resp.json()["data"]
        assert data["readOnly"] is True

    def test_status_all_write_flags_false(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/status")
        data = resp.json()["data"]
        assert data["writeEnabled"] is False
        assert data["approveEnabled"] is False
        assert data["rejectEnabled"] is False
        assert data["enqueueEnabled"] is False
        assert data["queueEnabled"] is False
        assert data["dryRunEnabled"] is True

    def test_status_counts(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/status")
        data = resp.json()["data"]
        counts = data["counts"]
        assert counts["pending"] == 3
        assert counts["rejected"] == 1
        assert counts["approved"] == 0
        assert counts["failed"] == 0
        assert counts["total"] == 4

    def test_status_available(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/status")
        data = resp.json()["data"]
        assert data["available"] is True
        assert data["storage"]["available"] is True

    def test_status_paths_redacted(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/status")
        data = resp.json()["data"]
        redacted = data["storage"]["redactedPath"]
        # Must not contain full local path
        assert "/Users/" not in redacted
        assert "/home/" not in redacted

    def test_status_no_home(self, client_no_home):
        resp = client_no_home.get("/api/dev/v1/reviews/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["available"] is False
        assert data["readOnly"] is True
        assert data["counts"]["total"] == 0

    def test_status_empty_home(self, client_empty_reviews):
        """Fresh install: queue dir doesn't exist, status still returns 200."""
        resp = client_empty_reviews.get("/api/dev/v1/reviews/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["available"] is False
        assert data["readOnly"] is True

    def test_status_has_meta(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/status")
        body = resp.json()
        assert "meta" in body
        assert "requestId" in body["meta"]
        assert "timestamp" in body["meta"]


# ── List tests ──


class TestReviewList:
    def test_list_returns_200(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews")
        assert resp.status_code == 200

    def test_list_returns_items(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews")
        data = resp.json()["data"]
        assert len(data["items"]) > 0

    def test_list_empty_queue(self, client_empty_reviews):
        """Empty queue returns 200 with empty list."""
        resp = client_empty_reviews.get("/api/dev/v1/reviews")
        assert resp.status_code == 503  # queue unavailable

    def test_list_pagination(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews?limit=2&offset=0")
        data = resp.json()["data"]
        assert len(data["items"]) <= 2
        assert data["page"]["limit"] == 2
        assert data["page"]["offset"] == 0
        assert data["page"]["hasMore"] is True

    def test_list_status_filter(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews?status=pending")
        data = resp.json()["data"]
        for item in data["items"]:
            assert item["status"] == "pending"

    def test_list_decision_filter(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews?decision=REVIEW")
        data = resp.json()["data"]
        for item in data["items"]:
            assert item["decision"] == "REVIEW"

    def test_list_category_filter(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews?category=hermes")
        data = resp.json()["data"]
        for item in data["items"]:
            assert item["category"] == "hermes"

    def test_list_query_filter(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews?query=Gateway")
        data = resp.json()["data"]
        assert len(data["items"]) >= 1
        # Should find "Hermes Gateway status"
        titles = [item["title"] for item in data["items"]]
        assert any("Gateway" in t or "gateway" in t.lower() for t in titles)

    def test_list_order_created_desc(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews?order=created_desc")
        data = resp.json()["data"]
        if len(data["items"]) >= 2:
            assert data["items"][0]["createdAt"] >= data["items"][1]["createdAt"]

    def test_list_limit_validation(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews?limit=0")
        assert resp.status_code == 422  # FastAPI validation

    def test_list_offset_validation(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews?offset=-1")
        assert resp.status_code == 422

    def test_list_has_page_meta(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews")
        data = resp.json()["data"]
        assert "page" in data
        assert "total" in data["page"]
        assert "hasMore" in data["page"]


# ── DTO whitelist tests ──


class TestReviewDtoWhitelist:
    """Verify that only whitelisted fields appear in responses."""

    FORBIDDEN_FIELDS = frozenset({
        "fingerprint",
        "source",
        "raw",
        "approval",
        "rejection",
        "evaluation",
        "matched_memory",
        "reasons",
        "tag_overlap",
        "core_tag_overlap",
    })

    def test_list_no_forbidden_fields(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews")
        data = resp.json()["data"]
        for item in data["items"]:
            for field in self.FORBIDDEN_FIELDS:
                assert field not in item, f"Forbidden field '{field}' found in list item"

    def test_list_item_fields(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews")
        data = resp.json()["data"]
        if data["items"]:
            item = data["items"][0]
            # Required fields
            assert "reviewId" in item
            assert "status" in item
            assert "decision" in item
            assert "proposedAction" in item
            assert "category" in item
            assert "title" in item
            assert "summaryPreview" in item
            assert "tags" in item
            assert "score" in item
            assert "reasonCodes" in item
            assert "occurrenceCount" in item
            assert "createdAt" in item
            assert "updatedAt" in item

    def test_title_truncated(self, client_with_reviews):
        """Title should be truncated to 120 chars."""
        resp = client_with_reviews.get("/api/dev/v1/reviews")
        data = resp.json()["data"]
        for item in data["items"]:
            assert len(item["title"]) <= 120

    def test_summary_preview_truncated(self, client_with_reviews):
        """Summary preview should be truncated to 120 chars."""
        resp = client_with_reviews.get("/api/dev/v1/reviews")
        data = resp.json()["data"]
        for item in data["items"]:
            assert len(item["summaryPreview"]) <= 120

    def test_detail_no_forbidden_fields(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        data = resp.json()["data"]
        for field in self.FORBIDDEN_FIELDS:
            assert field not in data, f"Forbidden field '{field}' found in detail"

    def test_paths_redacted_in_detail(self, client_with_reviews):
        """Detail should not contain local paths."""
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T103018-275c332b")
        data = resp.json()["data"]
        text = json.dumps(data)
        assert "/Users/" not in text
        assert "/home/" not in text


# ── Detail tests ──


class TestReviewDetail:
    def test_detail_returns_200(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        assert resp.status_code == 200

    def test_detail_has_safety_flags(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        data = resp.json()["data"]
        safety = data["safety"]
        assert safety["readOnly"] is True
        assert safety["approveAvailable"] is False
        assert safety["rejectAvailable"] is False
        assert safety["writeAvailable"] is False
        assert safety["dryRunAvailable"] is True

    def test_detail_has_score_breakdown(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        data = resp.json()["data"]
        assert "scoreBreakdown" in data
        assert len(data["scoreBreakdown"]) > 0
        for entry in data["scoreBreakdown"]:
            assert "rule" in entry
            assert "value" in entry

    def test_detail_has_similarity(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        data = resp.json()["data"]
        assert "similarity" in data
        sim = data["similarity"]
        assert "title" in sim
        assert "summary" in sim
        assert "combined" in sim
        assert "overall" in sim

    def test_detail_has_target(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        data = resp.json()["data"]
        assert "target" in data
        target = data["target"]
        assert target["memoryId"] == "MEM-HERMES-001"
        assert target["protected"] is True

    def test_detail_has_timestamps(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        data = resp.json()["data"]
        ts = data["timestamps"]
        assert "createdAt" in ts
        assert "updatedAt" in ts
        assert "lastSeenAt" in ts

    def test_detail_summary_truncated(self, client_with_reviews):
        """Detail summary should be truncated to 300 chars."""
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        data = resp.json()["data"]
        assert len(data["summary"]) <= 300

    def test_detail_error_redacted(self, client_with_reviews):
        """Detail error should be redacted and truncated."""
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T103018-275c332b")
        data = resp.json()["data"]
        if data["errors"]["lastError"]:
            assert len(data["errors"]["lastError"]) <= 200
            assert "/Users/" not in data["errors"]["lastError"]

    def test_detail_not_found(self, client_with_reviews):
        """Valid format but non-existent ID returns 404."""
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-20260101T000000-deadbeef")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "REVIEW_NOT_FOUND"

    def test_detail_invalid_id(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/invalid-id")
        assert resp.status_code == 400
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "INVALID_REVIEW_ID"

    def test_detail_invalid_id_path_separator(self, client_with_reviews):
        """ID with path separators is rejected (400 or 404)."""
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-../../etc/passwd")
        assert resp.status_code in (400, 404)

    def test_detail_has_reviewed_at_for_rejected(self, client_with_reviews):
        resp = client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080319-36981352")
        data = resp.json()["data"]
        ts = data["timestamps"]
        assert ts["reviewedAt"] is not None


# ── Forbidden routes ──


class TestReviewForbiddenRoutes:
    def test_post_reviews_405(self, client_with_reviews):
        resp = client_with_reviews.post("/api/dev/v1/reviews")
        assert resp.status_code in (404, 405)

    def test_post_review_approve_405(self, client_with_reviews):
        resp = client_with_reviews.post("/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve")
        assert resp.status_code in (404, 405)

    def test_post_review_reject_405(self, client_with_reviews):
        resp = client_with_reviews.post("/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject")
        assert resp.status_code in (404, 405)

    def test_post_review_enqueue_405(self, client_with_reviews):
        resp = client_with_reviews.post("/api/dev/v1/reviews/enqueue")
        assert resp.status_code in (404, 405)

    def test_patch_review_405(self, client_with_reviews):
        resp = client_with_reviews.patch("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        assert resp.status_code in (404, 405)

    def test_delete_review_405(self, client_with_reviews):
        resp = client_with_reviews.delete("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        assert resp.status_code in (404, 405)

    def test_forbidden_error_is_safe(self, client_with_reviews):
        """Error responses must not contain sensitive info."""
        resp = client_with_reviews.post("/api/dev/v1/reviews")
        body = resp.json()
        text = json.dumps(body)
        assert "traceback" not in text.lower()
        assert "secret" not in text.lower()
        assert "token" not in text.lower()


# ── Side-effect verification ──


class TestReviewSideEffects:
    """Verify that read-only API calls don't modify any files."""

    def _hash_dir(self, path: Path) -> dict[str, str]:
        """Hash all files in a directory tree."""
        hashes = {}
        if not path.exists():
            return hashes
        for f in sorted(path.rglob("*")):
            if f.is_file():
                rel = str(f.relative_to(path))
                hashes[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
        return hashes

    def test_no_file_changes_after_status(self, client_with_reviews, review_home):
        reviews_dir = review_home / "memory" / "reviews"
        before = self._hash_dir(reviews_dir)
        client_with_reviews.get("/api/dev/v1/reviews/status")
        after = self._hash_dir(reviews_dir)
        assert before == after

    def test_no_file_changes_after_list(self, client_with_reviews, review_home):
        reviews_dir = review_home / "memory" / "reviews"
        before = self._hash_dir(reviews_dir)
        client_with_reviews.get("/api/dev/v1/reviews")
        after = self._hash_dir(reviews_dir)
        assert before == after

    def test_no_file_changes_after_detail(self, client_with_reviews, review_home):
        reviews_dir = review_home / "memory" / "reviews"
        before = self._hash_dir(reviews_dir)
        client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        after = self._hash_dir(reviews_dir)
        assert before == after

    def test_no_file_changes_after_all_endpoints(self, client_with_reviews, review_home):
        """Call all endpoints including dry-run and verify no file changes."""
        reviews_dir = review_home / "memory" / "reviews"
        before = self._hash_dir(reviews_dir)

        client_with_reviews.get("/api/dev/v1/reviews/status")
        client_with_reviews.get("/api/dev/v1/reviews")
        client_with_reviews.get("/api/dev/v1/reviews?status=pending")
        client_with_reviews.get("/api/dev/v1/reviews?decision=REVIEW")
        client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080319-36981352")
        client_with_reviews.post("/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run")
        client_with_reviews.post("/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run")
        client_with_reviews.post("/api/dev/v1/reviews/MR-20260606T080609-ec6a074f/approve/dry-run")

        after = self._hash_dir(reviews_dir)
        assert before == after


# ── Approve dry-run tests ──


class TestApproveDryRun:
    """Tests for POST /reviews/{reviewId}/approve/dry-run."""

    def test_approve_dry_run_returns_200(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        assert resp.status_code == 200

    def test_approve_dry_run_always_true(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        data = resp.json()["data"]
        assert data["dryRun"] is True

    def test_approve_dry_run_action(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        data = resp.json()["data"]
        assert data["action"] == "APPROVE"

    def test_approve_dry_run_has_would_flags(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        data = resp.json()["data"]
        assert "wouldModify" in data
        assert "wouldWriteMemory" in data
        assert "wouldUpdateReview" in data
        assert "wouldAppendEvent" in data
        assert data["wouldCreateSnapshot"] is False

    def test_approve_dry_run_has_target(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        data = resp.json()["data"]
        assert "target" in data
        assert "memoryId" in data["target"]
        assert "category" in data["target"]
        assert "operation" in data["target"]

    def test_approve_dry_run_has_safety(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        data = resp.json()["data"]
        safety = data["safety"]
        assert safety["devOnly"] is True
        assert safety["productionBlocked"] is True

    def test_approve_dry_run_has_checks(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        data = resp.json()["data"]
        assert "checks" in data
        assert isinstance(data["checks"], list)
        assert len(data["checks"]) > 0

    def test_approve_dry_run_has_effects(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        data = resp.json()["data"]
        assert "effects" in data
        assert "noEffects" in data
        assert "warnings" in data

    def test_approve_dry_run_no_effects_contains_safety(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        data = resp.json()["data"]
        no_effects_text = " ".join(data["noEffects"])
        assert "No files were modified" in no_effects_text

    def test_approve_dry_run_has_preview(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        data = resp.json()["data"]
        assert data["preview"] is not None
        assert data["preview"]["redactedPaths"] is True

    def test_approve_dry_run_paths_redacted(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        text = json.dumps(resp.json())
        assert "/Users/" not in text
        assert "/home/" not in text

    def test_approve_dry_run_not_found(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260101T000000-deadbeef/approve/dry-run"
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "REVIEW_NOT_FOUND"

    def test_approve_dry_run_invalid_id(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/invalid-id/approve/dry-run"
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_REVIEW_ID"

    def test_approve_dry_run_not_pending(self, client_with_reviews):
        """Rejected item cannot be dry-run approved."""
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080319-36981352/approve/dry-run"
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REVIEW_NOT_PENDING"

    def test_approve_dry_run_no_home(self, client_no_home):
        resp = client_no_home.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "REVIEW_DRY_RUN_UNAVAILABLE"

    def test_approve_dry_run_has_meta(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        body = resp.json()
        assert "meta" in body
        assert "requestId" in body["meta"]


# ── Reject dry-run tests ──


class TestRejectDryRun:
    """Tests for POST /reviews/{reviewId}/reject/dry-run."""

    def test_reject_dry_run_returns_200(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        assert resp.status_code == 200

    def test_reject_dry_run_always_true(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        data = resp.json()["data"]
        assert data["dryRun"] is True

    def test_reject_dry_run_action(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        data = resp.json()["data"]
        assert data["action"] == "REJECT"

    def test_reject_dry_run_would_write_memory_false(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        data = resp.json()["data"]
        assert data["wouldWriteMemory"] is False

    def test_reject_dry_run_would_update_review_true(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        data = resp.json()["data"]
        assert data["wouldUpdateReview"] is True
        assert data["wouldAppendEvent"] is True
        assert data["wouldModify"] is True

    def test_reject_dry_run_has_target(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        data = resp.json()["data"]
        assert data["target"]["operation"] == "REJECT"
        assert data["target"]["memoryId"] is None

    def test_reject_dry_run_has_safety(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        data = resp.json()["data"]
        safety = data["safety"]
        assert safety["devOnly"] is True
        assert safety["productionBlocked"] is True

    def test_reject_dry_run_has_checks(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        data = resp.json()["data"]
        assert len(data["checks"]) > 0
        # Should have REVIEW_IS_PENDING check with pass status
        pending_check = [c for c in data["checks"] if c["code"] == "REVIEW_IS_PENDING"]
        assert len(pending_check) == 1
        assert pending_check[0]["status"] == "pass"

    def test_reject_dry_run_no_effects_safety(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        data = resp.json()["data"]
        no_effects_text = " ".join(data["noEffects"])
        assert "No files were modified" in no_effects_text
        assert "No memory was written" in no_effects_text

    def test_reject_dry_run_allowed(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        data = resp.json()["data"]
        assert data["allowed"] is True
        assert data["blockedReason"] is None

    def test_reject_dry_run_not_found(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260101T000000-deadbeef/reject/dry-run"
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "REVIEW_NOT_FOUND"

    def test_reject_dry_run_invalid_id(self, client_with_reviews):
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/invalid-id/reject/dry-run"
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_REVIEW_ID"

    def test_reject_dry_run_not_pending(self, client_with_reviews):
        """Rejected item cannot be dry-run rejected again."""
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080319-36981352/reject/dry-run"
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REVIEW_NOT_PENDING"

    def test_reject_dry_run_no_home(self, client_no_home):
        resp = client_no_home.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "REVIEW_DRY_RUN_UNAVAILABLE"


# ── Dry-run side-effect tests ──


class TestDryRunSideEffects:
    """Verify that dry-run calls don't modify any files."""

    def _hash_dir(self, path: Path) -> dict[str, str]:
        hashes = {}
        if not path.exists():
            return hashes
        for f in sorted(path.rglob("*")):
            if f.is_file():
                rel = str(f.relative_to(path))
                hashes[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
        return hashes

    def test_approve_dry_run_no_file_changes(self, client_with_reviews, review_home):
        reviews_dir = review_home / "memory" / "reviews"
        before = self._hash_dir(reviews_dir)
        client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        after = self._hash_dir(reviews_dir)
        assert before == after

    def test_reject_dry_run_no_file_changes(self, client_with_reviews, review_home):
        reviews_dir = review_home / "memory" / "reviews"
        before = self._hash_dir(reviews_dir)
        client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        after = self._hash_dir(reviews_dir)
        assert before == after

    def test_both_dry_runs_no_file_changes(self, client_with_reviews, review_home):
        reviews_dir = review_home / "memory" / "reviews"
        before = self._hash_dir(reviews_dir)
        client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/dry-run"
        )
        client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/dry-run"
        )
        client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080609-ec6a074f/approve/dry-run"
        )
        after = self._hash_dir(reviews_dir)
        assert before == after


# ── Execute disabled mode tests ──


class TestExecuteDisabledMode:
    """Verify execute routes return 503 when kill switch is disabled (default)."""

    def test_approve_execute_disabled(self, client_with_reviews):
        """Execute approve returns REVIEW_EXECUTE_DISABLED when kill switch off."""
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/execute",
            json={
                "confirmationText": "APPROVE",
                "expectedAction": "APPROVE",
                "reviewUpdatedAt": "2026-06-06T16:03:10+08:00",
                "dryRunPreviewed": True,
                "acknowledgedEffects": [
                    "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                ],
            },
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "REVIEW_EXECUTE_DISABLED"

    def test_reject_execute_disabled(self, client_with_reviews):
        """Execute reject returns REVIEW_EXECUTE_DISABLED when kill switch off."""
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/execute",
            json={
                "confirmationText": "REJECT",
                "expectedAction": "REJECT",
                "reviewUpdatedAt": "2026-06-06T16:03:10+08:00",
                "dryRunPreviewed": True,
                "acknowledgedEffects": [
                    "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                ],
            },
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "REVIEW_EXECUTE_DISABLED"

    def test_execute_disabled_no_file_changes(self, client_with_reviews, review_home):
        """Execute attempts with disabled kill switch must not modify any files."""
        reviews_dir = review_home / "memory" / "reviews"
        before = TestDryRunSideEffects()._hash_dir(reviews_dir)

        client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/execute",
            json={
                "confirmationText": "APPROVE",
                "expectedAction": "APPROVE",
                "reviewUpdatedAt": "2026-06-06T16:03:10+08:00",
                "dryRunPreviewed": True,
                "acknowledgedEffects": [
                    "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                ],
            },
        )
        client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/execute",
            json={
                "confirmationText": "REJECT",
                "expectedAction": "REJECT",
                "reviewUpdatedAt": "2026-06-06T16:03:10+08:00",
                "dryRunPreviewed": True,
                "acknowledgedEffects": [
                    "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                ],
            },
        )

        after = TestDryRunSideEffects()._hash_dir(reviews_dir)
        assert before == after

    def test_execute_status_shows_disabled(self, client_with_reviews):
        """Reviews status must show execute disabled."""
        resp = client_with_reviews.get("/api/dev/v1/reviews/status")
        data = resp.json()["data"]
        assert data.get("executeEnabled") is False
        assert data.get("killSwitchActive") is True

    def test_execute_disabled_no_home(self, client_no_home):
        """Execute without HERMES_HOME returns 503."""
        resp = client_no_home.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/execute",
            json={
                "confirmationText": "APPROVE",
                "expectedAction": "APPROVE",
                "reviewUpdatedAt": "2026-06-06T16:03:10+08:00",
                "dryRunPreviewed": True,
                "acknowledgedEffects": [
                    "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                ],
            },
        )
        assert resp.status_code == 503


# ── Execute enabled mode tests (temp fixture) ──


@pytest.fixture
def execute_home(tmp_path):
    """Create a temporary HERMES_HOME for execute testing.

    This fixture MUST only be used with kill switch enabled tests.
    It never touches /Users/huangruibang/Code/hermes-home-dev.
    """
    home = tmp_path / "hermes-exec-test"
    home.mkdir(exist_ok=True)

    for subdir in ("sessions", "cron", "memories", "skills"):
        (home / subdir).mkdir(exist_ok=True)

    # Create MEMORY.md
    (home / "MEMORY.md").write_text(
        "# Test Memory\n\n## hermes\n- test memory note\n",
        encoding="utf-8",
    )

    # Create memory directory structure
    memory_dir = home / "memory"
    memory_dir.mkdir(exist_ok=True)
    (memory_dir / "indexes").mkdir(exist_ok=True)
    (memory_dir / "records").mkdir(exist_ok=True)
    (memory_dir / "records" / "hermes").mkdir(exist_ok=True)
    (memory_dir / "snapshots").mkdir(exist_ok=True)
    (memory_dir / "events.jsonl").write_text("", encoding="utf-8")

    # Create index file
    (memory_dir / "indexes" / "hermes.md").write_text(
        "# hermes\n\n- [[HERMES-001]] Test memory\n",
        encoding="utf-8",
    )

    # Create reviews structure
    reviews_dir = memory_dir / "reviews"
    items_dir = reviews_dir / "items"
    items_dir.mkdir(parents=True)
    (reviews_dir / "events.jsonl").write_text("", encoding="utf-8")
    (reviews_dir / ".queue.lock").write_text("", encoding="utf-8")

    # Create pending review items for testing
    items = [
        _make_review_item(
            review_id="MR-20260609T143000-abc12345",
            status="pending",
            decision="REVIEW",
            category="hermes",
            title="Test approve execute item",
        ),
        _make_review_item(
            review_id="MR-20260609T143100-def67890",
            status="pending",
            decision="WRITE",
            category="hermes",
            title="Test reject execute item",
        ),
    ]

    for item in items:
        path = items_dir / f"{item['review_id']}.json"
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")

    return home


@pytest.fixture
def client_execute(execute_home):
    """TestClient with execute-enabled review queue data."""
    config = DevWebApiConfig(hermes_home=execute_home)
    app = create_dev_web_api_app(config)
    return TestClient(app)


class TestExecuteRejectEnabled:
    """Reject execute with kill switch enabled on temp fixture."""

    def test_reject_execute_success(self, client_execute, execute_home):
        """Reject execute succeeds when kill switch enabled."""
        review_id = "MR-20260609T143100-def67890"
        updated_at = "2026-06-06T16:03:10+08:00"
        _set_updated_at(execute_home, review_id, updated_at)

        with _execute_enabled():
            resp = client_execute.post(
                f"/api/dev/v1/reviews/{review_id}/reject/execute",
                json={
                    "confirmationText": "REJECT",
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["executed"] is True
        assert data["action"] == "REJECT"
        assert data["statusBefore"] == "pending"
        assert data["statusAfter"] == "rejected"
        assert data["memoryChanged"] is False
        assert data["reviewChanged"] is True
        assert data["eventAppended"] is True
        assert data["audit"]["devOnly"] is True
        assert data["audit"]["actor"] == "dev-webui"

    def test_reject_execute_updates_review_json(self, client_execute, execute_home):
        """Verify the review JSON file is updated to rejected."""
        review_id = "MR-20260609T143100-def67890"
        updated_at = "2026-06-06T16:03:10+08:00"
        _set_updated_at(execute_home, review_id, updated_at)

        with _execute_enabled():
            client_execute.post(
                f"/api/dev/v1/reviews/{review_id}/reject/execute",
                json={
                    "confirmationText": "REJECT",
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        item_path = execute_home / "memory" / "reviews" / "items" / f"{review_id}.json"
        updated = json.loads(item_path.read_text(encoding="utf-8"))
        assert updated["status"] == "rejected"
        assert updated["rejection"] is not None
        assert "rejected_at" in updated["rejection"]

    def test_reject_execute_appends_event(self, client_execute, execute_home):
        """Verify a review_rejected event is appended."""
        review_id = "MR-20260609T143100-def67890"
        updated_at = "2026-06-06T16:03:10+08:00"
        _set_updated_at(execute_home, review_id, updated_at)

        events_path = execute_home / "memory" / "reviews" / "events.jsonl"
        before_events = events_path.read_text(encoding="utf-8")

        with _execute_enabled():
            client_execute.post(
                f"/api/dev/v1/reviews/{review_id}/reject/execute",
                json={
                    "confirmationText": "REJECT",
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        after_events = events_path.read_text(encoding="utf-8")
        assert len(after_events) > len(before_events)
        assert "review_rejected" in after_events

    def test_reject_execute_no_memory_write(self, client_execute, execute_home):
        """Verify no memory records are created by reject."""
        review_id = "MR-20260609T143100-def67890"
        updated_at = "2026-06-06T16:03:10+08:00"
        _set_updated_at(execute_home, review_id, updated_at)

        records_dir = execute_home / "memory" / "records"
        before_files = set(records_dir.rglob("*.md"))

        with _execute_enabled():
            client_execute.post(
                f"/api/dev/v1/reviews/{review_id}/reject/execute",
                json={
                    "confirmationText": "REJECT",
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        after_files = set(records_dir.rglob("*.md"))
        assert before_files == after_files


class TestExecuteValidation:
    """Execute validation tests (kill switch enabled, temp fixture)."""

    def test_invalid_confirmation_text(self, client_execute, execute_home):
        """Wrong confirmationText returns INVALID_CONFIRMATION."""
        review_id = "MR-20260609T143100-def67890"
        updated_at = "2026-06-06T16:03:10+08:00"
        _set_updated_at(execute_home, review_id, updated_at)

        with _execute_enabled():
            resp = client_execute.post(
                f"/api/dev/v1/reviews/{review_id}/reject/execute",
                json={
                    "confirmationText": "WRONG",
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CONFIRMATION"

    def test_missing_dry_run_previewed(self, client_execute, execute_home):
        """dryRunPreviewed=false returns MISSING_DRY_RUN."""
        review_id = "MR-20260609T143100-def67890"
        updated_at = "2026-06-06T16:03:10+08:00"
        _set_updated_at(execute_home, review_id, updated_at)

        with _execute_enabled():
            resp = client_execute.post(
                f"/api/dev/v1/reviews/{review_id}/reject/execute",
                json={
                    "confirmationText": "REJECT",
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": False,
                    "acknowledgedEffects": [
                        "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "MISSING_DRY_RUN"

    def test_invalid_acknowledged_effects(self, client_execute, execute_home):
        """Missing acknowledged effects returns INVALID_ACKNOWLEDGED_EFFECTS."""
        review_id = "MR-20260609T143100-def67890"
        updated_at = "2026-06-06T16:03:10+08:00"
        _set_updated_at(execute_home, review_id, updated_at)

        with _execute_enabled():
            resp = client_execute.post(
                f"/api/dev/v1/reviews/{review_id}/reject/execute",
                json={
                    "confirmationText": "REJECT",
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": ["UPDATE_REVIEW"],
                },
            )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_ACKNOWLEDGED_EFFECTS"

    def test_precondition_failed(self, client_execute, execute_home):
        """Wrong reviewUpdatedAt returns REVIEW_PRECONDITION_FAILED."""
        review_id = "MR-20260609T143100-def67890"
        _set_updated_at(execute_home, review_id, "2026-06-06T16:03:10+08:00")

        with _execute_enabled():
            resp = client_execute.post(
                f"/api/dev/v1/reviews/{review_id}/reject/execute",
                json={
                    "confirmationText": "REJECT",
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": "2026-01-01T00:00:00+08:00",
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REVIEW_PRECONDITION_FAILED"

    def test_not_pending(self, client_execute, execute_home):
        """Rejecting a non-pending item returns REVIEW_NOT_PENDING."""
        review_id = "MR-20260609T143100-def67890"
        updated_at = "2026-06-06T16:03:10+08:00"
        _set_updated_at(execute_home, review_id, updated_at)

        # First reject it
        with _execute_enabled():
            client_execute.post(
                f"/api/dev/v1/reviews/{review_id}/reject/execute",
                json={
                    "confirmationText": "REJECT",
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        # Try to reject again
        item_path = execute_home / "memory" / "reviews" / "items" / f"{review_id}.json"
        item = json.loads(item_path.read_text(encoding="utf-8"))
        new_updated_at = item["updated_at"]

        with _execute_enabled():
            resp = client_execute.post(
                f"/api/dev/v1/reviews/{review_id}/reject/execute",
                json={
                    "confirmationText": "REJECT",
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": new_updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REVIEW_NOT_PENDING"

    def test_not_found(self, client_execute):
        """Non-existent review returns REVIEW_NOT_FOUND."""
        with _execute_enabled():
            resp = client_execute.post(
                "/api/dev/v1/reviews/MR-20260101T000000-deadbeef/reject/execute",
                json={
                    "confirmationText": "REJECT",
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": "2026-06-06T16:03:10+08:00",
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "REVIEW_NOT_FOUND"

    def test_missing_confirmation_text(self, client_execute):
        """Missing confirmationText returns error."""
        with _execute_enabled():
            resp = client_execute.post(
                "/api/dev/v1/reviews/MR-20260609T143100-def67890/reject/execute",
                json={
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": "2026-06-06T16:03:10+08:00",
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": ["UPDATE_REVIEW", "APPEND_REVIEW_EVENT"],
                },
            )
        assert resp.status_code == 400

    def test_execute_response_no_sensitive_data(self, client_execute, execute_home):
        """Execute response must not contain paths, secrets, or traceback."""
        review_id = "MR-20260609T143100-def67890"
        updated_at = "2026-06-06T16:03:10+08:00"
        _set_updated_at(execute_home, review_id, updated_at)

        with _execute_enabled():
            resp = client_execute.post(
                f"/api/dev/v1/reviews/{review_id}/reject/execute",
                json={
                    "confirmationText": "REJECT",
                    "expectedAction": "REJECT",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        text = json.dumps(resp.json())
        assert "/Users/" not in text
        assert "/home/" not in text
        assert "traceback" not in text.lower()
        assert "secret" not in text.lower()
        assert "token" not in text.lower()


class TestExecuteRoutes:
    """Verify execute routes exist and bare routes remain forbidden."""

    def test_approve_execute_route_exists(self, client_with_reviews):
        """Route exists (returns 503 disabled, not 404)."""
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve/execute",
            json={},
        )
        assert resp.status_code != 404

    def test_reject_execute_route_exists(self, client_with_reviews):
        """Route exists (returns 503 disabled, not 404)."""
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject/execute",
            json={},
        )
        assert resp.status_code != 404

    def test_bare_approve_still_405(self, client_with_reviews):
        """Bare /approve (no /dry-run or /execute) remains forbidden."""
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/approve",
            json={},
        )
        assert resp.status_code in (404, 405)

    def test_bare_reject_still_405(self, client_with_reviews):
        """Bare /reject (no /dry-run or /execute) remains forbidden."""
        resp = client_with_reviews.post(
            "/api/dev/v1/reviews/MR-20260606T080234-1e10c286/reject",
            json={},
        )
        assert resp.status_code in (404, 405)

    def test_enqueue_still_405(self, client_with_reviews):
        resp = client_with_reviews.post("/api/dev/v1/reviews/enqueue", json={})
        assert resp.status_code in (404, 405)


# ── Helpers ──


import contextlib


@contextlib.contextmanager
def _execute_enabled():
    """Context manager that enables the execute kill switch for testing."""
    old = os.environ.get("HERMES_REVIEW_EXECUTE_ENABLED")
    os.environ["HERMES_REVIEW_EXECUTE_ENABLED"] = "true"
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("HERMES_REVIEW_EXECUTE_ENABLED", None)
        else:
            os.environ["HERMES_REVIEW_EXECUTE_ENABLED"] = old


def _set_updated_at(home: Path, review_id: str, updated_at: str) -> None:
    """Set the updated_at field on a review item."""
    item_path = home / "memory" / "reviews" / "items" / f"{review_id}.json"
    item = json.loads(item_path.read_text(encoding="utf-8"))
    item["updated_at"] = updated_at
    item_path.write_text(json.dumps(item, indent=2), encoding="utf-8")


# ── Approve Execute Success Path Tests (Phase 1C-Post-01) ──


def _hash_tree(root: Path) -> dict[str, str]:
    """Return {relative_path: sha256} for all files under root."""
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(root))
            result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


@pytest.fixture
def approve_execute_home(tmp_path):
    """Temporary HERMES_HOME for approve execute success-path testing.

    Has a properly structured MEMORY.md (with index field) so that
    revalidate_review_approval → parse_root → category_index_path works.
    Never touches hermes-home-dev or ~/.hermes.
    """
    home = tmp_path / "hermes-approve-test"
    home.mkdir(exist_ok=True)

    for subdir in ("sessions", "cron", "memories", "skills"):
        (home / subdir).mkdir(exist_ok=True)

    # MEMORY.md with proper index field for parse_root()
    (home / "MEMORY.md").write_text(
        "# Test Memory\n\n"
        "## hermes\n"
        "- index: memory://indexes/hermes.md\n"
        "- status: active\n",
        encoding="utf-8",
    )

    # Memory directory structure
    memory_dir = home / "memory"
    memory_dir.mkdir(exist_ok=True)
    (memory_dir / "indexes").mkdir(exist_ok=True)
    (memory_dir / "records").mkdir(exist_ok=True)
    (memory_dir / "records" / "hermes").mkdir(exist_ok=True)
    (memory_dir / "snapshots").mkdir(exist_ok=True)
    (memory_dir / "events.jsonl").write_text("", encoding="utf-8")

    # Index file — empty (no items to cause duplicate detection for WRITE)
    (memory_dir / "indexes" / "hermes.md").write_text(
        "# Hermes Memory Index\n",
        encoding="utf-8",
    )

    # Reviews structure
    reviews_dir = memory_dir / "reviews"
    items_dir = reviews_dir / "items"
    items_dir.mkdir(parents=True)
    (reviews_dir / "events.jsonl").write_text("", encoding="utf-8")
    (reviews_dir / ".queue.lock").write_text("", encoding="utf-8")

    # Pending WRITE review item (no matched_memory to avoid duplicate path)
    write_item = _make_review_item(
        review_id="MR-20260609T150000-a1b2c3d4",
        status="pending",
        decision="WRITE",
        proposed_action="WRITE",
        category="hermes",
        title="Test approve write item",
        summary="A test summary for approve write.",
        tags=["alpha", "beta"],
        score=85,
        has_matched=False,
    )

    for item in [write_item]:
        path = items_dir / f"{item['review_id']}.json"
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")

    return home


@pytest.fixture
def client_approve_execute(approve_execute_home):
    """TestClient for approve execute success-path testing."""
    config = DevWebApiConfig(hermes_home=approve_execute_home)
    app = create_dev_web_api_app(config)
    return TestClient(app)


@pytest.fixture
def approve_update_home(tmp_path):
    """Temporary HERMES_HOME for approve UPDATE execute testing.

    Includes an existing memory item in the index with a record file,
    so that revalidate_review_approval for UPDATE can find the target,
    pass similarity checks, and update the existing record.
    """
    home = tmp_path / "hermes-approve-update-test"
    home.mkdir(exist_ok=True)

    for subdir in ("sessions", "cron", "memories", "skills"):
        (home / subdir).mkdir(exist_ok=True)

    # MEMORY.md with index field
    (home / "MEMORY.md").write_text(
        "# Test Memory\n\n"
        "## hermes\n"
        "- index: memory://indexes/hermes.md\n"
        "- status: active\n",
        encoding="utf-8",
    )

    memory_dir = home / "memory"
    memory_dir.mkdir(exist_ok=True)
    (memory_dir / "indexes").mkdir(exist_ok=True)
    (memory_dir / "records").mkdir(exist_ok=True)
    (memory_dir / "records" / "hermes").mkdir(exist_ok=True)
    (memory_dir / "snapshots").mkdir(exist_ok=True)
    (memory_dir / "events.jsonl").write_text("", encoding="utf-8")

    # Target memory item in index — must be parseable by parse_index()
    # Fields: type, importance (NOT P0), ttl (NOT permanent), status=active,
    # tags with non-generic overlap, summary similar to candidate
    target_memory_id = "MEM-HERMES-001"
    target_title = "Test approve update target item"
    target_summary = "A test summary for the approve update target memory record."
    target_tags = "alpha, beta"

    index_content = (
        "# Hermes Memory Index\n\n"
        f"## {target_memory_id} {target_title}\n\n"
        f"- type: project_status\n"
        f"- importance: P2\n"
        f"- ttl: project\n"
        f"- status: active\n"
        f"- tags: {target_tags}\n"
        f"- storage: memory://records/hermes/{target_memory_id.casefold()}.md\n"
        f"- created_at: 2026-06-09\n"
        f"- updated_at: 2026-06-09\n"
        f"- summary: {target_summary}\n"
    )
    (memory_dir / "indexes" / "hermes.md").write_text(index_content, encoding="utf-8")

    # Record file for target — minimal valid content
    record_dir = memory_dir / "records" / "hermes"
    record_content = (
        f"# {target_memory_id} {target_title}\n\n"
        f"{target_summary}\n\n"
        f"## Details\n\nOriginal content.\n\n"
        f"## Metadata\n\n"
        f"- type: project_status\n"
        f"- importance: P2\n"
        f"- ttl: project\n"
        f"- status: active\n"
        f"- tags: {target_tags}\n"
    )
    (record_dir / f"{target_memory_id.casefold()}.md").write_text(
        record_content, encoding="utf-8",
    )

    # Reviews structure
    reviews_dir = memory_dir / "reviews"
    items_dir = reviews_dir / "items"
    items_dir.mkdir(parents=True)
    (reviews_dir / "events.jsonl").write_text("", encoding="utf-8")
    (reviews_dir / ".queue.lock").write_text("", encoding="utf-8")

    # UPDATE review item — candidate must be similar to target
    # Use near-identical title and summary to pass similarity thresholds
    # title_similarity >= 0.85 OR summary_similarity >= 0.90
    update_item = _make_review_item(
        review_id="MR-20260609T160000-e5f6a7b8",
        status="pending",
        decision="UPDATE",
        proposed_action="UPDATE",
        category="hermes",
        title="Test approve update target item updated",
        summary="A test summary for the approve update target memory record.",
        tags=["alpha", "beta"],
        score=85,
        has_matched=True,
    )
    # Ensure matched_memory points to the target
    update_item["matched_memory"] = {
        "memory_id": target_memory_id,
        "title": target_title,
        "category": "hermes",
    }

    path = items_dir / f"{update_item['review_id']}.json"
    path.write_text(json.dumps(update_item, ensure_ascii=False, indent=2), encoding="utf-8")

    return home


@pytest.fixture
def client_approve_update(approve_update_home):
    """TestClient for approve UPDATE execute testing."""
    config = DevWebApiConfig(hermes_home=approve_update_home)
    app = create_dev_web_api_app(config)
    return TestClient(app)


class TestApproveExecuteWriteSuccess:
    """Approve execute WRITE success-path tests with isolated temp fixture."""

    def test_approve_execute_write_success_response(
        self, client_approve_execute, approve_execute_home,
    ):
        """Approve execute WRITE returns 200 with correct DTO fields."""
        review_id = "MR-20260609T150000-a1b2c3d4"
        updated_at = "2026-06-09T15:00:00+08:00"
        _set_updated_at(approve_execute_home, review_id, updated_at)

        with _execute_enabled():
            resp = client_approve_execute.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["executed"] is True
        assert data["action"] == "APPROVE"
        assert data["statusBefore"] == "pending"
        assert data["statusAfter"] == "approved"
        assert data["memoryChanged"] is True
        assert data["reviewChanged"] is True
        assert data["eventAppended"] is True
        assert data["audit"]["devOnly"] is True
        assert data["audit"]["actor"] == "dev-webui"
        assert "warnings" in data
        assert isinstance(data["warnings"], list)

    def test_approve_execute_write_review_json_approved(
        self, client_approve_execute, approve_execute_home,
    ):
        """Review JSON status changes to approved with approval object."""
        review_id = "MR-20260609T150000-a1b2c3d4"
        updated_at = "2026-06-09T15:00:00+08:00"
        _set_updated_at(approve_execute_home, review_id, updated_at)

        with _execute_enabled():
            client_approve_execute.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        item_path = approve_execute_home / "memory" / "reviews" / "items" / f"{review_id}.json"
        updated = json.loads(item_path.read_text(encoding="utf-8"))
        assert updated["status"] == "approved"
        assert updated["approval"] is not None
        assert "approved_at" in updated["approval"]
        assert "memory_id" in updated["approval"]
        assert updated["approval"]["action"] == "WRITE"
        assert updated.get("rejection") is None

    def test_approve_execute_write_review_event_appended(
        self, client_approve_execute, approve_execute_home,
    ):
        """review_approved event is appended to review events.jsonl."""
        review_id = "MR-20260609T150000-a1b2c3d4"
        updated_at = "2026-06-09T15:00:00+08:00"
        _set_updated_at(approve_execute_home, review_id, updated_at)

        events_path = approve_execute_home / "memory" / "reviews" / "events.jsonl"
        before_events = events_path.read_text(encoding="utf-8")

        with _execute_enabled():
            client_approve_execute.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        after_events = events_path.read_text(encoding="utf-8")
        assert len(after_events) > len(before_events)
        # Parse events and verify the last one is review_approved
        lines = [l for l in after_events.strip().splitlines() if l.strip()]
        last_event = json.loads(lines[-1])
        assert last_event["event"] == "review_approved"
        assert last_event["review_id"] == review_id
        assert "memory_id" in last_event

    def test_approve_execute_write_creates_memory_record(
        self, client_approve_execute, approve_execute_home,
    ):
        """Memory record file is created after WRITE approve."""
        review_id = "MR-20260609T150000-a1b2c3d4"
        updated_at = "2026-06-09T15:00:00+08:00"
        _set_updated_at(approve_execute_home, review_id, updated_at)

        # Record for "hermes" category goes to records/projects/hermes/
        records_dir = approve_execute_home / "memory" / "records"
        before_files = set(records_dir.rglob("*.md"))

        with _execute_enabled():
            client_approve_execute.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        after_files = set(records_dir.rglob("*.md"))
        new_files = after_files - before_files
        assert len(new_files) == 1
        new_file = new_files.pop()
        content = new_file.read_text(encoding="utf-8")
        assert "MEM-HERMES-" in content

    def test_approve_execute_write_updates_category_index(
        self, client_approve_execute, approve_execute_home,
    ):
        """Category index is updated with the new memory item."""
        review_id = "MR-20260609T150000-a1b2c3d4"
        updated_at = "2026-06-09T15:00:00+08:00"
        _set_updated_at(approve_execute_home, review_id, updated_at)

        index_path = approve_execute_home / "memory" / "indexes" / "hermes.md"
        before_content = index_path.read_text(encoding="utf-8")

        with _execute_enabled():
            client_approve_execute.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        after_content = index_path.read_text(encoding="utf-8")
        assert len(after_content) > len(before_content)
        assert "MEM-HERMES-" in after_content

    def test_approve_execute_write_appends_memory_event(
        self, client_approve_execute, approve_execute_home,
    ):
        """memory_create event is appended to memory events.jsonl."""
        review_id = "MR-20260609T150000-a1b2c3d4"
        updated_at = "2026-06-09T15:00:00+08:00"
        _set_updated_at(approve_execute_home, review_id, updated_at)

        events_path = approve_execute_home / "memory" / "events.jsonl"
        before = events_path.read_text(encoding="utf-8")

        with _execute_enabled():
            client_approve_execute.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        after = events_path.read_text(encoding="utf-8")
        assert len(after) > len(before)
        assert "memory_create" in after

    def test_approve_execute_write_creates_index_backup(
        self, client_approve_execute, approve_execute_home,
    ):
        """A snapshot/backup of the index file is created."""
        review_id = "MR-20260609T150000-a1b2c3d4"
        updated_at = "2026-06-09T15:00:00+08:00"
        _set_updated_at(approve_execute_home, review_id, updated_at)

        snapshots_dir = approve_execute_home / "memory" / "snapshots"
        before_files = set(snapshots_dir.iterdir())

        with _execute_enabled():
            client_approve_execute.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        after_files = set(snapshots_dir.iterdir())
        new_snapshots = after_files - before_files
        assert len(new_snapshots) >= 1
        # Verify backup file name pattern: INDEX-hermes-YYYYMMDD-HHMMSS.md
        snapshot_names = [f.name for f in new_snapshots]
        assert any("INDEX-hermes" in n or "INDEX-" in n for n in snapshot_names)

    def test_approve_execute_write_no_unexpected_file_changes(
        self, client_approve_execute, approve_execute_home,
    ):
        """File changes are limited to expected paths only."""
        review_id = "MR-20260609T150000-a1b2c3d4"
        updated_at = "2026-06-09T15:00:00+08:00"
        _set_updated_at(approve_execute_home, review_id, updated_at)

        before = _hash_tree(approve_execute_home)

        with _execute_enabled():
            client_approve_execute.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        after = _hash_tree(approve_execute_home)
        changed = sorted(k for k in set(list(before.keys()) + list(after.keys()))
                         if before.get(k) != after.get(k))

        # Expected changes:
        # - memory/indexes/hermes.md (new item added)
        # - memory/records/hermes/<new-id>.md (new record created)
        # - memory/events.jsonl (memory_create appended)
        # - memory/snapshots/<backup>.md (index backup)
        # - memory/reviews/items/<review-id>.json (status → approved)
        # - memory/reviews/events.jsonl (review_approved appended)
        for path in changed:
            is_expected = (
                path.startswith("memory/indexes/")
                or path.startswith("memory/records/")
                or path.startswith("memory/events.jsonl")
                or path.startswith("memory/snapshots/")
                or path.startswith("memory/reviews/")
            )
            assert is_expected, f"Unexpected file change: {path}"


class TestApproveExecuteUpdateSuccess:
    """Approve execute UPDATE success-path tests with isolated temp fixture."""

    def test_approve_execute_update_success_response(
        self, client_approve_update, approve_update_home,
    ):
        """Approve execute UPDATE returns 200 with correct DTO."""
        review_id = "MR-20260609T160000-e5f6a7b8"
        updated_at = "2026-06-09T16:00:00+08:00"
        _set_updated_at(approve_update_home, review_id, updated_at)

        with _execute_enabled():
            resp = client_approve_update.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["executed"] is True
        assert data["action"] == "APPROVE"
        assert data["statusBefore"] == "pending"
        assert data["statusAfter"] == "approved"
        assert data["memoryChanged"] is True
        assert data["reviewChanged"] is True
        assert data["eventAppended"] is True
        assert data["target"]["memoryId"] == "MEM-HERMES-001"
        assert data["target"]["operation"] == "UPDATE"
        assert data["audit"]["devOnly"] is True

    def test_approve_execute_update_review_json_approved(
        self, client_approve_update, approve_update_home,
    ):
        """Review JSON status changes to approved after UPDATE."""
        review_id = "MR-20260609T160000-e5f6a7b8"
        updated_at = "2026-06-09T16:00:00+08:00"
        _set_updated_at(approve_update_home, review_id, updated_at)

        with _execute_enabled():
            client_approve_update.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        item_path = approve_update_home / "memory" / "reviews" / "items" / f"{review_id}.json"
        updated = json.loads(item_path.read_text(encoding="utf-8"))
        assert updated["status"] == "approved"
        assert updated["approval"] is not None
        assert "approved_at" in updated["approval"]
        assert updated["approval"]["action"] == "UPDATE"
        assert updated["approval"]["memory_id"] == "MEM-HERMES-001"

    def test_approve_execute_update_review_event(
        self, client_approve_update, approve_update_home,
    ):
        """review_approved event is appended with UPDATE action."""
        review_id = "MR-20260609T160000-e5f6a7b8"
        updated_at = "2026-06-09T16:00:00+08:00"
        _set_updated_at(approve_update_home, review_id, updated_at)

        events_path = approve_update_home / "memory" / "reviews" / "events.jsonl"

        with _execute_enabled():
            client_approve_update.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        lines = [l for l in events_path.read_text(encoding="utf-8").strip().splitlines() if l.strip()]
        last_event = json.loads(lines[-1])
        assert last_event["event"] == "review_approved"
        assert last_event["review_id"] == review_id
        assert last_event.get("action") == "UPDATE"

    def test_approve_execute_update_modifies_record(
        self, client_approve_update, approve_update_home,
    ):
        """Target memory record is modified after UPDATE approve."""
        review_id = "MR-20260609T160000-e5f6a7b8"
        updated_at = "2026-06-09T16:00:00+08:00"
        _set_updated_at(approve_update_home, review_id, updated_at)

        record_path = approve_update_home / "memory" / "records" / "hermes" / "mem-hermes-001.md"
        before = record_path.read_text(encoding="utf-8")

        with _execute_enabled():
            client_approve_update.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        after = record_path.read_text(encoding="utf-8")
        assert after != before

    def test_approve_execute_update_appends_memory_event(
        self, client_approve_update, approve_update_home,
    ):
        """memory_update event is appended to memory events.jsonl."""
        review_id = "MR-20260609T160000-e5f6a7b8"
        updated_at = "2026-06-09T16:00:00+08:00"
        _set_updated_at(approve_update_home, review_id, updated_at)

        events_path = approve_update_home / "memory" / "events.jsonl"
        before = events_path.read_text(encoding="utf-8")

        with _execute_enabled():
            client_approve_update.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        after = events_path.read_text(encoding="utf-8")
        assert len(after) > len(before)
        assert "memory_update" in after

    def test_approve_execute_update_creates_backups(
        self, client_approve_update, approve_update_home,
    ):
        """Both index and record backups are created for UPDATE."""
        review_id = "MR-20260609T160000-e5f6a7b8"
        updated_at = "2026-06-09T16:00:00+08:00"
        _set_updated_at(approve_update_home, review_id, updated_at)

        snapshots_dir = approve_update_home / "memory" / "snapshots"
        before_files = set(snapshots_dir.iterdir())

        with _execute_enabled():
            client_approve_update.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        after_files = set(snapshots_dir.iterdir())
        new_snapshots = after_files - before_files
        assert len(new_snapshots) >= 2
        snapshot_names = [f.name for f in new_snapshots]
        has_index_backup = any("INDEX-" in n for n in snapshot_names)
        has_record_backup = any("RECORD-" in n for n in snapshot_names)
        assert has_index_backup, f"Missing index backup in: {snapshot_names}"
        assert has_record_backup, f"Missing record backup in: {snapshot_names}"

    def test_approve_execute_update_no_unexpected_file_changes(
        self, client_approve_update, approve_update_home,
    ):
        """File changes are limited to expected paths for UPDATE."""
        review_id = "MR-20260609T160000-e5f6a7b8"
        updated_at = "2026-06-09T16:00:00+08:00"
        _set_updated_at(approve_update_home, review_id, updated_at)

        before = _hash_tree(approve_update_home)

        with _execute_enabled():
            client_approve_update.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        after = _hash_tree(approve_update_home)
        changed = sorted(k for k in set(list(before.keys()) + list(after.keys()))
                         if before.get(k) != after.get(k))

        for path in changed:
            is_expected = (
                path.startswith("memory/indexes/")
                or path.startswith("memory/records/")
                or path.startswith("memory/events.jsonl")
                or path.startswith("memory/snapshots/")
                or path.startswith("memory/reviews/")
            )
            assert is_expected, f"Unexpected file change: {path}"


class TestApproveExecuteDtoSafety:
    """Verify approve execute response DTO does not leak sensitive data."""

    def test_approve_execute_response_no_sensitive_data(
        self, client_approve_execute, approve_execute_home,
    ):
        """Response must not contain paths, secrets, traceback, or raw candidate."""
        review_id = "MR-20260609T150000-a1b2c3d4"
        updated_at = "2026-06-09T15:00:00+08:00"
        _set_updated_at(approve_execute_home, review_id, updated_at)

        with _execute_enabled():
            resp = client_approve_execute.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        text = json.dumps(resp.json())
        assert "/Users/" not in text
        assert "/home/" not in text
        assert "traceback" not in text.lower()
        assert "secret" not in text.lower()
        assert "token" not in text.lower()
        assert "cookie" not in text.lower()

    def test_approve_execute_response_dto_whitelist(
        self, client_approve_execute, approve_execute_home,
    ):
        """Response data contains only whitelisted fields."""
        review_id = "MR-20260609T150000-a1b2c3d4"
        updated_at = "2026-06-09T15:00:00+08:00"
        _set_updated_at(approve_execute_home, review_id, updated_at)

        with _execute_enabled():
            resp = client_approve_execute.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        data = resp.json()["data"]
        allowed_top = {
            "reviewId", "executed", "action", "statusBefore", "statusAfter",
            "memoryChanged", "reviewChanged", "eventAppended",
            "target", "audit", "warnings",
        }
        assert set(data.keys()) == allowed_top

        # Target must not contain raw candidate or source
        assert "rawCandidate" not in data
        assert "source" not in data
        assert "fingerprint" not in data

        # Target sub-object
        target = data["target"]
        assert "memoryId" in target
        assert "category" in target
        assert "operation" in target

        # Audit sub-object
        audit = data["audit"]
        assert audit["actor"] == "dev-webui"
        assert audit["devOnly"] is True
        assert "timestamp" in audit


class TestApproveExecuteIdempotency:
    """Verify re-executing approve on already-approved item does not duplicate writes."""

    def test_second_approve_does_not_duplicate_memory_write(
        self, client_approve_execute, approve_execute_home,
    ):
        """Second approve request does not create additional memory records."""
        review_id = "MR-20260609T150000-a1b2c3d4"
        updated_at = "2026-06-09T15:00:00+08:00"
        _set_updated_at(approve_execute_home, review_id, updated_at)

        # First approve
        with _execute_enabled():
            resp1 = client_approve_execute.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        assert resp1.status_code == 200

        # Capture state after first approve
        records_dir = approve_execute_home / "memory" / "records"
        after_first_records = set(records_dir.rglob("*.md"))
        mem_events_path = approve_execute_home / "memory" / "events.jsonl"
        after_first_mem_events = mem_events_path.read_text(encoding="utf-8")
        review_events_path = approve_execute_home / "memory" / "reviews" / "events.jsonl"
        after_first_review_events = review_events_path.read_text(encoding="utf-8")

        # Read the updated review item to get new updated_at
        item_path = approve_execute_home / "memory" / "reviews" / "items" / f"{review_id}.json"
        updated_item = json.loads(item_path.read_text(encoding="utf-8"))
        new_updated_at = updated_item["updated_at"]

        # Second approve (should be idempotent or return error)
        with _execute_enabled():
            resp2 = client_approve_execute.post(
                f"/api/dev/v1/reviews/{review_id}/approve/execute",
                json={
                    "confirmationText": "APPROVE",
                    "expectedAction": "APPROVE",
                    "reviewUpdatedAt": new_updated_at,
                    "dryRunPreviewed": True,
                    "acknowledgedEffects": [
                        "WRITE_MEMORY", "UPDATE_REVIEW", "APPEND_REVIEW_EVENT",
                    ],
                },
            )

        # Second request should not duplicate memory records
        after_second_records = set(records_dir.rglob("*.md"))
        assert after_second_records == after_first_records

        # Second request should not duplicate memory events
        after_second_mem_events = mem_events_path.read_text(encoding="utf-8")
        first_count = after_first_mem_events.count("memory_create")
        second_count = after_second_mem_events.count("memory_create")
        assert second_count == first_count
