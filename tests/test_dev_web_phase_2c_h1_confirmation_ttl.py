"""Phase 2C-H1 — Confirmation token TTL + scope-isolation tests.

Focuses on TTL enforcement (expired tokens blocked) and the strict scope
isolation between write_execute / rollback_execute /
provider_write_preview_confirm tokens. A token issued for one scope must not
verify for another.

Phase: 2C-H1 — Write Execution Hardening
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hermes_cli.dev_web_confirmation_store import (
    BLOCKED_TOKEN_ALREADY_USED,
    BLOCKED_TOKEN_DIGEST_MISMATCH,
    BLOCKED_TOKEN_EXPIRED,
    BLOCKED_TOKEN_SCOPE_MISMATCH,
    DEFAULT_TTL_PROVIDER_PREVIEW_SECONDS,
    DEFAULT_TTL_ROLLBACK_SECONDS,
    DEFAULT_TTL_WRITE_SECONDS,
    SCOPE_PROVIDER_WRITE_PREVIEW_CONFIRM,
    SCOPE_ROLLBACK_EXECUTE,
    SCOPE_WRITE_EXECUTE,
    TOKEN_DIR_RELATIVE,
    create_confirmation_token,
    mark_confirmation_token_used,
    verify_confirmation_token,
)


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return str(home)


def _expire_token(dev_home: str, token_id: str) -> None:
    token_file = Path(dev_home) / TOKEN_DIR_RELATIVE / f"{token_id}.json"
    data = json.loads(token_file.read_text(encoding="utf-8"))
    data["expiresAt"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    token_file.write_text(json.dumps(data), encoding="utf-8")


class TestTTL:
    def test_expired_token_blocked(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WRITE_EXECUTE, argument_digest="d" * 64, hermes_home=dev_home
        )
        assert issue is not None
        _expire_token(dev_home, issue.tokenId)
        result = verify_confirmation_token(
            issue.token, expected_scope=SCOPE_WRITE_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is False
        assert result.blocked_reason == BLOCKED_TOKEN_EXPIRED

    def test_default_ttls(self) -> None:
        assert DEFAULT_TTL_WRITE_SECONDS == 600
        assert DEFAULT_TTL_ROLLBACK_SECONDS == 600
        assert DEFAULT_TTL_PROVIDER_PREVIEW_SECONDS == 300


class TestScopeIsolation:
    def test_write_token_cannot_verify_as_rollback(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WRITE_EXECUTE, argument_digest="d" * 64, hermes_home=dev_home
        )
        result = verify_confirmation_token(
            issue.token, expected_scope=SCOPE_ROLLBACK_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is False
        assert result.blocked_reason == BLOCKED_TOKEN_SCOPE_MISMATCH

    def test_rollback_token_cannot_verify_as_write(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_ROLLBACK_EXECUTE, argument_digest="d" * 64, hermes_home=dev_home
        )
        result = verify_confirmation_token(
            issue.token, expected_scope=SCOPE_WRITE_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is False
        assert result.blocked_reason == BLOCKED_TOKEN_SCOPE_MISMATCH

    def test_provider_preview_token_cannot_verify_as_write_or_rollback(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_PROVIDER_WRITE_PREVIEW_CONFIRM, argument_digest="d" * 64,
            hermes_home=dev_home,
        )
        for scope in (SCOPE_WRITE_EXECUTE, SCOPE_ROLLBACK_EXECUTE):
            result = verify_confirmation_token(
                issue.token, expected_scope=scope, expected_digest="d" * 64, hermes_home=dev_home
            )
            assert result.verified is False
            assert result.blocked_reason == BLOCKED_TOKEN_SCOPE_MISMATCH


class TestDigestBinding:
    def test_digest_mismatch_blocked(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WRITE_EXECUTE, argument_digest="d" * 64, hermes_home=dev_home
        )
        result = verify_confirmation_token(
            issue.token, expected_scope=SCOPE_WRITE_EXECUTE, expected_digest="e" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is False
        assert result.blocked_reason == BLOCKED_TOKEN_DIGEST_MISMATCH


class TestReplayPersistence:
    def test_used_token_replay_blocked_after_reload(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WRITE_EXECUTE, argument_digest="d" * 64, hermes_home=dev_home
        )
        mark_confirmation_token_used(issue.tokenId, hermes_home=dev_home)
        result = verify_confirmation_token(
            issue.token, expected_scope=SCOPE_WRITE_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is False
        assert result.blocked_reason == BLOCKED_TOKEN_ALREADY_USED


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
