"""Phase 4C — Target B authorization package shared common (pure stdlib, fail-closed).

This module is the **shared base** for the Phase 4C Target B **authorization
package**. Phase 4B implemented the gated engineering layers (every schema,
verifier, model, broker, gate, orchestrator, audit, and rollback — all
disabled). Phase 4C builds the **authorization-material validation structure**
on top of those layers: the schema for a real out-of-band human approval record,
the trust token validation pipeline, the trusted publisher set, the production
signature verifier authorization adapter, the sandbox worker lifecycle approval,
the registry trust policy approval, the network allowlist, the secret handling
policy, the rollback / incident plan approval, the route authorization plan, the
P0 pending-gate resolution evaluator, and the unified enablement readiness
evaluator.

Phase 4C is **deliberately inert** and changes nothing about production state:

  - It does NOT fabricate an approval. It does NOT bypass P0. It does NOT mint a
    trust token. It does NOT treat metadata, a static manifest, or an AI-generated
    approval as authorization. It does NOT flip the production runtime to GO.
  - It builds the **validation structure** that real out-of-band authorization
    materials would have to satisfy, and it keeps every gate **fail-closed**.
  - Pure / deterministic / stdlib-only. No filesystem access, no network, no
    subprocess, no dynamic import, no eval / exec, no real secret read, no
    production access, no production home directory access, and no production
    state database access.
  - Every Phase 4C authorization verdict is frozen ``NO-GO`` / ``BLOCKED`` /
    ``not_authorized``; the readiness evaluator returns ``BLOCKED`` by default;
    ``p0_resolved_count`` stays 0; the trust token stays not provisioned; the
    production signature verifier stays unauthorized.
  - The redactor masks any secret-shaped / production-path-shaped /
    fake-authorization-shaped substring should one ever reach a projected payload.
    The layers carry no secrets today.

This module is **not** imported by ``dev_web_api`` (the read-only WebUI surface
mirrors the package via a frozen static frontend manifest), so it adds **no
backend route** and changes **no route governance counts**.

Phase: 4C — Target B Authorization & Gate Resolution Package
Status: implemented (authorization-material validation structure). NOT an
        authorization, NOT an approval, NOT a signoff, NOT a closeout, NOT
        production authorization, and NOT an enablement. Resolves nothing;
        enables nothing; provisions nothing.
"""

from __future__ import annotations

from typing import Any, Mapping

from hermes_cli.dev_web_target_b_common import (
    TARGET_B_NO_GO,
    TARGET_B_PENDING_HUMAN_REVIEW_GATES,
    TARGET_B_P0_PARTIAL_EVIDENCE,
    TARGET_B_P0_PENDING_HUMAN_REVIEW,
    TARGET_B_P0_RESOLVED,
    TARGET_B_P0_TOTAL,
    TARGET_B_ROUTE_GOVERNANCE_BASELINE,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
    redact_target_b_string,
)

# ---------------------------------------------------------------------------
# 0. Re-exported defense-in-depth redactor (mirrors Phase 4B common)
# ---------------------------------------------------------------------------

__all__ = [
    "redact_target_b_string",
    "redact_target_b_payload",
    "detect_target_b_untrusted_metadata",
]


# ---------------------------------------------------------------------------
# 1. Frozen Phase 4C schema / status constants (cannot be flipped by metadata)
# ---------------------------------------------------------------------------

#: Schema version mirrored by the frontend Phase 4C authorization manifest.
TARGET_B_AUTHORIZATION_VERSION: str = "phase-4c-target-b-authorization-v1"

#: The frozen Phase 4C authorization package status — validation structure
#: implemented, never an enablement.
TARGET_B_AUTHORIZATION_STATUS: str = "AUTHORIZATION_PACKAGE_IMPLEMENTED"

#: The frozen Phase 4C production authorization verdict — always NO-GO.
TARGET_B_AUTHORIZATION_NO_GO: str = TARGET_B_NO_GO

#: The default reason token returned when no real authorization material exists.
TARGET_B_AUTHORIZATION_MISSING_REASON: str = "authorization_material_missing"

#: The reason token returned when a fake / forged approval is rejected.
TARGET_B_FAKE_AUTHORIZATION_REJECTED_REASON: str = "fake_authorization_rejected"

#: The reason token returned when an AI-generated approval is rejected.
TARGET_B_AI_AUTHORIZATION_REJECTED_REASON: str = "ai_authorization_rejected"

#: The reason token returned when a metadata-only approval is rejected.
TARGET_B_METADATA_AUTHORIZATION_REJECTED_REASON: str = "metadata_authorization_rejected"

#: The reason token returned when a static-manifest approval is rejected.
TARGET_B_STATIC_MANIFEST_AUTHORIZATION_REJECTED_REASON: str = "static_manifest_authorization_rejected"

#: The reason token returned when a fixture-only approval is (correctly) not
#: honored as production authorization.
TARGET_B_FIXTURE_NOT_PRODUCTION_REASON: str = "fixture_only_not_production_authorization"


# ---------------------------------------------------------------------------
# 2. Enablement readiness statuses (the four allowed values)
# ---------------------------------------------------------------------------

#: No real authorization material present (the default).
READINESS_BLOCKED: str = "BLOCKED"

#: Some authorization material is present, but the package is incomplete.
READINESS_PACKAGE_INCOMPLETE: str = "AUTHORIZATION_PACKAGE_INCOMPLETE"

#: A complete package of (fixture) authorization material is present, but
#: production is not enabled. Only reachable in test-only mode.
READINESS_AUTHORIZED_NOT_ENABLED: str = "AUTHORIZATION_READY_BUT_NOT_ENABLED"

#: A complete package of REAL authorization material is present AND production
#: mode is explicitly authorized. Never reachable in the dev skeleton.
READINESS_ENABLEMENT_ALLOWED: str = "ENABLEMENT_ALLOWED_BY_POLICY"

#: The frozen tuple of allowed readiness statuses.
READINESS_STATUSES: tuple[str, ...] = (
    READINESS_BLOCKED,
    READINESS_PACKAGE_INCOMPLETE,
    READINESS_AUTHORIZED_NOT_ENABLED,
    READINESS_ENABLEMENT_ALLOWED,
)


# ---------------------------------------------------------------------------
# 3. The Phase 4C authorization-package layer keys (the 12 sub-layers)
# ---------------------------------------------------------------------------

#: The 12 Phase 4C authorization-package sub-layers, in canonical order. Every
#: one must be present and authorized before Target B could ever be considered
#: for enablement. None is authorized in the dev skeleton.
TARGET_B_AUTHORIZATION_LAYERS: tuple[str, ...] = (
    "human_approval",
    "trust_token",
    "trusted_publishers",
    "production_signature",
    "sandbox_lifecycle",
    "registry_policy",
    "network_policy",
    "secret_policy",
    "incident_rollback",
    "route_authorization",
    "p0_gate_resolution",
    "enablement_readiness",
)

#: The number of independent authorization sub-layers that must ALL pass before
#: enablement could even be considered (excludes the enablement_readiness
#: aggregator itself, which is the 12th layer and the consumer of the other 11).
TARGET_B_AUTHORIZATION_GATE_COUNT: int = 11


# ---------------------------------------------------------------------------
# 4. Fixture-only marker helpers
# ---------------------------------------------------------------------------


def is_fixture_authorization_payload(payload: Any) -> bool:
    """True iff *payload* explicitly marks itself as fixture-only test material.

    Pure / total. Used by every Phase 4C layer to ensure a test-only fixture is
    never honored as production authorization.
    """
    if isinstance(payload, Mapping):
        for key in ("fixture_only", "fixtureOnly", "test_only", "testOnly"):
            if payload.get(key) is True:
                return True
    return False


# Extend the public surface now that the constants are defined.
__all__ = [
    # redactor + metadata detection (re-exported)
    "redact_target_b_string",
    "redact_target_b_payload",
    "detect_target_b_untrusted_metadata",
    # frozen constants
    "TARGET_B_AUTHORIZATION_VERSION",
    "TARGET_B_AUTHORIZATION_STATUS",
    "TARGET_B_AUTHORIZATION_NO_GO",
    "TARGET_B_AUTHORIZATION_MISSING_REASON",
    "TARGET_B_FAKE_AUTHORIZATION_REJECTED_REASON",
    "TARGET_B_AI_AUTHORIZATION_REJECTED_REASON",
    "TARGET_B_METADATA_AUTHORIZATION_REJECTED_REASON",
    "TARGET_B_STATIC_MANIFEST_AUTHORIZATION_REJECTED_REASON",
    "TARGET_B_FIXTURE_NOT_PRODUCTION_REASON",
    # P0 / route baselines (re-exported for convenience)
    "TARGET_B_P0_TOTAL",
    "TARGET_B_P0_RESOLVED",
    "TARGET_B_P0_PARTIAL_EVIDENCE",
    "TARGET_B_P0_PENDING_HUMAN_REVIEW",
    "TARGET_B_PENDING_HUMAN_REVIEW_GATES",
    "TARGET_B_ROUTE_GOVERNANCE_BASELINE",
    # readiness statuses
    "READINESS_BLOCKED",
    "READINESS_PACKAGE_INCOMPLETE",
    "READINESS_AUTHORIZED_NOT_ENABLED",
    "READINESS_ENABLEMENT_ALLOWED",
    "READINESS_STATUSES",
    # layer keys
    "TARGET_B_AUTHORIZATION_LAYERS",
    "TARGET_B_AUTHORIZATION_GATE_COUNT",
    # fixture helpers
    "is_fixture_authorization_payload",
]
