"""Phase 3B-Live-Enablement — Live Provider Network Allowlist (Frozen).

The only egress a live provider may ever make is a **single** outbound HTTPS
POST to an **explicitly allowlisted** host. The default allowlist is
**empty**; an operator-approved host is checked against a frozen static
allowlist (``api.openai.com`` for the first live slice). Any deviation fails
closed with a precise blocked reason and no network call.

This module is a pure decision surface: it never performs a network call, never
follows a redirect, never reads an API key, and never carries a secret. The
concrete HTTP client (an injected mock in tests) is wired only by the live
round-trip orchestrator, and only after every network check passes.

Phase: 3B-Live-Enablement — Strict Manual One-shot Real Provider Enablement
Status: live network allowlist implemented (no network call by default)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

# ---------------------------------------------------------------------------
# 1. Frozen static allowlist (the hosts the first live slice MAY approve)
# ---------------------------------------------------------------------------

# The default allowlist is EMPTY (no host is approved unless an operator
# approves one). The static allowlist bounds which host an approval may name.
LIVE_ALLOWED_HOSTS: frozenset[str] = frozenset({"api.openai.com"})

# ---------------------------------------------------------------------------
# 2. Frozen blocked-reason catalogue (network layer)
# ---------------------------------------------------------------------------

BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED = "blocked_live_provider_host_not_approved"
BLOCKED_LIVE_PROVIDER_SCHEME_NOT_HTTPS = "blocked_live_provider_scheme_not_https"
BLOCKED_LIVE_PROVIDER_REDIRECT_NOT_ALLOWED = "blocked_live_provider_redirect_not_allowed"
BLOCKED_LIVE_PROVIDER_PRIVATE_NETWORK_NOT_ALLOWED = "blocked_live_provider_private_network_not_allowed"
BLOCKED_LIVE_PROVIDER_RESPONSE_FETCH_NOT_ALLOWED = "blocked_live_provider_response_fetch_not_allowed"
BLOCKED_LIVE_PROVIDER_NETWORK_TIMEOUT = "blocked_live_provider_network_timeout"
BLOCKED_LIVE_PROVIDER_RESPONSE_TOO_LARGE = "blocked_live_provider_response_too_large"

# ---------------------------------------------------------------------------
# 3. Host classification helpers
# ---------------------------------------------------------------------------

# Conservative private / loopback detection. These hosts are NEVER approved
# for the first live slice; a redirect or request to them fails closed.
_PRIVATE_HOST_PREFIXES: tuple[str, ...] = (
    "127.", "10.", "192.168.", "169.254.", "0.",
)
_PRIVATE_HOST_OCTET_172 = "172."


def _is_private_or_loopback_host(host: str) -> bool:
    """True for localhost / loopback / private / link-local / wildcard hosts."""
    if not host:
        return True
    lowered = host.lower()
    if lowered in ("localhost", "ip6-localhost", "::1", "[::1]"):
        return True
    if lowered.endswith(".localhost"):
        return True
    # Strip a bracketed IPv6 host.
    if lowered.startswith("[") and lowered.endswith("]"):
        inner = lowered[1:-1]
        if inner in ("::1",):
            return True
    # IPv4-style host (prefix match — never exact tuple membership).
    if any(lowered.startswith(prefix) for prefix in _PRIVATE_HOST_PREFIXES):
        return True
    if lowered.startswith(_PRIVATE_HOST_OCTET_172):
        parts = lowered.split(".")
        if len(parts) == 4:
            try:
                second = int(parts[1])
            except ValueError:
                second = -1
            if 16 <= second <= 31:
                return True
    if lowered.startswith("192.168."):
        return True  # covered by prefix but kept for clarity
    return False


def _host_from_url(url: str) -> tuple[str, str, str | None]:
    """Return (scheme, host_no_port, error_reason) for a URL.

    Never returns the userinfo / port / query — only the bare host. An
    off-allowlist or non-https URL yields a precise reason.
    """
    if not isinstance(url, str) or not url.strip():
        return "", "", BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return "", "", BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED
    scheme = (parts.scheme or "").lower()
    host = (parts.hostname or "").lower()
    if scheme != "https":
        return scheme, host, BLOCKED_LIVE_PROVIDER_SCHEME_NOT_HTTPS
    if not host:
        return scheme, host, BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED
    if _is_private_or_loopback_host(host):
        return scheme, host, BLOCKED_LIVE_PROVIDER_PRIVATE_NETWORK_NOT_ALLOWED
    return scheme, host, None


# ---------------------------------------------------------------------------
# 4. Network decision
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LiveNetworkDecision:
    allowed: bool
    host: str
    blocked_reason: str | None

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "baseUrlHost": self.host if self.allowed else "",
            "blockedReason": self.blocked_reason,
            "redactionApplied": True,
        }


def evaluate_live_network(
    *,
    base_url: str,
    approval_host: str,
) -> LiveNetworkDecision:
    """Evaluate the live network allowlist for a base URL + approved host.

    The host must be https, must equal the approval's host, must be private-free,
    and must be in the frozen static allowlist. Anything else fails closed.
    """
    scheme, host, reason = _host_from_url(base_url)
    if reason is not None:
        return LiveNetworkDecision(allowed=False, host=host, blocked_reason=reason)
    approval_host_clean = (approval_host or "").lower().strip()
    if host != approval_host_clean:
        return LiveNetworkDecision(
            allowed=False, host=host, blocked_reason=BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED,
        )
    if host not in LIVE_ALLOWED_HOSTS:
        return LiveNetworkDecision(
            allowed=False, host=host, blocked_reason=BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED,
        )
    return LiveNetworkDecision(allowed=True, host=host, blocked_reason=None)


def validate_live_redirect(
    *,
    current_host: str,
    location: str,
) -> LiveNetworkDecision:
    """Validate an HTTP redirect. Off-allowlist / private redirect → blocked.

    The first live slice forbids redirects entirely: any non-empty redirect
    to a host other than the approved allowlisted host fails closed.
    """
    if not isinstance(location, str) or not location.strip():
        return LiveNetworkDecision(
            allowed=False, host="", blocked_reason=BLOCKED_LIVE_PROVIDER_REDIRECT_NOT_ALLOWED,
        )
    scheme, host, reason = _host_from_url(location)
    if reason is not None:
        return LiveNetworkDecision(allowed=False, host=host, blocked_reason=reason)
    current_clean = (current_host or "").lower().strip()
    if host != current_clean or host not in LIVE_ALLOWED_HOSTS:
        return LiveNetworkDecision(
            allowed=False, host=host, blocked_reason=BLOCKED_LIVE_PROVIDER_REDIRECT_NOT_ALLOWED,
        )
    return LiveNetworkDecision(allowed=True, host=host, blocked_reason=None)


def is_tool_external_http(tool_id: Any) -> bool:
    """A provider-requested tool that performs external HTTP is forbidden live."""
    if not isinstance(tool_id, str):
        return False
    return tool_id in (
        "external_http", "web_search", "web_extract", "browser_navigate",
        "browser_action", "send_message",
    )


__all__ = [
    "LIVE_ALLOWED_HOSTS",
    "BLOCKED_LIVE_PROVIDER_HOST_NOT_APPROVED",
    "BLOCKED_LIVE_PROVIDER_SCHEME_NOT_HTTPS",
    "BLOCKED_LIVE_PROVIDER_REDIRECT_NOT_ALLOWED",
    "BLOCKED_LIVE_PROVIDER_PRIVATE_NETWORK_NOT_ALLOWED",
    "BLOCKED_LIVE_PROVIDER_RESPONSE_FETCH_NOT_ALLOWED",
    "BLOCKED_LIVE_PROVIDER_NETWORK_TIMEOUT",
    "BLOCKED_LIVE_PROVIDER_RESPONSE_TOO_LARGE",
    "LiveNetworkDecision",
    "evaluate_live_network",
    "validate_live_redirect",
    "is_tool_external_http",
]
