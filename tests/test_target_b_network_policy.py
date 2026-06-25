"""Phase 4C — Target B network allowlist policy tests.

Asserts ``hermes_cli/dev_web_target_b_network_policy.py`` is inert, frozen, and
fail-closed:

  - the network allowlist is not approved by default (deny-all);
  - zero destinations are allowed;
  - wildcard hosts are denied;
  - cleartext HTTP is denied;
  - private ranges are denied;
  - no socket is ever opened;
  - the ``.invalid`` example domain is documentation-only;
  - metadata cannot allow a destination;
  - the aggregate report keeps production authorization NO-GO;
  - the module source contains NO forbidden primitive / production path.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, never opens a socket, and
introduces no new route.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_network_policy as network_policy
from hermes_cli.dev_web_target_b_network_policy import (
    NetworkAllowlistPolicy,
    NetworkDestination,
    assert_network_allowlist_not_approved,
    build_network_allowlist_policy,
    build_network_policy_report,
    evaluate_network_destination,
    validate_network_allowlist,
)


class TestNetworkAllowlistMissing:
    def test_default_policy_deny_all(self) -> None:
        policy = build_network_allowlist_policy()
        assert policy.approved is False
        assert policy.allowed_destinations == ()
        assert policy.allow_wildcard_hosts is False
        assert policy.allow_cleartext_http is False
        assert policy.allow_private_ranges is False

    def test_report_deny_all(self) -> None:
        report = build_network_policy_report()
        assert report.allowlist_present is False
        assert report.policy_approved is False
        assert report.destinations_allowed == 0
        assert report.wildcard_hosts_denied is True
        assert report.cleartext_http_denied is True
        assert report.private_ranges_denied is True
        assert report.no_socket_opened is True
        assert report.production_authorization == "NO-GO"


class TestDestinationsDenied:
    def test_https_destination_denied(self) -> None:
        dest = NetworkDestination(host="registry.example.invalid", port=443, scheme="https", purpose="fetch")
        result = evaluate_network_destination(dest)
        assert result.allowed is False
        assert result.policy_approved is False

    def test_wildcard_host_denied(self) -> None:
        result = evaluate_network_destination(NetworkDestination(host="*.com", port=443, scheme="https", purpose="x"))
        assert result.allowed is False
        assert result.wildcard_host_rejected is True

    def test_cleartext_http_denied(self) -> None:
        result = evaluate_network_destination(NetworkDestination(host="example.invalid", port=80, scheme="http", purpose="x"))
        assert result.allowed is False
        assert result.cleartext_http_rejected is True

    def test_private_range_denied(self) -> None:
        result = evaluate_network_destination(NetworkDestination(host="127.0.0.1", port=8080, scheme="tcp", purpose="x"))
        assert result.allowed is False
        assert result.private_range_rejected is True

    def test_metadata_cannot_allow(self) -> None:
        result = evaluate_network_destination(
            NetworkDestination(host="evil.example", port=443, scheme="https", purpose="x"),
            untrusted_metadata={"external network": "true"},
        )
        assert result.allowed is False


class TestValidation:
    def test_empty_deny_all_policy_is_the_only_valid_one(self) -> None:
        ok, reasons = validate_network_allowlist(build_network_allowlist_policy())
        assert ok is True
        assert reasons == ()

    def test_cleartext_policy_invalid(self) -> None:
        policy = NetworkAllowlistPolicy(
            allowlist_id="x",
            allowed_destinations=(),
            allow_wildcard_hosts=False,
            allow_cleartext_http=True,
            allow_private_ranges=False,
        )
        ok, reasons = validate_network_allowlist(policy)
        assert ok is False
        assert "cleartext_http_not_allowed" in reasons


class TestSourcePurity:
    MODULE_PATH = Path(network_policy.__file__)

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

    def test_assert_network_allowlist_not_approved_passes(self) -> None:
        assert_network_allowlist_not_approved()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
