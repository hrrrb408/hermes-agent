"""Phase 2C-H1 — File-backed confirmation token store tests.

Verifies the token store: tokens are file-backed under the dev HERMES_HOME,
the plain secret is never stored, the full tokenHash is not exposed, scope +
digest + TTL + single-use are enforced, single-use persists across a store
reload, and cleanup is safe (no symlink follow, no non-token deletion, no
production access).

Phase: 2C-H1 — Write Execution Hardening
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli.dev_web_confirmation_store import (
    BLOCKED_TOKEN_ALREADY_USED,
    BLOCKED_TOKEN_DIGEST_MISMATCH,
    BLOCKED_TOKEN_EXPIRED,
    BLOCKED_TOKEN_INVALID,
    BLOCKED_TOKEN_NOT_FOUND,
    BLOCKED_TOKEN_SCOPE_MISMATCH,
    DEFAULT_TTL_PROVIDER_PREVIEW_SECONDS,
    DEFAULT_TTL_ROLLBACK_SECONDS,
    DEFAULT_TTL_WRITE_SECONDS,
    MAX_TTL_SECONDS,
    PRODUCTION_HERMES_HOME,
    SCOPE_PROVIDER_WRITE_PREVIEW_CONFIRM,
    SCOPE_ROLLBACK_EXECUTE,
    SCOPE_WRITE_EXECUTE,
    TOKEN_DIR_RELATIVE,
    cleanup_expired_confirmation_tokens,
    create_confirmation_token,
    load_confirmation_token,
    mark_confirmation_token_used,
    redact_confirmation_token_for_audit,
    verify_confirmation_token,
)


@pytest.fixture
def dev_home(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "hermes-home-dev"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return str(home)


class TestCreateLoad:
    def test_token_created_under_dev_home(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"writePlanId": "wpln_x"}, scope=SCOPE_WRITE_EXECUTE,
            argument_digest="d" * 64, tool_id="dev_sandbox_file_write",
            operation="create_or_replace", hermes_home=dev_home,
        )
        assert issue is not None
        assert issue.token.startswith("cft_")
        assert "." in issue.token  # <tokenId>.<secret>
        token_file = Path(dev_home) / TOKEN_DIR_RELATIVE / f"{issue.tokenId}.json"
        assert token_file.exists()

    def test_plain_secret_not_stored(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WRITE_EXECUTE, argument_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert issue is not None
        secret = issue.token.split(".", 1)[1]
        token_file = Path(dev_home) / TOKEN_DIR_RELATIVE / f"{issue.tokenId}.json"
        blob = token_file.read_text(encoding="utf-8")
        # The plain secret must never appear in the stored file.
        assert secret not in blob
        assert "tokenSecret" not in blob
        assert "plainToken" not in blob

    def test_full_tokenhash_not_exposed_via_audit(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WRITE_EXECUTE, argument_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert issue is not None
        record = load_confirmation_token(issue.tokenId, hermes_home=dev_home)
        assert record is not None
        safe = redact_confirmation_token_for_audit(record)
        blob = json.dumps(safe)
        # The full tokenHash is never present in the audit-safe view.
        assert record.tokenHash not in blob
        assert "tokenHash" not in safe
        assert safe["redactionApplied"] is True

    def test_invalid_scope_rejected(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope="bogus_scope", argument_digest="d" * 64, hermes_home=dev_home
        )
        assert issue is None

    def test_production_home_rejected(self) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WRITE_EXECUTE, argument_digest="d" * 64,
            hermes_home=PRODUCTION_HERMES_HOME,
        )
        assert issue is None


class TestVerify:
    def _issue(self, dev_home, scope=SCOPE_WRITE_EXECUTE, digest="d" * 64, ttl=DEFAULT_TTL_WRITE_SECONDS):
        return create_confirmation_token(
            {"writePlanId": "wpln_x"}, scope=scope, argument_digest=digest,
            tool_id="dev_sandbox_file_write", operation="create_or_replace",
            ttl_seconds=ttl, hermes_home=dev_home,
        )

    def test_valid_token_verifies(self, dev_home: str) -> None:
        issue = self._issue(dev_home)
        result = verify_confirmation_token(
            issue.token, expected_scope=SCOPE_WRITE_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is True
        assert result.record is not None

    def test_wrong_secret_invalid(self, dev_home: str) -> None:
        issue = self._issue(dev_home)
        bad_token = issue.token.split(".", 1)[0] + ".wrongsecret"
        result = verify_confirmation_token(
            bad_token, expected_scope=SCOPE_WRITE_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is False
        assert result.blocked_reason == BLOCKED_TOKEN_INVALID

    def test_not_found(self, dev_home: str) -> None:
        result = verify_confirmation_token(
            "cft_" + "0" * 12 + ".x", expected_scope=SCOPE_WRITE_EXECUTE,
            expected_digest="d" * 64, hermes_home=dev_home,
        )
        assert result.verified is False
        assert result.blocked_reason in (BLOCKED_TOKEN_NOT_FOUND, BLOCKED_TOKEN_INVALID)

    def test_scope_mismatch(self, dev_home: str) -> None:
        issue = self._issue(dev_home, scope=SCOPE_WRITE_EXECUTE)
        result = verify_confirmation_token(
            issue.token, expected_scope=SCOPE_ROLLBACK_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is False
        assert result.blocked_reason == BLOCKED_TOKEN_SCOPE_MISMATCH

    def test_digest_mismatch(self, dev_home: str) -> None:
        issue = self._issue(dev_home, digest="d" * 64)
        result = verify_confirmation_token(
            issue.token, expected_scope=SCOPE_WRITE_EXECUTE, expected_digest="e" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is False
        assert result.blocked_reason == BLOCKED_TOKEN_DIGEST_MISMATCH

    def test_malformed_token_invalid(self, dev_home: str) -> None:
        for bad in ("", "no-dot", "cft_", None):
            result = verify_confirmation_token(
                bad, expected_scope=SCOPE_WRITE_EXECUTE, expected_digest="d" * 64,  # type: ignore[arg-type]
                hermes_home=dev_home,
            )
            assert result.verified is False
            assert result.blocked_reason == BLOCKED_TOKEN_INVALID


class TestSingleUse:
    def test_mark_used_then_replay_blocked(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WRITE_EXECUTE, argument_digest="d" * 64, hermes_home=dev_home
        )
        assert issue is not None
        ok = mark_confirmation_token_used(issue.tokenId, hermes_home=dev_home)
        assert ok is True
        result = verify_confirmation_token(
            issue.token, expected_scope=SCOPE_WRITE_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is False
        assert result.blocked_reason == BLOCKED_TOKEN_ALREADY_USED

    def test_single_use_persists_across_reload(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_ROLLBACK_EXECUTE, argument_digest="d" * 64, hermes_home=dev_home
        )
        assert issue is not None
        mark_confirmation_token_used(issue.tokenId, hermes_home=dev_home)
        # A fresh load (simulating process restart) still sees status=used.
        record = load_confirmation_token(issue.tokenId, hermes_home=dev_home)
        assert record is not None
        assert record.status == "used"
        assert record.usedAt is not None
        result = verify_confirmation_token(
            issue.token, expected_scope=SCOPE_ROLLBACK_EXECUTE, expected_digest="d" * 64,
            hermes_home=dev_home,
        )
        assert result.verified is False
        assert result.blocked_reason == BLOCKED_TOKEN_ALREADY_USED


class TestCleanup:
    def test_cleanup_deletes_only_expired(self, dev_home: str) -> None:
        expired = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WRITE_EXECUTE, argument_digest="d" * 64,
            ttl_seconds=0, hermes_home=dev_home,
        )
        active = create_confirmation_token(
            {"x": 2}, scope=SCOPE_WRITE_EXECUTE, argument_digest="d" * 64,
            ttl_seconds=300, hermes_home=dev_home,
        )
        assert expired and active
        # The expired token has expiresAt ~= createdAt (ttl=0); it is expired.
        from datetime import timedelta
        from hermes_cli.dev_web_confirmation_store import _now

        # Force the expired token into the past.
        token_file = Path(dev_home) / TOKEN_DIR_RELATIVE / f"{expired.tokenId}.json"
        data = json.loads(token_file.read_text())
        from datetime import datetime, timezone
        data["expiresAt"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        token_file.write_text(json.dumps(data))
        result = cleanup_expired_confirmation_tokens(hermes_home=dev_home)
        assert result.removed >= 1
        # Active token file still present.
        active_file = Path(dev_home) / TOKEN_DIR_RELATIVE / f"{active.tokenId}.json"
        assert active_file.exists()

    def test_cleanup_does_not_delete_non_token_files(self, dev_home: str) -> None:
        token_dir = Path(dev_home) / TOKEN_DIR_RELATIVE
        token_dir.mkdir(parents=True)
        (token_dir / "readme.txt").write_text("keep me")
        (token_dir / "not_a_token.json").write_text("{}")
        result = cleanup_expired_confirmation_tokens(hermes_home=dev_home)
        assert (token_dir / "readme.txt").exists()
        assert (token_dir / "not_a_token.json").exists()
        assert result.removed == 0

    def test_cleanup_does_not_follow_symlink(self, dev_home: str) -> None:
        import os

        token_dir = Path(dev_home) / TOKEN_DIR_RELATIVE
        token_dir.mkdir(parents=True)
        outside = Path(dev_home).parent / "outside-secret.txt"
        outside.write_text("secret")
        link = token_dir / "cft_deadbeefdeadbeef.json"  # well-formed token id name
        try:
            os.symlink(outside, link)
        except OSError:
            pytest.skip("symlink not supported")
        cleanup_expired_confirmation_tokens(hermes_home=dev_home)
        # The symlinked target must not be deleted.
        assert outside.exists()


class TestDefaultTtls:
    def test_default_ttls_within_cap(self) -> None:
        assert DEFAULT_TTL_WRITE_SECONDS == 600
        assert DEFAULT_TTL_ROLLBACK_SECONDS == 600
        assert DEFAULT_TTL_PROVIDER_PREVIEW_SECONDS == 300
        assert MAX_TTL_SECONDS == 1800
        for ttl in (DEFAULT_TTL_WRITE_SECONDS, DEFAULT_TTL_ROLLBACK_SECONDS, DEFAULT_TTL_PROVIDER_PREVIEW_SECONDS):
            assert ttl <= MAX_TTL_SECONDS

    def test_ttl_capped(self, dev_home: str) -> None:
        issue = create_confirmation_token(
            {"x": 1}, scope=SCOPE_WRITE_EXECUTE, argument_digest="d" * 64,
            ttl_seconds=10_000_000, hermes_home=dev_home,
        )
        assert issue is not None
        record = load_confirmation_token(issue.tokenId, hermes_home=dev_home)
        assert record is not None
        from datetime import datetime, timezone
        created = datetime.fromisoformat(record.createdAt)
        expires = datetime.fromisoformat(record.expiresAt)
        delta = (expires - created).total_seconds()
        assert delta <= MAX_TTL_SECONDS + 1  # allow sub-second clock granularity


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
