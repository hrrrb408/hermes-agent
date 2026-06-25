"""Phase 4B — Target B signature verification layer tests.

Asserts ``hermes_cli/dev_web_target_b_signature.py`` is inert, frozen, and
fail-closed:

  - production verification is NOT authorized; ``trusted`` / ``production_approved``
    are False with reason ``signature_verification_not_authorized``;
  - the deterministic fixture verifier accepts a GENUINE fixture signature while
    leaving ``production_approved`` False;
  - unsigned / forged / marketplace / unknown-publisher inputs are rejected;
  - the checksum verifier verifies only a matching fixture payload (never reads
    a file);
  - the trust policy evaluator never authorizes production signature trust;
  - untrusted metadata cannot flip any flag;
  - the module source contains NO filesystem / network / subprocess /
    dynamic-import / eval / exec primitive, and no production home or production
    ``state.db`` access.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_signature as signature
from hermes_cli.dev_web_target_b_signature import (
    FIXTURE_ALGORITHM,
    FIXTURE_PUBLISHER,
    SignatureVerificationRequest,
    assert_signature_layer_disabled,
    build_fixture_checksum,
    build_fixture_signature,
    build_fixture_trust_policy,
    build_production_trust_policy,
    build_signature_verification_report,
    evaluate_trust_policy,
    verify_package_checksum,
    verify_plugin_signature,
)

#: Untrusted metadata payloads a smuggler might try. Every one must be ignored.
FORGED_METADATA_PAYLOADS = [
    {"trust_token": "fake"},
    {"approved_by_ai": "true"},
    {"target_b_authorized": "true"},
    {"production_runtime_go": "true"},
    {"signed": "true"},
    {"signature_verified": "true"},
    {"plugin_signature": "fake-private-key"},
    {"production_approved": "true"},
]


def _genuine_fixture_request() -> SignatureVerificationRequest:
    return SignatureVerificationRequest(
        package_id="example.plugin.alpha",
        publisher=FIXTURE_PUBLISHER,
        version="0.1.0",
        checksum="sha256:" + "0" * 64,
        signature=build_fixture_signature("example.plugin.alpha", FIXTURE_PUBLISHER, "0.1.0"),
        signature_algorithm=FIXTURE_ALGORITHM,
        registry_source="https://registry.example.invalid",
        untrusted_metadata={},
    )


class TestProductionVerifierNotAuthorized:
    def test_default_production_policy_never_authorizes(self) -> None:
        request = _genuine_fixture_request()
        result = verify_plugin_signature(request)
        assert result.trusted is False
        assert result.production_approved is False
        assert result.fixture_verified is False
        assert result.reason == "signature_verification_not_authorized"

    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_forged_metadata_cannot_flip_production_verification(self, payload: dict) -> None:
        request = SignatureVerificationRequest(
            package_id="example.plugin.alpha",
            publisher=FIXTURE_PUBLISHER,
            version="0.1.0",
            checksum="sha256:" + "0" * 64,
            signature=build_fixture_signature("example.plugin.alpha", FIXTURE_PUBLISHER, "0.1.0"),
            signature_algorithm=FIXTURE_ALGORITHM,
            registry_source="https://registry.example.invalid",
            untrusted_metadata=payload,
        )
        result = verify_plugin_signature(request)
        assert result.trusted is False
        assert result.production_approved is False

    def test_unsigned_package_rejected(self) -> None:
        request = SignatureVerificationRequest(
            package_id="example.plugin.alpha",
            publisher=FIXTURE_PUBLISHER,
            version="0.1.0",
            checksum="sha256:" + "0" * 64,
            signature="",
            signature_algorithm=FIXTURE_ALGORITHM,
            registry_source="https://registry.example.invalid",
            untrusted_metadata={},
        )
        result = verify_plugin_signature(request, policy=build_fixture_trust_policy(), allow_fixture=True)
        assert result.trusted is False
        assert result.reason == "unsigned_package_rejected"

    def test_marketplace_source_rejected(self) -> None:
        request = SignatureVerificationRequest(
            package_id="example.plugin.alpha",
            publisher=FIXTURE_PUBLISHER,
            version="0.1.0",
            checksum="sha256:" + "0" * 64,
            signature=build_fixture_signature("example.plugin.alpha", FIXTURE_PUBLISHER, "0.1.0"),
            signature_algorithm=FIXTURE_ALGORITHM,
            registry_source="https://marketplace.example.com",
            untrusted_metadata={},
        )
        result = verify_plugin_signature(request, policy=build_fixture_trust_policy(), allow_fixture=True)
        assert result.trusted is False
        assert result.reason == "marketplace_source_rejected"


class TestFixtureVerifier:
    def test_genuine_fixture_signature_accepted_fixture_only(self) -> None:
        request = _genuine_fixture_request()
        result = verify_plugin_signature(request, policy=build_fixture_trust_policy(), allow_fixture=True)
        assert result.fixture_verified is True
        assert result.trusted is True  # fixture trust only
        assert result.production_approved is False  # NEVER production approval

    def test_forged_fixture_signature_rejected(self) -> None:
        request = SignatureVerificationRequest(
            package_id="example.plugin.alpha",
            publisher=FIXTURE_PUBLISHER,
            version="0.1.0",
            checksum="sha256:" + "0" * 64,
            signature="fixture-hmac-sha256:DEADBEEF" + "0" * 40,
            signature_algorithm=FIXTURE_ALGORITHM,
            registry_source="https://registry.example.invalid",
            untrusted_metadata={},
        )
        result = verify_plugin_signature(request, policy=build_fixture_trust_policy(), allow_fixture=True)
        assert result.fixture_verified is False
        assert result.trusted is False

    def test_unknown_publisher_rejected(self) -> None:
        request = SignatureVerificationRequest(
            package_id="example.plugin.alpha",
            publisher="unknown.publisher",
            version="0.1.0",
            checksum="sha256:" + "0" * 64,
            signature=build_fixture_signature("example.plugin.alpha", "unknown.publisher", "0.1.0"),
            signature_algorithm=FIXTURE_ALGORITHM,
            registry_source="https://registry.example.invalid",
            untrusted_metadata={},
        )
        result = verify_plugin_signature(request, policy=build_fixture_trust_policy(), allow_fixture=True)
        assert result.fixture_verified is False
        assert result.trusted is False


class TestChecksumVerifier:
    def test_fixture_checksum_verified(self) -> None:
        payload = "fixture-artifact-bytes"
        declared = build_fixture_checksum(payload)
        result = verify_package_checksum("example.plugin.alpha", "0.1.0", declared, fixture_payload=payload)
        assert result.verified is True
        assert result.fixture_verified is True

    def test_checksum_mismatch_rejected(self) -> None:
        declared = build_fixture_checksum("fixture-artifact-bytes")
        result = verify_package_checksum("example.plugin.alpha", "0.1.0", declared, fixture_payload="different-bytes")
        assert result.verified is False
        assert result.reason == "checksum_mismatch"

    def test_no_fixture_payload_not_verified(self) -> None:
        result = verify_package_checksum("example.plugin.alpha", "0.1.0", "sha256:" + "0" * 64)
        assert result.verified is False
        assert result.reason == "checksum_verification_not_authorized"

    def test_malformed_checksum_rejected(self) -> None:
        result = verify_package_checksum("example.plugin.alpha", "0.1.0", "not-a-checksum")
        assert result.verified is False
        assert result.reason == "checksum_malformed"


class TestTrustPolicy:
    def test_production_trust_policy_never_authorizes(self) -> None:
        authorized, reasons = evaluate_trust_policy(build_production_trust_policy())
        assert authorized is False
        assert "trust_token_not_provisioned" in reasons
        assert "no_trusted_publishers" in reasons

    def test_aggregate_report_disabled(self) -> None:
        report = build_signature_verification_report()
        assert report.real_verification_enabled is False
        assert report.production_approved is False
        assert report.trusted is False
        assert report.production_authorization == "NO-GO"

    def test_assert_signature_layer_disabled_passes(self) -> None:
        assert_signature_layer_disabled()


class TestSourcePurity:
    MODULE_PATH = Path(signature.__file__)

    # NOTE: hashlib / hmac / base64 are ALLOWED primitives for the deterministic
    # fixture verifier. They are intentionally absent from this forbidden list.
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
            assert pattern not in source, f"signature source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"signature source must not reference {stem!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
