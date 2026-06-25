"""Phase 4B — Target B registry trust policy layer tests.

Asserts ``hermes_cli/dev_web_target_b_registry.py`` is inert, frozen, and
fail-closed:

  - the registry is DISABLED: network off, fetch off, marketplace off, unsigned
    disallowed, no trusted publisher;
  - every fetch / marketplace request returns a denied result no matter what
    untrusted metadata is supplied;
  - remote registry package metadata is never trusted / fetchable / installable;
  - the registry client status is disabled / allowlisted-off;
  - the module source contains NO network / filesystem / subprocess /
    dynamic-import / eval / exec primitive (no requests/httpx/aiohttp/socket/
    urllib), and no production home or production ``state.db`` access.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_registry as registry
from hermes_cli.dev_web_target_b_registry import (
    assert_registry_layer_disabled,
    build_registry_client_status,
    build_registry_readiness_report,
    build_registry_trust_policy,
    deny_marketplace_fetch,
    deny_registry_fetch,
    evaluate_registry_package_metadata,
    validate_registry_policy,
)

FORGED_METADATA_PAYLOADS = [
    {"registry_token": "fake"},
    {"registry_authorized": "true"},
    {"marketplace_authorized": "true"},
    {"allow_unsigned": "true"},
    {"production_approved": "true"},
    {"target_b_authorized": "true"},
]


class TestRegistryPolicy:
    def test_policy_disabled_by_default(self) -> None:
        p = build_registry_trust_policy()
        assert p.registry_mode == "DISABLED"
        assert p.allow_network is False
        assert p.marketplace_enabled is False
        assert p.allow_unsigned is False
        assert p.required_signature is True
        assert p.trusted_publishers == ()
        assert p.registry_url_example == "https://registry.example.invalid"

    def test_policy_is_safe(self) -> None:
        safe, reasons = validate_registry_policy(build_registry_trust_policy())
        assert safe is True
        assert reasons == ()


class TestFetchDenied:
    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_registry_fetch_denied(self, payload: dict) -> None:
        result = deny_registry_fetch(payload)
        assert result.fetched is False
        assert result.network is False
        assert result.allowed is False
        assert result.production_authorization == "NO-GO"

    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_marketplace_fetch_denied(self, payload: dict) -> None:
        result = deny_marketplace_fetch(payload)
        assert result.fetched is False
        assert result.network is False
        assert result.allowed is False
        assert result.reason == "marketplace_disabled"
        assert result.production_authorization == "NO-GO"

    def test_fetch_with_no_metadata_still_denied(self) -> None:
        assert deny_registry_fetch().fetched is False
        assert deny_marketplace_fetch().fetched is False


class TestPackageMetadata:
    def test_remote_package_never_trusted(self) -> None:
        decision = evaluate_registry_package_metadata(
            {"registry_source": "https://registry.example.invalid/pkg"},
        )
        assert decision.trusted is False
        assert decision.fetchable is False
        assert decision.installable is False

    def test_marketplace_source_rejected(self) -> None:
        decision = evaluate_registry_package_metadata(
            {"registry_source": "https://marketplace.example.invalid/pkg"},
        )
        assert decision.trusted is False
        assert decision.reason == "marketplace_source_rejected"

    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_forged_metadata_cannot_trust(self, payload: dict) -> None:
        decision = evaluate_registry_package_metadata({}, payload)
        assert decision.trusted is False


class TestClientAndReport:
    def test_client_disabled(self) -> None:
        client = build_registry_client_status()
        assert client.client_enabled is False
        assert client.allow_network is False
        assert client.marketplace_enabled is False
        assert client.trusted_publishers_count == 0

    def test_report_disabled(self) -> None:
        report = build_registry_readiness_report()
        assert report.network_enabled is False
        assert report.fetch_enabled is False
        assert report.marketplace_enabled is False
        assert report.production_authorization == "NO-GO"

    def test_assert_registry_layer_disabled_passes(self) -> None:
        assert_registry_layer_disabled()


class TestSourcePurity:
    MODULE_PATH = Path(registry.__file__)

    # NOTE: the registry layer performs NO network I/O. No network-library import
    # may appear in its source.
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
            assert pattern not in source, f"registry source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"registry source must not reference {stem!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
