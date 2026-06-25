"""Phase 4C — Target B trusted publisher set tests.

Asserts ``hermes_cli/dev_web_target_b_trusted_publishers.py`` is inert, frozen,
and fail-closed:

  - the production trusted publisher set is empty by default;
  - an unknown publisher is rejected;
  - a marketplace publisher is rejected;
  - an unsigned publisher is rejected;
  - a wildcard publisher is rejected;
  - a publisher with overbroad permissions is rejected;
  - a fixture publisher is honored only under the fixture policy and never
    authorizes production;
  - the module source contains NO forbidden primitive / production path.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_trusted_publishers as trusted_publishers
from hermes_cli.dev_web_target_b_trusted_publishers import (
    FIXTURE_PUBLISHER_ID,
    FIXTURE_TRUSTED_PUBLISHER,
    TrustedPublisher,
    assert_trusted_publisher_set_empty,
    build_fixture_publisher_trust_policy,
    build_production_publisher_trust_policy,
    build_trusted_publisher_report,
    evaluate_publisher_for_package,
    validate_trusted_publisher,
)


class TestTrustedPublisherSetEmpty:
    def test_production_policy_has_no_trusted_publishers(self) -> None:
        policy = build_production_publisher_trust_policy()
        assert policy.trusted_publishers == ()
        assert policy.allow_marketplace is False
        assert policy.allow_unsigned is False
        assert policy.allow_wildcard is False
        assert policy.fixture_only is False

    def test_report_shows_empty_set(self) -> None:
        report = build_trusted_publisher_report()
        assert report.trusted_publishers_count == 0
        assert report.unknown_publisher_rejected is True
        assert report.marketplace_publisher_rejected is True
        assert report.unsigned_publisher_rejected is True
        assert report.wildcard_publisher_rejected is True
        assert report.overbroad_permissions_rejected is True
        assert report.production_authorization == "NO-GO"


class TestUnknownMarketplaceWildcardRejected:
    def test_unknown_publisher_rejected(self) -> None:
        result = evaluate_publisher_for_package("unknown.publisher", "example.plugin.alpha")
        assert result.trusted is False
        assert result.production_authorized is False
        assert result.unknown_publisher_rejected is True

    def test_wildcard_publisher_rejected(self) -> None:
        result = evaluate_publisher_for_package("*", "example.plugin.alpha")
        assert result.trusted is False
        assert result.wildcard_publisher_rejected is True

    def test_marketplace_publisher_rejected(self) -> None:
        result = evaluate_publisher_for_package("marketplace.publisher", "example.plugin.alpha")
        assert result.trusted is False
        assert result.marketplace_publisher_rejected is True

    def test_unsigned_publisher_invalid(self) -> None:
        unsigned = TrustedPublisher(
            publisher_id="some.publisher",
            display_name="Unsigned",
            public_key_id="",
            allowed_package_patterns=("example.plugin.*",),
            allowed_capabilities=("display.surface",),
            allowed_permissions=("ui.render",),
            review_status="pending",
            trust_scope="tests",
            expires_at="2026-12-31T23:59:59Z",
        )
        ok, reasons = validate_trusted_publisher(unsigned)
        assert ok is False
        assert "unsigned_publisher_no_public_key" in reasons

    def test_overbroad_permissions_invalid(self) -> None:
        broad = TrustedPublisher(
            publisher_id="some.publisher",
            display_name="Broad",
            public_key_id="key",
            allowed_package_patterns=("example.plugin.*",),
            allowed_capabilities=("display.surface",),
            allowed_permissions=("runtime.execute",),
            review_status="pending",
            trust_scope="tests",
            expires_at="2026-12-31T23:59:59Z",
        )
        ok, reasons = validate_trusted_publisher(broad)
        assert ok is False
        assert any("overbroad_permission" in r for r in reasons)


class TestFixturePublisherOnly:
    def test_fixture_publisher_under_production_policy_rejected(self) -> None:
        result = evaluate_publisher_for_package(FIXTURE_PUBLISHER_ID, "example.plugin.alpha")
        assert result.trusted is False
        assert result.production_authorized is False

    def test_fixture_publisher_under_fixture_policy_is_fixture_only(self) -> None:
        result = evaluate_publisher_for_package(
            FIXTURE_PUBLISHER_ID,
            "example.plugin.alpha",
            policy=build_fixture_publisher_trust_policy(),
        )
        # Fixture trust only — never production authorization.
        assert result.trusted is True
        assert result.production_authorized is False
        assert result.fixture_only is True


class TestSourcePurity:
    MODULE_PATH = Path(trusted_publishers.__file__)

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

    def test_assert_trusted_publisher_set_empty_passes(self) -> None:
        assert_trusted_publisher_set_empty()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
