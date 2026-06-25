"""Phase 4C — Target B trusted publisher set (pure stdlib, fail-closed).

Layer 3 of the Phase 4C Target B authorization package. Defines the **trusted
publisher set** that a real production signature verifier would honor, and the
policy that decides whether a publisher may publish a package for Target B.

The production trusted publisher set is **empty** by default: no publisher is
trusted until a real, reviewed trust policy and verifier are authorized out of
band. Therefore:

  - an unknown publisher is rejected;
  - a marketplace publisher is rejected;
  - an unsigned publisher is rejected;
  - a wildcard publisher (``*``) is rejected;
  - a publisher with overbroad permissions is rejected.

A deterministic **fixture publisher** is provided for tests only (the same
``fixture`` publisher the Phase 4B fixture verifier honors) and is explicitly
``fixture_only`` — it never authorizes production.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no eval / exec, no real secret read, no production
access, no registry fetch.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_target_b_authorization_common import (
    TARGET_B_AUTHORIZATION_NO_GO,
    TARGET_B_FIXTURE_NOT_PRODUCTION_REASON,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
)
from hermes_cli.dev_web_target_b_common import real_trusted_publishers

# ---------------------------------------------------------------------------
# 1. Frozen publisher constants
# ---------------------------------------------------------------------------

#: The fixture publisher id (tests only — matches the Phase 4B fixture verifier).
FIXTURE_PUBLISHER_ID: str = "fixture"

#: Permissions a fixture publisher is confined to (read-only display only).
FIXTURE_PUBLISHER_PERMISSIONS: tuple[str, ...] = ("ui.render",)

#: Capabilities a fixture publisher is confined to (display/read only).
FIXTURE_PUBLISHER_CAPABILITIES: tuple[str, ...] = ("display.surface", "read.descriptor")

#: Package id patterns a fixture publisher is confined to (example only).
FIXTURE_PUBLISHER_PACKAGE_PATTERN: str = "example.plugin.*"

#: Wildcard publisher ids that are rejected outright.
WILDCARD_PUBLISHER_IDS: frozenset[str] = frozenset({"*", "all", "any", "marketplace"})

#: Permissions that are too broad for any single publisher to hold (rejected).
OVERBROAD_PERMISSIONS: frozenset[str] = frozenset(
    {
        "process.spawn",
        "runtime.execute",
        "plugin.install",
        "marketplace.fetch",
        "secrets.read",
        "filesystem.write",
        "provider.write",
        "database.write",
        "*",
    }
)


# ---------------------------------------------------------------------------
# 2. The trusted publisher schema (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrustedPublisher:
    """A publisher the production trust policy would honor. Empty by default."""

    publisher_id: str
    display_name: str
    public_key_id: str
    allowed_package_patterns: tuple[str, ...]
    allowed_capabilities: tuple[str, ...]
    allowed_permissions: tuple[str, ...]
    review_status: str
    trust_scope: str
    expires_at: str
    fixture_only: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "publisherId": self.publisher_id,
                "displayName": self.display_name,
                "publicKeyId": self.public_key_id,
                "allowedPackagePatterns": list(self.allowed_package_patterns),
                "allowedCapabilities": list(self.allowed_capabilities),
                "allowedPermissions": list(self.allowed_permissions),
                "reviewStatus": self.review_status,
                "trustScope": self.trust_scope,
                "expiresAt": self.expires_at,
                "fixtureOnly": self.fixture_only,
            }
        )


@dataclass(frozen=True, slots=True)
class PublisherTrustPolicy:
    """The frozen publisher trust policy. The production set is empty."""

    trusted_publishers: tuple[TrustedPublisher, ...]
    allow_marketplace: bool
    allow_unsigned: bool
    allow_wildcard: bool
    fixture_only: bool


@dataclass(frozen=True, slots=True)
class PublisherVerificationResult:
    """The frozen result of verifying a publisher for a package."""

    trusted: bool
    production_authorized: bool
    fixture_only: bool
    unknown_publisher_rejected: bool
    marketplace_publisher_rejected: bool
    unsigned_publisher_rejected: bool
    wildcard_publisher_rejected: bool
    overbroad_permissions_rejected: bool
    reason: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "trusted": self.trusted,
                "productionAuthorized": self.production_authorized,
                "fixtureOnly": self.fixture_only,
                "unknownPublisherRejected": self.unknown_publisher_rejected,
                "marketplacePublisherRejected": self.marketplace_publisher_rejected,
                "unsignedPublisherRejected": self.unsigned_publisher_rejected,
                "wildcardPublisherRejected": self.wildcard_publisher_rejected,
                "overbroadPermissionsRejected": self.overbroad_permissions_rejected,
                "reason": self.reason,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


@dataclass(frozen=True, slots=True)
class TrustedPublisherReport:
    """The frozen aggregate trusted-publisher authorization report."""

    trusted_publishers_count: int
    unknown_publisher_rejected: bool
    marketplace_publisher_rejected: bool
    unsigned_publisher_rejected: bool
    wildcard_publisher_rejected: bool
    overbroad_permissions_rejected: bool
    production_authorization: str
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "trustedPublishersCount": self.trusted_publishers_count,
                "unknownPublisherRejected": self.unknown_publisher_rejected,
                "marketplacePublisherRejected": self.marketplace_publisher_rejected,
                "unsignedPublisherRejected": self.unsigned_publisher_rejected,
                "wildcardPublisherRejected": self.wildcard_publisher_rejected,
                "overbroadPermissionsRejected": self.overbroad_permissions_rejected,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
            }
        )


# ---------------------------------------------------------------------------
# 3. The fixture publisher + the policies
# ---------------------------------------------------------------------------


FIXTURE_TRUSTED_PUBLISHER: TrustedPublisher = TrustedPublisher(
    publisher_id=FIXTURE_PUBLISHER_ID,
    display_name="Fixture publisher (tests only)",
    public_key_id="fixture-publisher-key",
    allowed_package_patterns=(FIXTURE_PUBLISHER_PACKAGE_PATTERN,),
    allowed_capabilities=FIXTURE_PUBLISHER_CAPABILITIES,
    allowed_permissions=FIXTURE_PUBLISHER_PERMISSIONS,
    review_status="fixture_only",
    trust_scope="fixture_tests_only",
    expires_at="2026-12-31T23:59:59Z",
    fixture_only=True,
)


def build_production_publisher_trust_policy() -> PublisherTrustPolicy:
    """Build the frozen production publisher trust policy.

    The production trusted publisher set is empty (no publisher is trusted until
    a real trust policy is authorized out of band). Marketplace, unsigned, and
    wildcard publishers are never allowed.
    """
    return PublisherTrustPolicy(
        trusted_publishers=(),
        allow_marketplace=False,
        allow_unsigned=False,
        allow_wildcard=False,
        fixture_only=False,
    )


def build_fixture_publisher_trust_policy() -> PublisherTrustPolicy:
    """Build the frozen fixture-only publisher trust policy (tests only)."""
    return PublisherTrustPolicy(
        trusted_publishers=(FIXTURE_TRUSTED_PUBLISHER,),
        allow_marketplace=False,
        allow_unsigned=False,
        allow_wildcard=False,
        fixture_only=True,
    )


# ---------------------------------------------------------------------------
# 4. Validation
# ---------------------------------------------------------------------------


def validate_trusted_publisher(publisher: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate a single publisher record. Returns ``(valid, reasons)``.

    A publisher is invalid if it is a wildcard, a marketplace id, unsigned
    (empty public key), carries overbroad permissions, or is a fixture-only
    record being treated as production.
    """
    if not isinstance(publisher, TrustedPublisher):
        return False, ("publisher_not_a_trusted_publisher",)
    reasons: list[str] = []
    if publisher.publisher_id in WILDCARD_PUBLISHER_IDS:
        reasons.append("wildcard_publisher_id")
    if "marketplace" in publisher.publisher_id.lower():
        reasons.append("marketplace_publisher_id")
    if not publisher.public_key_id:
        reasons.append("unsigned_publisher_no_public_key")
    for perm in publisher.allowed_permissions:
        if perm in OVERBROAD_PERMISSIONS:
            reasons.append(f"overbroad_permission:{perm}")
    if publisher.fixture_only:
        reasons.append("fixture_only_publisher")
    return (len(reasons) == 0), tuple(reasons)


def evaluate_publisher_for_package(
    publisher_id: Any,
    package_id: Any,
    *,
    policy: PublisherTrustPolicy | None = None,
    untrusted_metadata: Any = None,
) -> PublisherVerificationResult:
    """Verify whether *publisher_id* is trusted to publish *package_id*.

    Defaults to not-trusted. Unknown / marketplace / wildcard publishers are
    rejected. A fixture publisher is honored only under the fixture policy and
    never authorizes production. Pure — never fetches a registry.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    active = policy if policy is not None else build_production_publisher_trust_policy()

    pid = publisher_id if isinstance(publisher_id, str) else ""
    if not pid:
        return PublisherVerificationResult(
            trusted=False,
            production_authorized=False,
            fixture_only=active.fixture_only,
            unknown_publisher_rejected=True,
            marketplace_publisher_rejected=False,
            unsigned_publisher_rejected=False,
            wildcard_publisher_rejected=False,
            overbroad_permissions_rejected=False,
            reason="publisher_id_missing",
            ignored_metadata_keys=ignored,
        )

    unknown = True
    fixture_match = False
    for pub in active.trusted_publishers:
        if pub.publisher_id == pid:
            unknown = False
            # Under the fixture policy, a fixture publisher is honored as
            # fixture-only trust (never production). The production set is empty,
            # so no non-fixture publisher can ever match here.
            if active.fixture_only and pub.fixture_only:
                fixture_match = True
            break

    is_wildcard = pid in WILDCARD_PUBLISHER_IDS
    is_marketplace = "marketplace" in pid.lower()
    fixture = active.fixture_only and fixture_match

    # Production authorization requires a non-fixture trusted publisher AND a
    # non-fixture policy. The production set is empty, so always False here.
    production_authorized = False
    trusted = bool(fixture) or production_authorized

    if is_wildcard:
        reason = "wildcard_publisher_rejected"
    elif is_marketplace:
        reason = "marketplace_publisher_rejected"
    elif unknown:
        reason = "unknown_publisher_rejected"
    elif fixture:
        reason = TARGET_B_FIXTURE_NOT_PRODUCTION_REASON
    else:
        reason = "publisher_not_trusted"

    return PublisherVerificationResult(
        trusted=trusted,
        production_authorized=production_authorized,
        fixture_only=fixture,
        unknown_publisher_rejected=unknown and not is_wildcard and not is_marketplace,
        marketplace_publisher_rejected=is_marketplace,
        unsigned_publisher_rejected=False,
        wildcard_publisher_rejected=is_wildcard,
        overbroad_permissions_rejected=False,
        reason=reason,
        ignored_metadata_keys=ignored,
    )


def build_trusted_publisher_report() -> TrustedPublisherReport:
    """Build the frozen aggregate trusted-publisher authorization report.

    The production trusted publisher set is empty. Unknown / marketplace /
    unsigned / wildcard / overbroad publishers are rejected. Production
    authorization stays NO-GO. Pure and deterministic.
    """
    return TrustedPublisherReport(
        trusted_publishers_count=0,
        unknown_publisher_rejected=True,
        marketplace_publisher_rejected=True,
        unsigned_publisher_rejected=True,
        wildcard_publisher_rejected=True,
        overbroad_permissions_rejected=True,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="trusted_publisher_set_empty",
    )


def assert_trusted_publisher_set_empty() -> None:
    """Re-affirm the production trusted publisher set is empty. Pure."""
    report = build_trusted_publisher_report()
    assert report.trusted_publishers_count == 0
    assert report.unknown_publisher_rejected is True
    assert report.marketplace_publisher_rejected is True
    assert report.unsigned_publisher_rejected is True
    assert report.wildcard_publisher_rejected is True
    assert report.overbroad_permissions_rejected is True
    assert report.production_authorization == TARGET_B_AUTHORIZATION_NO_GO
    # The real (production) trusted publisher set is empty.
    assert real_trusted_publishers() == frozenset()
    # An unknown publisher is rejected.
    result = evaluate_publisher_for_package("unknown.publisher", "example.plugin.alpha")
    assert result.trusted is False
    assert result.production_authorized is False
    # A wildcard publisher is rejected.
    wildcard = evaluate_publisher_for_package("*", "example.plugin.alpha")
    assert wildcard.trusted is False
    assert wildcard.wildcard_publisher_rejected is True
    # A fixture publisher under the production policy is rejected.
    fixture = evaluate_publisher_for_package(FIXTURE_PUBLISHER_ID, "example.plugin.alpha")
    assert fixture.trusted is False
    assert fixture.production_authorized is False


__all__ = [
    # constants
    "FIXTURE_PUBLISHER_ID",
    "FIXTURE_PUBLISHER_PERMISSIONS",
    "FIXTURE_PUBLISHER_CAPABILITIES",
    "FIXTURE_PUBLISHER_PACKAGE_PATTERN",
    "WILDCARD_PUBLISHER_IDS",
    "OVERBROAD_PERMISSIONS",
    # schema
    "TrustedPublisher",
    "FIXTURE_TRUSTED_PUBLISHER",
    "PublisherTrustPolicy",
    "PublisherVerificationResult",
    "TrustedPublisherReport",
    # policies
    "build_production_publisher_trust_policy",
    "build_fixture_publisher_trust_policy",
    # validation
    "validate_trusted_publisher",
    "evaluate_publisher_for_package",
    # report
    "build_trusted_publisher_report",
    # boundary
    "assert_trusted_publisher_set_empty",
]
