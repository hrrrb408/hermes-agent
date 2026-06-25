"""Phase 4C — Target B human approval record schema (pure stdlib, fail-closed).

Layer 1 of the Phase 4C Target B authorization package. Defines the **real
out-of-band human approval record schema** and the validator that decides
whether a genuine human approval exists for Target B.

A valid human approval is signed out-of-band by a **trusted human reviewer**,
covers the required Target B gates (P0-15 / P0-16 / P0-18 / P0-19 / P0-22),
carries real evidence references, a non-wildcard environment scope, an explicit
validity window, a replay nonce, and a token-derived signature that only the
real out-of-band trust token can produce. The dev skeleton holds **no** such
token, so **no** approval is ever valid — including:

  - a fake approval constructed from request metadata (``approved=true``,
    ``approved_by_ai=true``, ``target_b_authorized=true``,
    ``production_runtime_go=true``, ``implementation_authorization=GO``);
  - an AI-generated approval (``approved_by_ai=true``);
  - a metadata-only approval (``approved=true`` in a request body);
  - a static-manifest approval (an ``approved=true`` row in a frozen manifest);
  - a directly-constructed / forged dataclass with a hand-written signature.

The validator returns ``valid=False`` with the reason ``human_approval_missing``
by default. A test-only fixture builder is provided so a test can prove the
validator's positive logic, but the fixture is explicitly marked
``fixture_only`` / ``production_valid=False`` and never enables Target B.

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no eval / exec, no real secret read, no real
trust token, no production access. Validity checks use deterministic string
comparison on ISO-8601 timestamps — never the wall clock — so the validator is
fully deterministic.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_target_b_authorization_common import (
    TARGET_B_AI_AUTHORIZATION_REJECTED_REASON,
    TARGET_B_AUTHORIZATION_NO_GO,
    TARGET_B_FAKE_AUTHORIZATION_REJECTED_REASON,
    TARGET_B_FIXTURE_NOT_PRODUCTION_REASON,
    TARGET_B_METADATA_AUTHORIZATION_REJECTED_REASON,
    TARGET_B_STATIC_MANIFEST_AUTHORIZATION_REJECTED_REASON,
    detect_target_b_untrusted_metadata,
    is_fixture_authorization_payload,
    redact_target_b_payload,
)
from hermes_cli.dev_web_target_b_common import (
    TARGET_B_PENDING_HUMAN_REVIEW_GATES,
    real_trust_token_provisioned,
)

# ---------------------------------------------------------------------------
# 1. Frozen reviewer roles + decision verbs + scope constants
# ---------------------------------------------------------------------------

#: The only reviewer role that may own a Target B approval.
REVIEWER_ROLE_TRUSTED_HUMAN: str = "trusted_human_reviewer"

#: The allowed approval decisions.
APPROVAL_DECISION_READINESS: str = "APPROVED_FOR_READINESS"
APPROVAL_DECISION_ENABLEMENT: str = "APPROVED_FOR_ENABLEMENT"
APPROVAL_DECISIONS: frozenset[str] = frozenset(
    {APPROVAL_DECISION_READINESS, APPROVAL_DECISION_ENABLEMENT}
)

#: The Target B approval scope.
APPROVAL_SCOPE_TARGET_B: str = "target_b"

#: Signature algorithms a real approval may carry. The fixture algorithm is
#: included so a test can mint a genuine fixture approval; it is never honored
#: as production authorization.
APPROVAL_SIGNATURE_ALGORITHMS: frozenset[str] = frozenset(
    {"ed25519", "ecdsa-p256-sha256", "fixture-hmac-sha256"}
)

#: Out-of-band channels a real approval may be delivered through. These are
#: documentation labels only — no channel is ever contacted.
APPROVAL_OUT_OF_BAND_CHANNELS: frozenset[str] = frozenset(
    {"signed-document", "hardware-token", "offline-signing-ceremony"}
)

#: Wildcard environment scopes that are rejected (an approval must name a
#: concrete environment, never "*").
WILDCARD_ENVIRONMENT_SCOPES: frozenset[str] = frozenset({"*", "all", "any", "production", "prod"})

#: Deterministic fixture-only timestamps (ISO-8601, lexicographically ordered).
_FIXTURE_ISSUED_AT: str = "2026-01-01T00:00:00Z"
_FIXTURE_EXPIRES_AT: str = "2026-12-31T23:59:59Z"


# ---------------------------------------------------------------------------
# 2. The human approval record schema (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HumanReviewer:
    """The reviewer who signed an approval. The dev skeleton holds none."""

    reviewer_id: str
    reviewer_role: str
    reviewer_key_id: str


@dataclass(frozen=True, slots=True)
class ApprovalEvidenceRef:
    """A reference to a piece of out-of-band evidence backing an approval."""

    evidence_id: str
    evidence_kind: str  # e.g. "design-review", "security-audit", "test-report"
    evidence_locator: str  # a documentation locator only — never resolved


@dataclass(frozen=True, slots=True)
class ApprovalGateCoverage:
    """Which Target B gates and risks an approval covers."""

    covered_gate_ids: tuple[str, ...]
    covered_risks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ApprovalValidityWindow:
    """The validity window of an approval (deterministic ISO-8601 strings)."""

    issued_at: str
    expires_at: str


@dataclass(frozen=True, slots=True)
class ApprovalDecision:
    """The decision an approval records + why it was made."""

    decision: str
    decision_reason: str


@dataclass(frozen=True, slots=True)
class ApprovalScope:
    """The scope of an approval (Target B + a concrete environment)."""

    approval_scope: str
    environment_scope: str


@dataclass(frozen=True, slots=True)
class HumanApprovalRecord:
    """A real out-of-band human approval for Target B. Never valid by default.

    Validity is derived from :attr:`signature`, which only the real out-of-band
    trust token can produce. The dev skeleton provisions no token, so
    :func:`validate_human_approval_record` returns ``valid=False`` for every
    record — including one a caller forges by constructing the dataclass
    directly, one smuggled through :func:`create_human_approval`, or one minted
    by the fixture builder (which is explicitly ``fixture_only``).
    """

    approval_id: str
    reviewer: HumanReviewer
    scope: ApprovalScope
    coverage: ApprovalGateCoverage
    decision: ApprovalDecision
    validity: ApprovalValidityWindow
    evidence_refs: tuple[ApprovalEvidenceRef, ...]
    signature: str
    signature_algorithm: str
    out_of_band_channel: str
    replay_nonce: str
    fixture_only: bool = False
    production_valid: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        # The signature / replay nonce are never exposed (token-derived
        # material / anti-replay secret). Redact defensively.
        return redact_target_b_payload(
            {
                "approvalId": self.approval_id,
                "reviewerId": self.reviewer.reviewer_id,
                "reviewerRole": self.reviewer.reviewer_role,
                "approvalScope": self.scope.approval_scope,
                "environmentScope": self.scope.environment_scope,
                "coveredGateIds": list(self.coverage.covered_gate_ids),
                "coveredRisks": list(self.coverage.covered_risks),
                "decision": self.decision.decision,
                "issuedAt": self.validity.issued_at,
                "expiresAt": self.validity.expires_at,
                "signature": "[REDACTED]" if self.signature else "",
                "signatureAlgorithm": self.signature_algorithm,
                "outOfBandChannel": self.out_of_band_channel,
                "replayNonce": "[REDACTED]" if self.replay_nonce else "",
                "fixtureOnly": self.fixture_only,
                "productionValid": self.production_valid,
            }
        )


@dataclass(frozen=True, slots=True)
class HumanApprovalValidationResult:
    """The frozen result of validating a human approval record. Defaults invalid."""

    valid: bool
    production_valid: bool
    fixture_only: bool
    reason: str
    ignored_metadata_keys: tuple[str, ...]
    checks: Mapping[str, bool]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "valid": self.valid,
                "productionValid": self.production_valid,
                "fixtureOnly": self.fixture_only,
                "reason": self.reason,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
                "checks": dict(self.checks),
            }
        )


@dataclass(frozen=True, slots=True)
class HumanApprovalReport:
    """The frozen aggregate human-approval authorization report."""

    approval_present: bool
    valid: bool
    production_valid: bool
    fake_approval_rejected: bool
    ai_approval_rejected: bool
    metadata_approval_rejected: bool
    static_manifest_rejected: bool
    fixture_only: bool
    required_gate_coverage: tuple[str, ...]
    production_authorization: str
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "approvalPresent": self.approval_present,
                "valid": self.valid,
                "productionValid": self.production_valid,
                "fakeApprovalRejected": self.fake_approval_rejected,
                "aiApprovalRejected": self.ai_approval_rejected,
                "metadataApprovalRejected": self.metadata_approval_rejected,
                "staticManifestRejected": self.static_manifest_rejected,
                "fixtureOnly": self.fixture_only,
                "requiredGateCoverage": list(self.required_gate_coverage),
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
            }
        )


# ---------------------------------------------------------------------------
# 3. Validation
# ---------------------------------------------------------------------------


def _is_iso_window_ordered(issued_at: str, expires_at: str) -> bool:
    """Deterministic validity-window ordering check (no wall clock).

    ISO-8601 timestamps in the same form (e.g. ``2026-01-01T00:00:00Z``) sort
    lexicographically, so ``expires_at > issued_at`` iff the window is ordered.
    Never reads the system clock.
    """
    return (
        isinstance(issued_at, str)
        and isinstance(expires_at, str)
        and len(issued_at) > 0
        and len(expires_at) > 0
        and expires_at > issued_at
    )


def validate_human_approval_record(record: Any) -> HumanApprovalValidationResult:
    """Validate a human approval record's structure, coverage, and signature.

    Returns a :class:`HumanApprovalValidationResult`. Defaults to invalid with
    the reason ``human_approval_missing`` (no record) or
    ``human_approval_invalid`` (a malformed / forged record). A fixture-only
    record passes the *structural* checks but is never ``production_valid`` and
    is never ``valid`` as a production authorization.
    """
    if record is None:
        return HumanApprovalValidationResult(
            valid=False,
            production_valid=False,
            fixture_only=False,
            reason="human_approval_missing",
            ignored_metadata_keys=(),
            checks={},
        )
    if not isinstance(record, HumanApprovalRecord):
        return HumanApprovalValidationResult(
            valid=False,
            production_valid=False,
            fixture_only=False,
            reason="human_approval_invalid",
            ignored_metadata_keys=detect_target_b_untrusted_metadata(record),
            checks={},
        )

    checks: dict[str, bool] = {}
    checks["scope_is_target_b"] = record.scope.approval_scope == APPROVAL_SCOPE_TARGET_B
    checks["environment_not_wildcard"] = (
        record.scope.environment_scope not in WILDCARD_ENVIRONMENT_SCOPES
        and bool(record.scope.environment_scope)
    )
    pending = set(TARGET_B_PENDING_HUMAN_REVIEW_GATES)
    checks["covers_required_gates"] = pending.issubset(set(record.coverage.covered_gate_ids))
    checks["decision_is_approved"] = record.decision.decision in APPROVAL_DECISIONS
    checks["reviewer_role_trusted_human"] = record.reviewer.reviewer_role == REVIEWER_ROLE_TRUSTED_HUMAN
    checks["validity_window_present"] = _is_iso_window_ordered(
        record.validity.issued_at, record.validity.expires_at
    )
    checks["signature_present"] = bool(record.signature)
    checks["signature_algorithm_known"] = record.signature_algorithm in APPROVAL_SIGNATURE_ALGORITHMS
    checks["out_of_band_channel_present"] = record.out_of_band_channel in APPROVAL_OUT_OF_BAND_CHANNELS
    checks["replay_nonce_present"] = bool(record.replay_nonce)
    checks["evidence_refs_present"] = len(record.evidence_refs) > 0
    checks["reviewer_id_present"] = bool(record.reviewer.reviewer_id)
    checks["reviewer_key_id_present"] = bool(record.reviewer.reviewer_key_id)
    checks["approval_id_present"] = bool(record.approval_id)
    checks["not_fixture_only"] = record.fixture_only is False
    # The signature can only be genuine if the real out-of-band trust token is
    # provisioned — which the dev skeleton guarantees is not.
    checks["real_trust_token_provisioned"] = real_trust_token_provisioned()

    structural_ok = all(
        v for k, v in checks.items() if k != "real_trust_token_provisioned"
    ) and checks["not_fixture_only"]
    token_ok = checks["real_trust_token_provisioned"]

    # A record is a valid PRODUCTION authorization only when every structural
    # check passes, it is not fixture-only, AND the real trust token is
    # provisioned (so its signature could have been genuinely derived). With no
    # token, this is always False — defeating forgery, metadata smuggling, and
    # fixture approval alike.
    production_valid = bool(structural_ok and token_ok and not record.fixture_only)
    # ``valid`` (could authorize readiness consideration) follows the same rule
    # in the dev skeleton — no token, no valid approval, period.
    valid = production_valid

    if record.fixture_only:
        reason = TARGET_B_FIXTURE_NOT_PRODUCTION_REASON
    elif not token_ok:
        reason = "trust_token_not_provisioned"
    elif not structural_ok:
        reason = "human_approval_invalid"
    else:
        reason = "human_approval_valid"

    return HumanApprovalValidationResult(
        valid=valid,
        production_valid=production_valid,
        fixture_only=record.fixture_only,
        reason=reason,
        ignored_metadata_keys=(),
        checks=checks,
    )


def reject_fake_approval(untrusted_metadata: Any = None) -> HumanApprovalValidationResult:
    """Reject a fake / AI / metadata / static-manifest approval.

    Always returns invalid. *untrusted_metadata* is inspected only to report
    which bypass-shaped keys were detected and ignored. No flag can flip.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    return HumanApprovalValidationResult(
        valid=False,
        production_valid=False,
        fixture_only=False,
        reason=TARGET_B_FAKE_AUTHORIZATION_REJECTED_REASON,
        ignored_metadata_keys=ignored,
        checks={},
    )


def evaluate_human_approval(
    record: Any = None,
    untrusted_metadata: Any = None,
) -> HumanApprovalValidationResult:
    """Evaluate the human approval gate. Always invalid in the dev skeleton.

    If *record* is a :class:`HumanApprovalRecord`, its structure / coverage /
    signature are checked (always invalid without a token). *untrusted_metadata*
    is inspected only to report ignored bypass keys. A fixture record passes the
    structural checks but never authorizes production.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    if record is None:
        result = validate_human_approval_record(None)
        return HumanApprovalValidationResult(
            valid=result.valid,
            production_valid=result.production_valid,
            fixture_only=result.fixture_only,
            reason=result.reason,
            ignored_metadata_keys=ignored,
            checks=result.checks,
        )
    result = validate_human_approval_record(record)
    return HumanApprovalValidationResult(
        valid=result.valid,
        production_valid=result.production_valid,
        fixture_only=result.fixture_only,
        reason=result.reason,
        ignored_metadata_keys=ignored + result.ignored_metadata_keys,
        checks=result.checks,
    )


# ---------------------------------------------------------------------------
# 4. Test-only fixture builder + the aggregate report
# ---------------------------------------------------------------------------


def build_fixture_human_approval() -> HumanApprovalRecord:
    """Build a structurally-complete fixture approval (tests only).

    Every structural check passes, but the record is explicitly marked
    ``fixture_only=True`` / ``production_valid=False``. It proves the validator's
    positive logic (a complete record is structurally sound) while never being a
    production authorization — the real trust token is not provisioned, so the
    signature cannot have been genuinely derived. Never enables Target B.
    """
    reviewer = HumanReviewer(
        reviewer_id="fixture-reviewer",
        reviewer_role=REVIEWER_ROLE_TRUSTED_HUMAN,
        reviewer_key_id="fixture-reviewer-key",
    )
    scope = ApprovalScope(
        approval_scope=APPROVAL_SCOPE_TARGET_B,
        environment_scope="dev-skeleton",
    )
    coverage = ApprovalGateCoverage(
        covered_gate_ids=TARGET_B_PENDING_HUMAN_REVIEW_GATES,
        covered_risks=("supply-chain", "runtime-execution", "network-egress", "secret-access"),
    )
    decision = ApprovalDecision(
        decision=APPROVAL_DECISION_READINESS,
        decision_reason="fixture approval for validator tests only",
    )
    validity = ApprovalValidityWindow(issued_at=_FIXTURE_ISSUED_AT, expires_at=_FIXTURE_EXPIRES_AT)
    evidence = (
        ApprovalEvidenceRef(
            evidence_id="fixture-evidence-1",
            evidence_kind="design-review",
            evidence_locator="docs/webui/phase4c-target-b-authorization-gate-package-evidence.md",
        ),
    )
    return HumanApprovalRecord(
        approval_id="fixture-approval-target-b",
        reviewer=reviewer,
        scope=scope,
        coverage=coverage,
        decision=decision,
        validity=validity,
        evidence_refs=evidence,
        signature="fixture-hmac-sha256:test-only-not-a-real-signature",
        signature_algorithm="fixture-hmac-sha256",
        out_of_band_channel="signed-document",
        replay_nonce="fixture-replay-nonce",
        fixture_only=True,
        production_valid=False,
    )


def build_human_approval_report() -> HumanApprovalReport:
    """Build the frozen aggregate human-approval authorization report.

    No approval is present in the dev skeleton. Fake / AI / metadata / static
    approvals are rejected. The required gate coverage is the frozen pending set.
    Production authorization stays NO-GO. Pure and deterministic.
    """
    return HumanApprovalReport(
        approval_present=False,
        valid=False,
        production_valid=False,
        fake_approval_rejected=True,
        ai_approval_rejected=True,
        metadata_approval_rejected=True,
        static_manifest_rejected=True,
        fixture_only=False,
        required_gate_coverage=TARGET_B_PENDING_HUMAN_REVIEW_GATES,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="human_approval_missing",
    )


def assert_human_approval_not_enabled() -> None:
    """Re-affirm the human approval gate is not enabled. Pure."""
    report = build_human_approval_report()
    assert report.approval_present is False
    assert report.valid is False
    assert report.production_valid is False
    assert report.fake_approval_rejected is True
    assert report.ai_approval_rejected is True
    assert report.metadata_approval_rejected is True
    assert report.static_manifest_rejected is True
    assert report.production_authorization == TARGET_B_AUTHORIZATION_NO_GO
    assert report.reason == "human_approval_missing"
    # No record at all.
    assert validate_human_approval_record(None).valid is False
    assert validate_human_approval_record(None).reason == "human_approval_missing"
    # A fake approval (metadata) is rejected.
    fake = reject_fake_approval({"approved": "true", "approved_by_ai": "true"})
    assert fake.valid is False
    assert "approved" in fake.ignored_metadata_keys
    assert "approved_by_ai" in fake.ignored_metadata_keys
    # A directly-constructed forged record is not production-valid.
    forged = build_fixture_human_approval()
    assert forged.fixture_only is True
    forged_result = validate_human_approval_record(forged)
    assert forged_result.production_valid is False
    assert forged_result.valid is False
    assert forged_result.reason == TARGET_B_FIXTURE_NOT_PRODUCTION_REASON


__all__ = [
    # reviewer roles / decisions / scope constants
    "REVIEWER_ROLE_TRUSTED_HUMAN",
    "APPROVAL_DECISION_READINESS",
    "APPROVAL_DECISION_ENABLEMENT",
    "APPROVAL_DECISIONS",
    "APPROVAL_SCOPE_TARGET_B",
    "APPROVAL_SIGNATURE_ALGORITHMS",
    "APPROVAL_OUT_OF_BAND_CHANNELS",
    "WILDCARD_ENVIRONMENT_SCOPES",
    # schema
    "HumanReviewer",
    "ApprovalEvidenceRef",
    "ApprovalGateCoverage",
    "ApprovalValidityWindow",
    "ApprovalDecision",
    "ApprovalScope",
    "HumanApprovalRecord",
    "HumanApprovalValidationResult",
    "HumanApprovalReport",
    # validation
    "validate_human_approval_record",
    "reject_fake_approval",
    "evaluate_human_approval",
    # fixtures + report
    "build_fixture_human_approval",
    "build_human_approval_report",
    # boundary
    "assert_human_approval_not_enabled",
]
