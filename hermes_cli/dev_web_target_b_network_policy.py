"""Phase 4C — Target B network allowlist policy (pure stdlib, fail-closed).

Layer 7 of the Phase 4C Target B authorization package. Defines the **network
allowlist policy**: the allowed destinations, the evaluation of a destination
against the allowlist, and the report that gates whether any external network is
permitted for Target B.

The default policy is **deny-all**: no destination is allowed. Wildcard hosts are
denied, cleartext HTTP is denied unless explicitly allowlisted, and the reserved
``registry.example.invalid`` domain is documentation-only. No actual network call
is ever made — no raw socket, no HTTP client library, no URL opener.

Pure / deterministic / stdlib-only. No filesystem access, no network, no raw
socket, no subprocess, no dynamic import, no eval / exec, no production access.

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
# 1. The network policy schema (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NetworkDestination:
    """A frozen network destination candidate. Untrusted."""

    host: str
    port: int
    scheme: str  # e.g. "https", "http", "tcp"
    purpose: str


@dataclass(frozen=True, slots=True)
class NetworkAllowlistPolicy:
    """The frozen network allowlist policy. Deny-all by default."""

    allowlist_id: str
    allowed_destinations: tuple[NetworkDestination, ...]
    allow_wildcard_hosts: bool
    allow_cleartext_http: bool
    allow_private_ranges: bool
    approved: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "allowlistId": self.allowlist_id,
                "allowedDestinations": [
                    {
                        "host": d.host,
                        "port": d.port,
                        "scheme": d.scheme,
                        "purpose": d.purpose,
                    }
                    for d in self.allowed_destinations
                ],
                "allowWildcardHosts": self.allow_wildcard_hosts,
                "allowCleartextHttp": self.allow_cleartext_http,
                "allowPrivateRanges": self.allow_private_ranges,
                "approved": self.approved,
            }
        )


@dataclass(frozen=True, slots=True)
class NetworkPolicyEvaluation:
    """The frozen result of evaluating a destination against the allowlist."""

    allowed: bool
    policy_approved: bool
    wildcard_host_rejected: bool
    cleartext_http_rejected: bool
    private_range_rejected: bool
    destination: str
    production_authorization: str
    reason: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "allowed": self.allowed,
                "policyApproved": self.policy_approved,
                "wildcardHostRejected": self.wildcard_host_rejected,
                "cleartextHttpRejected": self.cleartext_http_rejected,
                "privateRangeRejected": self.private_range_rejected,
                "destination": self.destination,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


@dataclass(frozen=True, slots=True)
class NetworkPolicyReport:
    """The frozen aggregate network-policy authorization report."""

    allowlist_present: bool
    policy_approved: bool
    destinations_allowed: int
    wildcard_hosts_denied: bool
    cleartext_http_denied: bool
    private_ranges_denied: bool
    no_socket_opened: bool
    production_authorization: str
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "allowlistPresent": self.allowlist_present,
                "policyApproved": self.policy_approved,
                "destinationsAllowed": self.destinations_allowed,
                "wildcardHostsDenied": self.wildcard_hosts_denied,
                "cleartextHttpDenied": self.cleartext_http_denied,
                "privateRangesDenied": self.private_ranges_denied,
                "noSocketOpened": self.no_socket_opened,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
            }
        )


# ---------------------------------------------------------------------------
# 2. Frozen defaults + validation
# ---------------------------------------------------------------------------


#: Hosts that are wildcards / overbroad and rejected outright.
WILDCARD_HOST_PATTERNS: frozenset[str] = frozenset({"*", "*.com", "*.net", "*.org", "*.io", "*.*"})

#: Hosts on private / loopback ranges that are denied for egress (doc-only).
PRIVATE_RANGE_HOSTS: frozenset[str] = frozenset(
    {"127.0.0.1", "localhost", "0.0.0.0", "10.0.0.0", "192.168.0.0", "169.254.0.0"}
)


def build_network_allowlist_policy() -> NetworkAllowlistPolicy:
    """Build the frozen default network allowlist policy (deny-all)."""
    return NetworkAllowlistPolicy(
        allowlist_id="hermes-target-b-network-allowlist",
        allowed_destinations=(),
        allow_wildcard_hosts=False,
        allow_cleartext_http=False,
        allow_private_ranges=False,
        approved=False,
    )


def validate_network_allowlist(policy: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate a network allowlist policy. Returns ``(ok, reasons)``.

    A policy is invalid if it allows wildcard hosts, cleartext HTTP (without an
    explicit allowance), private ranges, or any destination, or if it is not
    marked approved. The default policy (empty + deny-all) is the only valid one
    in the dev skeleton.
    """
    if not isinstance(policy, NetworkAllowlistPolicy):
        return False, ("policy_not_a_network_allowlist_policy",)
    reasons: list[str] = []
    if policy.allow_wildcard_hosts:
        reasons.append("wildcard_hosts_not_allowed")
    if policy.allow_cleartext_http:
        reasons.append("cleartext_http_not_allowed")
    if policy.allow_private_ranges:
        reasons.append("private_ranges_not_allowed")
    for dest in policy.allowed_destinations:
        if dest.host in WILDCARD_HOST_PATTERNS:
            reasons.append(f"wildcard_destination:{dest.host}")
        if dest.scheme == "http":
            reasons.append(f"cleartext_destination:{dest.host}")
        if dest.host in PRIVATE_RANGE_HOSTS:
            reasons.append(f"private_destination:{dest.host}")
    if not policy.approved and policy.allowed_destinations:
        reasons.append("allowlist_not_approved")
    return (len(reasons) == 0), tuple(reasons)


def evaluate_network_destination(
    destination: Any,
    *,
    policy: NetworkAllowlistPolicy | None = None,
    untrusted_metadata: Any = None,
) -> NetworkPolicyEvaluation:
    """Evaluate a network destination against the allowlist. Always denied today.

    *untrusted_metadata* is inspected only to report ignored bypass keys. No
    socket is ever opened; no connection is ever attempted.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    active = policy if policy is not None else build_network_allowlist_policy()

    host = ""
    scheme = ""
    if isinstance(destination, NetworkDestination):
        host = destination.host
        scheme = destination.scheme
    elif isinstance(destination, str):
        host = destination
        scheme = "https" if destination.startswith("https://") else (
            "http" if destination.startswith("http://") else ""
        )

    is_wildcard = host in WILDCARD_HOST_PATTERNS or host.startswith("*.")
    is_cleartext = scheme == "http"
    is_private = host in PRIVATE_RANGE_HOSTS
    dest_label = f"{scheme}://{host}" if scheme else host

    # Only an explicitly-approved, non-wildcard, non-cleartext, non-private
    # destination that is present in the allowlist would be allowed — and the
    # default allowlist is empty + not approved.
    allowed = False

    return NetworkPolicyEvaluation(
        allowed=allowed,
        policy_approved=active.approved,
        wildcard_host_rejected=is_wildcard,
        cleartext_http_rejected=is_cleartext,
        private_range_rejected=is_private,
        destination=redact_if_invalid(dest_label),
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="network_destination_denied_by_default",
        ignored_metadata_keys=ignored,
    )


def redact_if_invalid(label: str) -> str:
    """Return *label* but ensure the ``.invalid`` example domain stays doc-only.

    The reserved ``.invalid`` domain is documentation only — it is never
    contacted. This helper leaves it visible as documentation but never treats
    it as an allowed destination.
    """
    if not isinstance(label, str):
        return ""
    if TARGET_B_REGISTRY_EXAMPLE_DOMAIN in label or "example.invalid" in label:
        return label + " (doc-only .invalid — never contacted)"
    return label


def build_network_policy_report() -> NetworkPolicyReport:
    """Build the frozen aggregate network-policy authorization report.

    The allowlist is not approved; zero destinations are allowed; wildcard hosts
    and cleartext HTTP are denied; no socket is ever opened. Production
    authorization stays NO-GO. Pure and deterministic.
    """
    return NetworkPolicyReport(
        allowlist_present=False,
        policy_approved=False,
        destinations_allowed=0,
        wildcard_hosts_denied=True,
        cleartext_http_denied=True,
        private_ranges_denied=True,
        no_socket_opened=True,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="network_allowlist_not_approved",
    )


def assert_network_allowlist_not_approved() -> None:
    """Re-affirm the network allowlist is not approved. Pure."""
    report = build_network_policy_report()
    assert report.allowlist_present is False
    assert report.policy_approved is False
    assert report.destinations_allowed == 0
    assert report.wildcard_hosts_denied is True
    assert report.cleartext_http_denied is True
    assert report.no_socket_opened is True
    assert report.production_authorization == TARGET_B_AUTHORIZATION_NO_GO
    result = evaluate_network_destination(
        NetworkDestination(host="registry.example.invalid", port=443, scheme="https", purpose="fetch"),
        untrusted_metadata={"external network": "true"},
    )
    assert result.allowed is False
    assert result.policy_approved is False


__all__ = [
    # schema
    "NetworkDestination",
    "NetworkAllowlistPolicy",
    "NetworkPolicyEvaluation",
    "NetworkPolicyReport",
    # constants
    "WILDCARD_HOST_PATTERNS",
    "PRIVATE_RANGE_HOSTS",
    # validation
    "build_network_allowlist_policy",
    "validate_network_allowlist",
    "evaluate_network_destination",
    "redact_if_invalid",
    "build_network_policy_report",
    # boundary
    "assert_network_allowlist_not_approved",
]
