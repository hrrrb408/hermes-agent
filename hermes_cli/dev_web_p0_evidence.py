"""Phase 3E–3H P0 Gate Evidence Aggregator (dev-only, pure stdlib).

A **fail-closed** evidence model for the 24 inherited P0 gates
(``PHASE-3F-P0-GATES-001``). It does three things and only three things:

  1. **Represent** the 24 gates with their theme, classification, reviewer,
     resolution requirement, and the code/test evidence that exists today.
  2. **Classify** each gate into a conservative status taxonomy — and prove
     that **no gate is ever classified ``resolved``** by automation. Resolution
     requires a valid :class:`HumanApprovalRecord`, and the dev skeleton holds
     **no** out-of-band trust token, so no valid approval can ever be created
     from request metadata.
  3. **Refuse** every authorization bypass: implementation authorization,
     Phase 3I, real runtime, new route, and production rollout stay NO-GO no
     matter what untrusted metadata is supplied.

It also ships four dev-only evaluators that turn the *descriptive* gaps behind
the remaining 9 governance-only gates into *code* evidence (still partial —
never resolved):

  - :func:`classify_plugin_source` — supply-chain provenance (P0-05 / P0-18):
    descriptor-only / local-static sources are readable as metadata only;
    every executable / remote / marketplace / generated source is denied.
  - :func:`evaluate_route_exception` — route-governance exception (P0-16): a
    requested route change is detected and flagged
    ``route_exception_required``, but ``route_exception_approved`` is always
    False and cannot be flipped by metadata.
  - :func:`evaluate_rollback_readiness` — rollback / incident (P0-21 / P0-23):
    cleanup targets must be temp/fake (a production-looking target is denied);
    a missing or fake incident owner leaves readiness unresolved.
  - :func:`classify_evidence_quality` — reproducibility (P0-24): evidence with
    a test command can be ``candidate_for_review``; without one it is partial;
    nothing becomes resolved without human approval.

Hard guarantees (frozen):

  - Pure / deterministic / stdlib-only. No dynamic import, no network, no
    subprocess, no file I/O, no real secret read, no production access.
  - ``resolved_count`` is **always 0** in this skeleton. The summary's
    implementation-authorization / Phase 3I / real-runtime / new-route /
    production-rollout flags are frozen NO-GO / not-authorized.
  - Request metadata is **untrusted by construction**: every public evaluator
    that accepts a metadata mapping detects and ignores bypass-shaped keys.

Phase: 3E–3H — Remaining P0 Gate Reduction
Status: implemented (dev-only evidence model). NOT a signoff, NOT a closeout,
        NOT an authorization. Resolves nothing on its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from hermes_cli.dev_web_sandbox_guards import redact_sandbox_payload

# ---------------------------------------------------------------------------
# 1. Status taxonomy
# ---------------------------------------------------------------------------

#: No code or test evidence at all.
GATE_STATUS_NO_EVIDENCE = "no_evidence"
#: Evidence is policy / governance text only — no executable code backing it.
GATE_STATUS_GOVERNANCE_ONLY = "governance_only"
#: Real code and/or test evidence exists, but the gate is not approved.
GATE_STATUS_PARTIAL_EVIDENCE = "partial_evidence"
#: Strong, reproducible test evidence exists; ready for a human reviewer to
#: look at — but explicitly NOT resolved.
GATE_STATUS_CANDIDATE_FOR_REVIEW = "candidate_for_review"
#: The gate can only advance via an explicit human / project-owner action
#: (authorization, signoff, plan approval). No code can move it.
GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW = "blocked_by_human_review"
#: Reviewed and intentionally left open / declined.
GATE_STATUS_NOT_RESOLVED = "not_resolved"
#: Fully resolved + approved. **Never auto-assignable** — requires a valid
#: :class:`HumanApprovalRecord`, which the dev skeleton cannot produce.
GATE_STATUS_RESOLVED = "resolved"

ALL_GATE_STATUSES: frozenset[str] = frozenset(
    {
        GATE_STATUS_NO_EVIDENCE,
        GATE_STATUS_GOVERNANCE_ONLY,
        GATE_STATUS_PARTIAL_EVIDENCE,
        GATE_STATUS_CANDIDATE_FOR_REVIEW,
        GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW,
        GATE_STATUS_NOT_RESOLVED,
        GATE_STATUS_RESOLVED,
    }
)

#: Statuses that count as "still unresolved" (not approved).
UNRESOLVED_STATUSES: frozenset[str] = ALL_GATE_STATUSES - {GATE_STATUS_RESOLVED}

# ---------------------------------------------------------------------------
# 2. Frozen NO-GO / not-authorized flags (cannot be flipped by metadata)
# ---------------------------------------------------------------------------

IMPLEMENTATION_AUTHORIZATION = "NO-GO"
PHASE_3I_AUTHORIZED: bool = False
REAL_RUNTIME = "NO-GO"
NEW_ROUTE = "NO-GO"
PRODUCTION_ROLLOUT = "NO-GO"

#: Reviewer roles that own each gate (mirrors phase-3f-p0-gate-consolidation).
REVIEWER_SECURITY = "security reviewer"
REVIEWER_PROJECT_OWNER = "project owner"
REVIEWER_ROUTE_GOVERNANCE = "route-governance reviewer"
REVIEWER_AUDIT = "audit reviewer"
REVIEWER_PRODUCTION_SAFETY = "production safety reviewer"
REVIEWER_CAPABILITY = "capability reviewer"
REVIEWER_IMPLEMENTATION = "implementation owner + security reviewer"

# ---------------------------------------------------------------------------
# 3. Gate evidence record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class P0GateEvidence:
    """One inherited P0 gate + the evidence that exists for it today."""

    gate_id: str
    theme: str
    classification: str
    requires_human_approval: bool
    reviewer: str
    resolution_requirement: str
    code_evidence: tuple[str, ...] = ()
    test_evidence: tuple[str, ...] = ()
    remaining_gap: str = ""

    def is_resolved(self) -> bool:
        return self.classification == GATE_STATUS_RESOLVED

    def to_safe_dict(self) -> dict[str, Any]:
        payload = {
            "gateId": self.gate_id,
            "theme": self.theme,
            "classification": self.classification,
            "requiresHumanApproval": self.requires_human_approval,
            "reviewer": self.reviewer,
            "resolutionRequirement": self.resolution_requirement,
            "codeEvidence": list(self.code_evidence),
            "testEvidence": list(self.test_evidence),
            "remainingGap": self.remaining_gap,
            "resolved": self.is_resolved(),
        }
        # Defense-in-depth: never let a raw secret / production path reach a
        # caller even if a future editor embeds one in gap text.
        return redact_sandbox_payload(payload)


# ---------------------------------------------------------------------------
# 4. The frozen 24-gate registry
# ---------------------------------------------------------------------------
#
# Themes are taken verbatim from docs/webui/phase-3f-p0-gate-consolidation.md
# and cross-checked against phase-3g-p0-gate-resolution-review.md. No gate is
# classified ``resolved``. The 15 already-partial gates keep PARTIAL_EVIDENCE;
# the 9 previously governance-only gates are now classified more precisely
# (PARTIAL_EVIDENCE where this codebase supplies real code evidence,
# BLOCKED_BY_HUMAN_REVIEW where only a human/project-owner action can advance
# the gate). Gate text deliberately avoids literal production path strings.

_GATES_RAW: tuple[tuple[Any, ...], ...] = (
    # (gate_id, theme, classification, requires_human, reviewer,
    #  resolution_requirement, code_evidence, test_evidence, remaining_gap)
    ("P0-01", "Sandbox model", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_SECURITY,
     "approved sandbox model + sandbox trust proof",
     ("dev_web_sandbox_proof.py",),
     ("test_dev_web_phase_3h_sandbox_proof_skeleton.py", "test_dev_web_phase_3e_h_p0_evidence_hardening.py"),
     "skeleton is not an approved runtime sandbox model"),
    ("P0-02", "Process isolation", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_SECURITY,
     "approved process-isolation model",
     ("dev_web_sandbox_policy.py (process.spawn denied)",),
     ("test_dev_web_phase_3h_sandbox_proof_skeleton.py",),
     "no approved process-isolation model"),
    ("P0-03", "Filesystem boundary", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_SECURITY,
     "approved filesystem-boundary model",
     ("dev_web_safety_baseline.py", "dev_web_sandbox_guards.py"),
     ("test_dev_web_phase_3e_h_safety_baseline.py", "test_dev_web_phase_3e_h_p0_evidence_hardening.py"),
     "boundary enforced; not an approved model"),
    ("P0-04", "Network boundary", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_SECURITY,
     "approved network-boundary model",
     ("dev_web_sandbox_guards.py (network deny)",),
     ("test_dev_web_phase_3h_sandbox_proof_skeleton.py", "test_dev_web_phase_3e_h_p0_evidence_hardening.py"),
     "intent-level deny only; no approved network policy"),
    ("P0-05", "Supply-chain policy", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_SECURITY,
     "approved supply-chain policy + supply-chain trust proof",
     ("dev_web_sandbox_guards.py", "dev_web_p0_evidence.py (classify_plugin_source)"),
     ("test_dev_web_phase_3e_h_remaining_p0_reduction.py",),
     "provenance classifier denies untrusted sources; no approved supply-chain policy"),
    ("P0-06", "Permission model", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_CAPABILITY,
     "approved permission model",
     ("dev_web_sandbox_policy.py (capability default-deny)",),
     ("test_dev_web_phase_3h_sandbox_proof_skeleton.py", "test_dev_web_phase_3e_h_p0_evidence_hardening.py"),
     "labels grant nothing at runtime; no real permission model"),
    ("P0-07", "Audit / redaction model", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_AUDIT,
     "approved audit / redaction model",
     ("dev_web_sandbox_audit.py", "dev_web_sandbox_guards.py"),
     ("test_dev_web_phase_3h_sandbox_proof_skeleton.py", "test_dev_web_phase_3e_h_p0_evidence_hardening.py"),
     "in-memory only; no durable audit approved"),
    ("P0-08", "Kill switch", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_PRODUCTION_SAFETY,
     "approved kill switch",
     ("dev_web_sandbox_policy.py (evaluate_kill_switch)",),
     ("test_dev_web_phase_3h_sandbox_proof_skeleton.py", "test_dev_web_phase_3e_h_p0_evidence_hardening.py"),
     "dev-only flag; not a production kill switch"),
    ("P0-09", "Production isolation", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_PRODUCTION_SAFETY,
     "approved production-isolation model",
     ("dev_web_safety_baseline.py (string-only)",),
     ("test_dev_web_phase_3e_h_safety_baseline.py",),
     "production referenced only as denial target; not an approved boundary"),
    ("P0-10", "Secret handling ambiguity", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_SECURITY,
     "unambiguous secret handling",
     ("dev_web_sandbox_guards.py (redaction)",),
     ("test_dev_web_phase_3h_sandbox_proof_skeleton.py", "test_dev_web_phase_3e_h_p0_evidence_hardening.py"),
     "redaction is defense-in-depth; no approved secret model; no real secret read"),
    ("P0-11", "Filesystem / network ambiguity", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_SECURITY,
     "unambiguous filesystem / network access",
     ("dev_web_safety_baseline.py", "dev_web_sandbox_guards.py"),
     ("test_dev_web_phase_3e_h_p0_evidence_hardening.py",),
     "pure deterministic evaluators; not approved by reviewers"),
    ("P0-12", "Unapproved execution path", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_SECURITY,
     "no unapproved execution path",
     ("dev_web_sandbox_policy.py (descriptor-only)",),
     ("test_dev_web_phase_3h_sandbox_proof_skeleton.py", "test_dev_web_phase_3e_h_p0_evidence_hardening.py"),
     "proven absent; remains not-introduced"),
    ("P0-13", "Production impact", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_PRODUCTION_SAFETY,
     "no production impact",
     ("dev_web_safety_baseline.py",),
     ("test_dev_web_phase_3e_h_safety_baseline.py", "test_dev_web_phase_3e_h_p0_evidence_hardening.py"),
     "none introduced"),
    ("P0-14", "Route governance", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_ROUTE_GOVERNANCE,
     "route-governance approval for any new route",
     ("dev_web_safety_baseline.py (34/34/5/0/1/1)",),
     ("test_dev_web_phase_3e_h_safety_baseline.py", "test_dev_web_phase_3e_h_p0_evidence_hardening.py"),
     "baseline frozen unchanged; no exception approval granted"),
    ("P0-15", "No implementation authorization", GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW, True, REVIEWER_PROJECT_OWNER,
     "explicit implementation authorization after gates clear",
     ("dev_web_p0_evidence.py (proof authorization cannot be automated)",),
     ("test_dev_web_phase_3e_h_remaining_p0_reduction.py",),
     "requires project-owner authorization; cannot be granted by code or metadata"),
    ("P0-16", "No runtime endpoint authorization", GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW, True, REVIEWER_ROUTE_GOVERNANCE,
     "explicit runtime endpoint authorization",
     ("dev_web_p0_evidence.py (route exception evaluator)",),
     ("test_dev_web_phase_3e_h_remaining_p0_reduction.py",),
     "no runtime endpoint wired; endpoint authorization requires route-governance reviewer"),
    ("P0-17", "No runtime artifact storage authorization", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_AUDIT,
     "approved runtime artifact storage model",
     ("dev_web_sandbox_audit.py (in-memory only)",),
     ("test_dev_web_phase_3h_sandbox_proof_skeleton.py", "test_dev_web_phase_3e_h_p0_evidence_hardening.py"),
     "no persistent artifact store exists; approved storage model still required"),
    ("P0-18", "No plugin source trust decision", GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW, True, REVIEWER_SECURITY,
     "explicit plugin source trust decision",
     ("dev_web_p0_evidence.py (classify_plugin_source deny-by-default)",),
     ("test_dev_web_phase_3e_h_remaining_p0_reduction.py",),
     "deny-by-default provenance; an explicit trust decision requires security reviewer"),
    ("P0-19", "No worker lifecycle approval", GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW, True, REVIEWER_SECURITY,
     "approved worker lifecycle",
     ("dev_web_sandbox_policy.py (process.spawn denied)",),
     ("test_dev_web_phase_3h_sandbox_proof_skeleton.py",),
     "no worker lifecycle code; approval requires security reviewer"),
    ("P0-20", "No failure-mode approval", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_SECURITY,
     "approved failure-mode behavior",
     ("dev_web_sandbox_policy.py", "dev_web_sandbox_audit.py (fail-closed)",),
     ("test_dev_web_phase_3h_sandbox_proof_skeleton.py", "test_dev_web_phase_3e_h_p0_evidence_hardening.py"),
     "fail-closed defaults implemented; not an approved failure-mode plan"),
    ("P0-21", "No rollback plan", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_PRODUCTION_SAFETY,
     "approved rollback / incident-response plan for implementation",
     ("dev_web_p0_evidence.py (evaluate_rollback_readiness)",),
     ("test_dev_web_phase_3e_h_remaining_p0_reduction.py",),
     "rollback readiness evaluator uses temp/fake targets only; approved plan required"),
    ("P0-22", "No human review signoff", GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW, True, REVIEWER_PROJECT_OWNER,
     "human review signoff for implementation",
     ("dev_web_p0_evidence.py (HumanApprovalRecord cannot be faked)",),
     ("test_dev_web_phase_3e_h_remaining_p0_reduction.py",),
     "signoff not started; cannot be synthesized from metadata"),
    ("P0-23", "No incident response plan", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_PRODUCTION_SAFETY,
     "approved incident-response plan",
     ("dev_web_p0_evidence.py (incident owner + redaction)",),
     ("test_dev_web_phase_3e_h_remaining_p0_reduction.py",),
     "incident owner/redaction helper added; approved plan required"),
    ("P0-24", "No test strategy approval", GATE_STATUS_PARTIAL_EVIDENCE, True, REVIEWER_IMPLEMENTATION,
     "approved test strategy",
     ("tests/test_dev_web_phase_3e_h_*.py",),
     ("test_dev_web_phase_3e_h_safety_baseline.py", "test_dev_web_phase_3h_sandbox_proof_skeleton.py",
      "test_dev_web_phase_3e_h_p0_evidence_hardening.py", "test_dev_web_phase_3e_h_remaining_p0_reduction.py"),
     "test strategy not approved by reviewers"),
)


def _build_gates() -> tuple[P0GateEvidence, ...]:
    return tuple(
        P0GateEvidence(
            gate_id=str(row[0]),
            theme=str(row[1]),
            classification=str(row[2]),
            requires_human_approval=bool(row[3]),
            reviewer=str(row[4]),
            resolution_requirement=str(row[5]),
            code_evidence=tuple(row[6]) if row[6] else (),
            test_evidence=tuple(row[7]) if row[7] else (),
            remaining_gap=str(row[8]),
        )
        for row in _GATES_RAW
    )


#: The frozen 24-gate registry. Immutable; the only source of gate truth.
GATES: tuple[P0GateEvidence, ...] = _build_gates()

#: Gate IDs that previously were "governance-only / unresolved" and that this
#: evidence model classifies more precisely.
REMAINING_GATE_IDS: tuple[str, ...] = (
    "P0-05",
    "P0-15",
    "P0-16",
    "P0-17",
    "P0-18",
    "P0-19",
    "P0-21",
    "P0-22",
    "P0-23",
)

assert len(GATES) == 24, "P0 gate registry must contain exactly 24 gates"
assert len({g.gate_id for g in GATES}) == 24, "P0 gate ids must be unique"
assert all(not g.is_resolved() for g in GATES), "no P0 gate may start resolved"

# ---------------------------------------------------------------------------
# 5. Human approval (cannot be faked from request metadata)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HumanApprovalRecord:
    """An out-of-band human approval for one gate.

    Validity is derived from :attr:`signature`, which only the real out-of-band
    trust token can produce. The dev skeleton holds **no** such token
    (:data:`_REAL_TRUST_TOKEN` is None), so :func:`is_approval_valid` returns
    False for *every* record — including one a caller tries to forge by
    constructing the dataclass directly. That is what keeps
    ``resolved_count`` at 0.
    """

    gate_id: str
    reviewer: str
    decision: str
    signature: str = ""

    def is_valid(self) -> bool:
        return is_approval_valid(self)

    def to_safe_dict(self) -> dict[str, Any]:
        # The signature is never exposed (it is token-derived material).
        return redact_sandbox_payload(
            {
                "gateId": self.gate_id,
                "reviewer": self.reviewer,
                "decision": self.decision,
                "valid": self.is_valid(),
            }
        )


#: The real, out-of-band trust token that signs a genuine human approval. It is
#: **deliberately None** in the dev skeleton: it would be provisioned by a
#: separate, auditable human process that is explicitly out of scope here.
#: Because it is None, no signature can be valid, so no approval constructed
#: from request metadata — or forged by direct dataclass construction — can
#: ever resolve a gate.
_REAL_TRUST_TOKEN: str | None = None


def _expected_approval_signature(gate_id: str, reviewer: str) -> str | None:
    """The signature a genuine human approval carries.

    Derived from the real out-of-band trust token. Returns None when no token
    is provisioned (the dev skeleton), which makes every approval invalid by
    construction.
    """
    if _REAL_TRUST_TOKEN is None:
        return None
    return f"{_REAL_TRUST_TOKEN}:{gate_id}:{reviewer}"


def create_human_approval(
    gate_id: Any,
    reviewer: Any,
    decision: Any,
    *,
    trust_token: Any = None,
) -> HumanApprovalRecord:
    """Construct a (always-invalid in the dev skeleton) human approval record.

    A non-empty :attr:`signature` is attached **only** when *trust_token*
    equals the real out-of-band token. Since :data:`_REAL_TRUST_TOKEN` is None,
    every call — including ones that try to smuggle ``approved`` / ``reviewer``
    / ``signoff`` through *trust_token* — yields a record whose signature is
    empty and therefore invalid.
    """
    gate_id_text = gate_id if isinstance(gate_id, str) else "<invalid>"
    reviewer_text = reviewer if isinstance(reviewer, str) else "<invalid>"
    decision_text = decision if isinstance(decision, str) else "<invalid>"
    signature = ""
    if (
        _REAL_TRUST_TOKEN is not None
        and isinstance(trust_token, str)
        and trust_token == _REAL_TRUST_TOKEN
    ):
        signature = _expected_approval_signature(gate_id_text, reviewer_text) or ""
    return HumanApprovalRecord(
        gate_id=gate_id_text,
        reviewer=reviewer_text,
        decision=decision_text,
        signature=signature,
    )


def is_approval_valid(record: Any) -> bool:
    """True iff *record* is a valid :class:`HumanApprovalRecord`.

    Validity requires the real trust token to exist AND the record's signature
    to match the expected token-derived signature. With no token provisioned
    (the dev skeleton), this is always False — defeating both metadata smuggling
    and direct dataclass forgery.
    """
    if not isinstance(record, HumanApprovalRecord):
        return False
    expected = _expected_approval_signature(record.gate_id, record.reviewer)
    if expected is None:
        return False
    return bool(record.signature) and record.signature == expected


# ---------------------------------------------------------------------------
# 6. Untrusted-metadata detection (authorization bypass prevention)
# ---------------------------------------------------------------------------

#: Metadata keys that look like an authorization bypass attempt. Detected and
#: ignored by every public evaluator. The list is intentionally broad: every
#: approval / authorization / signoff / trust-token / route-exception /
#: production / runtime / phase-3I / resolved variant a smuggler might invent is
#: reported as ignored. Detection is diagnostic only — the authorization flags
#: are frozen constants regardless, so an undetected variant still authorizes
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
        "phase_3i_authorized",
        "phase3iAuthorized",
        "phase_3i",
        "phase3i",
        "route_exception_approved",
        "routeExceptionApproved",
        "route_change_approved",
        "routeChangeApproved",
        "production_approved",
        "productionApproved",
        "production_rollout_approved",
        "productionRolloutApproved",
        "real_runtime_authorized",
        "realRuntimeAuthorized",
        "runtime_authorized",
        "runtimeAuthorized",
        "real_runtime",
        "reviewer",
        "review",
        "review_board_decision",
        "reviewBoardDecision",
        "human_signoff",
        "humanSignoff",
        "signoff",
        "signed_off",
        "signedOff",
        "signed_by",
        "signedBy",
        "signoff_id",
        "signoffId",
        "owner",
        "project_owner",
        "projectOwner",
        "operator",
        "trust",
        "trusted",
        "trust_token",
        "trustToken",
        "approval_token",
        "approvalToken",
        "approval_id",
        "approvalId",
        "real_trust_token",
        "realTrustToken",
        "bypass",
        "override",
        "force",
        "force_allow",
        "forceAllow",
        "skip_review",
        "p0_resolved",
        "p0Resolved",
        "resolved_ids",
        "resolvedIds",
        "resolved",
        "approved_by_ai",
        "approvedByAi",
        "approved_by_human",
        "approvedByHuman",
        "token",
        "secret",
        "password",
        "apikey",
        "api_key",
    }
)


def detect_untrusted_metadata(metadata: Any) -> tuple[str, ...]:
    """Return the sorted bypass-shaped keys present in *metadata*.

    Pure inspection — the keys are reported so a caller/audit can record that a
    bypass attempt was detected and ignored. Never raises.
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


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    """The frozen authorization verdict. Unaffected by request metadata."""

    implementation_authorization: str
    phase_3i_authorized: bool
    real_runtime: str
    new_route: str
    production_rollout: str
    ignored_metadata_keys: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "implementationAuthorization": self.implementation_authorization,
                "phase3iAuthorized": self.phase_3i_authorized,
                "realRuntime": self.real_runtime,
                "newRoute": self.new_route,
                "productionRollout": self.production_rollout,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
                "reasons": list(self.reasons),
                "redactionApplied": True,
            }
        )


def evaluate_authorization_request(untrusted_metadata: Any = None) -> AuthorizationDecision:
    """Return the frozen authorization verdict, ignoring any metadata.

    Every NO-GO / not-authorized flag is a frozen constant; *untrusted_metadata*
    is inspected only to report which bypass-shaped keys were detected and
    ignored. Implementation Authorization cannot become GO, Phase 3I cannot
    become authorized, no matter what is supplied.
    """
    ignored = detect_untrusted_metadata(untrusted_metadata)
    reasons: list[str] = ["authorization_requires_explicit_human_action"]
    if ignored:
        reasons.append("untrusted_metadata_ignored")
    return AuthorizationDecision(
        implementation_authorization=IMPLEMENTATION_AUTHORIZATION,
        phase_3i_authorized=PHASE_3I_AUTHORIZED,
        real_runtime=REAL_RUNTIME,
        new_route=NEW_ROUTE,
        production_rollout=PRODUCTION_ROLLOUT,
        ignored_metadata_keys=ignored,
        reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# 7. P0 evidence summary (fail-closed: resolved_count is always 0)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class P0EvidenceSummary:
    """Conservative aggregate of the 24 P0 gates."""

    total_gates: int
    resolved_count: int
    partial_evidence_count: int
    candidate_for_review_count: int
    blocked_by_human_review_count: int
    governance_only_count: int
    no_evidence_count: int
    implementation_authorization: str
    phase_3i_authorized: bool
    real_runtime: str
    new_route: str
    production_rollout: str
    ignored_metadata_keys: tuple[str, ...]
    gates: tuple[P0GateEvidence, ...] = ()

    @property
    def unresolved_count(self) -> int:
        return self.total_gates - self.resolved_count

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "totalGates": self.total_gates,
                "resolvedCount": self.resolved_count,
                "partialEvidenceCount": self.partial_evidence_count,
                "candidateForReviewCount": self.candidate_for_review_count,
                "blockedByHumanReviewCount": self.blocked_by_human_review_count,
                "governanceOnlyCount": self.governance_only_count,
                "noEvidenceCount": self.no_evidence_count,
                "unresolvedCount": self.unresolved_count,
                "implementationAuthorization": self.implementation_authorization,
                "phase3iAuthorized": self.phase_3i_authorized,
                "realRuntime": self.real_runtime,
                "newRoute": self.new_route,
                "productionRollout": self.production_rollout,
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
                "gates": [g.to_safe_dict() for g in self.gates],
                "redactionApplied": True,
            }
        )


def _summarize(
    gates: tuple[P0GateEvidence, ...],
    *,
    ignored_metadata_keys: tuple[str, ...],
    resolved_ids: frozenset[str],
) -> P0EvidenceSummary:
    """Build the summary. *resolved_ids* is empty unless valid approvals exist."""
    partial = 0
    candidate = 0
    blocked = 0
    governance = 0
    no_evidence = 0
    resolved = 0
    effective_gates: list[P0GateEvidence] = []
    for gate in gates:
        if gate.gate_id in resolved_ids:
            # A valid human approval (impossible in the dev skeleton) would
            # flip exactly this gate to resolved. With no valid approval this
            # branch is unreachable.
            effective = P0GateEvidence(
                gate_id=gate.gate_id,
                theme=gate.theme,
                classification=GATE_STATUS_RESOLVED,
                requires_human_approval=gate.requires_human_approval,
                reviewer=gate.reviewer,
                resolution_requirement=gate.resolution_requirement,
                code_evidence=gate.code_evidence,
                test_evidence=gate.test_evidence,
                remaining_gap="resolved_by_valid_human_approval",
            )
            resolved += 1
        else:
            effective = gate
            if gate.classification == GATE_STATUS_PARTIAL_EVIDENCE:
                partial += 1
            elif gate.classification == GATE_STATUS_CANDIDATE_FOR_REVIEW:
                candidate += 1
            elif gate.classification == GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW:
                blocked += 1
            elif gate.classification == GATE_STATUS_GOVERNANCE_ONLY:
                governance += 1
            elif gate.classification == GATE_STATUS_NO_EVIDENCE:
                no_evidence += 1
        effective_gates.append(effective)
    return P0EvidenceSummary(
        total_gates=len(gates),
        resolved_count=resolved,
        partial_evidence_count=partial,
        candidate_for_review_count=candidate,
        blocked_by_human_review_count=blocked,
        governance_only_count=governance,
        no_evidence_count=no_evidence,
        implementation_authorization=IMPLEMENTATION_AUTHORIZATION,
        phase_3i_authorized=PHASE_3I_AUTHORIZED,
        real_runtime=REAL_RUNTIME,
        new_route=NEW_ROUTE,
        production_rollout=PRODUCTION_ROLLOUT,
        ignored_metadata_keys=ignored_metadata_keys,
        gates=tuple(effective_gates),
    )


def evaluate_p0_evidence(
    *,
    approvals: Any = None,
    untrusted_metadata: Any = None,
) -> P0EvidenceSummary:
    """Evaluate the 24 P0 gates. Fail-closed: ``resolved_count`` is always 0.

    *approvals* may contain :class:`HumanApprovalRecord` objects, but only
    *valid* ones advance a gate — and the dev skeleton can produce none (see
    :func:`create_human_approval`). *untrusted_metadata* is inspected only to
    report ignored bypass keys; it cannot change any classification or flag.
    """
    ignored = detect_untrusted_metadata(untrusted_metadata)
    if untrusted_metadata is not None and isinstance(untrusted_metadata, Mapping):
        # An approval smuggled inside metadata is untrusted by construction.
        pass

    resolved_ids: set[str] = set()
    if approvals:
        for record in approvals:
            if is_approval_valid(record) and isinstance(record.gate_id, str):
                resolved_ids.add(record.gate_id)
    # resolved_ids is empty in the dev skeleton (no valid approval possible).
    return _summarize(
        GATES,
        ignored_metadata_keys=ignored,
        resolved_ids=frozenset(resolved_ids),
    )


# ---------------------------------------------------------------------------
# 8. Supply-chain provenance classifier (P0-05 / P0-18)
# ---------------------------------------------------------------------------

#: Source types that may be READ as static metadata (never executed / trusted).
ALLOWED_SOURCE_TYPES: frozenset[str] = frozenset(
    {
        "descriptor_only",
        "local_static_descriptor",
        "bundled_descriptor",
    }
)

#: Source types unconditionally denied — each maps to a precise reason.
_DENIED_SOURCE_TYPES: dict[str, str] = {
    "remote_registry": "remote_registry_denied",
    "marketplace": "marketplace_denied",
    "external_fetch": "external_fetch_denied",
    "external_download": "external_fetch_denied",
    "provider_generated": "provider_generated_denied",
    "llm_generated": "llm_generated_denied",
    "ai_generated": "llm_generated_denied",
    "generated": "generated_plugin_denied",
    "unreviewed_local_executable": "unreviewed_local_executable_denied",
    "local_executable": "unreviewed_local_executable_denied",
    "unknown": "unknown_source_denied",
}

#: Stable reason tokens the provenance classifier may emit.
PROVENANCE_REASONS: frozenset[str] = frozenset(
    {
        "provenance_unknown_source",
        "remote_registry_denied",
        "marketplace_denied",
        "external_fetch_denied",
        "provider_generated_denied",
        "llm_generated_denied",
        "generated_plugin_denied",
        "unreviewed_local_executable_denied",
        "unknown_source_denied",
        "executable_field_denied",
    }
)


@dataclass(frozen=True, slots=True)
class ProvenanceDecision:
    """Supply-chain provenance decision for a plugin source."""

    source_type: str
    metadata_readable: bool
    execution_trusted: bool
    reasons: tuple[str, ...]
    note: str

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "sourceType": self.source_type,
                "metadataReadable": self.metadata_readable,
                "executionTrusted": self.execution_trusted,
                "reasons": list(self.reasons),
                "note": self.note,
                "redactionApplied": True,
            }
        )


def _normalize_source_type(raw: Any) -> str:
    if not isinstance(raw, str):
        return "unknown"
    text = raw.strip().lower().replace("-", "_").replace(" ", "_")
    return text or "unknown"


def classify_plugin_source(source: Any) -> ProvenanceDecision:
    """Classify a plugin source. Default-deny; never trusts for execution.

    ``descriptor_only`` / ``local_static_descriptor`` sources are *readable as
    metadata* (``metadata_readable=True``) but **never** trusted for execution
    (``execution_trusted=False``). Every remote / marketplace / external /
    generated / unreviewed-executable / unknown source is denied outright. A
    source carrying any executable field is denied even if its declared type is
    otherwise allowed.
    """
    if not isinstance(source, Mapping):
        return ProvenanceDecision(
            source_type="unknown",
            metadata_readable=False,
            execution_trusted=False,
            reasons=("provenance_unknown_source",),
            note="non_mapping_source",
        )

    raw_type = source.get("sourceType", source.get("source_type", source.get("origin", "unknown")))
    source_type = _normalize_source_type(raw_type)

    # An executable field anywhere → denied regardless of declared type.
    executable_field_present = any(
        isinstance(k, str) and _looks_executable(k)
        for k in source.keys()
    )

    reasons: list[str] = []

    if executable_field_present:
        reasons.append("executable_field_denied")
        return ProvenanceDecision(
            source_type=source_type,
            metadata_readable=False,
            execution_trusted=False,
            reasons=tuple(reasons),
            note="source_carries_execution_surface",
        )

    if source_type in ALLOWED_SOURCE_TYPES:
        return ProvenanceDecision(
            source_type=source_type,
            metadata_readable=True,
            execution_trusted=False,
            reasons=(),
            note="descriptor_only_metadata_no_trust_decision",
        )

    reason = _DENIED_SOURCE_TYPES.get(source_type, "unknown_source_denied")
    reasons.append(reason)
    return ProvenanceDecision(
        source_type=source_type,
        metadata_readable=False,
        execution_trusted=False,
        reasons=tuple(reasons),
        note="untrusted_source_denied",
    )


_EXEC_SOURCE_STEMS: frozenset[str] = frozenset(
    {
        "entrypoint", "entrypoints", "module", "modules", "import", "imports",
        "importpath", "command", "commands", "cmd", "exec", "execute",
        "executable", "shell", "bash", "sh", "script", "scripts", "url", "href",
        "download", "downloads", "install", "installs", "installcommand",
        "package", "packages", "packageurl", "docker", "dockerimage", "image",
        "wheel", "wheelurl", "manifest", "manifesturl", "callable", "function",
        "handler", "binary", "subprocess", "childprocess", "process", "spawn",
        "fork", "code", "eval", "loader", "runtime", "program", "python",
        "node", "interpreter", "main", "app", "run", "src", "source", "file",
        "path",
    }
)

#: Normalized forms of the source-type CLASSIFIER keys. These keys identify the
#: source type itself (read separately above) and are never an execution
#: surface, so they are skipped by the executable-field scan — this lets
#: ``source`` stay in the stem set (so a bare ``source`` key is denied) without
#: ``sourceType`` / ``source_type`` tripping it.
_SOURCE_TYPE_KEY_NORMALIZED: frozenset[str] = frozenset({"sourcetype", "origin", "type"})


def _descriptor_key_tokens(key: str) -> list[str]:
    """Split a key into lowercase tokens on separators AND camelCase."""
    tokens: list[str] = []
    for part in re.split(r"[^A-Za-z0-9]+", key):
        if not part:
            continue
        sub = re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", part)
        tokens.extend(s.lower() for s in (sub or [part.lower()]))
    return tokens


def _looks_executable(key: str) -> bool:
    """True if a source key name denotes an execution surface.

    Token-exact matching (camelCase + separator split) so benign keys like
    ``description`` (which contains the substring "script") and ``profile``
    (contains "file") are NOT flagged, while ``subprocess``, ``sourceCode``,
    ``dockerImage`` are. The source-type classifier keys
    (``sourceType`` / ``source_type`` / ``origin`` / ``type``) are skipped.
    """
    if not isinstance(key, str):
        return False
    normalized = key.strip().lower().replace("-", "").replace("_", "").replace(".", "")
    if normalized in _SOURCE_TYPE_KEY_NORMALIZED:
        return False
    tokens = _descriptor_key_tokens(key)
    return any(tok in _EXEC_SOURCE_STEMS for tok in tokens)


@dataclass(frozen=True, slots=True)
class ProvenanceIntegrityDecision:
    """Checksum / signature requirement status for a plugin source.

    Requirements are *metadata expectations only* — nothing is fetched or
    verified against a real download (no network). A missing requirement
    leaves integrity unresolved; it is never auto-satisfied.
    """

    requirements_present: bool
    verified: bool
    reasons: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "requirementsPresent": self.requirements_present,
                "verified": self.verified,
                "reasons": list(self.reasons),
                "redactionApplied": True,
            }
        )


def evaluate_provenance_integrity(source: Any) -> ProvenanceIntegrityDecision:
    """Report whether a source carries checksum/signature metadata.

    ``verified`` is always False in the dev skeleton (no download, no
    cryptographic verification). Present requirements are noted but do not
    resolve the gate.
    """
    if not isinstance(source, Mapping):
        return ProvenanceIntegrityDecision(
            requirements_present=False, verified=False, reasons=("provenance_unknown_source",)
        )
    has_checksum = any(
        isinstance(k, str) and ("checksum" in k.lower() or "sha" in k.lower() or "digest" in k.lower())
        for k in source.keys()
    )
    has_signature = any(
        isinstance(k, str) and ("signature" in k.lower() or "signed" in k.lower())
        for k in source.keys()
    )
    requirements_present = has_checksum or has_signature
    reasons: list[str] = []
    if not requirements_present:
        reasons.append("integrity_requirements_missing")
    else:
        reasons.append("integrity_requirements_present_not_verified")
    return ProvenanceIntegrityDecision(
        requirements_present=requirements_present,
        verified=False,
        reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# 9. Route-governance exception evaluator (P0-16)
# ---------------------------------------------------------------------------

#: The frozen route-governance baseline (mirrors dev_web_safety_baseline).
ROUTE_GOVERNANCE_BASELINE: str = "34/34/5/0/1/1"


@dataclass(frozen=True, slots=True)
class RouteExceptionDecision:
    """Route-governance exception decision. Approval is never automatic."""

    route_change_detected: bool
    route_exception_required: bool
    route_exception_approved: bool
    reasons: tuple[str, ...]
    ignored_metadata_keys: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "routeChangeDetected": self.route_change_detected,
                "routeExceptionRequired": self.route_exception_required,
                "routeExceptionApproved": self.route_exception_approved,
                "reasons": list(self.reasons),
                "ignoredMetadataKeys": list(self.ignored_metadata_keys),
                "redactionApplied": True,
            }
        )


#: Markers that indicate a route / OpenAPI mutation intent. Matched against a
#: text projection of the requested change (keys, values, or a free-form
#: description string), so a route change is detected whether it arrives as a
#: mapping, a list, a tuple, or a descriptive string. Over-detection is safe
#: here: a false positive only sets ``route_exception_required=True`` while
#: ``route_exception_approved`` stays False.
_ROUTE_CHANGE_MARKERS: tuple[str, ...] = (
    "route", "openapi", "endpoint", "verb", "method", "add", "new", "modify",
    "change", "create", "register", "post", "put", "patch", "delete",
)


def _route_change_text(requested_change: Any) -> str:
    """Project *requested_change* to a text blob for marker scanning."""
    if isinstance(requested_change, Mapping):
        parts: list[str] = []
        for key, val in requested_change.items():
            if isinstance(key, str):
                parts.append(key)
            parts.append(str(val))
        return " ".join(parts)
    if isinstance(requested_change, (list, tuple)):
        return " ".join(str(item) for item in requested_change)
    if isinstance(requested_change, str):
        return requested_change
    return str(requested_change) if requested_change else ""


def _route_change_requested(requested_change: Any) -> bool:
    """True if *requested_change* describes any route/OpenAPI mutation.

    Handles mappings (keys + values), lists, tuples, and free-form description
    strings — a route change described in any of these shapes is detected so
    the route-governance-reviewer gate is flagged.
    """
    if requested_change is None:
        return False
    text = _route_change_text(requested_change)
    if not text.strip():
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in _ROUTE_CHANGE_MARKERS)


def evaluate_route_exception(
    requested_change: Any = None,
    *,
    untrusted_metadata: Any = None,
) -> RouteExceptionDecision:
    """Evaluate a route-governance exception request.

    A detected route change is flagged ``route_exception_required``, but
    ``route_exception_approved`` is **always False** — route-governance
    approval is a human route-governance-reviewer action and cannot be granted
    by code or metadata. No route is added; the OpenAPI surface is unchanged.
    """
    ignored = detect_untrusted_metadata(untrusted_metadata)
    detected = _route_change_requested(requested_change)
    reasons: list[str] = []
    if detected:
        reasons.append("route_exception_requires_human_route_governance_approval")
    if ignored:
        reasons.append("untrusted_metadata_ignored")
    return RouteExceptionDecision(
        route_change_detected=detected,
        route_exception_required=detected,
        route_exception_approved=False,
        reasons=tuple(reasons),
        ignored_metadata_keys=ignored,
    )


# ---------------------------------------------------------------------------
# 10. Rollback / incident readiness evaluator (P0-21 / P0-23)
# ---------------------------------------------------------------------------

#: Filenames that look like a production runtime store — never a safe cleanup
#: target (string-match only; the real paths are never touched).
_UNSAFE_CLEANUP_MARKERS: tuple[str, ...] = (
    "state.db",
    "gateway.db",
    "sessions.db",
    "plugin_registry.json",
    "plugin_execution_store.json",
    "provider_live_store.json",
    "workflow_runtime_store.json",
    "audit_runtime_store.json",
    "capability_runtime_store.json",
    "plugin_runtime.jsonl",
)


@dataclass(frozen=True, slots=True)
class RollbackReadinessDecision:
    """Rollback / incident readiness. Never ready without human/operator sign-off."""

    ready: bool
    cleanup_targets_safe: bool
    production_path_present: bool
    incident_owner_present: bool
    reasons: tuple[str, ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "ready": self.ready,
                "cleanupTargetsSafe": self.cleanup_targets_safe,
                "productionPathPresent": self.production_path_present,
                "incidentOwnerPresent": self.incident_owner_present,
                "reasons": list(self.reasons),
                "redactionApplied": True,
            }
        )


def _is_safe_cleanup_target(target: Any) -> bool:
    """True iff *target* is a temp/fake-style path with no production marker.

    String-only inspection: a production home segment, a production-db stem, or
    a known runtime-store filename makes the target unsafe. The real paths are
    never opened — this is pure policy.
    """
    if not isinstance(target, str):
        return False
    lowered = target.lower()
    if ".hermes" in lowered:
        return False
    if "/users/" in lowered and "/.hermes" in lowered:
        return False
    for marker in _UNSAFE_CLEANUP_MARKERS:
        if marker in lowered:
            return False
    # Treat an absolute non-temp path as unsafe (rollback targets are temp/fake
    # only). Allow explicit temp markers.
    if lowered.startswith("/") and "/tmp/" not in lowered and "/temp/" not in lowered and "tmp" not in lowered:
        return False
    return True


#: Tokens that mark an incident-owner string as fake / placeholder / AI-attributed
#: / a role (not a person). Matched per-token so "approved-by-ai" and "ai-approver"
#: are caught while a real name like "aidan" is not.
_FAKE_OWNER_TOKENS: frozenset[str] = frozenset(
    {
        # placeholders / sentinels
        "null", "none", "nil", "na", "n", "tbd", "todo", "pending", "missing",
        "unknown", "unspecified", "placeholder", "default", "nobody",
        "anonymous", "x", "xx", "xxx", "test", "demo", "sample", "example",
        "fake", "foo", "bar", "baz",
        # affirmatives (sound like an approval, not an owner)
        "approved", "approve", "accept", "accepted", "confirmed", "confirm",
        "valid", "true", "yes", "y", "done", "ok", "success", "successful",
        "signed",
        # roles / non-person identifiers
        "owner", "admin", "reviewer", "operator", "system", "auto",
        "automated", "self", "me", "you", "user", "someone",
        # ai-attributed
        "ai", "llm", "claude", "gpt", "bot", "machine", "ml", "model",
        "copilot",
    }
)


def _is_fake_owner(owner: Any) -> bool:
    """True iff *owner* looks fake / placeholder / AI-attributed / a role.

    Token-based: the owner is split on non-alphanumerics and any token matching
    a fake/placeholder/affirmative/role/AI marker rejects it. A real owner
    handle (e.g. ``release-engineering``, ``aidan``) has no such token.
    """
    if not isinstance(owner, str):
        return True
    text = owner.strip().lower()
    if not text or text in {"", "-", "n/a"}:
        return True
    tokens = [tok for tok in re.split(r"[^a-z0-9]+", text) if tok]
    if not tokens:
        return True
    if any(tok in _FAKE_OWNER_TOKENS for tok in tokens):
        return True
    # A real owner handle has at least one substantial token.
    if all(len(tok) < 2 for tok in tokens):
        return True
    return False


def evaluate_rollback_readiness(rollback_plan: Any) -> RollbackReadinessDecision:
    """Evaluate rollback / incident readiness. Partial at best.

    Cleanup targets must all be temp/fake (a production-looking target denies
    readiness). An incident owner must be present and not a fake/metadata
    string. Even with both, ``ready`` is False — readiness requires
    human/operator approval this evaluator cannot grant.
    """
    if not isinstance(rollback_plan, Mapping):
        return RollbackReadinessDecision(
            ready=False,
            cleanup_targets_safe=False,
            production_path_present=False,
            incident_owner_present=False,
            reasons=("rollback_plan_missing",),
        )

    raw_targets = rollback_plan.get("cleanupTargets", rollback_plan.get("cleanup_targets", []))
    targets: list[Any] = raw_targets if isinstance(raw_targets, (list, tuple)) else []

    production_path_present = any(
        isinstance(t, str) and (".hermes" in t.lower() or "/users/" in t.lower())
        for t in targets
    )
    cleanup_safe = bool(targets) and all(_is_safe_cleanup_target(t) for t in targets)

    owner = rollback_plan.get("incidentOwner", rollback_plan.get("incident_owner"))
    owner_present = isinstance(owner, str) and not _is_fake_owner(owner)

    reasons: list[str] = []
    if production_path_present:
        reasons.append("production_path_in_cleanup_targets")
    if not targets:
        reasons.append("cleanup_targets_missing")
    elif not cleanup_safe:
        reasons.append("cleanup_target_not_temp_or_fake")
    if not owner_present:
        reasons.append("incident_owner_missing_or_fake")
    reasons.append("rollback_requires_human_operator_approval")

    return RollbackReadinessDecision(
        ready=False,
        cleanup_targets_safe=cleanup_safe and not production_path_present,
        production_path_present=production_path_present,
        incident_owner_present=owner_present,
        reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# 11. Evidence quality / reproducibility (P0-24)
# ---------------------------------------------------------------------------

#: Evidence quality levels.
EVIDENCE_QUALITY_NONE = "no_evidence"
EVIDENCE_QUALITY_PARTIAL = "partial"
EVIDENCE_QUALITY_CANDIDATE_FOR_REVIEW = "candidate_for_review"


@dataclass(frozen=True, slots=True)
class EvidenceQualityDecision:
    """Reproducibility classification for an evidence record."""

    quality: str
    reproducible: bool
    has_test_command: bool
    resolvable_without_human: bool

    def to_safe_dict(self) -> dict[str, Any]:
        return redact_sandbox_payload(
            {
                "quality": self.quality,
                "reproducible": self.reproducible,
                "hasTestCommand": self.has_test_command,
                "resolvableWithoutHuman": self.resolvable_without_human,
                "redactionApplied": True,
            }
        )


def classify_evidence_quality(evidence_record: Any) -> EvidenceQualityDecision:
    """Classify evidence reproducibility. Never resolvable without human approval.

    Evidence without a test command is ``partial`` (or ``no_evidence`` if the
    record is empty). Evidence with a test command is
    ``candidate_for_review`` — ready for a human to look at, **not** resolved.
    """
    if not isinstance(evidence_record, Mapping) or not evidence_record:
        return EvidenceQualityDecision(
            quality=EVIDENCE_QUALITY_NONE,
            reproducible=False,
            has_test_command=False,
            resolvable_without_human=False,
        )
    test_command = evidence_record.get("testCommand", evidence_record.get("test_command"))
    has_test = isinstance(test_command, str) and bool(test_command.strip())
    if has_test:
        quality = EVIDENCE_QUALITY_CANDIDATE_FOR_REVIEW
    else:
        quality = EVIDENCE_QUALITY_PARTIAL
    return EvidenceQualityDecision(
        quality=quality,
        reproducible=has_test,
        has_test_command=has_test,
        resolvable_without_human=False,
    )


# ---------------------------------------------------------------------------
# 12. Boundary re-affirmation (pure constants, grep-able)
# ---------------------------------------------------------------------------

NO_REAL_PLUGIN_RUNTIME: bool = True
NO_PLUGIN_EXECUTION: bool = True
NO_PLUGIN_LOADER: bool = True
NO_DYNAMIC_LOADING: bool = True
NO_EXTERNAL_NETWORK: bool = True
NO_REAL_API_KEY_READ: bool = True
NO_NEW_ROUTE: bool = True
NO_PRODUCTION_ACCESS: bool = True
NO_HUMAN_APPROVAL_FABRICATED: bool = True


def assert_no_side_effect_surface() -> None:
    """Re-affirm the no-side-effect + no-fabricated-approval invariants."""
    assert NO_REAL_PLUGIN_RUNTIME is True
    assert NO_PLUGIN_EXECUTION is True
    assert NO_PLUGIN_LOADER is True
    assert NO_DYNAMIC_LOADING is True
    assert NO_EXTERNAL_NETWORK is True
    assert NO_REAL_API_KEY_READ is True
    assert NO_NEW_ROUTE is True
    assert NO_PRODUCTION_ACCESS is True
    assert NO_HUMAN_APPROVAL_FABRICATED is True
    assert _REAL_TRUST_TOKEN is None, "dev skeleton must hold no trust token"
    assert all(not g.is_resolved() for g in GATES), "no gate may start resolved"


__all__ = [
    # status taxonomy
    "GATE_STATUS_NO_EVIDENCE",
    "GATE_STATUS_GOVERNANCE_ONLY",
    "GATE_STATUS_PARTIAL_EVIDENCE",
    "GATE_STATUS_CANDIDATE_FOR_REVIEW",
    "GATE_STATUS_BLOCKED_BY_HUMAN_REVIEW",
    "GATE_STATUS_NOT_RESOLVED",
    "GATE_STATUS_RESOLVED",
    "ALL_GATE_STATUSES",
    "UNRESOLVED_STATUSES",
    # frozen flags
    "IMPLEMENTATION_AUTHORIZATION",
    "PHASE_3I_AUTHORIZED",
    "REAL_RUNTIME",
    "NEW_ROUTE",
    "PRODUCTION_ROLLOUT",
    "ROUTE_GOVERNANCE_BASELINE",
    # reviewers
    "REVIEWER_SECURITY",
    "REVIEWER_PROJECT_OWNER",
    "REVIEWER_ROUTE_GOVERNANCE",
    "REVIEWER_AUDIT",
    "REVIEWER_PRODUCTION_SAFETY",
    "REVIEWER_CAPABILITY",
    "REVIEWER_IMPLEMENTATION",
    # gate model
    "P0GateEvidence",
    "GATES",
    "REMAINING_GATE_IDS",
    # human approval
    "HumanApprovalRecord",
    "create_human_approval",
    "is_approval_valid",
    # authorization
    "detect_untrusted_metadata",
    "AuthorizationDecision",
    "evaluate_authorization_request",
    # summary
    "P0EvidenceSummary",
    "evaluate_p0_evidence",
    # provenance
    "ALLOWED_SOURCE_TYPES",
    "PROVENANCE_REASONS",
    "ProvenanceDecision",
    "classify_plugin_source",
    "ProvenanceIntegrityDecision",
    "evaluate_provenance_integrity",
    # route exception
    "RouteExceptionDecision",
    "evaluate_route_exception",
    # rollback / incident
    "RollbackReadinessDecision",
    "evaluate_rollback_readiness",
    # evidence quality
    "EVIDENCE_QUALITY_NONE",
    "EVIDENCE_QUALITY_PARTIAL",
    "EVIDENCE_QUALITY_CANDIDATE_FOR_REVIEW",
    "EvidenceQualityDecision",
    "classify_evidence_quality",
    # boundary
    "NO_REAL_PLUGIN_RUNTIME",
    "NO_PLUGIN_EXECUTION",
    "NO_PLUGIN_LOADER",
    "NO_DYNAMIC_LOADING",
    "NO_EXTERNAL_NETWORK",
    "NO_REAL_API_KEY_READ",
    "NO_NEW_ROUTE",
    "NO_PRODUCTION_ACCESS",
    "NO_HUMAN_APPROVAL_FABRICATED",
    "assert_no_side_effect_surface",
]
