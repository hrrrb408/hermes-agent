"""Isolated tests for the development WeChat review queue pilot."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import pytest

from agent.memory_review_queue import (
    enqueue_review_item,
    get_review_queue_paths,
    reject_review_item,
)
from agent.runtime_memory_writer import (
    MemoryCandidate,
    MemoryDecision,
    MemoryEvaluation,
    ScoreEntry,
    maybe_auto_write_memory,
)
from gateway import dev_isolation
from gateway.dev_isolation import (
    DevReviewPilotConfig,
    build_dev_review_pilot_environment,
    build_dev_review_pilot_state,
    format_dev_gateway_status,
    get_dev_gateway_status,
    get_review_queue_pending_count,
    validate_dev_review_pilot_safety,
    write_dev_gateway_runtime_state,
)
from hermes_cli.memory_router import ensure_memory_scaffold, validate_memory


@pytest.fixture
def pilot_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "pilot-home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    for name in (
        "HERMES_MEMORY_AUTO_WRITE",
        "HERMES_MEMORY_AUTO_UPDATE",
        "HERMES_MEMORY_AUTO_CREATE_CATEGORIES",
        "HERMES_MEMORY_REVIEW_QUEUE",
        "HERMES_MEMORY_REVIEW_MAX_PENDING",
        "HERMES_DEV_GATEWAY_MEMORY_LOGS",
    ):
        monkeypatch.delenv(name, raising=False)
    ensure_memory_scaffold(home)
    assert validate_memory(home).ok
    assert home.resolve() != Path("/Users/huangruibang/Code/hermes-home-dev").resolve()
    return home


def _candidate(suffix: str = "") -> MemoryCandidate:
    return MemoryCandidate(
        title=f"Hermes review pilot validation {suffix}".strip(),
        summary=f"Hermes review pilot isolated validation completed {suffix}".strip(),
        category="hermes",
        tags=["hermes", "review-queue", "pilot", suffix or "base"],
        memory_type="project_progress",
        importance="P1",
        ttl="project",
    )


def _evaluation(
    decision: MemoryDecision,
    *,
    suffix: str = "",
) -> MemoryEvaluation:
    candidate = _candidate(suffix)
    return MemoryEvaluation(
        candidate=candidate,
        score=90,
        score_breakdown=[ScoreEntry("pilot_test", 90)],
        decision=decision,
        reason_codes=[f"PILOT_{decision.value}"],
        reasons=["Isolated pilot test."],
        auto_write_enabled=False,
        auto_update_enabled=False,
        auto_create_categories_enabled=False,
        would_modify_files=False,
    )


def _formal_hash(home: Path) -> str:
    digest = hashlib.sha256()
    paths = [home / "MEMORY.md", home / "memory/events.jsonl"]
    paths.extend(sorted((home / "memory/indexes").rglob("*.md")))
    paths.extend(sorted((home / "memory/records").rglob("*.md")))
    for path in paths:
        digest.update(str(path.relative_to(home)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "YES", "on", "ON"])
@pytest.mark.parametrize(
    "name",
    [
        "HERMES_MEMORY_AUTO_WRITE",
        "HERMES_MEMORY_AUTO_UPDATE",
        "HERMES_MEMORY_AUTO_CREATE_CATEGORIES",
    ],
)
def test_pilot_rejects_truthy_unsafe_environment(name: str, value: str) -> None:
    with pytest.raises(RuntimeError, match="DEV_REVIEW_PILOT_UNSAFE_ENV"):
        validate_dev_review_pilot_safety(
            enabled=True,
            environ={name: value},
        )


@pytest.mark.parametrize("value", [None, "", "false", "0", "no", "off"])
def test_pilot_accepts_safe_environment_values(value: str | None) -> None:
    env = {} if value is None else {"HERMES_MEMORY_AUTO_WRITE": value}
    config = validate_dev_review_pilot_safety(enabled=True, environ=env)
    assert config.enabled
    assert config.max_pending == 20
    assert config.pilot_safety == "PASS"


@pytest.mark.parametrize("value", [1, 20, 500])
def test_pilot_max_pending_valid_boundaries(value: int) -> None:
    assert validate_dev_review_pilot_safety(
        enabled=True,
        max_pending=value,
        environ={},
    ).max_pending == value


@pytest.mark.parametrize("value", [0, 501, "invalid"])
def test_pilot_max_pending_rejects_invalid_values(value: int | str) -> None:
    with pytest.raises(ValueError, match="DEV_REVIEW_PILOT_INVALID_MAX_PENDING"):
        validate_dev_review_pilot_safety(
            enabled=True,
            max_pending=value,
            environ={},
        )


def test_max_pending_requires_pilot_flag() -> None:
    with pytest.raises(ValueError, match="REVIEW_PILOT_FLAG_REQUIRED"):
        validate_dev_review_pilot_safety(
            enabled=False,
            max_pending=20,
            environ={},
        )


def test_pilot_environment_forces_formal_writes_off() -> None:
    env = build_dev_review_pilot_environment(
        DevReviewPilotConfig(enabled=True, max_pending=20, pilot_safety="PASS")
    )
    assert env == {
        "HERMES_MEMORY_REVIEW_QUEUE": "true",
        "HERMES_MEMORY_REVIEW_MAX_PENDING": "20",
        "HERMES_MEMORY_AUTO_WRITE": "false",
        "HERMES_MEMORY_AUTO_UPDATE": "false",
        "HERMES_MEMORY_AUTO_CREATE_CATEGORIES": "false",
    }


def test_non_pilot_gateway_explicitly_disables_review_queue() -> None:
    env = build_dev_review_pilot_environment(
        DevReviewPilotConfig(enabled=False, max_pending=20)
    )
    assert env == {"HERMES_MEMORY_REVIEW_QUEUE": "false"}


def test_runtime_state_contains_only_safe_pilot_metadata(
    pilot_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dev_isolation, "EXPECTED_DEV_HOME", pilot_home)
    paths = dev_isolation._dev_paths(pilot_home)
    config = DevReviewPilotConfig(
        enabled=True,
        max_pending=20,
        pilot_safety="PASS",
    )
    write_dev_gateway_runtime_state(
        paths,
        auth={"allow_all_users": False, "allowed_users": ["test-user"]},
        redact_secrets=True,
        log_memory=True,
        review_pilot=config,
    )
    payload = json.loads(paths["runtime_status_file"].read_text(encoding="utf-8"))
    pilot = payload["memory_review_queue"]
    assert pilot["enabled"] is True
    assert pilot["max_pending"] == 20
    assert pilot["auto_write"] is False
    assert pilot["auto_update"] is False
    assert pilot["auto_create_categories"] is False
    assert pilot["pilot_safety"] == "PASS"
    serialized = json.dumps(payload).lower()
    for forbidden in ("user message body", "candidate summary", "api_key", "prompt", "cookie"):
        assert forbidden not in serialized

    payload["memory_review_queue"]["path"] = str(pilot_home / "untrusted")
    paths["runtime_status_file"].write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(dev_isolation, "_pid_running", lambda _pid: True)
    monkeypatch.setattr(dev_isolation, "_looks_like_dev_gateway", lambda _pid, _home: True)
    paths["pid_file"].write_text("4242", encoding="utf-8")
    assert get_dev_gateway_status(pilot_home).memory_review_queue_path == (
        pilot_home / "memory" / "reviews"
    )
    payload["memory_review_queue"]["auto_write"] = True
    paths["runtime_status_file"].write_text(json.dumps(payload), encoding="utf-8")
    assert get_dev_gateway_status(pilot_home).review_pilot_safety == "FAIL"


def test_gateway_status_uses_running_state_and_dynamic_pending_count(
    pilot_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dev_isolation, "EXPECTED_DEV_HOME", pilot_home)
    monkeypatch.setattr(dev_isolation, "_pid_running", lambda _pid: True)
    monkeypatch.setattr(dev_isolation, "_looks_like_dev_gateway", lambda _pid, _home: True)
    paths = dev_isolation._dev_paths(pilot_home)
    paths["pid_file"].write_text("4242", encoding="utf-8")
    write_dev_gateway_runtime_state(
        paths,
        auth={"allow_all_users": False, "allowed_users": ["test-user"]},
        redact_secrets=True,
        log_memory=True,
        review_pilot=DevReviewPilotConfig(
            enabled=True,
            max_pending=20,
            pilot_safety="PASS",
        ),
    )
    review_ids: dict[str, str] = {}
    for suffix in ("one", "two", "rejected", "approved"):
        item, _created, _message = enqueue_review_item(
            _evaluation(MemoryDecision.REVIEW, suffix=suffix),
            home=pilot_home,
            require_enabled=False,
        )
        assert item is not None
        review_ids[suffix] = item["review_id"]
    reject_review_item(review_ids["rejected"], "pilot test", home=pilot_home)
    approved_path = (
        get_review_queue_paths(pilot_home).items / f"{review_ids['approved']}.json"
    )
    approved = json.loads(approved_path.read_text(encoding="utf-8"))
    approved["status"] = "approved"
    approved["approval"] = {
        "approved_at": approved["updated_at"],
        "action": "WRITE",
        "memory_id": "MEM-HERMES-999",
    }
    approved_path.write_text(
        json.dumps(approved, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    status = get_dev_gateway_status(pilot_home)
    output = format_dev_gateway_status(status)
    assert status.memory_review_queue_enabled
    assert status.pending_reviews == 2
    assert "Memory review queue: enabled" in output
    assert "Pending reviews: 2" in output
    assert "Auto memory write: disabled" in output
    assert "Auto memory update: disabled" in output
    assert "Auto category creation: disabled" in output
    assert "Review pilot safety: PASS" in output
    assert "Wechat review commands: read-only enabled" in output


def test_stale_state_does_not_report_pilot_running(
    pilot_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dev_isolation, "EXPECTED_DEV_HOME", pilot_home)
    monkeypatch.setattr(dev_isolation, "_pid_running", lambda _pid: False)
    paths = dev_isolation._dev_paths(pilot_home)
    paths["pid_file"].write_text("4242", encoding="utf-8")
    write_dev_gateway_runtime_state(
        paths,
        auth={},
        redact_secrets=True,
        log_memory=False,
        review_pilot=DevReviewPilotConfig(
            enabled=True,
            max_pending=20,
            pilot_safety="PASS",
        ),
    )
    status = get_dev_gateway_status(pilot_home)
    assert status.state == "stale pid file"
    assert not status.memory_review_queue_enabled
    assert "disabled by default" in format_dev_gateway_status(status)


@pytest.mark.parametrize(
    ("decision", "expected_action", "expected_count"),
    [
        (MemoryDecision.REVIEW, "WRITE", 1),
        (MemoryDecision.WRITE, "WRITE", 1),
        (MemoryDecision.UPDATE, "UPDATE", 1),
        (MemoryDecision.SKIP, None, 0),
        (MemoryDecision.SKIP_DUPLICATE, None, 0),
    ],
)
def test_runtime_decision_routing_does_not_modify_formal_memory(
    pilot_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    decision: MemoryDecision,
    expected_action: str | None,
    expected_count: int,
) -> None:
    evaluation = _evaluation(decision, suffix=decision.value.casefold())
    monkeypatch.setenv("HERMES_MEMORY_REVIEW_QUEUE", "true")
    monkeypatch.setenv("HERMES_MEMORY_AUTO_WRITE", "false")
    monkeypatch.setenv("HERMES_MEMORY_AUTO_UPDATE", "false")
    monkeypatch.setenv("HERMES_MEMORY_AUTO_CREATE_CATEGORIES", "false")
    monkeypatch.setattr(
        "agent.runtime_memory_writer.evaluate_memory_auto_write",
        lambda *_args, **_kwargs: evaluation,
    )
    before = _formal_hash(pilot_home)

    result = maybe_auto_write_memory("not logged", "not logged", config={})

    assert result is evaluation
    review_files = list((pilot_home / "memory/reviews/items").glob("*.json"))
    assert len(review_files) == expected_count
    if review_files:
        payload = json.loads(review_files[0].read_text(encoding="utf-8"))
        assert payload["proposed_action"] == expected_action
    assert _formal_hash(pilot_home) == before
    assert validate_memory(pilot_home).ok


def test_verbose_dedup_log_has_metadata_without_message_body(
    pilot_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    evaluation = _evaluation(MemoryDecision.REVIEW, suffix="dedup")
    monkeypatch.setenv("HERMES_MEMORY_REVIEW_QUEUE", "true")
    monkeypatch.setenv("HERMES_DEV_GATEWAY_MEMORY_LOGS", "true")
    monkeypatch.setattr(
        "agent.runtime_memory_writer.evaluate_memory_auto_write",
        lambda *_args, **_kwargs: evaluation,
    )
    caplog.set_level(logging.INFO, logger="agent.runtime_memory_writer")

    maybe_auto_write_memory("private user body", "private assistant body", config={})
    maybe_auto_write_memory("private user body", "private assistant body", config={})

    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "enqueue=yes" in logs
    assert "enqueue=deduplicated" in logs
    assert "occurrence_count=2" in logs
    assert "review_id=MR-" in logs
    assert "private user body" not in logs
    assert "private assistant body" not in logs
    assert evaluation.candidate.summary not in logs
    assert get_review_queue_pending_count(pilot_home) == 1


def test_enqueue_failure_isolated_from_runtime(
    pilot_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    evaluation = _evaluation(MemoryDecision.REVIEW, suffix="failure")
    monkeypatch.setenv("HERMES_MEMORY_REVIEW_QUEUE", "true")
    monkeypatch.setattr(
        "agent.runtime_memory_writer.evaluate_memory_auto_write",
        lambda *_args, **_kwargs: evaluation,
    )
    monkeypatch.setattr(
        "agent.memory_review_queue.enqueue_review_item",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("simulated queue failure")
        ),
    )
    before = _formal_hash(pilot_home)
    caplog.set_level(logging.WARNING, logger="agent.runtime_memory_writer")

    result = maybe_auto_write_memory("not logged", "not logged", config={})

    assert result is evaluation
    assert "memory review queue enqueue failed: simulated queue failure" in caplog.text
    assert _formal_hash(pilot_home) == before
    assert not list((pilot_home / "memory/reviews/items").glob("*.json"))


def test_pilot_state_builder_reports_current_pending(pilot_home: Path) -> None:
    enqueue_review_item(
        _evaluation(MemoryDecision.REVIEW, suffix="state"),
        home=pilot_home,
        require_enabled=False,
    )
    state = build_dev_review_pilot_state(
        dev_isolation._dev_paths(pilot_home),
        DevReviewPilotConfig(enabled=True, max_pending=20, pilot_safety="PASS"),
    )
    assert state["pending_count_at_start"] == 1
    assert state["path"].startswith(str(pilot_home))
