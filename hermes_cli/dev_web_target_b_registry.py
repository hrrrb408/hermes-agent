"""Phase 4B — Target B registry trust policy layer (pure stdlib, fail-closed).

Layer 5 of the Phase 4B Target B engineering path. Defines the **registry
trust policy** and the **registry client** interface.

The registry is **disabled by default**: ``allow_network=False``,
``marketplace_enabled=False``, ``allow_unsigned=False``,
``registry_mode="DISABLED"``. No network fetch is ever performed — the module
imports no network library and performs no network I/O of any kind. Every fetch
request returns a denied result no matter what untrusted metadata is supplied.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no real secret read, no production access.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_target_b_common import (
    TARGET_B_MARKETPLACE_DISABLED_REASON,
    TARGET_B_NO_GO,
    TARGET_B_REGISTRY_DISABLED_REASON,
    TARGET_B_REGISTRY_EXAMPLE_DOMAIN,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
)

# ---------------------------------------------------------------------------
# 1. Frozen registry trust policy + modes
# ---------------------------------------------------------------------------

#: Registry modes. The production client is DISABLED; an ALLOWLIST mode is the
#: only future-enabled mode and still requires human authorization.
REGISTRY_MODE_DISABLED: str = "DISABLED"
REGISTRY_MODE_ALLOWLIST: str = "ALLOWLIST_DISABLED"

#: The frozen default registry mode.
DEFAULT_REGISTRY_MODE: str = REGISTRY_MODE_DISABLED


@dataclass(frozen=True, slots=True)
class RegistryTrustPolicy:
    """The frozen registry trust policy.

    Network is disabled; the marketplace is disabled; unsigned is never
    allowed; a signature is required; the trusted-publisher set is empty. The
    example registry URL uses a reserved ``.invalid`` domain that is never
    contacted.
    """

    registry_id: str
    registry_url_example: str
    registry_mode: str
    allow_network: bool
    allow_unsigned: bool
    required_signature: bool
    trusted_publishers: tuple[str, ...]
    trust_policy_version: str
    marketplace_enabled: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "registryId": self.registry_id,
                "registryUrlExample": self.registry_url_example,
                "registryMode": self.registry_mode,
                "allowNetwork": self.allow_network,
                "allowUnsigned": self.allow_unsigned,
                "requiredSignature": self.required_signature,
                "trustedPublishers": list(self.trusted_publishers),
                "trustPolicyVersion": self.trust_policy_version,
                "marketplaceEnabled": self.marketplace_enabled,
            }
        )


#: The frozen registry trust policy. Disabled / never fetched.
REGISTRY_TRUST_POLICY: RegistryTrustPolicy = RegistryTrustPolicy(
    registry_id="registry-trust-policy-v1-design-only",
    registry_url_example=TARGET_B_REGISTRY_EXAMPLE_DOMAIN,
    registry_mode=DEFAULT_REGISTRY_MODE,
    allow_network=False,
    allow_unsigned=False,
    required_signature=True,
    trusted_publishers=(),
    trust_policy_version="registry-trust-policy-v1-design-only",
    marketplace_enabled=False,
)


def build_registry_trust_policy() -> RegistryTrustPolicy:
    """Return a defensive copy of the frozen registry trust policy."""
    p = REGISTRY_TRUST_POLICY
    return RegistryTrustPolicy(
        registry_id=p.registry_id,
        registry_url_example=p.registry_url_example,
        registry_mode=p.registry_mode,
        allow_network=p.allow_network,
        allow_unsigned=p.allow_unsigned,
        required_signature=p.required_signature,
        trusted_publishers=p.trusted_publishers,
        trust_policy_version=p.trust_policy_version,
        marketplace_enabled=p.marketplace_enabled,
    )


# ---------------------------------------------------------------------------
# 2. Registry fetch / package-metadata evaluation (deny by default)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegistryFetchDecision:
    """The frozen result of a registry fetch request. Always denied."""

    fetched: bool
    network: bool
    allowed: bool
    reason: str
    production_authorization: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "fetched": self.fetched,
                "network": self.network,
                "allowed": self.allowed,
                "reason": self.reason,
                "productionAuthorization": self.production_authorization,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


@dataclass(frozen=True, slots=True)
class RegistryPackageMetadataDecision:
    """The frozen result of evaluating remote registry package metadata."""

    trusted: bool
    fetchable: bool
    installable: bool
    reason: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "trusted": self.trusted,
                "fetchable": self.fetchable,
                "installable": self.installable,
                "reason": self.reason,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


def validate_registry_policy(policy: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate that *policy* is safe (disabled / not authorized).

    Returns ``(safe, reasons)``. A policy is *safe* when network is disabled,
    the marketplace is disabled, unsigned is disallowed, and the trusted set is
    empty. The frozen policy is always safe.
    """
    if not isinstance(policy, RegistryTrustPolicy):
        return False, ("policy_not_a_registry_trust_policy",)
    reasons: list[str] = []
    if policy.allow_network:
        reasons.append("network_allowed_unsafe")
    if policy.marketplace_enabled:
        reasons.append("marketplace_enabled_unsafe")
    if policy.allow_unsigned:
        reasons.append("unsigned_allowed_unsafe")
    if policy.trusted_publishers:
        reasons.append("trusted_publishers_present_unsafe")
    safe = not reasons
    return safe, tuple(reasons)


def deny_registry_fetch(untrusted_metadata: Any = None) -> RegistryFetchDecision:
    """Deny a registry fetch request. Always network=False, fetched=False.

    The registry is never contacted; no external network is opened; no listing
    is fetched. *untrusted_metadata* is inspected only to report ignored keys.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    return RegistryFetchDecision(
        fetched=False,
        network=False,
        allowed=False,
        reason=TARGET_B_REGISTRY_DISABLED_REASON,
        production_authorization=TARGET_B_NO_GO,
        ignored_metadata_keys=ignored,
    )


def deny_marketplace_fetch(untrusted_metadata: Any = None) -> RegistryFetchDecision:
    """Deny a marketplace fetch request. Always marketplace=False.

    The marketplace is never reachable; no listing is fetched; no install is
    performed. *untrusted_metadata* is inspected only to report ignored keys.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    return RegistryFetchDecision(
        fetched=False,
        network=False,
        allowed=False,
        reason=TARGET_B_MARKETPLACE_DISABLED_REASON,
        production_authorization=TARGET_B_NO_GO,
        ignored_metadata_keys=ignored,
    )


def evaluate_registry_package_metadata(
    package_metadata: Any,
    untrusted_metadata: Any = None,
) -> RegistryPackageMetadataDecision:
    """Evaluate remote registry package metadata. Never trusted / fetchable.

    A remote package (or one sourced from a marketplace) is never trusted, never
    fetchable, and never installable in the dev skeleton. Local-untrusted
    metadata is inspected only to report ignored keys.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    if isinstance(package_metadata, Mapping):
        # Detect a marketplace / remote-shaped source inside the metadata.
        source = package_metadata.get("registry_source") or package_metadata.get("source") or ""
        if isinstance(source, str) and ("marketplace" in source.lower() or "marketplace" in str(package_metadata).lower()):
            return RegistryPackageMetadataDecision(
                trusted=False,
                fetchable=False,
                installable=False,
                reason="marketplace_source_rejected",
                ignored_metadata_keys=ignored,
            )
    return RegistryPackageMetadataDecision(
        trusted=False,
        fetchable=False,
        installable=False,
        reason="registry_trust_policy_not_authorized",
        ignored_metadata_keys=ignored,
    )


# ---------------------------------------------------------------------------
# 3. The registry client (disabled / allowlisted interface — never fetches)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegistryClientStatus:
    """The frozen registry client status. Disabled by default."""

    client_enabled: bool
    mode: str
    allow_network: bool
    marketplace_enabled: bool
    allow_unsigned: bool
    trusted_publishers_count: int

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "clientEnabled": self.client_enabled,
                "mode": self.mode,
                "allowNetwork": self.allow_network,
                "marketplaceEnabled": self.marketplace_enabled,
                "allowUnsigned": self.allow_unsigned,
                "trustedPublishersCount": self.trusted_publishers_count,
            }
        )


def build_registry_client_status() -> RegistryClientStatus:
    """Build the frozen registry client status. Disabled / allowlisted-off."""
    p = REGISTRY_TRUST_POLICY
    return RegistryClientStatus(
        client_enabled=False,
        mode=p.registry_mode,
        allow_network=p.allow_network,
        marketplace_enabled=p.marketplace_enabled,
        allow_unsigned=p.allow_unsigned,
        trusted_publishers_count=len(p.trusted_publishers),
    )


# ---------------------------------------------------------------------------
# 4. The aggregate registry readiness report
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegistryReadinessReport:
    """The frozen aggregate registry readiness report."""

    registry_mode: str
    network_enabled: bool
    fetch_enabled: bool
    marketplace_enabled: bool
    allow_unsigned: bool
    trusted_publishers_count: int
    production_authorization: str
    policy: RegistryTrustPolicy

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "registryMode": self.registry_mode,
                "networkEnabled": self.network_enabled,
                "fetchEnabled": self.fetch_enabled,
                "marketplaceEnabled": self.marketplace_enabled,
                "allowUnsigned": self.allow_unsigned,
                "trustedPublishersCount": self.trusted_publishers_count,
                "productionAuthorization": self.production_authorization,
                "policy": self.policy.to_safe_dict(),
            }
        )


def build_registry_readiness_report() -> RegistryReadinessReport:
    """Build the frozen aggregate registry readiness report.

    The registry is DISABLED; network is off; fetch is off; the marketplace is
    off; unsigned is disallowed; no trusted publisher exists; production
    authorization is NO-GO. Pure and deterministic.
    """
    p = build_registry_trust_policy()
    return RegistryReadinessReport(
        registry_mode=p.registry_mode,
        network_enabled=False,
        fetch_enabled=False,
        marketplace_enabled=False,
        allow_unsigned=p.allow_unsigned,
        trusted_publishers_count=len(p.trusted_publishers),
        production_authorization=TARGET_B_NO_GO,
        policy=p,
    )


def assert_registry_layer_disabled() -> None:
    """Re-affirm the registry layer disabled invariants. Pure."""
    safe, _reasons = validate_registry_policy(REGISTRY_TRUST_POLICY)
    assert safe is True
    assert REGISTRY_TRUST_POLICY.allow_network is False
    assert REGISTRY_TRUST_POLICY.marketplace_enabled is False
    assert REGISTRY_TRUST_POLICY.allow_unsigned is False
    client = build_registry_client_status()
    assert client.client_enabled is False
    assert client.allow_network is False
    report = build_registry_readiness_report()
    assert report.network_enabled is False
    assert report.fetch_enabled is False
    assert report.marketplace_enabled is False
    assert report.production_authorization == TARGET_B_NO_GO


__all__ = [
    # modes
    "REGISTRY_MODE_DISABLED",
    "REGISTRY_MODE_ALLOWLIST",
    "DEFAULT_REGISTRY_MODE",
    # policy
    "RegistryTrustPolicy",
    "REGISTRY_TRUST_POLICY",
    "build_registry_trust_policy",
    "validate_registry_policy",
    # decisions
    "RegistryFetchDecision",
    "RegistryPackageMetadataDecision",
    "deny_registry_fetch",
    "deny_marketplace_fetch",
    "evaluate_registry_package_metadata",
    # client
    "RegistryClientStatus",
    "build_registry_client_status",
    # report
    "RegistryReadinessReport",
    "build_registry_readiness_report",
    # boundary
    "assert_registry_layer_disabled",
]
