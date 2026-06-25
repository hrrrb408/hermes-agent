"""Phase 4C — Target B P0 gate resolution evaluator (pure stdlib, fail-closed).

Layer 11 of the Phase 4C Target B authorization package. Defines the **P0
pending-gate resolution evaluator**: it decides whether the pending human-review
P0 gates (P0-15 / P0-16 / P0-18 / P0-19 / P0-22) can be considered resolved.

A pending gate can be resolved **only** by a combination of:

  - a valid human approval (signed out-of-band);
  - a valid trust token (provisioned out-of-band);
  - real evidence coverage for the gate.

Code evidence alone cannot resolve a gate. Metadata cannot resolve a gate. AI
cannot resolve a gate. A fake approval cannot resolve a gate. A fixture approval
cannot resolve production gates. Therefore:

  - ``resolved_count_delta = 0``
  - ``p0_resolved_count = 0``
  - ``pending_human_review = 5``

Pure / deterministic / stdlib-only. No filesystem access, no network, no
subprocess, no dynamic import, no eval / exec, no production access.

This module is **not** imported by ``dev_web_api``, so it adds no backend route
and changes no route governance counts.

Phase: 4C — Target B Authorization & Gate Resolution Package
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_target_b_authorization_common import (
    TARGET_B_AUTHORIZATION_NO_GO,
    detect_target_b_untrusted_metadata,
    redact_target_b_payload,
)
from hermes_cli.dev_web_target_b_common import (
    TARGET_B_PENDING_HUMAN_REVIEW_GATES,
    TARGET_B_P0_PARTIAL_EVIDENCE,
    TARGET_B_P0_PENDING_HUMAN_REVIEW,
    TARGET_B_P0_RESOLVED,
    TARGET_B_P0_TOTAL,
)
from hermes_cli.dev_web_target_b_human_approval import (
    HumanApprovalValidationResult,
    validate_human_approval_record,
)
from hermes_cli.dev_web_target_b_trust_token import (
    TrustTokenValidationResult,
    validate_trust_token_envelope,
)

# ---------------------------------------------------------------------------
# 1. The P0 gate resolution schema (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class P0GateResolutionInput:
    """The inputs to a P0 gate resolution evaluation.

    Every input defaults to "not authorized". A gate can only be resolved when
    the human approval is valid AND the trust token is valid AND evidence is
    present for that gate.
    """

    human_approval: Any  # HumanApprovalValidationResult or None
    trust_token: Any  # TrustTokenValidationResult or None
    evidence_gate_ids: tuple[str, ...]
    fixture_only: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "humanApprovalValid": _input_valid(self.human_approval),
                "trustTokenValid": _input_valid(self.trust_token),
                "evidenceGateIds": list(self.evidence_gate_ids),
                "fixtureOnly": self.fixture_only,
            }
        )


@dataclass(frozen=True, slots=True)
class P0GateCoverageRow:
    """One pending gate and its resolution state."""

    gate_id: str
    resolved: bool
    has_evidence: bool
    has_human_approval: bool
    has_trust_token: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "gateId": self.gate_id,
                "resolved": self.resolved,
                "hasEvidence": self.has_evidence,
                "hasHumanApproval": self.has_human_approval,
                "hasTrustToken": self.has_trust_token,
            }
        )


@dataclass(frozen=True, slots=True)
class P0GateResolutionResult:
    """The frozen result of a P0 gate resolution evaluation."""

    resolved_count_delta: int
    p0_resolved_count: int
    p0_total: int
    pending_human_review: int
    fixture_only: bool
    coverage: tuple[P0GateCoverageRow, ...]
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "resolvedCountDelta": self.resolved_count_delta,
                "p0ResolvedCount": self.p0_resolved_count,
                "p0Total": self.p0_total,
                "pendingHumanReview": self.pending_human_review,
                "fixtureOnly": self.fixture_only,
                "coverage": [r.to_safe_dict() for r in self.coverage],
                "reason": self.reason,
            }
        )


@dataclass(frozen=True, slots=True)
class P0GateCoverageReport:
    """The frozen aggregate P0 gate coverage report."""

    p0_total: int
    p0_resolved: int
    p0_partial_evidence: int
    pending_human_review: int
    pending_human_review_gates: tuple[str, ...]
    resolved_count_delta: int
    production_authorization: str
    reason: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_target_b_payload(
            {
                "p0Total": self.p0_total,
                "p0Resolved": self.p0_resolved,
                "p0PartialEvidence": self.p0_partial_evidence,
                "pendingHumanReview": self.pending_human_review,
                "pendingHumanReviewGates": list(self.pending_human_review_gates),
                "resolvedCountDelta": self.resolved_count_delta,
                "productionAuthorization": self.production_authorization,
                "reason": self.reason,
            }
        )


# ---------------------------------------------------------------------------
# 2. Helpers + evaluation
# ---------------------------------------------------------------------------


def _input_valid(result: Any) -> bool:
    """True iff *result* is a valid validation result (production-valid)."""
    if isinstance(result, (HumanApprovalValidationResult, TrustTokenValidationResult)):
        return bool(result.valid and not getattr(result, "fixture_only", False))
    return False


def build_p0_gate_resolution_input() -> P0GateResolutionInput:
    """Build the frozen default P0 gate resolution input (nothing authorized)."""
    return P0GateResolutionInput(
        human_approval=None,
        trust_token=None,
        evidence_gate_ids=(),
        fixture_only=False,
    )


def evaluate_pending_p0_gate_resolution(
    inputs: Any = None,
    untrusted_metadata: Any = None,
) -> P0GateResolutionResult:
    """Evaluate the pending P0 gate resolution. Delta always 0 today.

    A pending gate is resolved only when ALL of: the human approval is valid
    (non-fixture), the trust token is valid (non-fixture), and evidence is
    present for that gate. Code evidence alone, metadata, AI, fake approval, and
    fixture approval all leave the gate unresolved. *untrusted_metadata* is
    inspected only to report ignored bypass keys.
    """
    ignored = detect_target_b_untrusted_metadata(untrusted_metadata)
    _ = ignored  # diagnostic only — no flag can flip
    active = inputs if isinstance(inputs, P0GateResolutionInput) else build_p0_gate_resolution_input()

    human_valid = _input_valid(active.human_approval)
    token_valid = _input_valid(active.trust_token)
    evidence_set = set(g for g in active.evidence_gate_ids if isinstance(g, str))

    coverage_rows: list[P0GateCoverageRow] = []
    resolved = 0
    for gate in TARGET_B_PENDING_HUMAN_REVIEW_GATES:
        has_evidence = gate in evidence_set
        gate_resolved = bool(
            human_valid and token_valid and has_evidence and not active.fixture_only
        )
        if gate_resolved:
            resolved += 1
        coverage_rows.append(
            P0GateCoverageRow(
                gate_id=gate,
                resolved=gate_resolved,
                has_evidence=has_evidence,
                has_human_approval=human_valid,
                has_trust_token=token_valid,
            )
        )

    # The resolved delta is the number of gates that transitioned from pending to
    # resolved. In the dev skeleton this is always 0.
    return P0GateResolutionResult(
        resolved_count_delta=resolved,
        p0_resolved_count=TARGET_B_P0_RESOLVED,
        p0_total=TARGET_B_P0_TOTAL,
        pending_human_review=TARGET_B_P0_PENDING_HUMAN_REVIEW,
        fixture_only=active.fixture_only,
        coverage=tuple(coverage_rows),
        reason="p0_gates_require_real_human_approval_and_trust_token",
    )


def build_p0_gate_coverage_report() -> P0GateCoverageReport:
    """Build the frozen aggregate P0 gate coverage report.

    The 24 P0 gates: 0 resolved, 19 partial evidence, 5 pending human review.
    The resolved delta is 0. Production authorization stays NO-GO. Pure and
    deterministic.
    """
    return P0GateCoverageReport(
        p0_total=TARGET_B_P0_TOTAL,
        p0_resolved=TARGET_B_P0_RESOLVED,
        p0_partial_evidence=TARGET_B_P0_PARTIAL_EVIDENCE,
        pending_human_review=TARGET_B_P0_PENDING_HUMAN_REVIEW,
        pending_human_review_gates=TARGET_B_PENDING_HUMAN_REVIEW_GATES,
        resolved_count_delta=0,
        production_authorization=TARGET_B_AUTHORIZATION_NO_GO,
        reason="p0_gates_require_real_human_approval_and_trust_token",
    )


def assert_p0_not_resolved_without_authorization() -> None:
    """Re-affirm P0 gates cannot resolve without real authorization. Pure."""
    report = build_p0_gate_coverage_report()
    assert report.p0_total == 24
    assert report.p0_resolved == 0
    assert report.p0_partial_evidence == 19
    assert report.pending_human_review == 5
    assert report.resolved_count_delta == 0
    assert set(report.pending_human_review_gates) == {
        "P0-15",
        "P0-16",
        "P0-18",
        "P0-19",
        "P0-22",
    }
    # Default inputs resolve nothing.
    result = evaluate_pending_p0_gate_resolution()
    assert result.resolved_count_delta == 0
    assert result.p0_resolved_count == 0
    assert result.pending_human_review == 5
    for row in result.coverage:
        assert row.resolved is False
    # Even "evidence" for every gate cannot resolve them without a real approval
    # + a real token.
    inputs = P0GateResolutionInput(
        human_approval=None,
        trust_token=None,
        evidence_gate_ids=TARGET_B_PENDING_HUMAN_REVIEW_GATES,
    )
    result = evaluate_pending_p0_gate_resolution(inputs)
    assert result.resolved_count_delta == 0
    # Smuggled metadata cannot resolve them either.
    smuggled = evaluate_pending_p0_gate_resolution(
        untrusted_metadata={"p0_resolved": "true", "approved": "true"},
    )
    assert smuggled.resolved_count_delta == 0


__all__ = [
    # schema
    "P0GateResolutionInput",
    "P0GateCoverageRow",
    "P0GateResolutionResult",
    "P0GateCoverageReport",
    # evaluation
    "build_p0_gate_resolution_input",
    "evaluate_pending_p0_gate_resolution",
    "build_p0_gate_coverage_report",
    # boundary
    "assert_p0_not_resolved_without_authorization",
]
