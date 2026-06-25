"""Phase 4C — Target B production signature verifier authorization (pure stdlib).

Layer 4 of the Phase 4C Target B authorization package. Extends the Phase 4B
signature verification layer with a **production signature verifier
authorization adapter** — the structure that decides whether a *real* production
signature verifier is authorized to vouch for a package.

The production verifier is **not authorized** by default: there is no real
signing key, no real trust policy, and no real trusted-publisher set. A genuine
fixture signature therefore does **not** imply production authorization, and the
absence of the production verifier keeps Target B NO-GO.

The adapter:

  - declares the verifier interface (the Phase 4B interface is implemented);
  - reports the production verifier as unauthorized by default;
  - keeps the deterministic fixture verifier test-only;
  - re-uses the Phase 4B ``verify_plugin_signature`` / ``evaluate_trust_policy``
    machinery so a forged signature, an unknown publisher, and a mismatched
    checksum are rejected.

Pure / deterministic / stdlib-only. No external crypto dependency beyond the
stdlib ``hmac`` + ``hashlib`` the Phase 4B fixture verifier already uses. No
filesystem access, no network, no subprocess, no dynamic import, no real signing
key.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hermes_cli.dev_web_target_b_authorization_common import (
    TARGET_B_AUTHORIZATION_NO_GO,
    TARGET_B_FIXTURE_NOT_PRODUCTION_REASON,
)
from hermes_cli.dev_web_target_b_common import (
    real_trusted_publishers,
    real_trust_token_provisioned,
    redact_target_b_payload,
)
from hermes_cli.dev_web_target_b_signature import (
    FIXTURE_PUBLISHER,
    SignatureVerificationRequest,
    assert_signature_layer_disabled,
    build_fixture_signature,
    build_fixture_trust_policy,
    build_production_trust_policy,
    build_signature_verification_report,
    evaluate_trust_policy,
    verify_package_checksum,
    verify_plugin_signature,
)
from hermes_cli.dev_web_target_b_trusted_publishers import (
    build_production_publisher_trust_policy,
)

# ---------------------------------------------------------------------------
# 1. The production signature verifier status (frozen dataclass)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProductionSignatureVerifierStatus:
    """The frozen production signature verifier authorization status.

    The verifier interface is implemented (Phase 4B), but the production
    verifier is not authorized: no real trust token, no trusted publishers.
    """

    verifier_interface_implemented: bool
    production_verifier_authorized: bool
    real_verification_enabled: bool
    trusted_publishers_count: int
    trust_token_provisioned: bool
    fixture_verifier_only: bool
    production_authorization: str
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "verifierInterfaceImplemented": self.verifier_interface_implemented,
                "productionVerifierAuthorized": self.production_verifier_authorized,
                "realVerificationEnabled": self.real_verification_enabled,
                "trustedPublishersCount": self.trusted_publishers_count,
                "trustTokenProvisioned": self.trust_token_provisioned,
                "fixtureVerifierOnly": self.fixture_verifier_only,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
            }
        )


@dataclass(frozen=True, slots=True)
class SignatureEnablementEvaluation:
    """The frozen result of evaluating the verifier for enablement."""

    production_authorized: bool
    fixture_signature_does_not_imply_production: bool
    forged_signature_rejected: bool
    unknown_publisher_rejected: bool
    mismatched_checksum_rejected: bool
    production_authorization: str
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "productionAuthorized": self.production_authorized,
                "fixtureSignatureDoesNotImplyProduction": self.fixture_signature_does_not_imply_production,
                "forgedSignatureRejected": self.forged_signature_rejected,
                "unknownPublisherRejected": self.unknown_publisher_rejected,
                "mismatchedChecksumRejected": self.mismatched_checksum_rejected,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
            }
        )


@dataclass(frozen=True, slots=True)
class ProductionSignatureReport:
    """The frozen aggregate production-signature authorization report."""

    verifier_interface_implemented: bool
    production_verifier_authorized: bool
    fixture_verifier_only: bool
    real_verification_enabled: bool
    production_authorization: str
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "verifierInterfaceImplemented": self.verifier_interface_implemented,
                "productionVerifierAuthorized": self.production_verifier_authorized,
                "fixtureVerifierOnly": self.fixture_verifier_only,
                "realVerificationEnabled": self.real_verification_enabled,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
            }
        )


# ---------------------------------------------------------------------------
# 2. Status + enablement evaluation
# ---------------------------------------------------------------------------


def build_production_signature_verifier_status() -> ProductionSignatureVerifierStatus:
    """Build the frozen production signature verifier status.

    The interface is implemented; the production verifier is NOT authorized
    (no real trust token, no trusted publishers); the fixture verifier is
    test-only. Production authorization stays NO-GO. Pure and deterministic.
    """
    return ProductionSignatureVerifierStatus(
        verifier_interface_implemented=True,
        production_verifier_authorized=False,
        real_verification_enabled=False,
        trusted_publishers_count=len(real_trusted_publishers()),
        trust_token_provisioned=real_trust_token_provisioned(),
        fixture_verifier_only=True,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="production_verifier_not_authorized",
    )


def evaluate_signature_for_enablement() -> SignatureEnablementEvaluation:
    """Evaluate the production signature verifier for Target B enablement.

    Proves, deterministically, that:
      - a valid fixture signature does NOT imply production authorization;
      - a forged signature is rejected;
      - an unknown publisher is rejected;
      - a mismatched checksum is rejected;
    and that the production verifier being unavailable keeps Target B NO-GO.
    """
    # 1. A genuine fixture signature is accepted by the fixture verifier but
    #    production_approved stays False.
    genuine = SignatureVerificationRequest(
        package_id="example.plugin.alpha",
        publisher=FIXTURE_PUBLISHER,
        version="0.1.0",
        checksum="sha256:" + "0" * 64,
        signature=build_fixture_signature("example.plugin.alpha", FIXTURE_PUBLISHER, "0.1.0"),
        signature_algorithm="fixture-hmac-sha256",
        registry_source="https://registry.example.invalid",
        untrusted_metadata={},
    )
    genuine_result = verify_plugin_signature(
        genuine, policy=build_fixture_trust_policy(), allow_fixture=True
    )
    fixture_does_not_imply_production = (
        genuine_result.fixture_verified is True and genuine_result.production_approved is False
    )

    # 2. A forged signature is rejected.
    forged = SignatureVerificationRequest(
        package_id="example.plugin.alpha",
        publisher=FIXTURE_PUBLISHER,
        version="0.1.0",
        checksum="sha256:" + "0" * 64,
        signature="forged-signature",
        signature_algorithm="fixture-hmac-sha256",
        registry_source="https://registry.example.invalid",
        untrusted_metadata={},
    )
    forged_result = verify_plugin_signature(
        forged, policy=build_fixture_trust_policy(), allow_fixture=True
    )
    forged_rejected = forged_result.trusted is False and forged_result.production_approved is False

    # 3. An unknown publisher is rejected.
    unknown = SignatureVerificationRequest(
        package_id="example.plugin.alpha",
        publisher="unknown.publisher",
        version="0.1.0",
        checksum="sha256:" + "0" * 64,
        signature=build_fixture_signature("example.plugin.alpha", "unknown.publisher", "0.1.0"),
        signature_algorithm="fixture-hmac-sha256",
        registry_source="https://registry.example.invalid",
        untrusted_metadata={},
    )
    unknown_result = verify_plugin_signature(
        unknown, policy=build_fixture_trust_policy(), allow_fixture=True
    )
    unknown_rejected = unknown_result.trusted is False

    # 4. A mismatched checksum is rejected.
    checksum_result = verify_package_checksum(
        "example.plugin.alpha",
        "0.1.0",
        "sha256:" + "f" * 64,
        fixture_payload="some-fixture-payload",
    )
    mismatched_rejected = checksum_result.verified is False

    production_authorized = False  # production verifier unavailable

    return SignatureEnablementEvaluation(
        production_authorized=production_authorized,
        fixture_signature_does_not_imply_production=bool(fixture_does_not_imply_production),
        forged_signature_rejected=bool(forged_rejected),
        unknown_publisher_rejected=bool(unknown_rejected),
        mismatched_checksum_rejected=bool(mismatched_rejected),
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="production_verifier_not_authorized",
    )


def build_production_signature_report() -> ProductionSignatureReport:
    """Build the frozen aggregate production-signature authorization report.

    The verifier interface is implemented; the production verifier is not
    authorized; the fixture verifier is test-only. Production authorization
    stays NO-GO. Pure and deterministic.
    """
    return ProductionSignatureReport(
        verifier_interface_implemented=True,
        production_verifier_authorized=False,
        fixture_verifier_only=True,
        real_verification_enabled=False,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="production_verifier_not_authorized",
    )


def assert_production_verifier_not_authorized_by_default() -> None:
    """Re-affirm the production signature verifier is not authorized. Pure."""
    status = build_production_signature_verifier_status()
    assert status.verifier_interface_implemented is True
    assert status.production_verifier_authorized is False
    assert status.real_verification_enabled is False
    assert status.trusted_publishers_count == 0
    assert status.trust_token_provisioned is False
    assert status.fixture_verifier_only is True
    assert status.production_authorization == TARGET_B_AUTHORIZATION_NO_GO
    # The production trust policy never authorizes.
    authorized, _reasons = evaluate_trust_policy(build_production_trust_policy())
    assert authorized is False
    # The enablement evaluation keeps Target B NO-GO.
    evaluation = evaluate_signature_for_enablement()
    assert evaluation.production_authorized is False
    assert evaluation.fixture_signature_does_not_imply_production is True
    assert evaluation.forged_signature_rejected is True
    assert evaluation.unknown_publisher_rejected is True
    assert evaluation.mismatched_checksum_rejected is True
    # The Phase 4B signature layer is still gated.
    assert_signature_layer_disabled()


__all__ = [
    # schema
    "ProductionSignatureVerifierStatus",
    "SignatureEnablementEvaluation",
    "ProductionSignatureReport",
    # status + evaluation
    "build_production_signature_verifier_status",
    "evaluate_signature_for_enablement",
    "build_production_signature_report",
    # boundary
    "assert_production_verifier_not_authorized_by_default",
]
