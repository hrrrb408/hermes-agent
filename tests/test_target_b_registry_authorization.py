"""Phase 4C — Target B registry trust policy authorization tests.

Asserts ``hermes_cli/dev_web_target_b_registry_policy.py`` is inert, frozen, and
fail-closed:

  - the registry is DISABLED by default;
  - network / fetch / marketplace are off;
  - unsigned packages and wildcard domains are rejected;
  - the trusted publisher set is empty;
  - the example URL is the reserved ``.invalid`` domain;
  - metadata cannot enable the registry;
  - the aggregate report keeps production authorization NO-GO;
  - the module source contains NO forbidden primitive / production path.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_registry_policy as registry_policy
from hermes_cli.dev_web_target_b_registry_policy import (
    RegistryAllowlist,
    RegistryPackagePolicy,
    RegistryTrustPolicyApproval,
    assert_registry_trust_policy_not_approved,
    build_registry_authorization_report,
    build_registry_trust_policy_approval,
    evaluate_registry_enablement,
    validate_registry_trust_policy_approval,
)


class TestRegistryDisabled:
    def test_default_approval_not_approved(self) -> None:
        approval = build_registry_trust_policy_approval()
        assert approval.approved is False
        assert approval.allowlist.allowed_domains == ()
        assert approval.allowlist.trusted_publishers_count == 0
        assert "marketplace" in approval.allowlist.marketplace_policy
        assert "disabled" in approval.allowlist.marketplace_policy

    def test_evaluation_disabled(self) -> None:
        result = evaluate_registry_enablement()
        assert result.registry_disabled is True
        assert result.network_allowed is False
        assert result.fetch_allowed is False
        assert result.marketplace_allowed is False
        assert result.production_authorization == "NO-GO"

    def test_report_disabled(self) -> None:
        report = build_registry_authorization_report()
        assert report.registry_disabled is True
        assert report.network_allowed is False
        assert report.fetch_allowed is False
        assert report.marketplace_allowed is False
        assert report.allow_unsigned is False
        assert report.wildcard_domains_rejected is True
        assert report.trusted_publishers_count == 0
        assert "example.invalid" in report.registry_url_example
        assert report.production_authorization == "NO-GO"

    def test_metadata_cannot_enable_registry(self) -> None:
        result = evaluate_registry_enablement(
            untrusted_metadata={"registry_authorized": "true", "registry_token": "fake"}
        )
        assert result.registry_disabled is True
        assert result.fetch_allowed is False


class TestValidation:
    def test_unsigned_not_allowed(self) -> None:
        approval = build_registry_trust_policy_approval()
        ok, reasons = validate_registry_trust_policy_approval(approval)
        assert ok is False
        # The default allowlist is empty + no reviewer approval, so it fails.
        assert "reviewer_approval_required" in reasons

    def test_wildcard_domains_rejected(self) -> None:
        approval = RegistryTrustPolicyApproval(
            registry_id="x",
            registry_url="https://registry.example.invalid",
            allowlist=RegistryAllowlist(
                registry_id="x",
                allowed_domains=("*.com",),
                required_signature_algorithms=("ed25519",),
                trusted_publishers_count=0,
                marketplace_policy="disabled",
                network_policy_id="net-1",
            ),
            package_policy=RegistryPackagePolicy(
                require_signature=True,
                allow_unsigned=False,
                require_trusted_publisher=True,
                require_reviewed_package=True,
            ),
            network_policy_id="net-1",
            reviewer_approval_id="rev-1",
        )
        ok, reasons = validate_registry_trust_policy_approval(approval)
        assert ok is False
        assert any("wildcard_domain" in r for r in reasons)


class TestSourcePurity:
    MODULE_PATH = Path(registry_policy.__file__)

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

    def test_assert_registry_trust_policy_not_approved_passes(self) -> None:
        assert_registry_trust_policy_not_approved()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
