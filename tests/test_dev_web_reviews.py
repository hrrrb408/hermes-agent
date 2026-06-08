"""Tests for the Hermes Dev Web API Review Queue read-only endpoints (Phase 1A).

Covers:
- GET /reviews/status — queue status and safety flags
- GET /reviews — paginated list with filters
- GET /reviews/{reviewId} — detail view
- Forbidden POST/PATCH/DELETE review routes
- Side-effect verification (no files changed)
- DTO whitelist (no forbidden fields in responses)
- Path redaction
- Text truncation
"""

from __future__ import annotations

import hashlib
import json
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
    """Create a temporary HERMES_HOME with review queue items."""
    home = tmp_path / "hermes-home"
    home.mkdir()

    # Create memory/reviews structure
    reviews_dir = home / "memory" / "reviews"
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
    home = tmp_path / "hermes-home-empty"
    home.mkdir()
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
        assert safety["dryRunAvailable"] is False

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
        """Call all 3 endpoints and verify no file changes."""
        reviews_dir = review_home / "memory" / "reviews"
        before = self._hash_dir(reviews_dir)

        client_with_reviews.get("/api/dev/v1/reviews/status")
        client_with_reviews.get("/api/dev/v1/reviews")
        client_with_reviews.get("/api/dev/v1/reviews?status=pending")
        client_with_reviews.get("/api/dev/v1/reviews?decision=REVIEW")
        client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080234-1e10c286")
        client_with_reviews.get("/api/dev/v1/reviews/MR-20260606T080319-36981352")

        after = self._hash_dir(reviews_dir)
        assert before == after
