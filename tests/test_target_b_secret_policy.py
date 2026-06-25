"""Phase 4C — Target B secret handling policy tests.

Asserts ``hermes_cli/dev_web_target_b_secret_policy.py`` is inert, frozen, and
fail-closed:

  - the secret policy is default-deny;
  - no API key / env secret / production-home secret / provider key is read;
  - secret values are always redacted;
  - metadata cannot grant secret access;
  - the aggregate report keeps production authorization NO-GO;
  - the module source contains NO forbidden primitive / production path.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, never reads an environment
secret, and introduces no new route.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_secret_policy as secret_policy
from hermes_cli.dev_web_target_b_secret_policy import (
    SECRET_SCOPES,
    SecretHandlingPolicy,
    assert_secret_policy_default_deny,
    build_secret_handling_policy,
    build_secret_policy_report,
    evaluate_secret_access,
    redact_secret_payload,
    validate_secret_policy,
)


class TestSecretPolicyDefaultDeny:
    def test_default_policy_denies_everything(self) -> None:
        policy = build_secret_handling_policy()
        assert policy.default_disposition == "DENY_BY_DEFAULT"
        assert policy.read_api_keys_allowed is False
        assert policy.read_env_secrets_allowed is False
        assert policy.read_production_home_secrets_allowed is False
        assert policy.read_provider_keys_allowed is False
        assert policy.redact_secret_values is True
        assert policy.approved is False

    def test_report_default_deny(self) -> None:
        report = build_secret_policy_report()
        assert report.default_disposition == "DENY_BY_DEFAULT"
        assert report.read_api_keys_allowed is False
        assert report.read_env_secrets_allowed is False
        assert report.read_production_home_secrets_allowed is False
        assert report.read_provider_keys_allowed is False
        assert report.redact_secret_values is True
        assert report.production_authorization == "NO-GO"

    def test_every_scope_read_denied(self) -> None:
        for scope in SECRET_SCOPES:
            assert scope.read_allowed is False


class TestSecretAccessDenied:
    def test_api_key_access_denied(self) -> None:
        decision = evaluate_secret_access("api_key")
        assert decision.allowed is False
        assert decision.api_key_read is False

    def test_metadata_cannot_grant_access(self) -> None:
        decision = evaluate_secret_access(
            "api_key",
            untrusted_metadata={"api_key": "sk-fake", "secret": "true"},
        )
        assert decision.allowed is False
        assert decision.api_key_read is False
        assert decision.production_home_accessed is False

    def test_production_home_never_read(self) -> None:
        for scope in ("production_home", "state_db"):
            decision = evaluate_secret_access(scope)
            assert decision.allowed is False
            assert decision.production_home_accessed is False


class TestRedaction:
    def test_secret_payload_redacted(self) -> None:
        assert redact_secret_payload({"token": "sk-1234"})["token"] == "[REDACTED]"
        assert redact_secret_payload({"x": "ghp_fake"})["x"] == "[REDACTED]"


class TestValidation:
    def test_default_policy_valid(self) -> None:
        ok, reasons = validate_secret_policy(build_secret_handling_policy())
        assert ok is True
        assert reasons == ()

    def test_api_key_read_not_allowed(self) -> None:
        policy = SecretHandlingPolicy(
            default_disposition="DENY_BY_DEFAULT",
            read_api_keys_allowed=True,
            read_env_secrets_allowed=False,
            read_production_home_secrets_allowed=False,
            read_provider_keys_allowed=False,
            redact_secret_values=True,
            approved=False,
        )
        ok, reasons = validate_secret_policy(policy)
        assert ok is False
        assert "api_key_read_not_allowed" in reasons

    def test_production_home_read_never_allowed(self) -> None:
        policy = SecretHandlingPolicy(
            default_disposition="DENY_BY_DEFAULT",
            read_api_keys_allowed=False,
            read_env_secrets_allowed=False,
            read_production_home_secrets_allowed=True,
            read_provider_keys_allowed=False,
            redact_secret_values=True,
            approved=True,
        )
        ok, reasons = validate_secret_policy(policy)
        assert ok is False
        assert "production_home_read_never_allowed" in reasons


class TestSourcePurity:
    MODULE_PATH = Path(secret_policy.__file__)

    FORBIDDEN_USAGE_PATTERNS = (
        "import subprocess",
        "subprocess.",
        "import importlib",
        "importlib.",
        "__import__",
        "import socket",
        "socket.",
        "requests.",
        "httpx.",
        "aiohttp.",
        "urllib",
        "eval(",
        "exec(",
        "os.system",
        "os.popen",
        "os.environ",
        "Path(",
        "Path.home",
        ".resolve(",
        "open(",
        "read_text(",
        "write_text(",
        "shutil.",
    )

    FORBIDDEN_PATH_STEMS = (
        "~/.hermes",
        ".hermes/state.db",
        "production/state.db",
        "state.db",
    )

    def test_module_source_contains_no_forbidden_usage_primitive(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8")
        for pattern in self.FORBIDDEN_USAGE_PATTERNS:
            assert pattern not in source, f"source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"source must not reference {stem!r}"

    def test_assert_secret_policy_default_deny_passes(self) -> None:
        assert_secret_policy_default_deny()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
