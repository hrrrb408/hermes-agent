"""Phase 4B — Target B shared common helpers (pure stdlib, fail-closed).

This module is the **shared base** for the Phase 4B Target B engineering
layers. Target B is the long-term goal of opening a real production plugin
runtime (signed / arbitrary plugin loading, a remote registry, a marketplace,
WebUI execution, and a production rollout). Phase 4B implements the **full
engineering path** for that runtime — every schema, verifier, model, broker,
gate, orchestrator, audit, and rollback — while keeping **every capability
gated and disabled**.

It is deliberately inert and self-contained:

  - Pure / deterministic / stdlib-only. No filesystem access, no network, no
    subprocess, no dynamic import, no real secret read, no production access,
    no production home directory access, and no production state database
    access.
  - Every Target B authorization verdict is frozen ``NO-GO``; every capability
    is frozen disabled; every permission is frozen ``DENIED_BY_DEFAULT``; the
    production authorization is frozen ``NO-GO``; ``p0_resolved_count`` stays 0.
  - The redactor masks any secret-shaped / production-path-shaped /
    fake-authorization-shaped substring should one ever reach a projected
    payload. The layers carry no secrets today.

This module is **not** imported by ``dev_web_api`` (the read-only WebUI surface
mirrors the layers via a frozen static frontend manifest), so it adds **no
backend route** and changes **no route governance counts**.

Phase: 4B — Target B End-to-End Implementation (gated)
Status: implemented (gated engineering layers). NOT an authorization, NOT an
        approval, NOT a signoff, NOT a closeout, and NOT production
        authorization. Resolves nothing; enables nothing.
"""

from __future__ import annotations

from typing import Any, Mapping

# ---------------------------------------------------------------------------
# 0. Self-contained defense-in-depth redactor
#
# A tiny local redactor masks any secret-shaped / production-path-shaped /
# fake-authorization-shaped substring should one ever reach a projected
# payload — the layers themselves carry no secrets today. Mirrors the
# conservative spirit of the Phase 4A scaffold redactor (prefer masking over
# exposing) without depending on it. Pure / total / stdlib-only.
# ---------------------------------------------------------------------------

#: Secret / production-path / fake-authorization stems a redactor masks. These
#: are *patterns* (not real values) — they exist only to scrub a substring.
_REDACT_STEMS: frozenset[str] = frozenset(
    {
        "sk-",
        "bearer ",
        "authorization:",
        "ghp_",
        "xox",
        "begin private key",
        "production home",
        "state database",
        "implementation_authorization=go",
        "implementation authorization = go",
        "openai_api_key",
        "db_password",
        "accesstoken",
        "phase_3i_authorized=true",
        "production_approved=true",
        "route_exception_approved=true",
        "approved_by_ai=true",
        "trust_token=fake",
        "trust_token=",
        "registry_token=fake",
        "registry_token=",
        "plugin_signature=fake-private-key",
        "plugin_signature=",
        "target_b_authorized=true",
        "target_b_authorized=",
        "production_runtime_go=true",
        "production_runtime_go=",
    }
)

#: The mask placeholder emitted by the redactor.
_REDACTED: str = "[REDACTED]"

#: The maximum recursion depth the redactor descends before masking wholesale.
_REDACT_MAX_DEPTH: int = 32


def redact_target_b_string(value: str) -> str:
    """Mask *value* entirely if it contains any redaction stem. Pure / total."""
    if not isinstance(value, str) or not value:
        return ""
    lowered = value.lower()
    for stem in _REDACT_STEMS:
        if stem in lowered:
            return _REDACTED
    return value


def redact_target_b_payload(payload: Any, *, depth: int = 0) -> Any:
    """Recursively redact secret-shaped strings in *payload*. Pure / total.

    Walks dicts / lists / tuples / strings; leaves every other value untouched.
    Never raises, never reads files or the network.
    """
    if depth > _REDACT_MAX_DEPTH:  # depth guard against pathological nesting
        return _REDACTED
    if isinstance(payload, str):
        return redact_target_b_string(payload)
    if isinstance(payload, Mapping):
        return {k: redact_target_b_payload(v, depth=depth + 1) for k, v in payload.items()}
    if isinstance(payload, (list, tuple)):
        redacted = [redact_target_b_payload(v, depth=depth + 1) for v in payload]
        return redacted if isinstance(payload, list) else tuple(redacted)
    return payload


# ---------------------------------------------------------------------------
# 1. Frozen verdict / status constants (cannot be flipped by metadata)
# ---------------------------------------------------------------------------

#: Schema version mirrored by the frontend Target B implementation manifest.
TARGET_B_IMPLEMENTATION_VERSION: str = "phase-4b-target-b-implementation-v1"

#: The frozen Target B implementation status — engineering layers drafted,
#: never an enablement.
TARGET_B_IMPLEMENTATION_STATUS: str = "SCAFFOLD_READY"

#: The frozen Target B execution status — always disabled.
TARGET_B_EXECUTION_STATUS: str = "DISABLED"

#: The frozen authorization verdict for every Target B dimension.
TARGET_B_NO_GO: str = "NO-GO"

#: The frozen route-governance baseline (unchanged by these layers).
TARGET_B_ROUTE_GOVERNANCE_BASELINE: str = "34/34/5/0/1/1"

#: The frozen P0 totals (resolved_count stays 0).
TARGET_B_P0_TOTAL: int = 24
TARGET_B_P0_RESOLVED: int = 0
TARGET_B_P0_PARTIAL_EVIDENCE: int = 19
TARGET_B_P0_PENDING_HUMAN_REVIEW: int = 5

#: The frozen set of gate IDs that require an explicit out-of-band human
#: approval before Target B could ever be considered.
TARGET_B_PENDING_HUMAN_REVIEW_GATES: tuple[str, ...] = (
    "P0-15",
    "P0-16",
    "P0-18",
    "P0-19",
    "P0-22",
)

#: The frozen permission disposition — denied by default, never granted.
TARGET_B_PERMISSION_DENIED: str = "DENIED_BY_DEFAULT"

#: The stable reason token every execution deny builder returns.
TARGET_B_DISABLED_REASON: str = "target_b_disabled"

#: The stable reason token the registry deny builder returns.
TARGET_B_REGISTRY_DISABLED_REASON: str = "registry_disabled"

#: The stable reason token the marketplace deny builder returns.
TARGET_B_MARKETPLACE_DISABLED_REASON: str = "marketplace_disabled"

#: The stable reason token the sandbox deny builder returns.
TARGET_B_SANDBOX_DISABLED_REASON: str = "sandbox_broker_disabled"

#: The stable reason token the signature verifier returns when not authorized.
TARGET_B_SIGNATURE_NOT_AUTHORIZED_REASON: str = "signature_verification_not_authorized"

#: The stable reason token the approval gate returns when not authorized.
TARGET_B_APPROVAL_NOT_AUTHORIZED_REASON: str = "approval_not_authorized"

#: The stable reason token the rollback layer returns when design-only.
TARGET_B_ROLLBACK_DESIGN_ONLY_REASON: str = "rollback_design_ready_only"

#: The real, out-of-band trust token that would sign a genuine human approval
#: for Target B. It is **deliberately None** in the dev skeleton — it would be
#: provisioned by a separate, auditable human process that is explicitly out of
#: scope. Because it is None, no approval constructed from request metadata —
#: or forged by direct construction — can ever enable Target B.
_REAL_TRUST_TOKEN: str | None = None

#: The set of trusted publishers that the *production* signature verifier would
#: honor. It is **deliberately empty** in the dev skeleton: no publisher is
#: trusted until a real trust policy and verifier are authorized out of band.
#: The deterministic *fixture* verifier honors a single ``fixture`` publisher
#: for tests only and is explicitly marked ``fixture_only``.
_REAL_TRUSTED_PUBLISHERS: frozenset[str] = frozenset()


def real_trust_token_provisioned() -> bool:
    """True iff a real out-of-band trust token is provisioned.

    Always False in the dev skeleton. Pure — never reads files, env, or the
    network. A caller cannot flip this by passing metadata.
    """
    return _REAL_TRUST_TOKEN is not None


def real_trusted_publishers() -> frozenset[str]:
    """Return the set of trusted publishers honored by the production verifier.

    Always empty in the dev skeleton. Pure — a defensive copy is returned so a
    caller cannot mutate the canonical (empty) set.
    """
    return frozenset(_REAL_TRUSTED_PUBLISHERS)


# ---------------------------------------------------------------------------
# 2. Untrusted-metadata detection (bypass prevention)
# ---------------------------------------------------------------------------

#: Metadata keys that look like a Target B authorization bypass attempt.
#: Detected and ignored by every public deny builder. The list is intentionally
#: broad: every approval / authorization / trust-token / registry / marketplace
#: / production / runtime / resolved variant a smuggler might invent is reported
#: as ignored. Detection is diagnostic only — the authorization flags are
#: frozen constants regardless, so an undetected variant still authorizes
#: nothing.
_UNTRUSTED_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "approved",
        "approve",
        "authorization",
        "authorized",
        "authorised",
        "implementation_authorization",
        "implementationAuthorization",
        "trust_token",
        "trustToken",
        "real_trust_token",
        "realTrustToken",
        "target_b_authorized",
        "targetBAuthorized",
        "production_approved",
        "productionApproved",
        "production_runtime_go",
        "productionRuntimeGo",
        "production_rollout_approved",
        "productionRolloutApproved",
        "registry_token",
        "registryToken",
        "registry_authorized",
        "registryAuthorized",
        "marketplace_authorized",
        "marketplaceAuthorized",
        "plugin_signature",
        "pluginSignature",
        "signature_verified",
        "signatureVerified",
        "signed",
        "signature",
        "bypass",
        "override",
        "force",
        "force_allow",
        "forceAllow",
        "skip_review",
        "p0_resolved",
        "p0Resolved",
        "resolved",
        "approved_by_ai",
        "approvedByAi",
        "approved_by_human",
        "approvedByHuman",
        "sandbox_bypass",
        "sandboxBypass",
        "kill_switch_armed",
        "killSwitchArmed",
        "route_exception_approved",
        "routeExceptionApproved",
        "token",
        "secret",
        "password",
        "apikey",
        "api_key",
    }
)


def detect_target_b_untrusted_metadata(metadata: Any) -> tuple[str, ...]:
    """Return the sorted bypass-shaped keys present in *metadata*.

    Pure inspection — the keys are reported so a caller / audit can record that
    a bypass attempt was detected and ignored. Never raises.
    """
    if not isinstance(metadata, Mapping):
        return ()
    found: set[str] = set()
    for key in metadata.keys():
        if not isinstance(key, str):
            continue
        if key in _UNTRUSTED_METADATA_KEYS:
            found.add(key)
        else:
            normalized = key.strip().lower().replace("-", "_")
            if normalized in _UNTRUSTED_METADATA_KEYS:
                found.add(key)
    return tuple(sorted(found))


# ---------------------------------------------------------------------------
# 3. Frozen production-safety / boundary constants (grep-able, pure)
# ---------------------------------------------------------------------------

#: The canonical dev HERMES_HOME (development instance only).
TARGET_B_DEV_HERMES_HOME: str = "/Users/huangruibang/Code/hermes-home-dev"

#: The production HERMES_HOME — referenced ONLY as a denied target. It is never
#: resolved, never opened, never stat'd.
TARGET_B_PRODUCTION_HERMES_HOME_STEM: str = "production home (~/.hermes)"

#: The production gateway PID — referenced ONLY as a do-not-touch target. It is
#: never signaled, never read.
TARGET_B_PRODUCTION_GATEWAY_PID_REFERENCE: str = "production gateway pid 28428"

#: The reserved ``.invalid`` registry example domain — never contacted.
TARGET_B_REGISTRY_EXAMPLE_DOMAIN: str = "https://registry.example.invalid"


__all__ = [
    # redactor
    "redact_target_b_string",
    "redact_target_b_payload",
    "REDACT_STEMS",
    # constants
    "TARGET_B_IMPLEMENTATION_VERSION",
    "TARGET_B_IMPLEMENTATION_STATUS",
    "TARGET_B_EXECUTION_STATUS",
    "TARGET_B_NO_GO",
    "TARGET_B_ROUTE_GOVERNANCE_BASELINE",
    "TARGET_B_P0_TOTAL",
    "TARGET_B_P0_RESOLVED",
    "TARGET_B_P0_PARTIAL_EVIDENCE",
    "TARGET_B_P0_PENDING_HUMAN_REVIEW",
    "TARGET_B_PENDING_HUMAN_REVIEW_GATES",
    "TARGET_B_PERMISSION_DENIED",
    "TARGET_B_DISABLED_REASON",
    "TARGET_B_REGISTRY_DISABLED_REASON",
    "TARGET_B_MARKETPLACE_DISABLED_REASON",
    "TARGET_B_SANDBOX_DISABLED_REASON",
    "TARGET_B_SIGNATURE_NOT_AUTHORIZED_REASON",
    "TARGET_B_APPROVAL_NOT_AUTHORIZED_REASON",
    "TARGET_B_ROLLBACK_DESIGN_ONLY_REASON",
    "real_trust_token_provisioned",
    "real_trusted_publishers",
    # metadata detection
    "detect_target_b_untrusted_metadata",
    "UNTRUSTED_METADATA_KEYS",
    # boundary constants
    "TARGET_B_DEV_HERMES_HOME",
    "TARGET_B_PRODUCTION_HERMES_HOME_STEM",
    "TARGET_B_PRODUCTION_GATEWAY_PID_REFERENCE",
    "TARGET_B_REGISTRY_EXAMPLE_DOMAIN",
]
