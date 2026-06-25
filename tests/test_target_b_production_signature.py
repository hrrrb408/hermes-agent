"""Phase 4C — Target B production signature verifier authorization tests.

Asserts ``hermes_cli/dev_web_target_b_production_signature.py`` is inert,
frozen, and fail-closed:

  - the production signature verifier is NOT authorized by default;
  - the verifier interface is implemented (Phase 4B);
  - the fixture verifier is test-only;
  - a valid fixture signature does NOT imply production authorization;
  - a forged signature is rejected;
  - an unknown publisher is rejected;
  - a mismatched checksum is rejected;
  - the aggregate report keeps production authorization NO-GO;
  - the module source contains NO forbidden primitive / production path.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_production_signature as production_signature
from hermes_cli.dev_web_target_b_production_signature import (
    assert_production_verifier_not_authorized_by_default,
    build_production_signature_report,
    build_production_signature_verifier_status,
    evaluate_signature_for_enablement,
)


class TestProductionVerifierNotAuthorized:
    def test_status_unauthorized_by_default(self) -> None:
        status = build_production_signature_verifier_status()
        assert status.verifier_interface_implemented is True
        assert status.production_verifier_authorized is False
        assert status.real_verification_enabled is False
        assert status.trusted_publishers_count == 0
        assert status.trust_token_provisioned is False
        assert status.fixture_verifier_only is True
        assert status.production_authorization == "NO-GO"

    def test_report_unauthorized(self) -> None:
        report = build_production_signature_report()
        assert report.verifier_interface_implemented is True
        assert report.production_verifier_authorized is False
        assert report.fixture_verifier_only is True
        assert report.real_verification_enabled is False
        assert report.production_authorization == "NO-GO"


class TestFixtureSignatureDoesNotImplyProduction:
    def test_evaluation_keeps_target_b_no_go(self) -> None:
        evaluation = evaluate_signature_for_enablement()
        assert evaluation.production_authorized is False
        assert evaluation.fixture_signature_does_not_imply_production is True
        assert evaluation.forged_signature_rejected is True
        assert evaluation.unknown_publisher_rejected is True
        assert evaluation.mismatched_checksum_rejected is True
        assert evaluation.production_authorization == "NO-GO"


class TestSourcePurity:
    MODULE_PATH = Path(production_signature.__file__)

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

    def test_assert_production_verifier_not_authorized_passes(self) -> None:
        assert_production_verifier_not_authorized_by_default()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
