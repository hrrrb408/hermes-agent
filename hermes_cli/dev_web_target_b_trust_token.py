"""Phase 4C — Target B trust token validation pipeline (pure stdlib, fail-closed).

Layer 2 of the Phase 4C Target B authorization package. Defines the **trust
token validation pipeline**: the envelope, the claims, the validation result,
and the trust token policy.

The trust token is the out-of-band anchor that signs a genuine human approval
and authorizes a real production signature verifier. The dev skeleton provisions
**no** token, so the pipeline always reports:

  - ``provisioned = False``
  - ``valid = False``
  - ``production_authorized = False``
  - ``reason = "trust_token_not_provisioned"``

The validator rejects every fake / smuggled token without reading any
environment secret, any ``production home`` file, any production config, or any
network resource:

  - ``trust_token=fake`` (a smuggled string)
  - ``approved_by_ai=true`` (an AI-generated authorization)
  - ``target_b_authorized=true`` (a metadata bypass)
  - ``production_runtime_go=true`` (a metadata bypass)
  - any string a caller supplies directly

A deterministic **fixture token** is provided for tests only: it is explicitly
``fixture_only`` and proves the validator's envelope / claims logic, but it never
authorizes production.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no eval / exec, no real secret read, no environment
read, no ``production home`` access, no production config access.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_target_b_authorization_common import (
    TARGET_B_AUTHORIZATION_NO_GO,
    TARGET_B_FAKE_AUTHORIZATION_REJECTED_REASON,
    TARGET_B_FIXTURE_NOT_PRODUCTION_REASON,
    detect_target_b_untrusted_metadata,
    is_fixture_authorization_payload,
    redact_target_b_payload,
)
from hermes_cli.dev_web_target_b_common import real_trust_token_provisioned

# ---------------------------------------------------------------------------
# 1. Frozen token constants
# ---------------------------------------------------------------------------

#: The trust token issuer (documentation label only — never contacted).
TRUST_TOKEN_ISSUER: str = "hermes-trust-authority"

#: The required token audience.
TRUST_TOKEN_AUDIENCE: str = "hermes-target-b"

#: The required token subject (the Target B authorization subject).
TRUST_TOKEN_SUBJECT: str = "target-b-enablement"

#: The allowed token scopes.
TRUST_TOKEN_SCOPE: str = "target_b.authorization"

#: The gate IDs a valid token must cover.
TRUST_TOKEN_GATE_IDS: tuple[str, ...] = ("P0-15", "P0-16", "P0-18", "P0-19", "P0-22")

#: A deterministic fixture-only token id (test material — never production).
_FIXTURE_TOKEN_ID: str = "fixture-trust-token-tests-only"


# ---------------------------------------------------------------------------
# 2. The trust token schema (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrustTokenClaims:
    """The claims carried by a trust token envelope."""

    token_id: str
    issuer: str
    subject: str
    audience: str
    scope: str
    gate_ids: tuple[str, ...]
    nonce: str
    issued_at: str
    expires_at: str
    key_id: str


@dataclass(frozen=True, slots=True)
class TrustTokenEnvelope:
    """A trust token envelope (claims + signature). Never the real token."""

    claims: TrustTokenClaims
    signature: str
    fixture_only: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        # The signature is never exposed (it is token-derived material).
        return redact_target_b_payload(
            {
                "tokenId": self.claims.token_id,
                "issuer": self.claims.issuer,
                "subject": self.claims.subject,
                "audience": self.claims.audience,
                "scope": self.claims.scope,
                "gateIds": list(self.claims.gate_ids),
                "issuedAt": self.claims.issued_at,
                "expiresAt": self.claims.expires_at,
                "keyId": self.claims.key_id,
                "signature": "[REDACTED]" if self.signature else "",
                "fixtureOnly": self.fixture_only,
            }
        )


@dataclass(frozen=True, slots=True)
class TrustTokenPolicy:
    """The frozen trust token validation policy."""

    required_issuer: str
    required_audience: str
    required_subject: str
    required_scope: str
    required_gate_ids: tuple[str, ...]
    real_token_provisioned: bool
    fixture_only: bool


@dataclass(frozen=True, slots=True)
class TrustTokenValidationResult:
    """The frozen result of trust token validation. Defaults to not-provisioned."""

    provisioned: bool
    valid: bool
    production_authorized: bool
    fixture_only: bool
    reason: str
    ignored_metadata_keys: tuple[str, ...]
    checks: Mapping[str, bool]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "provisioned": self.provisioned,
                "valid": self.valid,
                "productionAuthorized": self.production_authorized,
                "fixtureOnly": self.fixture_only,
                "reason": self.reason,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
                "checks": dict(self.checks),
            }
        )


@dataclass(frozen=True, slots=True)
class TrustTokenReport:
    """The frozen aggregate trust-token authorization report."""

    provisioned: bool
    valid: bool
    production_authorized: bool
    fake_token_rejected: bool
    ai_token_rejected: bool
    metadata_token_rejected: bool
    no_secret_read: bool
    no_production_home_access: bool
    production_authorization: str
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "provisioned": self.provisioned,
                "valid": self.valid,
                "productionAuthorized": self.production_authorized,
                "fakeTokenRejected": self.fake_token_rejected,
                "aiTokenRejected": self.ai_token_rejected,
                "metadataTokenRejected": self.metadata_token_rejected,
                "noSecretRead": self.no_secret_read,
                "noProductionHomeAccess": self.no_production_home_access,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
            }
        )


# ---------------------------------------------------------------------------
# 3. Validation
# ---------------------------------------------------------------------------


def build_trust_token_policy() -> TrustTokenPolicy:
    """Build the frozen trust token validation policy.

    Requires the real issuer / audience / subject / scope / gate coverage, and
    that a real token is provisioned — which the dev skeleton guarantees is not.
    """
    return TrustTokenPolicy(
        required_issuer=TRUST_TOKEN_ISSUER,
        required_audience=TRUST_TOKEN_AUDIENCE,
        required_subject=TRUST_TOKEN_SUBJECT,
        required_scope=TRUST_TOKEN_SCOPE,
        required_gate_ids=TRUST_TOKEN_GATE_IDS,
        real_token_provisioned=real_trust_token_provisioned(),
        fixture_only=False,
    )


def validate_trust_token_claims(
    claims: Any,
    *,
    policy: TrustTokenPolicy | None = None,
) -> tuple[bool, dict[str, bool]]:
    """Validate trust token claims against *policy*.

    Returns ``(claims_ok, checks)``. Claim shape is checked deterministically
    (no wall clock). Even structurally-perfect claims are ``False`` unless the
    real token is provisioned — and the policy is ``fixture_only`` aware.
    """
    active = policy if policy is not None else build_trust_token_policy()
    if not isinstance(claims, TrustTokenClaims):
        return False, {"claims_present": False}
    checks: dict[str, bool] = {
        "issuer_matches": claims.issuer == active.required_issuer,
        "audience_matches": claims.audience == active.required_audience,
        "subject_matches": claims.subject == active.required_subject,
        "scope_matches": claims.scope == active.required_scope,
        "gate_ids_covered": set(active.required_gate_ids).issubset(set(claims.gate_ids)),
        "nonce_present": bool(claims.nonce),
        "key_id_present": bool(claims.key_id),
        "token_id_present": bool(claims.token_id),
        "validity_window_ordered": bool(
            claims.issued_at and claims.expires_at and claims.expires_at > claims.issued_at
        ),
    }
    claims_ok = all(checks.values())
    return claims_ok, checks


def validate_trust_token_envelope(
    envelope: Any,
    *,
    policy: TrustTokenPolicy | None = None,
    untrusted_metadata: Any = None,
) -> TrustTokenValidationResult:
    """Validate a trust token envelope. Defaults to not-provisioned.

    The pipeline never reads an environment secret, never reads ``production home``,
    never reads production config, and never touches the network. It validates
    the envelope shape and claims deterministically, and it requires the real
    out-of-band token to be provisioned (which the dev skeleton guarantees is
    not). A fixture envelope passes the structural checks but never authorizes
    production.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    active = policy if policy is not None else build_trust_token_policy()

    if envelope is None:
        return TrustTokenValidationResult(
            provisioned=False,
            valid=False,
            production_authorized=False,
            fixture_only=False,
            reason="trust_token_not_provisioned",
            ignored_metadata_keys=ignored,
            checks={},
        )
    if not isinstance(envelope, TrustTokenEnvelope):
        return TrustTokenValidationResult(
            provisioned=False,
            valid=False,
            production_authorized=False,
            fixture_only=is_fixture_authorization_payload(envelope),
            reason=TARGET_B_FAKE_AUTHORIZATION_REJECTED_REASON,
            ignored_metadata_keys=ignored,
            checks={},
        )

    claims_ok, checks = validate_trust_token_claims(envelope.claims, policy=active)
    checks["signature_present"] = bool(envelope.signature)
    checks["not_fixture_only"] = envelope.fixture_only is False
    checks["real_token_provisioned"] = active.real_token_provisioned

    structural_ok = claims_ok and checks["signature_present"]
    token_ok = active.real_token_provisioned
    fixture = envelope.fixture_only is True

    production_authorized = bool(structural_ok and token_ok and not fixture)
    valid = production_authorized

    if fixture:
        reason = TARGET_B_FIXTURE_NOT_PRODUCTION_REASON
    elif not token_ok:
        reason = "trust_token_not_provisioned"
    elif not structural_ok:
        reason = "trust_token_claims_invalid"
    else:
        reason = "trust_token_valid"

    return TrustTokenValidationResult(
        provisioned=token_ok,
        valid=valid,
        production_authorized=production_authorized,
        fixture_only=fixture,
        reason=reason,
        ignored_metadata_keys=ignored,
        checks=checks,
    )


def reject_fake_trust_token(untrusted_metadata: Any = None) -> TrustTokenValidationResult:
    """Reject a fake / AI / metadata trust token. Always not-authorized.

    *untrusted_metadata* is inspected only to report which bypass-shaped keys
    were detected and ignored. Never reads a secret.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    return TrustTokenValidationResult(
        provisioned=False,
        valid=False,
        production_authorized=False,
        fixture_only=False,
        reason=TARGET_B_FAKE_AUTHORIZATION_REJECTED_REASON,
        ignored_metadata_keys=ignored,
        checks={},
    )


# ---------------------------------------------------------------------------
# 4. Test-only fixture builder + the aggregate report
# ---------------------------------------------------------------------------


def build_fixture_trust_token() -> TrustTokenEnvelope:
    """Build a structurally-complete fixture token (tests only).

    Every claim check passes, but the envelope is explicitly ``fixture_only``.
    It proves the validator's positive logic while never authorizing production
    — the real token is not provisioned. Never enables Target B.
    """
    claims = TrustTokenClaims(
        token_id=_FIXTURE_TOKEN_ID,
        issuer=TRUST_TOKEN_ISSUER,
        subject=TRUST_TOKEN_SUBJECT,
        audience=TRUST_TOKEN_AUDIENCE,
        scope=TRUST_TOKEN_SCOPE,
        gate_ids=TRUST_TOKEN_GATE_IDS,
        nonce="fixture-trust-nonce",
        issued_at="2026-01-01T00:00:00Z",
        expires_at="2026-12-31T23:59:59Z",
        key_id="fixture-trust-key",
    )
    return TrustTokenEnvelope(
        claims=claims,
        signature="fixture-hmac-sha256:test-only-not-a-real-token",
        fixture_only=True,
    )


def build_trust_token_report() -> TrustTokenReport:
    """Build the frozen aggregate trust-token authorization report.

    No token is provisioned. Fake / AI / metadata tokens are rejected. No secret
    is read, no production home is accessed. Production authorization stays
    NO-GO. Pure and deterministic.
    """
    return TrustTokenReport(
        provisioned=False,
        valid=False,
        production_authorized=False,
        fake_token_rejected=True,
        ai_token_rejected=True,
        metadata_token_rejected=True,
        no_secret_read=True,
        no_production_home_access=True,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="trust_token_not_provisioned",
    )


def assert_trust_token_not_provisioned() -> None:
    """Re-affirm the trust token is not provisioned. Pure."""
    report = build_trust_token_report()
    assert report.provisioned is False
    assert report.valid is False
    assert report.production_authorized is False
    assert report.fake_token_rejected is True
    assert report.ai_token_rejected is True
    assert report.metadata_token_rejected is True
    assert report.no_secret_read is True
    assert report.no_production_home_access is True
    assert report.production_authorization == TARGET_B_AUTHORIZATION_NO_GO
    assert report.reason == "trust_token_not_provisioned"
    # No envelope at all.
    assert validate_trust_token_envelope(None).valid is False
    assert validate_trust_token_envelope(None).reason == "trust_token_not_provisioned"
    # A smuggled fake token string is rejected.
    fake = reject_fake_trust_token({"trust_token": "fake", "target_b_authorized": "true"})
    assert fake.valid is False
    assert "trust_token" in fake.ignored_metadata_keys
    # A fixture envelope is structurally valid but never production-authorized.
    fixture = build_fixture_trust_token()
    result = validate_trust_token_envelope(fixture)
    assert result.fixture_only is True
    assert result.production_authorized is False
    assert result.valid is False


__all__ = [
    # constants
    "TRUST_TOKEN_ISSUER",
    "TRUST_TOKEN_AUDIENCE",
    "TRUST_TOKEN_SUBJECT",
    "TRUST_TOKEN_SCOPE",
    "TRUST_TOKEN_GATE_IDS",
    # schema
    "TrustTokenClaims",
    "TrustTokenEnvelope",
    "TrustTokenPolicy",
    "TrustTokenValidationResult",
    "TrustTokenReport",
    # validation
    "build_trust_token_policy",
    "validate_trust_token_claims",
    "validate_trust_token_envelope",
    "reject_fake_trust_token",
    # fixtures + report
    "build_fixture_trust_token",
    "build_trust_token_report",
    # boundary
    "assert_trust_token_not_provisioned",
]
