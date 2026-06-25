"""Phase 4B — Target B signature verification layer (pure stdlib, fail-closed).

Layer 3 of the Phase 4B Target B engineering path. Defines the **signature
verification interface** and a **deterministic fixture verifier** for tests.

The production verifier is **not authorized**: no real signing key, no real
trust policy, and no real trusted-publisher registry exist. Every signature
verification request therefore returns ``trusted=False`` with the reason
``signature_verification_not_authorized`` — no matter what untrusted metadata
(forged signatures, ``approved_by_ai``, ``trust_token=fake``, ``signed=true``,
``production_runtime_go=true``) is supplied.

A deterministic **fixture verifier** is provided for tests only. It honors a
single ``fixture`` publisher and a fixed test key, and is explicitly marked
``fixture_only=True``. It computes an HMAC-SHA256 tag with the stdlib
:mod:`hmac` + :mod:`hashlib` modules — **never** a production crypto key — and
proves the verification interface can accept a genuine signature while the
production path stays disabled. The fixture verifier is **never** the
production verifier: ``productionApproved`` is always False.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no real secret read, no production access, no
real signing key.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_target_b_common import (
    TARGET_B_NO_GO,
    TARGET_B_SIGNATURE_NOT_AUTHORIZED_REASON,
    detect_target_b_untrusted_metadata,
    real_trust_token_provisioned,
    real_trusted_publishers,
    redact_target_b_payload,
)

# ---------------------------------------------------------------------------
# 1. Frozen verification modes + the fixture-only trust anchors
# ---------------------------------------------------------------------------

#: Production verification is disabled: no real signing key / trust policy.
VERIFICATION_MODE_DISABLED: str = "production_verification_disabled"

#: The deterministic fixture verifier mode (tests only — never production).
VERIFICATION_MODE_FIXTURE: str = "fixture_only_tests"

#: The single publisher the fixture verifier honors. Never trusted in
#: production — :func:`real_trusted_publishers` is empty.
FIXTURE_PUBLISHER: str = "fixture"

#: A fixed, deterministic test key for the fixture verifier. It is NOT a
#: production signing key — it exists only so a test can mint a genuine fixture
#: signature and prove the interface accepts it. It carries no authority.
_FIXTURE_VERIFY_KEY: bytes = b"target-b-fixture-verify-key-not-a-production-secret"

#: The algorithm the fixture verifier uses (mirrors the package schema set).
FIXTURE_ALGORITHM: str = "fixture-hmac-sha256"


@dataclass(frozen=True, slots=True)
class TrustedPublisher:
    """A publisher a trust policy honors. The production set is empty."""

    publisher_id: str
    trusted: bool
    source: str  # e.g. "fixture_only" / "production_trust_policy"


@dataclass(frozen=True, slots=True)
class TrustPolicy:
    """The frozen signature trust policy.

    The production policy requires a signature, never allows unsigned, and is
    anchored to a real out-of-band trust token that is **not provisioned** in
    the dev skeleton. The fixture policy is explicitly ``fixture_only``.
    """

    required_signature: bool
    allow_unsigned: bool
    trusted_publishers: tuple[TrustedPublisher, ...]
    trust_policy_version: str
    real_verification_enabled: bool
    fixture_only: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "requiredSignature": self.required_signature,
                "allowUnsigned": self.allow_unsigned,
                "trustedPublishers": [p.to_safe_dict() for p in self.trusted_publishers],
                "trustPolicyVersion": self.trust_policy_version,
                "realVerificationEnabled": self.real_verification_enabled,
                "fixtureOnly": self.fixture_only,
            }
        )


# The frozen fixture publisher (tests only).
FIXTURE_TRUSTED_PUBLISHER: TrustedPublisher = TrustedPublisher(
    publisher_id=FIXTURE_PUBLISHER,
    trusted=True,
    source="fixture_only",
)


def build_production_trust_policy() -> TrustPolicy:
    """Build the frozen production trust policy.

    A signature is required; unsigned is never allowed; real verification is
    disabled (no token, no trusted publishers). Production approval is always
    NO-GO under this policy.
    """
    return TrustPolicy(
        required_signature=True,
        allow_unsigned=False,
        trusted_publishers=(),
        trust_policy_version="production-trust-policy-v1-design-only",
        real_verification_enabled=False,
        fixture_only=False,
    )


def build_fixture_trust_policy() -> TrustPolicy:
    """Build the frozen fixture-only trust policy (tests only)."""
    return TrustPolicy(
        required_signature=True,
        allow_unsigned=False,
        trusted_publishers=(FIXTURE_TRUSTED_PUBLISHER,),
        trust_policy_version="fixture-trust-policy-tests-only",
        real_verification_enabled=False,
        fixture_only=True,
    )


# ---------------------------------------------------------------------------
# 2. Verification request / result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SignatureVerificationRequest:
    """A signature verification request. Carries untrusted metadata only."""

    package_id: str
    publisher: str
    version: str
    checksum: str
    signature: str
    signature_algorithm: str
    registry_source: str
    untrusted_metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class SignatureVerificationResult:
    """The frozen result of a signature verification. Defaults to not-trusted.

    ``trusted`` / ``production_approved`` are False unless a *production*
    verifier — which is not authorized — accepts the signature. The fixture
    verifier can set ``fixture_verified=True`` while leaving
    ``production_approved=False``.
    """

    trusted: bool
    production_approved: bool
    fixture_verified: bool
    real_verification_enabled: bool
    reason: str
    verification_mode: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "trusted": self.trusted,
                "productionApproved": self.production_approved,
                "fixtureVerified": self.fixture_verified,
                "realVerificationEnabled": self.real_verification_enabled,
                "reason": self.reason,
                "verificationMode": self.verification_mode,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


def _fixture_expected_signature(package_id: str, publisher: str, version: str) -> str:
    """The deterministic fixture signature (HMAC-SHA256). Test-only material."""
    message = f"{publisher}:{package_id}:{version}".encode("utf-8")
    tag = hmac.new(_FIXTURE_VERIFY_KEY, message, hashlib.sha256).hexdigest()
    return f"{FIXTURE_ALGORITHM}:{tag}"


def _fixture_verify(request: SignatureVerificationRequest) -> SignatureVerificationResult:
    """Deterministic fixture verifier (tests only). Never grants production."""
    ignored = detect_target_b_untrusted_metadata(request.untrusted_metadata)
    expected = _fixture_expected_signature(request.package_id, request.publisher, request.version)
    # The fixture verifier honors ONLY the fixture publisher and a signature
    # that matches the deterministic HMAC tag. Any other publisher, any forged
    # signature, any marketplace / remote source is rejected.
    fixture_ok = (
        request.publisher == FIXTURE_PUBLISHER
        and request.signature == expected
        and request.signature_algorithm == FIXTURE_ALGORITHM
        and "marketplace" not in request.registry_source
        and request.registry_source.endswith(".invalid")
    )
    return SignatureVerificationResult(
        trusted=fixture_ok,  # fixture trust only — never production trust
        production_approved=False,
        fixture_verified=fixture_ok,
        real_verification_enabled=False,
        reason="fixture_verified_tests_only" if fixture_ok else "fixture_signature_rejected",
        verification_mode=VERIFICATION_MODE_FIXTURE,
        ignored_metadata_keys=ignored,
    )


def verify_plugin_signature(
    request: Any,
    *,
    policy: TrustPolicy | None = None,
    allow_fixture: bool = False,
) -> SignatureVerificationResult:
    """Verify a plugin signature under *policy*. Fail-closed by default.

    With the default production policy (:func:`build_production_trust_policy`)
    and ``allow_fixture=False`` (the default), the result is always
    ``trusted=False`` / ``production_approved=False`` with the reason
    ``signature_verification_not_authorized`` — real verification is disabled.

    With ``allow_fixture=True`` and the fixture policy, the deterministic
    fixture verifier runs (tests only) and may set ``fixture_verified=True``
    while leaving ``production_approved=False``.

    Untrusted metadata (``approved_by_ai``, ``trust_token=fake``, ``signed``,
    ``production_runtime_go``, …) is detected and ignored — it can never flip a
    flag.
    """
    if not isinstance(request, SignatureVerificationRequest):
        return SignatureVerificationResult(
            trusted=False,
            production_approved=False,
            fixture_verified=False,
            real_verification_enabled=False,
            reason="verification_request_invalid",
            verification_mode=VERIFICATION_MODE_DISABLED,
            ignored_metadata_keys=detect_target_b_untrusted_metadata(request),
        )
    active_policy = policy if policy is not None else build_production_trust_policy()
    ignored = detect_target_b_untrusted_metadata(request.untrusted_metadata)
    # Reject unsigned packages outright — even under the fixture policy, an
    # empty / malformed signature is rejected.
    if not isinstance(request.signature, str) or not request.signature.strip():
        return SignatureVerificationResult(
            trusted=False,
            production_approved=False,
            fixture_verified=False,
            real_verification_enabled=active_policy.real_verification_enabled,
            reason="unsigned_package_rejected",
            verification_mode=VERIFICATION_MODE_DISABLED,
            ignored_metadata_keys=ignored,
        )
    # Marketplace / non-.invalid remote sources are rejected regardless of
    # policy — there is no trusted marketplace path.
    registry = request.registry_source or ""
    if "marketplace" in registry.lower():
        return SignatureVerificationResult(
            trusted=False,
            production_approved=False,
            fixture_verified=False,
            real_verification_enabled=active_policy.real_verification_enabled,
            reason="marketplace_source_rejected",
            verification_mode=VERIFICATION_MODE_DISABLED,
            ignored_metadata_keys=ignored,
        )
    # Production real verification is not authorized: no token, no trusted
    # publishers. The production verifier would only ever run when
    # `real_trust_token_provisioned()` AND `real_trusted_publishers()` are
    # populated — which the dev skeleton guarantees are not.
    if active_policy.real_verification_enabled and real_trust_token_provisioned() and real_trusted_publishers():
        # Future production branch placeholder. Real verification is NOT
        # implemented in this task and the dev skeleton holds no token, so this
        # branch is unreachable today. It is documented as the sole future
        # hook and explicitly NOT taken.
        return SignatureVerificationResult(
            trusted=False,
            production_approved=False,
            fixture_verified=False,
            real_verification_enabled=True,
            reason="production_verifier_not_implemented",
            verification_mode=VERIFICATION_MODE_DISABLED,
            ignored_metadata_keys=ignored,
        )
    # Fixture verifier (tests only). Never grants production approval.
    if allow_fixture and active_policy.fixture_only:
        return _fixture_verify(request)
    # Default: production verification not authorized.
    return SignatureVerificationResult(
        trusted=False,
        production_approved=False,
        fixture_verified=False,
        real_verification_enabled=False,
        reason=TARGET_B_SIGNATURE_NOT_AUTHORIZED_REASON,
        verification_mode=VERIFICATION_MODE_DISABLED,
        ignored_metadata_keys=ignored,
    )


# ---------------------------------------------------------------------------
# 3. Checksum verification (format + fixture only — never reads a file)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChecksumVerificationResult:
    """The frozen result of a checksum verification. Defaults to not-verified."""

    verified: bool
    fixture_verified: bool
    reason: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "verified": self.verified,
                "fixtureVerified": self.fixture_verified,
                "reason": self.reason,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


def _fixture_expected_checksum(payload: str) -> str:
    """The deterministic fixture checksum (SHA256). Test-only material."""
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def verify_package_checksum(
    package_id: Any,
    version: Any,
    declared_checksum: Any,
    *,
    fixture_payload: str | None = None,
) -> ChecksumVerificationResult:
    """Verify a package checksum. Never reads a file — fixture-only verify.

    A declared checksum is *verified* only when a caller supplies a
    ``fixture_payload`` whose deterministic SHA256 matches. With no fixture
    payload, the result is ``verified=False`` (no file is read, no hash is
    computed against a real artifact).
    """
    ignored = detect_target_b_untrusted_metadata(
        {"package_id": package_id, "version": version, "checksum": declared_checksum}
    )
    if not isinstance(declared_checksum, str) or ":" not in declared_checksum:
        return ChecksumVerificationResult(
            verified=False,
            fixture_verified=False,
            reason="checksum_malformed",
            ignored_metadata_keys=ignored,
        )
    if fixture_payload is None:
        return ChecksumVerificationResult(
            verified=False,
            fixture_verified=False,
            reason="checksum_verification_not_authorized",
            ignored_metadata_keys=ignored,
        )
    expected = _fixture_expected_checksum(fixture_payload)
    ok = declared_checksum == expected
    return ChecksumVerificationResult(
        verified=ok,
        fixture_verified=ok,
        reason="fixture_checksum_verified" if ok else "checksum_mismatch",
        ignored_metadata_keys=ignored,
    )


# ---------------------------------------------------------------------------
# 4. Trust-policy evaluation + the aggregate report
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SignatureVerificationReport:
    """The frozen aggregate signature-verification readiness report."""

    real_verification_enabled: bool
    production_approved: bool
    trusted: bool
    unsigned_rejected: bool
    forged_rejected: bool
    marketplace_rejected: bool
    unknown_publisher_rejected: bool
    production_authorization: str
    fixture_only: bool
    trust_policy: TrustPolicy

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "realVerificationEnabled": self.real_verification_enabled,
                "productionApproved": self.production_approved,
                "trusted": self.trusted,
                "unsignedRejected": self.unsigned_rejected,
                "forgedRejected": self.forged_rejected,
                "marketplaceRejected": self.marketplace_rejected,
                "unknownPublisherRejected": self.unknown_publisher_rejected,
                "productionAuthorization": self.production_authorization,
                "fixtureOnly": self.fixture_only,
                "trustPolicy": self.trust_policy.to_safe_dict(),
            }
        )


def evaluate_trust_policy(policy: Any) -> tuple[bool, tuple[str, ...]]:
    """Evaluate whether *policy* authorizes production signature trust.

    Returns ``(authorized, reasons)``. Production authorization requires a real
    trust token AND a real trusted-publisher set AND ``real_verification_enabled``
    — none of which the dev skeleton provisions. Always ``(False, reasons)``.
    """
    if not isinstance(policy, TrustPolicy):
        return False, ("policy_not_a_trust_policy",)
    reasons: list[str] = []
    if not policy.required_signature:
        reasons.append("signature_not_required")
    if policy.allow_unsigned:
        reasons.append("unsigned_allowed")
    if not policy.real_verification_enabled:
        reasons.append("real_verification_disabled")
    if not real_trust_token_provisioned():
        reasons.append("trust_token_not_provisioned")
    if not real_trusted_publishers():
        reasons.append("no_trusted_publishers")
    if policy.fixture_only:
        reasons.append("fixture_only_policy")
    authorized = (
        policy.required_signature
        and not policy.allow_unsigned
        and policy.real_verification_enabled
        and real_trust_token_provisioned()
        and bool(real_trusted_publishers())
        and not policy.fixture_only
    )
    return authorized, tuple(reasons)


def build_signature_verification_report() -> SignatureVerificationReport:
    """Build the frozen aggregate signature-verification report.

    Real verification is disabled; production is not approved; unsigned /
    forged / marketplace / unknown-publisher inputs are rejected; production
    authorization is NO-GO. Pure and deterministic.
    """
    policy = build_production_trust_policy()
    return SignatureVerificationReport(
        real_verification_enabled=False,
        production_approved=False,
        trusted=False,
        unsigned_rejected=True,
        forged_rejected=True,
        marketplace_rejected=True,
        unknown_publisher_rejected=True,
        production_authorization=TARGET_B_NO_GO,
        fixture_only=False,
        trust_policy=policy,
    )


def build_fixture_signature(
    package_id: str,
    publisher: str,
    version: str,
) -> str:
    """Mint a deterministic fixture signature (tests only).

    Exposed so a test can construct a *genuine* fixture signature and prove the
    fixture verifier accepts it — while the production path stays disabled.
    Never a production signing operation.
    """
    return _fixture_expected_signature(package_id, publisher, version)


def build_fixture_checksum(payload: str) -> str:
    """Mint a deterministic fixture checksum (tests only)."""
    return _fixture_expected_checksum(payload)


def assert_signature_layer_disabled() -> None:
    """Re-affirm the signature layer disabled invariants. Pure."""
    policy = build_production_trust_policy()
    authorized, _reasons = evaluate_trust_policy(policy)
    assert authorized is False
    assert policy.real_verification_enabled is False
    assert policy.fixture_only is False
    report = build_signature_verification_report()
    assert report.real_verification_enabled is False
    assert report.production_approved is False
    assert report.trusted is False
    assert report.production_authorization == TARGET_B_NO_GO


__all__ = [
    # modes
    "VERIFICATION_MODE_DISABLED",
    "VERIFICATION_MODE_FIXTURE",
    "FIXTURE_PUBLISHER",
    "FIXTURE_ALGORITHM",
    # models
    "TrustedPublisher",
    "FIXTURE_TRUSTED_PUBLISHER",
    "TrustPolicy",
    "SignatureVerificationRequest",
    "SignatureVerificationResult",
    "ChecksumVerificationResult",
    "SignatureVerificationReport",
    # builders
    "build_production_trust_policy",
    "build_fixture_trust_policy",
    "build_signature_verification_report",
    "build_fixture_signature",
    "build_fixture_checksum",
    # verification
    "verify_plugin_signature",
    "verify_package_checksum",
    "evaluate_trust_policy",
    # boundary
    "assert_signature_layer_disabled",
]
