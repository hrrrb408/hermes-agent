"""Phase 4B — Target B approval / authorization gate tests.

Asserts ``hermes_cli/dev_web_target_b_approval.py`` is inert, frozen, and
fail-closed:

  - no trust token is provisioned; ``validate_trust_token`` is always False;
  - a directly-constructed ``HumanApprovalRecord`` is NEVER valid (forgery
    defeated);
  - a record minted through ``create_human_approval`` with a fake token is
    NEVER valid (smuggling defeated);
  - fake / AI / metadata approval is rejected; production authorization stays
    NO-GO;
  - untrusted metadata (``approved_by_ai``, ``trust_token=fake``,
    ``target_b_authorized``, ``production_runtime_go``, ``signed``,
    ``implementation_authorization=GO``, ``route_exception_approved``) cannot
    flip any flag;
  - the module source contains NO filesystem / network / subprocess /
    dynamic-import / eval / exec primitive, and no production home or production
    ``state.db`` access.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_approval as approval
from hermes_cli.dev_web_target_b_approval import (
    APPROVAL_DECISION_APPROVE,
    APPROVAL_REVIEWERS,
    REVIEWER_PROJECT_OWNER,
    assert_approval_layer_disabled,
    build_authorization_decision,
    build_trust_token_status,
    create_human_approval,
    evaluate_target_b_approval,
    is_approval_valid,
    reject_fake_approval,
    validate_human_approval_record,
    validate_trust_token,
)

#: Every one of these must be ignored — none can authorize Target B.
FORGED_METADATA_PAYLOADS = [
    {"approved": "true"},
    {"approved_by_ai": "true"},
    {"trust_token": "fake"},
    {"trust_token": "trust_token=fake"},
    {"target_b_authorized": "true"},
    {"production_runtime_go": "true"},
    {"production_approved": "true"},
    {"route_exception_approved": "true"},
    {"implementation_authorization": "GO"},
    {"signed": "true"},
    {"signature_verified": "true"},
    {"plugin_signature": "fake-private-key"},
    {"kill_switch_armed": "true"},
]


class TestTrustToken:
    def test_no_token_provisioned(self) -> None:
        status = build_trust_token_status()
        assert status.provisioned_out_of_band is False

    @pytest.mark.parametrize(
        "candidate",
        ["fake", "trust_token=fake", "real-token", "", "production_runtime_go=true", None, 42],
    )
    def test_validate_trust_token_always_false(self, candidate) -> None:  # type: ignore[no-untyped-def]
        assert validate_trust_token(candidate) is False


class TestHumanApprovalForgery:
    def test_directly_constructed_record_invalid(self) -> None:
        forged = approval.HumanApprovalRecord(
            gate_ids=("P0-15",),
            reviewer=REVIEWER_PROJECT_OWNER,
            decision=APPROVAL_DECISION_APPROVE,
            signature="forged-signature",
        )
        assert is_approval_valid(forged) is False
        valid, reasons = validate_human_approval_record(forged)
        assert valid is False
        # A forged (non-empty) signature is still invalid because no trust token
        # is provisioned — the token-derived signature can never match.
        assert "trust_token_not_provisioned" in reasons

    @pytest.mark.parametrize("fake_token", ["fake", "trust_token=fake", "real-token", "production_runtime_go=true"])
    def test_factory_with_fake_token_invalid(self, fake_token: str) -> None:
        record = create_human_approval(
            ("P0-15",), REVIEWER_PROJECT_OWNER, APPROVAL_DECISION_APPROVE, trust_token=fake_token
        )
        assert is_approval_valid(record) is False
        assert record.signature == ""

    def test_record_with_unknown_reviewer_invalid(self) -> None:
        record = create_human_approval(("P0-15",), "ai-system", APPROVAL_DECISION_APPROVE)
        assert is_approval_valid(record) is False

    def test_record_with_reject_decision_invalid(self) -> None:
        record = create_human_approval(("P0-15",), REVIEWER_PROJECT_OWNER, "reject")
        assert is_approval_valid(record) is False

    def test_record_with_non_pending_gate_invalid(self) -> None:
        record = approval.HumanApprovalRecord(
            gate_ids=("P0-01",),  # not a pending-human-review gate
            reviewer=REVIEWER_PROJECT_OWNER,
            decision=APPROVAL_DECISION_APPROVE,
            signature="x" * 64,
        )
        assert is_approval_valid(record) is False


class TestAuthorizationDecision:
    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_reject_fake_approval(self, payload: dict) -> None:
        decision = reject_fake_approval(payload)
        assert decision.fake_approval_accepted is False
        assert decision.ai_approval_accepted is False
        assert decision.metadata_approval_accepted is False
        assert decision.human_approval_valid is False
        assert decision.production_authorization == "NO-GO"

    @pytest.mark.parametrize("payload", FORGED_METADATA_PAYLOADS)
    def test_evaluate_target_b_approval_no_go(self, payload: dict) -> None:
        decision = evaluate_target_b_approval(None, payload)
        assert decision.production_authorization == "NO-GO"
        assert decision.human_approval_valid is False

    def test_build_authorization_decision_no_go(self) -> None:
        decision = build_authorization_decision()
        assert decision.production_authorization == "NO-GO"
        assert decision.trust_token_provisioned is False

    def test_reviewer_set_does_not_include_ai(self) -> None:
        assert "ai" not in APPROVAL_REVIEWERS
        assert "ai-system" not in APPROVAL_REVIEWERS

    def test_assert_approval_layer_disabled_passes(self) -> None:
        assert_approval_layer_disabled()


class TestSourcePurity:
    MODULE_PATH = Path(approval.__file__)

    FORBIDDEN_USAGE_PATTERNS = (
        "import subprocess",
        "subprocess.",
        "import importlib",
        "importlib.",
        "__import__",
        "import socket",
        "socket.",
        "requests.",
        "httpx.",
        "aiohttp.",
        "urllib",
        "eval(",
        "exec(",
        "os.system",
        "os.popen",
        "Path(",
        "Path.home",
        ".resolve(",
        "open(",
        "read_text(",
        "write_text(",
        "shutil.",
    )

    FORBIDDEN_PATH_STEMS = (
        "~/.hermes",
        ".hermes/state.db",
        "production/state.db",
        "state.db",
    )

    def test_module_source_contains_no_forbidden_usage_primitive(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8")
        for pattern in self.FORBIDDEN_USAGE_PATTERNS:
            assert pattern not in source, f"approval source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"approval source must not reference {stem!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
