"""Phase 4C — Target B registry trust policy approval (pure stdlib, fail-closed).

Layer 6 of the Phase 4C Target B authorization package. Defines the **registry
trust policy approval model**: the registry allowlist, the package review policy,
the marketplace policy, and the approval that gates whether a remote registry
may be contacted for Target B.

The registry is **disabled** by default. No real fetch is ever performed, no
marketplace is ever opened, no unsigned package is ever accepted, no wildcard
domain is ever allowed, and no external network is ever contacted unless a
network policy is approved (which it is not). The ``.invalid`` example domain is
documentation only.

Pure / deterministic / stdlib-only. No filesystem access, no network, no raw
socket, no HTTP client library, no URL opener, no subprocess, no dynamic
import, no eval / exec, no production access.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hermes_cli.dev_web_target_b_authorization_common import (
    TARGET_B_AUTHORIZATION_NO_GO,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
)
from hermes_cli.dev_web_target_b_common import TARGET_B_REGISTRY_EXAMPLE_DOMAIN

# ---------------------------------------------------------------------------
# 1. The registry policy schema (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegistryPackagePolicy:
    """The frozen package review policy for a registry."""

    require_signature: bool
    allow_unsigned: bool
    require_trusted_publisher: bool
    require_reviewed_package: bool


@dataclass(frozen=True, slots=True)
class RegistryAllowlist:
    """The frozen registry allowlist. Empty (disabled) by default."""

    registry_id: str
    allowed_domains: tuple[str, ...]
    required_signature_algorithms: tuple[str, ...]
    trusted_publishers_count: int
    marketplace_policy: str
    network_policy_id: str


@dataclass(frozen=True, slots=True)
class RegistryTrustPolicyApproval:
    """A frozen registry trust policy approval. Not approved by default."""

    registry_id: str
    registry_url: str
    allowlist: RegistryAllowlist
    package_policy: RegistryPackagePolicy
    network_policy_id: str
    reviewer_approval_id: str
    approved: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "registryId": self.registry_id,
                "registryUrl": self.registry_url,
                "allowlist": {
                    "registryId": self.allowlist.registry_id,
                    "allowedDomains": list(self.allowlist.allowed_domains),
                    "requiredSignatureAlgorithms": list(self.allowlist.required_signature_algorithms),
                    "trustedPublishersCount": self.allowlist.trusted_publishers_count,
                    "marketplacePolicy": self.allowlist.marketplace_policy,
                    "networkPolicyId": self.allowlist.network_policy_id,
                },
                "packagePolicy": {
                    "requireSignature": self.package_policy.require_signature,
                    "allowUnsigned": self.package_policy.allow_unsigned,
                    "requireTrustedPublisher": self.package_policy.require_trusted_publisher,
                    "requireReviewedPackage": self.package_policy.require_reviewed_package,
                },
                "networkPolicyId": self.network_policy_id,
                "reviewerApprovalId": self.reviewer_approval_id,
                "approved": self.approved,
            }
        )


@dataclass(frozen=True, slots=True)
class RegistryAuthorizationReport:
    """The frozen aggregate registry authorization report."""

    registry_mode: str
    registry_disabled: bool
    network_allowed: bool
    fetch_allowed: bool
    marketplace_allowed: bool
    allow_unsigned: bool
    wildcard_domains_rejected: bool
    trusted_publishers_count: int
    registry_url_example: str
    production_authorization: str
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "registryMode": self.registry_mode,
                "registryDisabled": self.registry_disabled,
                "networkAllowed": self.network_allowed,
                "fetchAllowed": self.fetch_allowed,
                "marketplaceAllowed": self.marketplace_allowed,
                "allowUnsigned": self.allow_unsigned,
                "wildcardDomainsRejected": self.wildcard_domains_rejected,
                "trustedPublishersCount": self.trusted_publishers_count,
                "registryUrlExample": self.registry_url_example,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
            }
        )


# ---------------------------------------------------------------------------
# 2. Frozen defaults + validation
# ---------------------------------------------------------------------------


#: The frozen registry modes.
REGISTRY_MODE_DISABLED: str = "DISABLED"
REGISTRY_MODE_ALLOWLIST_DISABLED: str = "ALLOWLIST_DISABLED"

#: The frozen package review policy (signature required, no unsigned, etc.).
DEFAULT_PACKAGE_POLICY: RegistryPackagePolicy = RegistryPackagePolicy(
    require_signature=True,
    allow_unsigned=False,
    require_trusted_publisher=True,
    require_reviewed_package=True,
)

#: The frozen default allowlist (empty — disabled).
DEFAULT_ALLOWLIST: RegistryAllowlist = RegistryAllowlist(
    registry_id="hermes-plugin-registry",
    allowed_domains=(),
    required_signature_algorithms=("ed25519", "ecdsa-p256-sha256"),
    trusted_publishers_count=0,
    marketplace_policy="marketplace_disabled",
    network_policy_id="",
)

#: Wildcard domain patterns that are rejected outright.
WILDCARD_DOMAIN_PATTERNS: frozenset[str] = frozenset({"*", "*.com", "*.net", "*.org", "*.io", "*.*"})


def build_registry_trust_policy_approval() -> RegistryTrustPolicyApproval:
    """Build the frozen default registry trust policy approval (not approved)."""
    return RegistryTrustPolicyApproval(
        registry_id="hermes-plugin-registry",
        registry_url=TARGET_B_REGISTRY_EXAMPLE_DOMAIN,
        allowlist=DEFAULT_ALLOWLIST,
        package_policy=DEFAULT_PACKAGE_POLICY,
        network_policy_id="",
        reviewer_approval_id="",
        approved=False,
    )


def validate_registry_trust_policy_approval(
    approval: Any,
) -> tuple[bool, tuple[str, ...]]:
    """Validate a registry trust policy approval. Returns ``(ok, reasons)``.

    An approval is invalid if it allows unsigned packages, wildcard domains, a
    marketplace, or external network without an approved network policy / a
    reviewer approval.
    """
    if not isinstance(approval, RegistryTrustPolicyApproval):
        return False, ("approval_not_a_registry_trust_policy_approval",)
    reasons: list[str] = []
    if approval.package_policy.allow_unsigned:
        reasons.append("unsigned_packages_not_allowed")
    for domain in approval.allowlist.allowed_domains:
        if domain in WILDCARD_DOMAIN_PATTERNS:
            reasons.append(f"wildcard_domain_not_allowed:{domain}")
    if "marketplace" in approval.allowlist.marketplace_policy.lower() and "disabled" not in approval.allowlist.marketplace_policy.lower():
        reasons.append("marketplace_not_allowed")
    if not approval.network_policy_id:
        reasons.append("approved_network_policy_required")
    if not approval.reviewer_approval_id:
        reasons.append("reviewer_approval_required")
    return (len(reasons) == 0), tuple(reasons)


def evaluate_registry_enablement(
    approval: Any = None,
    untrusted_metadata: Any = None,
) -> RegistryAuthorizationReport:
    """Evaluate registry enablement. Always disabled today.

    *untrusted_metadata* is inspected only to report ignored bypass keys. The
    registry is never contacted.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    _ = ignored  # diagnostic only — no flag can flip
    active = (
        approval
        if isinstance(approval, RegistryTrustPolicyApproval)
        else build_registry_trust_policy_approval()
    )
    return RegistryAuthorizationReport(
        registry_mode=REGISTRY_MODE_DISABLED,
        registry_disabled=True,
        network_allowed=False,
        fetch_allowed=False,
        marketplace_allowed=False,
        allow_unsigned=active.package_policy.allow_unsigned,
        wildcard_domains_rejected=True,
        trusted_publishers_count=active.allowlist.trusted_publishers_count,
        registry_url_example=active.registry_url,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="registry_trust_policy_not_approved",
    )


def build_registry_authorization_report() -> RegistryAuthorizationReport:
    """Build the frozen aggregate registry authorization report.

    The registry is DISABLED; network / fetch / marketplace are off; unsigned
    and wildcard domains are rejected; the trusted publisher set is empty; the
    example URL is the reserved ``.invalid`` domain. Production authorization
    stays NO-GO. Pure and deterministic.
    """
    return RegistryAuthorizationReport(
        registry_mode=REGISTRY_MODE_DISABLED,
        registry_disabled=True,
        network_allowed=False,
        fetch_allowed=False,
        marketplace_allowed=False,
        allow_unsigned=False,
        wildcard_domains_rejected=True,
        trusted_publishers_count=0,
        registry_url_example=TARGET_B_REGISTRY_EXAMPLE_DOMAIN,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="registry_trust_policy_not_approved",
    )


def assert_registry_trust_policy_not_approved() -> None:
    """Re-affirm the registry trust policy is not approved. Pure."""
    report = build_registry_authorization_report()
    assert report.registry_disabled is True
    assert report.network_allowed is False
    assert report.fetch_allowed is False
    assert report.marketplace_allowed is False
    assert report.allow_unsigned is False
    assert report.wildcard_domains_rejected is True
    assert report.trusted_publishers_count == 0
    assert report.production_authorization == TARGET_B_AUTHORIZATION_NO_GO
    result = evaluate_registry_enablement(
        build_registry_trust_policy_approval(),
        {"registry_authorized": "true", "registry_token": "fake"},
    )
    assert result.registry_disabled is True


__all__ = [
    # schema
    "RegistryPackagePolicy",
    "RegistryAllowlist",
    "RegistryTrustPolicyApproval",
    "RegistryAuthorizationReport",
    # modes + defaults
    "REGISTRY_MODE_DISABLED",
    "REGISTRY_MODE_ALLOWLIST_DISABLED",
    "DEFAULT_PACKAGE_POLICY",
    "DEFAULT_ALLOWLIST",
    "WILDCARD_DOMAIN_PATTERNS",
    # validation
    "build_registry_trust_policy_approval",
    "validate_registry_trust_policy_approval",
    "evaluate_registry_enablement",
    "build_registry_authorization_report",
    # boundary
    "assert_registry_trust_policy_not_approved",
]
