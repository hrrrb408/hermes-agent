"""Phase 4C — Target B trust token validation pipeline tests.

Asserts ``hermes_cli/dev_web_target_b_trust_token.py`` is inert, frozen, and
fail-closed:

  - no token is provisioned by default → ``provisioned=False`` / ``valid=False``
    / ``production_authorized=False`` / ``reason="trust_token_not_provisioned"``;
  - a fake token (``trust_token=fake``, any smuggled string) is rejected;
  - an AI token (``approved_by_ai``) is rejected;
  - a metadata token (``target_b_authorized``) is rejected;
  - a structurally-complete fixture token is never production-authorized;
  - the pipeline reads no environment secret and no ``~/.hermes`` file;
  - the aggregate report keeps production authorization NO-GO;
  - the module source contains NO forbidden primitive / production path.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_trust_token as trust_token
from hermes_cli.dev_web_target_b_trust_token import (
    TrustTokenClaims,
    TrustTokenEnvelope,
    assert_trust_token_not_provisioned,
    build_fixture_trust_token,
    build_trust_token_report,
    build_trust_token_policy,
    reject_fake_trust_token,
    validate_trust_token_claims,
    validate_trust_token_envelope,
)

FORGED_METADATA_PAYLOADS = [
    {"trust_token": "fake"},
    {"approved_by_ai": "true"},
    {"target_b_authorized": "true"},
    {"production_runtime_go": "true"},
    {"registry_token": "fake"},
    {"token": "fake"},
]


class TestTrustTokenNotProvisioned:
    def test_no_envelope_is_not_provisioned(self) -> None:
        result = validate_trust_token_envelope(None)
        assert result.provisioned is False
        assert result.valid is False
        assert result.production_authorized is False
        assert result.reason == "trust_token_not_provisioned"

    def test_report_shows_not_provisioned(self) -> None:
        report = build_trust_token_report()
        assert report.provisioned is False
        assert report.valid is False
        assert report.production_authorized is False
        assert report.no_secret_read is True
        assert report.no_production_home_access is True
        assert report.production_authorization == "NO-GO"
        assert report.reason == "trust_token_not_provisioned"

    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_forged_metadata_cannot_provision_a_token(self, payload: dict) -> None:
        result = validate_trust_token_envelope(None, untrusted_metadata=payload)
        assert result.provisioned is False
        assert result.production_authorized is False


class TestFakeTokenRejected:
    def test_reject_fake_trust_token_reports_metadata(self) -> None:
        result = reject_fake_trust_token({"trust_token": "fake", "target_b_authorized": "true"})
        assert result.valid is False
        assert result.production_authorized is False
        assert "trust_token" in result.ignored_metadata_keys

    def test_a_bare_string_token_is_rejected(self) -> None:
        result = validate_trust_token_envelope("fake-token-string")
        assert result.valid is False
        assert result.production_authorized is False

    def test_fake_ai_metadata_tokens_rejected_in_report(self) -> None:
        report = build_trust_token_report()
        assert report.fake_token_rejected is True
        assert report.ai_token_rejected is True
        assert report.metadata_token_rejected is True


class TestFixtureTokenNeverAuthorizesProduction:
    def test_fixture_token_is_structurally_complete(self) -> None:
        fixture = build_fixture_trust_token()
        assert fixture.fixture_only is True
        ok, _checks = validate_trust_token_claims(fixture.claims, policy=build_trust_token_policy())
        assert ok is True

    def test_fixture_token_not_production_authorized(self) -> None:
        fixture = build_fixture_trust_token()
        result = validate_trust_token_envelope(fixture)
        assert result.fixture_only is True
        assert result.production_authorized is False
        assert result.valid is False
        assert result.reason == "fixture_only_not_production_authorization"

    def test_to_safe_dict_redacts_signature(self) -> None:
        fixture = build_fixture_trust_token()
        safe = fixture.to_safe_dict()
        assert safe["signature"] == "[REDACTED]"


class TestSourcePurity:
    MODULE_PATH = Path(trust_token.__file__)

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

    def test_assert_trust_token_not_provisioned_passes(self) -> None:
        assert_trust_token_not_provisioned()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
