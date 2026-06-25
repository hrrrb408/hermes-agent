"""Phase 4C — Target B secret handling policy (pure stdlib, fail-closed).

Layer 8 of the Phase 4C Target B authorization package. Defines the **secret
handling policy**: the secret scopes, the access decision that gates whether a
secret may be read, the redactor for secret-bearing payloads, and the report
that gates whether any secret is ever read for Target B.

The default policy is **deny-all**: no secret is ever read. No real API key is
read, no environment secret is read, no ``production home`` secret is read, no provider
key is read, and the ``secrets.read`` permission is denied unless a future
explicit policy authorizes it. Secret values are always redacted.

Pure / deterministic / stdlib-only. No filesystem access, no environment
read, no network, no subprocess, no dynamic import, no eval / exec, no real
secret read, no ``production home`` access, no production access.

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
    redact_target_b_string,
)

# ---------------------------------------------------------------------------
# 1. The secret policy schema (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SecretScope:
    """A frozen secret scope definition. Read denied by default."""

    scope_id: str
    label: str
    read_allowed: bool
    requires_explicit_policy: bool


@dataclass(frozen=True, slots=True)
class SecretHandlingPolicy:
    """The frozen secret handling policy. Default deny."""

    default_disposition: str
    read_api_keys_allowed: bool
    read_env_secrets_allowed: bool
    read_production_home_secrets_allowed: bool
    read_provider_keys_allowed: bool
    redact_secret_values: bool
    approved: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "defaultDisposition": self.default_disposition,
                "readApiKeysAllowed": self.read_api_keys_allowed,
                "readEnvSecretsAllowed": self.read_env_secrets_allowed,
                "readProductionHomeSecretsAllowed": self.read_production_home_secrets_allowed,
                "readProviderKeysAllowed": self.read_provider_keys_allowed,
                "redactSecretValues": self.redact_secret_values,
                "approved": self.approved,
            }
        )


@dataclass(frozen=True, slots=True)
class SecretAccessDecision:
    """The frozen result of a secret access request. Defaults denied."""

    allowed: bool
    scope: str
    production_home_accessed: bool
    env_secret_read: bool
    api_key_read: bool
    provider_key_read: bool
    value_redacted: bool
    production_authorization: str
    reason: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "allowed": self.allowed,
                "scope": self.scope,
                "productionHomeAccessed": self.production_home_accessed,
                "envSecretRead": self.env_secret_read,
                "apiKeyRead": self.api_key_read,
                "providerKeyRead": self.provider_key_read,
                "valueRedacted": self.value_redacted,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


@dataclass(frozen=True, slots=True)
class SecretPolicyReport:
    """The frozen aggregate secret-policy authorization report."""

    default_disposition: str
    read_api_keys_allowed: bool
    read_env_secrets_allowed: bool
    read_production_home_secrets_allowed: bool
    read_provider_keys_allowed: bool
    redact_secret_values: bool
    production_authorization: str
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "defaultDisposition": self.default_disposition,
                "readApiKeysAllowed": self.read_api_keys_allowed,
                "readEnvSecretsAllowed": self.read_env_secrets_allowed,
                "readProductionHomeSecretsAllowed": self.read_production_home_secrets_allowed,
                "readProviderKeysAllowed": self.read_provider_keys_allowed,
                "redactSecretValues": self.redact_secret_values,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
            }
        )


# ---------------------------------------------------------------------------
# 2. Frozen defaults + the secret scope taxonomy
# ---------------------------------------------------------------------------


#: The frozen secret scope taxonomy (every scope read-denied).
SECRET_SCOPES: tuple[SecretScope, ...] = (
    SecretScope("api_key", "API key", read_allowed=False, requires_explicit_policy=True),
    SecretScope("env_secret", "Environment secret", read_allowed=False, requires_explicit_policy=True),
    SecretScope("provider_key", "Provider key", read_allowed=False, requires_explicit_policy=True),
    SecretScope("production_home", "Production home secret", read_allowed=False, requires_explicit_policy=True),
    SecretScope("state_db", "Production state database", read_allowed=False, requires_explicit_policy=True),
)


def build_secret_handling_policy() -> SecretHandlingPolicy:
    """Build the frozen default secret handling policy (default deny)."""
    return SecretHandlingPolicy(
        default_disposition="DENY_BY_DEFAULT",
        read_api_keys_allowed=False,
        read_env_secrets_allowed=False,
        read_production_home_secrets_allowed=False,
        read_provider_keys_allowed=False,
        redact_secret_values=True,
        approved=False,
    )


def validate_secret_policy(policy: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate a secret handling policy. Returns ``(ok, reasons)``.

    A policy is invalid if it allows any real secret read without being
    explicitly approved. The default policy (deny-all) is the only valid one in
    the dev skeleton.
    """
    if not isinstance(policy, SecretHandlingPolicy):
        return False, ("policy_not_a_secret_handling_policy",)
    reasons: list[str] = []
    if policy.read_api_keys_allowed and not policy.approved:
        reasons.append("api_key_read_not_allowed")
    if policy.read_env_secrets_allowed and not policy.approved:
        reasons.append("env_secret_read_not_allowed")
    if policy.read_production_home_secrets_allowed:
        reasons.append("production_home_read_never_allowed")
    if policy.read_provider_keys_allowed and not policy.approved:
        reasons.append("provider_key_read_not_allowed")
    if not policy.redact_secret_values:
        reasons.append("secret_redaction_required")
    return (len(reasons) == 0), tuple(reasons)


def evaluate_secret_access(
    scope: Any = "api_key",
    *,
    policy: SecretHandlingPolicy | None = None,
    untrusted_metadata: Any = None,
) -> SecretAccessDecision:
    """Evaluate a secret access request. Always denied today.

    *untrusted_metadata* is inspected only to report ignored bypass keys. No
    secret is ever read, no environment is inspected, no ``production home`` path is
    resolved, and no production state database is opened.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    active = policy if policy is not None else build_secret_handling_policy()
    scope_id = scope if isinstance(scope, str) else "unknown"
    # Secret read is denied unless an explicit, approved policy authorizes the
    # specific scope — which the dev skeleton does not.
    allowed = False
    return SecretAccessDecision(
        allowed=allowed,
        scope=scope_id,
        production_home_accessed=False,
        env_secret_read=False,
        api_key_read=False,
        provider_key_read=False,
        value_redacted=active.redact_secret_values,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="secret_access_denied_by_default",
        ignored_metadata_keys=ignored,
    )


def redact_secret_payload(payload: Any) -> Any:
    """Recursively redact secret-shaped strings in *payload*.

    Thin wrapper over the Phase 4B redactor, re-exported so the secret policy
    layer has an explicit redaction entry point. Pure / total.
    """
    return redact_target_b_payload(payload)


def build_secret_policy_report() -> SecretPolicyReport:
    """Build the frozen aggregate secret-policy authorization report.

    Default deny: no API key / env secret / production-home secret / provider
    key is read; secret values are always redacted. Production authorization
    stays NO-GO. Pure and deterministic.
    """
    return SecretPolicyReport(
        default_disposition="DENY_BY_DEFAULT",
        read_api_keys_allowed=False,
        read_env_secrets_allowed=False,
        read_production_home_secrets_allowed=False,
        read_provider_keys_allowed=False,
        redact_secret_values=True,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="secret_policy_default_deny",
    )


def assert_secret_policy_default_deny() -> None:
    """Re-affirm the secret policy is default-deny. Pure."""
    report = build_secret_policy_report()
    assert report.default_disposition == "DENY_BY_DEFAULT"
    assert report.read_api_keys_allowed is False
    assert report.read_env_secrets_allowed is False
    assert report.read_production_home_secrets_allowed is False
    assert report.read_provider_keys_allowed is False
    assert report.redact_secret_values is True
    assert report.production_authorization == TARGET_B_AUTHORIZATION_NO_GO
    # No secret access is allowed, regardless of metadata.
    decision = evaluate_secret_access(
        "api_key",
        untrusted_metadata={"api_key": "sk-fake", "secret": "true"},
    )
    assert decision.allowed is False
    assert decision.api_key_read is False
    assert decision.production_home_accessed is False
    # The redactor masks secret-shaped values.
    assert redact_target_b_string("sk-1234") == "[REDACTED]"
    assert redact_secret_payload({"token": "ghp_fake"})["token"] == "[REDACTED]"


__all__ = [
    # schema
    "SecretScope",
    "SecretHandlingPolicy",
    "SecretAccessDecision",
    "SecretPolicyReport",
    # taxonomy
    "SECRET_SCOPES",
    # validation
    "build_secret_handling_policy",
    "validate_secret_policy",
    "evaluate_secret_access",
    "redact_secret_payload",
    "build_secret_policy_report",
    # boundary
    "assert_secret_policy_default_deny",
]
