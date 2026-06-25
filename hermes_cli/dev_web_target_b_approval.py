"""Phase 4B — Target B approval / authorization gate (pure stdlib, fail-closed).

Layer 7 of the Phase 4B Target B engineering path. Defines the **approval /
authorization gate**: the human-approval record, the trust token, and the
authorization decision.

Validity is derived from a token-derived **signature**, which only the real
out-of-band trust token can produce. The dev skeleton holds **no** such token
(:func:`real_trust_token_provisioned` is False), so **no** approval is ever
valid — including one a caller tries to forge by direct construction or by
smuggling metadata (``approved_by_ai=true``, ``trust_token=fake``,
``target_b_authorized=true``, ``production_runtime_go=true``,
``route_exception_approved=true``, ``implementation_authorization=GO``,
``approved=true``, ``signed=true``). Production authorization stays NO-GO.

This is the same fail-closed pattern used by the Phase 3E–H
:mod:`dev_web_p0_evidence` approval model, extended to the Target B
implementation authorization. It is deliberately self-contained (it imports no
other dev_web approval module) so it cannot be coupled into a bypass path.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no real secret read, no production access, no
real trust token.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_target_b_common import (
    TARGET_B_APPROVAL_NOT_AUTHORIZED_REASON,
    TARGET_B_NO_GO,
    TARGET_B_PENDING_HUMAN_REVIEW_GATES,
    detect_target_b_untrusted_metadata,
    real_trust_token_provisioned,
    redact_target_b_payload,
)

# ---------------------------------------------------------------------------
# 1. Frozen reviewer roles + decision verbs
# ---------------------------------------------------------------------------

REVIEWER_PROJECT_OWNER: str = "project owner"
REVIEWER_SECURITY: str = "security reviewer"
REVIEWER_ROUTE_GOVERNANCE: str = "route-governance reviewer"
REVIEWER_PRODUCTION_SAFETY: str = "production safety reviewer"

#: The reviewers who may own a Target B approval. Any other reviewer is invalid.
APPROVAL_REVIEWERS: frozenset[str] = frozenset(
    {
        REVIEWER_PROJECT_OWNER,
        REVIEWER_SECURITY,
        REVIEWER_ROUTE_GOVERNANCE,
        REVIEWER_PRODUCTION_SAFETY,
    }
)

#: Valid approval decisions.
APPROVAL_DECISION_APPROVE: str = "approve"
APPROVAL_DECISION_REJECT: str = "reject"
APPROVAL_DECISIONS: frozenset[str] = frozenset({APPROVAL_DECISION_APPROVE, APPROVAL_DECISION_REJECT})

#: A notional approval staleness window (seconds). The dev skeleton holds no
#: token, so staleness is moot — but a record carrying a future/stale timestamp
#: is still rejected defensively.
APPROVAL_MAX_AGE_SECONDS: int = 86400


# ---------------------------------------------------------------------------
# 2. The trust token model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrustToken:
    """An out-of-band trust token reference. Never the real token.

    The dev skeleton provisions no token. A ``TrustToken`` constructed from
    request metadata (or by direct construction) is **never** valid —
    :func:`validate_trust_token` requires the real token, which is None.
    """

    token: str
    provisioned_out_of_band: bool

    def to_safe_dict(self) -> dict[str, Any]:
        # The token value is never exposed — it is token-derived material.
        return redact_target_b_payload(
            {
                "token": "[REDACTED]" if self.token else "",
                "provisionedOutOfBand": self.provisioned_out_of_band,
                "valid": validate_trust_token(self),
            }
        )


def validate_trust_token(token: Any) -> bool:
    """True iff *token* is the real out-of-band trust token.

    Always False in the dev skeleton (no token is provisioned). A fake token
    (``"fake"``, ``"trust_token=fake"``, any string a caller supplies) is
    rejected. Pure — never reads files, env, or the network.
    """
    # The real token is None. There is no string a caller can supply that
    # equals None, so every token is invalid by construction.
    if not real_trust_token_provisioned():
        return False
    # Unreachable in the dev skeleton: a real token would be compared here
    # using a constant-time hmac.compare_digest against the provisioned value.
    return False


def build_trust_token_status() -> TrustToken:
    """Build the frozen trust-token status: not provisioned."""
    return TrustToken(token="", provisioned_out_of_band=False)


# ---------------------------------------------------------------------------
# 3. The human approval record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    """A request to authorize Target B (or one of its gates). Untrusted."""

    gate_ids: tuple[str, ...]
    reviewer: str
    decision: str
    untrusted_metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class HumanApprovalRecord:
    """An out-of-band human approval for one or more Target B gates.

    Validity is derived from :attr:`signature`, which only the real out-of-band
    trust token can produce. The dev skeleton holds **no** such token, so
    :func:`is_approval_valid` returns False for *every* record — including one a
    caller forges by constructing the dataclass directly or by smuggling
    metadata through :func:`create_human_approval`.
    """

    gate_ids: tuple[str, ...]
    reviewer: str
    decision: str
    signature: str = ""

    def is_valid(self) -> bool:
        return is_approval_valid(self)

    def to_safe_dict(self) -> dict[str, Any]:
        # The signature is never exposed (it is token-derived material).
        return redact_target_b_payload(
            {
                "gateIds": list(self.gate_ids),
                "reviewer": self.reviewer,
                "decision": self.decision,
                "valid": self.is_valid(),
            }
        )


def _expected_approval_signature(gate_ids: tuple[str, ...], reviewer: str) -> str | None:
    """The signature a genuine human approval carries.

    Derived from the real out-of-band trust token. Returns None when no token is
    provisioned (the dev skeleton), making every approval invalid by
    construction.
    """
    if not real_trust_token_provisioned():
        return None
    # Unreachable in the dev skeleton. A real implementation would derive the
    # signature from the provisioned token + the gate ids + reviewer.
    return None


def create_human_approval(
    gate_ids: Any,
    reviewer: Any,
    decision: Any,
    *,
    trust_token: Any = None,
) -> HumanApprovalRecord:
    """Construct a (always-invalid in the dev skeleton) human approval record.

    A non-empty :attr:`signature` is attached **only** when *trust_token*
    validates against the real out-of-band token. Since no token is provisioned,
    every call — including ones smuggling ``approved`` / ``production_runtime_go``
    / ``signed`` through *trust_token* — yields a record whose signature is empty
    and therefore invalid.
    """
    gate_tuple = (
        tuple(gate_ids) if isinstance(gate_ids, (list, tuple)) else ()
    )
    gate_tuple = tuple(g for g in gate_tuple if isinstance(g, str))
    reviewer_text = reviewer if isinstance(reviewer, str) else "<invalid>"
    decision_text = decision if isinstance(decision, str) else "<invalid>"
    signature = ""
    if validate_trust_token(trust_token):
        signature = _expected_approval_signature(gate_tuple, reviewer_text) or ""
    return HumanApprovalRecord(
        gate_ids=gate_tuple,
        reviewer=reviewer_text,
        decision=decision_text,
        signature=signature,
    )


def is_approval_valid(record: Any) -> bool:
    """True iff *record* is a valid :class:`HumanApprovalRecord`.

    Validity requires the real trust token to exist AND the record's signature
    to match the expected token-derived signature AND the record to be
    structurally sound (a known reviewer, an ``approve`` decision, non-empty
    gate ids that are all pending-human-review gates). With no token provisioned
    (the dev skeleton), this is always False — defeating both metadata smuggling
    and direct dataclass forgery.
    """
    if not isinstance(record, HumanApprovalRecord):
        return False
    if record.decision != APPROVAL_DECISION_APPROVE:
        return False
    if record.reviewer not in APPROVAL_REVIEWERS:
        return False
    if not record.gate_ids:
        return False
    if not all(g in TARGET_B_PENDING_HUMAN_REVIEW_GATES for g in record.gate_ids):
        return False
    expected = _expected_approval_signature(record.gate_ids, record.reviewer)
    if expected is None:
        return False
    return bool(record.signature) and record.signature == expected


def validate_human_approval_record(record: Any) -> tuple[bool, tuple[str, ...]]:
    """Validate a human approval record's structure + signature.

    Returns ``(valid, reasons)``. Always ``(False, reasons)`` in the dev
    skeleton (no token). Reports *why* a record is invalid so an audit can
    record it.
    """
    if not isinstance(record, HumanApprovalRecord):
        return False, ("record_not_a_human_approval_record",)
    reasons: list[str] = []
    if record.decision != APPROVAL_DECISION_APPROVE:
        reasons.append("decision_not_approve")
    if record.reviewer not in APPROVAL_REVIEWERS:
        reasons.append("reviewer_unknown")
    if not record.gate_ids:
        reasons.append("gate_ids_missing")
    elif not all(g in TARGET_B_PENDING_HUMAN_REVIEW_GATES for g in record.gate_ids):
        reasons.append("gate_ids_not_pending_human_review")
    if not real_trust_token_provisioned():
        reasons.append("trust_token_not_provisioned")
    if not record.signature:
        reasons.append("signature_missing_unsigned")
    expected = _expected_approval_signature(record.gate_ids, record.reviewer)
    if expected is not None and record.signature != expected:
        reasons.append("signature_mismatch")
    return is_approval_valid(record), tuple(reasons)


# ---------------------------------------------------------------------------
# 4. Fake / AI / metadata approval rejection + the authorization decision
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    """The frozen Target B authorization decision. Always NO-GO."""

    human_approval_valid: bool
    trust_token_provisioned: bool
    fake_approval_accepted: bool
    ai_approval_accepted: bool
    metadata_approval_accepted: bool
    production_authorization: str
    reason: str
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "humanApprovalValid": self.human_approval_valid,
                "trustTokenProvisioned": self.trust_token_provisioned,
                "fakeApprovalAccepted": self.fake_approval_accepted,
                "aiApprovalAccepted": self.ai_approval_accepted,
                "metadataApprovalAccepted": self.metadata_approval_accepted,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
            }
        )


def reject_fake_approval(untrusted_metadata: Any = None) -> AuthorizationDecision:
    """Reject a fake / AI / metadata approval. Always production NO-GO.

    *untrusted_metadata* is inspected only to report which bypass-shaped keys
    were detected and ignored. No flag can flip.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    return AuthorizationDecision(
        human_approval_valid=False,
        trust_token_provisioned=real_trust_token_provisioned(),
        fake_approval_accepted=False,
        ai_approval_accepted=False,
        metadata_approval_accepted=False,
        production_authorization=TARGET_B_NO_GO,
        reason=TARGET_B_APPROVAL_NOT_AUTHORIZED_REASON,
        ignored_metadata_keys=ignored,
    )


def evaluate_target_b_approval(
    record: Any = None,
    untrusted_metadata: Any = None,
) -> AuthorizationDecision:
    """Evaluate the Target B approval gate. Always NO-GO in the dev skeleton.

    If *record* is a :class:`HumanApprovalRecord`, its structural + signature
    validity is checked (always invalid without a token). *untrusted_metadata*
    is inspected only to report ignored bypass keys.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    human_valid = False
    if isinstance(record, HumanApprovalRecord):
        human_valid, _reasons = validate_human_approval_record(record)
    return AuthorizationDecision(
        human_approval_valid=human_valid,
        trust_token_provisioned=real_trust_token_provisioned(),
        fake_approval_accepted=False,
        ai_approval_accepted=False,
        metadata_approval_accepted=False,
        production_authorization=TARGET_B_NO_GO,
        reason=TARGET_B_APPROVAL_NOT_AUTHORIZED_REASON,
        ignored_metadata_keys=ignored,
    )


def build_authorization_decision() -> AuthorizationDecision:
    """Build the frozen aggregate authorization decision. NO-GO."""
    return AuthorizationDecision(
        human_approval_valid=False,
        trust_token_provisioned=False,
        fake_approval_accepted=False,
        ai_approval_accepted=False,
        metadata_approval_accepted=False,
        production_authorization=TARGET_B_NO_GO,
        reason=TARGET_B_APPROVAL_NOT_AUTHORIZED_REASON,
        ignored_metadata_keys=(),
    )


def assert_approval_layer_disabled() -> None:
    """Re-affirm the approval layer disabled invariants. Pure."""
    token = build_trust_token_status()
    assert token.provisioned_out_of_band is False
    assert validate_trust_token(token) is False
    assert validate_trust_token("fake") is False
    assert validate_trust_token("trust_token=fake") is False
    # A directly-constructed record is invalid.
    forged = HumanApprovalRecord(
        gate_ids=("P0-15",),
        reviewer=REVIEWER_PROJECT_OWNER,
        decision=APPROVAL_DECISION_APPROVE,
        signature="forged-signature",
    )
    assert is_approval_valid(forged) is False
    # A record minted through the factory with a fake token is invalid.
    smuggled = create_human_approval(
        ("P0-15",), REVIEWER_PROJECT_OWNER, APPROVAL_DECISION_APPROVE, trust_token="fake"
    )
    assert is_approval_valid(smuggled) is False
    decision = build_authorization_decision()
    assert decision.production_authorization == TARGET_B_NO_GO
    assert decision.fake_approval_accepted is False


__all__ = [
    # reviewers / decisions
    "REVIEWER_PROJECT_OWNER",
    "REVIEWER_SECURITY",
    "REVIEWER_ROUTE_GOVERNANCE",
    "REVIEWER_PRODUCTION_SAFETY",
    "APPROVAL_REVIEWERS",
    "APPROVAL_DECISION_APPROVE",
    "APPROVAL_DECISION_REJECT",
    "APPROVAL_DECISIONS",
    "APPROVAL_MAX_AGE_SECONDS",
    # trust token
    "TrustToken",
    "validate_trust_token",
    "build_trust_token_status",
    # approval record
    "ApprovalRequest",
    "HumanApprovalRecord",
    "create_human_approval",
    "is_approval_valid",
    "validate_human_approval_record",
    # decision
    "AuthorizationDecision",
    "reject_fake_approval",
    "evaluate_target_b_approval",
    "build_authorization_decision",
    # boundary
    "assert_approval_layer_disabled",
]
